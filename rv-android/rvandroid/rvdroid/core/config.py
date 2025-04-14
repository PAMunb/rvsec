# rvandroid/rvdroid/core/config.py

"""
Configuration management for RVDroid.

This module provides classes for loading, validating, and accessing 
configuration settings for RVDroid components.
"""

import json
import os
from typing import Dict, Any, Optional, List, Set, Type, TypeVar

from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


T = TypeVar('T')


class ConfigKey:
    """Configuration key constants for RVDroid."""
    
    # Core configuration
    EXECUTION_TIMEOUT = "execution_timeout"
    DEVICE_ID = "device_id"
    
    # UI configuration
    SCREENSHOT_ENABLED = "screenshot_enabled"
    SCREENSHOT_FREQUENCY = "screenshot_frequency"
    
    # Memory configuration
    SHORT_TERM_CAPACITY = "short_term_capacity"
    LONG_TERM_PERSISTENCE = "long_term_persistence"
    
    # Strategy configuration
    PREFERRED_STRATEGY = "preferred_strategy"
    STRATEGY_SWITCH_INTERVAL = "strategy_switch_interval"
    
    # LLM configuration
    LLM_ENABLED = "llm_enabled"
    LLM_MODEL = "llm_model"
    LLM_STRATEGY_INTERVAL = "llm_strategy_interval"


class Config:
    """
    Configuration manager for RVDroid.
    
    ### Architectural Decisions:
    - Provides a centralized configuration system for all components
    - Supports JSON-based configuration with validation
    - Implements environment variable overrides for flexibility
    - Uses type checking for configuration values
    - Provides sensible defaults for all settings
    
    ### Role in the System:
    - Manages configuration settings across all components
    - Provides configuration validation to prevent errors
    - Enables consistent configuration access patterns
    - Supports component-specific configuration sections
    - Allows runtime configuration updates for dynamic behavior
    """
    
    def __init__(self, config_file: Optional[str] = None, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize the configuration.
        
        Args:
            config_file: Optional path to JSON configuration file
            config_dict: Optional configuration dictionary
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.core.config",
            {CONTEXT_COMPONENT: "Config"}
        )
        
        # Initialize configuration
        self.config: Dict[str, Any] = {}
        
        # Load default configuration
        self._load_default_config()
        
        # Load from file if provided
        if config_file:
            self._load_config_file(config_file)
            
        # Load from dictionary if provided
        if config_dict:
            self._load_config_dict(config_dict)
            
        # Apply environment variable overrides
        self._apply_env_overrides()
        
    def _load_default_config(self) -> None:
        """Load default configuration values."""
        self.config = {
            # Core configuration
            ConfigKey.EXECUTION_TIMEOUT: 3600,  # 1 hour
            ConfigKey.DEVICE_ID: "emulator-5554",
            
            # UI configuration
            ConfigKey.SCREENSHOT_ENABLED: True,
            ConfigKey.SCREENSHOT_FREQUENCY: "state_change",  # Options: always, state_change, never
            
            # Memory configuration
            ConfigKey.SHORT_TERM_CAPACITY: 50,
            ConfigKey.LONG_TERM_PERSISTENCE: True,
            
            # Strategy configuration
            ConfigKey.PREFERRED_STRATEGY: "MonitoredOperationsFocusedStrategy",
            ConfigKey.STRATEGY_SWITCH_INTERVAL: 300,  # 5 minutes
            
            # LLM configuration
            ConfigKey.LLM_ENABLED: True,
            ConfigKey.LLM_MODEL: "default",
            ConfigKey.LLM_STRATEGY_INTERVAL: 60  # 1 minute
        }
        
    def _load_config_file(self, config_file: str) -> None:
        """
        Load configuration from a JSON file.
        
        Args:
            config_file: Path to JSON configuration file
        """
        if not os.path.exists(config_file):
            self.logger.warning(f"Configuration file does not exist: {config_file}")
            return
            
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                
            # Update configuration
            self._load_config_dict(file_config)
            self.logger.info(f"Loaded configuration from {config_file}")
            
        except Exception as e:
            self.logger.error(f"Error loading configuration file: {e}")
            
    def _load_config_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        Load configuration from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
        """
        # Update configuration
        for key, value in config_dict.items():
            if key in self.config:
                # Validate value type
                expected_type = type(self.config[key])
                if not isinstance(value, expected_type):
                    self.logger.warning(f"Invalid type for {key}: expected {expected_type.__name__}, got {type(value).__name__}")
                    continue
                    
                self.config[key] = value
                
    def _apply_env_overrides(self) -> None:
        """Apply environment variable overrides to configuration."""
        # Look for environment variables of the form RVDROID_<KEY>
        for key in self.config:
            env_key = f"RVDROID_{key.upper()}"
            if env_key in os.environ:
                env_value = os.environ[env_key]
                
                # Convert environment value to expected type
                expected_type = type(self.config[key])
                try:
                    if expected_type == bool:
                        # Handle boolean values
                        env_value = env_value.lower() in ('true', '1', 'yes')
                    elif expected_type == int:
                        env_value = int(env_value)
                    elif expected_type == float:
                        env_value = float(env_value)
                    # String and other types can be used as-is
                    
                    self.config[key] = env_value
                    self.logger.info(f"Applied environment override for {key}")
                    
                except ValueError:
                    self.logger.warning(f"Invalid environment value for {key}: {env_value}")
                    
    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            Configuration value or default if not found
        """
        return self.config.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        if key in self.config:
            # Validate value type
            expected_type = type(self.config[key])
            if not isinstance(value, expected_type):
                self.logger.warning(f"Invalid type for {key}: expected {expected_type.__name__}, got {type(value).__name__}")
                return
                
        self.config[key] = value
        
    def get_component_config(self, component_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific component.
        
        Args:
            component_name: Component name
            
        Returns:
            Component configuration
        """
        # Look for component-specific configuration
        component_key = f"{component_name.lower()}"
        component_config = self.config.get(component_key, {})
        
        # For backward compatibility, also check underscore version
        if not component_config:
            component_key = component_name.lower().replace(' ', '_')
            component_config = self.config.get(component_key, {})
            
        return component_config
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()
        
    def save_to_file(self, config_file: str) -> bool:
        """
        Save configuration to a file.
        
        Args:
            config_file: Path to save configuration
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
                
            self.logger.info(f"Saved configuration to {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False