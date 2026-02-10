# rvandroid/llm/llm_config.py
import json
import logging
from typing import Dict, Any, List, Tuple

from rvandroid.llm.constants import LLMType, PromptStrategyType
from rvandroid.parser.screen.parser_factory import ParserType
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class LLMConfiguration:
    """
    Configuration class for language model settings.
    Centralizes all configuration parameters for LLM usage.
    
    ### Architectural Decisions:
    - Implements a comprehensive configuration system for LLM management
    - Provides validation and documentation for configuration parameters
    - Supports serialization and deserialization for persistence
    - Enables runtime configuration updates and introspection
    - Provides a schema-based approach to configuration management
    
    ### Role in the System:
    - Acts as the primary configuration entity for language model interactions
    - Centralizes all parameters needed for LLM operation
    - Enables consistent configuration across different components
    - Provides validation to ensure configuration integrity
    - Supports configuration introspection and documentation
    """

    # Configuration schema with default values, types, and documentation
    _SCHEMA = {
        "model_type": {
            "type": str,
            "default": "huggingface",
            "description": "Type of model ('huggingface', 'ollama', 'dspy', 'langchain', 'frontier', etc.)",
            "required": True
        },
        "model_name": {
            "type": str,
            "default": "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "description": "Name or identifier of the model",
            "required": True
        },
        "strategy_type": {
            "type": str,
            "default": "composable_single_action",
            "description": "Type of prompt strategy to use",
            "required": True
        },
        "parser_type": {
            "type": ParserType,
            "default": ParserType.DROIDBOT,
            "description": "Type of screen parser to use",
            "required": True
        },
        "max_tokens": {
            "type": int,
            "default": 800,
            "description": "Maximum number of tokens to generate",
            "required": False,
            "validator": lambda x: x > 0
        },
        "temperature": {
            "type": float,
            "default": 0.2,
            "description": "Temperature for generation (randomness)",
            "required": False,
            "validator": lambda x: 0.0 <= x <= 2.0
        },
        "top_p": {
            "type": float,
            "default": 1.0,
            "description": "Top-p sampling parameter",
            "required": False,
            "validator": lambda x: 0.0 < x <= 1.0
        },
        "top_k": {
            "type": int,
            "default": 40,
            "description": "Top-k sampling parameter",
            "required": False,
            "validator": lambda x: x > 0
        },
        "frequency_penalty": {
            "type": float,
            "default": 0.0,
            "description": "Penalty for token frequency",
            "required": False,
            "validator": lambda x: -2.0 <= x <= 2.0
        },
        "presence_penalty": {
            "type": float,
            "default": 0.0,
            "description": "Penalty for token presence",
            "required": False,
            "validator": lambda x: -2.0 <= x <= 2.0
        }
    }

    def __init__(
            self,
            model_type: str = LLMType.OLLAMA,
            model_name: str = "llama3.2:3b", # TODO
            strategy_type: str = PromptStrategyType.BATCH_ACTION,
            parser_type: ParserType = ParserType.DROIDBOT,
            max_tokens: int = 200,
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
        # Initialize logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "llm.config",
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )

        self.model_type = model_type
        self.model_name = model_name
        self.strategy_type = strategy_type
        self.parser_type = parser_type
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = kwargs.get("top_p", 1.0)
        self.top_k = kwargs.get("top_k", 40)
        self.frequency_penalty = kwargs.get("frequency_penalty", 0.0)
        self.presence_penalty = kwargs.get("presence_penalty", 0.0)
        self.kwargs = kwargs

        # Move standard parameters to kwargs for consistency and compatibility
        self.kwargs["max_tokens"] = max_tokens
        self.kwargs["temperature"] = temperature

        # Set default parameters if not provided
        self._set_default_parameters()

        # Validate configuration
        self.validate()

    def _set_default_parameters(self) -> None:
        """Set default parameters for common LLM configurations."""
        # Only set if not already provided
        if "top_p" not in self.kwargs:
            self.kwargs["top_p"] = self._SCHEMA["top_p"]["default"]
        if "top_k" not in self.kwargs:
            self.kwargs["top_k"] = self._SCHEMA["top_k"]["default"]
        if "frequency_penalty" not in self.kwargs:
            self.kwargs["frequency_penalty"] = self._SCHEMA["frequency_penalty"]["default"]
        if "presence_penalty" not in self.kwargs:
            self.kwargs["presence_penalty"] = self._SCHEMA["presence_penalty"]["default"]

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the configuration against schema.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check required parameters
        for param_name, schema in self._SCHEMA.items():
            if schema.get("required", False):
                if not hasattr(self, param_name) or getattr(self, param_name) is None:
                    errors.append(f"Missing required parameter: {param_name}")

        # Validate parameter types and constraints
        for param_name, schema in self._SCHEMA.items():
            if hasattr(self, param_name):
                value = getattr(self, param_name)
                # Type validation
                if not isinstance(value, schema["type"]) and not (value is None and not schema.get("required", False)):
                    errors.append(
                        f"Parameter {param_name} has invalid type. Expected {schema['type'].__name__}, got {type(value).__name__}")

                # Custom validation
                if "validator" in schema and value is not None:
                    try:
                        if not schema["validator"](value):
                            errors.append(f"Parameter {param_name} failed validation constraint: {value}")
                    except Exception as e:
                        errors.append(f"Error validating {param_name}: {str(e)}")

        # Validate kwargs parameters that are in schema
        for param_name, value in self.kwargs.items():
            if param_name in self._SCHEMA:
                schema = self._SCHEMA[param_name]
                # Type validation
                if not isinstance(value, schema["type"]) and not (value is None and not schema.get("required", False)):
                    errors.append(
                        f"Parameter kwargs.{param_name} has invalid type. Expected {schema['type'].__name__}, got {type(value).__name__}")

                # Custom validation
                if "validator" in schema and value is not None:
                    try:
                        if not schema["validator"](value):
                            errors.append(f"Parameter kwargs.{param_name} failed validation constraint: {value}")
                    except Exception as e:
                        errors.append(f"Error validating kwargs.{param_name}: {str(e)}")

        if errors:
            for error in errors:
                self.logger.warning(f"Configuration validation error: {error}")

        return len(errors) == 0, errors

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

    def set_parameter(self, name: str, value: Any) -> None:
        """
        Set a configuration parameter.
        
        Args:
            name: Parameter name
            value: Parameter value
            
        Raises:
            ValueError: If parameter validation fails
        """
        # Check if parameter is in schema
        if name in self._SCHEMA:
            schema = self._SCHEMA[name]

            # Type validation
            if not isinstance(value, schema["type"]) and value is not None:
                raise ValueError(
                    f"Parameter {name} has invalid type. Expected {schema['type'].__name__}, got {type(value).__name__}")

            # Custom validation
            if "validator" in schema and value is not None:
                if not schema["validator"](value):
                    raise ValueError(f"Parameter {name} failed validation constraint: {value}")

            # Set the parameter
            if hasattr(self, name):
                setattr(self, name, value)

            # Also update in kwargs for consistency
            self.kwargs[name] = value
        else:
            # For non-schema parameters, just add to kwargs
            self.kwargs[name] = value

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'LLMConfiguration':
        """
        Create configuration from dictionary.

        Args:
            config_dict: Dictionary with configuration parameters

        Returns:
            LLMConfiguration instance
        """
        # Make a copy to avoid modifying the original
        config = config_dict.copy()

        # Extract known parameters
        model_type = config.pop("model_type", cls._SCHEMA["model_type"]["default"])
        model_name = config.pop("model_name", cls._SCHEMA["model_name"]["default"])
        strategy_type = config.pop("strategy_type", cls._SCHEMA["strategy_type"]["default"])
        max_tokens = config.pop("max_tokens", cls._SCHEMA["max_tokens"]["default"])
        temperature = config.pop("temperature", cls._SCHEMA["temperature"]["default"])

        # Handle parser type conversion
        parser_type_str = config.pop("parser_type", None)
        if parser_type_str is None:
            parser_type = cls._SCHEMA["parser_type"]["default"]
        else:
            try:
                parser_type = ParserType[parser_type_str.upper()]
            except (KeyError, AttributeError):
                parser_type = cls._SCHEMA["parser_type"]["default"]
                logging.getLogger(__name__).warning(
                    f"Invalid parser type: {parser_type_str}, using default: {parser_type.name}")

        # Create configuration with remaining parameters as kwargs
        return cls(
            model_type=model_type,
            model_name=model_name,
            strategy_type=strategy_type,
            parser_type=parser_type,
            max_tokens=max_tokens,
            temperature=temperature,
            **config
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

        # Add other kwargs, excluding those already in config_dict
        for key, value in self.kwargs.items():
            if key not in config_dict:
                config_dict[key] = value

        return config_dict

    def to_json(self, indent: int = 2) -> str:
        """
        Convert configuration to JSON string.
        
        Args:
            indent: Indentation level for JSON formatting
            
        Returns:
            JSON string representation of the configuration
        """
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> 'LLMConfiguration':
        """
        Create configuration from JSON string.
        
        Args:
            json_str: JSON string representation of configuration
            
        Returns:
            LLMConfiguration instance
        """
        config_dict = json.loads(json_str)
        return cls.from_dict(config_dict)

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get the configuration schema.
        
        Returns:
            Dictionary with parameter schemas
        """
        # Replace type objects with their names for serialization
        schema = {}
        for name, param_schema in cls._SCHEMA.items():
            schema[name] = param_schema.copy()
            schema[name]["type"] = param_schema["type"].__name__
            # Remove validator function
            if "validator" in schema[name]:
                del schema[name]["validator"]

        return schema

    def __eq__(self, other: object) -> bool:
        """
        Check if two configurations are equal.
        
        Args:
            other: Object to compare with
            
        Returns:
            True if configurations are equal, False otherwise
        """
        if not isinstance(other, LLMConfiguration):
            return False

        # Compare all attributes
        return (
                self.model_type == other.model_type and
                self.model_name == other.model_name and
                self.strategy_type == other.strategy_type and
                self.parser_type == other.parser_type and
                self.max_tokens == other.max_tokens and
                self.temperature == other.temperature and
                self.kwargs == other.kwargs
        )

    def __str__(self) -> str:
        """
        String representation of the configuration.
        
        Returns:
            String representation
        """
        return (f"LLMConfiguration(model_type={self.model_type}, "
                f"model_name={self.model_name}, "
                f"strategy_type={self.strategy_type}, "
                f"parser_type={self.parser_type.name})")

    def __repr__(self) -> str:
        """
        Detailed string representation of the configuration.
        
        Returns:
            Detailed string representation
        """
        return (f"LLMConfiguration("
                f"model_type={repr(self.model_type)}, "
                f"model_name={repr(self.model_name)}, "
                f"strategy_type={repr(self.strategy_type)}, "
                f"parser_type={repr(self.parser_type)}, "
                f"max_tokens={repr(self.max_tokens)}, "
                f"temperature={repr(self.temperature)}, "
                f"kwargs={repr(self.kwargs)})")

    def get_compatible_models(self) -> List[str]:
        """
        Get a list of models compatible with the current configuration.
        
        Returns:
            List of compatible model names
        """
        # Import here to avoid circular imports
        from rvandroid.config.component_configurator import ComponentConfigurator

        try:
            # Get the registry for this model type
            registry = ComponentConfigurator._registries['llm']
            if registry.has(self.model_type):
                model_class = registry.get(self.model_type)
                if model_class and hasattr(model_class, 'models'):
                    return model_class.models()
            return []
        except Exception:
            return []
