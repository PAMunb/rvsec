#!/usr/bin/env python3
"""
Monitor Docker batch experiment progress.

Reads tasks.json and filter files from a results directory to compute
progress, ETA, and per-batch breakdown. Works for any Docker-based phase
(baseline, calibration, validation) — just point to the results dir.

Usage:
    python scripts/monitor_docker.py results/baseline_v2
    python scripts/monitor_docker.py results/baseline_v2 --watch 300
    python scripts/monitor_docker.py results/calibration_macro_v2
    python scripts/monitor_docker.py results/baseline_v2 --tools 3 --reps 3
"""

import argparse
import glob
import json
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


def load_batch_info(
    results_dir: Path, forced_tools: int = 0, forced_reps: int = 0
) -> list[dict]:
    """Load batch information from filter files and tasks.json.

    Args:
        results_dir: Path to the results directory.
        forced_tools: Override tool count (0 = infer from tasks).
        forced_reps: Override repetition count (0 = infer from tasks).
    """
    batches = []

    # Find all tasks.json files (pattern: batch_N/batch_N/tasks.json)
    task_files = sorted(glob.glob(str(results_dir / "batch_*/batch_*/tasks.json")))

    if not task_files:
        # Try single-level: batch_N/tasks.json
        task_files = sorted(glob.glob(str(results_dir / "batch_*/tasks.json")))

    for tf in task_files:
        tf_path = Path(tf)
        batch_name = tf_path.parent.name

        # Determine batch index from name
        try:
            batch_idx = int(batch_name.split("_")[1])
        except (IndexError, ValueError):
            batch_idx = -1

        # Load tasks.json
        with open(tf) as f:
            data = json.load(f)

        tasks = data.get("tasks", [])

        # Count completed and failed tasks
        completed = 0
        failed = 0
        for t in tasks:
            result = t.get("result", {})
            state = result.get("state", "")
            if state == "COMPLETED":
                completed += 1
            elif state == "ERROR":
                failed += 1

        # Count tasks per APK to determine fully completed APKs
        apk_task_counts = Counter()
        for t in tasks:
            cfg = t.get("config", {})
            apk_name = cfg.get("apk_name", "")
            if apk_name:
                result = t.get("result", {})
                if result.get("state") == "COMPLETED":
                    apk_task_counts[apk_name] += 1

        # Infer tools and reps from ALL tasks in the file
        tools = set()
        reps = set()
        for t in tasks:
            cfg = t.get("config", {})
            tc = cfg.get("tool_config", {})
            tool_name = tc.get("name", "")
            variant = tc.get("variant", "default")
            if variant and variant != "default":
                tools.add(f"{tool_name}:{variant}")
            else:
                tools.add(tool_name)
            reps.add(cfg.get("repetition", 1))

        n_tools = forced_tools if forced_tools > 0 else max(len(tools), 1)
        n_reps = forced_reps if forced_reps > 0 else max(len(reps), 1)
        tasks_per_apk = n_tools * n_reps

        # APKs fully done = all tasks_per_apk completed for that APK
        apks_fully_done = sum(
            1 for count in apk_task_counts.values() if count >= tasks_per_apk
        )
        apks_partial = sum(
            1 for count in apk_task_counts.values() if 0 < count < tasks_per_apk
        )

        # Load filter file for total APK count
        filter_file = results_dir / f"batch_{batch_idx}_apks.txt"
        if filter_file.exists():
            with open(filter_file) as f:
                total_apks = sum(1 for line in f if line.strip())
        else:
            total_apks = len(apk_task_counts)

        total_planned = total_apks * tasks_per_apk

        # Extract timing info from tasks
        durations = []
        latest_end = None
        for t in tasks:
            result = t.get("result", {})
            dur = result.get("execution_time_seconds")
            if dur is not None:
                durations.append(dur)
            et = result.get("end_time")
            if et:
                try:
                    parsed_et = datetime.fromisoformat(et)
                    if latest_end is None or parsed_et > latest_end:
                        latest_end = parsed_et
                except (ValueError, TypeError):
                    pass

        avg_duration = sum(durations) / len(durations) if durations else 0

        batches.append(
            {
                "name": batch_name,
                "index": batch_idx,
                "total_apks": total_apks,
                "apks_done": apks_fully_done,
                "apks_partial": apks_partial,
                "total_planned": total_planned,
                "completed": completed,
                "failed": failed,
                "tasks_per_apk": tasks_per_apk,
                "n_tools": n_tools,
                "n_reps": n_reps,
                "tools": sorted(tools),
                "avg_duration": avg_duration,
                "latest_end": latest_end,
            }
        )

    return batches


