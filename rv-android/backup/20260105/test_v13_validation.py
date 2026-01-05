#!/usr/bin/env python3
"""
V13 Validation Test - 5 Representative Apps
============================================

Tests V13 with:
1. cryptoapp - Baseline
2. ifixit - V11 outlier (180 actions, 13% LLM)
3. dicer - V11 outlier (193 actions, 12% LLM)
4. leafpicrevived - Normal app (~40 actions)
5. towercollector - Normal app (~35 actions)

Success criteria:
- Outliers (ifixit, dicer) with >50% LLM (NOT 13%)
- States/actions ratio >0.15 (max 6.7 actions/state)
- Tokens/action <5,000
- UI coverage metrics >0
"""

import json
import logging
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/v13_validation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Dataset directory
DATASET_DIR = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")

# Test apps as specified in plan
TEST_APPS = [
    "br.unb.cic.cryptoapp",                      # Baseline
    "com.dozuki.ifixit",                         # V11 outlier (180 actions, 13% LLM)
    "org.secuso.privacyfriendlydicer",           # V11 outlier (193 actions, 12% LLM)
    "com.alienpants.leafpicrevived",             # Normal (~40 actions)
    "info.zamojski.soft.towercollector",         # Normal (~35 actions)
]

# Test configuration
TEST_CONFIG = {
    "timeout": 300,  # 5 minutes per app
    "device_id": "emulator-5554",
    "agent_mode": "multimode",
    "strategy": "greedy",
    "llm_model": "qwen3-vl-4b-8k:latest",
    "llm_probability": 0.7,
    "device_dimensions": (1080, 1920),
    "optimized_dimensions": (704, 1248),
}


