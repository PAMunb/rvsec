"""
Unit tests for rv_uiautomator.utils.device_manager.

Tests cover DeviceManager device discovery, connection verification, device
info retrieval, and ADB server restart. All ADB/subprocess interactions and
timing are mocked. No real emulator/adb is ever touched.
"""

from unittest.mock import MagicMock, patch

import pytest

from rv_uiautomator.utils.device_manager import DeviceManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fake_proc(returncode=0, stdout="", stderr=""):
    """Build a fake subprocess.CompletedProcess-like result."""
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager():
    """DeviceManager with LoggingManager patched so logger is a MagicMock."""
    with patch("rv_uiautomator.utils.device_manager.LoggingManager") as mock_lm:
        mock_logger = MagicMock()
        mock_lm.get_instance.return_value.get_logger.return_value = mock_logger
        dm = DeviceManager()
    return dm


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_builds_logger():
    """__init__ wires a logger from LoggingManager and stores it."""
    with patch("rv_uiautomator.utils.device_manager.LoggingManager") as mock_lm:
        mock_logger = MagicMock()
        mock_lm.get_instance.return_value.get_logger.return_value = mock_logger
        dm = DeviceManager()

    assert dm.logger is mock_logger
    mock_logger.debug.assert_called_with("DeviceManager initialized")


# ---------------------------------------------------------------------------
# get_available_devices
#
# Equivalence partitioning over the parsed `adb devices` output: rows are
# partitioned into (a) valid "device"-status ids, (b) non-"device" status
# (offline), (c) blank lines, (d) lines without a tab separator. Only class
# (a) must survive filtering.
# ---------------------------------------------------------------------------


def test_get_available_devices_happy_filters_rows(manager):
    """Only tab-separated rows with status 'device' are returned."""
    stdout = (
        "List of devices attached\n"
        "emulator-5554\tdevice\n"
        "emulator-5556\toffline\n"
        "\n"
        "garbage-without-tab\n"
    )
    with patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub:
        mock_sub.run.return_value = fake_proc(returncode=0, stdout=stdout)
        devices = manager.get_available_devices()

    assert devices == ["emulator-5554"]


def test_get_available_devices_nonzero_returncode(manager):
    """A non-zero adb returncode yields an empty list (73-75)."""
    with patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub:
        mock_sub.run.return_value = fake_proc(returncode=1, stderr="boom")
        assert manager.get_available_devices() == []


def test_get_available_devices_exception(manager):
    """subprocess raising is swallowed by the inner except → [] (89-91)."""
    with patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub:
        mock_sub.run.side_effect = RuntimeError("adb exploded")
        assert manager.get_available_devices() == []


# ---------------------------------------------------------------------------
# verify_device_connection
#
# Decision table over (device in available list?) × (echo responsive?):
#   not-in-list            → False (short-circuit, no echo call)
#   in-list, responsive    → True
#   in-list, not responsive→ False
#   in-list, echo raises   → False
# ---------------------------------------------------------------------------


def test_verify_device_not_in_available(manager):
    """Device absent from the available list returns False, no echo call (107-109)."""
    manager.get_available_devices = MagicMock(return_value=[])
    with patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub:
        assert manager.verify_device_connection("emulator-5554") is False
        mock_sub.run.assert_not_called()


def test_verify_device_responsive(manager):
    """Listed device whose echo returns 'test' is responsive → True (119-121)."""
    manager.get_available_devices = MagicMock(return_value=["emulator-5554"])
    with patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub:
        mock_sub.run.return_value = fake_proc(returncode=0, stdout="test\n")
        assert manager.verify_device_connection("emulator-5554") is True


def test_verify_device_not_responsive(manager):
    """Listed device whose echo lacks 'test' is not responsive → False (122-124)."""
    manager.get_available_devices = MagicMock(return_value=["emulator-5554"])
    with patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub:
        mock_sub.run.return_value = fake_proc(returncode=0, stdout="nope\n")
        assert manager.verify_device_connection("emulator-5554") is False


def test_verify_device_exception(manager):
    """Echo subprocess raising is swallowed → False (126-128)."""
    manager.get_available_devices = MagicMock(return_value=["emulator-5554"])
    with patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub:
        mock_sub.run.side_effect = OSError("echo failed")
        assert manager.verify_device_connection("emulator-5554") is False


