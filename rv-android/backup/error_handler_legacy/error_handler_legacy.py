# rvandroid/util/error/error_handler.py
import functools
import threading
import time
from contextlib import contextmanager
from typing import Dict, List, Callable, Any, Type, Optional, Union

# Using simplified error handling
from rv_android_core.util.exceptions import (
    RVAndroidError, ADBError, EmulatorError, RvTimeoutError,
    RVTaskError, RVTaskExecutionError, RVTaskConfigurationError, RVTaskTimeoutError,
    RVToolError, RVToolExecutionError, RVToolConfigurationError,
    RVExperimentError, RVExperimentSetupError, RVExperimentExecutionError,
    RVParsingError, RVLLMError, RVPromptError
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
        with cls._lock:
            if cls._instance is None:
                cls._instance = ErrorHandler()
            return cls._instance

    def __init__(self):
        """Initialize the error handler."""
        print(f"DEBUG: Creating ErrorHandler instance, current instance: {ErrorHandler._instance}")
        
        # Get standardized logger with context
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            'util.error_handler',
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
        self.register_handler(RVTaskError, self._handle_task_error)
        self.register_handler(RVToolError, self._handle_tool_error)
        self.register_handler(RVExperimentError, self._handle_experiment_error)
        self.register_handler(RVParsingError, self._handle_parsing_error)
        self.register_handler(RVPromptError, self._handle_prompt_error)
        self.register_handler(RVLLMError, self._handle_llm_error)
        # Register generic handler last as fallback
        self.register_handler(RVAndroidError, self._handle_generic_error)
        
        self._logger.debug(f"Registered built-in error handlers, total callbacks: {len(self._error_callbacks)}")

    def register_error_callback(self, callback: Callable[[Exception, Optional[Dict[str, Any]]], None]) -> None:
        """
        Register a callback to be called when errors are handled.
        
        Args:
            callback: Function to call when errors occur. Receives (error, context) parameters.
        """
        if callback not in self._error_callbacks:
            self._error_callbacks.append(callback)
            self._logger.debug(f"Registered error callback: {callback.__name__ if hasattr(callback, '__name__') else 'unnamed callback'}")
    
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
            self._logger.debug(f"Unregistered error callback: {callback.__name__ if hasattr(callback, '__name__') else 'unnamed callback'}")
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
        # Use exact type matching to avoid duplicate handling in inheritance hierarchy
        self._error_callbacks.append(lambda e, c: handler(e, c) if type(e) == error_type else None)

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

        # Create a contextual logger for this specific error
        with self._logger.with_context(error_type=error_name, **({} if context is None else context)):
            # Log the error with context
            self._log_error(error, context)

            # Notify registered callbacks
            self._notify_error_callbacks(error, context)

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
        """Log an error with detailed information."""
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
                self._logger.error(f"Error in error callback {callback.__name__ if hasattr(callback, '__name__') else 'unnamed callback'}: {e}")

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
                    
                    if not handled and reraise:
                        raise
                    elif not handled:
                        # Log that error was not handled but don't re-raise
                        handler._logger.warning(f"Unhandled error in {func.__name__}: {e}")
                        return None  # Return None instead of re-raising
                    # If handled, just continue without raising
            return wrapper
        return decorator
    
    # Enhanced exception hierarchy handlers
    
    def _handle_task_error(self, error: RVTaskError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle task-related errors with enhanced context."""
        self._logger.info(f"Task error recorded: {error.message}")
        if hasattr(error, 'task_id') and error.task_id:
            self._logger.info(f"Task ID: {error.task_id}")
        return False  # Allow further handling
    
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
        return False  # Allow further handling
    
    def _handle_llm_error(self, error: RVLLMError, context: Optional[Dict[str, Any]] = None) -> bool:
        """Handle LLM-related errors with enhanced context."""
        self._logger.info(f"LLM error recorded: {error.message}")
        if hasattr(error, 'model_name') and error.model_name:
            self._logger.info(f"Model: {error.model_name}")
        return False  # Allow further handling


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
