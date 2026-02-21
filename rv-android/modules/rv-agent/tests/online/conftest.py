"""
Fixtures for online integration tests.

Provides:
- APK installation with automatic permission grants
- Static analysis data loading
- Device and agent setup
- SGLang client configuration
"""

import os
import subprocess
import time
import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Any

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.agent_factory import AgentFactory
from rv_agent.agent.device_interface import DeviceInterface

# =============================================================================
# Constants
# =============================================================================

DATASET_ROOT = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
APKS_ROOT = Path("/home/pedro/desenvolvimento/RV_ANDROID/apks")
DEVICE_ID = os.getenv("ANDROID_DEVICE_ID", "emulator-5554")
SGLANG_URL = os.getenv("SGLANG_URL", "http://192.168.0.36:30000/v1")
SGLANG_MODEL = os.getenv("SGLANG_MODEL", "Qwen/Qwen3-VL-4B-Instruct")


@dataclass
class TestApp:
    """Test application metadata."""

    name: str
    package_name: str
    apk_path: Path
    static_data_dir: Optional[Path] = None
    has_static_analysis: bool = False


# =============================================================================
# Available Test Apps
# =============================================================================

# Apps with complete static analysis (reach, wtg, gesda)
APPS_WITH_STATIC = [
    TestApp(
        name="cryptoapp",
        package_name="br.unb.cic.cryptoapp",
        apk_path=DATASET_ROOT / "cryptoapp.apk" / "cryptoapp.apk",
        static_data_dir=DATASET_ROOT / "cryptoapp.apk",
        has_static_analysis=True,
    ),
    TestApp(
        name="hashpass",
        package_name="byrne.utilities.hashpass",
        apk_path=DATASET_ROOT
        / "byrne.utilities.hashpass_2.apk"
        / "byrne.utilities.hashpass_2.apk",
        static_data_dir=DATASET_ROOT / "byrne.utilities.hashpass_2.apk",
        has_static_analysis=True,
    ),
    TestApp(
        name="ludo",
        package_name="org.secuso.privacyfriendlyludo",
        apk_path=DATASET_ROOT
        / "org.secuso.privacyfriendlyludo_5.apk"
        / "org.secuso.privacyfriendlyludo_5.apk",
        static_data_dir=DATASET_ROOT / "org.secuso.privacyfriendlyludo_5.apk",
        has_static_analysis=True,
    ),
    TestApp(
        name="dicer",
        package_name="org.secuso.privacyfriendlydicer",
        apk_path=DATASET_ROOT
        / "org.secuso.privacyfriendlydicer_8.apk"
        / "org.secuso.privacyfriendlydicer_8.apk",
        static_data_dir=DATASET_ROOT / "org.secuso.privacyfriendlydicer_8.apk",
        has_static_analysis=True,
    ),
    TestApp(
        name="hex",
        package_name="com.sam.hex",
        apk_path=DATASET_ROOT / "com.sam.hex_16.apk" / "com.sam.hex_16.apk",
        static_data_dir=DATASET_ROOT / "com.sam.hex_16.apk",
        has_static_analysis=True,
    ),
]

# Apps without static analysis (for graceful degradation tests)
APPS_WITHOUT_STATIC = [
    TestApp(
        name="cryptoapp_no_static",
        package_name="br.unb.cic.cryptoapp",
        apk_path=DATASET_ROOT / "cryptoapp.apk" / "cryptoapp.apk",
        has_static_analysis=False,
    ),
]


# =============================================================================
# APK Management Functions
# =============================================================================


def is_app_installed(device_id: str, package_name: str) -> bool:
    """Check if app is installed on device."""
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "shell", "pm", "list", "packages", package_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return f"package:{package_name}" in result.stdout
    except Exception:
        return False


def install_apk(device_id: str, apk_path: Path, grant_permissions: bool = True) -> bool:
    """
    Install APK on device with optional permission grants.

    Args:
        device_id: Target device ID
        apk_path: Path to APK file
        grant_permissions: If True, use -g flag to grant all permissions

    Returns:
        True if installation successful
    """
    if not apk_path.exists():
        raise FileNotFoundError(f"APK not found: {apk_path}")

    cmd = ["adb", "-s", device_id, "install"]
    if grant_permissions:
        cmd.append("-g")
    cmd.append(str(apk_path))

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return "Success" in result.stdout or "success" in result.stdout.lower()
    except subprocess.TimeoutExpired:
        return False


