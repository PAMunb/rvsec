"""
Manage Android emulator lifecycle and APK operations via ADB.

Provide utilities for starting, stopping, and interacting with Android emulators
using ADB (Android Debug Bridge). Handle APK installation, uninstallation, and
runtime permission granting for automated testing workflows.
"""

import logging as logging_api
import os
import subprocess
import time
from contextlib import contextmanager
from typing import Optional

from rv_android_core.commands.command import Command
from rv_android_core.constants import (
    ENV_ADB_CMD_TIMEOUT,
    ENV_APK_INSTALL_TIMEOUT,
    ENV_EMULATOR_BOOT_TIMEOUT,
)
from rv_android_core.domain.app import App
from rv_android_core.util import utils
from rv_android_core.util.error.exceptions import RVCommandTimeoutError

logging = logging_api.getLogger(__name__)

# Total seconds allowed across both boot phases. Provisional: 180 s was
# exceeded 322 times in the recorded history of the project (p50 182 s,
# p90 210 s, max 871 s), so 300 s is an improvement of unknown sufficiency.
# The real distribution is collected by observing production runs; when boot
# timeouts appear, RV_EMULATOR_BOOT_TIMEOUT is what rises.
DEFAULT_BOOT_TIMEOUT_SECONDS = 300

# Seconds allowed for a single ADB probe. A probe that exceeds it is killed
# and retried against the remaining boot budget.
DEFAULT_ADB_CMD_TIMEOUT_SECONDS = 30

# Seconds allowed for `adb install`. Errs long deliberately: no distribution
# of install durations exists, and killing a healthy slow install on a
# contended host is the worse failure mode. It exists to bound a hung
# install, which would otherwise hold the emulator session open for the
# whole task.
DEFAULT_APK_INSTALL_TIMEOUT_SECONDS = 600

# Seconds between two boot probes. Deliberately a module constant and not an
# environment variable: how often the device is asked is not a property of
# the host, only how long it is given.
BOOT_POLL_INTERVAL_SECONDS = 5

# Seconds to wait after a successful `adb emu kill` so the emulator releases
# its port before the next task binds it.
EMULATOR_KILL_SETTLE_SECONDS = 10


