"""
Enhanced Tool Factory with Unified Configuration Support

This module provides streamlined tool creation capabilities with special support
for complex tools like RVAndroid that require unified configuration management,
while maintaining essential functionality for all tool types.

### Architectural Overview:
This factory implements intelligent tool creation that provides special handling
for complex tools like RVAndroid while maintaining simplicity for standard tools,
enabling unified configuration injection and consistent tool instantiation.

### Key Features:
- Unified Configuration Support: Special handling for RVAndroid unified configuration
- Tool Specification Parsing: Supports tool:variant@params format for CLI integration
- Variant Support: Complex variant handling for sophisticated tools
- Configuration Injection: Automatic configuration injection based on tool requirements
- Error Handling: Comprehensive error handling with appropriate recovery strategies

### Design Patterns:
- Factory Method: Tool creation from specifications
- Strategy Pattern: Different creation strategies for different tool types
- Dependency Injection: Configuration injection for complex tools
- Template Method: Common tool creation workflow

### Integration Strategy:
- Integrates with ToolRegistry for tool discovery
- Provides special handling for RVAndroid tool unified configuration
- Maintains compatibility with existing tool creation patterns
- Enables dynamic tool creation based on experiment requirements
"""

from typing import Dict, List, Any, Optional, Tuple

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import ToolNotFoundError, ToolRegistrationError, ToolCreationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_tools.registry.registry import ToolRegistry


