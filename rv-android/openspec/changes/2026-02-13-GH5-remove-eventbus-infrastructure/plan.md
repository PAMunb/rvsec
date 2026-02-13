# Remove Dead EventBus Infrastructure from rv-android

**GitHub Issue**: #5
**Track**: Quick Path
**Status**: In Progress

## Context

The EventBus in rv-android-core implements a sophisticated event system with async processing (4 worker threads, PriorityQueue), priority-based handler sorting, event history tracking, decorator-based subscriptions, and utility functions. The audit found that production code only uses the synchronous publish side. The entire subscribe side, async processing, history tracking, decorators, and utility functions are unused.

## Audit Results (corrects original plan)

The original plan estimated 7 published EventType values. The actual audit found **17 published** and **14 unused**.

### EventType Values Published (17 — keep)

| EventType | Published In |
|-----------|-------------|
| TASK_STARTED | rv-platform/executor.py |
| TASK_COMPLETED | rv-platform/executor.py |
| TASK_FAILED | rv-platform/executor.py, tool_execution.py |
| EXPERIMENT_COMPLETED | rv-experiment/experiment_controller.py, post_processor.py |
| EXPERIMENT_FAILED | rv-experiment/experiment_controller.py |
| WORKFLOW_COMPLETED | rv-experiment/pre_processor.py |
| EMULATOR_STARTED | rv-platform/emulator.py |
| APP_INSTALLED | rv-platform/emulator.py |
| TOOL_STARTED | rv-platform/tool_execution.py, executor.py |
| TOOL_STOPPED | rv-platform/tool_execution.py |
| MONITOR_GENERATED | rv-experiment/pre_processor.py |
| INSTRUMENTATION_COMPLETED | rv-experiment/pre_processor.py |
| STATIC_ANALYSIS_COMPLETED | rv-experiment/pre_processor.py, rv-platform/static_analysis.py |
| COVERAGE_TRACKING_STARTED | rv-platform/coverage.py |
| COVERAGE_TRACKING_STOPPED | rv-platform/coverage.py |
| COVERAGE_UPDATED | rv-platform/coverage.py, rv-coverage/tracker.py |
| MOP_ERROR_DETECTED | rv-coverage/tracker.py |

### EventType Values Unused (14 — remove)

TASK_CREATED, TASK_CONFIGURED, EXPERIMENT_STARTED, EXPERIMENT_PAUSED, EXPERIMENT_RESUMED, EXPERIMENT_ERROR, WORKFLOW_STARTED, WORKFLOW_FAILED, ORCHESTRATION_EVENT, CUSTOM, COVERAGE_TRACKING_STOPPED (wait — this IS published), ANALYSIS_COMPLETED, EMULATOR_STOPPED, CONFIG_LOADED, CONFIG_SAVED

Correction: 14 unused = TASK_CREATED, TASK_CONFIGURED, EXPERIMENT_STARTED, EXPERIMENT_PAUSED, EXPERIMENT_RESUMED, EXPERIMENT_ERROR, WORKFLOW_STARTED, WORKFLOW_FAILED, ORCHESTRATION_EVENT, CUSTOM, ANALYSIS_COMPLETED, EMULATOR_STOPPED, CONFIG_LOADED, CONFIG_SAVED

### Infrastructure Unused in Production

| Component | Status |
|-----------|--------|
| Async processing (4 worker threads, PriorityQueue) | Zero async calls |
| EventPriority constants | Passed but never consumed (no subscribers) |
| HandlerPriority enum | Only in tests |
| EventHistoryManager | Never queried |
| publish_async() / publish_with_callback() | Zero calls |
| get_history() / get_statistics() | Zero calls |
| @publish_event / @subscribe_to decorators | Zero usage |
| Utils (filter_events_by_*, etc.) | Zero usage |
| EventChannel.DEFAULT | Not used in production (LIFECYCLE, ANALYSIS, ERROR are used) |
| Event subscriptions | Zero subscribers in production |

## Files Changed

### Deleted (rv-android-core)
- `event/decorators.py` — unused decorators
- `event/utils.py` — unused filter utilities
- `tests/event/test_bus_async.py` — async tests
- `tests/event/test_decorators.py` — decorator tests
- `tests/event/test_utils.py` — utils tests

### Rewritten (rv-android-core)
- `event/bus.py` — simplified to synchronous pub/sub (~200 lines)
- `event/models.py` — removed EventPriority, EventHistoryManager, 14 EventType values
- `event/handler.py` — removed HandlerPriority, priority support
- `event/__init__.py` — updated exports

### Updated Tests (rv-android-core)
- `tests/event/test_bus_core.py` — remove priority/async references
- `tests/event/test_bus_advanced.py` — remove history manager tests
- `tests/event/test_bus_helper_methods.py` — remove async_mode/priority params
- `tests/event/test_handler.py` — remove priority tests
- `tests/event/test_handler_integration.py` — remove priority references
- `tests/event/test_error_scenarios.py` — remove async/priority error tests
- `tests/event/test_models.py` — remove EventPriority, EventHistoryManager, unused EventType tests

### Edited (rv-platform)
- `execution/executor.py` — remove EventPriority import, async_mode param
- `components/coverage.py` — remove EventPriority import, priority param
- `components/static_analysis.py` — remove EventPriority import, priority param

### Edited (rv-coverage)
- `analysis/coverage/tracker.py` — remove EventPriority import, priority param

### Edited (rv-experiment)
- `experiment/workflow/pre_processor.py` — remove EventPriority import if present

### Documentation
- `CLAUDE.md` (root) — remove EventPriority/async references
- `rv-android-core/CLAUDE.md` — update event system description

## Acceptance Criteria

- [x] Zero `publish_async`/`publish_with_callback`/`EventHistoryManager`/`EventPriority`/`HandlerPriority` references in `modules/**/*.py`
- [ ] EventType enum has 17 values (the published ones)
- [ ] EventBus has no worker threads, no PriorityQueue, no history tracking
- [ ] No debug print statements in bus.py
- [ ] All tests pass
- [ ] `event/decorators.py` and `event/utils.py` deleted
