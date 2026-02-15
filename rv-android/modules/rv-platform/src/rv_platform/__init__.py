"""
RV-Platform - Central execution engine for Android testing experiments.

Registers external tools (rvagent) into the rv-tools registry on import
so they are available for both rv-platform standalone and rv-experiment usage.
"""

import logging

from rv_tools import ToolRegistry


def _register_external_tools():
    """Register external tools that are not part of rv-tools builtins."""
    registry = ToolRegistry.get_instance()

    # Register RVAgent tool if available and not already registered
    if not registry.is_tool_registered("rvagent"):
        try:
            from rvagent_tool.tools.rvagent.tool import RVAgentTool
            registry.register_tool_class(RVAgentTool)
        except ImportError as e:
            logging.getLogger(__name__).warning(f"rvagent tool not available: {e}")
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to register rvagent tool: {e}")


_register_external_tools()
