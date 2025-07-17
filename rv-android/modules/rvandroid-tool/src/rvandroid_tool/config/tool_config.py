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
        le=65535,
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
        if v < 1024 or v > 65535:
            raise ValueError(f"Server port must be between 1024-65535, got: {v}")
        return v

    @classmethod
    @ErrorHandler.handle_errors(
        component="RvAndroidToolConfig",
        operation="from_experiment_config"
    )
    def from_experiment_config(
        cls,
        experiment_config,
        tool_name: str = "rvandroid"
    ) -> 'RvAndroidToolConfig':
        """
        Create unified tool configuration from experiment configuration.
        
        This method serves as the primary factory for creating RvAndroidToolConfig
        instances from experiment-level configuration, ensuring consistent
        configuration patterns across the system.
        
        ### Configuration Resolution Strategy:
        1. Extract tool configuration from experiment tool_configs
        2. Create LLMConfig using experiment configuration
        3. Create PromptConfig from tool variants and parameters
        4. Combine configurations into unified tool configuration
        
        ### Variant Processing:
        - Strategy variants: 'standard', 'batch_action' → strategy_type
        - Parser variants: 'droidbot', 'uiautomator' → parser_type
        - Visitor variants: 'basic', 'detailed', 'default' → visitor_type
        
        Args:
            experiment_config: Experiment configuration containing tool specifications
            tool_name: Name of the tool to configure (default: "rvandroid")
            
        Returns:
            Unified RvAndroidToolConfig instance
            
        Raises:
            ConfigurationError: If tool configuration cannot be created
        """
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rvandroid_tool.config.tool_config",
            {CONTEXT_COMPONENT: "RvAndroidToolConfig"}
        )
        
        # Find tool configuration in experiment
        tool_configs = [tc for tc in experiment_config.tool_configs if tc.name == tool_name]
        if not tool_configs:
            raise ConfigurationError(f"Tool '{tool_name}' not found in experiment configuration")
        
        tool_config = tool_configs[0]
        
        # Create LLM configuration
        llm_config = experiment_config.get_llm_config(tool_name)
        
        # Create prompt configuration from variants
        prompt_config = experiment_config.get_prompt_config(tool_name)
        
        # Extract tool-specific parameters
        server_port = tool_config.parameters.get('server_port', DEFAULT_SERVER_PORT)
        debug_mode = tool_config.parameters.get('debug_mode', False)
        
        # Create unified configuration
        unified_config = cls(
            llm_config=llm_config,
            prompt_config=prompt_config,
            server_port=server_port,
            debug_mode=debug_mode,
            additional_params=tool_config.parameters
        )
        
        logger.info(
            f"Created unified RVAndroid configuration - "
            f"LLM: {llm_config.llm_type}:{llm_config.model}, "
            f"Strategy: {prompt_config.strategy_type}, "
            f"Parser: {prompt_config.parser_type}, "
            f"Server Port: {server_port}"
        )
        
        return unified_config

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