"""
Plugin interface for external tool integration.

This module defines the contract that external tool plugins must implement
to integrate with the RV-Android monitored operations framework.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Type, Optional

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec


class ToolPlugin(ABC):
    """
    Abstract interface for external tool plugins in the monitored operations framework.

    ### Architectural Decisions:
    - Defines clear contract for external tool integration
    - Supports plugin metadata and dependency management
    - Enables dynamic tool registration and discovery
    - Provides validation and compatibility checking capabilities
    - Facilitates plugin lifecycle management and error handling
    - Supports both single and multiple tool registration per plugin

    ### Role in the System:
    - Serves as the primary interface for external tool integration
    - Enables modular tool ecosystem with clean separation of concerns
    - Provides standardized mechanism for tool discovery and registration
    - Facilitates plugin validation and dependency resolution
    - Enables experiment framework integration with external tools
    - Supports configuration and variant management for external tools

    ### Key Considerations:
    - Must be implemented by all external tool plugins
    - Provides metadata for plugin discovery and validation
    - Supports dependency checking and compatibility verification
    - Enables flexible tool registration patterns (single or multiple tools)
    - Facilitates error handling and graceful degradation
    - Supports plugin versioning and compatibility management

    ### Integration Strategy:
    - Compatible with PluginLoader for automatic discovery
    - Integrates with ToolRegistry for tool registration
    - Supports experiment framework tool selection and filtering
    - Enables configuration management through ToolFactory
    - Provides clear extension points for custom plugin behavior
    - Facilitates testing and validation of plugin implementations
    """

    @abstractmethod
    def get_plugin_name(self) -> str:
        """
        Get the unique identifier for this plugin.
        
        This name should be unique across all plugins and will be used
        for plugin discovery and management.
        
        Returns:
            Unique plugin name
        """
        pass

    @abstractmethod
    def get_plugin_version(self) -> str:
        """
        Get the version of this plugin.
        
        Version should follow semantic versioning (e.g., "1.0.0").
        
        Returns:
            Plugin version string
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
            ValueError: If tool name is not provided by this plugin
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
            ValueError: If tool name is not provided by this plugin
        """
        pass

    @abstractmethod
    def get_dependencies(self) -> List[str]:
        """
        Get the list of required dependencies for this plugin.
        
        Dependencies should be specified as module names that can be
        imported or package names that should be available.
        
        Returns:
            List of required dependency names
        """
        pass

    @abstractmethod
    def register_tools(self, registry) -> None:
        """
        Register all tools provided by this plugin with the registry.
        
        This method should create tool instances and register them
        with the provided registry along with any configurations or variants.
        
        Args:
            registry: ToolRegistry instance to register tools with
            
        Raises:
            RuntimeError: If tool registration fails
        """
        pass

    def get_plugin_metadata(self) -> Dict[str, Any]:
        """
        Get comprehensive plugin metadata.
        
        This method provides a default implementation that collects
        metadata from other interface methods. Plugins can override
        this to provide additional metadata.
        
        Returns:
            Dictionary with plugin metadata
        """
        return {
            "name": self.get_plugin_name(),
            "version": self.get_plugin_version(),
            "description": self.get_plugin_description(),
            "tool_names": self.get_tool_names(),
            "dependencies": self.get_dependencies(),
            "plugin_type": "external_tool"
        }

    def validate_dependencies(self) -> bool:
        """
        Validate that all plugin dependencies are available.
        
        This method provides a default implementation that attempts
        to import all dependencies. Plugins can override this for
        custom dependency validation logic.
        
        Returns:
            True if all dependencies are available, False otherwise
        """
        try:
            for dependency in self.get_dependencies():
                __import__(dependency)
            return True
        except ImportError:
            return False

    def is_compatible_with_framework(self, framework_version: str) -> bool:
        """
        Check if this plugin is compatible with a specific framework version.
        
        This method provides a default implementation that returns True.
        Plugins can override this to provide version compatibility checking.
        
        Args:
            framework_version: Framework version string
            
        Returns:
            True if compatible, False otherwise
        """
        return True

    def get_supported_capabilities(self) -> List[str]:
        """
        Get all capabilities supported by tools in this plugin.
        
        This method aggregates capabilities from all tool specifications
        provided by this plugin.
        
        Returns:
            List of unique capabilities across all tools
        """
        capabilities = set()
        for tool_name in self.get_tool_names():
            try:
                tool_spec = self.get_tool_spec(tool_name)
                capabilities.update(tool_spec.capabilities)
            except Exception:
                # Skip tools that fail to provide specs
                continue
        return list(capabilities)

    def create_tool_instance(self, tool_name: str, config: Optional[Dict[str, Any]] = None) -> AbstractTool:
        """
        Create a configured instance of a specific tool.
        
        This method provides a default implementation for tool creation.
        Plugins can override this for custom tool creation logic.
        
        Args:
            tool_name: Name of the tool to create
            config: Optional configuration dictionary
            
        Returns:
            Configured tool instance
            
        Raises:
            ValueError: If tool name is not provided by this plugin
        """
        if tool_name not in self.get_tool_names():
            raise ValueError(f"Tool '{tool_name}' is not provided by plugin '{self.get_plugin_name()}'")

        # Get tool class and create instance
        tool_class = self.get_tool_class(tool_name)
        tool_instance = tool_class()

        # Apply configuration if provided and tool supports it
        if config and hasattr(tool_instance, 'configure') and callable(tool_instance.configure):
            tool_instance.configure(config)

        return tool_instance

    def validate_tool_configuration(self, tool_name: str, config: Dict[str, Any]) -> bool:
        """
        Validate a configuration for a specific tool.
        
        This method provides a default implementation that returns True.
        Plugins can override this to provide custom configuration validation.
        
        Args:
            tool_name: Name of the tool
            config: Configuration to validate
            
        Returns:
            True if configuration is valid, False otherwise
        """
        return True

    def get_default_configuration(self, tool_name: str) -> Dict[str, Any]:
        """
        Get the default configuration for a specific tool.
        
        This method provides a default implementation that returns an empty
        configuration. Plugins can override this to provide tool-specific defaults.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Default configuration dictionary
        """
        return {}

    def get_configuration_schema(self, tool_name: str) -> Dict[str, Any]:
        """
        Get the configuration schema for a specific tool.
        
        This method provides a default implementation that returns an empty
        schema. Plugins can override this to provide configuration validation schemas.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Configuration schema dictionary (e.g., JSON Schema format)
        """
        return {}

    def cleanup(self) -> None:
        """
        Perform cleanup operations when the plugin is unloaded.
        
        This method provides a default implementation that does nothing.
        Plugins can override this to perform custom cleanup operations.
        """
        pass

    def __str__(self) -> str:
        """String representation of the plugin."""
        return f"{self.__class__.__name__}(name='{self.get_plugin_name()}', version='{self.get_plugin_version()}')"

    def __repr__(self) -> str:
        """Detailed string representation of the plugin."""
        return (f"{self.__class__.__name__}(name='{self.get_plugin_name()}', "
                f"version='{self.get_plugin_version()}', tools={self.get_tool_names()})")