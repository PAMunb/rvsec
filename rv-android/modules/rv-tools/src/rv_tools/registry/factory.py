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
- Tool-specific configuration creation for complex tools (RVAndroid)
- Consistent configuration application across all tools
- Error handling with clear configuration failure messages

### Design Patterns:
- Factory Method: Tool creation from ToolConfig specifications
- Strategy Pattern: Different configuration strategies for different tool types
- Template Method: Common tool creation workflow with variant resolution
- Delegation Pattern: Tool-specific configuration creation in tool classes

### Integration Strategy:
- Uses ToolRegistry for variant resolution and validation
- Delegates to tool classes for specialized configuration creation
- Provides unified interface for all tool instantiation needs
- Maintains separation of concerns between registry, factory, and tools
"""

from typing import Dict, Any, Union

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import ToolNotFoundError, ConfigurationError, ToolCreationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_tools.registry.registry import ToolRegistry


class ToolFactory:
    """
    Factory for creating configured tool instances with variant support.
    
    ### Architectural Decisions:
    - Uses ToolRegistry for variant resolution
    - Delegates tool-specific configuration creation to tool classes
    - Provides consistent configuration application across all tools
    - Integrates with error handling for configuration failures
    
    ### Role in the System:
    - Creates tool instances with proper configuration applied
    - Resolves variants to configuration parameters
    - Coordinates between registry and tool-specific factories
    - Ensures tools are properly configured before execution
    
    ### Configuration Flow:
    1. Resolve tool class from registry
    2. Get variant configuration from registry
    3. Apply parameter overrides from tool_config
    4. Create tool-specific configuration (for RVAndroid)
    5. Configure tool instance with resolved parameters
    """

    def __init__(self, registry: ToolRegistry = None):
        """
        Initialize tool factory with optional registry instance.
        
        Args:
            registry: Optional tool registry instance for tool discovery
        """
        self.registry = registry or ToolRegistry.get_instance()
        
        # Initialize logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_tools.registry.factory",
            {CONTEXT_COMPONENT: "ToolFactory"}
        )
        

    @ErrorHandler.handle_errors(
        component="ToolFactory",
        operation="create_tool"
    )
    def create_tool(self, tool_config) -> AbstractTool:
        """
        Create configured tool instance from ToolConfig specification.
        
        This method performs complete tool instantiation including:
        - Tool class resolution from registry
        - Variant configuration resolution
        - Tool-specific configuration creation
        - Configuration application to tool instance
        
        ### Configuration Flow:
        1. Resolve tool class from registry
        2. Get variant configuration from registry
        3. Apply parameter overrides from tool_config
        4. Create tool-specific configuration (for RVAndroid)
        5. Configure tool instance with resolved parameters
        
        Args:
            tool_config: ToolConfig with name, variant, and parameters
            
        Returns:
            Configured tool instance ready for execution
            
        Raises:
            ConfigurationError: If tool or variant not found
            ToolCreationError: If tool creation fails
        """
        tool_name = tool_config.tool_name
        variant_name = tool_config.variant
        
        # Get tool class from registry
        if not self.registry.is_tool_registered(tool_name):
            raise ConfigurationError(f"Tool '{tool_name}' not found in registry")
        
        tool_class = self.registry.get_tool_class(tool_name)
        
        # Resolve variant configuration
        if variant_name and variant_name != "default":
            # Use specific variant
            if not self.registry.validate_tool_variant(tool_name, variant_name):
                raise ConfigurationError(f"Invalid variant '{variant_name}' for tool '{tool_name}'")
            
            variant_config = self.registry.get_variant_config(tool_name, variant_name)
        else:
            # Use default variant
            variant_config = self.registry.get_variant_config(tool_name, "default")
        
        # Apply parameter overrides from tool_config
        final_config = {**variant_config, **tool_config.additional_params}
        
        # Create tool instance
        tool_instance = tool_class()
        
        # Special handling for RVAndroid - create typed configuration
        if tool_name == "rvandroid" and hasattr(tool_class, 'create_tool_config'):
            typed_config = tool_class.create_tool_config(variant_config, tool_config.additional_params)
            tool_instance.configure(typed_config)
        else:
            # Standard configuration for other tools
            tool_instance.configure(final_config)
        
        self.logger.info(f"Created tool instance: {tool_name}:{variant_name}")
        return tool_instance