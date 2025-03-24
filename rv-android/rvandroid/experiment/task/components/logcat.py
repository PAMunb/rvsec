# rvandroid/experiment/components/logcat.py
from typing import Optional

from rvandroid.experiment.event.bus import EventBus
from rvandroid.experiment.task.task_model import Task
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.exceptions import AnalysisError
from rvandroid.util.logcat_manager import LogcatManager
from rvandroid.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_COMPONENT, LOG_START, \
    LOG_COMPLETE, LOG_ERROR
from rvandroid.util.logging.manager import LoggingManager


class LogcatComponent:
    """
    Component responsible for managing logcat operations.
    Handles logcat capture and filtering.

    ### Architectural Decisions:
    - Encapsulates logcat management functionality
    - Implements clear separation of concerns for task execution
    - Provides focused error handling for logcat operations

    ### Role in the System:
    - Manages logcat capture during task execution
    - Ensures proper logcat lifecycle management
    - Provides a clean interface for logcat operations
    """

    def __init__(self, task: Task, event_bus: Optional[EventBus] = None):
        """Initialize with task and optional event bus."""
        self.task = task
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.logcat_manager = LogcatManager()

        # Set up standardized logger with proper context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.components.logcat',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name,
                CONTEXT_COMPONENT: 'LogcatComponent'
            }
        )

    def start_capture(self) -> bool:
        """
        Start capturing logcat output.

        Returns:
            Success status
        """
        with self.logger.with_context(
                output_file=self.task.result.logcat_file,
                clear_buffer=self.task.config.clean_logcat,
                phase="start_capture"
        ):
            try:
                self.logger.info(LOG_START.format(
                    operation=f"logcat capture to {self.task.result.logcat_file}"
                ))

                result = self.logcat_manager.start_capture(
                    self.task.result.logcat_file,
                    clear_buffer=self.task.config.clean_logcat
                )

                if result:
                    self.logger.info(LOG_COMPLETE.format(
                        operation=f"starting logcat capture to {self.task.result.logcat_file}"
                    ))
                else:
                    self.logger.warning("Failed to start logcat capture")

                return result

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="starting logcat capture",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Failed to start logcat capture", e),
                    {"task_id": self.task.id}
                )
                return False

    def stop_capture(self) -> bool:
        """
        Stop logcat capture.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="stop_capture"):
            try:
                self.logger.info(LOG_START.format(operation="stopping logcat capture"))
                result = self.logcat_manager.stop_capture()

                if result:
                    self.logger.info(LOG_COMPLETE.format(operation="stopping logcat capture"))
                else:
                    self.logger.warning("Issues stopping logcat capture")

                return result

            except Exception as e:
                self.logger.warning(LOG_ERROR.format(
                    operation="stopping logcat capture",
                    error=str(e)
                ))
                return False
           