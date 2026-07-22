#!/usr/bin/env python3
"""
Select and split APKs into calibration and holdout sets for validation.

Reads the passed APKs from filter_apks_static_analysis.py output and joins
with apks_complete.csv metadata to produce stratified calibration/holdout
splits with diversity across categories and app complexity (methods count).

Usage:
    python scripts/select_dataset.py \
        --passed-apks ./out/static_analysis_filter/passed_apks.txt \
        --csv /path/to/apks_complete.csv \
        --cal-size 30 \
        --output-dir ./out/dataset_selection \
        --seed 42

    # Just show stats without splitting:
    python scripts/select_dataset.py \
        --passed-apks ./out/static_analysis_filter/passed_apks.txt \
        --csv /path/to/apks_complete.csv \
        --stats-only
"""

import argparse
import csv
import logging
import os
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Size buckets for stratification
# ---------------------------------------------------------------------------

SIZE_BUCKETS = {
    "tiny": (0, 50),
    "small": (50, 200),
    "medium": (200, 500),
    "large": (500, 1500),
    "xlarge": (1500, float("in")),
}


def get_size_bucket(methods: int) -> str:
    for name, (lo, hi) in SIZE_BUCKETS.items():
        if lo <= methods < hi:
            return name
    return "xlarge"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ApkInfo:
    apk: str
    methods: int
    categories: List[str]
    crashes: int
    manifest_package: str
    detected_package: str
    primary_category: str = ""
    size_bucket: str = ""
    stratum: str = ""

    def __post_init__(self):
        self.size_bucket = get_size_bucket(self.methods)
        self.primary_category = self.categories[0] if self.categories else "Unknown"
        self.stratum = f"{self.primary_category}|{self.size_bucket}"


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_passed_apks(path: str) -> List[str]:
    """Load APK names from passed_apks.txt (one per line)."""
    with open(path, "r", encoding="utf-8") as f:
        apks = [line.strip() for line in f if line.strip()]
    # Ensure .apk suffix for matching
    apks = [a if a.endswith(".apk") else a + ".apk" for a in apks]
    log.info(f"Loaded {len(apks)} passed APKs from {path}")
    return apks


def load_csv_metadata(csv_path: str) -> dict:
    """Load metadata from apks_complete.csv, keyed by APK name."""
    metadata = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            metadata[row["apk"]] = row
    log.info(f"Loaded metadata for {len(metadata)} APKs from {csv_path}")
    return metadata


def parse_categories(raw: str) -> List[str]:
    """Parse categories from CSV format like "['Internet', 'Security']"."""
    cleaned = raw.strip("[]").replace("'", "").replace('"', "")
    return [c.strip() for c in cleaned.split(",") if c.strip()]


