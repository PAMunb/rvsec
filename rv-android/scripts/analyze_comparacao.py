#!/usr/bin/env python3
"""Analysis script for the tool comparison experiment.

Compares rvsmart:mvp vs ape vs fastbot across six dimensions: executive
summary, bugs/anomalies, coverage, monitored-operation/error detection,
timing anomalies, and determinism (rep-to-rep variance). Outputs a
markdown report to stdout.

Each "area" function corresponds to a section in the experiment analysis
framework. Area numbers are non-contiguous because they map to the analysis
plan sections (some areas are handled elsewhere or were removed).

Key functions:
    - ``area1_summary``: Per-tool completion rate and mean coverage.
    - ``area2_anomalies``: Identifies APKs where rvsmart underperforms or
      outperforms baselines by a large margin (>15pp).
    - ``area3_coverage``: Win/tie/loss analysis for method, activity, and MOP
      coverage using a tolerance-based comparison.
    - ``area4_errors``: Monitored-operation violation detection comparison,
      including exclusive and missed detections.
    - ``area11_timing``: Duration distribution buckets and early-finish detection.
    - ``area12_determinism``: Coefficient of variation (CV) analysis between
      repetitions to assess result stability.
    - ``area16_validation``: Pass/fail checks against minimum coverage thresholds.

Usage:
    uv run python scripts/analyze_comparacao.py > report.md
"""

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "results"
CSV_PATH = DATA_DIR / "comparacao_consolidated.csv"

TOOLS = ["rvsmart:mvp", "ape", "fastbot"]
TOOL_SHORT = {"rvsmart:mvp": "rvsmart", "ape": "ape", "fastbot": "fastbot"}
COV_COLS = ["method_coverage", "activity_coverage", "mop_coverage"]
TIMEOUT = 600  # nominal timeout in seconds

# Tolerance for win/tie/loss classification: differences within this range
# (in percentage points) are considered ties. This accounts for noise in
# coverage measurement -- small differences are not meaningful.
PP_TOLERANCE = 2


def load_data() -> pd.DataFrame:
    """Load the consolidated comparison CSV and filter to the tools of interest.

    Returns:
        DataFrame with rows only for the TOOLS list, preserving all columns.
    """
    df = pd.read_csv(CSV_PATH)
    df = df[df["tool"].isin(TOOLS)].copy()
    return df


def print_section(title: str, level: int = 2) -> None:
    """Print a markdown section header.

    Args:
        title: Section title text.
        level: Heading level (2 = ``##``, 3 = ``###``).
    """
    print(f"\n{'#' * level} {title}\n")


# ---------------------------------------------------------------------------
# Area 1 - Executive Summary
# ---------------------------------------------------------------------------
def area1_summary(df: pd.DataFrame) -> None:
    """Print executive summary: completion rates and mean coverage per tool.

    Args:
        df: Filtered experiment DataFrame.
    """
    print_section("Area 1 - Executive Summary")

    for tool in TOOLS:
        t = df[df["tool"] == tool]
        name = TOOL_SHORT[tool]
        completed = (t["status"] == "COMPLETED").sum()
        total = len(t)
        print(f"**{name}**: {completed}/{total} completed")
        for col in COV_COLS + ["total_errors"]:
            vals = t[col].dropna()
            print(
                f"  {col}: mean={vals.mean():.2f}  median={vals.median():.2f}  std={vals.std():.2f}"
            )
        print()


