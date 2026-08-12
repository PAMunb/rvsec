"""
RV-Tools Module

Tool registry and variant system for the testing tools RV-Android drives.

### Key Components:

#### Base Classes (re-exported from rv-android-core):
- **AbstractTool**: Base abstraction for all testing tools
- **ToolSpec**: Tool specification and metadata management

#### Registry System:
- **ToolRegistry**: Singleton registry of tool classes, specs and variants
- **ToolFactory**: Builds a configured tool instance from a `ToolConfig`, merging
  the named variant's defaults with the caller's parameter overrides

### Registration:

- **Built-in tools**: `_register_builtin_tools()` runs at import and registers every
  class in `BUILTIN_TOOLS`. A tool whose registration raises is logged and skipped, so
  one broken tool never blocks the import.
- **External tools**: tools that live in their own modules (`rvagent-tool`, `aperv-tool`)
  are registered by `_register_external_tools()` in `rv_platform/__init__.py` — not here,
  and not by entry-point discovery. Registering them here would make rv-tools depend on
  rv-agent and its LLM stack; pushing that import up to rv-platform is what keeps
  rv-tools' only dependency at rv-android-core (openspec `tools` spec, INV-TOOL-12).

### Architectural Principles:
- **Registry Pattern**: one singleton is the source of truth for available tools
- **Factory Pattern**: variant defaults merged with user parameters at creation time
- **Template Method**: `AbstractTool.execute()` standardizes timeout handling and cleanup

### Integration Points:
- **rv-android-core**: Base infrastructure, error handling, logging
- **rv-platform / rv-experiment**: tool selection and task execution
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
