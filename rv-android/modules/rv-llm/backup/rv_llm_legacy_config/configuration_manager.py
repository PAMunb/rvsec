# rvandroid/config/configuration_manager.py
"""
Configuration manager for integrating configuration across the application.
Provides interfaces for accessing and managing component-specific configuration.
"""
import json
import logging
import os
from typing import Dict, Any, TypeVar, List

from rv_llm.config.configuration import Configuration

T = TypeVar('T')


class ConfigurationManager:
    """
    A comprehensive configuration management facade for centralizing and simplifying
    configuration access across the RV-Android framework.

    ### Architectural Decisions:
    - Implements a high-level configuration management abstraction
    - Provides a unified interface for configuration access and manipulation
    - Supports multiple configuration sources and loading strategies
    - Enables flexible and type-safe configuration handling
    - Integrates with the component registry system

    ### Role in the System:
    - Acts as the primary configuration management interface
    - Translates between raw configuration data and component-specific requirements
    - Provides validation and transformation of configuration parameters
    - Supports dynamic configuration loading and modification
    - Centralizes configuration logic across different experimental components

    ### Key Considerations:
    - Handles complex configuration scenarios with robust type conversion
    - Supports environment variable and file-based configuration
    - Provides default value management and validation
    - Enables component-specific configuration extraction
    - Supports experiment and tool configuration management

    ### Integration Strategy:
    - Deeply integrated with the RV-Android configuration system
    - Compatible with multiple configuration sources
    - Provides a consistent configuration access mechanism
    - Enables dependency injection of configuration parameters
    - Supports runtime configuration updates

    ### Performance and Scalability:
    - Designed for lightweight configuration management
    - Minimizes overhead in configuration access and transformation
    - Supports large-scale configuration scenarios
    - Adaptable to different experimental complexity levels
    - Provides efficient configuration caching and retrieval
    """

    def __init__(self):
        """Initialize the configuration manager."""
        self.logger = logging.getLogger(__name__)
        self.config = Configuration.get_instance()
        self._register_llm_configuration_schema()

    def _register_llm_configuration_schema(self) -> None:
        """
        Register LLM configuration schema in the global configuration.
        This ensures LLM configuration values are properly validated and documented.
        """
        # Import here to avoid circular imports
        from rv_llm.llm.llm_config import LLMConfiguration

        try:
            # Get schema definition from LLMConfiguration
            llm_schema = LLMConfiguration.schema()

            # Register each parameter with prefix
            for name, schema in llm_schema.items():
                config_key = f"llm.{name}"

                # Convert type name to actual type
                type_name = schema.get("type", "str")
                if type_name == "str":
                    param_type = str
                elif type_name == "int":
                    param_type = int
                elif type_name == "float":
                    param_type = float
                elif type_name == "bool":
                    param_type = bool
                elif type_name == "ParserType":
                    # Handle enum type specially
                    from rv_screen_parser.parser.screen.parser_factory import ParserType
                    param_type = ParserType
                else:
                    param_type = str  # Default to string

                # Add configuration value if not already present
                if config_key not in self.config.schema:
                    from rv_android_core.config.configuration import ConfigValue
                    self.config.schema[config_key] = ConfigValue(
                        key=config_key,
                        default=schema.get("default"),
                        value_type=param_type,
                        description=schema.get("description", "")
                    )
        except (ImportError, AttributeError) as e:
            self.logger.warning(f"Failed to register LLM configuration schema: {e}")

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
            "skip_experiment": "skip_experiment",
            "llm_model": "llm.model_name",
            "llm_type": "llm.model_type",
            "strategy_type": "llm.strategy_type",
            "parser_type": "llm.parser_type"
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
        # First, try to get tool-specific config section
        tool_config = self.config.get_section(f"tool.{tool_name}.")

        # Base configuration for all tools
        base_config = {
            "timeout": self.config.get_int("timeout", 60),
            "no_window": self.config.get_bool("no_window", True)
        }

        # Merge base config with tool-specific config
        merged_config = {**base_config, **tool_config}

        # Tool-specific configurations (legacy support)
        if tool_name == "humanoid" and "humanoid_url" not in merged_config:
            merged_config["humanoid_url"] = self.config.get_str("humanoid_url", "127.0.0.1:50405")
        elif tool_name == "rvandroid" and "rvandroid_url" not in merged_config:
            merged_config["rvandroid_url"] = self.config.get_str("rvandroid_url", "http://127.0.0.1:5000")

        return merged_config

    def get_android_config(self) -> Dict[str, Any]:
        """
        Get configuration for Android operations.

        Returns:
            Dictionary with Android configuration
        """
        # First, try to get android-specific config section
        android_config = self.config.get_section("android.")

        # Default android configuration
        default_config = {
            "avd_name": "RVSec",
            "no_window": self.config.get_bool("no_window", True),
            "clean_logcat": True
        }

        # Merge default config with android-specific config
        return {**default_config, **android_config}

    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM configuration.
        
        Returns:
            Dictionary with LLM configuration
        """
        return self.config.get_section("llm.")

    def get_strategy_config(self) -> Dict[str, Any]:
        """
        Get prompt strategy configuration.
        
        Returns:
            Dictionary with strategy configuration
        """
        return self.config.get_section("strategy.")

    def get_parser_config(self) -> Dict[str, Any]:
        """
        Get parser configuration.
        
        Returns:
            Dictionary with parser configuration
        """
        return self.config.get_section("parser.")

    def get_visitor_config(self) -> Dict[str, Any]:
        """
        Get visitor configuration.
        
        Returns:
            Dictionary with visitor configuration
        """
        return self.config.get_section("visitor.")

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

    def save_component_configuration(self, component: str, filename: str) -> bool:
        """
        Save component-specific configuration to file.
        
        Args:
            component: Component name (e.g., "llm", "strategy")
            filename: Path to save configuration
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Get component configuration
            component_config = self.config.get_section(f"{component}.")

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filename), exist_ok=True)

            # Save to file
            with open(filename, 'w') as f:
                json.dump(component_config, f, indent=2)

            return True
        except Exception as e:
            self.logger.error(f"Error saving component configuration: {e}")
            return False

    def load_component_configuration(self, component: str, filename: str) -> bool:
        """
        Load component-specific configuration from file.
        
        Args:
            component: Component name (e.g., "llm", "strategy")
            filename: Path to configuration file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(filename):
                self.logger.warning(f"Component configuration file not found: {filename}")
                return False

            # Load from file
            with open(filename, 'r') as f:
                component_config = json.load(f)

            # Set component configuration
            errors = self.config.set_section(f"{component}.", component_config)

            if errors:
                for error in errors:
                    self.logger.warning(f"Error loading component configuration: {error}")

            return len(errors) == 0
        except Exception as e:
            self.logger.error(f"Error loading component configuration: {e}")
            return False

    def get_configuration_summary(self) -> str:
        """
        Get a human-readable summary of current configuration.

        Returns:
            String with configuration summary
        """
        schema_info = self.config.get_schema_info()
        summary = ["Current Configuration:"]

        # Group by component
        components = {}
        for key, info in schema_info.items():
            if "." in key:
                component, param = key.split(".", 1)
                if component not in components:
                    components[component] = {}
                components[component][param] = info
            else:
                # Add to general section
                if "general" not in components:
                    components["general"] = {}
                components["general"][key] = info

        # Generate summary by component
        for component, params in components.items():
            summary.append(f"\n  [{component.upper()}]")
            for key, info in params.items():
                env_var = f" (from {info['env_var']})" if info['env_var'] else ""
                current = info['current_value']
                default = info['default']
                modified = current != default
                modified_str = " (modified)" if modified else ""
                summary.append(f"    {key}: {current}{env_var}{modified_str}")

        return "\n".join(summary)


    def create_llm_configuration(self) -> 'LLMConfiguration':
        """
        Create an LLMConfiguration instance from the current configuration.
        
        Returns:
            LLMConfiguration instance
        """
        # Import here to avoid circular imports
        from rv_llm.llm.llm_config import LLMConfiguration

        # Get LLM configuration
        llm_config = self.get_llm_config()

        # Create LLMConfiguration instance
        return LLMConfiguration.from_dict(llm_config)

    def update_from_llm_configuration(self, llm_config: 'LLMConfiguration') -> None:
        """
        Update configuration from an LLMConfiguration instance.
        
        Args:
            llm_config: LLMConfiguration instance
        """
        # Convert to dict and update configuration
        config_dict = llm_config.to_dict()

        # Update configuration
        errors = self.config.set_section("llm.", config_dict)

        if errors:
            for error in errors:
                self.logger.warning(f"Error updating LLM configuration: {error}")
