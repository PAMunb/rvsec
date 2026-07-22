# rvandroid/util/exceptions.py
from typing import Optional


class RVAndroidError(Exception):
    """Base exception class for all RV-Android errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        self.message = message
        self.cause = cause
        super().__init__(message)

    def __str__(self):
        cause_str = f" caused by {type(self.cause).__name__}: {self.cause}" if self.cause else ""
        return f"{type(self).__name__}: {self.message}{cause_str}"


class ConfigurationError(RVAndroidError):
    """Error raised when there's a problem with the configuration."""
    pass


class ResourceError(RVAndroidError):
    """Error raised when there's a problem with resource management."""
    pass


class NetworkError(RVAndroidError):
    """Error raised when there's a network-related problem."""
    pass


class EmulatorError(RVAndroidError):
    """Error raised when there's a problem with the Android emulator."""
    pass


class ADBError(NetworkError):
    """Error raised when there's a problem with ADB commands."""
    pass


class InstrumentationError(RVAndroidError):
    """Error raised when there's a problem with APK instrumentation."""
    pass


class AnalysisError(RVAndroidError):
    """Error raised when there's a problem with static or dynamic analysis."""
    pass


class ExecutionError(RVAndroidError):
    """Error raised when there's a problem during test execution."""
    pass


class MonitorError(RVAndroidError):
    """Error raised when there's a problem with monitor generation or execution."""
    pass


class RvTimeoutError(RVAndroidError):
    """Error raised when an operation times out."""
    pass


class TaskExecutionError(ExecutionError):
    """Error raised specifically during task execution."""

    def __init__(self, message: str, task_id: int, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.task_id = task_id

    def __str__(self):
        return f"{super().__str__()} (Task ID: {self.task_id})"


class ToolError(ExecutionError):
    """Error raised when a specific testing tool fails."""

    def __init__(self, message: str, tool_name: str, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.tool_name = tool_name

    def __str__(self):
        return f"{super().__str__()} (Tool: {self.tool_name})"


class LogcatError(AnalysisError):
    """Error raised when there's a problem with logcat operations."""
    pass


class CoverageError(AnalysisError):
    """Error raised when there's a problem with coverage tracking or analysis."""
    pass


class ActionExecutionError(ExecutionError):
    """Error raised specifically during action execution."""

    def __init__(self, message: str, action_id: Optional[int] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.action_id = action_id

    def __str__(self):
        action_info = f" (Action ID: {self.action_id})" if self.action_id else ""
        return f"{super().__str__()}{action_info}"
