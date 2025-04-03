# rvandroid/experiment/core/conductor.py
"""
Main orchestrator for the unified execution framework.

This module provides the ExperimentConductor class, which is the central
coordination point for experiment execution. It manages workflow creation,
configuration, and execution, and provides a high-level interface for running
experiments.
"""

import os
import uuid
from typing import List, Optional, Dict, Any, Type

from rvandroid.app import App
from rvandroid.experiment.core.interfaces import (
    IWorkflow,
    IExecutionContext,
    IPhaseProcessor,
    ExecutionPhase
)
from rvandroid.experiment.core.context import ExecutionContext
from rvandroid.experiment.core.factory import WorkflowFactory
from rvandroid.experiment.event import (
    EventBus,
    EventType,
    EventHandler,
    get_event_bus
)
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.tools.registry import ToolRegistry
from rvandroid.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE, LOG_ERROR
from rvandroid.util.logging.manager import LoggingManager
from settings import RESULTS_DIR


class ExperimentConductor:
    """
    Central orchestrator for experiment execution.
    
    ### Architectural Decisions:
    - Implements a high-level coordinator for experiment workflows
    - Provides a clean, unified interface for experiment execution
    - Enables flexible workflow composition and execution
    - Supports comprehensive error handling and recovery
    
    ### Role in the System:
    - Serves as the primary entry point for experiment execution
    - Coordinates workflow creation, configuration, and execution
    - Manages experiment context and shared state
    - Provides a consistent interface for various experiment types
    """
    
    def __init__(self, 
                experiment_id: Optional[str] = None,
                results_dir: Optional[str] = None,
                event_bus: Optional[EventBus] = None,
                processor_classes: Optional[List[Type[IPhaseProcessor]]] = None):
        """
        Initialize the experiment conductor.
        
        Args:
            experiment_id: Optional experiment ID (generated if not provided)
            results_dir: Optional results directory (created based on ID if not provided)
            event_bus: Optional event bus for event handling
            processor_classes: Optional list of processor classes to register with workflows
        """
        # Set up experiment identifier
        self.experiment_id = experiment_id or f"experiment_{uuid.uuid4().hex[:8]}"
        
        # Set up event bus
        self.event_bus = event_bus or get_event_bus()
        
        # Set up results directory
        self.base_results_dir = results_dir or RESULTS_DIR
        self.results_dir = os.path.join(self.base_results_dir, self.experiment_id)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Configure logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'experiment.core.conductor',
            {
                'experiment_id': self.experiment_id,
                CONTEXT_COMPONENT: 'ExperimentConductor'
            }
        )
        
        # Set up file logging for this experiment
        self.logging_manager.setup_file_logging(
            log_dir=os.path.join(self.results_dir, "logs"),
            experiment_id=self.experiment_id
        )
        
        # Create execution context
        self.context = ExecutionContext(
            experiment_id=self.experiment_id,
            results_dir=self.results_dir,
            event_bus=self.event_bus
        )
        
        # Create workflow factory
        self.factory = WorkflowFactory(
            base_results_dir=self.base_results_dir,
            event_bus=self.event_bus,
            processor_classes=processor_classes
        )
        
        # Store active workflows
        self.workflows: Dict[str, IWorkflow] = {}
        
        # Register event handlers
        self._setup_event_handlers()
        
        # Tool registry for accessing tools
        self.tool_registry = ToolRegistry.get_instance()
        
        # Log initialization
        self.logger.info(f"Initialized ExperimentConductor for experiment {self.experiment_id}")
        
    def _setup_event_handlers(self):
        """
        Set up event handlers for the conductor.
        
        Registers callback functions for various event types to provide
        comprehensive logging and coordination of workflow execution.
        """
        
        def on_experiment_started(event):
            """Handle experiment start events"""
            with self.logger.with_context(phase="experiment_start"):
                self.logger.info(LOG_START.format(
                    operation=f"Experiment {event.experiment_id}"
                ))
                
        def on_experiment_completed(event):
            """Handle experiment completion events"""
            with self.logger.with_context(phase="experiment_completion"):
                self.logger.info(LOG_COMPLETE.format(
                    operation=f"Experiment {event.experiment_id}"
                ))
                
        def on_workflow_started(event):
            """Handle workflow start events"""
            with self.logger.with_context(
                    workflow_id=event.workflow_id,
                    phase="workflow_start"
            ):
                self.logger.info(LOG_START.format(
                    operation=f"Workflow {event.workflow_id}"
                ))
                
        def on_workflow_completed(event):
            """Handle workflow completion events"""
            with self.logger.with_context(
                    workflow_id=event.workflow_id,
                    phase="workflow_completion"
            ):
                self.logger.info(LOG_COMPLETE.format(
                    operation=f"Workflow {event.workflow_id}"
                ))
                
        def on_workflow_failed(event):
            """Handle workflow failure events"""
            with self.logger.with_context(
                    workflow_id=event.workflow_id,
                    phase="workflow_failure"
            ):
                self.logger.error(LOG_ERROR.format(
                    operation=f"Workflow {event.workflow_id}",
                    error="Workflow execution failed"
                ))
                
        # Register handlers
        self.event_bus.subscribe(
            event_type=EventType.EXPERIMENT_STARTED, 
            callback=on_experiment_started,
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        self.event_bus.subscribe(
            event_type=EventType.EXPERIMENT_COMPLETED, 
            callback=on_experiment_completed,
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        self.event_bus.subscribe(
            event_type=EventType.WORKFLOW_STARTED, 
            callback=on_workflow_started,
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        self.event_bus.subscribe(
            event_type=EventType.WORKFLOW_COMPLETED, 
            callback=on_workflow_completed,
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        self.event_bus.subscribe(
            event_type=EventType.WORKFLOW_FAILED, 
            callback=on_workflow_failed,
            channel=EventBus.ERROR_CHANNEL
        )
        
    def create_workflow(self, name: str) -> IWorkflow:
        """
        Create a new workflow.
        
        Args:
            name: Name for the workflow
            
        Returns:
            New workflow instance
        """
        workflow = self.factory.create_workflow(name, self.context)
        self.workflows[name] = workflow
        return workflow
        
    def get_workflow(self, name: str) -> Optional[IWorkflow]:
        """
        Get a workflow by name.
        
        Args:
            name: Name of the workflow
            
        Returns:
            Workflow if it exists, None otherwise
        """
        return self.workflows.get(name)
        
    def execute_workflow(self, 
                       workflow: IWorkflow, 
                       phases: Optional[List[ExecutionPhase]] = None) -> bool:
        """
        Execute a workflow.
        
        Args:
            workflow: Workflow to execute
            phases: Optional list of phases to execute
            
        Returns:
            True if execution was successful, False otherwise
        """
        return workflow.execute(phases)
        
    def execute_standard_experiment(self,
                                 apks: List[App],
                                 tools: List[AbstractTool],
                                 repetitions: int = 1,
                                 timeouts: List[int] = None,
                                 generate_monitors: bool = True,
                                 instrument: bool = True,
                                 static_analysis: bool = True,
                                 skip_execution: bool = False,
                                 no_window: bool = False) -> bool:
        """
        Execute a standard experiment with the specified parameters.
        
        This method creates and executes a workflow for a standard experiment,
        similar to the original ExperimentController.execute method.
        
        Args:
            apks: List of apps to test
            tools: List of tools to use
            repetitions: Number of repetitions for each task
            timeouts: List of timeout values
            generate_monitors: Whether to generate monitors
            instrument: Whether to instrument APKs
            static_analysis: Whether to perform static analysis
            skip_execution: Whether to skip the execution phase
            no_window: Whether to run without a window
            
        Returns:
            True if the experiment was successful, False otherwise
        """
        if timeouts is None:
            timeouts = [60]
            
        # Store experiment configuration in context
        self.context.set("configuration", {
            "apks": [app.name for app in apks],
            "tools": [tool.name for tool in tools],
            "repetitions": repetitions,
            "timeouts": timeouts,
            "generate_monitors": generate_monitors,
            "instrument": instrument,
            "static_analysis": static_analysis,
            "skip_execution": skip_execution,
            "no_window": no_window
        })
        
        # Register tools and apps
        for app in apks:
            self.context.set(f"app.{app.name}", app)
            
        for tool in tools:
            self.context.set(f"tool.{tool.name}", tool)
            
        # Create standard experiment workflow
        workflow = self.create_workflow("standard_experiment")
        
        # Determine phases to execute
        phases = []
        
        if generate_monitors or instrument or static_analysis:
            phases.extend([ExecutionPhase.SETUP, ExecutionPhase.PREPARATION])
            
        if static_analysis:
            phases.append(ExecutionPhase.STATIC_ANALYSIS)
            
        if not skip_execution:
            phases.append(ExecutionPhase.EXECUTION)
            
        phases.extend([ExecutionPhase.ANALYSIS, ExecutionPhase.REPORTING, ExecutionPhase.CLEANUP])
        
        # Publish experiment started event
        self.event_bus.publish_experiment_event(
            event_type=EventType.EXPERIMENT_STARTED,
            experiment_id=self.experiment_id,
            message="Starting standard experiment execution",
            source="ExperimentConductor",
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        
        with self.logger.with_context(
                repetitions=repetitions,
                timeouts=timeouts,
                tools=[tool.name for tool in tools],
                generate_monitors=generate_monitors,
                instrument=instrument,
                static_analysis=static_analysis,
                skip_execution=skip_execution,
                no_window=no_window,
                phase="execute"
        ):
            self.logger.info(LOG_START.format(operation=f"Experiment {self.experiment_id}"))
            
            # Execute workflow
            success = self.execute_workflow(workflow, phases)
            
            # Publish experiment completed event
            event_type = EventType.EXPERIMENT_COMPLETED if success else EventType.EXPERIMENT_FAILED
            channel = EventBus.LIFECYCLE_CHANNEL if success else EventBus.ERROR_CHANNEL
            self.event_bus.publish_experiment_event(
                event_type=event_type,
                experiment_id=self.experiment_id,
                message=f"Experiment execution {'completed successfully' if success else 'failed'}",
                source="ExperimentConductor",
                channel=channel
            )
            
            # Log completion
            if success:
                self.logger.info(LOG_COMPLETE.format(operation=f"Experiment {self.experiment_id}"))
            else:
                self.logger.error(LOG_ERROR.format(
                    operation=f"Experiment {self.experiment_id}",
                    error="Experiment execution failed"
                ))
                
            return success
            
    def execute_from_config(self, config: Dict[str, Any]) -> bool:
        """
        Execute an experiment using a configuration dictionary.
        
        This method creates and executes a workflow based on the specified configuration.
        It's designed to be compatible with the Configuration singleton used in the original code.
        
        Args:
            config: Dictionary with experiment configuration
            
        Returns:
            True if the experiment was successful, False otherwise
        """
        # Extract configuration
        repetitions = config.get("repetitions", 1)
        timeouts = config.get("timeouts", [60])
        tools_names = config.get("tools", ["monkey"])
        generate_monitors = config.get("generate_monitors", True)
        instrument = config.get("instrument", True)
        static_analysis = config.get("static_analysis", True)
        skip_execution = config.get("skip_experiment", False)
        no_window = config.get("no_window", False)
        
        # Load tools
        tools = []
        for tool_name in tools_names:
            tool = self.tool_registry.get_tool(tool_name)
            if tool:
                tools.append(tool)
            else:
                self.logger.warning(f"Tool not found: {tool_name}")
                
        # Load apps
        if "apks" in config and config["apks"]:
            apks = config["apks"]
        else:
            # Import the PreProcessor to get instrumented APKs
            from rvandroid.experiment.workflow.pre_processor import PreProcessor
            pre_processor = PreProcessor(self.results_dir, self.event_bus)
            apks = pre_processor.get_instrumented_apks()
            
        # Execute experiment
        return self.execute_standard_experiment(
            apks=apks,
            tools=tools,
            repetitions=repetitions,
            timeouts=timeouts,
            generate_monitors=generate_monitors,
            instrument=instrument,
            static_analysis=static_analysis,
            skip_execution=skip_execution,
            no_window=no_window
        )