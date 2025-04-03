# rvandroid/experiment/processor/execution.py
"""
Execution processor for the unified execution framework.

This module provides the ExecutionProcessor class, which handles the
execution phase of experiment execution, including task creation, execution,
and monitoring.
"""

import os
from typing import List, Optional, Dict, Any

from rvandroid.app import App
from rvandroid.experiment.core.interfaces import (
    IExecutionContext,
    ExecutionPhase
)
from rvandroid.experiment.event import (
    EventBus,
    EventType,
    get_event_bus
)
from rvandroid.experiment.processor.base import BasePhaseProcessor
from rvandroid.experiment.task.interfaces import TaskState
from rvandroid.experiment.task.models import Task, TaskConfiguration, TaskFactory
from rvandroid.experiment.task.storage import TaskStorage
from rvandroid.experiment.task.executor import TaskExecutor
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.tools.registry import ToolRegistry
from rvandroid.util.logging.constants import LOG_START, LOG_COMPLETE, LOG_ERROR
from settings import INSTRUMENTED_DIR


class ExecutionProcessor(BasePhaseProcessor):
    """
    Processor for task execution phase.
    
    ### Architectural Decisions:
    - Implements a focused processor for task execution
    - Provides clean separation of execution concerns
    - Enables flexible task creation and execution strategies
    - Supports comprehensive error handling and recovery
    
    ### Role in the System:
    - Creates and configures tasks based on experiment parameters
    - Manages the execution of individual tasks
    - Tracks task execution progress and results
    - Ensures proper resource management during execution
    """
    
    def __init__(self, context: IExecutionContext, event_bus: Optional[EventBus] = None):
        """
        Initialize the execution processor.
        
        Args:
            context: Execution context
            event_bus: Optional event bus for event publishing
        """
        super().__init__(
            processor_name="ExecutionProcessor",
            supported_phases=[ExecutionPhase.EXECUTION],
            context=context,
            event_bus=event_bus
        )
        
        # Create task factory
        self.task_factory = TaskFactory(Task)
        
        # Initialize tool registry
        self.tool_registry = ToolRegistry.get_instance()
        
        # Task storage
        storage_file = os.path.join(context.results_dir, "tasks.json")
        self.task_storage = TaskStorage(storage_file, self.task_factory)
        
        # Track executed tasks
        self.executed_tasks = []
        self.failed_tasks = []
        
    def _process_phase(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Process the execution phase.
        
        Args:
            phase: Phase to process
            context: Execution context
            
        Returns:
            True if processing was successful, False otherwise
        """
        if phase != ExecutionPhase.EXECUTION:
            self.logger.warning(f"Unsupported phase: {phase.name}")
            return False
            
        return self._execute_tasks(context)
        
    def _execute_tasks(self, context: IExecutionContext) -> bool:
        """
        Execute experiment tasks.
        
        Args:
            context: Execution context
            
        Returns:
            True if execution was successful, False otherwise
        """
        with self.logger.with_context(phase="task_execution"):
            self.logger.info(LOG_START.format(operation="task execution"))
            
            # Get configuration
            config = context.get("configuration", {})
            repetitions = config.get("repetitions", 1)
            timeouts = config.get("timeouts", [60])
            no_window = config.get("no_window", False)
            
            # Get apps and tools
            apps = self._get_apps(context)
            tools = self._get_tools(context)
            
            if not apps:
                self.logger.error("No apps found for execution")
                return False
                
            if not tools:
                self.logger.error("No tools found for execution")
                return False
                
            self.logger.info(f"Executing {len(apps)} apps with {len(tools)} tools, " +
                           f"{repetitions} repetitions, and timeouts {timeouts}")
                           
            # Create tasks if needed
            tasks = self.task_storage.get_tasks()
            
            if not tasks:
                self.logger.info("Creating tasks for execution")
                tasks = self._create_tasks(apps, tools, repetitions, timeouts, no_window)
                
                # Save tasks
                for task in tasks:
                    self.task_storage.add_task(task)
                    
                self.task_storage.save()
                
            # Execute tasks
            pending_tasks = [t for t in tasks if t.can_execute]
            
            self.logger.info(f"Executing {len(pending_tasks)} tasks")
            all_success = True
            
            for task in pending_tasks:
                success = self._execute_task(task)
                
                if success:
                    self.executed_tasks.append(task.id)
                else:
                    self.failed_tasks.append(task.id)
                    all_success = False
                    
                # Update task in storage
                self.task_storage.update_task(task)
                
            # Store execution results in context
            context.set("execution.results", {
                "total_tasks": len(tasks),
                "executed_tasks": len(self.executed_tasks),
                "failed_tasks": len(self.failed_tasks),
                "success_rate": len(self.executed_tasks) / len(tasks) if tasks else 0
            })
            
            if all_success:
                self.logger.info(LOG_COMPLETE.format(operation="task execution"))
            else:
                self.logger.error(LOG_ERROR.format(
                    operation="task execution",
                    error=f"{len(self.failed_tasks)} tasks failed"
                ))
                
            return all_success
            
    def _create_tasks(self, apps: List[App], tools: List[AbstractTool],
                    repetitions: int, timeouts: List[int], no_window: bool) -> List[Task]:
        """
        Create tasks for execution.
        
        Args:
            apps: List of apps to test
            tools: List of tools to use
            repetitions: Number of repetitions
            timeouts: List of timeout values
            no_window: Whether to run without a window
            
        Returns:
            List of created tasks
        """
        tasks = []
        
        for app in apps:
            for rep in range(1, repetitions + 1):
                for timeout in timeouts:
                    for tool in tools:
                        # Create configuration
                        config = TaskConfiguration(
                            apk_name=app.name,
                            repetition=rep,
                            timeout=timeout,
                            tool_name=tool.name,
                            no_window=no_window
                        )
                        
                        # Create task
                        task = self.task_factory.create_task(config)
                        task.set_app(app)
                        
                        # Initialize task
                        task.initialize(self._context.results_dir)
                        
                        tasks.append(task)
                        
        return tasks
        
    def _execute_task(self, task: Task) -> bool:
        """
        Execute a single task.
        
        Args:
            task: Task to execute
            
        Returns:
            True if execution was successful, False otherwise
        """
        with self.logger.with_context(
                task_id=task.id,
                app_name=task.config.apk_name,
                tool_name=task.config.tool_name,
                repetition=task.config.repetition,
                timeout=task.config.timeout
        ):
            self.logger.info(LOG_START.format(operation=f"execution of task {task}"))
            
            # Get tool
            tool = self.tool_registry.get_tool(task.config.tool_name)
            
            if tool is None:
                error_msg = f"Tool not found: {task.config.tool_name}"
                self.logger.error(LOG_ERROR.format(
                    operation="task execution",
                    error=error_msg
                ))
                task.update_state(TaskState.ERROR, error_msg)
                self._publish_task_failed_event(task, error_msg)
                return False
                
            # Copy static analysis files
            self._copy_static_analysis_files(task)
            
            try:
                # Create executor
                executor = TaskExecutor(task, tool, self._event_bus)
                
                # Import components here to avoid circular imports
                from rvandroid.experiment.task.components.adapter import create_legacy_component_adapters
                
                # Create and register components
                adapters = create_legacy_component_adapters(task, tool, self._event_bus)
                for adapter in adapters.values():
                    executor.register_component(adapter)
                    
                # Execute task
                success = executor.execute()
                
                if success:
                    self.logger.info(LOG_COMPLETE.format(operation=f"execution of task {task}"))
                else:
                    self.logger.error(LOG_ERROR.format(
                        operation=f"execution of task {task}",
                        error=task.result.error_message or "Unknown error"
                    ))
                    
                return success
                
            except Exception as e:
                error_msg = str(e)
                self.logger.error(LOG_ERROR.format(
                    operation=f"execution of task {task}",
                    error=error_msg
                ))
                task.update_state(TaskState.ERROR, error_msg)
                self._publish_task_failed_event(task, error_msg)
                return False
                
    def _copy_static_analysis_files(self, task: Task) -> None:
        """
        Copy static analysis files to the task directory.
        
        Args:
            task: Task to copy files for
        """
        # Get app-specific static analysis files
        app_name = task.config.apk_name
        
        # Get static analysis data from context
        static_files = self._context.get(f"static_analysis.{app_name}", {})
        
        if not static_files:
            self.logger.warning(f"No static analysis files found for {app_name}")
            return
            
        # Copy relevant files
        for file_key, file_path in static_files.items():
            if not isinstance(file_path, str) or not file_path:
                continue
                
            if not file_key.endswith("_file"):
                continue
                
            if os.path.exists(file_path):
                import shutil
                dest_path = os.path.join(task.results_dir, os.path.basename(file_path))
                try:
                    shutil.copy(file_path, dest_path)
                    self.logger.debug(f"Copied {file_path} to {dest_path}")
                except Exception as e:
                    self.logger.error(LOG_ERROR.format(
                        operation=f"copying {file_path}",
                        error=str(e)
                    ))
                    
    def _get_apps(self, context: IExecutionContext) -> List[App]:
        """
        Get apps for execution.
        
        Args:
            context: Execution context
            
        Returns:
            List of App objects
        """
        # Get app names from context
        app_names = context.get("instrumented_apks", [])
        
        apps = []
        
        # Get apps from context
        for name in app_names:
            app = context.get(f"app.{name}")
            
            if app is not None:
                apps.append(app)
                
        # If no apps found in context, get from instrumented directory
        if not apps:
            try:
                for file in os.listdir(INSTRUMENTED_DIR):
                    if file.lower().endswith(".apk"):
                        try:
                            app_path = os.path.join(INSTRUMENTED_DIR, file)
                            app = App(app_path)
                            apps.append(app)
                            
                            # Store app in context
                            context.set(f"app.{app.name}", app)
                        except Exception as e:
                            self.logger.error(LOG_ERROR.format(
                                operation=f"processing APK {file}",
                                error=str(e)
                            ))
            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation="listing instrumented APKs",
                    error=str(e)
                ))
                
        return apps
        
    def _get_tools(self, context: IExecutionContext) -> List[AbstractTool]:
        """
        Get tools for execution.
        
        Args:
            context: Execution context
            
        Returns:
            List of Tool objects
        """
        # Get tool names from context
        config = context.get("configuration", {})
        tool_names = config.get("tools", [])
        
        tools = []
        
        # Get tools from registry
        for name in tool_names:
            tool = self.tool_registry.get_tool(name)
            
            if tool is not None:
                tools.append(tool)
                
        return tools
        
    def _publish_task_started_event(self, task: Task) -> None:
        """
        Publish task started event.
        
        Args:
            task: Task that started
        """
        self._event_bus.publish_task_event(
            event_type=EventType.TASK_STARTED,
            task_id=task.id,
            task_config={
                "apk_name": task.config.apk_name,
                "repetition": task.config.repetition,
                "timeout": task.config.timeout,
                "tool_name": task.config.tool_name
            },
            source="ExecutionProcessor",
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        
    def _publish_task_completed_event(self, task: Task) -> None:
        """
        Publish task completed event.
        
        Args:
            task: Task that completed
        """
        self._event_bus.publish_task_event(
            event_type=EventType.TASK_COMPLETED,
            task_id=task.id,
            task_config={
                "apk_name": task.config.apk_name,
                "repetition": task.config.repetition,
                "timeout": task.config.timeout,
                "tool_name": task.config.tool_name
            },
            source="ExecutionProcessor",
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        
    def _publish_task_failed_event(self, task: Task, error_message: str) -> None:
        """
        Publish task failed event.
        
        Args:
            task: Task that failed
            error_message: Error message
        """
        self._event_bus.publish_task_event(
            event_type=EventType.TASK_FAILED,
            task_id=task.id,
            task_config={
                "apk_name": task.config.apk_name,
                "repetition": task.config.repetition,
                "timeout": task.config.timeout,
                "tool_name": task.config.tool_name
            },
            details={
                "error": error_message
            },
            source="ExecutionProcessor",
            channel=EventBus.ERROR_CHANNEL
        )