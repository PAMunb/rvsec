"""
Manage Android emulator lifecycle and APK operations via ADB.

Provide utilities for starting, stopping, and interacting with Android emulators
using ADB (Android Debug Bridge). Handle APK installation, uninstallation, and
runtime permission granting for automated testing workflows.
"""

import logging as logging_api
import subprocess
import time
from contextlib import contextmanager

from rv_android_core.commands.command import Command
from rv_android_core.domain.app import App
from rv_android_core.util import utils
from rv_android_core.util.error.exceptions import RVCommandTimeoutError

logging = logging_api.getLogger(__name__)


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
    - Provides boot wait logic with multi-phase verification (boot animation,
      sys.boot_completed, root, remount)

    ### Key Features:

    - Parallel emulator support via configurable device ports
    - Multi-phase boot verification with per-command timeout and retry
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

        Args:
            avd_name: Name of the AVD (used for logging only).
            device_name: ADB device serial (default: "emulator-5554").
        """
        logging.info(f"Killing emulator {device_name}...")
        kill_emulator_cmd = Command("adb", ["-s", device_name, "emu", "kill"])
        kill_emulator_cmd.invoke()
        time.sleep(10)
        logging.info(f"Emulator {device_name} has been killed")

    @staticmethod
    def _wait_for_boot(device_name: str = "emulator-5554", boot_timeout: int = 180):
        """Wait for an Android emulator to fully boot and become ready.

        Run four sequential verification phases: boot animation stop,
        sys.boot_completed property, ADB root, and filesystem remount.
        Each phase retries on ADB command timeouts until the overall
        boot_timeout is exceeded.

        Args:
            device_name: ADB device serial (default: "emulator-5554").
            boot_timeout: Maximum total seconds to wait across all phases
                (default: 180).

        Raises:
            TimeoutError: If any phase does not complete within boot_timeout.
        """
        cmd_timeout = 30  # timeout per individual adb command
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
        while True:
            if time.time() - start > boot_timeout:
                raise TimeoutError(f"{device_name} did not boot within {boot_timeout}s")
            try:
                check_result = check_emulator_cmd.invoke()
                if check_result.stdout.strip().decode("ascii") == "stopped":
                    break
            except RVCommandTimeoutError:
                logging.warning(
                    f"ADB boot check timed out for {device_name}, retrying..."
                )
            time.sleep(5)
            logging.info(f"Waiting for {device_name} to boot")

        # Phase 2: Wait for sys.boot_completed.
        # Same retry pattern — the shell command can time out if the emulator is slow.
        wait_emulator_cmd = Command(
            "adb",
            [
                "-s",
                device_name,
                "wait-for-device",
                "shell",
                "'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 1; done;'",
            ],
            cmd_timeout,
        )
        while True:
            if time.time() - start > boot_timeout:
                raise TimeoutError(
                    f"{device_name} sys.boot_completed not set within {boot_timeout}s"
                )
            try:
                wait_emulator_cmd.invoke()
                break
            except RVCommandTimeoutError:
                logging.warning(
                    f"ADB boot_completed check timed out for {device_name}, retrying..."
                )
            time.sleep(5)

        # Phase 3: Root and remount.
        # Both commands can time out when the emulator is slow to respond after boot.
        root_cmd = Command(
            "adb", ["-s", device_name, "wait-for-device", "root"], cmd_timeout
        )
        while True:
            if time.time() - start > boot_timeout:
                raise TimeoutError(f"{device_name} root failed within {boot_timeout}s")
            try:
                if not root_cmd.invoke().stderr.strip().decode("ascii"):
                    break
            except RVCommandTimeoutError:
                logging.warning(
                    f"ADB root command timed out for {device_name}, retrying..."
                )
            time.sleep(5)

        adb_remount = Command(
            "adb", ["-s", device_name, "wait-for-device", "remount"], cmd_timeout
        )
        while True:
            if time.time() - start > boot_timeout:
                raise TimeoutError(
                    f"{device_name} remount failed within {boot_timeout}s"
                )
            try:
                if not adb_remount.invoke().stderr.strip().decode("ascii"):
                    break
            except RVCommandTimeoutError:
                logging.warning(
                    f"ADB remount command timed out for {device_name}, retrying..."
                )
            time.sleep(5)

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
        cls.grant_permissions(app, device_name)

    @classmethod
    def install_apk(cls, app: App, device_name: str = "emulator-5554"):
        """Install an APK on the target device via ADB.

        Resolve the APK path via readlink, then install with -r (replace)
        and -g (grant all permissions at install time) flags. The device
        is rooted before installation to ensure write access.

        Args:
            app: Application containing APK path and name.
            device_name: ADB device serial (default: "emulator-5554").

        Raises:
            RuntimeError: If ADB install reports a non-zero exit code.
        """
        logging.info("Installing APK: {0} on {1}".format(app.name, device_name))
        root_cmd = Command("adb", ["-s", device_name, "root"])
        result = root_cmd.invoke()
        readlink_cmd = Command("readlink", ["-f", app.path])
        readlink_result = readlink_cmd.invoke()
        apk_path = readlink_result.stdout.strip().decode("ascii")
        install_cmd = Command(
            "adb", ["-s", device_name, "install", "-r", "-g", apk_path]
        )
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
        uninstall_cmd = Command(
            "adb", ["-s", device_name, "uninstall", app.package_name]
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
            )
            grant_cmd.invoke()
