"""
RVAndroid Tool Configuration with Unified Architecture

This module provides configuration management for the RVAndroid tool using
composition instead of field duplication, eliminating architectural redundancy
and providing comprehensive prompt strategy support.

### Architectural Overview:
This configuration class implements clean composition architecture by combining
LLM backend configuration with prompt generation settings through composition
rather than duplication, ensuring single source of truth for all configuration.

### Key Features:
- Unified Configuration: Single class containing all tool configuration
- Composition Pattern: Uses PromptConfig instead of duplicating fields
- Strategy Support: Full support for prompt strategies (BATCH_ACTION, STANDARD)
- Factory Methods: Intelligent configuration creation from experiment config
- Validation: Comprehensive parameter validation using constants

### Design Principles:
- Single Responsibility: Each configuration class handles its specific domain
- Composition over Inheritance: Uses PromptConfig instead of duplicating fields
- Validation: Comprehensive parameter validation using Pydantic
- Type Safety: Strong typing with appropriate field validators
- Constants Usage: All magic values replaced with constants

### Integration Strategy:
- Created from ExperimentConfig via factory methods
- Used by LLMActionService for unified service initialization
- Provides configuration to all RVAndroid tool components
- Ensures consistent behavior across tool execution
"""

from typing import Dict, Any, Optional

from pydantic import Field, field_validator

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.validation import BaseValidatedModel
from rv_llm.config.llm_config import LLMConfig
from rv_llm.config.prompt_config import PromptConfig
# No server constants needed for RVSmart (direct execution)


class RvSmartToolConfig(BaseValidatedModel):
    """
    Unified configuration for RVSmart tool execution.
    
    This class provides centralized configuration management for the RVSmart tool,
    combining LLM backend configuration with prompt generation settings through
    composition rather than duplication.
    
    ### Configuration Categories:
    - LLM: Backend configuration for language model interaction
    - Prompt: Strategy and template configuration for prompt generation
    - Tool: RVAndroid-specific execution parameters
    
    ### Design Principles:
    - Single Responsibility: Each configuration class handles its specific domain
    - Composition over Inheritance: Uses PromptConfig instead of duplicating fields
    - Validation: Comprehensive parameter validation using Pydantic
    - Type Safety: Strong typing with appropriate field validators
    """

    # Composed Configuration Objects
    llm_config: LLMConfig = Field(
        description="LLM backend configuration for language model interaction"
    )
    prompt_config: PromptConfig = Field(
        description="Prompt strategy and template configuration"
    )

    # Tool-Specific Configuration  
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode for detailed logging and tracing"
    )

    # Additional Parameters
    additional_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional tool-specific parameters"
    )

    # RVSmart uses direct execution, no server validation needed

    @classmethod
    def create_from_variant(
            cls,
            variant_config: Dict[str, Any],
            override_params: Dict[str, Any] = None
    ) -> 'RvSmartToolConfig':
        """
        Create RvAndroidToolConfig from variant configuration and parameter overrides.
        
        This factory method creates typed configuration objects from variant
        specifications, enabling clean separation between predefined variants
        and experiment-specific parameter overrides.
        
        ### Configuration Resolution:
        1. Create LLMConfig from variant LLM parameters
        2. Create PromptConfig from variant prompt parameters  
        3. Apply parameter overrides for dynamic configuration
        4. Combine into unified RvAndroidToolConfig instance
        
        Args:
            variant_config: Base configuration from variant registry
            override_params: Parameter overrides from experiment configuration
            
        Returns:
            Configured RvAndroidToolConfig instance
            
        Raises:
            ConfigurationError: If configuration creation fails
        """
        from rv_llm.llm.constants import LLMType, PromptStrategyType
        from rv_screen_parser.constants import ScreenParserType, VisitorType

        override_params = override_params or {}

        # Merge variant config with overrides
        final_config = {**variant_config, **override_params}
        

        # Create LLM configuration
        llm_config = LLMConfig(
            llm_type=final_config.get("llm_type", LLMType.OLLAMA),
            model=final_config.get("llm_model", "llama3.2:1b"),
            temperature=final_config.get("temperature", 0.2),
            top_p=final_config.get("top_p", 0.7),
            top_k=final_config.get("top_k", 40),
            max_tokens=final_config.get("max_tokens", 800),
            vision=final_config.get("vision", False),
            think=final_config.get("think", False)
        )

        # Create prompt configuration  
        strategy_value = final_config.get("prompt_strategy", PromptStrategyType.BATCH)
        visitor_value = final_config.get("visitor_type", VisitorType.DEFAULT)
        prompt_config = PromptConfig(
            strategy_type=strategy_value,
            parser_type=final_config.get("parser_type", ScreenParserType.DROIDBOT),
            visitor_type=visitor_value
        )

        # Create tool configuration
        return cls(
            llm_config=llm_config,
            prompt_config=prompt_config,
            
            debug_mode=final_config.get("debug_mode", False),
            additional_params=override_params
        )

    @ErrorHandler.handle_errors(
        component="RvAndroidToolConfig",
        operation="validate"
    )
    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate the unified configuration.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate LLM configuration
        llm_valid, llm_error = self.llm_config.validate()
        if not llm_valid:
            return False, f"LLM configuration error: {llm_error}"

        # Validate prompt configuration
        prompt_valid, prompt_error = self.prompt_config.validate()
        if not prompt_valid:
            return False, f"Prompt configuration error: {prompt_error}"

        # RVSmart uses direct execution, no server port validation needed

        return True, None

    def get_strategy_type(self) -> str:
        """Get the prompt strategy type from composed configuration."""
        return self.prompt_config.strategy_type

    def get_parser_type(self) -> str:
        """Get the screen parser type from composed configuration."""
        return self.prompt_config.parser_type

    def get_visitor_type(self) -> str:
        """Get the visitor type from composed configuration."""
        return self.prompt_config.visitor_type

    def get_template_paths(self) -> Dict[str, str]:
        """
        Get template directory paths for registration with PromptFramework.
        
        ### Template Registration Strategy:
        This method provides the template directory paths that contain the
        tool-specific templates and fragments for monitored operations testing,
        enabling proper registration with the PromptFramework.
        
        Returns:
            Dictionary with template directory paths
        """
        from rvsmart_tool.templates import get_template_paths
        return get_template_paths()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            "llm_config": self.llm_config.to_dict() if hasattr(self.llm_config, 'to_dict')
                                                    else self.llm_config.model_dump(),
            "prompt_config": self.prompt_config.to_dict() if hasattr(self.prompt_config, 'to_dict')
                                                    else self.prompt_config.model_dump(),
            "debug_mode": self.debug_mode,
            "additional_params": self.additional_params
        }
