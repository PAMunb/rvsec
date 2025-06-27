# rvandroid/experiment/workflow/registry.py
"""
Component registry for dynamic component management in workflows.

This module provides a flexible registry system for workflow components,
enabling dynamic component discovery, registration, and retrieval. It supports
dependency management and configuration for components.
"""

import importlib
import inspect
import logging
import pkgutil
from typing import Dict, List, Any, Type, Optional, TypeVar, Generic, cast, Set, Callable

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_experiment.experiment.workflow.components import IComponent, ComponentMetadata

T = TypeVar('T', bound=IComponent)


class ComponentRegistry(Generic[T]):
    """
    Dynamic registry for workflow components.
    
    ### Architectural Decisions:
    - Implements a flexible registry pattern for component management
    - Supports dynamic component discovery and registration
    - Enables dependency injection and component configuration
    - Provides runtime component resolution
    
    ### Role in the System:
    - Serves as a central registry for workflow components
    - Provides dynamic component discovery and management
    - Enables flexible component composition
    - Supports dependency injection in the workflow architecture
    """

    def __init__(self, component_base_type: Type[T]):
        """
        Initialize the component registry.
        
        Args:
            component_base_type: Base type for components in this registry
        """
        self.component_base_type = component_base_type
        self.components: Dict[str, T] = {}
        self.component_types: Dict[str, Type[T]] = {}
        self.logger = logging.getLogger(__name__)
        self.dependencies: Dict[str, Set[str]] = {}
        self.factory_functions: Dict[str, Callable[..., T]] = {}

    def register(self, component: T, name: Optional[str] = None) -> str:
        """
        Register a component instance with the registry.
        
        Args:
            component: Component to register
            name: Optional name for the component (defaults to component ID)
            
        Returns:
            ID under which the component was registered
        """
        # Check component type
        if not isinstance(component, self.component_base_type):
            raise TypeError(f"Component {component} must be an instance of {self.component_base_type.__name__}")

        # Get component ID - use explicit ID if component has one
        component_id = name or component.id

        # Register component
        self.components[component_id] = component

        # Register dependencies if component has them
        if hasattr(component, 'dependencies'):
            self.dependencies[component_id] = component.dependencies

        self.logger.debug(f"Registered component: {component_id}")

        return component_id

    def register_type(self, component_type: Type[T], name: Optional[str] = None) -> str:
        """
        Register a component type with the registry.
        
        Args:
            component_type: Component type to register
            name: Optional name for the component type (defaults to class name)
            
        Returns:
            ID under which the component type was registered
        """
        # Check component type
        if not issubclass(component_type, self.component_base_type):
            raise TypeError(
                f"Component type {component_type} must be a subclass of {self.component_base_type.__name__}")

        # Get component ID - use metadata if available
        component_id = name
        if not component_id:
            # Check for metadata
            if hasattr(component_type, '__metadata__'):
                metadata = getattr(component_type, '__metadata__')
                if isinstance(metadata, ComponentMetadata):
                    component_id = metadata.name

            # Fall back to class name
            if not component_id:
                component_id = component_type.__name__

        # Register component type
        self.component_types[component_id] = component_type

        # Register dependencies if component has them
        if hasattr(component_type, '__metadata__'):
            metadata = getattr(component_type, '__metadata__')
            if isinstance(metadata, ComponentMetadata) and metadata.dependencies:
                self.dependencies[component_id] = metadata.dependencies

        self.logger.debug(f"Registered component type: {component_id}")

        return component_id

    def register_factory(self, factory: Callable[..., T], name: str) -> str:
        """
        Register a factory function for creating components.
        
        Args:
            factory: Factory function that creates components
            name: Name for the component created by this factory
            
        Returns:
            Name under which the factory was registered
        """
        self.factory_functions[name] = factory
        self.logger.debug(f"Registered component factory: {name}")

        return name

    def unregister(self, name: str) -> bool:
        """
        Unregister a component from the registry.
        
        Args:
            name: Name of the component to unregister
            
        Returns:
            True if the component was unregistered, False if not found
        """
        if name in self.components:
            del self.components[name]
            self.logger.debug(f"Unregistered component: {name}")

            # Clean up dependencies
            if name in self.dependencies:
                del self.dependencies[name]

            # Remove this component from other components' dependencies
            for deps in self.dependencies.values():
                if name in deps:
                    deps.remove(name)

            return True

        elif name in self.component_types:
            del self.component_types[name]
            self.logger.debug(f"Unregistered component type: {name}")
            return True

        elif name in self.factory_functions:
            del self.factory_functions[name]
            self.logger.debug(f"Unregistered component factory: {name}")
            return True

        return False

    def get(self, name: str, create_if_missing: bool = False, **kwargs) -> Optional[T]:
        """
        Get a component by name, optionally creating it if it doesn't exist.
        
        Args:
            name: Name of the component to retrieve
            create_if_missing: Whether to create the component if it doesn't exist
            **kwargs: Arguments to pass to the component constructor if creating
            
        Returns:
            Component instance, or None if not found and not creating
        """
        # Check if component already exists
        if name in self.components:
            return self.components[name]

        # Check if we should create the component
        if create_if_missing:
            # Try to create from type
            if name in self.component_types:
                component_type = self.component_types[name]
                component = self._create_component(component_type, **kwargs)
                self.components[name] = component
                return component

            # Try to create from factory
            elif name in self.factory_functions:
                factory = self.factory_functions[name]
                component = factory(**kwargs)
                self.components[name] = component
                return component

        return None

    def get_all(self) -> List[T]:
        """
        Get all registered components.
        
        Returns:
            List of all component instances
        """
        return list(self.components.values())

    def get_by_type(self, component_type: Type[Any]) -> List[T]:
        """
        Get all components that are instances of the specified type.
        
        Args:
            component_type: Type to filter by
            
        Returns:
            List of matching components
        """
        return [c for c in self.components.values() if isinstance(c, component_type)]

    def set_dependencies(self, component_name: str, dependencies: List[str]) -> None:
        """
        Set the dependencies for a component.
        
        Args:
            component_name: Name of the component
            dependencies: List of dependency component names
        """
        self.dependencies[component_name] = set(dependencies)

    def get_dependencies(self, component_name: str) -> List[str]:
        """
        Get the dependencies for a component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            List of dependency component names
        """
        return list(self.dependencies.get(component_name, set()))

    def create_with_dependencies(self, name: str, **kwargs) -> T:
        """
        Create a component and all its dependencies.
        
        Args:
            name: Name of the component to create
            **kwargs: Additional arguments for component creation
            
        Returns:
            Created component
        """
        # Check if component already exists
        if name in self.components:
            return self.components[name]

        # Check if we can create this component
        if name not in self.component_types and name not in self.factory_functions:
            raise ValueError(f"No component type or factory registered for: {name}")

        # Get dependencies
        dependencies = self.get_dependencies(name)

        # Create dependencies first
        for dep_name in dependencies:
            self.create_with_dependencies(dep_name, **kwargs)

        # Now create the component
        component = self.get(name, create_if_missing=True, **kwargs)

        if component is None:
            raise ValueError(f"Failed to create component: {name}")

        return component

    def load_components_by_scanning(self, module_or_package,
                                    predicate: Optional[Callable[[Type[Any]], bool]] = None) -> int:
        """
        Scan a module or package for components and register them.
        
        Args:
            module_or_package: Module or package to scan
            predicate: Optional function to filter component types
            
        Returns:
            Number of components registered
        """
        registered_count = 0

        # Define default predicate if not provided
        if predicate is None:
            predicate = lambda cls: (
                    inspect.isclass(cls) and
                    issubclass(cls, self.component_base_type) and
                    cls != self.component_base_type and
                    not inspect.isabstract(cls)
            )

        # Scan module for component types
        for name, obj in inspect.getmembers(module_or_package):
            if inspect.isclass(obj) and predicate(obj):
                try:
                    # Check if class has the component decorator
                    has_decorator = hasattr(obj, '__metadata__')

                    # Register the component type
                    self.register_type(cast(Type[T], obj))
                    registered_count += 1

                    # Log if component was registered without decorator
                    if not has_decorator:
                        self.logger.debug(f"Component {obj.__name__} registered without @component decorator")

                except TypeError:
                    self.logger.debug(f"Failed to register {obj.__name__}: not a valid component type")
                except Exception as e:
                    error_handler = ErrorHandler.get_instance()
                    error_context = {
                        "component": "ComponentRegistry",
                        "operation": "component_registration",
                        "component_name": obj.__name__,
                        "module": module_or_package.__name__
                    }
                    error_handler.handle_error(e, error_context)

        self.logger.info(f"Registered {registered_count} components from {module_or_package.__name__}")
        return registered_count

    def _create_component(self, component_type: Type[T], **kwargs) -> T:
        """
        Create a component instance from its type.
        
        Args:
            component_type: Type of component to create
            **kwargs: Arguments to pass to constructor
            
        Returns:
            Created component instance
        """
        try:
            # Check for metadata to use for creation
            config = {}
            if hasattr(component_type, '__metadata__'):
                metadata = getattr(component_type, '__metadata__')
                if isinstance(metadata, ComponentMetadata) and metadata.config:
                    config = metadata.config.copy()

            # Merge with provided kwargs
            if 'config' in kwargs:
                if config:
                    merged_config = config.copy()
                    merged_config.update(kwargs['config'])
                    kwargs['config'] = merged_config
            elif config:
                kwargs['config'] = config

            # Create component instance
            component = component_type(**kwargs)

            # Configure component if needed
            if hasattr(component, 'configure') and 'config' in kwargs:
                component.configure(kwargs['config'])

            return component
        except Exception as e:
            error_handler = ErrorHandler.get_instance()
            error_context = {
                "component": "ComponentRegistry",
                "operation": "component_creation",
                "component_type": component_type.__name__,
                "kwargs": list(kwargs.keys())
            }
            error_handler.handle_error(e, error_context)
            raise

    def discover_components(self, package_name: str) -> int:
        """
        Discover components in a package and its subpackages.
        
        Args:
            package_name: Name of the package to scan
            
        Returns:
            Number of components registered
        """
        try:
            package = importlib.import_module(package_name)
        except ImportError:
            self.logger.error(f"Failed to import package: {package_name}")
            return 0

        registered_count = 0

        # Register components in main package
        registered_count += self.load_components_by_scanning(package)

        # Scan subpackages recursively
        if hasattr(package, '__path__'):
            for _, subpackage_name, is_pkg in pkgutil.iter_modules(package.__path__, package.__name__ + '.'):
                if is_pkg:
                    registered_count += self.discover_components(subpackage_name)
                else:
                    try:
                        module = importlib.import_module(subpackage_name)
                        registered_count += self.load_components_by_scanning(module)
                    except ImportError:
                        self.logger.warning(f"Failed to import module: {subpackage_name}")

        return registered_count
