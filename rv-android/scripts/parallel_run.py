#!/usr/bin/env python3
"""
Parallel experiment runner for baseline and validation phases.

Splits APKs across N workers, each running rv-experiment on a separate
emulator port with isolated output directories.

Usage:
    python scripts/parallel_run.py \
        --tools ape,fastbot,rvagent:pure_algorithm \
        --apks-dir ./data/calibration_dataset_v2 \
        --n-emulators 6 \
        --timeout 300 \
        --output-base ./results/baseline_v2 \
        --skip-preprocessing

Resume interrupted run:
    python scripts/parallel_run.py \
        --tools ape,fastbot,rvagent:pure_algorithm \
        --apks-dir ./data/calibration_dataset_v2 \
        --n-emulators 6 \
        --timeout 300 \
        --output-base ./results/baseline_v2 \
        --skip-preprocessing \
        --resume --dry-run
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed


def split_apks(apks_dir: str, n_groups: int) -> list[list[str]]:
    """Split APK filenames into N groups via round-robin."""
    apk_files = sorted(Path(apks_dir).glob("*.apk"))
    groups: list[list[str]] = [[] for _ in range(n_groups)]
    for i, apk in enumerate(apk_files):
        groups[i % n_groups].append(apk.name)
    return groups


def count_tools(tools_spec: str) -> int:
    """Count number of tools from a tool specification string.

    E.g. "ape,fastbot,rvagent:pure_algorithm" -> 3
    """
    return len(tools_spec.split(","))


def find_completed_apks(output_base: str, worker_id: int,
                        experiment_name: str,
                        expected_tasks_per_apk: int) -> set[str]:
    """Read tasks.json and return set of fully-completed APK names.

    An APK is considered complete only when it has exactly
    ``expected_tasks_per_apk`` tasks with state COMPLETED.  This avoids
    falsely marking partial APKs as done (tasks.json only records tasks
    that actually ran, so a partially-completed APK may have all recorded
    tasks as COMPLETED while still missing unstarted ones).
    """
    tasks_file = (Path(output_base) / f"worker_{worker_id}"
                  / experiment_name / "tasks.json")
    if not tasks_file.exists():
        return set()

    data = json.loads(tasks_file.read_text())

    # Count COMPLETED tasks per APK
    apk_completed: dict[str, int] = {}
    for task in data.get("tasks", []):
        apk = task.get("config", {}).get("apk_name", "")
        state = task.get("result", {}).get("state", "")
        if state == "COMPLETED":
            apk_completed[apk] = apk_completed.get(apk, 0) + 1

    return {
        apk for apk, count in apk_completed.items()
        if count >= expected_tasks_per_apk
    }


def run_worker(worker_id: int, args: argparse.Namespace,
               filter_file: str) -> int:
    """Run a single rv-experiment worker."""
    port = 5554 + 2 * worker_id
    output_dir = str(Path(args.output_base) / f"worker_{worker_id}")

    cmd = [
        "uv", "run", "rv-experiment", "run",
        "--tools", args.tools,
        "--apks-dir", args.apks_dir,
        "--apks-filter", filter_file,
        "--device-port", str(port),
        "--name", f"{Path(args.output_base).name}_worker_{worker_id}",
        "--timeout", str(args.timeout),
        "--output-dir", output_dir,
        "--no-window",
        "--repetitions", str(args.repetitions),
    ]

    if args.skip_preprocessing:
        cmd.extend(["--skip-monitors", "--skip-instrument", "--skip-static"])

    print(f"[Worker {worker_id}] Starting on port {port}")
    print(f"[Worker {worker_id}] Command: {' '.join(cmd)}")

    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Run rv-experiment in parallel across multiple emulators"
    )
    parser.add_argument("--tools", required=True,
                        help="Tool specification (same as rv-experiment --tools)")
    parser.add_argument("--apks-dir", required=True,
                        help="Directory containing APK files")
    parser.add_argument("--n-emulators", type=int, default=6,
                        help="Number of parallel emulators (default: 6)")
    parser.add_argument("--timeout", type=int, default=300,
                        help="Timeout per APK in seconds (default: 300)")
    parser.add_argument("--output-base", required=True,
                        help="Base output directory (workers create subdirs)")
    parser.add_argument("--repetitions", type=int, default=1,
                        help="Number of repetitions (default: 1)")
    parser.add_argument("--skip-preprocessing", action="store_true",
                        help="Skip monitors, instrumentation, static analysis")
    parser.add_argument("--resume", action="store_true",
                        help="Resume interrupted run, skipping completed APKs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be resumed without executing")

    args = parser.parse_args()

    # Split APKs into groups (same deterministic split as original run)
    groups = split_apks(args.apks_dir, args.n_emulators)

    # Remove empty groups
    groups = [g for g in groups if g]
    n_workers = len(groups)

    if n_workers == 0:
        print("No APKs found in directory")
        sys.exit(1)

    # Resume: filter out completed APKs per worker
    if args.resume:
        experiment_base = Path(args.output_base).name
        n_tools = count_tools(args.tools)
        expected_tasks_per_apk = n_tools * args.repetitions
        total_completed = 0
        total_remaining = 0
        skipped_workers = []

        print(f"\n{'='*60}")
        print(f"RESUME MODE - Scanning previous results")
        print(f"Expected {expected_tasks_per_apk} tasks/APK "
              f"({n_tools} tools x {args.repetitions} repetitions)")
        print(f"{'='*60}")

        for i in range(n_workers):
            experiment_name = f"{experiment_base}_worker_{i}"
            completed = find_completed_apks(
                args.output_base, i, experiment_name,
                expected_tasks_per_apk
            )

            original_count = len(groups[i])
            groups[i] = [apk for apk in groups[i] if apk not in completed]
            remaining = len(groups[i])

            total_completed += original_count - remaining
            total_remaining += remaining

            status = "SKIP (all done)" if remaining == 0 else f"{remaining} remaining"
            print(
                f"  Worker {i}: {original_count - remaining}/{original_count} "
                f"APKs completed -> {status}"
            )

            if remaining == 0:
                skipped_workers.append(i)

        print(f"\nSummary: {total_completed} APKs completed, "
              f"{total_remaining} remaining across "
              f"{n_workers - len(skipped_workers)} active workers")
        print(f"{'='*60}\n")

        if total_remaining == 0:
            print("All APKs already completed. Nothing to resume.")
            sys.exit(0)

        if args.dry_run:
            print("DRY RUN - would launch the following workers:")
            for i in range(n_workers):
                if i in skipped_workers:
                    continue
                print(f"  Worker {i}: {len(groups[i])} APKs -> "
                      f"{', '.join(groups[i])}")
            sys.exit(0)
    else:
        print(f"Splitting {sum(len(g) for g in groups)} APKs "
              f"across {n_workers} workers")
        for i, group in enumerate(groups):
            print(f"  Worker {i}: {len(group)} APKs")

    # Create filter files (overwrite with potentially reduced APK lists)
    Path(args.output_base).mkdir(parents=True, exist_ok=True)
    filter_files = {}
    for i, group in enumerate(groups):
        if not group:
            continue
        filter_path = Path(args.output_base) / f"worker_{i}_apks.txt"
        filter_path.write_text("\n".join(group))
        filter_files[i] = str(filter_path)

    # Run workers in parallel (skip workers with no remaining APKs)
    futures = {}
    with ProcessPoolExecutor(max_workers=len(filter_files)) as executor:
        for i, filter_file in filter_files.items():
            future = executor.submit(run_worker, i, args, filter_file)
            futures[future] = i

        # Wait for completion
        for future in as_completed(futures):
            worker_id = futures[future]
            try:
                returncode = future.result()
                status = "OK" if returncode == 0 else f"FAILED (exit {returncode})"
                print(f"[Worker {worker_id}] {status}")
            except Exception as e:
                print(f"[Worker {worker_id}] Exception: {e}")

    print(f"\nAll workers completed. Results in: {args.output_base}")


if __name__ == "__main__":
    main()
