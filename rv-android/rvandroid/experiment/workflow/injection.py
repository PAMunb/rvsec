# rvandroid/experiment/workflow/injection.py
"""
Component injection support for workflow architecture.

This module provides mechanisms for component injection in workflows,
enabling flexible component composition and dependency management.
It integrates with the component registry to facilitate dynamic
component discovery, resolution, and injection.
"""

import inspect
import logging
from typing import Dict, Any, List, Type, Optional, TypeVar, Generic, Set, cast, Callable

from rvandroid.experiment.core.interfaces import IExecutionContext
from rvandroid.experiment.workflow.components import (
    IComponent, 
    ComponentMetadata, 
    ComponentProvider,
    ComponentLifecycle
)
from rvandroid.experiment.workflow.registry import ComponentRegistry

T = TypeVar('T', bound=IComponent)


class ComponentInjector(Generic[T], ComponentProvider[T]):
    """
    Component injector for dependency injection in workflows.
    
    ### Architectural Decisions:
    - Leverages the component registry for component management
    - Extends the provider protocol with dependency resolution
    - Supports both component instance and type registration
    - Enables flexible component creation and configuration
    
    ### Role in the System:
    - Resolves component dependencies during creation
    - Provides components to clients in a controlled manner
    - Ensures proper component initialization and configuration
    - Handles component lifecycle management
    """
    
    def __init__(self, registry: ComponentRegistry[T]):
        """
        Initialize the component injector.
        
        Args:
            registry: Component registry to use for component management
        """
        self.registry = registry
        self.logger = logging.getLogger(__name__)
        self.context: Optional[IExecutionContext] = None
        self.default_config: Dict[str, Dict[str, Any]] = {}
        
    def set_context(self, context: IExecutionContext) -> None:
        """
        Set the execution context for component initialization.
        
        Args:
            context: Execution context
        """
        self.context = context
        
    def set_default_config(self, component_id: str, config: Dict[str, Any]) -> None:
        """
        Set default configuration for a component type.
        
        Args:
            component_id: ID of the component
            config: Default configuration
        """
        self.default_config[component_id] = config
        
    def get(self, component_id: str) -> Optional[T]:
        """
        Get a component by ID.
        
        Args:
            component_id: ID of the component to get
            
        Returns:
            Component instance or None if not found
        """
        return self.registry.get(component_id)
        
    def create(self, component_type: Type[T], **kwargs) -> T:
        """
        Create a new component instance with dependency injection.
        
        Args:
            component_type: Type of component to create
            **kwargs: Additional arguments for component creation
            
        Returns:
            New component instance
        """
        # Get component metadata
        metadata = self._get_or_create_metadata(component_type)
        
        # Create component with constructor injection
        component = self._create_with_constructor_injection(component_type, metadata, **kwargs)
        
        # Initialize and configure component
        if self.context:
            component.initialize(self.context)
            
            # Apply default configuration if available
            default_config = self.default_config.get(component.id, {})
            if default_config:
                component.configure(default_config)
                
            # Apply provided configuration
            if kwargs.get('config'):
                component.configure(kwargs['config'])
                
            # Activate component
            component.activate()
            
        return component
        
    def register(self, component: T) -> str:
        """
        Register a component instance.
        
        Args:
            component: Component instance to register
            
        Returns:
            ID of the registered component
        """
        return self.registry.register(component)
        
    def register_type(self, component_type: Type[T]) -> str:
        """
        Register a component type.
        
        Args:
            component_type: Component type to register
            
        Returns:
            ID of the registered component type
        """
        return self.registry.register_type(component_type)
        
    def inject_dependencies(self, component: T) -> None:
        """
        Inject dependencies into an existing component.
        
        Args:
            component: Component to inject dependencies into
        """
        # Get dependencies
        dependencies = component.dependencies
        
        # Inject dependencies
        for dep_id in dependencies:
            # Skip if component is already active
            if component.lifecycle_state == ComponentLifecycle.ACTIVE:
                continue
                
            # Get or create dependency
            dependency = self.get(dep_id)
            if dependency is None:
                self.logger.warning(f"Dependency {dep_id} not found for component {component.id}")
                continue
                
            # Inject dependency using appropriate method
            self._inject_dependency(component, dependency)
            
    def create_all(self, component_types: List[Type[T]], **kwargs) -> Dict[str, T]:
        """
        Create multiple component instances.
        
        Args:
            component_types: List of component types to create
            **kwargs: Additional arguments for component creation
            
        Returns:
            Dictionary of component instances keyed by ID
        """
        components: Dict[str, T] = {}
        
        for component_type in component_types:
            component = self.create(component_type, **kwargs)
            components[component.id] = component
            
        return components
        
    def _get_or_create_metadata(self, component_type: Type[T]) -> ComponentMetadata[T]:
        """
        Get or create metadata for a component type.
        
        Args:
            component_type: Component type
            
        Returns:
            Component metadata
        """
        # Check if we already have metadata for this type
        type_name = component_type.__name__
        if hasattr(component_type, '__metadata__'):
            return getattr(component_type, '__metadata__')
            
        # Create new metadata
        metadata = ComponentMetadata(component_type)
        
        # Analyze type for dependencies
        self._analyze_dependencies(component_type, metadata)
        
        # Store metadata on the type
        setattr(component_type, '__metadata__', metadata)
        
        return metadata
        
    def _analyze_dependencies(self, component_type: Type[T], metadata: ComponentMetadata[T]) -> None:
        """
        Analyze a component type for dependencies.
        
        Args:
            component_type: Component type to analyze
            metadata: Metadata to update with dependencies
        """
        # Look for annotated dependencies in the class
        annotations = getattr(component_type, '__annotations__', {})
        
        for name, annotation in annotations.items():
            # Skip non-component annotations
            if not hasattr(annotation, '__origin__') or not issubclass(annotation.__origin__, IComponent):
                continue
                
            # Add dependency
            metadata.add_dependency(name)
            
    def _create_with_constructor_injection(self, 
                                          component_type: Type[T], 
                                          metadata: ComponentMetadata[T],
                                          **kwargs) -> T:
        """
        Create a component with constructor-based dependency injection.
        
        Args:
            component_type: Component type to create
            metadata: Component metadata
            **kwargs: Additional arguments for component creation
            
        Returns:
            New component instance
        """
        # Get constructor parameters
        signature = inspect.signature(component_type.__init__)
        parameters = signature.parameters
        
        # Prepare constructor arguments
        constructor_args = {}
        
        # Add explicit arguments
        for name, param in parameters.items():
            if name == 'self':
                continue
                
            if name in kwargs:
                constructor_args[name] = kwargs[name]
                
        # Add dependencies
        for dep_id in metadata.dependencies:
            if dep_id in constructor_args:
                continue
                
            # Get or create dependency
            dependency = self.get(dep_id)
            if dependency is None:
                self.logger.warning(f"Dependency {dep_id} not found for component {component_type.__name__}")
                continue
                
            constructor_args[dep_id] = dependency
            
        # Create instance
        try:
            return component_type(**constructor_args)
        except Exception as e:
            self.logger.error(f"Error creating component {component_type.__name__}: {e}")
            raise
            
    def _inject_dependency(self, component: T, dependency: T) -> None:
        """
        Inject a dependency into a component.
        
        Args:
            component: Component to inject into
            dependency: Dependency to inject
        """
        # Try setter injection first
        setter_name = f"set_{dependency.id}"
        if hasattr(component, setter_name) and callable(getattr(component, setter_name)):
            setter = getattr(component, setter_name)
            setter(dependency)
            return
            
        # Try property injection
        if hasattr(component, dependency.id) and isinstance(getattr(component.__class__, dependency.id, None), property):
            # Find the property setter
            prop = getattr(component.__class__, dependency.id)
            if prop.fset:
                prop.fset(component, dependency)
                return
                
        # Try field injection as last resort
        private_field_name = f"_{dependency.id}"
        if hasattr(component, private_field_name):
            setattr(component, private_field_name, dependency)
            return
            
        self.logger.warning(
            f"Could not inject dependency {dependency.id} into component {component.id}: "
            f"no suitable injection point found"
        )


