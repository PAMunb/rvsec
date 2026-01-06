#!/usr/bin/env python3
"""
Simple test script for validation framework.

Tests all 4 strategies with a single APK.
Usage:
    python test_simple.py --apk /path/to/app.apk --timeout 180
"""

import sys
import logging
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from rv_android_core.domain.app import App

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default APK paths for V10 baseline apps
V10_APKS = {
    "cryptoapp": "/home/pedro/desenvolvimento/RV_ANDROID/apks/cryptoapp.apk",
    "keepass": "/home/pedro/desenvolvimento/RV_ANDROID/apks/01/com.android.keepass_26702.apk",
    "kryptey": "/home/pedro/desenvolvimento/RV_ANDROID/apks/02/com.amnesica.kryptey_17.apk",
    "cryptomator": "/home/pedro/desenvolvimento/RV_ANDROID/apks/22/org.cryptomator.lite_2824.apk",
    "amaze": "/home/pedro/desenvolvimento/RV_ANDROID/apks/03/com.amaze.filemanager_117.apk",
    "twidere": "/home/pedro/desenvolvimento/RV_ANDROID/apks/04/org.mariotaku.twidere_490.apk",
    "moneytracker": "/home/pedro/desenvolvimento/RV_ANDROID/apks/05/com.blogspot.e_kanivets.moneytracker_28.apk",
    "leafpic": "/home/pedro/desenvolvimento/RV_ANDROID/apks/06/com.alienpants.leafpicrevived_20.apk",
    "s3manager": "/home/pedro/desenvolvimento/RV_ANDROID/apks/07/asgardius.page.s3manager_28.apk",
    "simplenotes": "/home/pedro/desenvolvimento/RV_ANDROID/apks/08/com.rafapps.simplenotes_14.apk",
}


def check_device(device_id: str = "emulator-5554") -> bool:
    """Check if device is available."""
    try:
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if device_id in result.stdout:
            logger.info(f"✓ Device {device_id} is connected")
            return True
        else:
            logger.error(f"✗ Device {device_id} not found")
            return False
    except Exception as e:
        logger.error(f"✗ Error checking device: {e}")
        return False


