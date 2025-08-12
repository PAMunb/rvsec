# rvandroid/util/exceptions.py
from typing import Optional, List


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


class LLMServiceError(RVAndroidError):
    """Error raised during LLM service operations."""
    pass


class ServerLifecycleError(RVAndroidError):
    """Error raised during server lifecycle management operations."""
    
    def __init__(self, message: str, server_port: Optional[int] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.server_port = server_port
    
    def __str__(self):
        port_info = f" (Port: {self.server_port})" if self.server_port else ""
        return f"{super().__str__()}{port_info}"


class ToolCreationError(RVAndroidError):
    """Error raised when tool creation fails."""
    pass


class RVAndroidToolError(ToolError):
    """Error raised specifically by the RVAndroid tool."""
    
    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message, "rvandroid", cause)


class ActionExecutionError(ExecutionError):
    """Error raised specifically during action execution."""

    def __init__(self, message: str, action_id: Optional[int] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.action_id = action_id

    def __str__(self):
        action_info = f" (Action ID: {self.action_id})" if self.action_id else ""
        return f"{super().__str__()}{action_info}"


# Enhanced exception hierarchy for improved automatic handling

class RVTaskError(RVAndroidError):
    """Base exception for task-related errors in the experiment framework."""
    
    def __init__(self, message: str, task_id: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.task_id = task_id
    
    def __str__(self):
        task_info = f" (Task: {self.task_id})" if self.task_id else ""
        return f"{super().__str__()}{task_info}"


class RVTaskExecutionError(RVTaskError):
    """Exception for task execution failures in experiment workflows."""
    pass


class RVTaskConfigurationError(RVTaskError):
    """Exception for task configuration errors in experiment setup."""
    pass


class RVTaskTimeoutError(RVTaskError):
    """Exception for task timeout errors during experiment execution."""
    pass


class RVToolError(RVAndroidError):
    """Base exception for tool-related errors in the testing framework."""
    
    def __init__(self, message: str, tool_name: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.tool_name = tool_name
    
    def __str__(self):
        tool_info = f" (Tool: {self.tool_name})" if self.tool_name else ""
        return f"{super().__str__()}{tool_info}"


class RVToolExecutionError(RVToolError):
    """Exception for tool execution failures during testing operations."""
    pass


class RVToolTimeoutError(RVToolError):
    """Exception for tool timeout scenarios during testing operations."""
    
    def __init__(self, message: str, tool_name: Optional[str] = None, timeout_seconds: Optional[int] = None, cause: Optional[Exception] = None):
        super().__init__(message, tool_name, cause)
        self.timeout_seconds = timeout_seconds
    
    def __str__(self):
        timeout_info = f" (Timeout: {self.timeout_seconds}s)" if self.timeout_seconds else ""
        return f"{super().__str__()}{timeout_info}"


class RVToolConfigurationError(RVToolError):
    """Exception for tool configuration errors during setup."""
    pass


class RVAndroidToolError(RVToolError):
    """Exception raised during RVAndroid tool execution."""
    
    def __init__(self, message: str, tool_name: Optional[str] = "rvandroid", cause: Optional[Exception] = None):
        super().__init__(message, tool_name, cause)
        
    def __str__(self):
        return f"RVAndroidToolError: {super().__str__()}"


class ToolNotFoundError(RVToolError):
    """Exception raised when a requested tool is not found in the registry."""
    pass


class ToolRegistrationError(RVToolError):
    """Exception raised when tool registration fails due to invalid data or conflicts."""
    pass


class ToolVariantError(RVToolError):
    """Exception for tool variant related errors."""
    
    def __init__(self, message: str, tool_name: Optional[str] = None, variant_name: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, tool_name, cause)
        self.variant_name = variant_name
    
    def __str__(self):
        variant_info = f" (Variant: {self.variant_name})" if self.variant_name else ""
        return f"{super().__str__()}{variant_info}"


class PluginError(RVToolError):
    """Exception for plugin system related errors."""
    
    def __init__(self, message: str, plugin_name: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, plugin_name, cause)
        self.plugin_name = plugin_name
    
    def __str__(self):
        plugin_info = f" (Plugin: {self.plugin_name})" if self.plugin_name else ""
        return f"{super().__str__()}{plugin_info}"


class RVExperimentError(RVAndroidError):
    """Base exception for experiment-related errors in the research framework."""
    
    def __init__(self, message: str, experiment_id: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.experiment_id = experiment_id
    
    def __str__(self):
        exp_info = f" (Experiment: {self.experiment_id})" if self.experiment_id else ""
        return f"{super().__str__()}{exp_info}"


class RVExperimentSetupError(RVExperimentError):
    """Exception for experiment setup failures during configuration."""
    pass


class RVExperimentExecutionError(RVExperimentError):
    """Exception for experiment execution failures during runtime."""
    pass


class RVParsingError(RVAndroidError):
    """Base exception for parsing-related errors in analysis components."""
    
    def __init__(self, message: str, parser_type: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.parser_type = parser_type
    
    def __str__(self):
        parser_info = f" (Parser: {self.parser_type})" if self.parser_type else ""
        return f"{super().__str__()}{parser_info}"

class RVPromptError(RVAndroidError):
    """Base exception for prompt framework related errors."""

    def __init__(self, message: str, strategy: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.strategy_name = strategy

    def __str__(self):
        strategy_info = f" (Strategy: {self.strategy_name})" if self.strategy_name else ""
        return f"{super().__str__()}{strategy_info}"

class RVLLMError(RVAndroidError):
    """Base exception for language model related errors."""
    
    def __init__(self, message: str, model_name: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.model_name = model_name
    
    def __str__(self):
        model_info = f" (Model: {self.model_name})" if self.model_name else ""
        return f"{super().__str__()}{model_info}"


class RVValidationError(ConfigurationError):
    """Base exception for data validation errors in Pydantic models."""
    
    def __init__(self, message: str, field_name: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.field_name = field_name
    
    def __str__(self):
        field_info = f" (Field: {self.field_name})" if self.field_name else ""
        return f"{super().__str__()}{field_info}"


class CommandValidationError(RVValidationError):
    """Exception for command parameter validation errors."""
    pass


class LogcatValidationError(RVValidationError):
    """Exception for logcat configuration validation errors."""
    pass


class EventProcessingError(RVAndroidError):
    """Exception for event processing failures in the event system."""
    
    def __init__(self, message: str, event_type: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.event_type = event_type
    
    def __str__(self):
        event_info = f" (Event: {self.event_type})" if self.event_type else ""
        return f"{super().__str__()}{event_info}"


class RVCommandTimeoutError(RVAndroidError):
    """Exception for command execution timeouts at the infrastructure level."""
    
    def __init__(self, message: str, timeout_seconds: Optional[int] = None, 
                 command: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.timeout_seconds = timeout_seconds
        self.command = command
    
    def __str__(self):
        timeout_info = f" (Timeout: {self.timeout_seconds}s)" if self.timeout_seconds else ""
        command_info = f" (Command: {self.command})" if self.command else ""
        return f"{super().__str__()}{timeout_info}{command_info}"


class JarNotFoundError(RVAndroidError):
    """Exception for JAR file resolution failures in tool execution."""
    
    def __init__(self, message: str, jar_name: Optional[str] = None, 
                 search_paths: Optional[List[str]] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.jar_name = jar_name
        self.search_paths = search_paths or []
    
    def __str__(self):
        jar_info = f" (JAR: {self.jar_name})" if self.jar_name else ""
        paths_info = f" (Searched: {len(self.search_paths)} paths)" if self.search_paths else ""
        return f"{super().__str__()}{jar_info}{paths_info}"


class CircuitBreakerOpenError(RVAndroidError):
    """Exception for circuit breaker open state in command execution."""
    
    def __init__(self, message: str, command_signature: Optional[str] = None, 
                 failure_count: Optional[int] = None, cause: Optional[Exception] = None):
        super().__init__(message, cause)
        self.command_signature = command_signature
        self.failure_count = failure_count
    
    def __str__(self):
        command_info = f" (Command: {self.command_signature})" if self.command_signature else ""
        failure_info = f" (Failures: {self.failure_count})" if self.failure_count else ""
        return f"{super().__str__()}{command_info}{failure_info}"


# LLM-specific exceptions

class RVLLMConnectionError(RVLLMError):
    """Exception for LLM connection failures."""
    
    def __init__(self, message: str, model_name: Optional[str] = None, 
                 provider: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, model_name, cause)
        self.provider = provider
    
    def __str__(self):
        provider_info = f" (Provider: {self.provider})" if self.provider else ""
        return f"{super().__str__()}{provider_info}"


class RVLLMModelError(RVLLMError):
    """Exception for LLM model loading and generation errors."""
    
    def __init__(self, message: str, model_name: Optional[str] = None, 
                 operation: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, model_name, cause)
        self.operation = operation
    
    def __str__(self):
        operation_info = f" (Operation: {self.operation})" if self.operation else ""
        return f"{super().__str__()}{operation_info}"


class RVLLMProviderError(RVLLMError):
    """Exception for provider-specific errors."""
    
    def __init__(self, message: str, model_name: Optional[str] = None, 
                 provider: Optional[str] = None, status_code: Optional[int] = None, 
                 cause: Optional[Exception] = None):
        super().__init__(message, model_name, cause)
        self.provider = provider
        self.status_code = status_code
    
    def __str__(self):
        provider_info = f" (Provider: {self.provider})" if self.provider else ""
        status_info = f" (Status: {self.status_code})" if self.status_code else ""
        return f"{super().__str__()}{provider_info}{status_info}"


class RVLLMConfigurationError(RVLLMError):
    """Exception for LLM configuration validation errors."""
    
    def __init__(self, message: str, model_name: Optional[str] = None, 
                 config_field: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, model_name, cause)
        self.config_field = config_field
    
    def __str__(self):
        field_info = f" (Field: {self.config_field})" if self.config_field else ""
        return f"{super().__str__()}{field_info}"


class RVLLMTemplateError(RVPromptError):
    """Exception for LLM template processing errors."""
    
    def __init__(self, message: str, strategy: Optional[str] = None, 
                 template_name: Optional[str] = None, cause: Optional[Exception] = None):
        super().__init__(message, strategy, cause)
        self.template_name = template_name
    
    def __str__(self):
        template_info = f" (Template: {self.template_name})" if self.template_name else ""
        return f"{super().__str__()}{template_info}"
