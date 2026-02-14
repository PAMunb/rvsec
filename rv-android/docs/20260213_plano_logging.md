# Logging System Review and Fix

**Date**: 2026-02-13
**Author**: Pedro Henrique Teixeira Costa (with Claude Code assistance)
**Status**: Active
**Last Updated**: 2026-02-14 (post-audit revision + test strategy)

## 1. Motivation

The logging system has a **fundamental architectural bug**: `LoggingManager` creates handlers on a logger named `'rvandroid'`, but all actual loggers use different name prefixes (`'platform.task_executor'`, `'rv_platform.components.coverage'`, etc.). Since these are NOT children of `'rvandroid'` in Python's logging hierarchy, the `StructuredFormatter` with context support is never used. **Context features have never worked.**

Additional issues found during audit:

| Issue | Severity | Example |
|-------|----------|---------|
| Duplicate error logging | High | 3 ERROR entries per timeout, up to 6 for non-timeout errors |
| Inconsistent logger names | Medium | 5 different naming patterns across modules |
| Awkward log messages | Medium | "Starting stopping coverage tracking" |
| Timeouts logged as ERROR | Medium | Expected behavior treated as error |
| Stale debug `print()` in production code | Medium | `dynamic_wtg.py`, `config.py`, `enhanced_visitor.py` |
| Missing CLI log-level option | Low | rv-platform has no `--log-level` |
| Unused features in LoggingManager | Low | Custom log levels, context_registry, configure_context_display |

### Key Design Questions

**Is LoggingManager over-engineering?** No — the concept is sound (centralized config, context injection, structured formatting). The problem is a broken implementation plus feature creep. Fix + simplify.

**Should rv-agent use it?** Yes — it already depends on rv-android-core. Context injection (iteration, app_name, mode) would be valuable. Defer to a separate issue after the core fix is proven.

## 2. How This Plan Was Produced

Systematic audit of the logging infrastructure across all modules:

1. Read `LoggingManager`, `ContextAdapter`, `StructuredFormatter`, `ErrorHandler` implementations
2. Traced the Python logging hierarchy to identify the root cause of broken context
3. Analyzed actual log output from experiment runs (user-provided examples)
4. Searched all modules for `logging.getLogger`, `print(`, `LOG_START`, `LOG_COMPLETE` usage patterns
5. Compared logger naming conventions across 5+ modules
6. Post-audit: verified every claim against code, traced error propagation paths through `@handle_errors(reraise=True)` on all 6 builtin tools

### Root Cause: Logger Hierarchy Mismatch

```
Python logging hierarchy:
  root (no handlers from LoggingManager)
  ├── platform.task_executor (used by TaskExecutor)
  ├── rv_platform.components.coverage (used by CoverageComponent)
  ├── analysis.coverage.tracker (used by CoverageTracker)
  ├── rv_android_core.util.error.error_handler (used by ErrorHandler)
  └── rvandroid (LoggingManager's handlers + StructuredFormatter here)
      └── (no children — nobody uses this prefix)
```

All loggers propagate to root, not to `'rvandroid'`. The `StructuredFormatter` attached to `'rvandroid'` never formats any log records. Additionally, `manager.py:96-100` checks if root already has handlers and skips setup entirely, making LoggingManager a complete no-op when CLI has called `basicConfig()` first.

---

## 3. Phases

### Phase 1: Fix Root Logger + Delete Unused Features

**Goal**: Make LoggingManager actually work. Highest impact change.

