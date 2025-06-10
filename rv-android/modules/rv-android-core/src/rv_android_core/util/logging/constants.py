# rvandroid/util/logging/constants.py
import logging

# Define custom log levels for experiment-specific events
EXPERIMENT_START = 25
EXPERIMENT_END = 26
TASK_START = 27
TASK_END = 28
ERROR = 40  # Same as logging.ERROR

# Register custom log levels with logging module
logging.addLevelName(EXPERIMENT_START, "EXPERIMENT_START")
logging.addLevelName(EXPERIMENT_END, "EXPERIMENT_END")
logging.addLevelName(TASK_START, "TASK_START")
logging.addLevelName(TASK_END, "TASK_END")

# Standard context keys that should be used consistently
CONTEXT_TASK_ID = "task_id"
CONTEXT_APP_NAME = "app_name"
CONTEXT_TOOL_NAME = "tool_name"
CONTEXT_COMPONENT = "component"
CONTEXT_PHASE = "phase"

# Common log messages patterns
LOG_START = "Starting {phase}"
LOG_COMPLETE = "Completed {phase}"
LOG_ERROR = "Error in {phase}: {error}"
LOG_SKIPPED = "Skipped {phase}: {reason}"
