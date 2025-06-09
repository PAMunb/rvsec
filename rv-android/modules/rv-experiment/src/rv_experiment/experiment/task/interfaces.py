# rvandroid/experiment/task/interfaces.py
"""
Core interfaces for the task execution subsystem.

This module provides the fundamental interfaces that define the contract
for task-related components in the RV-Android system, promoting clear
separation of concerns and enabling dependency injection.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any, Optional, TypeVar, Protocol

# TYPE_CHECKING import to avoid circular dependencies
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rv_android_core.domain.coverage import LogcatRepository


class TaskState(Enum):
    """
    Enum representing possible states in the task lifecycle.
    
    ### Architectural Decisions:
    - Uses auto() for value assignment to focus on state names rather than values
    - Organizes states in a logical flow sequence
    - Represents a complete task lifecycle from creation to completion
    - Supports error and cancellation states for robust lifecycle management
    
    ### Role in the System:
    - Defines the possible states in a task's lifecycle
    - Enables clear tracking of task progress
    - Supports state-based flow control and decision making
    - Facilitates reporting and visualization of task status
    """
    CREATED = auto()  # Task has been created but not yet configured
    CONFIGURED = auto()  # Task has been configured with all required settings
    INITIALIZING = auto()  # Task is preparing for execution (setting up directories, etc.)
    READY = auto()  # Task is fully initialized and ready for execution
    RUNNING = auto()  # Task is currently executing
    PAUSED = auto()  # Task execution has been temporarily paused
    COMPLETED = auto()  # Task has completed successfully
    ERROR = auto()  # Task encountered an error during execution
    CANCELED = auto()  # Task was explicitly canceled
    CLEANUP = auto()  # Task is cleaning up resources
    ARCHIVED = auto()  # Task has been archived for long-term storage


T = TypeVar('T')


class ITaskConfiguration(Protocol):
    """
    Interface defining the configuration for a task.
    
    ### Architectural Decisions:
    - Uses Protocol for structural typing rather than explicit inheritance
    - Defines required properties while allowing flexible implementation
    - Enables validation at runtime through type checking
    - Supports comprehensive configuration options for various task types
    
    ### Role in the System:
    - Defines the contract for task configuration objects
    - Ensures consistent configuration properties across the system
    - Enables validation of configuration completeness
    - Facilitates serialization and deserialization of task settings
    """
    apk_name: str  # Name of the APK to test
    repetition: int  # Repetition number of this task
    timeout: int  # Timeout in seconds for the task execution
    tool_name: str  # Name of the tool to use for testing
    no_window: bool  # Whether to run the emulator without a window
    clean_logcat: bool  # Whether to clean logcat before execution
    skip_installation: bool  # Whether to skip APK installation
    device_id: str  # Device ID to use for the emulator
    export_to_csv: bool  # Whether to export results to CSV


class ITaskResult(Protocol):
    """
    Interface defining the result of a task execution.
    
    ### Architectural Decisions:
    - Uses Protocol for structural typing to define expected properties
    - Separates execution metadata from analysis results
    - Supports comprehensive error reporting and status tracking
    - Enables flexible result representation for different task types
    
    ### Role in the System:
    - Defines the contract for task result objects
    - Ensures consistent result properties across the system
    - Enables standardized reporting and analysis of results
    - Facilitates serialization and deserialization of task outcomes
    """
    state: TaskState  # Current state of the task
    start_time: Optional[datetime]  # When the task started execution
    end_time: Optional[datetime]  # When the task finished execution
    execution_time_seconds: int  # How long the task took to execute
    error_message: Optional[str]  # Error message if the task failed
    logcat_file: str  # Path to the logcat file
    trace_file: str  # Path to the trace file
    coverage_metrics: Dict[str, float]  # Coverage metrics calculated from execution
    detected_errors: List[Dict[str, Any]]  # Errors detected during execution

    def update_execution_time(self) -> None:
        """Update execution time based on start and end times."""
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        pass


class ITask(Protocol):
    """
    Interface defining a task within the RV-Android system.
    
    ### Architectural Decisions:
    - Uses Protocol for structural typing to define expected properties and methods
    - Separates task identity from configuration and execution details
    - Enables comprehensive tracking of task lifecycle and results
    - Supports flexible implementation for different task types
    
    ### Role in the System:
    - Defines the contract for task objects
    - Ensures consistent task properties and methods across the system
    - Enables standardized task representation and manipulation
    - Facilitates serialization and deserialization of tasks
    """
    id: str  # Unique identifier for the task
    config: ITaskConfiguration  # Task configuration
    result: ITaskResult  # Task execution result
    repository: Optional['LogcatRepository']  # Repository for coverage data
    results_dir: str  # Directory for task results
    app: Any  # App instance for the task
    static_data: Any  # Static analysis data

    def initialize(self, base_results_dir: str) -> None:
        """Initialize task paths and create necessary directories."""
        pass

    def set_app(self, app: Any) -> None:
        """Set the app instance for this task."""
        pass

    def update_state(self, state: TaskState, error_message: Optional[str] = None) -> None:
        """Update the task state and related timestamps."""
        pass

    def add_error(self, error: Any) -> None:
        """Add an error to the task's repository."""
        pass

    def add_method_call(self, coverage_log: Any) -> None:
        """Add a method call to the task's repository."""
        pass

    def update_coverage(self) -> None:
        """Update coverage metrics based on repository data."""
        pass

    def get_repository(self) -> 'LogcatRepository':
        """Get the task's coverage repository."""
        pass

    @property
    def completed(self) -> bool:
        """Check if task completed successfully."""
        pass

    @property
    def failed(self) -> bool:
        """Check if task failed."""
        pass

    @property
    def running(self) -> bool:
        """Check if task is currently running."""
        pass

    @property
    def can_execute(self) -> bool:
        """Check if task is ready to execute."""
        pass


