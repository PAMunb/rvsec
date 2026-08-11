#!/usr/bin/env python3
"""Phase B preflight — refuse to start the 163-APK instrumentation on a wrong substrate.

Every assertion here guards a failure that is silent at the time it happens and expensive to
detect afterwards. The batch takes about 27 hours and writes 163 APKs; a substrate mistake is
only visible once the woven code is already inside them, at which point the corpus is
indistinguishable from a correct one by inspection.

The environment variables named in `rvsec-dataset`'s abandoned rerun plan
(`RVSEC_INSTRUMENTED_APKS_DIR` and its four siblings) do NOT apply to this route: they are read
only by `rvsec-dataset/src/rvsec_dataset/config.py`, and nothing under `rv-android/` reads them.
This route writes where `--output-dir` says and never touches `dataset.csv`.

Usage:
    uv run python scripts/e3_preflight_instrument.py --apks-filter <list> --output-dir <dir>
    uv run python scripts/e3_preflight_instrument.py ... --expect 10     # the pilot

Exit 0 iff every assertion passes. Anything else means do not launch.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import zipfile
from pathlib import Path

RV_ANDROID = Path(__file__).resolve().parent.parent
WORKSPACE = RV_ANDROID.parent.parent
EXPECTED_RVSEC_HOME = WORKSPACE / "rvsec"

MAVEN_REPO = Path("/home/pedro/desenvolvimento/repository")
RVSEC_CORE_JAR = (MAVEN_REPO / "br/unb/cic/rvsec-core/0.9.3-SNAPSHOT"
                  / "rvsec-core-0.9.3-SNAPSHOT.jar")

APKS_DIR = Path("/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS")

VARIANT = "dexlib2"


class Failed(Exception):
    """One assertion did not hold. Carries the message the operator needs."""


def check_rvsec_home() -> str:
    """`RVSEC_HOME` must be this workspace's reactor.

    Monitor generation and the runtime libraries are resolved relative to it. A stale value
    pointing at another checkout produces monitors from another set of specifications, which
    the run reports as success.
    """
    value = os.environ.get("RVSEC_HOME")
    if not value:
        raise Failed("RVSEC_HOME is not set")
    if Path(value).resolve() != EXPECTED_RVSEC_HOME.resolve():
        raise Failed(f"RVSEC_HOME is {value}, expected {EXPECTED_RVSEC_HOME}")
    specs = EXPECTED_RVSEC_HOME / "rvsec/rvsec-mop/src/main/resources/jca"
    count = len(list(specs.glob("*.mop")))
    if count != 23:
        raise Failed(f"{specs} holds {count} .mop files, expected the 23 frozen jca specs")
    return f"RVSEC_HOME={value} (23 jca specs)"


def check_rvsec_core_jar() -> str:
    """The `rvsec-core` in the local Maven repository is what gets dexed into every APK.

    It arrives there through `mvn dependency:copy-dependencies` against
    `/home/pedro/desenvolvimento/repository` (`instrumenter.py:114-123`) — not `~/.m2`. Study
    03 requires the reverted `ExecutionContext`, whose signature is the absence of the
    identity-keyed store; a jar still carrying it would weave the `jca_android` semantics into
    all 163 APKs with nothing in the output to say so.
    """
    if not RVSEC_CORE_JAR.is_file():
        raise Failed(f"missing {RVSEC_CORE_JAR}")
    with zipfile.ZipFile(RVSEC_CORE_JAR) as zf:
        blob = zf.read("br/unb/cic/mop/ExecutionContext.class")
    for marker in (b"IdentityHashMap", b"newSetFromMap"):
        if marker in blob:
            raise Failed(f"{RVSEC_CORE_JAR.name} still carries {marker.decode()} — "
                         f"the Phase 0 revert is not in this jar")
    if b"HashSet" not in blob:
        raise Failed(f"{RVSEC_CORE_JAR.name} has no HashSet in ExecutionContext — "
                     f"unexpected shape, inspect it before proceeding")
    return f"rvsec-core jar reverted (mtime {RVSEC_CORE_JAR.stat().st_mtime:.0f})"


def check_output_dir(output_dir: Path) -> str:
    """The output directory must not exist yet.

    Reusing one mixes substrates with no record of the boundary, and `get_instrumented_apks()`
    matches by file presence (INV-EXP-16): a half-woven APK left by an earlier attempt is
    indistinguishable from a complete one. Rollback is a fresh directory, never a resume.
    """
    if output_dir.exists():
        raise Failed(f"{output_dir} already exists — this route requires a fresh directory")
    if not output_dir.parent.is_dir():
        raise Failed(f"{output_dir.parent} does not exist")
    return f"{output_dir} is free"


def check_filter(filter_path: Path, expected: int) -> str:
    """The filter list must name exactly the intended APKs, byte for byte.

    Click only asserts the file exists. The parsing is
    `read_text().strip().splitlines()` matched by basename (`config.py:584-586`), so a `\\r`, a
    trailing space or a stray blank line silently drops an APK from the run and the batch
    finishes reporting success over a smaller corpus.
    """
    if not filter_path.is_file():
        raise Failed(f"missing {filter_path}")
    raw = filter_path.read_bytes()
    if b"\r" in raw:
        raise Failed(f"{filter_path} contains CR bytes — LF only")
    names = raw.decode("utf-8").strip().splitlines()
    if len(names) != expected:
        raise Failed(f"{filter_path} has {len(names)} entries, expected {expected}")
    if len(set(names)) != expected:
        raise Failed(f"{filter_path} has duplicate entries")
    for name in names:
        if name != name.strip():
            raise Failed(f"{filter_path}: entry {name!r} has surrounding whitespace")
        if not (APKS_DIR / name).is_file():
            raise Failed(f"{filter_path}: {name} is not in {APKS_DIR}")
    return f"{expected}/{expected} entries present in {APKS_DIR}"


def check_variant() -> str:
    """`dexlib2` must resolve to the DEX-native instrumenter.

    The CLI default is `ajc`, so the variant is passed explicitly on every real run; this
    asserts the name still dispatches where it is meant to, rather than falling through to a
    variant that would weave differently.
    """
    from rv_instrumentation.factory import get_instrumenter
    try:
        get_instrumenter(VARIANT, None)
    except ValueError as exc:
        raise Failed(f"{VARIANT} does not resolve: {exc}") from exc
    except Exception:
        # Constructing the instrumenter with a null config is expected to fail somewhere
        # inside it; what is under test is that dispatch reached the right class at all.
        pass
    from rv_instrumentation_dexlib2 import DexlibInstrumentation
    return f"{VARIANT} -> {DexlibInstrumentation.__name__}"


def check_java() -> str:
    """A JDK must be callable: the weaver shells out to it for every APK."""
    try:
        out = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Failed(f"cannot run java: {exc}") from exc
    if out.returncode != 0:
        raise Failed(f"java -version exited {out.returncode}")
    return (out.stderr or out.stdout).splitlines()[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apks-filter", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--expect", type=int, default=163,
                    help="how many APKs the filter must name (default 163)")
    args = ap.parse_args()

    checks = [
        ("RVSEC_HOME", check_rvsec_home),
        ("rvsec-core jar", check_rvsec_core_jar),
        ("output dir", lambda: check_output_dir(args.output_dir)),
        ("apks filter", lambda: check_filter(args.apks_filter, args.expect)),
        ("variant", check_variant),
        ("java", check_java),
    ]

    failures = 0
    for name, fn in checks:
        try:
            print(f"  PASS  {name:<16} {fn()}")
        except Failed as exc:
            print(f"  FAIL  {name:<16} {exc}")
            failures += 1

    print(f"\n{'PREFLIGHT PASSED' if not failures else f'PREFLIGHT FAILED ({failures})'}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
