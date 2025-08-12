"""
Factory Pattern Implementation for RV-Experiment Phase 8 Clean Architecture

### Architectural Overview:
This module implements factory patterns for component creation in the Phase 8 clean
architecture, eliminating complex coordination patterns in favor of simple, factory-based
component creation with just-in-time configuration and DI-ready design.

### Key Features:
- **Factory Pattern**: Clean component creation through factory methods
- **Just-in-Time Configuration**: Components configured only when created
- **DI-Ready Design**: Structure optimized for dependency injection containers
- **Module Independence**: Maintains module independence through simple parameter passing
- **English Documentation**: Comprehensive architectural comments in English

### Factory Types:
- ExperimentFactory: Creates and configures experiment components
- ConfigurationFactory: Creates configuration instances for different scenarios
- ComponentFactory: Creates sub-module components with just-in-time configuration
- RvAndroidConfigFactory: Creates RVAndroid tool configurations with hybrid variant system

### Role in the System:
- Provides clean component creation patterns for experiment orchestration
- Eliminates complex coordination and ComponentConfigurator patterns
- Enables dependency injection preparation and container integration
- Maintains module independence through factory-based component creation
"""

from .configuration_factory import ConfigurationFactory

__all__ = [
    'ConfigurationFactory'
]