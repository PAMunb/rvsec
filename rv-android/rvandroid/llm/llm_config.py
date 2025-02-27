# rvandroid/config/llm_config.py
from typing import Dict, Any, Optional
import os
import logging
import json
from rvandroid.parser.parser_factory import ParserType

logger = logging.getLogger(__name__)

class LLMConfiguration:
    """
    Configuration class for managing LLM settings.
    """
    
    def __init__(self, config_file: Optional[str] = None, model_type: Optional[str] = None, model_name: Optional[str] = None, strategy_type: Optional[str] = None, parser_type: ParserType = ParserType.DROIDBOT, model_kwargs: Optional[Dict[str, Any]] = None):
        """
        Initialize the LLM configuration.
        
        Args:
            config_file: Path to a JSON configuration file (optional)
        """
        self.config = {
            "model_type": "huggingface",
            "model_name": "microsoft/Phi-3.5-mini-instruct",
            "strategy_type": "basic",
            "model_kwargs": {}
        }
        
        # Load from environment variables if set
        self._load_from_env()
        
        # Load from config file if provided
        if config_file:
            self._load_from_file(config_file)
            
        if model_type:
            self.config["model_type"] = model_type
        if model_name:
            self.config["model_name"] = model_name
        if strategy_type:
            self.config["strategy_type"] = strategy_type
        if model_kwargs:
            self.config["model_kwargs"] = model_kwargs

        # TODO
        self.parser_type = parser_type
        self.config["parser_type"] = parser_type
                    
        logger.info(f"Initialized LLM configuration: {self.config}")
    
    def _load_from_env(self):
        """
        Load configuration from environment variables.
        """
        if os.environ.get("RV_MODEL_TYPE"):
            self.config["model_type"] = os.environ.get("RV_MODEL_TYPE")
        
        if os.environ.get("RV_MODEL_NAME"):
            self.config["model_name"] = os.environ.get("RV_MODEL_NAME")
        
        if os.environ.get("RV_STRATEGY_TYPE"):
            self.config["strategy_type"] = os.environ.get("RV_STRATEGY_TYPE")
        
        # Handle model kwargs from environment
        if os.environ.get("RV_MODEL_KWARGS"):
            try:
                kwargs_json = os.environ.get("RV_MODEL_KWARGS", "{}")
                self.config["model_kwargs"] = json.loads(kwargs_json)
            except json.JSONDecodeError:
                logger.error("Failed to parse RV_MODEL_KWARGS as JSON")
    
    def _load_from_file(self, config_file: str):
        """
        Load configuration from a JSON file.
        
        Args:
            config_file: Path to JSON configuration file
        """
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
        except Exception as e:
            logger.error(f"Failed to load config from {config_file}: {e}")
    
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
        return self.config["parser_type"]
    
    def get_model_kwargs(self) -> Dict[str, Any]:
        """Get additional model arguments."""
        return self.config["model_kwargs"]
    
    def update(self, **kwargs):
        """
        Update configuration with new values.
        
        Args:
            **kwargs: Configuration key-value pairs
        """
        self.config.update(kwargs)
    
    def save_to_file(self, config_file: str):
        """
        Save current configuration to a file.
        
        Args:
            config_file: Path to save configuration
        """
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config to {config_file}: {e}")
    
    def __str__(self) -> str:
        return f"LLMConfiguration(model_type={self.get_model_type()}, model_name={self.get_model_name()}, strategy_type={self.get_strategy_type()})"


# Predefined configurations for common use cases
DEFAULT_CONFIGS = {
    "local": {
        "model_type": "huggingface",
        "model_name": "microsoft/Phi-3.5-mini-instruct",
        "strategy_type": "basic"
    },
    "ollama": {
        "model_type": "ollama",
        "model_name": "phi3.5:3.8b",
        "strategy_type": "basic"
    },
    "claude": {
        "model_type": "anthropic",
        "model_name": "claude-3-5-sonnet-20241022",
        "strategy_type": "claude"
    },
    "gpt": {
        "model_type": "openai",
        "model_name": "gpt-4-turbo-2024-04-09",
        "strategy_type": "gpt"
    },
    "gemini": {
        "model_type": "google",
        "model_name": "gemini-pro",
        "strategy_type": "gemini"
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
    return DEFAULT_CONFIGS[name]