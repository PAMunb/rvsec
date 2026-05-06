"""
Validation configuration for RV-Android Core.

This module manages validation behavior across the RV-Android system through
environment variables and runtime configuration.
"""

import os
import threading
from typing import Optional

from rv_android_core.constants import ENV_PYDANTIC, ENV_PYDANTIC_LOG, ENV_PYDANTIC_STRICT
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ValidationConfig:
    """
    Centralized validation configuration management for RV-Android system.

    ### Architectural Decisions:
    - Implements singleton pattern for consistent validation behavior
    - Uses environment variables for deployment-specific configuration
    - Provides development vs production mode distinction
    - Integrates with the system's logging infrastructure

    ### Role in the System:
    - Controls validation behavior across all data models
    - Enables performance optimization in production environments
    - Provides debugging capabilities through detailed validation logs
    - Supports flexible validation policies for different deployment contexts

    ### Configuration Strategy:
    - Development: RV_PYDANTIC=true - Full validation for maximum type safety
    - Production: RV_PYDANTIC=false (default) - Minimal validation overhead
    - Testing: Can be overridden programmatically for test scenarios
    """

    _instance: Optional["ValidationConfig"] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "ValidationConfig":
        """Get the singleton instance of validation configuration."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ValidationConfig()
        return cls._instance

    def __init__(self):
        """Initialize validation configuration from environment."""
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self._logger = logging_manager.get_logger(
            "rv_android_core.util.validation.config",
            {CONTEXT_COMPONENT: "ValidationConfig"},
        )

        # Read configuration from environment
        self._enabled = self._read_validation_setting()
        self._strict_mode = self._read_strict_mode_setting()
        self._log_validation_events = self._read_logging_setting()

        # Log configuration status
        self._logger.info(
            f"Validation configured: enabled={self._enabled}, "
            f"strict={self._strict_mode}, logging={self._log_validation_events}"
        )

    def _read_validation_setting(self) -> bool:
        """Read RV_PYDANTIC env var (L1 cross-layer infra exception per gh55)."""
        env_value = os.getenv(ENV_PYDANTIC, "false").lower()
        return env_value in ("true", "1", "yes", "on")

    def _read_strict_mode_setting(self) -> bool:
        """Read RV_PYDANTIC_STRICT env var (L1 cross-layer infra exception per gh55)."""
        env_value = os.getenv(ENV_PYDANTIC_STRICT, "false").lower()
        return env_value in ("true", "1", "yes", "on")

    def _read_logging_setting(self) -> bool:
        """Read RV_PYDANTIC_LOG env var (L1 cross-layer infra exception per gh55)."""
        env_value = os.getenv(ENV_PYDANTIC_LOG, "false").lower()
        return env_value in ("true", "1", "yes", "on")

    @property
    def enabled(self) -> bool:
        """Check if validation is enabled."""
        return self._enabled

    @property
    def strict_mode(self) -> bool:
        """Check if strict validation mode is enabled."""
        return self._strict_mode

    @property
    def log_validation_events(self) -> bool:
        """Check if validation events should be logged."""
        return self._log_validation_events

    def set_enabled(self, enabled: bool) -> None:
        """
        Override validation setting programmatically.

        Args:
            enabled: Whether to enable validation

        Note:
            This override is primarily for testing scenarios.
            Production systems should use environment variables.
        """
        old_value = self._enabled
        self._enabled = enabled
        self._logger.debug(f"Validation setting changed: {old_value} -> {enabled}")

    def set_strict_mode(self, strict: bool) -> None:
        """
        Override strict mode setting programmatically.

        Args:
            strict: Whether to enable strict validation mode
        """
        old_value = self._strict_mode
        self._strict_mode = strict
        self._logger.debug(f"Strict mode setting changed: {old_value} -> {strict}")


# Module-level convenience function
def get_validation_config() -> ValidationConfig:
    """
    Get the global validation configuration instance.

    Returns:
        ValidationConfig instance
    """
    return ValidationConfig.get_instance()
