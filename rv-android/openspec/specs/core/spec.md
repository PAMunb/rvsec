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

- **INV-CORE-33**: After commit C1f, no Pydantic model in `rv_android_core.domain` MUST contain a field whose name ends with `_mop`, `_directly_mop`, or equals `mop_methods`. Verified by AST inspection in `tests/domain/test_no_legacy_mop_fields.py` (part of the `G_no_legacy_mop` CI gate scope).
- **INV-CORE-34**: The `target_reaches_target` member on `WindowTransition` MUST be implemented via the `@property` decorator, not as a stored Pydantic field. Verified by `tests/domain/test_wtg.py` asserting `isinstance(WindowTransition.__dict__['target_reaches_target'], property)`. Storing it as a field would duplicate derivable data (P1 violation).
- **INV-CORE-37**: WHEN `RV_LOGCAT_DIAGNOSTICS` is unset or `false`, the `adb logcat` command emitted by `LogcatManager.start_capture` MUST be byte-identical to the baseline `-v threadtime -s RVSEC:V RVSEC-COV:V` (with the device serial), and the resulting `.logcat` MUST be unchanged.
- **INV-CORE-38**: The diagnostic tag set MUST be *additive* — when enabled, `RVSEC:V` and `RVSEC-COV:V` MUST remain in the filter; the diagnostic tags MUST NOT replace or reorder them.
- **INV-CORE-39**: Registering any number of `RvDiagnosticEvent`s into `LogcatRepository.diagnostic_events` MUST NOT change `calculate_metrics()` output, `total_errors`, `unique_errors`, or any coverage value; those computations MUST read only `self.classes`, `self.errors`, and `self.unique_errors`.
- **INV-CORE-40**: `RvErrorLog.to_dict()` MUST include the `source` field. `source` MUST NOT appear in `unique_msg` and MUST NOT participate in `__eq__` or `__hash__`, so adding it cannot change any deduplicated count.
- **INV-CORE-41**: `RvErrorLog.unique_msg` counts at event granularity (`class:::method:::spec:::error_type:::message`) and is deliberately finer than the `(apk, class, method, spec)` key used for unique-misuse analysis. Any documentation or export that reports `unique_errors` MUST NOT present it as equivalent to a unique-misuse count.
- **INV-CORE-42**: No value written to the `class_full_name` or `method` field of an `RvErrorLog` MUST end with a `(<file>:<line>)` group. The source position belongs in `source` alone.
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

Validation behavior MUST be controlled by the `RV_PYDANTIC` environment variable. When `RV_PYDANTIC=true`, full Pydantic validation is active (development mode). When `RV_PYDANTIC=false` or unset, validation still occurs at the Pydantic level (model_config settings apply) but logging and strict mode checks are suppressed for performance. After this change the env read for `RV_PYDANTIC` (plus the related toggles `RV_PYDANTIC_STRICT` and `RV_PYDANTIC_LOG`) goes through the `ENV_PYDANTIC*` constants from `rv-android-core/constants.py` — string literals are forbidden by INV-CORE-31. These three reads remain the only authorized L1 cross-layer infra reads in `rv-android-core` and are explicitly allow-listed by the lint.

The `@validated_model(positional_fields)` decorator MUST enable Pydantic models to accept both positional and named arguments, maintaining backwards compatibility with pre-Pydantic constructors. The decorator MUST map positional arguments to field names in the declared order.

All configuration classes (PlatformConfig, ExperimentConfig, RVAgentConfig, and others in downstream modules) MUST inherit from BaseValidatedModel. **In addition** (this is the substantive delta from the baseline), the top-level configuration classes that sit at the user-input boundary — `ExperimentConfig` (in `rv-experiment`) and `PlatformConfig` (in `rv-platform`) — MUST explicitly set `model_config = ConfigDict(extra="forbid")` at the class level (not relying solely on the inherited setting). The reason is the change pairs Pydantic strict validation with the new Docker entry-point allow-list (see experiment delta INV-EXP-31) and the `ENV_*` registry (INV-CORE-30): the system has a single, tight allow-list at every entry point — configuration files, environment variables, and command-line flags — and the explicit `model_config` declaration on the boundary classes makes that pairing visible to readers and to Pydantic introspection.

This explicit declaration is what INV-CORE-32 verifies. It does NOT change validation behavior of `BaseValidatedModel` itself (which has always set `extra="forbid"`); it surfaces the constraint at the boundary classes so that the contract is auditable without needing to chase the inheritance chain.

