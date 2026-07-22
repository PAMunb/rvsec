"""Consolidate APE-RV comparison experiment results from 10 Docker containers.

Reads results from aperv_00..aperv_09 containers. All 3 tools (ape, aperv:sata,
aperv:sata_mop) run in the same experiment — no baseline merge needed.

Uses tasks.json for status/duration and summary.csv for coverage metrics.
Key includes (apk, tool, rep) since each container runs 3 tools.

Usage:
    cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
    uv run python scripts/consolidate_aperv_comparacao.py

Output:
    data/results/aperv_comparacao_consolidated.csv

See: docs/20260313_aperv_comparacao.md
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "data" / "results"
OUTPUT_CSV = RESULTS_DIR / "aperv_comparacao_consolidated.csv"
CONTAINERS = [f"aperv_{i:02d}" for i in range(10)]

# summary.csv columns → unified output columns
COLUMN_MAP = {
    "cov_act": "activity_coverage",
    "cov_method": "method_coverage",
    "cov_rv_method": "mop_coverage",
    "errors": "total_errors",
}

OUTPUT_COLUMNS = [
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


def load_container_data(container: str) -> pd.DataFrame:
    """Load results from a single container.

    Merges tasks.json (status, duration) with summary.csv (coverage metrics).
    Handles tasks that completed but are missing from summary.csv (edge case)
    and tasks that failed (never appear in summary.csv).
    """
    base = RESULTS_DIR / container / container
    tasks_path = base / "tasks.json"
    summary_path = base / "summary.csv"

    if not tasks_path.exists():
        print(f"  WARNING: {tasks_path} not found, skipping {container}")
        return pd.DataFrame()

    # Build maps from tasks.json — key is (apk, tool, rep) since 3 tools per container
    try:
        with open(tasks_path) as f:
            tasks_data = json.load(f)
    except json.JSONDecodeError:
        print(f"  WARNING: corrupted tasks.json in {container}, skipping")
        return pd.DataFrame()

    status_map = {}
    duration_map = {}
    for task in tasks_data["tasks"]:
        cfg = task["config"]
        tc = cfg["tool_config"]
        # Reconstruct tool name: "ape" for default variant, "aperv:sata" etc. otherwise
        tool_name = tc["name"]
        if tc.get("variant") and tc["variant"] != "default":
            tool_name = f"{tool_name}:{tc['variant']}"
        key = (cfg["apk_name"], tool_name, cfg["repetition"])
        status_map[key] = task["result"]["state"]
        duration_map[key] = task["result"].get("execution_time_seconds", 0)

    frames = []

    # Load summary.csv — contains only COMPLETED tasks with coverage metrics
    if summary_path.exists():
        df = pd.read_csv(summary_path)
        # Enrich with status and duration from tasks.json
        df["status"] = df.apply(
            lambda r: status_map.get((r["apk"], r["tool"], r["rep"]), "UNKNOWN"),
            axis=1,
        )
        df["duration_s"] = df.apply(
            lambda r: duration_map.get((r["apk"], r["tool"], r["rep"]), 0),
            axis=1,
        )
        frames.append(df)

        # Track which (apk, tool, rep) are already in summary.csv
        completed_keys = set(zip(df["apk"], df["tool"], df["rep"]))
    else:
        print(f"  WARNING: {summary_path} not found (only tasks.json available)")
        completed_keys = set()

    # Add FAILED/ERROR tasks that are missing from summary.csv (zero coverage)
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

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename to unified schema and select output columns."""
    df = df.rename(columns=COLUMN_MAP)
    # Ensure all output columns exist
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = 0
    return df[OUTPUT_COLUMNS]


def print_summary(df: pd.DataFrame) -> None:
    """Print per-tool summary statistics to stdout."""
    completed = df[df["status"] == "COMPLETED"]
    metrics = ["method_coverage", "activity_coverage", "mop_coverage", "total_errors"]

    print("\n" + "=" * 80)
    print("APE-RV COMPARISON EXPERIMENT — CONSOLIDATED SUMMARY")
    print("=" * 80)

    # Task counts
    print("\n--- Task Counts ---")
    for tool in sorted(df["tool"].unique()):
        g = df[df["tool"] == tool]
        total = len(g)
        ok = (g["status"] == "COMPLETED").sum()
        err = total - ok
        apks = g["apk"].nunique()
        print(
            f"  {tool:20s}: {total:4d} tasks "
            f"({ok} completed, {err} failed) | {apks} unique APKs"
        )

    # Coverage stats
    print("\n--- Coverage Statistics (COMPLETED tasks only) ---")
    print(
        f"  {'tool':20s} {'metric':22s} "
        f"{'mean':>8s} {'median':>8s} {'std':>8s} {'min':>8s} {'max':>8s}"
    )
    print("  " + "-" * 78)
    for tool in sorted(completed["tool"].unique()):
        g = completed[completed["tool"] == tool]
        for m in metrics:
            vals = g[m]
            print(
                f"  {tool:20s} {m:22s} "
                f"{vals.mean():8.2f} {vals.median():8.2f} {vals.std():8.2f} "
                f"{vals.min():8.2f} {vals.max():8.2f}"
            )
        print()

    # Per-APK mean coverage comparison (averaged across reps first, then across APKs)
    print("--- Per-APK Mean Coverage (averaged across reps, then across APKs) ---")
    apk_means = (
        completed.groupby(["tool", "apk"])[metrics[:3]].mean().groupby("tool").mean()
    )
    print(apk_means.to_string())
    print()

    # Head-to-head summary
    print("--- Head-to-Head (method_coverage, threshold ±2pp) ---")
    tools = sorted(completed["tool"].unique())
    apk_tool_means = (
        completed.groupby(["apk", "tool"])["method_coverage"].mean().unstack("tool")
    )
    for i, t1 in enumerate(tools):
        for t2 in tools[i + 1 :]:
            if t1 not in apk_tool_means.columns or t2 not in apk_tool_means.columns:
                continue
            valid = apk_tool_means[[t1, t2]].dropna()
            delta = valid[t1] - valid[t2]
            wins_t1 = (delta > 2).sum()
            wins_t2 = (delta < -2).sum()
            ties = len(delta) - wins_t1 - wins_t2
            print(
                f"  {t1} vs {t2}: "
                f"{t1} wins {wins_t1}, {t2} wins {wins_t2}, ties {ties} "
                f"(of {len(delta)} APKs)"
            )
    print()


def main():
    print("Loading container data...")
    frames = []
    for container in CONTAINERS:
        df = load_container_data(container)
        if not df.empty:
            n_tools = df["tool"].nunique() if "tool" in df.columns else 0
            print(f"  {container}: {len(df)} rows, {n_tools} tools")
            frames.append(df)

    if not frames:
        print("ERROR: No data found in any container")
        sys.exit(1)

    all_df = normalize_columns(pd.concat(frames, ignore_index=True))
    print(f"\nTotal consolidated: {len(all_df)} rows")
    print(f"  Tools: {sorted(all_df['tool'].unique())}")
    print(f"  APKs:  {all_df['apk'].nunique()}")

    # Save
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved to {OUTPUT_CSV}")

    print_summary(all_df)


if __name__ == "__main__":
    main()
