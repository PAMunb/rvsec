"""
Integration components for connecting the new orchestration system with existing experiment workflow.

This module provides adapter classes and integration points that allow the new orchestration
system to work with the existing experiment workflow components.
"""
import os
from typing import List, Optional, Dict, Any

from rvandroid.app import App
from rvandroid.experiment.event import (
    EventBus,
    EventType,
    Event,
    TaskEvent,
    ExperimentEvent,
    create_event_bus
)
from rvandroid.experiment.execution_manager import ExecutionManager
from rvandroid.experiment.orchestration.interfaces import (
    IOrchestrator, 
    OrchestrationMode,
    ExecutionStrategy
)
from rvandroid.experiment.orchestration.tracker import ExecutionTracker
from rvandroid.experiment.orchestration.orchestrator import ExperimentOrchestrator, OrchestrationConfig
from rvandroid.experiment.task.task_storage import TaskStorage
from rvandroid.experiment.workflow.result_manager import ResultManager
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.logging.manager import LoggingManager


class OrchestratorAdapter:
    """
    Adapter that connects the new orchestration system with the existing experiment workflow.
    
    This class provides a bridge between the existing ExecutionController/ExecutionManager
    and the new ExperimentOrchestrator, allowing for a gradual transition to the new system.
    """
    
    def __init__(self, 
                 results_dir: str,
                 event_bus: EventBus,
                 task_storage: TaskStorage,
                 execution_mode: OrchestrationMode = OrchestrationMode.PARALLEL):
        """
        Initialize the orchestrator adapter.
        
        Args:
            results_dir: Directory for experiment results
            event_bus: Event bus for event handling
            task_storage: Storage for task information
            execution_mode: Mode for task execution (sequential, parallel, etc.)
        """
        self.results_dir = results_dir
        self.event_bus = event_bus
        self.task_storage = task_storage
        self.execution_mode = execution_mode
        
        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment_workflow.orchestrator_adapter',
            {
                'component': 'OrchestratorAdapter',
                'execution_mode': execution_mode.name
            }
        )
        
        # Create the new orchestrator
        self.tracker = ExecutionTracker(
            experiment_id=os.path.basename(results_dir),
            results_dir=results_dir
        )
        
        # Create orchestration config
        self.config = OrchestrationConfig(
            mode=execution_mode,
            max_concurrent_tasks=4,  # Configurable
            checkpoint_interval=5,   # In minutes
            recovery_enabled=True
        )
        
        # Create the orchestrator
        self.orchestrator = ExperimentOrchestrator(
            results_dir=results_dir,
            storage=task_storage,
            event_bus=event_bus,
            config=self.config
        )
        
        # Set up event subscription for task status events
        self._setup_event_handlers()
        
        self.logger.info(f"OrchestratorAdapter initialized with mode: {execution_mode.name}")
    
    def _setup_event_handlers(self):
        """Set up event handlers for orchestration events."""
        # Handle task status change events
        def on_task_status_change(event: Event):
            # Process orchestration events related to task status
            if not hasattr(event, 'details'):
                return
                
            task_id = event.details.get('task_id')
            task_status = event.details.get('status')
            task_config = event.details.get('config', {})
            
            if task_status == 'started':
                self.event_bus.publish_task_event(
                    event_type=EventType.TASK_STARTED,
                    task_id=task_id,
                    task_config=task_config,
                    source="OrchestrationSystem",
                    channel=EventBus.LIFECYCLE_CHANNEL
                )
            elif task_status == 'completed':
                self.event_bus.publish_task_event(
                    event_type=EventType.TASK_COMPLETED,
                    task_id=task_id,
                    task_config=task_config,
                    source="OrchestrationSystem",
                    channel=EventBus.LIFECYCLE_CHANNEL
                )
            elif task_status == 'failed':
                error = event.details.get('error', 'Unknown error')
                self.event_bus.publish_task_event(
                    event_type=EventType.TASK_FAILED,
                    task_id=task_id,
                    task_config=task_config,
                    details={'error': error},
                    source="OrchestrationSystem",
                    channel=EventBus.ERROR_CHANNEL
                )
        
        # Subscribe to relevant events
        self.event_bus.subscribe(
            event_type=EventType.CUSTOM,  # Use custom event type for orchestration events
            callback=on_task_status_change,
            channel=EventBus.SYSTEM_CHANNEL
        )
        
    def setup(self, 
              apks: List[App], 
              repetitions: int, 
              timeouts: List[int], 
              tools: List[AbstractTool],
              **kwargs) -> None:
        """
        Set up the orchestrator with experiment parameters.
        
        Args:
            apks: List of applications to test
            repetitions: Number of repetitions for each test
            timeouts: List of timeouts to use
            tools: List of testing tools to use
            **kwargs: Additional parameters for setup
        """
        self.logger.info(f"Setting up orchestrator with {len(apks)} apps, {repetitions} repetitions, "
                        f"{len(timeouts)} timeouts, and {len(tools)} tools")
        
        # Pass setup to the new orchestrator
        self.orchestrator.setup(
            apps=apks,
            repetitions=repetitions,
            timeouts=timeouts,
            tools=tools,
            **kwargs
        )
    
    def run(self) -> bool:
        """
        Run the experiment using the new orchestration system.
        
        Returns:
            True if execution was successful, False otherwise
        """
        self.logger.info("Starting experiment execution with new orchestration system")
        
        # Publish experiment started event
        self.event_bus.publish_experiment_event(
            event_type=EventType.EXPERIMENT_STARTED,
            experiment_id=os.path.basename(self.results_dir),
            message="Starting experiment execution with new orchestration system",
            source="OrchestratorAdapter",
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        
        # Execute the experiment
        result = self.orchestrator.execute()
        
        # Publish experiment completed event
        self.event_bus.publish_experiment_event(
            event_type=EventType.EXPERIMENT_COMPLETED,
            experiment_id=os.path.basename(self.results_dir),
            message="Experiment execution completed with new orchestration system",
            source="OrchestratorAdapter",
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        
        self.logger.info(f"Experiment execution completed with result: {result}")
        return result
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the experiment execution.
        
        Returns:
            Dictionary with execution statistics
        """
        return self.tracker.get_statistics()


