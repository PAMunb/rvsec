# rvandroid/experiment/task_model.py
"""
Task model classes for experiment execution.
Provides a clear separation of concerns for task configuration, execution, and results.
Integrates with the standardized result system for consistent data representation.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional

from rvandroid.app import App
from rvandroid.domain.coverage import LogcatRepository
from rvandroid.domain.log import RvCoverageLog, RvErrorLog


class TaskStatus(Enum):
    """Enum representing the possible states of a task"""
    CREATED = 1
    CONFIGURED = 2
    RUNNING = 3
    EXECUTED = 4
    ERROR = 5
    CANCELED = 6


@dataclass
class TaskConfig:
    """
    Configuration parameters for a task execution.
    
    ### Architectural Decisions:
    - Provides a simplified interface for task configuration compatible with test framework
    - Serves as a bridge between the older TaskConfiguration and test framework executor
    - Maintains compatibility with existing code while supporting new features
    - Uses dataclass for concise definition and automatic implementation of common methods
    
    ### Role in the System:
    - Configures timeout and device settings for task execution
    - Supports the test framework's task execution requirements
    - Enables clean integration between components
    """
    timeout: int = 300  # Default timeout of 5 minutes
    device_id: str = "emulator-5554"  # Default device ID
    no_window: bool = False  # Whether to run the emulator headless
    clean_logcat: bool = True  # Whether to clear logcat before execution


@dataclass
class TaskConfiguration:
    """Configuration parameters for a task"""
    apk_name: str
    repetition: int
    timeout: int
    tool_name: str

    # Optional configuration
    no_window: bool = False
    clean_logcat: bool = True
    skip_installation: bool = False
    device_id: str = "emulator-5554"
    export_to_csv: bool = True  # New option to control CSV export

    def __str__(self) -> str:
        return (f"TaskConfiguration(apk={self.apk_name}, rep={self.repetition}, "
                f"timeout={self.timeout}, tool={self.tool_name})")


@dataclass
class TaskResult:
    """
    The TaskResult class encapsulates the outcome of a task execution within
    an experiment. It stores execution metadata, success/failure status, and
    any relevant output or error messages.

    ### Architectural Decisions:
    - Provides a structured format for capturing task execution results.
    - Supports serialization for logging and post-execution analysis.
    - Designed to be lightweight and easy to integrate with other components.

    ### Role in the System:
    - Acts as a data container for storing execution details of experiment tasks.
    - Facilitates debugging and performance tracking by logging execution results.
    - Ensures consistency in reporting task statuses across different experiments.
    """
    status: TaskStatus = TaskStatus.CREATED
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time_seconds: int = 0
    error_message: Optional[str] = None

    # Output files
    logcat_file: str = ""
    trace_file: str = ""

    # Analysis results
    coverage_metrics: Dict[str, float] = field(default_factory=dict)
    detected_errors: List[Dict[str, Any]] = field(default_factory=list)

    def update_execution_time(self) -> None:
        """Update execution time if start and end times are available"""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.execution_time_seconds = int(delta.total_seconds())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "status": self.status.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time_seconds": self.execution_time_seconds,
            "error_message": self.error_message,
            "logcat_file": self.logcat_file,
            "trace_file": self.trace_file,
            "coverage_metrics": self.coverage_metrics,
            "detected_errors_count": len(self.detected_errors)
        }


class Task:
    """
    A comprehensive model representing a single task within an experiment workflow.

    ### Architectural Decisions:
    - Implements a stateful task representation with rich metadata
    - Supports detailed task lifecycle tracking
    - Provides flexible configuration and result management
    - Enables comprehensive task execution and reporting

    ### Role in the System:
    - Represents a discrete unit of experiment execution
    - Tracks task configuration, execution status, and results
    - Manages coverage and error tracking for individual tasks
    - Supports detailed post-execution analysis

    ### Key Considerations:
    - Handles complex task state transitions
    - Supports multiple execution parameters
    - Provides rich metadata and result tracking
    - Enables detailed performance and coverage reporting

    ### Integration Strategy:
    - Compatible with various testing tools and experiment configurations
    - Supports flexible task scheduling and execution
    - Integrates with coverage and error tracking systems
    - Provides standardized task representation

    ### Performance and Scalability:
    - Lightweight task representation with minimal overhead
    - Supports large-scale experiment execution
    - Enables efficient task tracking and reporting
    - Adaptable to different experiment complexity levels
    """

    # Class-level counter for task IDs
    _next_id = 1

    def __init__(self, config: TaskConfiguration):
        """
        Initialize a task with its configuration.
        Uses standardized models for data representation.

        Args:
            config: Task configuration
        """
        self.id = Task._next_id
        Task._next_id += 1

        self.config = config
        self.result = TaskResult()
        self.logger = logging.getLogger(__name__)

        # Runtime data
        self.app: Optional[App] = None
        self.results_dir: str = ""
        self.static_data = None

        # Standard repository for coverage and error data
        from rvandroid.domain.coverage import LogcatRepository
        self.repository = LogcatRepository()

    def add_error(self, error: RvErrorLog) -> None:
        """
        Add an error to the task's repository.

        Args:
            error: Error log to add
        """
        # Ensure repository exists
        if not hasattr(self, 'repository') or self.repository is None:
            from rvandroid.domain.coverage import LogcatRepository
            self.repository = LogcatRepository()

        # Add to repository
        self.repository.register_rv_error(error)

    def add_method_call(self, coverage_log: RvCoverageLog) -> None:
        """
        Add a method call to the task's repository.

        Args:
            coverage_log: Coverage log to add
        """
        # Ensure repository exists
        if not hasattr(self, 'repository') or self.repository is None:
            from rvandroid.domain.coverage import LogcatRepository
            self.repository = LogcatRepository()

        # Add to repository
        self.repository.register_method_call(coverage_log)

    def update_coverage(self) -> None:
        """
        Update coverage metrics based on repository data.
        """
        if not hasattr(self, 'repository') or not self.repository or not self.static_data:
            self.logger.warning("Cannot update coverage: No repository or static data available")
            return

        # Calculate metrics directly from repository
        metrics = self.repository.calculate_metrics()
        metrics_dict = metrics.to_dict()

        # Update result metrics from repository using standardized keys
        self.result.coverage_metrics.update({
            "method_coverage": metrics_dict["method_coverage"],
            "activities_coverage": metrics_dict["activity_coverage"],
            "methods_jca_reachable_coverage": metrics_dict["mop_method_coverage"],
            "total_errors": metrics_dict["unique_errors"],
            "total_method_calls": metrics_dict["called_methods"]
        })

        # Store metrics for easy access
        self.coverage_metrics = metrics

        # Log summary of coverage metrics for quick reference
        self.logger.info(f"Coverage updated for task {self.id}:")
        self.logger.info(f"- Method coverage: {metrics_dict['method_coverage']:.2f}%")
        self.logger.info(f"- Activities coverage: {metrics_dict['activity_coverage']:.2f}%")
        self.logger.info(f"- MOP methods coverage: {metrics_dict['mop_method_coverage']:.2f}%")
        self.logger.info(f"- Methods called: {metrics_dict['called_methods']}")
        self.logger.info(f"- Errors detected: {metrics_dict['unique_errors']}")

    def get_repository(self) -> LogcatRepository:
        """
        Get the task's coverage repository, creating one if it doesn't exist.

        Returns:
            The task's LogcatRepository
        """
        if not hasattr(self, 'repository') or self.repository is None:
            from rvandroid.domain.coverage import LogcatRepository
            self.repository = LogcatRepository()

            # If logcat file exists, parse it and populate the repository
            if hasattr(self, 'result') and self.result.logcat_file and os.path.exists(self.result.logcat_file):
                from rvandroid.parser.log.logcat_parser import parse_logcat_file
                try:
                    self.repository = parse_logcat_file(self.result.logcat_file)
                except Exception as e:
                    self.logger.error(f"Error parsing logcat file: {e}")

        return self.repository

    def initialize(self, base_results_dir: str) -> None:
        """
        Initialize task paths and create necessary directories.

        Args:
            base_results_dir: Base directory for results
        """
        self.logger.info(f"Initializing task {self.id}: {self.config}")

        # Set status to configured
        self.result.status = TaskStatus.CONFIGURED

        # Create results directory
        app_results_dir = os.path.join(base_results_dir, self.config.apk_name)
        self.results_dir = app_results_dir
        os.makedirs(app_results_dir, exist_ok=True)

        # Generate output file paths
        base_name = f"{self.config.apk_name}__{self.config.repetition}__{self.config.timeout}__{self.config.tool_name}"
        self.result.logcat_file = os.path.join(app_results_dir, f"{base_name}.logcat")
        self.result.trace_file = os.path.join(app_results_dir, f"{base_name}.trace")

        self.logger.debug(f"Task initialized with result dir: {self.results_dir}")

    def set_app(self, app: App) -> None:
        """Set the app instance for this task"""
        self.app = app

    def mark_started(self) -> None:
        """Mark task as started with current timestamp"""
        self.result.start_time = datetime.now()
        self.result.status = TaskStatus.RUNNING

    def mark_completed(self) -> None:
        """Mark task as completed with current timestamp"""
        self.result.end_time = datetime.now()
        self.result.status = TaskStatus.EXECUTED
        self.result.update_execution_time()

    def mark_error(self, error_message: str) -> None:
        """
        Mark task as failed with error message.

        Args:
            error_message: Error description
        """
        self.result.end_time = datetime.now()
        self.result.status = TaskStatus.ERROR
        self.result.error_message = error_message
        self.result.update_execution_time()

    @property
    def executed(self) -> bool:
        """Check if task was executed"""
        return self.result.status == TaskStatus.EXECUTED

    @property
    def failed(self) -> bool:
        """Check if task failed"""
        return self.result.status == TaskStatus.ERROR

    def __str__(self) -> str:
        return f"Task[id={self.id}, {self.config}, status={self.result.status.name}]"
