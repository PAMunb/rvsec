"""Consolidate experiment 2 results and merge with experiment 1 for comparison.

Exp1 (2026-03-13): ape, aperv:sata, aperv:sata_mop (old weights 500/300/100)
Exp2 (2026-03-15): aperv:sata_mop (new weights 100/60/20), rvsmart:mvp

Output: 5 tools in one CSV for comparative analysis.

Usage:
    cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
    uv run python scripts/consolidate_exp2.py
"""

import json
from pathlib import Path

import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "data" / "results"

EXP1_CSV = RESULTS_DIR / "aperv_comparacao_consolidated.csv"
EXP2_CONTAINERS = [f"exp2_{i:02d}" for i in range(10)]
OUTPUT_CSV = RESULTS_DIR / "exp2_consolidated.csv"

# exp2 summary.csv columns -> unified schema
COLUMN_MAP = {
    "cov_act": "activity_coverage",
    "cov_method": "method_coverage",
    "cov_rv_method": "mop_coverage",
    "errors": "total_errors",
}


def load_exp2() -> pd.DataFrame:
    """Load exp2 results from 10 containers."""
    frames = []
    for container in EXP2_CONTAINERS:
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
                key = (cfg["apk_name"], tool_name, cfg["repetition"])
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

            # Add FAILED tasks missing from summary.csv
            completed_keys = set(zip(df["apk"], df["tool"], df["rep"]))
            for (apk, tool, rep), state in status_map.items():
                if state != "COMPLETED" and (apk, tool, rep) not in completed_keys:
                    frames.append(
                        pd.DataFrame(
                            [
                                {
                                    "apk": apk,
                                    "rep": rep,
                                    "timeout": 600,
                                    "tool": tool,
                                    "cov_act": 0.0,
                                    "cov_method": 0.0,
                                    "cov_rv_method": 0.0,
                                    "errors": 0,
                                    "status": state,
                                    "duration_s": duration_map.get((apk, tool, rep), 0),
                                }
                            ]
                        )
                    )
        else:
            df["status"] = "COMPLETED"
            df["duration_s"] = 600

        frames.append(df)

    exp2 = pd.concat(frames, ignore_index=True)
    exp2 = exp2.rename(columns=COLUMN_MAP)

    # Rename aperv:sata_mop to distinguish from exp1 version
    exp2.loc[exp2["tool"] == "aperv:sata_mop", "tool"] = "aperv:sata_mop_v2"

    return exp2[
        [
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
    ]


def load_exp1() -> pd.DataFrame:
    """Load exp1 consolidated results, renaming old sata_mop."""
    df = pd.read_csv(EXP1_CSV)
    # Rename old sata_mop to v1
    df.loc[df["tool"] == "aperv:sata_mop", "tool"] = "aperv:sata_mop_v1"
    return df


def print_summary(df: pd.DataFrame) -> None:
    """Print per-tool summary statistics."""
    completed = df[df["status"] == "COMPLETED"]

    print("=" * 90)
    print("EXPERIMENT 2 + EXP1 — CONSOLIDATED SUMMARY (5 tools)")
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

    # Coverage stats
    metrics = ["method_coverage", "activity_coverage", "mop_coverage"]
    print("\n--- Coverage (COMPLETED tasks, mean ± std) ---")
    print(f"  {'tool':25s} {'method':>14s} {'activity':>14s} {'mop':>14s}")
    print("  " + "-" * 70)
    for tool in sorted(completed["tool"].unique()):
        g = completed[completed["tool"] == tool]
        parts = []
        for m in metrics:
            parts.append(f"{g[m].mean():5.2f} ± {g[m].std():5.2f}")
        print(f"  {tool:25s} {parts[0]:>14s} {parts[1]:>14s} {parts[2]:>14s}")

    # Per-APK means (average reps first, then APKs)
    print("\n--- Per-APK Mean Coverage (averaged across reps, then APKs) ---")
    apk_means = (
        completed.groupby(["tool", "apk"])[metrics].mean().groupby("tool").mean()
    )
    for tool in sorted(apk_means.index):
        row = apk_means.loc[tool]
        print(
            f"  {tool:25s}  method={row['method_coverage']:.2f}%  activity={row['activity_coverage']:.2f}%  mop={row['mop_coverage']:.2f}%"
        )

    # Statistical tests: pairwise Wilcoxon for method_coverage
    print("\n--- Wilcoxon Signed-Rank Tests (method_coverage, paired by APK) ---")
    apk_tool = (
        completed.groupby(["tool", "apk"])["method_coverage"].mean().reset_index()
    )

    pairs = [
        ("aperv:sata_mop_v1", "aperv:sata_mop_v2"),
        ("ape", "aperv:sata_mop_v2"),
        ("ape", "rvsmart:mvp"),
        ("aperv:sata_mop_v2", "rvsmart:mvp"),
        ("aperv:sata", "aperv:sata_mop_v2"),
    ]

    for t1, t2 in pairs:
        d1 = apk_tool[apk_tool["tool"] == t1].set_index("apk")["method_coverage"]
        d2 = apk_tool[apk_tool["tool"] == t2].set_index("apk")["method_coverage"]
        common = d1.index.intersection(d2.index)
        if len(common) < 10:
            print(f"  {t1:25s} vs {t2:25s}: too few pairs ({len(common)})")
            continue
        v1, v2 = d1.loc[common], d2.loc[common]
        delta = v2 - v1
        try:
            stat, pval = stats.wilcoxon(v1, v2, alternative="two-sided")
            direction = ">" if delta.mean() > 0 else "<" if delta.mean() < 0 else "="
            sig = (
                "***"
                if pval < 0.001
                else "**" if pval < 0.01 else "*" if pval < 0.05 else "ns"
            )
            print(
                f"  {t1:25s} vs {t2:25s}: p={pval:.4f} {sig:3s}  delta={delta.mean():+.2f}pp  {t2}{direction}{t1}  (N={len(common)})"
            )
        except ValueError as e:
            print(f"  {t1:25s} vs {t2:25s}: {e}")


def main():
    print("Loading experiment 1...")
    exp1 = load_exp1()
    print(
        f"  {len(exp1)} rows ({exp1['tool'].nunique()} tools: {', '.join(sorted(exp1['tool'].unique()))})"
    )

    print("Loading experiment 2...")
    exp2 = load_exp2()
    print(
        f"  {len(exp2)} rows ({exp2['tool'].nunique()} tools: {', '.join(sorted(exp2['tool'].unique()))})"
    )

    all_df = pd.concat([exp1, exp2], ignore_index=True)
    print(f"\nTotal: {len(all_df)} rows, {all_df['tool'].nunique()} tools")

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved to {OUTPUT_CSV}\n")

    print_summary(all_df)


if __name__ == "__main__":
    main()
