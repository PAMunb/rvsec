# rvandroid/experiment/task/components/static_analysis.py
from typing import Dict, Any, Optional

from rv_android_core.util.exceptions import AnalysisError
from rv_android_core.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, LOG_START, \
    LOG_COMPLETE, LOG_SKIPPED, LOG_ERROR
from rv_android_core.experiment.event.bus import EventBus, EventType
from rv_android_core.experiment.task.component import BaseTaskComponent
from rv_android_core.experiment.task.task_model import Task
from rv_android_core.parser.static import static_analysis_parser


class StaticAnalysisComponent(BaseTaskComponent):
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
        super().__init__("StaticAnalysisComponent", event_bus)
        self.task = task

        # Update logger context with task information
        self.logger.push_context(**{
            CONTEXT_TASK_ID: task.id,
            CONTEXT_APP_NAME: task.config.apk_name
        })

    def _execute_impl(self, context: Dict[str, Any]) -> bool:
        """
        Execute static analysis data loading for the task.
        
        Args:
            context: Task execution context
            
        Returns:
            True if static analysis data was loaded successfully
        """
        return self.load_static_data(context)

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
                self._get_error_handler().handle_error(
                    AnalysisError("Failed to load static analysis data", e),
                    task_context
                )
                return False
