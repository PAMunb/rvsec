"""
Plugin discovery and loading system for external tools.

This module provides comprehensive plugin discovery, validation, and loading
capabilities for the monitored operations testing framework.
"""

import sys
from typing import List, Dict, Any, Optional, Set
from importlib import import_module
from importlib.metadata import entry_points, distributions

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_tools.interfaces.plugin_interface import ToolPlugin
from rv_tools.registry.registry import ToolRegistry


class PluginLoader:
    """
    Plugin discovery and loading system for external monitored operations tools.

    ### Architectural Decisions:
    - Uses Python entry points for automatic plugin discovery
    - Supports both package-based and module-based plugin registration
    - Validates plugin compatibility and dependencies before loading
    - Provides comprehensive error handling and graceful degradation
    - Integrates with rv-android-core infrastructure for logging and error management
    - Supports plugin lifecycle management and cleanup operations

    ### Role in the System:
    - Discovers available tool plugins from installed packages
    - Validates plugin compatibility and dependency requirements
    - Loads and registers external tools with the tool registry
    - Manages plugin lifecycle and error handling during loading
    - Provides plugin metadata and status information for debugging
    - Enables dynamic tool ecosystem expansion through plugin system

    ### Key Considerations:
    - Handles plugin loading failures gracefully without affecting other plugins
    - Validates plugin dependencies and compatibility before registration
    - Provides comprehensive logging for plugin discovery and loading operations
    - Supports plugin filtering and selective loading based on requirements
    - Manages plugin metadata and provides introspection capabilities
    - Integrates with experiment framework for dynamic tool availability

    ### Integration Strategy:
    - Compatible with ToolRegistry for automatic tool registration
    - Supports experiment framework integration for plugin-based tool discovery
    - Enables configuration management through plugin interface
    - Provides clear extension points for custom plugin loading behavior
    - Facilitates testing and validation of plugin loading mechanisms

    ### Performance and Scalability:
    - Optimized for efficient plugin discovery and loading
    - Supports lazy loading and caching of plugin metadata
    - Minimizes overhead through smart validation and error handling
    - Enables selective plugin loading for performance optimization
    - Adaptable to different plugin complexity and loading requirements
    """

    ENTRY_POINT_GROUP = "rv_tools.plugins"

    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        Initialize the plugin loader.

        Args:
            registry: Optional registry instance (uses singleton if not provided)
        """
        self.registry = registry or ToolRegistry.get_instance()
        
        # Set up standardized logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "tools.plugin_loader",
            {CONTEXT_COMPONENT: "PluginLoader"}
        )
        
        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()

        # Plugin tracking
        self.discovered_plugins: Dict[str, ToolPlugin] = {}
        self.loaded_plugins: Dict[str, ToolPlugin] = {}
        self.failed_plugins: Dict[str, str] = {}  # plugin_name -> error_message
        
        self.logger.info("Plugin loader initialized")

    def discover_plugins(self) -> List[ToolPlugin]:
        """
        Discover available tool plugins from entry points.
        
        This method scans installed packages for plugins registered
        under the rv_tools.plugins entry point group.

        Returns:
            List of discovered plugin instances
        """
        self.logger.info("Starting plugin discovery")
        plugins = []
        
        try:
            # Get entry points for our plugin group (compatible with new EntryPoints API)
            eps = entry_points()
            if hasattr(eps, 'get'):
                # Older API (Python < 3.10)
                plugin_entries = eps.get(self.ENTRY_POINT_GROUP, [])
            else:
                # Newer API (Python >= 3.10)
                plugin_entries = eps.select(group=self.ENTRY_POINT_GROUP)
            
            self.logger.debug(f"Found {len(plugin_entries)} plugin entry points")
            
            for entry_point in plugin_entries:
                try:
                    plugin = self._load_plugin_from_entry_point(entry_point)
                    if plugin:
                        plugins.append(plugin)
                        self.discovered_plugins[plugin.get_plugin_name()] = plugin
                        self.logger.debug(f"Discovered plugin: {plugin.get_plugin_name()}")
                
                except Exception as e:
                    error_msg = f"Failed to discover plugin from entry point '{entry_point.name}': {str(e)}"
                    self.logger.error(error_msg)
                    self.failed_plugins[entry_point.name] = error_msg
                    
                    # Handle error but continue with other plugins
                    self.error_handler.handle_error(
                        e,
                        context={
                            "operation": "discover_plugin",
                            "entry_point": entry_point.name,
                            "component": "PluginLoader"
                        }
                    )

            # Also include any manually registered plugins (for testing)
            for name, plugin in self.discovered_plugins.items():
                if plugin not in plugins:
                    plugins.append(plugin)
            
            self.logger.info(f"Plugin discovery completed: {len(plugins)} plugins discovered")
            return plugins

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "discover_plugins",
                    "component": "PluginLoader"
                }
            )
            raise

    def load_plugin(self, plugin_name: str) -> Optional[ToolPlugin]:
        """
        Load a specific plugin by name.

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            Loaded plugin instance or None if loading fails
        """
        try:
            self.logger.debug(f"Loading plugin: {plugin_name}")
            
            # Check if already loaded
            if plugin_name in self.loaded_plugins:
                self.logger.debug(f"Plugin '{plugin_name}' already loaded")
                return self.loaded_plugins[plugin_name]
            
            # Check if discovered but not loaded
            if plugin_name in self.discovered_plugins:
                plugin = self.discovered_plugins[plugin_name]
                return self._validate_and_load_plugin(plugin)
            
            # Try to discover the plugin
            self.discover_plugins()
            
            # Check again after discovery
            if plugin_name in self.discovered_plugins:
                plugin = self.discovered_plugins[plugin_name]
                return self._validate_and_load_plugin(plugin)
            
            self.logger.warning(f"Plugin '{plugin_name}' not found")
            return None

        except Exception as e:
            error_msg = f"Failed to load plugin '{plugin_name}': {str(e)}"
            self.logger.error(error_msg)
            self.failed_plugins[plugin_name] = error_msg
            
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "load_plugin",
                    "plugin_name": plugin_name,
                    "component": "PluginLoader"
                }
            )
            return None

    def load_all_plugins(self) -> List[ToolPlugin]:
        """
        Load all discovered plugins.

        Returns:
            List of successfully loaded plugins
        """
        self.logger.info("Loading all discovered plugins")
        
        # Discover plugins if not already done
        if not self.discovered_plugins:
            self.discover_plugins()
        
        loaded_plugins = []
        for plugin_name, plugin in self.discovered_plugins.items():
            try:
                loaded_plugin = self._validate_and_load_plugin(plugin)
                if loaded_plugin:
                    loaded_plugins.append(loaded_plugin)
            except Exception as e:
                error_msg = f"Failed to load plugin '{plugin_name}': {str(e)}"
                self.logger.error(error_msg)
                self.failed_plugins[plugin_name] = error_msg

        self.logger.info(f"Loaded {len(loaded_plugins)} plugins successfully")
        return loaded_plugins

    def register_external_tools(self, registry: Optional[ToolRegistry] = None) -> None:
        """
        Register all discovered external tools with the registry.

        Args:
            registry: Optional registry instance (uses default if not provided)
        """
        target_registry = registry or self.registry
        self.logger.info("Registering external tools from plugins")
        
        # Load all plugins
        loaded_plugins = self.load_all_plugins()
        
        registered_count = 0
        for plugin in loaded_plugins:
            try:
                self.logger.debug(f"Registering tools from plugin: {plugin.get_plugin_name()}")
                plugin.register_tools(target_registry)
                
                # Count registered tools
                tool_count = len(plugin.get_tool_names())
                registered_count += tool_count
                
                self.logger.info(f"Registered {tool_count} tools from plugin: {plugin.get_plugin_name()}")
                
            except Exception as e:
                plugin_name = plugin.get_plugin_name()
                error_msg = f"Failed to register tools from plugin '{plugin_name}': {str(e)}"
                self.logger.error(error_msg)
                self.failed_plugins[plugin_name] = error_msg
                
                self.error_handler.handle_error(
                    e,
                    context={
                        "operation": "register_external_tools",
                        "plugin_name": plugin_name,
                        "component": "PluginLoader"
                    }
                )

        self.logger.info(f"External tool registration completed: {registered_count} tools registered")

    def get_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin information dictionary or None if not found
        """
        # Check loaded plugins first
        if plugin_name in self.loaded_plugins:
            plugin = self.loaded_plugins[plugin_name]
            return self._get_plugin_metadata(plugin, "loaded")
        
        # Check discovered plugins
        if plugin_name in self.discovered_plugins:
            plugin = self.discovered_plugins[plugin_name]
            return self._get_plugin_metadata(plugin, "discovered")
        
        # Check failed plugins
        if plugin_name in self.failed_plugins:
            return {
                "name": plugin_name,
                "status": "failed",
                "error": self.failed_plugins[plugin_name]
            }
        
        return None

    def get_all_plugins_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all plugins.

        Returns:
            Dictionary mapping plugin names to their information
        """
        all_plugins = {}
        
        # Add failed plugins first (highest priority status)
        for name, error in self.failed_plugins.items():
            all_plugins[name] = {
                "name": name,
                "status": "failed",
                "error": error
            }
        
        # Add loaded plugins
        for name, plugin in self.loaded_plugins.items():
            if name not in all_plugins:
                all_plugins[name] = self._get_plugin_metadata(plugin, "loaded")
        
        # Add discovered but not loaded plugins (lowest priority)
        for name, plugin in self.discovered_plugins.items():
            if name not in all_plugins:
                all_plugins[name] = self._get_plugin_metadata(plugin, "discovered")
        
        return all_plugins

    def validate_plugin_dependencies(self, plugin: ToolPlugin) -> bool:
        """
        Validate that all plugin dependencies are available.

        Args:
            plugin: Plugin instance to validate

        Returns:
            True if all dependencies are available, False otherwise
        """
        try:
            return plugin.validate_dependencies()
        except Exception as e:
            self.logger.warning(f"Error validating dependencies for plugin '{plugin.get_plugin_name()}': {str(e)}")
            return False

    def cleanup_plugins(self) -> None:
        """
        Cleanup all loaded plugins.
        
        This method should be called when shutting down the application
        to ensure proper cleanup of plugin resources.
        """
        self.logger.info("Cleaning up loaded plugins")
        
        for plugin_name, plugin in self.loaded_plugins.items():
            try:
                plugin.cleanup()
                self.logger.debug(f"Cleaned up plugin: {plugin_name}")
            except Exception as e:
                self.logger.warning(f"Error cleaning up plugin '{plugin_name}': {str(e)}")

        self.loaded_plugins.clear()
        self.logger.info("Plugin cleanup completed")

    def _load_plugin_from_entry_point(self, entry_point) -> Optional[ToolPlugin]:
        """
        Load a plugin from an entry point.

        Args:
            entry_point: Entry point to load plugin from

        Returns:
            Plugin instance or None if loading fails
        """
        try:
            # Load the plugin class
            plugin_class = entry_point.load()
            
            # Instantiate the plugin
            plugin = plugin_class()
            
            # Validate that it's a proper ToolPlugin
            if not isinstance(plugin, ToolPlugin):
                raise TypeError(f"Plugin {entry_point.name} does not implement ToolPlugin interface")
            
            return plugin

        except Exception as e:
            self.logger.error(f"Failed to load plugin from entry point '{entry_point.name}': {str(e)}")
            raise

    def _validate_and_load_plugin(self, plugin: ToolPlugin) -> Optional[ToolPlugin]:
        """
        Validate and load a plugin.

        Args:
            plugin: Plugin instance to validate and load

        Returns:
            Loaded plugin instance or None if validation fails
        """
        plugin_name = plugin.get_plugin_name()
        
        try:
            self.logger.debug(f"Validating plugin: {plugin_name}")
            
            # Validate dependencies
            if not self.validate_plugin_dependencies(plugin):
                error_msg = f"Plugin '{plugin_name}' has unmet dependencies"
                self.logger.error(error_msg)
                self.failed_plugins[plugin_name] = error_msg
                return None
            
            # Validate tool specifications
            try:
                for tool_name in plugin.get_tool_names():
                    tool_spec = plugin.get_tool_spec(tool_name)
                    tool_class = plugin.get_tool_class(tool_name)
                    
                    if not tool_spec or not tool_class:
                        raise ValueError(f"Invalid tool specification for '{tool_name}'")
            
            except Exception as e:
                error_msg = f"Plugin '{plugin_name}' has invalid tool specifications: {str(e)}"
                self.logger.error(error_msg)
                self.failed_plugins[plugin_name] = error_msg
                return None
            
            # Plugin is valid, mark as loaded
            self.loaded_plugins[plugin_name] = plugin
            self.logger.info(f"Successfully loaded plugin: {plugin_name}")
            
            return plugin

        except Exception as e:
            error_msg = f"Plugin validation failed for '{plugin_name}': {str(e)}"
            self.logger.error(error_msg)
            self.failed_plugins[plugin_name] = error_msg
            return None

    def _get_plugin_metadata(self, plugin: ToolPlugin, status: str) -> Dict[str, Any]:
        """
        Get metadata for a plugin.

        Args:
            plugin: Plugin instance
            status: Plugin status (discovered, loaded, failed)

        Returns:
            Plugin metadata dictionary
        """
        try:
            metadata = plugin.get_plugin_metadata()
            metadata["status"] = status
            metadata["capabilities"] = plugin.get_supported_capabilities()
            return metadata
        except Exception as e:
            return {
                "name": plugin.get_plugin_name(),
                "status": "error",
                "error": f"Failed to get metadata: {str(e)}"
            }