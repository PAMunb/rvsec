# rvandroid/experiment/event/bus.py
import logging
import threading
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional

from rvandroid.experiment.event.handler import EventHandler
from rvandroid.experiment.event.models import Event, EventType, TaskEvent, ExperimentEvent, AnalysisEvent


class EventBus:
    """
    Central event bus for managing event subscriptions and publishing.

    A robust, thread-safe publish-subscribe event management system for decoupled communication across the rvandroid framework.

    ### Architectural Decisions:
    - Implements a sophisticated pub/sub pattern with high flexibility
    - Provides thread-safe event handling and subscription management
    - Supports multiple event types and granular filtering
    - Enables dynamic event registration and unregistration
    - Maintains a configurable event history for traceability

    ### Role in the System:
    - Serves as the central communication backbone for the experimental framework
    - Facilitates loose coupling between different system components
    - Enables real-time event tracking and notification
    - Supports complex event-driven workflows across experiment lifecycle
    - Provides a standardized mechanism for inter-component communication
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'EventBus':
        """
        Get the singleton instance of the event bus.

        Returns:
            EventBus instance
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = EventBus()
            return cls._instance

    def __init__(self):
        """Initialize the event bus"""
        self.logger = logging.getLogger(__name__)
        self.subscribers: Dict[EventType, List[EventHandler]] = {}
        self.history: List[Event] = []
        self.max_history_size = 1000
        self._lock = threading.Lock()

        # Initialize empty subscriber lists for each event type
        for event_type in EventType:
            self.subscribers[event_type] = []

    def subscribe(self, event_type: EventType,
                  callback: Callable[[Event], None],
                  filter_fn: Optional[Callable[[Event], bool]] = None) -> int:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
            filter_fn: Optional function to filter events

        Returns:
            Handler ID for unsubscribing
        """
        handler = EventHandler(callback, filter_fn)
        with self._lock:
            self.subscribers[event_type].append(handler)

        self.logger.debug(
            f"Subscribed to {event_type.name}, "
            f"total subscribers: {len(self.subscribers[event_type])}"
        )
        return id(handler)

    def subscribe_many(self, event_types: List[EventType],
                       callback: Callable[[Event], None],
                       filter_fn: Optional[Callable[[Event], bool]] = None) -> List[int]:
        """
        Subscribe to multiple event types.

        Args:
            event_types: List of event types to subscribe to
            callback: Function to call when any of the events occur
            filter_fn: Optional function to filter events

        Returns:
            List of handler IDs for unsubscribing
        """
        return [self.subscribe(event_type, callback, filter_fn)
                for event_type in event_types]

    def unsubscribe_by_handler(self, event_type: EventType, handler_id: int) -> bool:
        """
        Unsubscribe from an event type by handler ID.

        Args:
            event_type: Type of event to unsubscribe from
            handler_id: Handler ID returned from subscribe

        Returns:
            True if handler was found and removed, False otherwise
        """
        with self._lock:
            for i, handler in enumerate(self.subscribers[event_type]):
                if id(handler) == handler_id:
                    self.subscribers[event_type].pop(i)
                    self.logger.debug(f"Unsubscribed from {event_type.name}")
                    return True
        return False

    def unsubscribe_all(self, callback: Callable[[Event], None]) -> int:
        """
        Unsubscribe a callback from all event types.

        Args:
            callback: Callback to unsubscribe

        Returns:
            Number of subscriptions removed
        """
        count = 0
        with self._lock:
            for event_type in EventType:
                handlers = self.subscribers[event_type]
                self.subscribers[event_type] = [
                    h for h in handlers if h.callback != callback
                ]
                count += len(handlers) - len(self.subscribers[event_type])

        self.logger.debug(f"Unsubscribed {count} handlers")
        return count

    def publish(self, event: Event) -> int:
        """
        Publish an event to all subscribers.

        Args:
            event: Event to publish

        Returns:
            Number of handlers that processed the event
        """
        if not isinstance(event, Event):
            self.logger.error(f"Invalid event object: {event}")
            return 0

        self.logger.debug(f"Publishing event: {event}")

        # Add to history
        with self._lock:
            self.history.append(event)
            # Trim history if needed
            if len(self.history) > self.max_history_size:
                self.history = self.history[-self.max_history_size:]

        # Notify subscribers
        handlers = self.subscribers.get(event.type, [])
        count = 0

        for handler in handlers:
            try:
                if handler.handle(event):
                    count += 1
            except Exception as e:
                self.logger.error(f"Error in event handler: {e}", exc_info=True)

        return count

    # Helper methods for publishing common event types

    def publish_task_event(self,
                           event_type: EventType,
                           task_id: int,
                           task_config: Dict[str, Any] = None,
                           details: Dict[str, Any] = None,
                           source: str = None) -> int:
        """
        Create and publish a task event.

        Args:
            event_type: Event type
            task_id: Task ID
            task_config: Optional task configuration
            details: Optional additional details
            source: Optional event source

        Returns:
            Number of handlers that processed the event
        """
        event = TaskEvent(
            type=event_type,
            task_id=task_id,
            task_config=task_config or {},
            details=details or {},
            source=source
        )
        return self.publish(event)

    def publish_experiment_event(self,
                                 event_type: EventType,
                                 experiment_id: str,
                                 message: str = "",
                                 affected_tasks: List[int] = None,
                                 source: str = None) -> int:
        """
        Create and publish an experiment event.

        Args:
            event_type: Event type
            experiment_id: Experiment ID
            message: Optional message
            affected_tasks: Optional list of affected task IDs
            source: Optional event source

        Returns:
            Number of handlers that processed the event
        """
        event = ExperimentEvent(
            type=event_type,
            experiment_id=experiment_id,
            message=message,
            affected_tasks=affected_tasks or [],
            source=source
        )
        return self.publish(event)

    def publish_analysis_event(self,
                               event_type: EventType,
                               data: Dict[str, Any] = None,
                               related_task_id: Optional[int] = None,
                               source: str = None) -> int:
        """
        Create and publish an analysis event.

        Args:
            event_type: Event type
            data: Optional analysis data
            related_task_id: Optional related task ID
            source: Optional event source

        Returns:
            Number of handlers that processed the event
        """
        event = AnalysisEvent(
            type=event_type,
            data=data or {},
            related_task_id=related_task_id,
            source=source
        )
        return self.publish(event)

    def publish_error_event(self, error: Exception, context: Optional[Dict[str, Any]] = None) -> int:
        """
        Publish an error event with details about the exception.

        Args:
            error: The exception that occurred
            context: Optional context information

        Returns:
            Number of handlers that processed the event
        """
        # Extract task ID from context if available
        task_id = None
        if context and "task_id" in context:
            task_id = context["task_id"]

        # Create error data
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }

        # If it's a known RVAndroid error, include more details
        from rvandroid.util.exceptions import RVAndroidError
        if isinstance(error, RVAndroidError):
            error_data["message"] = error.message
            if error.cause:
                error_data["cause"] = {
                    "type": type(error.cause).__name__,
                    "message": str(error.cause)
                }

        # Publish as analysis event
        return self.publish_analysis_event(
            event_type=EventType.ERROR_DETECTED,
            data=error_data,
            related_task_id=task_id,
            source="ErrorHandler"
        )

    def get_history(self,
                    event_type: Optional[EventType] = None,
                    since: Optional[datetime] = None,
                    source: Optional[str] = None,
                    task_id: Optional[int] = None,
                    limit: int = 100) -> List[Event]:
        """
        Get event history with optional filters.

        Args:
            event_type: Optional filter by event type
            since: Optional filter by timestamp
            source: Optional filter by source
            task_id: Optional filter by task ID (for TaskEvents)
            limit: Maximum number of events to return

        Returns:
            List of events matching the filters
        """
        with self._lock:
            events = self.history.copy()

        # Apply filters
        if event_type is not None:
            events = [e for e in events if e.type == event_type]

        if since is not None:
            events = [e for e in events if e.timestamp >= since]

        if source is not None:
            events = [e for e in events if e.source == source]

        if task_id is not None:
            events = [e for e in events if isinstance(e, TaskEvent) and e.task_id == task_id]

        # Sort by timestamp (newest first) and apply limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]