#### Scenario: Positional and named argument equivalence

- **WHEN** `CommandResult(0, b"output", b"error")` and `CommandResult(code=0, stdout=b"output", stderr=b"error")` are both constructed
- **THEN** both instances MUST have identical field values: `code=0`, `stdout=b"output"`, `stderr=b"error"`
- **AND** `instance1 == instance2` MUST return True

#### Scenario: Extra fields are rejected (BaseValidatedModel subclass)

- **WHEN** a BaseValidatedModel subclass is constructed with an unexpected field (e.g., `CommandResult(code=0, stdout=b"", stderr=b"", unexpected_field="value")`)
- **THEN** Pydantic MUST raise a ValidationError because `extra='forbid'` is set in model_config
- **AND** the error message MUST indicate the unexpected field

#### Scenario: Top-level config explicitly declares extra='forbid' (NEW)

- **WHEN** `inspect.getsource(ExperimentConfig)` (or `PlatformConfig`) is read
- **THEN** the source MUST contain `model_config = ConfigDict(extra="forbid")` at the class body level (not just inherited from `BaseValidatedModel`)
- **AND** the test `tests/test_top_level_configs_strict.py` MUST assert the declaration via Python AST or string match
- **AND** instantiating the model with an extra field (e.g., `ExperimentConfig(unknown_field="value", ...)`) MUST raise `ValidationError` naming `unknown_field`

#### Scenario: Top-level config accepts only declared fields

- **WHEN** `ExperimentConfig` is instantiated with all required and declared optional fields
- **THEN** validation MUST succeed
- **AND** the resulting object's attributes MUST match the input

#### Scenario: Positional-keyword conflict detection

- **WHEN** `CommandResult(0, b"output", code=1)` is constructed (field "code" specified both positionally and as keyword)
- **THEN** a `ValueError` MUST be raised with a message indicating the conflict for field "code"

#### Scenario: Validation config from environment (constants only)

- **WHEN** `RV_PYDANTIC` is set to `"true"` in the environment
- **THEN** `ValidationConfig.get_instance().enabled` MUST return True
- **AND** when `RV_PYDANTIC` is set to `"false"`, `enabled` MUST return False
- **AND** when `RV_PYDANTIC` is not set, `enabled` MUST return False (default)
- **AND** the source code reading these values MUST use `os.getenv(ENV_PYDANTIC, ...)` (and analogously `ENV_PYDANTIC_STRICT`, `ENV_PYDANTIC_LOG`); string literals are forbidden by INV-CORE-31

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

### Requirement: Environment-Variable Identifier Registry (NFR01, NFR03)

The Core module MUST own the canonical registry of environment-variable identifiers used by the RV-Android system. The registry takes the form of `ENV_*` constants in `rv-android-core/src/rv_android_core/constants.py`, where each constant maps a logical identifier (e.g., `ENV_HUMANOID_URL`) to the corresponding environment-variable string (`"RV_HUMANOID_URL"`). The registry MUST cover all environment variables that the system recognizes as input — any variable name not listed in the registry is by definition unknown.

Higher layers consume the registry by importing the constant and passing it to `os.environ.get`. They MUST NOT pass string literals like `"RV_TIMEOUTS"` directly. This indirection serves two purposes: (a) it lets a single grep across `modules/` confirm Layer Purity (only L5 and L1-exceptions read environment variables), and (b) it provides a definitive list against which the Docker entry-point allow-list and the README documentation can be reconciled by the CI lint.

When a new environment variable is added to the system, the developer MUST first add the corresponding `ENV_*` constant to `constants.py`. The CI lint script `scripts/check_env_vars_drift.py` MUST fail if any `os.environ` access uses a string literal that does not correspond to an `ENV_*` constant.

#### Scenario: Tool reads an environment variable via the registry

- **WHEN** the rv-experiment CLI initialization code needs to resolve a value from the environment
- **AND** the value's logical name is `RV_TIMEOUTS`
- **THEN** the code MUST `from rv_android_core.constants import ENV_TIMEOUTS`
- **AND** MUST call `os.environ.get(ENV_TIMEOUTS)` (not `os.environ.get("RV_TIMEOUTS")`)
- **AND** the lint script `scripts/check_env_vars_drift.py` MUST pass

#### Scenario: Lint catches string-literal regression

