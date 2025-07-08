"""
Simplified tool registry for managing tool instances and variants.

This module provides a streamlined registry that manages tool instances
and variants for monitored operations testing.
"""

from typing import Dict, List, Optional, Any, Type

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.error.exceptions import ToolNotFoundError, ToolRegistrationError
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec


class ToolRegistry:
    """
    Simplified registry for tool management with variant support.

    ### Architectural Decisions:
    - Removes threading complexity and singleton pattern overhead
    - Maintains essential tool storage and variant management
    - Uses rv-android-core infrastructure for error handling and logging
    - Focuses on core functionality needed for tool discovery and creation
    - Preserves tool variant support for complex tools (droidbot, rvandroid)

    ### Role in the System:
    - Serves as central repository for monitored operations testing tools
    - Manages tool variants and basic configurations
    - Provides tools for experiment execution and discovery
    - Enables clean integration with simplified factory system
    - Supports plugin registration and external tool integration

    ### Key Features:
    - Tool registration with class and specification storage
    - Tool variant management for flexible configuration
    - Tool discovery and retrieval by name
    - Basic configuration support for tool variants
    - Integration with rv-android-core error handling and logging
    """

    _instance: Optional['ToolRegistry'] = None

    @classmethod
    def get_instance(cls) -> 'ToolRegistry':
        """
        Get the singleton instance of the tool registry.

        Returns:
            ToolRegistry instance
        """
        if cls._instance is None:
            cls._instance = ToolRegistry()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance for testing purposes.
        """
        cls._instance = None

    def __init__(self):
        """
        Initialize the registry with rv-android-core infrastructure.
        """
        # Set up standardized logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_tools.registry",
            {CONTEXT_COMPONENT: "ToolRegistry"}
        )
        
        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()

        # Core storage for tools and configurations
        self.tool_classes: Dict[str, Type[AbstractTool]] = {}
        self.tool_specs: Dict[str, ToolSpec] = {}
        self.variants: Dict[str, Dict[str, Dict[str, Any]]] = {}

        self.logger.info("Simplified tool registry initialized")

    @ErrorHandler.handle_errors(
        component="ToolRegistry",
        phase="register_tool"
    )
    def register_tool(self, tool_name: str, tool_class: Type[AbstractTool], tool_spec: ToolSpec) -> None:
        """
        Register a tool class and specification in the registry.

        Args:
            tool_name: Name of the tool
            tool_class: Tool class type
            tool_spec: Tool specification with metadata
            
        Raises:
            ToolRegistrationError: If tool registration fails
        """
        try:
            if tool_name in self.tool_classes:
                self.logger.warning(f"Tool '{tool_name}' already registered, replacing existing registration")

            self.tool_classes[tool_name] = tool_class
            self.tool_specs[tool_name] = tool_spec
            
            # Initialize empty variants if not present
            if tool_name not in self.variants:
                self.variants[tool_name] = {}

            self.logger.info(f"Registered tool: {tool_name}")

        except Exception as e:
            raise ToolRegistrationError(f"Failed to register tool '{tool_name}': {e}") from e

    @ErrorHandler.handle_errors(
        component="ToolRegistry",
        phase="register_tool_class"
    )
    def register_tool_class(self, tool_class: Type[AbstractTool]) -> None:
        """
        Register a tool class using its TOOL_SPEC attribute.

        Args:
            tool_class: Tool class to register
            
        Raises:
            ToolRegistrationError: If tool class registration fails
        """
        try:
            if not hasattr(tool_class, 'TOOL_SPEC'):
                raise ToolRegistrationError(f"Tool class {tool_class.__name__} must have TOOL_SPEC attribute")
            
            tool_spec = tool_class.TOOL_SPEC
            self.register_tool(tool_spec.name, tool_class, tool_spec)
            
        except Exception as e:
            raise ToolRegistrationError(f"Failed to register tool class '{tool_class.__name__}': {e}") from e

    @ErrorHandler.handle_errors(
        component="ToolRegistry",
        phase="register_variant"
    )
    def register_variant(self, tool_name: str, variant_name: str, config: Dict[str, Any]) -> None:
        """
        Register a configuration variant for a tool.

        Args:
            tool_name: Tool name
            variant_name: Variant name
            config: Configuration dictionary for this variant
            
        Raises:
            ToolRegistrationError: If variant registration fails
        """
        try:
            if tool_name not in self.tool_classes:
                raise ToolNotFoundError(f"Tool '{tool_name}' not found. Register tool first.")

            if tool_name not in self.variants:
                self.variants[tool_name] = {}

            self.variants[tool_name][variant_name] = config.copy()
            self.logger.debug(f"Registered variant '{variant_name}' for tool: {tool_name}")

        except Exception as e:
            raise ToolRegistrationError(
                f"Failed to register variant '{variant_name}' for tool '{tool_name}': {e}"
            ) from e

    def get_tool(self, tool_name: str, variant: str = "default") -> AbstractTool:
        """
        Get a tool instance, optionally with a specific variant configuration.

        Args:
            tool_name: Name of the tool
            variant: Variant name (default: "default")

        Returns:
            Configured tool instance
            
        Raises:
            ToolNotFoundError: If tool or variant is not found
        """
        if tool_name not in self.tool_classes:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found in registry")

        try:
            tool_class = self.tool_classes[tool_name]
            tool_spec = self.tool_specs[tool_name]

            # Create tool instance using spec data
            tool_instance = tool_class(
                name=tool_spec.name,
                description=tool_spec.description,
                process_pattern=tool_spec.process_pattern
            )

            # Apply variant configuration if available
            if variant != "default" and tool_name in self.variants:
                if variant in self.variants[tool_name]:
                    variant_config = self.variants[tool_name][variant]
                    if hasattr(tool_instance, 'configure') and callable(tool_instance.configure):
                        tool_instance.configure(variant_config)
                        self.logger.debug(f"Applied variant '{variant}' configuration to tool: {tool_name}")
                else:
                    self.logger.warning(f"Variant '{variant}' not found for tool '{tool_name}', using default")

            return tool_instance

        except Exception as e:
            raise ToolNotFoundError(f"Failed to create tool instance '{tool_name}': {e}") from e

    def get_all_tools(self) -> List[AbstractTool]:
        """
        Get instances of all registered tools with default configuration.

        Returns:
            List of tool instances
        """
        tools = []
        for tool_name in self.tool_classes:
            try:
                tool = self.get_tool(tool_name)
                tools.append(tool)
            except Exception as e:
                self.logger.error(f"Failed to create instance for tool '{tool_name}': {e}")
        
        return tools

    def get_tool_names(self) -> List[str]:
        """
        Get the names of all registered tools.

        Returns:
            List of tool names
        """
        return list(self.tool_classes.keys())

    def get_tool_spec(self, tool_name: str) -> ToolSpec:
        """
        Get the tool specification for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            ToolSpec instance
            
        Raises:
            ToolNotFoundError: If tool is not found
        """
        if tool_name not in self.tool_specs:
            raise ToolNotFoundError(f"Tool specification for '{tool_name}' not found")
        
        return self.tool_specs[tool_name]

    def get_tool_variants(self, tool_name: str) -> List[str]:
        """
        Get all available variants for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            List of variant names for the tool (empty if no variants)
        """
        if tool_name in self.variants:
            return list(self.variants[tool_name].keys())
        return []

    def has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool is registered.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool is registered, False otherwise
        """
        return tool_name in self.tool_classes

    def has_variant(self, tool_name: str, variant_name: str) -> bool:
        """
        Check if a tool variant is registered.

        Args:
            tool_name: Name of the tool
            variant_name: Name of the variant

        Returns:
            True if variant is registered, False otherwise
        """
        return (tool_name in self.variants and 
                variant_name in self.variants[tool_name])

    def get_variant_config(self, tool_name: str, variant_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific tool variant.

        Args:
            tool_name: Name of the tool
            variant_name: Name of the variant

        Returns:
            Configuration dictionary for the variant
            
        Raises:
            ToolNotFoundError: If tool or variant is not found
        """
        if not self.has_variant(tool_name, variant_name):
            raise ToolNotFoundError(
                f"Variant '{variant_name}' not found for tool '{tool_name}'"
            )
        
        return self.variants[tool_name][variant_name].copy()

    def clear(self) -> None:
        """Clear all registered tools and variants."""
        self.tool_classes.clear()
        self.tool_specs.clear()
        self.variants.clear()
        self.logger.debug("Registry cleared")

    def get_registry_info(self) -> Dict[str, Any]:
        """
        Get comprehensive registry information.

        Returns:
            Dictionary with registry statistics and metadata
        """
        total_variants = sum(len(variants) for variants in self.variants.values())
        
        return {
            "total_tools": len(self.tool_classes),
            "total_variants": total_variants,
            "tools": list(self.tool_classes.keys()),
            "variants_by_tool": {
                tool_name: list(variants.keys()) 
                for tool_name, variants in self.variants.items()
                if variants
            }
        }