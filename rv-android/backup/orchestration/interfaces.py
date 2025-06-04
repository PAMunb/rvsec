# rvandroid/experiment/orchestration/interfaces.py
"""
Interfaces for the experiment orchestration system.

This module defines the core interfaces for the orchestration system, including
execution strategies, orchestration modes, and the main orchestrator interface.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Set, Callable, TypeVar, Generic, Union

from rvandroid.app import App
from rvandroid.experiment.task.interfaces import ITask, ITaskResult
from rvandroid.tools.tool_spec import AbstractTool


class OrchestrationMode(Enum):
    """
    Orchestration execution modes.
    
    ### Architectural Decisions:
    - Defines clear, distinct modes for orchestration execution
    - Enables flexibility in execution strategies
    - Supports both sequential and parallel execution patterns
    - Facilitates consistent configuration and behavior across the system
    
    ### Role in the System:
    - Provides a standard vocabulary for orchestration modes
    - Enables configuration-based execution strategy selection
    - Supports different performance and reliability trade-offs
    - Facilitates consistent execution behavior
    """
    SEQUENTIAL = auto()          # Execute tasks one at a time
    PARALLEL = auto()            # Execute tasks in parallel with max concurrency
    ADAPTIVE = auto()            # Adapt concurrency based on system resources
    PRIORITY_BASED = auto()      # Execute tasks based on priority


class TaskPriority(Enum):
    """
    Task priority levels for orchestration.
    
    ### Architectural Decisions:
    - Defines standard priority levels for task scheduling
    - Enables priority-based task execution
    - Supports fine-grained control over task scheduling
    - Facilitates consistent task prioritization across the system
    
    ### Role in the System:
    - Provides a standard vocabulary for task priorities
    - Enables priority-based execution strategies
    - Supports scheduling optimization for critical tasks
    - Facilitates consistent task scheduling behavior
    """
    CRITICAL = 0      # Must execute immediately
    HIGH = 1          # Execute with high priority
    NORMAL = 2        # Default priority
    LOW = 3           # Execute when resources are available
    BACKGROUND = 4    # Execute only when system is idle


T = TypeVar('T', bound=ITask)
R = TypeVar('R', bound=ITaskResult)


class ExecutionStrategy(Generic[T], ABC):
    """
    Interface for task execution strategies.
    
    ### Architectural Decisions:
    - Defines a clear, strategy pattern interface for execution strategies
    - Enables modular, interchangeable execution approaches
    - Facilitates extension with new execution strategies
    - Supports parameterized strategy configuration
    
    ### Role in the System:
    - Provides the execution logic for different orchestration modes
    - Encapsulates the details of task scheduling and execution
    - Enables customization of execution behavior
    - Facilitates isolation of execution concerns from orchestration
    """
    
    @abstractmethod
    def execute(self, tasks: List[T], **kwargs) -> Dict[str, Any]:
        """
        Execute a set of tasks according to the strategy.
        
        Args:
            tasks: List of tasks to execute
            **kwargs: Additional execution parameters
            
        Returns:
            Execution statistics and results
        """
        pass
    
    @abstractmethod
    def cancel(self) -> None:
        """Cancel ongoing execution."""
        pass
    
    @abstractmethod
    def pause(self) -> None:
        """Pause ongoing execution."""
        pass
    
    @abstractmethod
    def resume(self) -> None:
        """Resume paused execution."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current execution status.
        
        Returns:
            Status dictionary with execution metrics
        """
        pass


class IExecutionTracker(ABC):
    """
    Interface for tracking experiment execution.
    
    ### Architectural Decisions:
    - Separates execution tracking concerns from orchestration logic
    - Enables consistent tracking across different execution strategies
    - Provides a clear contract for execution tracking
    - Facilitates modular tracking implementations
    
    ### Role in the System:
    - Tracks execution progress and metrics
    - Provides checkpoint and recovery capabilities
    - Enables detailed progress and performance monitoring
    - Facilitates experiment status reporting
    """
    
    @abstractmethod
    def track_task_start(self, task_id: str) -> None:
        """
        Track the start of a task.
        
        Args:
            task_id: ID of the started task
        """
        pass
    
    @abstractmethod
    def track_task_completion(self, task_id: str, success: bool, execution_time: float) -> None:
        """
        Track the completion of a task.
        
        Args:
            task_id: ID of the completed task
            success: Whether the task completed successfully
            execution_time: Task execution time in seconds
        """
        pass
    
    @abstractmethod
    def create_checkpoint(self) -> Dict[str, Any]:
        """
        Create a checkpoint of the current execution state.
        
        Returns:
            Checkpoint data
        """
        pass
    
    @abstractmethod
    def restore_from_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """
        Restore execution state from a checkpoint.
        
        Args:
            checkpoint: Checkpoint data
        """
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current execution statistics.
        
        Returns:
            Statistics dictionary
        """
        pass
    
    @abstractmethod
    def get_progress(self) -> float:
        """
        Get execution progress as a percentage.
        
        Returns:
            Progress percentage (0-100)
        """
        pass


class IOrchestrator(ABC):
    """
    Interface for experiment orchestration.
    
    ### Architectural Decisions:
    - Defines a comprehensive interface for experiment orchestration
    - Enables consistent orchestration behavior across implementations
    - Supports flexible configuration and execution strategies
    - Facilitates extension with new orchestration capabilities
    
    ### Role in the System:
    - Coordinates the execution of experiment tasks
    - Manages task scheduling, execution, and monitoring
    - Provides error recovery and checkpoint capabilities
    - Enables detailed progress and performance tracking
    """
    
    @abstractmethod
    def setup(self, 
             apps: List[App],
             repetitions: int,
             timeouts: List[int],
             tools: List[AbstractTool],
             **kwargs) -> None:
        """
        Set up tasks for execution.
        
        Args:
            apps: List of apps to test
            repetitions: Number of repetitions
            timeouts: List of timeouts
            tools: List of tools to use
            **kwargs: Additional task configuration parameters
        """
        pass
    
    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the experiment with the configured orchestration strategy.
        
        Returns:
            True if execution was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def cancel(self) -> None:
        """Cancel the experiment execution."""
        pass
    
    @abstractmethod
    def pause(self) -> None:
        """Pause the experiment execution."""
        pass
    
    @abstractmethod
    def resume(self) -> None:
        """Resume the experiment execution."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current experiment status.
        
        Returns:
            Status dictionary with execution metrics
        """
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get detailed experiment statistics.
        
        Returns:
            Statistics dictionary
        """
        pass
    
    @abstractmethod
    def create_checkpoint(self) -> Dict[str, Any]:
        """
        Create a checkpoint of the current experiment state.
        
        Returns:
            Checkpoint data
        """
        pass
    
    @abstractmethod
    def restore_from_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """
        Restore experiment state from a checkpoint.
        
        Args:
            checkpoint: Checkpoint data
        """
        pass