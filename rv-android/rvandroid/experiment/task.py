import logging
import os
from datetime import datetime
from enum import Enum
from typing import Optional, Set, Tuple, Dict

from rvandroid import utils
from rvandroid.app import App
from rvandroid.constants import EXTENSION_LOGCAT, EXTENSION_TRACE
from rvandroid.log.log import RvCoverageLog
from rvandroid.parser import static_analysis_parser

# Constants
DEFAULT_DATETIME = utils.milliseconds_to_datetime(0)


class TaskStatus(Enum):
    """Enum representing the possible states of a task"""
    CREATED = 1
    RUNNING = 2
    EXECUTED = 3


class Task:
    """
    Represents a task for analyzing an Android APK file.
    
    This class manages the execution and tracking of analysis tasks
    for Android applications, including coverage metrics and execution timing.
    """
    _task_counter = 0  # Class variable to generate unique task IDs

    def __init__(self,
                 apk: str,
                 repetition: int,
                 timeout: int,
                 tool: str,
                 status: TaskStatus = TaskStatus.CREATED,
                 start_time: datetime = DEFAULT_DATETIME,
                 finish_time: datetime = DEFAULT_DATETIME,
                 error: str = ""):
        """
        Initialize a new Task instance.
        
        Args:
            apk: Name or path of the APK file to analyze
            repetition: Number of times to repeat the analysis
            timeout: Maximum execution time in seconds
            tool: Name of the analysis tool to use
            status: Initial status of the task
            start_time: Task start time
            finish_time: Task completion time
        """
        Task._task_counter += 1
        self.id = Task._task_counter
        self.tracker = TaskExecutionTracker()
        self.logger = logging.getLogger(__name__)

        # Task configuration
        self.apk = apk
        self.tool = tool
        self.timeout = timeout
        self.repetition = repetition
        self.status = status

        # Execution timing
        self.start_time = start_time
        self.finish_time = finish_time
        self.execution_time = 0

        # Output files and results
        self.results_dir = ""
        self.logcat_file = ""
        self.log_file = ""
        self.error = error
        self.results: list[dict] = []
        self.coverage: Dict = {}

    @property
    def executed(self) -> bool:
        """
        Check if the task has been executed.

        Returns:
            True if the task has been executed, False otherwise
        """
        return self.status == TaskStatus.EXECUTED

    def initialize(self, base_results_dir: str) -> None:
        """
        Initialize task execution environment and create necessary directories/files.
        
        Args:
            base_results_dir: Base directory for storing task results
        """
        self.start_time = datetime.now()
        self.status = TaskStatus.CREATED

        # Create results directory and output files
        results_dir = os.path.join(base_results_dir, self.apk)
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)

        # Generate base filename for output files
        base_name = f"{self.apk}__{self.repetition}__{self.timeout}__{self.tool}"
        self.logcat_file = os.path.join(results_dir, f"{base_name}{EXTENSION_LOGCAT}")
        self.log_file = os.path.join(results_dir, f"{base_name}{EXTENSION_TRACE}")

    def start_tracker(self, app: App) -> None:
        """
        Start tracking task execution metrics.
        
        Args:
            app: Android application instance being analyzed
        """
        self.tracker.start(self, app.package_name)

    def __str__(self) -> str:
        return f"[id={self.id}, apk={self.apk}, rep={self.repetition}, timeout={self.timeout}, tool={self.tool}]"

    def __repr__(self) -> str:
        return f"[{self.id},{self.apk},{self.repetition},{self.timeout},{self.tool},{self.status}]"