class ITaskComponent(ABC):
    """
    Interface for task execution components.
    
    Components are specialized modules that handle specific aspects of task
    execution, such as static analysis, coverage tracking, or tool execution.
    They provide a consistent interface for integration with the task executor.
    
    ### Architectural Decisions:
    - Uses abstract base class for strict interface definition
    - Defines a clear contract for task components
    - Supports dependency injection for flexible component configuration
    - Enables standardized error handling and lifecycle management
    
    ### Role in the System:
    - Provides a consistent interface for task execution components
    - Enables modular task execution with clear responsibility boundaries
    - Facilitates component reuse across different task types
    - Supports comprehensive error handling and cleanup
    """

    @abstractmethod
    def initialize(self, context: Dict[str, Any]) -> bool:
        """
        Initialize the component with task-specific context.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if initialization was successful, False otherwise
        """
        pass

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the component's primary function.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if execution was successful, False otherwise
        """
        pass

    @abstractmethod
    def cleanup(self, context: Dict[str, Any]) -> bool:
        """
        Clean up any resources used by the component.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the component name.
        
        Returns:
            The name of this component
        """
        pass


class ITaskExecutor(ABC):
    """
    Interface for task executors.
    
    Task executors are responsible for managing the lifecycle of a task,
    coordinating the various components involved in task execution, and
    handling errors and exceptions.
    
    ### Architectural Decisions:
    - Uses abstract base class for strict interface definition
    - Defines a clear contract for task executors
    - Supports dependency injection for flexible executor configuration
    - Enables standardized error handling and lifecycle management
    
    ### Role in the System:
    - Coordinates execution of task components
    - Manages task state transitions
    - Handles errors and exceptions during execution
    - Reports task status and progress
    """

    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the task with comprehensive error handling.
        
        Returns:
            True if execution was successful, False otherwise
        """
        pass

    @abstractmethod
    def register_component(self, component: ITaskComponent) -> None:
        """
        Register a component with the executor.
        
        Args:
            component: Component to register
        """
        pass

    @abstractmethod
    def get_components(self) -> List[ITaskComponent]:
        """
        Get all registered components.
        
        Returns:
            List of registered components
        """
        pass

    @abstractmethod
    def set_error_handler(self, handler: Any) -> None:
        """
        Set the error handler for the executor.
        
        Args:
            handler: Error handler to use
        """
        pass

    @abstractmethod
    def get_task_context(self) -> Dict[str, Any]:
        """
        Get the current task context.
        
        Returns:
            Dictionary with task context information
        """
        pass


class ITaskStorage(ABC):
    """
    Interface for task storage providers.
    
    Task storage providers are responsible for persisting task information,
    including configuration, state, and results, to a storage backend.
    
    ### Architectural Decisions:
    - Uses abstract base class for strict interface definition
    - Defines a clear contract for task storage providers
    - Supports different storage backends through consistent interface
    - Enables robust error handling and atomicity for data persistence
    
    ### Role in the System:
    - Persists task information to storage
    - Retrieves task information from storage
    - Ensures data integrity during storage operations
    - Supports filtering and querying of tasks
    """

    @abstractmethod
    def load(self) -> bool:
        """
        Load tasks from storage.
        
        Returns:
            True if loading was successful, False otherwise
        """
        pass

    @abstractmethod
    def save(self) -> bool:
        """
        Save tasks to storage.
        
        Returns:
            True if saving was successful, False otherwise
        """
        pass

    @abstractmethod
    def add_task(self, task: ITask) -> None:
        """
        Add a task to storage.
        
        Args:
            task: Task to add
        """
        pass

    @abstractmethod
    def update_task(self, task: ITask) -> None:
        """
        Update a task in storage.
        
        Args:
            task: Task to update
        """
        pass

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[ITask]:
        """
        Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task if found, None otherwise
        """
        pass

    @abstractmethod
    def get_tasks(self) -> List[ITask]:
        """
        Get all tasks.
        
        Returns:
            List of all tasks
        """
        pass

    @abstractmethod
    def get_tasks_by_state(self, state: TaskState) -> List[ITask]:
        """
        Get tasks with specified state.
        
        Args:
            state: Task state to filter by
            
        Returns:
            List of matching tasks
        """
        pass

    @abstractmethod
    def get_pending_tasks(self) -> List[ITask]:
        """
        Get tasks that are not yet completed, failed, or canceled.
        
        Returns:
            List of pending tasks
        """
        pass


class ITaskFactory(ABC):
    """
    Interface for task factory implementations.
    
    Task factories are responsible for creating task instances with
    appropriate configuration and initialization.
    
    ### Architectural Decisions:
    - Uses abstract base class for strict interface definition
    - Defines a clear contract for task factories
    - Supports different task types through consistent interface
    - Enables centralized task creation logic
    
    ### Role in the System:
    - Creates task instances with appropriate configuration
    - Ensures consistent task initialization
    - Centralizes task creation logic
    - Supports different task types through factory methods
    """

    @abstractmethod
    def create_task(self, config: ITaskConfiguration) -> ITask:
        """
        Create a new task instance.
        
        Args:
            config: Task configuration
            
        Returns:
            Newly created task instance
        """
        pass

    @abstractmethod
    def create_task_from_dict(self, data: Dict[str, Any]) -> Optional[ITask]:
        """
        Create a task from a dictionary representation.
        
        Args:
            data: Dictionary with task data
            
        Returns:
            Task instance if successful, None otherwise
        """
        pass