class ComponentDecorator:
    """
    Decorators for component classes and methods.
    
    ### Architectural Decisions:
    - Provides declarative configuration for components
    - Enables metadata definition through decorators
    - Supports dependency declaration and configuration
    - Facilitates component discovery and registration
    
    ### Role in the System:
    - Simplifies component implementation and configuration
    - Enables declarative definition of component metadata
    - Provides clear dependency specification
    - Facilitates component auto-registration
    """
    
    @staticmethod
    def component(id: Optional[str] = None, 
                 name: Optional[str] = None,
                 description: Optional[str] = None):
        """
        Decorator for component classes.
        
        Args:
            id: Optional component ID
            name: Optional display name
            description: Optional description
            
        Returns:
            Decorator function
        """
        def decorator(cls: Type[T]) -> Type[T]:
            # Create or update metadata
            metadata = ComponentMetadata(
                component_type=cls,
                name=name or cls.__name__,
                description=description or cls.__doc__ or ""
            )
            
            # Store metadata on the class
            setattr(cls, '__metadata__', metadata)
            
            # Create custom __init__ that sets ID and name
            original_init = cls.__init__
            
            def new_init(self, *args, **kwargs):
                # Call original __init__
                original_init(self, *args, **kwargs)
                
                # Set ID and name if not set by __init__
                if hasattr(self, '_id') and not self._id:
                    self._id = id or cls.__name__
                if hasattr(self, '_name') and not self._name:
                    self._name = name or cls.__name__
                
            cls.__init__ = new_init
            
            return cls
        
        return decorator
    
    @staticmethod
    def dependency(dependency_id: str):
        """
        Decorator for declaring dependencies.
        
        Args:
            dependency_id: ID of the dependency
            
        Returns:
            Decorator function
        """
        def decorator(cls: Type[T]) -> Type[T]:
            # Get or create metadata
            metadata = getattr(cls, '__metadata__', None)
            if metadata is None:
                metadata = ComponentMetadata(component_type=cls)
                setattr(cls, '__metadata__', metadata)
                
            # Add dependency
            metadata.add_dependency(dependency_id)
            
            return cls
        
        return decorator
    
    @staticmethod
    def config(key: str, value: Any):
        """
        Decorator for setting component configuration.
        
        Args:
            key: Configuration key
            value: Configuration value
            
        Returns:
            Decorator function
        """
        def decorator(cls: Type[T]) -> Type[T]:
            # Get or create metadata
            metadata = getattr(cls, '__metadata__', None)
            if metadata is None:
                metadata = ComponentMetadata(component_type=cls)
                setattr(cls, '__metadata__', metadata)
                
            # Set configuration
            metadata.set_config(key, value)
            
            return cls
        
        return decorator


