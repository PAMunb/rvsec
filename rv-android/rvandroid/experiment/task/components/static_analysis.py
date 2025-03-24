# rvandroid/experiment/components/static_analysis.py
from typing import Dict, Any, Optional

from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.task.task_model import Task
from rvandroid.parser.static import static_analysis_parser
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.exceptions import AnalysisError
from rvandroid.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_COMPONENT, LOG_START, \
    LOG_COMPLETE, LOG_SKIPPED, LOG_ERROR
from rvandroid.util.logging.manager import LoggingManager


class StaticAnalysisComponent:
    """
    Component responsible for handling static analysis data loading.
    Separates this concern from the main TaskExecutor.

    ### Architectural Decisions:
    - Encapsulates static analysis loading functionality
    - Implements clear separation of concerns for task execution
    - Provides focused error handling for analysis operations

    ### Role in the System:
    - Manages static analysis data loading for tasks
    - Reports analysis events to the event system
    - Provides a clean interface for static data operations
    """

    def __init__(self, task: Task, event_bus: Optional[EventBus] = None):
        """Initialize with task and optional event bus."""
        self.task = task
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = ErrorHandler.get_instance()

        # Set up standardized logger with proper context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.components.static_analysis',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name,
                CONTEXT_COMPONENT: 'StaticAnalysisComponent'
            }
        )

    def load_static_data(self, task_context: Dict[str, Any]) -> bool:
        """
        Load static analysis data for the task.

        Args:
            task_context: Context information about the task

        Returns:
            Success status
        """
        with self.logger.with_context(phase="load_static_data"):
            if self.task.static_data:
                self.logger.debug("Static data already loaded")
                return True

            try:
                self.logger.info(LOG_START.format(operation="loading static analysis data"))

                self.task.static_data = static_analysis_parser.read_static_analysis_files(
                    self.task.results_dir,
                    self.task.config.apk_name,
                    self.task.app.package_name
                )

                if self.task.static_data:
                    self.logger.info(LOG_COMPLETE.format(operation="loading static analysis data"))

                    # Publish event
                    if self.event_bus:
                        self.event_bus.publish_analysis_event(
                            EventType.STATIC_ANALYSIS_COMPLETED,
                            data={"app_name": self.task.app.name},
                            related_task_id=self.task.id,
                            source="StaticAnalysisComponent"
                        )
                    return True
                else:
                    self.logger.warning(LOG_SKIPPED.format(
                        operation="static analysis data loading",
                        reason="No data found, coverage tracking will be limited"
                    ))
                    return False

            except Exception as e:
                self.logger.warning(LOG_ERROR.format(
                    operation="loading static data",
                    error=str(e)
                ))
                # Convert to AnalysisError but don't raise
                self.error_handler.handle_error(
                    AnalysisError("Failed to load static analysis data", e),
                    task_context
                )
                return False
           