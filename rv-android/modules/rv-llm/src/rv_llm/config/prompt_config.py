"""
Configuration management for prompt system in monitored operations testing.

### Architectural Overview:
This module provides type-safe configuration management for prompt generation,
implementing clean separation between LLM backend configuration and prompt-specific
settings. It follows the modern architecture pattern established in the system.

### Key Architectural Decisions:
- **Clean Separation**: Prompt configuration separate from LLM backend configuration
- **BaseValidatedModel**: Inherits from rv-android-core validation foundation
- **Type Safety**: Uses constants from appropriate modules to prevent string errors
- **Multi-Instance Support**: Enables different prompt configurations per tool instance
- **Factory Integration**: Designed to work with LLMComponentFactory and PromptFramework

### Role in the System:
- Central configuration point for prompt generation and strategy management
- Bridge between tool configuration and prompt framework instantiation
- Type-safe parameter passing for prompt strategies and templates
- Validation of prompt-specific parameters and dependencies
- Support for multiple tool instances with independent prompt configurations

### Design Patterns:
- **Data Transfer Object**: Pure data container for prompt configuration
- **Validation Pattern**: Comprehensive parameter validation using Pydantic
- **Factory Method**: Creation methods for different configuration sources
- **Immutable After Creation**: Configuration validated and frozen after creation
"""

from typing import Dict, Any, List, Tuple

from pydantic import Field, field_validator, model_validator

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.validation import BaseValidatedModel
from rv_llm.llm.constants import PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType


