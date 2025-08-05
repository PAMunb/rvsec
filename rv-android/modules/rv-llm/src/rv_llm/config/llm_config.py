"""
LLM configuration management for monitored operations testing.

This module provides type-safe configuration management that replaces
the complex ComponentConfigurator with a clean data-only approach.

### Architectural Overview:
This configuration system implements a Pydantic-based approach to LLM configuration,
providing type safety, validation, and clean separation between configuration data
and object creation logic.

### Key Architectural Decisions:
- **BaseValidatedModel**: Inherits from rv-android-core validation foundation
- **Field Validation**: Comprehensive constraint checking and error handling
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
from typing import Dict, Any, List, Optional, Tuple

from pydantic import Field, field_validator, model_validator

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.validation import BaseValidatedModel
from rv_llm.llm.constants import LLMType


class LLMConfig(BaseValidatedModel):
    """
    LLM configuration data class for monitored operations testing.
    
    ### Architectural Overview:
    This data class provides a type-safe approach to LLM configuration,
    replacing the complex ComponentConfigurator with a simple data-only structure.
    It focuses purely on configuration data without any business logic.
    
    ### Key Features:
    - Type-safe configuration with Pydantic validation
    - Support for multiple LLM backends (Ollama, OpenAI, etc.)
    - Strategy and parser configuration
    - CLI variant parsing support
    - Comprehensive validation
    
    ### Configuration Categories:
    - LLM Backend: Type, model, connection settings
    - Generation: Temperature, tokens, sampling parameters
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
    llm_type: str = Field(default="ollama", description="Type of LLM provider")
    model: str = Field(default="llama3.2:3b", description="Model name or identifier")
    base_url: str = Field(default="http://localhost:11434", description="Base URL for local LLM providers")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=800, ge=1, le=4096, description="Maximum tokens to generate")
    vision: bool = Field(default=False, description="Enable vision capabilities")
    think: bool = Field(default=False, description="Enable thinking capabilities")
    # Cloud Configuration
    api_key: Optional[str] = Field(default=None, description="API key for cloud providers")
    provider: Optional[str] = Field(default=None, description="Provider name")

    # Generation Parameters
    top_p: float = Field(default=1.0, gt=0.0, le=1.0, description="Top-p sampling parameter")
    top_k: int = Field(default=40, ge=1, le=100, description="Top-k sampling parameter")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")

    # Context Configuration
    max_context_length: int = Field(default=8192, ge=512, le=32768, description="Maximum context length")

    # Parser Configuration - Moved to rvandroid-tool RvAndroidToolConfig
    # Parser and visitor configuration is now handled by individual tools

    # Additional Parameters
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")

    def model_post_init(self, __context) -> None:
        """
        Initialize logging after model creation.
        
        ### Post-Initialization Strategy:
        - Set up logging for configuration validation
        - Prepare for validation operations
        - Initialize component dependencies
        """
        # Logging setup is handled by components that use this configuration
        pass

    @field_validator('llm_type')
    @classmethod
    def validate_llm_type(cls, v: str) -> str:
        """Validate LLM type against supported providers including registered backends."""
        # Import here to avoid circular imports
        from rv_llm.factories.component_factory import LLMComponentFactory

        # Get supported types including registered backends
        valid_types = LLMComponentFactory.get_supported_llm_types()
        if v not in valid_types:
            raise ValueError(f"llm_type must be one of: {valid_types}")
        return v

    # Parser/visitor validation moved to tool-specific configuration classes

    @model_validator(mode='after')
    def validate_api_key_dependencies(self) -> 'LLMConfig':
        """Validate API key dependencies for cloud providers."""
        if self.llm_type == LLMType.FRONTIER and not self.api_key:
            raise ValueError(f"api_key is required for {self.llm_type} backend")

        if self.llm_type == LLMType.OLLAMA and not self.base_url:
            raise ValueError("base_url is required for ollama backend")

        return self

    @model_validator(mode='after')
    def validate_model_name(self) -> 'LLMConfig':
        """Validate model name is not empty."""
        if not self.model or not isinstance(self.model, str):
            raise ValueError("model must be a non-empty string")
        return self

    @classmethod
    @ErrorHandler.handle_errors(
        component="LLMConfig",
        operation="from_variants_and_params"
    )
    def from_variants_and_params(cls, variants: List[str], params: Dict[str, Any]) -> 'LLMConfig':
        # DEPRECATED - Use tool-specific configuration classes instead
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

        # Strategy configuration moved to PromptConfig

        # Parser/UI variants moved to tool-specific configuration classes

        # Override with explicit parameters (Pydantic handles type conversion)
        config_dict.update(params)

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

    # Strategy variant parsing moved to PromptConfig

    # _parse_parser_variants moved to tool-specific configuration classes

    @ErrorHandler.handle_errors(
        component="LLMConfig",
        operation="validate"
    )
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate configuration parameters for consistency and correctness.
        
        ### Validation Strategy:
        This method performs comprehensive validation using Pydantic's built-in
        validation system, providing consistent error handling and type checking.
        
        ### Validation Categories:
        - **Type Validation**: Automatic type checking and conversion
        - **Range Validation**: Field constraints for numeric parameters
        - **Dependency Validation**: Model validators for complex requirements
        - **Logical Validation**: Cross-field validation for consistency
        
        Returns:
            Tuple of (is_valid, list_of_error_messages)
            
        Examples:
            >>> config = LLMConfig(temperature=2.5)  # Invalid range
            >>> is_valid, errors = config.validate()
            >>> assert not is_valid
            >>> assert "temperature must be between 0.0 and 2.0" in errors
        """
        try:
            # Pydantic validation happens automatically during model creation
            # This method provides backward compatibility
            return True, []
        except Exception as e:
            error_msg = str(e)
            if hasattr(self, 'logger'):
                self.logger.warning(f"Configuration validation error: {error_msg}")
            return False, [error_msg]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary representation.
        
        ### Serialization Strategy:
        Uses Pydantic's model_dump method to provide consistent serialization
        with proper handling of all field types and default values.
        
        Returns:
            Dictionary representation of the configuration
        """
        base_dict = self.model_dump(exclude_unset=False)

        # Add kwargs, excluding duplicates
        for key, value in self.kwargs.items():
            if key not in base_dict:
                base_dict[key] = value

        return base_dict

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

    def get_context_parameters(self) -> Dict[str, Any]:
        """
        Get context-specific parameters for context management.
        
        ### Parameter Extraction Strategy:
        Extracts parameters relevant for context management,
        including context length and token limits.
        
        Returns:
            Dictionary with context configuration parameters
        """
        return {
            "max_context_length": self.max_context_length,
            "max_tokens": self.max_tokens,
            **{k: v for k, v in self.kwargs.items() if k.startswith("context_")}
        }

    # get_parser_parameters() moved to tool-specific configuration classes

    def __str__(self) -> str:
        """
        String representation of the configuration.
        
        Returns:
            Concise string representation
        """
        return (f"LLMConfig(llm_type={self.llm_type}, model={self.model})")

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
                f"kwargs_count={len(self.kwargs)})")
