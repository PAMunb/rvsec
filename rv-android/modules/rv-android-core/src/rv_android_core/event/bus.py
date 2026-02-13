"""Synchronous event bus for the RV-Android event system."""

import threading
from typing import Dict, List, Any, Callable, Optional

from rv_android_core.event.handler import EventHandler
from rv_android_core.event.models import (
    Event, EventType, EventChannel,
    TaskEvent, ExperimentEvent, CoverageEvent, MOPErrorEvent,
    TaskToolExecutionEvent, PhaseExecutionModeEvent
)
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import EventProcessingError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class EventBus:
    """Synchronous publish-subscribe event bus for decoupled communication.

    Thread-safe singleton that routes typed events through channels to
    registered handlers. All event processing is synchronous.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'EventBus':
        """Get the singleton instance of the event bus."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = EventBus()
            return cls._instance

    @classmethod
    def create_instance(cls) -> 'EventBus':
        """Create a new independent event bus instance for dependency injection."""
        return EventBus(is_singleton=False)

    def __init__(self, is_singleton=True):
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_android_core.event.bus",
            {CONTEXT_COMPONENT: "EventBus"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Channel -> EventType -> list of handlers
        self.channel_subscribers: Dict[str, Dict[EventType, List[EventHandler]]] = {}
        self._lock = threading.Lock()

        for channel in EventChannel:
            self.channel_subscribers[channel.value] = {}
            for event_type in EventType:
                self.channel_subscribers[channel.value][event_type] = []

    # ── Subscription ──────────────────────────────────────────────────

    def subscribe(self,
                  event_type: EventType,
                  callback: Callable[[Event], None],
                  filter_fn: Optional[Callable[[Event], bool]] = None,
                  channel: EventChannel = EventChannel.DEFAULT) -> int:
        """Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to.
            callback: Function to call when event occurs.
            filter_fn: Optional function to filter events.
            channel: Channel to subscribe in.

        Returns:
            Handler ID for unsubscribing.
        """
        handler = EventHandler(callback, filter_fn)

        with self._lock:
            self.channel_subscribers[channel.value][event_type].append(handler)
            self.logger.debug(
                f"Subscribed to {event_type.name} in channel {channel.value}, "
                f"total subscribers: {len(self.channel_subscribers[channel.value][event_type])}"
            )

        return id(handler)

    def subscribe_many(self,
                       event_types: List[EventType],
                       callback: Callable[[Event], None],
                       filter_fn: Optional[Callable[[Event], bool]] = None,
                       channel: EventChannel = EventChannel.DEFAULT) -> List[int]:
        """Subscribe to multiple event types.

        Args:
            event_types: List of event types to subscribe to.
            callback: Function to call when any of the events occur.
            filter_fn: Optional function to filter events.
            channel: Channel to subscribe in.

        Returns:
            List of handler IDs for unsubscribing.
        """
        return [self.subscribe(event_type, callback, filter_fn, channel)
                for event_type in event_types]

    def unsubscribe_by_handler(self, event_type: EventType, handler_id: int,
                               channel: EventChannel = EventChannel.DEFAULT) -> bool:
        """Unsubscribe from an event type by handler ID.

        Returns:
            True if handler was found and removed, False otherwise.
        """
        with self._lock:
            for i, handler in enumerate(self.channel_subscribers[channel.value][event_type]):
                if id(handler) == handler_id:
                    self.channel_subscribers[channel.value][event_type].pop(i)
                    self.logger.debug(f"Unsubscribed from {event_type.name} in channel {channel.value}")
                    return True

        return False

    def unsubscribe_all(self, callback: Callable[[Event], None],
                        channels: Optional[List[EventChannel]] = None) -> int:
        """Unsubscribe a callback from all event types.

        Args:
            callback: Callback to unsubscribe.
            channels: Optional list of channels to unsubscribe from. If None, all channels.

        Returns:
            Number of subscriptions removed.
        """
        count = 0

        with self._lock:
            if channels:
                for channel in channels:
                    if channel.value in self.channel_subscribers:
                        for event_type in EventType:
                            handlers = self.channel_subscribers[channel.value][event_type]
                            self.channel_subscribers[channel.value][event_type] = [
                                h for h in handlers if h.callback != callback
                            ]
                            count += len(handlers) - len(self.channel_subscribers[channel.value][event_type])
            else:
                for channel in self.channel_subscribers:
                    for event_type in EventType:
                        handlers = self.channel_subscribers[channel][event_type]
                        self.channel_subscribers[channel][event_type] = [
                            h for h in handlers if h.callback != callback
                        ]
                        count += len(handlers) - len(self.channel_subscribers[channel][event_type])

        self.logger.debug(f"Unsubscribed {count} handlers")
        return count

    # ── Publication ───────────────────────────────────────────────────

    @ErrorHandler.handle_errors(component="EventBus", phase="synchronous_publication")
    def publish(self, event: Event, channel: EventChannel = EventChannel.DEFAULT) -> int:
        """Publish an event synchronously to all subscribers.

        Args:
            event: Event to publish.
            channel: Channel to publish to.

        Returns:
            Number of handlers that processed the event.
        """
        if not isinstance(event, Event):
            raise EventProcessingError(f"Invalid event object: {event}", event_type=str(type(event)))

        return self._process_event_in_channel(event, channel.value)

    def _process_event_in_channel(self, event: Event, channel: str) -> int:
        """Process an event within a specific channel.

        Returns:
            Number of handlers that processed the event.
        """
        if channel not in self.channel_subscribers:
            self.logger.warning(f"Unknown channel: {channel}")
            return 0

        handlers = self.channel_subscribers[channel].get(event.type, [])

        count = 0
        for handler in handlers:
            try:
                if handler.handle(event):
                    count += 1
            except Exception as e:
                self.logger.error(f"Error in event handler (channel {channel}): {e}", exc_info=True)

        return count

    # ── Typed helper methods ──────────────────────────────────────────

    @ErrorHandler.handle_errors(component="EventBus", phase="task_event_publication")
    def publish_task_event(self, event_type: EventType, task_id: str,
                           task_config: Dict[str, Any] = None,
                           details: Dict[str, Any] = None,
                           source: str = None,
                           channel: EventChannel = EventChannel.LIFECYCLE) -> int:
        """Create and publish a task event."""
        event = TaskEvent(
            type=event_type, task_id=task_id, task_config=task_config or {},
            details=details or {}, source=source
        )
        return self.publish(event, channel)

    @ErrorHandler.handle_errors(component="EventBus", phase="experiment_event_publication")
    def publish_experiment_event(self, event_type: EventType, experiment_id: str,
                                 message: str = "", affected_tasks: List[str] = None,
                                 source: str = None,
                                 channel: EventChannel = EventChannel.LIFECYCLE) -> int:
        """Create and publish an experiment event."""
        event = ExperimentEvent(
            type=event_type, experiment_id=experiment_id, message=message,
            affected_tasks=affected_tasks or [], source=source
        )
        return self.publish(event, channel)

    @ErrorHandler.handle_errors(component="EventBus", phase="coverage_event_publication")
    def publish_coverage_event(self, event_type: EventType, task_id: str,
                               coverage_entry: Dict[str, Any] = None,
                               coverage_metrics: Dict[str, Any] = None,
                               task_config: Dict[str, Any] = None,
                               details: Dict[str, Any] = None,
                               source: str = None,
                               channel: EventChannel = EventChannel.LIFECYCLE) -> int:
        """Create and publish a coverage event with task context."""
        event = CoverageEvent(
            type=event_type, task_id=task_id,
            coverage_entry=coverage_entry, coverage_metrics=coverage_metrics,
            task_config=task_config or {}, details=details or {}, source=source
        )
        return self.publish(event, channel)

    @ErrorHandler.handle_errors(component="EventBus", phase="mop_error_event_publication")
    def publish_mop_error_event(self, event_type: EventType, task_id: str,
                                error_log: Dict[str, Any] = None,
                                task_config: Dict[str, Any] = None,
                                details: Dict[str, Any] = None, source: str = None,
                                channel: EventChannel = EventChannel.LIFECYCLE) -> int:
        """Create and publish a MOP error event with task context."""
        event = MOPErrorEvent(
            type=event_type, task_id=task_id, error_log=error_log,
            task_config=task_config or {}, details=details or {}, source=source
        )
        return self.publish(event, channel)
