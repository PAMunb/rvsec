## 0. Dependency Fix

- [x] 0.1 Change `opencv-python>=4.10.0` to `opencv-python-headless>=4.10.0` in `modules/rv-screen-parser/pyproject.toml`
- [x] 0.2 Run `uv sync` and verify: `uv run python -c "import cv2; print(cv2.__version__)"`
- [x] 0.3 Run `uv run pytest modules/rv-screen-parser/tests/ -v` to confirm no regressions

## 1. ErrorDetector Integration Tests — rv-screen-parser (TDD)

Detection accuracy testing belongs in rv-screen-parser where ErrorDetector lives. Tests use real screenshots from `tests/images/` and characterize current behavior. These serve as a baseline — if ErrorDetector is improved later, false-positive tests become regression tests.

Test screenshots (already in `modules/rv-screen-parser/tests/images/`):
- `cryptoapp_009_errors.png` — true positive (2 error indicators, ~52x51 px, conf=0.80)
- `cryptoapp_005_normal.png` — true negative (0 indicators)
- `cryptoapp_001_initial.png` — true negative (0 indicators)
- `hourlyreminder_003_settings.png` — known false positive (15+ indicators, pink theme)
- `dnshero_002_main.png` — known false positive (5 indicators, red mascot, >100 px)
- `hex_003_gameplay.png` — known false positive (2+ indicators, red header/icons)

- [x] 1.1 Create `modules/rv-screen-parser/tests/test_error_detector_integration.py` with test cases using real screenshots:
  - `test_cryptoapp_errors_detected`: 009 → 2 indicators, all COLOR method, conf >= 0.7, size <= 60px
  - `test_cryptoapp_normal_no_errors`: 005 → 0 indicators
  - `test_cryptoapp_initial_no_errors`: 001 → 0 indicators
  - `test_hourlyreminder_known_false_positives`: 003 → documents indicator count and sizes (>= 10 indicators, many > 80px)
  - `test_dnshero_known_false_positives`: 002 → documents indicator count and sizes (>= 3 indicators, some > 100px)
  - `test_hex_known_false_positives`: 003 → documents indicator count (>= 1 indicator)
- [x] 1.2 Run `uv run pytest modules/rv-screen-parser/tests/test_error_detector_integration.py -v` — all pass

## 2. VisualErrorDetector (TDD)

rv-agent wrapper with false-positive filtering. Tests use mocks — detection accuracy is rv-screen-parser's responsibility.

- [x] 2.1 Create `modules/rv-agent/tests/unit/services/test_visual_error_detector.py` with test cases:
  - error detected (mock ErrorDetector returns 2 ErrorIndicators with conf=0.80, size=52x51)
  - no error (mock ErrorDetector returns empty list)
  - missing image returns `detected=False` (cv2.imread returns None)
  - cv2 import failure returns `detected=False`
  - confidence filter (mock returns indicator with conf=0.4 → rejected)
  - size filter (mock returns indicator 150x150 px → rejected by max_indicator_size=80)
  - region filter top (mock returns indicator at y=30 on 1920-height image → rejected, top 5% = y<96)
  - region filter bottom (mock returns indicator at y=1870 on 1920-height image → rejected, bottom 6% = y>1805)
  - region filter pass (mock returns indicator at y=500 → accepted, within content area)
  - count filter (mock returns 8 indicators → rejected by max_indicator_count=5)
  - mixed (mock returns 3 small + 2 large → large rejected, 3 small pass)
- [x] 2.2 Create `modules/rv-agent/src/rv_agent/services/error_detection.py` with `ValidationErrorResult` dataclass (`detected: bool`, `error_indicators: list[ErrorIndicator]`, `confidence: float` = max across indicators, `detection_method: str`, `filtered_by_size: int` = count removed by size filter, `filtered_by_region: int` = count removed by region filter, `filtered_by_count: bool` = True if count filter rejected all) and `VisualErrorDetector` class — wraps `get_error_detector().detect_errors(image, [])` from rv-screen-parser, applies 4-stage filtering (confidence → size → region → count), graceful fallback on import/load failure. Region filter uses percentage thresholds (SYSTEM_BAR_TOP_PERCENT=0.05, SYSTEM_BAR_BOTTOM_PERCENT=0.06) matching `RVAgentStrategy` system action thresholds, requires image height from cv2.imread shape.
- [x] 2.3 Verify all unit tests pass for VisualErrorDetector
- [ ] 2.4 Run `/rv-doc-code modules/rv-agent/src/rv_agent/services/error_detection.py`

## 3. parse_ui_node Screenshot Capture (TDD)

