# rv_platform/components/tool_execution.py
"""
Tool execution component for rv-platform.

This component handles tool invocation and result processing in a simplified,
standalone manner suitable for the platform architecture.
"""

from typing import Optional, Dict, Any

from rv_android_core.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_TOOL_NAME, \
    LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.event import EventBus, EventType
from rv_android_core.domain.task import Task
from rv_android_core.tools.abstract_tool import AbstractTool


class ToolExecutionComponent:
    """
    Component responsible for managing tool execution.
    Handles tool invocation and result processing.

    ### Architectural Decisions:
    - Encapsulates tool execution functionality
    - Implements clear separation of concerns for task execution
    - Provides focused error handling for tool operations

    ### Role in the System:
    - Manages testing tool execution during tasks
    - Reports tool events to the event system
    - Ensures proper process cleanup after execution
    """

    def __init__(self, task: Task, tool: AbstractTool, event_bus: Optional[EventBus] = None):
        """Initialize with task, tool and optional event bus."""
        self.name = "ToolExecutionComponent"
        self.task = task
        self.tool = tool
        self.event_bus = event_bus or EventBus.get_instance()
        
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            'rv_platform.components.tool_execution',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: task.config.apk_name,
                CONTEXT_TOOL_NAME: tool.name
            }
        )
        
        # Error handler
        self.error_handler = ErrorHandler.get_instance()

    def initialize(self, context: Dict[str, Any]) -> bool:
        """
        Initialize the component.
        
        Args:
            context: Task execution context
            
        Returns:
            True if initialization was successful
        """
        self.logger.debug(f"Initializing {self.name}")
        return True

    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the testing tool for the task.
        
        Args:
            context: Task execution context
            
        Returns:
            True if tool execution was successful
        """
        return self.run_tool()

    def cleanup(self, context: Dict[str, Any]) -> None:
        """
        Clean up component resources.
        
        Args:
            context: Task execution context
        """
        self.cleanup_processes()

    def run_tool(self) -> bool:
        """
        Execute the tool on the current task.

        Returns:
            Success status
        """
        try:
            self.logger.info(LOG_START.format(phase=f"tool: {self.tool.name}"))

            # Publish tool started event
            self.event_bus.publish_task_event(
                EventType.TOOL_STARTED,
                task_id=self.task.id,
                details={"tool_name": self.tool.name},
                source="ToolExecutionComponent"
            )

            # Execute the tool
            self.tool.execute(self.task, self.task.app)
            self.logger.info(LOG_COMPLETE.format(phase=f"tool: {self.tool.name}"))

            # Publish tool stopped event
            self.event_bus.publish_task_event(
                EventType.TOOL_STOPPED,
                task_id=self.task.id,
                details={"tool_name": self.tool.name},
                source="ToolExecutionComponent"
            )

            return True

        except Exception as e:
            # Check if this is a timeout exception (already logged)
            from rv_android_core.util.error.exceptions import RVToolTimeoutError
            
            if isinstance(e, RVToolTimeoutError):
                # Timeout is expected, don't log as error
                self.logger.info(LOG_COMPLETE.format(phase=f"tool: {self.tool.name} (timeout)"))
                
                # Publish tool completed event for timeouts
                self.event_bus.publish_task_event(
                    EventType.TOOL_STOPPED,
                    task_id=self.task.id,
                    details={"tool_name": self.tool.name, "reason": "timeout"},
                    source="ToolExecutionComponent"
                )
                
                return True  # Timeout is considered successful completion
            else:
                # Actual failure - reduced logging (tool already logged the details)
                self.logger.error(LOG_ERROR.format(
                    phase=f"executing tool {self.tool.name}",
                    error=str(e)
                ))
                
                # Don't handle the error here - let it propagate with original context
                # Publish tool failed event
                self.event_bus.publish_task_event(
                    EventType.TASK_FAILED,
                    task_id=self.task.id,
                    details={
                        "tool_name": self.tool.name,
                        "error": str(e)
                    },
                    source="ToolExecutionComponent"
                )

                return False

    def cleanup_processes(self) -> None:
        """Clean up any hanging processes related to the tool."""
        if hasattr(self.tool, 'process_pattern') and self.tool.process_pattern:
            try:
                self.logger.debug(LOG_START.format(
                    phase=f"cleaning up processes for tool: {self.tool.name}"
                ))
                self.tool.kill_related_processes(self.tool.process_pattern)
                self.logger.debug(LOG_COMPLETE.format(
                    phase=f"cleaning up processes for tool: {self.tool.name}"
                ))
            except Exception as e:
                self.logger.warning(LOG_ERROR.format(
                    phase=f"cleaning up processes for tool: {self.tool.name}",
                    error=str(e)
                ))