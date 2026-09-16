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
|   |   |-- build_type_suffix.py    Build-type suffix neutralization
|   |   |-- emulator_manager.py     Emulator lifecycle
|   |   |-- logcat_manager.py       Logcat capture
|   |   +-- package_detector.py     Code package detection
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
  package_detector: bool         # Elect the package heuristically (default False)
  # computed fields:
  path: str                      # os.path.abspath(app_path)
  name: str                      # os.path.basename(app_path)
  package_name: str              # From AndroidManifest.xml (for device ops)
  code_package: str              # package_name, or PackageDetector when enabled
  code_package_source: str       # "manifest" | "detector"
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
- `strip_build_type_suffix: bool` -- Run-scalar policy: neutralize a build-type suffix on the declared applicationId before reporting `code_package` (INV-CORE-58). Source: resolved at the entry point and passed to `App` by value.
- `RvErrorLog.message: str` -- The violation description as the monitor emitted it. Source: `logcat_parser`, the CSV collector, or a persisted `tasks.json`. When the emitter is an envelope-producing set the message is `v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<text>'`; otherwise it is free text. In both cases it MUST NOT contain the substring `:::` (INV-CORE-56).
- `RvErrorLog.code: str` / `RvErrorLog.event: str` -- The `code=` and `ev=` values of the envelope, or the sentinel `UNSPECIFIED` when the message carries no envelope. Source: the parser that built the record.

### Output

- `CommandResult(code, stdout, stderr)` -- Result of system command execution. Destination: calling module.
- `App` instance -- Android APK metadata extracted via Androguard, including `code_package` and `code_package_source` (`"manifest"`, `"manifest-neutralized"` or `"detector"`, INV-CORE-18). Destination: rv-platform tasks, rv-agent.
- `TaskResult.write_errors: Dict[str, int]` -- Rows not written, keyed by the artefact that lost them (`errors.csv`, `results.json`); serialized by `to_dict()`, read back by `from_dict()`, persisted after result processing (INV-CORE-61). Destination: `tasks.json`.
- `Task` instance -- Task with configuration, result, and coverage repository. Destination: rv-platform executor.
- `CoverageMetrics` -- Calculated coverage percentages. Destination: rv-platform result processor.
- `Metric` / `TimingMetric` -- Performance measurements. Destination: PerformanceMonitor subscribers.
- `RvErrorLog.unique_msg: str` -- Computed, seven `:::`-separated parts `class_full_name, method, spec, error_type, code, event, message`. Destination: `LogcatRepository` dedupe, `errors.csv`, `results.json`, every reader that splits on `:::`.
- `RvErrorLog.to_dict()` -- Carries the keys `code` and `event` beside the other fields. Destination: `tasks.json`, `errors.csv`.

### Side-Effects

- **Process creation**: Command.invoke() spawns OS processes via `subprocess.Popen`. Command.invoke_as_deamon() and invoke_as_process() create background processes.
- **Process termination**: `kill_process_tree()` recursively kills process trees via `psutil` and `os.kill(SIGKILL)`.
- **File system**: Task.initialize() creates results directories via `os.makedirs()`. LoggingManager.setup_file_logging() creates log files.
- **APK analysis**: App model_post_init() loads APK via Androguard (I/O operation reading APK file).
- **Counts**: `unique_errors` and every figure derived from it (`mop_errors_unique`, the `unique_msg` column of `errors.csv`) differ between the five-part and the seven-part identity for any input where two records of one `(class, method, spec, error_type, message)` differ in `code` or `event` — a declared discontinuity (INV-CORE-57).

### Error

- `ConfigurationError` -- Invalid configuration or APK file not found/invalid.
- `CommandValidationError` -- Empty command string, invalid timeout, or invalid arguments.
- `RVCommandTimeoutError` -- Command execution exceeded timeout. Contains `timeout_seconds` and `command`.
- `CircuitBreakerOpenError` -- Command blocked by circuit breaker after repeated failures. Contains `command_signature` and `failure_count`.
- `RVAndroidError` -- Base exception for all framework-specific errors. Contains `message` and `cause`.
- `CommandNotFoundError` -- OS command not found (OSError wrapper).
- Pydantic `ValidationError` -- Raised by BaseValidatedModel when field validation fails (not caught by ErrorHandler).
- `RvErrorLog` raises nothing on a message containing `:::`: the prohibition is enforced by the producer and detected by the readers, which count a key with a part count other than seven as unparsed (INV-CORE-56).

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

- **INV-CORE-18**: `App.code_package` MUST return the declared applicationId verbatim when both the `PackageDetector` and the build-type-suffix neutralization policy are off, which is the default; MUST return the neutralized identifier when the neutralization policy is on, the detector is off, and a denied segment was removed; and MUST return the `PackageDetector` election when the detector is on — **the detector takes precedence**: when both policies are on, `code_package` is the detector's election and `code_package_source` is `"detector"`, because the detector answers from the compiled classes themselves and the neutralization is only a repair of the declared id. `code_package_source` MUST report which of the three produced the value — `"manifest"`, `"manifest-neutralized"` or `"detector"` — so that no reader has to re-derive the key from the artefacts it shaped. `App.package_name` MUST return the manifest package name (from `APK.get_package()`) verbatim, with no normalization of any kind.

- **INV-CORE-19**: Task.id MUST be a UUID string. If no `task_id` is provided to the constructor, a new UUID MUST be generated via `uuid.uuid4()`.

- **INV-CORE-20**: TaskState transitions MUST follow the lifecycle: CREATED -> INITIALIZING -> READY -> RUNNING -> COMPLETED|ERROR|CANCELED. Each transition MUST be recorded in `TaskResult.state_transitions`.

- **INV-CORE-21**: LoggingManager MUST be a thread-safe singleton. `get_logger()` MUST cache logger instances by name + context and return `ContextAdapter` instances (not raw loggers).

