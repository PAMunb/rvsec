# rvandroid/config/configuration_manager.py
"""
Configuration manager for integrating configuration across the application.
"""
import logging
from typing import Dict, Any, TypeVar, List

from rvandroid.config.configuration import Configuration
from rvandroid.tools.tool_spec import AbstractTool

T = TypeVar('T')


class ConfigurationManager:
    """
    Configuration manager for integrating configuration across components.

    ### Architectural Decisions:
    - Acts as a facade for the Configuration system
    - Provides component-specific configuration methods
    - Simplifies access to configuration values throughout the system

    ### Role in the System:
    - Centralizes configuration access for different components
    - Provides defaults and validation specific to each component
    - Supports customization of configurations
    """

    def __init__(self):
        """Initialize the configuration manager."""
        self.logger = logging.getLogger(__name__)
        self.config = Configuration.get_instance()

    def load_from_args(self, args) -> None:
        """
        Load configuration from command-line arguments.

        Args:
            args: Command-line arguments namespace
        """
        # Create a dictionary from args
        arg_dict = vars(args)

        # Map arguments to configuration keys
        key_mapping = {
            "debug": "debug",
            "r": "repetitions",
            "t": "timeouts",
            "tools": "tools",
            "c": "memory_file",
            "no_window": "no_window",
            "skip_monitors": "generate_monitors",  # Note inversion
            "skip_instrument": "instrument",  # Note inversion
            "skip_static_analysis": "static_analysis",  # Note inversion
            "skip_experiment": "skip_experiment"
        }

        # Update configuration with inverted values for skip flags
        for arg_key, config_key in key_mapping.items():
            if arg_key in arg_dict and arg_dict[arg_key] is not None:
                value = arg_dict[arg_key]

                # Handle inversion for skip flags
                if arg_key.startswith("skip_") and arg_key != "skip_experiment":
                    value = not value

                try:
                    self.config.set(config_key, value)
                except ValueError as e:
                    self.logger.warning(f"Invalid configuration from arguments: {e}")

    def get_experiment_config(self) -> Dict[str, Any]:
        """
        Get configuration for experiment.

        Returns:
            Dictionary with experiment configuration
        """
        return {
            "repetitions": self.config.get_int("repetitions", 1),
            "timeouts": self.config.get_list("timeouts"),
            "generate_monitors": self.config.get_bool("generate_monitors", True),
            "instrument": self.config.get_bool("instrument", True),
            "static_analysis": self.config.get_bool("static_analysis", True),
            "skip_experiment": self.config.get_bool("skip_experiment", False),
            "no_window": self.config.get_bool("no_window", True),
            "memory_file": self.config.get_str("memory_file", "")
        }

    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Dictionary with tool-specific configuration
        """
        # Base configuration for all tools
        tool_config = {
            "timeout": self.config.get_int("timeout", 60),
            "no_window": self.config.get_bool("no_window", True)
        }

        # Tool-specific configurations
        if tool_name == "humanoid":
            tool_config["humanoid_url"] = self.config.get_str("humanoid_url", "127.0.0.1:50405")
        elif tool_name == "rvandroid":
            tool_config["rvandroid_url"] = self.config.get_str("rvandroid_url", "http://127.0.0.1:5000")

        return tool_config

    def get_android_config(self) -> Dict[str, Any]:
        """
        Get configuration for Android operations.

        Returns:
            Dictionary with Android configuration
        """
        return {
            "avd_name": "RVSec",
            "no_window": self.config.get_bool("no_window", True),
            "clean_logcat": True
        }

    def save_configuration(self, filename: str) -> bool:
        """
        Save current configuration to file.

        Args:
            filename: Path to save configuration

        Returns:
            True if saved successfully, False otherwise
        """
        return self.config.save_to_file(filename)

    def load_configuration(self, filename: str) -> bool:
        """
        Load configuration from file.

        Args:
            filename: Path to configuration file

        Returns:
            True if loaded successfully, False otherwise
        """
        return self.config.load_from_file(filename)

    def get_configuration_summary(self) -> str:
        """
        Get a human-readable summary of current configuration.

        Returns:
            String with configuration summary
        """
        schema_info = self.config.get_schema_info()
        summary = ["Current Configuration:"]

        for key, info in schema_info.items():
            env_var = f" (from {info['env_var']})" if info['env_var'] else ""
            current = info['current_value']
            default = info['default']
            modified = current != default
            modified_str = " (modified)" if modified else ""

            summary.append(f"  {key}: {current}{env_var}{modified_str}")

        return "\n".join(summary)


    def get_tools(self, tool_names: List[str]) -> List[AbstractTool]:
        """
        Get tools by name from the available tools.

        Args:
            tool_names: List of tool names to retrieve

        Returns:
            List of tool instances
        """
        # Get available tools from configuration
        config = self.config
        available_tools = config.get("available_tools", [])

        # Convert to dictionary for easy lookup
        tools_dict = {tool.name: tool for tool in available_tools}

        # Get selected tools
        selected_tools = []
        for name in tool_names:
            if name in tools_dict:
                selected_tools.append(tools_dict[name])

        return selected_tools
