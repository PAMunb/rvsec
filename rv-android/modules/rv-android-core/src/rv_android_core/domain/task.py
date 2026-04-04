# rv_platform/execution/task.py
"""
Core model implementations for the task execution subsystem.

This module provides concrete implementations of the task-related interfaces,
including task configuration, results, and the task itself. These models are
the foundation of the task execution system.
"""

import logging
import os
import uuid
from datetime import datetime
from enum import Enum

# TYPE_CHECKING import to avoid missing dependencies during tests
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import Field
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.validation.base import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model

if TYPE_CHECKING:
    from rv_android_core.domain.app import App
else:
    # Fallback for when full dependencies aren't available
    App = Any
if TYPE_CHECKING:
    from rv_android_core.domain.coverage import LogcatRepository
    from rv_android_core.domain.log import RvCoverageLog, RvErrorLog
else:
    # Fallback for when full dependencies aren't available
    LogcatRepository = Any
    RvCoverageLog = Any
    RvErrorLog = Any

if TYPE_CHECKING:
    from rv_android_core.util.logging.manager import LoggingManager
else:
    # Fallback for when full dependencies aren't available
    try:
        from rv_android_core.util.logging.manager import LoggingManager
    except ImportError:
        LoggingManager = None


class TaskState(Enum):
    """Task execution states for lifecycle management."""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELED = "canceled"


