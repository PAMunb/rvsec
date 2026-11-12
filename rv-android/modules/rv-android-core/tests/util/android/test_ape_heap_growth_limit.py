"""Tests for Android.set_ape_heap_growth_limit, the heap of APE's VM.

The `ape` built-in and APE-RV both call it before their launch (`tools` INV-TOOL-30,
`aperv` INV-APV-73). `Command` is replaced, so no adb runs: each test states the
results the device would give and reads back the commands that were built.
"""

from unittest.mock import patch

import pytest
from rv_android_core.commands.command_result import CommandResult
from rv_android_core.constants import APE_HEAP_GROWTH_LIMIT, HEAP_GROWTH_LIMIT_PROPERTY
from rv_android_core.util.android.android import (
    DEFAULT_ADB_CMD_TIMEOUT_SECONDS,
    Android,
)
from rv_android_core.util.error.exceptions import RVToolExecutionError

SETPROP = [
    "-s",
    "emulator-5556",
    "shell",
    "su",
    "0",
    "setprop",
    "dalvik.vm.heapgrowthlimit",
    "512m",
]
GETPROP = ["-s", "emulator-5556", "shell", "getprop", "dalvik.vm.heapgrowthlimit"]


class _Device:
    """Stands in for `Command`: records each command at invoke time and answers it
    with the next of the given results."""

    def __init__(self, *results):
        self.results = list(results)
        self.invoked = []

    def __call__(self, command, args, timeout):
        device = self

        class _Invocable:
            def invoke(self):
                device.invoked.append((command, list(args), timeout))
                return device.results.pop(0)

        return _Invocable()


def test_the_values_are_the_shared_constants():
    assert APE_HEAP_GROWTH_LIMIT == "512m"
    assert HEAP_GROWTH_LIMIT_PROPERTY == "dalvik.vm.heapgrowthlimit"


def test_setprop_as_root_runs_before_the_getprop():
    device = _Device(CommandResult(0, b"", b""), CommandResult(0, b"512m\n", b""))

    with patch("rv_android_core.util.android.android.Command", device):
        Android.set_ape_heap_growth_limit("aperv", "emulator-5556")

    assert device.invoked == [
        ("adb", SETPROP, DEFAULT_ADB_CMD_TIMEOUT_SECONDS),
        ("adb", GETPROP, DEFAULT_ADB_CMD_TIMEOUT_SECONDS),
    ]


def test_a_failed_setprop_raises_and_reads_nothing_back():
    device = _Device(CommandResult(1, b"", b"su: not found"))

    with (
        patch("rv_android_core.util.android.android.Command", device),
        pytest.raises(RVToolExecutionError) as raised,
    ):
        Android.set_ape_heap_growth_limit("ape", "emulator-5556")

    assert raised.value.tool_name == "ape"
    assert "exit code 1" in str(raised.value)
    assert "su: not found" in str(raised.value)
    assert [args for _, args, _ in device.invoked] == [SETPROP]


@pytest.mark.parametrize(
    "result, shown",
    [
        (CommandResult(0, b"192m\n", b""), "'192m'"),
        (CommandResult(0, b"", b""), "''"),
        (CommandResult(1, b"512m\n", b""), "exit code 1"),
    ],
    ids=["avd-default", "empty", "getprop-failed"],
)
def test_a_limit_that_does_not_read_back_raises_naming_the_value(result, shown):
    device = _Device(CommandResult(0, b"", b""), result)

    with (
        patch("rv_android_core.util.android.android.Command", device),
        pytest.raises(RVToolExecutionError) as raised,
    ):
        Android.set_ape_heap_growth_limit("aperv", "emulator-5556")

    assert raised.value.tool_name == "aperv"
    assert "dalvik.vm.heapgrowthlimit reads" in str(raised.value)
    assert shown in str(raised.value)
    assert len(device.invoked) == 2
