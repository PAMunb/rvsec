# rv_platform/components/emulator.py
"""
Emulator component for RV-Platform.

Manages emulator lifecycle operations including startup, app installation,
and cleanup during task execution.
"""

from typing import Any, Dict, Optional, Tuple

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

# Port of the single emulator used when no device_port is injected.
DEFAULT_DEVICE_PORT = 5554


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

        # Reason ADB gave for the last failed installation. install_app()
        # reports failure by returning False, which carries no text, so the
        # INSTALL_FAILED_* code is held here for the executor to put in the
        # task's error_message (INV-CORE-51).
        self.last_install_error: Optional[str] = None

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
        # No-op during the generic component execution phase. The actual emulator
        # lifecycle is managed by start_emulator() which is called directly by
        # TaskExecutor._run_emulator_session() as a context manager. This two-step
        # design exists because the emulator must wrap other components (logcat,
        # coverage, tool) rather than running alongside them.
        self.logger.info("EmulatorComponent prepared for execution")
        return True

    def cleanup(self, context: Dict[str, Any]) -> None:
        """
        Clean up emulator resources.

        Args:
            context: Task execution context
        """
        # Intentionally a no-op: the emulator is managed by the context manager
        # in start_emulator(). When the `with` block exits (normally or via exception),
        # EmulatorManager.__exit__ handles shutdown. Doing cleanup here would risk
        # double-shutdown or premature teardown.
        self.logger.debug("Cleaning up EmulatorComponent")

    def _resolve_device(self) -> Tuple[int, str]:
        """
        Resolve the emulator port and the ADB serial of this task's device.

        Both values come from this single derivation so they always denote the
        same device (INV-PLT-28): the serial follows from the port unless the
        task supplies an explicit `device_serial`. A task injecting only one of
        the two keys therefore cannot boot one device and install on another.

        Dynamic port allocation serves parallel Docker containers: each runs one
        emulator on a unique port (5554, 5556, 5558, ...), injected into
        `tool_config.parameters` by ExecutionController when --device-port is
        given. Without it, port 5554 applies (single-emulator mode).

        Returns:
            Tuple of (device_port, device_serial)
        """
        parameters = {}
        if (
            hasattr(self.task.config, "tool_config")
            and hasattr(self.task.config.tool_config, "parameters")
            and self.task.config.tool_config.parameters
        ):
            parameters = self.task.config.tool_config.parameters

        device_port = parameters.get("device_port", DEFAULT_DEVICE_PORT)
        device_serial = parameters.get("device_serial", f"emulator-{device_port}")
        return device_port, device_serial

    def start_emulator(self, avd_name: str = "RVSec"):
        """
        Start the emulator with dynamic port allocation for parallel execution.

        Args:
            avd_name: Name of the AVD to start

        Returns:
            Context manager for emulator session
        """
        device_port, _ = self._resolve_device()

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
                # Same derivation as start_emulator(), so the serial installed on
                # denotes the device booted. In parallel mode this is
                # "emulator-5556", "emulator-5558", etc.
                _, device_serial = self._resolve_device()

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
                install_error = EmulatorError(f"Failed to install app {app.name}", e)
                self.last_install_error = str(install_error)
                self.error_handler.handle_error(
                    install_error,
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
