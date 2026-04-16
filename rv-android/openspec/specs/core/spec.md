# Specification: Core Infrastructure

## Purpose

The rv-android-core module is the foundational infrastructure layer for the entire RV-Android framework. It provides the shared abstractions, domain models, communication primitives, and utility services that every other module depends on. rv-android-core has zero internal dependencies -- it is the root of the dependency graph -- and all 13 remaining modules import from it.

The module solves four interconnected problems:

1. **Consistent error management**: The framework spans multiple execution contexts -- emulator management, tool execution, static analysis, LLM inference -- each with distinct failure modes. The ErrorHandler provides centralized error classification with 30+ type-specific handlers, a decorator pattern (`@ErrorHandler.handle_errors`) for automatic error capture, and a callback system for higher-level modules to react to errors without creating circular dependencies.

2. **Validated domain models**: Configuration objects, task state, coverage data, and log entries all require structural validation, serialization, and backwards-compatible construction. BaseValidatedModel (Pydantic v2) with the `@validated_model` decorator provides environment-aware validation (controlled by `RV_PYDANTIC` env var), positional-argument compatibility, and consistent serialization across all models.

3. **System command execution**: The framework invokes external tools (adb, dex2jar, ajc, d8, jarsigner, JavaMOP, RV-Monitor, GATOR, GESDA, REACH) through a validated Command model with timeout enforcement, process tree management, and a circuit breaker pattern to prevent cascading failures from repeatedly failing commands.

4. **Observability**: Centralized logging (LoggingManager), performance metrics (PerformanceMonitor), and structured context injection (ContextAdapter) provide consistent observability across all modules.

### Component Architecture

```
rv-android-core
|
+-- util/
|   +-- error/
|   |   |-- error_handler.py   ErrorHandler singleton with 30+ handlers
|   |   +-- exceptions.py      Exception hierarchy (~40 classes)
|   +-- validation/
|   |   |-- base.py            BaseValidatedModel (Pydantic v2)
|   |   |-- decorators.py      @validated_model positional-arg support
|   |   +-- config.py          ValidationConfig (RV_PYDANTIC env var)
|   +-- logging/
|   |   |-- manager.py         LoggingManager singleton
|   |   |-- context_adapter.py ContextAdapter with_context()
|   |   |-- formatters.py      StructuredFormatter, JsonFormatter
|   |   +-- constants.py       Context keys, log patterns
|   +-- performance/
|   |   |-- performance_monitor.py  PerformanceMonitor singleton
|   |   +-- configuration.py       PerformanceMonitorConfig
|   +-- android/
|   |   |-- android.py              ADB operations
|   |   |-- emulator_manager.py     Emulator lifecycle
|   |   |-- logcat_manager.py       Logcat capture
|   |   |-- package_detector.py     Code package detection
|   |   +-- signature_normalizer.py Inner class notation
|   +-- decorators.py
|   +-- diagnostics.py
|   +-- jar_resolver.py
|   +-- json_helpers.py
|   +-- utils.py
|
+-- domain/
|   |-- task.py       Task, TaskConfiguration, TaskResult, TaskState, ToolConfig
|   |-- app.py        App (APK metadata via Androguard)
|   |-- static.py     StaticAnalysisData (GESDA + GATOR + REACH)
|   |-- coverage.py   LogcatRepository, CoverageMetrics, ClassCoverageData, MethodCoverageData
|   |-- log.py        RvCoverageLog, RvErrorLog
|   |-- classes.py    Classes model
|   |-- window.py     Windows model
|   |-- wtg.py        WindowTransitionGraph
|   |-- dynamic_wtg.py DynamicWindowTransitionGraph
|   +-- widget.py     Widget models
|
+-- commands/
|   |-- command.py           Command (validated, timeout, process tree kill)
|   |-- command_result.py    CommandResult (code, stdout, stderr)
|   |-- circuit_breaker.py   CommandCircuitBreaker (CLOSED/OPEN/HALF_OPEN)
|   |-- command_exception.py
|   +-- command_not_found_error.py
|
+-- tools/
|   |-- abstract_tool.py  AbstractTool (template method pattern)
|   +-- tool_spec.py      ToolSpec model
|
+-- analysis/
|   +-- base_analyzer.py  BaseAnalyzer abstract class
|
+-- constants.py           File extensions, column names, env var names
+-- __init__.py            Module exports
```

### Key Data Models

