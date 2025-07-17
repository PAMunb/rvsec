"""
RVAndroid Configuration Factory with Unified Configuration Support

This module provides factory methods to create unified RVAndroid configurations
from various configuration sources, implementing comprehensive strategy support
and eliminating configuration duplication through composition architecture.

### Architectural Overview:
This factory implements unified configuration creation that combines LLM backend
configuration with prompt strategy configuration, enabling complete control over
RVAndroid tool behavior through single configuration objects.

### Key Features:
- Unified Configuration Creation: Single factory for complete tool configuration
- Strategy Support: Full support for prompt strategies (BATCH_ACTION, STANDARD)
- Composition Architecture: Uses composed configurations instead of duplication
- Variant Processing: Comprehensive variant-to-configuration mapping
- CLI Integration: Direct CLI control over all configuration aspects

### Design Patterns:
- Factory Method: Configuration creation from different sources
- Composition Pattern: Combines multiple configuration objects
- Strategy Pattern: Different resolution strategies for different input types
- Template Method: Common configuration resolution workflow
- Validation Pattern: Comprehensive parameter validation

### Integration Strategy:
- Creates unified RvAndroidToolConfig instances
- Integrates with ExperimentConfig for configuration resolution
- Supports both predefined variants and manual configuration
- Provides type-safe configuration creation with validation
"""

from typing import Dict, Any, Optional, List

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_experiment.config import ExperimentConfig
from rv_llm.config import LLMConfig
from rv_llm.config.prompt_config import PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rvandroid_tool.config.tool_config import RvAndroidToolConfig


