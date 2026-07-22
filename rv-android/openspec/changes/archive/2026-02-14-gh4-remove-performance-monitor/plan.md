# Remove PerformanceMonitor from rv-android

**GitHub Issue**: #4
**Track**: Quick Path
**Status**: Complete

## Context

The PerformanceMonitor singleton collects runtime metrics through `measure_time()` context managers and `record_metric()` calls spread across 6 files. No production code ever reads the collected data. The performance CSV output uses TaskResult data, not PerformanceMonitor.

## Files Changed

### Deleted (rv-android-core)
- `util/performance/` directory (performance_monitor.py, configuration.py, __init__.py)
- `tests/util/performance/` directory (test_performance_monitor.py, __init__.py)

### Edited (rv-android-core)
- `util/decorators.py` — removed `measure_performance` parameter from `task_phase` decorator
- `util/diagnostics.py` — removed PerformanceMonitor stats gathering
- `tests/util/test_decorators.py` — removed performance_monitor mocking

### Edited (rv-platform)
- `execution/executor.py` — removed 5 measure_time context managers and 2 record_metric calls
- `components/performance_processor.py` — simplified to basic path only (no PerformanceMonitor dependency)
- `tests/execution/test_executor.py` — removed PerformanceMonitor patches

### Edited (rv-uiautomator)
- `executor/action_executor.py` — removed measure_time wrapper
- `adapter/uiautomator2.py` — removed 10 measure_time wrappers

### Edited (rv-experiment)
- `__main__.py` — removed 5 performance CLI options
- `tests/test_resume_cli.py` — removed performance config from test data

### Edited (rv-screen-parser)
- `parser/screen/visitor/basic_visitor.py` — removed docstring mention

### Documentation
- `CLAUDE.md` (root), `rv-android-core/CLAUDE.md`, `rv-platform/CLAUDE.md`, `rv-uiautomator/CLAUDE.md`

## Acceptance Criteria

- [x] Zero `PerformanceMonitor`/`performance_monitor` references in `modules/**/*.py`
- [x] Performance CSV still generates (uses PerformanceProcessorComponent basic path)
- [x] All affected tests pass (21 passed)
