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

from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.config.llm_config import LLMConfig
from rv_llm.config.prompt_config import PromptConfig
from rv_llm.llm.constants import PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rvandroid_tool.constants import DEFAULT_SERVER_PORT


class RvAndroidToolConfig(BaseValidatedModel):
    """
    Unified configuration for RVAndroid tool execution.
    
    This class provides centralized configuration management for the RVAndroid tool,
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
    
    ### Usage Examples:
    ```python
    # Create from experiment configuration
    tool_config = RvAndroidToolConfig.from_experiment_config(
        experiment_config=experiment_config,
        tool_name="rvandroid"
    )
    
    # Access composed configurations
    llm_config = tool_config.llm_config
    prompt_config = tool_config.prompt_config
    
    # Use in LLM service
    service = LLMActionService(
        static_data=static_data,
        tool_config=tool_config,
        app_package=app_package
    )
    ```
    """
    
    # Composed Configuration Objects
    llm_config: LLMConfig = Field(
        description="LLM backend configuration for language model interaction"
    )
    prompt_config: PromptConfig = Field(
        description="Prompt strategy and template configuration"
    )
    
    # Tool-Specific Configuration
    server_port: int = Field(
        default=DEFAULT_SERVER_PORT,
        ge=1024,
        le=49151,
        description="Port for RVAndroid server communication with DroidBot"
    )
    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode for detailed logging and tracing"
    )
    
    # Additional Parameters
    additional_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional tool-specific parameters"
    )

    @field_validator('server_port')
    @classmethod
    def validate_server_port(cls, v):
        """Validate server port is within valid range."""
        if v < 1024 or v > 49151:
            raise ValueError(f"Server port must be between 1024-49151, got: {v}")
        return v

    # REMOVED: from_experiment_config() method - created circular dependency with ExperimentConfig
    # Configuration will be created directly by RVAndroid tool using create_from_variant() method

    @classmethod
    def create_from_variant(
        cls,
        variant_config: Dict[str, Any],
        override_params: Dict[str, Any] = None
    ) -> 'RvAndroidToolConfig':
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
            model=final_config.get("llm_model", "llama3.2"),
            temperature=final_config.get("temperature", 0.1),
            top_p=final_config.get("top_p", 0.9),
            max_tokens=final_config.get("max_tokens", 2048),
            vision=final_config.get("vision", False),
            think=final_config.get("think", False)
        )
        
        # Create prompt configuration  
        prompt_config = PromptConfig(
            strategy_type=final_config.get("prompt_strategy", PromptStrategyType.STANDARD),
            parser_type=final_config.get("parser_type", ScreenParserType.DROIDBOT),
            visitor_type=final_config.get("visitor_type", VisitorType.DETAILED)
        )
        
        # Create tool configuration
        return cls(
            llm_config=llm_config,
            prompt_config=prompt_config,
            server_port=final_config.get("server_port", DEFAULT_SERVER_PORT),
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
        
        # Validate server port
        if self.server_port < 1024 or self.server_port > 65535:
            return False, f"Invalid server port: {self.server_port}"
        
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
        from rvandroid_tool.templates import get_template_paths
        return get_template_paths()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary format.
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            "llm_config": self.llm_config.to_dict() if hasattr(self.llm_config, 'to_dict') else self.llm_config.model_dump(),
            "prompt_config": self.prompt_config.to_dict() if hasattr(self.prompt_config, 'to_dict') else self.prompt_config.model_dump(),
            "server_port": self.server_port,
            "debug_mode": self.debug_mode,
            "additional_params": self.additional_params
        }