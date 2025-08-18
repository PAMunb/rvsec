"""
Constants for RVAndroid tool configuration and operation.

This module defines constants used throughout the RVAndroid tool for
configuration, action processing, and multimodal capabilities.
"""

# Tool identification
RVANDROID_TOOL_NAME = "rvandroid"
RVANDROID_DESCRIPTION = "LLM-based Android testing tool with DroidBot integration"

# Server configuration
DEFAULT_SERVER_PORT = 5000
SERVER_STARTUP_TIMEOUT = 30
SERVER_SHUTDOWN_TIMEOUT = 10

# External navigation limits
MAX_EXTERNAL_ATTEMPTS = 3
EXTERNAL_NAVIGATION_RESET_THRESHOLD = 1

# Action processing
ACTION_GENERATION_TIMEOUT = 60
MAX_RETRIES_PER_ACTION = 3

# Multimodal action types
CUSTOM_COORDINATE_ACTION_ID = "coord"
ACTION_TYPE_CLICK = "click"
ACTION_TYPE_LONG_CLICK = "long_click" 
ACTION_TYPE_SET_TEXT = "set_text"
ACTION_TYPE_TEXT_CHANGE = "text_change"
ACTION_TYPE_SCROLL = "scroll"
ACTION_TYPE_KEY_EVENT = "key_event"

# Action validation
COORDINATE_VALIDATION_MIN = 0
COORDINATE_VALIDATION_MAX = 4096
ACTION_ID_RANGE_MIN = 1
ACTION_ID_RANGE_MAX = 100

# Vision strategy configuration
VISION_STRATEGY_NAME = "vision"
VISION_MAX_TOKENS_DEFAULT = 1200
VISION_TEMPERATURE_DEFAULT = 0.3
