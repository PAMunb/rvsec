"""
Tool configuration for rvandroid-tool with parser/visitor settings.

This module provides configuration management for the rvandroid-tool,
including parser and visitor configuration that was moved from rv-llm
in Phase 7 of the refactoring process.

### Architectural Overview:
This configuration class handles tool-specific settings that don't belong
in the LLM configuration, providing clean separation between LLM concerns
and tool-specific parsing/visitor concerns.

### Key Features:
- Parser type configuration (DroidBot, UIAutomator)
- Visitor type configuration (basic, default, enhanced)
- LLM configuration integration
- Template registration with PromptFramework
- Clean separation from LLM-specific concerns

### Integration Strategy:
- Receives clean LLMConfig from rv-experiment
- Manages parser/visitor configuration locally
- Registers templates with PromptFramework during initialization
- Provides configuration to screen parser components
"""

from typing import Dict, Any, Optional
from pydantic import Field, field_validator

from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_llm.config.llm_config import LLMConfig


class RvAndroidToolConfig(BaseValidatedModel):
    """
    Configuration for rvandroid-tool with parser/visitor settings.
    
    ### Architectural Overview:
    This configuration class manages tool-specific settings that were
    previously mixed with LLM configuration. It provides clean separation
    between LLM concerns and tool-specific parsing/visitor concerns.
    
    ### Key Features:
    - Parser type configuration with validation
    - Visitor type configuration with validation
    - LLM configuration integration
    - Template path management
    - Clean separation from LLM-specific concerns
    
    ### Configuration Categories:
    - Parser: Screen parser type and configuration
    - Visitor: Visitor type and configuration
    - LLM: Clean LLM configuration from rv-llm
    - Templates: Tool-specific template paths
    
    ### Usage Examples:
    ```python
    # Create tool configuration
    llm_config = LLMConfig(llm_type="ollama", model="llama3.2:3b")
    tool_config = RvAndroidToolConfig(
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED,
        llm_config=llm_config
    )
    
    # Get parser parameters
    parser_params = tool_config.get_parser_parameters()
    
    # Get template paths
    template_paths = tool_config.get_template_paths()
    ```
    """
    
    # Parser Configuration
    parser_type: str = Field(default=ScreenParserType.DROIDBOT, description="Screen parser type")
    visitor_type: str = Field(default=VisitorType.DETAILED, description="Visitor type")
    
    # LLM Configuration
    llm_config: LLMConfig = Field(description="Clean LLM configuration")
    
    # Additional Parameters
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Additional parameters")
    
    def model_post_init(self, __context) -> None:
        """
        Initialize configuration after model creation.
        """
        # Note: Logging is handled directly in methods that need it
        # to avoid Pydantic validation issues with instance attributes
        pass
    
    @field_validator('parser_type')
    @classmethod
    def validate_parser_type(cls, v: str) -> str:
        """Validate parser type against supported parsers."""
        valid_parsers = ScreenParserType.ALL
        if v not in valid_parsers:
            raise ValueError(f"parser_type must be one of: {valid_parsers}")
        return v
    
    @field_validator('visitor_type')
    @classmethod
    def validate_visitor_type(cls, v: str) -> str:
        """Validate visitor type against supported visitors."""
        valid_visitors = VisitorType.ALL
        if v not in valid_visitors:
            raise ValueError(f"visitor_type must be one of: {valid_visitors}")
        return v
    
    @classmethod
    @ErrorHandler.handle_errors(
        component="RvAndroidToolConfig",
        operation="from_llm_config"
    )
    def from_llm_config(cls, llm_config: LLMConfig, 
                       parser_type: str = ScreenParserType.DROIDBOT,
                       visitor_type: str = VisitorType.DETAILED,
                       **kwargs) -> 'RvAndroidToolConfig':
        """
        Create tool configuration from LLMConfig.
        
        ### Configuration Strategy:
        This method creates a tool configuration by combining a clean LLMConfig
        with tool-specific parser and visitor settings, providing proper
        separation of concerns.
        
        Args:
            llm_config: Clean LLM configuration from rv-llm
            parser_type: Screen parser type
            visitor_type: Visitor type
            **kwargs: Additional configuration parameters
            
        Returns:
            Configured RvAndroidToolConfig instance
        """
        return cls(
            parser_type=parser_type,
            visitor_type=visitor_type,
            llm_config=llm_config,
            kwargs=kwargs
        )
    
    def get_parser_parameters(self) -> Dict[str, Any]:
        """
        Get parser-specific parameters for parser configuration.
        
        ### Parameter Extraction Strategy:
        Extracts parameters relevant for screen parser and visitor configuration,
        providing clean interface for parser creation.
        
        Returns:
            Dictionary with parser configuration parameters
        """
        return {
            "parser_type": self.parser_type,
            "visitor_type": self.visitor_type,
            **{k: v for k, v in self.kwargs.items() if k.startswith("parser_")}
        }
    
    def get_template_paths(self) -> Dict[str, str]:
        """
        Get template directory paths for registration with PromptFramework.
        
        ### Template Path Strategy:
        Provides template paths for the tool's templates and fragments,
        enabling proper registration with the PromptFramework.
        
        Returns:
            Dictionary with template directory paths
        """
        from rvandroid_tool.templates import get_template_paths
        return get_template_paths()
    
    def register_templates_with_framework(self, prompt_framework):
        """
        Register tool templates with the PromptFramework.
        
        ### Template Registration Strategy:
        Registers this tool's templates and fragments with the PromptFramework
        to enable proper template resolution and rendering.
        
        Args:
            prompt_framework: PromptFramework instance from rv-llm
        """
        template_paths = self.get_template_paths()
        
        # Register fragments directory
        if "fragments" in template_paths:
            prompt_framework.register_fragment_directory(template_paths["fragments"])
        
        # Register templates directory
        if "templates" in template_paths:
            prompt_framework.register_template_directory(template_paths["templates"])
        
        # Log template registration
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rvandroid_tool.config",
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )
        logger.debug(f"Registered templates with PromptFramework: {list(template_paths.keys())}")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary representation.
        
        Returns:
            Dictionary representation of the configuration
        """
        base_dict = self.model_dump(exclude_unset=False)
        
        # Add kwargs, excluding duplicates
        for key, value in self.kwargs.items():
            if key not in base_dict:
                base_dict[key] = value
        
        return base_dict
    
    def __str__(self) -> str:
        """
        String representation of the configuration.
        
        Returns:
            Concise string representation
        """
        return (f"RvAndroidToolConfig(parser_type={self.parser_type}, "
                f"visitor_type={self.visitor_type}, "
                f"llm_type={self.llm_config.llm_type}, "
                f"model={self.llm_config.model})")
    
    def __repr__(self) -> str:
        """
        Detailed string representation of the configuration.
        
        Returns:
            Detailed string representation for debugging
        """
        return (f"RvAndroidToolConfig("
                f"parser_type={repr(self.parser_type)}, "
                f"visitor_type={repr(self.visitor_type)}, "
                f"llm_config={repr(self.llm_config)}, "
                f"kwargs_count={len(self.kwargs)})")