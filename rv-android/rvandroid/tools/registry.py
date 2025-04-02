# rvandroid/tools/registry.py
"""
Tool registry for managing and accessing tool instances across the application.
Provides a singleton registry that can be accessed from any module.
"""
from typing import Dict, List, Optional, Any, Type

from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.logging.manager import LoggingManager


class ToolRegistry:
    """
    Singleton registry for tool management with enhanced configuration support.

    ### Architectural Decisions:
    - Implements singleton pattern for global access to registered tools
    - Stores both tool instances and their configurations
    - Supports tool retrieval by name, with optional variant specification
    - Enables dynamic tool registration and configuration

    ### Role in the System:
    - Serves as the central repository for all testing tools
    - Manages tool variants and configurations
    - Provides tools for experiment execution
    - Enables decoupling between tool definition and tool usage
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = ToolRegistry()
        return cls._instance

    def __init__(self):
        """Initialize the registry with logging."""
        # Set up standardized logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger("tools.registry")

        # Core storage for tools and configurations
        self.tools: Dict[str, AbstractTool] = {}
        self.tool_classes: Dict[str, Type[AbstractTool]] = {}
        self.configurations: Dict[str, Dict[str, Any]] = {}
        self.variants: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def register_tool(self, tool: AbstractTool) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool to register
        """
        self.tools[tool.name] = tool
        self.logger.debug(f"Registered tool: {tool.name}")

        # Store empty configurations if not already present
        if tool.name not in self.configurations:
            self.configurations[tool.name] = {}

        if tool.name not in self.variants:
            self.variants[tool.name] = {
                "default": {}  # Default empty variant
            }

    def register_tool_class(self, name: str, tool_class: Type[AbstractTool]) -> None:
        """
        Register a tool class for later instantiation.

        Args:
            name: Tool name
            tool_class: Tool class
        """
        self.tool_classes[name] = tool_class
        self.logger.debug(f"Registered tool class: {name}")

    def register_configuration(self, tool_name: str, config: Dict[str, Any]) -> None:
        """
        Register a base configuration for a tool.

        Args:
            tool_name: Tool name
            config: Configuration dictionary
        """
        if tool_name not in self.configurations:
            self.configurations[tool_name] = {}

        self.configurations[tool_name] = config
        self.logger.debug(f"Registered configuration for tool: {tool_name}")

    def register_variant(self, tool_name: str, variant_name: str, config: Dict[str, Any]) -> None:
        """
        Register a configuration variant for a tool.

        Args:
            tool_name: Tool name
            variant_name: Variant name
            config: Configuration dictionary for this variant
        """
        if tool_name not in self.variants:
            self.variants[tool_name] = {}

        self.variants[tool_name][variant_name] = config
        self.logger.debug(f"Registered variant '{variant_name}' for tool: {tool_name}")

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

    def get_tool_configuration(self, tool_name: str, variant: str = "default") -> Dict[str, Any]:
        """
        Get the configuration for a tool, optionally with a specific variant.

        Args:
            tool_name: Tool name
            variant: Variant name (default: "default")

        Returns:
            Configuration dictionary (merged base + variant)
        """
        # Get base configuration
        base_config = self.configurations.get(tool_name, {})

        # Get variant configuration
        variant_config = {}
        if tool_name in self.variants and variant in self.variants[tool_name]:
            variant_config = self.variants[tool_name][variant]

        # Merge configurations
        from rvandroid.util.config_utils import deep_merge
        return deep_merge(base_config, variant_config)

    def resolve_tool_spec(self, spec: str) -> tuple:
        """
        Resolve a tool specification string to tool name, variants, and parameters.

        Format: tool_name[:variant1][:variant2][@param1=value1,param2=value2]

        Args:
            spec: Tool specification string

        Returns:
            Tuple of (tool_name, [variants], {params})
        """
        # Parse the tool specification
        if '@' in spec:
            base_part, params_part = spec.split('@', 1)
            params = dict(p.split('=', 1) for p in params_part.split(',') if '=' in p)
        else:
            base_part = spec
            params = {}

        # Split by colon to get variants
        parts = base_part.split(':')
        tool_name = parts[0]
        variants = parts[1:] if len(parts) > 1 else ["default"]

        return tool_name, variants, params

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
        self.configurations.clear()
        self.variants.clear()
