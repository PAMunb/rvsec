# rv_android_core/util/logging/constants.py
# NOTE: `logging` is re-exported through this module's namespace — manager.py
# accesses stdlib logging as `constants.logging.*`. Do not remove this import.
import logging  # noqa: F401

ERROR = 40  # Same as logging.ERROR

# Standard log level names (strings)
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"

# Standard context keys that should be used consistently
CONTEXT_TASK_ID = "task_id"
CONTEXT_APP_NAME = "app_name"
CONTEXT_TOOL_NAME = "tool_name"
CONTEXT_COMPONENT = "component"
CONTEXT_PHASE = "phase"

# Log tags for runtime verification output
TAG_RVSEC = "RVSEC"
TAG_RVSEC_COV = "RVSEC-COV"

# Common log messages patterns
LOG_START = "Starting {phase}"
LOG_COMPLETE = "Completed {phase}"
LOG_ERROR = "Error in {phase}: {error}"
LOG_SKIPPED = "Skipped {phase}: {reason}"
