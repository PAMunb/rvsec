"""
Test RV-Agent on ar.rulosoft.mimanganu with all fixes applied:
- ENTER key support for form submission
- Enhanced scroll logging
- Fixed unknown action mappings
"""

import subprocess
import time
import logging
from pathlib import Path

# Test configuration
DEVICE_ID = "emulator-5554"
PACKAGE = "ar.rulosoft.mimanganu"
APK_PATH = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/ar.rulosoft.mimanganu_75.apk/ar.rulosoft.mimanganu_75.apk"
TIMEOUT = 60  # seconds

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def install_apk_with_permissions(apk_path: str, package: str) -> bool:
    """Install APK with automatic permission grants."""
    logger.info(f"Installing {package} with auto-permissions...")

    # Uninstall first
    subprocess.run(
        ["adb", "-s", DEVICE_ID, "uninstall", package],
        capture_output=True
    )
    time.sleep(1)

    # Install with -g flag (auto-grant permissions)
    result = subprocess.run(
        ["adb", "-s", DEVICE_ID, "install", "-g", "-r", apk_path],
        capture_output=True,
        text=True,
        timeout=60
    )

    if result.returncode == 0:
        logger.info(f"✅ Installed successfully with auto-permissions")
        return True
    else:
        logger.error(f"❌ Installation failed: {result.stderr}")
        return False


def grant_additional_permissions(package: str):
    """Grant any additional runtime permissions."""
    logger.info("Granting additional permissions...")
    permissions = [
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.INTERNET",
        "android.permission.ACCESS_NETWORK_STATE",
        "android.permission.WAKE_LOCK",
    ]

    for permission in permissions:
        subprocess.run(
            ["adb", "-s", DEVICE_ID, "shell", "pm", "grant", package, permission],
            capture_output=True
        )


def run_test():
    """Run RV-Agent test on the app."""
    logger.info("="*80)
    logger.info("TEST: ar.rulosoft.mimanganu with ALL FIXES")
    logger.info("="*80)
    logger.info("Fixes applied:")
    logger.info("  ✅ ENTER key action (android_press_enter)")
    logger.info("  ✅ Enhanced scroll logging (INFO level)")
    logger.info("  ✅ Lowercase action type mappings")
    logger.info("="*80)

    # Install app with permissions
    if not install_apk_with_permissions(APK_PATH, PACKAGE):
        logger.error("Failed to install app, aborting test")
        return

    # Grant additional permissions
    grant_additional_permissions(PACKAGE)
    time.sleep(2)

    # Import RVAgent directly
    from rv_agent.core.rv_agent import RVAgent
    from rv_agent.config.agent_config import RVAgentConfig

    # Run test
    logger.info(f"Starting test with timeout={TIMEOUT}s...")
    logger.info("="*80)

    try:
        # Create config
        config = RVAgentConfig(
            package_name=PACKAGE,
            device_id=DEVICE_ID,
            agent_mode="multimode",
            timeout=TIMEOUT,
            results_dir="/tmp/rv_agent_mimanganu"
        )

        # Run agent
        agent = RVAgent(config)
        result = agent.run()

        logger.info(f"Test completed: {result}")

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()

    logger.info("="*80)
    logger.info("TEST COMPLETED")
    logger.info("="*80)


if __name__ == "__main__":
    run_test()