def build_apk_info_list(passed_apks: List[str], metadata: dict) -> List[ApkInfo]:
    """Join passed APKs with CSV metadata."""
    infos = []
    missing = 0
    for apk in passed_apks:
        row = metadata.get(apk)
        if row is None:
            log.warning(f"No metadata for {apk}, skipping")
            missing += 1
            continue
        try:
            methods = int(row.get("methods", 0))
        except (ValueError, TypeError):
            methods = 0
        try:
            crashes = int(row.get("crashes", 0))
        except (ValueError, TypeError):
            crashes = 0

        infos.append(
            ApkInfo(
                apk=apk,
                methods=methods,
                categories=parse_categories(row.get("categories", "")),
                crashes=crashes,
                manifest_package=row.get("manifest_package", ""),
                detected_package=row.get("detected_package", ""),
            )
        )

    if missing:
        log.warning(f"{missing} APKs had no metadata in CSV")
    log.info(f"Built info for {len(infos)} APKs")
    return infos


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def print_stats(infos: List[ApkInfo]) -> None:
    """Print dataset statistics."""
    print(f"\n{'='*60}")
    print(f" Dataset Statistics ({len(infos)} APKs)")
    print(f"{'='*60}\n")

    # Size distribution
    size_counts = Counter(a.size_bucket for a in infos)
    print("Size distribution (by methods count):")
    for bucket in SIZE_BUCKETS:
        lo, hi = SIZE_BUCKETS[bucket]
        hi_str = str(int(hi)) if hi != float("in") else "+"
        print(f"  {bucket:8s} ({lo}-{hi_str}): {size_counts.get(bucket, 0):3d}")
    print()

    # Category distribution
    cat_counts = Counter(a.primary_category for a in infos)
    print("Category distribution (primary):")
    for cat, count in cat_counts.most_common():
        print(f"  {cat:30s}: {count:3d}")
    print()

    # Methods stats
    methods = sorted(a.methods for a in infos)
    n = len(methods)
    print("Methods stats:")
    print(
        f"  min={methods[0]}, Q1={methods[n//4]}, median={methods[n//2]}, "
        f"Q3={methods[3*n//4]}, max={methods[-1]}, mean={sum(methods)/n:.0f}"
    )
    print()

    # Crashes stats
    crashes = sorted(a.crashes for a in infos)
    high_crash = [a for a in infos if a.crashes > 250]
    print(f"Crashes: min={crashes[0]}, median={crashes[n//2]}, max={crashes[-1]}")
    if high_crash:
        print(f"  High crash APKs (>250): {len(high_crash)}")
        for a in sorted(high_crash, key=lambda x: x.crashes, reverse=True):
            print(f"    {a.apk}: {a.crashes}")
    print()

    # Package mismatches
    mismatches = [
        a
        for a in infos
        if a.manifest_package != a.detected_package and a.detected_package
    ]
    print(f"Package mismatches (manifest != detected): {len(mismatches)}/{len(infos)}")
    print()

    # Strata distribution
    strata = Counter(a.stratum for a in infos)
    print(f"Strata (category|size) — {len(strata)} unique:")
    for stratum, count in strata.most_common():
        print(f"  {stratum:40s}: {count:3d}")
    print()


# ---------------------------------------------------------------------------
# Stratified split
# ---------------------------------------------------------------------------


def stratified_split(
    infos: List[ApkInfo],
    cal_size: int,
    seed: int = 42,
) -> tuple:
    """
    Split APKs into calibration and holdout sets using stratified sampling.

    Stratifies by primary_category + size_bucket to ensure both sets have
    similar distributions. Within each stratum, APKs are shuffled randomly.

    Args:
        infos: List of ApkInfo objects
        cal_size: Number of APKs for calibration set
        seed: Random seed for reproducibility

    Returns:
        (calibration_set, holdout_set) as lists of ApkInfo
    """
    if cal_size >= len(infos):
        log.error(f"cal_size ({cal_size}) >= total APKs ({len(infos)})")
        sys.exit(1)

    holdout_size = len(infos) - cal_size
    rng = random.Random(seed)

    # Group by stratum
    strata = defaultdict(list)
    for info in infos:
        strata[info.stratum].append(info)

    # Shuffle within each stratum
    for apks in strata.values():
        rng.shuffle(apks)

    # Proportional allocation: each stratum contributes proportionally to cal_size
    cal_set = []
    holdout_set = []

    cal_ratio = cal_size / len(infos)

    # First pass: allocate proportionally (floor)
    remaining_cal = cal_size
    stratum_items = sorted(strata.items(), key=lambda x: len(x[1]), reverse=True)

    for stratum_name, apks in stratum_items:
        n_cal = max(1, round(len(apks) * cal_ratio))
        # Don't exceed remaining quota
        n_cal = min(n_cal, remaining_cal, len(apks))
        if remaining_cal <= 0:
            n_cal = 0

        cal_set.extend(apks[:n_cal])
        holdout_set.extend(apks[n_cal:])
        remaining_cal -= n_cal

    # If we under-allocated, pull from holdout (largest strata first)
    if remaining_cal > 0:
        rng.shuffle(holdout_set)
        extra = holdout_set[:remaining_cal]
        cal_set.extend(extra)
        holdout_set = holdout_set[remaining_cal:]

    # If we over-allocated, move excess to holdout
    while len(cal_set) > cal_size:
        holdout_set.append(cal_set.pop())

    log.info(
        f"Split: {len(cal_set)} calibration + {len(holdout_set)} holdout = {len(cal_set) + len(holdout_set)} total"
    )
    return cal_set, holdout_set


