# rv_platform/execution/executor.py
"""
Task executor for RV-Platform.

This module provides a comprehensive task executor for running platform tasks
with enhanced component-based architecture, improved error handling,
and support for event-driven communication.
"""

from typing import Optional, Dict, Any, List, Callable

from rv_android_core.util.decorators import log_execution
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import TaskExecutionError
from rv_android_core.util.logging.constants import (
    CONTEXT_TASK_ID,
    CONTEXT_APP_NAME,
    CONTEXT_TOOL_NAME,
    CONTEXT_COMPONENT,
    LOG_START,
    LOG_ERROR,
    LOG_COMPLETE
)
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.event.bus import EventBus
from rv_android_core.event.models import EventType, EventChannel
from rv_android_core.domain.task import Task, TaskState
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_platform.storage.task_storage import TaskStorage


@log_execution(logger_prefix="platform.task_executor", component_name="TaskExecutor")
class TaskExecutor:
    """
    Manages the execution of individual tasks within a platform workflow
    using a component-based architecture.
    
    ### Architectural Decisions:
    - Implements a component-based approach to task execution
    - Uses dependency injection for component management
    - Supports comprehensive error handling and performance tracking
    - Provides flexible task lifecycle management
    
    ### Role in the System:
    - Coordinates the detailed execution flow of individual platform tasks
    - Manages emulator interactions, app installation, and tool execution
    - Tracks and collects coverage data during task execution
    - Ensures proper resource management and cleanup
    """

    def __init__(self,
                 task: Task,
                 tool: AbstractTool,
                 event_bus: Optional[EventBus] = None,
                 task_storage: Optional[TaskStorage] = None,
                 error_handler: Optional[ErrorHandler] = None):
        """
        Initialize with a task and tool.

        Args:
            task: Task to execute
            tool: Tool implementation to use
            event_bus: Optional event bus for notifications
            task_storage: Optional task storage for persistence
            error_handler: Optional error handler
        """
        self.task = task
        self.tool = tool
        self.event_bus = event_bus or EventBus.get_instance()
        self.task_storage = task_storage
        self.error_handler = error_handler or ErrorHandler.get_instance()

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'platform.task_executor',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name,
                CONTEXT_TOOL_NAME: tool.name,
                CONTEXT_COMPONENT: "TaskExecutor"
            }
        )

        # Component registry for coordinated task execution
        # Components are initialized and executed in specific order for proper lifecycle
        self.components: List[Any] = []

        # Execution hooks for extension points
        # Allow task customization and monitoring integration
        self.pre_execution_hooks: List[Callable[[Task], None]] = []
        self.post_execution_hooks: List[Callable[[Task, bool], None]] = []

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
            "tool_name": self.task.config.tool_config.get_full_tool_name(),
            "repetition": self.task.config.repetition,
            "timeout": self.task.config.timeout
        }

    def register_component(self, component: Any) -> None:
        """
        Register a component with the executor.
        
        Args:
            component: Component to register
        """
        self.components.append(component)
        self.logger.debug(f"Registered component: {getattr(component, 'name', type(component).__name__)}")

    def get_components(self) -> List[Any]:
        """
        Get all registered components.
        
        Returns:
            List of registered components
        """
        return self.components

    def set_error_handler(self, handler: ErrorHandler) -> None:
        """
        Set the error handler for the executor.
        
        Args:
            handler: Error handler to use
        """
        self.error_handler = handler

    def add_pre_execution_hook(self, hook: Callable[[Task], None]) -> None:
        """
        Add a hook to be called before task execution.
        
        Args:
            hook: Function to call with the task
        """
        self.pre_execution_hooks.append(hook)
        self.logger.debug(f"Added pre-execution hook: {hook.__name__}")

    def add_post_execution_hook(self, hook: Callable[[Task, bool], None]) -> None:
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
        self.logger.info(LOG_START.format(phase=f"execution of task {self.task}"))

        # Validate task has required app instance for execution
        # App instance contains APK path, package info, and static analysis data
        if not self.task.app:
            error_msg = "Task has no app instance set"
            self.task.update_state(TaskState.ERROR, error_msg)
            self.logger.error(LOG_ERROR.format(
                phase="task execution",
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

            # Initialize all components
            context = self.get_task_context()
            self._initialize_components(context)

            # Execute components in specialized order with proper coordination
            self._execute_coordinated_components(context)

            # Clean up all components
            self._cleanup_components(context)

            # Mark task as completed
            self.task.update_state(TaskState.COMPLETED)

            # Publish completed event
            self._publish_task_completed_event()
            self.logger.info(LOG_COMPLETE.format(
                phase=f"Task {self.task.id}"
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
                phase=f"execution of task {self.task.id}",
                error=error_message
            ))
            self.task.update_state(TaskState.ERROR, error_message)

            # Publish failed event
            self._publish_task_failed_event(error_message)

            # Clean up resources
            self._cleanup_resources()

            # Run post-execution hooks
            for hook in self.post_execution_hooks:
                hook(self.task, False)

            return False

    def _initialize_components(self, context: Dict[str, Any]) -> None:
        """
        Initialize all registered components.
        
        Args:
            context: Task execution context
        """
        for component in self.components:
            if hasattr(component, 'initialize'):
                self.logger.debug(f"Initializing component: {getattr(component, 'name', type(component).__name__)}")
                component.initialize(context)

    def _execute_coordinated_components(self, context: Dict[str, Any]) -> None:
        """
        Execute components in a coordinated manner, managing emulator lifecycle properly.
        
        Args:
            context: Task execution context
        """
        # Get components by type
        static_component = None
        coverage_component = None
        emulator_component = None
        logcat_component = None
        tool_component = None

        for component in self.components:
            if "StaticAnalysis" in component.name:
                static_component = component
            elif "Coverage" in component.name:
                coverage_component = component
            elif "Emulator" in component.name:
                emulator_component = component
            elif "Logcat" in component.name:
                logcat_component = component
            elif "ToolExecution" in component.name:
                tool_component = component

        # Phase 1: Load static data (outside emulator)
        if static_component:
            self.logger.info(f"Executing component: {static_component.name}")
            if not static_component.execute(context):
                raise TaskExecutionError(f"Component {static_component.name} execution failed", self.task.id)

        # Phase 2: Initialize coverage tracking (outside emulator)
        if coverage_component:
            self.logger.info(f"Executing component: {coverage_component.name}")
            if not coverage_component.execute(context):
                raise TaskExecutionError(f"Component {coverage_component.name} execution failed", self.task.id)

        # Phase 3: Start emulator session and execute tool
        if emulator_component and tool_component:
            self._run_emulator_session(emulator_component, logcat_component, coverage_component, tool_component, context)
        else:
            self.logger.warning("Missing emulator or tool component - skipping emulator session")

    def _run_emulator_session(self, emulator_component, logcat_component, coverage_component, tool_component, context: Dict[str, Any]) -> None:
        """
        Run emulator session with proper lifecycle management.
        
        Args:
            emulator_component: Emulator component
            logcat_component: Logcat component  
            coverage_component: Coverage component
            tool_component: Tool execution component
            context: Task execution context
        """
        # Start emulator using context manager
        with emulator_component.start_emulator("RVSec") as android:
            # Store android interface and device_id in context for tools
            context["android"] = android
            context["device_id"] = self.task.config.device_id

            # Install app if needed
            if not self.task.config.skip_installation:
                self.logger.info("Installing application")
                if not emulator_component.install_app(android, self.task.app):
                    raise TaskExecutionError("Failed to install application", self.task.id)

            # Set up logcat and coverage tracking
            if logcat_component:
                self.logger.info("Starting logcat capture")
                logcat_component.start_capture()

            if coverage_component:
                self.logger.info("Starting coverage tracking")
                coverage_component.start_tracking()

            # Mark precise tool execution start for accurate timing measurement
            self.task.mark_tool_execution_start()
            self._publish_tool_execution_started_event()

            # Execute the tool
            self.logger.info(f"Executing component: {tool_component.name}")
            if not tool_component.execute(context):
                raise TaskExecutionError(f"Component {tool_component.name} execution failed", self.task.id)

            # Stop tracking and process results
            if coverage_component:
                self.logger.info("Stopping coverage tracking")
                coverage_component.stop_tracking()
                self.logger.info("Processing coverage results")
                coverage_component.process_results()

            if logcat_component:
                self.logger.info("Stopping logcat capture")
                logcat_component.stop_capture()

    def _cleanup_components(self, context: Dict[str, Any]) -> None:
        """
        Clean up all registered components.
        
        Args:
            context: Task execution context
        """
        for component in self.components:
            if hasattr(component, 'cleanup'):
                try:
                    component_name = getattr(component, 'name', type(component).__name__)
                    self.logger.debug(f"Cleaning up component: {component_name}")
                    component.cleanup(context)
                except Exception as e:
                    self.logger.warning(f"Error cleaning up component {component_name}: {e}")

    def _cleanup_resources(self) -> None:
        """Clean up resources in case of error."""
        context = self.get_task_context()
        with self.logger.with_context(phase="resource_cleanup"):
            try:
                # Clean up all components
                self._cleanup_components(context)
            except Exception as e:
                # Create error context for cleanup failure
                cleanup_context = self.get_task_context()
                cleanup_context["phase"] = "component_cleanup"
                cleanup_context["component_count"] = len(self.components)

                # Use ErrorHandler for proper exception handling
                self.error_handler.handle_error(e, cleanup_context)

                # Log cleanup warning
                self.logger.warning(LOG_ERROR.format(
                    phase="cleaning up components",
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
                "tool_name": self.task.config.tool_config.get_full_tool_name()
            },
            source="TaskExecutor",
            channel=EventChannel.LIFECYCLE
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
                "tool_name": self.task.config.tool_config.get_full_tool_name()
            },
            source="TaskExecutor",
            channel=EventChannel.LIFECYCLE
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
                "tool_name": self.task.config.tool_config.get_full_tool_name()
            },
            details={
                "error": error_message
            },
            source="TaskExecutor",
            channel=EventChannel.ERROR
        )
    
    def _publish_tool_execution_started_event(self) -> None:
        """
        Publish tool execution started event for timing coordination.
        
        This event provides accurate timing information for coverage analysis
        where time_since_task_start should reflect tool execution duration.
        """
        self.event_bus.publish_task_event(
            event_type=EventType.TOOL_STARTED,
            task_id=self.task.id,
            task_config={
                "apk_name": self.task.config.apk_name,
                "tool_name": self.task.config.tool_config.get_full_tool_name()
            },
            details={
                "tool_execution_start": self.task.result.tool_execution_start.isoformat() if self.task.result.tool_execution_start else None,
                "timing_context": "precise_tool_execution"
            },
            source="TaskExecutor",
            channel=EventChannel.LIFECYCLE
        )