def install_app(apk_path: str, device_id: str = "emulator-5554") -> bool:
    """Install APK with permissions granted (-g flag)."""
    try:
        logger.info(f"Installing {apk_path}...")
        result = subprocess.run(
            ["adb", "-s", device_id, "install", "-g", apk_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        if "Success" in result.stdout:
            logger.info(f"✓ Installed successfully")
            time.sleep(2)
            return True
        else:
            logger.error(f"✗ Install failed: {result.stdout} {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"✗ Error installing: {e}")
        return False


def uninstall_app(package_name: str, device_id: str = "emulator-5554") -> bool:
    """Uninstall app from device."""
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "uninstall", package_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        if "Success" in result.stdout:
            logger.info(f"✓ Uninstalled {package_name}")
            return True
        else:
            logger.warning(f"Uninstall result: {result.stdout}")
            return False
    except Exception as e:
        logger.warning(f"Error uninstalling: {e}")
        return False


def clear_app_data(package_name: str, device_id: str = "emulator-5554"):
    """Clear app data before run."""
    try:
        subprocess.run(
            ["adb", "-s", device_id, "shell", "pm", "clear", package_name],
            check=True,
            capture_output=True,
            timeout=30
        )
        logger.info(f"Cleared app data for {package_name}")
        time.sleep(1)
    except Exception as e:
        logger.warning(f"Could not clear app data: {e}")


def run_single_strategy(
    package_name: str,
    strategy: str,
    timeout_seconds: int,
    device_id: str = "emulator-5554"
):
    """Run a single strategy test."""
    from rv_agent.config.agent_config import RVAgentConfig
    from rv_agent.core.agent_factory import AgentFactory

    logger.info("=" * 60)
    logger.info(f"TESTING: {strategy.upper()}")
    logger.info(f"Package: {package_name}")
    logger.info(f"Timeout: {timeout_seconds}s")
    logger.info("=" * 60)

    # Clear app data first
    clear_app_data(package_name, device_id)

    # Create config for pure algorithm mode (no LLM)
    config = RVAgentConfig(
        package_name=package_name,
        device_id=device_id,
        agent_mode="pure_algorithm",
        strategy=strategy,
        timeout=timeout_seconds,
        results_dir=str(Path(__file__).parent / "test_results"),
        debug_mode=True,
    )

    start_time = time.time()

    try:
        agent = AgentFactory.create_agent(
            config=config,
            static_data=None
        )

        result = agent.run()
        end_time = time.time()

        execution_time = end_time - start_time
        graph_report = agent.dynamic_graph.get_transition_graph_report()
        states_discovered = graph_report["total_states"]
        transitions = graph_report["total_transitions"]

        # Get detailed memory stats (includes UI coverage and action distribution)
        memory_stats = result.get("memory_stats", {})
        ui_coverage = memory_stats.get("ui_coverage", {})

        metrics = {
            "strategy": strategy,
            "status": "completed",
            "execution_time": round(execution_time, 2),
            "states_discovered": states_discovered,
            "transitions": transitions,
            "total_actions": result.get("total_actions", 0),
            "valid_actions": result.get("valid_actions", 0),
            "invalid_actions": result.get("invalid_actions", 0),
            # UI coverage metrics
            "elements_discovered": ui_coverage.get("total_unique_elements", 0),
            "total_interactions": ui_coverage.get("total_interactions", 0),
            "action_distribution": ui_coverage.get("action_distribution", {}),
            "screens_explored": ui_coverage.get("total_screens", 0),
            # Most/least tested elements
            "most_tested_elements": ui_coverage.get("most_tested_elements", []),
            "recent_discoveries": ui_coverage.get("recent_discoveries", 0),
        }

        logger.info("-" * 40)
        logger.info("RESULT:")
        logger.info(f"  Status: {metrics['status']}")
        logger.info(f"  Time: {metrics['execution_time']}s")
        logger.info(f"  States: {metrics['states_discovered']}")
        logger.info(f"  Transitions: {metrics['transitions']}")
        logger.info(f"  Actions: {metrics['total_actions']}")
        logger.info(f"  Elements discovered: {metrics['elements_discovered']}")
        logger.info(f"  Action distribution: {metrics['action_distribution']}")
        logger.info("-" * 40)

        return metrics

    except Exception as e:
        end_time = time.time()
        logger.error(f"Error running {strategy}: {e}", exc_info=True)
        return {
            "strategy": strategy,
            "status": "error",
            "error": str(e),
            "execution_time": round(end_time - start_time, 2),
        }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Simple validation test")
    parser.add_argument(
        "--apk", type=str,
        help="Path to APK file (or short name: cryptoapp, keepass, etc.)"
    )
    parser.add_argument(
        "--timeout", type=int, default=180,
        help="Timeout in seconds per strategy (default: 180 = 3 min)"
    )
    parser.add_argument(
        "--strategies", type=str, default="rvagent,dfs,bfs,greedy",
        help="Comma-separated strategies (default: rvagent,dfs,bfs,greedy)"
    )
    parser.add_argument(
        "--device", type=str, default="emulator-5554",
        help="Device serial (default: emulator-5554)"
    )
    parser.add_argument(
        "--reps", type=int, default=1,
        help="Number of repetitions per strategy (default: 1)"
    )

    args = parser.parse_args()

    # Resolve APK path
    if args.apk is None:
        args.apk = "cryptoapp"

    if args.apk in V10_APKS:
        apk_path = V10_APKS[args.apk]
    else:
        apk_path = args.apk

    if not Path(apk_path).exists():
        print(f"ERROR: APK not found: {apk_path}")
        print(f"Available short names: {', '.join(V10_APKS.keys())}")
        sys.exit(1)

    # Get package name from APK using Androguard
    logger.info(f"Loading APK: {apk_path}")
    app = App(app_path=apk_path)
    package_name = app.package_name

    print("\n" + "=" * 60)
    print("SIMPLE VALIDATION TEST")
    print("=" * 60)
    print(f"APK: {apk_path}")
    print(f"Package: {package_name}")
    print(f"Timeout: {args.timeout}s per strategy")
    print(f"Strategies: {args.strategies}")
    print(f"Repetitions: {args.reps}")
    print(f"Device: {args.device}")
    print(f"Total runs: {len(args.strategies.split(','))} strategies × {args.reps} reps = {len(args.strategies.split(',')) * args.reps}")
    print("=" * 60 + "\n")

    # Pre-flight checks
    if not check_device(args.device):
        print("\nERROR: Device not available. Start emulator first.")
        sys.exit(1)

    # Install app
    if not install_app(apk_path, args.device):
        print(f"\nERROR: Could not install {apk_path}")
        sys.exit(1)

    # Run tests
    strategies = args.strategies.split(",")
    results = []
    run_counter = 0
    total_runs = len(strategies) * args.reps

    try:
        for rep in range(1, args.reps + 1):
            for strategy in strategies:
                run_counter += 1
                strategy = strategy.strip()

                logger.info(f"\n>>> RUN {run_counter}/{total_runs}: {strategy.upper()} (rep {rep}/{args.reps})")

                result = run_single_strategy(
                    package_name=package_name,
                    strategy=strategy,
                    timeout_seconds=args.timeout,
                    device_id=args.device
                )
                result["repetition"] = rep
                results.append(result)

                # Pause between runs
                if run_counter < total_runs:
                    logger.info("Waiting 5 seconds before next run...")
                    time.sleep(5)
    finally:
        # Always uninstall app at the end
        logger.info(f"Cleanup: uninstalling {package_name}")
        uninstall_app(package_name, args.device)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Strategy':<12} {'Rep':<5} {'Status':<10} {'States':<8} {'Actions':<8} {'Time':<8}")
    print("-" * 60)

    for r in results:
        strategy = r.get("strategy", "?")
        rep = r.get("repetition", "-")
        status = r.get("status", "?")
        states = r.get("states_discovered", "-")
        actions = r.get("total_actions", "-")
        time_s = r.get("execution_time", "-")
        print(f"{strategy:<12} {rep:<5} {status:<10} {states:<8} {actions:<8} {time_s:<8}")

    print("=" * 60)

    # Aggregate stats per strategy
    if args.reps > 1:
        print("\nAGGREGATE BY STRATEGY (mean ± std):")
        print("-" * 60)
        for strategy in strategies:
            strategy = strategy.strip()
            strategy_results = [r for r in results if r.get("strategy") == strategy and r.get("status") == "completed"]
            if strategy_results:
                states_list = [r.get("states_discovered", 0) for r in strategy_results]
                actions_list = [r.get("total_actions", 0) for r in strategy_results]
                time_list = [r.get("execution_time", 0) for r in strategy_results]

                import statistics
                states_mean = statistics.mean(states_list)
                actions_mean = statistics.mean(actions_list)
                time_mean = statistics.mean(time_list)

                if len(states_list) > 1:
                    states_std = statistics.stdev(states_list)
                    actions_std = statistics.stdev(actions_list)
                    time_std = statistics.stdev(time_list)
                    print(f"  {strategy:<10}: States={states_mean:.1f}±{states_std:.1f}, Actions={actions_mean:.1f}±{actions_std:.1f}, Time={time_mean:.1f}±{time_std:.1f}s")
                else:
                    print(f"  {strategy:<10}: States={states_mean:.1f}, Actions={actions_mean:.1f}, Time={time_mean:.1f}s")

    print("=" * 60 + "\n")

    # Save results
    import json
    results_dir = Path(__file__).parent / "test_results"
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"simple_test_{timestamp}.json"

    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": timestamp,
            "apk_path": apk_path,
            "package_name": package_name,
            "timeout": args.timeout,
            "repetitions": args.reps,
            "strategies": strategies,
            "device": args.device,
            "total_runs": total_runs,
            "results": results
        }, f, indent=2)

    print(f"Results saved to: {results_file}")


if __name__ == "__main__":
    main()