class RvAndroidConfigFactory:
    """
    Factory for creating unified RVAndroid configurations from various sources.
    
    ### Architectural Overview:
    This factory implements unified configuration creation that combines LLM backend
    configuration with prompt strategy configuration through composition, enabling
    complete control over RVAndroid tool behavior.
    
    ### Key Features:
    - Unified Configuration Creation: Single factory for complete tool configuration
    - Strategy Support: Full support for prompt strategies (BATCH_ACTION, STANDARD)
    - Composition Architecture: Uses composed configurations instead of duplication
    - Variant Processing: Comprehensive variant-to-configuration mapping
    - CLI Integration: Direct CLI control over all configuration aspects
    
    ### Configuration Resolution Strategy:
    1. Determine if variants match predefined configurations
    2. Create LLM configuration using experiment configuration
    3. Create prompt configuration with strategy support
    4. Combine configurations into unified RvAndroidToolConfig
    
    ### Variant Support:
    - Predefined variants: 'llama_batch_detailed', 'gpt4_standard_basic'
    - Strategy variants: 'batch_action', 'standard'
    - Parser variants: 'droidbot', 'uiautomator'
    - Visitor variants: 'basic', 'detailed', 'default'
    
    ### Role in the System:
    - Central factory for unified RVAndroid tool configuration creation
    - Bridge between experiment configuration and tool-specific configuration
    - Enables multi-instance support with independent configurations
    - Provides consistent configuration resolution across different input types
    """
    
    # Predefined variant configurations
    PREDEFINED_VARIANTS = {
        "llama_batch_detailed": {
            "llm_type": LLMType.OLLAMA,
            "model": "llama3.2",
            "strategy_type": PromptStrategyType.BATCH_ACTION,
            "parser_type": ScreenParserType.DROIDBOT,
            "visitor_type": VisitorType.DETAILED
        },
        "gpt4_standard_basic": {
            "llm_type": LLMType.OPENAI,
            "model": "gpt-4",
            "strategy_type": PromptStrategyType.STANDARD,
            "parser_type": ScreenParserType.DROIDBOT,
            "visitor_type": VisitorType.BASIC
        },
        "ollama_standard_detailed": {
            "llm_type": LLMType.OLLAMA,
            "model": "llama3.2",
            "strategy_type": PromptStrategyType.STANDARD,
            "parser_type": ScreenParserType.DROIDBOT,
            "visitor_type": VisitorType.DETAILED
        }
    }

    @classmethod
    def get_supported_variants(cls) -> List[str]:
        """Get list of supported predefined variants."""
        return list(cls.PREDEFINED_VARIANTS.keys())

    @classmethod
    def is_variant_supported(cls, variant: str) -> bool:
        """Check if a variant is supported by the factory."""
        return variant in cls.PREDEFINED_VARIANTS

    @classmethod
    @ErrorHandler.handle_errors(
        component="RvAndroidConfigFactory",
        operation="create_from_tool_config"
    )
    def create_from_tool_config(
        cls,
        tool_config,
        experiment_config: ExperimentConfig
    ) -> Dict[str, Any]:
        """
        Create unified RVAndroid configuration from tool configuration with strategy support.
        
        This method creates comprehensive RVAndroid configuration by combining
        LLM backend configuration with prompt strategy configuration, enabling
        different approaches to prompt generation and processing.
        
        ### Configuration Creation Strategy:
        1. Determine if variants match predefined configurations
        2. Create LLM configuration using experiment configuration
        3. Create prompt configuration with strategy support
        4. Combine configurations into unified dictionary
        
        ### Variant Support:
        - Predefined variants: 'llama_batch_detailed', 'gpt4_standard_basic'
        - Strategy variants: 'batch_action', 'standard'
        - Parser variants: 'droidbot', 'uiautomator'
        - Visitor variants: 'basic', 'detailed', 'default'
        
        Args:
            tool_config: Tool configuration containing variants and parameters
            experiment_config: Experiment configuration for LLM config creation
            
        Returns:
            Dictionary containing unified configuration
            
        Raises:
            ConfigurationError: If configuration creation fails
        """
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_experiment.factories.rvandroid_config_factory",
            {CONTEXT_COMPONENT: "RvAndroidConfigFactory"}
        )
        
        # Check for predefined variants
        predefined_variant = None
        for variant in tool_config.variants:
            if cls.is_variant_supported(variant):
                predefined_variant = variant
                break
        
        if predefined_variant:
            # Use predefined variant configuration
            logger.info(f"Using predefined variant: {predefined_variant}")
            config_dict = cls.create_from_tool_name(
                tool_name=predefined_variant,
                tool_config=tool_config,
                experiment_config=experiment_config
            )
        else:
            # Create configuration from individual variants
            logger.info("Creating configuration from individual variants")
            llm_config = experiment_config.get_llm_config(tool_config.name)
            prompt_config = experiment_config.get_prompt_config(tool_config.name)
            
            # Create unified configuration using factory method
            unified_config = RvAndroidToolConfig.from_experiment_config(
                experiment_config=experiment_config,
                tool_name=tool_config.name
            )
            
            config_dict = {
                "tool_config": unified_config,
                "llm_config": llm_config,
                "prompt_config": prompt_config
            }
        
        logger.info(f"Created unified RVAndroid configuration for tool: {tool_config.name}")
        return config_dict

    @classmethod
    @ErrorHandler.handle_errors(
        component="RvAndroidConfigFactory",
        operation="create_from_tool_name"
    )
    def create_from_tool_name(
        cls,
        tool_name: str,
        tool_config,
        experiment_config: ExperimentConfig
    ) -> Dict[str, Any]:
        """
        Create unified configuration from tool name with predefined variant support.
        
        This method creates configuration from predefined variants or constructs
        configuration from tool name and parameters, providing flexibility for
        both predefined and custom configurations.
        
        ### Configuration Resolution:
        1. Check if tool_name matches predefined variant
        2. Apply predefined configuration if found
        3. Create LLM and prompt configurations
        4. Combine into unified RvAndroidToolConfig
        5. Apply parameter overrides
        
        Args:
            tool_name: Name of the tool or predefined variant
            tool_config: Tool configuration containing parameters
            experiment_config: Experiment configuration for config creation
            
        Returns:
            Dictionary containing unified configuration
            
        Raises:
            ConfigurationError: If configuration creation fails
        """
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            "rv_experiment.factories.rvandroid_config_factory",
            {CONTEXT_COMPONENT: "RvAndroidConfigFactory"}
        )
        
        if tool_name in cls.PREDEFINED_VARIANTS:
            # Use predefined variant configuration
            variant_config = cls.PREDEFINED_VARIANTS[tool_name]
            
            # Create LLM configuration from variant
            llm_config = LLMConfig(
                llm_type=variant_config["llm_type"],
                model=variant_config["model"],
                base_url=cls._get_base_url_for_llm_type(variant_config["llm_type"]),
                temperature=0.1,
                max_tokens=2000
            )
            
            # Create prompt configuration from variant
            prompt_config = PromptConfig(
                strategy_type=variant_config["strategy_type"],
                parser_type=variant_config["parser_type"],
                visitor_type=variant_config["visitor_type"]
            )
            
            # Apply parameter overrides
            cls._apply_parameter_overrides(llm_config, prompt_config, tool_config.parameters)
            
            # Create unified configuration
            unified_config = RvAndroidToolConfig(
                llm_config=llm_config,
                prompt_config=prompt_config,
                server_port=tool_config.parameters.get('server_port', 8080),
                debug_mode=tool_config.parameters.get('debug_mode', False),
                additional_params=tool_config.parameters
            )
            
            logger.info(f"Created configuration from predefined variant: {tool_name}")
            
        else:
            # Create configuration using experiment config methods
            unified_config = RvAndroidToolConfig.from_experiment_config(
                experiment_config=experiment_config,
                tool_name=tool_name
            )
            
            logger.info(f"Created configuration from experiment config: {tool_name}")
        
        return {
            "tool_config": unified_config,
            "llm_config": unified_config.llm_config,
            "prompt_config": unified_config.prompt_config
        }

    @classmethod
    def _get_base_url_for_llm_type(cls, llm_type: str) -> str:
        """Get appropriate base URL for LLM type."""
        if llm_type == LLMType.OLLAMA:
            return "http://localhost:11434"
        elif llm_type == LLMType.OPENAI:
            return "https://api.openai.com/v1"
        else:
            return ""

    @classmethod
    def _apply_parameter_overrides(
        cls, 
        llm_config: LLMConfig, 
        prompt_config: PromptConfig, 
        parameters: Dict[str, Any]
    ) -> None:
        """Apply parameter overrides to configurations."""
        # Apply LLM configuration overrides
        if "model" in parameters:
            llm_config.model = parameters["model"]
        if "temperature" in parameters:
            llm_config.temperature = parameters["temperature"]
        if "max_tokens" in parameters:
            llm_config.max_tokens = parameters["max_tokens"]
        
        # Apply prompt configuration overrides
        if "strategy_type" in parameters:
            prompt_config.strategy_type = parameters["strategy_type"]
        if "parser_type" in parameters:
            prompt_config.parser_type = parameters["parser_type"]
        if "visitor_type" in parameters:
            prompt_config.visitor_type = parameters["visitor_type"]

    @classmethod
    @ErrorHandler.handle_errors(
        component="RvAndroidConfigFactory",
        operation="validate_configuration"
    )
    def validate_configuration(cls, config_dict: Dict[str, Any]) -> bool:
        """
        Validate unified configuration dictionary.
        
        Args:
            config_dict: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if "tool_config" not in config_dict:
            raise ConfigurationError("Missing tool_config in configuration")
        
        tool_config = config_dict["tool_config"]
        if not isinstance(tool_config, RvAndroidToolConfig):
            raise ConfigurationError("Invalid tool_config type")
        
        # Validate unified configuration
        is_valid, error = tool_config.validate()
        if not is_valid:
            raise ConfigurationError(f"Configuration validation failed: {error}")
        
        return True