class ToolFactory:
    """
    Enhanced factory for creating and configuring tool instances with unified configuration support.

    ### Architectural Decisions:
    - Focuses on essential tool creation with special handling for complex tools
    - Maintains tool:variant@params parsing for CLI integration
    - Uses rv-android-core infrastructure for error handling and logging
    - Provides unified configuration injection for RVAndroid tools
    - Supports dynamic tool creation for experiment execution

    ### Role in the System:
    - Creates properly configured tool instances for experiment execution
    - Translates tool specifications to concrete configured objects
    - Handles tool variant parsing and application
    - Provides unified interface for tool instantiation
    - Enables dynamic tool creation based on experiment requirements

    ### Key Features:
    - Tool specification parsing (tool:variant@params format)
    - Unified configuration injection for RVAndroid tools
    - Tool variant support for complex tools (droidbot, rvandroid)
    - Simple configuration merging and parameter override
    - Integration with ToolRegistry for tool discovery
    - Standardized error handling and logging

    ### Configuration Injection Strategy:
    - Standard tools: Basic parameter injection
    - RVAndroid tool: Unified configuration creation and injection
    - Plugin tools: Configuration through plugin interfaces
    """

    def __init__(self, experiment_config=None):
        """
        Initialize tool factory with optional experiment configuration.
        
        Args:
            experiment_config: Optional experiment configuration for unified config creation
        """
        self.experiment_config = experiment_config
        
        # Initialize logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_tools.registry.factory",
            {CONTEXT_COMPONENT: "ToolFactory"}
        )

    @staticmethod
    @ErrorHandler.handle_errors(
        component="ToolFactory",
        operation="create_tool_from_spec"
    )
    def create_tool_from_spec(spec: str, registry: Optional[ToolRegistry] = None) -> AbstractTool:
        """
        Create tool instance from specification string.
        
        This method parses tool specifications and creates appropriate tool instances
        with proper configuration injection based on tool requirements.
        
        ### Specification Format:
        - Simple: "tool_name"
        - With variants: "tool_name:variant1:variant2"
        - With parameters: "tool_name@param1=value1,param2=value2"
        - Combined: "tool_name:variant@param1=value1"
        
        Args:
            spec: Tool specification string
            registry: Optional tool registry for tool discovery
            
        Returns:
            Configured tool instance
            
        Raises:
            ToolNotFoundError: If tool cannot be found
            ToolCreationError: If tool creation fails
        """
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_tools.registry.factory",
            {CONTEXT_COMPONENT: "ToolFactory"}
        )
        
        # Parse tool specification
        tool_name, variants, params = ToolFactory._parse_tool_spec(spec)
        
        # Get registry
        if registry is None:
            registry = ToolRegistry()
        
        # Create factory instance with experiment config if needed
        factory = ToolFactory()
        
        # Create configured tool
        tool = factory.create_configured_tool(tool_name, variants, params)
        
        logger.info(f"Created tool from spec: {spec}")
        return tool

    @ErrorHandler.handle_errors(
        component="ToolFactory",
        operation="create_configured_tool"
    )
    def create_configured_tool(
        self,
        tool_name: str,
        variants: List[str],
        params: Dict[str, Any]
    ) -> AbstractTool:
        """
        Create configured tool instance with unified configuration injection.
        
        This method creates tool instances with appropriate configuration injection,
        providing special handling for complex tools like RVAndroid that require
        unified configuration management.
        
        ### Configuration Injection Strategy:
        - Standard tools: Basic parameter injection
        - RVAndroid tool: Unified configuration creation and injection
        - Plugin tools: Configuration through plugin interfaces
        
        ### RVAndroid Special Handling:
        Creates unified RvAndroidToolConfig combining LLM and prompt configurations
        based on experiment configuration and tool variants.
        
        Args:
            tool_name: Name of the tool to create
            variants: List of variant specifications
            params: Tool-specific parameters
            
        Returns:
            Configured tool instance ready for execution
            
        Raises:
            ToolCreationError: If tool creation fails
        """
        # Create base tool instance
        tool = self._create_tool_instance(tool_name)
        
        # Special handling for RVAndroid tool
        if tool_name == "rvandroid":
            try:
                # Import here to avoid circular dependencies
                from rvandroid_tool.config.tool_config import RvAndroidToolConfig
                
                # Create unified tool configuration if experiment config is available
                if self.experiment_config:
                    tool_config = RvAndroidToolConfig.from_experiment_config(
                        experiment_config=self.experiment_config,
                        tool_name=tool_name
                    )
                    
                    # Inject unified configuration
                    params['tool_config'] = tool_config
                    
                    self.logger.info(
                        f"Created unified RVAndroid configuration - "
                        f"LLM: {tool_config.llm_config.llm_type}:{tool_config.llm_config.model}, "
                        f"Strategy: {tool_config.prompt_config.strategy_type}"
                    )
                else:
                    self.logger.warning("No experiment config available for RVAndroid tool")
                    
            except Exception as e:
                raise ToolCreationError(f"Failed to create RVAndroid configuration: {e}")
        
        # Apply variants and configure tool
        self._apply_variants(tool, variants)
        
        # Configure tool with parameters
        if hasattr(tool, 'configure'):
            tool.configure(params)
        
        return tool

    def _create_tool_instance(self, tool_name: str) -> AbstractTool:
        """
        Create base tool instance from tool name.
        
        Args:
            tool_name: Name of the tool to create
            
        Returns:
            Base tool instance
            
        Raises:
            ToolNotFoundError: If tool cannot be found
        """
        # Get tool registry
        registry = ToolRegistry()
        
        # Get tool class from registry
        tool_class = registry.get_tool_class(tool_name)
        if tool_class is None:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found in registry")
        
        # Create tool instance
        try:
            tool = tool_class()
            self.logger.debug(f"Created tool instance: {tool_name}")
            return tool
        except Exception as e:
            raise ToolCreationError(f"Failed to create tool '{tool_name}': {e}")

    def _apply_variants(self, tool: AbstractTool, variants: List[str]) -> None:
        """
        Apply variants to tool instance.
        
        Args:
            tool: Tool instance to configure
            variants: List of variants to apply
        """
        if not variants:
            return
        
        # Apply variants if tool supports them
        if hasattr(tool, 'apply_variants'):
            tool.apply_variants(variants)
            self.logger.debug(f"Applied variants to tool: {variants}")

    @staticmethod
    def _parse_tool_spec(spec: str) -> Tuple[str, List[str], Dict[str, Any]]:
        """
        Parse tool specification string into components.
        
        ### Specification Format:
        - Simple: "tool_name"
        - With variants: "tool_name:variant1:variant2"
        - With parameters: "tool_name@param1=value1,param2=value2"
        - Combined: "tool_name:variant@param1=value1"
        
        Args:
            spec: Tool specification string
            
        Returns:
            Tuple of (tool_name, variants, parameters)
        """
        # Split by @ to separate tool/variants from parameters
        if '@' in spec:
            tool_part, params_part = spec.split('@', 1)
            params = ToolFactory._parse_params(params_part)
        else:
            tool_part = spec
            params = {}
        
        # Split by : to separate tool name from variants
        if ':' in tool_part:
            parts = tool_part.split(':')
            tool_name = parts[0]
            variants = parts[1:]
        else:
            tool_name = tool_part
            variants = []
        
        return tool_name, variants, params

    @staticmethod
    def _parse_params(params_str: str) -> Dict[str, Any]:
        """
        Parse parameters string into dictionary.
        
        ### Parameter Format:
        - "param1=value1,param2=value2"
        - Supports string, int, float, and boolean values
        
        Args:
            params_str: Parameters string
            
        Returns:
            Dictionary of parsed parameters
        """
        params = {}
        
        if not params_str:
            return params
        
        # Split by comma to get individual parameters
        for param_pair in params_str.split(','):
            if '=' in param_pair:
                key, value = param_pair.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Try to convert to appropriate type
                params[key] = ToolFactory._convert_param_value(value)
        
        return params

    @staticmethod
    def _convert_param_value(value: str) -> Any:
        """
        Convert parameter value to appropriate type.
        
        Args:
            value: String value to convert
            
        Returns:
            Converted value
        """
        # Try boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Return as string
        return value

    def set_experiment_config(self, experiment_config) -> None:
        """
        Set experiment configuration for unified configuration creation.
        
        Args:
            experiment_config: Experiment configuration instance
        """
        self.experiment_config = experiment_config
        self.logger.debug("Set experiment configuration for unified tool creation")