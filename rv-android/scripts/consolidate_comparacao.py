"""Consolidate comparison experiment results from 6 Docker containers + baseline.

Reads rvsmart:mvp results from cmp01-cmp06, baseline ape+fastbot results,
filters to the 100-APK calibration set, and produces a unified CSV + summary stats.
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS_DIR = DATA / "results"
BASELINE_CSV = ROOT / "results" / "baseline_v2" / "summary.csv"
APK_LIST = DATA / "selection" / "calibration_set_v2.txt"
OUTPUT_CSV = RESULTS_DIR / "comparacao_consolidated.csv"

# Columns shared by experiment and baseline summary.csv
# apk,rep,timeout,tool,cov_act,cov_method,cov_rv_method,errors
COLUMN_MAP = {
    "apk": "apk",
    "tool": "tool",
    "rep": "rep",
    "cov_act": "activity_coverage",
    "cov_method": "method_coverage",
    "cov_rv_method": "mop_coverage",
    "errors": "total_errors",
}


def load_apk_set() -> set[str]:
    """Load the 100-APK calibration set, appending .apk suffix."""
    names = APK_LIST.read_text().strip().splitlines()
    return {n.strip() + ".apk" for n in names if n.strip()}


def load_experiment_data() -> pd.DataFrame:
    """Load all 6 container results, using tasks.json for status and summary.csv for metrics."""
    frames = []
    for i in range(1, 7):
        container = f"cmp0{i}"
        base = RESULTS_DIR / container / container
        tasks_path = base / "tasks.json"
        summary_path = base / "summary.csv"

        # Build status map from tasks.json
        with open(tasks_path) as f:
            tasks_data = json.load(f)
        status_map = {}
        duration_map = {}
        for task in tasks_data["tasks"]:
            cfg = task["config"]
            key = (cfg["apk_name"], cfg["repetition"])
            status_map[key] = task["result"]["state"]
            duration_map[key] = task["result"].get("execution_time_seconds", 0)

        # Load summary.csv (only COMPLETED tasks appear here)
        df = pd.read_csv(summary_path)
        df["status"] = df.apply(
            lambda r: status_map.get((r["apk"], r["rep"]), "UNKNOWN"), axis=1
        )
        df["duration_s"] = df.apply(
            lambda r: duration_map.get((r["apk"], r["rep"]), 0), axis=1
        )
        frames.append(df)

        # Add ERROR tasks that are missing from summary.csv
        completed_keys = set(zip(df["apk"], df["rep"]))
        for (apk, rep), state in status_map.items():
            if state != "COMPLETED" and (apk, rep) not in completed_keys:
                frames.append(
                    pd.DataFrame(
                        [
                            {
                                "apk": apk,
                                "rep": rep,
                                "timeout": 600,
                                "tool": "rvsmart:mvp",
                                "cov_act": 0.0,
                                "cov_method": 0.0,
                                "cov_rv_method": 0.0,
                                "errors": 0,
                                "status": state,
                                "duration_s": duration_map.get((apk, rep), 0),
                            }
                        ]
                    )
                )

    return pd.concat(frames, ignore_index=True)


def load_baseline(apk_set: set[str]) -> pd.DataFrame:
    """Load baseline results filtered to the 100-APK set."""
    df = pd.read_csv(BASELINE_CSV)
    df = df[df["apk"].isin(apk_set)].copy()
    df["status"] = "COMPLETED"
    df["duration_s"] = 600  # baseline always runs full timeout
    return df


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename to unified schema."""
    df = df.rename(columns=COLUMN_MAP)
    return df[
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


def print_summary(df: pd.DataFrame) -> None:
    """Print per-tool summary statistics."""
    completed = df[df["status"] == "COMPLETED"]

    print("=" * 80)
    print("COMPARISON EXPERIMENT — CONSOLIDATED SUMMARY")
    print("=" * 80)

    # Task counts
    print("\n--- Task Counts ---")
    for tool, g in df.groupby("tool"):
        total = len(g)
        ok = (g["status"] == "COMPLETED").sum()
        err = total - ok
        apks = g["apk"].nunique()
        print(
            f"  {tool:20s}: {total:4d} tasks ({ok} completed, {err} failed) | {apks} unique APKs"
        )

    # Coverage stats
    metrics = ["method_coverage", "activity_coverage", "mop_coverage", "total_errors"]
    print("\n--- Coverage Statistics (COMPLETED tasks only) ---")
    print(
        f"  {'tool':20s} {'metric':22s} {'mean':>8s} {'median':>8s} {'std':>8s} {'min':>8s} {'max':>8s}"
    )
    print("  " + "-" * 78)
    for tool, g in completed.groupby("tool"):
        for m in metrics:
            vals = g[m]
            print(
                f"  {tool:20s} {m:22s} {vals.mean():8.2f} {vals.median():8.2f} {vals.std():8.2f} {vals.min():8.2f} {vals.max():8.2f}"
            )
        print()

    # Per-APK mean coverage comparison (averaged across reps first)
    print("--- Per-APK Mean Coverage (averaged across reps, then across APKs) ---")
    apk_means = (
        completed.groupby(["tool", "apk"])[metrics[:3]].mean().groupby("tool").mean()
    )
    print(apk_means.to_string())
    print()


def main():
    apk_set = load_apk_set()
    print(f"Loaded {len(apk_set)} APKs from calibration set")

    exp_df = load_experiment_data()
    print(f"Loaded {len(exp_df)} experiment rows (rvsmart:mvp)")

    baseline_df = load_baseline(apk_set)
    print(f"Loaded {len(baseline_df)} baseline rows (ape + fastbot)")

    # Normalize and concatenate
    all_df = pd.concat(
        [normalize_columns(exp_df), normalize_columns(baseline_df)], ignore_index=True
    )
    print(f"Total consolidated: {len(all_df)} rows")

    # Save
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved to {OUTPUT_CSV}")

    print_summary(all_df)


if __name__ == "__main__":
    main()
