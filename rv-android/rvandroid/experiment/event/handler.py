# rvandroid/experiment/event/handler.py
from typing import Callable, Optional, TypeVar, Generic
from rvandroid.experiment.event.models import Event

# Type variable for event handlers
T = TypeVar('T', bound=Event)


class EventHandler(Generic[T]):
    """Handler for specific event types"""

    def __init__(self, callback: Callable[[T], None], filter_fn: Optional[Callable[[T], bool]] = None):
        """
        Initialize the event handler.

        Args:
            callback: Function to call when event occurs
            filter_fn: Optional function to filter events
        """
        self.callback = callback
        self.filter_fn = filter_fn

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