- **WHEN** a developer commits code containing any of these forms — `os.environ.get("RV_TOOLS")`, `os.environ["RV_TOOLS"]`, `os.getenv("RV_TOOLS")` — instead of going through `ENV_TOOLS`
- **THEN** the CI lint MUST fail with a message naming the offending file, line, and which of the three forms was matched
- **AND** the message MUST point the developer at `rv-android-core/src/rv_android_core/constants.py` for the canonical constant
- **AND** the lint MUST also fail if it sees `dict(os.environ)` or `os.environ.copy()` outside of `modules/rv-experiment/` (these forms leak the entire environment past Layer Purity boundaries)

#### Scenario: New environment variable requires registry update

- **WHEN** a developer adds a new environment variable `RV_NEW_FEATURE` to the system
- **AND** does not add the corresponding `ENV_NEW_FEATURE` constant to `rv-android-core/constants.py`
- **THEN** the CI lint MUST fail with a drift message

### Requirement: Reachability Field Naming in Core Domain Models (FR33, NFR04)

The `rv-android-core` Pydantic domain models that carry method-of-interest reachability flags MUST use the field-name family `*_target` / `*_directly_target` / `target_methods` exclusively. The legacy family `*_mop` / `*_directly_mop` / `mop_methods` MUST NOT survive in any model after this change is merged (INV-CORE-33).

Affected models and their renamed fields:

- `rv_android_core.domain.classes.Method`:
  - `reaches_target: bool` (renamed from `reaches_mop`)
  - `directly_reaches_target: bool` (renamed from `directly_reaches_mop`)
- `rv_android_core.domain.widget.Widget`:
  - `reaches_target: bool` (renamed from `reaches_mop`)
  - `directly_reaches_target: bool` (renamed from `directly_reaches_mop`)
- `rv_android_core.domain.widget.WidgetEvent`:
  - Field reserved for future enrichment: `handler_reaches_target` and `handler_directly_reaches_target` are NOT added in this change (they belong to follow-up change C3 `agent-enrichment`). The naming convention is established here so C3 can add fields without further renames.
- `rv_android_core.domain.components.ComponentInfo`:
  - `reaches_target: bool` (renamed from `reaches_mop`)
  - `directly_reaches_target: bool` (renamed from `directly_reaches_mop`)
  - `target_methods: List[str]` (renamed from `mop_methods`) — list of resolved target signatures attributed to this component
- `rv_android_core.domain.wtg.WindowTransition`:
  - `target_reaches_target: bool` — Python `@property` derived from the methods of the target window. The transition itself does not embed the target window object; the property resolves `target_window` indirectly via a `window_id → List[Method]` map populated by `StaticAnalysisParser` and exposed to the transition through a parser-owned context (constructor injection of `window_methods_index: Mapping[str, list[Method]]` keyed by `target_window_id`). This avoids storing derived data (INV-CORE-34) while keeping the property accessible without re-traversing `StaticAnalysisData`. Renamed from `target_reaches_mop`; behavior unchanged.

The Pydantic `field description` strings for renamed fields MUST use the term "target method" (replacing "MOP method") to align the docstring with the new field name.

**New field introduced by this change:** `rv_android_core.domain.static.StaticAnalysisData.complete: bool` (default `False`) — the parser surface of the JSON sentinel emitted by `JsonReportWriter`. Declared here (not in `analysis` spec) because the field lives on a `core` Pydantic model and is consumed by every downstream module. Default `False` so that truncated outputs parse without error. No other new fields. No fields are removed (the rename preserves the field; only the name changes).

**Module**: rv-android-core (`src/rv_android_core/domain/classes.py`, `widget.py`, `components.py`, `wtg.py`, `static.py`).

#### Scenario: Method instantiation with renamed fields

- **WHEN** `Method(signature="<com.example.Foo: void bar()>", reaches_target=True, directly_reaches_target=False)` is constructed
- **THEN** the instance MUST have `method.reaches_target == True`
- **AND** `method.directly_reaches_target == False`
- **AND** accessing `method.reaches_mop` MUST raise `AttributeError` (P3 — no shim)

#### Scenario: Widget instantiation with renamed fields

- **WHEN** `Widget(id=1, type=WidgetType.BUTTON, reaches_target=True, directly_reaches_target=True)` is constructed
- **THEN** the instance MUST have both renamed fields populated
- **AND** legacy attribute access MUST raise `AttributeError`

#### Scenario: ComponentInfo instantiation with renamed fields

