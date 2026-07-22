"""
Constants for RV-UIAutomator module.

Define timing, retry, and quality constants used by all UIAutomator components.
Values are tuned for headless emulator mode where SwiftShader software rendering
causes slower UI idle detection than hardware-accelerated rendering.

### Performance Optimization Notes (2026-01-27):
- Swipe duration reduced from 0.5s to 0.25s (50 steps x 5ms)
- ACTION_EXECUTION_DELAY reduced from 0.5s to 0.3s
- waitForIdleTimeout configured to reduce UI idle waiting
- These optimizations improve headless mode performance significantly
"""

# Connection and timeout constants
DEFAULT_CONNECTION_TIMEOUT = 30
DEFAULT_DEVICE_ID = "emulator-5554"
DEFAULT_ADB_SERVER_PORT = 5037

# UIAutomator2 settings for performance optimization
# Reduces UI idle waiting time (default can cause 10-20s delays in headless mode)
WAIT_FOR_IDLE_TIMEOUT = 5.0  # seconds (default is 10s)
WAIT_FOR_SELECTOR_TIMEOUT = 10.0  # seconds

# Action execution constants
# Optimized for headless mode performance while maintaining stability
ACTION_EXECUTION_DELAY = 0.3  # Reduced from 0.5s - delay after each action
TEXT_INPUT_DELAY = 0.2  # Reduced from 0.3s
SCREENSHOT_QUALITY = 90
STATE_STABILIZATION_DELAY = 0.8  # Reduced from 1.0s

# Swipe action constants
# Duration formula: steps × 5ms (e.g., 50 steps = 250ms)
DEFAULT_SWIPE_DURATION = 0.25  # Reduced from 0.5s for faster swipes
MIN_SWIPE_DURATION = 0.1  # Minimum safe duration
MAX_SWIPE_DURATION = 1.0  # Maximum duration for slow swipes

# External navigation constants
MAX_EXTERNAL_NAVIGATION_ATTEMPTS = 3
EXTERNAL_NAVIGATION_DELAY = 1.5  # Reduced from 2.0s

# Error handling constants
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 0.8  # Reduced from 1.0s
MAX_CONSECUTIVE_ERRORS = 5

# Screenshot and state constants
SCREENSHOT_FORMAT = "PNG"
SCREENSHOT_DIR = "./screenshots"
DEFAULT_SCREENSHOT_PATH = "./screenshot.png"

# State converter constants
SCREEN_HASH_LENGTH = 16
