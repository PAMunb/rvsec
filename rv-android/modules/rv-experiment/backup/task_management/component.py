# rvandroid/experiment/task/component.py
"""
Task component system for modular task execution.

This module provides the base implementation for task components, which are
specialized modules that handle specific aspects of task execution, such as
static analysis, coverage tracking, or tool execution.
"""

import logging
from abc import abstractmethod
from typing import Dict, Any, Optional, List, Type, TypeVar, Generic

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_COMPONENT, CONTEXT_APP_NAME
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.event import EventBus
from rv_experiment.experiment.task.interfaces import ITaskComponent


class BaseTaskComponent(ITaskComponent):
    """
    Base implementation for task execution components.
    
    ### Architectural Decisions:
    - Implements common functionality for all components
    - Provides built-in error handling and logging
    - Supports event-based communication between components
    - Enables standardized component lifecycle management
    
    ### Role in the System:
    - Provides a foundation for specialized task components
    - Reduces boilerplate in component implementations
    - Ensures consistent error handling and logging
    - Facilitates event-based communication
    """

    def __init__(self,
                 component_name: str,
                 event_bus: Optional[EventBus] = None):
        """
        Initialize the component.
        
        Args:
            component_name: Name of this component
            event_bus: Optional event bus for publishing events
        """
        self._name = component_name
        self.event_bus = event_bus or EventBus.get_instance()
        self.error_handler = None  # Lazy-loaded to avoid circular imports

        # Create logger with basic context
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f'experiment.components.{component_name.lower()}',
            {
                CONTEXT_COMPONENT: component_name
            }
        )

    def _get_error_handler(self) -> ErrorHandler:
        """
        Get the error handler, initializing it if needed.
        
        Returns:
            Error handler instance
        """
        if self.error_handler is None:
            self.error_handler = ErrorHandler.get_instance()
        return self.error_handler

    def initialize(self, context: Dict[str, Any]) -> bool:
        """
        Initialize the component with task-specific context.
        
        This is the first phase of the component lifecycle, where it should
        prepare for execution by setting up any required resources or state.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if initialization was successful, False otherwise
        """
        # Update logger context with task information
        if context.get("task_id"):
            self.logger = LoggingManager.get_instance().get_logger(
                f'experiment.components.{self.name.lower()}',
                {
                    CONTEXT_TASK_ID: context.get("task_id"),
                    CONTEXT_APP_NAME: context.get("apk_name", "unknown"),
                    CONTEXT_COMPONENT: self.name
                }
            )

        self.logger.debug(f"Initializing component: {self.name}")
        return True

    def execute(self, context: Dict[str, Any]) -> bool:
        """
        Execute the component's primary function.
        
        This is the main phase of the component lifecycle, where it performs
        its core functionality as part of task execution.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if execution was successful, False otherwise
        """
        self.logger.debug(f"Executing component: {self.name}")
        return self._execute_impl(context)

    @abstractmethod
    def _execute_impl(self, context: Dict[str, Any]) -> bool:
        """
        Implementation of the component's primary function.
        
        This method should be overridden by subclasses to provide
        component-specific execution logic.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if execution was successful, False otherwise
        """
        pass

    def cleanup(self, context: Dict[str, Any]) -> bool:
        """
        Clean up any resources used by the component.
        
        This is the final phase of the component lifecycle, where it should
        release any resources and perform any necessary cleanup.
        
        Args:
            context: Dictionary with task context information
            
        Returns:
            True if cleanup was successful, False otherwise
        """
        self.logger.debug(f"Cleaning up component: {self.name}")
        return True

    @property
    def name(self) -> str:
        """
        Get the component name.
        
        Returns:
            The name of this component
        """
        return self._name


