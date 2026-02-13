# rv_android_core/util/error/error_handler.py
import functools
import threading
from contextlib import contextmanager
from typing import Dict, List, Callable, Any, Type, Optional, Union

from rv_android_core.util.error.exceptions import (
    RVAndroidError, RVToolError, RVToolExecutionError, RVToolTimeoutError, ToolNotFoundError,
    ToolRegistrationError, RVExperimentError, RVParsingError,
    RVValidationError, CommandValidationError, LogcatValidationError,
    EventProcessingError, ConfigurationError, RVCommandTimeoutError, JarNotFoundError
)
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ErrorHandler:
    """
    Centralized error handling system for rv-android-core.

    Provides a registry-based approach for error handler lookup and execution.
    Handlers are registered per exception type and matched by exact type. The
    handler returns True to indicate the error was fully handled (absorbed) or
    False to allow propagation.

    Two main usage patterns:
    - Decorator: @ErrorHandler.handle_errors(component="X", phase="Y")
    - Context manager: with error_handler.error_context(component="X"): ...

    This module does NOT publish events directly to maintain module independence.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ErrorHandler()
        return cls._instance

    def __init__(self):
        """Initialize the error handler."""
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            'rv_android_core.util.error.error_handler',
            {
                CONTEXT_COMPONENT: 'ErrorHandler'
            }
        )

        # Handler callbacks registered via register_handler()
        self._error_callbacks: List[Callable[[Exception, Optional[Dict[str, Any]]], None]] = []

        self._register_builtin_handlers()

    def _register_builtin_handlers(self):
        """Register built-in error handlers."""
        # Errors considered fully handled (return True, won't propagate from context manager)
        handled_types = [
            CommandValidationError, LogcatValidationError, EventProcessingError,
            RVValidationError, ToolNotFoundError, ToolRegistrationError,
            RVToolTimeoutError, RVToolExecutionError
        ]
        for error_type in handled_types:
            self.register_handler(error_type, self._handle_and_absorb)

        # Errors logged but not handled (return False, propagate from context manager)
        propagated_types = [
            RVToolError, RVExperimentError, RVParsingError,
            RVCommandTimeoutError, JarNotFoundError
        ]
        for error_type in propagated_types:
            self.register_handler(error_type, self._handle_and_propagate)

        # Special handlers with meaningful logic
        self.register_handler(FileNotFoundError, self._handle_file_not_found_error)
        self.register_handler(RVAndroidError, self._handle_generic_error)
        self.register_handler(Exception, self._handle_generic_exception)

        self._logger.debug(f"Registered built-in error handlers, total callbacks: {len(self._error_callbacks)}")

    def register_handler(self, error_type: Type[Exception],
                         handler: Callable[[Exception, Optional[Dict[str, Any]]], bool]):
        """
        Register a handler for a specific error type.

        Uses exact type matching to dispatch errors to the appropriate handler.
        Duplicate registrations (same error type + same handler function) are
        silently ignored.

        Args:
            error_type: The type of exception to handle
            handler: Function to call when this error occurs, should return True if handled
        """
        def handler_wrapper(e, c):
            if type(e) == error_type:
                return handler(e, c)
            return None

        # Prevent duplicate registrations
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
        Handle an error using registered handlers.

        Args:
            error: The exception to handle
            context: Additional context information (dict, ErrorContext, or None)

        Returns:
            True if the error was handled, False otherwise
        """
        if hasattr(context, 'build') and callable(getattr(context, 'build')):
            final_context = context.build(frame_offset=3)
        elif isinstance(context, dict):
            final_context = context
        else:
            final_context = {}

        return self._handle_error_internal(error, final_context)

    def _handle_error_internal(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Internal error handling: log the error, then iterate callbacks."""
        self._log_error(error, context)

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
            self._logger.debug(f"No handler successfully processed {type(error).__name__}")

        return handled

    def _log_error(self, error: Exception, context: Optional[Dict[str, Any]]):
        """Log an error with appropriate detail level based on error type."""
        # For timeout errors, log without stacktrace
        if isinstance(error, (RVToolTimeoutError, RVCommandTimeoutError)):
            self._logger.error(f"Error: {error}")
            return

        if isinstance(error, RVAndroidError) and error.cause:
            self._logger.error(f"Error: {error.message} caused by: {error.cause}", exc_info=error.cause)
        else:
            self._logger.error(f"Error: {error}", exc_info=error)

    # --- Generic handler methods ---

    def _handle_and_absorb(self, error, context=None):
        """Handle error and prevent further propagation."""
        return True

    def _handle_and_propagate(self, error, context=None):
        """Log error but allow propagation for higher-level handling."""
        return False

    def _handle_generic_error(self, error, context=None):
        """Default handler for RVAndroid errors."""
        self._logger.info(f"Recorded RVAndroid error: {error.message}")
        return False

    # --- Special handlers with meaningful logic ---

    def _handle_file_not_found_error(self, error: FileNotFoundError, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle FileNotFoundError with context-aware response.

        For file verification operations (e.g., check_if_instrumented), file absence
        is expected behavior and the error is absorbed. For other operations, the error
        is logged but allowed to propagate.

        Args:
            error: The FileNotFoundError
            context: Optional context information

        Returns:
            True if handled gracefully, False if should propagate
        """
        if context:
            operation = context.get('operation', '')
            component = context.get('component', 'unknown')

            expected_operations = [
                'check_if_instrumented',
                'check_if_exists',
                'verify_file',
                'get_file_hash',
            ]

            if any(op in operation.lower() for op in expected_operations):
                self._logger.debug(f"File not found during {operation} in {component} (expected): {error.filename}")
                return True

            self._logger.warning(f"File not found during {operation} in {component}: {error.filename}")
        else:
            self._logger.warning(f"File not found: {error.filename or str(error)}")

        return False

    def _handle_generic_exception(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Catch-all fallback for exceptions not matched by specific handlers.

        Critical error types (ValueError, ConfigurationError, validation errors,
        PydanticValidationError) are never absorbed -- they always propagate.
        Errors in decorator phases used by ToolFactory also propagate. Non-critical
        operations (static_analysis, file_copy, etc.) are absorbed to prevent
        system crashes.

        Args:
            error: Any exception that wasn't handled by specific handlers
            context: Optional context information

        Returns:
            True if handled gracefully (allows continuation), False if should propagate
        """
        error_type = type(error).__name__

        critical_error_types = [
            ValueError,
            ConfigurationError,
            RVValidationError,
            CommandValidationError,
            LogcatValidationError
        ]

        try:
            from pydantic_core import ValidationError as PydanticValidationError
            critical_error_types.append(PydanticValidationError)
        except ImportError:
            pass

        critical_error_types = tuple(critical_error_types)

        if isinstance(error, critical_error_types):
            self._logger.debug(f"Not handling {error_type} - allowing propagation")
            return False

        if context:
            component = context.get('component', 'unknown')
            operation = context.get('operation', 'unknown')
            phase = context.get('phase', 'unknown')

            decorator_phases = ['tool_copy', 'tool_creation', 'tool_instantiation']
            if phase in decorator_phases:
                self._logger.debug(f"Not handling {error_type} in decorator phase '{phase}' - allowing propagation")
                return False

            non_critical_operations = [
                'static_analysis',
                'file_copy',
                'artifact_validation',
                'optional_processing'
            ]

            if any(op in operation.lower() for op in non_critical_operations):
                self._logger.warning(f"Non-critical {error_type} in {component} during {operation}: {error}")
                return True

            self._logger.error(f"Unhandled {error_type} in {component} during {operation}: {error}")
        else:
            self._logger.error(f"Unhandled {error_type}: {error}")

        return True

    # --- Context manager and decorator ---

    @contextmanager
    def error_context(self, **context_kwargs):
        """
        Context manager for automatic error handling within a scope.

        Usage:
        ```python
        with error_handler.error_context(component="TaskExecutor", phase="setup"):
            risky_operation()
        ```
        """
        try:
            yield
        except Exception as e:
            context = context_kwargs.copy()
            if not self._handle_error_internal(e, context):
                raise

    @staticmethod
    def handle_errors(
            component: Optional[str] = None,
            phase: Optional[str] = None,
            reraise: bool = False,
            **context_kwargs
    ):
        """
        Decorator for automatic error handling.

        Args:
            component: Component name for error context
            phase: Phase/operation name for error context
            reraise: Whether to re-raise unhandled exceptions
            **context_kwargs: Additional context data

        Usage:
        ```python
        @ErrorHandler.handle_errors(component="TaskExecutor", phase="execution")
        def execute_task(self, task):
            return self._do_execution(task)

        @ErrorHandler.handle_errors(component="DataProcessor", reraise=True)
        def critical_operation(self):
            pass
        ```
        """

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                handler = ErrorHandler.get_instance()

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
                        if reraise:
                            raise
                        else:
                            return None
                    elif reraise:
                        raise
                    else:
                        handler._logger.warning(f"Unhandled error in {func.__name__}: {e}")
                        return None

            return wrapper

        return decorator