```
Task:                            # NOT a Pydantic model (plain class)
  id: str                        # UUID string
  config: TaskConfiguration      # Pydantic model
  result: TaskResult             # Pydantic model
  app: Optional[App]             # Set at runtime
  repository: LogcatRepository   # Coverage/error data store
  static_data: Any               # StaticAnalysisData reference

TaskConfiguration(BaseValidatedModel):
  apk_name: str                  # APK filename
  repetition: int                # Repetition number (1-based)
  timeout: int                   # Seconds for tool execution
  tool_config: ToolConfig        # Tool name + variant + params
  no_window: bool                # Headless mode flag
  device_id: str                 # Default "emulator-5554"

ToolConfig(BaseValidatedModel):
  name: str                      # e.g. "droidbot", "rvagent"
  variant: str                   # e.g. "dfs_greedy", "default"
  parameters: Dict               # Parameter overrides

App(BaseValidatedModel):
  app_path: str                  # Absolute path to APK file
  # computed fields:
  path: str                      # os.path.abspath(app_path)
  name: str                      # os.path.basename(app_path)
  package_name: str              # From AndroidManifest.xml (for device ops)
  code_package: str              # Detected via PackageDetector (for static analysis)
  sdk_target: int                # Target SDK version
  permissions: List[str]         # Requested permissions
  min_api: int                   # Minimum API level

Command(BaseValidatedModel):
  command: str                   # Executable name (validated non-empty)
  args: List[str]                # Command arguments
  timeout: Optional[float]       # Seconds (None = no timeout)

CommandResult(BaseValidatedModel):
  code: int                      # Exit code [-255, 255]
  stdout: Optional[bytes]        # Raw bytes from subprocess
  stderr: Optional[bytes]        # Raw bytes from subprocess

RvCoverageLog(BaseValidatedModel):
  clazz: str                     # Fully qualified class name
  method: str                    # Method name
  params: str                    # Semicolon-separated parameters
  signature: str                 # Full signature
  time_occurred: datetime        # When method was called
  time_since_task_start: int     # Seconds since tool execution started

RvErrorLog(BaseValidatedModel):
  spec: str                      # Monitor spec name (e.g. "SSLContextSpec")
  error_type: str                # Violation classification
  class_full_name: str           # Where violation occurred
  method: str                    # Method name
  source: str                    # Source file or monitor location
  message: str                   # Violation description
  time_since_task_start: int     # Seconds since tool execution started
  unique_msg: str (computed)     # Deduplication key
```

### Relationships with Other Domains

**Consumed by all modules**: Every module in the framework imports from rv-android-core. The primary consumers are:

- **rv-platform**: Uses Task, TaskConfiguration, TaskResult, ErrorHandler, Command, LogcatRepository, and PerformanceMonitor.
- **rv-experiment**: Uses ErrorHandler, Command, and all domain models for configuration.
- **rv-agent**: Uses AbstractTool (via rvagent-tool wrapper), ErrorHandler, LoggingManager, PerformanceMonitor, ScreenDescription models, StaticAnalysisData, and App.
- **rv-coverage**: Uses RvCoverageLog, RvErrorLog, LogcatRepository, CoverageMetrics.
- **rv-tools**: Uses AbstractTool as base class for all 8 built-in tools, ToolSpec, Command, CommandResult, and ErrorHandler.
- **rv-static-analysis**: Uses Command for running GATOR/GESDA/REACH, StaticAnalysisData, Classes, Windows, WindowTransitionGraph.
- **rv-instrumentation**: Uses Command for dex2jar/ajc/d8/jarsigner execution, ErrorHandler.
- **rv-monitor-generator**: Uses Command for JavaMOP/RV-Monitor execution, ErrorHandler.
- **rv-screen-parser**: Uses BaseValidatedModel for UI models, ErrorHandler.
- **rv-uiautomator**: Uses Command for ADB operations, ErrorHandler, PerformanceMonitor.

**Produced by rv-android-core**: Domain models (Task, App, StaticAnalysisData, coverage models), infrastructure services (ErrorHandler, LoggingManager, PerformanceMonitor), and the AbstractTool contract.

**External dependencies**: pydantic ^2.9.0, androguard 3.4.0a1, psutil ^7.0.0, networkx ^3.5.

## Data Contracts

### Input

- `RV_PYDANTIC: str` -- Environment variable controlling validation mode (`"true"` enables full validation, `"false"` or absent disables it). Source: system environment.
- `RV_PYDANTIC_STRICT: str` -- Environment variable for strict validation mode. Source: system environment.
- `RV_PYDANTIC_LOG: str` -- Environment variable for validation event logging. Source: system environment.
- `app_path: str` -- Absolute path to an Android APK file. Source: rv-experiment CLI or rv-platform task generation.
- `command: str` -- System command name to execute. Source: all modules that invoke external tools.

### Output

