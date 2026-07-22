#!/usr/bin/env python3
"""Gate G_signature_file_subset — STRICT ⊆ LENIENT on cryptoapp (gh60).

Background
----------
The gh60 split introduced two `TargetMethodSource` implementations:
    MopSpecsTargetSource     (--mop-dir <jca>)       LENIENT  per design D7
    SignatureFileTargetSource (--targets-file demo.txt) STRICT per-entry

Design D7 guarantees the bytecode-scan layer is LENIENT-by-construction,
so STRICT entries can never *add* call sites beyond what the LENIENT path
already matches — the inverse (STRICT shrinks the set) is the load-bearing
behavioural contract. The gate concretises that contract by running both
modes on cryptoapp and asserting

    {methods marked reachesTarget under STRICT} ⊆ {same under LENIENT}

Output
------
Exits 0 with a one-line PASS, or 1 with the offending methods listed.
Writes both raw JSON outputs to a `--workdir` (default: `/tmp/gh60_g_subset/`)
for post-mortem inspection — the operator may want to diff them by hand
when the gate fails.

Usage
-----
    python scripts/check_signature_file_subset.py
    python scripts/check_signature_file_subset.py --verbose
    python scripts/check_signature_file_subset.py --apk path/to/other.apk

Skipped when prerequisites are missing
--------------------------------------
    - RVSEC_HOME not set (no MOP specs)
    - cryptoapp.apk absent
    - lib/gator/{gator, rvsec-analysis-client.jar} missing (jar not deployed)

The exit code in those cases is 77 (POSIX "skipped" convention used by
automake) so the test harness can SKIP rather than FAIL.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKIP_EXIT = 77

# A minimal hand-picked subset of JCA target signatures — each is a STRICT
# entry (full param list).
#
# Picking rule for subset-safety
# ------------------------------
# Each entry's (className, methodName) pair MUST appear as a `call(...)`
# pattern inside the JCA .mop spec set. The bytecode-scan layer is LENIENT
# by construction (D7), so any STRICT signature whose class+name is also
# in the MOP set is guaranteed to match a strict subset of LENIENT hits.
# An entry whose class+name is absent (e.g. `SecretKeySpec.<init>`) will
# add call sites LENIENT never tracks and break the gate spuriously —
# verified empirically when the original 5-entry list flagged
# `CryptoUtils.createSecretKeyFromBytes` as a STRICT-only hit.
#
# Each pair below was cross-referenced against the JCA `.mop` files via
# `grep call(.*<class>.<name>` in `rvsec-mop/src/main/resources/jca/`.
STRICT_TARGETS = [
    "<javax.crypto.Cipher: javax.crypto.Cipher getInstance(java.lang.String)>",
    "<javax.crypto.Cipher: void init(int,java.security.Key)>",
    "<javax.crypto.KeyGenerator: javax.crypto.KeyGenerator getInstance(java.lang.String)>",
    "<javax.crypto.KeyGenerator: void init(int)>",
    "<javax.crypto.KeyGenerator: javax.crypto.SecretKey generateKey()>",
    "<javax.crypto.spec.IvParameterSpec: void <init>(byte[])>",
    "<java.security.MessageDigest: java.security.MessageDigest getInstance(java.lang.String)>",
]


def _run_gator(
    *,
    gator_dir: Path,
    apk: Path,
    client_jar: Path,
    out_json: Path,
    client_param: str,
    verbose: bool,
) -> None:
    """Drive ./gator with a single -clientParam token, blocking on completion.

    Uses `bash -l -c` like GatorTestHelper.java so /etc/profile is sourced
    (RVSEC_HOME, ANDROID_HOME). The timeout is 5 minutes — cryptoapp runs
    in ~6 s on a warm cache; the slack absorbs cold-cache + GC variance.
    """
    # CG algorithm: leave unset so GATOR uses its compiled-in default (spark
    # since gh51 D5). Until 2026-05-26 this line passed `-withCHA` explicitly,
    # which produced cha-era reachability numbers (67/61 on cryptoapp) — the
    # same numbers the stale in-tree baseline carried — so the parity gates
    # looked green even though production (which runs spark) emits 55/32.
    # See openspec/changes/gh60-targets-core/design.md §D12.
    cmd = (
        f"cd '{gator_dir}' && ./gator a -p '{apk}' --client-jar '{client_jar}'"
        f" --out '{out_json}' -client RvsecAnalysisClient"
        f" -clientParam '{client_param}' --timeout 300"
    )
    if verbose:
        print(f"[gator] {cmd}")
    proc = subprocess.run(
        ["bash", "-l", "-c", cmd],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"gator exited {proc.returncode} for {client_param}\n"
            f"stdout tail:\n{proc.stdout[-2000:]}\n"
            f"stderr tail:\n{proc.stderr[-2000:]}"
        )


def _reach_target_set(json_path: Path) -> set[str]:
    """Extract the set of Soot signatures where reachesTarget=True.

    Uses the renamed key `reachesTarget` directly (gh60 has landed).
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not data.get("complete"):
        # ADR-6 sentinel — incomplete runs cannot be compared meaningfully.
        raise RuntimeError(f"{json_path} missing 'complete':true sentinel — run truncated")
    out: set[str] = set()
    for cls in data.get("reachability", []):
        for m in cls.get("methods", []):
            if m.get("reachesTarget"):
                out.add(m["signature"])
    return out


