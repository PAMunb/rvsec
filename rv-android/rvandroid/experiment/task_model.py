# rvandroid/experiment/task_model.py
"""
Task model classes for experiment execution.
Provides a clear separation of concerns for task configuration, execution, and results.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional

from rvandroid.app import App
from rvandroid.model.log import RvCoverageLog, RvErrorLog


class TaskStatus(Enum):
    """Enum representing the possible states of a task"""
    CREATED = 1
    CONFIGURED = 2
    RUNNING = 3
    EXECUTED = 4
    ERROR = 5
    CANCELED = 6


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
    The Task class represents an individual unit of execution within an experiment.
    It defines the necessary attributes for task scheduling, execution, and tracking.

    ### Architectural Decisions:
    - Implements an object-oriented representation of tasks for better organization.
    - Supports dependency management, ensuring that tasks execute in the correct order.
    - Can be extended to include additional execution parameters if needed.

    ### Role in the System:
    - Serves as the fundamental building block for experiment workflows.
    - Enables flexible task execution, whether sequential or parallel.
    - Works alongside TaskExecutor and ExecutionManager to ensure smooth execution.
    """

    # Class-level counter for task IDs
    _next_id = 1

    def __init__(self, config: TaskConfiguration):
        """
        Initialize a task with its configuration.

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

        # Coverage data
        self.coverage: Dict = {}
        self.class_methods: Dict[str, List[RvCoverageLog]] = {}
        self.called_methods: Dict[str, Dict[str, Dict[str, RvCoverageLog]]] = {}
        self.errors: List[RvErrorLog] = []

    def add_error(self, error: RvErrorLog) -> None:
        """Add an error to the task's error list."""
        self.errors.append(error)

    def add_method_call(self, coverage_log: RvCoverageLog) -> None:
        """Add a method call to the task's coverage tracking."""
        if coverage_log.clazz not in self.class_methods:
            self.class_methods[coverage_log.clazz] = []

        self.class_methods[coverage_log.clazz].append(coverage_log)

        # Update the compatibility structure
        if coverage_log.clazz not in self.called_methods:
            self.called_methods[coverage_log.clazz] = {"methods": {}}

        self.called_methods[coverage_log.clazz]["methods"][coverage_log.signature] = coverage_log

    def update_coverage(self) -> None:
        """
        Update coverage metrics based on called methods and static data.

        This method processes the recorded method calls and compares them against
        the static analysis data to calculate various coverage metrics including:
        - Method coverage: Percentage of all methods that were called
        - Activity coverage: Percentage of activities that were called
        - JCA methods coverage: Percentage of methods related to JCA specifications that were called

        The method also updates the task's result metrics for reporting.
        """
        if not self.static_data or not hasattr(self.static_data, "classes"):
            self.logger.warning("Cannot update coverage: No static data available")
            return

        from rvandroid.analysis.coverage import process_coverage

        # Get all methods from static data
        all_methods = {}
        method_count = 0
        for class_name, class_info in self.static_data.classes.classes.items():
            all_methods[class_name] = {
                "is_activity": class_info.is_activity,  # Flag indicating if the class is an Activity
                "methods": {}
            }

            for method in class_info.methods:
                all_methods[class_name]["methods"][method.signature] = {
                    "reachable": method.reachable,  # Flag indicating if method can be reached through execution
                    "reaches_mop": method.reaches_mop,  # Flag indicating if method can reach a MOP specification point
                    "directly_reaches_mop": method.directly_reaches_mop,
                    # Flag indicating if method directly uses a MOP specification
                    "called": False  # Will be set to True if method was called during execution
                }
                method_count += 1

        # Log the static data for debugging
        self.logger.debug(f"Static data contains {len(all_methods)} classes and {method_count} methods")

        # Check if we have covered methods
        called_methods_count = sum(len(methods) for methods in self.class_methods.values())
        if called_methods_count == 0:
            self.logger.warning("No covered methods found, coverage will be 0%")
        else:
            self.logger.debug(f"Found {called_methods_count} covered methods")

        # If we have a directly populated coverage from CoverageTracker, use it
        if self.coverage and "SUMMARY" in self.coverage:
            self.logger.debug("Using pre-computed coverage")
        else:
            # If we already have formatted called_methods, use it directly
            if self.called_methods and any(cls.get("methods") for cls in self.called_methods.values()):
                self.logger.debug("Using existing formatted called_methods")
            else:
                # Update called_methods from class_methods for backward compatibility
                self.called_methods = {}
                for class_name, method_logs in self.class_methods.items():
                    if class_name not in self.called_methods:
                        self.called_methods[class_name] = {"methods": {}}

                    for log in method_logs:
                        self.called_methods[class_name]["methods"][log.signature] = log

            # Process coverage
            self.logger.debug(f"Processing coverage with {len(self.called_methods)} classes")
            self.coverage = process_coverage(self.called_methods, all_methods)

        # Update result metrics from coverage summary
        summary = self.coverage.get("SUMMARY", {})

        # Log detailed summary for debugging
        self.logger.debug(f"Coverage summary: {summary}")

        # Extract metrics and add to task result with explanations
        self.result.coverage_metrics.update({
            # Method coverage: Percentage of all application methods that were called during execution
            # Higher is better - indicates more code paths were exercised
            "method_coverage": summary.get("method_coverage", 0),

            # Activities coverage: Percentage of Android Activity classes that were called
            # Higher is better - indicates more screens in the app were tested
            "activities_coverage": summary.get("activities_coverage", 0),

            # Activities coverage total: Percentage of Activity classes called relative to all classes
            # This normalizes activity coverage against the total codebase
            "activities_coverage_total": summary.get("activities_coverage_total", 0),

            # JCA reachable methods coverage: Percentage of methods that can reach JCA operations that were called
            # Higher is better - indicates more code paths that could affect security properties were tested
            "methods_jca_reachable_coverage": summary.get("methods_jca_reachable_coverage", 0),

            # JCA reachable methods coverage total: Percentage of JCA-related methods called relative to all methods
            # This normalizes JCA method coverage against the total codebase
            "methods_jca_reachable_coverage_total": summary.get("methods_jca_reachable_coverage_total", 0),

            # Total method calls: Raw count of unique method calls recorded during execution
            # Higher is better - more method executions generally indicate more thorough testing
            "total_method_calls": sum(len(cls.get("methods", {})) for cls in self.called_methods.values()),

            # Total errors: Number of specification violations detected during execution
            # Lower is better - each error represents a potential security or functional issue
            "total_errors": len(self.errors)
        })

        # Log summary of coverage metrics for quick reference
        self.logger.info(f"Coverage updated for task {self.id}:")
        self.logger.info(f"- Method coverage: {self.result.coverage_metrics['method_coverage']:.2f}%")
        self.logger.info(f"- Activities coverage: {self.result.coverage_metrics['activities_coverage']:.2f}%")
        self.logger.info(
            f"- JCA methods coverage: {self.result.coverage_metrics['methods_jca_reachable_coverage']:.2f}%")
        self.logger.info(f"- Total methods called: {self.result.coverage_metrics['total_method_calls']}")
        self.logger.info(f"- Errors detected: {self.result.coverage_metrics['total_errors']}")

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