- **INV-CORE-22**: PerformanceMonitor MUST be a thread-safe singleton. When `_config` is None or `_config.enabled` is True, metrics MUST be collected. When disabled, `measure_time()` MUST yield without overhead and `record_metric()` MUST be a no-op.

- **INV-CORE-23**: AbstractTool.execute() MUST convert `RVCommandTimeoutError` to `RVToolTimeoutError`. Tool timeouts are considered expected behavior and MUST NOT be treated as failures.

- **INV-CORE-24**: LogcatRepository.register_method_call() MUST only register calls to methods that exist in the static analysis data (classes dictionary). Calls to unknown classes or methods MUST be silently ignored with a debug log.

- **INV-CORE-25**: `RvErrorLog.unique_msg` MUST be computed as `"{class_full_name}:::{method}:::{spec}:::{error_type}:::{code}:::{event}:::{identity_message}"` — seven `:::`-separated parts, `code` and `event` read from the message envelope (`code=`, `ev=`) or equal to the sentinel `UNSPECIFIED` when the message carries no envelope, and `identity_message` equal to `message` with the trailing evidence keys removed (INV-CORE-63). Two `RvErrorLog` instances with the same `unique_msg` MUST be considered equal. The key MUST be built in exactly one place, `RvErrorLog.unique_msg` in `rv_android_core/domain/log.py`; no other module MUST assemble it from the fields.

- **INV-CORE-33**: After commit C1f, no Pydantic model in `rv_android_core.domain` MUST contain a field whose name ends with `_mop`, `_directly_mop`, or equals `mop_methods`. Verified by AST inspection in `tests/domain/test_no_legacy_mop_fields.py` (part of the `G_no_legacy_mop` CI gate scope).
- **INV-CORE-34**: The `target_reaches_target` member on `WindowTransition` MUST be implemented via the `@property` decorator, not as a stored Pydantic field. Verified by `tests/domain/test_wtg.py` asserting `isinstance(WindowTransition.__dict__['target_reaches_target'], property)`. Storing it as a field would duplicate derivable data (P1 violation).
- **INV-CORE-37**: WHEN `RV_LOGCAT_DIAGNOSTICS` is unset or `false`, the `adb logcat` command emitted by `LogcatManager.start_capture` MUST be byte-identical to the baseline `-v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V` (with the device serial). The previous two-tag form is superseded, not retained as an alternative: a capture that omits the heartbeat tag produces a logcat the offline join cannot use.

- **INV-CORE-53**: The heartbeat tag MUST be declared once, as the named constant `TAG_APERV_HEARTBEAT` in `rv_android_core/util/logging/constants.py`, beside `TAG_RVSEC` and `TAG_RVSEC_COV`, and `LogcatManager.default_tags` MUST be built from those three constants rather than from repeated string literals. The value MUST equal the tag the APE-RV jar writes under; a literal duplicated across the two repositories is where that equality would silently drift, and the failure mode of a mismatch is an empty capture rather than an error.

- **INV-CORE-54**: The presence of heartbeat lines in a captured logcat MUST NOT change any value produced by `parse_logcat_file` — not `calculate_metrics()`, not `total_errors`, not `unique_errors`, not any coverage value, and not the diagnostic-event collection.

  This holds for two different reasons, and only one of them was true before this change. On the violation and coverage path it holds by construction: `parse_logcat_line` dispatches on the exact tag field, so a heartbeat line yields neither an error nor a coverage record. On the **diagnostic-event** path it did not hold, and had to be made to: `DiagnosticEventParser` is stateful and assembles a multi-line block, and it closed that block on any line whose tag was not diagnostic — after which the block's remaining lines found an empty buffer and were discarded, losing the exception class, the app stack frame and the frame count. Logcat merges every process into one timestamp-ordered stream, so a crash block is contiguous only in the crashing process's own output and an interleaved line lands inside it. Block assembly therefore MUST treat a line under any non-diagnostic tag as transparent — yielding no event and **not** closing the open block — and MUST close on a diagnostic key change, a new block start, a non-threadtime line (`analysis` INV-ANA-48) or `flush()`.

  The invariant is verified rather than assumed, and the verification MUST exercise the hard case: a fixture in which a heartbeat lands **between two lines of a crash block**, not merely between blocks. An equality asserted over interleavings that cannot reach the stateful path would be green by construction. The defect this uncovered is pre-existing and tag-agnostic — an `RVSEC-COV` line in the same position does identical damage, and that tag has always been in the allowlist — so the heartbeat is not its cause, and the correction protects every consumer of the diagnostic collection rather than only APE-RV runs.
- **INV-CORE-38**: The diagnostic tag set MUST be *additive* — when enabled, `RVSEC:V` and `RVSEC-COV:V` MUST remain in the filter; the diagnostic tags MUST NOT replace or reorder them.
- **INV-CORE-39**: Registering any number of `RvDiagnosticEvent`s into `LogcatRepository.diagnostic_events` MUST NOT change `calculate_metrics()` output, `total_errors`, `unique_errors`, or any coverage value; those computations MUST read only `self.classes`, `self.errors`, and `self.unique_errors`.
- **INV-CORE-40**: `RvErrorLog.to_dict()` MUST include the `source` field. `source` MUST NOT appear in `unique_msg` and MUST NOT participate in `__eq__` or `__hash__`, so adding it cannot change any deduplicated count.
- **INV-CORE-41**: `RvErrorLog.unique_msg` counts at event granularity (`class:::method:::spec:::error_type:::code:::event:::message`) and is deliberately finer than the `(apk, class, method, spec)` key used for unique-misuse analysis. Any documentation or export that reports `unique_errors` MUST NOT present it as equivalent to a unique-misuse count, and MUST state which identity era the count belongs to — five-part (the published dataset, comp162 and every campaign before gh104) or seven-part — because counts of the two eras are not comparable.
- **INV-CORE-42**: No value written to the `class_full_name` or `method` field of an `RvErrorLog` MUST end with a `(<file>:<line>)` group. The source position belongs in `source` alone.

