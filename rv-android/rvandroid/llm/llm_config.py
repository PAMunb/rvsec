# rvandroid/llm/llm_config.py
from typing import Dict, Any, Optional

from rvandroid.parser.screen.parser_factory import ParserType


class LLMConfiguration:
    """
    Configuration class for language model settings.
    Centralizes all configuration parameters for LLM usage.
    """

    def __init__(
            self,
            model_type: str = "huggingface",
            model_name: str = "meta-llama/Meta-Llama-3.1-8B-Instruct",
            strategy_type: str = "single_action",
            parser_type: ParserType = ParserType.DROIDBOT,
            max_tokens: int = 800,
            temperature: float = 0.2,
            **kwargs
    ):
        """
        Initialize LLM configuration.

        Args:
            model_type: Type of model ('huggingface', 'ollama', etc.)
            model_name: Name of the model
            strategy_type: Type of prompt strategy
            parser_type: Type of parser to use
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            **kwargs: Additional model-specific parameters
        """
        self.model_type = model_type
        self.model_name = model_name
        self.strategy_type = strategy_type
        self.parser_type = parser_type
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.kwargs = kwargs

        # Add temperature to kwargs if not present
        if "temperature" not in self.kwargs:
            self.kwargs["temperature"] = temperature

    def get_model_type(self) -> str:
        """Get model type."""
        return self.model_type

    def get_model_name(self) -> str:
        """Get model name."""
        return self.model_name

    def get_strategy_type(self) -> str:
        """Get prompt strategy type."""
        return self.strategy_type

    def get_parser_type(self) -> ParserType:
        """Get parser type."""
        return self.parser_type

    def get_max_tokens(self) -> int:
        """Get maximum tokens to generate."""
        return self.max_tokens

    def get_model_kwargs(self) -> Dict[str, Any]:
        """Get additional model parameters."""
        return self.kwargs

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LLMConfiguration':
        """
        Create configuration from dictionary.

        Args:
            config_dict: Dictionary with configuration parameters

        Returns:
            LLMConfiguration instance
        """
        # Extract known parameters
        model_type = config_dict.pop("model_type", "huggingface")
        model_name = config_dict.pop("model_name", "meta-llama/Meta-Llama-3.1-8B-Instruct")
        strategy_type = config_dict.pop("strategy_type", "single_action")
        parser_type_str = config_dict.pop("parser_type", "droidbot")
        max_tokens = config_dict.pop("max_tokens", 800)
        temperature = config_dict.pop("temperature", 0.2)

        # Convert parser type string to enum
        parser_type = ParserType.DROIDBOT
        try:
            parser_type = ParserType[parser_type_str.upper()]
        except (KeyError, AttributeError):
            pass

        # Create configuration with remaining parameters as kwargs
        return cls(
            model_type=model_type,
            model_name=model_name,
            strategy_type=strategy_type,
            parser_type=parser_type,
            max_tokens=max_tokens,
            temperature=temperature,
            **config_dict
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary with configuration parameters
        """
        config_dict = {
            "model_type": self.model_type,
            "model_name": self.model_name,
            "strategy_type": self.strategy_type,
            "parser_type": self.parser_type.name.lower(),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        # Add other kwargs
        for key, value in self.kwargs.items():
            if key not in config_dict:
                config_dict[key] = value

        return config_dict