- `CommandResult(code, stdout, stderr)` -- Result of system command execution. Destination: calling module.
- `App` instance -- Android APK metadata extracted via Androguard. Destination: rv-platform tasks, rv-agent.
- `Task` instance -- Task with configuration, result, and coverage repository. Destination: rv-platform executor.
- `CoverageMetrics` -- Calculated coverage percentages. Destination: rv-platform result processor.
- `Metric` / `TimingMetric` -- Performance measurements. Destination: PerformanceMonitor subscribers.

### Side-Effects

- **Process creation**: Command.invoke() spawns OS processes via `subprocess.Popen`. Command.invoke_as_deamon() and invoke_as_process() create background processes.
- **Process termination**: `kill_process_tree()` recursively kills process trees via `psutil` and `os.kill(SIGKILL)`.
- **File system**: Task.initialize() creates results directories via `os.makedirs()`. LoggingManager.setup_file_logging() creates log files.
- **APK analysis**: App model_post_init() loads APK via Androguard (I/O operation reading APK file).

### Error

- `ConfigurationError` -- Invalid configuration or APK file not found/invalid.
- `CommandValidationError` -- Empty command string, invalid timeout, or invalid arguments.
- `RVCommandTimeoutError` -- Command execution exceeded timeout. Contains `timeout_seconds` and `command`.
- `CircuitBreakerOpenError` -- Command blocked by circuit breaker after repeated failures. Contains `command_signature` and `failure_count`.
- `RVAndroidError` -- Base exception for all framework-specific errors. Contains `message` and `cause`.
- `CommandNotFoundError` -- OS command not found (OSError wrapper).
- Pydantic `ValidationError` -- Raised by BaseValidatedModel when field validation fails (not caught by ErrorHandler).

## Invariants

- **INV-CORE-06**: The ErrorHandler MUST be a thread-safe singleton using double-checked locking. Concurrent calls to `ErrorHandler.get_instance()` MUST return the same instance.

- **INV-CORE-07**: The ErrorHandler MUST register handlers for all exception types in the hierarchy at initialization time. Handler lookup MUST use exact type matching (`type(e) == error_type`), not isinstance matching, to ensure the most specific handler is invoked.

- **INV-CORE-08**: The `@ErrorHandler.handle_errors` decorator MUST catch all exceptions. When `reraise=False` (default), handled exceptions MUST be suppressed (return None). When `reraise=True`, exceptions MUST be re-raised regardless of handler outcome.

- **INV-CORE-09**: Validation errors (ValueError, ConfigurationError, RVValidationError, Pydantic ValidationError) MUST NOT be suppressed by the generic catch-all handler (`_handle_generic_exception`). They MUST propagate to the caller.

- **INV-CORE-10**: BaseValidatedModel MUST forbid extra fields (`extra='forbid'`), strip whitespace from strings (`str_strip_whitespace=True`), and validate on assignment (`validate_assignment=True`).

- **INV-CORE-11**: The `@validated_model` decorator MUST map positional arguments to field names in the order specified by `positional_fields`. If a field is specified both positionally and as a keyword argument, it MUST raise `ValueError`.

- **INV-CORE-12**: ValidationConfig MUST read `RV_PYDANTIC` from the environment at initialization. The value `"true"`, `"1"`, `"yes"`, or `"on"` (case-insensitive) MUST enable validation. All other values MUST disable validation.

- **INV-CORE-13**: Command MUST validate that the `command` field is a non-empty string. An empty or whitespace-only command MUST raise `CommandValidationError`.

- **INV-CORE-14**: Command.invoke() MUST raise `RVCommandTimeoutError` when the subprocess exceeds the configured timeout. Before raising, it MUST call `kill_process_tree()` to terminate the process and all its children.

- **INV-CORE-15**: CommandResult.code MUST be in the range [-255, 255]. `is_success()` MUST return True if and only if `code == 0`. `is_failure()` MUST return True if and only if `code != 0`.

- **INV-CORE-16**: The CommandCircuitBreaker MUST track failures per command signature (SHA-256 hash of command + args). When failures reach `failure_threshold` (default: 3), the circuit MUST transition from CLOSED to OPEN. In OPEN state, `is_execution_allowed()` MUST raise `CircuitBreakerOpenError`.

- **INV-CORE-17**: App MUST validate that `app_path` is non-empty and points to an existing `.apk` file. If the file does not exist or is not a valid APK, it MUST raise `ConfigurationError`.

- **INV-CORE-18**: App.package_name MUST return the manifest package name (from `APK.get_package()`). App.code_package MUST return the implementation package detected by PackageDetector. These values MAY differ (observed in ~27.5% of APKs).

- **INV-CORE-19**: Task.id MUST be a UUID string. If no `task_id` is provided to the constructor, a new UUID MUST be generated via `uuid.uuid4()`.