- **WHEN** a `ComponentInfo` for a Service is constructed with `reaches_target=False` and `target_methods=["<com.example.S: void onCreate()>"]`
- **THEN** the instance MUST have `component.reaches_target == False`
- **AND** `component.target_methods == ["<com.example.S: void onCreate()>"]`
- **AND** legacy attribute access (`reaches_mop`, `mop_methods`) MUST raise `AttributeError`

#### Scenario: WindowTransition derived property with window methods index

- **WHEN** a `WindowTransition` is constructed with `target_window_id="W2"` and the parser provides a `window_methods_index` where `index["W2"]` contains at least one `Method` with `reaches_target == True`
- **THEN** the `@property target_reaches_target` MUST return `True`
- **AND** the property MUST be lazy (computed on access, not stored — INV-CORE-34)
- **AND** the legacy property name `target_reaches_mop` MUST NOT exist on the class
- **AND** when no `window_methods_index` is injected (e.g., orphan transition constructed in unit test), the property MUST return `False` rather than raise

#### Scenario: Pydantic deserialization from JSON with new key names

- **WHEN** `Method.model_validate({"signature": "<...>", "reaches_target": true, "directly_reaches_target": false})` is invoked
- **THEN** validation MUST succeed
- **AND** the resulting instance MUST have the renamed fields populated correctly

#### Scenario: Pydantic deserialization with legacy keys under RV_PYDANTIC=true

- **WHEN** `Method.model_validate({"signature": "<...>", "reaches_mop": true})` is invoked AND the env var `RV_PYDANTIC=true` is active (development/CI mode — `extra="forbid"` semantics)
- **THEN** Pydantic MUST raise `ValidationError` indicating `reaches_mop` is not a valid field (P3 — no field alias for the legacy name)

#### Scenario: Pydantic deserialization with legacy keys under RV_PYDANTIC=false

- **WHEN** `Method.model_validate({"signature": "<...>", "reaches_mop": true})` is invoked AND `RV_PYDANTIC` is unset or `false` (production mode — `extra="ignore"` per existing `BaseValidatedModel` behavior)
- **THEN** the legacy key MUST be silently dropped
- **AND** `reaches_target` MUST default to its declared default value
- **AND** no warning or error MUST be emitted

#### Scenario: StaticAnalysisData sentinel default

- **WHEN** `StaticAnalysisData.model_validate({...})` is invoked on a JSON payload that does not include the `complete` key
- **THEN** validation MUST succeed
- **AND** `data.complete` MUST be `False`

### Requirement: Opt-in Diagnostic Logcat Capture (FR33, FR34)

`LogcatManager` SHALL support an opt-in capture mode that, when enabled via the
`RV_LOGCAT_DIAGNOSTICS` flag, augments the logcat tag filter with the diagnostic tags
`AndroidRuntime:E art:E dalvikvm:E ActivityManager:W` in addition to the existing `RVSEC:V RVSEC-COV:V`.
When the flag is disabled (the default), capture behavior MUST be identical to the current baseline.
The flag SHALL be exposed as a named constant `ENV_LOGCAT_DIAGNOSTICS = "RV_LOGCAT_DIAGNOSTICS"` in
`rv_android_core/constants.py`.

#### Scenario: Flag off preserves baseline command byte-for-byte
- **WHEN** `RV_LOGCAT_DIAGNOSTICS` is unset and `start_capture` is called for serial `emulator-5554`
- **THEN** the emitted command is `adb -s emulator-5554 logcat -v threadtime -s RVSEC:V RVSEC-COV:V`
- **AND** no diagnostic tag (`AndroidRuntime`, `art`, `dalvikvm`, `ActivityManager`) appears in the filter

#### Scenario: Flag on appends diagnostic tags additively
- **WHEN** `RV_LOGCAT_DIAGNOSTICS=true` and `start_capture` is called
- **THEN** the filter contains `RVSEC:V` and `RVSEC-COV:V` unchanged
- **AND** the filter additionally contains `AndroidRuntime:E`, `art:E`, `dalvikvm:E`, and `ActivityManager:W`

### Requirement: Diagnostic Event Domain Model (FR33)

The core domain SHALL provide an `RvDiagnosticEvent` model in `domain/log.py` representing a single
execution-level diagnostic event, following the existing `RvErrorLog`/`RvCoverageLog` conventions
(validated model, `to_dict`/`from_dict`, computed `unique_msg`). The model SHALL carry a `category`
discriminator with values `crash`, `verify_error`, and `anr`.

