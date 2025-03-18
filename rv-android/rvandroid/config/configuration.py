# rvandroid/config/configuration.py
"""
Centralized configuration system for rv-android.
Provides a unified approach to managing configuration parameters.
"""
import json
import logging
import os
from typing import Dict, Any

from rvandroid.constants import (
    ENV_MEMORY_FILE, ENV_REPETITIONS, ENV_TIMEOUTS, ENV_TOOLS,
    ENV_SKIP_MONITORS, ENV_SKIP_INSTRUMENT, ENV_SKIP_STATIC_ANALYSIS,
    ENV_SKIP_EXPERIMENT, ENV_NO_WINDOW, ENV_DEBUG
)


class Configuration:
    """
    Centralized configuration management for rv-android.

    ### Architectural Decisions:
    - Implements a singleton pattern for global configuration access
    - Loads configuration from multiple sources with priority ordering
    - Provides type conversion and validation for configuration values

    ### Role in the System:
    - Acts as the central source of truth for all configuration parameters
    - Normalizes access to environment variables, command-line arguments, and defaults
    - Provides validation to ensure configuration values meet requirements
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

        # Default configuration values
        self.defaults = {
            "repetitions": 1,
            "timeouts": [60],
            "generate_monitors": True,
            "instrument": True,
            "static_analysis": True,
            "skip_experiment": False,
            "no_window": True,
            "memory_file": "",
            "debug": False
        }

        # Environment variable mappings
        self.env_mappings = {
            "repetitions": ENV_REPETITIONS,
            "timeouts": ENV_TIMEOUTS,
            "tools": ENV_TOOLS,
            "generate_monitors": ENV_SKIP_MONITORS,  # Note inversion
            "instrument": ENV_SKIP_INSTRUMENT,  # Note inversion
            "static_analysis": ENV_SKIP_STATIC_ANALYSIS,  # Note inversion
            "skip_experiment": ENV_SKIP_EXPERIMENT,
            "no_window": ENV_NO_WINDOW,
            "memory_file": ENV_MEMORY_FILE,
            "debug": ENV_DEBUG
        }

        # Current configuration
        self.config = self.defaults.copy()

        # Load from environment
        self._load_from_environment()

    def _load_from_environment(self):
        """Load configuration from environment variables."""
        for config_key, env_var in self.env_mappings.items():
            if env_var in os.environ:
                env_value = os.environ[env_var]

                # Handle inversion for skip flags
                if config_key in ["generate_monitors", "instrument", "static_analysis"]:
                    # ENV_SKIP_X=True means we should set generate_x=False
                    inverted_value = env_value.lower() in ["true", "1", "yes"]
                    self.config[config_key] = not inverted_value
                    continue

                # Type conversion based on default type
                default_value = self.defaults.get(config_key)

                if isinstance(default_value, bool):
                    self.config[config_key] = env_value.lower() in ["true", "1", "yes"]
                elif isinstance(default_value, int):
                    try:
                        self.config[config_key] = int(env_value)
                    except ValueError:
                        self.logger.warning(f"Invalid integer value for {env_var}: {env_value}")
                elif isinstance(default_value, list):
                    # For simplicity, assume space-separated values
                    self.config[config_key] = env_value.split()

                    # Convert to int for timeouts
                    if config_key == "timeouts":
                        try:
                            self.config[config_key] = [int(x) for x in self.config[config_key]]
                        except ValueError:
                            self.logger.warning(f"Invalid integer list for {env_var}: {env_value}")
                else:
                    self.config[config_key] = env_value

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
            self.config.update(file_config)
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

            with open(file_path, 'w') as f:
                json.dump(self.config, f, indent=2)

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
        return self.config.get(key, default)

    def set(self, key: str, value):
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value

    def update(self, config_dict: Dict[str, Any]):
        """
        Update configuration with multiple values.

        Args:
            config_dict: Dictionary of configuration values
        """
        self.config.update(config_dict)


# Create a singleton instance
config = Configuration.get_instance()
