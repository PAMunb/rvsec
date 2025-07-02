"""
Simplified plugin interface for external tool integration.

This module defines the essential contract that external tool plugins must implement
to integrate with the RV-Android monitored operations framework.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type, Optional

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.exceptions import PluginError, ToolRegistrationError
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec


class ToolPlugin(ABC):
    """
    Simplified interface for external tool plugins in the monitored operations framework.

    ### Architectural Decisions:
    - Focuses on essential plugin functionality only
    - Maintains tool variant support for complex tools (e.g., droidbot, rvandroid)
    - Uses rv-android-core infrastructure for error handling and logging
    - Removes complex capability and dependency management
    - Supports clean tool registration and discovery patterns

    ### Role in the System:
    - Serves as the primary interface for external tool integration
    - Enables modular tool ecosystem with clean separation of concerns
    - Provides standardized mechanism for tool discovery and registration
    - Supports tool variant management for flexible tool configuration
    - Integrates with simplified registry and factory systems

    ### Key Features:
    - Essential metadata methods (name, version, description)
    - Tool class and specification provision
    - Tool variant support for complex tools
    - Simplified registration workflow
    - Standardized error handling and logging
    """

    def __init__(self):
        """Initialize plugin with standardized logging and error handling."""
        # Set up rv-android-core infrastructure
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            f"rv_tools.plugin.{self.get_plugin_name()}",
            {CONTEXT_COMPONENT: "ToolPlugin"}
        )
        self.error_handler = ErrorHandler.get_instance()

    @abstractmethod
    def get_plugin_name(self) -> str:
        """
        Get the unique identifier for this plugin.
        
        Returns:
            Unique plugin name
        """
        pass

    @abstractmethod
    def get_plugin_version(self) -> str:
        """
        Get the version of this plugin.
        
        Returns:
            Plugin version string (should follow semantic versioning)
        """
        pass

    @abstractmethod
    def get_plugin_description(self) -> str:
        """
        Get a human-readable description of this plugin.
        
        Returns:
            Plugin description
        """
        pass

    @abstractmethod
    def get_tool_names(self) -> List[str]:
        """
        Get the names of all tools provided by this plugin.
        
        Returns:
            List of tool names provided by this plugin
        """
        pass

    @abstractmethod
    def get_tool_class(self, tool_name: str) -> Type[AbstractTool]:
        """
        Get the tool class for a specific tool name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool class type
            
        Raises:
            ToolRegistrationError: If tool name is not provided by this plugin
        """
        pass

    @abstractmethod
    def get_tool_spec(self, tool_name: str) -> ToolSpec:
        """
        Get the tool specification for a specific tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            ToolSpec instance with tool metadata
            
        Raises:
            ToolRegistrationError: If tool name is not provided by this plugin
        """
        pass

    def get_tool_variants(self, tool_name: str) -> List[str]:
        """
        Get available variants for a specific tool.
        
        This method supports tools that have multiple configuration variants
        (e.g., droidbot with bfs_greedy, dfs_greedy; rvandroid with different models).
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            List of variant names for the tool (empty if no variants)
        """
        # Default implementation returns no variants
        # Tools with variants should override this method
        return []

    def get_variant_config(self, tool_name: str, variant_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific tool variant.
        
        Args:
            tool_name: Name of the tool
            variant_name: Name of the variant
            
        Returns:
            Configuration dictionary for the variant
            
        Raises:
            ToolRegistrationError: If tool or variant is not available
        """
        # Default implementation returns empty config
        # Tools with variants should override this method
        return {}

    @ErrorHandler.handle_errors(
        component="ToolPlugin",
        phase="register_tools"
    )
    def register_tools(self, registry) -> None:
        """
        Register all tools provided by this plugin with the registry.
        
        This method registers tools and their variants with the provided registry.
        
        Args:
            registry: ToolRegistry instance to register tools with
            
        Raises:
            ToolRegistrationError: If tool registration fails
        """
        try:
            for tool_name in self.get_tool_names():
                # Register the tool class and spec
                tool_class = self.get_tool_class(tool_name)
                tool_spec = self.get_tool_spec(tool_name)
                
                registry.register_tool(tool_name, tool_class, tool_spec)
                self.logger.info(f"Registered tool: {tool_name}")
                
                # Register variants if available
                variants = self.get_tool_variants(tool_name)
                for variant_name in variants:
                    variant_config = self.get_variant_config(tool_name, variant_name)
                    registry.register_variant(tool_name, variant_name, variant_config)
                    self.logger.debug(f"Registered variant '{variant_name}' for tool: {tool_name}")
                
        except Exception as e:
            raise ToolRegistrationError(
                f"Failed to register tools from plugin '{self.get_plugin_name()}': {e}"
            ) from e

    def create_tool_instance(self, tool_name: str, config: Optional[Dict[str, Any]] = None) -> AbstractTool:
        """
        Create a configured instance of a specific tool.
        
        Args:
            tool_name: Name of the tool to create
            config: Optional configuration dictionary
            
        Returns:
            Configured tool instance
            
        Raises:
            ToolRegistrationError: If tool name is not provided by this plugin
        """
        if tool_name not in self.get_tool_names():
            raise ToolRegistrationError(
                f"Tool '{tool_name}' is not provided by plugin '{self.get_plugin_name()}'"
            )

        try:
            # Get tool class and create instance
            tool_class = self.get_tool_class(tool_name)
            tool_spec = self.get_tool_spec(tool_name)
            
            # Create instance using spec data
            tool_instance = tool_class(
                name=tool_spec.name,
                description=tool_spec.description,
                process_pattern=tool_spec.process_pattern
            )

            # Apply configuration if provided and tool supports it
            if config and hasattr(tool_instance, 'configure') and callable(tool_instance.configure):
                tool_instance.configure(config)

            return tool_instance
            
        except Exception as e:
            raise ToolRegistrationError(
                f"Failed to create tool instance '{tool_name}': {e}"
            ) from e

    def get_plugin_metadata(self) -> Dict[str, Any]:
        """
        Get comprehensive plugin metadata.
        
        Returns:
            Dictionary with plugin metadata
        """
        return {
            "name": self.get_plugin_name(),
            "version": self.get_plugin_version(),
            "description": self.get_plugin_description(),
            "tool_names": self.get_tool_names(),
            "plugin_type": "external_tool"
        }

    def __str__(self) -> str:
        """String representation of the plugin."""
        return f"{self.__class__.__name__}(name='{self.get_plugin_name()}', version='{self.get_plugin_version()}')"

    def __repr__(self) -> str:
        """Detailed string representation of the plugin."""
        return (f"{self.__class__.__name__}(name='{self.get_plugin_name()}', "
                f"version='{self.get_plugin_version()}', tools={self.get_tool_names()})")