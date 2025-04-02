# rvandroid/tools/configurable_tool.py
"""
Base class for tools that support configuration.
"""
from typing import Dict, Any, Optional

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.task.task_model import Task
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.logging.manager import LoggingManager


class ConfigurableTool(AbstractTool):
    """
    Base class for tools that support rich configuration options.

    ### Architectural Decisions:
    - Extends AbstractTool with configuration capabilities
    - Integrates with ComponentConfigurator for LLM configuration
    - Provides a standard interface for configuration across tools
    - Implements a template method pattern for tool-specific configuration

    ### Role in the System:
    - Serves as a foundation for configurable testing tools
    - Standardizes configuration handling across different tools
    - Enables flexible tool variants without code duplication
    - Provides a bridge between tool registry/factory and specific implementations
    """

    def __init__(self, name: str, description: str, process_pattern: str):
        """
        Initialize a configurable tool.

        Args:
            name: Tool name
            description: Tool description
            process_pattern: Process pattern to kill when cleanup is needed
        """
        super().__init__(name, description, process_pattern)

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(f"tools.{name}")

        # Initialize configuration components
        self.component_config = ComponentConfigurator()
        self.config: Dict[str, Any] = {}

    def configure(self, config: Dict[str, Any]) -> None:
        """
        Configure the tool with the provided configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config.copy()
        self.logger.debug(f"Tool {self.name} configured with: {config}")

        # Call tool-specific configuration
        self.configure_tool_specific(config)

    def configure_tool_specific(self, config: Dict[str, Any]) -> None:
        """
        Configure tool-specific parameters.
        This method should be overridden by subclasses.

        Args:
            config: Configuration dictionary
        """
        pass

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key (supports dot notation for nested values)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        # Support dot notation for nested keys (e.g., "llm.temperature")
        if '.' in key:
            parts = key.split('.')
            current = self.config
            for part in parts[:-1]:
                if part not in current:
                    return default
                current = current[part]
            return current.get(parts[-1], default)

        return self.config.get(key, default)

    def execute(self, task: Task, app: App) -> None:
        """
        Execute the tool with the current configuration.

        Args:
            task: Task to execute
            app: App to test
        """
        self.logger.info(f"Executing {self.name} with configuration: {self.config}")
        super().execute(task, app)
