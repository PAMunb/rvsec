# rv_platform/components/coverage.py
"""
Coverage component for RV-Platform.

Manages coverage tracking and analysis during task execution.
"""

from typing import Dict, Any, Optional

from rv_android_core.domain.coverage import LogcatRepository
from rv_android_core.util.error.exceptions import AnalysisError
from rv_android_core.util.logging.constants import (
    CONTEXT_TASK_ID,
    CONTEXT_APP_NAME,
    LOG_ERROR,
    LOG_SKIPPED
)
from rv_coverage.analysis.coverage.tracker import CoverageTracker
from rv_coverage.parser.log.logcat_parser import parse_logcat_file
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.domain.task import Task


class CoverageComponent:
    """
    Component responsible for managing coverage tracking and analysis in rv-platform.
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

    def __init__(self, task: Task):
        """
        Initialize the coverage component.

        Args:
            task: Task being executed
        """
        self.name = "CoverageComponent"
        self.task = task
        self.error_handler = ErrorHandler.get_instance()

        # Coverage tracking
        self.repository = LogcatRepository()
        self.task.repository = self.repository
        self.tracker_process = None
        self.coverage_tracker = None

        # Initialize logging with task context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'rv_platform.components.coverage',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name
            }
        )

        # Parse any existing logcat file if available
        if task.result.logcat_file:
            self._parse_existing_logcat()

    def initialize(self, context: Dict[str, Any]) -> None:
        """
        Initialize the coverage component.
        
        Args:
            context: Task execution context
        """
        self.logger.debug("Initializing CoverageComponent")

    @ErrorHandler.handle_errors(
        component="CoverageComponent",
        phase="execution"
    )
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute coverage initialization for the task.
        This method is called during preparation phase to initialize coverage tracker.
        
        Args:
            context: Task execution context
            
        Returns:
            True if coverage tracker was initialized successfully
        """
        try:
            # Initialize coverage tracker (but don't start tracking yet)
            if not self.initialize_tracker():
                return False
                
            # Store coverage tracker in context for later use
            context["coverage_tracker"] = self.coverage_tracker
            
            self.logger.info("Coverage tracker initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Coverage component initialization failed: {e}")
            self.error_handler.handle_error(e, context)
            return False

    def cleanup(self, context: Dict[str, Any]) -> None:
        """
        Clean up coverage resources.
        
        Args:
            context: Task execution context
        """
        self.logger.debug("Cleaning up CoverageComponent")
        try:
            self.stop_tracking()
            self.process_results()
        except Exception as e:
            self.logger.warning(f"Error during coverage cleanup: {e}")

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
                self.error_handler.handle_error(e, {"task_id": self.task.id, "phase": "parse_logcat"})

    @ErrorHandler.handle_errors(
        component="CoverageComponent",
        phase="tracker_initialization"
    )
    def initialize_tracker(self) -> bool:
        """
        Initialize the coverage tracker.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="initialize_tracker"):
            try:
                self.logger.info("Initializing coverage tracker")

                # Use task start_time as initial timing reference during tracker initialization.
                # The accurate tool_execution_start timestamp is set later in start_tracking(),
                # after mark_tool_execution_start() has been called in the executor.
                timing_reference = self.task.result.start_time

                self.coverage_tracker = CoverageTracker(
                    logcat_file=self.task.result.logcat_file,
                    static_data=getattr(self.task, 'static_data', None),
                    task_start_time=timing_reference,
                    task_id=self.task.id
                )
                return True
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase="initializing coverage tracker",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Failed to initialize coverage tracker", e),
                    {"task_id": self.task.id}
                )
                return False

    @ErrorHandler.handle_errors(
        component="CoverageComponent",
        phase="start_tracking"
    )
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
                self.logger.info("Starting coverage tracking")

                # Update timing reference now that tool_execution_start is available
                if self.task.result.tool_execution_start:
                    self.coverage_tracker.tool_execution_start_time = self.task.result.tool_execution_start

                self.coverage_tracker.start()
                self.logger.info(f"Coverage tracking started for task {self.task.id}")
                return True
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase="starting coverage tracking",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Failed to start coverage tracking", e),
                    {"task_id": self.task.id}
                )
                return False

    @ErrorHandler.handle_errors(
        component="CoverageComponent",
        phase="stop_tracking"
    )
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
                self.logger.info("Stopping coverage tracking")
                self.coverage_tracker.stop()
                self.logger.info(f"Coverage tracking stopped for task {self.task.id}")
                return True
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase="stopping coverage tracking",
                    error=str(e)
                ))
                self.error_handler.handle_error(
                    AnalysisError("Failed to stop coverage tracking", e),
                    {"task_id": self.task.id}
                )
                return False

    @ErrorHandler.handle_errors(
        component="CoverageComponent",
        phase="process_results"
    )
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
                    phase="coverage data processing",
                    reason="No coverage tracker available"
                ))
                return False

            try:
                self.logger.info("Processing coverage data")

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

                self.logger.info(f"Coverage updated for task {self.task.id}: {self.task.result.coverage_metrics}")
                self.logger.info("Coverage data processing completed")
                return True

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    phase="processing coverage data",
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