"""
Constants for RVDroid Tool

### Architectural Overview:
This module defines constants used throughout the RVDroid tool system, including
tool metadata, configuration defaults, and integration parameters.

### Design Principles:
- Centralized constant management for maintainability
- Clear separation between tool-specific and system-wide constants
- Support for both LLM-enabled and traditional testing modes

### Integration Strategy:
- Used by tool registration system for plugin discovery
- Referenced by configuration system for default values
- Provides metadata for experiment orchestration
"""

# Tool Metadata
RVDROID_TOOL_NAME = "rvdroid"
RVDROID_DESCRIPTION = "RVDroid: UIAutomator2-based Android testing tool with optional LLM strategic guidance"

# Default Configuration Values
DEFAULT_DEVICE_ID = "emulator-5554"
DEFAULT_EXECUTION_TIMEOUT = 3600
DEFAULT_LLM_ENABLED = False

# Guidance System Constants
GUIDANCE_REQUEST_INTERVAL = 10  # Number of actions between guidance requests
MAX_GUIDANCE_HISTORY = 50      # Maximum number of historical entries for guidance context

# Strategy Constants
DEFAULT_STRATEGY = "adaptive"
FALLBACK_STRATEGY = "random"

# Template Paths (relative to module root)
TEMPLATES_DIR = "templates"
FRAGMENTS_DIR = "templates/fragments"

# Guidance Types
GUIDANCE_TYPE_STRATEGIC = "STRATEGIC_ADVICE"
GUIDANCE_TYPE_FLOW_CHANGE = "FLOW_CHANGE"  
GUIDANCE_TYPE_NO_GUIDANCE = "NO_GUIDANCE"

# Performance Monitoring
PERFORMANCE_METRIC_PREFIX = "rvdroid"
GUIDANCE_LATENCY_THRESHOLD = 5.0  # seconds