def uninstall_app(device_id: str, package_name: str) -> bool:
    """Uninstall app from device."""
    try:
        result = subprocess.run(
            ["adb", "-s", device_id, "uninstall", package_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return "Success" in result.stdout
    except Exception:
        return False


def launch_app(device_id: str, package_name: str) -> bool:
    """Launch app using monkey command."""
    try:
        result = subprocess.run(
            [
                "adb",
                "-s",
                device_id,
                "shell",
                "monkey",
                "-p",
                package_name,
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def force_stop_app(device_id: str, package_name: str) -> bool:
    """Force stop app."""
    try:
        subprocess.run(
            ["adb", "-s", device_id, "shell", "am", "force-stop", package_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return True
    except Exception:
        return False


def go_home(device_id: str) -> bool:
    """Press home button."""
    try:
        subprocess.run(
            ["adb", "-s", device_id, "shell", "input", "keyevent", "KEYCODE_HOME"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return True
    except Exception:
        return False


# =============================================================================
# Fixtures - Device
# =============================================================================


@pytest.fixture(scope="session")
def device_id():
    """Get device ID from environment or default."""
    return DEVICE_ID


@pytest.fixture(scope="session")
def device(device_id):
    """Create DeviceInterface for session."""
    device = DeviceInterface(device_id)
    yield device
    # Cleanup: go home
    go_home(device_id)


@pytest.fixture(scope="session")
def check_emulator(device_id):
    """Verify emulator is running."""
    result = subprocess.run(
        ["adb", "-s", device_id, "get-state"], capture_output=True, text=True
    )
    if "device" not in result.stdout:
        pytest.skip(f"Emulator {device_id} not running")
    return True


# =============================================================================
# Fixtures - SGLang
# =============================================================================


@pytest.fixture(scope="session")
def sglang_url():
    """SGLang server URL."""
    return SGLANG_URL


@pytest.fixture(scope="session")
def sglang_model():
    """SGLang model name."""
    return SGLANG_MODEL


@pytest.fixture(scope="session")
def check_sglang(sglang_url):
    """Verify SGLang server is available."""
    import httpx

    try:
        response = httpx.get(f"{sglang_url}/models", timeout=10)
        if response.status_code != 200:
            pytest.skip(f"SGLang server not responding at {sglang_url}")
    except Exception as e:
        pytest.skip(f"SGLang server not available: {e}")
    return True


# =============================================================================
# Fixtures - Test Apps
# =============================================================================


@pytest.fixture(scope="module", params=APPS_WITH_STATIC[:3])  # First 3 apps
def test_app_with_static(request, device_id, check_emulator) -> TestApp:
    """
    Provide test app with static analysis data.

    Installs APK if not present, yields TestApp, then cleans up.
    """
    app: TestApp = request.param

    # Install if needed
    if not is_app_installed(device_id, app.package_name):
        success = install_apk(device_id, app.apk_path, grant_permissions=True)
        if not success:
            pytest.skip(f"Failed to install {app.name}")

    yield app

    # Cleanup: force stop
    force_stop_app(device_id, app.package_name)


@pytest.fixture(scope="module")
def cryptoapp(device_id, check_emulator) -> TestApp:
    """Provide cryptoapp (primary test app)."""
    app = APPS_WITH_STATIC[0]  # cryptoapp

    if not is_app_installed(device_id, app.package_name):
        success = install_apk(device_id, app.apk_path, grant_permissions=True)
        if not success:
            pytest.skip("Failed to install cryptoapp")

    yield app

    force_stop_app(device_id, app.package_name)


@pytest.fixture(scope="module")
def hashpass(device_id, check_emulator) -> TestApp:
    """Provide hashpass app."""
    app = APPS_WITH_STATIC[1]  # hashpass

    if not is_app_installed(device_id, app.package_name):
        success = install_apk(device_id, app.apk_path, grant_permissions=True)
        if not success:
            pytest.skip("Failed to install hashpass")

    yield app

    force_stop_app(device_id, app.package_name)


@pytest.fixture(scope="module")
def ludo(device_id, check_emulator) -> TestApp:
    """Provide ludo app."""
    app = APPS_WITH_STATIC[2]  # ludo

    if not is_app_installed(device_id, app.package_name):
        success = install_apk(device_id, app.apk_path, grant_permissions=True)
        if not success:
            pytest.skip("Failed to install ludo")

    yield app

    force_stop_app(device_id, app.package_name)


# =============================================================================
# Fixtures - Agent Configuration
# =============================================================================


@pytest.fixture
def agent_config_multimode(cryptoapp, sglang_url, sglang_model) -> RVAgentConfig:
    """Create multimode agent config."""
    return RVAgentConfig(
        package_name=cryptoapp.package_name,
        device_id=DEVICE_ID,
        agent_mode="multimode",
        llm_probability=0.7,
        llm_base_url=sglang_url,
        llm_model=sglang_model,
        timeout=60,
        debug_mode=True,
    )


@pytest.fixture
def agent_config_pure_algorithm(cryptoapp) -> RVAgentConfig:
    """Create pure algorithm agent config (no LLM)."""
    return RVAgentConfig(
        package_name=cryptoapp.package_name,
        device_id=DEVICE_ID,
        agent_mode="pure_algorithm",
        timeout=60,
        debug_mode=True,
    )


@pytest.fixture
def agent_config_llm_only(cryptoapp, sglang_url, sglang_model) -> RVAgentConfig:
    """Create LLM-only agent config."""
    return RVAgentConfig(
        package_name=cryptoapp.package_name,
        device_id=DEVICE_ID,
        agent_mode="llm_only",
        llm_base_url=sglang_url,
        llm_model=sglang_model,
        timeout=60,
        debug_mode=True,
    )


# =============================================================================
# Fixtures - Static Analysis
# =============================================================================


@pytest.fixture
def static_data_cryptoapp(cryptoapp):
    """Load static analysis data for cryptoapp."""
    from rv_static_analysis.loader import StaticAnalysisLoader

    if not cryptoapp.has_static_analysis or not cryptoapp.static_data_dir:
        return None

    try:
        loader = StaticAnalysisLoader(cryptoapp.static_data_dir)
        return loader.load()
    except Exception:
        return None


# =============================================================================
# Markers
# =============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "online: tests requiring real emulator")
    config.addinivalue_line("markers", "sglang: tests requiring SGLang server")
    config.addinivalue_line("markers", "slow: tests that take significant time")
    config.addinivalue_line(
        "markers", "static_analysis: tests using static analysis data"
    )
