#!/usr/bin/env python3
"""
V11 Fair Comparison Test - 120s timeout matching V10 baseline
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


# Packages that completed V10 with 120s timeout
COMPLETED_V10_PACKAGES = [
    "ar.rulosoft.mimanganu",
    "au.com.wallaceit.reddinator",
    "biz.gyrus.yaab",
    "byrne.utilities.hashpass",
    "ca.farrelltonsolar.classic",
    "cf.playhi.freezeyou",
    "com.aidinhut.simpletextcrypt",
    "com.akop.bach",
    "com.alienpants.leafpicrevived",
    "com.crazyhitty.chdev.ks.munch",
    "com.cyanogenmod.filemanager.ics",
    "com.dougkeen.bart",
    "com.dozuki.ifixit",
    "com.gh4a",
    "com.gianlu.dnshero",
    "com.github.axet.hourlyreminder",
    "com.hwloc.lstopo",
    "com.orpheusdroid.sqliteviewer",
    "com.rafapps.simplenotes",
    "com.sam.hex",
    "br.unb.cic.cryptoapp",
    "info.zamojski.soft.towercollector",
    "livio.rssreader"
]


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


def run_test(package: str, timeout: int = 120) -> dict:
    """Run single test with V11 and 120s timeout."""

    logger.info(f"Testing {package} with V11 (timeout={timeout}s)")

    config = RVAgentConfig(
        package_name=package,
        device_id="emulator-5554",
        agent_mode="multimode",
        strategy="greedy",
        llm_probability=0.7,
        llm_model="qwen3-vl-4b-8k:latest",
        timeout=timeout,
        max_iterations=200,
        screenshot_dir=f"/tmp/dataset_test_v11_fair/{package}",
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
            'prompt_version': 'v11',
            'timeout': timeout
        }

    except Exception as e:
        logger.error(f"Test failed for {package}: {e}")
        return {
            'status': 'failed',
            'package': package,
            'prompt_version': 'v11',
            'timeout': timeout,
            'error': str(e)
        }


def main():
    """Main test execution."""

    logger.info("="*80)
    logger.info("V11 FAIR COMPARISON TEST - 120s TIMEOUT (MATCHING V10)")
    logger.info("="*80)

    logger.info(f"\nTesting {len(COMPLETED_V10_PACKAGES)} apps that completed V10")
    logger.info(f"Timeout per app: 120s (same as V10)")
    logger.info(f"Estimated time: {len(COMPLETED_V10_PACKAGES) * 2.5} minutes")

    # Results storage
    results = {
        'timestamp': datetime.now().isoformat(),
        'total_apks': len(COMPLETED_V10_PACKAGES),
        'test_timeout': 120,
        'v11_results': []
    }

    for i, package in enumerate(COMPLETED_V10_PACKAGES, 1):
        logger.info(f"\n[{i}/{len(COMPLETED_V10_PACKAGES)}] Testing {package}")

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

        # Run test with 120s timeout
        result = run_test(package, timeout=120)
        results['v11_results'].append(result)

        # Save intermediate results
        with open('/tmp/v11_fair_comparison_progress.json', 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"  Status: {result['status']}")

    # Save final results
    final_path = f"/tmp/v11_fair_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(final_path, 'w') as f:
        json.dump(results, f, indent=2)

    completed = len([r for r in results['v11_results'] if r.get('status') == 'completed'])

    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETED")
    logger.info("="*80)
    logger.info(f"Results saved to: {final_path}")
    logger.info(f"V11 completed (120s): {completed}/{len(COMPLETED_V10_PACKAGES)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
