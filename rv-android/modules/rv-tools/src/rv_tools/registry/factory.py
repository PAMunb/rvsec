"""
Simplified factory for creating and configuring tool instances.

This module provides streamlined tool creation capabilities with focus on
essential functionality and tool variant support.
"""

from typing import Dict, List, Any, Optional, Tuple

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.exceptions import ToolNotFoundError, ToolRegistrationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_tools.registry.registry import ToolRegistry


class ToolFactory:
    """
    Simplified factory for creating and configuring tool instances.

    ### Architectural Decisions:
    - Focuses on essential tool creation and variant support
    - Maintains tool:variant@params parsing for CLI integration
    - Uses rv-android-core infrastructure for error handling and logging
    - Removes complex configuration merging while preserving variant functionality
    - Supports dynamic tool creation for experiment execution

    ### Role in the System:
    - Creates properly configured tool instances for experiment execution
    - Translates tool specifications to concrete configured objects
    - Handles tool variant parsing and application
    - Provides unified interface for tool instantiation
    - Enables dynamic tool creation based on experiment requirements

    ### Key Features:
    - Tool specification parsing (tool:variant@params format)
    - Tool variant support for complex tools (droidbot, rvandroid)
    - Simple configuration merging and parameter override
    - Integration with simplified ToolRegistry
    - Standardized error handling and logging
    """

    @staticmethod
    @ErrorHandler.handle_errors(
        component="ToolFactory",
        phase="create_tool_from_spec"
    )
    def create_tool_from_spec(spec: str, registry: Optional[ToolRegistry] = None) -> AbstractTool:
        """
        Create a tool from a specification string.

        Format: tool_name[:variant1][:variant2][@param1=value1,param2=value2]

        Examples:
        - "monkey" - Basic Monkey tool with default configuration
        - "droidbot:bfs_greedy" - DroidBot with BFS greedy strategy variant
        - "droidbot:dfs_greedy" - DroidBot with DFS greedy strategy variant
        - "monkey@event_count=10000" - Monkey with custom event count
        - "rvandroid:llama:batch@temperature=0.3" - RVAndroid with model and strategy variants

        Args:
            spec: Tool specification string
            registry: Optional registry instance (uses singleton if not provided)

        Returns:
            Configured tool instance

        Raises:
            ToolNotFoundError: If tool specification is invalid or tool not found
            ToolRegistrationError: If tool creation fails
        """
        if not registry:
            registry = ToolRegistry.get_instance()

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_tools.factory",
            {CONTEXT_COMPONENT: "ToolFactory"}
        )

        try:
            logger.debug(f"Creating tool from specification: {spec}")

            # Parse tool specification
            tool_name, variants, params = ToolFactory._parse_tool_spec(spec)
            logger.debug(f"Parsed spec - tool: {tool_name}, variants: {variants}, params: {params}")

            # Check if tool exists
            if not registry.has_tool(tool_name):
                raise ToolNotFoundError(f"Tool '{tool_name}' not found in registry")

            # Create tool with variants and parameters
            return ToolFactory._create_configured_tool(
                tool_name=tool_name,
                variants=variants,
                params=params,
                registry=registry,
                logger=logger
            )

        except Exception as e:
            raise ToolRegistrationError(f"Failed to create tool from spec '{spec}': {e}") from e

    @staticmethod
    @ErrorHandler.handle_errors(
        component="ToolFactory",
        phase="create_configured_tool"
    )
    def create_configured_tool(
            tool_name: str,
            variants: List[str] = None,
            params: Dict[str, Any] = None,
            registry: Optional[ToolRegistry] = None
    ) -> AbstractTool:
        """
        Create a configured tool instance.

        Args:
            tool_name: Name of the tool
            variants: List of variant names to apply (in order)
            params: Additional parameters to override configuration
            registry: Optional registry instance

        Returns:
            Configured tool instance

        Raises:
            ToolNotFoundError: If tool not found
            ToolRegistrationError: If tool creation fails
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
            variants=variants or [],
            params=params or {},
            registry=registry,
            logger=logger
        )

    @staticmethod
    def _parse_tool_spec(spec: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Parse a tool specification string to tool name, variants, and parameters.

        Format: tool_name[:variant1][:variant2][@param1=value1,param2=value2]

        Args:
            spec: Tool specification string

        Returns:
            Tuple of (tool_name, [variants], {params})

        Raises:
            ValueError: If specification format is invalid
        """
        try:
            # Parse parameters if present
            if '@' in spec:
                base_part, params_part = spec.split('@', 1)
                params = {}
                if params_part:
                    for param in params_part.split(','):
                        if '=' in param:
                            key, value = param.split('=', 1)
                            params[key.strip()] = value.strip()
                        else:
                            # Boolean flag parameter
                            params[param.strip()] = True
            else:
                base_part = spec
                params = {}

            # Split by colon to get tool name and variants
            parts = base_part.split(':')
            tool_name = parts[0].strip()
            variants = [v.strip() for v in parts[1:] if v.strip()]

            if not tool_name:
                raise ValueError("Tool name cannot be empty")

            return tool_name, variants, params

        except Exception as e:
            raise ValueError(f"Invalid tool specification '{spec}': {e}") from e

    @staticmethod
    def _create_configured_tool(
            tool_name: str,
            variants: List[str],
            params: Dict[str, Any],
            registry: ToolRegistry,
            logger
    ) -> AbstractTool:
        """
        Internal method to create a configured tool with variants and parameters.

        Args:
            tool_name: Name of the tool
            variants: List of variant names to apply
            params: Additional parameters to override
            registry: Registry instance
            logger: Logger instance

        Returns:
            Configured tool instance

        Raises:
            ToolNotFoundError: If tool or variant not found
        """
        try:
            # Start with base tool instance
            if variants:
                # Apply first variant as primary configuration
                primary_variant = variants[0]
                tool_instance = registry.get_tool(tool_name, primary_variant)
                logger.debug(f"Created tool '{tool_name}' with primary variant '{primary_variant}'")
                
                # Apply additional variants if present
                for variant in variants[1:]:
                    if registry.has_variant(tool_name, variant):
                        variant_config = registry.get_variant_config(tool_name, variant)
                        if hasattr(tool_instance, 'configure') and callable(tool_instance.configure):
                            tool_instance.configure(variant_config)
                            logger.debug(f"Applied additional variant '{variant}' to tool '{tool_name}'")
                    else:
                        logger.warning(f"Variant '{variant}' not found for tool '{tool_name}', skipping")
            else:
                # Use default configuration
                tool_instance = registry.get_tool(tool_name)
                logger.debug(f"Created tool '{tool_name}' with default configuration")

            # Apply additional parameters if provided
            if params and hasattr(tool_instance, 'configure') and callable(tool_instance.configure):
                tool_instance.configure(params)
                logger.debug(f"Applied additional parameters to tool '{tool_name}': {params}")

            return tool_instance

        except Exception as e:
            raise ToolNotFoundError(f"Failed to create configured tool '{tool_name}': {e}") from e

    @staticmethod
    def get_supported_tools(registry: Optional[ToolRegistry] = None) -> List[str]:
        """
        Get list of all supported tool names.

        Args:
            registry: Optional registry instance

        Returns:
            List of tool names
        """
        if not registry:
            registry = ToolRegistry.get_instance()
        
        return registry.get_tool_names()

    @staticmethod
    def get_tool_variants(tool_name: str, registry: Optional[ToolRegistry] = None) -> List[str]:
        """
        Get list of available variants for a specific tool.

        Args:
            tool_name: Name of the tool
            registry: Optional registry instance

        Returns:
            List of variant names
        """
        if not registry:
            registry = ToolRegistry.get_instance()
        
        return registry.get_tool_variants(tool_name)