def _checked_path(path: Path, label: str) -> Path | None:
    if not path.exists():
        print(f"[skip] {label} missing at {path}")
        return None
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="rv-android repo root (default: parent of this script's directory)",
    )
    parser.add_argument(
        "--apk",
        type=Path,
        help="APK to analyze (default: <root>/apks_examples/cryptoapp.apk)",
    )
    parser.add_argument(
        "--workdir",
        type=Path,
        default=Path("/tmp/gh60_g_subset"),
        help="scratch dir for the two JSON outputs and demo.txt",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    root: Path = args.root.resolve()
    apk: Path = (args.apk or (root / "apks_examples" / "cryptoapp.apk")).resolve()
    workdir: Path = args.workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    rvsec_home = os.environ.get("RVSEC_HOME")
    if not rvsec_home:
        print("[skip] RVSEC_HOME not set")
        return SKIP_EXIT
    mop_dir = Path(rvsec_home) / "rvsec" / "rvsec-mop" / "src" / "main" / "resources" / "jca"
    if _checked_path(mop_dir, "JCA mop dir") is None:
        return SKIP_EXIT
    if _checked_path(apk, "cryptoapp.apk") is None:
        return SKIP_EXIT
    gator_dir = root / "lib" / "gator"
    if _checked_path(gator_dir / "gator", "gator launcher") is None:
        return SKIP_EXIT
    client_jar = gator_dir / "rvsec-analysis-client.jar"
    if _checked_path(client_jar, "analysis-client jar") is None:
        return SKIP_EXIT
    if shutil.which("bash") is None:
        print("[skip] bash not on PATH")
        return SKIP_EXIT

    # 1. LENIENT run via mopDir
    lenient_json = workdir / "lenient.json"
    if args.verbose:
        print(f"[1/3] LENIENT — mopDir={mop_dir} → {lenient_json}")
    _run_gator(
        gator_dir=gator_dir,
        apk=apk,
        client_jar=client_jar,
        out_json=lenient_json,
        client_param=f"mopDir={mop_dir}",
        verbose=args.verbose,
    )

    # 2. demo.txt — hand-picked STRICT targets
    demo_txt = workdir / "demo.txt"
    demo_txt.write_text(
        "# gh60 G_signature_file_subset — STRICT targets derived from JCA\n"
        + "\n".join(STRICT_TARGETS)
        + "\n",
        encoding="utf-8",
    )

    # 3. STRICT run via targetsFile
    strict_json = workdir / "strict.json"
    if args.verbose:
        print(f"[2/3] STRICT — targetsFile={demo_txt} → {strict_json}")
    _run_gator(
        gator_dir=gator_dir,
        apk=apk,
        client_jar=client_jar,
        out_json=strict_json,
        client_param=f"targetsFile={demo_txt}",
        verbose=args.verbose,
    )

    # 4. Compare
    if args.verbose:
        print("[3/3] comparing reachesTarget sets")
    lenient = _reach_target_set(lenient_json)
    strict = _reach_target_set(strict_json)
    leak = strict - lenient

    print(
        f"G_signature_file_subset: |LENIENT|={len(lenient)} |STRICT|={len(strict)} "
        f"diff(STRICT\\LENIENT)={len(leak)}"
    )
    if leak:
        print("FAIL — STRICT contains methods absent from LENIENT (subset broken):")
        for sig in sorted(leak):
            print(f"  {sig}")
        return 1

    if not strict:
        # A guard against trivially-vacuous pass: STRICT must produce *some*
        # reachable methods, otherwise the demo.txt entries miss cryptoapp
        # entirely and the subset is empty ⊆ anything. Treat as FAIL — the
        # operator should add at least one signature that cryptoapp does
        # exercise.
        print("FAIL — STRICT result is empty; demo.txt targets don't match cryptoapp")
        return 1

    print("G_signature_file_subset: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