- **INV-CORE-55**: `modules/rv-android-core/src/rv_android_core/domain/app.py` MUST NOT read the process environment. The `package_detector` value MUST reach `App` as a constructor argument. The three L1 canonical reader locations (`util/validation/config.py`, `util/jar_resolver.py`, `util/android/android.py`) MUST remain the complete set of environment readers inside `rv-android-core`, and `scripts/check_env_vars_drift.py` MUST keep enforcing it.

- **INV-CORE-58**: `App.code_package` MUST apply build-type-suffix neutralization when, and only when, the run states the policy. The rule MUST be the fixed denylist `{debug, dev, beta, staging, qa, nightly, alpha, snapshot, current, head, indev}` with a floor of two remaining segments, compared **in lowercase** and applied **repeatedly** until the last segment is not a denied one. Lowercase comparison is what handles `.BETA`; repeated application is what handles `.qa.debug` and `.debug.HEAD`; the floor is what prevents a two-segment applicationId from being consumed. `App` MUST NOT read the policy from the environment (INV-CORE-55) and MUST receive it as a constructor argument.

- **INV-CORE-59**: The denylist MUST NOT be treated as total: an applicationId whose suffix the denylist does not cover MUST pass through the neutralization unchanged and reach the denominator gate, which refuses the resulting implausible analysis (INV-ANA-69) — the wrong key MUST NOT be silently published. The space of suffixes is open by construction (`com.learntube.app` declares `applicationIdSuffix = ".debug.$branch"`, interpolating a git branch name); the neutralization resolves the common case, the gate carries the guarantee.

- **INV-CORE-60**: `LogcatRepository.register_method_call` MUST count every event it does not register, classifying it as **out-of-scope** when an effective scope key is known and the event's class does not start with it, as **in-scope** when the key is known and the class does start with it, and as **unclassified** when no key is known (`None`, the state of every artefact produced before the key was recorded) — never silently as in-scope. No count MUST be emitted at `logger.debug` alone.

- **INV-CORE-61**: `TaskResult.to_dict()` MUST serialize `write_errors` as the `Dict[str, int]` it is, and `TaskResult.from_dict()` MUST read the key back with its per-artefact counts intact; a `tasks.json` without the key MUST still load, defaulting to `{}`, because the resume protocol reads it. The counts are incremented only during result processing, which runs after every per-task save, so the task store MUST be saved again after result processing — on the live path (`Platform`) and on the standalone `--process-results` path alike. The round trip without that save does not persist anything.

