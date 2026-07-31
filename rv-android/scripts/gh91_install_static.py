#!/usr/bin/env python3
"""gh91 — install the 30 re-analysed JSONs into STATIC_DIR and prove the copy (task 5.1).

This is the step that makes the whole re-run take effect. The consolidation path this change
prescribes (`consolidate_offline.sh` -> `regenerate_container.py:114`) opens
`os.path.join(STATIC_DIR, f"{apk}.json")` on the FLAT corpus directory. Until the 30 land
there, the campaign's output is inert: the consolidation would happily read the old JSONs and
emit numbers that look perfectly normal. That silent no-op is the failure mode the whole
change is guarding against (design.md, "Consolidation - the existing pipeline, and the trap").

WHY THE PREDECESSOR IS PRESERVED FIRST
    `<apk>.json.pkgdet` is not a backup of convenience - it is a stage-2 deliverable (task
    5.5). It is the evidence of what the old, wrong filtering key produced, which is what lets
    the paper side diff old against new without re-running anything. So the copy is refused
    outright if a `.pkgdet` already exists: overwriting one would destroy the only remaining
    copy of the predecessor.

WHY THE PROOF IS MECHANISED
    "It looks right" is not available here. A copy that silently touched a 31st file, or that
    left one of the 30 stale, produces a corpus that consolidates without complaint. The proof
    is therefore three-way and closed against the manifests written at task 4.4, before any
    copy existed:

      P1  the 30 installed .json now hash to `manifest_sa_rerun_30.sha256`
      P2  the 189 other .json still hash to `manifest_static_dir_pre_install.sha256`
      P3  the 30 .pkgdet hash to the PRE-INSTALL value of their .json - i.e. the predecessor
          was preserved intact rather than merely displaced

    P1 and P2 alone would pass if a predecessor had been lost in the process; P3 closes that.
    The file set is also checked for cardinality (219 .json, 30 .pkgdet, no strays), so a file
    that appeared or vanished cannot hide behind a hash comparison over the intersection.

Usage:
    uv run python scripts/gh91_install_static.py            # dry run - reports, copies nothing
    uv run python scripts/gh91_install_static.py --install  # perform the copy, then prove it
    uv run python scripts/gh91_install_static.py --verify   # prove an already-installed corpus

Exit code 0 only if every assertion passes.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
from pathlib import Path

DATASET = Path("/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET")
SRC_DIR = DATASET / "SA_RERUN_gh91"
RECORD_DIR = SRC_DIR / "record"
STATIC_DIR = DATASET / "APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706"

MANIFEST_30 = RECORD_DIR / "manifest_sa_rerun_30.sha256"
MANIFEST_PRE = RECORD_DIR / "manifest_static_dir_pre_install.sha256"

EXPECTED_TOTAL = 219
EXPECTED_NEW = 30
EXPECTED_UNTOUCHED = 189


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_manifest(path: Path) -> dict[str, str]:
    """Parse a `sha256sum`-style manifest, skipping the `#` provenance header."""
    entries: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        digest, name = line.split(None, 1)
        entries[name.strip()] = digest
    return entries


class Report:
    """Collects PASS/FAIL lines so every assertion is reported, not just the first failure."""

    def __init__(self) -> None:
        self.failed = False

    def check(self, ok: bool, label: str, detail: str = "") -> bool:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            self.failed = True
        print(f"  [{mark}] {label}" + (f" - {detail}" if detail else ""))
        return ok


def install(manifest_30: dict[str, str], report: Report) -> bool:
    """Preserve each predecessor as <apk>.json.pkgdet, then overwrite with the new JSON."""
    print("\n== INSTALL ==")
    names = sorted(manifest_30)

    # Refuse the whole batch before touching anything: a half-applied install is worse than
    # none, because the proof below cannot then distinguish it from a corrupted corpus.
    blockers: list[str] = []
    for name in names:
        src, dst, keep = SRC_DIR / name, STATIC_DIR / name, STATIC_DIR / f"{name}.pkgdet"
        if not src.is_file():
            blockers.append(f"source missing: {src}")
        if not dst.is_file():
            blockers.append(f"predecessor missing (nothing to preserve): {dst}")
        if keep.exists():
            blockers.append(f"refusing to clobber an existing predecessor copy: {keep}")
    if blockers:
        for line in blockers:
            print(f"  [FAIL] {line}")
        report.failed = True
        return False

    for name in names:
        src, dst, keep = SRC_DIR / name, STATIC_DIR / name, STATIC_DIR / f"{name}.pkgdet"
        shutil.copy2(dst, keep)   # preserve FIRST
        shutil.copy2(src, dst)    # then install
    print(f"  installed {len(names)} JSONs, preserved {len(names)} predecessors as .pkgdet")
    return True


def verify(manifest_30: dict[str, str], manifest_pre: dict[str, str], report: Report) -> None:
    print("\n== PROOF ==")

    jsons = {p.name for p in STATIC_DIR.glob("*.apk.json")}
    pkgdets = {p.name for p in STATIC_DIR.glob("*.apk.json.pkgdet")}
    new_names = set(manifest_30)

    # --- cardinality: a file that appeared or vanished cannot hide behind a hash diff -------
    report.check(len(jsons) == EXPECTED_TOTAL, f"{EXPECTED_TOTAL} .json present", f"found {len(jsons)}")
    report.check(len(pkgdets) == EXPECTED_NEW, f"{EXPECTED_NEW} .pkgdet present", f"found {len(pkgdets)}")
    report.check(jsons == set(manifest_pre), "the .json file set is unchanged since the pre-install manifest",
                 f"+{sorted(jsons - set(manifest_pre))} -{sorted(set(manifest_pre) - jsons)}")
    report.check(pkgdets == {f"{n}.pkgdet" for n in new_names},
                 "the .pkgdet set is exactly the 30 installed apps")

    live = {name: sha256(STATIC_DIR / name) for name in sorted(jsons)}

    # --- P1: the 30 are the new JSONs, byte for byte ----------------------------------------
    bad_new = [n for n in sorted(new_names) if live.get(n) != manifest_30[n]]
    report.check(not bad_new, f"P1 the {EXPECTED_NEW} installed JSONs match manifest_sa_rerun_30",
                 f"mismatched: {bad_new}")

    # --- P2: everything else is byte-identical to the pre-install state ----------------------
    others = sorted(set(manifest_pre) - new_names)
    bad_other = [n for n in others if live.get(n) != manifest_pre[n]]
    report.check(len(others) == EXPECTED_UNTOUCHED, f"{EXPECTED_UNTOUCHED} apps outside the 30",
                 f"found {len(others)}")
    report.check(not bad_other, f"P2 those {len(others)} JSONs are byte-identical to pre-install",
                 f"changed: {bad_other}")

    # --- P3: the predecessor was preserved, not merely displaced -----------------------------
    bad_keep = [n for n in sorted(new_names)
                if sha256(STATIC_DIR / f"{n}.pkgdet") != manifest_pre[n]]
    report.check(not bad_keep, "P3 each .pkgdet equals its predecessor's pre-install sha256",
                 f"mismatched: {bad_keep}")

    # --- the headline the task asks for -------------------------------------------------------
    changed = [n for n in sorted(manifest_pre) if live.get(n) != manifest_pre[n]]
    unchanged = len(manifest_pre) - len(changed)
    report.check(len(changed) == EXPECTED_NEW and set(changed) == new_names,
                 f"exactly {EXPECTED_NEW} files changed", f"changed {len(changed)}")
    report.check(unchanged == EXPECTED_UNTOUCHED, f"{EXPECTED_UNTOUCHED} files byte-identical",
                 f"unchanged {unchanged}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--install", action="store_true", help="perform the copy, then prove it")
    ap.add_argument("--verify", action="store_true", help="prove an already-installed corpus")
    args = ap.parse_args()

    manifest_30 = read_manifest(MANIFEST_30)
    manifest_pre = read_manifest(MANIFEST_PRE)
    print(f"STATIC_DIR : {STATIC_DIR}")
    print(f"source     : {SRC_DIR}")
    print(f"manifests  : {len(manifest_30)} new, {len(manifest_pre)} pre-install")

    report = Report()
    if len(manifest_30) != EXPECTED_NEW or len(manifest_pre) != EXPECTED_TOTAL:
        report.check(False, "manifest sizes", f"{len(manifest_30)} / {len(manifest_pre)}")
        return 1

    if args.install:
        if not install(manifest_30, report):
            return 1
        verify(manifest_30, manifest_pre, report)
    elif args.verify:
        verify(manifest_30, manifest_pre, report)
    else:
        jsons = len(list(STATIC_DIR.glob("*.apk.json")))
        pkgdets = len(list(STATIC_DIR.glob("*.apk.json.pkgdet")))
        print(f"\n== DRY RUN == corpus currently holds {jsons} .json and {pkgdets} .pkgdet")
        print("re-run with --install to copy, or --verify to prove an existing install")
        return 0

    print("\nRESULT:", "FAIL" if report.failed else "PASS")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
