#!/usr/bin/env python3
"""
Docker-based preprocessing for Phase A of the calibration campaign.

Splits APKs across N Docker containers, each running rv-experiment with
--skip-execution to perform only preprocessing (monitor generation,
APK instrumentation, static analysis). After all containers finish,
collects artifacts and assembles a flat dataset directory.

The Docker image contains RVSEC_HOME, Java 8, and all tools — no host-side
dependencies needed. The entrypoint is overridden because the frozen image's
docker-entrypoint.sh does not support RV_SKIP_EXECUTION.

Usage:
    uv run python scripts/preprocess_docker.py \
        --apks-dir /path/to/original_apks \
        --filter-file /tmp/exp01_jca_apks.txt \
        --output-dir ./results/preprocessing_v2 \
        --n-containers 6
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Stagger delay between containers to avoid boot-storm on the host (seconds)
CONTAINER_STAGGER_SECONDS = 10

# SA file extensions that must all be present for an APK to pass completeness
SA_EXTENSIONS = (".json",)


# ---------------------------------------------------------------------------
# Pure functions — all testable without Docker
# ---------------------------------------------------------------------------


def split_apks_round_robin(apk_names: list[str], n_batches: int) -> list[list[str]]:
    """Distribute APK names across N batches using round-robin assignment."""
    batches: list[list[str]] = [[] for _ in range(n_batches)]
    for i, apk in enumerate(apk_names):
        batches[i % n_batches].append(apk)
    return batches


def generate_preprocess_compose(
    n_containers: int,
    data_dir: str,
    output_dir: str,
    image: str,
    cpus: int,
    memory: str,
    sa_timeout: Optional[int] = None,
    jvm_memory: Optional[str] = None,
) -> dict:
    """Generate a docker-compose dict for preprocessing containers.

    Each container runs rv-experiment with --skip-execution, which performs
    only the preprocessing phases (monitor generation, instrumentation,
    static analysis) without launching emulators or executing testing tools.

    The entrypoint is overridden because the frozen Docker image's
    docker-entrypoint.sh does not map RV_SKIP_EXECUTION. Instead, we
    invoke rv-experiment directly via bash -c.

    Unlike calibration/baseline compose, preprocessing containers do NOT
    set RV_SKIP_MONITORS, RV_SKIP_INSTRUMENT, or RV_SKIP_STATIC_ANALYSIS
    — all preprocessing phases must run.
    """
    data_dir = str(Path(data_dir).resolve())
    output_dir = str(Path(output_dir).resolve())

    services = {}
    for i in range(n_containers):
        service_name = f"preprocess_{i}"
        services[service_name] = {
            "image": image,
            "container_name": service_name,
            "entrypoint": ["bash", "-c"],
            "command": [
                f"sleep {i * CONTAINER_STAGGER_SECONDS} && "
                "uv run rv-experiment run "
                "--tools monkey "
                "--skip-execution "
                "--specification-set jca "
                "--apks-dir /opt/rvsec/rv-android/apks "
                "--apks-filter /opt/rvsec/rv-android/filters/filter.txt "
                "--output-dir /opt/rvsec/rv-android/out "
                "--no-window"
            ],
            "volumes": [
                f"{data_dir}:/opt/rvsec/rv-android/apks:ro",
                f"{output_dir}/{service_name}_filter.txt:/opt/rvsec/rv-android/filters/filter.txt:ro",
                f"{output_dir}/{service_name}:/opt/rvsec/rv-android/out",
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

        env_vars = []
        if sa_timeout is not None:
            env_vars.append(f"RV_SA_TIMEOUT={sa_timeout}")
        if jvm_memory is not None:
            env_vars.append(f"RV_JVM_MEMORY={jvm_memory}")
        if env_vars:
            services[service_name]["environment"] = env_vars

    return {"services": services}


def collect_preprocessed_artifacts(output_dir: Path, n_containers: int) -> Path:
    """Merge per-container instrumented_apks/ into a single dataset/ directory.

    Each container writes its output to {output_dir}/preprocess_{i}/.
    Inside each container's output, instrumented APKs and SA files are in
    the instrumented_apks/ subdirectory.

    Files are copied (not moved) so container output is preserved for
    debugging if needed.

    Returns the path to the assembled dataset directory.
    """
    dataset_dir = output_dir / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    for i in range(n_containers):
        source = output_dir / f"preprocess_{i}" / "instrumented_apks"
        if not source.is_dir():
            logger.warning(f"Missing container output: {source}")
            continue

        for f in source.iterdir():
            if f.is_file():
                dest = dataset_dir / f.name
                if not dest.exists():
                    shutil.copy2(f, dest)
                    copied += 1

    logger.info(f"Collected {copied} files into {dataset_dir}")
    return dataset_dir


def filter_by_sa_completeness(
    dataset_dir: Path,
) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Filter APKs by static analysis completeness.

    An APK passes if it has the unified analysis JSON file (.json).
    SA files are named {apk_filename}.json (e.g. com.example.app.apk.json).

    Returns:
        (passed, failed) where:
        - passed: list of APK filenames that have the analysis JSON
        - failed: list of (apk_filename, missing_extensions) for APKs missing files
    """
    apk_files = sorted(f.name for f in dataset_dir.glob("*.apk"))

    passed = []
    failed = []
    for apk_name in apk_files:
        missing = [
            ext
            for ext in SA_EXTENSIONS
            if not (dataset_dir / f"{apk_name}{ext}").exists()
        ]
        if missing:
            failed.append((apk_name, missing))
        else:
            passed.append(apk_name)

    return passed, failed


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


