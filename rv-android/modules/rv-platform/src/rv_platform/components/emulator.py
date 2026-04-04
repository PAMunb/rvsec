# rv_platform/components/emulator.py
"""
Emulator component for RV-Platform.

Manages emulator lifecycle operations including startup, app installation,
and cleanup during task execution.
"""

from typing import Any, Dict

from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.util.android.emulator_manager import EmulatorManager
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import EmulatorError
from rv_android_core.util.logging.constants import (
    CONTEXT_APP_NAME,
    CONTEXT_TASK_ID,
    LOG_COMPLETE,
    LOG_ERROR,
    LOG_SKIPPED,
    LOG_START,
)
from rv_android_core.util.logging.manager import LoggingManager


class EmulatorComponent:
    """
    Component responsible for managing emulator operations in rv-platform.
    Handles emulator lifecycle and app installation.

    ### Architectural Decisions:
    - Encapsulates emulator management functionality
    - Implements clear separation of concerns for task execution
    - Provides focused error handling for emulator operations

    ### Role in the System:
    - Manages emulator lifecycle during task execution
    - Handles app installation and setup
    - Reports emulator lifecycle via logging
    """

    def __init__(self, task: Task):
        """Initialize with task."""
        self.name = "EmulatorComponent"
        self.task = task
        self.error_handler = ErrorHandler.get_instance()
        self.emulator_manager = EmulatorManager()

        # Initialize logging with task context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_platform.components.emulator",
            {CONTEXT_TASK_ID: task.id, CONTEXT_APP_NAME: task.config.apk_name},
        )

    def initialize(self, context: Dict[str, Any]) -> None:
        """
        Initialize the emulator component.

        Args:
            context: Task execution context
        """
        self.logger.debug("Initializing EmulatorComponent")

    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute emulator setup for the task.
        This method is called during preparation phase, not during emulator session.

        Args:
            context: Task execution context

        Returns:
            True if emulator component is ready
        """
        # EmulatorComponent execution is handled by _run_emulator_session
        # This method just indicates the component is ready
        self.logger.info("EmulatorComponent prepared for execution")
        return True

    def cleanup(self, context: Dict[str, Any]) -> None:
        """
        Clean up emulator resources.

        Args:
            context: Task execution context
        """
        self.logger.debug("Cleaning up EmulatorComponent")
        # Cleanup is handled by context manager

    def start_emulator(self, avd_name: str = "RVSec"):
        """
        Start the emulator with dynamic port allocation for parallel execution.

        Args:
            avd_name: Name of the AVD to start

        Returns:
            Context manager for emulator session
        """
        # Extract dynamic port allocation from task configuration for parallel execution
        # Each parallel task gets unique emulator port (5554, 5556, 5558, etc.)
        # Set by ParallelManager during task distribution to prevent port conflicts
        device_port = 5554  # default fallback port
        if (
            hasattr(self.task.config, "tool_config")
            and hasattr(self.task.config.tool_config, "parameters")
            and self.task.config.tool_config.parameters
        ):
            device_port = self.task.config.tool_config.parameters.get(
                "device_port", 5554
            )

        with self.logger.with_context(
            avd_name=avd_name, device_port=device_port, phase="start_emulator"
        ):
            try:
                self.logger.info(
                    LOG_START.format(phase=f"emulator {avd_name} (port {device_port})")
                )

                # Start emulator with dynamic port for true parallel execution
                # EmulatorManager creates isolated emulator instance on specified port
                # This enables multiple concurrent tasks without port conflicts
                emulator_context = self.emulator_manager.start_emulator(
                    avd_name,
                    self.task.config.no_window,
                    device_port,  # Unique port for this parallel task
                )

                self.logger.info(
                    f"Emulator started for task {self.task.id} device={self.task.config.device_id}"
                )

                return emulator_context

            except Exception as e:
                self.logger.error(
                    LOG_ERROR.format(
                        phase=f"starting emulator {avd_name}", error=str(e)
                    )
                )
                self.error_handler.handle_error(
                    EmulatorError(f"Failed to start emulator {avd_name}", e),
                    {"task_id": self.task.id},
                )
                raise

    def install_app(self, android, app: App) -> bool:
        """
        Install the app on the emulator.

        Args:
            android: Android interface from emulator
            app: App to install

        Returns:
            Success status
        """
        with self.logger.with_context(phase="install_app"):
            if self.task.config.skip_installation:
                self.logger.info(
                    LOG_SKIPPED.format(
                        phase="app installation",
                        reason="skipped as requested in configuration",
                    )
                )
                return True

            try:
                # Get device_serial from parameters for installation
                device_serial = "emulator-5554"  # default
                if (
                    hasattr(self.task.config, "tool_config")
                    and hasattr(self.task.config.tool_config, "parameters")
                    and self.task.config.tool_config.parameters
                ):
                    device_serial = self.task.config.tool_config.parameters.get(
                        "device_serial", device_serial
                    )

                self.logger.info(
                    LOG_START.format(
                        phase=f"installing app {app.name} on {device_serial}"
                    )
                )
                if not self.emulator_manager.install_app(
                    app, device_serial=device_serial
                ):
                    raise EmulatorError(
                        f"Failed to install app {app.name} on {device_serial}"
                    )
                self.logger.info(
                    LOG_COMPLETE.format(phase=f"installing app {app.name}")
                )

                self.logger.info(f"App installed for task {self.task.id}")

                return True

            except Exception as e:
                self.logger.error(
                    LOG_ERROR.format(phase=f"installing app {app.name}", error=str(e))
                )
                self.error_handler.handle_error(
                    EmulatorError(f"Failed to install app {app.name}", e),
                    {"task_id": self.task.id, "app_name": app.name},
                )
                return False

    def clean_logcat(self) -> bool:
        """
        Clear the logcat buffer.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="clean_logcat"):
            try:
                self.logger.debug(LOG_START.format(phase="cleaning logcat buffer"))
                result = self.emulator_manager.clear_logcat()
                if result:
                    self.logger.debug(
                        LOG_COMPLETE.format(phase="cleaning logcat buffer")
                    )
                return result
            except Exception as e:
                self.logger.warning(
                    LOG_ERROR.format(phase="clearing logcat", error=str(e))
                )
                # Non-critical error, just log and continue
                return False
