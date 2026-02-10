import logging as logging_api
import time
from contextlib import contextmanager

from rv_android_core.domain.app import App
from rv_android_core.commands.command import Command
from rv_android_core.util import utils


# TODO logging manager
logging = logging_api.getLogger(__name__)


class Android:
    """
    The Android class is responsible for managing the lifecycle of Android emulators
    and handling APK installation/uninstallation. It provides utilities to start,
    stop, and interact with an emulator using ADB (Android Debug Bridge).

    ### Architectural Decisions:
    - Uses ADB commands to communicate with the emulator.
    - Implements a context manager to ensure proper cleanup of emulator instances.
    - Provides automation capabilities for APK installation and permission management.

    ### Role in the System:
    - Supports automated testing by launching and managing Android virtual devices.
    - Enables APK installation and interaction during security and coverage experiments.
    - Ensures that the emulator environment is properly reset before each experiment.
    """

    @classmethod
    @contextmanager
    def create_emulator(cls, avd_name, no_window=False, device_port: int = 5554):
        """
        Context manager for creating and managing an Android emulator.
        Ensures proper cleanup even in case of errors.

        Args:
            avd_name: Name of the Android Virtual Device
            no_window: Whether to run the emulator without a window
            device_port: Emulator port (default: 5554)

        Yields:
            Reference to the emulator
        """
        device_name = f"emulator-{device_port}"
        emulator = None
        try:
            logging.info(f'Starting emulator {avd_name} on {device_name}')
            emulator = cls.start_emulator(avd_name, no_window, device_port)
            yield emulator
        except Exception as e:
            logging.error(f"Error while using emulator: {e}")
            raise
        finally:
            if emulator:
                logging.info(f'Cleaning up emulator {avd_name} ({device_name})')
                try:
                    cls.kill_emulator(avd_name, device_name)
                except Exception as cleanup_error:
                    logging.error(f"Error during emulator cleanup: {cleanup_error}")

    @classmethod
    def start_emulator(cls, avd_name: str, no_window: bool, device_port: int = 5554):
        """
        Start an Android emulator with specific configuration parameters.
        
        Enhanced for parallel execution support with device port assignment.

        Args:
            avd_name (str): Name of the Android Virtual Device to launch (RVSec)
            no_window (bool): Flag to determine whether to run emulator without a graphical window
            device_port (int): Port for emulator (enables parallel execution, default: 5554)

        Returns:
            The emulator process that was started as a daemon

        Notes:
            Configures emulator with settings optimized for parallel testing:
            - Port assignment for parallel execution
            - Read-only mode for multiple AVD instances
            - No cache to prevent conflicts
            - Disabled boot animation
            - No audio
            - No snapshot saving
            - Delayed ADB communication
        """
        device_name = f"emulator-{device_port}"
        logging.info(f'Starting emulator on {device_name}')

        args = ['-avd', avd_name,
                '-port', str(device_port),    # CRITICAL: Port assignment for parallel execution
                '-read-only',                 # CRITICAL: Allows multiple instances of same AVD
                '-no-cache',                  # CRITICAL: Prevents cache conflicts between instances
                '-no-boot-anim',             # disable animation for faster boot
                '-noaudio',                  # disable audio support
                '-no-snapshot-save',         # do not auto-save to snapshot on exit: abandon changed state
                '-delay-adb']                # delay adb communication till boot completes
        if no_window:
            args.append('-no-window')  # disable graphical window display

        start_emulator_cmd = Command('emulator', args)
        
        # CHANGED: Using invoke_as_process instead of invoke_as_deamon to prevent process duplication
        # The invoke_as_deamon method was causing fork-based process duplication in parallel execution,
        # leading to multiple emulator processes on the same port. invoke_as_process uses subprocess.Popen
        # with process groups to avoid this duplication issue.
        # TESTING: Reverting to invoke_as_deamon to check if hanging issue is related to process management
        emulator_proc = start_emulator_cmd.invoke_as_deamon()

        cls._wait_for_boot(device_name)

    @classmethod
    def kill_emulator(cls, avd_name, device_name: str = "emulator-5554"):
        """
        Terminate a specific Android emulator instance.

        Uses 'adb emu kill' which targets a specific device via the -s flag.
        Does NOT kill the ADB server or remove AVD lock files, as those are
        shared resources that would break other emulator instances in parallel execution.

        Args:
            avd_name (str): The name of the AVD (used for logging).
            device_name (str): Device serial for targeting specific emulator (default: "emulator-5554")
        """
        logging.info(f"Killing emulator {device_name}...")
        kill_emulator_cmd = Command('adb', ['-s', device_name, 'emu', 'kill'])
        kill_emulator_cmd.invoke()
        time.sleep(10)
        logging.info(f'Emulator {device_name} has been killed')

    @staticmethod
    def _wait_for_boot(device_name: str = "emulator-5554", boot_timeout: int = 180):
        """
        Wait for an Android emulator to fully boot and become ready.

        Args:
            device_name: Device name to wait for boot (default: "emulator-5554")
            boot_timeout: Maximum seconds to wait for boot (default: 180)

        Raises:
            TimeoutError: If emulator does not boot within boot_timeout seconds.
        """
        cmd_timeout = 30  # timeout per individual adb command
        start = time.time()
        logging.info(f'Waiting for {device_name} to boot (timeout={boot_timeout}s)')

        # Phase 1: Wait for boot animation to stop
        check_emulator_cmd = Command('adb', ['-s', device_name, 'shell', 'getprop', 'init.svc.bootanim'], cmd_timeout)
        check_result = check_emulator_cmd.invoke()
        while check_result.stdout.strip().decode('ascii') != 'stopped':
            if time.time() - start > boot_timeout:
                raise TimeoutError(f'{device_name} did not boot within {boot_timeout}s')
            time.sleep(5)
            logging.info(f'Waiting for {device_name} to boot')
            check_result = check_emulator_cmd.invoke()

        # Phase 2: Wait for sys.boot_completed
        wait_emulator_cmd = Command('adb', ['-s', device_name, 'wait-for-device', 'shell',
                                            "'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 1; done;'"],
                                    cmd_timeout)
        wait_emulator_cmd.invoke()

        # Phase 3: Root and remount
        root_cmd = Command('adb', ['-s', device_name, 'wait-for-device', 'root'], cmd_timeout)
        while root_cmd.invoke().stderr.strip().decode('ascii'):
            if time.time() - start > boot_timeout:
                raise TimeoutError(f'{device_name} root failed within {boot_timeout}s')
            time.sleep(5)

        adb_remount = Command('adb', ['-s', device_name, 'wait-for-device', 'remount'], cmd_timeout)
        while adb_remount.invoke().stderr.strip().decode('ascii'):
            if time.time() - start > boot_timeout:
                raise TimeoutError(f'{device_name} remount failed within {boot_timeout}s')
            time.sleep(5)

        logging.info(f'{device_name} booted!')
        elapsed = time.time() - start
        logging.info(f'{device_name} took {utils.to_readable_time(elapsed)} to boot')

    @classmethod
    def simulate_reboot(cls):
        """
        Simulate a device reboot for an Android emulator.

        Broadcasts a boot completed intent and waits for the emulator to fully boot.
        Useful for testing scenarios that require a device reboot simulation.
        """
        logging.info('Starting reboot simulation')
        sim_reboot_cmd = Command('adb', ['shell', 'am', 'broadcast', '-a', 'android.intent.action.BOOT_COMPLETED'], 15)
        sim_reboot_cmd.invoke()
        time.sleep(1)
        cls._wait_for_boot()

    @classmethod
    def install_with_permissions(cls, app: App, device_name: str = "emulator-5554"):
        cls.install_apk(app, device_name)
        cls.grant_permissions(app, device_name)

    @classmethod
    def install_apk(cls, app: App, device_name: str = "emulator-5554"):
        logging.info("Installing APK: {0} on {1}".format(app.name, device_name))
        root_cmd = Command('adb', ['-s', device_name, 'root'])
        result = root_cmd.invoke()
        readlink_cmd = Command('readlink', ['-f', app.path])
        readlink_result = readlink_cmd.invoke()
        apk_path = readlink_result.stdout.strip().decode('ascii')
        install_cmd = Command('adb', [
            '-s',
            device_name,
            'install',
            '-r',
            '-g',
            apk_path
        ])
        result = install_cmd.invoke()
        if result.is_failure():
            error_msg = result.get_combined_output() or "unknown error"
            raise RuntimeError(
                f"APK installation failed for {app.name} on {device_name} "
                f"(exit code {result.code}): {error_msg}"
            )

    @classmethod
    def uninstall_apk(cls, app: App, device_name: str = "emulator-5554"):
        logging.info("Uninstalling APK: {} from {}".format(app.name, device_name))
        uninstall_cmd = Command('adb', ['-s', device_name, 'uninstall', app.package_name])
        uninstall_cmd.invoke()

    @classmethod
    def grant_permissions(cls, app: App, device_name: str = "emulator-5554"):
        for permission in app.permissions:
            logging.info("Granting permission {} on {}".format(permission, device_name))
            grant_cmd = Command('adb', ['-s', device_name, 'shell', 'pm', 'grant', app.package_name, permission])
            grant_cmd.invoke()

    # @staticmethod
    # def install_platform(number: str):
    #     logging.info("Installing android platform: {}".format(number))
    #
    #     platform_dir = os.path.join(ANDROID_PLATFORMS_DIR, "android-{}".format(number))
    #     if os.path.exists(platform_dir):
    #         logging.info("Platform already exists.")
    #         return
    #
    #     platform = "platforms;android-" + number
    #     install_cmd = Command('sdkmanager', ['--install', platform])
    #     install_cmd.invoke()
    #     logging.info("Android platform installed!")
    #
    # @staticmethod
    # def list_installed_platforms():
    #     platforms_list = []
    #     for f in os.listdir(ANDROID_PLATFORMS_DIR):
    #         file = os.path.join(ANDROID_PLATFORMS_DIR, f)
    #         if os.path.isdir(file):
    #             platform = f.split('-')
    #             if len(platform) == 2:
    #                 platforms_list.append(platform[1].strip())
    #     return platforms_list
