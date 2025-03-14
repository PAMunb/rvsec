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
    """Results from a task execution"""
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
    Represents a test execution task with clear separation of configuration, execution, and results.
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
