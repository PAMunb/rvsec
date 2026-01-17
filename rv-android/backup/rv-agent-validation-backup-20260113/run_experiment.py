#!/usr/bin/env python3
"""
Main script for running strategy validation experiments.

Supports:
- Static analysis integration for MOP metrics
- Composite scoring for strategy comparison
- Checkpoint/resume for long experiments

Usage:
    # Run with static analysis apps (recommended)
    python run_experiment.py --with-static

    # Single test run
    python run_experiment.py --test --app cryptoapp.apk --strategy rvagent

    # Resume interrupted experiment
    python run_experiment.py --resume

    # Custom configuration
    python run_experiment.py --strategies dfs,bfs --reps 2 --timeout 180
"""

import argparse
import logging
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from experiment import ExperimentConfig, ExperimentRunner
from experiment.config import (
    APPS_WITH_STATIC_ANALYSIS,
    get_apps_with_static_analysis,
    DEFAULT_STATIC_ANALYSIS_DIR,
)


DEFAULT_STRATEGIES = ["rvagent", "dfs", "bfs", "greedy"]


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run strategy validation experiment"
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--test", action="store_true",
        help="Run single test (requires --app and --strategy)"
    )
    mode_group.add_argument(
        "--with-static", action="store_true",
        help="Run with apps that have static analysis data (14 apps)"
    )

    # Single test options
    parser.add_argument(
        "--app", type=str,
        help="App name (APK filename) for test run (e.g., cryptoapp.apk)"
    )
    parser.add_argument(
        "--strategy", type=str,
        help="Strategy for test run"
    )

    # Experiment options
    parser.add_argument(
        "--strategies", type=str,
        help="Comma-separated list of strategies (default: rvagent,dfs,bfs,greedy)"
    )
    parser.add_argument(
        "--apps", type=str,
        help="Comma-separated list of app names to test (e.g., cryptoapp.apk,ludo.apk)"
    )
    parser.add_argument(
        "--reps", type=int, default=3,
        help="Number of repetitions (default: 3)"
    )
    parser.add_argument(
        "--timeout", type=int, default=180,
        help="Timeout per run in seconds (default: 180)"
    )

    # Control options
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from checkpoint"
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Reset checkpoint and start fresh"
    )
    parser.add_argument(
        "--no-static", action="store_true",
        help="Disable static analysis loading"
    )

    # Environment options
    parser.add_argument(
        "--device", type=str, default="emulator-5554",
        help="Device serial (default: emulator-5554)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Verbose logging"
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip confirmation prompt"
    )

    return parser.parse_args()


def find_apk_path(app_name: str) -> str:
    """
    Find APK path for an app by name.

    Searches in:
    1. Static analysis directories
    2. Common APK locations

    Args:
        app_name: APK filename (e.g., cryptoapp.apk)

    Returns:
        Full path to APK file.

    Raises:
        FileNotFoundError: If APK not found.
    """
    # Search in static analysis dirs
    for app in APPS_WITH_STATIC_ANALYSIS:
        if app["name"] == app_name:
            app_dir = DEFAULT_STATIC_ANALYSIS_DIR / app["dir"]
            apk_path = app_dir / app_name
            if apk_path.exists():
                return str(apk_path)

    # Search in parent of static analysis dir
    apk_path = DEFAULT_STATIC_ANALYSIS_DIR / app_name
    if apk_path.exists():
        return str(apk_path)

    raise FileNotFoundError(f"APK not found: {app_name}")


