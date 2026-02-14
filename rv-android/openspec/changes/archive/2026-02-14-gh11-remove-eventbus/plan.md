# Remove Dead EventBus Infrastructure

**GitHub Issue**: #11
**Track**: Quick Path
**Date**: 2026-02-14
**Author**: Pedro Henrique Teixeira Costa (with Claude Code assistance)
**Status**: Active

## 1. Motivation

The EventBus system in rv-android-core was already simplified in gh5 (removed async processing, decorators, history manager, priorities). What remains is a synchronous pub/sub system that publishes 17 event types from ~40 call sites across 3 modules (rv-platform, rv-experiment, rv-coverage) — but has **zero subscribers in production code**. All `subscribe()` calls exist only in EventBus test files.

This is ~650 lines of infrastructure (bus.py 252, models.py 331, handler.py 24, __init__.py 23) providing zero functional value — a P1 (Simplicity) violation. Every `publish_*()` call constructs a rich event object with task_id, config, metrics, etc., sends it to the EventBus... and nothing happens.

### Evidence

| Metric | Value |
|--------|-------|
| Event types defined | 17 |
| Publish calls in production | ~40 |
| **Subscribers in production** | **0** |
| EventBus implementation lines | ~630 |
| EventBus test lines | ~1,500+ (7 test files) |

### Replacement Strategy

Replace all `publish_*()` calls with `logger.info()` or `logger.debug()` calls. The information that was being published (task lifecycle, coverage updates, experiment completion) continues to appear in logs for diagnostic purposes. No coordination, data flow, or side effects depend on events.

## 2. How This Plan Was Produced

1. Deep analysis by 3 LLMs (Gemini, Qwen, Claude) independently identified EventBus as dead infrastructure
2. Comprehensive dependency mapping: grep for all imports, attribute assignments, and usages across all modules
3. Confirmed zero `subscribe()` calls in production code (only in test files)
4. Reviewed archived gh5 change to understand what was already simplified
5. Mapped all spec references (5 domain specs + CLAUDE.md mention EventBus)

## 3. Scope

### Files to DELETE (core infrastructure)

| File | Lines | Content |
|------|-------|---------|
| `modules/rv-android-core/src/rv_android_core/event/bus.py` | 252 | EventBus singleton, publish, subscribe, channels |
| `modules/rv-android-core/src/rv_android_core/event/models.py` | 331 | EventType enum, Event/TaskEvent/ExperimentEvent/CoverageEvent/MOPErrorEvent/TaskToolExecutionEvent/PhaseExecutionModeEvent classes |
| `modules/rv-android-core/src/rv_android_core/event/handler.py` | 24 | EventHandler generic class |
| `modules/rv-android-core/src/rv_android_core/event/__init__.py` | 23 | Exports |
| `modules/rv-android-core/tests/event/test_bus_core.py` | — | EventBus core tests |
| `modules/rv-android-core/tests/event/test_bus_advanced.py` | — | EventBus advanced tests |
| `modules/rv-android-core/tests/event/test_bus_helper_methods.py` | — | Helper method tests |
| `modules/rv-android-core/tests/event/test_handler.py` | — | EventHandler tests |
| `modules/rv-android-core/tests/event/test_handler_integration.py` | — | Handler integration tests |
| `modules/rv-android-core/tests/event/test_error_scenarios.py` | — | Error scenario tests |
| `modules/rv-android-core/tests/event/test_models.py` | — | Event model tests |

After deletion, also remove the empty `event/` directories.

### Files to EDIT (replace publish calls with logging)

#### rv-platform (7 files)

**`modules/rv-platform/src/rv_platform/platform.py`**
- Line 18: Remove `from rv_android_core.event import EventBus`
- Line 60: Remove `self.event_bus = EventBus.get_instance()`
- Lines 274, 278-282: Remove `event_bus=self.event_bus` from TaskExecutor and component constructor args