**`modules/rv-android-core/src/rv_android_core/util/logging/manager.py`**
- Line 73: `getLogger('rvandroid')` → `getLogger()` (root logger)
- Lines 96-100: Remove "root already has handlers" guard. LoggingManager should be authoritative — `_setup_default_logging()` already clears handlers with `self.root_logger.handlers = []`, so any previous `basicConfig()` handlers are replaced.
- Line 128: Remove `self.root_logger.propagate = False` (no-op on root logger — root has no parent to propagate to)
- Delete `toggle_context_display()` (lines 288-329) — near-duplicate of `configure_context_display()`, never called in production (only in tests)
- Delete `configure_context_display()` (lines 331-391) — never called in production (only in tests), redundant with `configure_output(console_context=..., file_context=...)`. If `max_context_length` is needed later, add params to `configure_output()`.
- Delete `get_context_display_config()` (lines 393-412) — never called externally (only in tests)
- Delete `context_registry`, `register_context()`, `get_context()` (lines 266-286) — `register_context` is called by `get_logger()` internally, `get_context()` is never called in production
- Line 11: Remove `from rv_android_core.util.error.exceptions import ConfigurationError` — only used by the deleted `toggle_context_display` and `configure_context_display`
- Trim the 45-line docstring to ~10 lines (P1 simplicity, P4 no promotional language)

**`modules/rv-android-core/src/rv_android_core/util/logging/constants.py`**
- Delete custom log levels: `EXPERIMENT_START`, `EXPERIMENT_END`, `TASK_START`, `TASK_END` and their `addLevelName()` calls (lines 4-8, 19-22) — never used in production
- Keep: `ERROR`, `LOG_LEVEL_*` strings, `CONTEXT_*` keys, `LOG_*` templates

**`modules/rv-android-core/src/rv_android_core/util/logging/context_adapter.py`**
- Delete `experiment_start()`, `experiment_end()`, `task_start()`, `task_end()` methods (lines 106-116) — use deleted custom levels
- Delete the import `from rv_android_core.util.logging.constants import EXPERIMENT_START, EXPERIMENT_END, TASK_START, TASK_END` (line 7)

**`modules/rv-android-core/src/rv_android_core/util/logging/formatters.py`**
- `StructuredFormatter.format()` line 76: add missing standard attrs to exclusion set. Current set is missing several standard `LogRecord` attributes that would appear as spurious context. Complete exclusion set:
  ```python
  'args', 'msg', 'message', 'pathname', 'filename',
  'module', 'exc_info', 'exc_text', 'lineno',
  'funcName', 'created', 'msecs', 'relativeCreated',
  'levelname', 'levelno', 'name',
  'stack_info', 'taskName', 'thread', 'threadName',
  'process', 'processName', 'asctime'
  ```

**`modules/rv-experiment/src/rv_experiment/__main__.py`**
- In `configure_logging()` (line 122-126): Remove the `logging.basicConfig()` call that creates a competing handler. Use `LoggingManager.configure_output()` exclusively.
- Keep lines 138-139 (third-party logger silencing) — these use `logging.getLogger(name)` directly and work correctly with the root logger approach.

**Tests — `test_manager.py`**:

Delete tests for removed features:
- `test_toggle_context_display` (line 195)
- `test_toggle_context_display_none_values` (line 218)
- `test_toggle_context_display_validation` (line 233)
- `test_configure_context_display` (line 247)
- `test_configure_context_display_partial` (line 265)
- `test_configure_context_display_validation` (line 281)
- `test_get_context_display_config` (line 305)
- `test_register_context` (line 95)
- `test_get_context` (line 110)
- `test_complex_context_registration` (line 158)

Update existing tests:
- `test_initialization` (line 36): Change `assert manager.root_logger.name == 'rvandroid'` → `assert manager.root_logger.name == 'root'`. Remove `assert manager.context_registry == {}`.

Add new tests:
1. **`test_root_logger_receives_handlers`**: Create a `LoggingManager`, then create a logger via `logging.getLogger("some.unrelated.module")`. Log a message and verify it passes through the root logger's `StructuredFormatter` (check that handler output contains the context brackets `[...]`). This validates the **core fix** — without it, the most critical regression has no test.
2. **`test_logging_manager_overrides_basic_config`**: Call `logging.basicConfig(level=logging.WARNING)` first, then initialize `LoggingManager`. Verify that the root logger's handlers are replaced (not accumulated) and that the level is INFO (LoggingManager's default), not WARNING. This validates removal of the guard at lines 96-100.
3. **`test_get_logger_receives_structured_formatter`**: Create a logger via `get_logger("some.module")` and verify it receives LoggingManager's `StructuredFormatter`. This was the only test originally planned.