- [x] 3.1 Create `modules/rv-agent/tests/unit/agent/nodes/test_parse_node_screenshot.py` with test cases: hash repeats + detection enabled -> screenshot taken and stored in state; hash differs -> no screenshot (state value is None); detection disabled -> no screenshot; screenshot exception caught -> warning logged, state value is None
- [x] 3.2 Add conditional screenshot capture to `parse_node.py`: after computing `screen_hash`, if `error_detection_enabled` and `screen_hash == state.get("previous_screen_hash")`, call `agent.device.take_screenshot()` and add `"error_detection_screenshot"` to return dict. Screenshot lifecycle: use a fixed path per agent instance or `tempfile.NamedTemporaryFile(suffix=".png", delete=False)` to avoid file accumulation during long runs
- [x] 3.3 Verify all parse_node tests pass (new + existing)

## 4. learn_node Integration (TDD)

- [x] 4.1 Create `modules/rv-agent/tests/unit/agent/nodes/test_learn_node_error_detection.py` with test cases: screenshot available + error detected -> stuck_screen_count reset + force_fill_input set + error_indicators passed + error_recovery_count incremented; no screenshot available (screen changed) -> error_recovery_count reset to 0 + force_fill_input defensively cleared + error_indicators defensively cleared; detection disabled via config -> returns None; error_recovery_count >= MAX_ERROR_RECOVERY + screenshot exists -> detection skipped, counter stays at MAX (does NOT reset to 0); screen changes after MAX_ERROR_RECOVERY -> counter resets to 0; screenshot exists + detection ran + no error found -> counter reset to 0
- [x] 4.2 Add `_detect_validation_error()` to `learn_node.py` — returns `Optional[ValidationErrorResult]`, calls `VisualErrorDetector.detect()` with screenshot path from state and filter params from agent config (loop protection is handled by the 3-way branching in learn_node before this function is called)
- [x] 4.3 Integrate error detection into learn_node flow with 3-way branching (before Level 1 stuck check at line ~148): (a) no screenshot (screen changed) → reset `error_recovery_count` to 0, defensively clear `force_fill_input=False` and `error_indicators=None` in result (prevents phantom fills if flags persisted from a previous iteration where force_restart_app took priority); (b) screenshot exists BUT `error_recovery_count >= MAX_ERROR_RECOVERY` → skip detection, do NOT reset counter (let stuck detection accumulate); (c) screenshot exists AND count < MAX → call `_detect_validation_error()`, if error detected: reset `stuck_screen_count`, increment `error_recovery_count`, set `force_fill_input` + `error_indicators` in result dict; if no error: reset `error_recovery_count` to 0. Update `track.learn()` with `error_detected` param
- [x] 4.4 Verify all learn_node tests pass (new + existing)
- [ ] 4.5 Run `/rv-doc-code modules/rv-agent/src/rv_agent/agent/nodes/learn_node.py` — document `_detect_validation_error` (Tier 1 docstring), add WHY block before 3-way branching explaining counter reset vs. skip vs. detect logic

## 5. algorithm_node and decision_node Handling (TDD)

- [x] 5.1 Create `modules/rv-agent/tests/unit/agent/nodes/test_algorithm_node_error_recovery.py` with test cases: flag set + inputs available (EditText) -> SET_TEXT with decision_maker="error_recovery"; flag set + Spinner match -> CLICK with decision_maker="error_recovery"; flag set + no inputs -> flags cleared, normal flow; flag not set -> unchanged behavior
- [x] 5.2a Create `modules/rv-agent/tests/unit/agent/nodes/test_find_next_input_action.py` with test cases: screen with TEXT_CHANGE actions -> prepared ItemAction returned; no TEXT_CHANGE actions -> None; all values exhausted -> None; screen_description missing -> None
- [x] 5.2b Create `modules/rv-agent/tests/unit/agent/nodes/test_find_associated_input.py` with test cases: overlap match with EditText -> SET_TEXT + 1.2x boost; overlap match with Spinner -> CLICK + 1.1x boost; overlap match with generic component -> CLICK + 1.0x (no boost); below-field heuristic (error 50px below EditText, horizontally aligned) -> score 0.7; no spatial match -> falls back to sequential; empty error_indicators -> None; multiple indicators -> highest-scoring match wins; item with target_view=None -> skipped gracefully
- [x] 5.3 Add spatial association functions to `algorithm_node.py`:
  - Hardcoded constants: `SPATIAL_BELOW_FIELD_SCORE = 0.7`, `SPATIAL_BELOW_FIELD_MAX_PX = 100`. Configurable via RVAgentConfig (task 6.4): `spatial_edittext_boost` (default 1.2), `spatial_spinner_boost` (default 1.1), `spatial_min_match_threshold` (default 0.1)
  - `_calculate_association_score(error_bounds, item_bounds, item_class)` → overlap + widget boost + below-field heuristic
  - `_find_associated_input_action(agent, state)` → spatial match ErrorIndicator → nearest actionable item (TEXT_CHANGE → SET_TEXT, CLICK → CLICK), skip items where `target_view` or `target_view["bounds"]` is None, fallback to `_find_next_input_action()`
  - `_find_next_input_action(agent, state)` → sequential TEXT_CHANGE iteration (fallback)
