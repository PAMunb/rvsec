"""Tests for the emulator boot gate and the timeouts that bound it.

`Android._wait_for_boot` is the only thing standing between a task and an
APK installed on a device that never finished booting. These tests pin the
acceptance condition (INV-CORE-44), the absence of any shell dependency in
the probe argv (INV-CORE-45), the single shared budget (INV-CORE-46), the
timeout resolution order (INV-CORE-47) and the rule that a returned
`CommandResult` is never treated as success without being inspected
(INV-CORE-43).

`MagicMock().is_failure()` returns a truthy `MagicMock`, which would make
every result read as a failure. Every result mock in this file is built by
`command_result()`, which sets `is_failure.return_value` explicitly.
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.constants import (
    ENV_ADB_CMD_TIMEOUT,
    ENV_APK_INSTALL_TIMEOUT,
    ENV_EMULATOR_BOOT_TIMEOUT,
)
from rv_android_core.util.android.android import (
    DEFAULT_ADB_CMD_TIMEOUT_SECONDS,
    DEFAULT_APK_INSTALL_TIMEOUT_SECONDS,
    DEFAULT_BOOT_TIMEOUT_SECONDS,
    EMULATOR_KILL_SETTLE_SECONDS,
    Android,
)


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


@pytest.fixture(autouse=True)
def clean_timeout_env(monkeypatch):
    """Run every test against an environment with no timeout overrides set."""
    for name in (
        ENV_EMULATOR_BOOT_TIMEOUT,
        ENV_ADB_CMD_TIMEOUT,
        ENV_APK_INSTALL_TIMEOUT,
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def mock_command_class():
    with patch("rv_android_core.util.android.android.Command") as mock_command:
        yield mock_command


@pytest.fixture(autouse=True)
def mock_to_readable_time():
    with patch(
        "rv_android_core.util.android.android.utils.to_readable_time"
    ) as mock_readable:
        mock_readable.return_value = "0m 5s"
        yield mock_readable


class TestPhase2AcceptanceCondition:
    """Phase 2 terminates only on a probe that succeeded and read exactly "1"."""

    def test_accepts_only_boot_completed_one(self, mock_command_class, fake_clock):
        """A successful probe reading b"1" ends the wait."""
        mock_command_class.return_value.invoke.side_effect = [
            command_result(stdout=b"stopped"),
            command_result(stdout=b"1"),
        ]

        Android._wait_for_boot("emulator-5554", boot_timeout=180)

    def test_failed_probe_never_ends_the_wait(self, mock_command_class, fake_clock):
        """Exit 127 — the status the old quoted shell string produced — is not
        success, and polling continues until the budget is spent."""
        mock_command_class.return_value.invoke.side_effect = [
            command_result(stdout=b"stopped")
        ] + [
            command_result(stderr=b"/system/bin/sh: not found", code=127, failure=True)
            for _ in range(20)
        ]

        with pytest.raises(TimeoutError, match="sys.boot_completed not set within 30s"):
            Android._wait_for_boot("emulator-5554", boot_timeout=30)

    def test_empty_stdout_continues_polling(self, mock_command_class, fake_clock):
        """The device answered but the property is not set yet: keep polling,
        then accept as soon as it reads b"1"."""
        mock_command_class.return_value.invoke.side_effect = [
            command_result(stdout=b"stopped"),
            command_result(stdout=b""),
            command_result(stdout=b""),
            command_result(stdout=b"1"),
        ]

        Android._wait_for_boot("emulator-5554", boot_timeout=180)

    def test_unexpected_value_continues_polling(self, mock_command_class, fake_clock):
        """Any value other than b"1" keeps the wait open."""
        mock_command_class.return_value.invoke.side_effect = [
            command_result(stdout=b"stopped"),
            command_result(stdout=b"0"),
            command_result(stdout=b"1"),
        ]

        Android._wait_for_boot("emulator-5554", boot_timeout=180)


class TestProbeArgv:
    """The probe argv reaches the device verbatim, so it carries no shell."""

    def test_phase2_argv_has_no_quotes_or_shell_tokens(
        self, mock_command_class, fake_clock
    ):
        mock_command_class.return_value.invoke.side_effect = [
            command_result(stdout=b"stopped"),
            command_result(stdout=b"1"),
        ]

        Android._wait_for_boot("emulator-5554", boot_timeout=180)

        phase2_args = mock_command_class.call_args_list[1][0][1]
        assert phase2_args == [
            "-s",
            "emulator-5554",
            "shell",
            "getprop",
            "sys.boot_completed",
        ]
        for element in phase2_args:
            for forbidden in ("'", '"', "$(", "[[", "while", ";"):
                assert forbidden not in element

    def test_wait_for_device_token_is_gone(self, mock_command_class, fake_clock):
        """An unbounded device wait inside a single probe is what the Python
        poll replaced; the token must not survive alongside it."""
        mock_command_class.return_value.invoke.side_effect = [
            command_result(stdout=b"stopped"),
            command_result(stdout=b"1"),
        ]

        Android._wait_for_boot("emulator-5554", boot_timeout=180)

        for call_args in mock_command_class.call_args_list:
            assert "wait-for-device" not in call_args[0][1]


class TestSharedBudget:
    """Both phases spend one budget taken from one timestamp."""

    def test_phase2_inherits_what_phase1_left(self, mock_command_class, fake_clock):
        """Phase 1 burns most of a 30 s budget; phase 2 fails against the
        remainder and its message names phase 2, not phase 1."""
        mock_command_class.return_value.invoke.side_effect = [
            command_result(stdout=b"booting"),  # 5s
            command_result(stdout=b"booting"),  # 10s
            command_result(stdout=b"booting"),  # 15s
            command_result(stdout=b"booting"),  # 20s
            command_result(stdout=b"stopped"),  # phase 1 done at 20s
        ] + [command_result(stdout=b"") for _ in range(10)]

        with pytest.raises(TimeoutError) as excinfo:
            Android._wait_for_boot("emulator-5554", boot_timeout=30)

        message = str(excinfo.value)
        assert "sys.boot_completed not set within 30s" in message
        assert "did not boot within" not in message

    def test_phase1_and_phase2_messages_are_distinguishable(
        self, mock_command_class, fake_clock
    ):
        """The two strings are the historical signal in stored records."""
        mock_command_class.return_value.invoke.return_value = command_result(
            stdout=b"booting"
        )

        with pytest.raises(TimeoutError, match="did not boot within 10s"):
            Android._wait_for_boot("emulator-5554", boot_timeout=10)


class TestPhase1Diagnostics:
    """A broken ADB is reported in seconds, not after the full budget."""

    def test_failed_probe_logs_serial_and_combined_output(
        self, mock_command_class, fake_clock
    ):
        mock_command_class.return_value.invoke.return_value = command_result(
            stderr=b"device offline", code=1, failure=True
        )

        with patch("rv_android_core.util.android.android.logging") as mock_logging:
            with pytest.raises(TimeoutError):
                Android._wait_for_boot("emulator-5554", boot_timeout=10)

            warnings = [
                call_args[0][0] for call_args in mock_logging.warning.call_args_list
            ]

        probe_failures = [w for w in warnings if "ADB probe failed" in w]
        assert probe_failures, f"no probe-failure diagnostic emitted: {warnings}"
        first = probe_failures[0]
        assert "emulator-5554" in first
        assert "device offline" in first
        assert "exit code 1" in first

    def test_empty_stdout_is_reported_as_such(self, mock_command_class, fake_clock):
        """An answered probe with an unset property is distinct from a broken
        channel, and says so."""
        mock_command_class.return_value.invoke.side_effect = [
            command_result(stdout=b""),
            command_result(stdout=b"stopped"),
            command_result(stdout=b"1"),
        ]

        with patch("rv_android_core.util.android.android.logging") as mock_logging:
            Android._wait_for_boot("emulator-5554", boot_timeout=180)

            warnings = [
                call_args[0][0] for call_args in mock_logging.warning.call_args_list
            ]

        assert any("empty output" in w and "emulator-5554" in w for w in warnings)
        assert not any("ADB probe failed" in w for w in warnings)


class TestTimeoutResolution:
    """Argument, then environment, then default — and never silently."""

    def test_unset_environment_uses_the_default(self):
        assert (
            Android._resolve_timeout(ENV_EMULATOR_BOOT_TIMEOUT, 300)
            == DEFAULT_BOOT_TIMEOUT_SECONDS
        )

    def test_valid_integer_is_honoured(self, monkeypatch):
        monkeypatch.setenv(ENV_EMULATOR_BOOT_TIMEOUT, "600")
        assert Android._resolve_timeout(ENV_EMULATOR_BOOT_TIMEOUT, 300) == 600

    def test_explicit_argument_overrides_the_environment(self, monkeypatch):
        monkeypatch.setenv(ENV_EMULATOR_BOOT_TIMEOUT, "600")
        assert Android._resolve_timeout(ENV_EMULATOR_BOOT_TIMEOUT, 300, 10) == 10

    def test_invalid_value_raises_rather_than_defaulting(self, monkeypatch):
        """A capital O typed for a zero must not quietly become 300."""
        monkeypatch.setenv(ENV_EMULATOR_BOOT_TIMEOUT, "30O")
        with pytest.raises(ValueError):
            Android._resolve_timeout(ENV_EMULATOR_BOOT_TIMEOUT, 300)

    def test_boot_budget_defaults_to_300_when_unset(
        self, mock_command_class, fake_clock
    ):
        """The budget in force with no override is the documented default."""
        mock_command_class.return_value.invoke.return_value = command_result(
            stdout=b"booting"
        )

        with pytest.raises(
            TimeoutError,
            match=f"did not boot within {DEFAULT_BOOT_TIMEOUT_SECONDS}s",
        ):
            Android._wait_for_boot("emulator-5554")

    def test_boot_budget_reads_the_environment(
        self, mock_command_class, fake_clock, monkeypatch
    ):
        monkeypatch.setenv(ENV_EMULATOR_BOOT_TIMEOUT, "45")
        mock_command_class.return_value.invoke.return_value = command_result(
            stdout=b"booting"
        )

        with pytest.raises(TimeoutError, match="did not boot within 45s"):
            Android._wait_for_boot("emulator-5554")

    def test_probes_carry_the_adb_command_timeout(
        self, mock_command_class, fake_clock, monkeypatch
    ):
        monkeypatch.setenv(ENV_ADB_CMD_TIMEOUT, "17")
        mock_command_class.return_value.invoke.side_effect = [
            command_result(stdout=b"stopped"),
            command_result(stdout=b"1"),
        ]

        Android._wait_for_boot("emulator-5554", boot_timeout=180)

        for call_args in mock_command_class.call_args_list:
            assert call_args[0][2] == 17


class TestInstallTimeout:
    """`adb install` runs under a timeout; it had none before."""

    def _app(self):
        app = MagicMock()
        app.name = "cryptoapp.apk"
        app.path = "/apks/cryptoapp.apk"
        app.package_name = "br.unb.cic.cryptoapp"
        return app

    def test_install_command_carries_a_non_none_timeout(self, mock_command_class):
        mock_command_class.return_value.invoke.return_value = command_result(
            stdout=b"/apks/cryptoapp.apk"
        )

        Android.install_apk(self._app(), "emulator-5554")

        install_calls = [
            call_args
            for call_args in mock_command_class.call_args_list
            if "install" in call_args[0][1]
        ]
        assert len(install_calls) == 1
        assert install_calls[0][0][2] == DEFAULT_APK_INSTALL_TIMEOUT_SECONDS

    def test_install_timeout_reads_the_environment(
        self, mock_command_class, monkeypatch
    ):
        monkeypatch.setenv(ENV_APK_INSTALL_TIMEOUT, "900")
        mock_command_class.return_value.invoke.return_value = command_result(
            stdout=b"/apks/cryptoapp.apk"
        )

        Android.install_apk(self._app(), "emulator-5554")

        install_calls = [
            call_args
            for call_args in mock_command_class.call_args_list
            if "install" in call_args[0][1]
        ]
        assert install_calls[0][0][2] == 900

    def test_every_device_command_declares_a_timeout(self, mock_command_class):
        """No `Command` in the install path may fall back to
        `communicate(timeout=None)`."""
        mock_command_class.return_value.invoke.return_value = command_result(
            stdout=b"/apks/cryptoapp.apk"
        )

        Android.install_apk(self._app(), "emulator-5554")

        for call_args in mock_command_class.call_args_list:
            assert len(call_args[0]) == 3, f"no timeout on {call_args[0]}"
            assert call_args[0][2] is not None

    def test_adb_cmd_timeout_default_applies_to_probe_commands(
        self, mock_command_class
    ):
        mock_command_class.return_value.invoke.return_value = command_result(
            stdout=b"/apks/cryptoapp.apk"
        )

        Android.install_apk(self._app(), "emulator-5554")

        root_calls = [
            call_args
            for call_args in mock_command_class.call_args_list
            if call_args[0][1][-1] == "root"
        ]
        assert root_calls[0][0][2] == DEFAULT_ADB_CMD_TIMEOUT_SECONDS


class TestKillSettlingDelay:
    """The post-kill delay is a port release, so it follows a successful kill."""

    def test_delay_is_taken_when_the_kill_succeeds(self, mock_command_class):
        mock_command_class.return_value.invoke.return_value = command_result(
            stdout=b"OK"
        )

        with patch("time.sleep") as mock_sleep:
            Android.kill_emulator("RVSec", "emulator-5556")

        mock_sleep.assert_called_once_with(EMULATOR_KILL_SETTLE_SECONDS)

    def test_delay_is_skipped_when_the_kill_fails(self, mock_command_class):
        """Registration now happens before launch, so teardown fires on paths
        where no emulator process ever existed. Waiting ten seconds for a port
        that was never bound taxes every failed launch for no effect."""
        mock_command_class.return_value.invoke.return_value = command_result(
            stderr=b"error: device 'emulator-5556' not found", code=1, failure=True
        )

        with patch("time.sleep") as mock_sleep:
            Android.kill_emulator("RVSec", "emulator-5556")

        mock_sleep.assert_not_called()

    def test_repeated_identical_failures_are_reported_once(
        self, mock_command_class, fake_clock
    ):
        """`-delay-adb` makes ADB answer "device offline" for most of a healthy
        boot, so warning on every poll would bury the diagnostic in dozens of
        identical lines. Each distinct reason is reported the first time it
        appears, and a change of reason is reported again."""
        mock_command_class.return_value.invoke.side_effect = (
            [
                command_result(
                    stderr=b"device 'emulator-5554' not found", code=1, failure=True
                )
                for _ in range(3)
            ]
            + [
                command_result(stderr=b"device offline", code=1, failure=True)
                for _ in range(3)
            ]
            + [command_result(stdout=b"stopped"), command_result(stdout=b"1")]
        )

        with patch("rv_android_core.util.android.android.logging") as mock_logging:
            Android._wait_for_boot("emulator-5554", boot_timeout=180)

            warnings = [
                call_args[0][0] for call_args in mock_logging.warning.call_args_list
            ]

        probe_failures = [w for w in warnings if "ADB probe failed" in w]
        assert (
            len(probe_failures) == 2
        ), f"expected one line per distinct reason, got {probe_failures}"
        assert "not found" in probe_failures[0]
        assert "device offline" in probe_failures[1]
