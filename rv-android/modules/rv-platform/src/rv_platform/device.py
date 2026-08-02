# rv_platform/device.py
"""
Device resolution for RV-Platform.

Holds the single derivation of the emulator port and ADB serial that a task
addresses, shared by every site that needs them.
"""

from typing import Any, Mapping, Optional, Tuple

# Port of the single emulator used when no device_port is injected.
DEFAULT_DEVICE_PORT = 5554


def resolve_device(parameters: Optional[Mapping[str, Any]]) -> Tuple[int, str]:
    """
    Resolve the emulator port and the ADB serial of a task's device.

    Every site that addresses the device — the boot, the app installation and
    the logcat capture — derives its target here, so a task supplying only one
    of the two keys cannot boot one device and install or capture on another
    (INV-PLT-28). The serial follows from the port unless the task supplies an
    explicit `device_serial`. Independent per-site fallbacks are what this
    replaces: a wrong-device install at least fails loudly, but a wrong-device
    capture raises nothing and yields an empty logcat, zero coverage and an
    empty resume reconstruction.

    It takes the parameters mapping rather than a `Task` because
    `Platform._generate_tasks` is one of the three callers and resolves the
    device while building the `TaskConfiguration` — before any `Task` exists.

    Dynamic port allocation serves parallel Docker containers: each runs one
    emulator on a unique port (5554, 5556, 5558, ...), injected into
    `tool_config.parameters` by ExecutionController when --device-port is given.
    Without it, port 5554 applies (single-emulator mode).

    Args:
        parameters: A task's `tool_config.parameters`, or None when it has none.

    Returns:
        Tuple of (device_port, device_serial)
    """
    params = parameters or {}
    device_port = params.get("device_port", DEFAULT_DEVICE_PORT)
    device_serial = params.get("device_serial", f"emulator-{device_port}")
    return device_port, device_serial