# ---------------------------------------------------------------------------
# Area 2 - Bugs and Anomalies
# ---------------------------------------------------------------------------
def area2_anomalies(df: pd.DataFrame) -> None:
    """Identify APKs with anomalous coverage patterns.

    Detects four categories:
    - 2a: rvsmart at 0% method coverage while baselines exceed 10% (potential bug).
    - 2b: rvsmart significantly worse than both baselines (>15pp gap).
    - 2c: rvsmart significantly better than both baselines (>15pp advantage).
    - 2d: Failed tasks (OOM-killed containers).

    Args:
        df: Filtered experiment DataFrame.
    """
    print_section("Area 2 - Bugs and Anomalies")

    # Pivot to per-APK mean coverage across reps, one column per tool
    means = (
        df.groupby(["apk", "tool"])[COV_COLS + ["total_errors"]].mean().reset_index()
    )
    pivot = means.pivot(index="apk", columns="tool")

    # 2a: rvsmart 0% method cov but others >10%
    print_section("2a - rvsmart 0% method coverage, others >10%", 3)
    rs_meth = pivot[("method_coverage", "rvsmart:mvp")]
    ape_meth = pivot[("method_coverage", "ape")]
    fb_meth = pivot[("method_coverage", "fastbot")]
    mask = (rs_meth == 0) & ((ape_meth > 10) | (fb_meth > 10))
    zero_apks = mask[mask].index.tolist()
    if zero_apks:
        print(f"Found {len(zero_apks)} APKs:\n")
        for apk in zero_apks:
            print(
                f"- `{apk}`: ape={ape_meth.get(apk, 0):.1f}%, fastbot={fb_meth.get(apk, 0):.1f}%"
            )
    else:
        print("None found.")
    print()

    # 2b: rvsmart significantly less coverage (>15pp gap vs both)
    print_section("2b - rvsmart significantly LESS method coverage (>15pp vs both)", 3)
    gap_ape = ape_meth - rs_meth
    gap_fb = fb_meth - rs_meth
    mask = (gap_ape > 15) & (gap_fb > 15)
    worse_apks = mask[mask].index.tolist()
    if worse_apks:
        print(f"Found {len(worse_apks)} APKs:\n")
        print("| APK | rvsmart | ape | fastbot | gap_ape | gap_fb |")
        print("|-----|---------|-----|---------|---------|--------|")
        for apk in sorted(worse_apks, key=lambda a: -(gap_ape[a] + gap_fb[a]) / 2):
            print(
                f"| `{apk}` | {rs_meth[apk]:.1f} | {ape_meth[apk]:.1f} | {fb_meth[apk]:.1f} | {gap_ape[apk]:.1f} | {gap_fb[apk]:.1f} |"
            )
    else:
        print("None found.")
    print()

    # 2c: rvsmart significantly MORE coverage (>15pp vs both)
    print_section("2c - rvsmart significantly MORE method coverage (>15pp vs both)", 3)
    mask = (rs_meth - ape_meth > 15) & (rs_meth - fb_meth > 15)
    better_apks = mask[mask].index.tolist()
    if better_apks:
        print(f"Found {len(better_apks)} APKs:\n")
        print("| APK | rvsmart | ape | fastbot |")
        print("|-----|---------|-----|---------|")
        for apk in sorted(better_apks, key=lambda a: -rs_meth[a]):
            print(
                f"| `{apk}` | {rs_meth[apk]:.1f} | {ape_meth[apk]:.1f} | {fb_meth[apk]:.1f} |"
            )
    else:
        print("None found.")
    print()

    # 2d: Failed tasks
    print_section("2d - Failed tasks (OOM killed)", 3)
    failed = df[df["status"] != "COMPLETED"]
    if len(failed) > 0:
        print(f"Found {len(failed)} failed tasks:\n")
        for _, row in failed.iterrows():
            print(
                f"- `{row['apk']}` tool={row['tool']} rep={row['rep']} status={row['status']} duration={row['duration_s']}s"
            )
    else:
        print("None found.")
    print()


# ---------------------------------------------------------------------------
# Area 3 - Coverage Comparison
# ---------------------------------------------------------------------------
def area3_coverage(df: pd.DataFrame) -> None:
    """Compare coverage metrics using pairwise win/tie/loss analysis.

    For each coverage dimension (method, activity, MOP), computes the per-APK
    difference between rvsmart and each baseline, then classifies the outcome
    as win/tie/loss using PP_TOLERANCE.

    Args:
        df: Filtered experiment DataFrame.
    """
    print_section("Area 3 - Coverage Comparison")

    means = df.groupby(["apk", "tool"])["method_coverage"].mean().reset_index()
    pivot = means.pivot(index="apk", columns="tool", values="method_coverage")

    for other in ["ape", "fastbot"]:
        diff = pivot["rvsmart:mvp"] - pivot[other]
        diff = diff.dropna()
        print(f"**rvsmart - {other} (method_coverage)**:")
        print(f"  mean diff = {diff.mean():.2f}pp, median = {diff.median():.2f}pp")
        print(f"  min = {diff.min():.2f}pp, max = {diff.max():.2f}pp")

        wins = (diff > PP_TOLERANCE).sum()
        ties = ((diff >= -PP_TOLERANCE) & (diff <= PP_TOLERANCE)).sum()
        losses = (diff < -PP_TOLERANCE).sum()
        print(f"  Win/Tie/Loss: {wins}/{ties}/{losses} (±{PP_TOLERANCE}pp tolerance)")
        print()

    # Same for activity and mop
    for col in ["activity_coverage", "mop_coverage"]:
        means_c = df.groupby(["apk", "tool"])[col].mean().reset_index()
        pivot_c = means_c.pivot(index="apk", columns="tool", values=col)
        for other in ["ape", "fastbot"]:
            diff = pivot_c["rvsmart:mvp"] - pivot_c[other]
            diff = diff.dropna()
            wins = (diff > PP_TOLERANCE).sum()
            ties = ((diff >= -PP_TOLERANCE) & (diff <= PP_TOLERANCE)).sum()
            losses = (diff < -PP_TOLERANCE).sum()
            print(
                f"**{col} rvsmart vs {other}**: W/T/L = {wins}/{ties}/{losses}, mean diff = {diff.mean():.2f}pp"
            )
        print()


