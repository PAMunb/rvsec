# rv_platform/components/emulator.py
"""
Emulator component for RV-Platform.

Manages emulator lifecycle operations including startup, app installation,
and cleanup during task execution.
"""

from typing import Any, Optional, Dict

from rv_android_core.app import App
from rv_android_core.util.emulator_manager import EmulatorManager
from rv_android_core.util.exceptions import EmulatorError
from rv_android_core.util.logging.constants import (
    CONTEXT_TASK_ID, 
    CONTEXT_APP_NAME, 
    LOG_START, 
    LOG_ERROR,
    LOG_SKIPPED, 
    LOG_COMPLETE
)
from rv_android_core.event import EventBus, EventType
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.domain.task import Task


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
    - Reports emulator events to the event system
    """

    def __init__(self, task: Task, event_bus: Optional[EventBus] = None):
        """Initialize with task and optional event bus."""
        self.name = "EmulatorComponent"
        self.task = task
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.emulator_manager = EmulatorManager()

        # Initialize logging with task context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'platform.emulator',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name
            }
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
        Start the emulator and return a context manager.

        Args:
            avd_name: Name of the AVD to start

        Returns:
            Context manager for emulator session
        """
        with self.logger.with_context(avd_name=avd_name, phase="start_emulator"):
            try:
                self.logger.info(LOG_START.format(phase=f"emulator {avd_name}"))

                # Get emulator context manager
                emulator_context = self.emulator_manager.start_emulator(
                    avd_name,
                    self.task.config.no_window
                )

                # Publish event
                if self.event_bus:
                    self.event_bus.publish_task_event(
                        EventType.EMULATOR_STARTED,
                        task_id=self.task.id,
                        details={"device_id": self.task.config.device_id},
                        source="EmulatorComponent"
                    )

                return emulator_context

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase=f"starting emulator {avd_name}",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    EmulatorError(f"Failed to start emulator {avd_name}", e),
                    {"task_id": self.task.id}
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
                self.logger.info(LOG_SKIPPED.format(
                    phase="app installation",
                    reason="skipped as requested in configuration"
                ))
                return True

            try:
                self.logger.info(LOG_START.format(phase=f"installing app {app.name}"))
                self.emulator_manager.install_app(app)
                self.logger.info(LOG_COMPLETE.format(phase=f"installing app {app.name}"))

                # Publish event
                if self.event_bus:
                    self.event_bus.publish_task_event(
                        EventType.APP_INSTALLED,
                        task_id=self.task.id,
                        details={"app_name": app.name},
                        source="EmulatorComponent"
                    )

                return True

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase=f"installing app {app.name}",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    EmulatorError(f"Failed to install app {app.name}", e),
                    {"task_id": self.task.id, "app_name": app.name}
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
                    self.logger.debug(LOG_COMPLETE.format(phase="cleaning logcat buffer"))
                return result
            except Exception as e:
                self.logger.warning(LOG_ERROR.format(
                    phase="clearing logcat",
                    error=str(e)
                ))
                # Non-critical error, just log and continue
                return False