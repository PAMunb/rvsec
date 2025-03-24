# rvandroid/util/error/handler_registry.py - With suggested improvements
import logging
from typing import Dict, List, Callable, Type, Optional


class HandlerRegistry:
    """
    Registry for error handlers with type-based lookup.
    Manages the registration and retrieval of error handlers.

    ### Architectural Decisions:
    - Separates handler registration from error processing logic
    - Implements a type-based lookup system with inheritance support
    - Provides a clean interface for handler management
    """

    def __init__(self):
        """Initialize the handler registry."""
        self.logger = logging.getLogger(__name__)
        self._registry: Dict[Type[Exception], List[Callable]] = {}

    def register(self, error_type: Type[Exception],
                 handler: Callable[[Exception, Optional[Dict]], bool]) -> None:
        """
        Register a handler for a specific error type.

        Args:
            error_type: The type of exception to handle
            handler: Function to call when this error occurs, should return True if handled

        Raises:
            TypeError: If error_type is not an Exception class or handler is not callable
        """
        # Validate error type is an Exception class
        if not isinstance(error_type, type) or not issubclass(error_type, Exception):
            raise TypeError(f"Error type must be an Exception class, got {error_type}")

        # Validate handler is callable
        if not callable(handler):
            raise TypeError(f"Handler must be callable, got {handler}")

        if error_type not in self._registry:
            self._registry[error_type] = []

        # Prevent duplicate handlers
        if handler not in self._registry[error_type]:
            self._registry[error_type].append(handler)

    def find_handlers(self, error_type: Type[Exception]) -> List[Callable]:
        """
        Find all handlers that can handle this error type (including parent classes).

        Args:
            error_type: Exception type to find handlers for

        Returns:
            List of handler functions
        """
        handlers = []

        # Check inheritance hierarchy from most specific to most general
        for registered_type, type_handlers in self._registry.items():
            # Check if the error type is the exact registered type or a subclass
            if error_type == registered_type or issubclass(error_type, registered_type):
                handlers.extend(type_handlers)

        return handlers