def autowired(target_class: Optional[Type] = None):
    """
    Decorator for autowiring dependencies.
    
    Args:
        target_class: Optional target class for the dependency
        
    Returns:
        Decorator function
    """
    def decorator(func_or_class):
        if inspect.isclass(func_or_class):
            # Class decorator
            cls = func_or_class
            
            # Store original __init__
            original_init = cls.__init__
            
            def new_init(self, *args, **kwargs):
                # Call original __init__
                original_init(self, *args, **kwargs)
                
                # Autowire dependencies
                for name, value in cls.__annotations__.items():
                    if hasattr(value, '__origin__') and issubclass(value.__origin__, IComponent):
                        # This is a potential dependency
                        component_type = value.__args__[0] if hasattr(value, '__args__') else None
                        
                        # Skip if already set
                        if hasattr(self, name) and getattr(self, name) is not None:
                            continue
                            
                        # Skip if we don't have a provider
                        if not hasattr(self, '__provider__'):
                            continue
                            
                        provider = getattr(self, '__provider__')
                        if not provider or not isinstance(provider, ComponentProvider):
                            continue
                            
                        # Get dependency
                        dependency = provider.get(name)
                        if dependency is None and component_type:
                            # Try to create it
                            try:
                                dependency = provider.create(component_type)
                            except Exception:
                                pass
                                
                        if dependency:
                            setattr(self, name, dependency)
                            
            cls.__init__ = new_init
            return cls
        else:
            # Method or property decorator
            return func_or_class
            
    # Handle case where decorator is used without parentheses
    if target_class is not None and callable(target_class) and not isinstance(target_class, type):
        return decorator(target_class)
        
    return decorator