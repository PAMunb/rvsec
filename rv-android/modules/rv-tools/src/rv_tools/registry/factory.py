"""
Tool Factory with Variant System Support

This module provides tool creation capabilities with comprehensive variant support
for all testing tools in the RV-Android framework, enabling consistent tool
instantiation and configuration management.

### Architectural Overview:
This factory implements the variant system by creating configured tool instances
from ToolConfig specifications, resolving variants through the ToolRegistry,
and applying configuration parameters to tool instances.

### Key Features:
- ToolConfig-based tool creation with variant support
- Registry-based variant resolution and validation
- Consistent configuration application across all tools
- Error handling with clear configuration failure messages

### Design Patterns:
- Factory Method: Tool creation from ToolConfig specifications
- Template Method: Common tool creation workflow with variant resolution

### Integration Strategy:
- Uses ToolRegistry for variant resolution and validation
- Provides unified interface for all tool instantiation needs
- Maintains separation of concerns between registry, factory, and tools
"""

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_tools.registry.registry import ToolRegistry


class ToolFactory:
    """
    Factory for creating configured tool instances with variant support.

    ### Architectural Decisions:
    - Uses ToolRegistry for variant resolution
    - Provides consistent configuration application across all tools
    - Integrates with error handling for configuration failures

    ### Role in the System:
    - Creates tool instances with proper configuration applied
    - Resolves variants to configuration parameters
    - Ensures tools are properly configured before execution

    ### Configuration Flow:
    1. Resolve tool class from registry
    2. Get variant configuration from registry
    3. Apply parameter overrides from tool_config
    4. Configure tool instance with resolved parameters
    """

    def __init__(self, registry: ToolRegistry = None):
        """
        Initialize tool factory with optional registry instance.

        Args:
            registry: Optional tool registry instance for tool discovery

        State:
            registry: ToolRegistry used for tool class and variant resolution.
            logger: Structured logger for factory operations.
        """
        self.registry = registry or ToolRegistry.get_instance()

        # Initialize logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_tools.registry.factory", {CONTEXT_COMPONENT: "ToolFactory"}
        )

    @ErrorHandler.handle_errors(component="ToolFactory", operation="create_tool")
    def create_tool(self, tool_config) -> AbstractTool:
        """
        Create configured tool instance from ToolConfig specification.

        This method performs complete tool instantiation including:
        - Tool class resolution from registry
        - Variant configuration resolution
        - Configuration application to tool instance

        ### Configuration Flow:
        1. Resolve tool class from registry
        2. Get variant configuration from registry
        3. Apply parameter overrides from tool_config
        4. Configure tool instance with resolved parameters

        Args:
            tool_config: ToolConfig with name, variant, and parameters

        Returns:
            Configured tool instance ready for execution

        Raises:
            ConfigurationError: If tool or variant not found
        """
        tool_name = tool_config.name
        variant_name = tool_config.variant

        # Step 1: Resolve tool class from registry
        if not self.registry.is_tool_registered(tool_name):
            raise ConfigurationError(f"Tool '{tool_name}' not found in registry")

        tool_class = self.registry.get_tool_class(tool_name)

        # Step 2: Resolve variant configuration.
        # Every tool must have at least a "default" variant registered.
        # Named variants provide curated presets (e.g., droidbot:dfs_greedy).
        if variant_name and variant_name != "default":
            if not self.registry.validate_tool_variant(tool_name, variant_name):
                raise ConfigurationError(
                    f"Invalid variant '{variant_name}' for tool '{tool_name}'"
                )

            variant_config = self.registry.get_variant_config(tool_name, variant_name)
        else:
            variant_config = self.registry.get_variant_config(tool_name, "default")

        # Step 3: Merge user parameters over variant defaults.
        # This lets users override individual settings (e.g., timeout) without
        # having to respecify the entire variant configuration.
        final_config = {**variant_config, **tool_config.parameters}

        # Step 4: Create a fresh instance and apply the merged configuration.
        # The constructor sets sane defaults; configure() overrides with the
        # variant+user values. This two-step pattern keeps constructors simple.
        tool_instance = tool_class()
        tool_instance.configure(final_config)

        self.logger.info(f"Created tool instance: {tool_name}:{variant_name}")
        return tool_instance
