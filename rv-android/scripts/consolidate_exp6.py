"""Consolidate exp6 (component triggering) results and compare with all 600s experiments.

Usage:
    cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
    uv run python scripts/consolidate_exp6.py
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "data" / "results"
OUTPUT_CSV = RESULTS_DIR / "exp6_consolidated.csv"

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


def load_container(container: str) -> pd.DataFrame:
    base = RESULTS_DIR / container / container
    tasks_path = base / "tasks.json"
    summary_path = base / "summary.csv"

    if not tasks_path.exists():
        return pd.DataFrame()

    with open(tasks_path) as f:
        tasks_data = json.load(f)

    status_map = {}
    duration_map = {}
    for task in tasks_data["tasks"]:
        cfg = task["config"]
        tc = cfg["tool_config"]
        tool_name = tc["name"]
        if tc.get("variant") and tc["variant"] != "default":
            tool_name = f"{tool_name}:{tc['variant']}"
        key = (cfg["apk_name"], tool_name, cfg["repetition"])
        status_map[key] = task["result"]["state"]
        duration_map[key] = task["result"].get("execution_time_seconds", 0)

    frames = []
    if summary_path.exists():
        df = pd.read_csv(summary_path)
        df["status"] = df.apply(
            lambda r: status_map.get((r["apk"], r["tool"], r["rep"]), "UNKNOWN"), axis=1
        )
        df["duration_s"] = df.apply(
            lambda r: duration_map.get((r["apk"], r["tool"], r["rep"]), 0), axis=1
        )
        frames.append(df)
        completed_keys = set(zip(df["apk"], df["tool"], df["rep"]))
    else:
        completed_keys = set()

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

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=COLUMN_MAP)
    for col in OUTPUT_COLUMNS:
        if col not in df.columns:
            df[col] = 0
    return df[OUTPUT_COLUMNS]


def main():
    # 1. Consolidate exp6
    print("Consolidating exp6...")
    exp6_frames = []
    for i in range(10):
        name = f"exp6_{i:02d}"
        df = load_container(name)
        if not df.empty:
            exp6_frames.append(df)
            print(f"  {name}: {len(df)} rows")
    exp6 = normalize(pd.concat(exp6_frames, ignore_index=True))
    exp6["tool"] = "aperv:sata_mop_comp"  # Rename to distinguish from old sata_mop
    exp6.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved: {OUTPUT_CSV} ({len(exp6)} rows)")

    # 2. Load previous 600s results
    prev_csv = RESULTS_DIR / "aperv_comparacao_consolidated.csv"
    if prev_csv.exists():
        prev = pd.read_csv(prev_csv)
        print(f"Loaded previous: {prev_csv} ({len(prev)} rows)")
    else:
        prev = pd.DataFrame(columns=OUTPUT_COLUMNS)
        print("No previous results found")

    # 3. Combine all
    combined = pd.concat([prev, exp6], ignore_index=True)
    completed = combined[combined["status"] == "COMPLETED"]

    # 4. Print comparison
    print("\n" + "=" * 90)
    print("COMPARISON: ALL 600s EXPERIMENTS")
    print("=" * 90)

    print(
        f"\n{'Tool':<25s} {'N':>5s} {'APKs':>5s}  "
        f"{'Method%':>8s} {'MOP%':>8s} {'Errors':>7s}"
    )
    print("-" * 70)

    for tool in sorted(completed["tool"].unique()):
        g = completed[completed["tool"] == tool]
        # Average per APK (across reps), then mean across APKs
        apk_means = g.groupby("apk")[
            ["method_coverage", "mop_coverage", "total_errors"]
        ].mean()
        print(
            f"  {tool:<23s} {len(g):>5d} {g['apk'].nunique():>5d}  "
            f"{apk_means['method_coverage'].mean():>7.2f}% "
            f"{apk_means['mop_coverage'].mean():>7.2f}% "
            f"{apk_means['total_errors'].mean():>7.2f}"
        )

    # 5. Paired comparison: sata_mop_comp vs sata_mop (old)
    print("\n--- Paired Comparison: sata_mop_comp (gh11) vs sata_mop (baseline) ---")
    old = completed[completed["tool"] == "aperv:sata_mop"]
    new = completed[completed["tool"] == "aperv:sata_mop_comp"]
    if not old.empty and not new.empty:
        old_means = old.groupby("apk")["method_coverage"].mean()
        new_means = new.groupby("apk")["method_coverage"].mean()
        common = old_means.index.intersection(new_means.index)
        if len(common) > 0:
            old_v = old_means.loc[common]
            new_v = new_means.loc[common]
            diff = new_v - old_v
            wins = (diff > 0).sum()
            losses = (diff < 0).sum()
            ties = (diff == 0).sum()
            print(f"  Common APKs: {len(common)}")
            print(
                f"  Method coverage: old={old_v.mean():.2f}%, new={new_v.mean():.2f}%, diff={diff.mean():+.2f}pp"
            )
            print(f"  Wins/Losses/Ties: {wins}/{losses}/{ties}")

            # Same for MOP
            old_mop = old.groupby("apk")["mop_coverage"].mean().loc[common]
            new_mop = new.groupby("apk")["mop_coverage"].mean().loc[common]
            mop_diff = new_mop - old_mop
            print(
                f"  MOP coverage:    old={old_mop.mean():.2f}%, new={new_mop.mean():.2f}%, diff={mop_diff.mean():+.2f}pp"
            )
    else:
        print("  Cannot pair — missing one of the tools")


if __name__ == "__main__":
    main()
