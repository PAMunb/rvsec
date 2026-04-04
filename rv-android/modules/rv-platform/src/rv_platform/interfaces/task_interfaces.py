"""
Core interfaces for the task execution subsystem in rv-platform.

This module provides the fundamental interfaces that define the contract
for task-related components in the RV-Android system, promoting clear
separation of concerns and enabling dependency injection.

Note: Concrete implementations (TaskExecutor, TaskStorage, component classes)
do not formally inherit from these ABCs — they follow the same API by convention.
These interfaces serve as documentation of the expected contracts rather than
enforced type constraints, keeping the system simpler (P1: Simplicity).
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, TypeVar

# TaskState is now located in rv_platform.execution.task_model to avoid duplication
# and ensure compatibility with serialization/deserialization
if TYPE_CHECKING:
    from rv_android_core.domain.task import TaskState

T = TypeVar("T")


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

        Called once per task execution, before execute(). Components should
        prepare internal state but NOT acquire expensive resources (emulators,
        file handles) — those are deferred to execute() or phase-specific
        methods (e.g., start_capture(), start_tracking()).

        Args:
            context: Dictionary with task context information

        Returns:
            True if initialization was successful, False otherwise
        """

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the component's primary function.

        For some components (Emulator, Logcat), this is a no-op because their
        actual work is driven by the executor's phase coordination. For others
        (StaticAnalysis, Coverage), this performs real work during Phases 1-2.

        Args:
            context: Dictionary with task context information

        Returns:
            True if execution was successful, False otherwise
        """

    @abstractmethod
    def cleanup(self, context: Dict[str, Any]) -> bool:
        """
        Clean up any resources used by the component.

        Called after execution completes (both success and failure paths).
        Must be idempotent — may be called multiple times if error recovery
        triggers additional cleanup attempts.

        Args:
            context: Dictionary with task context information

        Returns:
            True if cleanup was successful, False otherwise
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the component name.

        Returns:
            The name of this component
        """


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

    @abstractmethod
    def register_component(self, component: ITaskComponent) -> None:
        """
        Register a component with the executor.

        Args:
            component: Component to register
        """

    @abstractmethod
    def get_components(self) -> List[ITaskComponent]:
        """
        Get all registered components.

        Returns:
            List of registered components
        """

    @abstractmethod
    def set_error_handler(self, handler: Any) -> None:
        """
        Set the error handler for the executor.

        Args:
            handler: Error handler to use
        """

    @abstractmethod
    def get_task_context(self) -> Dict[str, Any]:
        """
        Get the current task context.

        Returns:
            Dictionary with task context information
        """


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

    @abstractmethod
    def save(self) -> bool:
        """
        Save tasks to storage.

        Returns:
            True if saving was successful, False otherwise
        """

    @abstractmethod
    def add_task(self, task: Any) -> None:
        """
        Add a task to storage.

        Args:
            task: Task to add
        """

    @abstractmethod
    def update_task(self, task: Any) -> None:
        """
        Update a task in storage.

        Args:
            task: Task to update
        """

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Any]:
        """
        Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """

    @abstractmethod
    def get_tasks(self) -> List[Any]:
        """
        Get all tasks.

        Returns:
            List of all tasks
        """

    @abstractmethod
    def get_tasks_by_state(self, state: "TaskState") -> List[Any]:
        """
        Get tasks with specified state.

        Args:
            state: Task state to filter by

        Returns:
            List of matching tasks
        """

    @abstractmethod
    def get_pending_tasks(self) -> List[Any]:
        """
        Get tasks that are not yet completed, failed, or canceled.

        Returns:
            List of pending tasks
        """