#### Scenario: Crash event carries attribution and trace summary
- **WHEN** a crash event is constructed from a parsed `AndroidRuntime` FATAL block for package
  `br.unb.cic.cryptoapp`
- **THEN** `category == "crash"`, `fatal == true`, `process == "br.unb.cic.cryptoapp"`, and `pid` is set
- **AND** `exception_class`, `stack_head`, `n_frames`, and `original_msg` (the full multi-line block) are populated

#### Scenario: unique_msg disambiguates by category
- **WHEN** two events share class/method but differ in `category` (`crash` vs `verify_error`)
- **THEN** their `unique_msg` values differ

### Requirement: Isolated Diagnostic Event Collection on LogcatRepository (FR33, FR37)

`LogcatRepository` SHALL expose a `diagnostic_events` collection with
`register_diagnostic_event(event)` and `get_diagnostic_events()`, kept strictly separate from the
coverage (`classes`) and property-violation (`errors`) data so that diagnostic events never enter
coverage/MOP metrics or the `total_errors`/`unique_errors` counts.

#### Scenario: Diagnostics do not affect metrics
- **WHEN** a repository holds RVSEC violations and coverage data, and N crash events are registered
- **THEN** `calculate_metrics()`, `total_errors`, `unique_errors`, and every coverage value are identical
  to the same repository with zero diagnostic events
- **AND** `get_diagnostic_events()` returns the N events sorted by `time_since_task_start`

### Requirement: RvErrorLog Preserves the Source Location in the Written Schema (FR13, FR14)

`RvErrorLog.to_dict()` MUST include the `source` field, and the per-run `errors.csv` produced by
`ResultProcessorComponent` MUST carry a corresponding `source` column placed after `method`. The
field MUST remain outside `unique_msg`, `__eq__` and `__hash__`, so that preserving it cannot
change `unique_errors`, `total_errors`, or any coverage or MOP metric.

The distinction this requirement encodes is between *excluding a field from the identity of a
violation* and *discarding it*. The source position must not identify a violation — two
occurrences of the same misuse at different lines are one misuse — but it is still the most
direct pointer to where the violation happened, and it is the evidence needed to audit a
frame-form normalization after a campaign has run.

Because the column set of `errors.csv` is a contract shared with `rvsec-dataset` and the
article's analysis scripts, the change MUST be verified against those consumers before it lands:
readers that address columns by name tolerate an added column, readers that address them
positionally do not.

#### Scenario: source survives serialization

- **WHEN** an `RvErrorLog` is created with `class_full_name` = `okio.ByteString`,
  `method` = `digest$okio`, `source` = `ByteString.kt:83`
- **THEN** `to_dict()` MUST contain the key `source` with value `ByteString.kt:83`

#### Scenario: source does not affect identity

- **WHEN** two `RvErrorLog` instances agree on `class_full_name`, `method`, `spec`,
  `error_type` and `message` but carry `source` = `ByteString.kt:83` and `ByteString.kt:84`
- **THEN** their `unique_msg` values MUST be identical
- **AND** `error1 == error2` MUST return True
- **AND** `hash(error1) == hash(error2)` MUST return True
- **AND** registering both in a `LogcatRepository` MUST yield `unique_errors` = 1

#### Scenario: errors.csv carries the source column

- **WHEN** `ResultProcessorComponent` generates `errors.csv` for a completed task
- **THEN** the header MUST be
  `apk,rep,timeout,tool,time,spec,class,method,source,message,unique_msg`
- **AND** each row MUST carry the originating record's `source` value in that column

### Requirement: Event Granularity of unique_msg Is Documented, Not Changed (FR13)

`RvErrorLog.unique_msg` MUST remain `"{class_full_name}:::{method}:::{spec}:::{error_type}:::{message}"`
(INV-CORE-25 is unchanged). The model documentation MUST state that this key counts at event
granularity and is finer than the `(apk, class, method, spec)` key used to count unique misuses
in the thesis and the journal article, and MUST give the reason: `error_type` separates a
sequence violation from a constraint violation in the same method, and `message` names the
offending parameter, so two messages under one method are two different misuses.

The documentation MUST state the consequence explicitly — that `unique_errors` and the
`mop_errors_unique` column derived from it are not numerically comparable to a unique-misuse
count — so that a reader comparing the two figures does not conclude that one is defective.

#### Scenario: distinct offending parameters remain distinct events

- **WHEN** two violations occur in `com.apk.axml.APKParser.getCertificateFingerprint` under
  `MessageDigestSpec`, one with message `expecting one of {SHA-256, SHA-384, SHA-512} but found SHA1.`
  and one with `… but found MD5.`
