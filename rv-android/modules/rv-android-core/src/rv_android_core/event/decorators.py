# rvandroid/experiment/event/decorators.py
"""
Decorators for working with events.

This module provides decorators that simplify common event operations,
such as publishing events when methods are called and subscribing
methods to specific events.
"""

import functools
from typing import Callable, TypeVar, Optional, Dict, Any, Union, List

from rv_android_core.event.bus import EventBus
from rv_android_core.event.handler import HandlerPriority
from rv_android_core.event.models import Event, EventType
from rv_android_core.event.provider import EventBusProvider

F = TypeVar('F', bound=Callable)
T = TypeVar('T')


def publish_event(event_type: EventType,
                  get_source: Optional[Callable[[Any], str]] = None,
                  get_details: Optional[Callable[[Any, Any], Dict[str, Any]]] = None,
                  channel: str = EventBus.DEFAULT_CHANNEL,
                  async_mode: bool = False,
                  event_bus_provider: Callable[[], EventBus] = EventBusProvider.get_default_bus) -> Callable[[F], F]:
    """
    Decorator to publish an event after a function is called.
    
    This decorator wraps a function to automatically publish an event after
    the function is called. It provides a declarative way to integrate
    event publishing into existing code with minimal changes.
    
    Args:
        event_type: EventType to publish
        get_source: Optional function to extract the source from the function's self parameter
        get_details: Optional function to extract event details from function args/kwargs
        channel: Channel to publish to (defaults to DEFAULT_CHANNEL)
        async_mode: Whether to publish asynchronously
        event_bus_provider: Function providing the event bus to use
        
    Returns:
        Decorated function that publishes an event after execution
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Call the original function
            result = func(*args, **kwargs)

            # Build event details
            details = {}
            source = None

            if get_source and args:
                source = get_source(args[0])

            if get_details:
                details = get_details(args, kwargs)

            # Get the event bus
            event_bus = event_bus_provider()

            # Create a generic event
            event = Event(type=event_type, source=source)

            # Publish the event
            if async_mode:
                event_bus.publish_async(event, channel=channel)
            else:
                event_bus.publish(event, channel=channel)

            return result

        return wrapper

    return decorator


def subscribe_to(event_types: Union[EventType, List[EventType]],
                 filter_fn: Optional[Callable[[Event], bool]] = None,
                 priority: HandlerPriority = HandlerPriority.NORMAL,
                 channel: str = EventBus.DEFAULT_CHANNEL,
                 event_bus_provider: Callable[[], EventBus] = EventBusProvider.get_default_bus) -> Callable[[F], F]:
    """
    Decorator to subscribe a function to events.
    
    This decorator subscribes a function to one or more event types,
    automatically creating an event handler that delegates to the function.
    It provides a declarative way to define event handlers.
    
    Args:
        event_types: EventType(s) to subscribe to
        filter_fn: Optional function to filter events
        priority: Priority for this handler
        channel: Channel to subscribe in (defaults to DEFAULT_CHANNEL)
        event_bus_provider: Function providing the event bus to use
        
    Returns:
        Decorated function that is subscribed to the specified events
    """
    if not isinstance(event_types, list):
        event_types = [event_types]

    def decorator(cls_or_func: F) -> F:
        # Subscribe to events
        event_bus = event_bus_provider()
        for event_type in event_types:
            event_bus.subscribe(
                event_type=event_type,
                callback=cls_or_func,
                filter_fn=filter_fn,
                priority=priority,
                channel=channel
            )

        # Return original function/class unchanged
        return cls_or_func

    return decorator
