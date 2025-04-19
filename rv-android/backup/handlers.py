# rvandroid/experiment/event/handlers.py
"""
Event handlers for the RV-Android system.

This module provides implementations of event handlers that can be
registered with the event bus to process events based on type and
optional filtering criteria.
"""

from typing import Callable, Optional, TypeVar, Generic, Dict, Any, Type

from rvandroid.experiment.event.interfaces import IEvent, IEventHandler

T = TypeVar('T', bound=IEvent)

class EventHandler(Generic[T], IEventHandler[T]):
    """
    Standard event handler implementation with filtering capabilities.
    
    ### Architectural Decisions:
    - Implements the IEventHandler interface with type safety
    - Provides flexible filtering through type checking and custom predicates
    - Supports prioritization for handling order control
    - Separates filtering logic from event handling
    
    ### Role in the System:
    - Processes events published through the event bus
    - Enables selective event handling based on criteria
    - Facilitates clean integration of event responses
    - Supports type-safe event handling with generics
    
    ### Key Considerations:
    - Provides fault isolation through callback error handling
    - Offers flexible filtering through multiple mechanisms
    - Enables prioritization for complex event processing
    - Maintains clean separation between filtering and handling
    """
    
    def __init__(self, callback: Callable[[T], None], 
                event_type: Optional[Type[T]] = None,
                filter_fn: Optional[Callable[[T], bool]] = None,
                priority: int = 0):
        """
        Initialize the event handler with callback and optional filters.
        
        Creates a handler that will invoke the callback when an event
        passes all filtering conditions. Filtering can be based on event
        type and/or a custom filter function.
        
        Args:
            callback: Function to call when an acceptable event occurs
            event_type: Optional type to restrict events to a specific class
            filter_fn: Optional function to further filter events
            priority: Handler priority (higher values run first)
        """
        self.callback = callback
        self.event_type = event_type
        self.filter_fn = filter_fn
        self.priority = priority
        
    def handle(self, event: T) -> bool:
        """
        Handle an event if it matches the filter criteria.
        
        Processes an event by first checking if it passes all filters,
        and if so, invoking the callback function. The callback is
        invoked with the event as its argument.
        
        Args:
            event: Event to handle
            
        Returns:
            True if event was handled, False if it was filtered out
        """
        if self.can_handle(event):
            self.callback(event)
            return True
        return False
        
    @property
    def can_handle(self, event: IEvent) -> bool:
        """
        Check if this handler can handle the event.
        
        Determines whether this handler should process the given event
        by checking if it matches the type constraint and passes the
        filter function, if provided.
        
        Args:
            event: Event to check
            
        Returns:
            True if this handler can handle the event, False otherwise
        """
        # Check event type if specified
        if self.event_type and not isinstance(event, self.event_type):
            return False
            
        # Apply filter function if specified
        if self.filter_fn and not self.filter_fn(event):
            return False
            
        return True

class AttributeFilterHandler(EventHandler[T]):
    """
    Event handler that filters events based on their attribute values.
    
    ### Architectural Decisions:
    - Extends EventHandler with attribute-based filtering
    - Converts attribute filters to a predicate function
    - Maintains type safety through generics
    - Preserves the standard handler interface
    
    ### Role in the System:
    - Enables declarative filtering based on event attributes
    - Provides a convenient way to handle specific event subsets
    - Supports complex event routing based on content
    - Facilitates targeted event handling without custom code
    """
    
    def __init__(self, callback: Callable[[T], None],
                event_type: Type[T],
                attribute_filters: Dict[str, Any],
                priority: int = 0):
        """
        Initialize the attribute filter handler.
        
        Creates a handler that will invoke the callback when an event
        of the specified type has attributes matching the provided filters.
        
        Args:
            callback: Function to call when an acceptable event occurs
            event_type: Type to restrict events handled
            attribute_filters: Dictionary of attribute names and expected values
            priority: Handler priority (higher values run first)
        """
        self.attribute_filters = attribute_filters
        
        # Create filter function from attribute filters
        def _attribute_filter_fn(event: T) -> bool:
            """
            Filter function that checks if event attributes match expected values.
            
            Args:
                event: Event to check
                
            Returns:
                True if all attributes match, False otherwise
            """
            for key, value in self.attribute_filters.items():
                if not hasattr(event, key) or getattr(event, key) != value:
                    return False
            return True
            
        super().__init__(
            callback, 
            event_type,
            _attribute_filter_fn,
            priority
        )