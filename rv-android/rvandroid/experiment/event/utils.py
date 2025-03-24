# rvandroid/experiment/event/utils.py
from typing import Callable

from rvandroid.experiment.event.bus import EventBus
from rvandroid.experiment.event.models import EventType, Event


def event_handler(event_type: EventType, filter_fn=None):
    """
    Decorator for event handlers.

    Args:
        event_type: Event type to subscribe to
        filter_fn: Optional function to filter events

    Returns:
        Decorator function
    """

    def decorator(func: Callable[[Event], None]):
        # Subscribe when the function is defined
        EventBus.get_instance().subscribe(event_type, func, filter_fn)
        return func

    return decorator
