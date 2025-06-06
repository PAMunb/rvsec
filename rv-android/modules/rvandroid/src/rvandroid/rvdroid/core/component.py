# rvandroid/rvdroid/core/component.py

"""
Base component interface for RVDroid.

This module defines the base interface for all RVDroid components,
providing a consistent lifecycle and configuration approach.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class Component(ABC):
    """
    Base interface for all RVDroid components.
    
    ### Architectural Decisions:
    - Provides a standard lifecycle for all components
    - Centralizes configuration and initialization logic
    - Enforces consistent shutdown and resource management
    - Enables component-level error handling and logging
    - Implements the Composite pattern for component hierarchies
    
    ### Role in the System:
    - Serves as the base for all specialized components
    - Standardizes component interaction and management
    - Ensures proper resource acquisition and release
    - Supports hierarchical component organization
    - Provides consistent error handling and recovery
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the component.
        
        Args:
            name: Component name
            config: Optional configuration dictionary
        """
        self.name = name
        self.config = config or {}
        self.initialized = False
        self.running = False
        
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"rvdroid.{name.lower().replace(' ', '_')}",
            {CONTEXT_COMPONENT: name}
        )
        
        # Child components if this is a composite
        self.child_components = {}
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the component.
        
        Returns:
            True if initialization is successful, False otherwise
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """
        Start the component.
        
        Returns:
            True if start is successful, False otherwise
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        Stop the component.
        
        Returns:
            True if stop is successful, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """
        Clean up component resources.
        """
        pass
    
    def add_child_component(self, component_id: str, component: 'Component') -> None:
        """
        Add a child component to this component.
        
        Args:
            component_id: Identifier for the child component
            component: The child component to add
        """
        self.child_components[component_id] = component
        self.logger.debug(f"Added child component: {component_id}")
    
    def get_child_component(self, component_id: str) -> Optional['Component']:
        """
        Get a child component by ID.
        
        Args:
            component_id: Identifier for the child component
            
        Returns:
            The child component or None if not found
        """
        return self.child_components.get(component_id)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of this component.
        
        Returns:
            Dictionary with component status information
        """
        return {
            "name": self.name,
            "initialized": self.initialized,
            "running": self.running,
            "child_components": {
                component_id: component.get_status() 
                for component_id, component in self.child_components.items()
            }
        }


class CompositeComponent(Component):
    """
    Component that contains and manages child components.
    
    Implements the Composite design pattern to create component hierarchies
    with consistent lifecycle management.
    """
    
    def initialize(self) -> bool:
        """
        Initialize this component and all child components.
        
        Returns:
            True if initialization is successful, False otherwise
        """
        self.logger.info(f"Initializing composite component: {self.name}")
        
        # Initialize all child components
        all_initialized = True
        for component_id, component in self.child_components.items():
            self.logger.debug(f"Initializing child component: {component_id}")
            if not component.initialize():
                self.logger.error(f"Failed to initialize child component: {component_id}")
                all_initialized = False
        
        self.initialized = all_initialized
        return all_initialized
    
    def start(self) -> bool:
        """
        Start this component and all child components.
        
        Returns:
            True if start is successful, False otherwise
        """
        if not self.initialized:
            self.logger.error(f"Cannot start component {self.name}: not initialized")
            return False
            
        self.logger.info(f"Starting composite component: {self.name}")
        
        # Start all child components
        all_started = True
        for component_id, component in self.child_components.items():
            self.logger.debug(f"Starting child component: {component_id}")
            if not component.start():
                self.logger.error(f"Failed to start child component: {component_id}")
                all_started = False
        
        self.running = all_started
        return all_started
    
    def stop(self) -> bool:
        """
        Stop this component and all child components.
        
        Returns:
            True if stop is successful, False otherwise
        """
        if not self.running:
            self.logger.warning(f"Component {self.name} is not running")
            return True
            
        self.logger.info(f"Stopping composite component: {self.name}")
        
        # Stop all child components in reverse order
        all_stopped = True
        for component_id, component in reversed(list(self.child_components.items())):
            self.logger.debug(f"Stopping child component: {component_id}")
            if not component.stop():
                self.logger.error(f"Failed to stop child component: {component_id}")
                all_stopped = False
        
        self.running = not all_stopped
        return all_stopped
    
    def cleanup(self) -> None:
        """
        Clean up this component and all child components.
        """
        self.logger.info(f"Cleaning up composite component: {self.name}")
        
        # Clean up all child components in reverse order
        for component_id, component in reversed(list(self.child_components.items())):
            self.logger.debug(f"Cleaning up child component: {component_id}")
            try:
                component.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up child component {component_id}: {e}")
        
        self.initialized = False
        self.running = False