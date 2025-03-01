import json
import logging
import os
from typing import Dict, Any, Optional, Union

from rvandroid.parser.screen.parser_factory import ParserType

logger = logging.getLogger(__name__)


class LLMConfiguration:
    """
    Configuration class for managing LLM settings.
    Provides a centralized approach to handling configuration from various sources.
    """

    # Default configuration values
    DEFAULT_CONFIG = {
        "model_type": "huggingface",
        "model_name": "microsoft/Phi-3.5-mini-instruct",
        "strategy_type": "basic",
        "parser_type": ParserType.DROIDBOT,
        "max_tokens": 800,
        "temperature": 0.7,
        "model_kwargs": {}
    }

    def __init__(
            self,
            config_file: Optional[str] = None,
            model_type: Optional[str] = None,
            model_name: Optional[str] = None,
            strategy_type: Optional[str] = None,
            parser_type: Optional[Union[ParserType, str]] = None,
            model_kwargs: Optional[Dict[str, Any]] = None,
            **additional_config
    ):
        """
        Initialize the LLM configuration.

        Args:
            config_file: Path to a JSON configuration file (optional)
            model_type: Type of model to use (optional)
            model_name: Name of the model (optional)
            strategy_type: Type of prompt strategy (optional)
            parser_type: Type of parser (optional)
            model_kwargs: Additional model arguments (optional)
            **additional_config: Any additional configuration parameters
        """
        # Start with default configuration
        self.config = self.DEFAULT_CONFIG.copy()

        # Load from environment variables
        self._load_from_env()

        # Load from config file if provided
        if config_file:
            self._load_from_file(config_file)

        # Override with explicitly provided parameters
        if model_type:
            self.config["model_type"] = model_type
        if model_name:
            self.config["model_name"] = model_name
        if strategy_type:
            self.config["strategy_type"] = strategy_type
        if parser_type:
            if isinstance(parser_type, str):
                # Convert string to ParserType enum if needed
                try:
                    self.config["parser_type"] = ParserType(parser_type)
                except ValueError:
                    logger.warning(f"Invalid parser_type string: {parser_type}, using default")
            else:
                self.config["parser_type"] = parser_type
        if model_kwargs:
            self.config["model_kwargs"].update(model_kwargs)

        # Add any additional configuration
        self.config.update(additional_config)

        logger.info(f"Initialized LLM configuration: {self}")

    def _load_from_env(self) -> None:
        """
        Load configuration from environment variables.
        Environment variables take the form RV_* (e.g., RV_MODEL_TYPE).
        """
        # Map of environment variable names to config keys
        env_mapping = {
            "RV_MODEL_TYPE": "model_type",
            "RV_MODEL_NAME": "model_name",
            "RV_STRATEGY_TYPE": "strategy_type",
            "RV_PARSER_TYPE": "parser_type",
            "RV_MAX_TOKENS": "max_tokens",
            "RV_TEMPERATURE": "temperature"
        }

        # Process standard config values
        for env_var, config_key in env_mapping.items():
            if env_var in os.environ:
                value = os.environ[env_var]

                # Handle numeric values
                if config_key in ["max_tokens", "temperature"]:
                    try:
                        value = float(value)
                        if config_key == "max_tokens":
                            value = int(value)
                    except ValueError:
                        logger.warning(f"Invalid numeric value for {env_var}: {value}")
                        continue

                # Handle parser type
                if config_key == "parser_type":
                    try:
                        value = ParserType(value)
                    except ValueError:
                        logger.warning(f"Invalid parser type: {value}")
                        continue

                self.config[config_key] = value

        # Handle model kwargs from environment
        if "RV_MODEL_KWARGS" in os.environ:
            try:
                kwargs_json = os.environ["RV_MODEL_KWARGS"]
                model_kwargs = json.loads(kwargs_json)
                if isinstance(model_kwargs, dict):
                    self.config["model_kwargs"].update(model_kwargs)
                else:
                    logger.warning("RV_MODEL_KWARGS must be a JSON object")
            except json.JSONDecodeError:
                logger.error("Failed to parse RV_MODEL_KWARGS as JSON")

    def _load_from_file(self, config_file: str) -> None:
        """
        Load configuration from a JSON file.

        Args:
            config_file: Path to JSON configuration file
        """
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)

                # Handle special case for parser_type
                if "parser_type" in file_config and isinstance(file_config["parser_type"], str):
                    try:
                        file_config["parser_type"] = ParserType(file_config["parser_type"])
                    except ValueError:
                        logger.warning(f"Invalid parser_type in config file: {file_config['parser_type']}")
                        del file_config["parser_type"]

                # Update configuration
                self.config.update(file_config)
        except Exception as e:
            logger.error(f"Failed to load config from {config_file}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)

    def get_model_type(self) -> str:
        """Get the model type."""
        return self.config["model_type"]

    def get_model_name(self) -> str:
        """Get the model name."""
        return self.config["model_name"]

    def get_strategy_type(self) -> str:
        """Get the strategy type."""
        return self.config["strategy_type"]

    def get_parser_type(self) -> ParserType:
        """Get the parser type."""
        return self.config["parser_type"]

    def get_model_kwargs(self) -> Dict[str, Any]:
        """Get additional model arguments."""
        return self.config["model_kwargs"].copy()

    def get_max_tokens(self) -> int:
        """Get maximum tokens for generation."""
        return self.config["max_tokens"]

    def get_temperature(self) -> float:
        """Get temperature for generation."""
        return self.config["temperature"]

    def update(self, **kwargs) -> None:
        """
        Update configuration with new values.

        Args:
            **kwargs: Configuration key-value pairs
        """
        for key, value in kwargs.items():
            if key == "model_kwargs" and isinstance(value, dict):
                # Merge model_kwargs rather than replace
                self.config["model_kwargs"].update(value)
            else:
                self.config[key] = value

    def save_to_file(self, config_file: str) -> None:
        """
        Save current configuration to a file.

        Args:
            config_file: Path to save configuration
        """
        try:
            # Convert ParserType enum to string for serialization
            serializable_config = self.config.copy()
            if "parser_type" in serializable_config and isinstance(serializable_config["parser_type"], ParserType):
                serializable_config["parser_type"] = serializable_config["parser_type"].value

            with open(config_file, 'w') as f:
                json.dump(serializable_config, f, indent=2)
                logger.info(f"Configuration saved to {config_file}")
        except Exception as e:
            logger.error(f"Failed to save config to {config_file}: {e}")

    def as_dict(self) -> Dict[str, Any]:
        """
        Get configuration as a dictionary.

        Returns:
            Configuration dictionary with ParserType converted to string
        """
        result = self.config.copy()
        if "parser_type" in result and isinstance(result["parser_type"], ParserType):
            result["parser_type"] = result["parser_type"].value
        return result

    def __str__(self) -> str:
        """String representation of the configuration."""
        return (f"LLMConfiguration(model_type={self.get_model_type()}, "
                f"model_name={self.get_model_name()}, "
                f"strategy_type={self.get_strategy_type()}, "
                f"parser_type={self.get_parser_type().value})")


# Predefined configurations for common use cases
DEFAULT_CONFIGS = {
    "local": {
        "model_type": "huggingface",
        "model_name": "microsoft/Phi-3.5-mini-instruct",
        "strategy_type": "basic",
        "parser_type": ParserType.DROIDBOT
    },
    "ollama": {
        "model_type": "ollama",
        "model_name": "phi3.5:3.8b",
        "strategy_type": "basic",
        "parser_type": ParserType.DROIDBOT
    },
    "claude": {
        "model_type": "anthropic",
        "model_name": "claude-3-5-sonnet-20241022",
        "strategy_type": "frontier",
        "parser_type": ParserType.DROIDBOT
    },
    "gpt": {
        "model_type": "openai",
        "model_name": "gpt-4-turbo-2024-04-09",
        "strategy_type": "frontier",
        "parser_type": ParserType.DROIDBOT
    },
    "gemini": {
        "model_type": "google",
        "model_name": "gemini-pro",
        "strategy_type": "frontier",
        "parser_type": ParserType.DROIDBOT
    }
}


def get_predefined_config(name: str) -> Dict[str, Any]:
    """
    Get a predefined configuration.

    Args:
        name: Name of the predefined configuration

    Returns:
        Configuration dictionary

    Raises:
        ValueError: If configuration name doesn't exist
    """
    if name not in DEFAULT_CONFIGS:
        raise ValueError(f"Predefined configuration '{name}' not found")

    config = DEFAULT_CONFIGS[name].copy()

    # Ensure parser_type is ParserType enum
    if "parser_type" in config and isinstance(config["parser_type"], str):
        try:
            config["parser_type"] = ParserType(config["parser_type"])
        except ValueError:
            logger.warning(f"Invalid parser_type in predefined config {name}: {config['parser_type']}")
            config["parser_type"] = ParserType.DROIDBOT

    return config
