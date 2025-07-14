"""
RVAndroid configuration factory for monitored operations testing.

This module provides factory methods to create RVAndroidToolConfig instances
from various configuration sources, implementing the hybrid variant system
for maximum flexibility and ease of use.
"""

from typing import Dict, Any, Optional, List
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.error.exceptions import ConfigurationError
from rv_experiment.config import ExperimentConfig
# from rv_experiment.domain.task import TaskConfig  # Use generic type for now
from rv_llm.config import LLMConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType


class RvAndroidConfigFactory:
    """
    Factory for creating RVAndroidToolConfig instances from various sources.
    
    ### Architectural Overview:
    This factory implements the hybrid variant system that allows users to:
    1. Use pre-configured variants for common scenarios
    2. Manually configure all parameters for custom scenarios
    3. Mix variants with parameter overrides for flexibility
    
    ### Key Features:
    - Pre-configured variants for common LLM + strategy combinations
    - Manual configuration support for custom scenarios
    - Hybrid approach: variant baseline + parameter overrides
    - Type-safe configuration creation with validation
    - Integration with rv-experiment configuration system
    
    ### Role in the System:
    - Central factory for RVAndroid tool configuration creation
    - Bridge between experiment configuration and tool-specific configuration
    - Enables multi-instance support with independent configurations
    - Provides consistent configuration resolution across different input types
    
    ### Design Patterns:
    - Factory Method: Configuration creation from different sources
    - Strategy Pattern: Different resolution strategies for different input types
    - Template Method: Common configuration resolution workflow
    - Validation Pattern: Comprehensive parameter validation
    """
    
    # Pre-configured variants for common use cases
    PREDEFINED_VARIANTS = {
        "llama_batch_detailed": {
            "llm_backend": LLMType.OLLAMA,
            "llm_model": "llama3.2:3b",
            "llm_base_url": "http://localhost:11434",
            "llm_temperature": 0.2,
            "llm_max_tokens": 800,
            "prompt_strategy": PromptStrategyType.BATCH_ACTION,
            "screen_parser": ScreenParserType.DROIDBOT,
            "visitor_type": VisitorType.DETAILED,
            "max_context_length": 8192
        },
        "gpt4_standard_basic": {
            "llm_backend": LLMType.FRONTIER,
            "llm_model": "gpt-4",
            "llm_provider": "openai",
            "llm_temperature": 0.3,
            "llm_max_tokens": 600,
            "prompt_strategy": PromptStrategyType.STANDARD,
            "screen_parser": ScreenParserType.DROIDBOT,
            "visitor_type": VisitorType.BASIC,
            "max_context_length": 16384
        },
        "claude_context_enhanced": {
            "llm_backend": LLMType.FRONTIER,
            "llm_model": "claude-3-5-sonnet-20241022",
            "llm_provider": "anthropic",
            "llm_temperature": 0.1,
            "llm_max_tokens": 1000,
            "prompt_strategy": PromptStrategyType.STANDARD,
            "screen_parser": ScreenParserType.UIAUTOMATOR,
            "visitor_type": VisitorType.DEFAULT,
            "max_context_length": 32768
        },
        "local_llama_fast": {
            "llm_backend": LLMType.OLLAMA,
            "llm_model": "llama3.2:1b",
            "llm_base_url": "http://localhost:11434",
            "llm_temperature": 0.4,
            "llm_max_tokens": 400,
            "prompt_strategy": PromptStrategyType.STANDARD,
            "screen_parser": ScreenParserType.DROIDBOT,
            "visitor_type": VisitorType.BASIC,
            "max_context_length": 4096
        },
        "gemini_comprehensive": {
            "llm_backend": LLMType.FRONTIER,
            "llm_model": "gemini-pro",
            "llm_provider": "google",
            "llm_temperature": 0.2,
            "llm_max_tokens": 800,
            "prompt_strategy": PromptStrategyType.BATCH_ACTION,
            "screen_parser": ScreenParserType.UIAUTOMATOR,
            "visitor_type": VisitorType.DETAILED,
            "max_context_length": 16384
        }
    }
    
    def __init__(self):
        """Initialize the factory with logging."""
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.factories.rvandroid_config_factory",
            {CONTEXT_COMPONENT: "RvAndroidConfigFactory"}
        )
    
    @classmethod
    @ErrorHandler.handle_errors(
        component="RvAndroidConfigFactory",
        operation="create_from_tool_name"
    )
    def create_from_tool_name(
        cls,
        tool_name: str,
        tool_config: Any,
        experiment_config: ExperimentConfig
    ) -> Dict[str, Any]:
        """
        Create RVAndroid configuration from tool name and configuration.
        
        ### Configuration Resolution Strategy:
        This method implements the hybrid variant system:
        1. Check if tool_name matches a predefined variant
        2. If yes, use variant as baseline and apply parameter overrides
        3. If no, use manual configuration from parameters
        4. Validate and return complete configuration
        
        Args:
            tool_name: Tool name (may be variant name like "llama_batch_detailed")
            tool_config: Any with configuration parameters
            experiment_config: ExperimentConfig for global settings
            
        Returns:
            Dictionary with complete RVAndroid configuration
            
        Raises:
            RVConfigurationError: If configuration is invalid
        """
        factory = cls()
        
        # Determine configuration source
        if tool_name in cls.PREDEFINED_VARIANTS:
            # Use predefined variant as baseline
            config = cls._resolve_variant_configuration(tool_name, tool_config, factory)
        else:
            # Use manual configuration from parameters
            config = cls._resolve_manual_configuration(tool_config, factory)
        
        # Apply experiment-level defaults
        config = cls._apply_experiment_defaults(config, experiment_config, factory)
        
        # Validate configuration
        cls._validate_configuration(config, factory)
        
        factory.logger.info(f"Created RVAndroid configuration for tool: {tool_name}")
        return config
    
    @classmethod
    def _resolve_variant_configuration(
        cls,
        tool_name: str,
        tool_config: Any,
        factory: 'RvAndroidConfigFactory'
    ) -> Dict[str, Any]:
        """
        Resolve configuration using predefined variant as baseline.
        
        Args:
            tool_name: Variant name
            tool_config: Any with parameter overrides
            factory: Factory instance for logging
            
        Returns:
            Resolved configuration dictionary
        """
        # Start with variant baseline
        config = cls.PREDEFINED_VARIANTS[tool_name].copy()
        
        # Apply parameter overrides
        if hasattr(tool_config, 'parameters') and tool_config.parameters:
            config.update(tool_config.parameters)
        
        factory.logger.debug(f"Resolved variant configuration for: {tool_name}")
        return config
    
    @classmethod
    def _resolve_manual_configuration(
        cls,
        tool_config: Any,
        factory: 'RvAndroidConfigFactory'
    ) -> Dict[str, Any]:
        """
        Resolve configuration using manual parameters.
        
        Args:
            tool_config: Any with manual configuration
            factory: Factory instance for logging
            
        Returns:
            Resolved configuration dictionary
        """
        config = {}
        
        # Extract configuration from parameters
        if hasattr(tool_config, 'parameters') and tool_config.parameters:
            config.update(tool_config.parameters)
        
        # Apply defaults for missing parameters
        defaults = {
            "llm_backend": LLMType.OLLAMA,
            "llm_model": "llama3.2:3b",
            "llm_temperature": 0.2,
            "llm_max_tokens": 800,
            "prompt_strategy": PromptStrategyType.STANDARD,
            "screen_parser": ScreenParserType.DROIDBOT,
            "visitor_type": VisitorType.DETAILED,
            "max_context_length": 8192
        }
        
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
        
        factory.logger.debug("Resolved manual configuration")
        return config
    
    @classmethod
    def _apply_experiment_defaults(
        cls,
        config: Dict[str, Any],
        experiment_config: ExperimentConfig,
        factory: 'RvAndroidConfigFactory'
    ) -> Dict[str, Any]:
        """
        Apply experiment-level defaults to configuration.
        
        Args:
            config: Configuration dictionary
            experiment_config: ExperimentConfig for global settings
            factory: Factory instance for logging
            
        Returns:
            Configuration with experiment defaults applied
        """
        # Apply global timeout if not specified
        if "timeout" not in config:
            config["timeout"] = getattr(experiment_config, 'default_timeout', 3600)
        
        # Apply global working directory if not specified
        if "working_directory" not in config:
            config["working_directory"] = getattr(experiment_config, 'working_directory', '/tmp')
        
        factory.logger.debug("Applied experiment defaults")
        return config
    
    @classmethod
    def _validate_configuration(
        cls,
        config: Dict[str, Any],
        factory: 'RvAndroidConfigFactory'
    ) -> None:
        """
        Validate configuration parameters.
        
        Args:
            config: Configuration dictionary to validate
            factory: Factory instance for logging
            
        Raises:
            RVConfigurationError: If configuration is invalid
        """
        # Validate required parameters
        required_params = [
            "llm_backend", "llm_model", "prompt_strategy",
            "screen_parser", "visitor_type"
        ]
        
        missing_params = [param for param in required_params if param not in config]
        if missing_params:
            raise ConfigurationError(
                f"Missing required parameters: {', '.join(missing_params)}"
            )
        
        # Validate enum values
        if config["llm_backend"] not in LLMType.ALL:
            raise ConfigurationError(
                f"Invalid llm_backend: {config['llm_backend']}"
            )
        
        if config["prompt_strategy"] not in PromptStrategyType.ALL:
            raise ConfigurationError(
                f"Invalid prompt_strategy: {config['prompt_strategy']}"
            )
        
        if config["screen_parser"] not in ScreenParserType.ALL:
            raise ConfigurationError(
                f"Invalid screen_parser: {config['screen_parser']}"
            )
        
        if config["visitor_type"] not in VisitorType.ALL:
            raise ConfigurationError(
                f"Invalid visitor_type: {config['visitor_type']}"
            )
        
        # Validate numeric ranges
        if "llm_temperature" in config:
            temp = config["llm_temperature"]
            if not (0.0 <= temp <= 2.0):
                raise ConfigurationError(
                    f"llm_temperature must be between 0.0 and 2.0, got: {temp}"
                )
        
        if "llm_max_tokens" in config:
            tokens = config["llm_max_tokens"]
            if not (1 <= tokens <= 4096):
                raise ConfigurationError(
                    f"llm_max_tokens must be between 1 and 4096, got: {tokens}"
                )
        
        factory.logger.debug("Configuration validation passed")
    
    @classmethod
    def create_llm_config(cls, config: Dict[str, Any]) -> LLMConfig:
        """
        Create LLMConfig from resolved configuration.
        
        Args:
            config: Resolved configuration dictionary
            
        Returns:
            LLMConfig instance
        """
        llm_params = {}
        
        # Map configuration keys to LLMConfig fields
        mapping = {
            "llm_backend": "llm_type",
            "llm_model": "model",
            "llm_base_url": "base_url",
            "llm_temperature": "temperature",
            "llm_max_tokens": "max_tokens",
            "llm_provider": "provider",
            "llm_api_key": "api_key"
        }
        
        for config_key, llm_key in mapping.items():
            if config_key in config:
                llm_params[llm_key] = config[config_key]
        
        # Add other LLM-specific parameters
        for key, value in config.items():
            if key.startswith("llm_") and key not in mapping:
                llm_params[key] = value
        
        return LLMConfig(**llm_params)
    
    @classmethod
    def get_supported_variants(cls) -> List[str]:
        """
        Get list of supported predefined variants.
        
        Returns:
            List of supported variant names
        """
        return list(cls.PREDEFINED_VARIANTS.keys())
    
    @classmethod
    def get_variant_config(cls, variant_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific variant.
        
        Args:
            variant_name: Name of the variant
            
        Returns:
            Configuration dictionary or None if variant not found
        """
        return cls.PREDEFINED_VARIANTS.get(variant_name)
    
    @classmethod
    def is_variant_supported(cls, variant_name: str) -> bool:
        """
        Check if a variant is supported.
        
        Args:
            variant_name: Name of the variant
            
        Returns:
            True if variant is supported, False otherwise
        """
        return variant_name in cls.PREDEFINED_VARIANTS