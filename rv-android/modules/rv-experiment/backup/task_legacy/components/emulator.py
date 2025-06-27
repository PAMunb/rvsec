# rvandroid/experiment/task/components/emulator.py
from typing import Any, Optional, Dict

from rv_android_core.app import App
from rv_android_core.util.emulator_manager import EmulatorManager
from rv_android_core.util.exceptions import EmulatorError
from rv_android_core.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, LOG_START, LOG_ERROR, \
    LOG_SKIPPED, LOG_COMPLETE
from rv_android_core.event import EventBus, EventType
from rv_experiment.experiment.task.component import BaseTaskComponent
from rv_experiment.experiment.task.task_model import Task


class EmulatorComponent(BaseTaskComponent):
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
        super().__init__("EmulatorComponent", event_bus)
        self.task = task
        self.emulator_manager = EmulatorManager()

        # Update logger context with task information
        self.logger.push_context(**{
            CONTEXT_TASK_ID: task.id,
            CONTEXT_APP_NAME: task.config.apk_name
        })

    def _execute_impl(self, context: Dict[str, Any]) -> bool:
        """
        Execute emulator setup for the task.
        
        Args:
            context: Task execution context
            
        Returns:
            True if emulator setup was successful
        """
        # This component primarily provides context managers and utilities
        # The actual emulator management is handled by the task executor
        return True

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
