"""
Dependency Injection Interfaces - Phase 8 Modern Architecture

### Architectural Overview:
This module provides dependency injection interfaces and lifecycle management
for the modernized Phase 8 architecture. It defines clean contracts for
component creation, configuration, and lifecycle management while preparing
the system for future DI container integration.

### Key Architectural Decisions:
- **Interface-Based Design**: All components implement clean interfaces
- **Lifecycle Management**: Comprehensive component lifecycle support
- **Factory Integration**: Seamless integration with modern factory pattern
- **Configuration-Driven**: All components configurable through dependency injection
- **Future-Ready**: Prepared for integration with DI containers (Spring, etc.)

### DI Container Preparation:
- Clear separation between interfaces and implementations
- Constructor injection patterns throughout the system
- Minimal coupling between components
- Comprehensive error handling and logging integration
- Support for both singleton and prototype component scopes

### Role in the System:
- Defines contracts for all major system components
- Enables clean testing through interface mocking
- Prepares architecture for enterprise DI container integration
- Supports configuration-driven component creation
- Provides lifecycle management for complex component hierarchies
"""

from .interfaces import (
    IExperimentOrchestrator,
    IExperimentConfig,
    IDirectoryManager,
    IComponentLifecycle,
    IConfigurationProvider,
    IDependencyContainer
)

from .lifecycle import (
    ComponentLifecycleManager,
    LifecycleState,
    LifecycleEvent
)

from .providers import (
    ConfigurationProvider,
    DependencyRegistry
)

__all__ = [
    # Core interfaces
    'IExperimentOrchestrator',
    'IExperimentConfig', 
    'IDirectoryManager',
    'IComponentLifecycle',
    'IConfigurationProvider',
    'IDependencyContainer',
    
    # Lifecycle management
    'ComponentLifecycleManager',
    'LifecycleState',
    'LifecycleEvent',
    
    # Configuration providers
    'ConfigurationProvider',
    'DependencyRegistry'
]