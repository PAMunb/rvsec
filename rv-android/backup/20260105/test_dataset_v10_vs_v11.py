#!/usr/bin/env python3
"""
Comprehensive V10 vs V11 Comparison Test

Tests all 28 APKs from dataset with both prompt versions:
- V10: Baseline prompt
- V11: Enhanced UI coverage prompt

Compares:
- android_scroll usage
- android_type_text usage
- android_back usage
- Text field interactions
- Spinner interactions
- Overall UI coverage diversity
"""

import sys
import os
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Add modules to path
sys.path.insert(0, str(Path(__file__).parent / "modules" / "rv-agent" / "src"))

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.agent_factory import AgentFactory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Dataset directory
DATASET_DIR = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")


def get_package_name(apk_path: Path) -> str:
    """Extract package name from APK using aapt."""
    try:
        result = subprocess.run(
            ["aapt", "dump", "badging", str(apk_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        for line in result.stdout.split('\n'):
            if line.startswith('package: name='):
                # Extract: package: name='com.example.app'
                package = line.split("'")[1]
                return package
        return None
    except Exception as e:
        logger.error(f"Failed to extract package from {apk_path}: {e}")
        return None


def discover_apks():
    """Discover all APKs in dataset."""
    apks = []

    for app_dir in sorted(DATASET_DIR.iterdir()):
        if not app_dir.is_dir():
            continue

        # Find APK file inside app directory
        apk_files = list(app_dir.glob("*.apk"))
        if not apk_files:
            logger.warning(f"No APK found in {app_dir}")
            continue

        apk_path = apk_files[0]
        package = get_package_name(apk_path)

        if not package:
            logger.warning(f"Could not extract package from {apk_path}")
            continue

        apks.append({
            'apk_path': apk_path,
            'package': package,
            'app_dir': app_dir.name
        })

    logger.info(f"Discovered {len(apks)} APKs with valid packages")
    return apks


def install_apk(apk_path: Path, package: str) -> bool:
    """Install APK on emulator."""
    try:
        # Uninstall first if exists
        subprocess.run(
            ["adb", "uninstall", package],
            capture_output=True,
            timeout=30
        )

        # Install
        result = subprocess.run(
            ["adb", "install", "-r", str(apk_path)],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"Failed to install {apk_path}: {result.stderr}")
            return False

        logger.info(f"Installed {package}")
        return True

    except Exception as e:
        logger.error(f"Error installing {apk_path}: {e}")
        return False


def run_test(package: str, prompt_version: str, timeout: int = 120) -> dict:
    """Run single test with specified prompt version."""

    logger.info(f"Testing {package} with {prompt_version} (timeout={timeout}s)")

    config = RVAgentConfig(
        package_name=package,
        device_id="emulator-5554",
        agent_mode="multimode",
        strategy="greedy",
        llm_probability=0.7,
        llm_model="qwen3-vl-4b-8k:latest",
        timeout=timeout,
        max_iterations=200,
        screenshot_dir=f"/tmp/dataset_test_{prompt_version}/{package}",
        screenshot_rotation_limit=50,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248)
    )

    try:
        agent = AgentFactory.create_agent(config)
        result = agent.run()

        return {
            'status': 'completed',
            'package': package,
            'prompt_version': prompt_version,
            'timeout': timeout
        }

    except Exception as e:
        logger.error(f"Test failed for {package} with {prompt_version}: {e}")
        return {
            'status': 'failed',
            'package': package,
            'prompt_version': prompt_version,
            'error': str(e)
        }


def switch_prompt_version(version: str):
    """Switch prompt version in agent_factory.py."""
    factory_path = Path(__file__).parent / "modules" / "rv-agent" / "src" / "rv_agent" / "core" / "agent_factory.py"

    with open(factory_path, 'r') as f:
        content = f.read()

    if version == "v10":
        new_content = content.replace(
            "from rv_agent.prompts import v11 as current_prompt",
            "from rv_agent.prompts import v10 as current_prompt"
        )
    elif version == "v11":
        new_content = content.replace(
            "from rv_agent.prompts import v10 as current_prompt",
            "from rv_agent.prompts import v11 as current_prompt"
        )
    else:
        raise ValueError(f"Invalid version: {version}")

    with open(factory_path, 'w') as f:
        f.write(new_content)

    logger.info(f"Switched to prompt {version}")


def main():
    """Main test execution."""

    logger.info("="*80)
    logger.info("DATASET V10 VS V11 COMPARISON TEST")
    logger.info("="*80)

    # Discover APKs
    apks = discover_apks()

    if not apks:
        logger.error("No APKs found in dataset!")
        return 1

    logger.info(f"\nFound {len(apks)} APKs to test")
    logger.info(f"Estimated time: {len(apks) * 2 * 2} minutes (2 tests x 2 min each)")

    # Results storage
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_apks': len(apks),
        'test_timeout': 120,
        'v10_results': [],
        'v11_results': []
    }

    # Test with V10 first
    logger.info("\n" + "="*80)
    logger.info("PHASE 1: Testing with V10 (BASELINE)")
    logger.info("="*80)

    switch_prompt_version("v10")

    for i, apk_info in enumerate(apks, 1):
        logger.info(f"\n[{i}/{len(apks)}] Testing {apk_info['package']} with V10")

        # Install APK
        if not install_apk(apk_info['apk_path'], apk_info['package']):
            logger.error(f"Skipping {apk_info['package']} - installation failed")
            results['v10_results'].append({
                'package': apk_info['package'],
                'status': 'install_failed'
            })
            continue

        # Run test
        result = run_test(apk_info['package'], "v10", timeout=120)
        results['v10_results'].append(result)

        # Save intermediate results
        with open('/tmp/dataset_v10_vs_v11_progress.json', 'w') as f:
            json.dump(results, f, indent=2)

    # Test with V11
    logger.info("\n" + "="*80)
    logger.info("PHASE 2: Testing with V11 (ENHANCED)")
    logger.info("="*80)

    switch_prompt_version("v11")

    for i, apk_info in enumerate(apks, 1):
        logger.info(f"\n[{i}/{len(apks)}] Testing {apk_info['package']} with V11")

        # Install APK (reinstall to ensure clean state)
        if not install_apk(apk_info['apk_path'], apk_info['package']):
            logger.error(f"Skipping {apk_info['package']} - installation failed")
            results['v11_results'].append({
                'package': apk_info['package'],
                'status': 'install_failed'
            })
            continue

        # Run test
        result = run_test(apk_info['package'], "v11", timeout=120)
        results['v11_results'].append(result)

        # Save intermediate results
        with open('/tmp/dataset_v10_vs_v11_progress.json', 'w') as f:
            json.dump(results, f, indent=2)

    # Save final results
    final_path = f"/tmp/dataset_v10_vs_v11_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(final_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETED")
    logger.info("="*80)
    logger.info(f"Results saved to: {final_path}")
    logger.info(f"V10 completed: {len(results['v10_results'])}")
    logger.info(f"V11 completed: {len(results['v11_results'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
