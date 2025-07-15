# rvandroid/config/configuration.py
"""
Centralized configuration system for rv-android.
Provides a unified approach to managing configuration parameters.
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional, TypeVar, Generic, Type

from rvandroid.constants import (
    ENV_MEMORY_FILE, ENV_REPETITIONS, ENV_TIMEOUTS, ENV_TOOLS,
    ENV_SKIP_MONITORS, ENV_SKIP_INSTRUMENT, ENV_SKIP_STATIC_ANALYSIS,
    ENV_SKIP_EXPERIMENT, ENV_NO_WINDOW, ENV_DEBUG, ENV_HUMANOID_URL,
    ENV_RVANDROID_URL
)

T = TypeVar('T')


class ConfigValue(Generic[T]):
    """
    Generic configuration value wrapper with validation and type conversion.
    """

    def __init__(self, key: str, default: T, value_type: Type[T],
                 description: str = "", env_var: Optional[str] = None,
                 choices: Optional[List[T]] = None, validator=None):
        """
        Initialize configuration value.

        Args:
            key: Configuration key
            default: Default value
            value_type: Expected type
            description: Human-readable description
            env_var: Environment variable to read from
            choices: Valid choices for the value
            validator: Optional validation function
        """
        self.key = key
        self.default = default
        self.value_type = value_type
        self.description = description
        self.env_var = env_var
        self.choices = choices
        self.validator = validator
        self._value = default

    @property
    def value(self) -> T:
        """Get the current value."""
        return self._value

    @value.setter
    def value(self, new_value: Any) -> None:
        """
        Set a new value with validation.

        Args:
            new_value: New value to set

        Raises:
            ValueError: If value is invalid
            TypeError: If value is of wrong type
        """
        # Try to convert to the expected type
        if new_value is not None:
            try:
                if self.value_type == bool and isinstance(new_value, str):
                    # Special handling for booleans
                    new_value = new_value.lower() in ('true', 'yes', '1', 'y')
                elif self.value_type == list or getattr(self.value_type, "__origin__", None) == list:
                    # Special handling for lists (including List[str] and similar)
                    if isinstance(new_value, str):
                        # Convert string to list
                        new_value = new_value.split()
                    elif not isinstance(new_value, list):
                        # Convert other types to list if possible
                        new_value = list(new_value)
                elif getattr(self.value_type, "__origin__", None) == dict:
                    # Special handling for Dict[K, V] and similar
                    if isinstance(new_value, str):
                        # Try to parse JSON
                        import json
                        new_value = json.loads(new_value)
                    elif not isinstance(new_value, dict):
                        new_value = dict(new_value)
                else:
                    # Standard type conversion
                    new_value = self.value_type(new_value)
            except (ValueError, TypeError) as e:
                # More specific error message with type name
                type_name = getattr(self.value_type, "__name__", str(self.value_type))
                raise TypeError(f"Cannot convert {new_value} to {type_name}")

        # Check choices if specified
        if self.choices is not None and new_value not in self.choices:
            raise ValueError(f"Value {new_value} not in valid choices: {self.choices}")

        # Run custom validator if provided
        if self.validator is not None and not self.validator(new_value):
            raise ValueError(f"Value {new_value} failed validation")

        self._value = new_value


class Configuration:
    """
    A centralized, type-safe configuration management system for the RV-Android framework.

    ### Architectural Decisions:
    - Implements a singleton pattern for global configuration access
    - Uses type-safe configuration value management
    - Supports multiple configuration sources (environment, files)
    - Provides comprehensive validation and type conversion

    ### Role in the System:
    - Acts as the central source of truth for all configuration parameters
    - Normalizes access to environment variables and defaults
    - Provides validation to ensure configuration integrity
    - Supports dynamic configuration updates and schema management

    ### Key Considerations:
    - Handles complex configuration scenarios with robust type handling
    - Supports environment variable overrides
    - Provides detailed schema information and validation
    - Enables flexible configuration loading and saving

    ### Integration Strategy:
    - Configurable across different components of the RV-Android framework
    - Supports JSON-based configuration files
    - Compatible with runtime and static configuration updates
    - Provides comprehensive configuration introspection

    ### Performance and Scalability:
    - Lightweight configuration management with minimal overhead
    - Efficient type conversion and validation mechanisms
    - Supports large-scale configuration scenarios
    - Designed for extensibility and future configuration needs
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the configuration."""
        if cls._instance is None:
            cls._instance = Configuration()
        return cls._instance

    def __init__(self):
        """Initialize configuration with default values."""
        self.logger = logging.getLogger(__name__)

        # Define configuration schema with default values and metadata
        self.schema: Dict[str, ConfigValue] = {
            "repetitions": ConfigValue(
                key="repetitions",
                default=1,
                value_type=int,
                description="Number of repetitions for each task",
                env_var=ENV_REPETITIONS,
                validator=lambda x: x > 0
            ),
            "timeouts": ConfigValue(
                key="timeouts",
                default=[60],
                value_type=List[int],
                description="List of timeouts to test in seconds",
                env_var=ENV_TIMEOUTS,
                validator=lambda x: all(t > 0 for t in x)
            ),
            "tools": ConfigValue(
                key="tools",
                default=["monkey"],
                value_type=list,
                description="List of testing tools to use",
                env_var=ENV_TOOLS
            ),
            "generate_monitors": ConfigValue(
                key="generate_monitors",
                default=True,
                value_type=bool,
                description="Whether to generate monitors",
                env_var=ENV_SKIP_MONITORS
            ),
            "instrument": ConfigValue(
                key="instrument",
                default=True,
                value_type=bool,
                description="Whether to instrument APKs",
                env_var=ENV_SKIP_INSTRUMENT
            ),
            "static_analysis": ConfigValue(
                key="static_analysis",
                default=True,
                value_type=bool,
                description="Whether to perform static analysis",
                env_var=ENV_SKIP_STATIC_ANALYSIS
            ),
            "skip_experiment": ConfigValue(
                key="skip_experiment",
                default=False,
                value_type=bool,
                description="Whether to skip the experiment execution",
                env_var=ENV_SKIP_EXPERIMENT
            ),
            "no_window": ConfigValue(
                key="no_window",
                default=True,
                value_type=bool,
                description="Whether to run emulator without window",
                env_var=ENV_NO_WINDOW
            ),
            "memory_file": ConfigValue(
                key="memory_file",
                default="",
                value_type=str,
                description="Path to a previous execution state file",
                env_var=ENV_MEMORY_FILE
            ),
            "debug": ConfigValue(
                key="debug",
                default=False,
                value_type=bool,
                description="Whether to enable debug logging",
                env_var=ENV_DEBUG
            ),
            "humanoid_url": ConfigValue(
                key="humanoid_url",
                default="127.0.0.1:50405",
                value_type=str,
                description="URL for Humanoid service",
                env_var=ENV_HUMANOID_URL
            ),
            "rvandroid_url": ConfigValue(
                key="rvandroid_url",
                default="http://127.0.0.1:5000",
                value_type=str,
                description="URL for RV-Android service",
                env_var=ENV_RVANDROID_URL
            ),
            "export_to_csv": ConfigValue(
                key="export_to_csv",
                default=True,
                value_type=bool,
                description="Whether to export data to CSV files"
            ),
            "csv_coverage_file": ConfigValue(
                key="csv_coverage_file",
                default="coverage_data.csv",
                value_type=str,
                description="Name of the CSV file for coverage data"
            ),
            "csv_error_file": ConfigValue(
                key="csv_error_file",
                default="error_data.csv",
                value_type=str,
                description="Name of the CSV file for error data"
            ),
            "use_enhanced_controller": ConfigValue(
                key="use_enhanced_controller",
                default=False,
                value_type=bool,
                description="Whether to use the enhanced experiment controller"
            ),
            "orchestration_mode": ConfigValue(
                key="orchestration_mode",
                default="SEQUENTIAL",
                value_type=str,
                description="Orchestration mode for experiment execution"
            )
        }

        # Load from environment
        self._load_from_environment()

    def _load_from_environment(self):
        """Load configuration from environment variables."""
        for config_key, config_value in self.schema.items():
            if config_value.env_var and config_value.env_var in os.environ:
                env_value = os.environ[config_value.env_var]

                # Special handling for skip flags
                if config_key in ["generate_monitors", "instrument",
                                  "static_analysis"] and config_value.env_var.startswith("RV_SKIP_"):
                    # ENV_SKIP_X=True means we should set generate_x=False
                    inverted_value = env_value.lower() in ["true", "1", "yes"]
                    try:
                        config_value.value = not inverted_value
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Invalid value for {config_value.env_var}: {env_value}")
                        self.logger.warning(f"Error: {e}")
                else:
                    # Normal case
                    try:
                        config_value.value = env_value
                    except (ValueError, TypeError) as e:
                        self.logger.warning(f"Invalid value for {config_value.env_var}: {env_value}")
                        self.logger.warning(f"Error: {e}")

    def load_from_file(self, file_path: str) -> bool:
        """
        Load configuration from a JSON file.

        Args:
            file_path: Path to the configuration file

        Returns:
            True if loaded successfully, False otherwise
        """
        if not os.path.exists(file_path):
            self.logger.warning(f"Configuration file not found: {file_path}")
            return False

        try:
            with open(file_path, 'r') as f:
                file_config = json.load(f)

            # Update configuration
            for key, value in file_config.items():
                self.set(key, value)

            return True
        except Exception as e:
            self.logger.error(f"Error loading configuration file: {e}")
            return False

    def save_to_file(self, file_path: str) -> bool:
        """
        Save configuration to a JSON file.

        Args:
            file_path: Path to save the configuration

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Convert config to dict
            config_dict = self.to_dict()

            with open(file_path, 'w') as f:
                json.dump(config_dict, f, indent=2)

            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration file: {e}")
            return False

    def get(self, key: str, default=None):
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        if key in self.schema:
            return self.schema[key].value
        return default

    def set(self, key: str, value):
        """
        Set a configuration value with validation.

        Args:
            key: Configuration key
            value: Configuration value

        Raises:
            ValueError: If key is unknown or value is invalid
        """
        if key not in self.schema:
            raise ValueError(f"Unknown configuration key: {key}")

        try:
            self.schema[key].value = value
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid value for {key}: {e}")

    def update(self, config_dict: Dict[str, Any]):
        """
        Update configuration with multiple values.

        Args:
            config_dict: Dictionary of configuration values
        """
        for key, value in config_dict.items():
            try:
                self.set(key, value)
            except ValueError as e:
                self.logger.warning(f"Skipping invalid configuration: {e}")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary of configuration values
        """
        return {key: config_value.value for key, config_value in self.schema.items()}

    def get_schema_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get schema information for all configuration parameters.

        Returns:
            Dictionary with configuration metadata
        """
        result = {}
        for key, config_value in self.schema.items():
            result[key] = {
                "type": config_value.value_type.__name__,
                "default": config_value.default,
                "description": config_value.description,
                "env_var": config_value.env_var,
                "current_value": config_value.value,
                "choices": config_value.choices
            }
        return result
    
    def get_section(self, prefix: str, remove_prefix: bool = True) -> Dict[str, Any]:
        """
        Get a configuration section by prefix.
        
        This method extracts all configuration values that start with the given prefix
        and returns them as a dictionary. This is useful for component-specific
        configuration.
        
        Args:
            prefix: Configuration key prefix (e.g., "llm." for LLM settings)
            remove_prefix: If True, remove the prefix from the keys
            
        Returns:
            Dictionary with section configuration values
        
        Example:
            ```python
            # Get all LLM configuration
            llm_config = config.get_section("llm.")
            # llm_config = {"model": "gpt-3", "temperature": 0.7}
            
            # Without removing prefix
            llm_config = config.get_section("llm.", remove_prefix=False)
            # llm_config = {"llm.model": "gpt-3", "llm.temperature": 0.7}
            ```
        """
        result = {}
        
        for key, config_value in self.schema.items():
            if key.startswith(prefix):
                if remove_prefix:
                    # Remove prefix and return section-relative key
                    section_key = key[len(prefix):]
                else:
                    # Keep full key
                    section_key = key
                    
                result[section_key] = config_value.value
                
        return result
    
    def set_section(self, prefix: str, values: Dict[str, Any], append_prefix: bool = True) -> List[str]:
        """
        Set multiple configuration values in a section.
        
        Args:
            prefix: Configuration key prefix (e.g., "llm." for LLM settings)
            values: Dictionary with configuration values to set
            append_prefix: If True, append the prefix to the keys
            
        Returns:
            List of error messages for values that couldn't be set
            
        Example:
            ```python
            # Set LLM configuration
            config.set_section("llm.", {"model": "gpt-4", "temperature": 0.5})
            
            # Without appending prefix (keys already include it)
            config.set_section("", {"llm.model": "gpt-4"}, append_prefix=False)
            ```
        """
        errors = []
        
        for key, value in values.items():
            full_key = f"{prefix}{key}" if append_prefix else key
            
            try:
                self.set(full_key, value)
            except ValueError as e:
                errors.append(f"Could not set {full_key}: {e}")
                
        return errors

    def validate_all(self) -> List[str]:
        """
        Validate all configuration values.

        Returns:
            List of validation error messages
        """
        errors = []
        for key, config_value in self.schema.items():
            try:
                if config_value.validator:
                    if not config_value.validator(config_value.value):
                        errors.append(f"Invalid value for {key}: {config_value.value}")
            except Exception as e:
                errors.append(f"Error validating {key}: {e}")
        return errors

    def reset_to_defaults(self):
        """Reset all configuration values to defaults."""
        for config_value in self.schema.values():
            config_value._value = config_value.default

    def get_int(self, key: str, default: Optional[int] = None) -> int:
        """Get a configuration value as an integer."""
        value = self.get(key, default)
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"No value for {key} and no default provided")
        return int(value)

    def get_bool(self, key: str, default: Optional[bool] = None) -> bool:
        """Get a configuration value as a boolean."""
        value = self.get(key, default)
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"No value for {key} and no default provided")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'y')
        return bool(value)

    def get_str(self, key: str, default: Optional[str] = None) -> str:
        """Get a configuration value as a string."""
        value = self.get(key, default)
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"No value for {key} and no default provided")
        return str(value)

    def get_list(self, key: str, default: Optional[List] = None) -> List:
        """Get a configuration value as a list."""
        value = self.get(key, default)
        if value is None:
            if default is not None:
                return default
            raise ValueError(f"No value for {key} and no default provided")
        if isinstance(value, str):
            return value.split()
        if not isinstance(value, list):
            return [value]
        return value

    def get_experiment_summary(self) -> str:
        """
        Generate a human-readable summary of the experiment configuration.

        Returns:
            String containing a formatted configuration summary
        """
        # Get core experiment values directly from configuration
        repetitions = self.get_int("repetitions", 1)
        timeouts = self.get_list("timeouts", [60])
        tools = self.get_list("tools", ["monkey"])
        generate_monitors = self.get_bool("generate_monitors", True)
        instrument = self.get_bool("instrument", True)
        static_analysis = self.get_bool("static_analysis", True)
        skip_experiment = self.get_bool("skip_experiment", False)
        memory_file = self.get_str("memory_file", "")
        no_window = self.get_bool("no_window", True)

        # Format the configuration summary
        return (
            f"Experiment configuration:\n"
            f"  - repetitions={repetitions}\n"
            f"  - timeouts={timeouts}\n"
            f"  - tools={tools}\n"
            f"  - pre-process=[\n"
            f"      generate_monitors={generate_monitors},\n"
            f"      instrument={instrument},\n"
            f"      static_analysis={static_analysis}\n"
            f"    ]\n"
            f"  - skip_experiment={skip_experiment}\n"
            f"  - memory_file={memory_file}\n"
            f"  - no_window={no_window}"
        )

    def print_experiment_summary(self) -> None:
        """
        Print a human-readable summary of the experiment configuration.
        """
        summary = self.get_experiment_summary()
        self.logger.info(summary)
