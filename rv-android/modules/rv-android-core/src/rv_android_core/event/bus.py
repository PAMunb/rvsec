"""
Event bus system for RV-Android Core.

This module provides a centralized event bus for managing event subscriptions
and publishing with thread-safe operations and priority-based processing.
"""

import concurrent.futures
import queue
import threading
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional, Union

from rv_android_core.event.handler import EventHandler, HandlerPriority
from rv_android_core.event.models import (
    Event, EventType, EventPriority, EventChannel, EventHistoryManager,
    TaskEvent, ExperimentEvent, CoverageEvent, MOPErrorEvent,
    TaskToolExecutionEvent, PhaseExecutionModeEvent
)
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import EventProcessingError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class EventBus:
    """
    Central event bus for managing event subscriptions and publishing.

    A thread-safe publish-subscribe event management system for decoupled 
    communication across the RV-Android framework.

    ### Architectural Decisions:
    - Implements pub/sub pattern with strict type safety
    - Provides thread-safe event handling and subscription management
    - Supports multiple event types with type-safe channel routing
    - Enables dynamic event registration and unregistration
    - Delegates history management to EventHistoryManager
    - Supports asynchronous event processing with priority queuing
    - Uses EventChannel enum for type-safe channel specification

    ### Role in the System:
    - Serves as the central communication backbone for the framework
    - Facilitates loose coupling between different system components
    - Enables real-time event tracking and notification
    - Supports event-driven workflows across experiment lifecycle
    - Provides mechanism for inter-component communication

    ### Key Features:
    - Type-safe event channel routing via EventChannel enum
    - Priority-based event processing with EventPriority constants
    - Memory-efficient event history management
    - Comprehensive error handling integration
    - Thread-safe subscription management
    - Asynchronous event processing with worker threads
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

    @classmethod
    def create_instance(cls) -> 'EventBus':
        """
        Create a new independent event bus instance.
        
        This method supports dependency injection by allowing the creation
        of separate event bus instances for different components.
        
        Returns:
            A new EventBus instance
        """
        return EventBus(is_singleton=False)

    def __init__(self, is_singleton=True, worker_threads=4, max_queue_size=1000):
        """
        Initialize the event bus.
        
        Args:
            is_singleton: Whether this instance is a singleton
            worker_threads: Number of worker threads for async processing
            max_queue_size: Maximum size of the event queue
        """
        # Configure logging and error handling
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_android_core.event.bus",
            {
                CONTEXT_COMPONENT: "EventBus"
            }
        )
        self.error_handler = ErrorHandler.get_instance()
        
        # Initialize event history manager
        self.history_manager = EventHistoryManager()
        
        # Initialize subscriber management
        self.channel_subscribers: Dict[str, Dict[EventType, List[EventHandler]]] = {}
        self._lock = threading.Lock()
        self._active = True

        # Create type-safe channel map
        for channel in EventChannel:
            self.channel_subscribers[channel.value] = {}
            # Initialize empty subscriber lists for each event type in each channel
            for event_type in EventType:
                self.channel_subscribers[channel.value][event_type] = []

        # Setup asynchronous processing
        self._setup_async_processing(worker_threads, max_queue_size)

    def _setup_async_processing(self, worker_threads: int, max_queue_size: int) -> None:
        """
        Set up asynchronous event processing infrastructure.
        
        Args:
            worker_threads: Number of worker threads to use
            max_queue_size: Maximum size of the event queue
        """
        self._event_queue = queue.PriorityQueue(maxsize=max_queue_size)
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=worker_threads,
            thread_name_prefix="EventBus-Worker"
        )

        # Start the event processing thread
        self._processing_thread = threading.Thread(
            target=self._process_event_queue,
            name="EventBus-QueueProcessor",
            daemon=True
        )
        self._processing_thread.start()

        self.logger.debug(f"Initialized asynchronous event processing with {worker_threads} workers")

    def _process_event_queue(self) -> None:
        """Process events from the queue in a separate thread."""
        while self._active:
            try:
                # Get the next event from the queue (blocking with timeout)
                priority, event, channel = self._event_queue.get(timeout=0.5)

                # Process the event
                self._process_event_in_channel(event, channel)

                # Mark the task as done
                self._event_queue.task_done()

            except queue.Empty:
                # No events in queue, just continue
                continue
            except Exception as e:
                self.logger.error(f"Error processing event from queue: {e}", exc_info=True)

    @ErrorHandler.handle_errors(component="EventBus", phase="event_publication")
    def _publish_base(self, event: Event, channel: str, 
                      callback: Optional[Callable] = None, 
                      priority: int = EventPriority.NORMAL) -> int:
        """
        Base method for all event publication forms with complete integration.
        
        ### Architectural Decisions:
        - Centralized validation and history management via EventHistoryManager
        - Common error handling for all publication types
        - Supports both synchronous and asynchronous processing
        - Uses EventPriority constants for consistent priority handling
        - Eliminates duplicated history logic from EventBus
        
        ### Role in the System:
        - Serves as the foundation for all publication methods
        - Ensures consistent event processing behavior
        - Delegates history management to EventHistoryManager
        - Provides unified error handling and logging
        """
        # Validation
        if not isinstance(event, Event):
            raise EventProcessingError(f"Invalid event object: {event}", event_type=str(type(event)))
        
        # Add to history via EventHistoryManager
        self.history_manager.add_event(event)
        
        # Process event
        handler_count = self._process_event_in_channel(event, channel)
        
        # Execute callback if provided
        if callback:
            try:
                callback(event, handler_count)
            except Exception as e:
                self.logger.error(f"Error in publication callback: {e}", exc_info=True)
        
        return handler_count

    def _process_event_in_channel(self, event: Event, channel: str) -> int:
        """
        Process an event within a specific channel.
        
        Args:
            event: The event to process
            channel: The channel to process in
            
        Returns:
            Number of handlers that processed the event
        """
        # Get handlers for this event type in this channel
        if channel not in self.channel_subscribers:
            self.logger.warning(f"Unknown channel: {channel}")
            return 0

        print(f"******************* _process_event_in_channel .... event={event} ... channel={channel}")

        handlers = self.channel_subscribers[channel].get(event.type, [])

        # Sort handlers by priority
        handlers.sort()

        # Process with all handlers
        count = 0
        for handler in handlers:
            try:
                if handler.handle(event):
                    count += 1
            except Exception as e:
                self.logger.error(f"Error in event handler (channel {channel}): {e}", exc_info=True)

        return count

    def subscribe(self,
                  event_type: EventType,
                  callback: Callable[[Event], None],
                  filter_fn: Optional[Callable[[Event], bool]] = None,
                  priority: HandlerPriority = HandlerPriority.NORMAL,
                  channel: EventChannel = EventChannel.DEFAULT) -> int:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
            filter_fn: Optional function to filter events
            priority: Priority for this handler
            channel: Channel to subscribe in (strict EventChannel enum)

        Returns:
            Handler ID for unsubscribing
        """
        handler = EventHandler(callback, filter_fn, priority=priority)

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
                       priority: HandlerPriority = HandlerPriority.NORMAL,
                       channel: EventChannel = EventChannel.DEFAULT) -> List[int]:
        """
        Subscribe to multiple event types.

        Args:
            event_types: List of event types to subscribe to
            callback: Function to call when any of the events occur
            filter_fn: Optional function to filter events
            priority: Priority for this handler
            channel: Channel to subscribe in (strict EventChannel enum)

        Returns:
            List of handler IDs for unsubscribing
        """
        return [self.subscribe(event_type, callback, filter_fn, priority, channel)
                for event_type in event_types]

    def unsubscribe_by_handler(self, event_type: EventType, handler_id: int,
                               channel: EventChannel = EventChannel.DEFAULT) -> bool:
        """
        Unsubscribe from an event type by handler ID.

        Args:
            event_type: Type of event to unsubscribe from
            handler_id: Handler ID returned from subscribe
            channel: Channel to unsubscribe from (strict EventChannel enum)

        Returns:
            True if handler was found and removed, False otherwise
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
        """
        Unsubscribe a callback from all event types.

        Args:
            callback: Callback to unsubscribe
            channels: Optional list of channels to unsubscribe from (if None, unsubscribes from all)

        Returns:
            Number of subscriptions removed
        """
        count = 0

        with self._lock:
            # Unsubscribe from specified channels
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
                # Unsubscribe from all channels
                for channel in self.channel_subscribers:
                    for event_type in EventType:
                        handlers = self.channel_subscribers[channel][event_type]
                        self.channel_subscribers[channel][event_type] = [
                            h for h in handlers if h.callback != callback
                        ]
                        count += len(handlers) - len(self.channel_subscribers[channel][event_type])

        self.logger.debug(f"Unsubscribed {count} handlers")
        return count

    @ErrorHandler.handle_errors(component="EventBus", phase="synchronous_publication")
    def publish(self, event: Event, channel: EventChannel = EventChannel.DEFAULT) -> int:
        """Publish an event to all subscribers synchronously."""
        return self._publish_base(event, channel.value)

    @ErrorHandler.handle_errors(component="EventBus", phase="asynchronous_publication")
    def publish_async(self, event: Event, 
                      channel: EventChannel = EventChannel.DEFAULT, 
                      priority: int = EventPriority.NORMAL) -> None:
        """
        Publish an event asynchronously using priority queue with EventPriority constants.
        
        ### Priority Queue Behavior:
        - Lower priority values are processed first (EventPriority.CRITICAL = 0)
        - Events with same priority are processed in FIFO order
        - Uses queue.PriorityQueue for thread-safe priority handling
        - Standard priority levels defined in EventPriority class
        
        ### Architectural Decisions:
        - Priority queue ensures critical events are processed first
        - Thread-safe implementation supports concurrent publishing
        - Queue overflow handling prevents system instability
        - Event ordering maintained within priority levels
        - EventPriority constants eliminate magic numbers
        
        Args:
            event: Event to publish
            channel: Channel to publish to (strict EventChannel enum)
            priority: Event priority using EventPriority constants
        """
        # Add to history via EventHistoryManager
        self.history_manager.add_event(event)
        
        try:
            self._event_queue.put((priority, event, channel.value))
        except queue.Full:
            raise EventProcessingError("Event queue is full", event_type=event.type.name)

    @ErrorHandler.handle_errors(component="EventBus", phase="callback_publication")
    def publish_with_callback(self, event: Event, 
                              callback: Callable[[Event, int], None],
                              channel: EventChannel = EventChannel.DEFAULT) -> None:
        """Publish an event and call the provided callback with the result."""
        def _publish_and_callback():
            count = self._publish_base(event, channel.value)
            callback(event, count)
        
        self._thread_pool.submit(_publish_and_callback)

    # Type-safe helper methods for publishing specific event types

    @ErrorHandler.handle_errors(component="EventBus", phase="task_event_publication")
    def publish_task_event(self, event_type: EventType, task_id: str, 
                           task_config: Dict[str, Any] = None, 
                           details: Dict[str, Any] = None,
                           source: str = None, async_mode: bool = False,
                           channel: EventChannel = EventChannel.LIFECYCLE,
                           priority: int = EventPriority.NORMAL) -> Union[int, None]:
        """Create and publish a task event with strict type safety."""
        event = TaskEvent(
            type=event_type, task_id=task_id, task_config=task_config or {},
            details=details or {}, source=source
        )
        
        if async_mode:
            self.publish_async(event, channel, priority)
            return None
        else:
            return self.publish(event, channel)

    @ErrorHandler.handle_errors(component="EventBus", phase="experiment_event_publication")
    def publish_experiment_event(self, event_type: EventType, experiment_id: str,
                                 message: str = "", affected_tasks: List[str] = None,
                                 source: str = None, async_mode: bool = False,
                                 channel: EventChannel = EventChannel.LIFECYCLE,
                                 priority: int = EventPriority.NORMAL) -> Union[int, None]:
        """Create and publish an experiment event with strict type safety."""
        event = ExperimentEvent(
            type=event_type, experiment_id=experiment_id, message=message,
            affected_tasks=affected_tasks or [], source=source
        )
        
        if async_mode:
            self.publish_async(event, channel, priority)
            return None
        else:
            return self.publish(event, channel)

    @ErrorHandler.handle_errors(component="EventBus", phase="coverage_event_publication")
    def publish_coverage_event(self, event_type: EventType, task_id: str,
                               coverage_entry: Dict[str, Any] = None,
                               coverage_metrics: Dict[str, Any] = None,
                               task_config: Dict[str, Any] = None, 
                               details: Dict[str, Any] = None,
                               source: str = None, async_mode: bool = False,
                               channel: EventChannel = EventChannel.LIFECYCLE,
                               priority: int = EventPriority.NORMAL) -> Union[int, None]:
        """Create and publish a coverage event with task context."""
        event = CoverageEvent(
            type=event_type, task_id=task_id, 
            coverage_entry=coverage_entry, coverage_metrics=coverage_metrics,
            task_config=task_config or {}, details=details or {}, source=source
        )
        
        if async_mode:
            self.publish_async(event, channel, priority)
            return None
        else:
            return self.publish(event, channel)

    @ErrorHandler.handle_errors(component="EventBus", phase="mop_error_event_publication")
    def publish_mop_error_event(self, event_type: EventType, task_id: str,
                                error_log: Dict[str, Any] = None,
                                task_config: Dict[str, Any] = None,
                                details: Dict[str, Any] = None, source: str = None,
                                async_mode: bool = False, 
                                channel: EventChannel = EventChannel.LIFECYCLE,
                                priority: int = EventPriority.HIGH) -> Union[int, None]:
        """Create and publish a MOP error event with task context."""
        event = MOPErrorEvent(
            type=event_type, task_id=task_id, error_log=error_log,
            task_config=task_config or {}, details=details or {}, source=source
        )
        
        if async_mode:
            self.publish_async(event, channel, priority)
            return None
        else:
            return self.publish(event, channel)

    def get_history(self,
                    event_type: Optional[EventType] = None,
                    since: Optional[datetime] = None,
                    source: Optional[str] = None,
                    task_id: Optional[str] = None,
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
        return self.history_manager.get_events(event_type, since, source, task_id, limit)

    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return self.history_manager.get_statistics()

    def shutdown(self, wait_for_completion: bool = True) -> None:
        """
        Shut down the event bus and its worker threads.
        
        Args:
            wait_for_completion: Whether to wait for all queued events to be processed
        """
        self.logger.info("Shutting down EventBus")

        # Set active flag to false to stop processing thread
        self._active = False

        if wait_for_completion:
            # Wait for all queued events to be processed
            self._event_queue.join()

        # Shutdown thread pool
        self._thread_pool.shutdown(wait=wait_for_completion)

        # Wait for processing thread to terminate
        if self._processing_thread.is_alive():
            self._processing_thread.join(timeout=2.0)

        self.logger.info("EventBus shutdown complete")