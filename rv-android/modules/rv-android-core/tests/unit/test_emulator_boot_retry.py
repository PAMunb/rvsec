"""Tests for emulator boot retry resilience.

Verifies that _wait_for_boot() retries on RVCommandTimeoutError instead of
propagating it immediately. Before this fix, a single ADB command timeout
(30s) would abort the entire boot wait even though the 180s boot_timeout
had not been reached.

The boot wait runs two phases:
- Phase 1: boot animation stop (`init.svc.bootanim` → "stopped").
- Phase 2: sys.boot_completed property set.

A previous Phase 3 (`adb root` + `adb remount`) was removed: under the
emulator's `-read-only` flag the remount is rejected at the qemu layer
regardless of adbd state, and rv-platform / rv-tools do not need root
since every push goes to /data/local/tmp/ or /sdcard/.
"""

from unittest.mock import MagicMock, call, patch

import pytest
from rv_android_core.util.android.android import Android
from rv_android_core.util.error.exceptions import RVCommandTimeoutError


@pytest.fixture(autouse=True)
def mock_command_class():
    with patch("rv_android_core.util.android.android.Command") as mock_command:
        yield mock_command


@pytest.fixture(autouse=True)
def mock_logging():
    with patch("rv_android_core.util.android.android.logging") as mock_log:
        yield mock_log


@pytest.fixture(autouse=True)
def mock_time_sleep():
    with patch("time.sleep") as mock_sleep:
        yield mock_sleep


@pytest.fixture(autouse=True)
def mock_to_readable_time():
    with patch(
        "rv_android_core.util.android.android.utils.to_readable_time"
    ) as mock_readable:
        mock_readable.return_value = "0m 5s"
        yield mock_readable


class TestPhase1BootAnimRetry:
    """Phase 1: boot animation check retries on RVCommandTimeoutError."""

    def test_retries_on_command_timeout_then_succeeds(
        self, mock_command_class, mock_logging
    ):
        """First 2 invocations time out, third returns 'stopped' — no exception raised."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            RVCommandTimeoutError("timeout", timeout_seconds=30),
            RVCommandTimeoutError("timeout", timeout_seconds=30),
            MagicMock(stdout=b"stopped"),  # Phase 1 done
            MagicMock(stdout=b""),  # Phase 2 done (invoke succeeds)
        ]

        with patch("time.time", side_effect=[0, 10, 20, 30, 40, 50]):
            Android._wait_for_boot("emulator-5554", boot_timeout=180)

        # Two timeout warnings for Phase 1
        mock_logging.warning.assert_any_call(
            "ADB boot check timed out for emulator-5554, retrying..."
        )
        assert (
            mock_logging.warning.call_args_list.count(
                call("ADB boot check timed out for emulator-5554, retrying...")
            )
            == 2
        )

    def test_raises_timeout_after_boot_timeout_exceeded(self, mock_command_class):
        """When boot_timeout is exceeded during Phase 1 retries, TimeoutError is raised."""
        mock_cmd = mock_command_class.return_value
        # All invocations time out
        mock_cmd.invoke.side_effect = RVCommandTimeoutError(
            "timeout", timeout_seconds=30
        )

        with patch("time.time", side_effect=[0, 200]):
            with pytest.raises(TimeoutError, match="did not boot within 10s"):
                Android._wait_for_boot("emulator-5554", boot_timeout=10)

    def test_retries_on_non_stopped_then_timeout_then_stopped(self, mock_command_class):
        """Mix of non-stopped responses and command timeouts, eventually succeeds."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            MagicMock(stdout=b"booting"),  # not stopped
            RVCommandTimeoutError("timeout", timeout_seconds=30),  # timeout
            MagicMock(stdout=b"stopped"),  # Phase 1 done
            MagicMock(stdout=b""),  # Phase 2 done
        ]

        with patch("time.time", side_effect=[0, 5, 10, 15, 20, 25]):
            Android._wait_for_boot("emulator-5554", boot_timeout=180)


class TestPhase2BootCompletedRetry:
    """Phase 2: sys.boot_completed check retries on RVCommandTimeoutError."""

    def test_retries_phase2_on_command_timeout(self, mock_command_class, mock_logging):
        """Phase 2 invoke times out once, succeeds on retry."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            MagicMock(stdout=b"stopped"),  # Phase 1 done
            RVCommandTimeoutError("timeout", timeout_seconds=30),  # Phase 2 timeout
            MagicMock(stdout=b""),  # Phase 2 done on retry
        ]

        with patch("time.time", side_effect=[0, 5, 10, 15, 20]):
            Android._wait_for_boot("emulator-5554", boot_timeout=180)

        mock_logging.warning.assert_any_call(
            "ADB boot_completed check timed out for emulator-5554, retrying..."
        )

    def test_phase2_raises_timeout_when_exceeded(self, mock_command_class):
        """Phase 2 exceeds boot_timeout — TimeoutError raised."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            MagicMock(stdout=b"stopped"),  # Phase 1 done
            RVCommandTimeoutError("timeout", timeout_seconds=30),  # Phase 2 timeout
        ]

        with patch("time.time", side_effect=[0, 5, 10, 200]):
            with pytest.raises(
                TimeoutError, match="sys.boot_completed not set within 10s"
            ):
                Android._wait_for_boot("emulator-5554", boot_timeout=10)


class TestFullBootRetryIntegration:
    """End-to-end test: both phases experience timeouts but boot completes within budget."""

    def test_all_phases_retry_and_succeed(self, mock_command_class, mock_logging):
        """Both phases have at least one command timeout, but boot completes."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            RVCommandTimeoutError("timeout", timeout_seconds=30),  # Phase 1 timeout
            MagicMock(stdout=b"stopped"),  # Phase 1 done
            RVCommandTimeoutError("timeout", timeout_seconds=30),  # Phase 2 timeout
            MagicMock(stdout=b""),  # Phase 2 done
        ]

        with patch("time.time", side_effect=[0, 5, 10, 15, 20, 25, 30]):
            Android._wait_for_boot("emulator-5554", boot_timeout=180)

        mock_logging.warning.assert_any_call(
            "ADB boot check timed out for emulator-5554, retrying..."
        )
        mock_logging.warning.assert_any_call(
            "ADB boot_completed check timed out for emulator-5554, retrying..."
        )
