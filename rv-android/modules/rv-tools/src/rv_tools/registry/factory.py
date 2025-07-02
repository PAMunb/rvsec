"""
Factory for creating and configuring tool instances.

This module provides sophisticated tool creation and configuration capabilities
for the monitored operations testing framework.
"""

import copy
from typing import Dict, List, Any, Optional

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.exceptions import RVToolError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_tools.registry.registry import ToolRegistry


class ToolFactory:
    """
    Factory for creating and configuring tool instances based on specifications.

    ### Architectural Decisions:
    - Implements static factory pattern for tool creation and configuration
    - Separates tool instantiation from tool configuration management
    - Supports dynamic construction of tools from string specifications
    - Provides flexible configuration merging and parameter override capabilities
    - Integrates with ToolRegistry for tool discovery and metadata access
    - Handles both built-in and external plugin-based tool creation

    ### Role in the System:
    - Creates properly configured tool instances for experiment execution
    - Translates tool specifications to concrete configured objects
    - Handles merging of configurations from multiple sources (base, variants, parameters)
    - Provides unified interface for tool instantiation across the framework
    - Enables dynamic tool creation based on experiment requirements
    - Facilitates configuration inheritance and override patterns

    ### Key Considerations:
    - Supports flexible tool specification parsing with variants and parameters
    - Provides comprehensive error handling for invalid specifications and configurations
    - Enables deep configuration merging with proper type handling
    - Supports both instance-based and class-based tool creation patterns
    - Maintains tool configuration state and metadata throughout creation process
    - Integrates with rv-android-core infrastructure for error handling and logging

    ### Integration Strategy:
    - Compatible with ToolRegistry for tool discovery and configuration management
    - Supports experiment framework integration for dynamic tool selection
    - Enables plugin system integration for external tool creation
    - Provides clear extension points for custom tool creation patterns
    - Facilitates configuration validation and parameter processing

    ### Performance and Scalability:
    - Optimized for efficient tool creation and configuration processing
    - Minimizes overhead through smart caching and reuse strategies
    - Supports high-volume tool creation for large-scale experiments
    - Enables lazy configuration evaluation and validation
    - Adaptable to different tool complexity and configuration requirements
    """

    @staticmethod
    def create_tool_from_spec(spec: str, registry: Optional[ToolRegistry] = None) -> AbstractTool:
        """
        Create a tool from a specification string.

        Format: tool_name[:variant1][:variant2][@param1=value1,param2=value2]

        Examples:
        - "ape" - Basic APE tool with default configuration
        - "ape:sata" - APE tool with SATA strategy variant
        - "monkey@event_count=10000" - Monkey with custom event count
        - "ape:bfs@running_minutes=5" - APE with BFS variant and custom timeout

        Args:
            spec: Tool specification string
            registry: Optional registry instance (uses singleton if not provided)

        Returns:
            Configured tool instance

        Raises:
            ValueError: If tool specification is invalid or tool not found
            RuntimeError: If tool creation fails
        """
        if not registry:
            registry = ToolRegistry.get_instance()

        # Set up logging and error handling
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_tools.factory",
            {CONTEXT_COMPONENT: "ToolFactory"}
        )
        error_handler = ErrorHandler.get_instance()

        # Example: Using context manager for scoped error handling
        with error_handler.error_context(component="ToolFactory", phase="tool_creation"):
            logger.debug(f"Creating tool from specification: {spec}")

            # Parse tool specification
            tool_name, variants, params = registry.resolve_tool_spec(spec)
            logger.debug(f"Parsed spec - tool: {tool_name}, variants: {variants}, params: {params}")

            # Check if tool exists
            base_tool = registry.get_tool(tool_name)
            tool_class = registry.get_tool_class(tool_name)

            if not base_tool and not tool_class:
                raise RVToolError(f"Unknown tool: {tool_name}", tool_name=tool_name)

            # If no variants or params and we have an instance, return copy of base tool
            if variants == ["default"] and not params and base_tool:
                logger.debug(f"Returning configured copy of base tool: {tool_name}")
                return ToolFactory._create_tool_copy(base_tool, {}, logger)

            # Create configured tool with variants and parameters
            return ToolFactory._create_configured_tool(
                tool_name=tool_name,
                variants=variants,
                params=params,
                registry=registry,
                logger=logger
            )

    @staticmethod
    def create_configured_tool(
            tool_name: str,
            variants: List[str] = None,
            params: Dict[str, Any] = None,
            registry: Optional[ToolRegistry] = None
    ) -> AbstractTool:
        """
        Create a configured copy of a tool.

        Args:
            tool_name: Name of the tool
            variants: List of variant names to apply (in order)
            params: Additional parameters to override configuration
            registry: Optional registry instance

        Returns:
            Configured tool instance

        Raises:
            ValueError: If tool not found or configuration invalid
            RuntimeError: If tool creation fails
        """
        if not registry:
            registry = ToolRegistry.get_instance()

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_tools.factory",
            {CONTEXT_COMPONENT: "ToolFactory"}
        )

        return ToolFactory._create_configured_tool(
            tool_name=tool_name,
            variants=variants or ["default"],
            params=params or {},
            registry=registry,
            logger=logger
        )

    @staticmethod
    def _create_configured_tool(
            tool_name: str,
            variants: List[str],
            params: Dict[str, Any],
            registry: ToolRegistry,
            logger
    ) -> AbstractTool:
        """
        Internal method to create a configured tool.

        Args:
            tool_name: Name of the tool
            variants: List of variant names to apply
            params: Additional parameters to override
            registry: Registry instance
            logger: Logger instance

        Returns:
            Configured tool instance
        """
        # Get the base tool or tool class
        base_tool = registry.get_tool(tool_name)
        tool_class = registry.get_tool_class(tool_name)

        if not base_tool and not tool_class:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Start with base configuration from registry
        config = registry.configurations.get(tool_name, {}).copy()

        # Apply variants in sequence
        for variant in variants:
            # Skip 'default' variant if no explicit default is defined
            if variant == "default":
                variant_config = registry.variants.get(tool_name, {}).get(variant)
                if variant_config:
                    config = ToolFactory._deep_merge(config, variant_config)
                    logger.debug(f"Applied default variant for tool '{tool_name}'")
                # Skip warning for default variant if not explicitly defined
                continue

            variant_config = registry.variants.get(tool_name, {}).get(variant)
            if variant_config:
                config = ToolFactory._deep_merge(config, variant_config)
                logger.debug(f"Applied variant '{variant}' for tool '{tool_name}'")
            else:
                logger.warning(f"Unknown variant '{variant}' for tool '{tool_name}'")

        # Apply custom parameters (highest priority)
        if params:
            # Convert flat params to hierarchical config
            param_config = ToolFactory._params_to_config(tool_name, params)
            config = ToolFactory._deep_merge(config, param_config)
            logger.debug(f"Applied custom parameters for tool '{tool_name}': {params}")

        # Create tool instance
        if base_tool:
            # Create copy of existing tool instance
            tool = ToolFactory._create_tool_copy(base_tool, config, logger)
        else:
            # Instantiate from tool class
            tool = ToolFactory._create_tool_from_class(tool_class, config, logger, tool_name)

        logger.info(f"Created configured tool: {tool_name}")
        return tool

    @staticmethod
    @ErrorHandler.handle_errors(component="ToolFactory", phase="tool_copy", reraise=True)
    def _create_tool_copy(base_tool: AbstractTool, config: Dict[str, Any], logger) -> AbstractTool:
        """
        Create a copy of an existing tool instance.

        Args:
            base_tool: Base tool instance to copy
            config: Configuration to apply
            logger: Logger instance

        Returns:
            Configured tool copy
        """
        # Example: Decorator handles errors automatically, cleaner code
        # Create a deep copy of the tool
        tool = copy.deepcopy(base_tool)
        logger.debug(f"Created copy of tool: {base_tool.name}")

        # Configure the tool if it supports configuration and has any config data
        if hasattr(tool, 'configure') and callable(tool.configure):
            tool.configure(config)
            logger.debug(f"Applied configuration to tool copy: {base_tool.name}")

        return tool

    @staticmethod
    def _create_tool_from_class(tool_class: type, config: Dict[str, Any], logger,
                                tool_name: str = None) -> AbstractTool:
        """
        Create a tool instance from a tool class.

        Args:
            tool_class: Tool class to instantiate
            config: Configuration to apply
            logger: Logger instance
            tool_name: Optional tool name to use for instantiation

        Returns:
            Configured tool instance
        """
        try:
            # Get class name safely (handle mock objects)
            class_name = getattr(tool_class, '__name__', repr(tool_class))

            # Instantiate the tool class, passing tool_name if supported
            try:
                # Try to instantiate with tool_name if the constructor supports it
                import inspect
                sig = inspect.signature(tool_class.__init__)
                if 'name' in sig.parameters and tool_name:
                    tool = tool_class(name=tool_name)
                    logger.debug(f"Instantiated tool from class: {class_name} with name: {tool_name}")
                else:
                    tool = tool_class()
                    logger.debug(f"Instantiated tool from class: {class_name}")
            except (TypeError, ValueError):
                # Fallback to parameterless constructor
                tool = tool_class()
                logger.debug(f"Instantiated tool from class: {class_name} (fallback)")

            # Configure the tool if it supports configuration
            if hasattr(tool, 'configure') and callable(tool.configure):
                tool.configure(config)
                # Get tool name safely for logging
                tool_name = getattr(tool, 'name', 'unknown')
                logger.debug(f"Applied configuration to tool instance: {tool_name}")

            return tool

        except Exception as e:
            # Get class name safely for error messages
            class_name = getattr(tool_class, '__name__', repr(tool_class))
            logger.error(f"Failed to create tool from class: {str(e)}")
            raise RuntimeError(f"Failed to create tool from class '{class_name}': {str(e)}")

    @staticmethod
    def _params_to_config(tool_name: str, params: Dict[str, str]) -> Dict[str, Any]:
        """
        Convert flat parameters to hierarchical configuration structure.

        Args:
            tool_name: Tool name (for tool-specific handling)
            params: Flat parameter dictionary

        Returns:
            Hierarchical configuration dictionary
        """
        config = {}

        # General parameter handling
        if 'timeout' in params:
            try:
                config['timeout'] = int(params['timeout'])
            except ValueError:
                pass  # Ignore invalid timeout values

        if 'verbose' in params:
            # Convert string boolean to actual boolean
            verbose_value = params['verbose'].lower()
            config['verbose'] = verbose_value in ('true', '1', 'yes', 'on')

        if 'device_id' in params:
            config['device_id'] = params['device_id']

        # Tool-specific parameter handling
        if tool_name == 'ape':
            config.update(ToolFactory._params_to_config_ape(params))
        elif tool_name == 'monkey':
            config.update(ToolFactory._params_to_config_monkey(params))
        elif tool_name == 'droidbot':
            config.update(ToolFactory._params_to_config_droidbot(params))
        elif tool_name in ['rvandroid', 'rvdroid']:
            config.update(ToolFactory._params_to_config_rvandroid(params))

        return config

    @staticmethod
    def _params_to_config_ape(params: Dict[str, str]) -> Dict[str, Any]:
        """Convert APE parameters to configuration."""
        config = {}

        if 'strategy' in params:
            config['strategy'] = params['strategy']

        if 'running_minutes' in params:
            try:
                config['running_minutes'] = int(params['running_minutes'])
            except ValueError:
                pass

        if 'device_id' in params:
            config['device_id'] = params['device_id']

        return config

    @staticmethod
    def _params_to_config_monkey(params: Dict[str, str]) -> Dict[str, Any]:
        """Convert Monkey parameters to configuration."""
        config = {}

        if 'event_count' in params:
            try:
                config['event_count'] = int(params['event_count'])
            except ValueError:
                pass

        if 'seed' in params:
            try:
                config['seed'] = int(params['seed'])
            except ValueError:
                pass

        if 'throttle' in params:
            try:
                config['throttle'] = int(params['throttle'])
            except ValueError:
                pass

        if 'device_id' in params:
            config['device_id'] = params['device_id']

        if 'verbosity' in params:
            try:
                config['verbosity'] = int(params['verbosity'])
            except ValueError:
                pass

        # Boolean flags
        boolean_flags = [
            'ignore_crashes', 'ignore_timeouts', 'ignore_monitored_violations',
            'kill_process_after_error', 'monitor_native_crashes'
        ]

        for flag in boolean_flags:
            if flag in params:
                config[flag] = params[flag].lower() in ('true', '1', 'yes', 'on')

        return config

    @staticmethod
    def _params_to_config_droidbot(params: Dict[str, str]) -> Dict[str, Any]:
        """Convert DroidBot parameters to configuration."""
        config = {}

        if 'policy' in params:
            config['policy'] = params['policy']

        if 'count' in params:
            try:
                config['count'] = int(params['count'])
            except ValueError:
                pass

        if 'interval' in params:
            try:
                config['interval'] = int(params['interval'])
            except ValueError:
                pass

        if 'device_id' in params:
            config['device_id'] = params['device_id']

        return config

    @staticmethod
    def _params_to_config_rvandroid(params: Dict[str, str]) -> Dict[str, Any]:
        """Convert RVAndroid/RVDroid parameters to configuration."""
        config = {}

        # LLM configuration
        llm_config = {}

        if 'model' in params:
            llm_config['model_name'] = params['model']

        if 'model_type' in params:
            llm_config['model_type'] = params['model_type']

        if 'temp' in params or 'temperature' in params:
            try:
                temp_value = params.get('temp', params.get('temperature'))
                llm_config['temperature'] = float(temp_value)
            except ValueError:
                pass

        if 'max_tokens' in params:
            try:
                llm_config['max_tokens'] = int(params['max_tokens'])
            except ValueError:
                pass

        if llm_config:
            config['llm'] = llm_config

        # Strategy configuration
        if 'strategy' in params:
            config['strategy'] = {'type': params['strategy']}

        # Parser configuration
        if 'parser' in params:
            config['parser'] = {'type': params['parser']}

        # Visitor configuration
        if 'visitor' in params:
            config['visitor'] = {'type': params['visitor']}

        # Device configuration
        if 'device_id' in params:
            config['device_id'] = params['device_id']

        return config

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
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
                result[key] = ToolFactory._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def batch_create_tools(specs: List[str], registry: Optional[ToolRegistry] = None) -> List[AbstractTool]:
        """
        Create multiple tools from a list of specifications.

        Args:
            specs: List of tool specification strings
            registry: Optional registry instance

        Returns:
            List of configured tool instances

        Raises:
            ValueError: If any specification is invalid
        """
        if not registry:
            registry = ToolRegistry.get_instance()

        tools = []
        for spec in specs:
            tool = ToolFactory.create_tool_from_spec(spec, registry)
            tools.append(tool)

        return tools

    @staticmethod
    def validate_tool_spec(spec: str, registry: Optional[ToolRegistry] = None) -> bool:
        """
        Validate a tool specification without creating the tool.

        Args:
            spec: Tool specification string
            registry: Optional registry instance

        Returns:
            True if specification is valid, False otherwise
        """
        try:
            if not registry:
                registry = ToolRegistry.get_instance()

            tool_name, variants, params = registry.resolve_tool_spec(spec)

            # Check if tool exists
            if not registry.has_tool(tool_name) and tool_name not in registry.tool_classes:
                return False

            # Validate variants exist
            tool_variants = registry.variants.get(tool_name, {})
            for variant in variants:
                if variant != "default" and variant not in tool_variants:
                    return False

            return True

        except Exception:
            return False
