## 1. ErrorPatternMatcher (TDD)

- [ ] 1.1 Create `modules/rv-agent/tests/unit/services/test_error_pattern_matcher.py` with test cases: known error strings match ("Field required", "Invalid format", "Please enter a valid email"), normal strings don't match ("Submit", "Email", "Password"), exclusion patterns ("Error Log", "Report Error"), confidence threshold filtering, strong pattern minimum confidence (0.8), empty screen handling, `content_description` attribute access
- [ ] 1.2 Create `modules/rv-agent/src/rv_agent/services/error_detection.py` with `ValidationErrorResult` dataclass and `ErrorPatternMatcher` class — regex patterns derived from rv-screen-parser's `ErrorDetector._detect_text_errors()`, confidence calculation with STRONG_PATTERNS minimum, reads `item.view['text']` and `item.view['content_description']`
- [ ] 1.3 Verify all unit tests pass for ErrorPatternMatcher

## 2. learn_node Integration (TDD)

- [ ] 2.1 Create `modules/rv-agent/tests/unit/agent/nodes/test_learn_node_error_detection.py` with test cases: error detected -> stuck_screen_count reset + force_fill_input set + error_recovery_count incremented; no error -> error_recovery_count reset to 0; detection disabled via config -> no detection; screen_description missing -> no detection; error_recovery_count >= MAX_ERROR_RECOVERY -> detection skipped
- [ ] 2.2 Add `_detect_validation_error()` to `learn_node.py` — calls `ErrorPatternMatcher.detect()` with agent's confidence threshold, checks MAX_ERROR_RECOVERY limit
- [ ] 2.3 Integrate `_detect_validation_error()` into learn_node flow: call before stuck detection (before Level 1 check at line ~148), reset `stuck_screen_count` and increment `error_recovery_count` if error detected, reset `error_recovery_count` if no error, set `force_fill_input` in result dict, update `track.learn()` with `error_detected` param
- [ ] 2.4 Verify all learn_node tests pass (new + existing)

## 3. algorithm_node and decision_node Handling (TDD)

- [ ] 3.1 Create `modules/rv-agent/tests/unit/agent/nodes/test_algorithm_node_error_recovery.py` with test cases: flag set + inputs available -> SET_TEXT action with decision_maker="error_recovery"; flag set + no inputs -> flag cleared, normal flow; flag not set -> unchanged behavior
- [ ] 3.2 Create `modules/rv-agent/tests/unit/agent/nodes/test_find_next_input_action.py` with test cases: screen with TEXT_CHANGE actions -> prepared ItemAction returned; no TEXT_CHANGE actions -> None; all values exhausted -> None; screen_description missing -> None
- [ ] 3.3 Add `_find_next_input_action()` helper to `algorithm_node.py` — iterates `screen_desc.items` for TEXT_CHANGE actions, uses `agent.strategy._prepare_input_action()` to get ItemAction with remaining test values
- [ ] 3.4 Add `force_fill_input` check block in `algorithm_node()` after the `force_back_action` return (line 75), before deadlock detection (line 78)
- [ ] 3.5 Add `force_fill_input` routing in `decision_node.py` after the `force_back_action` check (line 47)
- [ ] 3.6 Verify all algorithm_node and decision_node tests pass (new + existing)

## 4. State and Configuration

- [ ] 4.1 Add `force_fill_input: bool` to `AgentState` in `domain/state.py`
- [ ] 4.2 Init `"force_fill_input": False` in `rv_agent.py` initial state dict (next to `force_back_action`)
- [ ] 4.3 Init `error_recovery_count = 0` on RVAgent instance (next to `stuck_screen_count`)
- [ ] 4.4 Add `error_detection_enabled: bool = True` and `error_detection_confidence: float = 0.7` to `RVAgentConfig`
- [ ] 4.5 Wire config values to RVAgent: `agent.error_detection_enabled`, `agent.error_confidence`

## 5. Tracking

- [ ] 5.1 Add `track.error()` function: `error(iter, error_texts, confidence)` with category `ERROR`
- [ ] 5.2 Update `track.learn()` signature: add `error_detected: bool = False` parameter
- [ ] 5.3 Update categories documentation in module docstring (add ERROR category)

## 6. Integration Test

- [ ] 6.1 Create integration test: simulate action on error screen -> ErrorPatternMatcher detects error -> learn_node sets force_fill_input -> decision_node routes to algorithm -> algorithm_node selects SET_TEXT action
- [ ] 6.2 Create integration test: fill input -> retry button -> no error -> normal flow resumes, error_recovery_count reset
- [ ] 6.3 Create integration test: MAX_ERROR_RECOVERY reached -> detection disabled -> normal flow resumes

## 7. Verification (Automated)

- [ ] 7.1 Run `uv run pytest modules/rv-agent/tests/unit/ -v` — all pass
- [ ] 7.2 Run `uv run pytest modules/rv-agent/tests/integration/ -v` — all pass
- [ ] 7.3 Run `/rv-verify rv-agent` (tests + lint + type)
- [ ] 7.4 Verify acceptance criteria: validation error detected, stuck counter suppressed, input prioritized, submit action NOT blacklisted, BACK NOT forced, loop protection active after MAX_ERROR_RECOVERY

## 8. Smoke Test (Manual)

Standalone rv-agent with CryptoApp, `pure_algorithm` mode. Goal: confirm error detection and input filling work on a real Android app with validation errors.

- [ ] 8.1 Run: `cd modules/rv-agent && uv run rv-agent run --package br.unb.cic.cryptoapp --mode pure_algorithm --timeout 120 --debug`
- [ ] 8.2 Verify in logs: `[RVTRACK:ERROR]` appears at least once (validation error detected)
- [ ] 8.3 Verify in logs: `decision_maker=error_recovery` appears (input filling triggered)
- [ ] 8.4 Verify in logs: `action_type=SET_TEXT` follows the error detection (input was filled)
- [ ] 8.5 Verify in logs: the same submit button is clicked again after input filling (action was NOT blacklisted)
- [ ] 8.6 Verify: no `record_action_failure` in logs, no `-9999` penalty scores

## 9. E2E Test (via rv-experiment)

Full pipeline via rv-experiment with instrumented CryptoApp. Goal: confirm that error detection + input filling leads to MOP coverage improvement.

- [ ] 9.1 Run: `uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --specification-set jca --timeout 120`
- [ ] 9.2 Check results: MOP coverage > 0% for MessageDigest or Cipher operations in CryptoApp
- [ ] 9.3 Compare with baseline (run with `error_detection_enabled=False`): error detection run should have equal or higher MOP coverage
- [ ] 9.4 Verify in experiment logs: `[RVTRACK:ERROR]` and `decision_maker=error_recovery` events present
