"""Consolidate experiment 4 results and merge with previous experiments.

Exp4 (2026-03-21): aperv:sata_mop (calibrated #139), ape, fastbot
Previous: ape, aperv:sata, aperv:sata_mop_v1, aperv:sata_mop_v2,
          aperv:sata_mop_llm, rvsmart:mvp

Output: all tools in one CSV for comparative analysis.

Usage:
    cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
    uv run python scripts/consolidate_exp4.py
"""

import json
from pathlib import Path

import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "data" / "results"

PREV_CSV = RESULTS_DIR / "exp3_consolidated.csv"
EXP4_CONTAINERS = [f"exp4_{i:02d}" for i in range(10)]
OUTPUT_CSV = RESULTS_DIR / "exp4_consolidated.csv"

# exp4 summary.csv columns -> unified schema
COLUMN_MAP = {
    "cov_act": "activity_coverage",
    "cov_method": "method_coverage",
    "cov_rv_method": "mop_coverage",
    "errors": "total_errors",
}

UNIFIED_COLS = [
    "apk",
    "tool",
    "rep",
    "status",
    "duration_s",
    "method_coverage",
    "activity_coverage",
    "mop_coverage",
    "total_errors",
]


def load_exp4() -> pd.DataFrame:
    """Load exp4 results from 10 containers."""
    frames = []
    for container in EXP4_CONTAINERS:
        base = RESULTS_DIR / container / container
        summary_path = base / "summary.csv"
        tasks_path = base / "tasks.json"

        if not summary_path.exists():
            print(f"  WARN: {summary_path} not found, skipping")
            continue

        df = pd.read_csv(summary_path)

        # Get status and duration from tasks.json
        if tasks_path.exists():
            with open(tasks_path) as f:
                tasks_data = json.load(f)
            status_map = {}
            duration_map = {}
            for task in tasks_data["tasks"]:
                cfg = task["config"]
                tc = cfg["tool_config"]
                tool_name = (
                    f"{tc['name']}:{tc['variant']}" if tc.get("variant") else tc["name"]
                )
                # Also store without ":default" suffix — summary.csv uses bare names
                # (e.g. "ape" not "ape:default", "fastbot" not "fastbot:default")
                bare_name = tc["name"]
                for key_name in (tool_name, bare_name):
                    key = (cfg["apk_name"], key_name, cfg["repetition"])
                    status_map[key] = task["result"]["state"]
                    duration_map[key] = task["result"].get("execution_time_seconds", 0)

            df["status"] = df.apply(
                lambda r: status_map.get((r["apk"], r["tool"], r["rep"]), "UNKNOWN"),
                axis=1,
            )
            df["duration_s"] = df.apply(
                lambda r: duration_map.get((r["apk"], r["tool"], r["rep"]), 0),
                axis=1,
            )

            # Add FAILED/ERROR tasks missing from summary.csv
            # Use bare tool names (without :default) to match summary.csv convention
            completed_keys = set(zip(df["apk"], df["tool"], df["rep"]))
            seen_error_keys = set()
            for task in tasks_data["tasks"]:
                cfg = task["config"]
                state = task["result"]["state"]
                if state == "COMPLETED":
                    continue
                tc = cfg["tool_config"]
                bare_name = tc["name"]
                apk = cfg["apk_name"]
                rep = cfg["repetition"]
                error_key = (apk, bare_name, rep)
                if error_key not in completed_keys and error_key not in seen_error_keys:
                    seen_error_keys.add(error_key)
                    frames.append(
                        pd.DataFrame(
                            [
                                {
                                    "apk": apk,
                                    "rep": rep,
                                    "timeout": 600,
                                    "tool": bare_name,
                                    "cov_act": 0.0,
                                    "cov_method": 0.0,
                                    "cov_rv_method": 0.0,
                                    "errors": 0,
                                    "status": state,
                                    "duration_s": task["result"].get(
                                        "execution_time_seconds", 0
                                    ),
                                }
                            ]
                        )
                    )
        else:
            df["status"] = "COMPLETED"
            df["duration_s"] = 600

        frames.append(df)

    exp4 = pd.concat(frames, ignore_index=True)
    exp4 = exp4.rename(columns=COLUMN_MAP)

    # Rename the calibrated aperv:sata_mop to distinguish from v1/v2
    exp4.loc[exp4["tool"] == "aperv:sata_mop", "tool"] = "aperv:sata_mop_cal"

    return exp4[UNIFIED_COLS]


def load_previous() -> pd.DataFrame:
    """Load previous consolidated results (exp1+exp2+exp3)."""
    if not PREV_CSV.exists():
        print(f"  WARN: {PREV_CSV} not found, loading only exp4")
        return pd.DataFrame(columns=UNIFIED_COLS)
    df = pd.read_csv(PREV_CSV)
    return df