class PromptConfig(BaseValidatedModel):
    """
    Configuration class for prompt generation in monitored operations testing.
    
    ### Architectural Overview:
    This class provides type-safe configuration management for prompt generation,
    implementing clean separation from LLM backend concerns. It focuses purely
    on prompt-specific configuration without any business logic.
    
    ### Key Features:
    - Type-safe configuration with Pydantic validation
    - Support for multiple prompt strategies (standard, batch_action)
    - Screen parser and visitor type configuration
    - Template path management for modular prompt system
    - Context length management for different LLM backends
    - Comprehensive validation of prompt-specific parameters
    
    ### Configuration Categories:
    - Strategy: Prompt strategy type and generation parameters
    - Parser: Screen parser type for UI analysis
    - Visitor: Visitor type for screen element extraction
    - Template: Template paths and fragment management
    - Context: Context length and processing parameters
    
    ### Usage Examples:
    ```python
    # Basic configuration
    config = PromptConfig(
        strategy_type=PromptStrategyType.STANDARD,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED
    )
    
    # With custom template paths
    config = PromptConfig(
        strategy_type=PromptStrategyType.BATCH_ACTION,
        parser_type=ScreenParserType.UIAUTOMATOR,
        visitor_type=VisitorType.BASIC,
        template_paths={"system": "custom_system.xml"}
    )
    
    # Validation
    is_valid, errors = config.validate()
    ```
    """

    # Strategy Configuration
    strategy_type: str = Field(
        default=PromptStrategyType.SINGLE,
        description="Type of prompt strategy for action generation"
    )

    # Parser Configuration
    parser_type: str = Field(
        default=ScreenParserType.DROIDBOT,
        description="Type of screen parser for UI analysis"
    )

    # Visitor Configuration
    visitor_type: str = Field(
        default=VisitorType.DETAILED,
        description="Type of visitor for screen element extraction"
    )

    # Template Configuration
    template_paths: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom template paths for prompt generation"
    )

    # Context Management
    # TODO deprecate
    max_context_length: int = Field(
        default=8192,
        ge=512,
        le=32768,
        description="Maximum context length for prompt generation"
    )

    # Additional Parameters
    additional_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional prompt-specific parameters"
    )

    def model_post_init(self, __context) -> None:
        """
        Initialize logging and validation after model creation.
        
        ### Post-Initialization Strategy:
        - Set up logging for configuration validation
        - Prepare for validation operations
        - Initialize component dependencies
        """
        # Initialize logging after model creation
        logging_manager = LoggingManager.get_instance()
        # Store logger directly without making it a model field
        object.__setattr__(self, '_logger', logging_manager.get_logger(
            "rv_llm.config.prompt_config",
            {CONTEXT_COMPONENT: "PromptConfig"}
        ))

    @field_validator('strategy_type')
    @classmethod
    def validate_strategy_type(cls, v: str) -> str:
        """Validate strategy type against supported prompt strategies."""
        valid_strategies = PromptStrategyType.ALL
        if v not in valid_strategies:
            raise ValueError(f"strategy_type must be one of: {valid_strategies}")
        return v

    @field_validator('parser_type')
    @classmethod
    def validate_parser_type(cls, v: str) -> str:
        """Validate parser type against supported screen parsers."""
        valid_parsers = ScreenParserType.ALL
        if v not in valid_parsers:
            raise ValueError(f"parser_type must be one of: {valid_parsers}")
        return v

    @field_validator('visitor_type')
    @classmethod
    def validate_visitor_type(cls, v: str) -> str:
        """Validate visitor type against supported visitor types."""
        valid_visitors = VisitorType.ALL
        if v not in valid_visitors:
            raise ValueError(f"visitor_type must be one of: {valid_visitors}")
        return v

    @model_validator(mode='after')
    def validate_template_paths(self) -> 'PromptConfig':
        """Validate template paths are properly structured."""
        if self.template_paths:
            for name, path in self.template_paths.items():
                if not isinstance(name, str) or not isinstance(path, str):
                    raise ValueError("template_paths must contain string keys and values")
                if not name.strip() or not path.strip():
                    raise ValueError("template_paths cannot contain empty keys or values")
        return self

    @model_validator(mode='after')
    def validate_strategy_parser_compatibility(self) -> 'PromptConfig':
        """Validate strategy and parser type compatibility."""
        # All current strategies support all parsers
        # This method is prepared for future compatibility constraints
        return self

    @classmethod
    @ErrorHandler.handle_errors(
        component="PromptConfig",
        operation="from_tool_config"
    )
    def from_tool_config(cls, tool_config: Dict[str, Any]) -> 'PromptConfig':
        """
        Create PromptConfig from tool configuration dictionary.
        
        ### Tool Configuration Integration:
        This method creates prompt configuration from tool-specific settings,
        extracting prompt-related parameters and applying appropriate defaults.
        
        Args:
            tool_config: Dictionary containing tool configuration
            
        Returns:
            Configured PromptConfig instance
            
        Raises:
            ValueError: If tool_config contains invalid parameters
        """
        config_dict = {}

        # Extract prompt-specific parameters
        if "strategy_type" in tool_config:
            config_dict["strategy_type"] = tool_config["strategy_type"]

        if "parser_type" in tool_config:
            config_dict["parser_type"] = tool_config["parser_type"]

        if "visitor_type" in tool_config:
            config_dict["visitor_type"] = tool_config["visitor_type"]

        if "template_paths" in tool_config:
            config_dict["template_paths"] = tool_config["template_paths"]

        if "max_context_length" in tool_config:
            config_dict["max_context_length"] = tool_config["max_context_length"]

        # Extract additional prompt parameters
        prompt_params = {
            k: v for k, v in tool_config.items()
            if k.startswith("prompt_") or k in ["context_length", "template_"]
        }
        if prompt_params:
            config_dict["additional_params"] = prompt_params

        return cls(**config_dict)

    @classmethod
    @ErrorHandler.handle_errors(
        component="PromptConfig",
        operation="from_variants"
    )
    def from_variants(cls, variants: List[str], params: Dict[str, Any] = None) -> 'PromptConfig':
        """
        Create PromptConfig from variant specifications.
        
        ### Variant Parsing Strategy:
        This method creates prompt configuration from variant strings,
        using predefined templates for common configurations while allowing
        parameter overrides.
        
        ### Supported Variants:
        - **Strategy Variants**: standard, batch_action
        - **Parser Variants**: droidbot, uiautomator
        - **Visitor Variants**: basic, detailed, default
        
        Args:
            variants: List of variant strings
            params: Optional parameter overrides
            
        Returns:
            Configured PromptConfig instance
        """
        if params is None:
            params = {}

        config_dict = {}

        # Parse strategy variants
        if "standard" in variants:
            config_dict["strategy_type"] = PromptStrategyType.STANDARD
        elif "batch_action" in variants:
            config_dict["strategy_type"] = PromptStrategyType.BATCH_ACTION

        # Parse parser variants
        if "droidbot" in variants:
            config_dict["parser_type"] = ScreenParserType.DROIDBOT
        elif "uiautomator" in variants:
            config_dict["parser_type"] = ScreenParserType.UIAUTOMATOR

        # Parse visitor variants
        if "basic" in variants:
            config_dict["visitor_type"] = VisitorType.BASIC
        elif "detailed" in variants:
            config_dict["visitor_type"] = VisitorType.DETAILED
        elif "default" in variants:
            config_dict["visitor_type"] = VisitorType.DEFAULT

        # Apply parameter overrides
        config_dict.update(params)

        return cls(**config_dict)

    @ErrorHandler.handle_errors(
        component="PromptConfig",
        operation="validate"
    )
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate configuration parameters for consistency and correctness.
        
        ### Validation Strategy:
        This method performs comprehensive validation using Pydantic's built-in
        validation system, providing consistent error handling and type checking.
        
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        try:
            # Pydantic validation happens automatically during model creation
            # This method provides backward compatibility
            getattr(self, '_logger', None) and self._logger.debug("PromptConfig validation successful")
            return True, []
        except Exception as e:
            error_msg = str(e)
            getattr(self, '_logger', None) and self._logger.warning(f"PromptConfig validation error: {error_msg}")
            return False, [error_msg]

    def get_strategy_parameters(self) -> Dict[str, Any]:
        """
        Get strategy-specific parameters for strategy configuration.
        
        ### Parameter Extraction Strategy:
        Extracts parameters relevant for prompt strategy configuration,
        including context management and template settings.
        
        Returns:
            Dictionary with strategy configuration parameters
        """
        return {
            "strategy_type": self.strategy_type,
            "max_context_length": self.max_context_length,
            "template_paths": self.template_paths,
            **self.additional_params
        }

    def get_parser_parameters(self) -> Dict[str, Any]:
        """
        Get parser-specific parameters for parser configuration.
        
        ### Parameter Extraction Strategy:
        Extracts parameters relevant for screen parser configuration,
        including visitor type and processing settings.
        
        Returns:
            Dictionary with parser configuration parameters
        """
        return {
            "parser_type": self.parser_type,
            "visitor_type": self.visitor_type,
            **{k: v for k, v in self.additional_params.items() if k.startswith("parser_")}
        }

    def get_visitor_parameters(self) -> Dict[str, Any]:
        """
        Get visitor-specific parameters for visitor configuration.
        
        ### Parameter Extraction Strategy:
        Extracts parameters relevant for visitor configuration,
        including processing options and output formatting.
        
        Returns:
            Dictionary with visitor configuration parameters
        """
        return {
            "visitor_type": self.visitor_type,
            **{k: v for k, v in self.additional_params.items() if k.startswith("visitor_")}
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary representation.
        
        ### Serialization Strategy:
        Uses Pydantic's model_dump method to provide consistent serialization
        with proper handling of all field types and default values.
        
        Returns:
            Dictionary representation of the configuration
        """
        return self.model_dump(exclude_unset=False)

    def __str__(self) -> str:
        """
        String representation of the configuration.
        
        Returns:
            Concise string representation
        """
        return (f"PromptConfig(strategy_type={self.strategy_type}, "
                f"parser_type={self.parser_type}, visitor_type={self.visitor_type})")

    def __repr__(self) -> str:
        """
        Detailed string representation of the configuration.
        
        Returns:
            Detailed string representation for debugging
        """
        return (f"PromptConfig("
                f"strategy_type={repr(self.strategy_type)}, "
                f"parser_type={repr(self.parser_type)}, "
                f"visitor_type={repr(self.visitor_type)}, "
                f"max_context_length={repr(self.max_context_length)}, "
                f"template_paths_count={len(self.template_paths)})")
