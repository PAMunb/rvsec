"""Tests for emulator boot retry resilience (Group 15).

Verifies that _wait_for_boot() retries on RVCommandTimeoutError instead of
propagating it immediately. Before this fix, a single ADB command timeout (30s)
would abort the entire boot wait even though the 180s boot_timeout had not
been reached.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from rv_android_core.util.android.android import Android
from rv_android_core.util.error.exceptions import RVCommandTimeoutError


@pytest.fixture(autouse=True)
def mock_command_class():
    with patch('rv_android_core.util.android.android.Command') as mock_command:
        yield mock_command


@pytest.fixture(autouse=True)
def mock_logging():
    with patch('rv_android_core.util.android.android.logging') as mock_log:
        yield mock_log


@pytest.fixture(autouse=True)
def mock_time_sleep():
    with patch('time.sleep') as mock_sleep:
        yield mock_sleep


@pytest.fixture(autouse=True)
def mock_to_readable_time():
    with patch('rv_android_core.util.android.android.utils.to_readable_time') as mock_readable:
        mock_readable.return_value = "0m 5s"
        yield mock_readable


class TestPhase1BootAnimRetry:
    """Phase 1: boot animation check retries on RVCommandTimeoutError."""

    def test_retries_on_command_timeout_then_succeeds(self, mock_command_class, mock_logging):
        """First 2 invocations time out, third returns 'stopped' — no exception raised."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            RVCommandTimeoutError("timeout", timeout_seconds=30),
            RVCommandTimeoutError("timeout", timeout_seconds=30),
            MagicMock(stdout=b'stopped'),   # Phase 1 done
            MagicMock(stdout=b''),          # Phase 2 done (invoke succeeds)
            MagicMock(stderr=b''),          # Phase 3 root done
            MagicMock(stderr=b''),          # Phase 3 remount done
        ]

        # time.time() calls: start, 3x Phase 1 timeout checks, Phase 2 check,
        # Phase 3 root check, Phase 3 remount check, elapsed
        with patch('time.time', side_effect=[0, 10, 20, 30, 40, 50, 60, 70]):
            Android._wait_for_boot("emulator-5554", boot_timeout=180)

        # Two timeout warnings for Phase 1
        mock_logging.warning.assert_any_call(
            'ADB boot check timed out for emulator-5554, retrying...'
        )
        assert mock_logging.warning.call_args_list.count(
            call('ADB boot check timed out for emulator-5554, retrying...')
        ) == 2

    def test_raises_timeout_after_boot_timeout_exceeded(self, mock_command_class):
        """When boot_timeout is exceeded during Phase 1 retries, TimeoutError is raised."""
        mock_cmd = mock_command_class.return_value
        # All invocations time out
        mock_cmd.invoke.side_effect = RVCommandTimeoutError("timeout", timeout_seconds=30)

        # time.time(): start=0, then each loop iteration exceeds boot_timeout
        with patch('time.time', side_effect=[0, 200]):
            with pytest.raises(TimeoutError, match="did not boot within 10s"):
                Android._wait_for_boot("emulator-5554", boot_timeout=10)

    def test_retries_on_non_stopped_then_timeout_then_stopped(self, mock_command_class):
        """Mix of non-stopped responses and command timeouts, eventually succeeds."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            MagicMock(stdout=b'booting'),                               # not stopped
            RVCommandTimeoutError("timeout", timeout_seconds=30),       # timeout
            MagicMock(stdout=b'stopped'),                               # Phase 1 done
            MagicMock(stdout=b''),                                      # Phase 2 done
            MagicMock(stderr=b''),                                      # root done
            MagicMock(stderr=b''),                                      # remount done
        ]

        with patch('time.time', side_effect=[0, 5, 10, 15, 20, 25, 30, 35]):
            Android._wait_for_boot("emulator-5554", boot_timeout=180)


class TestPhase2BootCompletedRetry:
    """Phase 2: sys.boot_completed check retries on RVCommandTimeoutError."""

    def test_retries_phase2_on_command_timeout(self, mock_command_class, mock_logging):
        """Phase 2 invoke times out once, succeeds on retry."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            MagicMock(stdout=b'stopped'),                               # Phase 1 done
            RVCommandTimeoutError("timeout", timeout_seconds=30),       # Phase 2 timeout
            MagicMock(stdout=b''),                                      # Phase 2 done on retry
            MagicMock(stderr=b''),                                      # root done
            MagicMock(stderr=b''),                                      # remount done
        ]

        with patch('time.time', side_effect=[0, 5, 10, 15, 20, 25, 30]):
            Android._wait_for_boot("emulator-5554", boot_timeout=180)

        mock_logging.warning.assert_any_call(
            'ADB boot_completed check timed out for emulator-5554, retrying...'
        )

    def test_phase2_raises_timeout_when_exceeded(self, mock_command_class):
        """Phase 2 exceeds boot_timeout — TimeoutError raised."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            MagicMock(stdout=b'stopped'),                               # Phase 1 done
            RVCommandTimeoutError("timeout", timeout_seconds=30),       # Phase 2 timeout
        ]

        # After Phase 1, Phase 2 loop checks time and it exceeds boot_timeout
        with patch('time.time', side_effect=[0, 5, 10, 200]):
            with pytest.raises(TimeoutError, match="sys.boot_completed not set within 10s"):
                Android._wait_for_boot("emulator-5554", boot_timeout=10)


class TestPhase3RootRemountRetry:
    """Phase 3: root and remount commands retry on RVCommandTimeoutError."""

    def test_retries_root_on_command_timeout(self, mock_command_class, mock_logging):
        """Root command times out once, succeeds on retry."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            MagicMock(stdout=b'stopped'),                               # Phase 1 done
            MagicMock(stdout=b''),                                      # Phase 2 done
            RVCommandTimeoutError("timeout", timeout_seconds=30),       # root timeout
            MagicMock(stderr=b''),                                      # root done on retry
            MagicMock(stderr=b''),                                      # remount done
        ]

        with patch('time.time', side_effect=[0, 5, 10, 15, 20, 25, 30]):
            Android._wait_for_boot("emulator-5554", boot_timeout=180)

        mock_logging.warning.assert_any_call(
            'ADB root command timed out for emulator-5554, retrying...'
        )

    def test_retries_remount_on_command_timeout(self, mock_command_class, mock_logging):
        """Remount command times out once, succeeds on retry."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            MagicMock(stdout=b'stopped'),                               # Phase 1 done
            MagicMock(stdout=b''),                                      # Phase 2 done
            MagicMock(stderr=b''),                                      # root done
            RVCommandTimeoutError("timeout", timeout_seconds=30),       # remount timeout
            MagicMock(stderr=b''),                                      # remount done on retry
        ]

        with patch('time.time', side_effect=[0, 5, 10, 15, 20, 25, 30]):
            Android._wait_for_boot("emulator-5554", boot_timeout=180)

        mock_logging.warning.assert_any_call(
            'ADB remount command timed out for emulator-5554, retrying...'
        )

    def test_root_raises_timeout_when_exceeded(self, mock_command_class):
        """Root command keeps timing out until boot_timeout is exceeded."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            MagicMock(stdout=b'stopped'),                               # Phase 1 done
            MagicMock(stdout=b''),                                      # Phase 2 done
            RVCommandTimeoutError("timeout", timeout_seconds=30),       # root timeout
        ]

        with patch('time.time', side_effect=[0, 5, 10, 15, 200]):
            with pytest.raises(TimeoutError, match="root failed within 10s"):
                Android._wait_for_boot("emulator-5554", boot_timeout=10)

    def test_remount_raises_timeout_when_exceeded(self, mock_command_class):
        """Remount command keeps timing out until boot_timeout is exceeded."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            MagicMock(stdout=b'stopped'),                               # Phase 1 done
            MagicMock(stdout=b''),                                      # Phase 2 done
            MagicMock(stderr=b''),                                      # root done
            RVCommandTimeoutError("timeout", timeout_seconds=30),       # remount timeout
        ]

        # time.time() calls: start=0, Phase1 check=5, Phase2 check=6,
        # root check=7 (root succeeds), remount check=8 (invoke raises timeout),
        # remount check 2nd loop=200 (exceeds boot_timeout → TimeoutError)
        with patch('time.time', side_effect=[0, 5, 6, 7, 8, 200]):
            with pytest.raises(TimeoutError, match="remount failed within 10s"):
                Android._wait_for_boot("emulator-5554", boot_timeout=10)


class TestFullBootRetryIntegration:
    """End-to-end test: all phases experience timeouts but boot completes within budget."""

    def test_all_phases_retry_and_succeed(self, mock_command_class, mock_logging):
        """Every phase has at least one command timeout, but boot completes."""
        mock_cmd = mock_command_class.return_value
        mock_cmd.invoke.side_effect = [
            RVCommandTimeoutError("timeout", timeout_seconds=30),       # Phase 1 timeout
            MagicMock(stdout=b'stopped'),                               # Phase 1 done
            RVCommandTimeoutError("timeout", timeout_seconds=30),       # Phase 2 timeout
            MagicMock(stdout=b''),                                      # Phase 2 done
            RVCommandTimeoutError("timeout", timeout_seconds=30),       # root timeout
            MagicMock(stderr=b''),                                      # root done
            RVCommandTimeoutError("timeout", timeout_seconds=30),       # remount timeout
            MagicMock(stderr=b''),                                      # remount done
        ]

        # Enough time values for: start + all timeout checks in all phases + elapsed
        with patch('time.time', side_effect=[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]):
            Android._wait_for_boot("emulator-5554", boot_timeout=180)

        # Verify warnings were logged for each phase
        mock_logging.warning.assert_any_call(
            'ADB boot check timed out for emulator-5554, retrying...'
        )
        mock_logging.warning.assert_any_call(
            'ADB boot_completed check timed out for emulator-5554, retrying...'
        )
        mock_logging.warning.assert_any_call(
            'ADB root command timed out for emulator-5554, retrying...'
        )
        mock_logging.warning.assert_any_call(
            'ADB remount command timed out for emulator-5554, retrying...'
        )