- **INV-CORE-20**: TaskState transitions MUST follow the lifecycle: CREATED -> INITIALIZING -> READY -> RUNNING -> COMPLETED|ERROR|CANCELED. Each transition MUST be recorded in `TaskResult.state_transitions`.

- **INV-CORE-21**: LoggingManager MUST be a thread-safe singleton. `get_logger()` MUST cache logger instances by name + context and return `ContextAdapter` instances (not raw loggers).

- **INV-CORE-22**: PerformanceMonitor MUST be a thread-safe singleton. When `_config` is None or `_config.enabled` is True, metrics MUST be collected. When disabled, `measure_time()` MUST yield without overhead and `record_metric()` MUST be a no-op.

- **INV-CORE-23**: AbstractTool.execute() MUST convert `RVCommandTimeoutError` to `RVToolTimeoutError`. Tool timeouts are considered expected behavior and MUST NOT be treated as failures.

- **INV-CORE-24**: LogcatRepository.register_method_call() MUST only register calls to methods that exist in the static analysis data (classes dictionary). Calls to unknown classes or methods MUST be silently ignored with a debug log.

- **INV-CORE-25**: RvErrorLog.unique_msg MUST be computed as `"{class_full_name}:::{method}:::{spec}:::{error_type}:::{message}"`. Two RvErrorLog instances with the same unique_msg MUST be considered equal.
## Requirements
### Requirement: Error Handling with Recovery Strategies (FR34, NFR04)

The rv-android-core module MUST provide centralized error handling through the ErrorHandler singleton. The ErrorHandler serves as the framework's unified error management facility, providing consistent error classification, logging, tracking, and optional recovery. It uses a registry-based approach where each exception type has a dedicated handler.

The ErrorHandler MUST register 27+ type-specific handlers at initialization covering the entire exception hierarchy: RVTaskError, RVToolError (and subclasses: ToolNotFoundError, ToolRegistrationError, ToolVariantError, PluginError, RVToolTimeoutError, RVToolExecutionError), RVExperimentError, RVParsingError, RVPromptError, RVLLMError (and subclasses: RVLLMConnectionError, RVLLMModelError, RVLLMProviderError, RVLLMConfigurationError, RVLLMTemplateError), RVValidationError (and subclasses: CommandValidationError, LogcatValidationError), RVCommandTimeoutError, JarNotFoundError, CircuitBreakerOpenError, FileNotFoundError, and generic fallbacks (RVAndroidError, Exception).

Handler lookup MUST use exact type matching to ensure the most specific handler is selected. The `@ErrorHandler.handle_errors(component, phase, reraise)` decorator MUST provide Spring-like automatic error management for decorated methods.

When `reraise=True`, the decorator MUST annotate the exception with `_error_phase` set to the decorator's `phase` parameter before re-raising. If the exception already has an `_error_phase` attribute (set by an inner decorator), the outer decorator MUST NOT overwrite it. This preserves the most specific phase from nested decorator chains.

The ErrorHandler MUST support a callback system (`register_error_callback` / `unregister_error_callback`) for higher-level modules to react to errors.

#### Scenario: Decorator with reraise=False suppresses handled exception

- **WHEN** a method decorated with `@ErrorHandler.handle_errors(component="Test", phase="exec", reraise=False)` raises `RVToolTimeoutError`
- **THEN** the error MUST be logged and classified by `_handle_tool_timeout_error`
- **AND** the decorated method MUST return None (exception suppressed)
- **AND** the error MUST be recorded in `_error_counts` and `_error_history`

#### Scenario: Decorator with reraise=True propagates exception

- **WHEN** a method decorated with `@ErrorHandler.handle_errors(component="Test", reraise=True)` raises `RVToolExecutionError`
- **THEN** the error MUST be logged and handled by `_handle_tool_execution_error`
- **AND** the exception MUST be re-raised to the caller
- **AND** the caller MUST receive the original exception

#### Scenario: Decorator with reraise=True annotates exception with phase

- **WHEN** a method decorated with `@ErrorHandler.handle_errors(component="RVInstrumentation", phase="apk_signing", reraise=True)` raises `CommandException`
- **THEN** the exception MUST have attribute `_error_phase` set to `"apk_signing"` before re-raising
- **AND** the caller MUST receive the exception with `_error_phase == "apk_signing"`

#### Scenario: Inner decorator phase preserved through nested chain

- **WHEN** an inner method decorated with `@ErrorHandler.handle_errors(phase="apk_signing", reraise=True)` raises `CommandException`
- **AND** the outer method is decorated with `@ErrorHandler.handle_errors(phase="apk_creation", reraise=True)`
- **THEN** the inner decorator MUST set `_error_phase = "apk_signing"` on the exception
- **AND** the outer decorator MUST NOT overwrite `_error_phase` (because `hasattr(e, '_error_phase')` is True)
- **AND** the final caller MUST receive the exception with `_error_phase == "apk_signing"`

