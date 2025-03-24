# rvandroid/experiment/components/emulator.py
from typing import Any, Optional

from rvandroid.app import App
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.task.task_model import Task
from rvandroid.util.emulator_manager import EmulatorManager
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.exceptions import EmulatorError
from rvandroid.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_COMPONENT, LOG_START, LOG_ERROR, \
    LOG_SKIPPED, LOG_COMPLETE
from rvandroid.util.logging.manager import LoggingManager


class EmulatorComponent:
    """
    Component responsible for managing emulator operations.
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
        self.task = task
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.emulator_manager = EmulatorManager()

        # Set up standardized logger with proper context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.components.emulator',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name,
                CONTEXT_COMPONENT: 'EmulatorComponent'
            }
        )

    def start_emulator(self, avd_name: str = "RVSec") -> Any:
        """
        Start the emulator and return a context manager.

        Args:
            avd_name: Name of the AVD to start

        Returns:
            Context manager for emulator session
        """
        with self.logger.with_context(avd_name=avd_name, phase="start_emulator"):
            try:
                self.logger.info(LOG_START.format(operation=f"emulator {avd_name}"))

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
                    operation=f"starting emulator {avd_name}",
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
                    operation="app installation",
                    reason="skipped as requested in configuration"
                ))
                return True

            try:
                self.logger.info(LOG_START.format(operation=f"installing app {app.name}"))
                self.emulator_manager.install_app(app)
                self.logger.info(LOG_COMPLETE.format(operation=f"installing app {app.name}"))

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
                    operation=f"installing app {app.name}",
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
                self.logger.debug(LOG_START.format(operation="cleaning logcat buffer"))
                result = self.emulator_manager.clear_logcat()
                if result:
                    self.logger.debug(LOG_COMPLETE.format(operation="cleaning logcat buffer"))
                return result
            except Exception as e:
                self.logger.warning(LOG_ERROR.format(
                    operation="clearing logcat",
                    error=str(e)
                ))
                # Non-critical error, just log and continue
                return False
