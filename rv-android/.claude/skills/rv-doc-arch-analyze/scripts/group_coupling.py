"""External-coupling ratio of an architecture target, counted from first-party imports.

For a target (a subsystem of subsystems.yaml, or one module) this counts the
first-party import edges that leave each source file of the target and splits them
into internal (the imported unit lies inside the target's paths) and external
(first-party code outside the target). The ratio external / (internal + external)
says how much of the target's own wiring points outside its boundary.

Edges are deduplicated per (importing file, imported unit). Test code is skipped:
the ratio describes the shipped structure. Process and file-format contracts
(``java -jar``, JSON documents) are not imports, so this count does not see them;
analyze records those as ``relations[].mechanism``.

Usage (from the rv-android repository root):
    python3 .claude/skills/rv-doc-arch-analyze/scripts/group_coupling.py subsystem:instrumentation
    python3 .claude/skills/rv-doc-arch-analyze/scripts/group_coupling.py module:rv-platform
"""

import argparse
import ast
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

DEFAULT_MANIFEST = (
    Path(__file__).resolve().parents[2] / "rv-doc-arch" / "subsystems.yaml"
)
JAVA_FIRST_PARTY_PREFIX = "br.unb."
# Foundation packages every module imports (logging, error handling, validation, constants).
# They are the Aspects style of the module view, not a boundary leak, so edges into them are
# reported apart and left out of the ratio. Override with --cross-cutting.
CROSS_CUTTING = (
    "rv_android_core.util.logging",
    "rv_android_core.util.error",
    "rv_android_core.util.validation",
    "rv_android_core.constants",
)
# Indicative reading bands; the document states the number and the top targets, not a verdict.
RATIO_SELF_CONTAINED = 0.3
RATIO_MOSTLY_OUTSIDE = 0.5
TEST_DIR_NAMES = {"tests", "test"}
SKIP_DIR_NAMES = {".venv", "__pycache__", "build", "target", "node_modules"}
JAVA_PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
JAVA_IMPORT_RE = re.compile(
    r"^\s*import\s+(static\s+)?([\w.]+?)(\.\*)?\s*;", re.MULTILINE
)


def reading(ratio):
    if ratio is None:
        return "no first-party imports"
    if ratio < RATIO_SELF_CONTAINED:
        return "mostly self-contained"
    if ratio <= RATIO_MOSTLY_OUTSIDE:
        return "leans on outside code; name the contracts"
    return "mostly wired outside; check whether targets are a lower layer or a peer"


def resolve_target(target, manifest, root):
    """Return {language: [absolute paths]} for the target spec."""
    if target.startswith("module:"):
        return {"python": [root / "modules" / target.split(":", 1)[1]]}
    name = target.split(":", 1)[1] if target.startswith("subsystem:") else target
    groups = yaml.safe_load(manifest.read_text())
    if name not in groups:
        sys.exit(f"unknown subsystem '{name}'; known: {', '.join(sorted(groups))}")
    entry = groups[name]
    return {
        lang: [(root / p).resolve() for p in entry[lang]]
        for lang in ("python", "java")
        if lang in entry
    }


def in_group(path, group_paths):
    return any(path == g or g in path.parents for g in group_paths)


def walk_sources(group_paths, suffix):
    for g in group_paths:
        # A module root contributes its src/ tree only; scripts and docs are not structure.
        base = g / "src" if (g / "src").is_dir() and suffix == ".py" else g
        files = [g] if g.is_file() else base.rglob(f"*{suffix}")
        for f in files:
            rel = f.relative_to(g.parent if g.is_file() else base).parts[:-1]
            # Build-output names are skipped only above the first src/: below it they are
            # package names (rvsec-gator has presto.android.gui.clients.target).
            outer = rel[: rel.index("src")] if "src" in rel else rel
            if f.suffix != suffix or set(rel) & TEST_DIR_NAMES or set(outer) & SKIP_DIR_NAMES:
                continue
            if suffix == ".py" and f.name.startswith("test_"):
                continue
            yield f


# ---------------------------------------------------------------- Python


def python_package_roots(root):
    """Top-level first-party package name -> its directory (modules/*/src/<pkg>)."""
    return {
        pkg.name: pkg
        for pkg in (root / "modules").glob("*/src/*")
        if pkg.is_dir() and (pkg / "__init__.py").exists()
    }


def module_file(base, parts):
    """File of the longest existing module prefix of `parts` under `base`, else None."""
    for n in range(len(parts), -1, -1):
        stem = base.joinpath(*parts[:n]) if n else base
        if stem.with_suffix(".py").is_file() and n:
            return stem.with_suffix(".py")
        if (stem / "__init__.py").is_file():
            return stem / "__init__.py"
    return None


