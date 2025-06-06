# rvandroid/experiment/workflow/components.py
"""
Component interfaces for workflow architecture.

This module defines the interfaces and base classes for workflow components,
establishing a contract for component implementation and interaction.
These interfaces support the dynamic component registry and enable
flexible component composition and injection.
"""

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Dict, Any, List, Optional, Set, Type, TypeVar, Generic, Protocol

from rv_android_core.experiment.core.interfaces import IExecutionContext, ExecutionPhase
from rv_android_core.experiment.event import EventBus, get_event_bus


class ComponentLifecycle(Enum):
    """
    Enum representing the lifecycle stages of a component.
    
    ### Architectural Decisions:
    - Uses auto() for value assignment to focus on lifecycle stage names
    - Provides a consistent vocabulary for component lifecycle management
    - Enables state-based component activation and deactivation
    - Supports orderly component initialization and cleanup
    
    ### Role in the System:
    - Defines standard lifecycle stages for components
    - Enables components to implement specific initialization and cleanup logic
    - Facilitates coordinated component management in workflows
    - Provides a foundation for dependency ordering and resolution
    """
    CREATED = auto()  # Component has been created
    INITIALIZED = auto()  # Component has been initialized
    CONFIGURED = auto()  # Component has been configured
    ACTIVE = auto()  # Component is active and ready for use
    SUSPENDED = auto()  # Component is temporarily suspended
    DESTROYED = auto()  # Component has been destroyed


class IComponent(ABC):
    """
    Base interface for all workflow components.
    
    ### Architectural Decisions:
    - Establishes a common contract for all components
    - Provides lifecycle management capabilities
    - Enables component identification and metadata
    - Supports dependency injection and resolution
    
    ### Role in the System:
    - Serves as the foundation for all component types
    - Enables consistent component management
    - Facilitates component discovery and registration
    - Provides a framework for component dependencies
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """
        Get the unique identifier for this component.
        
        Returns:
            Component identifier
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the display name for this component.
        
        Returns:
            Component name
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Get the description of this component.
        
        Returns:
            Component description
        """
        pass

    @property
    @abstractmethod
    def lifecycle_state(self) -> ComponentLifecycle:
        """
        Get the current lifecycle state of this component.
        
        Returns:
            Current lifecycle state
        """
        pass

    @property
    @abstractmethod
    def dependencies(self) -> Set[str]:
        """
        Get the component dependencies.
        
        Returns:
            Set of component IDs that this component depends on
        """
        pass

    @abstractmethod
    def initialize(self, context: IExecutionContext) -> bool:
        """
        Initialize the component with the provided context.
        
        Args:
            context: Execution context
            
        Returns:
            True if initialization was successful, False otherwise
        """
        pass

    @abstractmethod
    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the component with the provided configuration.
        
        Args:
            config: Component configuration
            
        Returns:
            True if configuration was successful, False otherwise
        """
        pass

    @abstractmethod
    def activate(self) -> bool:
        """
        Activate the component.
        
        Returns:
            True if activation was successful, False otherwise
        """
        pass

    @abstractmethod
    def suspend(self) -> bool:
        """
        Suspend the component.
        
        Returns:
            True if suspension was successful, False otherwise
        """
        pass

    @abstractmethod
    def destroy(self) -> bool:
        """
        Destroy the component and free any resources.
        
        Returns:
            True if destruction was successful, False otherwise
        """
        pass


