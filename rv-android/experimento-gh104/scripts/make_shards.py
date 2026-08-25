#!/usr/bin/env python3
"""Partition the gh104 corpus into N shard filter files for stage 1 (dexlib2, on the host).

Stage 1 has no ``--jobs`` flag: ``instrument_apks`` is a plain ``for`` loop, one JVM per APK
(``modules/rv-instrumentation-dexlib2/.../dexlib_instrumentation.py``). The only parallelism
available is process sharding — N concurrent ``rv-experiment`` runs, each with its own
``--apks-filter`` and its own ``--output-dir`` (the work dir *is* the output dir, and the Java
``BatchRunner`` resolves flat scratch names inside it, so two JVMs sharing one would silently
overwrite each other's ``woven_classes.dex``).

Wall-clock of the whole stage is the slowest shard, and weaving cost tracks APK size closely.
Round-robin over the size-descending order spreads the heavy APKs one per shard, so the shards
finish together instead of one shard carrying three 100 MB apps while another idles.

Usage:
    uv run python experimento-gh104/scripts/make_shards.py
    uv run python experimento-gh104/scripts/make_shards.py --shards 8 --out-dir <dir>
    uv run python experimento-gh104/scripts/make_shards.py --check   # verify, write nothing

Exit 0 iff the shards are written (or verified) consistent with the subset.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RV_ANDROID = Path(__file__).resolve().parent.parent.parent

DATASET = Path("/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET")
DEFAULT_APKS_DIR = DATASET / "APKS"
DEFAULT_SUBSET = (DATASET / "APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162"
                  / "selected162.txt")
DEFAULT_OUT_DIR = RV_ANDROID / "experimento-gh104" / "filters"
DEFAULT_SHARDS = 8

SHARD_NAME = "s{index}.txt"


class Failed(Exception):
    """One invariant did not hold. Carries the message the operator needs."""


def read_name_list(path: Path) -> list[str]:
    """Read a filter list the same way ``rv-experiment`` does, and refuse anything it would eat.

    The consumer is ``set(Path(self.apks_filter).read_text().strip().splitlines())`` matched by
    basename (``modules/rv-experiment/src/rv_experiment/config.py:584-586``). That parse is
    unforgiving in a silent way: a ``\\r`` left by a CRLF editor, or a trailing space, becomes
    part of the name, the basename comparison misses, and the APK simply never enters the run —
    no warning, and the batch still reports success over the smaller corpus. So: LF only, no
    surrounding whitespace, no duplicates, no blank lines.
    """
    if not path.is_file():
        raise Failed(f"missing {path}")
    raw = path.read_bytes()
    if b"\r" in raw:
        raise Failed(f"{path} contains CR bytes — LF only")
    names = raw.decode("utf-8").strip().splitlines()
    for name in names:
        if name != name.strip():
            raise Failed(f"{path}: entry {name!r} carries surrounding whitespace")
        if not name:
            raise Failed(f"{path}: blank line")
        if not name.endswith(".apk"):
            raise Failed(f"{path}: entry {name!r} is not an .apk basename")
    if len(set(names)) != len(names):
        dupes = sorted({n for n in names if names.count(n) > 1})
        raise Failed(f"{path}: duplicate entries {dupes}")
    return names


def write_name_list(path: Path, names: list[str]) -> None:
    """Write a filter list in exactly the shape ``read_name_list`` accepts."""
    path.write_text("\n".join(names) + "\n", encoding="utf-8", newline="\n")


def sizes_of(apks_dir: Path, names: list[str]) -> dict[str, int]:
    """Size of every original APK, asserting the whole subset is actually there.

    The subset was selected against the *instrumented* corpus of comp162; stage 1 re-weaves from
    the originals, so the names have to exist in ``apks_dir`` too. A missing one would only show
    up as a shard that instruments fewer APKs than the preflight expects.
    """
    sizes = {}
    missing = []
    for name in names:
        apk = apks_dir / name
        if not apk.is_file():
            missing.append(name)
        else:
            sizes[name] = apk.stat().st_size
    if missing:
        raise Failed(f"{len(missing)} subset names absent from {apks_dir}: {missing[:5]}")
    return sizes


def partition(names: list[str], sizes: dict[str, int], shards: int) -> list[list[str]]:
    """Round-robin over the size-descending order: shard i takes ranks i, i+N, i+2N, ...

    Ties broken by name so the partition is reproducible across runs and machines.
    """
    ordered = sorted(names, key=lambda n: (-sizes[n], n))
    buckets: list[list[str]] = [[] for _ in range(shards)]
    for rank, name in enumerate(ordered):
        buckets[rank % shards].append(name)
    return buckets


def report(buckets: list[list[str]], sizes: dict[str, int]) -> None:
    """Print cardinality and byte load per shard, plus the imbalance ratio.

    The ratio is the honest predictor of how ragged the finish will be: at 1.0 all shards carry
    the same bytes, and stage-1 wall clock is the serial time divided by the shard count.
    """
    totals = []
    for index, bucket in enumerate(buckets):
        total = sum(sizes[n] for n in bucket)
        totals.append(total)
        print(f"  s{index}: {len(bucket):>4} apks  {total / 1e9:>6.2f} GB")
    if totals and min(totals) > 0:
        print(f"  byte imbalance (max/min): {max(totals) / min(totals):.3f}")


def do_write(args: argparse.Namespace, names: list[str], sizes: dict[str, int]) -> int:
    buckets = partition(names, sizes, args.shards)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for index, bucket in enumerate(buckets):
        write_name_list(args.out_dir / SHARD_NAME.format(index=index), bucket)
    print(f"wrote {args.shards} shards to {args.out_dir}")
    report(buckets, sizes)
    print(f"  total: {len(names)} apks")
    return 0


def do_check(args: argparse.Namespace, names: list[str], sizes: dict[str, int]) -> int:
    """Verify shards already on disk without touching them.

    Re-reads each shard through ``read_name_list``, so the CR / whitespace / duplicate gate runs
    against exactly the bytes ``rv-experiment`` will read at launch time.
    """
    buckets = []
    for index in range(args.shards):
        path = args.out_dir / SHARD_NAME.format(index=index)
        buckets.append(read_name_list(path))

    union: list[str] = [n for bucket in buckets for n in bucket]
    if len(set(union)) != len(union):
        dupes = sorted({n for n in union if union.count(n) > 1})
        raise Failed(f"a name appears in more than one shard: {dupes[:5]}")
    if set(union) != set(names):
        only_shards = sorted(set(union) - set(names))
        only_subset = sorted(set(names) - set(union))
        raise Failed(f"union != subset; extra in shards {only_shards[:5]}, "
                     f"missing from shards {only_subset[:5]}")

    print(f"checked {args.shards} shards in {args.out_dir} — union == subset, no duplicates")
    report(buckets, sizes)
    print(f"  total: {len(union)} apks")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apks-dir", type=Path, default=DEFAULT_APKS_DIR,
                    help="directory holding the ORIGINAL (non-instrumented) .apk files")
    ap.add_argument("--subset", type=Path, default=DEFAULT_SUBSET,
                    help="text file with one .apk basename per line")
    ap.add_argument("--shards", type=int, default=DEFAULT_SHARDS)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--check", action="store_true",
                    help="verify existing shards and write nothing")
    args = ap.parse_args()

    if args.shards < 1:
        print("--shards must be >= 1", file=sys.stderr)
        return 2

    try:
        names = read_name_list(args.subset)
        sizes = sizes_of(args.apks_dir, names)
        if args.shards > len(names):
            raise Failed(f"{args.shards} shards for {len(names)} apks leaves empty shards")
        return do_check(args, names, sizes) if args.check else do_write(args, names, sizes)
    except Failed as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