**`modules/rv-platform/src/rv_platform/execution/executor.py`**
- Lines 24-25: Remove EventBus/EventType/EventChannel imports
- Line 58: Remove `event_bus` parameter
- Line 73: Remove `self.event_bus = event_bus or EventBus.get_instance()`
- Lines 380-393 (`_publish_task_started_event`): Replace entire method body with `self.logger.info(f"Task started: {self.task.id} tool={self.tool.name} apk={self.task.config.apk_name}")`
- Lines 395-408 (`_publish_task_completed_event`): Replace with `self.logger.info(f"Task completed: {self.task.id}")`
- Lines 410-430 (`_publish_task_failed_event`): Replace with `self.logger.error(f"Task failed: {self.task.id} error={error}")`
- Line ~440 (TOOL_STARTED publish): Replace with logger call

**`modules/rv-platform/src/rv_platform/components/emulator.py`**
- Line ~44: Remove `event_bus: Optional[EventBus] = None` parameter
- Line 48: Remove `self.event_bus` assignment
- Lines 130-135 (EMULATOR_STARTED): Replace with `self.logger.info(f"Emulator started for task {self.task.id} device={self.task.config.device_id}")`
- Lines 184-185 (APP_INSTALLED): Replace with `self.logger.info(f"App installed for task {self.task.id}")`

**`modules/rv-platform/src/rv_platform/components/tool_execution.py`**
- Line ~36: Remove `event_bus` parameter
- Line 41: Remove `self.event_bus` assignment
- Lines 102-107 (TOOL_STARTED): Replace with `self.logger.info(f"Tool started: {self.tool.name} for task {self.task.id}")`
- Lines 114-119 (TOOL_STOPPED): Replace with `self.logger.info(f"Tool stopped: {self.tool.name} for task {self.task.id}")`
- Lines 132-137, 149-154 (TASK_FAILED): Replace with logger.error calls

**`modules/rv-platform/src/rv_platform/components/coverage.py`**
- Line ~45: Remove `event_bus` parameter
- Line 55: Remove `self.event_bus` assignment
- Lines 208-215 (COVERAGE_TRACKING_STARTED): Replace with `self.logger.info(f"Coverage tracking started for task {self.task.id}")`
- Lines 249-256 (COVERAGE_TRACKING_STOPPED): Replace with `self.logger.info(f"Coverage tracking stopped for task {self.task.id}")`
- Lines 319-326 (COVERAGE_UPDATED): Replace with `self.logger.info(f"Coverage updated for task {self.task.id}: method={metrics.get('method_coverage', 0):.1%}")`

**`modules/rv-platform/src/rv_platform/components/static_analysis.py`**
- Remove `event_bus` parameter and assignment
- Lines 141-148 (STATIC_ANALYSIS_COMPLETED): Replace with `self.logger.info(f"Static analysis completed for {app_name}")`

**`modules/rv-platform/src/rv_platform/components/logcat.py`** (if it receives event_bus)
- Remove `event_bus` parameter and assignment

#### rv-experiment (6 files)

**`modules/rv-experiment/src/rv_experiment/experiment/experiment_controller.py`**
- Line 15: Remove EventBus/EventType import
- Line 75: Remove `self.event_bus = EventBus.get_instance()`
- Lines 78-80: Remove `event_bus` from component constructor args
- Lines 134-139 (EXPERIMENT_COMPLETED): Replace with `self.logger.info(f"Experiment completed: {self.experiment_id}")`
- Lines 151-156 (EXPERIMENT_FAILED): Replace with `self.logger.error(f"Experiment failed: {self.experiment_id}")`

**`modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py`**
- Line 11: Remove EventBus/EventType/EventChannel import
- Line 46: Remove `self.event_bus = event_bus`
- Lines 91-96 (WORKFLOW_COMPLETED): Replace with `self.logger.info("Pre-processing phase completed")`
- Lines 123+ (MONITOR_GENERATED, INSTRUMENTATION_COMPLETED, STATIC_ANALYSIS_COMPLETED): Replace with logger calls

**`modules/rv-experiment/src/rv_experiment/experiment/workflow/execution_controller.py`**
- Line 15: Remove EventBus import
- Line 60: Remove `self.event_bus = event_bus`
- Line 114: Remove `event_bus=self.event_bus` from Platform constructor

