# rvandroid/util/error/handler_registry.py
from typing import Dict, List, Callable, Type, Optional
import logging


class HandlerRegistry:
    """
    Registry for error handlers with type-based lookup.
    Manages the registration and retrieval of error handlers.

    ### Architectural Decisions:
    - Separates handler registration from error processing logic
    - Implements a type-based lookup system with inheritance support
    - Provides a clean interface for handler management

    ### Role in the System:
    - Maintains a catalog of error handlers by exception type
    - Supports handler lookup based on exception type hierarchy
    - Enables extensible error handling strategies
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._registry: Dict[Type[Exception], List[Callable]] = {}

    def register(self, error_type: Type[Exception],
                 handler: Callable[[Exception, Optional[Dict]], bool]) -> None:
        """
        Register a handler for a specific error type.

        Args:
            error_type: The type of exception to handle
            handler: Function to call when this error occurs, should return True if handled
        """
        if error_type not in self._registry:
            self._registry[error_type] = []

        if handler not in self._registry[error_type]:
            self._registry[error_type].append(handler)
            self.logger.debug(f"Registered handler for {error_type.__name__}")

    def find_handlers(self, error_type: Type[Exception]) -> List[Callable]:
        """
        Find all handlers that can handle this error type (including parent classes).

        Args:
            error_type: Exception type to find handlers for

        Returns:
            List of handler functions
        """
        handlers = []

        # Check for handlers for this specific type
        if error_type in self._registry:
            handlers.extend(self._registry[error_type])

        # Also check for parent class handlers (inheritance hierarchy)
        for registered_type, type_handlers in self._registry.items():
            if error_type != registered_type and issubclass(error_type, registered_type):
                handlers.extend(type_handlers)

        return handlers
   