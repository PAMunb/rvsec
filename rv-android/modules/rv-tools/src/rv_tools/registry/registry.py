"""
Tool registry for managing and accessing tool instances across the application.

This module provides a singleton registry that manages tool instances,
configurations, and variants for monitored operations testing.
"""

import threading
from typing import Dict, List, Optional, Any, Type, Set

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec


class ToolRegistry:
    """
    Singleton registry for comprehensive tool management with enhanced configuration support.

    ### Architectural Decisions:
    - Implements thread-safe singleton pattern for global tool access
    - Stores tool instances, classes, configurations, and metadata
    - Supports tool retrieval by name with optional variant specification
    - Enables dynamic tool registration and configuration management
    - Integrates with rv-android-core infrastructure for error handling and logging
    - Provides tool discovery and filtering capabilities based on requirements

    ### Role in the System:
    - Serves as central repository for all monitored operations testing tools
    - Manages tool variants, configurations, and capability metadata
    - Provides tools for experiment execution and dynamic selection
    - Enables decoupling between tool definition and tool usage patterns
    - Facilitates plugin system integration and external tool registration
    - Supports configuration inheritance and override mechanisms

    ### Key Considerations:
    - Thread-safe operations for concurrent access in multi-threaded environments
    - Efficient tool lookup and filtering based on capabilities and requirements
    - Flexible configuration management with variant support and inheritance
    - Comprehensive error handling and logging for registration and access operations
    - Support for both built-in and external plugin-based tools
    - Validation of tool compatibility and dependency requirements

    ### Integration Strategy:
    - Compatible with ToolFactory for dynamic tool creation and configuration
    - Supports PluginLoader for automatic discovery and registration of external tools
    - Enables experiment framework integration for tool selection and execution
    - Provides clear extension points for custom tool registration patterns
    - Facilitates tool metadata management and capability-based selection

    ### Performance and Scalability:
    - Optimized for fast tool lookup and configuration retrieval
    - Minimizes memory overhead through efficient storage patterns
    - Supports large numbers of tools and configurations without degradation
    - Enables lazy loading and initialization of tool instances
    - Adaptable to different tool complexity and registration requirements
    """

    _instance: Optional['ToolRegistry'] = None
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> 'ToolRegistry':
        """
        Get the singleton instance of the tool registry.
        
        This method implements thread-safe singleton initialization
        to ensure only one registry instance exists globally.

        Returns:
            ToolRegistry instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ToolRegistry()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance for testing purposes.
        
        This method should only be used in test environments
        to ensure clean state between test cases.
        """
        with cls._lock:
            cls._instance = None

    def __init__(self):
        """
        Initialize the registry with logging and error handling.
        
        Note: This constructor should not be called directly.
        Use get_instance() to obtain the singleton instance.
        """
        # Set up standardized logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "tools.registry",
            {CONTEXT_COMPONENT: "ToolRegistry"}
        )
        
        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()

        # Core storage for tools and configurations
        self.tools: Dict[str, AbstractTool] = {}
        self.tool_classes: Dict[str, Type[AbstractTool]] = {}
        self.tool_specs: Dict[str, ToolSpec] = {}
        self.configurations: Dict[str, Dict[str, Any]] = {}
        self.variants: Dict[str, Dict[str, Dict[str, Any]]] = {}
        
        # Tool capability indexing for efficient filtering
        self.capability_index: Dict[str, Set[str]] = {}
        
        # Thread safety for concurrent access
        self._registry_lock = threading.RLock()

        self.logger.info("Tool registry initialized")

    def register_tool(self, tool: AbstractTool, tool_spec: Optional[ToolSpec] = None) -> None:
        """
        Register a tool instance in the registry.

        Args:
            tool: Tool instance to register
            tool_spec: Optional tool specification for metadata
            
        Raises:
            ValueError: If tool name conflicts with existing registration
        """
        with self._registry_lock:
            try:
                if tool.name in self.tools:
                    self.logger.warning(f"Tool '{tool.name}' already registered, replacing existing instance")

                self.tools[tool.name] = tool
                self.logger.debug(f"Registered tool: {tool.name}")

                # Register tool specification if provided
                if tool_spec:
                    self.tool_specs[tool.name] = tool_spec
                    self._update_capability_index(tool.name, tool_spec.capabilities)

                # Initialize empty configurations if not present
                if tool.name not in self.configurations:
                    self.configurations[tool.name] = {}

                if tool.name not in self.variants:
                    self.variants[tool.name] = {}

                self.logger.info(f"Successfully registered tool: {tool.name}")

            except Exception as e:
                # Get tool name safely for error context
                tool_name = "unknown"
                try:
                    tool_name = tool.name
                except Exception:
                    tool_name = "unknown (name access failed)"
                
                self.error_handler.handle_error(
                    e,
                    context={
                        "operation": "register_tool",
                        "tool_name": tool_name,
                        "component": "ToolRegistry"
                    }
                )
                raise

    def register_tool_class(self, name: str, tool_class: Type[AbstractTool], 
                          tool_spec: Optional[ToolSpec] = None) -> None:
        """
        Register a tool class for later instantiation.

        Args:
            name: Tool name identifier
            tool_class: Tool class type
            tool_spec: Optional tool specification for metadata
        """
        with self._registry_lock:
            try:
                self.tool_classes[name] = tool_class
                self.logger.debug(f"Registered tool class: {name}")

                # Register tool specification if provided
                if tool_spec:
                    self.tool_specs[name] = tool_spec
                    self._update_capability_index(name, tool_spec.capabilities)

                self.logger.info(f"Successfully registered tool class: {name}")

            except Exception as e:
                self.error_handler.handle_error(
                    e,
                    context={
                        "operation": "register_tool_class",
                        "tool_name": name,
                        "component": "ToolRegistry"
                    }
                )
                raise

    def register_configuration(self, tool_name: str, config: Dict[str, Any]) -> None:
        """
        Register a base configuration for a tool.

        Args:
            tool_name: Tool name
            config: Configuration dictionary
        """
        with self._registry_lock:
            try:
                if tool_name not in self.configurations:
                    self.configurations[tool_name] = {}

                self.configurations[tool_name] = config.copy()
                self.logger.debug(f"Registered configuration for tool: {tool_name}")

            except Exception as e:
                self.error_handler.handle_error(
                    e,
                    context={
                        "operation": "register_configuration",
                        "tool_name": tool_name,
                        "component": "ToolRegistry"
                    }
                )
                raise

    def register_variant(self, tool_name: str, variant_name: str, config: Dict[str, Any]) -> None:
        """
        Register a configuration variant for a tool.

        Args:
            tool_name: Tool name
            variant_name: Variant name
            config: Configuration dictionary for this variant
        """
        with self._registry_lock:
            try:
                if tool_name not in self.variants:
                    self.variants[tool_name] = {}

                self.variants[tool_name][variant_name] = config.copy()
                self.logger.debug(f"Registered variant '{variant_name}' for tool: {tool_name}")

            except Exception as e:
                self.error_handler.handle_error(
                    e,
                    context={
                        "operation": "register_variant",
                        "tool_name": tool_name,
                        "variant_name": variant_name,
                        "component": "ToolRegistry"
                    }
                )
                raise

    def get_tool(self, name: str) -> Optional[AbstractTool]:
        """
        Get a tool instance by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        with self._registry_lock:
            return self.tools.get(name)

    def get_tool_class(self, name: str) -> Optional[Type[AbstractTool]]:
        """
        Get a tool class by name.

        Args:
            name: Tool name

        Returns:
            Tool class or None if not found
        """
        with self._registry_lock:
            return self.tool_classes.get(name)

    def get_tool_spec(self, name: str) -> Optional[ToolSpec]:
        """
        Get tool specification by name.

        Args:
            name: Tool name

        Returns:
            ToolSpec instance or None if not found
        """
        with self._registry_lock:
            return self.tool_specs.get(name)

    def get_tools(self, names: List[str]) -> List[AbstractTool]:
        """
        Get multiple tools by name.

        Args:
            names: List of tool names

        Returns:
            List of tool instances (missing tools are skipped)
        """
        with self._registry_lock:
            return [self.tools[name] for name in names if name in self.tools]

    def get_tools_by_capability(self, capability: str) -> List[AbstractTool]:
        """
        Get tools that have a specific capability.

        Args:
            capability: Required capability

        Returns:
            List of tools with the specified capability
        """
        with self._registry_lock:
            tool_names = self.capability_index.get(capability, set())
            return [self.tools[name] for name in tool_names if name in self.tools]

    def get_tools_by_capabilities(self, capabilities: List[str], require_all: bool = True) -> List[AbstractTool]:
        """
        Get tools that have specified capabilities.

        Args:
            capabilities: List of required capabilities
            require_all: If True, tool must have ALL capabilities; if False, ANY capability

        Returns:
            List of tools matching capability requirements
        """
        with self._registry_lock:
            if not capabilities:
                return list(self.tools.values())

            matching_tools = []
            for tool_name, tool in self.tools.items():
                tool_spec = self.tool_specs.get(tool_name)
                if tool_spec:
                    if require_all:
                        if all(cap in tool_spec.capabilities for cap in capabilities):
                            matching_tools.append(tool)
                    else:
                        if any(cap in tool_spec.capabilities for cap in capabilities):
                            matching_tools.append(tool)

            return matching_tools

    def get_tool_configuration(self, tool_name: str, variant: str = "default") -> Dict[str, Any]:
        """
        Get the configuration for a tool, optionally with a specific variant.

        Args:
            tool_name: Tool name
            variant: Variant name (default: "default")

        Returns:
            Configuration dictionary (merged base + variant)
        """
        with self._registry_lock:
            # Get base configuration
            base_config = self.configurations.get(tool_name, {})

            # Get variant configuration
            variant_config = {}
            if tool_name in self.variants and variant in self.variants[tool_name]:
                variant_config = self.variants[tool_name][variant]

            # Merge configurations (variant overrides base)
            return self._deep_merge(base_config, variant_config)

    def resolve_tool_spec(self, spec: str) -> tuple:
        """
        Resolve a tool specification string to tool name, variants, and parameters.

        Format: tool_name[:variant1][:variant2][@param1=value1,param2=value2]

        Args:
            spec: Tool specification string

        Returns:
            Tuple of (tool_name, [variants], {params})
        """
        try:
            # Parse the tool specification
            if '@' in spec:
                base_part, params_part = spec.split('@', 1)
                params = {}
                if params_part:
                    for param in params_part.split(','):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            params[key.strip()] = value.strip()
            else:
                base_part = spec
                params = {}

            # Split by colon to get variants
            parts = base_part.split(':')
            tool_name = parts[0].strip()
            variants = [v.strip() for v in parts[1:]] if len(parts) > 1 else ["default"]

            return tool_name, variants, params

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "operation": "resolve_tool_spec",
                    "spec": spec,
                    "component": "ToolRegistry"
                }
            )
            raise ValueError(f"Invalid tool specification: {spec}")

    def get_all_tools(self) -> List[AbstractTool]:
        """
        Get all registered tools.

        Returns:
            List of all tool instances
        """
        with self._registry_lock:
            return list(self.tools.values())

    def get_tool_names(self) -> List[str]:
        """
        Get names of all registered tools.

        Returns:
            List of tool names
        """
        with self._registry_lock:
            return list(self.tools.keys())
    
    def list_registered_tools(self) -> List[str]:
        """
        List all registered tool names.
        
        This is an alias for get_tool_names() for compatibility.

        Returns:
            List of tool names
        """
        return self.get_tool_names()

    def get_available_capabilities(self) -> List[str]:
        """
        Get all available capabilities across registered tools.

        Returns:
            List of unique capabilities
        """
        with self._registry_lock:
            return list(self.capability_index.keys())

    def has_tool(self, name: str) -> bool:
        """
        Check if a tool is registered.

        Args:
            name: Tool name

        Returns:
            True if tool is registered
        """
        with self._registry_lock:
            return name in self.tools

    def clear(self) -> None:
        """
        Clear all registered tools and configurations.
        
        This method should only be used for testing purposes.
        """
        with self._registry_lock:
            self.tools.clear()
            self.tool_classes.clear()
            self.tool_specs.clear()
            self.configurations.clear()
            self.variants.clear()
            self.capability_index.clear()
            self.logger.debug("Registry cleared")

    def get_tool_variants(self, tool_name: str) -> List[str]:
        """
        Get all available variants for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            List of variant names for the tool (empty if no variants)
        """
        with self._registry_lock:
            if tool_name in self.variants:
                return list(self.variants[tool_name].keys())
            return []

    def get_registry_info(self) -> Dict[str, Any]:
        """
        Get comprehensive registry information.

        Returns:
            Dictionary with registry statistics and metadata
        """
        with self._registry_lock:
            return {
                "total_tools": len(self.tools),
                "total_tool_classes": len(self.tool_classes),
                "total_configurations": len(self.configurations),
                "total_variants": sum(len(variants) for variants in self.variants.values()),
                "available_capabilities": list(self.capability_index.keys()),
                "registered_tools": list(self.tools.keys())
            }

    def _update_capability_index(self, tool_name: str, capabilities: List[str]) -> None:
        """
        Update the capability index with tool capabilities.

        Args:
            tool_name: Name of the tool
            capabilities: List of capabilities to index
        """
        for capability in capabilities:
            if capability not in self.capability_index:
                self.capability_index[capability] = set()
            self.capability_index[capability].add(tool_name)

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two configuration dictionaries.

        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary

        Returns:
            Merged configuration dictionary
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result