#### Scenario: Validation errors are not suppressed by catch-all

- **WHEN** a `ValueError` or `RVValidationError` is passed to `_handle_generic_exception`
- **THEN** the handler MUST return False (not handled)
- **AND** the error MUST propagate to the caller

#### Scenario: Tool timeout treated as expected behavior

- **WHEN** `_handle_tool_timeout_error` receives an `RVToolTimeoutError` with `tool_name="monkey"` and `timeout_seconds=300`
- **THEN** the handler MUST log at INFO level (not ERROR) with the tool name and timeout duration
- **AND** the handler MUST return True (successfully handled)

#### Scenario: Error context manager

- **WHEN** code executes within `with error_handler.error_context(component="TaskExecutor", phase="setup"):` and raises an exception
- **THEN** the exception MUST be passed to `_handle_error_internal` with context `{"component": "TaskExecutor", "phase": "setup"}`
- **AND** if the error is handled, it MUST be suppressed
- **AND** if the error is not handled, it MUST be re-raised

#### Scenario: Error statistics tracking

- **WHEN** three `RVToolTimeoutError` instances and two `ConfigurationError` instances are handled
- **THEN** `get_error_statistics()` MUST return `error_counts` with `{"RVToolTimeoutError": 3, "ConfigurationError": 2}`
- **AND** `recent_errors` MUST contain the 5 most recent error entries with timestamps

### Requirement: Pydantic Validation (FR35, NFR03, NFR05)

The rv-android-core module MUST provide BaseValidatedModel as the foundation for all validated domain models. BaseValidatedModel inherits from Pydantic v2 BaseModel and enforces consistent validation configuration across the framework.

Validation behavior MUST be controlled by the `RV_PYDANTIC` environment variable. When `RV_PYDANTIC=true`, full Pydantic validation is active (development mode). When `RV_PYDANTIC=false` or unset, validation still occurs at the Pydantic level (model_config settings apply) but logging and strict mode checks are suppressed for performance.

The `@validated_model(positional_fields)` decorator MUST enable Pydantic models to accept both positional and named arguments, maintaining backwards compatibility with pre-Pydantic constructors. The decorator MUST map positional arguments to field names in the declared order.

All configuration classes (PlatformConfig, ExperimentConfig, RVAgentConfig, and others in downstream modules) MUST inherit from BaseValidatedModel.

#### Scenario: Positional and named argument equivalence

- **WHEN** `CommandResult(0, b"output", b"error")` and `CommandResult(code=0, stdout=b"output", stderr=b"error")` are both constructed
- **THEN** both instances MUST have identical field values: `code=0`, `stdout=b"output"`, `stderr=b"error"`
- **AND** `instance1 == instance2` MUST return True

#### Scenario: Extra fields are rejected

- **WHEN** a BaseValidatedModel subclass is constructed with an unexpected field (e.g., `CommandResult(code=0, stdout=b"", stderr=b"", unexpected_field="value")`)
- **THEN** Pydantic MUST raise a ValidationError because `extra='forbid'` is set in model_config
- **AND** the error message MUST indicate the unexpected field

#### Scenario: Positional-keyword conflict detection

- **WHEN** `CommandResult(0, b"output", code=1)` is constructed (field "code" specified both positionally and as keyword)
- **THEN** a `ValueError` MUST be raised with a message indicating the conflict for field "code"

#### Scenario: Validation config from environment

- **WHEN** `RV_PYDANTIC` is set to `"true"` in the environment
- **THEN** `ValidationConfig.get_instance().enabled` MUST return True
- **AND** when `RV_PYDANTIC` is set to `"false"`, `enabled` MUST return False
- **AND** when `RV_PYDANTIC` is not set, `enabled` MUST return False (default)

#### Scenario: String whitespace stripping

- **WHEN** a BaseValidatedModel subclass has a `name: str` field and is constructed with `name="  padded  "`
- **THEN** the stored value MUST be `"padded"` (whitespace stripped)
- **AND** this behavior is enforced by `str_strip_whitespace=True` in model_config

### Requirement: Centralized Logging (FR36, NFR06)

The rv-android-core module MUST provide centralized logging through LoggingManager. The LoggingManager is a thread-safe singleton that provides consistent logging configuration, context injection, and structured formatting across all modules.

LoggingManager MUST support context-aware logging through ContextAdapter, which wraps standard Python loggers with automatic context injection. Context includes component name, task ID, app name, tool name, and other operational metadata. The `with_context()` context manager MUST enable temporary context additions for scoped operations.