# ---------------------------------------------------------------------------
# Area 4 - MOP/Error Detection
# ---------------------------------------------------------------------------
def area4_errors(df: pd.DataFrame) -> None:
    """Compare monitored-operation violation detection across tools.

    Identifies APKs where rvsmart exclusively detects violations (not found
    by ape or fastbot) and APKs where rvsmart misses violations that baselines
    find. This reveals differences in exploration strategies.

    Args:
        df: Filtered experiment DataFrame.
    """
    print_section("Area 4 - MOP/Error Detection")

    # Use mean across reps: an APK "has errors" if the average across reps > 0
    means = df.groupby(["apk", "tool"])["total_errors"].mean().reset_index()
    pivot = means.pivot(index="apk", columns="tool", values="total_errors")

    # Per-tool: APKs with errors detected
    for tool in TOOLS:
        name = TOOL_SHORT[tool]
        has_err = (pivot[tool] > 0).sum()
        total_err = pivot[tool].sum()
        print(
            f"**{name}**: {has_err} APKs with errors, {total_err:.0f} total errors (mean across reps)"
        )

    print()

    # APKs where rvsmart finds errors but others don't
    print_section("rvsmart-exclusive error detection", 3)
    rs_err = pivot["rvsmart:mvp"] > 0
    ape_err = pivot["ape"] > 0
    fb_err = pivot["fastbot"] > 0
    exclusive = rs_err & ~ape_err & ~fb_err
    excl_apks = exclusive[exclusive].index.tolist()
    if excl_apks:
        print(f"Found {len(excl_apks)} APKs where only rvsmart detects errors:\n")
        for apk in excl_apks:
            print(f"- `{apk}`: rvsmart={pivot.loc[apk, 'rvsmart:mvp']:.1f} errors")
    else:
        print("None found.")
    print()

    # APKs where others find errors but rvsmart doesn't
    print_section("Errors missed by rvsmart (found by ape or fastbot)", 3)
    missed = ~rs_err & (ape_err | fb_err)
    missed_apks = missed[missed].index.tolist()
    if missed_apks:
        print(f"Found {len(missed_apks)} APKs:\n")
        for apk in missed_apks:
            print(
                f"- `{apk}`: ape={pivot.loc[apk, 'ape']:.1f}, fastbot={pivot.loc[apk, 'fastbot']:.1f}"
            )
    else:
        print("None found.")
    print()


# ---------------------------------------------------------------------------
# Area 11 - Timing Anomalies
# ---------------------------------------------------------------------------
def area11_timing(df: pd.DataFrame) -> None:
    """Analyze task duration distribution and identify timing anomalies.

    Tasks finishing early (<300s) may indicate crashes or trivially small apps.
    Tasks exceeding the nominal timeout (590-660s) indicate overhead from
    emulator teardown. Tasks >660s suggest a container hang.

    Args:
        df: Filtered experiment DataFrame.
    """
    print_section("Area 11 - Timing Anomalies")

    # Bucket boundaries chosen around the 600s nominal timeout:
    # 590-660s is the expected range (timeout + teardown overhead)
    buckets = [0, 60, 300, 590, 660, 99999]
    labels = ["<60s", "60-300s", "300-590s", "590-660s", ">660s"]

    print("**Duration distribution:**\n")
    print("| Bucket | " + " | ".join(TOOL_SHORT[t] for t in TOOLS) + " |")
    print("|--------|" + "|".join(["-----"] * len(TOOLS)) + "|")
    for i, label in enumerate(labels):
        row = f"| {label} |"
        for tool in TOOLS:
            t = df[df["tool"] == tool]
            count = (
                (t["duration_s"] >= buckets[i]) & (t["duration_s"] < buckets[i + 1])
            ).sum()
            row += f" {count} |"
        print(row)
    print()

    # Early finishers
    print_section("Tasks finishing early (<300s)", 3)
    early = df[df["duration_s"] < 300].sort_values("duration_s")
    if len(early) > 0:
        print(f"Found {len(early)} tasks:\n")
        print("| APK | tool | rep | duration | method_cov | status |")
        print("|-----|------|----|----------|------------|--------|")
        for _, r in early.iterrows():
            print(
                f"| `{r['apk']}` | {TOOL_SHORT[r['tool']]} | {r['rep']} | {r['duration_s']:.0f}s | {r['method_coverage']:.1f}% | {r['status']} |"
            )
    else:
        print("None found.")
    print()