**Tests — `test_constants.py`**:

Delete tests for removed custom log levels:
- `test_custom_log_levels_values` (line 19)
- `test_custom_log_levels_registered` (line 27)
- `test_log_levels_ordering` (line 90)

Update import at line 8: Remove `EXPERIMENT_START, EXPERIMENT_END, TASK_START, TASK_END` from the import.

**Tests — `test_context_adapter.py`**:

Delete test for removed methods:
- `test_custom_log_methods` (line 157) — tests `experiment_start()`, `experiment_end()`, `task_start()`, `task_end()`

Update import at line 9: Remove `EXPERIMENT_START, EXPERIMENT_END, TASK_START, TASK_END` from the import.

**Tests — `test_formatters.py`**:

Add new test:
1. **`test_structured_formatter_excludes_all_standard_attrs`**: Create a `LogRecord`, format it with `StructuredFormatter`, and verify that none of the standard `LogRecord` attributes (`args`, `msg`, `message`, `pathname`, `filename`, `module`, `exc_info`, `exc_text`, `lineno`, `funcName`, `created`, `msecs`, `relativeCreated`, `levelname`, `levelno`, `name`, `stack_info`, `taskName`, `thread`, `threadName`, `process`, `processName`, `asctime`) appear as spurious context keys in the `[...]` section. Only custom attributes (e.g., `record.my_custom_key = "value"`) should appear.

**Test fixture update** — `cleanup_instance` in `test_manager.py`:
- **Important**: The fixture must clear `logging.getLogger().handlers = []` after resetting `LoggingManager._instance = None`, because LoggingManager now operates on the root logger. Without this, stale handlers accumulate across tests.

**Note on `basicConfig()` in other modules**: rv-monitor-generator, rv-instrumentation, rv-agent, rv-agent-validation also call `basicConfig()`. These are safe because: (a) they run as standalone CLIs without initializing LoggingManager, so basicConfig works normally, or (b) if LoggingManager initializes later, `_setup_default_logging()` clears and replaces all root handlers. No changes needed now; migration to LoggingManager is future work.

---

### Phase 2: Fix Duplicate Error Logging + Timeout Level

**Goal**: Reduce error log noise. Timeouts as WARNING not ERROR.

**Root Cause — Error Logging Cascade:**

6 tools use `@ErrorHandler.handle_errors(reraise=True)` on `execute_tool_specific_logic`: monkey, droidbot, ape, ares, humanoid (in `rv-tools/builtin/`), and rvagent (in `rvagent-tool/`). The other 3 builtin tools (fastbot, droidmate, qtesting) use `reraise=False` (default), so errors are absorbed by the decorator and never reach `AbstractTool.execute()`'s except block — they are not affected by this change. For the 6 tools with `reraise=True`, errors are caught, logged, and re-raised at each layer. For a **timeout**, before the fix:

1. `_execute_and_check_command()` catches `RVCommandTimeoutError` → logs **INFO** → raises `RVToolTimeoutError`
2. `@handle_errors(reraise=True)` catches it → `_log_error()` → **ERROR** "Error: ..." (Log #1)
3. `AbstractTool.execute()` except block line 237 → **ERROR** with full traceback (Log #2)
4. `AbstractTool.execute()` line 240 → `error_handler.handle_error()` → `_log_error()` → **ERROR** (Log #3)
5. `ToolExecutionComponent.execute()` catches `RVToolTimeoutError` → **INFO** (appropriate)

Result: **3 ERROR + 1 INFO** for a timeout. After the fix: **1 WARNING + 1 INFO**.

For **non-timeout errors**, the cascade is even worse (up to 6 ERROR entries across tool decorator, AbstractTool.execute(), ToolExecutionComponent, and TaskExecutor). After the fix, 3 entries remain at different architectural layers (tool `@handle_errors`, ToolExecutionComponent, TaskExecutor `error_handler`). This is acceptable — each layer adds context at its level.

### Changes

**`modules/rv-android-core/src/rv_android_core/util/error/error_handler.py`** lines 159-162:
- Change timeout log level from ERROR to WARNING:
  ```python
  if isinstance(error, (RVToolTimeoutError, RVCommandTimeoutError)):
      self._logger.warning(f"Timeout: {error}")
      return
  ```

**`modules/rv-android-core/src/rv_android_core/tools/abstract_tool.py`** lines 236-248:
- In `except Exception` block: Remove `self.logger.error()` at line 237 AND `self.error_handler.handle_error()` at lines 240-247. Keep only `raise`. The caller (ToolExecutionComponent) is responsible for logging.
- Rationale: The tool layer should convert exceptions (command→tool timeout) but NOT log them. The component layer decides how to handle and log. The `@handle_errors(reraise=True)` on `execute_tool_specific_logic` already logs the first entry.

**`modules/rv-platform/src/rv_platform/execution/executor.py`** lines 222-226:
- In `execute()` catch block: Remove `self.logger.error(LOG_ERROR.format(...))` at line 223. The `error_handler.handle_error()` at line 219 already logs the error.

**Tests — `test_error_handler_comprehensive.py`**:

Update existing tests:
- `test_log_error_with_timeout_error` (line 276): Change `mock_logger.error.assert_called_once()` → `mock_logger.warning.assert_called_once()`. Change `assert "Error:" in args[0]` → `assert "Timeout:" in args[0]`.
- `test_log_error_with_command_timeout_error` (line 289): Same changes as above.

Add new test:
1. **`test_log_error_non_timeout_still_uses_error_level`**: Call `_log_error()` with a non-timeout exception (e.g., `RVToolExecutionError`) and verify it still logs at ERROR level with `exc_info=True`. This confirms the change is targeted to timeouts only.

**Tests — `test_abstract_tool.py`**:

Add new test:
1. **`test_execute_exception_no_duplicate_logging`**: Mock `execute_tool_specific_logic` to raise `RVToolExecutionError`. Verify that `AbstractTool.execute()` re-raises the exception but does NOT call `self.logger.error()` or `self.error_handler.handle_error()` in the except block. The `@handle_errors(reraise=True)` decorator on `execute_tool_specific_logic` is responsible for logging; the except block in `execute()` should only contain `raise`.

**Result summary:**

| Scenario | Before | After |
|----------|--------|-------|
| Timeout | 3 ERROR + 1 INFO | 1 WARNING + 1 INFO |
| Non-timeout error | up to 6 ERROR | 3 ERROR (tool decorator + component + executor) |

---

### Phase 3: Fix Duplicate Component Lifecycle Messages + LOG_START/LOG_COMPLETE Cleanup

**Goal**: Eliminate patterns like "Stopping coverage tracking" + "Starting stopping coverage tracking". Replace mechanical `LOG_START`/`LOG_COMPLETE` templates with natural messages in coverage.py.

**`modules/rv-platform/src/rv_platform/execution/executor.py`** lines 316-347:
- Remove TaskExecutor's log messages for operations delegated to components. Components log their own lifecycle. Remove:
  - Line 322: `"Starting logcat capture"` — LogcatComponent logs this
  - Line 330: `"Starting coverage tracking"` — CoverageComponent logs this
  - Line 340: `"Stopping coverage tracking"` — CoverageComponent logs this
  - Line 342: `"Processing coverage results"` — CoverageComponent logs this
  - Line 346: `"Stopping logcat capture"` — LogcatComponent logs this
- Keep: line 316 "Installing application" (EmulatorComponent doesn't log this), line 334 "Executing component: {tool}" (this is the orchestrator's job)

**`modules/rv-platform/src/rv_platform/components/coverage.py`**:
- Line 159: `LOG_START.format(phase="initializing coverage tracker")` → `"Initializing coverage tracker"`
- Line 173: `LOG_COMPLETE.format(phase="initializing coverage tracker")` → remove (line 112 already reports "Coverage tracker initialized successfully")
- Line 203: `LOG_START.format(phase="coverage tracking")` → `"Starting coverage tracking"`
- Line 248: `LOG_START.format(phase="stopping coverage tracking")` → `"Stopping coverage tracking"`
- Line 250: `LOG_COMPLETE.format(phase="stopping coverage tracking")` → `"Coverage tracking stopped"`
- Line 293: `LOG_START.format(phase="processing coverage data")` → `"Processing coverage data"`
- Line 332: `LOG_COMPLETE.format(phase="processing coverage data")` → `"Coverage data processing completed"`

**Note**: Other components (logcat.py, emulator.py, tool_execution.py, result_processor.py, static_analysis.py, performance_processor.py) and rv-android-core (command.py, emulator_manager.py, logcat_manager.py) also use `LOG_START`/`LOG_COMPLETE` extensively (~40 uses total). However, these usages produce grammatically correct messages (e.g., `LOG_START.format(phase="emulator RVSec")` → "Starting emulator RVSec"). Only coverage.py produces the awkward "Starting stopping..." pattern. The other components' usage is acceptable and doesn't need changes in this PR.

---

### Phase 4: Standardize Logger Names

**Goal**: One naming convention: full Python module path (matches `__name__`).

### Convention

Logger name = Python module path where the logger is created. One logger per module, not per function or per class.

### Logger Name Renames

| Current Name | New Name | File | API |
|---|---|---|---|
| `platform.task_executor` | `rv_platform.execution.executor` | executor.py:79 | `logging_manager.get_logger()` |
| `platform.task.task_result` | `rv_android_core.domain.task` | task.py:489 | `logging_manager.get_logger()` |
| `platform.task.task_factory` | `rv_android_core.domain.task` | task.py:832 | `logging_manager.get_logger()` |
| `platform.task` | `rv_android_core.domain.task` | task.py:541 | `logging.getLogger()` → change to `logging_manager.get_logger()` |
| `rvandroid_core.domain.widget.Widget` | `rv_android_core.domain.widget` | widget.py:275 | `logging_manager.get_logger()` |
| `rvandroid_core.domain.window.Window` | `rv_android_core.domain.window` | window.py:108 | `logging_manager.get_logger()` |
| `rvandroid_core.domain.window.Windows` | `rv_android_core.domain.window` | window.py:262 | `logging_manager.get_logger()` |
| `analysis.coverage.tracker` | `rv_coverage.analysis.coverage.tracker` | tracker.py:115 | `logging_manager.get_logger()` |

### Per-Function Logger Consolidation

`utils.py` creates ~15 separate loggers with per-function names (e.g., `rv_android_core.util.utils.execute_command`, `rv_android_core.util.utils.file_hash`). Consolidate to a single module-level logger:

| Current Pattern | New Pattern | File |
|---|---|---|
| `logging_manager.get_logger("rv_android_core.util.utils.<func>", {...})` (x15) | Module-level `logger = logging_manager.get_logger("rv_android_core.util.utils")` | utils.py:37,73,97,116,135,169,206,238,266,283,303,321,346,366,462,508 |
| `logging_manager.get_logger("rv_static_analysis...read_static_analysis_files", {...})` | Same as enclosing class logger | static_analysis_parser.py:84 |

### Also Update

- `@log_execution` decorator call at executor.py:36: `logger_prefix="platform.task_executor"` → `"rv_platform.execution.executor"`
- task.py:541: Change from `logging.getLogger('platform.task')` to `logging_manager.get_logger('rv_android_core.domain.task')` (unify API too)

---

### Phase 5: Add --log-level CLI Option + Remove Stale print() Statements

**Goal**: Users can control log verbosity from CLI. Remove debug `print()` from production code.

### CLI Changes

**`modules/rv-platform/src/rv_platform/__main__.py`**:
- Add `--log-level` argument (choices: DEBUG, INFO, WARNING, ERROR, default: INFO)
- Add `--debug` flag as shortcut for `--log-level DEBUG`
- Wire to `LoggingManager.get_instance().configure_output(console_level=level)`

**`modules/rv-experiment/src/rv_experiment/__main__.py`**:
- Add `--log-level` alongside existing `--debug` flag
- Wire both to `LoggingManager.configure_output()`

### Remove Stale print() Statements

Remove debug/diagnostic `print()` from production code. Replace with `logger.debug()` or delete.

**Replace with logging:**
- `rv_android_core/domain/dynamic_wtg.py:75` — `print(f"Recording visit to activity...")` → `logger.debug()`
- `rv_android_core/domain/dynamic_wtg.py:84` — `print(f"Recording tested element...")` → `logger.debug()`
- `rv_experiment/config.py:390,400,403` — `print()` about directory/MOP validation → `logger.info()` / `logger.debug()`
- `rv_screen_parser/screenshot/detectors/enhanced_visitor.py:937` — `print("*** get_screen_description")` → delete (debug leftover)

**Keep as-is (legitimate CLI output):**
- `rv_platform/__main__.py` — All prints are CLI user-facing summaries, tool listings, and status messages. Appropriate use of `print()`.
- `rv_instrumentation/__main__.py` — CLI summaries and progress output
- `rv_static_analysis/__main__.py` — CLI summaries and progress output
- `rv_monitor_generator/__main__.py` — CLI summaries and progress output
- `rv_agent_validation/analysis/*.py` — Report/analysis output scripts
- `rv_android_core/commands/command_result.py:51` — Inside a docstring example, not executed

**Do NOT touch (vendored third-party code):**
- `rv_tools/builtin/qtesting/src/*.py` — Forked QTesting codebase with ~60 print statements. These are in vendored code and should not be modified.

---

### Phase 6 (Separate Issue): rv-agent LoggingManager Adoption

42 files using `logging.getLogger(__name__)`. Mechanical migration to `LoggingManager.get_instance().get_logger(__name__)`. Add context dicts for key files (nodes, strategies, services). Do NOT change `[RVTRACK:*]` tracking system.

Also remove `logging.basicConfig()` from `rv_agent/cli/main.py:35` and replace with `LoggingManager.configure_output()`.

Defer to separate issue after Phase 1 is merged and validated.

---

## 4. Execution Order

Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 (separate issue)

Phases 2-5 are independent of each other (any order after Phase 1). All phases except Phase 6 can be one PR.

## 5. Verification

After each phase:
1. `poetry run pytest modules/rv-android-core/tests/ -v`
2. `poetry run pytest modules/rv-platform/tests/ -v`
3. Real experiment: `poetry run rv-experiment run --tools monkey --apks-dir ./apks_examples --timeout 60`
4. Inspect log output for: context display `[key=value]`, no duplicate messages, timeouts as WARNING, consistent logger names

## 6. Scope Boundaries

**In scope (this PR):** Phases 1-5 — fix the core bug, reduce log noise, standardize names, add CLI options, remove stale prints.

**Out of scope (future work):**
- rv-agent LoggingManager adoption (Phase 6, separate issue)
- `basicConfig()` migration in rv-monitor-generator, rv-instrumentation, rv-agent-validation (safe as-is, migrate when those modules are next touched)
- QTesting vendored code cleanup (not our codebase)
- `LOG_START`/`LOG_COMPLETE` in components other than coverage.py (they produce grammatically correct messages)