- [x] 5.4 Add `force_fill_input` check block in `algorithm_node()` after the `force_back_action` block, before deadlock detection — calls `_find_associated_input_action()`, returns SET_TEXT or CLICK, clears `force_fill_input` + `error_indicators`. **Important**: the else branch (no actionable field found) MUST explicitly clear `force_fill_input=False` and `error_indicators=None` before falling through to deadlock detection — LangGraph state persists unless overwritten, so omitting the clear would leave the flag True for the next iteration. Build a `error_recovery_clear` dict and merge it into the return dict of whatever path follows (deadlock or normal selection). Note: do NOT increment any counter here — error recovery counting is handled by `error_recovery_count` in learn_node (avoid the `forced_back_count` double-increment anti-pattern in decision_node+algorithm_node)
- [x] 5.5 Add `force_fill_input` routing in `decision_node.py` after the `force_back_action` check (line 47)
- [x] 5.6 Verify all algorithm_node and decision_node tests pass (new + existing)
- [ ] 5.7 Run `/rv-doc-code modules/rv-agent/src/rv_agent/agent/nodes/algorithm_node.py`
- [x] 5.8 Run `/rv-verify rv-agent` — intermediate verification after largest group: catches complexity anomalies, formatting, type errors, unused imports before proceeding to G6-G8

## 6. State and Configuration

- [x] 6.1 Add `force_fill_input: bool`, `error_detection_screenshot: Optional[str]`, and `error_indicators: Optional[List[ErrorIndicator]]` to `AgentState` in `domain/state.py`
- [x] 6.2 Init `"force_fill_input": False, "error_detection_screenshot": None, "error_indicators": None` in `rv_agent.py` initial state dict
- [x] 6.3 Init `error_recovery_count = 0` on RVAgent instance (next to `stuck_screen_count`)
- [x] 6.4 Add to `RVAgentConfig`:
  - `error_detection_enabled: bool = True` — master switch
  - `error_detection_confidence: float = 0.7` — confidence threshold [0.3, 0.95]
  - `error_max_indicator_size: int = 80` — max px for valid indicator [30, 200]
  - `error_max_indicator_count: int = 5` — max indicators before assuming themed UI [2, 20]
  - `spatial_edittext_boost: float = 1.2` — spatial association EditText priority tiebreaker [1.0, 2.0]
  - `spatial_spinner_boost: float = 1.1` — spatial association Spinner priority tiebreaker [1.0, 2.0]
  - `spatial_min_match_threshold: float = 0.1` — minimum score to accept a spatial match [0.01, 0.5]
- [x] 6.5 Wire config values to RVAgent: `agent.error_detection_enabled`, `agent.error_confidence`, `agent.error_max_indicator_size`, `agent.error_max_indicator_count`, `agent.spatial_edittext_boost`, `agent.spatial_spinner_boost`, `agent.spatial_min_match_threshold`

## 7. Tracking

- [x] 7.1 Add `track.error()` function: `error(iter, indicators_count, confidence, method, filtered_by_size=0, filtered_by_region=0, filtered_by_count=False)` with category `ERROR` — filtering stats provide calibration data for gh9 Optuna to tune size/region/count thresholds
- [x] 7.2 Update `track.learn()` signature: add `error_detected: bool = False` parameter
- [x] 7.3 Update categories documentation in module docstring (add ERROR category)

## 8. Integration Test