class IWorkflowComponent(IComponent):
    """
    Interface for workflow-specific components.
    
    ### Architectural Decisions:
    - Extends the base component interface with workflow-specific capabilities
    - Enables phase-based component execution
    - Supports event-driven communication between components
    - Facilitates component coordination in workflows
    
    ### Role in the System:
    - Defines the contract for components that participate in workflows
    - Enables phase-based component execution and coordination
    - Provides access to the workflow execution context
    - Facilitates event-based communication between components
    """

    @property
    @abstractmethod
    def supported_phases(self) -> List[ExecutionPhase]:
        """
        Get the phases supported by this component.
        
        Returns:
            List of supported phases
        """
        pass

    @property
    @abstractmethod
    def event_bus(self) -> EventBus:
        """
        Get the event bus for this component.
        
        Returns:
            Event bus instance
        """
        pass

    @abstractmethod
    def execute(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Execute the component for the specified phase.
        
        Args:
            phase: Phase to execute
            context: Execution context
            
        Returns:
            True if execution was successful, False otherwise
        """
        pass

    @abstractmethod
    def can_execute(self, phase: ExecutionPhase) -> bool:
        """
        Check if this component can execute the specified phase.
        
        Args:
            phase: Phase to check
            
        Returns:
            True if this component can execute the phase, False otherwise
        """
        pass


T = TypeVar('T', bound=IComponent)


class ComponentMetadata(Generic[T]):
    """
    Metadata for a component, including dependencies and configuration.
    
    ### Architectural Decisions:
    - Separates component metadata from component implementation
    - Enables metadata discovery and introspection
    - Supports component dependency management
    - Facilitates component configuration and customization
    
    ### Role in the System:
    - Stores metadata about components
    - Defines component dependencies and configurations
    - Enables component discovery and registration
    - Facilitates component dependency resolution
    """

    def __init__(self,
                 component_type: Type[T],
                 dependencies: Optional[Set[str]] = None,
                 config: Optional[Dict[str, Any]] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None):
        """
        Initialize component metadata.
        
        Args:
            component_type: Type of component
            dependencies: Set of component IDs that this component depends on
            config: Configuration for the component
            name: Optional display name for the component
            description: Optional description of the component
        """
        self.component_type = component_type
        self.dependencies = dependencies or set()
        self.config = config or {}
        self.name = name or component_type.__name__
        self.description = description or component_type.__doc__ or ""

    def add_dependency(self, component_id: str) -> None:
        """
        Add a dependency to this component.
        
        Args:
            component_id: ID of the component dependency
        """
        self.dependencies.add(component_id)

    def remove_dependency(self, component_id: str) -> bool:
        """
        Remove a dependency from this component.
        
        Args:
            component_id: ID of the component dependency
            
        Returns:
            True if the dependency was removed, False if it wasn't a dependency
        """
        if component_id in self.dependencies:
            self.dependencies.remove(component_id)
            return True
        return False

    def set_config(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key doesn't exist
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def update_config(self, config: Dict[str, Any]) -> None:
        """
        Update configuration with new values.
        
        Args:
            config: New configuration values
        """
        self.config.update(config)


class BaseComponent(IComponent):
    """
    Base implementation of the component interface.
    
    ### Architectural Decisions:
    - Provides a standard implementation of common component functionality
    - Implements lifecycle management and state transitions
    - Enables easy dependency tracking and management
    - Facilitates component identification and introspection
    
    ### Role in the System:
    - Serves as a foundation for component implementations
    - Handles common component lifecycle management
    - Provides standard implementation of component properties
    - Enables consistent component behavior across the system
    """

    def __init__(self, component_id: Optional[str] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 dependencies: Optional[Set[str]] = None):
        """
        Initialize the component.
        
        Args:
            component_id: Optional component ID (defaults to class name)
            name: Optional display name (defaults to class name)
            description: Optional description (defaults to class docstring)
            dependencies: Optional set of component dependencies
        """
        self._id = component_id or self.__class__.__name__
        self._name = name or self.__class__.__name__
        self._description = description or self.__class__.__doc__ or ""
        self._dependencies = dependencies or set()
        self._lifecycle_state = ComponentLifecycle.CREATED
        self._context: Optional[IExecutionContext] = None
        self._config: Dict[str, Any] = {}

    @property
    def id(self) -> str:
        """
        Get the unique identifier for this component.
        
        Returns:
            Component identifier
        """
        return self._id

    @property
    def name(self) -> str:
        """
        Get the display name for this component.
        
        Returns:
            Component name
        """
        return self._name

    @property
    def description(self) -> str:
        """
        Get the description of this component.
        
        Returns:
            Component description
        """
        return self._description

    @property
    def lifecycle_state(self) -> ComponentLifecycle:
        """
        Get the current lifecycle state of this component.
        
        Returns:
            Current lifecycle state
        """
        return self._lifecycle_state

    @property
    def dependencies(self) -> Set[str]:
        """
        Get the component dependencies.
        
        Returns:
            Set of component IDs that this component depends on
        """
        return self._dependencies.copy()

    def add_dependency(self, component_id: str) -> None:
        """
        Add a dependency to this component.
        
        Args:
            component_id: ID of the component dependency
        """
        self._dependencies.add(component_id)

    def initialize(self, context: IExecutionContext) -> bool:
        """
        Initialize the component with the provided context.
        
        Args:
            context: Execution context
            
        Returns:
            True if initialization was successful, False otherwise
        """
        if self._lifecycle_state != ComponentLifecycle.CREATED:
            return False

        self._context = context
        self._lifecycle_state = ComponentLifecycle.INITIALIZED
        return True

    def configure(self, config: Dict[str, Any]) -> bool:
        """
        Configure the component with the provided configuration.
        
        Args:
            config: Component configuration
            
        Returns:
            True if configuration was successful, False otherwise
        """
        if self._lifecycle_state not in (ComponentLifecycle.INITIALIZED, ComponentLifecycle.CONFIGURED):
            return False

        self._config.update(config)
        self._lifecycle_state = ComponentLifecycle.CONFIGURED
        return True

    def activate(self) -> bool:
        """
        Activate the component.
        
        Returns:
            True if activation was successful, False otherwise
        """
        if self._lifecycle_state != ComponentLifecycle.CONFIGURED:
            return False

        self._lifecycle_state = ComponentLifecycle.ACTIVE
        return True

    def suspend(self) -> bool:
        """
        Suspend the component.
        
        Returns:
            True if suspension was successful, False otherwise
        """
        if self._lifecycle_state != ComponentLifecycle.ACTIVE:
            return False

        self._lifecycle_state = ComponentLifecycle.SUSPENDED
        return True

    def destroy(self) -> bool:
        """
        Destroy the component and free any resources.
        
        Returns:
            True if destruction was successful, False otherwise
        """
        if self._lifecycle_state == ComponentLifecycle.DESTROYED:
            return False

        self._lifecycle_state = ComponentLifecycle.DESTROYED
        return True


class BaseWorkflowComponent(BaseComponent, IWorkflowComponent):
    """
    Base implementation of a workflow component.
    
    ### Architectural Decisions:
    - Extends the base component with workflow-specific functionality
    - Implements phase-based execution support
    - Provides access to the event bus for communication
    - Facilitates workflow context management
    
    ### Role in the System:
    - Serves as a foundation for workflow component implementations
    - Handles workflow-specific component behavior
    - Provides phase-based execution capabilities
    - Enables event-driven communication between components
    """

    def __init__(self, component_id: Optional[str] = None,
                 name: Optional[str] = None,
                 description: Optional[str] = None,
                 dependencies: Optional[Set[str]] = None,
                 event_bus: Optional[EventBus] = None,
                 supported_phases: Optional[List[ExecutionPhase]] = None):
        """
        Initialize the workflow component.
        
        Args:
            component_id: Optional component ID (defaults to class name)
            name: Optional display name (defaults to class name)
            description: Optional description (defaults to class docstring)
            dependencies: Optional set of component dependencies
            event_bus: Optional event bus for communication
            supported_phases: Optional list of supported phases
        """
        super().__init__(component_id, name, description, dependencies)
        self._event_bus = event_bus
        self._supported_phases = supported_phases or []

    @property
    def supported_phases(self) -> List[ExecutionPhase]:
        """
        Get the phases supported by this component.
        
        Returns:
            List of supported phases
        """
        return self._supported_phases.copy()

    @property
    def event_bus(self) -> EventBus:
        """
        Get the event bus for this component.
        
        Returns:
            Event bus instance
        """
        if self._event_bus is None:
            self._event_bus = get_event_bus()
        return self._event_bus

    def execute(self, phase: ExecutionPhase, context: IExecutionContext) -> bool:
        """
        Execute the component for the specified phase.
        
        Args:
            phase: Phase to execute
            context: Execution context
            
        Returns:
            True if execution was successful, False otherwise
        """
        if not self.can_execute(phase) or self._lifecycle_state != ComponentLifecycle.ACTIVE:
            return False

        # Subclasses should override this method with actual execution logic
        return True

    def can_execute(self, phase: ExecutionPhase) -> bool:
        """
        Check if this component can execute the specified phase.
        
        Args:
            phase: Phase to check
            
        Returns:
            True if this component can execute the phase, False otherwise
        """
        return phase in self._supported_phases


# Component provider protocol for dependency injection

class ComponentProvider(Protocol[T]):
    """
    Protocol for component providers used in dependency injection.
    
    ### Architectural Decisions:
    - Uses Protocol for structural typing
    - Enables flexible component provision strategies
    - Supports both instance and factory-based component creation
    - Facilitates dependency injection and testability
    
    ### Role in the System:
    - Defines a common contract for component provision
    - Enables dynamic component resolution and creation
    - Supports dependency management and injection
    - Facilitates component lifecycle management
    """

    def get(self, component_id: str) -> Optional[T]:
        """
        Get a component by ID.
        
        Args:
            component_id: ID of the component to get
            
        Returns:
            Component instance or None if not found
        """
        ...

    def create(self, component_type: Type[T], **kwargs) -> T:
        """
        Create a new component instance.
        
        Args:
            component_type: Type of component to create
            **kwargs: Additional arguments for component creation
            
        Returns:
            New component instance
        """
        ...

    def register(self, component: T) -> str:
        """
        Register a component instance.
        
        Args:
            component: Component instance to register
            
        Returns:
            ID of the registered component
        """
        ...