def run_test(args):
    """Run a single test."""
    if not args.app or not args.strategy:
        print("Error: --test requires --app and --strategy")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("SINGLE TEST RUN")
    print(f"App: {args.app}")
    print(f"Strategy: {args.strategy}")
    print(f"Timeout: {args.timeout}s")
    print(f"Static analysis: {'disabled' if args.no_static else 'enabled'}")
    print(f"{'='*60}\n")

    # Find APK path
    try:
        apk_path = find_apk_path(args.app)
        print(f"APK path: {apk_path}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Create config
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    config = ExperimentConfig(
        experiment_id=f"test_{args.strategy}_{timestamp}",
        experiment_name="Single Test Run",
        apk_paths=[apk_path],
        strategies=[args.strategy],
        repetitions=1,
        timeout_seconds=args.timeout,
        device_serial=args.device,
        enable_static_analysis=not args.no_static,
    )

    runner = ExperimentRunner(config)
    result = runner.run_single(apk_path, args.strategy)

    print(f"\n{'='*60}")
    print("RESULT:")
    print(f"  Status: {result.get('status', 'unknown')}")
    print(f"  States: {result.get('states_discovered', 0)}")
    print(f"  Actions: {result.get('total_actions', 0)}")
    print(f"  Valid: {result.get('action_validity_rate', 0):.1f}%")
    print(f"  Time: {result.get('execution_time_seconds', 0):.1f}s")
    print(f"  UI Coverage: {result.get('ui_coverage_percentage', 0):.1f}%")
    print(f"  MOP Methods: {result.get('mop_methods_reached', 0)}")
    print(f"  States/Action: {result.get('states_per_action', 0):.4f}")
    print(f"  Static Analysis: {result.get('static_analysis_enabled', False)}")
    print(f"{'='*60}\n")

    return result


def run_with_static_apps(args):
    """Run experiment with apps that have static analysis data."""
    strategies = args.strategies.split(",") if args.strategies else DEFAULT_STRATEGIES

    # Get verified apps
    verified_apps = get_apps_with_static_analysis()
    if not verified_apps:
        print("Error: No apps with complete static analysis found")
        sys.exit(1)

    # Filter by --apps if specified
    if args.apps:
        app_filter = [a.strip() for a in args.apps.split(",")]
        verified_apps = [app for app in verified_apps if app["name"] in app_filter]
        if not verified_apps:
            print(f"Error: No matching apps found for: {app_filter}")
            print("Available apps:")
            for app in get_apps_with_static_analysis():
                print(f"  - {app['name']}")
            sys.exit(1)

    # Build APK paths
    apk_paths = []
    for app in verified_apps:
        app_dir = Path(app["static_dir"])
        apk_path = app_dir / app["name"]
        if apk_path.exists():
            apk_paths.append(str(apk_path))
        else:
            # Try parent directory
            apk_path = app_dir.parent / app["name"]
            if apk_path.exists():
                apk_paths.append(str(apk_path))

    if not apk_paths:
        print("Error: No APK files found for apps with static analysis")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("STRATEGY VALIDATION WITH STATIC ANALYSIS")
    print(f"{'='*60}")
    print(f"Apps with static analysis: {len(apk_paths)}")
    print(f"Strategies: {strategies}")
    print(f"Repetitions: {args.reps}")
    print(f"Timeout: {args.timeout}s per run")
    print(f"Total runs: {len(apk_paths) * len(strategies) * args.reps}")
    print(f"{'='*60}")
    print("\nApps:")
    for app in verified_apps:
        print(f"  - {app['name']} ({app['category']})")
    print()

    # Create config
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    config = ExperimentConfig(
        experiment_id=f"static_validation_{timestamp}",
        experiment_name="Strategy Validation with Static Analysis",
        apk_paths=apk_paths,
        strategies=strategies,
        repetitions=args.reps,
        timeout_seconds=args.timeout,
        device_serial=args.device,
        enable_static_analysis=True,
    )

    estimated_hours = config.estimated_time_hours
    print(f"Estimated time: {estimated_hours:.1f} hours")
    print()

    # Confirmation (skip if --yes flag)
    if not args.yes:
        response = input("Start experiment? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    runner = ExperimentRunner(config)

    if args.reset:
        runner.checkpoint.reset()
        print("Checkpoint reset.")

    result = runner.run_experiment(resume=args.resume or not args.reset)

    print(f"\n{'='*60}")
    print("EXPERIMENT COMPLETED")
    print(f"Completed: {result['completed']}/{result['total']}")
    print(f"Failed: {result['failed']}")
    print(f"Results: {runner.experiment_dir}")
    print(f"{'='*60}\n")

    # Quick analysis if completed
    if result['completed'] > 0:
        print("Run analysis with:")
        print(f"  python analysis/strategy_comparison.py --experiment-dir {runner.experiment_dir}")

    return result


def main():
    """Main entry point."""
    args = parse_args()
    setup_logging(args.verbose)

    try:
        if args.test:
            run_test(args)
        elif args.with_static:
            run_with_static_apps(args)
        else:
            # Default: run with static apps
            print("Tip: Use --with-static for apps with static analysis")
            print("     Use --test --app APP --strategy STRATEGY for single test")
            print()
            run_with_static_apps(args)

    except KeyboardInterrupt:
        print("\nInterrupted. Progress saved to checkpoint.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
