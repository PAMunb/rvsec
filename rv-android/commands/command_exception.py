class CommandException(Exception):
    "Raised when the command execution fails"

    def __init__(self, tool: str, code, message: str):
        self.tool = tool
        self.code = code #TODO qual o tipo???
        self.message = message

    def __str__(self):
        return f'CommandException[tool={self.tool} ::: code={self.code} ::: message={self.message}]'
