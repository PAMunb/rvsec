## 1. Fix Source

- [x] 1.1 Remove the TODO comment (lines 417-418) from `dynamic_wtg.py`
- [x] 1.2 Fix `record_current_to_next()` to construct `actions = [{"action_id": action_id, "action_type": action_type}]` and pass it to `record_transition()`

## 2. Fix Tests

- [x] 2.1 Replace `test_record_current_to_next_success` to test the fixed behavior (assert transition is returned, current_activity is updated)
- [x] 2.2 Remove `test_record_current_to_next_with_proper_fix` (redundant after fix)

## 3. Verification

- [x] 3.1 Run `uv run pytest modules/rv-android-core/tests/domain/test_dynamic_wtg.py -v`
- [x] 3.2 Confirm all acceptance criteria from plan.md are met
