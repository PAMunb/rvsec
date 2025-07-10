# rvandroid/util/emulator_manager.py
from contextlib import contextmanager
from typing import Optional

from rv_android_core.util.android.android import Android
from rv_android_core.commands.command import Command
from rv_android_core.util.error.exceptions import EmulatorError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager


class EmulatorManager:
    """
    Responsible for managing Android emulator lifecycle.

    ### Architectural Decisions:
    - Centralizes emulator management to separate this concern from task execution
    - Improves resource management with proper context managers
    - Provides robust error handling for emulator operations

    ### Role in the System:
    - Manages emulator startup and shutdown
    - Handles device preparations like clearing logcat
    - Provides a clean API for emulator interaction
    """

    def __init__(self):
        """Initialize the emulator manager with standard logging."""
        # Set up logging using LoggingManager
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_android_core.util.android.emulator_manager",
            {CONTEXT_COMPONENT: "EmulatorManager"}
        )

        self.android: Optional[Android] = None
        self._active_emulators = set()

    @contextmanager
    def start_emulator(self, avd_name: str, no_window: bool = False) -> Android:
        """
        Start an emulator and yield an Android instance for interaction.

        Args:
            avd_name: Name of the AVD to launch
            no_window: Whether to run in headless mode

        Yields:
            Android instance for interacting with the emulator

        Raises:
            EmulatorError: If emulator fails to start
        """
        with self.logger.with_context(avd_name=avd_name, no_window=no_window, phase="startup"):
            self.logger.info(LOG_START.format(phase=f"emulator: {avd_name}"))
            self.android = Android()

            try:
                # Start the emulator
                self.android.start_emulator(avd_name, no_window)
                self._active_emulators.add(avd_name)
                self.logger.info(LOG_COMPLETE.format(
                    phase=f"emulator {avd_name} startup"
                ))

                yield self.android

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase=f"starting emulator {avd_name}",
                    error=str(e)
                ))
                raise EmulatorError(f"Failed to start emulator {avd_name}", cause=e)

            finally:
                # Always try to clean up
                with self.logger.with_context(phase="shutdown"):
                    try:
                        if avd_name in self._active_emulators:
                            self.logger.info(f"Shutting down emulator {avd_name}")
                            self.android.kill_emulator(avd_name)
                            self._active_emulators.remove(avd_name)
                    except Exception as e:
                        self.logger.warning(LOG_ERROR.format(
                            phase=f"shutting down emulator {avd_name}",
                            error=str(e)
                        ))

    def clear_logcat(self):
        """Clear logcat buffer."""
        with self.logger.with_context(phase="clear_logcat"):
            try:
                clear_cmd = Command("adb", ["logcat", "-c"])
                clear_cmd.invoke()
                self.logger.debug("Cleared logcat buffer")
                return True
            except Exception as e:
                self.logger.warning(LOG_ERROR.format(
                    phase="clearing logcat",
                    error=str(e)
                ))
                return False

    def install_app(self, app, with_permissions: bool = True) -> bool:
        """
        Install an app on the emulator.

        Args:
            app: App to install
            with_permissions: Whether to grant permissions

        Returns:
            True if installation succeeded, False otherwise
        """
        with self.logger.with_context(
                app_name=app.name,
                package_name=app.package_name,
                with_permissions=with_permissions,
                phase="app_installation"
        ):
            if not self.android:
                self.logger.error("No active emulator for app installation")
                return False

            try:
                if with_permissions:
                    self.android.install_with_permissions(app)
                else:
                    self.android.install_apk(app)

                self.logger.info(LOG_COMPLETE.format(
                    phase=f"installation of app: {app.name}"
                ))
                return True

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase=f"installing app {app.name}",
                    error=str(e)
                ))
                return False
