#!/usr/bin/env python3
"""
Overnight validation experiment - 60 apps x 4 strategies x 1 rep.

Configuration:
- 60 stratified apps from rv-agent/apks/
- 4 strategies: rvagent, dfs, bfs, greedy
- 180 seconds (3 min) timeout per run
- 1 repetition
- Total: 240 runs
- Estimated time: ~14 hours

Usage:
    python run_overnight.py              # Start/resume experiment
    python run_overnight.py --reset      # Reset and start fresh
    python run_overnight.py --dry-run    # Show plan without running
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
from glob import glob

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from experiment import ExperimentConfig, ExperimentRunner


# APKs directory (local to rv-agent module)
APKS_DIR = Path(__file__).parent.parent / "apks"

# Experiment parameters
STRATEGIES = ["rvagent", "dfs", "bfs", "greedy"]
TIMEOUT_SECONDS = 180  # 3 minutes
REPETITIONS = 1
BASE_SEED = 42


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


def get_apk_paths() -> list[str]:
    """Get all APK paths from the apks directory."""
    apks = sorted(glob(str(APKS_DIR / "*.apk")))
    if not apks:
        raise RuntimeError(f"No APKs found in {APKS_DIR}")
    return apks


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run overnight validation experiment (60 apps x 4 strategies)"
    )

    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show plan without running"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Reset checkpoint and start fresh"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose logging"
    )
    parser.add_argument(
        "--device", type=str, default="emulator-5554",
        help="Device serial (default: emulator-5554)"
    )
    parser.add_argument(
        "--timeout", type=int, default=TIMEOUT_SECONDS,
        help=f"Timeout per run in seconds (default: {TIMEOUT_SECONDS})"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Limit number of APKs (0 = all, for testing)"
    )

    return parser.parse_args()


def check_device(device_id: str) -> bool:
    """Check if device is available."""
    import subprocess
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return device_id in result.stdout
    except Exception:
        return False


def main():
    """Main entry point."""
    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Get APK paths
    apk_paths = get_apk_paths()

    if args.limit > 0:
        apk_paths = apk_paths[:args.limit]
        logger.info(f"Limited to {args.limit} APKs for testing")

    # Create config
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config = ExperimentConfig(
        experiment_id=f"overnight_validation_{timestamp}",
        experiment_name="Overnight Strategy Validation (60 apps)",
        apk_paths=apk_paths,
        strategies=STRATEGIES,
        repetitions=REPETITIONS,
        timeout_seconds=args.timeout,
        agent_mode="pure_algorithm",
        base_seed=BASE_SEED,
        device_serial=args.device,
        enable_static_analysis=False,
    )

    # Print summary
    print()
    print("=" * 70)
    print("OVERNIGHT VALIDATION EXPERIMENT")
    print("=" * 70)
    print(f"APKs directory: {APKS_DIR}")
    print(f"Total APKs: {len(apk_paths)}")
    print(f"Strategies: {', '.join(STRATEGIES)}")
    print(f"Repetitions: {REPETITIONS}")
    print(f"Timeout per run: {args.timeout}s ({args.timeout/60:.1f} min)")
    print(f"Device: {args.device}")
    print()
    print(f"Total runs: {config.total_runs}")
    print(f"Estimated time: {config.estimated_time_hours:.1f} hours")
    print(f"Expected finish: ~{datetime.now().hour + int(config.estimated_time_hours)}:00")
    print("=" * 70)
    print()

    # List first/last few APKs
    print("APKs (first 5):")
    for apk in apk_paths[:5]:
        print(f"  - {Path(apk).name}")
    if len(apk_paths) > 10:
        print(f"  ... ({len(apk_paths) - 10} more)")
    print("APKs (last 5):")
    for apk in apk_paths[-5:]:
        print(f"  - {Path(apk).name}")
    print()

    if args.dry_run:
        print("DRY RUN - Not starting experiment")
        print(f"Would run {config.total_runs} configurations")
        return

    # Check device
    if not check_device(args.device):
        print(f"ERROR: Device {args.device} not found!")
        print("Start emulator first: emulator -avd <name>")
        sys.exit(1)

    print(f"Device {args.device} is connected")
    print()

    # Confirmation
    response = input("Start overnight experiment? [y/N]: ")
    if response.lower() != 'y':
        print("Aborted.")
        sys.exit(0)

    # Create runner and start
    runner = ExperimentRunner(config)

    if args.reset:
        runner.checkpoint.reset()
        logger.info("Checkpoint reset - starting fresh")

    try:
        result = runner.run_experiment(resume=not args.reset)

        print()
        print("=" * 70)
        print("EXPERIMENT COMPLETED")
        print("=" * 70)
        print(f"Completed: {result['completed']}/{result['total']}")
        print(f"Failed: {result['failed']}")
        print(f"Results directory: {runner.experiment_dir}")
        print("=" * 70)
        print()

    except KeyboardInterrupt:
        print("\n\nInterrupted! Progress saved to checkpoint.")
        print("Resume with: python run_overnight.py")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
