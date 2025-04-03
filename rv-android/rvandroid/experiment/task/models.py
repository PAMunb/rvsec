# rvandroid/experiment/task/models.py
"""
Core model implementations for the task execution subsystem.

This module provides concrete implementations of the task-related interfaces,
including task configuration, results, and the task itself. These models are
the foundation of the task execution system.
"""

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional, Type, TypeVar, Generic

from rvandroid.app import App
from rvandroid.domain.coverage import LogcatRepository
from rvandroid.domain.log import RvCoverageLog, RvErrorLog
from rvandroid.experiment.task.interfaces import (
    TaskState, 
    ITaskConfiguration, 
    ITaskResult, 
    ITask
)
from rvandroid.util.logging.manager import LoggingManager


@dataclass
class TaskConfiguration:
    """
    Configuration parameters for a task.
    
    ### Architectural Decisions:
    - Uses dataclass for concise definition and automatic implementation of common methods
    - Provides clear separation between required and optional parameters
    - Uses explicit types for all fields for better code comprehension
    - Implements string representation for improved debugging
    
    ### Role in the System:
    - Defines the complete set of parameters needed to execute a task
    - Provides defaults for optional parameters
    - Enables serialization and deserialization of task configuration
    - Supports reproducible task execution
    """
    apk_name: str
    repetition: int
    timeout: int
    tool_name: str

    # Optional configuration with defaults
    no_window: bool = False
    clean_logcat: bool = True
    skip_installation: bool = False
    device_id: str = "emulator-5554"
    export_to_csv: bool = True

    def __str__(self) -> str:
        """
        Generate a human-readable string representation of the configuration.
        
        Returns:
            String representation
        """
        return (f"TaskConfiguration(apk={self.apk_name}, rep={self.repetition}, "
                f"timeout={self.timeout}, tool={self.tool_name})")
                
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "apk_name": self.apk_name,
            "repetition": self.repetition,
            "timeout": self.timeout,
            "tool_name": self.tool_name,
            "no_window": self.no_window,
            "clean_logcat": self.clean_logcat,
            "skip_installation": self.skip_installation,
            "device_id": self.device_id,
            "export_to_csv": self.export_to_csv
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskConfiguration':
        """
        Create configuration from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            TaskConfiguration instance
        """
        return cls(
            apk_name=data.get("apk_name", ""),
            repetition=data.get("repetition", 1),
            timeout=data.get("timeout", 60),
            tool_name=data.get("tool_name", ""),
            no_window=data.get("no_window", False),
            clean_logcat=data.get("clean_logcat", True),
            skip_installation=data.get("skip_installation", False),
            device_id=data.get("device_id", "emulator-5554"),
            export_to_csv=data.get("export_to_csv", True)
        )


