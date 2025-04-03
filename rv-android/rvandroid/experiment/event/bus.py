# rvandroid/experiment/event/bus.py
import logging
import threading
import queue
import concurrent.futures
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional, Set, Union

from rvandroid.experiment.event.handler import EventHandler, HandlerPriority
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
    - Supports asynchronous event processing with priority queuing
    - Provides dedicated event channels for different system components

    ### Role in the System:
    - Serves as the central communication backbone for the experimental framework
    - Facilitates loose coupling between different system components
    - Enables real-time event tracking and notification
    - Supports complex event-driven workflows across experiment lifecycle
    - Provides a standardized mechanism for inter-component communication
    """

    _instance = None
    _lock = threading.Lock()

    # Event channels for specialized system aspects
    SYSTEM_CHANNEL = "system"
    LIFECYCLE_CHANNEL = "lifecycle"
    ANALYSIS_CHANNEL = "analysis"
    ERROR_CHANNEL = "error"
    USER_CHANNEL = "user"
    
    # Default channel for events without a specified channel
    DEFAULT_CHANNEL = "default"

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
        self.logger = logging.getLogger(__name__)
        self.channel_subscribers: Dict[str, Dict[EventType, List[EventHandler]]] = {}
        self.history: List[Event] = []
        self.max_history_size = 1000
        self._lock = threading.Lock()
        self._active = True
        
        # Create channel map
        for channel in [self.SYSTEM_CHANNEL, self.LIFECYCLE_CHANNEL, self.ANALYSIS_CHANNEL, 
                        self.ERROR_CHANNEL, self.USER_CHANNEL, self.DEFAULT_CHANNEL]:
            self.channel_subscribers[channel] = {}
            
        # Initialize empty subscriber lists for each event type in each channel
        for channel in self.channel_subscribers:
            for event_type in EventType:
                self.channel_subscribers[channel][event_type] = []
            
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
                if channel:
                    self._process_event_in_channel(event, channel)
                else:
                    self._process_event(event)
                    
                # Mark the task as done
                self._event_queue.task_done()
                
            except queue.Empty:
                # No events in queue, just continue
                continue
            except Exception as e:
                self.logger.error(f"Error processing event from queue: {e}", exc_info=True)
    
    def _process_event(self, event: Event) -> int:
        """
        Process an event synchronously through the default channel.
        
        Args:
            event: The event to process
            
        Returns:
            Number of handlers that processed the event
        """
        # Process through the default channel
        return self._process_event_in_channel(event, self.DEFAULT_CHANNEL)
    
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
                  channel: str = DEFAULT_CHANNEL) -> int:
        """
        Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
            filter_fn: Optional function to filter events
            priority: Priority for this handler
            channel: Channel to subscribe in (defaults to DEFAULT_CHANNEL)

        Returns:
            Handler ID for unsubscribing
        """
        handler = EventHandler(callback, filter_fn, priority=priority)
        
        with self._lock:
            if channel not in self.channel_subscribers:
                self.logger.warning(f"Unknown channel: {channel}, defaulting to {self.DEFAULT_CHANNEL}")
                channel = self.DEFAULT_CHANNEL
                
            self.channel_subscribers[channel][event_type].append(handler)
            self.logger.debug(
                f"Subscribed to {event_type.name} in channel {channel}, "
                f"total subscribers: {len(self.channel_subscribers[channel][event_type])}"
            )
                
        return id(handler)

    def subscribe_many(self, 
                       event_types: List[EventType],
                       callback: Callable[[Event], None],
                       filter_fn: Optional[Callable[[Event], bool]] = None,
                       priority: HandlerPriority = HandlerPriority.NORMAL,
                       channel: str = DEFAULT_CHANNEL) -> List[int]:
        """
        Subscribe to multiple event types.

        Args:
            event_types: List of event types to subscribe to
            callback: Function to call when any of the events occur
            filter_fn: Optional function to filter events
            priority: Priority for this handler
            channel: Channel to subscribe in (defaults to DEFAULT_CHANNEL)

        Returns:
            List of handler IDs for unsubscribing
        """
        return [self.subscribe(event_type, callback, filter_fn, priority, channel)
                for event_type in event_types]

    def unsubscribe_by_handler(self, event_type: EventType, handler_id: int, 
                               channel: str = DEFAULT_CHANNEL) -> bool:
        """
        Unsubscribe from an event type by handler ID.

        Args:
            event_type: Type of event to unsubscribe from
            handler_id: Handler ID returned from subscribe
            channel: Channel to unsubscribe from (defaults to DEFAULT_CHANNEL)

        Returns:
            True if handler was found and removed, False otherwise
        """
        with self._lock:
            if channel not in self.channel_subscribers:
                return False
                
            for i, handler in enumerate(self.channel_subscribers[channel][event_type]):
                if id(handler) == handler_id:
                    self.channel_subscribers[channel][event_type].pop(i)
                    self.logger.debug(f"Unsubscribed from {event_type.name} in channel {channel}")
                    return True
                    
        return False

    def unsubscribe_all(self, callback: Callable[[Event], None], 
                        channels: Optional[List[str]] = None) -> int:
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
                    if channel in self.channel_subscribers:
                        for event_type in EventType:
                            handlers = self.channel_subscribers[channel][event_type]
                            self.channel_subscribers[channel][event_type] = [
                                h for h in handlers if h.callback != callback
                            ]
                            count += len(handlers) - len(self.channel_subscribers[channel][event_type])
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

    def publish(self, event: Event, channel: str = DEFAULT_CHANNEL) -> int:
        """
        Publish an event to all subscribers synchronously.

        Args:
            event: Event to publish
            channel: Channel to publish to (defaults to DEFAULT_CHANNEL)

        Returns:
            Number of handlers that processed the event
        """
        if not isinstance(event, Event):
            self.logger.error(f"Invalid event object: {event}")
            return 0

        self.logger.debug(f"Publishing event: {event} in channel {channel}")

        # Add to history
        with self._lock:
            self.history.append(event)
            # Trim history if needed
            if len(self.history) > self.max_history_size:
                self.history = self.history[-self.max_history_size:]

        # Process the event
        return self._process_event_in_channel(event, channel)

    def publish_async(self, event: Event, 
                     channel: str = DEFAULT_CHANNEL,
                     priority: int = 0) -> None:
        """
        Publish an event asynchronously.
        
        The event will be added to a queue and processed by worker threads.
        
        Args:
            event: Event to publish
            channel: Channel to publish to (defaults to DEFAULT_CHANNEL)
            priority: Priority of this event (lower numbers = higher priority)
        """
        if not isinstance(event, Event):
            self.logger.error(f"Invalid event object for async publishing: {event}")
            return
            
        self.logger.debug(f"Queuing async event: {event} in channel {channel}")
        
        # Add to history
        with self._lock:
            self.history.append(event)
            # Trim history if needed
            if len(self.history) > self.max_history_size:
                self.history = self.history[-self.max_history_size:]
                
        # Add to the processing queue
        try:
            self._event_queue.put((priority, event, channel))
        except queue.Full:
            self.logger.error("Event queue is full, discarding event")

    def publish_with_callback(self, event: Event, 
                             callback: Callable[[Event, int], None],
                             channel: str = DEFAULT_CHANNEL) -> None:
        """
        Publish an event and call the provided callback with the result.
        
        Args:
            event: Event to publish
            callback: Function to call with (event, handler_count) after processing
            channel: Channel to publish to (defaults to DEFAULT_CHANNEL)
        """
        if not isinstance(event, Event):
            self.logger.error(f"Invalid event object for callback publishing: {event}")
            return
            
        # Submit the task to the thread pool
        def _publish_and_callback():
            # Process the event
            count = self._process_event_in_channel(event, channel)
                
            # Call the callback with the result
            try:
                callback(event, count)
            except Exception as e:
                self.logger.error(f"Error in publish callback: {e}", exc_info=True)
        
        # Add to history
        with self._lock:
            self.history.append(event)
            # Trim history if needed
            if len(self.history) > self.max_history_size:
                self.history = self.history[-self.max_history_size:]
                
        # Submit to thread pool
        self._thread_pool.submit(_publish_and_callback)

    # Helper methods for publishing common event types

    def publish_task_event(self,
                           event_type: EventType,
                           task_id: str,  # Changed from int to str for UUID support
                           task_config: Dict[str, Any] = None,
                           details: Dict[str, Any] = None,
                           source: str = None,
                           async_mode: bool = False,
                           channel: Optional[str] = LIFECYCLE_CHANNEL) -> Union[int, None]:
        """
        Create and publish a task event.

        Args:
            event_type: Event type
            task_id: Task ID (UUID as string)
            task_config: Optional task configuration
            details: Optional additional details
            source: Optional event source
            async_mode: Whether to publish asynchronously
            channel: Optional channel to publish to (defaults to LIFECYCLE_CHANNEL)

        Returns:
            Number of handlers that processed the event, or None if async
        """
        event = TaskEvent(
            type=event_type,
            task_id=task_id,
            task_config=task_config or {},
            details=details or {},
            source=source
        )
        
        if async_mode:
            self.publish_async(event, channel)
            return None
        else:
            return self.publish(event, channel)

    def publish_experiment_event(self,
                                 event_type: EventType,
                                 experiment_id: str,
                                 message: str = "",
                                 affected_tasks: List[str] = None,  # Changed to str for UUID support
                                 source: str = None,
                                 async_mode: bool = False,
                                 channel: Optional[str] = LIFECYCLE_CHANNEL) -> Union[int, None]:
        """
        Create and publish an experiment event.

        Args:
            event_type: Event type
            experiment_id: Experiment ID
            message: Optional message
            affected_tasks: Optional list of affected task IDs
            source: Optional event source
            async_mode: Whether to publish asynchronously
            channel: Optional channel to publish to (defaults to LIFECYCLE_CHANNEL)

        Returns:
            Number of handlers that processed the event, or None if async
        """
        event = ExperimentEvent(
            type=event_type,
            experiment_id=experiment_id,
            message=message,
            affected_tasks=affected_tasks or [],
            source=source
        )
        
        if async_mode:
            self.publish_async(event, channel)
            return None
        else:
            return self.publish(event, channel)

    def publish_analysis_event(self,
                               event_type: EventType,
                               data: Dict[str, Any] = None,
                               related_task_id: Optional[str] = None,  # Changed to str for UUID support
                               source: str = None,
                               async_mode: bool = False,
                               channel: Optional[str] = ANALYSIS_CHANNEL) -> Union[int, None]:
        """
        Create and publish an analysis event.

        Args:
            event_type: Event type
            data: Optional analysis data
            related_task_id: Optional related task ID
            source: Optional event source
            async_mode: Whether to publish asynchronously
            channel: Optional channel to publish to (defaults to ANALYSIS_CHANNEL)

        Returns:
            Number of handlers that processed the event, or None if async
        """
        event = AnalysisEvent(
            type=event_type,
            data=data or {},
            related_task_id=related_task_id,
            source=source
        )
        
        if async_mode:
            self.publish_async(event, channel)
            return None
        else:
            return self.publish(event, channel)

    def publish_error_event(self, 
                           error: Exception, 
                           context: Optional[Dict[str, Any]] = None,
                           async_mode: bool = False) -> Union[int, None]:
        """
        Publish an error event with details about the exception.

        Args:
            error: The exception that occurred
            context: Optional context information
            async_mode: Whether to publish asynchronously

        Returns:
            Number of handlers that processed the event, or None if async
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
            source="ErrorHandler",
            async_mode=async_mode,
            channel=self.ERROR_CHANNEL
        )

    def get_history(self,
                    event_type: Optional[EventType] = None,
                    since: Optional[datetime] = None,
                    source: Optional[str] = None,
                    task_id: Optional[str] = None,  # Changed to str for UUID support
                    channels: Optional[List[str]] = None,
                    limit: int = 100) -> List[Event]:
        """
        Get event history with optional filters.

        Args:
            event_type: Optional filter by event type
            since: Optional filter by timestamp
            source: Optional filter by source
            task_id: Optional filter by task ID (for TaskEvents)
            channels: Optional filter by channels
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
