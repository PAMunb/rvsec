# rvandroid/experiment/event_system.py
"""
Event system for experiment execution.
Provides a publish-subscribe mechanism for task events.
"""

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Any, Callable, Optional, Generic, TypeVar, Set


class EventType(Enum):
    """Event types for the experiment execution system"""
    # Task lifecycle events
    TASK_CREATED = auto()
    TASK_CONFIGURED = auto()
    TASK_STARTED = auto()
    TASK_COMPLETED = auto()
    TASK_FAILED = auto()

    # Experiment lifecycle events
    EXPERIMENT_STARTED = auto()
    EXPERIMENT_COMPLETED = auto()
    EXPERIMENT_FAILED = auto()
    EXPERIMENT_PAUSED = auto()
    EXPERIMENT_RESUMED = auto()

    # Analysis events
    COVERAGE_UPDATED = auto()
    COVERAGE_TRACKING_STARTED = auto()
    COVERAGE_TRACKING_STOPPED = auto()
    ERROR_DETECTED = auto()
    STATIC_ANALYSIS_COMPLETED = auto()

    # Environment lifecycle events
    EMULATOR_STARTED = auto()
    EMULATOR_STOPPED = auto()
    APP_INSTALLED = auto()
    TOOL_STARTED = auto()
    TOOL_STOPPED = auto()

    # Configuration events
    CONFIG_LOADED = auto()
    CONFIG_SAVED = auto()


@dataclass
class Event:
    """Base class for all events in the system"""
    type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    source: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.type.name} at {self.timestamp.isoformat()} from {self.source or 'unknown'}"


@dataclass
class TaskEvent(Event):
    """Event related to a specific task"""
    task_id: int = 0
    task_config: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.type.name} for Task {self.task_id} at {self.timestamp.isoformat()}"


@dataclass
class ExperimentEvent(Event):
    """Event related to the overall experiment"""
    experiment_id: str = ""
    affected_tasks: List[int] = field(default_factory=list)
    message: str = ""

    def __str__(self) -> str:
        return f"{self.type.name} for Experiment {self.experiment_id}: {self.message}"


@dataclass
class AnalysisEvent(Event):
    """Event related to analysis results"""
    data: Dict[str, Any] = field(default_factory=dict)
    related_task_id: Optional[int] = None

    def __str__(self) -> str:
        task_str = f" for Task {self.related_task_id}" if self.related_task_id else ""
        return f"{self.type.name}{task_str} at {self.timestamp.isoformat()}"


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


class EventBus:
    """
    Central event bus for managing event subscriptions and publishing.
    Implements a publish-subscribe (pub/sub) pattern to enable decoupled communication
    between different components of the system. Provides a thread-safe mechanism for
    registering event handlers, filtering events, and broadcasting events across the application.

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

    ### Key Considerations:
    - Manages multiple event types with type-safe handling
    - Supports sophisticated event filtering and routing
    - Implements efficient event dispatch mechanisms
    - Provides comprehensive event tracking and historical analysis
    - Ensures minimal performance overhead during event processing

    ### Integration Strategy:
    - Compatible with all experimental framework components
    - Supports dynamic event handler registration
    - Allows fine-grained event subscription and filtering
    - Provides methods for event history retrieval and analysis
    - Enables cross-component communication without direct dependencies

    ### Performance and Scalability:
    - Designed for high-performance, low-latency event dispatching
    - Supports concurrent event processing with thread-safe mechanisms
    - Configurable event history size for memory management
    - Scales efficiently across complex experimental workflows
    - Minimizes computational overhead through optimized event handling
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

    # Add this method to the EventBus class
    def publish_event(self, event_type: EventType, details: Optional[Dict[str, Any]] = None, source: str = None) -> int:
        """
        Generic method to publish an event of any type.
        Determines the appropriate event class based on the event type.

        Args:
            event_type: Type of event to publish
            details: Optional details for the event
            source: Optional source of the event

        Returns:
            Number of handlers that processed the event
        """
        # Task-related events
        if event_type in [
            EventType.TASK_CREATED, EventType.TASK_CONFIGURED,
            EventType.TASK_STARTED, EventType.TASK_COMPLETED,
            EventType.TASK_FAILED, EventType.EMULATOR_STARTED,
            EventType.EMULATOR_STOPPED, EventType.APP_INSTALLED,
            EventType.TOOL_STARTED, EventType.TOOL_STOPPED
        ]:
            return self.publish_task_event(
                event_type=event_type,
                task_id=details.get("task_id", 0),
                details=details or {},
                source=source
            )

        # Experiment-related events
        elif event_type in [
            EventType.EXPERIMENT_STARTED, EventType.EXPERIMENT_COMPLETED,
            EventType.EXPERIMENT_FAILED, EventType.EXPERIMENT_PAUSED,
            EventType.EXPERIMENT_RESUMED
        ]:
            return self.publish_experiment_event(
                event_type=event_type,
                experiment_id=details.get("experiment_id", "unknown"),
                message=details.get("message", ""),
                source=source
            )

        # Analysis-related events
        elif event_type in [
            EventType.COVERAGE_UPDATED, EventType.COVERAGE_TRACKING_STARTED,
            EventType.COVERAGE_TRACKING_STOPPED, EventType.ERROR_DETECTED,
            EventType.STATIC_ANALYSIS_COMPLETED
        ]:
            return self.publish_analysis_event(
                event_type=event_type,
                data=details or {},
                source=source
            )

        # Configuration events and default case
        else:
            event = Event(type=event_type, source=source)
            return self.publish(event)

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

    def clear_history(self) -> int:
        """
        Clear event history.

        Returns:
            Number of events cleared
        """
        with self._lock:
            count = len(self.history)
            self.history = []
            return count

    def get_subscriber_count(self, event_type: EventType) -> int:
        """
        Get the number of subscribers for an event type.

        Args:
            event_type: Event type

        Returns:
            Number of subscribers
        """
        return len(self.subscribers.get(event_type, []))

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

    # Decorator for event handlers
    def event_handler(event_type: EventType, filter_fn: Optional[Callable[[Event], bool]] = None):
        """
        Decorator for event handlers.

        Args:
            event_type: Event type to subscribe to
            filter_fn: Optional function to filter events

        Returns:
            Decorator function
        """

        def decorator(func):
            # Subscribe when the function is defined
            EventBus.get_instance().subscribe(event_type, func, filter_fn)
            return func

        return decorator

# Example usage of the event system:
# if __name__ == "__main__":
#     # Configure logging
#     logging.basicConfig(level=logging.DEBUG)
#
#     # Get event bus
#     event_bus = EventBus.get_instance()
#
#     # Define an event handler using the decorator
#     @event_handler(EventType.TASK_COMPLETED)
#     def handle_task_completed(event: TaskEvent):
#         print(f"Task {event.task_id} completed at {event.timestamp}")
#
#     # Subscribe to multiple events
#     def handle_experiment_events(event: ExperimentEvent):
#         print(f"Experiment {event.experiment_id}: {event.message}")
#
#     event_bus.subscribe_many(
#         [EventType.EXPERIMENT_STARTED, EventType.EXPERIMENT_COMPLETED],
#         handle_experiment_events
#     )
#
#     # Publish events
#     event_bus.publish_task_event(
#         EventType.TASK_COMPLETED,
#         task_id=123,
#         task_config={"timeout": 60, "tool": "droidbot"},
#         source="example"
#     )
#
#     event_bus.publish_experiment_event(
#         EventType.EXPERIMENT_STARTED,
#         experiment_id="exp-001",
#         message="Starting experiment with 10 tasks",
#         source="example"
#     )