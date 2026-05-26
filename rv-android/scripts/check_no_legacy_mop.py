#!/usr/bin/env python3
"""Gate G_no_legacy_mop — scan for legacy MOP identifiers post-rename (gh60).

Background
----------
Change gh60 renamed the gator-local MOP types and fields to Target:
    MopMethod alias  → TargetMethod          (within rvsec-gator)
    reaches_mop      → reaches_target        (rv-android-core, parser)
    reachesMop       → reachesTarget         (JSON keys, Java)
    mop_methods      → target_methods        (ComponentInfo)
    directly_reaches_mop → directly_reaches_target
    findDirectMopCallersByBytecodeScan → findDirectTargetCallersByBytecodeScan
… and ~260 other call sites across 41 files. INV-ANA-37 / NFR04 (P3: no
backward compat) demand the legacy names are absent from live code.

The upstream `br.unb.cic.mop.extractor.model.MopMethod` type retains its
original name because it ships from the rvsec-mop-extractor module (a
separate JavaMOP-derived component). That boundary is intentional —
`MopSpecsTargetSource` is the *adapter* and is allowed to keep MOP-named
variables for the bytes that arrive from the upstream API.

Forbidden tokens
----------------
Each token below must NOT appear in live code outside the documented
allowlist. The patterns are matched whole-word (`\\b…\\b`) so that
`MopSpecsTargetSource` (which contains the substring `Mop`) does not
get spuriously flagged.

    reaches_mop / reachesMop
    directly_reaches_mop / directlyReachesMop
    mop_methods / mopMethods
    MopReachability
    findDirectMopCallersByBytecodeScan
    NReachesMop, ReachesMopNode (none expected — included for safety)

`MopMethod` is **not** in the forbidden list — it is the upstream type
name and survives at the adapter boundary. The reviewer is expected to
keep an eye on it during review.

Allowlist (case-sensitive paths)
--------------------------------
    backup/                                            (historical, gitignored)
    modules/rv-agent/                                  (deprecated, per CLAUDE.md)
    openspec/                                          (SDD artifacts describe the rename history)
    docs/                                              (planning + retrospective notes)
    .planning/                                         (GSD scratchpad)
    rvsec-mop/, rvsec-mop-extractor/, rvsec-mop-defsuses/
                                                       (upstream modules — out of gh60 scope)
    rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/target/MopSpecsTargetSource.java
    rvsec-android/rvsec-gator/client/src/test/java/presto/android/gui/clients/BytecodeScanMatchTest.java
    rvsec-android/rvsec-gator/client/src/test/java/presto/android/gui/clients/MopSignatureLoaderTest.java
                                                       (MOP→Target adapter and its tests)

Scope (positive search roots)
-----------------------------
    rvsec/rvsec-android/rvsec-gator/   (Java production code + tests)
    modules/                           (Python production code + tests, excl rv-agent)
    scripts/                           (utility scripts)

Usage
-----
    python scripts/check_no_legacy_mop.py
    python scripts/check_no_legacy_mop.py --verbose
    python scripts/check_no_legacy_mop.py --root /custom/repo/root

Exit code 0 ⇒ gate PASS; exit code 1 ⇒ FAIL with listing.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

# Whole-word patterns. The boundary `\b` keeps `MopSpecsTargetSource` (which
# substring-contains "Mop") from matching `\bMop…\b` patterns.
FORBIDDEN_PATTERNS = [
    re.compile(r"\breaches_mop\b"),
    re.compile(r"\breachesMop\b"),
    re.compile(r"\bdirectly_reaches_mop\b"),
    re.compile(r"\bdirectlyReachesMop\b"),
    re.compile(r"\bmop_methods\b"),
    re.compile(r"\bmopMethods\b"),
    re.compile(r"\bMopReachability\b"),
    re.compile(r"\bfindDirectMopCallersByBytecodeScan\b"),
    re.compile(r"\bNReachesMop\b"),
    re.compile(r"\bReachesMopNode\b"),
]

# Filename-suffix allowlist (path ends with one of these — relative to the
# repo root layout the user has, which interleaves rvsec/ and rv-android/).
ALLOWLIST_SUFFIXES = (
    "MopSpecsTargetSource.java",
    "BytecodeScanMatchTest.java",
    "MopSignatureLoaderTest.java",
    # The scanner itself documents the forbidden tokens — exempting by
    # filename keeps the gate self-hosting without forcing awkward string
    # splits inside the docstring.
    "check_no_legacy_mop.py",
    "test_no_legacy_mop.py",
)

# Path-substring allowlist (matches anywhere in the relative path). This
# is the only directory filter — substring matching catches `backup/`
# nested under any module (e.g. `rv-android-core/backup/...`) without the
# scanner needing to know the depth in advance.
ALLOWLIST_DIR_SUBSTRINGS = (
    "/backup/",
    "backup/",                         # at the start of the relative path
    "/rv-agent/",                      # deprecated module, per CLAUDE.md + memory
    "/rvsec-mop/",
    "/rvsec-mop-extractor/",
    "/rvsec-mop-defsuses/",
    "/openspec/",
    "/docs/",
    "/.planning/",
    "/.claude/",
    "/.qwen/",
    "/target/classes/",                # maven build output
    "/target/test-classes/",
    "/.git/",
    "/__pycache__/",
    "/node_modules/",
    "/tests/lint/fixtures/",
    "/tests/parity/fixtures/",
)

# Search roots — relative to the rv-android working dir. The Java tree lives
# in a sibling repo (rvsec/rvsec-android/rvsec-gator) so the scanner walks
# upward to reach it. The roots are stored as `(label, path)` pairs purely
# for clearer diagnostics.
SCAN_ROOTS = (
    ("modules",        "modules"),
    ("scripts",        "scripts"),
    ("rvsec-gator",    "../rvsec/rvsec-android/rvsec-gator"),
)

# File-extension whitelist — restrict scanning to source files. JAR/PNG/etc.
# would never legitimately contain these tokens as source code (and binary
# false-positives are noise).
SOURCE_EXTENSIONS = (".java", ".py", ".sh", ".kt", ".groovy", ".xml")


@dataclass(frozen=True)
class Finding:
    """Single forbidden-token hit. ``path`` is repo-relative POSIX."""

    path: str
    line: int
    token: str
    snippet: str


def _is_allowlisted(rel_posix: str, filename: str) -> bool:
    if filename.endswith(ALLOWLIST_SUFFIXES):
        return True
    if any(needle in rel_posix for needle in ALLOWLIST_DIR_SUBSTRINGS):
        return True
    return False


def _iter_source_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        yield path


def scan(rv_android_root: Path) -> List[Finding]:
    """Walk all SCAN_ROOTS under ``rv_android_root`` and collect findings.

    Symlinks aren't followed (rglob default) — keeps the scanner from
    looping if the user has a self-referential workspace layout.
    """
    findings: List[Finding] = []
    for label, rel_root in SCAN_ROOTS:
        root = (rv_android_root / rel_root).resolve()
        for path in _iter_source_files(root):
            try:
                rel = path.relative_to(root).as_posix()
            except ValueError:
                rel = path.as_posix()
            tagged_rel = f"{label}/{rel}"
            if _is_allowlisted(tagged_rel, path.name):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                for pattern in FORBIDDEN_PATTERNS:
                    match = pattern.search(line)
                    if not match:
                        continue
                    findings.append(
                        Finding(
                            path=tagged_rel,
                            line=lineno,
                            token=match.group(0),
                            snippet=line.strip()[:200],
                        )
                    )
    return findings


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="rv-android repo root (default: parent of this script's directory)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print scan roots and counts even on PASS",
    )
    args = parser.parse_args(argv)

    rv_android_root: Path = args.root.resolve()
    findings = scan(rv_android_root)

    if args.verbose:
        print(f"[check_no_legacy_mop] root = {rv_android_root}")
        for label, rel in SCAN_ROOTS:
            resolved = (rv_android_root / rel).resolve()
            exists = "OK" if resolved.exists() else "MISSING"
            print(f"  scan root [{label}] = {resolved} [{exists}]")

    if not findings:
        print("G_no_legacy_mop: PASS (0 legacy MOP identifiers in live code)")
        return 0

    print(f"G_no_legacy_mop: FAIL ({len(findings)} legacy identifier(s) found)")
    for f in findings:
        print(f"  {f.path}:{f.line}: {f.token}  |  {f.snippet}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
