#!/usr/bin/env python3
"""
Baseline and validation runner for Docker-based parallel experiments.

Splits APKs across N Docker containers using round-robin distribution.
Each container runs all specified tools on its batch of APKs. Results
are auto-aggregated into a single summary.csv after all containers complete.

Usage:
    uv run python scripts/baseline_docker.py \
        --tools ape,fastbot,rvagent:pure_algorithm \
        --data-dir /path/to/calibration_dataset_v2 \
        --filter-file /path/to/all_valid_apks.txt \
        --output-dir ./results/baseline_v2 \
        --n-containers 6 --timeout 300 --repetitions 3
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure functions — all testable without Docker
# ---------------------------------------------------------------------------


def split_apks_round_robin(apk_names: list[str], n_batches: int) -> list[list[str]]:
    """Distribute APK names across N batches using round-robin assignment.

    This ensures an even distribution: if the number of APKs is not evenly
    divisible by n_batches, some batches get one extra APK.

    Example: 105 APKs / 6 containers = 4 batches of 18, 2 batches of 17.
    """
    batches: list[list[str]] = [[] for _ in range(n_batches)]
    for i, apk in enumerate(apk_names):
        batches[i % n_batches].append(apk)
    return batches


def generate_baseline_compose(
    n_batches: int,
    tools: str,
    data_dir: str,
    output_dir: str,
    image: str,
    cpus: int,
    memory: str,
    timeout: int,
    repetitions: int,
    extra_hosts: Optional[list[str]] = None,
) -> dict:
    """Generate a docker-compose dict for baseline/validation experiments.

    All containers receive the same RV_TOOLS specification. Each container
    processes a different batch of APKs, identified by its own filter file.

    The generated structure follows the pattern established in
    docker/docker-compose.parallel.yml. Notable differences from the
    calibration orchestrator: no Optuna parameters, no per-trial tool specs,
    and each container uses a batch-specific filter file instead of a shared one.
    """
    data_dir = str(Path(data_dir).resolve())
    output_dir = str(Path(output_dir).resolve())

    services = {}
    for i in range(n_batches):
        service: dict = {
            "image": image,
            "container_name": f"batch_{i}",
            "environment": {
                "RV_TOOLS": tools,
                "RV_EXPERIMENT_NAME": f"batch_{i}",
                "RV_REPETITIONS": str(repetitions),
                "RV_TIMEOUTS": str(timeout),
                "RV_APKS_FILTER": f"/opt/rvsec/rv-android/filters/batch_{i}_apks.txt",
                "RV_NO_WINDOW": "true",
                "RV_SKIP_MONITORS": "true",
                "RV_SKIP_INSTRUMENT": "true",
                "RV_SKIP_STATIC_ANALYSIS": "true",
                "RV_DELAY": str(i * 10),
            },
            "volumes": [
                f"{data_dir}:/opt/rvsec/rv-android/apks:ro",
                f"{output_dir}/batch_{i}_apks.txt:/opt/rvsec/rv-android/filters/batch_{i}_apks.txt:ro",
                f"{output_dir}/batch_{i}:/opt/rvsec/rv-android/results",
            ],
            "devices": ["/dev/kvm:/dev/kvm"],
            "deploy": {
                "resources": {
                    "limits": {
                        "cpus": str(cpus),
                        "memory": memory,
                    }
                }
            },
        }
        if extra_hosts:
            service["extra_hosts"] = list(extra_hosts)
        services[f"batch_{i}"] = service

    return {"services": services}


def aggregate_summaries(output_dir: Path, n_batches: int) -> Optional[Path]:
    """Concatenate per-batch summary.csv files into a single aggregated file.

    Each container writes results to {output_dir}/batch_{i}/batch_{i}/summary.csv.
    The double nesting happens because the host mounts {output_dir}/batch_{i}/ as
    the container's /opt/rvsec/rv-android/results, and rv-experiment creates a
    subdirectory named after RV_EXPERIMENT_NAME (also batch_{i}) inside it.

    The output file is named summary.csv (not aggregated_summary.csv) so that
    ObjectiveFunction.compute_baseline_max_errors() can read it directly at
    {output_dir}/summary.csv without path changes.
    """
    dfs = []
    for i in range(n_batches):
        csv_path = output_dir / f"batch_{i}" / f"batch_{i}" / "summary.csv"
        if csv_path.exists():
            dfs.append(pd.read_csv(csv_path))
        else:
            logger.warning(f"Missing batch {i} summary: {csv_path}")

    if dfs:
        combined = pd.concat(dfs, ignore_index=True)
        out_path = output_dir / "summary.csv"
        combined.to_csv(out_path, index=False)

        # Symlink for human readability (D5/L2)
        symlink_path = output_dir / "aggregated_summary.csv"
        if symlink_path.exists() or symlink_path.is_symlink():
            symlink_path.unlink()
        symlink_path.symlink_to("summary.csv")

        logger.info(
            f"Aggregated {len(dfs)} batch summaries "
            f"({len(combined)} rows) into {out_path}"
        )
        return out_path

    return None


def read_filter_file(filter_path: str) -> list[str]:
    """Read APK names from a filter file (one name per line).

    Strips whitespace, skips empty lines and comments (lines starting with #).
    """
    apk_names = []
    with open(filter_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                apk_names.append(stripped)
    return apk_names


def preflight_checks(data_dir: str, filter_file: str) -> None:
    """Validate prerequisites before launching containers.

    Checks that the data directory and filter file exist, and that
    the filesystem has enough free space (at least 10 GB).
    Raises SystemExit on failure.
    """
    data_path = Path(data_dir)
    if not data_path.is_dir():
        print(f"ERROR: data directory not found: {data_dir}", file=sys.stderr)
        raise SystemExit(1)

    filter_path = Path(filter_file)
    if not filter_path.is_file():
        print(f"ERROR: filter file not found: {filter_file}", file=sys.stderr)
        raise SystemExit(1)

    # Check disk space on the output filesystem (use data_dir parent as proxy)
    min_free_bytes = 10 * 1024 * 1024 * 1024  # 10 GB
    usage = shutil.disk_usage(str(data_path))
    if usage.free < min_free_bytes:
        free_gb = usage.free / (1024 ** 3)
        print(
            f"ERROR: insufficient disk space: {free_gb:.1f} GB free, "
            f"need at least 10 GB",
            file=sys.stderr,
        )
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run baseline/validation experiments across N Docker containers. "
            "Splits APKs via round-robin and aggregates results."
        )
    )
    parser.add_argument(
        "--tools",
        required=True,
        help="Tool specification, same for all containers (e.g., 'ape,fastbot,rvagent:pure_algorithm')",
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        help="Directory with pre-instrumented APKs and static analysis files",
    )
    parser.add_argument(
        "--filter-file",
        required=True,
        help="Text file with APK names to process (one per line)",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for results, filter files, and compose file",
    )
    parser.add_argument(
        "--n-containers",
        type=int,
        default=6,
        help="Number of Docker containers to run in parallel (default: 6)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Timeout per APK per tool in seconds (default: 300)",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=3,
        help="Number of repetitions per APK per tool (default: 3)",
    )
    parser.add_argument(
        "--image",
        default="phtcosta/rvandroid:0.8.0",
        help="Docker image to use (default: phtcosta/rvandroid:0.8.0)",
    )
    parser.add_argument(
        "--cpus",
        type=int,
        default=10,
        help="CPU limit per container (default: 10)",
    )
    parser.add_argument(
        "--memory",
        default="20g",
        help="Memory limit per container (default: 20g)",
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Generate compose file and batch filters, then exit without launching containers",
    )
    parser.add_argument(
        "--sglang-url",
        type=str,
        default=None,
        help="SGLang server URL reachable from containers (e.g. http://host.docker.internal:30000/v1). "
             "Injects llm_base_url into multimode tool spec and adds extra_hosts to compose.",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Preflight checks
    preflight_checks(args.data_dir, args.filter_file)

    # Read APK list from filter file
    apk_names = read_filter_file(args.filter_file)
    if not apk_names:
        print("ERROR: no APK names found in filter file", file=sys.stderr)
        sys.exit(1)

    # Determine actual number of batches (no more batches than APKs)
    n_batches = min(args.n_containers, len(apk_names))

    # Split APKs into batches
    batches = split_apks_round_robin(apk_names, n_batches)

    print(f"Splitting {len(apk_names)} APKs across {n_batches} containers:")
    for i, batch in enumerate(batches):
        print(f"  batch_{i}: {len(batch)} APKs")

    # Create output directory
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write per-batch filter files
    for i, batch in enumerate(batches):
        filter_path = output_path / f"batch_{i}_apks.txt"
        filter_path.write_text("\n".join(batch) + "\n")
        logger.info(f"Wrote {len(batch)} APKs to {filter_path}")

    # Inject llm_base_url into multimode tool spec when --sglang-url is provided
    tools = args.tools
    if args.sglang_url and "multimode" in tools:
        if "@" in tools:
            tools = tools.rstrip(",") + f",llm_base_url={args.sglang_url}"
        else:
            # No params yet — add the @ separator before the param
            tools = tools.replace("multimode", f"multimode@llm_base_url={args.sglang_url}", 1)

    # Generate and write compose file
    extra_hosts = ["host.docker.internal:host-gateway"] if args.sglang_url else None
    compose = generate_baseline_compose(
        n_batches=n_batches,
        tools=tools,
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        image=args.image,
        cpus=args.cpus,
        memory=args.memory,
        timeout=args.timeout,
        repetitions=args.repetitions,
        extra_hosts=extra_hosts,
    )

    compose_path = output_path / "docker-compose.yml"
    with open(compose_path, "w", encoding="utf-8") as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

    print(f"Compose file: {compose_path}")

    if args.generate_only:
        print("--generate-only: exiting before docker compose up")
        return

    # Run containers
    print(f"\nLaunching {n_batches} containers...")
    try:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_path), "up"],
            check=False,
        )
    finally:
        # Guaranteed cleanup: bring down containers even on interrupt/error
        subprocess.run(
            ["docker", "compose", "-f", str(compose_path), "down"],
            check=False,
        )

    # Aggregate results
    print("\nAggregating batch summaries...")
    summary_path = aggregate_summaries(output_path, n_batches)

    # Print summary
    print("\n" + "=" * 60)
    print("BASELINE COMPLETE")
    print("=" * 60)
    print(f"Tools: {args.tools}")
    print(f"APKs: {len(apk_names)}")
    print(f"Containers: {n_batches}")
    print(f"Repetitions: {args.repetitions}")
    print(f"Timeout: {args.timeout}s per APK per tool")
    if summary_path:
        df = pd.read_csv(summary_path)
        print(f"Aggregated summary: {summary_path} ({len(df)} rows)")
        if "cov_method" in df.columns:
            print(f"  Mean method coverage: {df['cov_method'].mean():.1f}%")
        if "errors" in df.columns:
            print(f"  Mean errors: {df['errors'].mean():.1f}")
    else:
        print("WARNING: no batch summaries found to aggregate")
    print(f"Results directory: {args.output_dir}")


if __name__ == "__main__":
    main()
