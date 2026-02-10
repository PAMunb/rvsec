# rvandroid/experiment/core/interfaces.py
"""
Core interfaces for the unified execution framework.

This module defines the foundational interfaces that all execution components
must implement. These interfaces establish a clear separation of concerns and
provide a common contract for components to interact with each other.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, Any, List, TypeVar, Optional, Generic, Callable

from rvandroid.experiment.event import EventBus
from rvandroid.experiment.task.interfaces import ITask, ITaskExecutor


class ExecutionPhase(Enum):
    """
    Enum representing the phases of experiment execution.
    
    ### Architectural Decisions:
    - Uses auto() for value assignment to focus on phase names
    - Provides a consistent vocabulary for workflow stages
    - Enables state-based execution control and tracking
    - Supports clear definition of component responsibilities
    
    ### Role in the System:
    - Defines standard phases of experiment execution
    - Enables components to declare which phases they support
    - Facilitates coordinated, phase-based workflow execution
    - Provides a foundation for flexible workflow composition
    """
    SETUP = auto()             # Initial setup of the experiment
    PREPARATION = auto()       # Preparation of resources and environment
    STATIC_ANALYSIS = auto()   # Static analysis of application code
    EXECUTION = auto()         # Actual execution of experiment tasks
    ANALYSIS = auto()          # Analysis of experiment results
    REPORTING = auto()         # Generation of reports and visualizations
    CLEANUP = auto()           # Cleanup of resources after execution


class IExecutionContext(ABC):
    """
    Interface for experiment execution context.
    
    ### Architectural Decisions:
    - Provides a shared state container for the entire workflow
    - Enables consistent access to experiment configuration and state
    - Supports dynamic attribute registration and discovery
    - Facilitates dependency injection between components
    
    ### Role in the System:
    - Acts as a central repository for experiment state
    - Provides access to configuration parameters and settings
    - Enables communication and data sharing between workflow phases
    - Preserves state across workflow execution phases
    """
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the context.
        
        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            Value associated with the key, or default if not found
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """
        Set a value in the context.
        
        Args:
            key: Key to set
            value: Value to associate with the key
        """
        pass
    
    @abstractmethod
    def has(self, key: str) -> bool:
        """
        Check if a key exists in the context.
        
        Args:
            key: Key to check
            
        Returns:
            True if the key exists, False otherwise
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """
        Delete a key from the context.
        
        Args:
            key: Key to delete
        """
        pass
    
    @abstractmethod
    def get_all(self) -> Dict[str, Any]:
        """
        Get all values from the context.
        
        Returns:
            Dictionary containing all key-value pairs in the context
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear the context."""
        pass
    
    @abstractmethod
    def merge(self, other: Dict[str, Any]) -> None:
        """
        Merge another dictionary into the context.
        
        Args:
            other: Dictionary to merge
        """
        pass
    
    @property
    @abstractmethod
    def experiment_id(self) -> str:
        """
        Get the experiment ID.
        
        Returns:
            Experiment ID
        """
        pass
    
    @property
    @abstractmethod
    def results_dir(self) -> str:
        """
        Get the results directory.
        
        Returns:
            Path to results directory
        """
        pass
    
    @property
    @abstractmethod
    def event_bus(self) -> EventBus:
        """
        Get the event bus.
        
        Returns:
            Event bus instance
        """
        pass


