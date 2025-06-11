# rv_llm/config/strategy_config.py
"""Configuration class for prompt strategies following the established architectural pattern."""

import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


@dataclass
class PromptStrategyConfig:
    """
    Configuration class for prompt strategy settings.
    Follows the established architectural pattern with typed configuration classes.
    
    ### Architectural Decisions:
    - Implements typed configuration class with validation
    - Provides schema-based approach to configuration management
    - Supports serialization and deserialization for persistence
    - Enables runtime configuration updates and introspection
    - Follows the established pattern from LLMConfiguration
    """
    
    # Core strategy configuration
    strategy_name: str = "standard"
    template_name: Optional[str] = None
    enable_context_caching: bool = True
    max_context_length: int = 8192
    
    # Information fragment configuration
    enabled_fragments: List[str] = field(default_factory=lambda: [
        "monitored_operations",
        "screenshot",
        "history",
        "transition_guidance", 
        "ui_elements"
    ])
    
    # Template configuration
    template_format: str = "jinja2"
    template_validation: bool = True
    
    # Performance configuration
    generation_timeout: int = 30
    retry_attempts: int = 3
    
    # Additional parameters
    kwargs: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize logging after dataclass creation."""
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "llm.config.strategy",
            {CONTEXT_COMPONENT: self.__class__.__name__}
        )
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate the configuration.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate strategy name
        if not self.strategy_name or not isinstance(self.strategy_name, str):
            errors.append("strategy_name must be a non-empty string")
        
        # Validate max_context_length
        if not isinstance(self.max_context_length, int) or self.max_context_length <= 0:
            errors.append("max_context_length must be a positive integer")
        
        # Validate enabled_fragments
        if not isinstance(self.enabled_fragments, list):
            errors.append("enabled_fragments must be a list")
        
        # Validate template_format
        valid_formats = ["jinja2", "xml", "simple"]
        if self.template_format not in valid_formats:
            errors.append(f"template_format must be one of: {valid_formats}")
        
        # Validate timeout values
        if not isinstance(self.generation_timeout, int) or self.generation_timeout <= 0:
            errors.append("generation_timeout must be a positive integer")
        
        if not isinstance(self.retry_attempts, int) or self.retry_attempts < 0:
            errors.append("retry_attempts must be a non-negative integer")
        
        if errors and hasattr(self, 'logger'):
            for error in errors:
                self.logger.warning(f"Configuration validation error: {error}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'PromptStrategyConfig':
        """
        Create configuration from dictionary.
        
        Args:
            config_dict: Dictionary with configuration parameters
            
        Returns:
            PromptStrategyConfig instance
        """
        # Make a copy to avoid modifying the original
        config = config_dict.copy()
        
        # Extract known parameters with defaults
        strategy_name = config.pop("strategy_name", "standard")
        template_name = config.pop("template_name", None)
        enable_context_caching = config.pop("enable_context_caching", True)
        max_context_length = config.pop("max_context_length", 8192)
        enabled_fragments = config.pop("enabled_fragments", [
            "monitored_operations", "screenshot", "history", 
            "transition_guidance", "ui_elements"
        ])
        template_format = config.pop("template_format", "jinja2")
        template_validation = config.pop("template_validation", True)
        generation_timeout = config.pop("generation_timeout", 30)
        retry_attempts = config.pop("retry_attempts", 3)
        
        # Remaining parameters go to kwargs
        kwargs = config
        
        return cls(
            strategy_name=strategy_name,
            template_name=template_name,
            enable_context_caching=enable_context_caching,
            max_context_length=max_context_length,
            enabled_fragments=enabled_fragments,
            template_format=template_format,
            template_validation=template_validation,
            generation_timeout=generation_timeout,
            retry_attempts=retry_attempts,
            kwargs=kwargs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dictionary with configuration parameters
        """
        config_dict = {
            "strategy_name": self.strategy_name,
            "template_name": self.template_name,
            "enable_context_caching": self.enable_context_caching,
            "max_context_length": self.max_context_length,
            "enabled_fragments": self.enabled_fragments,
            "template_format": self.template_format,
            "template_validation": self.template_validation,
            "generation_timeout": self.generation_timeout,
            "retry_attempts": self.retry_attempts,
        }
        
        # Add kwargs
        config_dict.update(self.kwargs)
        
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
    def from_json(cls, json_str: str) -> 'PromptStrategyConfig':
        """
        Create configuration from JSON string.
        
        Args:
            json_str: JSON string representation of configuration
            
        Returns:
            PromptStrategyConfig instance
        """
        config_dict = json.loads(json_str)
        return cls.from_dict(config_dict)
    
    def get_fragment_config(self, fragment_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific information fragment.
        
        Args:
            fragment_name: Name of the fragment
            
        Returns:
            Configuration dictionary for the fragment
        """
        fragment_config = self.kwargs.get(f"{fragment_name}_config", {})
        return fragment_config
    
    def set_fragment_config(self, fragment_name: str, config: Dict[str, Any]) -> None:
        """
        Set configuration for a specific information fragment.
        
        Args:
            fragment_name: Name of the fragment
            config: Configuration dictionary for the fragment
        """
        self.kwargs[f"{fragment_name}_config"] = config
    
    def is_fragment_enabled(self, fragment_name: str) -> bool:
        """
        Check if a specific information fragment is enabled.
        
        Args:
            fragment_name: Name of the fragment
            
        Returns:
            True if fragment is enabled, False otherwise
        """
        return fragment_name in self.enabled_fragments
    
    def enable_fragment(self, fragment_name: str) -> None:
        """
        Enable a specific information fragment.
        
        Args:
            fragment_name: Name of the fragment to enable
        """
        if fragment_name not in self.enabled_fragments:
            self.enabled_fragments.append(fragment_name)
    
    def disable_fragment(self, fragment_name: str) -> None:
        """
        Disable a specific information fragment.
        
        Args:
            fragment_name: Name of the fragment to disable
        """
        if fragment_name in self.enabled_fragments:
            self.enabled_fragments.remove(fragment_name)
    
    def __str__(self) -> str:
        """
        String representation of the configuration.
        
        Returns:
            String representation
        """
        return (f"PromptStrategyConfig(strategy_name={self.strategy_name}, "
                f"template_name={self.template_name}, "
                f"fragments={len(self.enabled_fragments)})")
    
    def __repr__(self) -> str:
        """
        Detailed string representation of the configuration.
        
        Returns:
            Detailed string representation
        """
        return (f"PromptStrategyConfig("
                f"strategy_name={repr(self.strategy_name)}, "
                f"template_name={repr(self.template_name)}, "
                f"enable_context_caching={repr(self.enable_context_caching)}, "
                f"max_context_length={repr(self.max_context_length)}, "
                f"enabled_fragments={repr(self.enabled_fragments)}, "
                f"kwargs={repr(self.kwargs)})")