**`modules/rv-experiment/src/rv_experiment/experiment/workflow/post_processor.py`**
- Line 13: Remove EventBus/EventType import
- Line 48: Remove `self.event_bus = event_bus`
- Lines 84, 100 (EXPERIMENT_COMPLETED): Replace with logger calls

**`modules/rv-experiment/src/rv_experiment/experiment/workflow/result_manager.py`**
- Line 20: Remove EventBus import
- Line 64: Remove `self.event_bus = EventBus.get_instance()`

**`modules/rv-experiment/src/rv_experiment/experiment/workflow/workflow_factory.py`**
- Line 6: Remove EventBus import
- Line 44: Remove `self.event_bus = event_bus`
- Lines 58, 67, 81, 93: Remove `event_bus=self.event_bus` from component constructor args

#### rv-coverage (1 file)

**`modules/rv-coverage/src/rv_coverage/analysis/coverage/tracker.py`**
- Lines 14-15: Remove EventBus/Event/EventType/EventChannel imports
- Line 125: Remove `self.event_bus = EventBus.get_instance()`
- Lines 334-355 (MOP_ERROR_DETECTED): Replace with `self.logger.warning(f"MOP violation detected: {error_log.spec} in {error_log.class_full_name}.{error_log.method}")`
- Lines 426-440 (COVERAGE_UPDATED): Replace with `self.logger.debug(f"Coverage updated: method={metrics['method_coverage']:.1%} activities={metrics['activity_coverage']:.1%}")`

#### rv-android-core (1 file)

**`modules/rv-android-core/src/rv_android_core/__init__.py`**
- Remove all event-related exports (Event, EventType, EventChannel, EventBus, EventHandler, TaskEvent, ExperimentEvent, CoverageEvent, MOPErrorEvent, etc.)

### Test files to EDIT (remove EventBus mocks/references)

**`modules/rv-experiment/tests/experiment/test_experiment_controller.py`**
- Line 20: Remove `from rv_android_core.event import EventType`
- Remove any EventBus mock setup and event assertion

**`modules/rv-platform/tests/execution/test_executor.py`**
- Line 7: Remove `from rv_android_core.event import EventBus`
- Remove EventBus mock from fixtures

**`modules/rv-platform/tests/execution/test_resume.py`**
- Line 23: Remove `from rv_android_core.event import EventBus`
- Remove EventBus mock from fixtures

**`modules/rv-platform/tests/components/test_tool_execution.py`**
- Line 7: Remove `from rv_android_core.event import EventBus, EventType`
- Remove EventBus mock and event assertions

### Spec files to UPDATE (5 specs + CLAUDE.md)

**`openspec/specs/core/spec.md`** (major changes)
- Line 9: Rewrite Purpose paragraph — remove EventBus description
- Lines 24-28: Delete entire `event/` directory from component architecture
- Lines 92-113: Delete all Event model definitions
- Lines 179-182: Remove EventBus from module relationship descriptions
- Line 190: Remove "EventBus" from "Produced by rv-android-core" list
- Line 207: Delete Event subclass data flow line
- Line 219: Delete EventBus thread creation line
- Lines 235-244: Delete INV-CORE-01 through INV-CORE-05 (5 invariants)
- Lines 289-338: Delete entire FR33 requirement "Event-Driven Communication" with all 6 scenarios
- Line 348: Revise ErrorHandler callback description

**`openspec/specs/platform/spec.md`** (moderate changes)
- Line 112: Remove "EventBus" from rv-android-core dependency list
- Line 132: Delete `EventBus: Optional[EventBus]` line
- Line 149: Delete EventBus channel/event publishing line
- Line 206: Remove EventBus event expectation from scenario
- Line 280: Delete sentence about executor publishing lifecycle events

**`openspec/specs/experiment/spec.md`** (moderate changes)
- Line 51: Remove EventBus from pipeline diagram
- Line 126: Delete EventBus events line
- Line 129: Remove "EventBus" from dependency list
- Line 157: Delete EventBus events data flow line
- Line 199: Delete INV-EXP-10 invariant
- Line 230: Remove EventBus event expectation from scenario