- **INV-CORE-62**: `LoggingManager.setup_file_logging` MUST have a production caller at every entry point that runs an experiment or processes results, so the run's INFO log — including the effective scope key — reaches disk. The method's own `log_path` guard cannot supply the call, since `log_path` is assigned only inside the method it guards.
- **INV-CORE-56**: The `message` part of `unique_msg` MUST NOT contain the substring `:::`. The producer of the message (the monitor's envelope grammar) forbids it inside every value; `RvErrorLog` MUST NOT rewrite the message to hide a violation of that rule, and a reader that splits `unique_msg` on `:::` and finds a part count other than seven MUST count the record as unparsed rather than reinterpret it.
- **INV-CORE-57**: Every published deduplicated count of violations MUST carry the identity era it was computed under. A count of the seven-part era MUST NOT be compared to a count of the five-part era without the discontinuity being stated beside the comparison, and the discontinuity measured on the same input MUST be non-zero where that input's records carry an `ev=` envelope — a zero difference there would mean `code` and `event` added no information to the identity; on a pre-envelope input (the published dataset, comp162) the difference is zero by construction and is labelled so, not read as a failure.
- **INV-CORE-63**: `identity_message` MUST be `message` with every trailing ` vfp='<value>'` and ` vcls='<value>'` that follows the closing quote of `msg` removed, and nothing else removed. A message with no evidence key MUST be its own `identity_message`, byte for byte.
- **INV-CORE-64**: Before every capture, `LogcatManager.start_capture` MUST run `adb -s <serial> logcat -G <LOGCAT_BUFFER_SIZE>` with `LOGCAT_BUFFER_SIZE = "16M"` from `rv_android_core/constants.py`, before the buffer is cleared and before the capture command starts. The capture command itself stays as INV-CORE-37 fixes it. A success MUST be logged at INFO with the device serial and the size; a failure MUST be logged at WARNING with the same two values and MUST NOT prevent the capture.
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
  package_detector: bool         # Elect the package heuristically (default False)
  strip_build_type_suffix: bool  # Neutralize a build-type suffix on the declared applicationId (default False)
  # computed fields:
  path: str                      # os.path.abspath(app_path)
  name: str                      # os.path.basename(app_path)
  package_name: str              # From AndroidManifest.xml (for device ops)
  code_package: str              # package_name, or PackageDetector when enabled
  code_package_source: str       # "manifest" | "manifest-neutralized" | "detector"
  sdk_target: int                # Target SDK version
  permissions: List[str]         # Requested permissions
  min_api: int                   # Minimum API level

Command(BaseValidatedModel):
  command: str                   # Executable name (validated non-empty)
  args: List[str]                # Command arguments
  timeout: Optional[float]       # Seconds (None = no timeout)
```

`App.package_detector` carries a decision made by the user, not one derived from the APK. Which package scopes app-owned classes depends on the corpus under study, so `App` reports the package the APK declares and elects one heuristically only on request. The value is resolved at the entry point the user invoked and passed to the constructor; the domain model reads no environment variable (INV-CORE-55).

`App.strip_build_type_suffix` carries a decision of the same kind, for the other normalization. Normalization of the declared identifier — stripping a build-type suffix — is **not** a property this model invents per corpus, and it is not something the model performs on its own initiative: it is a run-scalar **policy the caller states**, resolved at the same entry point and passed to the same constructor, applied when and only when it is stated. The model still decides nothing. It reads no environment variable (INV-CORE-55), consults no per-APK map or curated key table, and leaves the declared identifier untouched when the policy is off, which is the default.

This supersedes the gh98 decision that normalization "is a property of a particular corpus and belongs to whoever curates it, not to this model". That decision named a responsible party without giving it a channel: the corpus curator had no way to state the repair, so the wrong key kept reaching every consumer of `code_package`. The channel is now the constructor argument, and the responsibility is unchanged — the caller still decides, the model still only obeys.

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

#### Scenario: App reports the declared package by default

- **WHEN** an App is created from the Godot game whose manifest declares `ir.hsn6.trans` and whose implementation classes live under `org.godotengine.godot`, without stating a package preference
- **THEN** `app.package_name` MUST return `"ir.hsn6.trans"`
- **AND** `app.code_package` MUST return `"ir.hsn6.trans"`
- **AND** `app.code_package_source` MUST return `"manifest"`
- **AND** `PackageDetector` MUST NOT be invoked

#### Scenario: App elects the implementation package when the detector is enabled

- **WHEN** an App is created from the same APK with `package_detector=True`
- **THEN** `app.package_name` MUST return `"ir.hsn6.trans"`
- **AND** `app.code_package` MUST return `"org.godotengine.godot"`
- **AND** `app.code_package_source` MUST return `"detector"`
- **AND** a log message MUST be emitted at INFO level indicating the mismatch

#### Scenario: The declared package is reported verbatim, suffix included

- **WHEN** an App is created from `org.fossify.calendar_20.apk`, whose manifest declares `org.fossify.calendar.debug`, without stating a package preference and without stating the neutralization policy
- **THEN** `app.code_package` MUST return `"org.fossify.calendar.debug"`
- **AND** `app.code_package_source` MUST return `"manifest"`
- **AND** no build-type segment MUST be stripped, because the policy is off by default and the model never decides the normalization on its own

#### Scenario: The build-type suffix is neutralized when the policy is on

- **WHEN** an App is created from the same `org.fossify.calendar_20.apk` with `strip_build_type_suffix=True`
- **THEN** `app.package_name` MUST return `"org.fossify.calendar.debug"`, because that is the id the `PackageManager` knows
- **AND** `app.code_package` MUST return `"org.fossify.calendar"`
- **AND** `app.code_package_source` MUST return `"manifest-neutralized"`

#### Scenario: Coverage repository ignores unknown methods

- **WHEN** a LogcatRepository has static analysis data for class "com.example.MyClass" with method signature `<com.example.MyClass: void doSomething()>`, the effective scope key is `com.example`, and `register_method_call()` is called with a RvCoverageLog for class "com.unknown.Other"
- **THEN** the call MUST NOT be registered, because the denominator holds no such method
- **AND** `calculate_metrics().called_methods` MUST remain 0
- **AND** the discard MUST be counted and classified as out-of-scope, because `com.unknown.Other` does not start with the effective scope key
- **AND** the discard MUST NOT be recorded at `logger.debug` alone

#### Scenario: RvErrorLog deduplication

- **WHEN** two RvErrorLog instances are created with the same `class_full_name`, `method`, `spec`, `error_type`, and `message`
- **THEN** both instances MUST have identical `unique_msg` computed properties
- **AND** `error1 == error2` MUST return True
- **AND** `hash(error1) == hash(error2)` MUST return True

### Requirement: Package Key Provenance on the App Model (FR33, NFR06)

`App` MUST expose which mechanism produced `code_package`, as the computed field `code_package_source`, taking the value `"manifest"` when the package was read from the APK manifest verbatim, `"manifest-neutralized"` when it was read from the manifest and had a build-type suffix removed under the run policy, and `"detector"` when it was elected by `PackageDetector`.

The field exists because the choice does not survive in the data it shapes. Two runs over one APK can produce different `code_package` values, and the artefacts downstream carry no trace of which run produced them — measured over the 162 artefacts of the article corpus, zero classes start with the `package` the GATOR JSON records and 162 of 162 start with the key that actually filtered it. Whoever records a run MUST be able to state the key and its origin without re-deriving either. The analysis capability now requires the effective key to be recorded in the artefact (INV-ANA-66); this field is its source.

`App` MUST NOT read an existing analysis artefact to infer a key, and MUST NOT override a caller's choice on the grounds that a stored artefact used a different one. Reconciling stored results with the key they were measured under is data management, outside this model's responsibility.

#### Scenario: Provenance follows the mechanism that ran

- **WHEN** `App(apk_path)` is constructed with no package preference and `code_package` is read
- **THEN** `app.code_package_source` MUST be `"manifest"`

- **WHEN** `App(apk_path, strip_build_type_suffix=True)` is constructed over an APK declaring `org.fossify.paint.debug` and `code_package` is read
- **THEN** `app.code_package_source` MUST be `"manifest-neutralized"`

- **WHEN** `App(apk_path, package_detector=True)` is constructed and `code_package` is read
- **THEN** `app.code_package_source` MUST be `"detector"`

#### Scenario: Provenance is consistent with the returned key

- **WHEN** any `App` instance has been asked for `code_package`
- **THEN** `code_package == package_name` MUST hold whenever `code_package_source == "manifest"`
- **AND** `code_package` MUST be a proper prefix of `package_name` whenever `code_package_source == "manifest-neutralized"`
- **AND** `code_package` MUST equal the `PackageDetector` election whenever `code_package_source == "detector"`

#### Scenario: Neutralization that removes nothing reports the plain origin

- **WHEN** `App(apk_path, strip_build_type_suffix=True)` wraps an APK declaring `org.cry.otp`, which carries no denied suffix
- **THEN** `code_package` MUST be `org.cry.otp`
- **AND** `code_package_source` MUST be `"manifest"`, because no neutralization occurred

#### Scenario: The detector takes precedence when both policies are on

- **WHEN** `App(apk_path, package_detector=True, strip_build_type_suffix=True)` wraps `com.github.cvzi.screenshottile_148`, whose manifest declares `com.github.cvzi.screenshottile` and whose detector election is `com.github.cvzi`
- **THEN** `code_package` MUST be `"com.github.cvzi"`, the detector's election
- **AND** `code_package_source` MUST be `"detector"` — never `"manifest-neutralized"`, even though a neutralization pass over the declared id would also have been possible (INV-CORE-18)

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
`AndroidRuntime:E art:E dalvikvm:E ActivityManager:W` in addition to the baseline tags
`RVSEC:V RVSEC-COV:V ApeRvHb:V`. When the flag is disabled (the default), capture behavior MUST be
the baseline described by INV-CORE-37. The flag SHALL be exposed as a named constant
`ENV_LOGCAT_DIAGNOSTICS = "RV_LOGCAT_DIAGNOSTICS"` in `rv_android_core/constants.py`.

The baseline is three tags rather than two because the APE-RV step heartbeat must survive the
device-side filter; see "APE-RV Step Heartbeat Tag in the Capture Allowlist" below for why the tag
cannot be added at the point of use instead.

#### Scenario: Flag off emits the baseline command byte-for-byte
- **WHEN** `RV_LOGCAT_DIAGNOSTICS` is unset and `start_capture` is called for serial `emulator-5554`
- **THEN** the emitted command is `adb -s emulator-5554 logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V`
- **AND** no diagnostic tag (`AndroidRuntime`, `art`, `dalvikvm`, `ActivityManager`) appears in the filter

#### Scenario: Flag on appends diagnostic tags additively
- **WHEN** `RV_LOGCAT_DIAGNOSTICS=true` and `start_capture` is called
- **THEN** the filter contains `RVSEC:V`, `RVSEC-COV:V` and `ApeRvHb:V` unchanged and in that order
- **AND** the filter additionally contains `AndroidRuntime:E`, `art:E`, `dalvikvm:E`, and `ActivityManager:W`

### Requirement: APE-RV Step Heartbeat Tag in the Capture Allowlist (FR33, FR34)

`LogcatManager.default_tags` SHALL include the APE-RV step heartbeat tag `ApeRvHb`, declared as the
constant `TAG_APERV_HEARTBEAT` in `rv_android_core/util/logging/constants.py` beside `TAG_RVSEC` and
`TAG_RVSEC_COV`, and appended after them so the existing two keep their position and order
(INV-CORE-53).

**Why the allowlist and not the point of use.** Capture is a live stream, not a post-run dump: the
buffer is cleared at start and `adb logcat -s <tags>` runs for the run's duration, so a tag that is
not in the filter when capture begins is discarded at the device and cannot be recovered afterwards
by any consumer. There is no per-tool tag channel — `LogcatComponent` builds the tag list from
`default_tags` for every task regardless of which tool runs — so adding the tag anywhere narrower
would mean inventing that channel for one string. The tag emits nothing for tools that do not write
under it, so the global default costs those runs nothing.

**Why the tag string is not chosen locally.** The jar writes the heartbeat under a fixed tag defined
by the `ape` change `rearch-04-step-ndjson-telemetry` (design D-6, `Log.i("ApeRvHb", "s=<N> t=<tRelMs>")`).
The two sides must name the same string, and a mismatch fails silently: capture succeeds, the file
contains no heartbeat, and the consumer that needed it reports nothing unusual. The constant is
therefore the single place the string appears on this side, and the tag SHALL fit the device's
23-character bound on logcat tags.

Heartbeat lines SHALL be inert to every existing consumer of the captured file (INV-CORE-54).
`parse_logcat_file` dispatches on `RVSEC` and `RVSEC-COV` alone; the heartbeat is neither, so it
contributes to no coverage value, no violation, and no diagnostic event.

#### Scenario: Heartbeat lines survive the device-side filter
- **WHEN** an APE-RV run executes 1,603 steps with the heartbeat flag at its jar-side default and capture runs with `default_tags`
- **THEN** `task.result.logcat_file` SHALL contain 1,603 heartbeat lines under tag `ApeRvHb`
- **AND** their `s` values SHALL match the step numbers of the trace's `StepRecord` lines

#### Scenario: The tag is declared once
- **WHEN** the module's tests search the source tree for the literal `"ApeRvHb"`
- **THEN** it SHALL appear exactly once, as the value of `TAG_APERV_HEARTBEAT`
- **AND** `LogcatManager.default_tags` SHALL be `[TAG_RVSEC, TAG_RVSEC_COV, TAG_APERV_HEARTBEAT]`

#### Scenario: Heartbeat lines change no parsed value
- **WHEN** `parse_logcat_file` runs over a captured logcat containing 1,603 heartbeat lines, and again over the same file with those lines removed
- **THEN** `calculate_metrics()`, `total_errors`, `unique_errors` and every coverage value SHALL be identical between the two runs
- **AND** the diagnostic-event collection SHALL be identical between the two runs

#### Scenario: A run by a tool that writes no heartbeat is unaffected
- **WHEN** a `monkey` task runs with the same `default_tags`
- **THEN** the emitted command SHALL carry `ApeRvHb:V` like every other capture
- **AND** the captured file SHALL contain no line under that tag, and every downstream value SHALL be what it was before this change

### Requirement: The Device Log Buffer Is Sized Before Capture (FR33, NFR06)

`LogcatManager.start_capture` SHALL set the device's log ring buffers to 16 MiB with `adb -s <serial> logcat -G 16M` before it clears the buffer and starts the capture (INV-CORE-64). The size is a named constant, `LOGCAT_BUFFER_SIZE`, in `rv_android_core/constants.py`.

A capture is a live stream of a ring buffer, so a line that `logd` prunes before the host reader receives it is lost without a trace in the file. The default of the campaign image is 2 MiB, which held 46 s of history in a one-minute run; 16 MiB, the largest size Android's developer settings offer, holds eight times that. The sizing runs on every capture rather than once per device because it is cheap and a device may have been rebooted between tasks. It is a separate command, not an extra flag on the capture command, so the capture command stays byte-identical to INV-CORE-37. A failure is logged and the capture proceeds: a smaller buffer loses lines under load, and no capture loses every line.

#### Scenario: the buffer is sized before the capture starts

- **WHEN** `start_capture` is called for serial `emulator-5554` with `clear_buffer=True`
- **THEN** the commands MUST be issued in the order `adb -s emulator-5554 logcat -G 16M`, `adb -s emulator-5554 logcat -c`, `adb -s emulator-5554 logcat -v threadtime -s RVSEC:V RVSEC-COV:V ApeRvHb:V`
- **AND** the third command MUST be byte-identical to the one INV-CORE-37 fixes

#### Scenario: a failed sizing does not stop the capture

- **WHEN** `adb -s emulator-5554 logcat -G 16M` exits non-zero
- **THEN** a WARNING naming `emulator-5554` and the requested size MUST be logged
- **AND** the capture command MUST still be started and `start_capture` MUST return `True` when the capture starts

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
  `error_type`, `code`, `event` and `message` but carry `source` = `ByteString.kt:83` and `ByteString.kt:84`
- **THEN** their `unique_msg` values MUST be identical
- **AND** `error1 == error2` MUST return True
- **AND** `hash(error1) == hash(error2)` MUST return True
- **AND** registering both in a `LogcatRepository` MUST yield `unique_errors` = 1

#### Scenario: errors.csv carries the source column

- **WHEN** `ResultProcessorComponent` generates `errors.csv` for a completed task
- **THEN** the header MUST be
  `apk,rep,timeout,tool,time,spec,class,method,source,code,event,message,unique_msg`
- **AND** each row MUST carry the originating record's `source` value in that column

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

### Requirement: Event Granularity of unique_msg Is Extended and Declared (FR13)

`RvErrorLog.unique_msg` MUST be `"{class_full_name}:::{method}:::{spec}:::{error_type}:::{code}:::{event}:::{message}"`
(INV-CORE-25), where `{message}` is the record's message with the evidence keys `vfp` and `vcls` removed (INV-CORE-63). `code` and `event` are the `code=` and `ev=` values of the message envelope the monitor emitted; when the
message carries no envelope — every record produced by the frozen `jca` set, and every record persisted before this
change — both parts MUST be the sentinel `UNSPECIFIED`, never an empty string, so a legacy record has a readable
seven-part key that is distinguishable from an envelope record whose event was named. The `message` part MUST NOT
contain `:::` (INV-CORE-56): the producer forbids it inside every envelope value, the model does not rewrite the
message to hide a violation of that rule, and a reader that finds a part count other than seven counts the record
as unparsed — a separator inside a part makes the key unreadable to every consumer that splits on it.

The evidence keys are removed from the identity because they carry per-object values — a fingerprint of the bytes the monitor could not trace, the classes of a trust-manager array — and a key that included them would make every run of the same misuse a different record, multiplying `unique_errors` and `mop_errors_unique` by the number of distinct values rather than counting misuses. They stay in `message` itself, and therefore in the `message` column of `errors.csv`, which is where an analysis reads them. Removal is exact: the two keys are recognised only in the trailing position the envelope grammar gives them, after `msg`, and a `vfp=` or `vcls=` inside a quoted value is not a key.

The key MUST be built in exactly one place, `RvErrorLog.unique_msg` in `rv_android_core/domain/log.py`. The four
other construction sites in the tree — `rv_platform/components/result_processor.py:631`, `:999`, `:1038` and
`scripts/regenerate_results/regenerate_container.py:244` — MUST be deleted, and each caller MUST obtain the key
from the domain object (P3). A key assembled elsewhere from the fields would fork the identity the moment the
domain formula changed, which is what this change does.

Because `unique_msg` is `__hash__` and `__eq__` of `RvErrorLog`, the identity of a violation record changes with
this requirement. That is a declared count discontinuity, not a side effect: every deduplicated count computed
before this change (five-part identity) is not comparable to one computed after it (seven-part identity), and any
report of `unique_errors`, `mop_errors_unique` or the `unique_msg` column MUST say which era it belongs to
(INV-CORE-41, INV-CORE-57). The discontinuity measured on the same envelope-carrying input MUST be non-zero; on a pre-envelope input it is zero by construction and is labelled so.

The model documentation MUST state that this key counts at event granularity and is finer than the
`(apk, class, method, spec)` key used to count unique misuses in the thesis and the journal article, and MUST give
the reason: `error_type` separates a sequence violation from a constraint violation in the same method, `event` and
`code` name the transition of the automaton that failed, and `message` names the offending parameter, so two events
under one method are two different misuses.

The documentation MUST state the consequence explicitly — that `unique_errors` and the `mop_errors_unique` column
derived from it are not numerically comparable to a unique-misuse count, nor across identity eras — so that a
reader comparing the two figures does not conclude that one is defective.

#### Scenario: an envelope message yields code and event parts

- **WHEN** an `RvErrorLog` is created with `class_full_name` = `com.example.vault.KeyDeriver`, `method` = `derive`,
  `spec` = `PBEKeySpecSpec`, `error_type` = `ForbiddenMethod`, `code` = `PBEKEYSPEC-FORB-01`, `event` = `f1` and
  `message` = `v=1 code=PBEKEYSPEC-FORB-01 ev=f1 obj=PBEKeySpec val='PBEKeySpec(char[])' exp='PBEKeySpec(char[],byte[],int,int)' msg='forbidden constructor'` (the `<SPEC>` token of a code is the specification name without its `Spec` suffix, upper-cased — `PBEKEYSPEC`, `MESSAGEDIGEST`, `TRUSTMANAGERFACTORY`; list-valued `exp` values are joined with `,`)
- **THEN** `unique_msg` MUST be
  `com.example.vault.KeyDeriver:::derive:::PBEKeySpecSpec:::ForbiddenMethod:::PBEKEYSPEC-FORB-01:::f1:::v=1 code=PBEKEYSPEC-FORB-01 ev=f1 obj=PBEKeySpec val='PBEKeySpec(char[])' exp='PBEKeySpec(char[],byte[],int,int)' msg='forbidden constructor'`
- **AND** splitting it on `:::` MUST yield exactly seven parts, the fifth being `PBEKEYSPEC-FORB-01` and the sixth `f1`

#### Scenario: a legacy `unknown` message yields the sentinels

- **WHEN** an `RvErrorLog` is created from a record of the frozen `jca` set with `class_full_name` = `okio.ByteString`,
  `method` = `digest$okio`, `spec` = `MessageDigestSpec`, `error_type` = `SequenceViolation` and `message` = `unknown`, no envelope present
- **THEN** `code` MUST be `UNSPECIFIED` and `event` MUST be `UNSPECIFIED`
- **AND** `unique_msg` MUST be `okio.ByteString:::digest$okio:::MessageDigestSpec:::SequenceViolation:::UNSPECIFIED:::UNSPECIFIED:::unknown`
- **AND** two such records MUST compare equal and hash equal, so a legacy campaign deduplicates exactly as its records allow

#### Scenario: distinct offending parameters remain distinct events

- **WHEN** two violations occur in `com.apk.axml.APKParser.getCertificateFingerprint` under `MessageDigestSpec` with the same
  `error_type` and the same `message`, one with `event` = `g1` and one with `event` = `d1`
- **THEN** their `unique_msg` values MUST differ
- **AND** `unique_errors` MUST count them as 2
- **AND** the `(apk, class, method, spec)` analysis key MUST count them as 1 unique misuse
- **AND** both counts MUST be understood as correct at their own granularity

#### Scenario: a message containing the separator is counted, not reinterpreted

- **WHEN** a record reaches a reader with `message` = `expecting one of {A:::B} but found C.` and its `unique_msg` therefore splits into eight parts on `:::`
- **THEN** the reader MUST count the record as unparsed
- **AND** MUST NOT take the fifth and sixth parts as `code` and `event`
- **AND** the record MUST NOT be silently dropped from the row total

#### Scenario: the key has one constructor

- **WHEN** the tree is searched for the f-string pattern `:::{` outside `rv_android_core/domain/log.py`
- **THEN** `rv_platform/components/result_processor.py` and `scripts/regenerate_results/regenerate_container.py` MUST contain no occurrence
- **AND** each of those callers MUST read `unique_msg` from the `RvErrorLog` (or its `to_dict()`), never assemble it

#### Scenario: the discontinuity is declared and non-zero

- **WHEN** `unique_errors` is computed for a corpus whose records carry `ev=` envelopes (the differential-harness traces of the change, or the device logcat of its integration task) once with the five-part identity and once with the seven-part identity
- **THEN** the two figures MUST be published side by side, each labelled with its era
- **AND** their difference MUST be non-zero
- **AND** neither figure MUST be presented as a correction of the other

#### Scenario: a pre-envelope corpus is zero by construction

- **WHEN** the same two computations run on `experimento-comp162` or the published dataset, whose records carry no envelope and whose `event` is therefore the sentinel on every row
- **THEN** the two figures are equal, MUST be published labelled `zero by construction`, and MUST NOT be read as the failure of the seven-part identity

#### Scenario: evidence keys do not split the identity

- **WHEN** two `RvErrorLog` records have the same class, method, spec, error type, code `SECRETKEYSPEC-NOBS-00` and event `c1`, and messages that differ only in `vfp='sha256:1111111111111111'` and `vfp='sha256:2222222222222222'` after `msg`
- **THEN** their `unique_msg` values MUST be equal and end in `msg='…'` with no `vfp`
- **AND** each record's `message` MUST still contain its own `vfp`
- **AND** `unique_errors` MUST count them as 1

### Requirement: Build-Type Suffix Neutralization as a Run Policy

`App` SHALL accept a run-scalar policy stating that this corpus was built with a build-type suffix, and SHALL neutralize that suffix when reporting `code_package`. The declared applicationId remains the rule; the policy states that this particular corpus departs from it in a mechanical, reversible way.

The policy MUST be a boolean resolved at the entry point the user invoked and passed to the constructor, propagated to every `App(` construction site by value. It MUST NOT be a per-APK map, a curated key channel, or a lookup table: which package scopes app-owned classes is a property of the corpus under study, and a scalar is the aridity that property has.

The rule SHALL be the denylist recorded in the article's `mneut_scope.py`, applied in lowercase and repeatedly, never reducing the applicationId below two segments.

#### Scenario: A single build-type suffix
- **WHEN** `App(path, strip_build_type_suffix=True)` wraps an APK declaring `br.com.colman.petals.debug`
- **THEN** `code_package` MUST be `br.com.colman.petals`
- **AND** `package_name` MUST remain `br.com.colman.petals.debug`, because that is the id the `PackageManager` knows
- **AND** `code_package_source` MUST be `"manifest-neutralized"`

#### Scenario: A stacked suffix
- **WHEN** an APK declares `com.example.app.qa.debug` and the policy is enabled
- **THEN** `code_package` MUST be `com.example.app`
- **AND** the rule MUST have been applied twice

#### Scenario: A capitalized suffix
- **WHEN** an APK declares `com.example.app.BETA` and the policy is enabled
- **THEN** `code_package` MUST be `com.example.app`

#### Scenario: The floor protects a short applicationId
- **WHEN** an APK declares `com.debug` and the policy is enabled
- **THEN** `code_package` MUST be `com.debug`
- **AND** no segment MUST be removed, because two segments is the floor

#### Scenario: The policy is off by default
- **WHEN** `App(path)` is constructed with no policy stated and the APK declares `br.com.colman.petals.debug`
- **THEN** `code_package` MUST be `br.com.colman.petals.debug`
- **AND** `code_package_source` MUST be `"manifest"`

#### Scenario: A suffix the denylist does not cover
- **WHEN** an APK declares `com.learntube.app.debug.feature-x`, produced by `applicationIdSuffix = ".debug.$branch"`, and the policy is enabled
- **THEN** `code_package` MUST be `com.learntube.app.debug.feature-x`
- **AND** the wrong key MUST NOT pass silently — the denominator gate MUST refuse the resulting analysis (INV-ANA-69)

### Requirement: The Coverage Crossing Counts Its Discards

`LogcatRepository` SHALL count every runtime event it declines to register and SHALL classify the discard by scope. An event whose class does not start with the effective scope key is out-of-scope, and the discard is expected — the weavers instrument by a library deny-list, not by the app key, so library events legitimately arrive. An event whose class is under the key but absent from the denominator, or present with a non-matching signature, is in-scope, and that discard is a defect in the chain.

The two counts MUST be kept separate. Summing them would restore exactly the ambiguity the counters exist to remove.

Both `LogcatRepository` and the `ParserDiagnostics` object that carries the parser's own discard counters live in **rv-android-core**, in `modules/rv-android-core/src/rv_android_core/domain/coverage.py` — not in rv-coverage, which increments the object the repository owns rather than constructing one of its own, because rv-android-core cannot import rv-coverage. The counters added here belong beside them, so the live tracker path and the offline `parse_logcat_file` path count onto the same totals.

#### Scenario: An unknown class
- **WHEN** `register_method_call` receives an event for `br.com.colman.petals.settings.SettingsWorker` and no such class is in the repository, with effective key `br.com.colman.petals`
- **THEN** the event MUST NOT be registered
- **AND** the in-scope discard count MUST be incremented

#### Scenario: A known class with an unknown signature
- **WHEN** the repository holds `br.com.colman.petals.MainActivity` but not the signature `<br.com.colman.petals.MainActivity: void onCreate(android.os.Bundle)>`
- **THEN** the event MUST NOT be registered
- **AND** the in-scope discard count MUST be incremented

#### Scenario: A library event
- **WHEN** the event names `kotlin.jvm.internal.Intrinsics` and the effective key is `br.com.colman.petals`
- **THEN** the out-of-scope discard count MUST be incremented
- **AND** the in-scope count MUST be unchanged

### Requirement: What the Run Counts Reaches Disk

`TaskResult` SHALL serialize `write_errors` in `to_dict()` and read it back in `from_dict()`, the task store SHALL be persisted after result processing, and `LoggingManager.setup_file_logging` SHALL have a production caller.

The second is not a matter of re-enabling existing wiring. `setup_file_logging` is called from `manager.py:147` under `if self.log_path:`, and `log_path` is assigned only inside `setup_file_logging` — the guard can never be true unless the method has already run. Its only caller, `configure_output`, has no production caller of its own. The repair MUST create a call at an entry point.

Because `tasks.json` is what the resume protocol reads, the serialization change MUST be verified in both directions, and `write_errors` MUST keep its shape: a `Dict[str, int]` mapping each output artefact to the number of rows it lost. Flattening it to a list of artefact names would discard the per-artefact count INV-PLT-32 exists to preserve.

Serialization is necessary and not sufficient. `write_errors` is populated only during result processing, and the task store is never saved again after it, so a run that counted a loss still ends with a `tasks.json` that shows none. The repair MUST therefore also persist the store after result processing, on the live path and on the standalone `--process-results` path.

#### Scenario: Write errors survive a round trip
- **WHEN** a `TaskResult` accumulates `write_errors == {"errors.csv": 2, "results.json": 1}` and is serialized to `tasks.json`
- **THEN** `to_dict()` MUST include the mapping with both counts
- **AND** `from_dict()` on that file MUST restore `{"errors.csv": 2, "results.json": 1}`
- **AND** the per-artefact counts MUST NOT be flattened into a list of artefact names

#### Scenario: A tasks.json without the write_errors key still loads
- **WHEN** the resume protocol reads a `tasks.json` with no `write_errors` key
- **THEN** `from_dict()` MUST load it
- **AND** `write_errors` MUST be an empty dict `{}`

#### Scenario: A write error counted during result processing is on disk when the run ends
- **WHEN** result processing fails to write two rows of `errors.csv` for a task, so `_count_write_error` leaves `write_errors == {"errors.csv": 2}` on the in-memory `TaskResult`
- **THEN** the task store MUST be persisted after result processing completes, not only inside the per-task execution loop
- **AND** `tasks.json` read after the run ends MUST carry `{"errors.csv": 2}` for that task

#### Scenario: The standalone result-processing path persists the same counts
- **WHEN** `rv-platform --process-results` reprocesses a finished run and counts one lost row of `results.json`
- **THEN** `tasks.json` MUST carry `{"results.json": 1}` for that task after the command returns
- **AND** the persistence MUST happen on that path as it does on the live path

#### Scenario: The effective key reaches the log file
- **WHEN** a run resolves the effective scope key and logs it at INFO
- **THEN** the file handler MUST be installed
- **AND** the line MUST be present in the run's log file on disk

