# rvandroid/experiment/orchestration/orchestrator.py
"""
Main experiment orchestrator using the component-based architecture.

This module provides the experiment orchestrator that coordinates the execution
of tasks and manages the workflow for experiments.
"""

import json
import os
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set, Callable, Type, Union

from rvandroid.app import App
from rvandroid.experiment.event import (
    EventBus,
    EventBusProvider,
    EventType,
    Event,
    TaskEvent,
    ExperimentEvent,
    get_event_bus
)
from rvandroid.experiment.orchestration.interfaces import (
    IOrchestrator,
    OrchestrationMode,
    TaskPriority,
    ExecutionStrategy
)
from rvandroid.experiment.orchestration.tracker import (
    ExecutionTracker,
    ExecutionCheckpoint
)
from rvandroid.experiment.orchestration.execution import (
    SequentialExecutionStrategy,
    ParallelExecutionStrategy,
    AdaptiveExecutionStrategy,
    PriorityBasedExecutionStrategy
)
from rvandroid.experiment.task.interfaces import ITask
from rvandroid.experiment.task.models import TaskConfiguration
from rvandroid.experiment.task.storage import TaskStorage
from rvandroid.experiment.workflow.components import IComponent
from rvandroid.experiment.workflow.registry import ComponentRegistry
from rvandroid.tools.registry import ToolRegistry
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.logging.constants import LOG_START, LOG_COMPLETE, LOG_ERROR
from rvandroid.util.logging.manager import LoggingManager


@dataclass
class OrchestrationConfig:
    """
    Configuration for experiment orchestration.
    
    ### Architectural Decisions:
    - Uses dataclass for clear, type-safe configuration
    - Provides comprehensive orchestration settings
    - Enables flexible execution strategy configuration
    - Supports fine-grained control over orchestration behavior
    
    ### Role in the System:
    - Serves as a container for orchestration settings
    - Enables consistent configuration across orchestration components
    - Facilitates configuration-based execution strategy adaptation
    - Provides a unified interface for orchestration configuration
    """
    mode: OrchestrationMode = OrchestrationMode.SEQUENTIAL
    max_workers: int = 4
    max_retries: int = 3
    retry_delay: int = 5  # seconds
    timeout_factor: float = 1.1  # multiply task timeout by this factor for orchestration
    fail_fast: bool = False  # stop on first error
    ignore_failures: bool = False  # continue even if tasks fail
    prioritize_by: Optional[Callable[[ITask], TaskPriority]] = None
    resource_threshold: float = 0.8  # CPU/memory threshold for adaptive mode
    checkpoint_interval: int = 60  # seconds between checkpoints
    auto_recovery: bool = True  # automatically recover from checkpoints
    preserve_order: bool = False  # maintain task order in results
    task_labels: Dict[str, str] = field(default_factory=dict)  # custom task labels


