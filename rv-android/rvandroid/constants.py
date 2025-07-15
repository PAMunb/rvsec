EXTENSION_AJ = ".aj"
EXTENSION_APK = ".apk"
EXTENSION_CSV = ".csv"
EXTENSION_DEX = ".dex"
EXTENSION_JAVA = ".java"
EXTENSION_JAR = ".jar"
EXTENSION_MOP = ".mop"
EXTENSION_RVM = ".rvm"

EXTENSION_LOGCAT = ".logcat"
EXTENSION_TRACE = ".trace"
EXTENSION_METHODS = ".methods"
EXTENSION_REACH = ".reach"
EXTENSION_GESDA = ".gesda"
EXTENSION_GATOR = ".wtg"

EXECUTION_MEMORY_FILENAME = "execution_memory.json"
RESULTS_FILENAME = "results_analysis.json"

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
# cobertura do metodos alcancaveis que usam MOP: (called_methods_jca_reachable * 100) / total_methods_jca_reachable
METHODS_JCA_COVERAGE = "methods_jca_reachable_coverage"

ACTIVITIES_COVERAGE_AVG = "activities_coverage_avg"
METHOD_COVERAGE_AVG = "method_coverage_avg"
METHODS_JCA_COVERAGE_AVG = "methods_jca_reachable_coverage_avg"

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

ENV_HUMANOID_URL = "RV_HUMANOID_URL"
ENV_MEMORY_FILE = "RV_MEMORY_FILE"
ENV_REPETITIONS = "RV_REPETITIONS"
ENV_TIMEOUTS = "RV_TIMEOUTS"
ENV_TOOLS = "RV_TOOLS"
ENV_SKIP_MONITORS = "RV_SKIP_MONITORS"
ENV_SKIP_INSTRUMENT = "RV_SKIP_INSTRUMENT"
ENV_SKIP_STATIC_ANALYSIS = "RV_SKIP_STATIC_ANALYSIS"
ENV_SKIP_EXPERIMENT = "RV_SKIP_EXPERIMENT"
ENV_NO_WINDOW = "RV_NO_WINDOW"
ENV_DELAY = "RV_DELAY"
ENV_DEBUG = "RV_DEBUG"
ENV_JCA_SPEC = "RV_JCA_SPEC"
ENV_RT_JAR = "RV_RT_JAR"
ENV_RVANDROID_URL = "RV_RVANDROID_URL"