def python_targets(src, roots):
    """Yield the first-party file each import statement of `src` reaches."""
    tree = ast.parse(src.read_text(encoding="utf-8", errors="replace"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top, *rest = alias.name.split(".")
                if top in roots:
                    yield module_file(roots[top], rest)
        elif isinstance(node, ast.ImportFrom):
            names = [a.name for a in node.names if a.name != "*"] or [None]
            if node.level:
                base = src.parent
                for _ in range(node.level - 1):
                    base = base.parent
                mod = node.module.split(".") if node.module else []
                for name in names:
                    yield module_file(base, mod + ([name] if name else []))
            elif node.module:
                top, *rest = node.module.split(".")
                if top in roots:
                    for name in names:
                        yield module_file(roots[top], rest + ([name] if name else []))


def python_label(path, roots):
    for pkg, base in roots.items():
        if base == path or base in path.parents:
            rel = path.relative_to(base).with_suffix("").parts
            rel = [p for p in rel if p != "__init__"][:2]
            return ".".join([pkg, *rel])
    return str(path)


def python_counts(group_paths, root, cross_cutting):
    roots = python_package_roots(root)
    internal, external, aside, files = set(), set(), set(), 0
    for src in walk_sources(group_paths, ".py"):
        files += 1
        for target in python_targets(src, roots):
            if target is None or target == src:
                continue
            if in_group(target, group_paths):
                internal.add((src, target))
            elif python_label(target, roots).startswith(cross_cutting):
                aside.add((src, target))
            else:
                external.add((src, target))
    top = Counter(python_label(t, roots) for _, t in external)
    return files, len(internal), len(external), len(aside), top


# ------------------------------------------------------------------ Java


def java_counts(group_paths, prefix):
    sources = list(walk_sources(group_paths, ".java"))
    classes, packages, texts = set(), set(), {}
    for f in sources:
        text = f.read_text(encoding="utf-8", errors="replace")
        texts[f] = text
        m = JAVA_PACKAGE_RE.search(text)
        pkg = m.group(1) if m else ""
        packages.add(pkg)
        classes.add(f"{pkg}.{f.stem}" if pkg else f.stem)

    def defined(name):
        parts = name.split(".")
        return any(".".join(parts[:n]) in classes for n in range(len(parts), 0, -1))

    internal, external = set(), set()
    for f, text in texts.items():
        for static, name, wildcard in JAVA_IMPORT_RE.findall(text):
            if wildcard and not static:
                inside = name in packages
            else:
                inside = defined(
                    name.rsplit(".", 1)[0] if static and not wildcard else name
                )
            if inside:
                internal.add((f, name))
            elif name.startswith(prefix):
                external.add((f, name))
    top = Counter(n.rsplit(".", 1)[0] for _, n in external)
    return len(sources), len(internal), len(external), 0, top


# ------------------------------------------------------------------ main


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("target", help="subsystem:<name> | <name> | module:<name>")
    ap.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument(
        "--root", type=Path, default=Path.cwd(), help="rv-android repo root"
    )
    ap.add_argument("--java-prefix", default=JAVA_FIRST_PARTY_PREFIX)
    ap.add_argument(
        "--cross-cutting",
        nargs="*",
        default=list(CROSS_CUTTING),
        help="Python package prefixes counted apart from the ratio (empty to count all)",
    )
    ap.add_argument(
        "--top", type=int, default=5, help="external targets listed per language"
    )
    args = ap.parse_args()

    root = args.root.resolve()
    group = resolve_target(args.target, args.manifest, root)
    for paths in group.values():
        missing = [str(p) for p in paths if not p.exists()]
        if missing:
            sys.exit(f"paths not found: {', '.join(missing)}")

    rows = []
    if "python" in group:
        cross_cutting = tuple(args.cross_cutting)
        rows.append(("python", *python_counts(group["python"], root, cross_cutting)))
    if "java" in group:
        rows.append(("java", *java_counts(group["java"], args.java_prefix)))

    print(f"target: {args.target}")
    head = f"{'language':<9}{'files':>7}{'internal':>10}{'external':>10}{'x-cut':>7}{'ratio':>8}"
    print(f"{head}  reading")
    tot_i = tot_e = tot_x = 0
    for lang, files, i, e, x, _ in rows:
        ratio = e / (i + e) if i + e else None
        tot_i, tot_e, tot_x = tot_i + i, tot_e + e, tot_x + x
        shown = f"{ratio:.2f}" if ratio is not None else "-"
        print(f"{lang:<9}{files:>7}{i:>10}{e:>10}{x:>7}{shown:>8}  {reading(ratio)}")
    total = tot_e / (tot_i + tot_e) if tot_i + tot_e else None
    shown = f"{total:.2f}" if total is not None else "-"
    print(
        f"{'all':<9}{'':>7}{tot_i:>10}{tot_e:>10}{tot_x:>7}{shown:>8}  {reading(total)}"
    )
    for lang, _, _, _, _, top in rows:
        # Ties are ordered by name: Counter keeps set order, which follows the hash seed.
        ranked = sorted(top.items(), key=lambda kv: (-kv[1], kv[0]))
        for label, count in ranked[: args.top]:
            print(f"  external {lang}: {label} ({count})")


if __name__ == "__main__":
    main()
