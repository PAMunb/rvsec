## Purpose

Delta spec for the ErrorHandler `@handle_errors` decorator in rv-android-core. This change adds phase annotation on exceptions when `reraise=True`, enabling callers to retrieve the pipeline phase where the error originated without relying on hardcoded phase strings.

## MODIFIED Invariants

- **INV-CORE-08**: The `@ErrorHandler.handle_errors` decorator MUST catch all exceptions. When `reraise=False` (default), handled exceptions MUST be suppressed (return None). When `reraise=True`, the decorator MUST annotate the exception with `_error_phase` set to the decorator's `phase` parameter (only if `_error_phase` is not already set) and then re-raise the exception regardless of handler outcome.

## MODIFIED Requirements

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