- [x] 8.1 Create integration test: screenshot with error indicators -> VisualErrorDetector detects error -> learn_node sets force_fill_input + error_indicators -> decision_node routes to algorithm -> algorithm_node spatially matches EditText -> SET_TEXT action
- [x] 8.2 Create integration test: Spinner error indicator -> spatial match -> CLICK action -> dropdown opens -> normal exploration selects option
- [x] 8.3 Create integration test: fill input -> retry button -> no screenshot (hash changed) -> no error -> normal flow resumes, error_recovery_count reset
- [x] 8.4 Create integration test: MAX_ERROR_RECOVERY reached -> detection disabled, counter stays at MAX (not reset), stuck_screen_count accumulates -> eventually BACK triggers; then screen changes -> counter resets to 0
- [x] 8.5 Create integration test: no spatial match -> falls back to sequential _find_next_input_action()
- [x] 8.6 Create integration test: MAX_ERROR_RECOVERY regression — mock error detection returning error for 4+ consecutive iterations → verify error_recovery_count stays at 3 (NOT reset to 0), verify stuck_screen_count accumulates normally (not suppressed), verify BACK triggers after enough iterations. This tests the 3-way branching prevents the infinite 4-iteration cycle (3 detect + 1 skip-and-reset)
- [x] 8.7 Create integration test: LLM mode + error recovery bypass — set `agent_mode="llm_only"`, trigger error detection → verify `decision_path="algorithm"` and `decision_maker="error_recovery"`, verify LLM is NOT called for this iteration. Ensures error recovery is mode-independent (force_fill_input check in decision_node runs before routing_manager)
- [x] 8.8 Create integration test: concurrent `force_fill_input` + `force_restart_app` — set both flags in learn_node result → verify decision_node routes for restart (higher priority) → verify algorithm_node processes restart (clears force_restart_app) → verify force_fill_input persists → verify learn_node defensive clear resets it when screen changes after restart
- [x] 8.9 Create integration test: screenshot state persistence in LangGraph — verify that `parse_ui_node` ALWAYS sets `error_detection_screenshot` in its return dict (either path or None), never omits it. If omitted, LangGraph state would retain a stale screenshot path from a previous iteration, causing phantom error detections

## 9. Verification (Automated)

- [x] 9.1 Run `uv run pytest modules/rv-screen-parser/tests/test_error_detector_integration.py -v` — all pass
- [x] 9.2 Run `uv run pytest modules/rv-agent/tests/unit/ -v` — all pass
- [x] 9.3 Run `uv run pytest modules/rv-agent/tests/integration/ -v` — all pass
- [x] 9.4 Run `/rv-verify rv-agent` (tests + lint + type)
- [x] 9.5 Verify acceptance criteria: validation error detected visually, stuck counter suppressed, input prioritized via spatial association, submit action NOT blacklisted, BACK NOT forced, loop protection active after MAX_ERROR_RECOVERY, Spinner gets CLICK (not SET_TEXT)
- [x] 9.6 Grep for `record_action_failure` and `FailedActionScorer` in new/modified files — verify gh18 did not connect validation errors to the action failure system (D4)
- [ ] 9.7 Invoke `rv-code-reviewer` via Task tool: `subagent_type=rv-code-reviewer, prompt="Review gh18-error-detection implementation: VisualErrorDetector, parse_node screenshot capture, learn_node 3-way branching, algorithm_node spatial association. Focus on: TDD adherence, error handling, state management, INV-AGT-20 to INV-AGT-27 compliance."`

## 10. Smoke Test (Manual)

Standalone rv-agent with CryptoApp, `pure_algorithm` mode. Goal: confirm visual error detection, spatial association, and input filling work on a real Android app with validation errors.

- [ ] 10.1 Run: `cd modules/rv-agent && uv run rv-agent run --package br.unb.cic.cryptoapp --mode pure_algorithm --timeout 120 --debug`
- [ ] 10.2 Verify in logs: `[RVTRACK:ERROR]` appears at least once (validation error detected)
- [ ] 10.3 Verify in logs: `decision_maker=error_recovery` appears (input filling triggered)
- [ ] 10.4 Verify in logs: `action_type=SET_TEXT` or `action_type=CLICK` follows error detection (input was filled or Spinner opened)
- [ ] 10.5 Verify in logs: the same submit button is clicked again after input filling (action was NOT blacklisted)
- [ ] 10.6 Verify: no `record_action_failure` in logs, no `-9999` penalty scores

## 11. E2E Test (via rv-experiment)

Full pipeline via rv-experiment with instrumented CryptoApp. Goal: confirm that visual error detection + spatial association + input filling leads to MOP coverage improvement.

- [ ] 11.1 Run: `uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --specification-set jca --timeout 120`
- [ ] 11.2 Check results: MOP coverage > 0% for MessageDigest or Cipher operations in CryptoApp
- [ ] 11.3 Compare with baseline (run with `error_detection_enabled=False`): error detection run should have equal or higher MOP coverage
- [ ] 11.4 Verify in experiment logs: `[RVTRACK:ERROR]` and `decision_maker=error_recovery` events present