- **THEN** their `unique_msg` values MUST differ
- **AND** `unique_errors` MUST count them as 2
- **AND** the `(apk, class, method, spec)` analysis key MUST count them as 1 unique misuse
- **AND** both counts MUST be understood as correct at their own granularity

### Requirement: Emulator Boot Completion Gating (FR07, NFR04)

`Android._wait_for_boot` MUST verify that the Android framework has completed boot before returning, and MUST NOT return successfully on the basis of a command that failed.

The wait MUST proceed in two phases against a single shared budget. Phase 1 polls `adb -s <serial> shell getprop init.svc.bootanim` and advances when the device reports `stopped`. Phase 1 is a coarse gate only: the emulator is launched with `-no-boot-anim`, so the animation service can report `stopped` before the framework is usable. Phase 2 polls `adb -s <serial> shell getprop sys.boot_completed` and is the authoritative readiness signal.

Phase 2 MUST be implemented as a Python poll issuing a plain `getprop` on each iteration. It MUST NOT delegate iteration to a shell loop embedded in a command string: `Command.invoke()` spawns processes with `shell=False`, so quoting characters in an argv element are delivered literally to the device and the whole string is interpreted as a single command name.

The `wait-for-device` token the current argv carries before `shell` is dropped along with the loop. It exists to block until ADB sees the device, which is what a Python poll bounded by the shared budget now does explicitly and observably; keeping it would reintroduce an unbounded wait inside a single probe, answerable only to the per-command timeout.

Both phases MUST inspect the returned `CommandResult` before acting on it. `RVCommandTimeoutError` from an individual probe MUST be caught and the probe retried, because ADB responds slowly during early boot; a non-zero exit or an unexpected value MUST NOT terminate the wait.

Phase 1 MUST distinguish "the device is not ready yet" from "ADB is broken". An empty stdout or a failed probe MUST be reported with diagnostics at the point it occurs, rather than silently consuming the budget for the full duration.

#### Scenario: Boot completes normally

- **WHEN** `_wait_for_boot("emulator-5554")` is called and `getprop init.svc.bootanim` returns `b"stopped"` with exit `0`, then `getprop sys.boot_completed` returns `b"1"` with exit `0`
- **THEN** the method MUST return without raising
- **AND** it MUST log the device serial together with the elapsed boot time measured from the single `start` timestamp

#### Scenario: Phase 2 probe fails with a non-zero exit

- **WHEN** `getprop sys.boot_completed` returns a `CommandResult` whose `is_failure()` is `True` — for example exit `127`, the status produced today by the quoted shell string
- **THEN** the wait MUST NOT terminate
- **AND** polling MUST continue until the shared budget expires
- **AND** `TimeoutError` MUST then be raised naming phase 2 and the budget in force

#### Scenario: Phase 2 probe returns an unset property

- **WHEN** `getprop sys.boot_completed` succeeds with exit `0` but `stdout.strip()` is `b""` — the device answered, the property is simply not set yet
- **THEN** the wait MUST NOT terminate
- **AND** the next poll MUST be issued after the configured interval

#### Scenario: Argument vector carries no shell dependency

- **WHEN** the argument vector for the `sys.boot_completed` probe is constructed
- **THEN** it MUST contain no literal `'` or `"` characters
- **AND** it MUST contain no `$(`, `[[`, `while`, or `;` tokens
- **AND** it MUST be the plain form `["-s", "<serial>", "shell", "getprop", "sys.boot_completed"]`

#### Scenario: Broken ADB is reported in seconds, not after the full budget

- **WHEN** the phase-1 probe returns a `CommandResult` whose `is_failure()` is `True` with `stderr` containing `b"device offline"`
- **THEN** the condition MUST be logged with the device serial and the combined command output at the point of detection
- **AND** the log MUST identify it as a probe failure rather than a not-yet-booted device

#### Scenario: Both phases share one budget

- **WHEN** `_wait_for_boot("emulator-5554", boot_timeout=10)` is called and phase 1 consumes 8 seconds before reporting `stopped`
- **THEN** phase 2 MUST have at most the remaining 2 seconds before `TimeoutError` is raised
- **AND** the raised message MUST identify phase 2, distinguishably from phase 1's message

### Requirement: Environment-Parameterized Device Timeouts (FR07, NFR04)

The boot budget, the per-command ADB timeout, and the `adb install` timeout MUST be configurable per environment through environment variables, with the values in force today as defaults where one exists.

