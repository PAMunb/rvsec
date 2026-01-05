#!/usr/bin/env python3
"""
V10 Complete Dataset Test - 180s timeout per app
Uses Greedy strategy in Multimode
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

        logger.info(f"✅ Installed {package}")
        return True

    except Exception as e:
        logger.error(f"Error installing {apk_path}: {e}")
        return False


def run_test(package: str, apk_path: Path, timeout: int = 180) -> dict:
    """Run single test with V10 and specified timeout."""

    logger.info(f"{'='*80}")
    logger.info(f"Testing {package} with V10 (timeout={timeout}s)")
    logger.info(f"{'='*80}")

    config = RVAgentConfig(
        package_name=package,
        device_id="emulator-5554",
        agent_mode="multimode",
        strategy="greedy",
        llm_probability=0.7,
        llm_model="qwen3-vl-4b-8k:latest",
        timeout=timeout,
        max_iterations=200,
        screenshot_dir=f"/tmp/dataset_test_v10_180s/{package}",
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
            'prompt_version': 'v10',
            'timeout': timeout,
            'apk_path': str(apk_path)
        }

    except Exception as e:
        logger.error(f"❌ Test failed for {package}: {e}")
        return {
            'status': 'failed',
            'package': package,
            'prompt_version': 'v10',
            'timeout': timeout,
            'error': str(e),
            'apk_path': str(apk_path)
        }


def discover_apks():
    """Discover all APKs in dataset directory."""
    apks = []

    for app_dir in sorted(DATASET_DIR.iterdir()):
        if not app_dir.is_dir():
            continue

        apk_files = list(app_dir.glob("*.apk"))
        if not apk_files:
            continue

        apk_path = apk_files[0]
        package = get_package_name(apk_path)

        if package:
            apks.append({
                'package': package,
                'apk_path': apk_path,
                'app_dir': app_dir.name
            })

    return apks


def main():
    """Main test execution."""

    logger.info("="*80)
    logger.info("V10 COMPLETE DATASET TEST - 180s TIMEOUT")
    logger.info("="*80)
    logger.info("")
    logger.info("Configuration:")
    logger.info("  - Prompt: V10")
    logger.info("  - Mode: multimode")
    logger.info("  - Strategy: GREEDY")
    logger.info("  - LLM probability: 0.7")
    logger.info("  - Timeout per app: 180s")
    logger.info("  - Device: emulator-5554")
    logger.info("")

    # Discover APKs
    logger.info("Discovering APKs...")
    apks = discover_apks()

    logger.info(f"Found {len(apks)} APKs to test")
    estimated_time = len(apks) * 3.5  # 180s + overhead ≈ 3.5 min per app
    logger.info(f"Estimated total time: {estimated_time:.0f} minutes ({estimated_time/60:.1f} hours)")
    logger.info("")

    # Results storage
    results = {
        'timestamp_start': datetime.now().isoformat(),
        'total_apks': len(apks),
        'test_timeout': 180,
        'prompt_version': 'v10',
        'mode': 'multimode',
        'strategy': 'greedy',
        'results': []
    }

    # Test each APK
    for i, apk_info in enumerate(apks, 1):
        logger.info("")
        logger.info("="*80)
        logger.info(f"[{i}/{len(apks)}] Processing: {apk_info['package']}")
        logger.info(f"APK: {apk_info['app_dir']}")
        logger.info("="*80)

        # Install APK
        if not install_apk(apk_info['apk_path'], apk_info['package']):
            logger.error(f"⚠️  Skipping {apk_info['package']} - installation failed")
            results['results'].append({
                'package': apk_info['package'],
                'status': 'install_failed',
                'apk_path': str(apk_info['apk_path'])
            })

            # Save intermediate results
            with open('/tmp/v10_complete_180s_progress.json', 'w') as f:
                json.dump(results, f, indent=2)
            continue

        # Run test
        result = run_test(apk_info['package'], apk_info['apk_path'], timeout=180)
        results['results'].append(result)

        # Save intermediate results
        with open('/tmp/v10_complete_180s_progress.json', 'w') as f:
            json.dump(results, f, indent=2)

        completed = len([r for r in results['results'] if r.get('status') == 'completed'])
        failed = len([r for r in results['results'] if r.get('status') == 'failed'])
        logger.info(f"Progress: {completed} completed, {failed} failed, {i}/{len(apks)} total")

    # Save final results
    results['timestamp_end'] = datetime.now().isoformat()
    final_path = f"/tmp/v10_complete_180s_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(final_path, 'w') as f:
        json.dump(results, f, indent=2)

    completed = len([r for r in results['results'] if r.get('status') == 'completed'])
    failed = len([r for r in results['results'] if r.get('status') == 'failed'])

    logger.info("")
    logger.info("="*80)
    logger.info("TEST COMPLETED")
    logger.info("="*80)
    logger.info(f"Results saved to: {final_path}")
    logger.info(f"Completed: {completed}/{len(apks)}")
    logger.info(f"Failed: {failed}/{len(apks)}")
    logger.info(f"Success rate: {(completed/len(apks)*100):.1f}%")
    logger.info("="*80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
