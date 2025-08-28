"""
Constants for RV-UIAutomator module.

This module defines constants used throughout the UIAutomator components
for consistent configuration and behavior.
"""

# Connection and timeout constants
DEFAULT_CONNECTION_TIMEOUT = 30
DEFAULT_DEVICE_ID = "emulator-5554"
DEFAULT_ADB_SERVER_PORT = 5037

# Action execution constants  
ACTION_EXECUTION_DELAY = 0.5
TEXT_INPUT_DELAY = 0.3
SCREENSHOT_QUALITY = 90
STATE_STABILIZATION_DELAY = 1.0

# External navigation constants
MAX_EXTERNAL_NAVIGATION_ATTEMPTS = 3
EXTERNAL_NAVIGATION_DELAY = 2.0

# Error handling constants
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 1.0
MAX_CONSECUTIVE_ERRORS = 5

# Screenshot and state constants  
SCREENSHOT_FORMAT = "PNG"
SCREENSHOT_DIR = "./screenshots"
DEFAULT_SCREENSHOT_PATH = "./screenshot.png"

# State converter constants
SCREEN_HASH_LENGTH = 16