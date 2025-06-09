"""
Configurable tool base class providing rich configuration capabilities.

This module extends AbstractTool with comprehensive configuration management
for monitored operations testing tools.
"""

from typing import Dict, Any, Optional

from rv_android_core.app import App
from .abstract_tool import AbstractTool


class ConfigurableTool(AbstractTool):
    """
    Base class for tools that support rich configuration options.

    ### Architectural Decisions:
    - Extends AbstractTool with comprehensive configuration capabilities
    - Provides standardized interface for configuration across tools
    - Implements template method pattern for tool-specific configuration
    - Supports hierarchical configuration with dot notation access
    - Enables flexible tool variants without code duplication

    ### Role in the System:
    - Serves as foundation for configurable monitored operations testing tools
    - Standardizes configuration handling across different tool implementations
    - Enables flexible tool variants and parameter customization
    - Provides bridge between tool registry/factory and specific implementations
    - Facilitates experiment-specific tool configuration management

    ### Key Considerations:
    - Supports both flat and hierarchical configuration structures
    - Provides type-safe configuration access with default values
    - Enables tool-specific configuration validation and processing
    - Maintains configuration state throughout tool lifecycle
    - Integrates with tool factory and registry systems

    ### Integration Strategy:
    - Compatible with ToolFactory configuration merging
    - Supports ToolRegistry variant management
    - Enables dynamic configuration through experiment specifications
    - Provides clear extension points for tool-specific configuration
    - Facilitates configuration inheritance and override patterns
    """

    def __init__(self, name: str, description: str, process_pattern: str):
        """
        Initialize a configurable tool with default configuration.

        Args:
            name: Unique tool identifier
            description: Human-readable tool description
            process_pattern: Pattern for identifying related processes to cleanup
        """
        super().__init__(name, description, process_pattern)
        
        # Initialize configuration storage
        self.config: Dict[str, Any] = {}
        
        self.logger.debug(f"Initialized configurable tool: {name}")

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the tool with provided configuration dictionary.
        
        This method applies the configuration and delegates to tool-specific
        configuration handling for custom parameter processing.

        Args:
            config: Configuration dictionary with tool parameters
        """
        # Store the configuration
        self.config = config.copy() if config else {}
        
        self.logger.debug(f"Tool {self.name} configured with: {self.config}")
        
        # Call tool-specific configuration hook
        self.configure_tool_specific(config)

    def configure_tool_specific(self, config: Dict[str, Any]) -> None:
        """
        Configure tool-specific parameters.
        
        This method should be overridden by subclasses to handle
        tool-specific configuration requirements and validation.
        
        Args:
            config: Configuration dictionary
        """
        # Default implementation does nothing
        # Subclasses should override this method for custom configuration
        pass

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value with support for nested keys.
        
        This method supports dot notation for accessing nested configuration
        values (e.g., "llm.temperature" accesses config["llm"]["temperature"]).
        
        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key not found
            
        Returns:
            Configuration value or default if not found
        """
        # Handle dot notation for nested keys
        if '.' in key:
            return self._get_nested_value(key, default)
        
        return self.config.get(key, default)

    def _get_nested_value(self, key: str, default: Any) -> Any:
        """
        Get nested configuration value using dot notation.
        
        Args:
            key: Dot-separated key path (e.g., "llm.temperature")
            default: Default value if path not found
            
        Returns:
            Nested value or default
        """
        parts = key.split('.')
        current = self.config
        
        try:
            for part in parts[:-1]:
                if part not in current or not isinstance(current[part], dict):
                    return default
                current = current[part]
            
            return current.get(parts[-1], default)
            
        except (KeyError, TypeError):
            return default

    def set_config_value(self, key: str, value: Any) -> None:
        """
        Set a configuration value with support for nested keys.
        
        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        if '.' in key:
            self._set_nested_value(key, value)
        else:
            self.config[key] = value

    def _set_nested_value(self, key: str, value: Any) -> None:
        """
        Set nested configuration value using dot notation.
        
        Args:
            key: Dot-separated key path
            value: Value to set
        """
        parts = key.split('.')
        current = self.config
        
        # Navigate to the parent dictionary
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        
        # Set the final value
        current[parts[-1]] = value

    def has_config(self, key: str) -> bool:
        """
        Check if a configuration key exists.
        
        Args:
            key: Configuration key (supports dot notation)
            
        Returns:
            True if key exists, False otherwise
        """
        if '.' in key:
            parts = key.split('.')
            current = self.config
            
            try:
                for part in parts[:-1]:
                    if part not in current or not isinstance(current[part], dict):
                        return False
                    current = current[part]
                
                return parts[-1] in current
                
            except (KeyError, TypeError):
                return False
        
        return key in self.config

    def get_config_dict(self) -> Dict[str, Any]:
        """
        Get a copy of the complete configuration dictionary.
        
        Returns:
            Copy of the configuration dictionary
        """
        return self.config.copy()

    def clear_config(self) -> None:
        """Clear all configuration values."""
        self.config.clear()
        self.logger.debug(f"Cleared configuration for tool: {self.name}")

    def execute(self, task: Any, app: App) -> None:
        """
        Execute the tool with current configuration.
        
        This method logs the configuration state before delegating
        to the parent execution workflow.
        
        Args:
            task: Task configuration and context
            app: Application under test
        """
        if self.config:
            self.logger.info(f"Executing {self.name} with configuration: {self.config}")
        else:
            self.logger.info(f"Executing {self.name} with default configuration")
        
        # Delegate to parent execution workflow
        super().execute(task, app)

    def execute_tool_specific_logic(self, task: Any, app: App) -> None:
        """
        Default implementation that can be overridden by subclasses.
        
        For tools that need to implement specific logic, override this method.
        This default implementation logs a message indicating the tool execution.
        
        Args:
            task: Task configuration and context
            app: Application under test
        """
        self.logger.info(f"Executing {self.name} tool for app: {app.name}")
        # Default implementation - subclasses should override for specific behavior
    
    def get_tool_info(self) -> dict:
        """
        Get extended tool information including configuration.
        
        Returns:
            Dictionary containing tool metadata and current configuration
        """
        info = super().get_tool_info()
        info["configuration"] = self.get_config_dict()
        info["configurable"] = True
        return info