def preflight_checks(apks_dir: str, filter_file: str) -> None:
    """Validate prerequisites before launching containers.

    Checks that the APKs directory and filter file exist, and that
    the filesystem has enough free space (at least 20 GB — preprocessing
    generates monitors, instrumented APKs, and SA files).
    Raises SystemExit on failure.
    """
    apks_path = Path(apks_dir)
    if not apks_path.is_dir():
        print(f"ERROR: APKs directory not found: {apks_dir}", file=sys.stderr)
        raise SystemExit(1)

    filter_path = Path(filter_file)
    if not filter_path.is_file():
        print(f"ERROR: filter file not found: {filter_file}", file=sys.stderr)
        raise SystemExit(1)

    # Check disk space (preprocessing generates more data than execution)
    min_free_bytes = 20 * 1024 * 1024 * 1024  # 20 GB
    usage = shutil.disk_usage(str(apks_path))
    if usage.free < min_free_bytes:
        free_gb = usage.free / (1024**3)
        print(
            f"ERROR: insufficient disk space: {free_gb:.1f} GB free, "
            "need at least 20 GB",
            file=sys.stderr,
        )
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run preprocessing (monitors, instrumentation, static analysis) "
            "across N Docker containers. Collects artifacts and filters by "
            "SA completeness."
        )
    )
    parser.add_argument(
        "--apks-dir",
        required=True,
        help="Directory with original (non-instrumented) APKs",
    )
    parser.add_argument(
        "--filter-file",
        required=True,
        help="Text file with APK names to process (one per line)",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for container outputs, dataset, and compose file",
    )
    parser.add_argument(
        "--n-containers",
        type=int,
        default=6,
        help="Number of Docker containers to run in parallel (default: 6)",
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
        "--sa-timeout",
        type=int,
        default=None,
        help="Static analysis timeout in seconds (default: use image default of 600s)",
    )
    parser.add_argument(
        "--jvm-memory",
        default=None,
        help="JVM heap size for GATOR (e.g. '20g'). Default: use image default of 12g",
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Generate compose file and filters, then exit without launching containers",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Preflight checks
    preflight_checks(args.apks_dir, args.filter_file)

    # Read APK list from filter file
    apk_names = read_filter_file(args.filter_file)
    if not apk_names:
        print("ERROR: no APK names found in filter file", file=sys.stderr)
        sys.exit(1)

    # Determine actual number of containers (no more than APKs)
    n_containers = min(args.n_containers, len(apk_names))

    # Split APKs into batches
    batches = split_apks_round_robin(apk_names, n_containers)

    print(f"Splitting {len(apk_names)} APKs across {n_containers} containers:")
    for i, batch in enumerate(batches):
        print(f"  preprocess_{i}: {len(batch)} APKs")

    # Create output directory
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Write per-container filter files
    for i, batch in enumerate(batches):
        filter_path = output_path / f"preprocess_{i}_filter.txt"
        filter_path.write_text("\n".join(batch) + "\n")
        logger.info(f"Wrote {len(batch)} APKs to {filter_path}")

    # Generate and write compose file
    compose = generate_preprocess_compose(
        n_containers=n_containers,
        data_dir=args.apks_dir,
        output_dir=args.output_dir,
        image=args.image,
        cpus=args.cpus,
        memory=args.memory,
        sa_timeout=args.sa_timeout,
        jvm_memory=args.jvm_memory,
    )

    compose_path = output_path / "docker-compose.yml"
    with open(compose_path, "w", encoding="utf-8") as f:
        yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

    print(f"Compose file: {compose_path}")

    if args.generate_only:
        print("--generate-only: exiting before docker compose up")
        return

    # Run containers
    print(f"\nLaunching {n_containers} containers...")
    try:
        subprocess.run(
            ["docker", "compose", "-", str(compose_path), "up"],
            check=False,
        )
    finally:
        subprocess.run(
            ["docker", "compose", "-f", str(compose_path), "down"],
            check=False,
        )

    # Collect artifacts from all containers
    print("\nCollecting preprocessed artifacts...")
    dataset_dir = collect_preprocessed_artifacts(output_path, n_containers)

    # Filter by SA completeness
    print("Filtering by SA completeness...")
    passed, failed = filter_by_sa_completeness(dataset_dir)

    # Write passed_apks.txt and failed_apks.txt
    passed_path = output_path / "passed_apks.txt"
    passed_path.write_text("\n".join(passed) + "\n" if passed else "")

    failed_path = output_path / "failed_apks.txt"
    with open(failed_path, "w", encoding="utf-8") as f:
        for apk_name, missing in failed:
            f.write(f"{apk_name}\tmissing: {', '.join(missing)}\n")

    # Print summary
    print("\n" + "=" * 60)
    print("PREPROCESSING COMPLETE")
    print("=" * 60)
    print(f"APKs processed: {len(apk_names)}")
    print(f"Containers: {n_containers}")
    print(f"Passed SA completeness: {len(passed)}")
    print(f"Failed SA completeness: {len(failed)}")
    print(f"Dataset directory: {dataset_dir}")
    print(f"Passed APKs list: {passed_path}")
    if failed:
        print(f"Failed APKs list: {failed_path}")
        print("\nFailed APKs:")
        for apk_name, missing in failed:
            print(f"  {apk_name}: missing {', '.join(missing)}")

    print(f"\nNext step: run select_dataset.py with --passed-apks {passed_path}")


if __name__ == "__main__":
    main()