LoggingManager MUST support both console and file output with independent configuration (level, format, context display). StructuredFormatter MUST append context data to log messages. JsonFormatter MUST produce structured JSON log output.

Logging constants MUST define standard context keys: `CONTEXT_TASK_ID`, `CONTEXT_APP_NAME`, `CONTEXT_TOOL_NAME`, `CONTEXT_COMPONENT`, `CONTEXT_PHASE`. Standard log patterns MUST be provided: `LOG_START`, `LOG_COMPLETE`, `LOG_ERROR`, `LOG_SKIPPED`.

#### Scenario: Logger caching by name and context

- **WHEN** `get_logger("module.component", {"component": "MyComponent"})` is called twice
- **THEN** the same ContextAdapter instance MUST be returned both times (cached)
- **AND** the logger MUST be stored in `logger_cache` with a key derived from name and sorted context items

#### Scenario: Context adapter with scoped context

- **WHEN** `logger.with_context(task_id="abc")` is used as a context manager and a log message is emitted inside the block
- **THEN** the log record MUST include `task_id="abc"` in its context
- **AND** after the context manager exits, subsequent log messages MUST NOT include `task_id="abc"`

#### Scenario: Custom log levels

- **WHEN** the logging constants module is imported
- **THEN** custom log levels MUST be registered: EXPERIMENT_START (25), EXPERIMENT_END (26), TASK_START (27), TASK_END (28)
- **AND** `logging.getLevelName(25)` MUST return `"EXPERIMENT_START"`

### Requirement: Performance Monitoring (FR37, NFR06)

The rv-android-core module MUST provide performance metrics collection through PerformanceMonitor. The PerformanceMonitor is a thread-safe singleton that tracks timing and custom metrics across the framework.

PerformanceMonitor MUST support timing measurement via the `measure_time()` context manager, which records start time, end time, and duration as TimingMetric objects. It MUST support custom metric recording via `record_metric()`.

PerformanceMonitor MUST support a subscriber pattern where callbacks are invoked when metrics are recorded. Subscribing to `"*"` MUST receive all metrics. Subscribing to a specific metric name MUST receive only matching metrics.

PerformanceMonitor MUST be configurable via PerformanceMonitorConfig. When `enabled=False`, `measure_time()` MUST yield without overhead and `record_metric()` MUST be a no-op. When `max_samples > 0`, the metrics list MUST not exceed that limit (oldest metrics are evicted).

#### Scenario: Timing measurement with context

- **WHEN** `with monitor.measure_time("tool_execution", {"tool": "monkey"}):` wraps a block that takes approximately 2 seconds
- **THEN** a TimingMetric MUST be recorded with `name="tool_execution"`, `value` approximately 2.0, `unit="s"`, and `context={"tool": "monkey"}`
- **AND** `start_time` and `end_time` MUST be valid Unix timestamps with `end_time - start_time` approximately equal to `value`

#### Scenario: Disabled monitoring has zero overhead

- **WHEN** PerformanceMonitor is configured with `PerformanceMonitorConfig(enabled=False)` and `measure_time()` is used
- **THEN** the context manager MUST yield immediately without recording any metric
- **AND** `len(monitor.metrics)` MUST remain unchanged

#### Scenario: Max samples eviction

- **WHEN** PerformanceMonitor is configured with `max_samples=5` and 7 metrics are recorded
- **THEN** `len(monitor.metrics)` MUST be 5
- **AND** the 2 oldest metrics MUST have been evicted
- **AND** the 5 most recent metrics MUST be retained in order

#### Scenario: Statistical aggregation

- **WHEN** three metrics named "latency" are recorded with values 1.0, 2.0, and 3.0
- **THEN** `get_metrics_stats("latency")` MUST return `{"count": 3, "min": 1.0, "max": 3.0, "avg": 2.0, "median": 2.0}`

### Requirement: System Command Execution (implied by FR34-FR37 infrastructure)

The rv-android-core module MUST provide validated system command execution through the Command model. Command is a Pydantic model that validates command name, arguments, and timeout before execution. The Command class is used by all modules that invoke external tools (adb, dex2jar, ajc, d8, jarsigner, JavaMOP, RV-Monitor, GATOR, GESDA, REACH).

Command MUST support three execution modes: `invoke()` (synchronous, blocking), `invoke_as_deamon()` (background process, non-blocking), and `invoke_as_process()` (background with process group for proper cleanup).

Command MUST enforce timeout by calling `subprocess.communicate(timeout=self.timeout)`. On timeout, it MUST kill the process tree via `kill_process_tree()` using psutil and then raise `RVCommandTimeoutError`.

