#!/usr/bin/env python3
"""
Test single app (ar.rulosoft.mimanganu) with V12 and automatic permissions.
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

# Test configuration
PACKAGE = "ar.rulosoft.mimanganu"
APK_PATH = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/ar.rulosoft.mimanganu_75.apk/ar.rulosoft.mimanganu_75.apk"
DEVICE_ID = "emulator-5554"


def install_apk_with_permissions(apk_path: str, package: str) -> bool:
    """Install APK with automatic permission grants."""
    try:
        logger.info(f"Uninstalling {package} if exists...")
        subprocess.run(
            ["adb", "-s", DEVICE_ID, "uninstall", package],
            capture_output=True,
            timeout=30
        )

        logger.info(f"Installing {apk_path} with auto-grant permissions (-g flag)...")
        result = subprocess.run(
            ["adb", "-s", DEVICE_ID, "install", "-g", "-r", apk_path],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            logger.error(f"Failed to install: {result.stderr}")
            return False

        logger.info(f"✅ Installed {package} with all permissions granted")
        return True

    except Exception as e:
        logger.error(f"Error installing: {e}")
        return False


def grant_additional_permissions(package: str):
    """Grant any additional runtime permissions that might be needed."""
    permissions = [
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.CAMERA",
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.RECORD_AUDIO",
        "android.permission.READ_CONTACTS",
        "android.permission.WRITE_CONTACTS",
        "android.permission.READ_PHONE_STATE",
        "android.permission.CALL_PHONE",
    ]

    logger.info("Granting additional runtime permissions...")
    for permission in permissions:
        try:
            subprocess.run(
                ["adb", "-s", DEVICE_ID, "shell", "pm", "grant", package, permission],
                capture_output=True,
                timeout=5
            )
        except:
            pass  # Ignore if permission doesn't apply

    logger.info("✅ Additional permissions granted")


def run_test():
    """Run test with V12 and automatic permissions."""

    logger.info("="*80)
    logger.info(f"TESTING: {PACKAGE}")
    logger.info("Configuration:")
    logger.info("  - Prompt: V12")
    logger.info("  - Permissions: Auto-granted via adb install -g")
    logger.info("  - Mode: multimode")
    logger.info("  - Strategy: greedy")
    logger.info("  - Timeout: 180s")
    logger.info("="*80)
    logger.info("")

    # Install with permissions
    if not install_apk_with_permissions(APK_PATH, PACKAGE):
        logger.error("❌ Installation failed")
        return {
            'status': 'install_failed',
            'package': PACKAGE,
            'error': 'Installation failed'
        }

    # Grant additional permissions
    grant_additional_permissions(PACKAGE)

    # Configure agent
    config = RVAgentConfig(
        package_name=PACKAGE,
        device_id=DEVICE_ID,
        agent_mode="multimode",
        strategy="greedy",
        llm_probability=0.7,
        llm_model="qwen3-vl-4b-8k:latest",
        timeout=180,
        max_iterations=200,
        screenshot_dir=f"/tmp/test_single_app_v12/{PACKAGE}",
        screenshot_rotation_limit=50,
        device_dimensions=(1080, 1920),
        optimized_dimensions=(704, 1248)
    )

    try:
        logger.info("Creating agent...")
        agent = AgentFactory.create_agent(config)

        logger.info("Starting exploration...")
        result = agent.run()

        logger.info("="*80)
        logger.info("✅ TEST COMPLETED SUCCESSFULLY")
        logger.info("="*80)

        return {
            'status': 'completed',
            'package': PACKAGE,
            'prompt_version': 'v12',
            'permissions': 'auto-granted'
        }

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return {
            'status': 'failed',
            'package': PACKAGE,
            'prompt_version': 'v12',
            'error': str(e)
        }


def main():
    result = run_test()

    # Save result
    output_path = f"/tmp/test_single_app_v12_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    logger.info(f"\nResult saved to: {output_path}")
    logger.info(f"Status: {result['status']}")

    return 0 if result['status'] == 'completed' else 1


if __name__ == "__main__":
    sys.exit(main())