# ---------------------------------------------------------------------------
# get_device_info
#
# subprocess.run is invoked 6 times: 5 getprop calls then 1 `wm size`. The
# side_effect list supplies one fake result per call, exercising the full
# property loop plus resolution parsing branches.
# ---------------------------------------------------------------------------


def test_get_device_info_full(manager):
    """All props present and a parseable `wm size` populate every key."""
    side = [
        fake_proc(returncode=0, stdout="Pixel 5\n"),
        fake_proc(returncode=0, stdout="Google\n"),
        fake_proc(returncode=0, stdout="12\n"),
        fake_proc(returncode=0, stdout="31\n"),
        fake_proc(returncode=0, stdout="arm64-v8a\n"),
        fake_proc(returncode=0, stdout="Physical size: 1080x1920\n"),
    ]
    with patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub:
        mock_sub.run.side_effect = side
        info = manager.get_device_info("emulator-5554")

    assert info == {
        "model": "Pixel 5",
        "manufacturer": "Google",
        "android_version": "12",
        "api_level": "31",
        "cpu_abi": "arm64-v8a",
        "resolution": "1080x1920",
    }


def test_get_device_info_partial(manager):
    """A failed getprop omits its key; `wm size` without the marker omits resolution."""
    side = [
        fake_proc(returncode=0, stdout="Pixel 5\n"),
        fake_proc(returncode=1, stdout="ignored"),  # manufacturer fails → omitted
        fake_proc(returncode=0, stdout="12\n"),
        fake_proc(returncode=0, stdout="31\n"),
        fake_proc(returncode=0, stdout="arm64-v8a\n"),
        fake_proc(returncode=0, stdout="some other output\n"),  # no "Physical size:"
    ]
    with patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub:
        mock_sub.run.side_effect = side
        info = manager.get_device_info("emulator-5554")

    assert "manufacturer" not in info
    assert "resolution" not in info
    assert info["model"] == "Pixel 5"


def test_get_device_info_size_without_x(manager):
    """`wm size` with the marker but no 'x' skips resolution (176 guard)."""
    side = [
        fake_proc(returncode=0, stdout="Pixel 5\n"),
        fake_proc(returncode=0, stdout="Google\n"),
        fake_proc(returncode=0, stdout="12\n"),
        fake_proc(returncode=0, stdout="31\n"),
        fake_proc(returncode=0, stdout="arm64-v8a\n"),
        fake_proc(returncode=0, stdout="Physical size:\n"),  # marker present, no 'x'
    ]
    with patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub:
        mock_sub.run.side_effect = side
        info = manager.get_device_info("emulator-5554")

    assert "resolution" not in info


def test_get_device_info_exception(manager):
    """First subprocess call raising is swallowed → {} (183-185)."""
    with patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub:
        mock_sub.run.side_effect = TimeoutError("getprop hung")
        assert manager.get_device_info("emulator-5554") == {}


# ---------------------------------------------------------------------------
# restart_adb_server
#
# subprocess.run is invoked twice: kill-server then start-server. The
# start-server returncode partitions success (0) from failure (non-zero);
# a raised exception is the third path.
# ---------------------------------------------------------------------------


def test_restart_adb_server_success(manager):
    """start-server returncode 0 → True and sleeps 2s between kill/start (207-209)."""
    side = [fake_proc(returncode=0), fake_proc(returncode=0)]
    with (
        patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub,
        patch("rv_uiautomator.utils.device_manager.time.sleep") as mock_sleep,
    ):
        mock_sub.run.side_effect = side
        assert manager.restart_adb_server() is True
        mock_sleep.assert_called_once_with(2)


def test_restart_adb_server_failure(manager):
    """start-server non-zero returncode → False (210-212)."""
    side = [fake_proc(returncode=0), fake_proc(returncode=1, stderr="cannot bind")]
    with (
        patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub,
        patch("rv_uiautomator.utils.device_manager.time.sleep"),
    ):
        mock_sub.run.side_effect = side
        assert manager.restart_adb_server() is False


def test_restart_adb_server_exception(manager):
    """subprocess raising is swallowed → False (214-216)."""
    with (
        patch("rv_uiautomator.utils.device_manager.subprocess") as mock_sub,
        patch("rv_uiautomator.utils.device_manager.time.sleep"),
    ):
        mock_sub.run.side_effect = RuntimeError("kill-server failed")
        assert manager.restart_adb_server() is False
