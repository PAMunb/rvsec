# rvandroid/experiment/event/interfaces.py
"""
Interfaces for the event system.

This module defines the core interfaces for the event system, providing a
contract for events, event bus implementations, and event handlers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, TypeVar, Generic

T = TypeVar('T')

class IEvent(ABC):
    """
    Interface for all events in the RV-Android system.
    
    ### Architectural Decisions:
    - Defines a consistent interface for all event types
    - Provides methods for introspection and serialization
    - Ensures events carry consistent metadata
    - Enables filtering and categorization of events
    
    ### Role in the System:
    - Serves as a standardized data transfer object for events
    - Provides metadata for event tracking and analysis
    - Enables type-safe event handling
    - Facilitates serialization for persistence or remote communication
    """
    
    @property
    @abstractmethod
    def event_id(self) -> str:
        """
        Get the unique identifier for this event.
        
        Returns:
            A unique string identifier for this event instance
        """
        pass
        
    @property
    @abstractmethod
    def timestamp(self) -> float:
        """
        Get the timestamp for this event.
        
        Returns:
            The time when this event was created, as seconds since epoch
        """
        pass
        
    @property
    def name(self) -> str:
        """
        Get the event name.
        
        Returns:
            The name of this event type, used for subscription matching
        """
        # This is no longer an abstract method - provides a default implementation
        # to maintain compatibility with the interface
        return getattr(self, '_name', "UNNAMED_EVENT")
        
    @property
    @abstractmethod
    def source(self) -> Optional[str]:
        """
        Get the event source.
        
        Returns:
            The component that generated this event, or None if unknown
        """
        pass
        
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary for serialization.
        
        Returns:
            A dictionary representation of this event
        """
        pass

class IEventBus(ABC):
    """
    Interface for event bus implementations.
    
    ### Architectural Decisions:
    - Provides a decoupled communication mechanism across components
    - Supports type-safe event handlers with filtering capabilities
    - Maintains an event history for diagnostics and debugging
    - Offers a standardized publish-subscribe contract
    
    ### Role in the System:
    - Serves as the central message broker for all components
    - Enables loose coupling between event publishers and subscribers
    - Provides a consistent messaging pattern throughout the system
    - Facilitates complex event-driven workflows
    """
    
    @abstractmethod
    def publish(self, event: IEvent) -> int:
        """
        Publish an event to subscribers.
        
        Distributes an event to all registered handlers that have subscribed
        to the event's name. Handlers are invoked in order of priority.
        
        Args:
            event: The event to publish
            
        Returns:
            Number of handlers that processed the event
        """
        pass
        
    @abstractmethod
    def subscribe(self, event_name: str, handler: 'IEventHandler') -> str:
        """
        Subscribe to events with a handler.
        
        Registers a handler to be notified when events with the specified
        name are published. The handler can optionally filter events based
        on additional criteria.
        
        Args:
            event_name: Name of the event to subscribe to
            handler: Handler to process events
            
        Returns:
            Subscription ID for unsubscribing
        """
        pass
        
    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.
        
        Removes a previously registered subscription based on its ID.
        This prevents the associated handler from receiving future events.
        
        Args:
            subscription_id: ID returned from subscribe
            
        Returns:
            True if successfully unsubscribed, False otherwise
        """
        pass
        
    @abstractmethod
    def get_history(self, 
                   event_name: Optional[str] = None,
                   source: Optional[str] = None, 
                   limit: int = 100) -> List[IEvent]:
        """
        Get event history with optional filters.
        
        Retrieves previously published events from the bus's history,
        with optional filtering by event name, source, and maximum count.
        
        Args:
            event_name: Optional filter by event name
            source: Optional filter by source
            limit: Maximum number of events to return
            
        Returns:
            List of events matching the filters, sorted by timestamp (newest first)
        """
        pass

class IEventHandler(Generic[T], ABC):
    """
    Interface for event handlers.
    
    ### Architectural Decisions:
    - Uses generics to enable type-safe event handling
    - Provides filtering capabilities for selective event processing
    - Separates handler capability check from handling logic
    - Enables prioritization of handlers
    
    ### Role in the System:
    - Processes events published to the event bus
    - Implements business logic in response to events
    - Enables selective handling of events
    - Facilitates complex event-driven workflows
    """
    
    @abstractmethod
    def handle(self, event: T) -> bool:
        """
        Handle an event.
        
        Processes an event according to the handler's implementation.
        The handler may choose to ignore the event based on filtering criteria.
        
        Args:
            event: Event to handle
            
        Returns:
            True if event was handled, False otherwise
        """
        pass
        
    @property
    @abstractmethod
    def can_handle(self, event: IEvent) -> bool:
        """
        Check if this handler can handle the event.
        
        Determines whether this handler is capable of and interested in
        handling the specified event. This is typically based on the event
        type and optional filtering criteria.
        
        Args:
            event: Event to check
            
        Returns:
            True if this handler can handle the event
        """
        pass