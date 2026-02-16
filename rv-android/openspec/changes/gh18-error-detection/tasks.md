## 1. ErrorPatternMatcher (TDD)

- [ ] 1.1 Create `modules/rv-agent/tests/unit/services/test_error_pattern_matcher.py` with test cases: known error strings match ("Field required", "Invalid format", "Please enter a valid email"), normal strings don't match ("Submit", "Email", "Password"), exclusion patterns ("Error Log", "Report Error"), confidence threshold filtering, empty screen handling
- [ ] 1.2 Create `modules/rv-agent/src/rv_agent/services/error_detection.py` with `ValidationErrorResult` dataclass and `ErrorPatternMatcher` class — regex patterns derived from rv-screen-parser's `ErrorDetector._detect_text_errors()`
- [ ] 1.3 Verify all unit tests pass for ErrorPatternMatcher

## 2. learn_node Integration (TDD)

- [ ] 2.1 Create `modules/rv-agent/tests/unit/agent/nodes/test_learn_node_error_detection.py` with test cases: error detected -> stuck_screen_count reset + force_fill_input set; no error -> state unchanged; detection disabled via config -> no detection; screen_description missing -> no detection
- [ ] 2.2 Add `_detect_validation_error()` to `learn_node.py` — calls `ErrorPatternMatcher.detect()` with agent's confidence threshold
- [ ] 2.3 Integrate `_detect_validation_error()` into learn_node flow: call before stuck detection (before line ~125), reset `stuck_screen_count` if error detected, set `force_fill_input` in result dict, update `track.learn()` with `error_detected` param
- [ ] 2.4 Verify all learn_node tests pass (new + existing)

## 3. algorithm_node Handling (TDD)

- [ ] 3.1 Create `modules/rv-agent/tests/unit/agent/nodes/test_algorithm_node_error_recovery.py` with test cases: flag set + inputs available -> SET_TEXT action with decision_maker="error_recovery"; flag set + no inputs -> flag cleared, normal flow; flag not set -> unchanged behavior
- [ ] 3.2 Add `_find_next_input_action()` helper to `algorithm_node.py` — iterates TEXT_CHANGE actions on current screen, uses `agent.strategy._prepare_input_action()` to get one with remaining test values
- [ ] 3.3 Add `force_fill_input` check block in `algorithm_node()` after the `force_back_action` check (after line ~75), before deadlock detection
- [ ] 3.4 Add `force_fill_input` routing in `decision_node.py` after the `force_back_action` check
- [ ] 3.5 Verify all algorithm_node and decision_node tests pass (new + existing)

## 4. State and Configuration

- [ ] 4.1 Add `force_fill_input: bool` to `AgentState` in `domain/state.py`
- [ ] 4.2 Init `force_fill_input: False` in `rv_agent.py` initial state dict
- [ ] 4.3 Add `error_detection_enabled: bool = True` and `error_detection_confidence: float = 0.7` to `RVAgentConfig`
- [ ] 4.4 Wire config values to RVAgent: `agent.error_detection_enabled`, `agent.error_confidence`

## 5. Tracking

- [ ] 5.1 Add `track.error()` function: `error(iter, error_texts, confidence)` with category `ERROR`
- [ ] 5.2 Update `track.learn()` signature: add `error_detected: bool = False` parameter
- [ ] 5.3 Update `LEARN` category documentation in module docstring

## 6. Integration Test

- [ ] 6.1 Create integration test: simulate action on error screen -> ErrorPatternMatcher detects error -> learn_node sets force_fill_input -> algorithm_node selects SET_TEXT action
- [ ] 6.2 Create integration test: fill input -> retry button -> no error -> normal flow resumes

## 7. Verification

- [ ] 7.1 Run `uv run pytest modules/rv-agent/tests/unit/ -v` — all pass
- [ ] 7.2 Run `uv run pytest modules/rv-agent/tests/integration/ -v` — all pass
- [ ] 7.3 Run `/rv-verify rv-agent` (tests + lint + type)
- [ ] 7.4 Verify acceptance criteria: validation error detected, stuck counter suppressed, input prioritized, submit action NOT blacklisted, BACK NOT forced
