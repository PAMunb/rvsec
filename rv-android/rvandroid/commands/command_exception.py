class CommandException(Exception):
    """
    Exception raised when command execution fails.
    Contains information about the tool, exit code, and error message.
    """
    def __init__(self, tool: str, code, message: str):
        """
        Initialize CommandException with execution details.
        
        Args:
            tool (str): Name of the tool/command that failed
            code: Exit code from the command execution
            message (str): Error message describing the failure
        """
        self.tool = tool
        self.code = code
        self.message = message

    def __str__(self) -> str:
        """Returns a formatted string representation of the exception"""
        return f'CommandException[tool={self.tool} ::: code={self.code} ::: message={self.message}]'