The correct value for each depends on the host and its concurrency level, not on the experiment being run: the same cold boot that finishes quickly on an idle machine disperses far beyond that under 8 to 16 containers competing for KVM, CPU and RAM — the recorded phase-1 timeouts already span a p50 of 182 s and a maximum of 871 s on the same 180 s budget. These are properties of the environment, and MUST be read from the environment at the point of use, following the L1 cross-layer infra exception established in `util/validation/config.py:75-88`.

The boot poll interval is not included. It stays a module constant, because the interval at which the device is asked does not depend on the machine — only the budget does.

Each variable MUST be declared as an `ENV_*` constant in `constants.py` and documented in `.env.example`. A value that is set but not a valid integer MUST raise, not silently revert to the default — a mistyped budget that quietly becomes the default is indistinguishable from a working configuration until an experiment fails.

`adb install` MUST run under a timeout. It has none today, so a hung install blocks the task for as long as the process lives, holding the emulator session open.

#### Scenario: Default applies when the variable is unset

- **WHEN** `RV_EMULATOR_BOOT_TIMEOUT` is absent from the environment and `_wait_for_boot("emulator-5554")` is called with no explicit `boot_timeout`
- **THEN** the budget in force MUST be `300` seconds
- **AND** the initial log line MUST report that value

#### Scenario: Valid integer is honoured

- **WHEN** `RV_EMULATOR_BOOT_TIMEOUT` is `"600"` and `_wait_for_boot("emulator-5554")` is called with no explicit `boot_timeout`
- **THEN** the budget in force MUST be `600` seconds

#### Scenario: Explicit argument overrides the environment

- **WHEN** `RV_EMULATOR_BOOT_TIMEOUT` is `"600"` and `_wait_for_boot("emulator-5554", boot_timeout=10)` is called
- **THEN** the budget in force MUST be `10` seconds, preserving the injection point the unit tests rely on

#### Scenario: Invalid value fails loudly

- **WHEN** `RV_EMULATOR_BOOT_TIMEOUT` is `"30O"` — a capital letter O typed for a zero
- **THEN** `ValueError` MUST propagate from the resolution
- **AND** the default MUST NOT be substituted

#### Scenario: APK installation runs under a timeout

- **WHEN** `Android.install_apk` constructs the `adb install -r -g <path>` command
- **THEN** that `Command` MUST carry a non-`None` timeout resolved from `RV_APK_INSTALL_TIMEOUT`
- **AND** exceeding it MUST raise `RVCommandTimeoutError` after the process tree is killed, rather than blocking indefinitely

#### Scenario: New variables are declared in the registry

- **WHEN** `RV_EMULATOR_BOOT_TIMEOUT`, `RV_ADB_CMD_TIMEOUT` and `RV_APK_INSTALL_TIMEOUT` are set in a container's environment
- **THEN** each MUST appear as an `ENV_*` constant in `constants.py`
- **AND** `docker/rvandroid/scripts/validate_env_vars.sh` MUST accept them rather than terminating the container with exit `64`

### Requirement: Emulator Session Failure Attribution (FR07, NFR04, NFR06)

`EmulatorManager.start_emulator` MUST report failures with their true origin. A failure that occurs while the emulator session is in use MUST NOT be relabelled as a failure to start the emulator.

The context manager currently places its `yield` inside the `try` whose `except` raises `EmulatorError(f"Failed to start emulator {avd_name}", cause=e)`. In a `@contextmanager`, an exception raised in the body of the `with` is re-raised at the `yield`, so every failure during installation, logcat capture, coverage tracking, or tool execution is caught there and re-labelled. The resulting message — `EmulatorError: Failed to start emulator RVSec caused by TaskExecutionError: Failed to install application` — is self-contradictory, since it is only generable when startup succeeded, and it is present in 1,174 stored failure records.

Startup and session MUST therefore be separated, with only startup covered by the `except` that produces `EmulatorError`. Teardown MUST remain unconditional and MUST cover **both**: the `finally` that kills the emulator encloses the startup sequence and the `yield` together, so neither a failing session nor a failing startup can leave a device running for the next task. This is the one structural detail that is easy to get wrong — placing the `except` and the `finally` on two sibling blocks satisfies the relabelling requirement while silently removing teardown from the startup-failure path, which is exactly the path the next obligation exists for.