@validated_model(["name"])
class ToolConfig(BaseValidatedModel):
    """
    Tool configuration for experiment specification and task execution.

    Each ToolConfig represents exactly one (tool, variant, parameters) combination.
    For experiments with multiple variants of the same tool, create multiple ToolConfig
    instances — one per variant. All modules import ToolConfig from rv-android-core.

    Fields:
        name: Tool identifier (e.g., "droidbot", "rvagent", "monkey")
        variant: Variant name for preset configuration (e.g., "dfs_greedy", "multimode")
        parameters: Parameter overrides that are merged with variant defaults
    """

    name: str = Field(..., description="Tool identifier")
    variant: str = Field(default="default", description="Tool variant name")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Tool-specific parameter overrides"
    )

    def get_full_tool_name(self) -> str:
        """
        Get full tool identification string including variant.

        Returns:
            Full tool name in format "name:variant" or "name" if default variant.
        """
        if self.variant and self.variant != "default":
            return f"{self.name}:{self.variant}"
        return self.name

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert tool configuration to dictionary for serialization.

        Returns:
            Dictionary representation with keys: name, variant, parameters.
        """
        return {
            "name": self.name,
            "variant": self.variant,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolConfig":
        """
        Create tool configuration from dictionary.

        Args:
            data: Dictionary with keys: name, variant, parameters.

        Returns:
            ToolConfig instance
        """
        return cls(
            name=data.get("name", ""),
            variant=data.get("variant", "default"),
            parameters=data.get("parameters", {}),
        )

    @classmethod
    def from_tool_specification(
        cls, tool_spec: str, parameters: Dict[str, Any] = None
    ) -> "ToolConfig":
        """
        Create tool configuration from CLI-style tool specification.

        Parses "name:variant" or "name" format.

        Args:
            tool_spec: Tool specification string (e.g., "droidbot:dfs_greedy" or "ape")
            parameters: Parameter overrides for tool configuration

        Returns:
            ToolConfig instance with parsed tool name and variant
        """
        parameters = parameters or {}

        if ":" in tool_spec:
            tool_name, variant = tool_spec.split(":", 1)
        else:
            tool_name = tool_spec
            variant = "default"

        return cls(
            name=tool_name.strip(), variant=variant.strip(), parameters=parameters
        )

    def __str__(self) -> str:
        """String representation for debugging."""
        return f"ToolConfig(name={self.name}, variant={self.variant})"

    def __repr__(self):
        return f"ToolConfig({self.name}, {self.variant})"


@validated_model(["apk_name", "repetition", "timeout", "tool_config"])
class TaskConfiguration(BaseValidatedModel):
    """
    Configuration parameters for a task with tool variant support.

    Defines the complete set of parameters needed to execute a task.
    tool_config provides tool identification with variant support for precise tool instantiation.
    """

    apk_name: str = Field(..., description="Name of the APK to be processed")
    repetition: int = Field(..., description="Repetition number for this task")
    timeout: int = Field(..., description="Timeout in seconds for task execution")
    tool_config: ToolConfig = Field(
        ..., description="Tool configuration with variant support"
    )

    # Optional configuration with defaults
    no_window: bool = Field(default=False, description="Run in headless mode")
    clean_logcat: bool = Field(
        default=True, description="Clean logcat before execution"
    )
    skip_installation: bool = Field(
        default=False, description="Skip APK installation"
    )  # TODO(#25): Remove this
    device_id: str = Field(default="emulator-5554", description="Target device ID")
    export_to_csv: bool = Field(
        default=True, description="Export results to CSV"
    )  # TODO(#25): Remove this

    def __str__(self) -> str:
        """
        Generate a human-readable string representation of the configuration.

        Returns:
            String representation
        """
        return (
            f"TaskConfiguration(apk={self.apk_name}, rep={self.repetition}, "
            f"timeout={self.timeout}, tool={self.tool_config.get_full_tool_name()})"
        )

    def __repr__(self):
        return f"TaskConfiguration({self.apk_name}, {self.repetition}, {self.timeout}, {self.tool_config})"

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
            "tool_config": self.tool_config.to_dict(),
            "no_window": self.no_window,
            "clean_logcat": self.clean_logcat,
            "skip_installation": self.skip_installation,
            "device_id": self.device_id,
            "export_to_csv": self.export_to_csv,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskConfiguration":
        """
        Create configuration from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TaskConfiguration instance
        """
        if "tool_config" in data:
            tool_config = ToolConfig.from_dict(data["tool_config"])
        else:
            tool_config = ToolConfig(name="")

        return cls(
            apk_name=data.get("apk_name", ""),
            repetition=data.get("repetition", 1),
            timeout=data.get("timeout", 60),
            tool_config=tool_config,
            no_window=data.get("no_window", False),
            clean_logcat=data.get("clean_logcat", True),
            skip_installation=data.get("skip_installation", False),
            device_id=data.get("device_id", "emulator-5554"),
            export_to_csv=data.get("export_to_csv", True),
        )

    @classmethod
    def create_from_tool_spec(
        cls,
        apk_name: str,
        repetition: int,
        timeout: int,
        tool_spec: str,
        parameters: Dict[str, Any] = None,
        **kwargs,
    ) -> "TaskConfiguration":
        """
        Create task configuration from tool specification string.

        Args:
            apk_name: APK name
            repetition: Repetition number
            timeout: Timeout in seconds
            tool_spec: Tool specification (e.g., "droidbot:dfs_greedy" or "ape")
            parameters: Parameter overrides for tool configuration
            **kwargs: Other task configuration parameters

        Returns:
            TaskConfiguration with parsed tool configuration
        """
        tool_config = ToolConfig.from_tool_specification(tool_spec, parameters)

        return cls(
            apk_name=apk_name,
            repetition=repetition,
            timeout=timeout,
            tool_config=tool_config,
            no_window=kwargs.get("no_window", False),
            clean_logcat=kwargs.get("clean_logcat", True),
            skip_installation=kwargs.get("skip_installation", False),
            device_id=kwargs.get("device_id", "emulator-5554"),
            export_to_csv=kwargs.get("export_to_csv", True),
        )


@validated_model(["start_time", "end_time"])
class TaskResult(BaseValidatedModel):
    """
    Task execution result with accurate timing measurement capabilities.

    ### Architectural Decisions:
    - Inherits from BaseValidatedModel for comprehensive validation and serialization
    - Implements constructor compatibility for existing code through @validated_model
    - Separates task lifecycle timing from tool execution timing for accurate measurement
    - Provides comprehensive error handling through ErrorHandler integration

    ### Role in the System:
    - Stores the complete outcome of a task execution with precise timing data
    - Tracks both task lifecycle and tool execution phases separately
    - Provides coverage and error metrics with accurate timing context
    - Enables serialization and deserialization of task results
    - Supports analysis and reporting of task outcomes with timing precision

    ### Timing Architecture:
    - start_time: When task state changes to RUNNING (task lifecycle start)
    - tool_execution_start: When actual tool execution begins (accurate for coverage logs)
    - end_time: When task completes, fails, or is canceled
    - execution_time_seconds: Total task duration from start_time to end_time
    """

    state: TaskState = Field(
        default=TaskState.CREATED, description="Current task execution state"
    )
    start_time: Optional[datetime] = Field(
        default=None, description="Task lifecycle start timestamp"
    )
    end_time: Optional[datetime] = Field(
        default=None, description="Task completion timestamp"
    )
    tool_execution_start: Optional[datetime] = Field(
        default=None, description="Tool execution start timestamp for accurate timing"
    )
    execution_time_seconds: int = Field(
        default=0, description="Total task execution duration"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if task failed"
    )

    # Output files
    logcat_file: str = Field(default="", description="Path to logcat output file")
    trace_file: str = Field(default="", description="Path to trace output file")

    # Analysis results
    coverage_metrics: Dict[str, float] = Field(
        default_factory=dict, description="Coverage analysis metrics"
    )
    detected_errors: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of detected errors"
    )

    # State transition history
    state_transitions: List[Dict[str, Any]] = Field(
        default_factory=list, description="Task state change history"
    )

    @ErrorHandler.handle_errors(component="TaskResult", phase="timing")
    def mark_tool_execution_start(self) -> None:
        """
        Mark the precise moment when tool execution begins.

        This provides accurate timing for coverage analysis where time_since_task_start
        should reflect tool execution duration rather than task lifecycle duration.
        """
        self.tool_execution_start = datetime.now()

    @ErrorHandler.handle_errors(component="TaskResult", phase="timing")
    def get_time_since_tool_start(self) -> int:
        """
        Calculate seconds elapsed since tool execution started.

        Returns:
            Seconds since tool execution started, or 0 if tool hasn't started
        """
        if self.tool_execution_start:
            return int((datetime.now() - self.tool_execution_start).total_seconds())
        return 0

    @ErrorHandler.handle_errors(component="TaskResult", phase="timing")
    def get_time_since_task_start(self) -> int:
        """
        Calculate seconds elapsed since task started.

        Returns:
            Seconds since task started, or 0 if task hasn't started
        """
        if self.start_time:
            return int((datetime.now() - self.start_time).total_seconds())
        return 0

    def update_execution_time(self) -> None:
        """
        Update execution time if start and end times are available.
        """
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            self.execution_time_seconds = int(delta.total_seconds())

    def add_state_transition(
        self, state: TaskState, timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a state transition with timestamp.

        Args:
            state: New state
            timestamp: When the transition occurred (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        self.state_transitions.append(
            {
                "state": state.name,
                "timestamp": timestamp.isoformat(),
                "previous_state": self.state.name,
            }
        )

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
            "tool_execution_start": (
                self.tool_execution_start.isoformat()
                if self.tool_execution_start
                else None
            ),
            "execution_time_seconds": self.execution_time_seconds,
            "error_message": self.error_message,
            "logcat_file": self.logcat_file,
            "trace_file": self.trace_file,
            "coverage_metrics": self.coverage_metrics,
            "detected_errors_count": len(self.detected_errors),
            "state_transitions": self.state_transitions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskResult":
        """
        Create result from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            TaskResult instance
        """
        try:
            # Parse datetime fields
            start_time = None
            if data.get("start_time"):
                start_time = datetime.fromisoformat(data["start_time"])

            end_time = None
            if data.get("end_time"):
                end_time = datetime.fromisoformat(data["end_time"])

            tool_execution_start = None
            if data.get("tool_execution_start"):
                tool_execution_start = datetime.fromisoformat(
                    data["tool_execution_start"]
                )

            # Create instance with parsed data
            result = cls(
                state=TaskState[data.get("state", "CREATED")],
                start_time=start_time,
                end_time=end_time,
                tool_execution_start=tool_execution_start,
                execution_time_seconds=data.get("execution_time_seconds", 0),
                error_message=data.get("error_message"),
                logcat_file=data.get("logcat_file", ""),
                trace_file=data.get("trace_file", ""),
                coverage_metrics=data.get("coverage_metrics", {}),
                detected_errors=data.get("detected_errors", []),
                state_transitions=data.get("state_transitions", []),
            )

            return result

        except Exception as e:
            # Use LoggingManager for consistent logging
            if LoggingManager:
                logging_manager = LoggingManager.get_instance()
                logger = logging_manager.get_logger("rv_android_core.domain.task")
                logger.error(f"Error deserializing TaskResult: {e}")
            else:
                logging.getLogger(__name__).error(
                    f"Error deserializing TaskResult: {e}"
                )
            # Return default instance on error
            return cls()


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

        Args:
            config: Task configuration defining APK, tool, timeout, and device
            task_id: Optional task ID (auto-generated UUID if not provided)

        State:
            self.id: Unique task identifier (UUID string).
            self.config: Immutable task configuration.
            self.result: Mutable TaskResult tracking state, timing, and metrics.
            self.app: App instance set during execution setup. None until set_app().
            self.results_dir: Output directory path. Empty until initialize().
            self.static_data: Static analysis data for coverage. None until set externally.
            self.repository: LogcatRepository for coverage/error tracking. None if
                coverage module unavailable.
        """
        self.id = task_id or str(uuid.uuid4())
        self.config = config
        self.result = TaskResult()

        # Get logger
        if LoggingManager:
            logging_manager = LoggingManager.get_instance()
            self.logger = logging_manager.get_logger(
                "rv_android_core.domain.task",
                {
                    "task_id": self.id,
                    "apk_name": self.config.apk_name,
                    "tool": self.config.tool_config.get_full_tool_name(),
                },
            )
        else:
            # Fallback to standard logging
            self.logger = logging.getLogger("rv_android_core.domain.task")

        # Runtime data
        self.app: Optional[App] = None
        self.results_dir: str = ""
        self.static_data = None

        # Standard repository for coverage and error data
        if LogcatRepository != Any:
            self.repository = LogcatRepository()
        else:
            self.repository = None

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
        if not hasattr(self, "repository") or self.repository is None:
            if LogcatRepository != Any:
                self.repository = LogcatRepository()
            else:
                self.repository = None

        # Add to repository
        if self.repository is not None:
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
        if not hasattr(self, "repository") or self.repository is None:
            if LogcatRepository != Any:
                self.repository = LogcatRepository()
            else:
                self.repository = None

        # Add to repository
        if self.repository is not None:
            self.repository.register_method_call(coverage_log)

    def update_coverage(self) -> None:
        """
        Update coverage metrics based on repository data.
        """
        if (
            not hasattr(self, "repository")
            or not self.repository
            or not self.static_data
        ):
            self.logger.warning(
                "Cannot update coverage: No repository or static data available"
            )
            return

        # Calculate metrics directly from repository
        metrics = self.repository.calculate_metrics()
        metrics_dict = metrics.to_dict()

        # Update result metrics from repository using standardized keys
        self.result.coverage_metrics.update(
            {
                "method_coverage": metrics_dict["method_coverage"],
                "activities_coverage": metrics_dict["activity_coverage"],
                "methods_jca_reachable_coverage": metrics_dict["mop_method_coverage"],
                "total_errors": metrics_dict["unique_errors"],
                "total_method_calls": metrics_dict["called_methods"],
            }
        )

        # Store metrics for easy access
        self.coverage_metrics = metrics

        # Log summary of coverage metrics for quick reference
        self.logger.info(f"Coverage updated for task {self.id}:")
        self.logger.info(f"- Method coverage: {metrics_dict['method_coverage']:.2f}%")
        self.logger.info(
            f"- Activities coverage: {metrics_dict['activity_coverage']:.2f}%"
        )
        self.logger.info(
            f"- MOP methods coverage: {metrics_dict['mop_method_coverage']:.2f}%"
        )
        self.logger.info(f"- Methods called: {metrics_dict['called_methods']}")
        self.logger.info(f"- Errors detected: {metrics_dict['unique_errors']}")

    def get_repository(self) -> LogcatRepository:
        """
        Get the task's coverage repository, creating one if it doesn't exist.

        Returns:
            The task's LogcatRepository
        """
        if not hasattr(self, "repository") or self.repository is None:
            if LogcatRepository != Any:
                self.repository = LogcatRepository()
            else:
                self.repository = None

            # If logcat file exists, parse it and populate the repository
            if (
                hasattr(self, "result")
                and self.result.logcat_file
                and os.path.exists(self.result.logcat_file)
            ):
                from rv_coverage.parser.log.logcat_parser import parse_logcat_file

                try:
                    # CRITICAL: Pass static_data to preserve class/method information during parsing
                    # Without static_data, all method calls are ignored as "unknown classes"
                    self.repository = parse_logcat_file(
                        self.result.logcat_file, self.static_data
                    )
                    self.logger.info(
                        f"Parsed logcat file: {self.result.logcat_file} with static data"
                    )
                except Exception as e:
                    self.logger.error(f"Error parsing logcat file: {e}")
                    # Fallback: try without static data
                    try:
                        self.repository = parse_logcat_file(self.result.logcat_file)
                        self.logger.warning(
                            "Parsed logcat file without static data - method calls may be ignored"
                        )
                    except Exception as fallback_error:
                        self.logger.error(
                            f"Failed to parse logcat file even without static data: {fallback_error}"
                        )

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

        # Generate output file paths with variant information
        base_name = f"{self.config.apk_name}__{self.config.repetition}__{self.config.timeout}__{self.config.tool_config.get_full_tool_name()}"
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

    def update_state(
        self, state: TaskState, error_message: Optional[str] = None
    ) -> None:
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
            self.logger.info(
                f"Execution time: {self.result.execution_time_seconds} seconds"
            )

        self.logger.debug(f"Task state updated: {state.name}")

    def mark_tool_execution_start(self) -> None:
        """
        Mark the precise moment when tool execution begins.

        This method delegates to TaskResult for accurate timing measurement
        and ensures timing data is available for coverage analysis.
        """
        self.result.mark_tool_execution_start()
        self.logger.debug(
            f"Tool execution started at {self.result.tool_execution_start}"
        )

    def get_time_since_tool_start(self) -> int:
        """
        Get seconds elapsed since tool execution started.

        Returns:
            Seconds since tool execution started
        """
        return self.result.get_time_since_tool_start()

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
            "result": self.result.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["Task"]:
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
            # Use LoggingManager for consistent logging
            if LoggingManager:
                logging_manager = LoggingManager.get_instance()
                logger = logging_manager.get_logger("rv_android_core.domain.task")
                logger.error(f"Error creating task from dictionary: {e}")
            else:
                logging.getLogger(__name__).error(
                    f"Error creating task from dictionary: {e}"
                )
            return None

    def __str__(self) -> str:
        """
        Generate a human-readable string representation of the task.

        Returns:
            String representation
        """
        return f"Task[id={self.id}, {self.config}, state={self.result.state.name}]"


T = TypeVar("T", bound=Task)


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

    def create_task(
        self, config: TaskConfiguration, task_id: Optional[str] = None
    ) -> T:
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
