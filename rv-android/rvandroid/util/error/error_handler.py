# rvandroid/util/error/error_handler.py
import threading
import time
from typing import Dict, List, Callable, Any, Type, Optional

from rvandroid.util.error.handler_registry import HandlerRegistry
from rvandroid.util.error.recovery_strategies import RecoveryStrategies
from rvandroid.util.exceptions import RVAndroidError, ADBError, EmulatorError, RvTimeoutError
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ErrorHandler:
    """
    Centralized error handling system for rv-android.

    ### Architectural Decisions:
    - Implements a unified approach to error management across all components
    - Delegates specific error handling to specialized strategies
    - Provides detailed error tracking, aggregation, and reporting
    - Uses a registry-based approach for handler lookup and execution

    ### Role in the System:
    - Acts as the central error management facility
    - Provides consistent error handling behavior across the framework
    - Enables error aggregation for pattern detection and reporting
    - Supports automatic recovery strategies for common failure scenarios
    - Facilitates error classification and appropriate response selection
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
        # Get standardized logger with context
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            'util.error_handler',
            {
                CONTEXT_COMPONENT: 'ErrorHandler'
            }
        )

        # Initialize handler registry
        self._registry = HandlerRegistry()

        # Importe EventBus apenas quando necessário
        # para evitar a importação circular
        self._event_bus = None

        # Error statistics and tracking
        self._error_counts: Dict[str, int] = {}
        self._error_history: List[Dict[str, Any]] = []
        self._recovery_attempts: Dict[str, int] = {}

        # Configure default error handlers
        self._configure_default_handlers()

    @property
    def event_bus(self):
        # Importação tardia (lazy import)
        if self._event_bus is None:
            try:
                from rvandroid.experiment.event.bus import EventBus
                self._event_bus = EventBus.get_instance()
            except ImportError:
                self._logger.warning("EventBus module could not be imported")
                self._event_bus = None
        return self._event_bus

    def _configure_default_handlers(self):
        """Set up default error handlers for common errors."""
        # ADB error handling
        self.register_handler(ADBError, RecoveryStrategies.handle_adb_error)

        # Emulator error handling
        self.register_handler(EmulatorError, RecoveryStrategies.handle_emulator_error)

        # Timeout error handling
        self.register_handler(RvTimeoutError, RecoveryStrategies.handle_timeout_error)

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
        self._registry.register(error_type, handler)

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
            handlers = self._registry.find_handlers(error_type)

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
                    self._logger.error(f"Error in handler: {e}")

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

    def _publish_error_event(self, error: Exception, context: Optional[Dict[str, Any]]):
        """Publish an error event to the event bus."""
        if not self.event_bus:
            return

        # Importação tardia (lazy import)
        try:
            from rvandroid.experiment.event.bus import EventType

            # Prepare event data
            event_data = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {}
            }

            # Add task_id to event if available in context
            if context and "task_id" in context:
                self.event_bus.publish_analysis_event(
                    EventType.ERROR_DETECTED,
                    data=event_data,
                    related_task_id=context["task_id"],
                    source="ErrorHandler"
                )
            else:
                self.event_bus.publish_analysis_event(
                    EventType.ERROR_DETECTED,
                    data=event_data,
                    source="ErrorHandler"
                )
        except ImportError:
            self._logger.warning("EventType could not be imported, event not published")

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
