# rvandroid/tools/registry.py
"""
Tool registry for managing and accessing tool instances across the application.
Provides a singleton registry that can be accessed from any module.
"""
from typing import Dict, List, Optional

from rvandroid.tools.tool_spec import AbstractTool


class ToolRegistry:
    """
    Singleton registry for accessing tool instances across the application.
    This avoids having to pass tool instances around or import from __main__.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = ToolRegistry()
        return cls._instance

    def __init__(self):
        """Initialize the registry."""
        self.tools: Dict[str, AbstractTool] = {}

    def register_tool(self, tool: AbstractTool) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool to register
        """
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[AbstractTool]:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self.tools.get(name)

    def get_tools(self, names: List[str]) -> List[AbstractTool]:
        """
        Get multiple tools by name.

        Args:
            names: List of tool names

        Returns:
            List of tool instances (missing tools are skipped)
        """
        return [self.tools[name] for name in names if name in self.tools]

    def get_all_tools(self) -> List[AbstractTool]:
        """
        Get all registered tools.

        Returns:
            List of all tool instances
        """
        return list(self.tools.values())

    def clear(self) -> None:
        """Clear all registered tools."""
        self.tools.clear()
