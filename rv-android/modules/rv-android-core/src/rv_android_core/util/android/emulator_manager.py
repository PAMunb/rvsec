# rvandroid/util/emulator_manager.py
from contextlib import contextmanager
from typing import Iterator, Optional

from rv_android_core.commands.command import Command
from rv_android_core.util.android.android import Android
from rv_android_core.util.error.exceptions import EmulatorError
from rv_android_core.util.logging.constants import (
    CONTEXT_COMPONENT,
    LOG_COMPLETE,
    LOG_ERROR,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager

# Animation scale settings for performance optimization
# Setting to 0.0 disables animations completely
ANIMATION_SCALE_DISABLED = "0.0"

# ADB commands to disable system animations
# These significantly improve headless mode performance
ADB_DISABLE_WINDOW_ANIMATION = "settings put global window_animation_scale"
ADB_DISABLE_TRANSITION_ANIMATION = "settings put global transition_animation_scale"
ADB_DISABLE_ANIMATOR_DURATION = "settings put global animator_duration_scale"


class EmulatorManager:
    """
    Responsible for managing Android emulator lifecycle.

    ### Architectural Decisions:
    - Centralizes emulator management to separate this concern from task execution
    - Improves resource management with proper context managers
    - Provides robust error handling for emulator operations
    - Configures device for optimal testing performance (animations disabled)

    ### Role in the System:
    - Manages emulator startup and shutdown
    - Handles device preparations like clearing logcat and disabling animations
    - Provides a clean API for emulator interaction
    """

    def __init__(self):
        """Initialize the emulator manager with standard logging."""
        # Set up logging using LoggingManager
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_android_core.util.android.emulator_manager",
            {CONTEXT_COMPONENT: "EmulatorManager"},
        )

        self.android: Optional[Android] = None
        self._active_emulators = set()

    @contextmanager
    def start_emulator(
        self,
        avd_name: str,
        no_window: bool = False,
        device_port: int = 5554,
        disable_animations: bool = True,
    ) -> Iterator[Android]:
        """
        Start an emulator with dynamic port allocation for parallel execution.

        The block structure is load-bearing and is nested, not split into two
        siblings. An outer `try` whose `finally` tears the device down encloses
        everything; inside it, an inner `try/except` covers the startup
        sequence alone and is the only thing that produces `EmulatorError`.
        The `yield` sits after that inner block, so a failure in the caller's
        `with` body propagates with its own type instead of being relabelled a
        startup failure.

        Two sibling blocks — `try/except` for startup, then `try/finally` for
        the `yield` — read as the same refactor and are not: a startup failure
        raises out of the first block and never enters the second, so the
        teardown would not run and the AVD registered before launch would be
        left holding its port.

        Args:
            avd_name: Name of the AVD to launch
            no_window: Whether to run in headless mode
            device_port: Emulator port for parallel execution (default: 5554)
            disable_animations: Whether to disable system animations (default: True)

        Yields:
            Android instance for interacting with the emulator

        Raises:
            EmulatorError: If the emulator fails to start. Failures raised by
                the body of the `with` block keep their own type.
        """
        device_serial = f"emulator-{device_port}"
        with self.logger.with_context(
            avd_name=avd_name,
            no_window=no_window,
            device_port=device_port,
            phase="startup",
        ):
            self.logger.info(
                LOG_START.format(phase=f"emulator: {avd_name} (port {device_port})")
            )
            self.android = Android()

            try:
                try:
                    # Register before launching: the teardown below acts only on
                    # registered AVDs, so a boot that never completes would
                    # otherwise leave the daemonized emulator alive holding its
                    # port for the next task to find.
                    self._active_emulators.add(avd_name)

                    # Start the emulator with dynamic port allocation
                    self.android.start_emulator(avd_name, no_window, device_port)

                    # Configure device for optimal testing performance
                    if disable_animations:
                        self.disable_animations(device_serial)

                    self.logger.info(
                        LOG_COMPLETE.format(phase=f"emulator {avd_name} startup")
                    )
                except Exception as e:
                    self.logger.error(
                        LOG_ERROR.format(
                            phase=f"starting emulator {avd_name}", error=str(e)
                        )
                    )
                    raise EmulatorError(f"Failed to start emulator {avd_name}", cause=e)

                yield self.android

            finally:
                # Always try to clean up with correct device serial
                with self.logger.with_context(
                    phase="shutdown", device_serial=device_serial
                ):
                    try:
                        if avd_name in self._active_emulators:
                            self.logger.info(
                                f"Shutting down emulator {avd_name} ({device_serial})"
                            )
                            self.android.kill_emulator(avd_name, device_serial)
                            self._active_emulators.remove(avd_name)
                    except Exception as e:
                        self.logger.warning(
                            LOG_ERROR.format(
                                phase=f"shutting down emulator {avd_name}", error=str(e)
                            )
                        )

    def clear_logcat(self, device_serial: str = "emulator-5554") -> bool:
        """
        Clear logcat buffer.

        Args:
            device_serial: Target device serial (default: emulator-5554)

        Returns:
            True if logcat cleared successfully
        """
        with self.logger.with_context(
            phase="clear_logcat", device_serial=device_serial
        ):
            try:
                clear_cmd = Command("adb", ["-s", device_serial, "logcat", "-c"])
                clear_cmd.invoke()
                self.logger.debug("Cleared logcat buffer")
                return True
            except Exception as e:
                self.logger.warning(
                    LOG_ERROR.format(phase="clearing logcat", error=str(e))
                )
                return False

    def disable_animations(self, device_serial: str = "emulator-5554") -> bool:
        """
        Disable system animations for optimal testing performance.

        Disabling animations significantly improves performance, especially
        in headless mode where software rendering (SwiftShader) is used.
        This reduces UI idle waiting time and speeds up action execution.

        Args:
            device_serial: Target device serial (default: emulator-5554)

        Returns:
            True if all animations were disabled successfully
        """
        with self.logger.with_context(
            phase="disable_animations", device_serial=device_serial
        ):
            try:
                animation_commands = [
                    (ADB_DISABLE_WINDOW_ANIMATION, "window_animation_scale"),
                    (ADB_DISABLE_TRANSITION_ANIMATION, "transition_animation_scale"),
                    (ADB_DISABLE_ANIMATOR_DURATION, "animator_duration_scale"),
                ]

                success = True
                for cmd_prefix, setting_name in animation_commands:
                    cmd = Command(
                        "adb",
                        [
                            "-s",
                            device_serial,
                            "shell",
                            f"{cmd_prefix} {ANIMATION_SCALE_DISABLED}",
                        ],
                    )
                    result = cmd.invoke()
                    if not result.is_success():
                        self.logger.warning(f"Failed to disable {setting_name}")
                        success = False

                if success:
                    self.logger.info(
                        "System animations disabled for optimal performance"
                    )
                return success

            except Exception as e:
                self.logger.warning(
                    LOG_ERROR.format(phase="disabling animations", error=str(e))
                )
                return False

    def install_app(
        self, app, with_permissions: bool = True, device_serial: str = "emulator-5554"
    ) -> bool:
        """
        Install an app on the specific emulator instance.

        An ADB failure is reported by raising, not by returning `False`. The
        `RuntimeError` that `Android.install_apk` raises already carries the
        exit code and the `INSTALL_FAILED_*` text; reducing it to a boolean
        here is what kept that reason out of every one of the 1,174 recorded
        install failures. Letting it propagate needs no new carrier type and
        cannot be ignored the way a returned `False` could.

        `False` is still returned for the one condition that produces no ADB
        output to carry: being asked to install with no emulator attached.

        Args:
            app: App to install
            with_permissions: Whether to grant permissions
            device_serial: Target emulator device serial (for parallel execution)

        Returns:
            True if installation succeeded; False if there is no active
            emulator to install onto.

        Raises:
            RuntimeError: If ADB reported an installation failure; the message
                carries the exit code and the ADB output.
            RVCommandTimeoutError: If the install exceeded its timeout.
        """
        with self.logger.with_context(
            app_name=app.name,
            package_name=app.package_name,
            with_permissions=with_permissions,
            phase="app_installation",
        ):
            if not self.android:
                self.logger.error("No active emulator for app installation")
                return False

            try:
                if with_permissions:
                    self.android.install_with_permissions(app, device_serial)
                else:
                    self.android.install_apk(app, device_serial)

                self.logger.info(
                    LOG_COMPLETE.format(phase=f"installation of app: {app.name}")
                )
                return True

            except Exception as e:
                self.logger.error(
                    LOG_ERROR.format(phase=f"installing app {app.name}", error=str(e))
                )
                raise
