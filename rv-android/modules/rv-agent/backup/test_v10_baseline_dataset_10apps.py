#!/usr/bin/env python3
"""
V10 Baseline Test with Correct Dataset - 10 Apps

Tests 10 diverse Android applications from the validated test dataset
to establish baseline performance metrics for V10 simplified prompt with
state tracking and transition fixes.

Dataset: /home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/
- Each app directory contains: screenshots, dumps, static analysis, APK

Test Configuration:
- Prompt: V10 Simplified (minimal context, stateless architecture)
- Model: qwen3-vl:4b (vision-language model)
- Duration: 120 seconds (2 minutes) per app
- Temperature: 0.0 (deterministic)

Metrics Tracked:
- Iterations performed
- Unique states discovered
- State transitions recorded (NOW FIXED!)
- Tool call success rate
- LLM response times
- Screenshot optimization stats
- Execution time
- Loop detection

Each test:
1. Uninstalls existing app installation
2. Installs APK from dataset via ADB
3. Launches RVAgent exploration
4. Captures detailed logs
5. Saves individual results to JSON
6. Generates aggregate summary
"""

import os
import sys
import json
import time
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Configure logging for detailed analysis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Test Configuration
DATASET_DIR = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
TIMEOUT_PER_APP = 120  # 2 minutes per app
MODEL_NAME = "qwen3-vl:4b"
PROMPT_VERSION = "v10"

# Selected apps from validated dataset (diverse types, with static analysis when available)
TEST_APPS = [
    {
        "name": "CryptoApp",
        "app_dir": "cryptoapp.apk",
        "apk": "cryptoapp.apk",
        "type": "encryption",
        "has_static": True
    },
    {
        "name": "HashPass",
        "app_dir": "byrne.utilities.hashpass_2.apk",
        "apk": "byrne.utilities.hashpass_2.apk",
        "type": "password_utility",
        "has_static": True
    },
    {
        "name": "DNSHero",
        "app_dir": "com.gianlu.dnshero_40.apk",
        "apk": "com.gianlu.dnshero_40.apk",
        "type": "network_tool",
        "has_static": True
    },
    {
        "name": "HourlyReminder",
        "app_dir": "com.github.axet.hourlyreminder_476.apk",
        "apk": "com.github.axet.hourlyreminder_476.apk",
        "type": "productivity",
        "has_static": True
    },
    {
        "name": "LeafPic",
        "app_dir": "com.alienpants.leafpicrevived_24.apk",
        "apk": "com.alienpants.leafpicrevived_24.apk",
        "type": "gallery",
        "has_static": False
    },
    {
        "name": "RSSReader",
        "app_dir": "livio.rssreader_101.apk",
        "apk": "livio.rssreader_101.apk",
        "type": "news_reader",
        "has_static": True
    },
    {
        "name": "TowerCollector",
        "app_dir": "info.zamojski.soft.towercollector_2140302.apk",
        "apk": "info.zamojski.soft.towercollector_2140302.apk",
        "type": "network_tool",
        "has_static": True
    },
    {
        "name": "PrivacyFriendlyLudo",
        "app_dir": "org.secuso.privacyfriendlyludo_5.apk",
        "apk": "org.secuso.privacyfriendlyludo_5.apk",
        "type": "game",
        "has_static": True
    },
    {
        "name": "SimpleNotes",
        "app_dir": "com.rafapps.simplenotes_7.apk",
        "apk": "com.rafapps.simplenotes_7.apk",
        "type": "productivity",
        "has_static": False
    },
    {
        "name": "HexGame",
        "app_dir": "com.sam.hex_16.apk",
        "apk": "com.sam.hex_16.apk",
        "type": "game",
        "has_static": True
    }
]


