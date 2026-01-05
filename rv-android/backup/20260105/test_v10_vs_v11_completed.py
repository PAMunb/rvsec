#!/usr/bin/env python3
"""
V10 vs V11 Comparison Test - Completed Apps Only

Tests only the 23 apps that completed V10 baseline, comparing with V11.
Uses 60s timeout per app for faster completion.
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
                package = line.split("'")[1]
                return package
        return None
    except Exception as e:
        logger.error(f"Failed to extract package from {apk_path}: {e}")
        return None


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


def run_test(package: str, prompt_version: str, timeout: int = 60) -> dict:
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


def get_apk_path(package: str) -> Path:
    """Find APK path for a package."""
    for app_dir in DATASET_DIR.iterdir():
        if not app_dir.is_dir():
            continue

        apk_files = list(app_dir.glob("*.apk"))
        if not apk_files:
            continue

        apk_package = get_package_name(apk_files[0])
        if apk_package == package:
            return apk_files[0]

    return None


def main():
    """Main test execution."""

    logger.info("="*80)
    logger.info("V10 VS V11 COMPARISON TEST - COMPLETED APPS ONLY")
    logger.info("="*80)

    # Load previous results
    with open('/tmp/dataset_v10_vs_v11_progress.json', 'r') as f:
        previous_results = json.load(f)

    # Get apps that completed V10
    completed_v10 = [r for r in previous_results['v10_results'] if r.get('status') == 'completed']
    packages = [r['package'] for r in completed_v10]

    logger.info(f"\nFound {len(packages)} apps with V10 baseline")
    logger.info(f"Estimated time: {len(packages)} minutes (60s per app)")

    # Results storage
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_apks': len(packages),
        'test_timeout': 60,
        'v10_results': completed_v10,  # Reuse existing V10 results
        'v11_results': []
    }

    # Test with V11
    logger.info("\n" + "="*80)
    logger.info("TESTING WITH V11 (ENHANCED UI COVERAGE)")
    logger.info("="*80)

    switch_prompt_version("v11")

    for i, package in enumerate(packages, 1):
        logger.info(f"\n[{i}/{len(packages)}] Testing {package} with V11")

        # Find APK
        apk_path = get_apk_path(package)
        if not apk_path:
            logger.error(f"APK not found for {package}")
            results['v11_results'].append({
                'package': package,
                'status': 'apk_not_found'
            })
            continue

        # Install APK
        if not install_apk(apk_path, package):
            logger.error(f"Skipping {package} - installation failed")
            results['v11_results'].append({
                'package': package,
                'status': 'install_failed'
            })
            continue

        # Run test
        result = run_test(package, "v11", timeout=60)
        results['v11_results'].append(result)

        # Save intermediate results
        with open('/tmp/v10_vs_v11_completed_progress.json', 'w') as f:
            json.dump(results, f, indent=2)

    # Save final results
    final_path = f"/tmp/v10_vs_v11_completed_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(final_path, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETED")
    logger.info("="*80)
    logger.info(f"Results saved to: {final_path}")
    logger.info(f"V10 (reused): {len(results['v10_results'])}")
    logger.info(f"V11 completed: {len([r for r in results['v11_results'] if r.get('status') == 'completed'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
