# rvandroid/experiment/task/components/coverage.py
from typing import Optional, Dict, Any

from rv_android_core.domain.coverage import LogcatRepository
from rv_android_core.util.exceptions import AnalysisError
from rv_android_core.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, LOG_START, \
    LOG_COMPLETE, LOG_ERROR, LOG_SKIPPED
from rv_android_core.analysis.coverage.tracker import CoverageTracker
from rv_android_core.experiment.event.bus import EventBus, EventType
from rv_android_core.experiment.task.component import BaseTaskComponent
from rv_android_core.experiment.task.task_model import Task
from rv_android_core.parser.log.logcat_parser import parse_logcat_file


class CoverageComponent(BaseTaskComponent):
    """
    Component responsible for managing coverage tracking and analysis.
    Handles coverage tracker lifecycle and result processing.

    ### Architectural Decisions:
    - Encapsulates coverage tracking functionality
    - Implements clear separation of concerns for task execution
    - Provides focused error handling for coverage operations
    - Integrates with the unified analysis component system

    ### Role in the System:
    - Manages coverage tracking during task execution
    - Reports coverage events to the event system
    - Processes coverage data after task completion
    - Formats coverage results for the standardized result system
    """

    def __init__(self, task: Task, event_bus: Optional[EventBus] = None):
        """
        Initialize the coverage component.

        Args:
            task: Task being executed
            event_bus: Optional event bus for publishing events
        """
        super().__init__("CoverageComponent", event_bus)
        self.task = task

        # Coverage tracking
        self.repository = LogcatRepository()
        self.task.repository = self.repository
        self.tracker_process = None

        # Update logger context with task information
        self.logger.push_context(**{
            CONTEXT_TASK_ID: task.id,
            CONTEXT_APP_NAME: task.config.apk_name
        })

        # Parse any existing logcat file if available
        if task.result.logcat_file:
            self._parse_existing_logcat()

    def _execute_impl(self, context: Dict[str, Any]) -> bool:
        """
        Execute coverage tracking for the task.
        
        Args:
            context: Task execution context
            
        Returns:
            True if coverage tracking was initialized successfully
        """
        return self.initialize_tracker()

    def _parse_existing_logcat(self) -> None:
        """Parse existing logcat file if available."""
        import os
        if self.task.result.logcat_file and os.path.exists(self.task.result.logcat_file):
            self.logger.info(f"Parsing existing logcat file: {self.task.result.logcat_file}")
            try:
                self.repository = parse_logcat_file(self.task.result.logcat_file)
                self.task.repository = self.repository
            except Exception as e:
                self.logger.error(f"Error parsing logcat file: {e}")
                # Utilize o error handler através do método getter
                error_handler = self._get_error_handler()
                if error_handler:
                    error_handler.handle_error(e, {"task_id": self.task.id, "phase": "parse_logcat"})

    def initialize_tracker(self) -> bool:
        """
        Initialize the coverage tracker.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="initialize_tracker"):
            try:
                self.logger.info(LOG_START.format(operation="initializing coverage tracker"))
                self.coverage_tracker = CoverageTracker(
                    logcat_file=self.task.result.logcat_file,
                    static_data=self.task.static_data,
                    task_start_time=self.task.result.start_time
                )

                self.logger.info(LOG_COMPLETE.format(operation="initializing coverage tracker"))
                return True
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="initializing coverage tracker",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Failed to initialize coverage tracker", e),
                    {"task_id": self.task.id}
                )
                return False

    def start_tracking(self) -> bool:
        """
        Start coverage tracking.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="start_tracking"):
            if not self.coverage_tracker:
                self.logger.error("Cannot start tracking: tracker not initialized")
                return False

            try:
                self.logger.info(LOG_START.format(operation="coverage tracking"))
                self.coverage_tracker.start()

                # Publish event
                if self.event_bus:
                    self.event_bus.publish_analysis_event(
                        EventType.COVERAGE_TRACKING_STARTED,
                        data={"logcat_file": self.task.result.logcat_file},
                        related_task_id=self.task.id,
                        source="CoverageComponent"
                    )
                return True
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="starting coverage tracking",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Failed to start coverage tracking", e),
                    {"task_id": self.task.id}
                )
                return False

    def stop_tracking(self) -> bool:
        """
        Stop coverage tracking.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="stop_tracking"):
            if not self.coverage_tracker:
                return True

            try:
                self.logger.info(LOG_START.format(operation="stopping coverage tracking"))
                self.coverage_tracker.stop()
                self.logger.info(LOG_COMPLETE.format(operation="stopping coverage tracking"))

                # Publish event
                if self.event_bus:
                    self.event_bus.publish_analysis_event(
                        EventType.COVERAGE_TRACKING_STOPPED,
                        related_task_id=self.task.id,
                        source="CoverageComponent"
                    )
                return True
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="stopping coverage tracking",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Failed to stop coverage tracking", e),
                    {"task_id": self.task.id}
                )
                return False

    def process_results(self) -> bool:
        """
        Process coverage results and update task metrics.
        Uses the standardized result system for consistent data representation.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="process_results"):
            if not self.coverage_tracker:
                self.logger.warning(LOG_SKIPPED.format(
                    operation="coverage data processing",
                    reason="No coverage tracker available"
                ))
                return False

            try:
                self.logger.info(LOG_START.format(operation="processing coverage data"))

                # Get repository from coverage tracker
                repository = self.coverage_tracker.repository

                # Calculate metrics using the repository
                metrics = repository.calculate_metrics()
                metrics_dict = metrics.to_dict()

                # Update task result with metrics
                self.task.result.coverage_metrics.update({
                    "method_coverage": metrics_dict["method_coverage"],
                    "activities_coverage": metrics_dict["activity_coverage"],
                    "methods_jca_reachable_coverage": metrics_dict["mop_method_coverage"],
                    "total_errors": metrics_dict["unique_errors"],
                    "total_method_calls": metrics.called_methods
                })

                # Store the repository directly in the task
                self.task.repository = repository

                # Log coverage summary
                self.logger.info(
                    f"Final coverage: Methods: {metrics_dict['method_coverage']:.2f}%, "
                    f"Activities: {metrics_dict['activity_coverage']:.2f}%, "
                    f"MOP Methods: {metrics_dict['mop_method_coverage']:.2f}%, "
                    f"Errors: {metrics_dict['unique_errors']}"
                )

                # Publish coverage updated event
                if self.event_bus:
                    self.event_bus.publish_analysis_event(
                        EventType.COVERAGE_UPDATED,
                        data={"coverage_metrics": self.task.result.coverage_metrics},
                        related_task_id=self.task.id,
                        source="CoverageComponent"
                    )

                self.logger.info(LOG_COMPLETE.format(operation="processing coverage data"))
                return True

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="processing coverage data",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Coverage data processing failed", e),
                    {"task_id": self.task.id}
                )
                return False

    def get_repository(self) -> Optional[LogcatRepository]:
        """
        Get the coverage repository if available.

        Returns:
            LogcatRepository or None
        """
        if self.coverage_tracker:
            return self.coverage_tracker.repository
        return None
