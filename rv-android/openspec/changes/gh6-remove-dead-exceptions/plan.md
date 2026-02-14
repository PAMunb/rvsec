# Plan: Remove Dead Exception Types and Collapse ErrorHandler

**GitHub Issue**: #6
**Workflow**: Quick Path (Analyze -> Fix -> Verify)
**Branch**: `modules` (current)

## Analysis Summary

Audited all 48 exception types in `exceptions.py` and 30+ handlers in `error_handler.py`.
Result: 25 dead exception types (52%), 6 dead ErrorHandler methods, 30+ redundant handlers.

## KEEP List (23 types)

| # | Exception | Reason |
|---|-----------|--------|
| 1 | RVAndroidError | Root base class |
| 2 | ConfigurationError | 74 raised, 7 caught |
| 3 | NetworkError | Base for ADBError (inheritance chain) |
| 4 | EmulatorError | 3 raised, 1 caught |
| 5 | ADBError | 1 raised, 1 caught |
| 6 | InstrumentationError | 7 raised |
| 7 | AnalysisError | 1 raised, 1 caught |
| 8 | ExecutionError | Base for TaskExecutionError (inheritance chain) |
| 9 | TaskExecutionError | 4 raised |
| 10 | RVValidationError | 21 raised |
| 11 | CommandValidationError | 5 raised |
| 12 | LogcatValidationError | 10 raised, 2 caught |
| 13 | EventProcessingError | 1 raised |
| 14 | RVCommandTimeoutError | 2 raised, 2 caught |
| 15 | JarNotFoundError | 5 raised, 1 caught |
| 16 | RVToolError | Base for 4 active subclasses (inheritance chain) |
| 17 | RVToolExecutionError | 9 raised |
| 18 | RVToolTimeoutError | 2 raised, 1 caught |
| 19 | ToolNotFoundError | 6 raised |
| 20 | ToolRegistrationError | 4 raised |
| 21 | RVExperimentError | Base for RVExperimentExecutionError (inheritance chain) |
| 22 | RVExperimentExecutionError | 3 raised |
| 23 | RVParsingError | 13 raised |

## DELETE List (25 types)

ResourceError, MonitorError, RvTimeoutError, ToolError, LogcatError, CoverageError,
LLMServiceError, ServerLifecycleError, ToolCreationError, ActionExecutionError,
RVTaskError, RVTaskExecutionError, RVTaskConfigurationError, RVTaskTimeoutError,
RVToolConfigurationError, ToolVariantError, PluginError, RVExperimentSetupError,
RVPromptError, RVLLMError, RVLLMConnectionError, RVLLMModelError,
RVLLMProviderError, RVLLMConfigurationError, RVLLMTemplateError

## ErrorHandler Changes

### Remove dead tracking infrastructure
- `_error_counts`, `_error_history`, `_recovery_attempts` dicts
- `_add_to_history()` method
- `get_error_statistics()` method
- `clear_statistics()` method

### Remove dead methods
- `_notify_error_callbacks()` and `_error_callbacks` list
- `handle_error_with_introspection()`
- `create_context()` (static)
- Module-level `error_context()` function (instance method stays)
- `_register_new_exception_handlers()` function

### Collapse 30+ handlers to generic approach
All type-specific handlers do identical work (log + return True/False). The `@handle_errors`
decorator suppresses/re-raises regardless of handler return value. Replace with a single
`_register_builtin_handlers` that registers one handler per base exception class.

### Keep (active core)
- Singleton pattern (`get_instance`, `reset`)
- `handle_error()` method
- `handle_errors()` decorator
- `error_context()` instance method (context manager)
- `register_handler()` / `_handlers` dict
- `_log_error()` method
- `_handle_generic_exception()` (has critical error logic for non-RVAndroid exceptions)

## Tasks

### Task 1: Back up files
- Copy `exceptions.py` and `error_handler.py` to `backup/`

### Task 2: Rewrite exceptions.py
- Remove 25 dead types, keep 23
- Preserve docstrings and inheritance chain
- Expected: ~200 lines (from 419)

### Task 3: Rewrite error_handler.py
- Remove dead tracking, dead methods, module-level functions
- Collapse 30+ handlers to generic approach
- Expected: ~250 lines (from 921)

### Task 4: Update tests
- Remove tests for deleted exceptions and dead methods
- Update remaining tests to match collapsed handler

### Task 5: Update imports across codebase
- Grep for deleted exception names in all modules
- Update any `__init__.py` re-exports

### Task 6: Update CLAUDE.md
- Update key files table (line counts)
- Update exception hierarchy description

## Acceptance Criteria
- [ ] Zero references to deleted exception types in `**/src/**/*.py`
- [ ] Zero references to deleted ErrorHandler methods in `**/src/**/*.py`
- [ ] All event tests pass (76/76)
- [ ] Total test suite: same pass count as before (~894)
- [ ] Commit with `closes #6`
