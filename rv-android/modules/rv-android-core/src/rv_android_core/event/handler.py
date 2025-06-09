# rvandroid/experiment/event/handler.py
from enum import IntEnum
from typing import Callable, Optional, TypeVar, Generic, Dict, Any

from rv_android_core.event.models import Event

# Type variable for event handlers
T = TypeVar('T', bound=Event)


class HandlerPriority(IntEnum):
    """Priority levels for event handlers"""
    LOW = 0
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class EventHandler(Generic[T]):
    """Handler for specific event types with priority support"""

    def __init__(self,
                 callback: Callable[[T], None],
                 filter_fn: Optional[Callable[[T], bool]] = None,
                 priority: HandlerPriority = HandlerPriority.NORMAL,
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize the event handler.

        Args:
            callback: Function to call when event occurs
            filter_fn: Optional function to filter events
            priority: Priority level for this handler
            metadata: Optional metadata associated with this handler
        """
        self.callback = callback
        self.filter_fn = filter_fn
        self.priority = priority
        self.metadata = metadata or {}

    def handle(self, event: T) -> bool:
        """
        Process an event by applying an optional filter and invoking the handler's callback.

        Checks if the event passes the optional filter function. If no filter is set or the event
        passes the filter, the handler's callback is executed.

        Args:
            event: The event to be processed and potentially handled.

        Returns:
            A boolean indicating whether the event was successfully handled.
        """
        if self.filter_fn is None or self.filter_fn(event):
            self.callback(event)
            return True
        return False

    def __lt__(self, other: 'EventHandler') -> bool:
        """
        Compare handlers based on priority for sorting.
        
        Args:
            other: Another event handler to compare with
            
        Returns:
            True if this handler has higher priority than the other
        """
        # Higher priority comes first in sorting
        return self.priority > other.priority
