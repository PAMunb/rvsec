"""
Tests for device resolution — the single derivation shared by every site that
addresses the emulator (INV-PLT-28).

The cross-site class below is the regression pin for the defect that motivated
`resolve_device`: with only `device_port` injected — the form the tool DSL
produces for `--tools "monkey@device_port=5558"` — boot and install resolved to
`emulator-5558` while logcat captured `emulator-5554`. A wrong-device capture
raises nothing, so it surfaced only as an empty logcat and zero coverage.
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.task import Task, TaskConfiguration, ToolConfig
from rv_platform.components.emulator import EmulatorComponent
from rv_platform.components.logcat import LogcatComponent
from rv_platform.device import DEFAULT_DEVICE_PORT, resolve_device

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(parameters, device_id=None):
    """Build a real Task whose tool_config carries the given parameters.

    `device_id` defaults to the resolved serial, which is what
    `Platform._generate_tasks` stores. Pass it explicitly to make the stored
    value disagree with the parameters — the only way to tell a component that
    resolves from the parameters apart from one that reads `device_id`.
    """
    config = TaskConfiguration(
        apk_name="cryptoapp.apk",
        repetition=1,
        timeout=60,
        tool_config=ToolConfig(name="monkey", variant="default", parameters=parameters),
        device_id=device_id or resolve_device(parameters)[1],
    )
    task = Task(config)
    task.set_app(MagicMock())
    return task


def _logcat_serial(task):
    """The serial LogcatComponent hands to LogcatManager — where it lands."""
    with patch("rv_platform.components.logcat.LogcatManager") as logcat_manager:
        LogcatComponent(task)
    return logcat_manager.call_args.kwargs["device_serial"]


def _emulator_device(task):
    """The (port, serial) EmulatorComponent boots and installs on."""
    with patch("rv_platform.components.emulator.EmulatorManager"):
        return EmulatorComponent(task)._resolve_device()


# ===========================================================================
# resolve_device()
# ===========================================================================


class TestResolveDevice:
    def test_both_keys_are_honoured(self):
        """Explicit values are used exactly as injected."""
        assert resolve_device(
            {"device_port": 5558, "device_serial": "emulator-5558"}
        ) == (
            5558,
            "emulator-5558",
        )

    def test_port_only_derives_the_matching_serial(self):
        """The serial follows the port, so both name one device."""
        assert resolve_device({"device_port": 5558}) == (5558, "emulator-5558")

    def test_serial_only_keeps_the_default_port(self):
        """An explicit serial is honoured; the port keeps its default."""
        assert resolve_device({"device_serial": "emulator-5560"}) == (
            DEFAULT_DEVICE_PORT,
            "emulator-5560",
        )

    @pytest.mark.parametrize("parameters", [{}, None])
    def test_no_parameters_uses_the_5554_defaults(self, parameters):
        """Single-emulator mode: port and serial aligned on 5554."""
        assert resolve_device(parameters) == (5554, "emulator-5554")


# ===========================================================================
# Every site addresses one device (INV-PLT-28)
# ===========================================================================


class TestEverySiteAddressesOneDevice:
    """Boot, install, logcat and TaskConfiguration.device_id must agree."""

    def test_port_only_is_seen_by_boot_install_and_logcat(self):
        """The regression case: no device_serial key anywhere in the parameters."""
        task = _make_task({"device_port": 5558})

        port, install_serial = _emulator_device(task)

        assert port == 5558
        assert install_serial == "emulator-5558"
        assert _logcat_serial(task) == "emulator-5558"
        assert task.config.device_id == "emulator-5558"

    def test_a_stale_device_id_is_consulted_by_no_site(self):
        """No component may resolve from `device_id` (spec: "Logcat captures the
        device that was booted").

        With `device_id` left at "emulator-5554" while the parameters say 5558,
        a component that reads it addresses the wrong device. This is what the
        realistic case above cannot show: there `device_id` already agrees, so a
        component reading it lands on the right serial by coincidence — the
        fallback-chaining agreement design D10 rejected as option (a).
        """
        task = _make_task({"device_port": 5558}, device_id="emulator-5554")

        port, install_serial = _emulator_device(task)

        assert port == 5558
        assert install_serial == "emulator-5558"
        assert _logcat_serial(task) == "emulator-5558"

    def test_both_keys_are_honoured_at_every_site(self):
        """The form ExecutionController injects: all three keys together."""
        task = _make_task({"device_port": 5560, "device_serial": "emulator-5560"})

        port, install_serial = _emulator_device(task)

        assert port == 5560
        assert install_serial == "emulator-5560"
        assert _logcat_serial(task) == "emulator-5560"
        assert task.config.device_id == "emulator-5560"

    def test_no_keys_yields_the_5554_defaults_at_every_site(self):
        """Single-emulator mode, the shape every non-parallel run takes."""
        task = _make_task({})

        port, install_serial = _emulator_device(task)

        assert port == 5554
        assert install_serial == "emulator-5554"
        assert _logcat_serial(task) == "emulator-5554"
        assert task.config.device_id == "emulator-5554"
