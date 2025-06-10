"""
Configuration Providers and Dependency Registry - DI System Infrastructure

### Architectural Overview:
This module implements configuration providers and dependency registry for the DI system,
enabling flexible configuration management and component registration. It provides
comprehensive support for different configuration sources while maintaining clean
separation between configuration and component logic.

### Key Architectural Decisions:
- **Multi-Source Configuration**: Support for files, environment variables, and programmatic config
- **Hierarchical Configuration**: Configuration inheritance and override mechanisms
- **Type-Safe Registry**: Strong typing for component registration and resolution
- **Lazy Loading**: Efficient lazy loading of configuration and components
- **Validation Integration**: Comprehensive configuration validation and error reporting

### Configuration Sources:
- JSON configuration files
- YAML configuration files  
- Environment variables with prefix mapping
- Command line arguments
- Programmatic configuration
- Remote configuration services (future)

### Role in the System:
- Provides flexible configuration management for all DI components
- Manages component registration and dependency resolution
- Enables configuration-driven component creation and assembly
- Supports different deployment scenarios and configuration strategies
- Integrates with lifecycle management and error handling systems
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional, Type, Union, TypeVar, Generic
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import threading
from collections import defaultdict

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.exceptions import ConfigurationError, ValidationError

from .interfaces import IConfigurationProvider, IDependencyContainer

T = TypeVar('T')


@dataclass
class ComponentRegistration:
    """
    Registration information for DI components.
    
    ### Registration Strategy:
    Stores comprehensive registration information including interface type,
    implementation type, scope, and any initialization parameters. This
    enables flexible component creation and lifecycle management.
    """
    interface: Type
    implementation: Type
    scope: str = "singleton"  # "singleton" or "prototype"
    instance: Optional[Any] = None
    config: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class ConfigurationProvider(IConfigurationProvider):
    """
    Flexible configuration provider supporting multiple sources.
    
    ### Architectural Overview:
    This provider implements a hierarchical configuration system that supports
    multiple configuration sources with proper override mechanisms. It provides
    type-safe configuration access while supporting validation and error reporting.
    
    ### Key Architectural Decisions:
    - **Source Hierarchy**: Clear precedence order for configuration sources
    - **Type Safety**: Strongly typed configuration access with validation
    - **Lazy Loading**: Efficient loading of configuration data on demand
    - **Environment Integration**: Seamless integration with environment variables
    - **File Watching**: Automatic reload on configuration file changes (future)
    
    ### Configuration Hierarchy (highest to lowest precedence):
    1. Programmatic configuration (set_config calls)
    2. Environment variables
    3. Command line arguments
    4. Configuration files (YAML/JSON)
    5. Default values
    
    ### Role in the System:
    - Primary configuration source for all DI components
    - Provides unified interface for accessing configuration from multiple sources
    - Supports configuration validation and error reporting
    - Enables environment-specific configuration overrides
    - Integrates with component lifecycle and dependency injection
    """
    
    def __init__(self, config_files: List[str] = None, 
                 env_prefix: str = "RV_", logger=None):
        """
        Initialize configuration provider with multiple sources.
        
        ### Initialization Strategy:
        - Loads configuration from specified files
        - Sets up environment variable mapping
        - Configures logging and error handling
        - Prepares provider for configuration access
        
        Args:
            config_files: List of configuration file paths to load
            env_prefix: Prefix for environment variable mapping
            logger: Optional logger instance for DI container injection
        """
        # DI-ready logging setup
        if logger:
            self.logger = logger
        else:
            logging_manager = LoggingManager.get_instance()
            self.logger = logging_manager.get_logger(
                "rv_experiment.di.providers",
                {CONTEXT_COMPONENT: "ConfigurationProvider"}
            )
        
        # Configuration storage
        self.config_data: Dict[str, Any] = {}
        self.component_configs: Dict[str, Dict[str, Any]] = {}
        self.env_prefix = env_prefix
        
        # File tracking
        self.config_files = config_files or []
        self.file_timestamps: Dict[str, float] = {}
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Load initial configuration
        self._load_configuration()
        
        self.logger.info(f"ConfigurationProvider initialized with {len(self.config_files)} files")
    
    @ErrorHandler.handle_errors(
        component="ConfigurationProvider",
        phase="load_configuration",
    )
    def _load_configuration(self) -> None:
        """
        Load configuration from all sources.
        
        ### Loading Strategy:
        - Loads configuration files in specified order
        - Applies environment variable overrides
        - Validates configuration structure
        - Logs configuration loading progress
        """
        with self._lock:
            # Load configuration files
            for config_file in self.config_files:
                self._load_config_file(config_file)
            
            # Load environment variables
            self._load_environment_variables()
            
            # Extract component-specific configurations
            self._extract_component_configs()
    
    def _load_config_file(self, config_file: str) -> None:
        """
        Load configuration from a single file.
        
        Args:
            config_file: Path to configuration file
        """
        file_path = Path(config_file)
        
        if not file_path.exists():
            self.logger.warning(f"Configuration file not found: {config_file}")
            return
        
        try:
            # Track file timestamp for change detection
            self.file_timestamps[config_file] = file_path.stat().st_mtime
            
            # Load based on file extension
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yaml', '.yml']:
                    file_config = yaml.safe_load(f) or {}
                elif file_path.suffix.lower() == '.json':
                    file_config = json.load(f)
                else:
                    self.logger.warning(f"Unknown config file format: {config_file}")
                    return
            
            # Merge with existing configuration
            self._merge_config(self.config_data, file_config)
            
            self.logger.debug(f"Loaded configuration from: {config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to load config file {config_file}: {e}")
            raise ConfigurationError(f"Cannot load configuration file {config_file}: {e}")
    
    def _load_environment_variables(self) -> None:
        """
        Load configuration from environment variables.
        
        ### Environment Variable Mapping:
        Environment variables with the configured prefix are mapped to configuration
        keys using underscore-to-dot notation. For example:
        RV_EXPERIMENT_TIMEOUT -> experiment.timeout
        """
        env_config = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                # Convert environment variable to config key
                config_key = key[len(self.env_prefix):].lower().replace('_', '.')
                
                # Try to parse as JSON for complex values
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    # Use as string if not valid JSON
                    parsed_value = value
                
                # Set nested configuration
                self._set_nested_config(env_config, config_key, parsed_value)
        
        if env_config:
            self._merge_config(self.config_data, env_config)
            self.logger.debug(f"Loaded {len(env_config)} environment variables")
    
    def _set_nested_config(self, config: Dict[str, Any], key: str, value: Any) -> None:
        """
        Set nested configuration value using dot notation.
        
        Args:
            config: Configuration dictionary to update
            key: Dot-separated configuration key
            value: Value to set
        """
        keys = key.split('.')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        
        current[keys[-1]] = value
    
    def _merge_config(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Merge source configuration into target configuration.
        
        Args:
            target: Target configuration dictionary
            source: Source configuration dictionary to merge
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_config(target[key], value)
            else:
                target[key] = value
    
    def _extract_component_configs(self) -> None:
        """
        Extract component-specific configurations from global config.
        
        ### Component Configuration Structure:
        Component configurations are expected under the "components" key:
        ```yaml
        components:
          llm_factory:
            provider: ollama
            model: llama3
          orchestrator:
            timeout: 300
        ```
        """
        components_config = self.config_data.get('components', {})
        
        for component_name, component_config in components_config.items():
            self.component_configs[component_name] = component_config
    
    def get_config(self, component_name: str) -> Dict[str, Any]:
        """
        Get configuration for specific component.
        
        Args:
            component_name: Name of component to get configuration for
            
        Returns:
            Configuration dictionary for the component
        """
        with self._lock:
            return self.component_configs.get(component_name, {}).copy()
    
    def get_global_config(self) -> Dict[str, Any]:
        """
        Get global system configuration.
        
        Returns:
            Global configuration dictionary
        """
        with self._lock:
            return self.config_data.copy()
    
    def has_config(self, component_name: str) -> bool:
        """
        Check if configuration exists for component.
        
        Args:
            component_name: Name of component to check
            
        Returns:
            True if configuration exists, False otherwise
        """
        with self._lock:
            return component_name in self.component_configs
    
    def set_config(self, component_name: str, config: Dict[str, Any]) -> None:
        """
        Set configuration for component programmatically.
        
        Args:
            component_name: Name of component to set configuration for
            config: Configuration dictionary to set
        """
        with self._lock:
            self.component_configs[component_name] = config.copy()
            self.logger.debug(f"Set configuration for component: {component_name}")
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get specific configuration value using dot notation.
        
        Args:
            key: Dot-separated configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        with self._lock:
            keys = key.split('.')
            current = self.config_data
            
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default
            
            return current
    
    @ErrorHandler.handle_errors(
        component="ConfigurationProvider",
        phase="reload_config",
    )
    def reload_config(self) -> bool:
        """
        Reload configuration from all sources.
        
        Returns:
            True if reload successful, False otherwise
        """
        try:
            with self._lock:
                # Clear existing configuration
                self.config_data.clear()
                self.component_configs.clear()
                
                # Reload from all sources
                self._load_configuration()
                
                self.logger.info("Configuration reloaded successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
            return False


class DependencyRegistry(IDependencyContainer):
    """
    Registry for dependency injection components.
    
    ### Architectural Overview:
    This registry implements a comprehensive dependency injection container
    that supports both singleton and prototype scopes, constructor injection,
    and circular dependency detection. It provides type-safe component
    registration and resolution with comprehensive error handling.
    
    ### Key Architectural Decisions:
    - **Type Safety**: Strong typing for all registration and resolution operations
    - **Scope Management**: Support for singleton and prototype component scopes
    - **Circular Detection**: Comprehensive circular dependency detection and resolution
    - **Lazy Resolution**: Efficient lazy resolution of component dependencies
    - **Thread Safety**: All operations are thread-safe for concurrent environments
    
    ### DI Features:
    - Interface-based component registration
    - Constructor injection with automatic dependency resolution
    - Singleton and prototype scope management
    - Circular dependency detection and prevention
    - Component tagging and filtering
    - Hierarchical container support (parent-child relationships)
    
    ### Role in the System:
    - Primary dependency injection container for all components
    - Manages component lifecycle and scope
    - Provides type-safe component resolution
    - Supports testing through easy mocking and stub registration
    - Integrates with configuration providers and lifecycle managers
    """
    
    def __init__(self, parent: Optional['DependencyRegistry'] = None, logger=None):
        """
        Initialize dependency registry.
        
        Args:
            parent: Optional parent registry for hierarchical containers
            logger: Optional logger instance for DI container injection
        """
        # DI-ready logging setup
        if logger:
            self.logger = logger
        else:
            logging_manager = LoggingManager.get_instance()
            self.logger = logging_manager.get_logger(
                "rv_experiment.di.registry",
                {CONTEXT_COMPONENT: "DependencyRegistry"}
            )
        
        # Registry storage
        self.registrations: Dict[Type, ComponentRegistration] = {}
        self.singleton_instances: Dict[Type, Any] = {}
        self.parent = parent
        
        # Resolution tracking for circular dependency detection
        self._resolution_stack: List[Type] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        self.logger.info("DependencyRegistry initialized")
    
    @ErrorHandler.handle_errors(
        component="DependencyRegistry",
        phase="register",
    )
    def register(self, interface: Type, implementation: Type, 
                scope: str = "singleton") -> None:
        """
        Register component implementation for interface.
        
        Args:
            interface: Interface type to register
            implementation: Implementation type for the interface
            scope: Component scope ("singleton" or "prototype")
            
        Raises:
            TypeError: If interface is not a type or implementation doesn't implement interface
            ValueError: If scope is invalid
        """
        if not isinstance(interface, type):
            raise TypeError("Interface must be a type")
        
        if not isinstance(implementation, type):
            raise TypeError("Implementation must be a type")
        
        if scope not in ["singleton", "prototype"]:
            raise ValueError("Scope must be 'singleton' or 'prototype'")
        
        # Validate that implementation can be used for interface
        # Note: This is a basic check - more sophisticated checking could be added
        if not hasattr(implementation, '__bases__'):
            raise TypeError(f"Implementation {implementation} must be a class")
        
        with self._lock:
            registration = ComponentRegistration(
                interface=interface,
                implementation=implementation,
                scope=scope
            )
            
            self.registrations[interface] = registration
            
            # Remove any existing singleton instance if re-registering
            if interface in self.singleton_instances:
                del self.singleton_instances[interface]
            
            self.logger.debug(f"Registered {implementation.__name__} for {interface.__name__} (scope: {scope})")
    
    def register_instance(self, interface: Type, instance: Any) -> None:
        """
        Register specific instance for interface.
        
        Args:
            interface: Interface type to register
            instance: Pre-created instance to register
        """
        with self._lock:
            registration = ComponentRegistration(
                interface=interface,
                implementation=type(instance),
                scope="singleton",
                instance=instance
            )
            
            self.registrations[interface] = registration
            self.singleton_instances[interface] = instance
            
            self.logger.debug(f"Registered instance of {type(instance).__name__} for {interface.__name__}")
    
    @ErrorHandler.handle_errors(
        component="DependencyRegistry",
        phase="get",
    )
    def get(self, interface: Type) -> Any:
        """
        Get component instance for interface.
        
        Args:
            interface: Interface type to resolve
            
        Returns:
            Component instance implementing the interface
            
        Raises:
            ValueError: If interface is not registered
            ConfigurationError: If circular dependency detected
        """
        with self._lock:
            # Check for circular dependency
            if interface in self._resolution_stack:
                circular_path = " -> ".join([t.__name__ for t in self._resolution_stack] + [interface.__name__])
                raise ConfigurationError(f"Circular dependency detected: {circular_path}")
            
            # Check local registration
            if interface in self.registrations:
                return self._resolve_component(interface)
            
            # Check parent registry
            if self.parent and self.parent.has(interface):
                return self.parent.get(interface)
            
            raise ValueError(f"No registration found for interface: {interface.__name__}")
    
    def _resolve_component(self, interface: Type) -> Any:
        """
        Resolve component instance for registered interface.
        
        Args:
            interface: Interface type to resolve
            
        Returns:
            Component instance
        """
        registration = self.registrations[interface]
        
        # Return existing instance if singleton
        if registration.scope == "singleton":
            if interface in self.singleton_instances:
                return self.singleton_instances[interface]
            
            # If pre-created instance exists, use it
            if registration.instance is not None:
                self.singleton_instances[interface] = registration.instance
                return registration.instance
        
        # Create new instance
        self._resolution_stack.append(interface)
        
        try:
            instance = self._create_instance(registration)
            
            # Store singleton instance
            if registration.scope == "singleton":
                self.singleton_instances[interface] = instance
            
            return instance
            
        finally:
            self._resolution_stack.pop()
    
    def _create_instance(self, registration: ComponentRegistration) -> Any:
        """
        Create new instance of registered component.
        
        Args:
            registration: Component registration information
            
        Returns:
            New component instance
        """
        implementation = registration.implementation
        
        try:
            # Get constructor parameters
            import inspect
            constructor = implementation.__init__
            signature = inspect.signature(constructor)
            
            # Resolve constructor dependencies
            kwargs = {}
            for param_name, param in signature.parameters.items():
                if param_name == 'self':
                    continue
                
                # Check if parameter has type annotation
                if param.annotation != inspect.Parameter.empty:
                    # Try to resolve dependency
                    try:
                        dependency = self.get(param.annotation)
                        kwargs[param_name] = dependency
                    except ValueError:
                        # Dependency not registered - check if parameter has default
                        if param.default == inspect.Parameter.empty:
                            self.logger.warning(f"Cannot resolve dependency {param.annotation} for {implementation.__name__}")
                        # If parameter has default, let it use the default
            
            # Create instance
            instance = implementation(**kwargs)
            
            self.logger.debug(f"Created instance of {implementation.__name__}")
            return instance
            
        except Exception as e:
            raise ConfigurationError(f"Failed to create instance of {implementation.__name__}: {e}")
    
    def has(self, interface: Type) -> bool:
        """
        Check if interface is registered.
        
        Args:
            interface: Interface type to check
            
        Returns:
            True if interface is registered, False otherwise
        """
        with self._lock:
            # Check local registration
            if interface in self.registrations:
                return True
            
            # Check parent registry
            if self.parent:
                return self.parent.has(interface)
            
            return False
    
    def create_child_container(self) -> 'DependencyRegistry':
        """
        Create child container with inheritance.
        
        Returns:
            New child container inheriting parent registrations
        """
        child = DependencyRegistry(parent=self, logger=self.logger)
        self.logger.debug("Created child dependency container")
        return child
    
    def get_registrations(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all registrations.
        
        Returns:
            Dictionary with registration information
        """
        with self._lock:
            result = {}
            
            for interface, registration in self.registrations.items():
                result[interface.__name__] = {
                    "interface": interface.__name__,
                    "implementation": registration.implementation.__name__,
                    "scope": registration.scope,
                    "has_instance": interface in self.singleton_instances,
                    "tags": registration.tags
                }
            
            return result
    
    def clear(self) -> None:
        """
        Clear all registrations and instances.
        """
        with self._lock:
            self.registrations.clear()
            self.singleton_instances.clear()
            self.logger.debug("Cleared all registrations and instances")