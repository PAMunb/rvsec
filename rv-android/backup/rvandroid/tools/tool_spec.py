# rvandroid/tools/tool_spec.py
import logging as logging_api
import os
from abc import ABCMeta, abstractmethod

from rvandroid.app import App
from rvandroid.commands.command import Command

logging = logging_api.getLogger(__name__)


class AbstractTool:
    __metaclass__ = ABCMeta
    """
    An abstract base class defining the core contract for test automation tools in the RV-Android framework.

    ### Architectural Decisions:
    - Implements a standardized interface for test automation tool integration
    - Defines a template method pattern for tool execution
    - Provides a consistent mechanism for tool-specific logic implementation
    - Supports flexible extension and customization of testing tools

    ### Role in the System:
    - Serves as the foundational abstraction for all testing tools
    - Defines a uniform execution workflow for different testing approaches
    - Enables seamless integration of diverse testing strategies
    - Provides a standardized mechanism for process management and cleanup
    - Acts as a critical component in experiment tool orchestration

    ### Key Considerations:
    - Enforces a consistent execution contract for all tool implementations
    - Manages tool-specific process termination
    - Supports flexible tool initialization and configuration
    - Provides a template for implementing tool-specific execution logic
    - Ensures proper resource management and process cleanup

    ### Integration Strategy:
    - Compatible with multiple testing tool implementations
    - Supports dynamic tool registration and execution
    - Enables dependency injection and tool composition
    - Provides a clear extension point for new testing tools
    - Facilitates tool-agnostic experiment design

    ### Performance and Scalability:
    - Designed for lightweight tool abstraction
    - Minimizes overhead in tool execution and management
    - Supports diverse testing tool implementations
    - Enables efficient process termination and resource cleanup
    - Adaptable to different testing complexity and scale requirements
    """

    def __init__(self, name: str, description: str, process_pattern: str):
        self.name = name
        self.description = description
        self.process_pattern = process_pattern
        super(AbstractTool, self).__init__()

    @abstractmethod
    def execute_tool_specific_logic(self, task, app: App):
        """This is our hook method, an extention point that every tool developer
        must provide an implementation. It should only be called by the execute
        instance method.
        """
        pass

    def execute(self, task, app: App):
        """This is the operation that allows the execution of a tool. It works
        as a template method, implementing a loging that delegates to
        the abstract method of this class the actual logic.

        Args:
           task: task to be executed (can be Task or task_model.Task)
           app (App): app under test
        """
        logging.info("Executing tool: {}".format(self.name))
        self.execute_tool_specific_logic(task, app)
        self.kill_related_processes(self.process_pattern)

    def kill_related_processes(self, process_pattern: str):
        """Kills all related processes"""
        if process_pattern is None:
            return

        get_processes_cmd = Command('adb', [
            'shell',
            'ps',
            '|',
            'grep',
            process_pattern
        ])
        get_processes_result = get_processes_cmd.invoke()
        for line in get_processes_result.stdout.decode('ascii').split(os.linesep):
            if line.strip():
                tokens = line.split()
                kill_process_cmd = Command('adb', [
                    'shell',
                    'kill',
                    tokens[1],
                ])
                kill_process_cmd.invoke()
