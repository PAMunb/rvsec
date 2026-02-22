"""Exception hierarchy for the RV-Android framework."""

from typing import List, Optional


class RVAndroidError(Exception):
    """Base exception class for all RV-Android errors."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        self.message = message
        self.cause = cause
        super().__init__(message)

    def __str__(self):
        cause_str = (
            f" caused by {type(self.cause).__name__}: {self.cause}"
            if self.cause
            else ""
        )
        return f"{type(self).__name__}: {self.message}{cause_str}"


class ConfigurationError(RVAndroidError):
    """Error raised when there's a problem with the configuration."""


class NetworkError(RVAndroidError):
    """Error raised when there's a network-related problem."""


class EmulatorError(RVAndroidError):
    """Error raised when there's a problem with the Android emulator."""


class ADBError(NetworkError):
    """Error raised when there's a problem with ADB commands."""


class InstrumentationError(RVAndroidError):
    """Error raised when there's a problem with APK instrumentation."""


class AnalysisError(RVAndroidError):
    """Error raised when there's a problem with static or dynamic analysis."""


class ExecutionError(RVAndroidError):
    """Error raised when there's a problem during test execution."""


class TaskExecutionError(ExecutionError):
    """Error raised specifically during task execution."""

    def __init__(self, message: str, task_id: int, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.task_id = task_id

    def __str__(self):
        return f"{super().__str__()} (Task ID: {self.task_id})"


class RVValidationError(ConfigurationError):
    """Base exception for data validation errors in Pydantic models."""

    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, cause)
        self.field_name = field_name

    def __str__(self):
        field_info = f" (Field: {self.field_name})" if self.field_name else ""
        return f"{super().__str__()}{field_info}"


class CommandValidationError(RVValidationError):
    """Exception for command parameter validation errors."""


class LogcatValidationError(RVValidationError):
    """Exception for logcat configuration validation errors."""


class EventProcessingError(RVAndroidError):
    """Exception for event processing failures in the event system."""

    def __init__(
        self,
        message: str,
        event_type: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, cause)
        self.event_type = event_type

    def __str__(self):
        event_info = f" (Event: {self.event_type})" if self.event_type else ""
        return f"{super().__str__()}{event_info}"


class RVCommandTimeoutError(RVAndroidError):
    """Exception for command execution timeouts at the infrastructure level."""

    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[int] = None,
        command: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, cause)
        self.timeout_seconds = timeout_seconds
        self.command = command

    def __str__(self):
        timeout_info = (
            f" (Timeout: {self.timeout_seconds}s)" if self.timeout_seconds else ""
        )
        command_info = f" (Command: {self.command})" if self.command else ""
        return f"{super().__str__()}{timeout_info}{command_info}"


class JarNotFoundError(RVAndroidError):
    """Exception for JAR file resolution failures in tool execution."""

    def __init__(
        self,
        message: str,
        jar_name: Optional[str] = None,
        search_paths: Optional[List[str]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, cause)
        self.jar_name = jar_name
        self.search_paths = search_paths or []

    def __str__(self):
        jar_info = f" (JAR: {self.jar_name})" if self.jar_name else ""
        paths_info = (
            f" (Searched: {len(self.search_paths)} paths)" if self.search_paths else ""
        )
        return f"{super().__str__()}{jar_info}{paths_info}"


class RVToolError(RVAndroidError):
    """Base exception for tool-related errors in the testing framework."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, cause)
        self.tool_name = tool_name

    def __str__(self):
        tool_info = f" (Tool: {self.tool_name})" if self.tool_name else ""
        return f"{super().__str__()}{tool_info}"


class RVToolExecutionError(RVToolError):
    """Exception for tool execution failures during testing operations."""


class RVToolTimeoutError(RVToolError):
    """Exception for tool timeout scenarios during testing operations."""

    def __init__(
        self,
        message: str,
        tool_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, tool_name, cause)
        self.timeout_seconds = timeout_seconds

    def __str__(self):
        timeout_info = (
            f" (Timeout: {self.timeout_seconds}s)" if self.timeout_seconds else ""
        )
        return f"{super().__str__()}{timeout_info}"


class ToolNotFoundError(RVToolError):
    """Exception raised when a requested tool is not found in the registry."""


class ToolRegistrationError(RVToolError):
    """Exception raised when tool registration fails due to invalid data or conflicts."""


class RVExperimentError(RVAndroidError):
    """Base exception for experiment-related errors in the research framework."""

    def __init__(
        self,
        message: str,
        experiment_id: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, cause)
        self.experiment_id = experiment_id

    def __str__(self):
        exp_info = f" (Experiment: {self.experiment_id})" if self.experiment_id else ""
        return f"{super().__str__()}{exp_info}"


class RVExperimentExecutionError(RVExperimentError):
    """Exception for experiment execution failures during runtime."""


class RVParsingError(RVAndroidError):
    """Base exception for parsing-related errors in analysis components."""

    def __init__(
        self,
        message: str,
        parser_type: Optional[str] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message, cause)
        self.parser_type = parser_type

    def __str__(self):
        parser_info = f" (Parser: {self.parser_type})" if self.parser_type else ""
        return f"{super().__str__()}{parser_info}"