# ---------------------------------------------------------------------------
# Area 12 - Determinism (Variance between reps)
# ---------------------------------------------------------------------------
def area12_determinism(df: pd.DataFrame) -> None:
    """Assess result determinism using coefficient of variation (CV) between reps.

    CV measures how much coverage varies across repetitions of the same
    APK+tool combination. High CV (>30%) indicates the tool is sensitive
    to non-deterministic factors (random seeds, emulator timing). Low CV
    suggests stable, reproducible results.

    Args:
        df: Filtered experiment DataFrame.
    """
    print_section("Area 12 - Determinism (Variance between reps)")

    # CV per APK x tool -- coefficient of variation = (std / mean) * 100
    grouped = df.groupby(["apk", "tool"])["method_coverage"]

    def cv(x):
        m = x.mean()
        if m == 0:
            return 0.0  # all zeros means deterministically zero coverage
        return (x.std() / m) * 100

    cv_df = grouped.apply(cv).reset_index(name="cv")

    print("**Mean CV of method_coverage per tool:**\n")
    for tool in TOOLS:
        name = TOOL_SHORT[tool]
        t = cv_df[cv_df["tool"] == tool]
        print(
            f"  {name}: mean CV = {t['cv'].mean():.2f}%, median = {t['cv'].median():.2f}%"
        )
    print()

    # High variance APKs
    print_section("High variance APKs (CV > 30%)", 3)
    high_cv = cv_df[cv_df["cv"] > 30].sort_values("cv", ascending=False)
    if len(high_cv) > 0:
        print(f"Found {len(high_cv)} APK×tool combinations:\n")
        print("| APK | tool | CV% |")
        print("|-----|------|-----|")
        for _, r in high_cv.iterrows():
            print(f"| `{r['apk']}` | {TOOL_SHORT[r['tool']]} | {r['cv']:.1f}% |")
    else:
        print("None found.")
    print()

    # Per-tool count of high-CV APKs
    print("**High-CV count per tool:**\n")
    for tool in TOOLS:
        name = TOOL_SHORT[tool]
        count = len(high_cv[high_cv["tool"] == tool])
        print(f"  {name}: {count} APKs with CV > 30%")
    print()


# ---------------------------------------------------------------------------
# Area 16 - Validation Criteria
# ---------------------------------------------------------------------------
def area16_validation(df: pd.DataFrame) -> None:
    """Validate each tool against minimum coverage thresholds.

    Thresholds are baseline expectations for a functioning testing tool:
    - Activity coverage >= 30%: tool navigates beyond the launcher
    - Method coverage >= 10%: tool exercises non-trivial app code
    - MOP coverage >= 5%: tool reaches at least some monitored operations

    Args:
        df: Filtered experiment DataFrame.
    """
    print_section("Area 16 - Validation Criteria")

    for tool in TOOLS:
        name = TOOL_SHORT[tool]
        t = df[df["tool"] == tool]
        total = len(t)
        completed = (t["status"] == "COMPLETED").sum()
        comp_rate = completed / total * 100

        # Mean coverage (completed only)
        tc = t[t["status"] == "COMPLETED"]
        mean_act = tc["activity_coverage"].mean()
        mean_meth = tc["method_coverage"].mean()
        mean_mop = tc["mop_coverage"].mean()

        # Thresholds
        act_pass = "PASS" if mean_act >= 30 else "FAIL"
        meth_pass = "PASS" if mean_meth >= 10 else "FAIL"
        mop_pass = "PASS" if mean_mop >= 5 else "FAIL"

        # Zero on BOTH metrics suggests the app crashed on launch or the tool
        # failed to interact at all -- these are not meaningful test results
        zero_all = ((tc["method_coverage"] == 0) & (tc["activity_coverage"] == 0)).sum()

        print(f"**{name}**:")
        print(f"  Completion rate: {comp_rate:.1f}% ({completed}/{total})")
        print(f"  Mean Act%: {mean_act:.2f}% [{act_pass} >= 30%]")
        print(f"  Mean Meth%: {mean_meth:.2f}% [{meth_pass} >= 10%]")
        print(f"  Mean MOP%: {mean_mop:.2f}% [{mop_pass} >= 5%]")
        print(f"  Zero-coverage tasks (crash/empty): {zero_all}/{completed}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    """Load experiment data and print the full analysis report to stdout."""
    df = load_data()
    print("# RVSmart Comparison Experiment - Analysis Report\n")
    print(
        f"Data: {len(df)} rows, {df['apk'].nunique()} APKs, tools: {', '.join(TOOLS)}"
    )
    # mode() returns the most common rep count -- should be uniform by design
    print(f"Reps per APK x tool: {df.groupby(['apk', 'tool']).size().mode().iloc[0]}")

    area1_summary(df)
    area2_anomalies(df)
    area3_coverage(df)
    area4_errors(df)
    area11_timing(df)
    area12_determinism(df)
    area16_validation(df)


if __name__ == "__main__":
    main()
