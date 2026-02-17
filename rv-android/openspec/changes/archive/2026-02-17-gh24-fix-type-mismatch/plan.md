# Change Plan: gh24-fix-type-mismatch

**Date**: 2026-02-17
**Track**: Quick Path
**Priority**: Low
**GitHub Issue**: [#24](https://github.com/PAMunb/rvsec/issues/24)
**PRD Reference**: N/A
**Domains**: core

## 1. Context

`DynamicTransitionGraph.record_current_to_next()` in `dynamic_wtg.py` has a type mismatch bug. The method calls `record_transition()` passing `action_id` (str) and `action_type` (str) as two separate positional arguments, but `record_transition()` expects a single `actions: List[Dict[str, Any]]` parameter. This causes a `TypeError` at runtime because 4 positional args are passed to a 3-parameter method.

The bug is documented by the existing test `test_record_current_to_next_success`, which asserts that `TypeError` is raised. A companion test `test_record_current_to_next_with_proper_fix` shows the intended behavior: construct `[{"action_id": action_id, "action_type": action_type}]` and pass that as the `actions` argument.

Currently, `record_current_to_next()` has no callers in production code (rv-agent uses `record_transition()` directly), but the method should be correct for future use.

## 2. Scope

Single module: `rv-android-core`. Two files affected: the source file with the bug and its test file.

## 3. File Inventory

| File | Action | Detail |
|------|--------|--------|
| `modules/rv-android-core/src/rv_android_core/domain/dynamic_wtg.py` | Edit lines 417-419 | Remove the TODO comment (line 417-418). Construct `actions = [{"action_id": action_id, "action_type": action_type}]` and pass it to `record_transition()` instead of passing `action_id` and `action_type` as separate args. |
| `modules/rv-android-core/tests/domain/test_dynamic_wtg.py` | Edit lines 727-757 | Replace `test_record_current_to_next_success` (which expects `TypeError`) with a test that verifies the fixed behavior. Remove `test_record_current_to_next_with_proper_fix` (its logic moves into the success test). |

## 4. Execution Order

Single group, no parallelism needed. Fix source first, then update tests.

## 5. Acceptance Criteria

- [ ] `record_current_to_next()` constructs a proper `List[Dict]` from `action_id` and `action_type` before calling `record_transition()`
- [ ] The TODO comment referencing issue #24 is removed
- [ ] `test_record_current_to_next_success` verifies the fixed behavior (no `TypeError`)
- [ ] `test_record_current_to_next_with_proper_fix` is removed (redundant after fix)
- [ ] All existing tests in `test_dynamic_wtg.py` pass
- [ ] No other callers of `record_current_to_next()` are affected
