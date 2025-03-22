# rvandroid/util/error_handler.py
import os
import time
from contextlib import contextmanager
from functools import wraps
from typing import Dict, List, Callable, Any, Type, Optional

from rvandroid.experiment.event_system import EventBus, EventType
from rvandroid.util.exceptions import RVAndroidError, ADBError, EmulatorError, RvTimeoutError
from rvandroid.util.logging_manager import LoggingManager


class ErrorHandler:
    """
    Centralized error handling system for rv-android.

    ### Architectural Decisions:
    - Implements a unified approach to error management across all components
    - Supports customizable error handling strategies and recovery mechanisms
    - Provides detailed error tracking, aggregation, and reporting
    - Enables component-specific error handlers with fallback to default handlers

    ### Role in the System:
    - Acts as the central error management facility
    - Provides consistent error handling behavior across the framework
    - Enables error aggregation for pattern detection and reporting
    - Supports automatic recovery strategies for common failure scenarios
    - Facilitates error classification and appropriate response selection
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = ErrorHandler()
        return cls._instance

    def __init__(self):
        """Initialize the error handler."""
        # Get standardized logger with context
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            'util.error_handler',
            {
                LoggingManager.CONTEXT_COMPONENT: 'ErrorHandler'
            }
        )

        # Event bus for publishing errors
        self._event_bus = EventBus.get_instance()

        # Error statistics and tracking
        self._error_counts: Dict[str, int] = {}
        self._error_history: List[Dict[str, Any]] = []
        self._recovery_attempts: Dict[str, int] = {}

        # Registry of error handlers for different exception types
        self._error_handlers: Dict[Type[Exception], List[Callable]] = {}

        # Configure default error handlers
        self._configure_default_handlers()

    def _configure_default_handlers(self):
        """Set up default error handlers for common errors."""
        # ADB error handling
        self.register_handler(ADBError, self._handle_adb_error)

        # Emulator error handling
        self.register_handler(EmulatorError, self._handle_emulator_error)

        # Timeout error handling
        self.register_handler(RvTimeoutError, self._handle_timeout_error)

        # General RVAndroid error
        self.register_handler(RVAndroidError, self._handle_generic_error)

    def register_handler(self, error_type: Type[Exception],
                         handler: Callable[[Exception, Optional[Dict[str, Any]]], bool]):
        """
        Register a handler for a specific error type.

        Args:
            error_type: The type of exception to handle
            handler: Function to call when this error occurs, should return True if handled
        """
        if error_type not in self._error_handlers:
            self._error_handlers[error_type] = []

        if handler not in self._error_handlers[error_type]:
            self._error_handlers[error_type].append(handler)
            self._logger.debug(f"Registered handler for {error_type.__name__}")

    def handle_error(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle an error using registered handlers.

        Args:
            error: The exception to handle
            context: Additional context information

        Returns:
            True if the error was handled, False otherwise
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

            # Publish error event
            self._publish_error_event(error, context)

            # Find and execute handlers for this error type and its parent types
            handlers = self._find_handlers(error_type)

            # Execute handlers
            handled = False
            for handler in handlers:
                try:
                    self._logger.debug(f"Trying handler for {error_name}")
                    if handler(error, context):
                        handled = True
                        self._logger.debug(
                            f"Error handled by {handler.__name__ if hasattr(handler, '__name__') else 'unnamed handler'}")
                        # Once an error is handled, we can stop (unless we want multiple handlers)
                        break
                except Exception as e:
                    self._logger.error(LoggingManager.LOG_ERROR.format(operation="error handler", error=str(e)))

            if not handled:
                self._logger.debug(f"No handler successfully processed {error_name}")

            return handled

    def _find_handlers(self, error_type: Type[Exception]) -> List[Callable]:
        """
        Find all handlers that can handle this error type (including parent classes).

        Args:
            error_type: Exception type to find handlers for

        Returns:
            List of handler functions
        """
        handlers = []
        # Check for handlers for this specific type
        if error_type in self._error_handlers:
            handlers.extend(self._error_handlers[error_type])

        # Also check for parent class handlers (inheritance hierarchy)
        for registered_type, type_handlers in self._error_handlers.items():
            if error_type != registered_type and issubclass(error_type, registered_type):
                handlers.extend(type_handlers)

        return handlers

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
            self._logger.error(LoggingManager.LOG_ERROR.format(
                operation=error.message if hasattr(error, 'message') else "operation",
                error=str(error.cause)
            ), exc_info=error.cause)
        else:
            self._logger.error(LoggingManager.LOG_ERROR.format(
                operation="processing",
                error=str(error)
            ), exc_info=error)

    def _publish_error_event(self, error: Exception, context: Optional[Dict[str, Any]]):
        """Publish an error event to the event bus."""
        if not self._event_bus:
            return

        # Prepare event data
        event_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }

        # Add task_id to event if available in context
        if context and "task_id" in context:
            self._event_bus.publish_analysis_event(
                EventType.ERROR_DETECTED,
                data=event_data,
                related_task_id=context["task_id"],
                source="ErrorHandler"
            )
        else:
            self._event_bus.publish_analysis_event(
                EventType.ERROR_DETECTED,
                data=event_data,
                source="ErrorHandler"
            )

    def _handle_adb_error(self, error: ADBError, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle ADB-related errors with retry mechanism.

        Args:
            error: The ADB error
            context: Optional context information

        Returns:
            True if handled successfully, False otherwise
        """
        with self._logger.with_context(phase="adb_error_recovery"):
            self._logger.info(f"Attempting to recover from ADB error: {error.message}")

            # Track recovery attempts for this error message
            key = f"adb:{error.message}"
            attempts = self._recovery_attempts.get(key, 0)

            # Limit recovery attempts
            if attempts >= 3:
                self._logger.warning(f"Too many ADB recovery attempts for: {error.message}")
                return False

            # Update attempt count
            self._recovery_attempts[key] = attempts + 1

            # Try to restart ADB server
            try:
                from rvandroid.commands.command import Command

                # Kill ADB server
                kill_cmd = Command("adb", ["kill-server"])
                kill_cmd.invoke()
                self._logger.info("ADB server killed")

                # Wait a moment
                time.sleep(2)

                # Start ADB server
                start_cmd = Command("adb", ["start-server"])
                start_cmd.invoke()
                self._logger.info("ADB server restarted")

                # Wait for devices
                devices_cmd = Command("adb", ["devices"])
                devices_cmd.invoke()

                self._logger.info("ADB recovery successful")
                return True

            except Exception as e:
                self._logger.error(LoggingManager.LOG_ERROR.format(
                    operation="ADB recovery",
                    error=str(e)
                ))
                return False

    def _handle_emulator_error(self, error: EmulatorError, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle emulator-related errors.

        Args:
            error: The emulator error
            context: Optional context information

        Returns:
            True if handled successfully, False otherwise
        """
        with self._logger.with_context(phase="emulator_error_recovery"):
            self._logger.info(f"Handling emulator error: {error.message}")

            # Check if we have a device ID in the context
            device_id = None
            if context and "device_id" in context:
                device_id = context["device_id"]

            try:
                # Try to kill any existing emulator processes
                from rvandroid.commands.command import Command

                # Kill running emulator instance if we have a device ID
                if device_id:
                    kill_cmd = Command("adb", ["-s", device_id, "emu", "kill"])
                    kill_cmd.invoke()
                    self._logger.info(f"Emulator {device_id} killed")
                else:
                    # General emulator cleanup
                    kill_all_cmd = Command("pkill", ["-f", "emulator"])
                    kill_all_cmd.invoke()
                    self._logger.info("All emulator processes terminated")

                return True
            except Exception as e:
                self._logger.error(LoggingManager.LOG_ERROR.format(
                    operation="emulator recovery",
                    error=str(e)
                ))
                return False

    def _handle_timeout_error(self, error: RvTimeoutError, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Handle timeout errors.

        Args:
            error: The timeout error
            context: Optional context information

        Returns:
            True if handled successfully, False otherwise
        """
        with self._logger.with_context(phase="timeout_error_recovery"):
            self._logger.info(f"Handling timeout error: {error.message}")

            # Examine context to determine timeout type
            if context and "process" in context:
                # Handle process timeout
                process = context["process"]
                try:
                    # Try to terminate the process
                    import signal
                    if hasattr(process, "pid"):
                        os.kill(process.pid, signal.SIGTERM)
                        self._logger.info(f"Process {process.pid} terminated due to timeout")
                        return True
                except Exception as e:
                    self._logger.error(LoggingManager.LOG_ERROR.format(
                        operation="process termination",
                        error=str(e)
                    ))

            # Log unhandled timeout
            self._logger.warning(f"No specific handling for timeout error: {error.message}")
            return False

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

# Decorator for automatic retry
def retry(max_attempts: int = 3,
          retry_exceptions: List[Type[Exception]] = None,
          delay: float = 1.0,
          backoff_factor: float = 2.0,
          log_retries: bool = True):
    """
    Decorator to automatically retry a function on specified exceptions.

    Args:
        max_attempts: Maximum number of retry attempts
        retry_exceptions: List of exception types to retry on
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay with each retry
        log_retries: Whether to log retry attempts

    Returns:
        Decorated function
    """
    if retry_exceptions is None:
        retry_exceptions = [ADBError, EmulatorError]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger from LoggingManager
            logger = LoggingManager.get_instance().get_logger(
                'util.error_handler.retry',
                {'function': func.__name__}
            )

            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except tuple(retry_exceptions) as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        wait_time = current_delay
                        if log_retries:
                            logger.warning(
                                f"Attempt {attempt + 1}/{max_attempts} failed with {type(e).__name__}: {e}. "
                                f"Retrying in {wait_time:.2f}s..."
                            )

                        time.sleep(wait_time)
                        current_delay *= backoff_factor
                    else:
                        if log_retries:
                            logger.error(f"All {max_attempts} attempts failed")

            # Re-raise the last exception
            raise last_exception

        return wrapper

    return decorator

# Context manager for error handling
@contextmanager
def handle_errors(context: Optional[Dict[str, Any]] = None):
    """
    Context manager for handling errors with the central ErrorHandler.

    Args:
        context: Optional context information for the error

    Yields:
        Nothing

    Example:
        ```
        with handle_errors({"task_id": task.id}):
            # Code that might raise exceptions
            process_task(task)
        ```
    """
    handler = ErrorHandler.get_instance()
    try:
        yield
    except Exception as e:
        handler.handle_error(e, context)
        raise  # Re-raise the exception after handling
