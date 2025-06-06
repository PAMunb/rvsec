# rvandroid/rvdroid/core/registry.py

"""
Component registry for RVDroid.

This module provides a centralized registry for managing
and accessing RVDroid components.
"""

from typing import Dict, Any, Optional, Type, TypeVar, List, Set

from rv_android_core.util.error.decorators import handle_error
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager

from rv_android_core.rvdroid.core.component import Component


# Type variable for component types
T = TypeVar('T', bound=Component)


class ComponentRegistry:
    """
    Registry for RVDroid components.
    
    ### Architectural Decisions:
    - Implements a service locator pattern for component management
    - Provides centralized component registration and discovery
    - Supports type-safe component retrieval with proper error handling
    - Enables component lifecycle management through the registry
    - Allows component dependencies to be resolved automatically
    
    ### Role in the System:
    - Acts as a central hub for component management
    - Facilitates component discovery and instantiation
    - Manages component dependencies and initialization order
    - Provides a consistent interface for component access
    - Supports component hierarchies with parent-child relationships
    """
    
    def __init__(self):
        """Initialize the component registry."""
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.core.registry",
            {CONTEXT_COMPONENT: "ComponentRegistry"}
        )
        
        # Component storage
        self.components: Dict[str, Component] = {}
        self.component_types: Dict[str, Type[Component]] = {}
        
        # Component dependencies
        self.dependencies: Dict[str, Set[str]] = {}
        
        # Initialization state
        self.initialized = False
        
    @handle_error(level="ERROR")
    def register_component_type(self, component_type: Type[T], component_id: Optional[str] = None) -> None:
        """
        Register a component type with the registry.
        
        Args:
            component_type: Component class to register
            component_id: Optional ID for the component (defaults to class name)
        """
        if not issubclass(component_type, Component):
            raise TypeError(f"Component type must inherit from Component: {component_type.__name__}")
            
        # Use class name as ID if not provided
        if component_id is None:
            component_id = component_type.__name__
            
        # Check for duplicate registration
        if component_id in self.component_types:
            self.logger.warning(f"Component type already registered: {component_id}")
            return
            
        # Register component type
        self.component_types[component_id] = component_type
        self.logger.info(f"Registered component type: {component_id}")
        
    @handle_error(level="ERROR")
    def register_component(self, component: Component, component_id: Optional[str] = None) -> None:
        """
        Register a component instance with the registry.
        
        Args:
            component: Component instance to register
            component_id: Optional ID for the component (defaults to class name)
        """
        # Use class name as ID if not provided
        if component_id is None:
            component_id = component.__class__.__name__
            
        # Check for duplicate registration
        if component_id in self.components:
            self.logger.warning(f"Component already registered: {component_id}")
            return
            
        # Register component
        self.components[component_id] = component
        self.logger.info(f"Registered component: {component_id}")
        
    @handle_error(level="ERROR")
    def get_component(self, component_id: str) -> Optional[Component]:
        """
        Get a component by ID.
        
        Args:
            component_id: Component ID
            
        Returns:
            Component instance or None if not found
        """
        # Check if component exists
        if component_id in self.components:
            return self.components[component_id]
            
        # Check if component type exists and create instance
        if component_id in self.component_types:
            # Create and register component
            component_type = self.component_types[component_id]
            component = component_type()
            self.register_component(component, component_id)
            return component
            
        # Component not found
        self.logger.warning(f"Component not found: {component_id}")
        return None
        
    @handle_error(level="ERROR")
    def get_component_by_type(self, component_type: Type[T]) -> Optional[T]:
        """
        Get a component by type.
        
        Args:
            component_type: Component class
            
        Returns:
            Component instance or None if not found
        """
        # Look for component instance with matching type
        for component in self.components.values():
            if isinstance(component, component_type):
                return component
                
        # Look for registered component type
        type_id = component_type.__name__
        if type_id in self.component_types:
            component = component_type()
            self.register_component(component, type_id)
            return component
            
        # Component type not found
        self.logger.warning(f"Component type not found: {component_type.__name__}")
        return None
        
    @handle_error(level="ERROR")
    def initialize_components(self) -> bool:
        """
        Initialize all registered components.
        
        Returns:
            True if all components initialized successfully, False otherwise
        """
        if self.initialized:
            self.logger.warning("Components already initialized")
            return True
            
        # Process components in dependency order
        init_order = self._get_initialization_order()
        
        # Initialize components
        all_initialized = True
        for component_id in init_order:
            component = self.components.get(component_id)
            if not component:
                self.logger.warning(f"Component not found for initialization: {component_id}")
                continue
                
            try:
                self.logger.info(f"Initializing component: {component_id}")
                if not component.initialize():
                    self.logger.error(f"Failed to initialize component: {component_id}")
                    all_initialized = False
            except Exception as e:
                self.logger.error(f"Error initializing component {component_id}: {e}")
                all_initialized = False
                
        self.initialized = all_initialized
        return all_initialized
        
    @handle_error(level="ERROR")
    def start_components(self) -> bool:
        """
        Start all initialized components.
        
        Returns:
            True if all components started successfully, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot start components: not initialized")
            return False
            
        # Process components in dependency order
        start_order = self._get_initialization_order()
        
        # Start components
        all_started = True
        for component_id in start_order:
            component = self.components.get(component_id)
            if not component:
                self.logger.warning(f"Component not found for starting: {component_id}")
                continue
                
            try:
                self.logger.info(f"Starting component: {component_id}")
                if not component.start():
                    self.logger.error(f"Failed to start component: {component_id}")
                    all_started = False
            except Exception as e:
                self.logger.error(f"Error starting component {component_id}: {e}")
                all_started = False
                
        return all_started
        
    @handle_error(level="ERROR")
    def stop_components(self) -> bool:
        """
        Stop all running components.
        
        Returns:
            True if all components stopped successfully, False otherwise
        """
        # Process components in reverse dependency order
        stop_order = list(reversed(self._get_initialization_order()))
        
        # Stop components
        all_stopped = True
        for component_id in stop_order:
            component = self.components.get(component_id)
            if not component:
                self.logger.warning(f"Component not found for stopping: {component_id}")
                continue
                
            try:
                self.logger.info(f"Stopping component: {component_id}")
                if not component.stop():
                    self.logger.error(f"Failed to stop component: {component_id}")
                    all_stopped = False
            except Exception as e:
                self.logger.error(f"Error stopping component {component_id}: {e}")
                all_stopped = False
                
        return all_stopped
        
    @handle_error(level="ERROR")
    def cleanup_components(self) -> None:
        """Clean up all components."""
        # Process components in reverse dependency order
        cleanup_order = list(reversed(self._get_initialization_order()))
        
        # Clean up components
        for component_id in cleanup_order:
            component = self.components.get(component_id)
            if not component:
                self.logger.warning(f"Component not found for cleanup: {component_id}")
                continue
                
            try:
                self.logger.info(f"Cleaning up component: {component_id}")
                component.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up component {component_id}: {e}")
                
        # Reset initialization state
        self.initialized = False
        
    @handle_error(level="ERROR")
    def add_dependency(self, component_id: str, dependency_id: str) -> None:
        """
        Add a dependency between components.
        
        Args:
            component_id: Component that depends on another
            dependency_id: Component that is depended on
        """
        # Initialize dependency set if needed
        if component_id not in self.dependencies:
            self.dependencies[component_id] = set()
            
        # Add dependency
        self.dependencies[component_id].add(dependency_id)
        self.logger.debug(f"Added dependency: {component_id} -> {dependency_id}")
        
    def _get_initialization_order(self) -> List[str]:
        """
        Get the order in which components should be initialized.
        
        Returns:
            List of component IDs in initialization order
        """
        # Start with components that have no dependencies
        pending = set(self.components.keys())
        processed = set()
        order = []
        
        # Process components without dependencies first
        while pending:
            next_batch = set()
            
            for component_id in pending:
                # Check if component has unprocessed dependencies
                deps = self.dependencies.get(component_id, set())
                if deps.issubset(processed):
                    # All dependencies processed, add to order
                    next_batch.add(component_id)
                    order.append(component_id)
                    
            # Update sets
            processed.update(next_batch)
            pending.difference_update(next_batch)
            
            # Handle cyclic dependencies
            if not next_batch and pending:
                self.logger.warning(f"Cyclic dependencies detected: {pending}")
                # Break cycle by adding one component to the order
                component_id = next(iter(pending))
                order.append(component_id)
                processed.add(component_id)
                pending.remove(component_id)
                
        return order
        
    def get_component_status(self) -> Dict[str, Any]:
        """
        Get status of all components.
        
        Returns:
            Dictionary with component status information
        """
        return {
            component_id: component.get_status()
            for component_id, component in self.components.items()
        }


# Global component registry instance
_registry = None


def get_registry() -> ComponentRegistry:
    """
    Get the global component registry instance.
    
    Returns:
        Global component registry
    """
    global _registry
    if _registry is None:
        _registry = ComponentRegistry()
    return _registry