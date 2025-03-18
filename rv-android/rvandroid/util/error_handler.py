# rvandroid/util/error_handler.py - Centralized error handling

import time
from functools import wraps
from typing import Dict, List, Callable, Any, Type

from rvandroid.util.exceptions import RVAndroidError, ADBError, EmulatorError, RvTimeoutError
from rvandroid.util.logging_manager import LoggingManager


class ErrorHandler:
    """
    The ErrorHandler class provides a centralized mechanism for handling exceptions
    and errors within the rvandroid framework. It ensures that errors are logged,
    tracked, and managed efficiently to prevent unexpected failures.

    ### Architectural Decisions:
    - Implements a structured error-handling approach to improve system resilience.
    - Supports logging of error details for debugging and post-mortem analysis.
    - Provides categorization of errors to differentiate between critical failures
      and recoverable exceptions.

    ### Role in the System:
    - Acts as a global error-handling utility, reducing redundant exception handling across modules.
    - Improves system stability by preventing unhandled exceptions from causing crashes.
    - Enhances debugging and troubleshooting by maintaining detailed error logs.
    - Supports potential integrations with external monitoring or alerting systems.
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
        self._logger = LoggingManager.get_instance().get_logger(
            'util.error_handler', {'component': 'ErrorHandler'})

        # Keep track of errors by type to detect patterns
        self._error_counts: Dict[str, int] = {}

        # Track recovery attempts
        self._recovery_attempts: Dict[str, int] = {}

        # Registry of error handlers
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

    def register_handler(self, error_type: Type[Exception], handler: Callable[[Exception], None]):
        """
        Register a handler for a specific error type.

        Args:
            error_type: The type of exception to handle
            handler: Function to call when this error occurs
        """
        if error_type not in self._error_handlers:
            self._error_handlers[error_type] = []

        if handler not in self._error_handlers[error_type]:
            self._error_handlers[error_type].append(handler)
            self._logger.debug(f"Registered handler for {error_type.__name__}")

    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> bool:
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

        # Log the error with context
        self._log_error(error, context)

        # Find and execute handlers for this error type and its parent types
        handlers = []
        for err_type, err_handlers in self._error_handlers.items():
            if isinstance(error, err_type):
                handlers.extend(err_handlers)

        # Execute handlers
        handled = False
        for handler in handlers:
            try:
                if handler(error):
                    handled = True
            except Exception as e:
                self._logger.error(f"Error in error handler: {e}")

        return handled

    def _log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log an error with detailed information."""
        ctx_str = ""
        if context:
            ctx_str = " - Context: " + ", ".join(f"{k}={v}" for k, v in context.items())

        if isinstance(error, RVAndroidError) and error.cause:
            self._logger.error(
                f"{type(error).__name__}: {error.message}{ctx_str}",
                exc_info=error.cause
            )
        else:
            self._logger.error(
                f"{type(error).__name__}: {str(error)}{ctx_str}",
                exc_info=error
            )

    def _handle_adb_error(self, error: ADBError) -> bool:
        """
        Handle ADB-related errors with retry mechanism.

        Args:
            error: The ADB error

        Returns:
            True if handled successfully, False otherwise
        """
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
            self._logger.error(f"ADB recovery failed: {e}")
            return False

    def _handle_emulator_error(self, error: EmulatorError) -> bool:
        """
        Handle emulator-related errors.

        Args:
            error: The emulator error

        Returns:
            True if handled successfully, False otherwise
        """
        self._logger.info(f"Handling emulator error: {error.message}")

        # For now, we just log the error - actual recovery would depend on specific emulator issues
        self._logger.warning("Emulator error recovery not yet implemented")
        return False

    def _handle_timeout_error(self, error: RvTimeoutError) -> bool:
        """
        Handle timeout errors.

        Args:
            error: The timeout error

        Returns:
            True if handled successfully, False otherwise
        """
        self._logger.info(f"Handling timeout error: {error.message}")

        # For now, we just log the error - more specific handling would depend on the context
        self._logger.warning("Timeout recovery not yet implemented")
        return False

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get statistics about errors encountered."""
        return {
            "error_counts": self._error_counts.copy(),
            "recovery_attempts": self._recovery_attempts.copy()
        }


# Decorator for automatic retry
def retry(max_attempts: int = 3,
          retry_exceptions: List[Type[Exception]] = None,
          delay: float = 1.0,
          backoff_factor: float = 2.0):
    """
    Decorator to automatically retry a function on specified exceptions.

    Args:
        max_attempts: Maximum number of retry attempts
        retry_exceptions: List of exception types to retry on
        delay: Initial delay between retries in seconds
        backoff_factor: Factor to increase delay with each retry

    Returns:
        Decorated function
    """
    if retry_exceptions is None:
        retry_exceptions = [ADBError, EmulatorError]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = LoggingManager.get_instance().get_logger(
                'util.error_handler.retry', {'function': func.__name__})

            current_delay = delay
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except tuple(retry_exceptions) as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        wait_time = current_delay
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed with {type(e).__name__}: {e}. "
                            f"Retrying in {wait_time:.2f}s...")

                        time.sleep(wait_time)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"All {max_attempts} attempts failed")

            # Re-raise the last exception
            raise last_exception

        return wrapper

    return decorator
