"""
RVAndroid Tool Constants

This module provides constants specific to the RVAndroid tool module,
including server configuration and tool-specific parameters.

### Tool-Specific Constants:
- Server configuration for DroidBot policy communication
- Tool execution parameters
- Default values for RVAndroid tool configuration

### Integration Strategy:
- Used by RVAndroidTool for server port configuration
- Imported by RvAndroidToolConfig for default values
- Supports tool-specific configuration validation
"""

# Server Configuration
DEFAULT_SERVER_PORT = 8080  # Port for RVAndroid server communication with DroidBot

# Tool Execution Parameters
DEFAULT_TOOL_TIMEOUT = 600  # Default timeout for tool execution in seconds
DEFAULT_DEBUG_MODE = False  # Default debug mode setting

# Tool Configuration
DEFAULT_MAX_RETRIES = 3  # Maximum retry attempts for tool operations
DEFAULT_RETRY_DELAY = 1  # Delay between retry attempts in seconds