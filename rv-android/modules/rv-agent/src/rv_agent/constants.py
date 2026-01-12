"""
RV-Agent Constants

Phase 0 validated parameters and system constants for RV-Agent operation.
These values are based on extensive validation (12,193+ tests) and should not
be modified without scientific validation.
"""


class RVAgentConstants:
    """Constants for RVAgent client operation."""

    # === LLM PARAMETERS (validated 2026-01) ===
    # Optimal for tool calling with SGLang + Qwen3-VL
    DEFAULT_TEMPERATURE = 0.01  # Low temperature for consistent tool calls
    DEFAULT_TOP_P = 0.6         # Controlled sampling
    DEFAULT_TOP_K = 50          # Controlled diversity
    DEFAULT_MAX_TOKENS = 800    # Sufficient for tool call response

    # Model selection (SGLang OpenAI-compatible API)
    DEFAULT_MODEL = "Qwen/Qwen3-VL-4B-Instruct"  # Qwen3-VL 4B with vision+tools

    # === SCREENSHOT OPTIMIZATION (Qwen3-VL specific) ===
    # Dimensions MUST be multiples of 32 for Qwen3-VL
    SCREENSHOT_TARGET_WIDTH = 704   # 22 × 32 (multiple of 32)
    SCREENSHOT_TARGET_HEIGHT = 1248  # 39 × 32 (multiple of 32)
    SCREENSHOT_JPEG_QUALITY = 85    # Balance between size and UI clarity
    SCREENSHOT_FORMAT = "JPEG"      # More efficient than PNG for screenshots
    # Expected tokens: ~878,592 pixels / 1024 = ~858 tokens (optimal for Qwen3-VL)

    # === COORDINATE ENHANCEMENT (CRITICAL) ===
    # Difference between 30% and 100% success rate
    COORDINATE_TOLERANCE = 50  # 50px tolerance validated scientifically
    COORDINATE_FORMAT = "at position ({x}, {y})"  # MANDATORY format for 100% success

    # === EXECUTION PARAMETERS ===
    DEFAULT_TIMEOUT = 300  # 5 minutes default execution timeout
    DEFAULT_MAX_ITERATIONS = 50  # Maximum test iterations before stopping
    ITERATION_DELAY = 2.0  # Delay between iterations in seconds
    DEFAULT_DEVICE_ID = "emulator-5554"

    # === MEMORY CONFIGURATION ===
    MAX_SHORT_TERM_ITERATIONS = 10  # Screen-scoped memory limit
    MAX_LONG_TERM_STATES = 1000     # Cross-session memory limit

    # === UI COVERAGE THRESHOLDS ===
    UNTESTED_PRIORITY = 100    # Highest priority for untested elements
    WELL_TESTED_THRESHOLD = 3  # Element considered well-tested after 3 interactions

    # === DEBUG LOGGING ===
    DEBUG_PREFIX = "[RVAGENT_DEBUG]"  # Prefix for debug logs (removable)
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # === VALIDATION THRESHOLDS (Phase 0 based) ===
    MIN_SUCCESS_RATE = 0.75    # Minimum 75% success rate for approval
    MIN_DISCOVERY_RATE = 0.6   # Minimum 60% discovery rate for exploration efficiency
    MAX_HALLUCINATION_RATE = 0.15  # Maximum 15% validation failures

    # === FILE NAMING CONVENTIONS ===
    RESULTS_FILE_EXTENSION = ".json"
    METRICS_FILE_SUFFIX = "_metrics"
    DEBUG_LOG_SUFFIX = "_debug.log"

    # === API ENDPOINTS (for future server integration) ===
    DEFAULT_SERVER_PORT = 8080
    METRICS_ENDPOINT = "/metrics"
    STATUS_ENDPOINT = "/status"

    # === COORDINATE ENHANCEMENT CRITICAL CONSTANTS ===
    # These values are MANDATORY for coordinate enhancement success
    BOUNDS_PATTERN = r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]'  # XML bounds parsing pattern
    CLICKABLE_ATTRIBUTE = 'clickable'
    CLICKABLE_VALUE = 'true'

    # Element description format components (validated in Phase 0)
    TEXT_FORMAT = '"{text}"'
    CONTENT_DESC_FORMAT = 'desc:"{content_desc}"'
    RESOURCE_ID_FORMAT = 'id:{resource_id}'
    DEFAULT_ELEMENT_DESC = 'Interactive element'

    # === QUALITY METRICS CONSTANTS ===
    EXECUTION_STABILITY_TARGET = 1.0  # 100% execution stability (no crashes)
    LLM_RESPONSE_TIME_TARGET = 3.0    # Maximum 3s average response time
    FORMAT_COMPLIANCE_TARGET = 0.95   # 95% JSON format compliance
    REASONING_QUALITY_TARGET = 0.90   # 90% coherent reasoning explanations