# rvandroid/experiment/event/event_bus.py
"""
EventBus implementation for the RV-Android system.

This module provides a thread-safe, high-performance implementation of
the IEventBus interface for decoupled communication across the system.
"""

import time
import uuid
import threading
from typing import Dict, List, Any, Optional, Type, Callable, TypeVar, Set

from rvandroid.experiment.event.interfaces import IEvent, IEventBus, IEventHandler
from rvandroid.util.logging.manager import LoggingManager

T = TypeVar('T', bound=IEvent)

class EventBus(IEventBus):
    """
    A comprehensive event bus implementation for the RV-Android system.
    
    ### Architectural Decisions:
    - Employs a thread-safe design for concurrent event publishing and subscription
    - Uses a publisher-subscriber pattern with event filtering capability
    - Provides comprehensive event history tracking for diagnostics
    - Implements fine-grained subscription management with unique identifiers
    - Integrates with the system's logging infrastructure for visibility
    
    ### Role in the System:
    - Acts as the central communication backbone for all system components
    - Enables decoupled interactions between logically separate modules
    - Facilitates complex event-driven workflows with minimal coupling
    - Provides a standardized communication mechanism across the framework
    - Supports debugging and diagnostics through event history tracking
    
    ### Key Considerations:
    - Handles multithreaded access with proper synchronization
    - Employs fast lookup structures for efficient event dispatch
    - Provides fault isolation through exception handling in handlers
    - Maintains bounded memory usage with configurable history limits
    - Supports comprehensive event filtering and prioritization
    
    ### Integration Strategy:
    - Components access the bus through dependency injection or provider
    - Event types follow a standard hierarchical naming convention
    - Event handlers can be registered statically or dynamically
    - Event history provides an audit trail for diagnostics
    """
    
    def __init__(self, logger_manager: Optional[LoggingManager] = None):
        """
        Initialize the event bus with configurable logging.
        
        Creates a new, independent event bus with its own subscription registry
        and event history. Multiple event buses can exist in the system for
        isolation between different subsystems if needed.
        
        Args:
            logger_manager: Optional logging manager for event logging.
                            If not provided, the default instance will be used.
        """
        # Data structures for subscriptions and history
        self._subscribers: Dict[str, Dict[str, IEventHandler]] = {}
        self._history: List[IEvent] = []
        self._max_history_size = 1000
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Set up logging
        self._logger_manager = logger_manager or LoggingManager.get_instance()
        self._logger = self._logger_manager.get_logger('event.bus', {'component': 'EventBus'})
        self._logger.debug("EventBus initialized")
    
    def publish(self, event: IEvent) -> int:
        """
        Publish an event to all subscribers.
        
        Distributes an event to all registered handlers that have subscribed
        to the event's name. The event is also added to the history for later
        retrieval. Handlers are executed in the current thread, so this method
        may block until all handlers have processed the event.
        
        Thread Safety:
            This method is thread-safe and can be called concurrently from
            multiple threads.
        
        Error Handling:
            Exceptions in event handlers are caught and logged, preventing
            them from affecting other handlers or the publisher.
        
        Args:
            event: The event to publish
            
        Returns:
            Number of handlers that successfully processed the event
        """
        if not isinstance(event, IEvent):
            self._logger.error(f"Invalid event object: {event}")
            return 0
            
        with self._lock:
            # Add to history
            self._history.append(event)
            if len(self._history) > self._max_history_size:
                self._history = self._history[-self._max_history_size:]
            
            # Get subscribers for this event type
            event_name = event.name
            if event_name not in self._subscribers:
                return 0
                
            # Make a copy of handlers to avoid issues if handlers are modified during iteration
            handlers = list(self._subscribers[event_name].values())
            
        # Process event with handlers (outside lock to prevent deadlocks)
        count = 0
        for handler in handlers:
            try:
                if handler.can_handle(event) and handler.handle(event):
                    count += 1
            except Exception as e:
                self._logger.error(f"Error in event handler for event {event.name}: {e}", exc_info=True)
                
        self._logger.debug(f"Published event {event.name} to {count} handlers")
        return count
    
    def subscribe(self, event_name: str, handler: IEventHandler) -> str:
        """
        Subscribe to events with a handler.
        
        Registers a handler to be notified when events with the specified
        name are published. Each subscription receives a unique identifier
        that can be used to unsubscribe later. Multiple handlers can subscribe
        to the same event name, and they will all be notified when such events
        are published.
        
        Thread Safety:
            This method is thread-safe and can be called concurrently from
            multiple threads.
        
        Args:
            event_name: Name of the event to subscribe to
            handler: Handler to process events
            
        Returns:
            Subscription ID that can be used for unsubscribing
        """
        # Generate a unique subscription ID
        subscription_id = str(uuid.uuid4())
        
        with self._lock:
            # Create subscriber map for this event type if it doesn't exist
            if event_name not in self._subscribers:
                self._subscribers[event_name] = {}
                
            # Add handler to subscribers
            self._subscribers[event_name][subscription_id] = handler
            
        self._logger.debug(f"Subscribed to {event_name}, subscription ID: {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Removes a previously registered subscription based on its ID.
        This prevents the associated handler from receiving future events.
        
        Thread Safety:
            This method is thread-safe and can be called concurrently from
            multiple threads.
        
        Args:
            subscription_id: ID returned from subscribe
            
        Returns:
            True if successfully unsubscribed, False if subscription ID not found
        """
        with self._lock:
            # Search for subscription ID in all event types
            for event_name in self._subscribers:
                if subscription_id in self._subscribers[event_name]:
                    # Remove subscription
                    del self._subscribers[event_name][subscription_id]
                    self._logger.debug(f"Unsubscribed from {event_name} with ID {subscription_id}")
                    return True
                    
        self._logger.debug(f"Subscription ID {subscription_id} not found")
        return False
    
    def get_history(self, 
                  event_name: Optional[str] = None,
                  source: Optional[str] = None, 
                  limit: int = 100) -> List[IEvent]:
        """
        Get event history with optional filters.
        
        Retrieves previously published events from the bus's history,
        with optional filtering by event name, source, and maximum count.
        
        Thread Safety:
            This method is thread-safe and can be called concurrently from
            multiple threads.
        
        Args:
            event_name: Optional filter by event name
            source: Optional filter by source
            limit: Maximum number of events to return
            
        Returns:
            List of events matching the filters, sorted by timestamp (newest first)
        """
        with self._lock:
            # Make a copy of the history list to avoid concurrent modification issues
            events = list(self._history)
            
        # Apply filters
        if event_name is not None:
            events = [e for e in events if e.name == event_name]
            
        if source is not None:
            events = [e for e in events if e.source == source]
            
        # Sort by timestamp (newest first) and apply limit
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]