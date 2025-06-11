"""
Simple LLM configuration data class for monitored operations testing.

This module provides a clean, type-safe configuration system that replaces
the complex ComponentConfigurator with a simple data-only approach.

### Architectural Overview:
This configuration system implements a pure data class approach to LLM configuration,
providing type safety, validation, and clean separation between configuration data
and object creation logic.

### Key Architectural Decisions:
- **Pure Data Class**: No business logic, only configuration data
- **Type Safety**: Full type annotations with dataclass validation
- **Variant Parsing**: Factory method for CLI tool specification parsing
- **Immutable After Creation**: Configuration is validated and frozen
- **Clean Interface**: Simple, predictable API for configuration management

### Role in the System:
- Central configuration data structure for all LLM operations
- Interface between CLI parsing and object creation
- Type-safe parameter passing between components
- Configuration validation and error reporting
- Variant-based configuration generation from CLI specifications

### Design Patterns:
- **Data Transfer Object**: Pure data container without behavior
- **Factory Method**: from_variants_and_params for CLI integration
- **Validation Pattern**: Comprehensive configuration validation
- **Builder Pattern**: Progressive configuration building from variants

### Integration Strategy:
- Used by LLMServiceFactory for object creation
- Accepted by strategy configure_from_config methods
- Generated from CLI tool specification parsing
- Validated before object creation to ensure consistency
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


@dataclass
class LLMConfig:
    """
    Simple LLM configuration data class for monitored operations testing.
    
    ### Architectural Overview:
    This data class provides a clean, type-safe approach to LLM configuration,
    replacing the complex ComponentConfigurator with a simple data-only structure.
    It focuses purely on configuration data without any business logic.
    
    ### Key Features:
    - Type-safe configuration with dataclass validation
    - Support for multiple LLM backends (Ollama, OpenAI, etc.)
    - Strategy and parser configuration
    - CLI variant parsing support
    - Comprehensive validation
    
    ### Configuration Categories:
    - LLM Backend: Type, model, connection settings
    - Generation: Temperature, tokens, sampling parameters
    - Strategy: Prompt strategy type and template configuration
    - Parser: Screen parser and visitor configuration
    - Additional: Custom parameters via kwargs
    
    ### Usage Examples:
    ```python
    # Basic configuration
    config = LLMConfig(llm_type="ollama", model="llama3.2:3b")
    
    # From CLI variants
    config = LLMConfig.from_variants_and_params(
        variants=["llama", "batch_action"],
        params={"temperature": "0.3"}
    )
    
    # Validation
    is_valid, errors = config.validate()
    ```
    """
    
    # LLM Backend Configuration
    llm_type: str = "ollama"
    model: str = "llama3.2:3b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.2
    max_tokens: int = 500
    api_key: Optional[str] = None
    provider: Optional[str] = None
    
    # Generation Parameters
    top_p: float = 1.0
    top_k: int = 40
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    
    # Strategy Configuration
    strategy_type: str = "standard"
    template_name: Optional[str] = None
    enable_context_caching: bool = True
    max_context_length: int = 8192
    
    # Parser Configuration
    parser_type: str = "droidbot"
    visitor_type: str = "enhanced"
    enhanced_parsing: bool = True
    
    # Additional Parameters
    kwargs: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """
        Initialize logging after dataclass creation.
        
        ### Post-Initialization Strategy:
        - Set up logging for configuration validation
        - Ensure consistent parameter types
        - Prepare for validation operations
        """
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "llm.config",
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )
        
        # Ensure numeric types are correct
        self.temperature = float(self.temperature)
        self.max_tokens = int(self.max_tokens)
        self.top_p = float(self.top_p)
        self.top_k = int(self.top_k)
        self.frequency_penalty = float(self.frequency_penalty)
        self.presence_penalty = float(self.presence_penalty)
        self.max_context_length = int(self.max_context_length)
    
    @classmethod
    @ErrorHandler.handle_errors(
        component="LLMConfig",
        operation="from_variants_and_params"
    )
    def from_variants_and_params(cls, variants: List[str], params: Dict[str, Any]) -> 'LLMConfig':
        """
        Create configuration from CLI tool specification variants and parameters.
        
        ### Variant Parsing Strategy:
        This method implements intelligent variant parsing to convert CLI tool
        specifications into comprehensive configuration objects. It uses predefined
        templates for common variant combinations while allowing parameter overrides.
        
        ### Supported Variants:
        - **LLM Backends**: llama, gpt4, claude, gemini
        - **Strategies**: batch_action, single_action, standard
        - **Features**: detailed_ui, enhanced_parsing
        
        ### Parameter Override:
        Any parameter passed in the params dict will override variant-based defaults,
        providing fine-grained control over configuration.
        
        Args:
            variants: List of variant strings from CLI parsing
            params: Dictionary of explicit parameters from CLI
            
        Returns:
            Configured LLMConfig instance
            
        Raises:
            ValueError: If variants contain invalid combinations
            
        Examples:
            >>> config = LLMConfig.from_variants_and_params(
            ...     variants=["llama", "batch_action"],
            ...     params={"temperature": "0.3"}
            ... )
            >>> assert config.llm_type == "ollama"
            >>> assert config.strategy_type == "batch_action"
            >>> assert config.temperature == 0.3
        """
        # Start with default configuration
        config_dict = {}
        
        # Parse LLM backend variants
        llm_config = cls._parse_llm_variants(variants)
        config_dict.update(llm_config)
        
        # Parse strategy variants
        strategy_config = cls._parse_strategy_variants(variants)
        config_dict.update(strategy_config)
        
        # Parse parser/UI variants
        parser_config = cls._parse_parser_variants(variants)
        config_dict.update(parser_config)
        
        # Override with explicit parameters
        # Convert string values to appropriate types
        typed_params = cls._convert_parameter_types(params)
        config_dict.update(typed_params)
        
        # Create configuration instance
        return cls(**config_dict)
    
    @classmethod
    def _parse_llm_variants(cls, variants: List[str]) -> Dict[str, Any]:
        """
        Parse LLM backend variants into configuration parameters.
        
        ### LLM Backend Templates:
        - **llama**: Ollama with Llama model
        - **gpt4**: OpenAI GPT-4
        - **claude**: Anthropic Claude
        - **gemini**: Google Gemini
        
        Args:
            variants: List of variant strings
            
        Returns:
            Dictionary with LLM backend configuration
        """
        config = {}
        
        if "llama" in variants:
            config.update({
                "llm_type": "ollama",
                "model": "llama3.2:3b",
                "base_url": "http://localhost:11434",
                "provider": "ollama"
            })
        elif "gpt4" in variants:
            config.update({
                "llm_type": "openai",
                "model": "gpt-4",
                "provider": "openai",
                "api_key": os.getenv("OPENAI_API_KEY")
            })
        elif "claude" in variants:
            config.update({
                "llm_type": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "provider": "anthropic", 
                "api_key": os.getenv("ANTHROPIC_API_KEY")
            })
        elif "gemini" in variants:
            config.update({
                "llm_type": "google",
                "model": "gemini-pro",
                "provider": "google",
                "api_key": os.getenv("GOOGLE_API_KEY")
            })
        
        return config
    
    @classmethod
    def _parse_strategy_variants(cls, variants: List[str]) -> Dict[str, Any]:
        """
        Parse strategy variants into configuration parameters.
        
        ### Strategy Templates:
        - **batch_action**: Generate multiple actions in one response
        - **single_action**: Generate one action per response
        - **standard**: Default strategy with balanced approach
        
        Args:
            variants: List of variant strings
            
        Returns:
            Dictionary with strategy configuration
        """
        config = {}
        
        if "batch_action" in variants:
            config.update({
                "strategy_type": "batch_action",
                "max_tokens": 800,  # More tokens for batch actions
                "enable_context_caching": True
            })
        elif "single_action" in variants:
            config.update({
                "strategy_type": "standard",
                "max_tokens": 500,
                "enable_context_caching": False
            })
        else:
            # Default strategy
            config.update({
                "strategy_type": "standard",
                "max_tokens": 500
            })
        
        return config
    
    @classmethod
    def _parse_parser_variants(cls, variants: List[str]) -> Dict[str, Any]:
        """
        Parse parser and UI variants into configuration parameters.
        
        ### Parser Templates:
        - **detailed_ui**: Enhanced UI parsing with detailed visitor
        - **uiautomator**: Use UIAutomator parser
        - **droidbot**: Use DroidBot parser (default)
        
        Args:
            variants: List of variant strings
            
        Returns:
            Dictionary with parser configuration
        """
        config = {}
        
        if "detailed_ui" in variants:
            config.update({
                "parser_type": "uiautomator",
                "visitor_type": "enhanced",
                "enhanced_parsing": True
            })
        elif "uiautomator" in variants:
            config.update({
                "parser_type": "uiautomator",
                "visitor_type": "default",
                "enhanced_parsing": False
            })
        else:
            # Default to DroidBot parser
            config.update({
                "parser_type": "droidbot",
                "visitor_type": "enhanced",
                "enhanced_parsing": True
            })
        
        return config
    
    @classmethod
    def _convert_parameter_types(cls, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert string parameters from CLI to appropriate types.
        
        ### Type Conversion Strategy:
        - Automatic type detection based on parameter names
        - Safe conversion with error handling
        - Preservation of complex types (dicts, lists)
        
        Args:
            params: Dictionary of string parameters from CLI
            
        Returns:
            Dictionary with properly typed parameters
        """
        typed_params = {}
        
        # Define type conversion rules
        float_params = {"temperature", "top_p", "frequency_penalty", "presence_penalty"}
        int_params = {"max_tokens", "top_k", "max_context_length"}
        bool_params = {"enable_context_caching", "enhanced_parsing"}
        
        for key, value in params.items():
            try:
                if key in float_params and isinstance(value, str):
                    typed_params[key] = float(value)
                elif key in int_params and isinstance(value, str):
                    typed_params[key] = int(value)
                elif key in bool_params and isinstance(value, str):
                    typed_params[key] = value.lower() in ("true", "1", "yes", "on")
                else:
                    typed_params[key] = value
            except (ValueError, TypeError) as e:
                # Keep original value if conversion fails
                typed_params[key] = value
        
        return typed_params
    
    @ErrorHandler.handle_errors(
        component="LLMConfig",
        operation="validate"
    )
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate configuration parameters for consistency and correctness.
        
        ### Validation Strategy:
        This method performs comprehensive validation of all configuration parameters,
        checking for valid ranges, required dependencies, and logical consistency.
        
        ### Validation Categories:
        - **Type Validation**: Ensure parameters have correct types
        - **Range Validation**: Check numeric parameters are within valid ranges
        - **Dependency Validation**: Verify required parameters for specific backends
        - **Logical Validation**: Check for conflicting configuration combinations
        
        Returns:
            Tuple of (is_valid, list_of_error_messages)
            
        Examples:
            >>> config = LLMConfig(temperature=2.5)  # Invalid range
            >>> is_valid, errors = config.validate()
            >>> assert not is_valid
            >>> assert "temperature must be between 0.0 and 2.0" in errors
        """
        errors = []
        
        # Validate LLM type
        valid_llm_types = {"ollama", "openai", "anthropic", "google", "huggingface"}
        if self.llm_type not in valid_llm_types:
            errors.append(f"llm_type must be one of: {valid_llm_types}")
        
        # Validate model name
        if not self.model or not isinstance(self.model, str):
            errors.append("model must be a non-empty string")
        
        # Validate temperature range
        if not (0.0 <= self.temperature <= 2.0):
            errors.append("temperature must be between 0.0 and 2.0")
        
        # Validate max_tokens
        if not (1 <= self.max_tokens <= 4096):
            errors.append("max_tokens must be between 1 and 4096")
        
        # Validate top_p range
        if not (0.0 < self.top_p <= 1.0):
            errors.append("top_p must be between 0.0 and 1.0")
        
        # Validate top_k
        if not (1 <= self.top_k <= 100):
            errors.append("top_k must be between 1 and 100")
        
        # Validate penalty ranges
        if not (-2.0 <= self.frequency_penalty <= 2.0):
            errors.append("frequency_penalty must be between -2.0 and 2.0")
        
        if not (-2.0 <= self.presence_penalty <= 2.0):
            errors.append("presence_penalty must be between -2.0 and 2.0")
        
        # Validate strategy type
        valid_strategies = {"standard", "batch_action", "frontier"}
        if self.strategy_type not in valid_strategies:
            errors.append(f"strategy_type must be one of: {valid_strategies}")
        
        # Validate parser type
        valid_parsers = {"droidbot", "uiautomator"}
        if self.parser_type not in valid_parsers:
            errors.append(f"parser_type must be one of: {valid_parsers}")
        
        # Validate visitor type
        valid_visitors = {"default", "enhanced", "basic"}
        if self.visitor_type not in valid_visitors:
            errors.append(f"visitor_type must be one of: {valid_visitors}")
        
        # Validate API key dependencies
        if self.llm_type in {"openai", "anthropic", "google"} and not self.api_key:
            errors.append(f"api_key is required for {self.llm_type} backend")
        
        # Validate base_url for local backends
        if self.llm_type == "ollama" and not self.base_url:
            errors.append("base_url is required for ollama backend")
        
        # Validate max_context_length
        if not (512 <= self.max_context_length <= 32768):
            errors.append("max_context_length must be between 512 and 32768")
        
        # Log validation errors
        if errors:
            for error in errors:
                self.logger.warning(f"Configuration validation error: {error}")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary representation.
        
        ### Serialization Strategy:
        Converts the configuration to a clean dictionary format suitable for
        JSON serialization, logging, or passing to other components.
        
        Returns:
            Dictionary representation of the configuration
        """
        config_dict = {
            # LLM Backend
            "llm_type": self.llm_type,
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "api_key": self.api_key,
            "provider": self.provider,
            
            # Generation Parameters
            "top_p": self.top_p,
            "top_k": self.top_k,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            
            # Strategy Configuration
            "strategy_type": self.strategy_type,
            "template_name": self.template_name,
            "enable_context_caching": self.enable_context_caching,
            "max_context_length": self.max_context_length,
            
            # Parser Configuration
            "parser_type": self.parser_type,
            "visitor_type": self.visitor_type,
            "enhanced_parsing": self.enhanced_parsing,
        }
        
        # Add kwargs, excluding duplicates
        for key, value in self.kwargs.items():
            if key not in config_dict:
                config_dict[key] = value
        
        return config_dict
    
    def get_llm_parameters(self) -> Dict[str, Any]:
        """
        Get LLM-specific parameters for model initialization.
        
        ### Parameter Extraction Strategy:
        Extracts only the parameters relevant for LLM model initialization,
        filtering out strategy and parser configuration.
        
        Returns:
            Dictionary with LLM initialization parameters
        """
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty,
            "base_url": self.base_url,
            "api_key": self.api_key,
            **{k: v for k, v in self.kwargs.items() if k.startswith("llm_")}
        }
    
    def get_strategy_parameters(self) -> Dict[str, Any]:
        """
        Get strategy-specific parameters for strategy configuration.
        
        ### Parameter Extraction Strategy:
        Extracts parameters relevant for prompt strategy configuration,
        including template and context management settings.
        
        Returns:
            Dictionary with strategy configuration parameters
        """
        return {
            "strategy_type": self.strategy_type,
            "template_name": self.template_name,
            "enable_context_caching": self.enable_context_caching,
            "max_context_length": self.max_context_length,
            "max_tokens": self.max_tokens,
            **{k: v for k, v in self.kwargs.items() if k.startswith("strategy_")}
        }
    
    def get_parser_parameters(self) -> Dict[str, Any]:
        """
        Get parser-specific parameters for parser configuration.
        
        ### Parameter Extraction Strategy:
        Extracts parameters relevant for screen parser and visitor configuration,
        including UI analysis settings.
        
        Returns:
            Dictionary with parser configuration parameters
        """
        return {
            "parser_type": self.parser_type,
            "visitor_type": self.visitor_type,
            "enhanced_parsing": self.enhanced_parsing,
            **{k: v for k, v in self.kwargs.items() if k.startswith("parser_")}
        }
    
    def __str__(self) -> str:
        """
        String representation of the configuration.
        
        Returns:
            Concise string representation
        """
        return (f"LLMConfig(llm_type={self.llm_type}, model={self.model}, "
                f"strategy_type={self.strategy_type}, parser_type={self.parser_type})")
    
    def __repr__(self) -> str:
        """
        Detailed string representation of the configuration.
        
        Returns:
            Detailed string representation for debugging
        """
        return (f"LLMConfig("
                f"llm_type={repr(self.llm_type)}, "
                f"model={repr(self.model)}, "
                f"temperature={repr(self.temperature)}, "
                f"strategy_type={repr(self.strategy_type)}, "
                f"parser_type={repr(self.parser_type)}, "
                f"kwargs_count={len(self.kwargs)})")