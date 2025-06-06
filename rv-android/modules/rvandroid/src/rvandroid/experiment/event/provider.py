# rvandroid/experiment/event/provider.py
"""
Provider for EventBus instances.

This module provides a provider for EventBus instances, allowing
components to get a shared event bus or create their own.
"""

from typing import Optional

from rv_android_core.experiment.event.bus import EventBus

# TODO deprecated???
class EventBusProvider:
    """
    Centralized provider for EventBus instances in the RV-Android system.
    
    ### Architectural Decisions:
    - Uses a service locator pattern to provide EventBus instances
    - Maintains a single default instance for system-wide events
    - Supports creating isolated instances for subsystem events
    - Decouples event bus implementation from client code
    
    ### Role in the System:
    - Provides a centralized access point for the default event bus
    - Enables dependency injection of event buses across the system
    - Facilitates testing by allowing bus replacement
    - Eliminates direct dependencies on singleton EventBus
    
    ### Key Considerations:
    - Maintains separation between event bus creation and usage
    - Enables future changes to event bus implementation
    - Supports isolation between system components when needed
    - Provides static methods for convenient access
    """
    
    # Class variable to store the default EventBus instance
    _default_instance: Optional[EventBus] = None
    
    @classmethod
    def get_default_bus(cls) -> EventBus:
        """
        Get the default event bus instance.
        
        Provides access to the shared default event bus, creating it if
        it doesn't already exist. This bus is used for system-wide
        communication between components.
        
        Returns:
            The default event bus instance
        """
        if cls._default_instance is None:
            cls._default_instance = EventBus.get_instance()
        return cls._default_instance
        
    @classmethod
    def set_default_bus(cls, bus: EventBus) -> None:
        """
        Set the default event bus instance.
        
        Replaces the default event bus with a custom implementation.
        This is primarily useful for testing or for injecting specialized
        event bus implementations.
        
        Args:
            bus: The event bus to set as the default instance
        """
        cls._default_instance = bus
        
    @classmethod
    def create_bus(cls, worker_threads: int = 4, max_queue_size: int = 1000) -> EventBus:
        """
        Create a new, isolated event bus instance.
        
        Creates a new event bus that is separate from the default instance.
        This is useful for isolating events within a subsystem or for
        testing components independently.
        
        Args:
            worker_threads: Number of worker threads for async processing
            max_queue_size: Maximum size of the event queue
            
        Returns:
            A new event bus instance
        """
        return EventBus.create_instance()