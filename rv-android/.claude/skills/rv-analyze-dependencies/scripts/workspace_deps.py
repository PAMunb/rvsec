#!/usr/bin/env python3
"""Declared and actual dependencies between the uv workspace modules.

The module list comes from the root `pyproject.toml` (`[tool.uv.workspace]` members minus
exclude), and each module's import names come from the packages under its `src/`. Nothing
is keyed on a name prefix: `aperv_tool` and `rvagent_tool` are workspace packages too.

    python3 .claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py [module]
    python3 .claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py --src-dirs

Run from the repository root. `--src-dirs` prints each member's `src/` directory, one per
line, for greps that must cover exactly the workspace. With a module name, the per-module and SDP sections are
limited to edges touching that module; metrics are always computed on the whole workspace,
because Ca of a module depends on every other module.

Imports are read with `ast` from `src/` only (test-only imports are not dependencies).
Each import is tagged by where it sits: `top` (module level), `lazy` (inside a function,
e.g. a guarded plugin registration) or `type` (under `if TYPE_CHECKING:`).
"""

import ast
import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path.cwd()


def norm(name: str) -> str:
    return re.match(r"[A-Za-z0-9_.-]+", name.strip()).group(0).lower().replace("_", "-")


def workspace_modules() -> dict[str, Path]:
    ws = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["uv"]["workspace"]
    excluded = {p.resolve() for g in ws.get("exclude", []) for p in ROOT.glob(g)}
    modules = {}
    for pattern in ws["members"]:
        for path in sorted(ROOT.glob(pattern)):
            if (path / "pyproject.toml").is_file() and path.resolve() not in excluded:
                meta = tomllib.loads((path / "pyproject.toml").read_text())["project"]
                modules[norm(meta["name"])] = path
    return modules


def imports_of(src: Path, packages: dict[str, str]) -> dict[str, set[str]]:
    """Map workspace module -> set of placement tags for every import of it under src."""
    found: dict[str, set[str]] = defaultdict(set)

    def visit(node: ast.AST, tag: str) -> None:
        for child in ast.iter_child_nodes(node):
            child_tag = tag
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and tag == "top":
                child_tag = "lazy"
            if isinstance(child, ast.If) and "TYPE_CHECKING" in ast.unparse(child.test):
                for stmt in child.body:
                    visit(ast.Module(body=[stmt], type_ignores=[]), "type")
                for stmt in child.orelse:
                    visit(ast.Module(body=[stmt], type_ignores=[]), child_tag)
                continue
            names = []
            if isinstance(child, ast.Import):
                names = [a.name for a in child.names]
            elif isinstance(child, ast.ImportFrom) and child.level == 0 and child.module:
                names = [child.module]
            for name in names:
                top = name.split(".")[0]
                if top in packages:
                    found[packages[top]].add(child_tag)
            visit(child, child_tag)

    for py in src.rglob("*.py"):
        if "__pycache__" not in py.parts:
            visit(ast.parse(py.read_text(), str(py)), "top")
    return found


def main() -> None:
    modules = workspace_modules()
    if sys.argv[1:] == ["--src-dirs"]:
        print("\n".join(str((p / "src").relative_to(ROOT)) for p in modules.values()))
        return
    scope = norm(sys.argv[1]) if len(sys.argv) > 1 else None
    packages = {
        pkg.name: mod
        for mod, path in modules.items()
        for pkg in (path / "src").glob("*/")
        if (pkg / "__init__.py").is_file()
    }
    declared, actual = {}, {}
    for mod, path in modules.items():
        deps = tomllib.loads((path / "pyproject.toml").read_text())["project"].get("dependencies", [])
        declared[mod] = {norm(d) for d in deps if norm(d) in modules and norm(d) != mod}
        found = imports_of(path / "src", packages)
        found.pop(mod, None)
        actual[mod] = found

    print("=== MODULES (module: import packages) ===")
    for mod in modules:
        print(f"{mod}: {', '.join(p for p, m in packages.items() if m == mod)}")

    print("\n=== DECLARED vs IMPORTED (src/ only) ===")
    for mod in modules:
        if scope and mod != scope and scope not in declared[mod] and scope not in actual[mod]:
            continue
        imported = {d: "+".join(sorted(t)) for d, t in actual[mod].items()}
        print(f"\n{mod}")
        print(f"  declared:   {', '.join(sorted(declared[mod])) or '-'}")
        print(f"  imported:   {', '.join(f'{d}[{t}]' for d, t in sorted(imported.items())) or '-'}")
        print(f"  undeclared: {', '.join(sorted(set(imported) - declared[mod])) or '-'}")
        print(f"  unused:     {', '.join(sorted(declared[mod] - set(imported))) or '-'}")

    # Metrics on the declared graph: pyproject.toml is the architectural contract.
    ca = {m: sum(m in declared[o] for o in modules) for m in modules}
    ce = {m: len(declared[m]) for m in modules}
    inst = {m: ce[m] / (ca[m] + ce[m]) if ca[m] + ce[m] else 0.0 for m in modules}

    def depth(m: str, seen: frozenset = frozenset()) -> int:
        nxt = [d for d in declared[m] if d not in seen]
        return 1 + max(depth(d, seen | {m}) for d in nxt) if nxt else 0

    print("\n=== METRICS (declared graph) ===")
    print(f"{'module':28} {'Ca':>3} {'Ce':>3} {'I':>5} {'depth':>5}")
    for m in sorted(modules, key=lambda m: (inst[m], m)):
        print(f"{m:28} {ca[m]:>3} {ce[m]:>3} {inst[m]:>5.2f} {depth(m):>5}")

    print("\n=== SDP: edges where I(dependency) >= I(dependent) ===")
    hits = [
        (a, b) for a in modules for b in sorted(declared[a])
        if inst[b] >= inst[a] and (not scope or scope in (a, b))
    ]
    for a, b in hits:
        print(f"{a} (I={inst[a]:.2f}) -> {b} (I={inst[b]:.2f})")
    print("-" if not hits else "")

    print("=== CYCLES (declared + imported edges) ===")
    graph = {m: declared[m] | set(actual[m]) for m in modules}
    cycles = set()

    def walk(start: str, node: str, path: list[str]) -> None:
        for nxt in graph[node]:
            if nxt == start:
                cycles.add(tuple(path))
            elif nxt not in path and nxt > start:
                walk(start, nxt, path + [nxt])

    for m in sorted(modules):
        walk(m, m, [m])
    for c in sorted(cycles):
        print(" -> ".join(c + (c[0],)))
    print("-" if not cycles else "")


if __name__ == "__main__":
    main()
