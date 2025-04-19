# rvandroid/experiment/workflow/example.py
"""
Example usage of the workflow component system.

This module demonstrates how to use the workflow component system to create
and execute workflows with the component-based architecture.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Set

from rvandroid.app import App
from rvandroid.experiment.core.interfaces import ExecutionPhase
from rvandroid.experiment.core.workflow import BaseWorkflow
from rvandroid.experiment.event import EventBusProvider
from rvandroid.experiment.workflow.components import (
    BaseWorkflowComponent,
    IComponent,
    ComponentLifecycle
)
from rvandroid.experiment.workflow.injection import (
    ComponentDecorator,
    autowired
)
from rvandroid.experiment.workflow.conductor import WorkflowConductor


# Example of a custom component using decorators
@ComponentDecorator.component(id="CustomProcessor", name="Custom Processor")
@ComponentDecorator.config("enabled", True)
class CustomProcessor(BaseWorkflowComponent):
    """
    Example custom processor component.
    
    This component demonstrates how to create a custom processor
    using the component decorators and autowiring.
    """
    
    def __init__(self, context=None, event_bus=None):
        super().__init__(
            component_id="CustomProcessor",
            name="Custom Processor",
            description="Example custom processor",
            event_bus=event_bus,
            supported_phases=[ExecutionPhase.EXECUTION]
        )
        self.logger = logging.getLogger(__name__)
        
        if context:
            self.initialize(context)
            self.configure({"enabled": True})
            self.activate()
    
    def execute(self, phase: ExecutionPhase, context: Any) -> bool:
        """Execute the custom processing logic."""
        self.logger.info(f"Custom processor executing for phase: {phase.name}")
        
        # Example custom logic
        context.set("custom_processor.executed", True)
        context.set("custom_processor.timestamp", import_module("datetime").datetime.now().isoformat())
        
        return True


def create_basic_workflow() -> BaseWorkflow:
    """Create a basic workflow with the component system."""
    # Create conductor
    results_dir = os.path.join(os.getcwd(), "results")
    event_bus = EventBusProvider.get_default_bus()
    conductor = WorkflowConductor(results_dir, event_bus)
    
    # Register custom component
    conductor.register_component_type(CustomProcessor)
    
    # Create workflow
    workflow = conductor.create_workflow("ExampleWorkflow")
    
    # Create and register custom processor
    custom_processor = conductor.create_component(CustomProcessor, context=workflow.context)
    workflow.register_processor(custom_processor)
    
    return workflow


def execute_sample_workflow(app_path: str, tool_name: str) -> bool:
    """
    Execute a sample workflow with the given app and tool.
    
    Args:
        app_path: Path to the APK
        tool_name: Name of the tool to use
        
    Returns:
        True if the workflow executed successfully, False otherwise
    """
    # Create app
    app = App(app_path)
    
    # Create conductor
    results_dir = os.path.join(os.getcwd(), "results")
    conductor = WorkflowConductor(results_dir)
    
    # Create and execute workflow
    return conductor.create_and_execute_workflow(
        name="SampleWorkflow",
        app=app,
        tool_name=tool_name,
        phases=[
            ExecutionPhase.SETUP,
            ExecutionPhase.STATIC_ANALYSIS,
            ExecutionPhase.EXECUTION,
            ExecutionPhase.ANALYSIS,
            ExecutionPhase.REPORTING,
            ExecutionPhase.CLEANUP
        ],
        config={
            "timeout": 300,  # 5 minutes
            "no_window": False,
            "clean_logcat": True
        }
    )


# Example of a component with dependencies
@ComponentDecorator.component(id="DependentComponent")
@ComponentDecorator.dependency("CustomProcessor")
class DependentComponent(BaseWorkflowComponent):
    """Example component with dependencies."""
    
    def __init__(self, CustomProcessor=None, **kwargs):
        super().__init__(
            component_id="DependentComponent",
            name="Dependent Component",
            dependencies={"CustomProcessor"},
            **kwargs
        )
        self.custom_processor = CustomProcessor
    
    def execute(self, phase: ExecutionPhase, context: Any) -> bool:
        """Execute using the dependency."""
        if self.custom_processor:
            self.logger.info(f"Using dependency: {self.custom_processor.name}")
            
        return True


def import_module(name):
    """Helper function to import modules dynamically."""
    import importlib
    return importlib.import_module(name)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Example 1: Create a basic workflow
    workflow = create_basic_workflow()
    print(f"Created workflow: {workflow.name}")
    print(f"Registered processors: {[p.name for p in workflow.get_processors()]}")
    
    # Example 2: Execute a sample workflow (commented out as it requires a real APK)
    """
    app_path = "/path/to/your/app.apk"
    tool_name = "rvandroid"
    success = execute_sample_workflow(app_path, tool_name)
    print(f"Workflow execution {'succeeded' if success else 'failed'}")
    """