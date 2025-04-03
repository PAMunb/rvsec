# rvandroid/experiment/workflow/conductor.py
"""
Workflow conductor for orchestrating workflow execution.

This module provides the WorkflowConductor class, which orchestrates the 
execution of workflows using the component-based architecture. It integrates
with the component registry and injection systems to provide a flexible
workflow execution environment.
"""

import logging
import os
from typing import Dict, List, Optional, Type, Set, Any

from rvandroid.app import App
from rvandroid.experiment.core.interfaces import (
    IExecutionContext, 
    ExecutionPhase,
    IPhaseProcessor
)
from rvandroid.experiment.core.context import ExecutionContext
from rvandroid.experiment.core.workflow import BaseWorkflow
from rvandroid.experiment.event import EventBus, EventType, get_event_bus
from rvandroid.experiment.workflow.components import IComponent, IWorkflowComponent
from rvandroid.experiment.workflow.registry import ComponentRegistry
from rvandroid.experiment.workflow.injection import ComponentInjector
from rvandroid.experiment.workflow.processors import (
    SetupProcessor,
    StaticAnalysisProcessor,
    ExecutionProcessor,
    AnalysisProcessor,
    ReportingProcessor,
    CleanupProcessor
)
from rvandroid.tools.tool_factory import ToolFactory


class WorkflowConductor:
    """
    Conductor for workflow execution using the component-based architecture.
    
    ### Architectural Decisions:
    - Centralizes workflow orchestration in a dedicated conductor
    - Integrates component registry and injection systems
    - Provides high-level workflow execution capabilities
    - Enables flexible workflow composition and execution
    
    ### Role in the System:
    - Orchestrates workflow execution
    - Manages workflow components and their lifecycle
    - Provides centralized workflow configuration
    - Enables consistent workflow execution patterns
    """
    
    def __init__(self, base_results_dir: str, event_bus: Optional[EventBus] = None):
        """
        Initialize the workflow conductor.
        
        Args:
            base_results_dir: Base directory for results
            event_bus: Optional event bus for communication
        """
        self.base_results_dir = base_results_dir
        self.event_bus = event_bus or get_event_bus()
        self.logger = logging.getLogger(__name__)
        
        # Create component registry and injector
        self.registry = ComponentRegistry(IComponent)
        self.injector = ComponentInjector(self.registry)
        
        # Register standard components
        self._register_standard_components()
    
    def create_workflow(self, name: str, experiment_id: Optional[str] = None) -> BaseWorkflow:
        """
        Create a new workflow.
        
        Args:
            name: Name for the workflow
            experiment_id: Optional experiment ID
            
        Returns:
            New workflow instance
        """
        # Create execution context
        context = self._create_context(experiment_id)
        
        # Register context with injector
        self.injector.set_context(context)
        
        # Create workflow
        workflow = BaseWorkflow(name, context)
        
        # Register default processors
        self._register_default_processors(workflow)
        
        return workflow
    
    def execute_workflow(self, workflow: BaseWorkflow, phases: Optional[List[ExecutionPhase]] = None) -> bool:
        """
        Execute a workflow.
        
        Args:
            workflow: Workflow to execute
            phases: Optional list of phases to execute
            
        Returns:
            True if execution was successful, False otherwise
        """
        self.logger.info(f"Executing workflow: {workflow.name}")
        
        # Set workflow in context
        workflow.context.set("workflow.current", workflow)
        
        # Execute workflow
        success = workflow.execute(phases)
        
        # Record completion
        workflow.context.set("workflow.completed", success)
        
        return success
    
    def create_and_execute_workflow(self, 
                                   name: str, 
                                   app: App, 
                                   tool_name: str,
                                   phases: Optional[List[ExecutionPhase]] = None,
                                   config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Create and execute a workflow in one step.
        
        Args:
            name: Name for the workflow
            app: App to test
            tool_name: Name of tool to use
            phases: Optional list of phases to execute
            config: Optional workflow configuration
            
        Returns:
            True if execution was successful, False otherwise
        """
        # Create workflow
        workflow = self.create_workflow(name)
        
        # Set up app and tool
        workflow.context.set("experiment.app", app)
        workflow.context.set("experiment.tool_name", tool_name)
        
        # Create tool
        tool = ToolFactory.create_tool(tool_name)
        workflow.context.set("experiment.tool", tool)
        
        # Apply configuration
        if config:
            workflow.context.set("experiment.config", config)
            
        # Execute workflow
        return self.execute_workflow(workflow, phases)
    
    def register_component(self, component: IComponent) -> str:
        """
        Register a component with the conductor.
        
        Args:
            component: Component to register
            
        Returns:
            ID of the registered component
        """
        return self.registry.register(component)
    
    def register_component_type(self, component_type: Type[IComponent]) -> str:
        """
        Register a component type with the conductor.
        
        Args:
            component_type: Component type to register
            
        Returns:
            ID of the registered component type
        """
        return self.registry.register_type(component_type)
    
    def get_component(self, component_id: str) -> Optional[IComponent]:
        """
        Get a component by ID.
        
        Args:
            component_id: ID of the component to get
            
        Returns:
            Component instance or None if not found
        """
        return self.registry.get(component_id)
    
    def create_component(self, component_type: Type[IComponent], **kwargs) -> IComponent:
        """
        Create a component instance.
        
        Args:
            component_type: Type of component to create
            **kwargs: Additional arguments for component creation
            
        Returns:
            New component instance
        """
        return self.injector.create(component_type, **kwargs)
    
    def discover_components(self, package_name: str) -> int:
        """
        Discover components in a package.
        
        Args:
            package_name: Name of package to scan
            
        Returns:
            Number of components discovered
        """
        return self.registry.discover_components(package_name)
    
    def _create_context(self, experiment_id: Optional[str] = None) -> ExecutionContext:
        """
        Create an execution context.
        
        Args:
            experiment_id: Optional experiment ID
            
        Returns:
            New execution context
        """
        import uuid
        
        # Generate experiment ID if not provided
        if not experiment_id:
            experiment_id = f"experiment_{uuid.uuid4().hex[:8]}"
            
        # Create results directory
        results_dir = os.path.join(self.base_results_dir, experiment_id)
        os.makedirs(results_dir, exist_ok=True)
        
        # Create context
        context = ExecutionContext(experiment_id, results_dir, self.event_bus)
        
        return context
    
    def _register_standard_components(self) -> None:
        """Register standard component types."""
        # Register phase processors
        self.register_component_type(SetupProcessor)
        self.register_component_type(StaticAnalysisProcessor)
        self.register_component_type(ExecutionProcessor)
        self.register_component_type(AnalysisProcessor)
        self.register_component_type(ReportingProcessor)
        self.register_component_type(CleanupProcessor)
        
        self.logger.debug("Registered standard components")
    
    def _register_default_processors(self, workflow: BaseWorkflow) -> None:
        """
        Register default processors with a workflow.
        
        Args:
            workflow: Workflow to register processors with
        """
        # Create each processor
        context = workflow.context
        
        # Create and register processors
        processor_types = [
            SetupProcessor,
            StaticAnalysisProcessor,
            ExecutionProcessor,
            AnalysisProcessor,
            ReportingProcessor,
            CleanupProcessor
        ]
        
        for processor_type in processor_types:
            try:
                processor = self.injector.create(processor_type, context=context, event_bus=self.event_bus)
                workflow.register_processor(processor)
                self.logger.debug(f"Registered processor: {processor.name} with workflow: {workflow.name}")
            except Exception as e:
                self.logger.error(f"Error creating processor {processor_type.__name__}: {e}")