def print_split_comparison(cal: List[ApkInfo], holdout: List[ApkInfo]) -> None:
    """Print side-by-side comparison of calibration and holdout sets."""
    print(f"\n{'='*60}")
    print(f" Split: {len(cal)} calibration / {len(holdout)} holdout")
    print(f"{'='*60}\n")

    # Size distribution comparison
    cal_sizes = Counter(a.size_bucket for a in cal)
    hold_sizes = Counter(a.size_bucket for a in holdout)
    print("Size distribution:")
    print(f"  {'Bucket':10s} {'Cal':>5s} {'%':>6s}  {'Hold':>5s} {'%':>6s}")
    print(f"  {'-'*38}")
    for bucket in SIZE_BUCKETS:
        cc = cal_sizes.get(bucket, 0)
        hc = hold_sizes.get(bucket, 0)
        cp = 100 * cc / len(cal) if cal else 0
        hp = 100 * hc / len(holdout) if holdout else 0
        print(f"  {bucket:10s} {cc:5d} {cp:5.1f}%  {hc:5d} {hp:5.1f}%")
    print()

    # Category distribution comparison
    cal_cats = Counter(a.primary_category for a in cal)
    hold_cats = Counter(a.primary_category for a in holdout)
    all_cats = sorted(set(list(cal_cats.keys()) + list(hold_cats.keys())))
    print("Category distribution:")
    print(f"  {'Category':25s} {'Cal':>5s} {'%':>6s}  {'Hold':>5s} {'%':>6s}")
    print(f"  {'-'*48}")
    for cat in all_cats:
        cc = cal_cats.get(cat, 0)
        hc = hold_cats.get(cat, 0)
        cp = 100 * cc / len(cal) if cal else 0
        hp = 100 * hc / len(holdout) if holdout else 0
        print(f"  {cat:25s} {cc:5d} {cp:5.1f}%  {hc:5d} {hp:5.1f}%")
    print()

    # Methods stats comparison
    cal_m = sorted(a.methods for a in cal)
    hold_m = sorted(a.methods for a in holdout)
    print("Methods stats:")
    print(f"  {'':10s} {'Cal':>10s}  {'Holdout':>10s}")
    print(f"  {'min':10s} {cal_m[0]:10d}  {hold_m[0]:10d}")
    print(f"  {'median':10s} {cal_m[len(cal_m)//2]:10d}  {hold_m[len(hold_m)//2]:10d}")
    print(
        f"  {'mean':10s} {sum(cal_m)/len(cal_m):10.0f}  {sum(hold_m)/len(hold_m):10.0f}"
    )
    print(f"  {'max':10s} {cal_m[-1]:10d}  {hold_m[-1]:10d}")
    print()


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def write_apk_list(apks: List[ApkInfo], path: str) -> None:
    """Write APK names to text file (one per line, without .apk extension)."""
    with open(path, "w", encoding="utf-8") as f:
        for a in sorted(apks, key=lambda x: x.apk):
            # Write without .apk extension (consistent with existing set files)
            name = a.apk.removesuffix(".apk")
            f.write(name + "\n")
    log.info(f"Wrote {len(apks)} APKs to {path}")


