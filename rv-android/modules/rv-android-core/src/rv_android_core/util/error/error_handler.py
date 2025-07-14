# rvandroid/util/error/error_handler.py
import functools
import threading
import time
from contextlib import contextmanager
from typing import Dict, List, Callable, Any, Type, Optional, Union

from rv_android_core.util.error.exceptions import (
    RVAndroidError, RVTaskError, RVToolError, RVToolExecutionError, RVToolTimeoutError, ToolNotFoundError,
    ToolRegistrationError, ToolVariantError, PluginError,
    RVExperimentError, RVParsingError, RVLLMError, RVPromptError,
    RVValidationError, CommandValidationError, LogcatValidationError,
    EventProcessingError, ConfigurationError, RVCommandTimeoutError, JarNotFoundError,
    CircuitBreakerOpenError, RVLLMConnectionError, RVLLMModelError, RVLLMProviderError,
    RVLLMConfigurationError, RVLLMTemplateError
)
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ErrorHandler:
    """
    Centralized error handling system for rv-android-core.

    ### Architectural Decisions:
    - Implements a unified approach to error management across all components
    - Delegates specific error handling to specialized strategies
    - Provides detailed error tracking, aggregation, and reporting
    - Uses a registry-based approach for handler lookup and execution
    - Uses callback pattern instead of EventBus for loose coupling

    ### Role in the System:
    - Acts as the central error management facility
    - Provides consistent error handling behavior across the framework
    - Enables error aggregation for pattern detection and reporting
    - Supports automatic recovery strategies for common failure scenarios
    - Facilitates error classification and appropriate response selection

    ### Design Note - Event Publishing:
    This core module ErrorHandler does NOT publish events directly to maintain
    module independence. Event publishing should be implemented in higher-level
    modules (like experiment modules) through the callback system.
    Use register_error_callback() to integrate with event systems when needed.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = ErrorHandler()
        return cls._instance

    def __init__(self):
        """Initialize the error handler."""
        # Get standardized logger with context
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            'rv_android_core.util.error.error_handler',
            {
                CONTEXT_COMPONENT: 'ErrorHandler'
            }
        )

        # Error callbacks for external integration
        self._error_callbacks: List[Callable[[Exception, Optional[Dict[str, Any]]], None]] = []

        # Error statistics and tracking
        self._error_counts: Dict[str, int] = {}
        self._error_history: List[Dict[str, Any]] = []
        self._recovery_attempts: Dict[str, int] = {}

        # Register built-in handlers
        self._register_builtin_handlers()

    def _register_builtin_handlers(self):
        """Register all built-in error handlers."""
        # Register handlers for each error type
        # Order matters: register most specific handlers first
        self.register_handler(CommandValidationError, self._handle_command_validation_error)
        self.register_handler(LogcatValidationError, self._handle_logcat_validation_error)
        self.register_handler(EventProcessingError, self._handle_event_processing_error)
        self.register_handler(RVValidationError, self._handle_validation_error)
        self.register_handler(RVTaskError, self._handle_task_error)
        self.register_handler(ToolNotFoundError, self._handle_tool_not_found_error)
        self.register_handler(ToolRegistrationError, self._handle_tool_registration_error)
        self.register_handler(ToolVariantError, self._handle_tool_variant_error)
        self.register_handler(PluginError, self._handle_plugin_error)
        self.register_handler(RVToolTimeoutError, self._handle_tool_timeout_error)
        self.register_handler(RVToolExecutionError, self._handle_tool_execution_error)
        self.register_handler(RVToolError, self._handle_tool_error)
        self.register_handler(RVExperimentError, self._handle_experiment_error)
        self.register_handler(RVParsingError, self._handle_parsing_error)
        self.register_handler(RVPromptError, self._handle_prompt_error)
        # Register specific LLM error handlers (Phase 6)
        self.register_handler(RVLLMConnectionError, self._handle_llm_connection_error)
        self.register_handler(RVLLMModelError, self._handle_llm_model_error)
        self.register_handler(RVLLMProviderError, self._handle_llm_provider_error)
        self.register_handler(RVLLMConfigurationError, self._handle_llm_configuration_error)
        self.register_handler(RVLLMTemplateError, self._handle_llm_template_error)
        # Register generic LLM error handler last
        self.register_handler(RVLLMError, self._handle_llm_error)
        # Register new infrastructure exception handlers
        self.register_handler(RVCommandTimeoutError, self._handle_command_timeout_error)
        self.register_handler(JarNotFoundError, self._handle_jar_not_found_error)
        self.register_handler(CircuitBreakerOpenError, self._handle_circuit_breaker_open_error)
        # Register common system error handlers
        self.register_handler(FileNotFoundError, self._handle_file_not_found_error)
        # Register generic handlers - order matters: specific before generic
        self.register_handler(RVAndroidError, self._handle_generic_error)
        # Register catch-all handler last as ultimate fallback
        self.register_handler(Exception, self._handle_generic_exception)

        self._logger.debug(f"Registered built-in error handlers, total callbacks: {len(self._error_callbacks)}")

    def register_error_callback(self, callback: Callable[[Exception, Optional[Dict[str, Any]]], None]) -> None:
        """
        Register a callback to be called when errors are handled.
        
        Args:
            callback: Function to call when errors occur. Receives (error, context) parameters.
        """
        if callback not in self._error_callbacks:
            self._error_callbacks.append(callback)
            self._logger.debug(
                f"Registered error callback: {callback.__name__ if hasattr(callback, '__name__') else 'unnamed callback'}")

    def unregister_error_callback(self, callback: Callable[[Exception, Optional[Dict[str, Any]]], None]) -> bool:
        """
        Unregister an error callback.
        
        Args:
            callback: Function to remove from callbacks
            
        Returns:
            True if callback was found and removed, False otherwise
        """
        try:
            self._error_callbacks.remove(callback)
            self._logger.debug(
                f"Unregistered error callback: {callback.__name__ if hasattr(callback, '__name__') else 'unnamed callback'}")
            return True
        except ValueError:
            return False

    def register_handler(self, error_type: Type[Exception],
                         handler: Callable[[Exception, Optional[Dict[str, Any]]], bool]):
        """
        Register a handler for a specific error type.
        
        Note: Simplified implementation - currently only supports callback registration.

        Args:
            error_type: The type of exception to handle
            handler: Function to call when this error occurs, should return True if handled
        """
        # Create handler wrapper with exact type matching and unique ID
        import uuid
        callback_id = str(uuid.uuid4())[:8]

        def handler_wrapper(e, c):
            if type(e) == error_type:  # Exact type matching
                return handler(e, c)
            return None

        # Check if this exact handler is already registered to avoid duplicates  
        handler_name = getattr(handler, '__name__', f'handler_{id(handler)}')
        handler_signature = f"{error_type.__name__}:{handler_name}"
        if not hasattr(self, '_registered_handlers'):
            self._registered_handlers = set()

        if handler_signature not in self._registered_handlers:
            self._error_callbacks.append(handler_wrapper)
            self._registered_handlers.add(handler_signature)
            self._logger.debug(f"Registered handler for {error_type.__name__}")
        else:
            self._logger.debug(f"Handler for {error_type.__name__} already registered, skipping")

    def handle_error(self, error: Exception, context: Optional[Union[Dict[str, Any], 'ErrorContext']] = None) -> bool:
        """
        Handle an error using registered handlers with enhanced context support.

        Args:
            error: The exception to handle
            context: Additional context information (dict, ErrorContext, or None for auto-introspection)

        Returns:
            True if the error was handled, False otherwise
        """
        # Process context - support both legacy dict and new ErrorContext
        if hasattr(context, 'build') and callable(getattr(context, 'build')):
            # ErrorContext instance
            final_context = context.build(frame_offset=3)
        elif isinstance(context, dict):
            # Legacy dictionary context
            final_context = context
        elif context is None:
            # Use empty context when none provided (maintain backward compatibility)
            final_context = {}
        else:
            final_context = {}

        return self._handle_error_internal(error, final_context)

    def _handle_error_internal(self, error: Exception, context: Dict[str, Any]) -> bool:
        """
        Internal error handling implementation
        """
        error_type = type(error)
        error_name = error_type.__name__

        # Update error counts for tracking patterns
        self._error_counts[error_name] = self._error_counts.get(error_name, 0) + 1

        # Record in history for analysis
        self._add_to_history(error, context)

        # Log the error with context
        self._log_error(error, context)

        # Execute callbacks (simplified error handling)
        handled = False
        for callback in self._error_callbacks:
            try:
                result = callback(error, context)
                if result is True:
                    handled = True
                    self._logger.debug(f"Error handled by callback")
                    break
            except Exception as e:
                self._logger.error(f"Error in callback: {e}")

        if not handled:
            self._logger.debug(f"No handler successfully processed {error_name}")

        return handled

    def _add_to_history(self, error: Exception, context: Optional[Dict[str, Any]]):
        """Add error to history with timestamp and context."""
        entry = {
            "timestamp": time.time(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }

        # Keep the history at a reasonable size
        if len(self._error_history) >= 100:
            self._error_history.pop(0)

        self._error_history.append(entry)

    def _log_error(self, error: Exception, context: Optional[Dict[str, Any]]):
        """Log an error with appropriate detail level based on error type."""
        # For timeout errors, log less verbosely (no stacktrace)
        if isinstance(error, (RVToolTimeoutError, RVCommandTimeoutError)):
            self._logger.error(f"Error: {error}")
            return

        # For other errors, log with full detail
        if isinstance(error, RVAndroidError) and error.cause:
            self._logger.error(f"Error: {error.message} caused by: {error.cause}", exc_info=error.cause)
        else:
            self._logger.error(f"Error: {error}", exc_info=error)

    def _notify_error_callbacks(self, error: Exception, context: Optional[Dict[str, Any]]) -> None:
        """Notify all registered error callbacks."""
        for callback in self._error_callbacks:
            try:
                callback(error, context)
            except Exception as e:
                self._logger.error(
                    f"Error in error callback {callback.__name__ if hasattr(callback, '__name__') else 'unnamed callback'}: {e}")

    def _handle_generic_error(self, error: RVAndroidError, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Default handler for RVAndroid errors.

        Args:
            error: The error
            context: Optional context information

        Returns:
            True if handled, False otherwise
        """
        # Log that we've seen this error but don't claim to have handled it specifically
        self._logger.info(f"Recorded RVAndroid error: {error.message}")
        return False

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about errors encountered.

        Returns:
            Dictionary with error statistics
        """
        return {
            "error_counts": self._error_counts.copy(),
            "recovery_attempts": self._recovery_attempts.copy(),
            "recent_errors": self._error_history[-10:] if self._error_history else []
        }

    def clear_statistics(self) -> None:
        """Clear all error statistics."""
        self._error_counts = {}
        self._error_history = []
        self._recovery_attempts = {}

    # Enhanced error handling methods for hybrid approach

    def handle_error_with_introspection(self, error: Exception, **context_kwargs) -> bool:
        """
        Handle error with automatic introspection and minimal context.
        
        This method provides a cleaner alternative to the standard handle_error
        by automatically capturing caller information and reducing boilerplate.
        
        Args:
            error: The exception to handle
            **context_kwargs: Additional context data to include
            
        Returns:
            True if the error was handled, False otherwise
            
        Usage:
        ```python
        # Instead of building verbose context manually:
        try:
            risky_operation()
        except Exception as e:
            self.error_handler.handle_error_with_introspection(e, task_id=task.id)
        ```
        """
        # Use simplified context without ErrorContext dependency
        context = context_kwargs.copy()
        return self._handle_error_internal(error, context)

    def create_context(self, **kwargs) -> Dict[str, Any]:
        """
        Create a new context dictionary for error handling.
        
        Args:
            **kwargs: Initial context data
            
        Returns:
            Context dictionary for error handling
            
        Usage:
        ```python
        try:
            risky_operation()
        except Exception as e:
            context = self.error_handler.create_context(
                component="TaskExecutor",
                phase="execution",
                task_id=task.id
            )
            self.error_handler.handle_error(e, context)
        ```
        """
        return kwargs.copy()

    @contextmanager
    def error_context(self, **context_kwargs):
        """
        Context manager for automatic error handling within a scope.
        
        Args:
            **context_kwargs: Context information to apply to any errors
            
        Usage:
        ```python
        with self.error_handler.error_context(component="TaskExecutor", phase="setup"):
            # Code that might raise exceptions - automatically handled
            risky_operation()
        ```
        """
        try:
            yield
        except Exception as e:
            # Use simplified context without ErrorContext dependency
            context = context_kwargs.copy()
            if not self._handle_error_internal(e, context):
                # Re-raise if not handled
                raise

    @staticmethod
    def handle_errors(
            component: Optional[str] = None,
            phase: Optional[str] = None,
            reraise: bool = False,
            **context_kwargs
    ):
        """
        Decorator for automatic error handling (Spring-like approach).
        
        Args:
            component: Component name for error context
            phase: Phase/operation name for error context
            reraise: Whether to re-raise unhandled exceptions
            **context_kwargs: Additional context data
        
        Usage:
        ```python
        @ErrorHandler.handle_errors(component="TaskExecutor", phase="execution")
        def execute_task(self, task):
            # Method implementation - errors automatically handled
            return self._do_execution(task)
        
        @ErrorHandler.handle_errors(component="DataProcessor", reraise=True)
        def critical_operation(self):
            # Errors logged but re-raised for critical operations
            pass
        ```
        """

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Get error handler instance
                handler = ErrorHandler.get_instance()

                # Build context with provided values (simplified)
                context = context_kwargs.copy()
                if component:
                    context['component'] = component
                if phase:
                    context['phase'] = phase

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    handled = handler._handle_error_internal(e, context)

                    if handled:
                        handler._logger.debug(f"Error handled by decorator in {func.__name__}")
                        # Check if we should re-raise even after successful handling
                        if reraise:
                            raise  # Re-raise even though handled when reraise=True
                        else:
                            return None  # Suppress exception when reraise=False
                    elif reraise:
                        raise  # Not handled but reraise requested
                    else:
                        # Log that error was not handled but don't re-raise when reraise=False
                        handler._logger.warning(f"Unhandled error in {func.__name__}: {e}")
                        # Suppress the exception since reraise=False
                        return None

            return wrapper

        return decorator

    # Enhanced exception hierarchy handlers

    def _handle_task_error(self, error: RVTaskError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle task-related errors with enhanced context."""
        self._logger.info(f"Task error recorded: {error.message}")
        if hasattr(error, 'task_id') and error.task_id:
            self._logger.info(f"Task ID: {error.task_id}")
        return False  # Allow further handling

    def _handle_tool_not_found_error(self, error: ToolNotFoundError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle tool not found errors with enhanced context."""
        self._logger.error(f"Tool not found: {error.message}")
        if hasattr(error, 'tool_name') and error.tool_name:
            self._logger.error(f"Requested tool: {error.tool_name}")
        return True  # Error fully handled - don't propagate further

    def _handle_tool_registration_error(self, error: ToolRegistrationError,
                                        context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle tool registration errors with enhanced context."""
        self._logger.error(f"Tool registration failed: {error.message}")
        if hasattr(error, 'tool_name') and error.tool_name:
            self._logger.error(f"Tool: {error.tool_name}")
        return True  # Error fully handled - don't propagate further

    def _handle_tool_variant_error(self, error: ToolVariantError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle tool variant errors with enhanced context."""
        self._logger.error(f"Tool variant error: {error.message}")
        if hasattr(error, 'tool_name') and error.tool_name:
            self._logger.error(f"Tool: {error.tool_name}")
        if hasattr(error, 'variant_name') and error.variant_name:
            self._logger.error(f"Variant: {error.variant_name}")
        return True  # Error fully handled - don't propagate further

    def _handle_plugin_error(self, error: PluginError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle plugin system errors with enhanced context."""
        self._logger.error(f"Plugin error: {error.message}")
        if hasattr(error, 'plugin_name') and error.plugin_name:
            self._logger.error(f"Plugin: {error.plugin_name}")
        return True  # Error fully handled - don't propagate further

    def _handle_tool_timeout_error(self, error: RVToolTimeoutError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle tool timeout errors with enhanced context."""
        self._logger.info(f"Tool timeout (expected): {error.message}")
        if hasattr(error, 'tool_name') and error.tool_name:
            self._logger.info(f"Tool: {error.tool_name}")
        if hasattr(error, 'timeout_seconds') and error.timeout_seconds:
            self._logger.info(f"Timeout duration: {error.timeout_seconds}s")
        return True  # Successfully handled - timeouts are expected

    def _handle_tool_execution_error(self, error: RVToolExecutionError,
                                     context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle tool execution errors with context logging.
        
        Processes RVToolExecutionError instances by logging error details
        and context information. Returns True to indicate successful handling
        and prevent "No handler successfully processed" messages.
        
        Args:
            error: RVToolExecutionError instance with execution failure details
            context: Optional context dictionary with additional error information
            
        Returns:
            True indicating error was processed successfully
        """
        # Extract essential context for debugging
        tool_name = getattr(error, 'tool_name', context.get('tool_name', 'unknown') if context else 'unknown')
        error_type = type(error).__name__
        exit_code = getattr(error, 'exit_code', None)

        # Log with essential context - balance between simplicity and useful debugging info
        self._logger.error(
            f"Tool execution failed: {error.message}",
            extra={
                'tool_name': tool_name,
                'error_type': error_type,
                'exit_code': exit_code
            }
        )

        # Return True to indicate successful error handling
        return True

    def _handle_tool_error(self, error: RVToolError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle tool-related errors with enhanced context."""
        self._logger.info(f"Tool error recorded: {error.message}")
        if hasattr(error, 'tool_name') and error.tool_name:
            self._logger.info(f"Tool: {error.tool_name}")
        return False  # Allow further handling

    def _handle_experiment_error(self, error: RVExperimentError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle experiment-related errors with enhanced context."""
        self._logger.info(f"Experiment error recorded: {error.message}")
        if hasattr(error, 'experiment_id') and error.experiment_id:
            self._logger.info(f"Experiment ID: {error.experiment_id}")
        return False  # Allow further handling

    def _handle_parsing_error(self, error: RVParsingError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle parsing-related errors with enhanced context."""
        self._logger.info(f"Parsing error recorded: {error.message}")
        if hasattr(error, 'parser_type') and error.parser_type:
            self._logger.info(f"Parser: {error.parser_type}")
        return False  # Allow further handling

    def _handle_prompt_error(self, error: RVPromptError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle prompt framework related errors with enhanced context."""
        self._logger.info(f"Prompt error recorded: {error.message}")
        if hasattr(error, 'strategy_name') and error.strategy_name:
            self._logger.info(f"Strategy: {error.strategy_name}")
        return True  # Successfully handled

    def _handle_llm_error(self, error: RVLLMError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle LLM-related errors with enhanced context."""
        self._logger.info(f"LLM error recorded: {error.message}")
        if hasattr(error, 'model_name') and error.model_name:
            self._logger.info(f"Model: {error.model_name}")
        return True  # Successfully handled
    
    def _handle_llm_connection_error(self, error: RVLLMConnectionError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle LLM connection failures with enhanced context."""
        self._logger.error(f"LLM connection failed: {error.message}")
        if hasattr(error, 'model_name') and error.model_name:
            self._logger.error(f"Model: {error.model_name}")
        if hasattr(error, 'provider') and error.provider:
            self._logger.error(f"Provider: {error.provider}")
        return True  # Successfully handled
    
    def _handle_llm_model_error(self, error: RVLLMModelError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle LLM model loading/generation errors with enhanced context."""
        self._logger.error(f"LLM model error: {error.message}")
        if hasattr(error, 'model_name') and error.model_name:
            self._logger.error(f"Model: {error.model_name}")
        if hasattr(error, 'operation') and error.operation:
            self._logger.error(f"Operation: {error.operation}")
        return True  # Successfully handled
    
    def _handle_llm_provider_error(self, error: RVLLMProviderError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle LLM provider-specific errors with enhanced context."""
        self._logger.error(f"LLM provider error: {error.message}")
        if hasattr(error, 'model_name') and error.model_name:
            self._logger.error(f"Model: {error.model_name}")
        if hasattr(error, 'provider') and error.provider:
            self._logger.error(f"Provider: {error.provider}")
        if hasattr(error, 'status_code') and error.status_code:
            self._logger.error(f"Status Code: {error.status_code}")
        return True  # Successfully handled
    
    def _handle_llm_configuration_error(self, error: RVLLMConfigurationError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle LLM configuration validation errors with enhanced context."""
        self._logger.error(f"LLM configuration error: {error.message}")
        if hasattr(error, 'model_name') and error.model_name:
            self._logger.error(f"Model: {error.model_name}")
        if hasattr(error, 'config_field') and error.config_field:
            self._logger.error(f"Configuration Field: {error.config_field}")
        return True  # Successfully handled
    
    def _handle_llm_template_error(self, error: RVLLMTemplateError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle LLM template processing errors with enhanced context."""
        self._logger.error(f"LLM template error: {error.message}")
        if hasattr(error, 'strategy_name') and error.strategy_name:
            self._logger.error(f"Strategy: {error.strategy_name}")
        if hasattr(error, 'template_name') and error.template_name:
            self._logger.error(f"Template: {error.template_name}")
        return True  # Successfully handled

    def _handle_validation_error(self, error: RVValidationError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle validation-related errors with enhanced context."""
        self._logger.warning(f"Validation error recorded: {error.message}")
        if hasattr(error, 'field_name') and error.field_name:
            self._logger.warning(f"Field: {error.field_name}")
        return True  # Successfully handled

    def _handle_command_validation_error(self, error: CommandValidationError,
                                         context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle command validation errors with specific context."""
        self._logger.error(f"Command validation error: {error.message}")
        if hasattr(error, 'field_name') and error.field_name:
            self._logger.error(f"Invalid command field: {error.field_name}")
        # Check for common command issues and suggest fixes
        if context and 'command' in context:
            self._logger.error(f"Failed command: {context['command']}")
        return True  # Successfully handled

    def _handle_logcat_validation_error(self, error: LogcatValidationError,
                                        context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle logcat validation errors with specific context."""
        self._logger.error(f"Logcat validation error: {error.message}")
        if hasattr(error, 'field_name') and error.field_name:
            self._logger.error(f"Invalid logcat field: {error.field_name}")
        # Check for common logcat configuration issues
        if context:
            if 'tags' in context:
                self._logger.error(f"Failed tags: {context['tags']}")
            if 'output_file' in context:
                self._logger.error(f"Failed output file: {context['output_file']}")
        return True  # Successfully handled

    def _handle_event_processing_error(self, error: EventProcessingError,
                                       context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle event processing errors with specific context."""
        self._logger.error(f"Event processing error: {error.message}")
        if hasattr(error, 'event_type') and error.event_type:
            self._logger.error(f"Failed event type: {error.event_type}")
        # Check for common event processing issues
        if context:
            if 'channel' in context:
                self._logger.error(f"Event channel: {context['channel']}")
            if 'handler_count' in context:
                self._logger.error(f"Available handlers: {context['handler_count']}")
            if 'queue_size' in context:
                self._logger.error(f"Queue size: {context['queue_size']}")
        return True  # Successfully handled

    def _handle_file_not_found_error(self, error: FileNotFoundError, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle FileNotFoundError with context-aware response.
        
        ### Handling Strategy:
        - For file verification operations (e.g., check_if_instrumented): treat as expected behavior
        - For critical file operations: log as warning and let caller handle
        - Provides consistent behavior across all modules
        
        Args:
            error: The FileNotFoundError
            context: Optional context information
            
        Returns:
            True if handled gracefully, False if should propagate
        """
        if context:
            operation = context.get('operation', '')
            component = context.get('component', 'unknown')

            # Handle expected cases where file absence is normal
            expected_operations = [
                'check_if_instrumented',  # APK may not exist yet
                'check_if_exists',  # General existence checks
                'verify_file',  # File verification operations
                'get_file_hash',  # Hash calculation for optional files
            ]

            if any(op in operation.lower() for op in expected_operations):
                self._logger.debug(f"File not found during {operation} in {component} (expected): {error.filename}")
                return True  # Handle gracefully - this is expected behavior

            # For other operations, log as warning but don't handle
            self._logger.warning(f"File not found during {operation} in {component}: {error.filename}")

        else:
            # No context - log as warning
            self._logger.warning(f"File not found: {error.filename or str(error)}")

        return False  # Don't handle - let caller decide

    def _handle_command_timeout_error(self, error: RVCommandTimeoutError,
                                      context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle command timeout errors at the infrastructure level.
        
        Command timeouts are expected behavior for long-running tool executions
        and should be converted to appropriate tool-level timeout exceptions.
        
        Args:
            error: The RVCommandTimeoutError
            context: Optional context information
            
        Returns:
            False to allow conversion to tool-level timeout exceptions
        """
        self._logger.debug(f"Command timeout detected: {error.message}")
        if hasattr(error, 'timeout_seconds') and error.timeout_seconds:
            self._logger.debug(f"Timeout duration: {error.timeout_seconds}s")
        if hasattr(error, 'command') and error.command:
            self._logger.debug(f"Command: {error.command}")

        # Log context if available
        if context:
            component = context.get('component', 'unknown')
            self._logger.debug(f"Component: {component}")

        return False  # Let it propagate to be converted to tool timeout

    def _handle_jar_not_found_error(self, error: JarNotFoundError, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle JAR file resolution failures in tool execution.
        
        JAR resolution failures indicate missing tool dependencies and should
        provide detailed information for troubleshooting installation issues.
        
        Args:
            error: The JarNotFoundError
            context: Optional context information
            
        Returns:
            False to propagate as tool execution error
        """
        self._logger.error(f"JAR resolution failed: {error.message}")
        if hasattr(error, 'jar_name') and error.jar_name:
            self._logger.error(f"Missing JAR: {error.jar_name}")
        if hasattr(error, 'search_paths') and error.search_paths:
            self._logger.error(f"Searched {len(error.search_paths)} paths:")
            for path in error.search_paths:
                self._logger.error(f"  - {path}")

        # Log context if available
        if context:
            component = context.get('component', 'unknown')
            tool_name = context.get('tool_name', 'unknown')
            self._logger.error(f"Tool: {tool_name}, Component: {component}")

        return False  # Let it propagate as tool execution error

    def _handle_circuit_breaker_open_error(self, error: CircuitBreakerOpenError,
                                           context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle circuit breaker open state errors in command execution.
        
        Circuit breaker open errors indicate that a command has been blocked
        due to repeated failures, providing protection against cascading failures.
        
        Args:
            error: The CircuitBreakerOpenError
            context: Optional context information
            
        Returns:
            True to handle gracefully and prevent execution
        """
        self._logger.warning(f"Circuit breaker protection activated: {error.message}")
        if hasattr(error, 'command_signature') and error.command_signature:
            self._logger.warning(f"Blocked command: {error.command_signature}")
        if hasattr(error, 'failure_count') and error.failure_count:
            self._logger.warning(f"Previous failures: {error.failure_count}")

        # Log context if available
        if context:
            component = context.get('component', 'unknown')
            tool_name = context.get('tool_name', 'unknown')
            self._logger.warning(f"Tool: {tool_name}, Component: {component}")

        return True  # Handle gracefully - circuit breaker is protective behavior

    def _handle_generic_exception(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle any unhandled exception as a catch-all fallback.
        
        ### Handling Strategy:
        - Provides graceful degradation for any unhandled exception type
        - Logs error details with context for debugging
        - Does NOT handle validation errors, configuration errors, or ValueError (let them propagate)
        - Does NOT handle exceptions in decorator context with reraise=True (let them propagate)
        - Should be registered last to catch exceptions not handled by specific handlers
        
        Args:
            error: Any exception that wasn't handled by specific handlers
            context: Optional context information
            
        Returns:
            True if handled gracefully (allows continuation), False if should propagate
        """
        error_type = type(error).__name__

        # Don't handle validation errors - let them propagate to tests/callers
        critical_error_types = [
            ValueError,
            ConfigurationError,
            RVValidationError,
            CommandValidationError,
            LogcatValidationError
        ]

        # Add PydanticValidationError if available
        try:
            from pydantic_core import ValidationError as PydanticValidationError
            critical_error_types.append(PydanticValidationError)
        except ImportError:
            pass  # pydantic_core not available

        critical_error_types = tuple(critical_error_types)

        if isinstance(error, critical_error_types):
            self._logger.debug(f"Not handling {error_type} - allowing propagation")
            return False  # Don't handle - let it propagate

        if context:
            component = context.get('component', 'unknown')
            operation = context.get('operation', 'unknown')
            phase = context.get('phase', 'unknown')

            # If this is from a decorator context (ToolFactory decorators should propagate)
            # Don't handle exceptions in decorator context - let them be re-raised
            decorator_phases = ['tool_copy', 'tool_creation', 'tool_instantiation']
            if phase in decorator_phases:
                self._logger.debug(f"Not handling {error_type} in decorator phase '{phase}' - allowing propagation")
                return False  # Let decorator handle reraise logic

            # Check if this is a non-critical operation that can continue
            non_critical_operations = [
                'static_analysis',
                'file_copy',
                'artifact_validation',
                'optional_processing'
            ]

            if any(op in operation.lower() for op in non_critical_operations):
                self._logger.warning(f"Non-critical {error_type} in {component} during {operation}: {error}")
                return True  # Handle gracefully - allow continuation

            # For other operations, log as error but don't handle critical errors
            self._logger.error(f"Unhandled {error_type} in {component} during {operation}: {error}")

        else:
            # No context - log as generic error
            self._logger.error(f"Unhandled {error_type}: {error}")

        # For non-critical errors, handle to prevent system crashes
        return True


# Global convenience functions for easy access to enhanced features

def error_context(**context_kwargs):
    """
    Global context manager function for scoped error handling.
    
    Usage:
    ```python
    with error_context(component="TaskExecutor", phase="setup"):
        # Code block - errors automatically handled
        risky_operation()
    ```
    """
    handler = ErrorHandler.get_instance()
    return handler.error_context(**context_kwargs)