class ExperimentOrchestrator(IOrchestrator):
    """
    Advanced orchestrator for coordinating complex experiment workflows.
    
    ### Architectural Decisions:
    - Implements a comprehensive orchestration system with flexible execution strategies
    - Integrates with the component-based architecture using dependency injection
    - Provides event-driven control flow and robust error handling
    - Enables fine-grained control over experiment execution
    
    ### Role in the System:
    - Serves as the central coordinator for experiment execution
    - Manages task scheduling, execution, and monitoring
    - Provides advanced flow control and error recovery
    - Enables efficient resource utilization and experiment scaling
    
    ### Key Capabilities:
    - Multiple execution strategies (sequential, parallel, adaptive, priority-based)
    - Event-driven workflow orchestration
    - Checkpointing and automatic recovery
    - Comprehensive metrics and progress tracking
    - Dynamic concurrency control
    - Robust error handling and recovery
    """
    
    def __init__(self, 
                results_dir: str, 
                storage: Optional[TaskStorage] = None,
                event_bus: Optional[EventBus] = None,
                config: Optional[OrchestrationConfig] = None):
        """
        Initialize the experiment orchestrator.
        
        Args:
            results_dir: Base directory for results
            storage: Optional task storage
            event_bus: Optional event bus for communication
            config: Optional orchestration configuration
        """
        # Generate experiment ID
        self.experiment_id = f"experiment_{uuid.uuid4().hex[:8]}"
        self.results_dir = os.path.join(results_dir, self.experiment_id)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Set up components with dependency injection
        self.event_bus = event_bus or get_event_bus()
        self.storage = storage
        if not self.storage:
            storage_file = os.path.join(self.results_dir, "tasks.json")
            self.storage = TaskStorage(storage_file)
            
        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment.orchestration.orchestrator',
            {
                'experiment_id': self.experiment_id,
                'component': 'ExperimentOrchestrator'
            }
        )
        
        # Set up file logging for this experiment
        log_dir = os.path.join(self.results_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        self.logging_manager.setup_file_logging(
            log_dir=log_dir,
            experiment_id=self.experiment_id
        )
        
        # Set configuration
        self.config = config or OrchestrationConfig()
        
        # Set up execution components
        self.tracker = ExecutionTracker(self.experiment_id, self.results_dir)
        self.registry = ComponentRegistry(IComponent)
        self.tool_registry = ToolRegistry.get_instance()
        
        # Task management
        self.registered_apps: Dict[str, App] = {}
        self.task_priorities: Dict[str, TaskPriority] = {}
        self.task_factory = self.storage.task_factory
        
        # Execution management
        self._create_execution_strategy()
        self.is_running = False
        
        self.logger.info(f"Initialized ExperimentOrchestrator with ID: {self.experiment_id}")
    
    def _create_execution_strategy(self) -> None:
        """Create the execution strategy based on configuration."""
        # Create strategy based on mode
        if self.config.mode == OrchestrationMode.SEQUENTIAL:
            self.execution_strategy = SequentialExecutionStrategy(
                self.event_bus,
                self.tracker,
                self.tool_registry,
                self.registered_apps
            )
            self.logger.info("Using sequential execution strategy")
            
        elif self.config.mode == OrchestrationMode.PARALLEL:
            self.execution_strategy = ParallelExecutionStrategy(
                self.event_bus,
                self.tracker,
                self.tool_registry,
                self.registered_apps,
                max_workers=self.config.max_workers
            )
            self.logger.info(f"Using parallel execution strategy with {self.config.max_workers} workers")
            
        elif self.config.mode == OrchestrationMode.ADAPTIVE:
            self.execution_strategy = AdaptiveExecutionStrategy(
                self.event_bus,
                self.tracker,
                self.tool_registry,
                self.registered_apps,
                initial_workers=1,
                max_workers=self.config.max_workers,
                resource_threshold=self.config.resource_threshold
            )
            self.logger.info(
                f"Using adaptive execution strategy with up to {self.config.max_workers} workers "
                f"(threshold: {self.config.resource_threshold * 100}%)"
            )
            
        elif self.config.mode == OrchestrationMode.PRIORITY_BASED:
            strategy = PriorityBasedExecutionStrategy(
                self.event_bus,
                self.tracker,
                self.tool_registry,
                self.registered_apps,
                max_workers=self.config.max_workers
            )
            
            # Set task priorities if available
            for task_id, priority in self.task_priorities.items():
                strategy.set_task_priority(task_id, priority)
                
            self.execution_strategy = strategy
            self.logger.info(f"Using priority-based execution strategy with {self.config.max_workers} workers")
            
        else:
            # Default to sequential
            self.execution_strategy = SequentialExecutionStrategy(
                self.event_bus,
                self.tracker,
                self.tool_registry,
                self.registered_apps
            )
            self.logger.warning(f"Unknown mode {self.config.mode}, defaulting to sequential execution")
    
    def register_app(self, app: App) -> None:
        """
        Register an app with the orchestrator.
        
        Args:
            app: App to register
        """
        self.registered_apps[app.name] = app
        self.logger.debug(f"Registered app: {app.name}")
    
    def set_task_priority(self, task_id: str, priority: TaskPriority) -> None:
        """
        Set priority for a specific task.
        
        Args:
            task_id: ID of the task
            priority: Priority level
        """
        self.task_priorities[task_id] = priority
        
        # Update strategy if it's priority-based
        if isinstance(self.execution_strategy, PriorityBasedExecutionStrategy):
            self.execution_strategy.set_task_priority(task_id, priority)
    
    def setup(self, 
             apps: List[App],
             repetitions: int,
             timeouts: List[int],
             tools: List[AbstractTool],
             **kwargs) -> None:
        """
        Set up tasks for experiment execution.
        
        Args:
            apps: List of apps to test
            repetitions: Number of repetitions
            timeouts: List of timeouts
            tools: List of tools to use
            **kwargs: Additional task configuration parameters
        """
        created_count = 0
        
        # Register apps and tools
        for app in apps:
            self.register_app(app)
            
        for tool in tools:
            self.tool_registry.register_tool(tool)
            
        # Create tasks
        for app in apps:
            for rep in range(1, repetitions + 1):
                for timeout in timeouts:
                    for tool in tools:
                        # Create task configuration
                        config = TaskConfiguration(
                            apk_name=app.name,
                            repetition=rep,
                            timeout=timeout,
                            tool_name=tool.name,
                            **kwargs
                        )
                        
                        # Create task
                        task = self.task_factory.create_task(config)
                        task.initialize(self.results_dir)
                        task.set_app(app)
                        
                        # Add to storage
                        self.storage.add_task(task)
                        created_count += 1
                        
                        # Add to tracker
                        self.tracker.add_pending_task(task.id)
                        
                        # Set default priority
                        if self.config.prioritize_by:
                            priority = self.config.prioritize_by(task)
                        else:
                            priority = TaskPriority.NORMAL
                            
                        self.set_task_priority(task.id, priority)
        
        # Save to storage
        self.storage.save()
        self.logger.info(f"Created {created_count} tasks for experiment")
    
    def execute(self) -> bool:
        """
        Execute the experiment with the configured orchestration strategy.
        
        Returns:
            True if execution was successful, False otherwise
        """
        if self.is_running:
            self.logger.warning("Execution already in progress")
            return False
            
        self.is_running = True
        has_errors = False
        
        # Publish experiment started event
        self.event_bus.publish_experiment_event(
            event_type=EventType.EXPERIMENT_STARTED,
            experiment_id=self.experiment_id,
            source="ExperimentOrchestrator",
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        
        self.logger.info(LOG_START.format(operation=f"Experiment {self.experiment_id}"))
        
        try:
            # Get tasks to execute
            tasks = self.storage.get_pending_tasks()
            
            if not tasks:
                self.logger.warning("No pending tasks to execute")
                return True
                
            # Execute tasks with strategy
            execution_params = {
                'max_workers': self.config.max_workers,
                'prioritize_by': self.config.prioritize_by,
                'resource_threshold': self.config.resource_threshold
            }
            
            # Execute tasks
            self.execution_strategy.execute(tasks, **execution_params)
            
            # Check for errors
            statistics = self.tracker.get_statistics()
            failed = statistics.get('tasks_failed', 0)
            has_errors = failed > 0 and not self.config.ignore_failures
            
            # Publish experiment completion event
            if has_errors:
                self.event_bus.publish_experiment_event(
                    event_type=EventType.EXPERIMENT_FAILED,
                    experiment_id=self.experiment_id,
                    details={"statistics": statistics},
                    source="ExperimentOrchestrator",
                    channel=EventBus.ERROR_CHANNEL
                )
                self.logger.error(LOG_ERROR.format(
                    operation=f"Experiment {self.experiment_id}",
                    error=f"Failed with {failed} task failures"
                ))
            else:
                self.event_bus.publish_experiment_event(
                    event_type=EventType.EXPERIMENT_COMPLETED,
                    experiment_id=self.experiment_id,
                    details={"statistics": statistics},
                    source="ExperimentOrchestrator",
                    channel=EventBus.LIFECYCLE_CHANNEL
                )
                self.logger.info(LOG_COMPLETE.format(operation=f"Experiment {self.experiment_id}"))
                
            # Record experiment completion
            self.tracker.record_experiment_end()
            
            return not has_errors
            
        except Exception as e:
            self.logger.error(LOG_ERROR.format(
                operation=f"Experiment {self.experiment_id}",
                error=str(e)
            ))
            
            # Publish experiment failed event
            self.event_bus.publish_experiment_event(
                event_type=EventType.EXPERIMENT_FAILED,
                experiment_id=self.experiment_id,
                details={"error": str(e)},
                source="ExperimentOrchestrator",
                channel=EventBus.ERROR_CHANNEL
            )
            
            return False
            
        finally:
            self.is_running = False
    
    def cancel(self) -> None:
        """Cancel the experiment execution."""
        if not self.is_running:
            self.logger.warning("No execution in progress to cancel")
            return
            
        self.logger.info("Cancelling experiment execution")
        self.execution_strategy.cancel()
        
        # Publish cancellation event
        self.event_bus.publish(
            Event(
                type=EventType.CUSTOM,
                name="EXECUTION_CANCELLED",
                details={"experiment_id": self.experiment_id},
                source="ExperimentOrchestrator"
            ),
            channel=EventBus.SYSTEM_CHANNEL
        )
    
    def pause(self) -> None:
        """Pause the experiment execution."""
        if not self.is_running:
            self.logger.warning("No execution in progress to pause")
            return
            
        self.logger.info("Pausing experiment execution")
        self.execution_strategy.pause()
        
        # Publish pause event
        self.event_bus.publish(
            Event(
                type=EventType.CUSTOM,
                name="EXECUTION_PAUSED",
                details={"experiment_id": self.experiment_id},
                source="ExperimentOrchestrator"
            ),
            channel=EventBus.SYSTEM_CHANNEL
        )
    
    def resume(self) -> None:
        """Resume the experiment execution."""
        self.logger.info("Resuming experiment execution")
        self.execution_strategy.resume()
        
        # Publish resume event
        self.event_bus.publish(
            Event(
                type=EventType.CUSTOM,
                name="EXECUTION_RESUMED",
                details={"experiment_id": self.experiment_id},
                source="ExperimentOrchestrator"
            ),
            channel=EventBus.SYSTEM_CHANNEL
        )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current experiment status.
        
        Returns:
            Status dictionary with execution metrics
        """
        # Get status from execution strategy
        if hasattr(self, 'execution_strategy'):
            return self.execution_strategy.get_status()
            
        # Return basic status if no strategy
        return {
            'running': self.is_running,
            'experiment_id': self.experiment_id,
            'results_dir': self.results_dir
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get detailed experiment statistics.
        
        Returns:
            Statistics dictionary
        """
        if hasattr(self, 'tracker'):
            stats = self.tracker.get_statistics()
            
            # Add experiment info
            stats.update({
                'experiment_id': self.experiment_id,
                'results_dir': self.results_dir,
                'mode': self.config.mode.name if hasattr(self.config, 'mode') else 'UNKNOWN'
            })
            
            # Process task breakdown (tools and apps)
            self._process_task_breakdown(stats)
            
            return stats
            
        return {
            'experiment_id': self.experiment_id,
            'results_dir': self.results_dir
        }
    
    def _process_task_breakdown(self, stats: Dict[str, Any]) -> None:
        """
        Process task breakdown by tool and app.
        
        Args:
            stats: Statistics dictionary to update
        """
        # Get all tasks
        tasks = self.storage.get_tasks()
        
        # Create breakdown structures
        tools: Dict[str, Dict[str, int]] = {}
        apps: Dict[str, Dict[str, int]] = {}
        
        # Process each task
        for task in tasks:
            # Process by tool
            tool_name = task.config.tool_name
            if tool_name not in tools:
                tools[tool_name] = {"total": 0, "completed": 0, "failed": 0}
                
            tools[tool_name]["total"] += 1
            
            if task.result.is_executed():
                tools[tool_name]["completed"] += 1
                
            if task.result.has_error():
                tools[tool_name]["failed"] += 1
                
            # Process by app
            app_name = task.config.apk_name
            if app_name not in apps:
                apps[app_name] = {"total": 0, "completed": 0, "failed": 0}
                
            apps[app_name]["total"] += 1
            
            if task.result.is_executed():
                apps[app_name]["completed"] += 1
                
            if task.result.has_error():
                apps[app_name]["failed"] += 1
                
        # Update tracker
        self.tracker.set_task_breakdown(tools, apps)
        
        # Update stats
        stats["tools"] = tools
        stats["apps"] = apps
    
    def create_checkpoint(self) -> Dict[str, Any]:
        """
        Create a checkpoint of the current experiment state.
        
        Returns:
            Checkpoint data
        """
        return self.tracker.create_checkpoint()
    
    def restore_from_checkpoint(self, checkpoint: Dict[str, Any]) -> None:
        """
        Restore experiment state from a checkpoint.
        
        Args:
            checkpoint: Checkpoint data
        """
        self.tracker.restore_from_checkpoint(checkpoint)
        
        # Recreate execution strategy to update with new state
        self._create_execution_strategy()
    
    def resume_from_checkpoint_file(self, checkpoint_file: str) -> bool:
        """
        Resume experiment from a checkpoint file.
        
        Args:
            checkpoint_file: Path to checkpoint file
            
        Returns:
            True if resumption was successful, False otherwise
        """
        try:
            # Load checkpoint
            checkpoint = ExecutionCheckpoint.load_from_file(checkpoint_file)
            
            # Restore state
            self.restore_from_checkpoint(checkpoint.to_dict())
            
            self.logger.info(f"Resumed experiment from checkpoint: {checkpoint_file}")
            return True
            
        except Exception as e:
            self.logger.error(LOG_ERROR.format(
                operation=f"resuming from checkpoint",
                error=str(e)
            ))
            
            return False