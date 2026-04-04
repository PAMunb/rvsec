"""
RV-Tools Module

Tool registry and plugin system for monitored operations testing in RV-Android.

This module provides comprehensive tool management capabilities including:
- Abstract base classes for tool implementations
- Plugin discovery and registration system
- Built-in testing tools (APE, DroidBot, Monkey, etc.)
- External tool plugin interfaces
- Configuration and variant management

### Key Components:

#### Base Classes:
- **AbstractTool**: Base abstraction for all testing tools
- **ConfigurableTool**: Enhanced tool base with configuration support
- **ToolSpec**: Tool specification and metadata management

#### Registry System:
- **ToolRegistry**: Central registry for tool discovery and access
- **ToolFactory**: Factory for creating configured tool instances
- **PluginLoader**: Plugin discovery and loading system

#### Plugin System:
- **ToolPlugin**: Interface for external tool plugins
- **PluginManager**: Lifecycle management for plugins
- **ExperimentToolManager**: Tool coordination for experiments

### Architectural Principles:
- **Plugin Architecture**: Extensible system for external tools
- **Configuration Management**: Rich configuration and variant support
- **Dependency Injection**: Flexible tool composition and setup
- **Registry Pattern**: Centralized tool discovery and management
- **Factory Pattern**: Consistent tool creation and configuration
- **Template Method**: Standardized tool execution workflow

### Integration Points:
- **rv-android-core**: Base infrastructure, error handling, logging
- **External Modules**: Plugin registration via entry points
- **Experiment Framework**: Tool selection and execution coordination
"""

# Core base classes
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec

# Factory system
from .registry.factory import ToolFactory

# Registry system
from .registry.registry import ToolRegistry


# Auto-register built-in tools
def _register_builtin_tools():
    """Auto-register all built-in tools when module is imported."""
    try:
        from .builtin import BUILTIN_TOOLS
        from .registry.registry import ToolRegistry

        registry = ToolRegistry.get_instance()

        for tool_class in BUILTIN_TOOLS:
            try:
                # Register tool class (this will also register the tool spec)
                registry.register_tool_class(tool_class)

            except Exception as e:
                # Log error but don't fail module import
                import logging

                logging.getLogger(__name__).warning(
                    f"Failed to register builtin tool {tool_class.__name__}: {e}"
                )

    except Exception:
        # Fail silently if builtin tools can't be imported
        pass


# Auto-register when module is imported
_register_builtin_tools()

__version__ = "0.1.0"
__all__ = [
    # Base classes
    "AbstractTool",
    "ToolSpec",
    # Registry system
    "ToolRegistry",
    "ToolFactory",
]