def print_report(
    results_dir: Path, forced_tools: int = 0, forced_reps: int = 0
) -> None:
    """Print progress report."""
    batches = load_batch_info(results_dir, forced_tools, forced_reps)

    if not batches:
        print(f"No tasks.json found in {results_dir}")
        return

    now = datetime.now()
    print(f"\n{'=' * 70}")
    print(f"  Docker Batch Monitor — {results_dir.name}")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 70}")

    # Per-batch table header
    print(
        f"\n  {'Batch':<10} {'Tasks':<16} {'APKs':<14} {'Avg(s)':<8} {'Left':<8} {'ETA(h)':<8}"
    )
    print(f"  {'-' * 64}")

    total_completed = 0
    total_planned = 0
    total_failed = 0
    total_apks_done = 0
    total_apks = 0
    all_durations = []
    max_remaining_time = 0

    for b in batches:
        remaining = b["total_planned"] - b["completed"]
        eta_h = (remaining * b["avg_duration"]) / 3600 if b["avg_duration"] > 0 else 0
        pct = (
            (b["completed"] / b["total_planned"] * 100) if b["total_planned"] > 0 else 0
        )

        # APK display: "2+1/30" means 2 fully done, 1 in progress
        if b["apks_partial"] > 0:
            apk_str = f"{b['apks_done']}+{b['apks_partial']}/{b['total_apks']}"
        else:
            apk_str = f"{b['apks_done']}/{b['total_apks']}"

        print(
            f"  {b['name']:<10} "
            f"{b['completed']:>4}/{b['total_planned']:<4} ({pct:>5.1f}%) "
            f"{apk_str:<12}  "
            f"{b['avg_duration']:>6.0f}  "
            f"{remaining:>6}  "
            f"{eta_h:>6.1f}"
        )

        total_completed += b["completed"]
        total_planned += b["total_planned"]
        total_failed += b["failed"]
        total_apks_done += b["apks_done"]
        total_apks += b["total_apks"]
        if b["avg_duration"] > 0:
            all_durations.extend([b["avg_duration"]] * b["completed"])

        remaining_time = remaining * b["avg_duration"] if b["avg_duration"] > 0 else 0
        if remaining_time > max_remaining_time:
            max_remaining_time = remaining_time

    # Totals
    total_remaining = total_planned - total_completed
    overall_pct = (total_completed / total_planned * 100) if total_planned > 0 else 0
    avg_all = sum(all_durations) / len(all_durations) if all_durations else 0

    print(f"  {'-' * 64}")
    print(
        f"  {'TOTAL':<10} "
        f"{total_completed:>4}/{total_planned:<4} ({overall_pct:>5.1f}%) "
        f"{total_apks_done}/{total_apks:<12}  "
        f"{avg_all:>6.0f}  "
        f"{total_remaining:>6}  "
        f"{max_remaining_time / 3600:>6.1f}"
    )

    if total_failed > 0:
        print(f"\n  FAILED tasks: {total_failed}")

    # ETA
    print("\n--- ETA ---")
    if max_remaining_time > 0:
        eta_finish = now + timedelta(seconds=max_remaining_time)
        print(f"  Remaining: {max_remaining_time / 3600:.1f}h")
        print(f"  Finish:    {eta_finish.strftime('%Y-%m-%d %H:%M:%S')}")

    # Config (from first batch with tools)
    if batches and batches[0]["tools"]:
        print("\n--- Config ---")
        print(f"  Tools:     {', '.join(batches[0]['tools'])}")
        print(f"  Reps:      {batches[0]['n_reps']}")
        print(f"  Tasks/APK: {batches[0]['tasks_per_apk']}")
        print(f"  Batches:   {len(batches)}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Monitor Docker batch experiment progress from tasks.json files."
    )
    parser.add_argument(
        "results_dir",
        help="Path to the results directory (e.g., results/baseline_v2)",
    )
    parser.add_argument(
        "--watch",
        "-w",
        type=int,
        default=0,
        metavar="SECONDS",
        help="Refresh interval in seconds (0 = single run, default: 0)",
    )
    parser.add_argument(
        "--tools",
        type=int,
        default=0,
        help="Override tool count (avoids inference errors early in execution)",
    )
    parser.add_argument(
        "--reps",
        type=int,
        default=0,
        help="Override repetition count (avoids inference errors early in execution)",
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    if not results_dir.exists():
        print(f"Error: directory not found: {results_dir}", file=sys.stderr)
        sys.exit(1)

    if args.watch > 0:
        try:
            while True:
                print("\033[2J\033[H", end="")
                print_report(results_dir, args.tools, args.reps)
                print(f"  [Refreshing every {args.watch}s — Ctrl+C to stop]")
                time.sleep(args.watch)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        print_report(results_dir, args.tools, args.reps)


if __name__ == "__main__":
    main()