class IPhaseProcessor(ABC):
    """
    Interface for phase-specific processors in the workflow.
    
    ### Architectural Decisions:
    - Defines a clear contract for processors that handle specific phases
    - Supports flexible processor implementation and composition
    - Enables dependency injection and testability
    - Facilitates clear separation of concerns
    
    ### Role in the System:
    - Handles specific phases of experiment workflow
    - Provides a standardized interface for phase processors
    - Enables modular workflow composition
    - Facilitates clear error handling and state management
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the processor name.
        
        Returns:
            Processor name
        """
        pass
    
    @property
    @abstractmethod
    def supported_phases(self) -> List[ExecutionPhase]:
        """
        Get the phases supported by this processor.
        
        Returns:
            List of supported phases
        """
        pass
    
    @abstractmethod
    def process(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Process the specified phase with the given context.
        
        Args:
            phase: Phase to process
            context: Execution context
            
        Returns:
            True if processing was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def can_process(self, phase: ExecutionPhase) -> bool:
        """
        Check if this processor can handle the specified phase.
        
        Args:
            phase: Phase to check
            
        Returns:
            True if this processor can handle the phase
        """
        pass


class IWorkflow(ABC):
    """
    Interface for experiment workflows.
    
    ### Architectural Decisions:
    - Defines a clear contract for workflow implementations
    - Supports flexible workflow composition and execution
    - Enables dependency injection and testability
    - Facilitates comprehensive error handling and recovery
    
    ### Role in the System:
    - Coordinates the execution of experiment phases
    - Manages phase processors and their lifecycle
    - Provides comprehensive workflow monitoring and control
    - Enables flexible workflow configuration and extension
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the workflow name.
        
        Returns:
            Workflow name
        """
        pass
    
    @property
    @abstractmethod
    def context(self) -> IExecutionContext:
        """
        Get the workflow execution context.
        
        Returns:
            Execution context
        """
        pass
    
    @abstractmethod
    def register_processor(self, processor: IPhaseProcessor) -> None:
        """
        Register a phase processor with the workflow.
        
        Args:
            processor: Processor to register
        """
        pass
    
    @abstractmethod
    def get_processors(self) -> List[IPhaseProcessor]:
        """
        Get all registered processors.
        
        Returns:
            List of registered processors
        """
        pass
    
    @abstractmethod
    def get_processors_for_phase(self, phase: ExecutionPhase) -> List[IPhaseProcessor]:
        """
        Get processors that can handle the specified phase.
        
        Args:
            phase: Phase to find processors for
            
        Returns:
            List of processors that can handle the phase
        """
        pass
    
    @abstractmethod
    def execute(self, phases: Optional[List[ExecutionPhase]] = None) -> bool:
        """
        Execute the workflow with the specified phases.
        
        Args:
            phases: Phases to execute (defaults to all phases in order)
            
        Returns:
            True if execution was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def execute_phase(self, phase: ExecutionPhase) -> bool:
        """
        Execute a specific phase of the workflow.
        
        Args:
            phase: Phase to execute
            
        Returns:
            True if execution was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def add_execution_hook(self, phase: ExecutionPhase, hook: Callable[[IExecutionContext], None]) -> None:
        """
        Add a hook to be executed before or after a specific phase.
        
        Args:
            phase: Phase to hook
            hook: Function to execute
        """
        pass


T = TypeVar('T', bound=IWorkflow)

class IWorkflowFactory(Generic[T], ABC):
    """
    Interface for workflow factories.
    
    ### Architectural Decisions:
    - Uses generic typing to support different workflow types
    - Defines a clear contract for workflow creation
    - Enables consistent workflow configuration and initialization
    - Facilitates dependency injection and testability
    
    ### Role in the System:
    - Creates and configures workflow instances
    - Manages workflow dependencies and component registration
    - Provides a centralized point for workflow customization
    - Enables workflow reuse and extension
    """
    
    @abstractmethod
    def create_workflow(self, 
                       name: str, 
                       context: Optional[IExecutionContext] = None) -> T:
        """
        Create a new workflow instance.
        
        Args:
            name: Name for the workflow
            context: Optional execution context (created if not provided)
            
        Returns:
            New workflow instance
        """
        pass
    
    @abstractmethod
    def create_task_executor(self, task: ITask) -> ITaskExecutor:
        """
        Create a task executor for the specified task.
        
        Args:
            task: Task to create executor for
            
        Returns:
            Task executor instance
        """
        pass
    
    @abstractmethod
    def register_default_processors(self, workflow: T) -> None:
        """
        Register default processors with a workflow.
        
        Args:
            workflow: Workflow to register processors with
        """
        pass