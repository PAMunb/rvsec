# rvandroid/util/emulator_manager.py
import logging
from contextlib import contextmanager
from typing import Optional

from rvandroid.android import Android
from rvandroid.commands.command import Command
from rvandroid.util.exceptions import EmulatorError


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
        self.logger = logging.getLogger(__name__)
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
        self.logger.info(f"Starting emulator: {avd_name}")
        self.android = Android()

        try:
            # Start the emulator
            self.android.start_emulator(avd_name, no_window)
            self._active_emulators.add(avd_name)
            self.logger.info(f"Emulator {avd_name} started successfully")

            yield self.android

        except Exception as e:
            self.logger.error(f"Error starting emulator {avd_name}: {e}")
            raise EmulatorError(f"Failed to start emulator {avd_name}", cause=e)

        finally:
            # Always try to clean up
            try:
                if avd_name in self._active_emulators:
                    self.logger.info(f"Shutting down emulator {avd_name}")
                    self.android.kill_emulator(avd_name)
                    self._active_emulators.remove(avd_name)
            except Exception as e:
                self.logger.warning(f"Error shutting down emulator {avd_name}: {e}")

    def clear_logcat(self):
        """Clear logcat buffer."""
        try:
            clear_cmd = Command("adb", ["logcat", "-c"])
            clear_cmd.invoke()
            self.logger.debug("Cleared logcat buffer")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to clear logcat: {e}")
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
        if not self.android:
            self.logger.error("No active emulator for app installation")
            return False

        try:
            if with_permissions:
                self.android.install_with_permissions(app)
            else:
                self.android.install_apk(app)
            self.logger.info(f"Installed app: {app.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to install app {app.name}: {e}")
            return False