class TaskExecutionTracker:
    """
    Tracks and manages execution metrics for a task.
    
    This class maintains counters and sets for various metrics related to
    code coverage and method execution during task analysis.
    """

    def __init__(self):
        """Initialize a new TaskExecutionTracker instance."""
        self.logger = logging.getLogger(__name__)
        self.task: Optional[Task] = None

        # Total counts
        self.total_classes = 0
        self.total_activities = 0
        self.total_methods = 0
        self.total_reachable_methods = 0
        self.total_reaches_mop = 0
        self.total_directly_reaches_mop = 0

        # Visited sets
        self.visited_classes: Set[str] = set()
        self.visited_activities: Set[str] = set()
        self.visited_methods: Set[str] = set()
        self.visited_reachable_methods: Set[str] = set()
        self.visited_reaches_mop: Set[str] = set()
        self.visited_directly_reaches_mop: Set[str] = set()

        # Analysis results
        self.classes = None
        self.windows = None
        self.wtg = None

    def start(self, task: Task, package_name: str) -> None:
        """
        Start tracking a new task.
        
        Args:
            task: Task instance to track
            package_name: Android package name being analyzed
        """
        self.logger.info(f"Starting tracker for task={task}")
        self.task = task

        # Parse static analysis files
        self.classes, self.windows, self.wtg = static_analysis_parser.read_static_analysis_files(
            task.results_dir, task.apk, package_name
        )

        # Calculate initial metrics
        self._calculate_total_metrics()

    def _calculate_total_metrics(self) -> None:
        """Calculate total metrics from static analysis results."""
        for class_name, class_info in self.classes.classes.items():
            self.total_classes += 1

            if class_info.is_activity:
                self.total_activities += 1

            for method in class_info.methods:
                self.total_methods += 1
                if method.reachable:
                    self.total_reachable_methods += 1
                if method.reaches_mop:
                    self.total_reaches_mop += 1
                if method.directly_reaches_mop:
                    self.total_directly_reaches_mop += 1

    def call(self, coverage_log: RvCoverageLog) -> Tuple[float, float, float, float, float, float]:
        """
        Process a coverage log entry and update metrics.
        
        Args:
            coverage_log: Coverage log entry to process
            
        Returns:
            Tuple containing various coverage percentages
        """
        if coverage_log.clazz in self.classes.classes:
            class_info = self.classes.classes[coverage_log.clazz]

            # Update class and activity coverage
            if coverage_log.clazz not in self.visited_classes:
                self.visited_classes.add(coverage_log.clazz)
            if class_info.is_activity and coverage_log.clazz not in self.visited_activities:
                self.visited_activities.add(coverage_log.clazz)

            # Update method coverage
            signature = coverage_log.signature
            if signature in self.classes.methods:
                self.visited_methods.add(signature)
                method = self.classes.methods[signature]

                if method.reaches_mop:
                    self.visited_reaches_mop.add(signature)
                if method.directly_reaches_mop:
                    self.visited_directly_reaches_mop.add(signature)

        return self.calculate_coverage()

    def calculate_coverage(self) -> Tuple[float, float, float, float, float, float]:
        """
        Calculate current coverage percentages.
        
        Returns:
            Tuple containing:
            - Class coverage percentage
            - Activity coverage percentage
            - Method coverage percentage
            - Reachable methods coverage percentage
            - Methods reaching MOP coverage percentage
            - Methods directly reaching MOP coverage percentage
        """
        return (
            self._calculate_percentage(self.visited_classes, self.total_classes),
            self._calculate_percentage(self.visited_activities, self.total_activities),
            self._calculate_percentage(self.visited_methods, self.total_methods),
            self._calculate_percentage(self.visited_reachable_methods, self.total_reachable_methods),
            self._calculate_percentage(self.visited_reaches_mop, self.total_reaches_mop),
            self._calculate_percentage(self.visited_directly_reaches_mop, self.total_directly_reaches_mop)
        )

    @staticmethod
    def _calculate_percentage(collection: Set, total: int) -> float:
        """
        Calculate percentage of items covered.
        
        Args:
            collection: Set of visited/covered items
            total: Total number of possible items
            
        Returns:
            Coverage percentage (0-100)
        """
        return 0 if total == 0 else (len(collection) * 100) / total
