# rvandroid/tools/tool_factory.py
"""
Factory for creating and configuring tool instances.
"""
import logging
from typing import Dict, List, Any, Optional, Type

from rv_android_core.config.component_configurator import ComponentConfigurator
from rv_android_core.tools.registry import ToolRegistry
from rv_android_core.tools.tool_spec import AbstractTool
from rv_android_core.util.config_utils import deep_merge


class ToolFactory:
    """
    Factory for creating and configuring tool instances based on specifications.

    ### Architectural Decisions:
    - Implements factory pattern for tool creation
    - Separates tool creation from tool configuration
    - Supports dynamic construction of tools from specifications
    - Integrates with ComponentConfigurator for LLM configuration

    ### Role in the System:
    - Creates properly configured tool instances
    - Translates tool specifications to concrete objects
    - Handles merging of configurations from different sources
    - Provides a unified interface for tool instantiation
    """

    @staticmethod
    def create_tool_from_spec(spec: str) -> AbstractTool:
        """
        Create a tool from a specification string.

        Format: tool_name[:variant1][:variant2][@param1=value1,param2=value2]

        Args:
            spec: Tool specification string

        Returns:
            Configured tool instance

        Raises:
            ValueError: If tool specification is invalid or tool not found
        """
        registry = ToolRegistry.get_instance()
        tool_name, variants, params = registry.resolve_tool_spec(spec)

        # Check if tool exists
        base_tool = registry.get_tool(tool_name)
        if not base_tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        # If no variants or params, return the base tool
        if variants == ["default"] and not params:
            return base_tool

        # Otherwise, create a configured copy of the tool
        return ToolFactory.create_configured_tool(tool_name, variants, params)

    @staticmethod
    def create_configured_tool(
            tool_name: str,
            variants: List[str] = None,
            params: Dict[str, Any] = None
    ) -> AbstractTool:
        """
        Create a configured copy of a tool.

        Args:
            tool_name: Name of the tool
            variants: List of variant names to apply (in order)
            params: Additional parameters to override configuration

        Returns:
            Configured tool instance

        Raises:
            ValueError: If tool not found or configuration invalid
        """
        registry = ToolRegistry.get_instance()
        logger = logging.getLogger(__name__)

        # Get the base tool
        base_tool = registry.get_tool(tool_name)
        if not base_tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Start with base configuration
        config = {}

        # Apply variants in sequence
        if variants:
            for variant in variants:
                variant_config = registry.variants.get(tool_name, {}).get(variant)
                if variant_config:
                    config = deep_merge(config, variant_config)
                else:
                    logger.warning(f"Unknown variant '{variant}' for tool '{tool_name}'")

        # Apply custom parameters (highest priority)
        if params:
            # Convert flat params to hierarchical config
            param_config = ToolFactory._params_to_config(tool_name, params)
            config = deep_merge(config, param_config)

        # Create a copy of the tool
        # Note: This assumes tools can be copied directly - actual implementation
        # may need to use the tool's class constructor
        import copy
        tool = copy.deepcopy(base_tool)

        # Configure the tool if it's configurable
        if hasattr(tool, 'configure'):
            tool.configure(config)

        # Special handling for tools with ComponentConfigurator
        if hasattr(tool, 'component_config') and isinstance(tool.component_config, ComponentConfigurator):
            ToolFactory._configure_component(tool.component_config, config)

        return tool

    @staticmethod
    def _configure_component(component_config: ComponentConfigurator, config: Dict[str, Any]) -> None:
        """
        Configure a ComponentConfigurator instance with the provided configuration.

        Args:
            component_config: ComponentConfigurator instance
            config: Configuration dictionary
        """
        # Configure LLM
        if 'llm' in config:
            llm_config = config['llm']
            component_config.set_llm(
                llm_config.get('model_type', 'ollama'),
                llm_config.get('model_name', 'llama3.2:3b'),
                temperature=llm_config.get('temperature', 0.2),
                max_tokens=llm_config.get('max_tokens', 800)
            )

        # Configure strategy
        if 'strategy' in config:
            strategy_config = config['strategy']
            component_config.set_strategy(strategy_config.get('type', 'basic'))

        # Configure parser
        if 'parser' in config:
            parser_config = config['parser']
            component_config.set_parser(parser_config.get('type', 'droidbot'))

        # Configure visitor
        if 'visitor' in config:
            visitor_config = config['visitor']
            component_config.set_visitor(visitor_config.get('type', 'enhanced'))

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
            config['timeout'] = int(params['timeout'])

        # Tool-specific parameter handling
        if tool_name == 'droidbot':
            return ToolFactory._params_to_config_droidbot(params)
        elif tool_name == 'rvandroid' or tool_name == 'rvdroid':
            return ToolFactory._params_to_config_rvandroid(params)

        return config

    @staticmethod
    def _params_to_config_droidbot(params: Dict[str, str]) -> Dict[str, Any]:
        """Convert DroidBot parameters to configuration."""
        config = {}

        if 'policy' in params:
            config['policy'] = params['policy']

        if 'count' in params:
            config['count'] = params['count']

        if 'timeout' in params:
            config['timeout'] = int(params['timeout'])

        return config

    @staticmethod
    def _params_to_config_rvandroid(params: Dict[str, str]) -> Dict[str, Any]:
        """Convert RVAndroid parameters to configuration."""
        config = {}

        # LLM configuration
        llm_config = {}

        if 'model' in params:
            llm_config['model_name'] = params['model']

        if 'model_type' in params:
            llm_config['model_type'] = params['model_type']

        if 'temp' in params:
            llm_config['temperature'] = float(params['temp'])

        if 'max_tokens' in params:
            llm_config['max_tokens'] = int(params['max_tokens'])

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

        return config