The AVD MUST be registered in `_active_emulators` before the emulator process is launched. Registration currently happens after `Android.start_emulator` returns — which includes the boot wait — and the teardown `finally` acts only on registered AVDs, so a genuine boot failure leaves the daemonized emulator alive holding its port for the next task to find.

Registering earlier makes teardown fire on paths where no emulator process may exist. The settling delay that follows `adb emu kill` MUST therefore become conditional on the kill having succeeded, so a failed launch is not taxed for a port release that is not happening.

#### Scenario: Failure inside the session keeps its identity

- **WHEN** the body of `with emulator_manager.start_emulator("RVSec") as android:` raises `TaskExecutionError("Failed to install application", task_id)`
- **THEN** the caller MUST receive `TaskExecutionError`, not `EmulatorError`
- **AND** the message MUST NOT contain `"Failed to start emulator"`

#### Scenario: Genuine startup failure is still labelled as such

- **WHEN** `Android.start_emulator` raises `TimeoutError("emulator-5554 sys.boot_completed not set within 300s")`
- **THEN** the caller MUST receive `EmulatorError` whose message names the AVD
- **AND** its `cause` MUST be the original `TimeoutError`

#### Scenario: Teardown runs even when the session fails

- **WHEN** the body of the `with` block raises any exception
- **THEN** `Android.kill_emulator` MUST still be invoked for the registered AVD with the device serial derived from `device_port`
- **AND** the AVD MUST be removed from `_active_emulators`

#### Scenario: Failed boot leaves no orphan holding the port

- **WHEN** `Android.start_emulator("RVSec", no_window=True, device_port=5556)` raises `TimeoutError` during the boot wait
- **THEN** `"RVSec"` MUST already be present in `_active_emulators` at that moment
- **AND** the teardown `finally` MUST issue `adb -s emulator-5556 emu kill`
- **AND** no `emulator` process MUST remain holding port `5556`

#### Scenario: Teardown runs when startup itself fails

- **WHEN** the startup sequence raises and `EmulatorError` is produced, so the `with` body is never entered
- **THEN** `Android.kill_emulator` MUST still be invoked for the registered AVD
- **AND** `"RVSec"` MUST be removed from `_active_emulators`
- **AND** the `EmulatorError` MUST continue to propagate to the caller unchanged

#### Scenario: Post-kill delay is skipped when nothing was killed

- **WHEN** teardown issues `adb emu kill` for an AVD whose emulator process never came up, and the kill command reports failure
- **THEN** the settling delay MUST NOT be taken
- **AND** teardown MUST return without waiting for a port that was never bound

### Requirement: ADB Failure Reason Propagation (FR07, NFR06)

When APK installation fails, the reason ADB gave MUST reach the task's `error_message`.

`Android.install_apk` already preserves it: on failure it raises `RuntimeError` carrying the exit code and `result.get_combined_output()`. The information is discarded one layer up, where `EmulatorManager.install_app` catches the exception, logs it, and returns bare `False`. The caller therefore has a boolean, and the stored `error_message` records only `"Failed to install application"`. Across 1,174 recorded install failures, not one carries an `INSTALL_FAILED_*` code.

This matters beyond diagnostics. The AVD baked into `phtcosta/rvsec_android:0.9.3` has `disk.dataPartition.size = 800M`, against 6 GB on the host AVD built from the same `pixel` profile. That raises an untested hypothesis: `INSTALL_FAILED_INSUFFICIENT_STORAGE` as a **direct** cause of install failure, independent of the boot gate, producing an identical symptom. It is recorded here as a hypothesis and not as a finding — it cannot be decided from existing artifacts precisely because the reason is never stored. Propagating the reason is what allows the next occurrence to distinguish the two causes from a single record.

#### Scenario: Installation failure carries the ADB reason

- **WHEN** `adb install -r -g <path>` exits non-zero with stderr containing `INSTALL_FAILED_INSUFFICIENT_STORAGE`
- **THEN** the failure surfaced by `EmulatorManager.install_app` MUST carry that text
- **AND** the text MUST reach the task's stored `error_message`
- **AND** the message MUST NOT be reduced to `"Failed to install application"` alone

#### Scenario: Signature-mismatch retry preserves the final reason

- **WHEN** the first `adb install` fails with `INSTALL_FAILED_UPDATE_INCOMPATIBLE`, the package is uninstalled, and the retry also fails with `INSTALL_FAILED_INSUFFICIENT_STORAGE`
- **THEN** the reason propagated MUST be the one from the retry
- **AND** it MUST include the ADB exit code