**`openspec/specs/analysis/spec.md`** (major changes)
- Line 39: Rewrite CoverageTracker paragraph — remove EventBus publishing
- Line 209: Remove "EventBus" from dependency list
- Line 237: Remove "EventBus COVERAGE_UPDATED events" from data destination
- Lines 248-249: Delete both EventBus event output lines
- Line 267 (INV-ANA-04): Delete or rewrite invariant — remove EventBus requirement
- Line 429: Rewrite CoverageTracker description — remove event publishing
- Lines 453-456: Delete "Coverage metrics publication via EventBus" scenario
- Lines 476-509: Remove EventBus references from MOP error detection scenarios

**`openspec/specs/agent/spec.md`** (minimal)
- Line 213: Remove `EventBus` from rv-android-core dependency line

**`CLAUDE.md`** (moderate changes)
- Line 12: Remove "Event-Driven Communication" principle or replace with "Structured Logging"
- Lines 100-101: Remove "EventBus" from rv-android-core service list
- Lines 144-147: Delete entire "Event-Driven Architecture" section
- Line 194: Remove "EventBus" from comment template reference list

## 4. Task Groups (for subagent orchestration)

Total affected files: ~30. Use subagent orchestration per WORKFLOW.md Section 5.

### Group A: Replace publish calls with logging (FIRST — removes all EventBus usage)
- 7 rv-platform production files
- 6 rv-experiment production files
- 1 rv-coverage production file
- **14 files, sequential dependency on nothing**

### Group B: Delete EventBus infrastructure (AFTER Group A)
- Delete `rv-android-core/src/rv_android_core/event/` directory (4 files)
- Delete `rv-android-core/tests/event/` directory (7 test files)
- Update `rv-android-core/__init__.py` (remove exports)
- **12 files (11 delete + 1 edit)**

### Group C: Fix test files (AFTER Group A, parallel with B)
- 4 test files in rv-experiment and rv-platform need mock removal
- **4 files, independent of Group B**

### Group D: Update specs and docs (AFTER Groups A+B, parallel with C)
- 5 spec files + CLAUDE.md
- **6 files, independent of code changes**

### Execution Order
```
Group A (replace publish → logging)
    ├── Group B (delete event/ infrastructure)  ← after A
    ├── Group C (fix test mocks)                ← after A, parallel with B
    └── Group D (update specs + docs)           ← after A+B, parallel with C
```

## 5. Verification

### Automated
```bash
# All module tests
poetry run pytest modules/rv-android-core/tests/ -v
poetry run pytest modules/rv-platform/tests/ -v
poetry run pytest modules/rv-experiment/tests/ -v
poetry run pytest modules/rv-coverage/tests/ -v

# Confirm zero dangling references
grep -r "EventBus\|EventType\|EventChannel\|EventHandler" modules/*/src/ --include="*.py"
grep -r "from rv_android_core.event" modules/ --include="*.py"
grep -r "event_bus" modules/*/src/ --include="*.py"
```

### Manual
- Run a real experiment: `poetry run rv-experiment run --tools monkey --apks-dir ./apks_examples --timeout 60`
- Verify log output contains lifecycle information (task started/completed, coverage updates)
- Confirm no import errors or runtime exceptions

## 6. Acceptance Criteria

- [ ] Zero references to `EventBus`, `EventType`, `EventChannel`, `EventHandler` in `modules/*/src/**/*.py`
- [ ] Zero references to `from rv_android_core.event` in any production or test file
- [ ] Zero `event_bus` attribute assignments in any production file
- [ ] `modules/rv-android-core/src/rv_android_core/event/` directory does not exist
- [ ] `modules/rv-android-core/tests/event/` directory does not exist
- [ ] All existing tests pass (except deleted EventBus tests)
- [ ] Specs updated: FR33 removed, INV-CORE-01..05 removed, INV-EXP-10 removed, INV-ANA-04 revised
- [ ] CLAUDE.md updated: Event-Driven Architecture section removed
- [ ] Former publish calls replaced with equivalent logger.info/warning/error calls
