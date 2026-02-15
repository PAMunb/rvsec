## 1. ErrorPatternMatcher (TDD)

- [ ] 1.1 Create `modules/rv-agent/tests/unit/services/test_error_pattern_matcher.py` with test cases: known error strings match, normal strings don't match, confidence threshold filtering, false positive resistance ("Error Log", "Report Error")
- [ ] 1.2 Create `modules/rv-agent/src/rv_agent/services/error_detection.py` with `ErrorIndicator` dataclass and `ErrorPatternMatcher` class — extract regex patterns from rv-screen-parser's `ErrorDetector._detect_text_errors()`
- [ ] 1.3 Verify all unit tests pass for ErrorPatternMatcher

## 2. learn_node Integration (TDD)

- [ ] 2.1 Create `modules/rv-agent/tests/unit/agent/nodes/test_learn_node_error_detection.py` with test cases: error detected → record_action_failure called, no error → no recording, recovery action set on error
- [ ] 2.2 Add `_check_for_errors()` method to `learn_node.py` — calls ErrorPatternMatcher on current UI elements, records failure on ScreenNode, returns error_type
- [ ] 2.3 Integrate `_check_for_errors()` into learn_node workflow: call after screen capture, before stuck detection; if error detected, set BACK as recovery action
- [ ] 2.4 Verify all unit tests pass for learn_node error integration

## 3. FailedActionScorer Activation

- [ ] 3.1 Create `modules/rv-agent/tests/unit/strategies/ranking/test_failed_action_scorer_with_data.py` — verify scorer returns -9999 when `record_action_failure()` has populated failure data
- [ ] 3.2 Verify existing `FailedActionScorer` works correctly with real failure data (no code changes expected — just test activation)

## 4. Configuration

- [ ] 4.1 Add `error_detection_enabled: bool = True` and `error_detection_confidence_threshold: float = 0.7` to `agent_config.py`
- [ ] 4.2 Wire config into learn_node's `_check_for_errors()` (skip detection if disabled)

## 5. Integration Test

- [ ] 5.1 Create integration test: simulate action → error screen → verify full chain (detection → recording → scoring → recovery action)
- [ ] 5.2 Clean up TODOs resolved by this change: screen_node.py:120 (`record_action_failure` now called), memory_coordinator.py:219 (success tracking improved)

## 6. Verification

- [ ] 6.1 Run `uv run pytest modules/rv-agent/tests/unit/ -v` — all tests pass
- [ ] 6.2 Run `uv run pytest modules/rv-agent/tests/integration/ -v` — all tests pass
- [ ] 6.3 Run `/rv-verify rv-agent` (tests + lint + type)
- [ ] 6.4 Verify acceptance criteria: error detection active, record_action_failure called, FailedActionScorer receives data, BACK triggered on errors
