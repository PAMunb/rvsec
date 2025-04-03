# rvandroid/experiment/core/factory.py
"""
Factory implementation for the unified execution framework.

This module provides the WorkflowFactory class, which creates and configures
workflow instances and their associated components. It ensures consistent
initialization and proper dependency injection.
"""

import os
import uuid
from typing import Optional, Dict, Any, Type, List

from rvandroid.app import App
from rvandroid.experiment.core.interfaces import (
    IWorkflowFactory,
    IExecutionContext,
    IPhaseProcessor,
    ExecutionPhase
)
from rvandroid.experiment.core.workflow import BaseWorkflow
from rvandroid.experiment.core.context import ExecutionContext
from rvandroid.experiment.event import EventBus, get_event_bus
from rvandroid.experiment.task.interfaces import ITask, ITaskExecutor
from rvandroid.experiment.task.executor import TaskExecutor
from rvandroid.experiment.task.models import Task, TaskFactory
from rvandroid.experiment.task.storage import TaskStorage
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.tools.registry import ToolRegistry
from rvandroid.util.logging.manager import LoggingManager


class WorkflowFactory(IWorkflowFactory[BaseWorkflow]):
    """
    Factory for creating and configuring workflow instances.
    
    ### Architectural Decisions:
    - Implements the factory pattern for consistent component creation
    - Centralizes component initialization and configuration
    - Provides dependency injection for workflow components
    - Enables flexible workflow composition and customization
    
    ### Role in the System:
    - Creates workflow instances with proper initialization
    - Configures workflow components with appropriate dependencies
    - Provides centralized management of workflow processors
    - Enables consistent workflow configuration across the system
    """
    
    def __init__(self, 
                base_results_dir: str,
                event_bus: Optional[EventBus] = None,
                processor_classes: Optional[List[Type[IPhaseProcessor]]] = None):
        """
        Initialize the workflow factory.
        
        Args:
            base_results_dir: Base directory for experiment results
            event_bus: Optional event bus for communication
            processor_classes: Optional list of processor classes to register
        """
        self.base_results_dir = base_results_dir
        self.event_bus = event_bus or get_event_bus()
        self.processor_classes = processor_classes or []
        
        # Tool registry for accessing tools
        self.tool_registry = ToolRegistry.get_instance()
        
        # Task factory for creating tasks
        self.task_factory = TaskFactory(Task)
        
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.core.factory',
            {'component': 'WorkflowFactory'}
        )
        
    def create_workflow(self, 
                      name: str, 
                      context: Optional[IExecutionContext] = None) -> BaseWorkflow:
        """
        Create a new workflow instance.
        
        Args:
            name: Name for the workflow
            context: Optional execution context (created if not provided)
            
        Returns:
            New workflow instance
        """
        # Create context if not provided
        if context is None:
            experiment_id = f"experiment_{uuid.uuid4().hex[:8]}"
            results_dir = os.path.join(self.base_results_dir, experiment_id)
            context = ExecutionContext(experiment_id, results_dir, self.event_bus)
            
        # Create workflow
        workflow = BaseWorkflow(name, context)
        
        # Register default processors
        self.register_default_processors(workflow)
        
        self.logger.info(f"Created workflow: {name}")
        return workflow
        
    def create_task_executor(self, task: ITask) -> ITaskExecutor:
        """
        Create a task executor for the specified task.
        
        Args:
            task: Task to create executor for
            
        Returns:
            Task executor instance
        """
        # Get the tool for the task
        tool = self.tool_registry.get_tool(task.config.tool_name)
        
        if tool is None:
            raise ValueError(f"Tool not found: {task.config.tool_name}")
            
        # Create executor
        executor = TaskExecutor(task, tool, self.event_bus)
        
        # Configure executor
        self._configure_executor(executor, task)
        
        return executor
        
    def _configure_executor(self, executor: TaskExecutor, task: ITask) -> None:
        """
        Configure a task executor with appropriate components.
        
        Args:
            executor: Executor to configure
            task: Task being executed
        """
        # Import components here to avoid circular imports
        from rvandroid.experiment.task.components.adapter import create_legacy_component_adapters
        
        # Get the tool for the task
        tool = self.tool_registry.get_tool(task.config.tool_name)
        
        if tool is None:
            raise ValueError(f"Tool not found: {task.config.tool_name}")
            
        # Create and register components
        adapters = create_legacy_component_adapters(task, tool, self.event_bus)
        for adapter in adapters.values():
            executor.register_component(adapter)
            
    def register_default_processors(self, workflow: BaseWorkflow) -> None:
        """
        Register default processors with a workflow.
        
        Args:
            workflow: Workflow to register processors with
        """
        # Create and register processor instances
        for processor_class in self.processor_classes:
            try:
                processor = processor_class(workflow.context, self.event_bus)
                workflow.register_processor(processor)
                self.logger.debug(f"Registered processor: {processor.name}")
            except Exception as e:
                self.logger.error(f"Error creating processor {processor_class.__name__}: {e}")
                
    def create_storage(self, results_dir: str) -> TaskStorage:
        """
        Create a task storage instance.
        
        Args:
            results_dir: Directory for storing task data
            
        Returns:
            TaskStorage instance
        """
        storage_file = os.path.join(results_dir, "tasks.json")
        return TaskStorage(storage_file, self.task_factory)
        
    def create_task(self, app: App, tool_name: str, repetition: int, timeout: int, 
                  no_window: bool = False, clean_logcat: bool = True) -> Task:
        """
        Create a task for the specified app and tool.
        
        Args:
            app: App to test
            tool_name: Name of tool to use
            repetition: Repetition number
            timeout: Timeout in seconds
            no_window: Whether to run without a window
            clean_logcat: Whether to clean logcat before execution
            
        Returns:
            Task instance
        """
        # Get the tool to validate it exists
        tool = self.tool_registry.get_tool(tool_name)
        
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")
            
        # Import task classes here to avoid circular imports
        from rvandroid.experiment.task.models import TaskConfiguration
        
        # Create configuration
        config = TaskConfiguration(
            apk_name=app.name,
            repetition=repetition,
            timeout=timeout,
            tool_name=tool_name,
            no_window=no_window,
            clean_logcat=clean_logcat
        )
        
        # Create task
        task = self.task_factory.create_task(config)
        task.set_app(app)
        
        return task