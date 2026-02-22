# rvandroid/commands/command_not_found_error.py
"""
Exception for command not found errors in the RV-Android framework.

This module provides the CommandNotFoundError class, a specialized exception
for handling cases where a command is not found or cannot be executed due to
missing binaries or incorrect paths.
"""

from .command_exception import CommandException


class CommandNotFoundError(CommandException):
    """
    Exception raised when a command is not found in the system.

    ### Architectural Decisions:
    - Extends CommandException with specialized handling for "not found" scenarios
    - Provides clear error messages specific to missing commands
    - Enables distinct error handling for command not found cases

    ### Role in the System:
    - Indicates system configuration or environment issues
    - Helps distinguish between runtime failures and setup issues
    - Facilitates appropriate error recovery strategies
    """

    def __init__(self, message: str = "Command not found"):
        """
        Initialize the CommandNotFoundError.

        Args:
            message (str): Detailed error message
        """
        super().__init__(tool="unknown", code=-1, message=message)

        # Extract command name from message if possible
        if "command " in message and " was not found" in message:
            try:
                cmd = message.split("command ")[1].split(" was not found")[0]
                self.tool = cmd
            except:
                pass