def write_detailed_csv(apks: List[ApkInfo], path: str, set_name: str) -> None:
    """Write detailed CSV with metadata for each APK in the set."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "apk",
                "set",
                "methods",
                "size_bucket",
                "primary_category",
                "crashes",
                "manifest_package",
                "detected_package",
                "stratum",
            ]
        )
        for a in sorted(apks, key=lambda x: x.apk):
            writer.writerow(
                [
                    a.apk,
                    set_name,
                    a.methods,
                    a.size_bucket,
                    a.primary_category,
                    a.crashes,
                    a.manifest_package,
                    a.detected_package,
                    a.stratum,
                ]
            )
    log.info(f"Wrote detailed CSV to {path}")


def write_full_report(
    all_apks: List[ApkInfo],
    cal: List[ApkInfo],
    holdout: List[ApkInfo],
    output_dir: str,
    cal_size: int,
    seed: int,
) -> None:
    """Write all output files."""
    os.makedirs(output_dir, exist_ok=True)

    # APK lists (text files)
    write_apk_list(cal, os.path.join(output_dir, "calibration_set_v2.txt"))
    write_apk_list(holdout, os.path.join(output_dir, "holdout_set_v2.txt"))
    write_apk_list(all_apks, os.path.join(output_dir, "all_valid_apks.txt"))

    # Detailed CSVs
    write_detailed_csv(
        cal, os.path.join(output_dir, "calibration_set_v2.csv"), "calibration"
    )
    write_detailed_csv(
        holdout, os.path.join(output_dir, "holdout_set_v2.csv"), "holdout"
    )

    # Combined CSV
    combined_path = os.path.join(output_dir, "dataset_split.csv")
    with open(combined_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "apk",
                "set",
                "methods",
                "size_bucket",
                "primary_category",
                "crashes",
                "stratum",
            ]
        )
        for a in sorted(cal, key=lambda x: x.apk):
            writer.writerow(
                [
                    a.apk,
                    "calibration",
                    a.methods,
                    a.size_bucket,
                    a.primary_category,
                    a.crashes,
                    a.stratum,
                ]
            )
        for a in sorted(holdout, key=lambda x: x.apk):
            writer.writerow(
                [
                    a.apk,
                    "holdout",
                    a.methods,
                    a.size_bucket,
                    a.primary_category,
                    a.crashes,
                    a.stratum,
                ]
            )
    log.info(f"Wrote combined split CSV to {combined_path}")

    # Summary
    summary_path = os.path.join(output_dir, "selection_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("Dataset Selection Summary\n")
        f.write(f"========================\n\n")
        f.write(f"Date: auto-generated\n")
        f.write(f"Seed: {seed}\n")
        f.write(f"Total valid APKs: {len(all_apks)}\n")
        f.write(f"Calibration set: {len(cal)} APKs\n")
        f.write(f"Holdout set: {len(holdout)} APKs\n")
        f.write(f"Cal ratio: {len(cal)/len(all_apks)*100:.1f}%\n\n")
        f.write("Stratification: primary_category + size_bucket\n")
        f.write(f"Size buckets: {SIZE_BUCKETS}\n")
    log.info(f"Wrote summary to {summary_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Select and split APKs into calibration/holdout sets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show stats only (no split):
  python scripts/select_dataset.py \\
      --passed-apks ./out/static_analysis_filter/passed_apks.txt \\
      --csv /path/to/apks_complete.csv \\
      --stats-only

  # Split 30 cal / rest holdout:
  python scripts/select_dataset.py \\
      --passed-apks ./out/static_analysis_filter/passed_apks.txt \\
      --csv /path/to/apks_complete.csv \\
      --cal-size 30 \\
      --output-dir ./out/dataset_selection

  # Split 50/50:
  python scripts/select_dataset.py \\
      --passed-apks ./out/static_analysis_filter/passed_apks.txt \\
      --csv /path/to/apks_complete.csv \\
      --cal-size 50 \\
      --output-dir ./out/dataset_selection
        """,
    )
    parser.add_argument(
        "--passed-apks",
        required=True,
        help="Path to passed_apks.txt from filter_apks_static_analysis.py",
    )
    parser.add_argument(
        "--csv",
        required=True,
        help="Path to apks_complete.csv with metadata",
    )
    parser.add_argument(
        "--cal-size",
        type=int,
        default=None,
        help="Number of APKs for calibration set (rest goes to holdout)",
    )
    parser.add_argument(
        "--output-dir",
        default="./out/dataset_selection",
        help="Output directory for split files (default: ./out/dataset_selection)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Only print dataset statistics, don't split",
    )

    args = parser.parse_args()

    # Load data
    passed_apks = load_passed_apks(args.passed_apks)
    metadata = load_csv_metadata(args.csv)
    infos = build_apk_info_list(passed_apks, metadata)

    if not infos:
        log.error("No valid APKs found")
        sys.exit(1)

    # Always show stats
    print_stats(infos)

    if args.stats_only:
        return

    # Split
    if args.cal_size is None:
        log.error("--cal-size is required for splitting (or use --stats-only)")
        sys.exit(1)

    cal, holdout = stratified_split(infos, args.cal_size, args.seed)
    print_split_comparison(cal, holdout)

    # Write output
    write_full_report(infos, cal, holdout, args.output_dir, args.cal_size, args.seed)

    print(f"\nOutput written to: {args.output_dir}/")
    print(f"  calibration_set_v2.txt  ({len(cal)} APKs)")
    print(f"  holdout_set_v2.txt      ({len(holdout)} APKs)")
    print("  dataset_split.csv       (combined with metadata)")


if __name__ == "__main__":
    main()
