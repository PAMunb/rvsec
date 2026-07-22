# Plan: Fix coverage.csv Time Offset

**GitHub Issue**: #8
**Workflow**: Quick Path (Analyze -> Fix -> Verify)
**Status**: Complete

## Context

The `time` field in `coverage.csv` showed incorrect values (64-71 seconds instead of 0-7). The field should represent seconds elapsed since the testing tool started executing, but it included pre-processing overhead (emulator boot + app installation).

**Root cause**: `CoverageTracker` was initialized in Phase 2 (before emulator starts) with `tool_execution_start` timestamp, but that timestamp was `None` at initialization time because `mark_tool_execution_start()` was only called later in Phase 3 — after `start_tracking()`. The `or` fallback in `coverage.py:165` caused it to use `start_time` (task creation time) instead.

## Fix

Reorder executor calls: call `mark_tool_execution_start()` BEFORE `coverage_component.start_tracking()` so the timestamp is available when the tracker initializes.

## Files Changed

| File | Change |
|------|--------|
| `modules/rv-platform/src/rv_platform/execution/executor.py` | Reorder `mark_tool_execution_start()` before `start_tracking()` |
| `modules/rv-platform/src/rv_platform/components/coverage.py` | Update `initialize_tracker()` timing reference |
| `modules/rv-coverage/src/rv_coverage/analysis/coverage/tracker.py` | Remove stale TODO comments |

## Acceptance Criteria

- [x] `mark_tool_execution_start()` called BEFORE `coverage_component.start_tracking()` in executor
- [x] `start_tracking()` updates tracker's `tool_execution_start_time` with the now-available timestamp
- [x] First coverage.csv entry shows time 0-3 seconds (not 60+)
- [x] Coverage percentages in summary.csv remain unchanged (only time values change)
- [x] Unit tests verify call ordering and timing reference update
- [x] TODO comments removed from coverage.py and tracker.py

## Resolution

Fixed in commit `0dde083d`: "fix coverage.csv time offset by reordering executor calls, closes #8"
