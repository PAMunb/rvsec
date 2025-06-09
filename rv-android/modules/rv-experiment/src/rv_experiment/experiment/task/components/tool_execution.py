# rvandroid/experiment/task/components/tool_execution.py
from typing import Optional, Dict, Any

from rv_android_core.util.exceptions import ToolError
from rv_android_core.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_TOOL_NAME, \
    LOG_START, LOG_COMPLETE, LOG_ERROR
from rv_android_core.event.bus import EventBus, EventType
from rv_experiment.experiment.task.component import BaseTaskComponent
from rv_experiment.experiment.task.task_model import Task
from rv_android_core.tools.abstract_tool import AbstractTool


class ToolExecutionComponent(BaseTaskComponent):
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
        super().__init__("ToolExecutionComponent", event_bus)
        self.task = task
        self.tool = tool

        # Update logger context with task and tool information
        self.logger.push_context(**{
            CONTEXT_TASK_ID: task.id,
            CONTEXT_APP_NAME: task.config.apk_name,
            CONTEXT_TOOL_NAME: tool.name
        })

    def _execute_impl(self, context: Dict[str, Any]) -> bool:
        """
        Execute the testing tool for the task.
        
        Args:
            context: Task execution context
            
        Returns:
            True if tool execution was successful
        """
        return self.run_tool()

    def run_tool(self) -> bool:
        """
        Execute the tool on the current task.

        Returns:
            Success status
        """
        with self.logger.with_context(phase="execute_tool"):
            try:
                self.logger.info(LOG_START.format(operation=f"tool: {self.tool.name}"))

                # Publish tool started event
                if self.event_bus:
                    self.event_bus.publish_task_event(
                        EventType.TOOL_STARTED,
                        task_id=self.task.id,
                        details={"tool_name": self.tool.name},
                        source="ToolExecutionComponent"
                    )

                # Execute the tool
                self.tool.execute(self.task, self.task.app)
                self.logger.info(LOG_COMPLETE.format(operation=f"tool: {self.tool.name}"))

                # Publish tool stopped event
                if self.event_bus:
                    self.event_bus.publish_task_event(
                        EventType.TOOL_STOPPED,
                        task_id=self.task.id,
                        details={"tool_name": self.tool.name},
                        source="ToolExecutionComponent"
                    )

                return True

            except Exception as e:
                self.logger.error(LOG_ERROR.format(
                    operation=f"executing tool {self.tool.name}",
                    error=str(e)
                ))
                self._get_error_handler().handle_error(
                    ToolError(f"Error executing tool {self.tool.name}", self.tool.name, e),
                    {"task_id": self.task.id, "tool_name": self.tool.name}
                )

                # Publish tool failed event
                if self.event_bus:
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
        with self.logger.with_context(phase="cleanup_processes"):
            if hasattr(self.tool, 'process_pattern') and self.tool.process_pattern:
                try:
                    self.logger.debug(LOG_START.format(
                        operation=f"cleaning up processes for tool: {self.tool.name}"
                    ))
                    self.tool.kill_related_processes(self.tool.process_pattern)
                    self.logger.debug(LOG_COMPLETE.format(
                        operation=f"cleaning up processes for tool: {self.tool.name}"
                    ))
                except Exception as e:
                    self.logger.warning(LOG_ERROR.format(
                        operation=f"cleaning up processes for tool: {self.tool.name}",
                        error=str(e)
                    ))