def run_adb_command(command: List[str]) -> tuple[bool, str]:
    """
    Execute ADB command and return success status and output.

    Args:
        command: ADB command as list of strings

    Returns:
        Tuple of (success, output)
    """
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def extract_package_name(apk_path: Path) -> Optional[str]:
    """
    Extract package name from APK using aapt.

    Args:
        apk_path: Path to APK file

    Returns:
        Package name or None if extraction fails
    """
    try:
        result = subprocess.run(
            ["aapt", "dump", "badging", str(apk_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        for line in result.stdout.split('\n'):
            if line.startswith("package: name="):
                # Extract: package: name='com.example' versionCode='1' ...
                package = line.split("name='")[1].split("'")[0]
                return package
        return None
    except Exception as e:
        logger.error(f"Failed to extract package name: {e}")
        return None


def uninstall_app(package: str) -> bool:
    """
    Uninstall app if installed.

    Args:
        package: Package name to uninstall

    Returns:
        True if successful or app not installed
    """
    logger.info(f"   Uninstalling {package}...")
    success, output = run_adb_command(["adb", "uninstall", package])

    if success or "not installed" in output.lower():
        logger.info(f"   ✅ Uninstall successful")
        return True
    else:
        logger.warning(f"   ⚠️  Uninstall failed: {output}")
        return False


def install_apk(apk_path: Path) -> bool:
    """
    Install APK via ADB.

    Args:
        apk_path: Path to APK file

    Returns:
        True if installation successful
    """
    logger.info(f"   Installing {apk_path.name}...")
    success, output = run_adb_command(["adb", "install", "-r", str(apk_path)])

    if success and "Success" in output:
        logger.info(f"   ✅ Installation successful")
        return True
    else:
        logger.error(f"   ❌ Installation failed: {output}")
        return False


def run_rvagent_test(app_config: Dict) -> Dict:
    """
    Run RVAgent test for a single app.

    Args:
        app_config: App configuration dictionary

    Returns:
        Test results dictionary
    """
    from rv_agent.core.device_interface import DeviceInterface
    from rv_agent.core.rv_agent import RVAgent
    from rv_agent.config.agent_config import RVAgentConfig
    from rv_agent.prompts.v10 import SYSTEM_PROMPT

    app_name = app_config["name"]
    app_dir = DATASET_DIR / app_config["app_dir"]
    apk_path = app_dir / app_config["apk"]

    logger.info(f"\n{'='*80}")
    logger.info(f"  Testing: {app_name}")
    logger.info(f"  APK: {apk_path}")
    logger.info(f"  Has Static Analysis: {app_config['has_static']}")
    logger.info(f"{'='*80}\n")

    # Extract package name from APK
    package = extract_package_name(apk_path)
    if not package:
        logger.error(f"❌ Failed to extract package name from {apk_path}")
        return {
            "app": app_name,
            "type": app_config["type"],
            "model": MODEL_NAME,
            "prompt_version": PROMPT_VERSION,
            "timeout": TIMEOUT_PER_APP,
            "success": False,
            "error": "Failed to extract package name",
            "metrics": {
                "iterations": 0,
                "unique_states": 0,
                "transitions": 0,
                "potential_loop": False,
                "execution_time_s": 0
            }
        }

    logger.info(f"   Package: {package}")

    start_time = time.time()

    try:
        # Connect to device
        logger.info("📱 Connecting to device...")
        device = DeviceInterface("emulator-5554")
        logger.info(f"Connected to device emulator-5554")

        # Disable soft keyboard
        logger.info("Disabling Android soft keyboard via ADB")
        run_adb_command([
            "adb", "shell", "settings", "put", "secure",
            "show_ime_with_hard_keyboard", "0"
        ])
        logger.info("✅ Soft keyboard disabled successfully")

        # Create RVAgent config
        logger.info("⚙️  Creating RVAgent config...")
        config = RVAgentConfig(
            package_name=package,
            device_id="emulator-5554",
            strategy="dfs",
            timeout=TIMEOUT_PER_APP,
            max_iterations=100,
            llm_model=MODEL_NAME,
            llm_temperature=0.0,
            llm_top_p=0.9,
            llm_top_k=40
        )

        # Create and run agent
        logger.info(f"🤖 Creating RVAgent with {PROMPT_VERSION} prompt...")
        agent = RVAgent(config, static_data=None, device=device)

        logger.info(f"\n🚀 Starting exploration (timeout: {TIMEOUT_PER_APP}s)...")
        logger.info("   Monitoring:")
        logger.info(f"   ✓ Tool calls generated")
        logger.info(f"   ✓ Unique states discovered")
        logger.info(f"   ✓ State transitions recorded (FIXED!)")
        logger.info(f"   ✓ No immediate loops")

        # Run exploration
        results = agent.run()

        # Collect metrics
        execution_time = time.time() - start_time

        iterations = results.get('iterations', 0)
        unique_states = results.get('unique_states', 0)
        transitions = results.get('total_transitions', 0)
        potential_loop = results.get('potential_loop', False)

        test_results = {
            "app": app_name,
            "package": package,
            "type": app_config["type"],
            "has_static_analysis": app_config["has_static"],
            "model": MODEL_NAME,
            "prompt_version": PROMPT_VERSION,
            "timeout": TIMEOUT_PER_APP,
            "success": True,
            "metrics": {
                "iterations": iterations,
                "unique_states": unique_states,
                "transitions": transitions,
                "potential_loop": potential_loop,
                "execution_time_s": execution_time
            },
            "validation": {
                "generated_actions": iterations > 0,
                "discovered_states": unique_states > 0,
                "recorded_transitions": transitions > 0,
                "no_immediate_loop": not potential_loop,
                "overall_success": iterations > 0 and unique_states > 0 and not potential_loop
            }
        }

        logger.info(f"\n{'='*80}")
        logger.info(f"  RESULTS: {app_name}")
        logger.info(f"{'='*80}\n")
        logger.info(f"Metrics:")
        logger.info(f"  Iterations: {iterations}")
        logger.info(f"  Unique States: {unique_states}")
        logger.info(f"  Transitions: {transitions} {'✅ FIXED!' if transitions > 0 else '⚠️  Still 0'}")
        logger.info(f"  Execution Time: {execution_time:.1f}s")
        logger.info(f"  Loop Detected: {'YES ❌' if potential_loop else 'NO ✅'}")

        return test_results

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"❌ Test failed for {app_name}: {e}")
        import traceback
        logger.error(traceback.format_exc())

        return {
            "app": app_name,
            "package": package,
            "type": app_config["type"],
            "has_static_analysis": app_config["has_static"],
            "model": MODEL_NAME,
            "prompt_version": PROMPT_VERSION,
            "timeout": TIMEOUT_PER_APP,
            "success": False,
            "error": str(e),
            "metrics": {
                "iterations": 0,
                "unique_states": 0,
                "transitions": 0,
                "potential_loop": False,
                "execution_time_s": execution_time
            },
            "validation": {
                "generated_actions": False,
                "discovered_states": False,
                "recorded_transitions": False,
                "no_immediate_loop": True,
                "overall_success": False
            }
        }


def main():
    """Run baseline test on all 10 apps from validated dataset."""

    logger.info("="*80)
    logger.info("  V10 BASELINE TEST - VALIDATED DATASET - 10 APPS")
    logger.info("="*80)
    logger.info("")
    logger.info(f"Configuration:")
    logger.info(f"  Dataset: {DATASET_DIR}")
    logger.info(f"  Apps: {len(TEST_APPS)}")
    logger.info(f"  Model: {MODEL_NAME}")
    logger.info(f"  Prompt: {PROMPT_VERSION} Simplified (minimal context)")
    logger.info(f"  Timeout per app: {TIMEOUT_PER_APP}s")
    logger.info(f"  Temperature: 0.0 (deterministic)")
    logger.info(f"  FIX: State transitions now tracking correctly!")
    logger.info("")

    all_results = []
    successful_tests = 0
    failed_tests = 0

    for i, app_config in enumerate(TEST_APPS, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"  APP {i}/{len(TEST_APPS)}: {app_config['name']}")
        logger.info(f"{'='*80}\n")

        # Get APK path from dataset
        app_dir = DATASET_DIR / app_config["app_dir"]
        apk_path = app_dir / app_config["apk"]

        if not apk_path.exists():
            logger.error(f"❌ APK not found: {apk_path}")
            failed_tests += 1
            continue

        # Extract and uninstall package
        package = extract_package_name(apk_path)
        if package:
            uninstall_app(package)

        # Install APK
        if not install_apk(apk_path):
            logger.error(f"❌ Failed to install {app_config['name']}")
            failed_tests += 1
            continue

        # Wait for installation to settle
        time.sleep(2)

        # Run test
        results = run_rvagent_test(app_config)
        all_results.append(results)

        if results["success"] and results["validation"]["overall_success"]:
            successful_tests += 1
        else:
            failed_tests += 1

        # Save individual results
        results_file = f"test_v10_dataset_{app_config['app_dir'].replace('.apk', '')}_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"\n💾 Results saved: {results_file}")

        # Brief pause between tests
        if i < len(TEST_APPS):
            logger.info("\n⏸️  Pausing 5 seconds before next test...")
            time.sleep(5)

    # Generate aggregate summary
    logger.info(f"\n{'='*80}")
    logger.info("  AGGREGATE SUMMARY")
    logger.info(f"{'='*80}\n")

    logger.info(f"Tests completed: {len(all_results)}/{len(TEST_APPS)}")
    logger.info(f"Successful: {successful_tests}")
    logger.info(f"Failed: {failed_tests}")
    logger.info("")

    # Calculate aggregate metrics
    total_iterations = sum(r["metrics"]["iterations"] for r in all_results)
    total_states = sum(r["metrics"]["unique_states"] for r in all_results)
    total_transitions = sum(r["metrics"]["transitions"] for r in all_results)
    avg_iterations = total_iterations / len(all_results) if all_results else 0
    avg_states = total_states / len(all_results) if all_results else 0
    avg_transitions = total_transitions / len(all_results) if all_results else 0

    logger.info("Aggregate Metrics:")
    logger.info(f"  Total Iterations: {total_iterations}")
    logger.info(f"  Total States Discovered: {total_states}")
    logger.info(f"  Total Transitions: {total_transitions} {'✅ NOW TRACKING!' if total_transitions > 0 else '⚠️  Still 0 - investigate'}")
    logger.info(f"  Avg Iterations/App: {avg_iterations:.1f}")
    logger.info(f"  Avg States/App: {avg_states:.1f}")
    logger.info(f"  Avg Transitions/App: {avg_transitions:.1f}")
    logger.info("")

    # App type analysis
    logger.info("Performance by App Type:")
    by_type = {}
    for result in all_results:
        app_type = result["type"]
        if app_type not in by_type:
            by_type[app_type] = []
        by_type[app_type].append(result)

    for app_type, results in sorted(by_type.items()):
        avg_iters = sum(r["metrics"]["iterations"] for r in results) / len(results)
        avg_states_type = sum(r["metrics"]["unique_states"] for r in results) / len(results)
        avg_trans = sum(r["metrics"]["transitions"] for r in results) / len(results)
        logger.info(f"  {app_type}: {avg_iters:.1f} iters, {avg_states_type:.1f} states, {avg_trans:.1f} trans")

    # Save aggregate results
    aggregate_results = {
        "test_name": "V10 Baseline - Validated Dataset - 10 Apps",
        "timestamp": datetime.now().isoformat(),
        "dataset_path": str(DATASET_DIR),
        "configuration": {
            "model": MODEL_NAME,
            "prompt_version": PROMPT_VERSION,
            "timeout_per_app": TIMEOUT_PER_APP,
            "num_apps": len(TEST_APPS),
            "fix_applied": "State transitions tracking corrected"
        },
        "summary": {
            "total_tests": len(all_results),
            "successful": successful_tests,
            "failed": failed_tests,
            "total_iterations": total_iterations,
            "total_states": total_states,
            "total_transitions": total_transitions,
            "avg_iterations_per_app": avg_iterations,
            "avg_states_per_app": avg_states,
            "avg_transitions_per_app": avg_transitions
        },
        "individual_results": all_results
    }

    aggregate_file = "test_v10_baseline_dataset_10apps_aggregate.json"
    with open(aggregate_file, 'w') as f:
        json.dump(aggregate_results, f, indent=2)

    logger.info(f"\n💾 Aggregate results saved: {aggregate_file}")

    logger.info(f"\n{'='*80}")
    if successful_tests == len(TEST_APPS):
        logger.info("  ✅ ALL TESTS PASSED")
    else:
        logger.info(f"  ⚠️  {failed_tests} TESTS FAILED")
    logger.info(f"{'='*80}\n")


if __name__ == "__main__":
    main()