@dataclass
class TaskResult:
    """
    Result of a task execution.
    
    ### Architectural Decisions:
    - Uses dataclass for concise definition and automatic implementation of common methods
    - Separates execution metadata from analysis results
    - Uses explicit types for all fields for better code comprehension
    - Implements utility methods for common operations
    
    ### Role in the System:
    - Stores the complete outcome of a task execution
    - Tracks execution time and resource usage
    - Provides coverage and error metrics
    - Enables serialization and deserialization of task results
    - Supports analysis and reporting of task outcomes
    """
    state: TaskState = TaskState.CREATED
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

    # State transition history
    state_transitions: List[Dict[str, Any]] = field(default_factory=list)

    def update_execution_time(self) -> None:
        """
        Update execution time if start and end times are available.
        """
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.execution_time_seconds = int(delta.total_seconds())

    def add_state_transition(self, state: TaskState, timestamp: Optional[datetime] = None) -> None:
        """
        Record a state transition with timestamp.
        
        Args:
            state: New state
            timestamp: When the transition occurred (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        self.state_transitions.append({
            "state": state,
            "timestamp": timestamp.isoformat(),
            "previous_state": self.state
        })
        
        self.state = state

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "state": self.state.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time_seconds": self.execution_time_seconds,
            "error_message": self.error_message,
            "logcat_file": self.logcat_file,
            "trace_file": self.trace_file,
            "coverage_metrics": self.coverage_metrics,
            "detected_errors_count": len(self.detected_errors),
            "state_transitions": self.state_transitions
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        """
        Create result from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            TaskResult instance
        """
        result = cls()
        
        try:
            # Set basic fields
            result.state = TaskState[data.get("state", "CREATED")]
            
            # Parse dates if present
            if data.get("start_time"):
                result.start_time = datetime.fromisoformat(data["start_time"])
            if data.get("end_time"):
                result.end_time = datetime.fromisoformat(data["end_time"])
                
            result.execution_time_seconds = data.get("execution_time_seconds", 0)
            result.error_message = data.get("error_message")
            result.logcat_file = data.get("logcat_file", "")
            result.trace_file = data.get("trace_file", "")
            
            # Set complex fields
            result.coverage_metrics = data.get("coverage_metrics", {})
            result.detected_errors = data.get("detected_errors", [])
            result.state_transitions = data.get("state_transitions", [])
        
        except Exception as e:
            logging.getLogger(__name__).error(f"Error deserializing TaskResult: {e}")
            
        return result


class Task:
    """
    A comprehensive model representing a single task within an experiment workflow.
    
    ### Architectural Decisions:
    - Uses UUID for robust, distributed-safe identification
    - Implements a state machine for lifecycle management
    - Provides comprehensive error handling and reporting
    - Centralizes coverage tracking and analysis
    
    ### Role in the System:
    - Represents a discrete unit of experiment execution
    - Tracks task configuration, execution status, and results
    - Manages coverage and error tracking for individual tasks
    - Supports detailed post-execution analysis
    - Enables persistence and serialization of task state
    """

    def __init__(self, config: TaskConfiguration, task_id: Optional[str] = None):
        """
        Initialize a task with its configuration.
        Uses standardized models for data representation.

        Args:
            config: Task configuration
            task_id: Optional task ID (generated if not provided)
        """
        self.id = task_id or str(uuid.uuid4())
        self.config = config
        self.result = TaskResult()
        
        # Get logger
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.task',
            {
                'task_id': self.id,
                'apk_name': self.config.apk_name,
                'tool_name': self.config.tool_name
            }
        )

        # Runtime data
        self.app: Optional[App] = None
        self.results_dir: str = ""
        self.static_data = None

        # Standard repository for coverage and error data
        self.repository = LogcatRepository()
        
        # Record creation
        self.result.add_state_transition(TaskState.CREATED)
        self.logger.info(f"Task {self.id} created with configuration: {self.config}")

    def add_error(self, error: RvErrorLog) -> None:
        """
        Add an error to the task's repository.

        Args:
            error: Error log to add
        """
        # Ensure repository exists
        if not hasattr(self, 'repository') or self.repository is None:
            self.repository = LogcatRepository()

        # Add to repository
        self.repository.register_rv_error(error)
        
        # Log the error
        self.logger.info(f"Error registered: {error}")

    def add_method_call(self, coverage_log: RvCoverageLog) -> None:
        """
        Add a method call to the task's repository.

        Args:
            coverage_log: Coverage log to add
        """
        # Ensure repository exists
        if not hasattr(self, 'repository') or self.repository is None:
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
            self.repository = LogcatRepository()

            # If logcat file exists, parse it and populate the repository
            if hasattr(self, 'result') and self.result.logcat_file and os.path.exists(self.result.logcat_file):
                from rvandroid.parser.log.logcat_parser import parse_logcat_file
                try:
                    self.repository = parse_logcat_file(self.result.logcat_file)
                    self.logger.info(f"Parsed logcat file: {self.result.logcat_file}")
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
        self.update_state(TaskState.INITIALIZING)

        # Create results directory
        app_results_dir = os.path.join(base_results_dir, self.config.apk_name)
        self.results_dir = app_results_dir
        os.makedirs(app_results_dir, exist_ok=True)

        # Generate output file paths
        base_name = f"{self.config.apk_name}__{self.config.repetition}__{self.config.timeout}__{self.config.tool_name}"
        self.result.logcat_file = os.path.join(app_results_dir, f"{base_name}.logcat")
        self.result.trace_file = os.path.join(app_results_dir, f"{base_name}.trace")

        # Mark as ready
        self.update_state(TaskState.READY)
        self.logger.debug(f"Task initialized with result dir: {self.results_dir}")

    def set_app(self, app: App) -> None:
        """
        Set the app instance for this task.
        
        Args:
            app: App instance
        """
        self.app = app
        self.logger.debug(f"Set app: {app.name}")

    def update_state(self, state: TaskState, error_message: Optional[str] = None) -> None:
        """
        Update the task state and related timestamps.
        
        Args:
            state: New task state
            error_message: Optional error message for ERROR state
        """
        # Record the state transition
        self.result.add_state_transition(state)
        
        # Perform state-specific actions
        if state == TaskState.RUNNING:
            self.result.start_time = datetime.now()
            self.logger.info(f"Task {self.id} started at {self.result.start_time}")
            
        elif state in [TaskState.COMPLETED, TaskState.ERROR, TaskState.CANCELED]:
            self.result.end_time = datetime.now()
            
            if state == TaskState.ERROR and error_message:
                self.result.error_message = error_message
                self.logger.error(f"Task {self.id} failed: {error_message}")
            elif state == TaskState.COMPLETED:
                self.logger.info(f"Task {self.id} completed successfully")
            elif state == TaskState.CANCELED:
                self.logger.info(f"Task {self.id} was canceled")
                
            # Update execution time
            self.result.update_execution_time()
            self.logger.info(f"Execution time: {self.result.execution_time_seconds} seconds")
            
        self.logger.debug(f"Task state updated: {state.name}")

    @property
    def completed(self) -> bool:
        """
        Check if task completed successfully.
        
        Returns:
            True if task completed successfully
        """
        return self.result.state == TaskState.COMPLETED

    @property
    def failed(self) -> bool:
        """
        Check if task failed.
        
        Returns:
            True if task failed
        """
        return self.result.state == TaskState.ERROR

    @property
    def running(self) -> bool:
        """
        Check if task is currently running.
        
        Returns:
            True if task is running
        """
        return self.result.state == TaskState.RUNNING

    @property
    def can_execute(self) -> bool:
        """
        Check if task is ready to execute.
        
        Returns:
            True if task is ready to execute
        """
        return self.result.state == TaskState.READY

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "config": self.config.to_dict(),
            "result": self.result.to_dict()
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional['Task']:
        """
        Create task from dictionary.
        
        Args:
            data: Dictionary representation
            
        Returns:
            Task instance or None if error
        """
        try:
            # Create config from dictionary
            config_data = data.get("config", {})
            config = TaskConfiguration.from_dict(config_data)
            
            # Create task with given ID
            task_id = data.get("id", str(uuid.uuid4()))
            task = cls(config, task_id)
            
            # Set result from dictionary
            result_data = data.get("result", {})
            task.result = TaskResult.from_dict(result_data)
            
            return task
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error creating task from dictionary: {e}")
            return None

    def __str__(self) -> str:
        """
        Generate a human-readable string representation of the task.
        
        Returns:
            String representation
        """
        return f"Task[id={self.id}, {self.config}, state={self.result.state.name}]"

T = TypeVar('T', bound=Task)

class TaskFactory(Generic[T]):
    """
    Factory for creating task instances.
    
    ### Architectural Decisions:
    - Uses generics to support different task types
    - Provides centralized task creation logic
    - Supports creation from configuration or dictionary
    - Ensures consistent task initialization
    
    ### Role in the System:
    - Creates task instances with appropriate configuration
    - Ensures consistent task initialization
    - Centralizes task creation logic
    - Supports different task types through generics
    """
    
    def __init__(self, task_class: Type[T]):
        """
        Initialize the factory with a task class.
        
        Args:
            task_class: Class to use for creating tasks
        """
        self.task_class = task_class
        self.logger = logging.getLogger(__name__)
        
    def create_task(self, config: TaskConfiguration, task_id: Optional[str] = None) -> T:
        """
        Create a new task instance.
        
        Args:
            config: Task configuration
            task_id: Optional task ID (generated if not provided)
            
        Returns:
            Newly created task instance
        """
        return self.task_class(config, task_id)
        
    def create_task_from_dict(self, data: Dict[str, Any]) -> Optional[T]:
        """
        Create a task from a dictionary representation.
        
        Args:
            data: Dictionary with task data
            
        Returns:
            Task instance if successful, None otherwise
        """
        try:
            # Extract config and ID
            config_data = data.get("config", {})
            config = TaskConfiguration.from_dict(config_data)
            task_id = data.get("id")
            
            # Create task
            task = self.create_task(config, task_id)
            
            # Set result data
            result_data = data.get("result", {})
            task.result = TaskResult.from_dict(result_data)
            
            return task
            
        except Exception as e:
            self.logger.error(f"Error creating task from dictionary: {e}")
            return None