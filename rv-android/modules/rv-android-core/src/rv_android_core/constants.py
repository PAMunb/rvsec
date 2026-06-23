EXTENSION_AJ = ".aj"
EXTENSION_APK = ".apk"
EXTENSION_CSV = ".csv"
EXTENSION_DEX = ".dex"
EXTENSION_JAVA = ".java"
EXTENSION_JAR = ".jar"
EXTENSION_MOP = ".mop"
EXTENSION_RVM = ".rvm"
EXTENSION_XML = ".xml"

EXTENSION_LOGCAT = ".logcat"
EXTENSION_TRACE = ".trace"
EXTENSION_METHODS = ".methods"
EXTENSION_STATIC_ANALYSIS = ".json"

EXECUTION_MEMORY_FILENAME = "execution_memory.json"
RESULTS_FILENAME = "results_analysis.json"

# Export formats
FORMAT_JSON = "JSON"
FORMAT_CSV = "CSV"
FORMAT_XML = "XML"

# COLUMNS (reports, results)

# Quantidade total de activities (no apk)
TOTAL_ACTIVITIES = "total_activities"
# Quantidade total de classes (apenas as classes contidas no pacote definido no manifest)
TOTAL_CLASSES = "total_classes"
# Quantidade total de métodos (apenas os métodos das classes contidas no pacote definido no manifest)
TOTAL_METHODS = "total_methods"
# Quantidade total de métodos alcançáveis que usam jca (utilizados nas especificações ... apenas os métodos das classes contidas no pacote definido no manifest)
TOTAL_METHODS_JCA_REACHABLE = "total_methods_jca_reachable"

# Quantidade de atividades chamadas
CALLED_ACTIVITIES = "called_activities"
# Quantidade de métodos chamados
CALLED_METHODS = "called_methods"
# Quantidade de métodos chamados que usam jca e são alcançáveis
CALLED_METHODS_JCA_REACHABLE = "called_methods_jca_reachable"

# cobertura de atividades: (called_activities * 100) / total_activities
ACTIVITIES_COVERAGE = "activities_coverage"
# cobertura de atividades em relacao ao total de classes: (called_activities * 100) / total_classes
ACTIVITIES_COVERAGE_TOTAL = "activities_coverage_total"
# cobertura de metodos: (called_methods * 100) / total_methods
METHOD_COVERAGE = "method_coverage"
# Coverage of methods reachable from monitored operations:
# (called_methods_mop_reachable * 100) / total_methods_mop_reachable.
# Spec-agnostic — works for both JCA and generic spec sets.
METHODS_MOP_COVERAGE = "methods_mop_reachable_coverage"

ACTIVITIES_COVERAGE_AVG = "activities_coverage_avg"
METHOD_COVERAGE_AVG = "method_coverage_avg"
METHODS_MOP_COVERAGE_AVG = "methods_mop_reachable_coverage_avg"

METHODS_JCA_REACHABLE = "methods_jca_reachable"
METHODS = "methods"
IS_ACTIVITY = "is_activity"
REACHABLE = "reachable"
REACHES_JCA = "reach_jca"
USE_JCA = "use_jca"
CALLED = "called"
SUMMARY = "summary"

RVSEC_ERRORS = "rvsec_errors"
RVSEC_ERRORS_COUNT = "rvsec_errors_count"
RVSEC_METHODS_CALLED = "rvsec_methods_called"

TOOLS = "tools"
TIMEOUTS = "timeouts"
REPETITIONS = "repetitions"

ENV_RVSEC_HOME = "RVSEC_HOME"
ENV_ANDROID_HOME = "ANDROID_HOME"
ENV_TOOLS_DIR = "TOOLS_DIR"
ENV_HUMANOID_URL = "RV_HUMANOID_URL"
ENV_REPETITIONS = "RV_REPETITIONS"
ENV_TIMEOUTS = "RV_TIMEOUTS"
ENV_TOOLS = "RV_TOOLS"
ENV_SKIP_MONITORS = "RV_SKIP_MONITORS"
ENV_SKIP_INSTRUMENT = "RV_SKIP_INSTRUMENT"
ENV_SKIP_STATIC_ANALYSIS = "RV_SKIP_STATIC_ANALYSIS"
ENV_NO_WINDOW = "RV_NO_WINDOW"
ENV_DELAY = "RV_DELAY"
ENV_DEBUG = "RV_DEBUG"
ENV_APKS_DIR = "RV_APKS_DIR"
ENV_SPEC_SET = "RV_SPEC_SET"
ENV_SKIP_EXECUTION = "RV_SKIP_EXECUTION"
ENV_NO_QUARANTINE = "RV_NO_QUARANTINE"
ENV_DEVICE_PORT = "RV_DEVICE_PORT"
ENV_INSTRUMENTATION_VARIANT = "RV_INSTRUMENTATION_VARIANT"
ENV_APKS_FILTER = "RV_APKS_FILTER"
ENV_EXPERIMENT_NAME = "RV_EXPERIMENT_NAME"
ENV_RESUME_DIR = "RV_RESUME_DIR"
ENV_SA_DIR = "RV_SA_DIR"
ENV_SA_TIMEOUT = "RV_SA_TIMEOUT"
ENV_JVM_MEMORY = "RV_JVM_MEMORY"
ENV_PYDANTIC = "RV_PYDANTIC"
ENV_PYDANTIC_STRICT = "RV_PYDANTIC_STRICT"
ENV_PYDANTIC_LOG = "RV_PYDANTIC_LOG"
# Opt-in capture of execution-level diagnostic events (crashes, VerifyError, ANR).
# Default off: when unset, logcat capture stays byte-identical to the RVSEC/RVSEC-COV baseline.
ENV_LOGCAT_DIAGNOSTICS = "RV_LOGCAT_DIAGNOSTICS"

# Variant system constants
DEFAULT_VARIANT_NAME = "default"
VARIANT_SEPARATOR = ":"
TASK_ID_SEPARATOR = "__"


# UI Coverage tracking constants
class UI_COVERAGE_CONSTANTS:
    """Constants for UI coverage tracking and guidance system."""

    # Coverage analysis thresholds
    MIN_ACTIONS_FOR_BALANCE_ANALYSIS = 3
    UNTESTED_PRIORITY_THRESHOLD = 5
    CLICK_OVERUSE_THRESHOLD = 60  # Percentage
    TEXT_UNDERUSE_THRESHOLD = 20  # Percentage

    # Coverage annotation settings
    MAX_COVERAGE_ANNOTATION_LENGTH = 15
    COVERAGE_STATS_CACHE_TTL_SECONDS = 30

    # Element tracking settings
    MAX_ELEMENT_ID_LENGTH = 100
    SCREEN_HASH_LENGTH = 8

    # Action type constants
    ACTION_TYPE_CLICK = "click"
    ACTION_TYPE_SET_TEXT = "set_text"
    ACTION_TYPE_COORDINATE = "coordinate"
    ACTION_TYPE_SCROLL = "scroll"
    ACTION_TYPE_LONG_CLICK = "long_click"

    # Coverage guidance messages
    GUIDANCE_ALL_TESTED = "All elements tested"
    GUIDANCE_SYSTEMATIC_EXPLORATION = (
        "Focus on [UNTESTED] elements for systematic exploration"
    )
    GUIDANCE_COMPLETE_REMAINING = "Complete remaining"
    GUIDANCE_GOOD_BALANCE = "Good distribution of action types"
    GUIDANCE_VARY_ACTIONS = "Vary between click, text input, and coordinate actions"
