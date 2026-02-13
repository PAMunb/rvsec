"""Event handler for the RV-Android event system."""

from typing import Callable, Optional, TypeVar, Generic, Any

from rv_android_core.event.models import Event

T = TypeVar('T', bound=Event)


class EventHandler(Generic[T]):
    """Handler for specific event types with optional filtering."""

    def __init__(self,
                 callback: Callable[[T], None],
                 filter_fn: Optional[Callable[[T], bool]] = None):
        self.callback = callback
        self.filter_fn = filter_fn

    def handle(self, event: T) -> bool:
        if self.filter_fn is None or self.filter_fn(event):
            self.callback(event)
            return True
        return False
