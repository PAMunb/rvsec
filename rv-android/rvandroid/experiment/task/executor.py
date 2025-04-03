# rvandroid/experiment/task/executor.py
"""
Task executor for RV-Android experiments.

This module provides a comprehensive task executor for running RV-Android
experiments with enhanced component-based architecture, improved error handling,
and support for event-driven communication.
"""

import os
import time
from typing import Optional, Dict, Any, List, Callable

from rvandroid.domain.coverage import LogcatRepository
from rvandroid.experiment.event import (
    EventBus,
    EventType,
    get_event_bus
)
from rvandroid.experiment.task.component import BaseTaskComponent, ComponentRegistry
from rvandroid.experiment.task.interfaces import (
    ITaskExecutor, 
    ITaskComponent, 
    ITask, 
    TaskState
)
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.decorators import log_execution
from rvandroid.util.error import handle_errors
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.exceptions import TaskExecutionError
from rvandroid.util.logging.constants import (
    CONTEXT_TASK_ID,
    CONTEXT_APP_NAME, 
    CONTEXT_TOOL_NAME, 
    CONTEXT_COMPONENT,
    LOG_START, 
    LOG_ERROR, 
    LOG_COMPLETE, 
    LOG_SKIPPED
)
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


@log_execution(logger_prefix="experiment.task_executor", component_name="TaskExecutor")
class TaskExecutor(ITaskExecutor):
    """
    Manages the execution of individual tasks within an experiment workflow
    using a component-based architecture.
    
    ### Architectural Decisions:
    - Implements a component-based approach to task execution
    - Uses dependency injection for component management
    - Supports comprehensive error handling and performance tracking
    - Provides flexible task lifecycle management
    
    ### Role in the System:
    - Coordinates the detailed execution flow of individual experiment tasks
    - Manages emulator interactions, app installation, and tool execution
    - Tracks and collects coverage data during task execution
    - Ensures proper resource management and cleanup
    """

    def __init__(self, 
                task: ITask, 
                tool: AbstractTool, 
                event_bus: Optional[EventBus] = None,
                error_handler: Optional[ErrorHandler] = None):
        """
        Initialize with a task and tool.

        Args:
            task: Task to execute
            tool: Tool implementation to use
            event_bus: Optional event bus for notifications
            error_handler: Optional error handler
        """
        self.task = task
        self.tool = tool
        self.event_bus = event_bus or get_event_bus()
        self.error_handler = error_handler or ErrorHandler.get_instance()

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'experiment.task_executor',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name,
                CONTEXT_TOOL_NAME: tool.name,
                CONTEXT_COMPONENT: "TaskExecutor"
            }
        )

        # Component registry
        self.components = ComponentRegistry()
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor.get_instance()
        
        # Execution hooks
        self.pre_execution_hooks: List[Callable[[ITask], None]] = []
        self.post_execution_hooks: List[Callable[[ITask, bool], None]] = []

    def get_task_context(self) -> Dict[str, Any]:
        """
        Get the standard context for this task execution.
        Used by components and error handlers.

        Returns:
            Dictionary with task context
        """
        return {
            "task_id": self.task.id,
            "apk_name": self.task.config.apk_name,
            "tool_name": self.task.config.tool_name,
            "repetition": self.task.config.repetition,
            "timeout": self.task.config.timeout
        }

    def register_component(self, component: ITaskComponent) -> None:
        """
        Register a component with the executor.
        
        Args:
            component: Component to register
        """
        self.components.register(component)
        self.logger.debug(f"Registered component: {component.name}")

    def get_components(self) -> List[ITaskComponent]:
        """
        Get all registered components.
        
        Returns:
            List of registered components
        """
        return self.components.get_all()

    def set_error_handler(self, handler: ErrorHandler) -> None:
        """
        Set the error handler for the executor.
        
        Args:
            handler: Error handler to use
        """
        self.error_handler = handler

    def add_pre_execution_hook(self, hook: Callable[[ITask], None]) -> None:
        """
        Add a hook to be called before task execution.
        
        Args:
            hook: Function to call with the task
        """
        self.pre_execution_hooks.append(hook)
        self.logger.debug(f"Added pre-execution hook: {hook.__name__}")

    def add_post_execution_hook(self, hook: Callable[[ITask, bool], None]) -> None:
        """
        Add a hook to be called after task execution.
        
        Args:
            hook: Function to call with the task and success flag
        """
        self.post_execution_hooks.append(hook)
        self.logger.debug(f"Added post-execution hook: {hook.__name__}")

    def execute(self) -> bool:
        """
        Execute the task with comprehensive error handling and performance monitoring.

        Returns:
            bool: True if task execution was successful, False otherwise
        """
        self.logger.info(LOG_START.format(operation=f"execution of task {self.task}"))

        if not self.task.app:
            error_msg = "Task has no app instance set"
            self.task.update_state(TaskState.ERROR, error_msg)
            self.logger.error(LOG_ERROR.format(
                operation="task execution",
                error="app instance not set"
            ))
            self._publish_task_failed_event(error_msg)
            return False

        try:
            # Run pre-execution hooks
            for hook in self.pre_execution_hooks:
                hook(self.task)
                
            # Update task state to running
            self.task.update_state(TaskState.RUNNING)
            self._publish_task_started_event()

            # Measure the total execution time
            with self.performance_monitor.measure_time("task_execution_total", self.get_task_context()):
                # Initialize all components
                context = self.get_task_context()
                if not self.components.initialize_all(context):
                    raise TaskExecutionError("Failed to initialize components", self.task.id)
                
                # Execute all components in order
                for component in self.components.get_all():
                    with self.performance_monitor.measure_time(f"component_{component.name.lower()}", context):
                        self.logger.info(f"Executing component: {component.name}")
                        if not component.execute(context):
                            raise TaskExecutionError(f"Component {component.name} execution failed", self.task.id)
                            
                # Clean up all components
                self.components.cleanup_all(context)

            # Mark task as completed
            self.task.update_state(TaskState.COMPLETED)

            # Record metrics about the task
            self.performance_monitor.record_metric(
                name="task_duration",
                value=self.task.result.execution_time_seconds,
                unit="s",
                context=self.get_task_context()
            )

            # Publish completed event
            self._publish_task_completed_event()
            self.logger.info(LOG_COMPLETE.format(
                operation=f"Task {self.task.id}"
            ))
            
            # Run post-execution hooks
            for hook in self.post_execution_hooks:
                hook(self.task, True)
                
            return True

        except Exception as e:
            # Let the error handler process the error
            self.error_handler.handle_error(e, self.get_task_context())

            # Still need to update task status
            error_message = str(e)
            self.logger.error(LOG_ERROR.format(
                operation=f"execution of task {self.task.id}",
                error=error_message
            ))
            self.task.update_state(TaskState.ERROR, error_message)

            # Record error metric
            self.performance_monitor.record_metric(
                name="task_error",
                value=1,
                context={**self.get_task_context(), "error": error_message}
            )

            # Publish failed event
            self._publish_task_failed_event(error_message)

            # Clean up resources
            self._cleanup_resources()
            
            # Run post-execution hooks
            for hook in self.post_execution_hooks:
                hook(self.task, False)

            return False

    def _cleanup_resources(self) -> None:
        """Clean up resources in case of error."""
        context = self.get_task_context()
        with self.logger.with_context(phase="resource_cleanup"):
            try:
                # Clean up all components
                self.components.cleanup_all(context)
            except Exception as e:
                self.logger.warning(LOG_ERROR.format(
                    operation="cleaning up components",
                    error=str(e)
                ))

    # Event publication methods

    def _publish_task_started_event(self) -> None:
        """Publish task started event using the event system."""
        self.event_bus.publish_task_event(
            event_type=EventType.TASK_STARTED,
            task_id=self.task.id,
            task_config={
                "apk_name": self.task.config.apk_name,
                "repetition": self.task.config.repetition,
                "timeout": self.task.config.timeout,
                "tool_name": self.task.config.tool_name
            },
            source="TaskExecutor",
            channel=EventBus.LIFECYCLE_CHANNEL
        )

    def _publish_task_completed_event(self) -> None:
        """Publish task completed event using the event system."""
        self.event_bus.publish_task_event(
            event_type=EventType.TASK_COMPLETED,
            task_id=self.task.id,
            task_config={
                "apk_name": self.task.config.apk_name,
                "repetition": self.task.config.repetition,
                "timeout": self.task.config.timeout,
                "tool_name": self.task.config.tool_name
            },
            source="TaskExecutor",
            channel=EventBus.LIFECYCLE_CHANNEL
        )

    def _publish_task_failed_event(self, error_message: str) -> None:
        """
        Publish task failed event using the event system.
        
        Args:
            error_message: Error message to include in the event
        """
        self.event_bus.publish_task_event(
            event_type=EventType.TASK_FAILED,
            task_id=self.task.id,
            task_config={
                "apk_name": self.task.config.apk_name,
                "repetition": self.task.config.repetition,
                "timeout": self.task.config.timeout,
                "tool_name": self.task.config.tool_name
            },
            details={
                "error": error_message
            },
            source="TaskExecutor",
            channel=EventBus.ERROR_CHANNEL
        )