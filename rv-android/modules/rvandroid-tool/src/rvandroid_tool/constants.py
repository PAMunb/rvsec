"""
Constants for RVAndroid tool configuration and operation.
"""

# Tool identification
RVANDROID_TOOL_NAME = "rvandroid"
RVANDROID_DESCRIPTION = "LLM-based Android testing tool with DroidBot integration"

# Server configuration
DEFAULT_SERVER_PORT = 5000
SERVER_STARTUP_TIMEOUT = 30
SERVER_SHUTDOWN_TIMEOUT = 10

# External navigation limits
# TODO sincronizar com as alteracoes no droidbot e verificar a necessidade de tunar o prompt
MAX_EXTERNAL_ATTEMPTS = 3
EXTERNAL_NAVIGATION_RESET_THRESHOLD = 1

# Action processing
ACTION_GENERATION_TIMEOUT = 60
MAX_RETRIES_PER_ACTION = 3 # TODO rever: esta sendo usado? e como?
