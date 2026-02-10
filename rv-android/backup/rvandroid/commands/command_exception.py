"""
Exception class for command execution errors in the RV-Android framework.

### Architectural Decisions:
- Provides detailed error information for command failures
- Captures context of the failed command
- Enables precise error tracking and debugging
"""


class CommandException(Exception):
    """
    Exception raised when a command execution fails.

    ### Attributes:
    - tool: Name of the tool or context of the command
    - code: Exit code of the failed command
    - message: Detailed error message from command execution
    """

    def __init__(self, tool: str, code: int, message: str):
        """
        Initialize the CommandException.

        Args:
            tool: Identifier for the tool or command context
            code: Exit code from the command
            message: Error message from command execution
        """
        self.tool = tool
        self.code = code
        self.message = message

    def __str__(self):
        """
        Provide a string representation of the exception.

        Returns:
            Formatted error message with tool, code, and details
        """
        return f"CommandException[tool={self.tool} ::: code={self.code} ::: message={self.message}]"