def print_summary(df: pd.DataFrame) -> None:
    """Print per-tool summary statistics."""
    completed = df[df["status"] == "COMPLETED"]

    print("=" * 90)
    print("EXPERIMENT 4 + PREVIOUS — CONSOLIDATED SUMMARY")
    print("=" * 90)

    # Task counts
    print("\n--- Task Counts ---")
    for tool in sorted(df["tool"].unique()):
        g = df[df["tool"] == tool]
        total = len(g)
        ok = (g["status"] == "COMPLETED").sum()
        err = total - ok
        apks = g["apk"].nunique()
        reps = g["rep"].max()
        print(
            f"  {tool:25s}: {total:4d} tasks ({ok} ok, {err} fail) | {apks} APKs × {reps} reps"
        )

    # Per-APK means (average reps first, then APKs)
    metrics = ["method_coverage", "activity_coverage", "mop_coverage", "total_errors"]
    print("\n--- Per-APK Mean Coverage (averaged across reps, then APKs) ---")
    print(
        f"  {'tool':25s} {'method':>10s} {'activity':>10s} {'mop':>10s} {'violations':>12s}"
    )
    print("  " + "-" * 70)
    apk_means = (
        completed.groupby(["tool", "apk"])[metrics].mean().groupby("tool").mean()
    )
    for tool in sorted(apk_means.index):
        row = apk_means.loc[tool]
        viol = (
            completed.groupby(["tool", "apk"])["total_errors"]
            .sum()
            .groupby("tool")
            .mean()
        )
        print(
            f"  {tool:25s}  {row['method_coverage']:>8.2f}%  {row['activity_coverage']:>8.2f}%  "
            f"{row['mop_coverage']:>8.2f}%  {viol.get(tool, 0):>10.1f}"
        )

    # Violation summary
    print("\n--- Violations ---")
    for tool in sorted(completed["tool"].unique()):
        g = completed[completed["tool"] == tool]
        total_viol = g["total_errors"].sum()
        apks_with = (g.groupby("apk")["total_errors"].sum() > 0).sum()
        n_reps = g["rep"].max()
        per_rep = total_viol / n_reps if n_reps > 0 else 0
        print(
            f"  {tool:25s}: {total_viol:>5.0f} total / {n_reps} reps = {per_rep:.1f}/rep "
            f"| {apks_with} APKs with violations"
        )

    # Statistical tests: pairwise Wilcoxon for method_coverage
    print("\n--- Wilcoxon Signed-Rank Tests (method_coverage, paired by APK) ---")
    apk_tool = (
        completed.groupby(["tool", "apk"])["method_coverage"].mean().reset_index()
    )

    # Compare calibrated vs all others
    cal_tool = "aperv:sata_mop_cal"
    others = sorted([t for t in completed["tool"].unique() if t != cal_tool])

    for t2 in others:
        d1 = apk_tool[apk_tool["tool"] == cal_tool].set_index("apk")["method_coverage"]
        d2 = apk_tool[apk_tool["tool"] == t2].set_index("apk")["method_coverage"]
        common = d1.index.intersection(d2.index)
        if len(common) < 10:
            print(f"  {cal_tool:25s} vs {t2:25s}: too few pairs ({len(common)})")
            continue
        v1, v2 = d1.loc[common], d2.loc[common]
        delta = v1 - v2
        try:
            stat, pval = stats.wilcoxon(v1, v2, alternative="two-sided")
            direction = ">" if delta.mean() > 0 else "<" if delta.mean() < 0 else "="
            sig = (
                "***"
                if pval < 0.001
                else "**" if pval < 0.01 else "*" if pval < 0.05 else "ns"
            )
            print(
                f"  {cal_tool:25s} vs {t2:25s}: p={pval:.4f} {sig:3s}  "
                f"delta={delta.mean():+.2f}pp  cal{direction}{t2}  (N={len(common)})"
            )
        except ValueError as e:
            print(f"  {cal_tool:25s} vs {t2:25s}: {e}")

    # Also test MOP coverage
    print("\n--- Wilcoxon Signed-Rank Tests (mop_coverage, paired by APK) ---")
    apk_tool_mop = (
        completed.groupby(["tool", "apk"])["mop_coverage"].mean().reset_index()
    )

    for t2 in others:
        d1 = apk_tool_mop[apk_tool_mop["tool"] == cal_tool].set_index("apk")[
            "mop_coverage"
        ]
        d2 = apk_tool_mop[apk_tool_mop["tool"] == t2].set_index("apk")["mop_coverage"]
        common = d1.index.intersection(d2.index)
        if len(common) < 10:
            continue
        v1, v2 = d1.loc[common], d2.loc[common]
        delta = v1 - v2
        try:
            stat, pval = stats.wilcoxon(v1, v2, alternative="two-sided")
            direction = ">" if delta.mean() > 0 else "<" if delta.mean() < 0 else "="
            sig = (
                "***"
                if pval < 0.001
                else "**" if pval < 0.01 else "*" if pval < 0.05 else "ns"
            )
            print(
                f"  {cal_tool:25s} vs {t2:25s}: p={pval:.4f} {sig:3s}  "
                f"delta={delta.mean():+.2f}pp  cal{direction}{t2}  (N={len(common)})"
            )
        except ValueError as e:
            print(f"  {cal_tool:25s} vs {t2:25s}: {e}")


def main():
    print("Loading previous experiments (exp1+exp2+exp3)...")
    prev = load_previous()
    print(
        f"  {len(prev)} rows ({prev['tool'].nunique()} tools: {', '.join(sorted(prev['tool'].unique()))})"
    )

    print("Loading experiment 4...")
    exp4 = load_exp4()
    print(
        f"  {len(exp4)} rows ({exp4['tool'].nunique()} tools: {', '.join(sorted(exp4['tool'].unique()))})"
    )

    all_df = pd.concat([prev, exp4], ignore_index=True)
    print(f"\nTotal: {len(all_df)} rows, {all_df['tool'].nunique()} tools")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved to {OUTPUT_CSV}\n")

    print_summary(all_df)


if __name__ == "__main__":
    main()