class Android:
    """
    Manage Android emulator lifecycle and APK operations via ADB.

    Provide a stateless utility interface for emulator management and APK
    handling. All methods are class methods or static methods, enabling
    direct invocation without instantiation.

    ### Architectural Decisions:

    - All ADB communication goes through Command objects with timeout support,
      preventing indefinite hangs during emulator interaction
    - Context manager pattern for emulator lifecycle ensures cleanup even on errors
    - Port-based device targeting enables parallel emulator execution

    ### Role in the System:

    - Called by EmulatorComponent in rv-platform for emulator lifecycle management
    - Handles APK installation and permission granting during task execution
    - Provides boot wait logic with two-phase verification (boot animation,
      then sys.boot_completed)

    ### Key Features:

    - Parallel emulator support via configurable device ports
    - Two-phase boot verification against one shared budget, with per-command
      timeout and retry
    - APK installation with automatic permission granting
    """

    @classmethod
    @contextmanager
    def create_emulator(cls, avd_name, no_window=False, device_port: int = 5554):
        """Create and manage an Android emulator with guaranteed cleanup.

        Context manager that starts an emulator, yields control, and kills
        the emulator in the finally block regardless of success or failure.

        Args:
            avd_name: Name of the Android Virtual Device to launch.
            no_window: Whether to run the emulator headless.
            device_port: ADB port for device targeting (default: 5554).

        Yields:
            Reference to the started emulator process.
        """
        device_name = f"emulator-{device_port}"
        emulator = None
        try:
            logging.info(f"Starting emulator {avd_name} on {device_name}")
            emulator = cls.start_emulator(avd_name, no_window, device_port)
            yield emulator
        except Exception as e:
            logging.error(f"Error while using emulator: {e}")
            raise
        finally:
            if emulator:
                logging.info(f"Cleaning up emulator {avd_name} ({device_name})")
                try:
                    cls.kill_emulator(avd_name, device_name)
                except Exception as cleanup_error:
                    logging.error(f"Error during emulator cleanup: {cleanup_error}")

    @classmethod
    def start_emulator(cls, avd_name: str, no_window: bool, device_port: int = 5554):
        """Start an Android emulator and wait for boot completion.

        Launch the emulator as a daemon process with flags optimized for
        parallel testing (read-only, no cache, no snapshot), then block
        until the device is fully booted and remounted.

        Args:
            avd_name: Name of the Android Virtual Device to launch.
            no_window: Whether to run the emulator headless.
            device_port: ADB port for device targeting (default: 5554).
        """
        device_name = f"emulator-{device_port}"
        logging.info(f"Starting emulator on {device_name}")

        args = [
            "-avd",
            avd_name,
            "-port",
            str(device_port),  # CRITICAL: Port assignment for parallel execution
            "-read-only",  # CRITICAL: Allows multiple instances of same AVD
            "-no-cache",  # CRITICAL: Prevents cache conflicts between instances
            "-no-boot-anim",  # disable animation for faster boot
            "-noaudio",  # disable audio support
            "-no-snapshot-save",  # do not auto-save to snapshot on exit: abandon changed state
            "-delay-adb",
        ]  # delay adb communication till boot completes
        if no_window:
            args.append("-no-window")  # disable graphical window display

        start_emulator_cmd = Command("emulator", args)
        # DEVNULL: emulator output is never consumed, and newer emulator versions
        # fail to register with ADB when stdout is a pipe (isatty behavior change)
        emulator_proc = start_emulator_cmd.invoke_as_deamon(
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        cls._wait_for_boot(device_name)

    @classmethod
    def kill_emulator(cls, avd_name, device_name: str = "emulator-5554"):
        """Terminate a specific Android emulator instance.

        Send 'adb emu kill' targeting the device via the -s flag. Does NOT
        kill the ADB server or remove AVD lock files, as those are shared
        resources needed by other emulator instances in parallel execution.

        The settling delay that follows the kill is taken only when the kill
        succeeded. It exists to let the emulator release its port before the
        next task binds it, which is meaningless when nothing was killed —
        and teardown now runs on paths where no emulator process ever came up.

        Args:
            avd_name: Name of the AVD (used for logging only).
            device_name: ADB device serial (default: "emulator-5554").
        """
        logging.info(f"Killing emulator {device_name}...")
        cmd_timeout = cls._resolve_timeout(
            ENV_ADB_CMD_TIMEOUT, DEFAULT_ADB_CMD_TIMEOUT_SECONDS
        )
        kill_emulator_cmd = Command(
            "adb", ["-s", device_name, "emu", "kill"], cmd_timeout
        )
        kill_result = kill_emulator_cmd.invoke()
        if kill_result.is_failure():
            logging.info(
                f"No emulator answered on {device_name} "
                f"(exit code {kill_result.code}): "
                f"{kill_result.get_combined_output()}"
            )
            return
        time.sleep(EMULATOR_KILL_SETTLE_SECONDS)
        logging.info(f"Emulator {device_name} has been killed")

    @staticmethod
    def _resolve_timeout(
        env_name: str, default: int, override: Optional[int] = None
    ) -> int:
        """Resolve a timeout as: explicit argument, then environment, then default.

        A value that is set but is not a valid integer raises `ValueError`
        rather than reverting to the default. A mistyped budget that quietly
        becomes the default is indistinguishable from a working configuration
        until an experiment fails, so it must fail at the point of use.

        Args:
            env_name: Name of the environment variable to consult.
            default: Value in force when neither an override nor the variable
                is supplied.
            override: Explicit value; wins over both other sources when given.

        Returns:
            The number of seconds in force.

        Raises:
            ValueError: If the environment variable is set to a non-integer.
        """
        if override is not None:
            return override
        env_value = os.environ.get(env_name)
        if env_value is None:
            return default
        return int(env_value)

    @staticmethod
    def _wait_for_boot(
        device_name: str = "emulator-5554", boot_timeout: Optional[int] = None
    ):
        """Wait for an Android emulator to fully boot and become ready.

        Run two sequential verification phases against a single shared budget
        measured from one timestamp: the boot animation must report `stopped`,
        then `sys.boot_completed` must read `1`. Each phase retries on ADB
        command timeouts — ADB responds slowly during early boot — until the
        shared budget is exhausted.

        Both phases poll from Python and inspect the returned `CommandResult`
        before acting on it. `Command.invoke()` raises only on timeout and on
        a local `OSError`; a non-zero exit is reported exclusively through the
        result, so "it did not raise" says nothing about whether the command
        worked. Iteration in particular must stay in Python: `Command` spawns
        processes with `shell=False`, so a loop embedded in a device-side
        shell string reaches the device as one quoted word and fails with
        "command not found".

        Phase 1 is a coarse gate only. The emulator is launched with
        `-no-boot-anim`, so the animation service can report `stopped` before
        the Android framework is usable; phase 2 is the authoritative signal.

        Phase 3 (`adb root` + `adb remount`) was intentionally removed
        (commit c0274def, gh50 §17). The emulator is launched with
        `-read-only`, which causes the qemu layer to reject root/remount;
        on API 30+ that rejection populates stderr with "remount failed",
        making the prior `if not stderr.strip(): break` check loop forever
        until boot_timeout. None of the runtime tools (APE, APE-RV, Monkey,
        FastBot) require system-partition writes — all targets land in
        `/data/local/tmp/` or `/sdcard/`, both world-writable on stock
        images.

        Args:
            device_name: ADB device serial (default: "emulator-5554").
            boot_timeout: Maximum total seconds to wait across both phases.
                When None, resolved from RV_EMULATOR_BOOT_TIMEOUT and then
                from the module default. The parameter is retained so tests
                can inject a budget without patching the environment.

        Raises:
            TimeoutError: If either phase exhausts the shared budget. The
                message names the phase, so the two failure modes stay
                separable in stored error_message values.
            ValueError: If a timeout environment variable holds a
                non-integer value.
        """
        boot_timeout = Android._resolve_timeout(
            ENV_EMULATOR_BOOT_TIMEOUT, DEFAULT_BOOT_TIMEOUT_SECONDS, boot_timeout
        )
        cmd_timeout = Android._resolve_timeout(
            ENV_ADB_CMD_TIMEOUT, DEFAULT_ADB_CMD_TIMEOUT_SECONDS
        )
        start = time.time()
        logging.info(f"Waiting for {device_name} to boot (timeout={boot_timeout}s)")

        # Phase 1: Wait for boot animation to stop.
        # The invoke() is inside the loop so that RVCommandTimeoutError (raised when
        # ADB is slow to respond during early boot) is caught and retried instead of
        # propagating immediately and aborting the entire boot wait.
        check_emulator_cmd = Command(
            "adb",
            ["-s", device_name, "shell", "getprop", "init.svc.bootanim"],
            cmd_timeout,
        )
        # Each distinct probe failure is reported once. The emulator is launched
        # with `-delay-adb`, so ADB legitimately answers "device not found" and
        # then "device offline" for most of a healthy boot; warning on every
        # poll would emit dozens of identical lines per task and bury the case
        # this diagnostic exists for. Reporting each new reason the moment it
        # first appears is what makes a genuinely broken ADB visible in seconds
        # instead of indistinguishable from a slow boot until the whole budget
        # is consumed.
        last_reported_failure = None
        while True:
            if time.time() - start > boot_timeout:
                raise TimeoutError(f"{device_name} did not boot within {boot_timeout}s")
            try:
                check_result = check_emulator_cmd.invoke()
                if check_result.is_failure():
                    reason = check_result.get_combined_output()
                    if reason != last_reported_failure:
                        last_reported_failure = reason
                        logging.warning(
                            f"ADB probe failed for {device_name} "
                            f"(exit code {check_result.code}): {reason}"
                        )
                elif not check_result.stdout.strip():
                    if last_reported_failure != "":
                        last_reported_failure = ""
                        logging.warning(
                            f"ADB probe for {device_name} returned empty output "
                            f"for init.svc.bootanim; the device answered but the "
                            f"property is not set"
                        )
                elif check_result.stdout.strip() == b"stopped":
                    break
            except RVCommandTimeoutError:
                logging.warning(
                    f"ADB boot check timed out for {device_name}, retrying..."
                )
            time.sleep(BOOT_POLL_INTERVAL_SECONDS)
            logging.info(f"Waiting for {device_name} to boot")

        # Phase 2: Wait for sys.boot_completed, the authoritative readiness
        # signal. The wait ends only on a probe that both succeeded and read
        # exactly "1"; every other outcome keeps polling until the shared
        # budget expires.
        wait_emulator_cmd = Command(
            "adb",
            ["-s", device_name, "shell", "getprop", "sys.boot_completed"],
            cmd_timeout,
        )
        last_reported_failure = None
        while True:
            if time.time() - start > boot_timeout:
                raise TimeoutError(
                    f"{device_name} sys.boot_completed not set within {boot_timeout}s"
                )
            try:
                wait_result = wait_emulator_cmd.invoke()
                if wait_result.is_failure():
                    reason = wait_result.get_combined_output()
                    if reason != last_reported_failure:
                        last_reported_failure = reason
                        logging.warning(
                            f"ADB boot_completed probe failed for {device_name} "
                            f"(exit code {wait_result.code}): {reason}"
                        )
                elif wait_result.stdout.strip() == b"1":
                    break
            except RVCommandTimeoutError:
                logging.warning(
                    f"ADB boot_completed check timed out for {device_name}, retrying..."
                )
            time.sleep(BOOT_POLL_INTERVAL_SECONDS)

        logging.info(f"{device_name} booted!")
        elapsed = time.time() - start
        logging.info(f"{device_name} took {utils.to_readable_time(elapsed)} to boot")

    @classmethod
    def simulate_reboot(cls):
        """Simulate a device reboot by broadcasting BOOT_COMPLETED intent.

        Broadcast the boot completed intent and then wait for the emulator
        to finish its boot sequence. Used for scenarios that need a fresh
        device state without a full emulator restart.
        """
        logging.info("Starting reboot simulation")
        sim_reboot_cmd = Command(
            "adb",
            ["shell", "am", "broadcast", "-a", "android.intent.action.BOOT_COMPLETED"],
            15,
        )
        sim_reboot_cmd.invoke()
        time.sleep(1)
        cls._wait_for_boot()

    @classmethod
    def install_with_permissions(cls, app: App, device_name: str = "emulator-5554"):
        """Install an APK and grant all declared runtime permissions.

        Args:
            app: Application containing APK path, package name, and permissions.
            device_name: ADB device serial (default: "emulator-5554").

        Raises:
            RuntimeError: If APK installation fails.
        """
        cls.install_apk(app, device_name)
        # install_apk already passes `-g`, which grants every runtime permission
        # the manifest declares. The per-permission loop below issues a stream
        # of `adb shell pm grant` calls that (a) duplicate what -g did and
        # (b) noisily fail with exit 255 on install-time permissions
        # (FOREGROUND_SERVICE_DATA_SYNC, RECEIVE_BOOT_COMPLETED) or on
        # permissions ART already reports as granted. Disabled for now; if
        # we ever need it for custom/runtime-only permissions not covered by
        # -g, reintroduce with a filter on `protection=dangerous` and
        # already-granted detection.
        # cls.grant_permissions(app, device_name)

    @classmethod
    def install_apk(cls, app: App, device_name: str = "emulator-5554"):
        """Install an APK on the target device via ADB.

        Resolve the APK path via readlink, then install with -r (replace)
        and -g (grant all permissions at install time) flags. Installation
        needs no elevated privileges: the APK is handed to the package
        manager, which owns the write.

        The `adb root` attempt that precedes it is expected to be rejected,
        because the emulator runs with `-read-only`; its result is logged and
        installation proceeds regardless.

        Args:
            app: Application containing APK path and name.
            device_name: ADB device serial (default: "emulator-5554").

        Raises:
            RuntimeError: If ADB install reports a non-zero exit code. The
                message carries the exit code and the combined output, so the
                INSTALL_FAILED_* reason reaches the caller.
            RVCommandTimeoutError: If the install exceeds
                RV_APK_INSTALL_TIMEOUT.
        """
        logging.info("Installing APK: {0} on {1}".format(app.name, device_name))
        cmd_timeout = cls._resolve_timeout(
            ENV_ADB_CMD_TIMEOUT, DEFAULT_ADB_CMD_TIMEOUT_SECONDS
        )
        install_timeout = cls._resolve_timeout(
            ENV_APK_INSTALL_TIMEOUT, DEFAULT_APK_INSTALL_TIMEOUT_SECONDS
        )
        root_cmd = Command("adb", ["-s", device_name, "root"], cmd_timeout)
        root_result = root_cmd.invoke()
        if root_result.is_failure():
            logging.debug(
                f"adb root rejected on {device_name} "
                f"(exit code {root_result.code}): "
                f"{root_result.get_combined_output()}"
            )
        readlink_cmd = Command("readlink", ["-f", app.path], cmd_timeout)
        readlink_result = readlink_cmd.invoke()
        apk_path = readlink_result.stdout.strip().decode("ascii")
        install_cmd = Command(
            "adb",
            ["-s", device_name, "install", "-r", "-g", apk_path],
            install_timeout,
        )
        result = install_cmd.invoke()
        if result.is_failure():
            error_msg = result.get_combined_output() or "unknown error"
            if "INSTALL_FAILED_UPDATE_INCOMPATIBLE" in error_msg:
                # Signature mismatch (e.g. previously installed instrumented APK).
                # Uninstall the old version and retry.
                logging.info(
                    f"Signature mismatch for {app.name}, uninstalling old version"
                )
                uninstall_cmd = Command(
                    "adb",
                    ["-s", device_name, "uninstall", app.package_name],
                    cmd_timeout,
                )
                uninstall_cmd.invoke()
                result = install_cmd.invoke()
            if result.is_failure():
                error_msg = result.get_combined_output() or "unknown error"
                raise RuntimeError(
                    f"APK installation failed for {app.name} on {device_name} "
                    f"(exit code {result.code}): {error_msg}"
                )

    @classmethod
    def uninstall_apk(cls, app: App, device_name: str = "emulator-5554"):
        """Uninstall an APK from the target device via ADB.

        Args:
            app: Application containing the package name to uninstall.
            device_name: ADB device serial (default: "emulator-5554").
        """
        logging.info("Uninstalling APK: {} from {}".format(app.name, device_name))
        cmd_timeout = cls._resolve_timeout(
            ENV_ADB_CMD_TIMEOUT, DEFAULT_ADB_CMD_TIMEOUT_SECONDS
        )
        uninstall_cmd = Command(
            "adb", ["-s", device_name, "uninstall", app.package_name], cmd_timeout
        )
        uninstall_cmd.invoke()

    @classmethod
    def grant_permissions(cls, app: App, device_name: str = "emulator-5554"):
        """Grant all declared runtime permissions for an installed app.

        Iterate over the app's permission list and issue individual
        'adb shell pm grant' commands for each permission.

        Args:
            app: Application containing package name and permissions list.
            device_name: ADB device serial (default: "emulator-5554").
        """
        cmd_timeout = cls._resolve_timeout(
            ENV_ADB_CMD_TIMEOUT, DEFAULT_ADB_CMD_TIMEOUT_SECONDS
        )
        for permission in app.permissions:
            logging.info("Granting permission {} on {}".format(permission, device_name))
            grant_cmd = Command(
                "adb",
                [
                    "-s",
                    device_name,
                    "shell",
                    "pm",
                    "grant",
                    app.package_name,
                    permission,
                ],
                cmd_timeout,
            )
            grant_cmd.invoke()
