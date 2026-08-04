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

# The APE-RV step heartbeat tag. This value is a cross-repository contract with the
# APE-RV jar, which writes one `Log.i` line per exploration step under exactly this
# tag (`ape` design D-6). It is declared once, here, because the failure mode of a
# mismatch between the two sides is an empty capture rather than an error: logcat is
# captured as a live stream under `adb logcat -s <tags>`, a strict device-side
# allowlist, so a heartbeat written under any other tag is discarded at the device
# and no consumer ever learns it was expected (INV-CORE-53).
TAG_APERV_HEARTBEAT = "ApeRvHb"

# Common log messages patterns
LOG_START = "Starting {phase}"
LOG_COMPLETE = "Completed {phase}"
LOG_ERROR = "Error in {phase}: {error}"
LOG_SKIPPED = "Skipped {phase}: {reason}"
