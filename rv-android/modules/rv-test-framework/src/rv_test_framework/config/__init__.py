"""Configuration management for RV-Android Test Framework."""

from rv_test_framework.config.predefined_configs import (
    get_basic_evaluation_configs,
    get_extended_evaluation_configs,
    get_all_evaluation_configs,
    TEST_VALIDATION_CONFIGS,
    TEST_EXPERIMENT_CONFIGS
)

__all__ = [
    "get_basic_evaluation_configs",
    "get_extended_evaluation_configs", 
    "get_all_evaluation_configs",
    "TEST_VALIDATION_CONFIGS",
    "TEST_EXPERIMENT_CONFIGS"
]