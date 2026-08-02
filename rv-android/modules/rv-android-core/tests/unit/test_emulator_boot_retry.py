"""Tests for emulator boot retry resilience.

ADB responds slowly during early boot, so a single probe exceeding its
per-command timeout must be retried rather than aborting the whole wait:
`RVCommandTimeoutError` is caught inside both phase loops and the probe is
reissued against the remaining shared budget.

Two properties of the surrounding code shape every test here.

`MagicMock().is_failure()` returns a truthy `MagicMock`, so a bare result mock
reads as a *failed* probe and the wait would never terminate. Results are
built by `command_result()`, which sets `is_failure.return_value` explicitly.

The budget is spent by the monotonic `fake_clock` fixture, which advances only
when the code under test sleeps. Counting `time.time()` calls into a
`side_effect` list — as these tests once did — pins the exact number of clock
reads the implementation performs, so any unrelated edit that adds or removes
one breaks tests that have nothing to do with it.
"""

from unittest.mock import MagicMock, call, patch

import pytest
from rv_android_core.util.android.android import Android
from rv_android_core.util.error.exceptions import RVCommandTimeoutError


def command_result(stdout=b"", stderr=b"", code=0, failure=False):
    """Build a `CommandResult` double with an explicit failure verdict."""
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.code = code
    result.is_failure.return_value = failure
    result.get_combined_output.return_value = (stdout + stderr).decode(
        "ascii", errors="replace"
    )
    return result


BOOTANIM_STOPPED = dict(stdout=b"stopped")
BOOT_COMPLETED = dict(stdout=b"1")


@pytest.fixture(autouse=True)
def mock_command_class():
    with patch("rv_android_core.util.android.android.Command") as mock_command:
        yield mock_command


@pytest.fixture(autouse=True)
def mock_logging():
    with patch("rv_android_core.util.android.android.logging") as mock_log:
        yield mock_log


@pytest.fixture(autouse=True)
def mock_to_readable_time():
    with patch(
        "rv_android_core.util.android.android.utils.to_readable_time"
    ) as mock_readable:
        mock_readable.return_value = "0m 5s"
        yield mock_readable


class TestPhase1BootAnimRetry:
    """Phase 1: the boot animation check retries on RVCommandTimeoutError."""

    def test_retries_on_command_timeout_then_succeeds(
        self, mock_command_class, mock_logging, fake_clock
    ):
        """The first two probes time out; the third reads `stopped`."""
        mock_command_class.return_value.invoke.side_effect = [
            RVCommandTimeoutError("timeout", timeout_seconds=30),
            RVCommandTimeoutError("timeout", timeout_seconds=30),
            command_result(**BOOTANIM_STOPPED),
            command_result(**BOOT_COMPLETED),
        ]

        Android._wait_for_boot("emulator-5554", boot_timeout=180)

        assert (
            mock_logging.warning.call_args_list.count(
                call("ADB boot check timed out for emulator-5554, retrying...")
            )
            == 2
        )

    def test_raises_timeout_after_boot_timeout_exceeded(
        self, mock_command_class, fake_clock
    ):
        """Retrying does not extend the budget: when it is spent, phase 1 raises."""
        mock_command_class.return_value.invoke.side_effect = RVCommandTimeoutError(
            "timeout", timeout_seconds=30
        )

        with pytest.raises(TimeoutError, match="did not boot within 10s"):
            Android._wait_for_boot("emulator-5554", boot_timeout=10)

    def test_retries_on_non_stopped_then_timeout_then_stopped(
        self, mock_command_class, fake_clock
    ):
        """A mix of not-yet-ready answers and probe timeouts still converges."""
        mock_command_class.return_value.invoke.side_effect = [
            command_result(stdout=b"booting"),
            RVCommandTimeoutError("timeout", timeout_seconds=30),
            command_result(**BOOTANIM_STOPPED),
            command_result(**BOOT_COMPLETED),
        ]

        Android._wait_for_boot("emulator-5554", boot_timeout=180)


class TestPhase2BootCompletedRetry:
    """Phase 2: the sys.boot_completed check retries on RVCommandTimeoutError."""

    def test_retries_phase2_on_command_timeout(
        self, mock_command_class, mock_logging, fake_clock
    ):
        """The probe times out once and reads b"1" on the retry."""
        mock_command_class.return_value.invoke.side_effect = [
            command_result(**BOOTANIM_STOPPED),
            RVCommandTimeoutError("timeout", timeout_seconds=30),
            command_result(**BOOT_COMPLETED),
        ]

        Android._wait_for_boot("emulator-5554", boot_timeout=180)

        mock_logging.warning.assert_any_call(
            "ADB boot_completed check timed out for emulator-5554, retrying..."
        )

    def test_phase2_raises_timeout_when_exceeded(self, mock_command_class, fake_clock):
        """The message names phase 2, keeping the two failures separable."""
        mock_command_class.return_value.invoke.side_effect = [
            command_result(**BOOTANIM_STOPPED)
        ] + [RVCommandTimeoutError("timeout", timeout_seconds=30)] * 20

        with pytest.raises(TimeoutError, match="sys.boot_completed not set within 10s"):
            Android._wait_for_boot("emulator-5554", boot_timeout=10)