The CommandCircuitBreaker MUST provide resilience against repeatedly failing commands. It tracks failures per command signature (SHA-256 hash) and transitions through three states: CLOSED (normal), OPEN (blocked), HALF_OPEN (testing recovery).

#### Scenario: Successful command execution

- **WHEN** `Command(command="echo", args=["hello"]).invoke()` is executed
- **THEN** a CommandResult MUST be returned with `code=0` and `stdout` containing `b"hello"`
- **AND** `result.is_success()` MUST return True
- **AND** `result.is_failure()` MUST return False

#### Scenario: Command timeout with process tree kill

- **WHEN** `Command(command="sleep", args=["60"], timeout=1.0).invoke()` is executed
- **THEN** after approximately 1 second, `kill_process_tree()` MUST be called with the process PID
- **AND** `RVCommandTimeoutError` MUST be raised with `timeout_seconds=1.0` and `command="sleep 60"`

#### Scenario: Empty command validation

- **WHEN** `Command(command="", args=[])` is constructed
- **THEN** `CommandValidationError` MUST be raised with `field_name="command"`
- **AND** the error message MUST indicate that the command must be a non-empty string

#### Scenario: Circuit breaker opens after threshold failures

- **WHEN** a CommandCircuitBreaker with `failure_threshold=3` records 3 failures for the same command
- **THEN** the circuit state for that command MUST be OPEN
- **AND** calling `is_execution_allowed()` for that command MUST raise `CircuitBreakerOpenError`

#### Scenario: Circuit breaker recovery via half-open

- **WHEN** a circuit breaker is in OPEN state and `retry_count=1` attempts are made
- **THEN** the circuit MUST transition to HALF_OPEN state
- **AND** `is_execution_allowed()` MUST return True (allowing a test execution)
- **AND** if the test execution succeeds (via `record_success()`), the circuit MUST transition to CLOSED

### Requirement: AbstractTool Contract (implied by FR34-FR37 infrastructure, FR18-FR20, NFR01, NFR02)

The rv-android-core module MUST define the AbstractTool base class that establishes the contract for all testing tools in the framework. AbstractTool implements the template method pattern: `execute()` is the template method that delegates to `execute_tool_specific_logic()` (the abstract extension point).

AbstractTool MUST define four abstract methods that subclasses MUST implement: `get_variants()` (returns variant configurations), `get_tool_spec()` (returns ToolSpec for registration), `configure()` (applies variant parameters), and `execute_tool_specific_logic()` (tool-specific testing logic).

AbstractTool.execute() MUST handle `RVCommandTimeoutError` by converting it to `RVToolTimeoutError` and MUST call `kill_related_processes()` for cleanup on successful completion.

AbstractTool MUST integrate the CommandCircuitBreaker via `_execute_and_check_command()`, which provides circuit breaker protection for all command executions within tools.

#### Scenario: Timeout conversion in execute()

- **WHEN** `execute_tool_specific_logic()` raises `RVCommandTimeoutError(message="timed out", timeout_seconds=300, command="adb shell monkey")`
- **THEN** AbstractTool.execute() MUST raise `RVToolTimeoutError` with `tool_name` set to the tool's name and `timeout_seconds=300`
- **AND** the original `RVCommandTimeoutError` MUST be set as the `cause` of the `RVToolTimeoutError`

#### Scenario: Circuit breaker integration in command execution

- **WHEN** `_execute_and_check_command()` is called and the circuit breaker is OPEN for that command
- **THEN** `CircuitBreakerOpenError` MUST be raised without executing the command
- **AND** no subprocess MUST be created

#### Scenario: Process cleanup after execution

- **WHEN** `execute_tool_specific_logic()` completes successfully
- **THEN** `kill_related_processes(self.process_pattern)` MUST be called
- **AND** any processes matching the pattern on the device MUST be terminated via ADB

### Requirement: Domain Models (FR33)

The core domain layer MUST provide validated data models used across all modules. These models use `BaseValidatedModel` (with `@validated_model` decorator) for field validation when `RV_PYDANTIC=true`.

The central data models are:

```
TaskConfiguration(BaseValidatedModel):
  apk_name: str                  # APK filename
  repetition: int                # Repetition number (1-based)
  timeout: int                   # Seconds for tool execution
  tool_config: ToolConfig        # Tool name + variant + params
  no_window: bool                # Headless mode flag
  device_id: str                 # Default "emulator-5554"

ToolConfig(BaseValidatedModel):
  name: str                      # e.g. "droidbot", "rvagent"
  variant: str                   # e.g. "dfs_greedy", "default"
  parameters: Dict               # Parameter overrides

App(BaseValidatedModel):
  app_path: str                  # Absolute path to APK file
  # computed fields:
  path: str                      # os.path.abspath(app_path)
  name: str                      # os.path.basename(app_path)
  package_name: str              # From AndroidManifest.xml (for device ops)
  code_package: str              # Detected via PackageDetector (for static analysis)
  sdk_target: int                # Target SDK version
  permissions: List[str]         # Requested permissions
  min_api: int                   # Minimum API level

Command(BaseValidatedModel):
  command: str                   # Executable name (validated non-empty)
  args: List[str]                # Command arguments
  timeout: Optional[float]       # Seconds (None = no timeout)
```