def extract_comprehensive_metrics(
    results: Dict[str, Any],
    ui_coverage_stats: Dict[str, Any],
    short_term_stats: Dict[str, Any] = None,
    long_term_stats: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Extract comprehensive metrics (adapted from test_prompt_comparison_complete.py)."""

    # Handle None values
    short_term_stats = short_term_stats or {}
    long_term_stats = long_term_stats or {}

    total_actions = results.get("total_actions", 0)
    llm_decisions = results.get("llm_decisions", 0)
    algorithm_decisions = results.get("algorithm_decisions", 0)
    execution_time = results.get("execution_time_s", 0.0)

    # Calculate percentages
    llm_pct = (llm_decisions / total_actions * 100) if total_actions > 0 else 0
    algorithm_pct = (algorithm_decisions / total_actions * 100) if total_actions > 0 else 0

    # LLM metrics
    tokens_input = results.get("llm_tokens_input", 0)
    tokens_output = results.get("llm_tokens_output", 0)
    tokens_total = tokens_input + tokens_output
    llm_time_ms = results.get("llm_time_ms", 0.0)
    llm_time_s = llm_time_ms / 1000.0

    # Exploration metrics
    unique_states = results.get("unique_states", 0)
    total_transitions = results.get("total_transitions", 0)

    # Performance metrics
    exec_minutes = execution_time / 60.0 if execution_time > 0 else 0.001
    actions_per_minute = total_actions / exec_minutes if exec_minutes > 0 else 0
    tokens_per_action = tokens_total / total_actions if total_actions > 0 else 0
    states_actions_ratio = unique_states / total_actions if total_actions > 0 else 0

    return {
        "actions": {
            "total": total_actions,
            "by_decisor": {
                "llm": llm_decisions,
                "algorithm": algorithm_decisions
            },
            "decisor_percentage": {
                "llm": llm_pct,
                "algorithm": algorithm_pct
            }
        },
        "decisor": {
            "llm_count": llm_decisions,
            "algorithm_count": algorithm_decisions,
            "llm_percentage": llm_pct,
            "algorithm_percentage": algorithm_pct
        },
        "ui_coverage": {
            "total_unique_elements": ui_coverage_stats.get("total_unique_elements", 0),
            "total_interactions": ui_coverage_stats.get("total_interactions", 0),
            "average_interactions_per_element": ui_coverage_stats.get("average_interactions_per_element", 0.0),
            "total_screens": ui_coverage_stats.get("total_screens", 0)
        },
        "exploration": {
            "unique_states": unique_states,
            "total_transitions": total_transitions,
            "states_per_minute": unique_states / exec_minutes if exec_minutes > 0 else 0,
            "transitions_per_state": total_transitions / unique_states if unique_states > 0 else 0
        },
        "llm": {
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "tokens_total": tokens_total,
            "time_ms": llm_time_ms,
            "time_seconds": llm_time_s,
            "average_tokens_per_call": tokens_total / llm_decisions if llm_decisions > 0 else 0,
            "tokens_per_second": tokens_total / llm_time_s if llm_time_s > 0 else 0,
            "calls_total": llm_decisions
        },
        "temporal": {
            "execution_time_s": execution_time
        },
        "performance": {
            "actions_per_minute": actions_per_minute,
            "tokens_per_action": tokens_per_action,
            "states_actions_ratio": states_actions_ratio
        },
        "short_term_memory": {
            "iteration_count": short_term_stats.get("iteration_count", 0)
        },
        "long_term_memory": {
            "total_states": long_term_stats.get("total_states", 0)
        },
        "metadata": {
            "status": results.get("status", "unknown"),
            "iterations": results.get("iterations", 0),
            "prompt_version": "v13"
        }
    }


def find_apk_for_package(package_name: str) -> Path:
    """Find APK file for given package name in dataset."""
    for app_dir in DATASET_DIR.iterdir():
        if not app_dir.is_dir():
            continue

        apk_files = list(app_dir.glob("*.apk"))
        if not apk_files:
            continue

        apk_path = apk_files[0]

        # Quick check: if package name is in directory name, likely match
        if package_name.split('.')[-1] in app_dir.name.lower():
            return apk_path

    return None


def install_apk(apk_path: Path, package: str) -> bool:
    """Install APK on emulator (adapted from test_v12_complete_180s.py)."""
    try:
        # Uninstall first if exists
        subprocess.run(
            ["adb", "uninstall", package],
            capture_output=True,
            timeout=30
        )

        # Install with permissions
        result = subprocess.run(
            ["adb", "install", "-r", "-g", str(apk_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"Failed to install {apk_path}: {result.stderr}")
            return False

        logger.info(f"✅ Installed {package}")
        return True

    except Exception as e:
        logger.error(f"Error installing {apk_path}: {e}")
        return False


def test_single_app(app_package: str, results_dir: Path) -> Dict[str, Any]:
    """Test single app with V13."""
    logger.info(f"\n{'='*80}")
    logger.info(f"TESTING: {app_package}")
    logger.info(f"{'='*80}")

    # Find and install APK if not cryptoapp (assumed pre-installed)
    if app_package != "br.unb.cic.cryptoapp":
        apk_path = find_apk_for_package(app_package)
        if apk_path:
            logger.info(f"Found APK: {apk_path}")
            if not install_apk(apk_path, app_package):
                logger.error(f"Failed to install {app_package}")
                return {
                    "app_package": app_package,
                    "status": "installation_failed",
                    "all_checks_passed": False
                }
        else:
            logger.warning(f"APK not found for {app_package} - assuming pre-installed")

    config = RVAgentConfig(
        package_name=app_package,
        timeout=TEST_CONFIG["timeout"],
        prompt_version="v13",  # <<< Test V13
        agent_mode=TEST_CONFIG["agent_mode"],
        strategy=TEST_CONFIG["strategy"],
        llm_model=TEST_CONFIG["llm_model"],
        llm_probability=TEST_CONFIG["llm_probability"],
        device_dimensions=TEST_CONFIG["device_dimensions"],
        optimized_dimensions=TEST_CONFIG["optimized_dimensions"],
        screenshot_dir=f"/tmp/v13_validation_{app_package}",
        screenshot_rotation_limit=50
    )

    try:
        # Create and run agent
        logger.info("Creating agent with V13...")
        agent = AgentFactory.create_agent(config=config)

        logger.info("Starting exploration...")
        start_time = time.time()
        results = agent.run()
        elapsed = time.time() - start_time

        # Extract memory stats using new facade
        memory_stats = results.get("memory_stats", {})
        ui_coverage_stats = memory_stats.get("ui_coverage", {})
        short_term_stats = memory_stats.get("short_term", {})
        long_term_stats = memory_stats.get("long_term", {})

        # Extract comprehensive metrics
        metrics = extract_comprehensive_metrics(
            results,
            ui_coverage_stats,
            short_term_stats,
            long_term_stats
        )

        # Add app info
        metrics["app_package"] = app_package

        # Extract key values for validation
        total_actions = metrics["actions"]["total"]
        llm_percentage = metrics["decisor"]["llm_percentage"]
        states_actions_ratio = metrics["performance"]["states_actions_ratio"]
        tokens_per_action = metrics["performance"]["tokens_per_action"]
        ui_elements = metrics["ui_coverage"]["total_unique_elements"]

        # Validation checks
        validation = {
            "llm_percentage_ok": llm_percentage > 50,  # Must be >50%, not 13%
            "ratio_ok": states_actions_ratio > 0.15,   # Max 6.7 actions/state
            "tokens_ok": tokens_per_action < 5000,     # <5k tokens/action
            "ui_coverage_ok": ui_elements > 0
        }

        metrics["validation"] = validation
        metrics["all_checks_passed"] = all(validation.values())

        # Save individual result
        result_file = results_dir / f"v13_{app_package}.json"
        with open(result_file, 'w') as f:
            json.dump(metrics, f, indent=2)

        # Log summary
        logger.info(f"\n{'='*80}")
        logger.info("TEST COMPLETED")
        logger.info(f"{'='*80}")
        logger.info(f"⏱️  Duration: {elapsed:.1f}s")
        logger.info(f"📊 Total actions: {total_actions}")
        logger.info(f"🧠 LLM: {llm_percentage:.1f}% ({metrics['actions']['by_decisor']['llm']} decisions)")
        logger.info(f"⚙️  Algorithm: {metrics['decisor']['algorithm_percentage']:.1f}% ({metrics['actions']['by_decisor']['algorithm']} decisions)")
        logger.info(f"🗺️  States: {metrics['exploration']['unique_states']}")
        logger.info(f"📈 Ratio: {states_actions_ratio:.3f} (states/actions)")
        logger.info(f"💬 Tokens/action: {tokens_per_action:.0f}")
        logger.info(f"🎯 UI Elements: {ui_elements}")
        logger.info(f"\n{'='*80}")
        logger.info(f"VALIDATION: {'✅ PASSED' if metrics['all_checks_passed'] else '❌ FAILED'}")
        logger.info(f"{'='*80}")

        return metrics

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return {
            "app_package": app_package,
            "status": "error",
            "error": str(e),
            "all_checks_passed": False
        }


def main():
    """Run V13 validation test."""
    logger.info("\n" + "="*80)
    logger.info("V13 VALIDATION TEST - 5 REPRESENTATIVE APPS")
    logger.info("="*80)
    logger.info(f"Apps: {len(TEST_APPS)}")
    logger.info(f"Timeout: {TEST_CONFIG['timeout']}s per app")
    logger.info(f"Prompt: v13")

    # Create results directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(f"results/v13_validation_{timestamp}")
    results_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Results: {results_dir}")

    # Run tests
    all_results = []
    for app_package in TEST_APPS:
        result = test_single_app(app_package, results_dir)
        all_results.append(result)
        time.sleep(2)  # Small pause between apps

    # Generate summary
    logger.info("\n" + "="*80)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*80)

    passed_count = sum(1 for r in all_results if r.get("all_checks_passed", False))
    failed_count = len(all_results) - passed_count

    logger.info(f"Total apps: {len(all_results)}")
    logger.info(f"Passed: {passed_count}")
    logger.info(f"Failed: {failed_count}")

    # Check outliers specifically
    logger.info("\n" + "-"*80)
    logger.info("OUTLIER CHECK (ifixit, dicer)")
    logger.info("-"*80)

    for result in all_results:
        if "ifixit" in result["app_package"] or "dicer" in result["app_package"]:
            app_name = result["app_package"].split(".")[-1]
            llm_pct = result.get("llm_percentage", 0)
            ratio = result.get("states_actions_ratio", 0)

            status = "✅" if result.get("all_checks_passed", False) else "❌"
            logger.info(f"{status} {app_name}:")
            logger.info(f"   LLM: {llm_pct:.1f}% (need >50%)")
            logger.info(f"   Ratio: {ratio:.3f} (need >0.15)")

    # Save summary
    summary = {
        "test_date": datetime.now().isoformat(),
        "prompt_version": "v13",
        "total_apps": len(all_results),
        "passed": passed_count,
        "failed": failed_count,
        "results": all_results
    }

    summary_file = results_dir / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    logger.info(f"\n✅ Summary saved: {summary_file}")

    # Final verdict
    logger.info("\n" + "="*80)
    if passed_count == len(all_results):
        logger.info("✅ V13 VALIDATION: PASSED")
        logger.info("All apps met success criteria!")
    else:
        logger.warning(f"⚠️  V13 VALIDATION: PARTIAL ({passed_count}/{len(all_results)} passed)")
        logger.warning("Some apps did not meet all criteria")
    logger.info("="*80)

    return 0 if passed_count == len(all_results) else 1


if __name__ == "__main__":
    sys.exit(main())