class ComponentRegistry:
    """
    Registry for task components.
    
    ### Architectural Decisions:
    - Centralizes component registration and retrieval
    - Supports component ordering by dependency or priority
    - Provides type-safe component access
    - Enables component lifecycle management
    
    ### Role in the System:
    - Manages component registration and dependencies
    - Facilitates component discovery and retrieval
    - Ensures consistent component initialization
    - Supports component ordering and prioritization
    """

    def __init__(self):
        """Initialize an empty component registry."""
        self.components: Dict[str, ITaskComponent] = {}
        self.component_order: List[str] = []
        self.logger = logging.getLogger(__name__)

    def register(self, component: ITaskComponent) -> None:
        """
        Register a component with the registry.
        
        Args:
            component: Component to register
        """
        self.components[component.name] = component
        if component.name not in self.component_order:
            self.component_order.append(component.name)
        self.logger.debug(f"Registered component: {component.name}")

    def unregister(self, component_name: str) -> bool:
        """
        Unregister a component from the registry.
        
        Args:
            component_name: Name of component to unregister
            
        Returns:
            True if component was unregistered, False if not found
        """
        if component_name in self.components:
            del self.components[component_name]
            if component_name in self.component_order:
                self.component_order.remove(component_name)
            self.logger.debug(f"Unregistered component: {component_name}")
            return True
        return False

    def get(self, component_name: str) -> Optional[ITaskComponent]:
        """
        Get a component by name.
        
        Args:
            component_name: Name of component to retrieve
            
        Returns:
            Component if found, None otherwise
        """
        return self.components.get(component_name)

    def get_all(self) -> List[ITaskComponent]:
        """
        Get all registered components in registration order.
        
        Returns:
            List of all components
        """
        return [self.components[name] for name in self.component_order if name in self.components]

    def set_order(self, component_names: List[str]) -> None:
        """
        Set the execution order of components.
        
        Args:
            component_names: Ordered list of component names
        """
        if not all(name in self.components for name in component_names):
            missing = [name for name in component_names if name not in self.components]
            self.logger.warning(f"Some components not registered: {missing}")

        # Only include registered components
        self.component_order = [name for name in component_names if name in self.components]

        # Add any registered components not in the order list at the end
        for name in self.components:
            if name not in self.component_order:
                self.component_order.append(name)

        self.logger.debug(f"Component order set: {self.component_order}")

    def initialize_all(self, context: Dict[str, Any]) -> bool:
        """
        Initialize all components with the given context.
        
        Args:
            context: Context to pass to components
            
        Returns:
            True if all components initialized successfully
        """
        success = True
        for component in self.get_all():
            if not component.initialize(context):
                self.logger.error(f"Failed to initialize component: {component.name}")
                success = False
        return success

    def cleanup_all(self, context: Dict[str, Any]) -> bool:
        """
        Clean up all components with the given context.
        
        Args:
            context: Context to pass to components
            
        Returns:
            True if all components cleaned up successfully
        """
        success = True
        # Clean up in reverse order to handle dependencies properly
        for component in reversed(self.get_all()):
            if not component.cleanup(context):
                self.logger.error(f"Failed to clean up component: {component.name}")
                success = False
        return success


T = TypeVar('T', bound=ITaskComponent)


class ComponentFactory(Generic[T]):
    """
    Factory for creating task components.
    
    ### Architectural Decisions:
    - Uses generics to support different component types
    - Provides centralized component creation logic
    - Ensures consistent component initialization
    - Supports dependency injection for component creation
    
    ### Role in the System:
    - Creates component instances with appropriate configuration
    - Ensures consistent component initialization
    - Centralizes component creation logic
    - Supports different component types through generics
    """

    def __init__(self, component_class: Type[T]):
        """
        Initialize the factory with a component class.
        
        Args:
            component_class: Class to use for creating components
        """
        self.component_class = component_class
        self.logger = logging.getLogger(__name__)

    def create(self, *args, **kwargs) -> T:
        """
        Create a new component instance.
        
        Args:
            *args: Positional arguments to pass to component constructor
            **kwargs: Keyword arguments to pass to component constructor
            
        Returns:
            Newly created component instance
        """
        component = self.component_class(*args, **kwargs)
        self.logger.debug(f"Created component: {component.name}")
        return component