ToolConfig is the single source of truth for tool configuration across all modules. It represents exactly one (tool, variant, parameters) combination. For experiments with multiple variants of the same tool, multiple ToolConfig instances are created — one per variant. All modules import ToolConfig from rv-android-core; no other module defines its own ToolConfig class.

ToolConfig provides `from_dict()` for deserialization from JSON. It accepts only the current field names (`name`, `variant`, `parameters`). Per P3 (No Backward Compatibility), old `tasks.json` files using previous field names (`tool_name`, `additional_params`) are not supported — experiments must be re-run.

#### Scenario: ToolConfig creation with unified field names

- **WHEN** `ToolConfig(name="droidbot", variant="dfs_greedy", parameters={"count": 5000})` is created
- **THEN** the instance MUST have `name == "droidbot"`, `variant == "dfs_greedy"`, `parameters == {"count": 5000}`

#### Scenario: ToolConfig default variant

- **WHEN** `ToolConfig(name="monkey")` is created without specifying a variant
- **THEN** the instance MUST have `variant == "default"` and `parameters == {}`

#### Scenario: ToolConfig from_dict with current field names

- **WHEN** `ToolConfig.from_dict({"name": "droidbot", "variant": "dfs_greedy", "parameters": {"count": 5000}})` is called
- **THEN** the result MUST have `name == "droidbot"`, `variant == "dfs_greedy"`, `parameters == {"count": 5000}`

#### Scenario: ToolConfig get_full_tool_name

- **WHEN** `tool_config.get_full_tool_name()` is called on a ToolConfig with `name="droidbot"`, `variant="dfs_greedy"`
- **THEN** the result MUST be `"droidbot:dfs_greedy"`

- **WHEN** `tool_config.get_full_tool_name()` is called on a ToolConfig with `name="monkey"`, `variant="default"`
- **THEN** the result MUST be `"monkey"`

#### Scenario: ToolConfig serialization via to_dict

- **WHEN** `tool_config.to_dict()` is called on a ToolConfig with `name="rvagent"`, `variant="multimode"`, `parameters={"mop_direct_score": 500}`
- **THEN** the result MUST be `{"name": "rvagent", "variant": "multimode", "parameters": {"mop_direct_score": 500}}`
- **AND** the keys MUST use the unified field names (not legacy names)

#### Scenario: Task UUID generation

- **WHEN** `Task(config=valid_config)` is constructed without a `task_id` parameter
- **THEN** `task.id` MUST be a valid UUID string (36 characters, 8-4-4-4-12 format)
- **AND** two tasks created without explicit IDs MUST have different IDs

#### Scenario: Task state lifecycle

- **WHEN** a Task is created and then `task.update_state(TaskState.RUNNING)` is called
- **THEN** `task.result.state` MUST be `TaskState.RUNNING`
- **AND** `task.result.start_time` MUST be set to approximately the current time
- **AND** `task.result.state_transitions` MUST contain entries for both CREATED and RUNNING

#### Scenario: App package mismatch detection

- **WHEN** an App is created from an APK where the manifest package is "ir.hsn6.trans" but the implementation package is "org.godotengine.godot"
- **THEN** `app.package_name` MUST return "ir.hsn6.trans"
- **AND** `app.code_package` MUST return "org.godotengine.godot"
- **AND** a log message MUST be emitted at INFO level indicating the mismatch

#### Scenario: Coverage repository ignores unknown methods

- **WHEN** a LogcatRepository has static analysis data for class "com.example.MyClass" with method signature `<com.example.MyClass: void doSomething()>`, and `register_method_call()` is called with a RvCoverageLog for class "com.unknown.Other"
- **THEN** the call MUST be silently ignored (debug log only)
- **AND** `calculate_metrics().called_methods` MUST remain 0

#### Scenario: RvErrorLog deduplication

- **WHEN** two RvErrorLog instances are created with the same `class_full_name`, `method`, `spec`, `error_type`, and `message`
- **THEN** both instances MUST have identical `unique_msg` computed properties
- **AND** `error1 == error2` MUST return True
- **AND** `hash(error1) == hash(error2)` MUST return True

