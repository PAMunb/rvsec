# Design: Validation Error Detection

**Change**: gh18-error-detection
**GitHub Issue**: [#18](https://github.com/PAMunb/rvsec/issues/18)
**Schema**: rv-sdd

## Context

This design supports change gh18-error-detection, which adds validation error detection and input-filling guidance to rv-agent. Without error detection, the agent clicks submit buttons with empty input fields, gets validation errors, and never fills the inputs — preventing it from reaching monitored operations (MOP) behind form submissions.

**Functional requirements addressed:**
- **FR29** (Stuck State Detection & Recovery): gh18 extends stuck detection by suppressing `stuck_screen_count` when a validation error is detected, preventing false BACK actions on screens where the agent should stay and fill inputs.
- **FR27** (Composite Action Ranking): gh18 adds `error_recovery` as a new decision maker in `algorithm_node`, using spatial association to generate SET_TEXT or CLICK actions for input filling.
- **FR23** (UI Parsing via UIAutomator XML): gh18 adds conditional screenshot capture to `parse_ui_node` when the screen hash repeats.

**Non-functional requirements addressed:**
- **NFR04** (Resilience): `VisualErrorDetector` degrades gracefully when `cv2` is unavailable or image loading fails.
- **NFR06** (Observability): `track.error()` logs detection events with indicator count, confidence, and method.

**Constraints from specs**: Detection is visual-only (color-based via ErrorDetector). Text-based detection for M3 `TextInputLayout.setError()` is documented as future work (D12). The `force_fill_input` flag follows the existing `force_back_action`/`force_restart_app` communication pattern (INV-AG-22). Validation errors MUST NOT connect to `FailedActionScorer` (INV-AG-23).

## 1. Architecture

### Detection Strategy: Visual (Color-Based via ErrorDetector)

CryptoApp validation errors are purely visual (red `!` icon, red input underline) — the UIAutomator dump is **identical** before and after the error. Detection uses `ErrorDetector` from rv-screen-parser, which analyzes screenshots for color-based error indicators.

The detection flow:
1. `parse_ui_node` captures a screenshot when screen hash repeats (same screen after action)
2. `learn_node` passes the screenshot to `VisualErrorDetector`
3. `VisualErrorDetector` calls `get_error_detector().detect_errors(image, [])` from rv-screen-parser
4. Returns a `ValidationErrorResult` with detection status, indicator descriptions, and confidence score

### Integration Point: learn_node

Error detection runs in `learn_node` before stuck detection. learn_node already handles post-execution analysis (stuck detection, action success recording). Error detection is the same category of post-execution analysis.

When a validation error is detected:
- `stuck_screen_count` is reset to 0 (suppress false stuck — the screen may be unchanged, but backing out is wrong)
- `force_fill_input = True` is set in the result state
- `error_recovery_count` is incremented (loop protection — see Section 4)

### Response: Guidance via `force_fill_input` State Flag

The `force_fill_input` flag follows the same pattern as `force_back_action` and `force_restart_app` for learn_node-to-algorithm_node communication. When `algorithm_node` sees this flag along with `error_indicators` (list of `ErrorIndicator` objects with coordinates), it uses spatial association to find the input field closest to an error indicator and generates the appropriate action:

Error indicators can appear near any component type — not just EditText and Spinner. The action generated depends on the matched item's available actions:
- **TEXT_CHANGE action** (EditText, etc.) → SET_TEXT with test value from `InputValueGenerator`
- **CLICK action** (Spinner, Button, etc.) → CLICK to interact

Widget-type boosts (1.2x EditText, 1.1x Spinner) are prioritization tiebreakers when multiple items overlap similarly, not filters.

If spatial association finds no match (no screen item above the minimum threshold), it falls back to sequential iteration of TEXT_CHANGE actions via `_find_next_input_action()`.

This is guidance, not punishment: the agent stays on the screen, fills inputs, and retries the submit action on the next iteration.

### Data Flow

```
parse_ui_node (start of iteration):
  1. Parse UI hierarchy (existing)
  2. Compute screen_hash (existing)
  3. [NEW] If error_detection_enabled AND screen_hash == previous_screen_hash:
     a. Take screenshot via agent.device.take_screenshot()
     b. Store path in state["error_detection_screenshot"]
  4. Continue to decision_node

execute_node (action) -> learn_node:
  1. Update memories (existing)
  2. [NEW] Detect validation errors via VisualErrorDetector:
     a. If state["error_detection_screenshot"] exists:
        VisualErrorDetector.detect(screenshot_path, threshold)
        → returns ValidationErrorResult with error_indicators (list of ErrorIndicator with coords)
     b. Otherwise: skip detection (no screenshot = screen changed normally)
  3. Three-way branching on detection result:
     a. No screenshot (screen changed normally): reset error_recovery_count = 0
     b. Screenshot exists BUT error_recovery_count >= MAX_ERROR_RECOVERY (3): skip detection,
        do NOT reset counter — let stuck detection accumulate normally
     c. Screenshot exists AND error detected AND count < MAX_ERROR_RECOVERY:
        - Reset stuck_screen_count = 0
        - Increment error_recovery_count
        - Set force_fill_input = True + error_indicators in result
        - Log via track.error()
     d. Screenshot exists AND no error detected: reset error_recovery_count = 0
  4. Stuck detection (existing, runs normally — but stuck_screen_count was reset in case 3c, so it won't trigger)
  6. Normal learn flow continues

decision_node:
  [NEW] Check force_fill_input -> route to algorithm

algorithm_node:
  [NEW] Check force_fill_input flag (after force_restart_app and force_back_action checks)
  1. _find_associated_input_action(): spatial match ErrorIndicator coords → nearest actionable item
     a. For each ErrorIndicator, calculate association score with each screen item
     b. Score = overlap + widget-type boost (1.2x EditText, 1.1x Spinner, 1.0x others) + below-field heuristic
     c. Best match above threshold (0.1) → generate action based on matched item's events:
        - TEXT_CHANGE → SET_TEXT with test value from InputValueGenerator
        - CLICK → CLICK to interact (e.g., open dropdown for Spinner)
  2. If no spatial match: fallback to _find_next_input_action() (sequential TEXT_CHANGE iteration)
  3. Return action with decision_maker="error_recovery", clear force_fill_input + error_indicators
  4. If no input found at all: clear flags, fall through to normal flow
```

### Screenshot Flow

```
Iteration N: parse_ui(S_N) → action A_N → execute → learn(S_N hash)
Iteration N+1: parse_ui(S_{N+1}) → if hash(S_{N+1}) == hash(S_N): take screenshot of S_{N+1}
                → action A_{N+1} → execute → learn: uses S_{N+1} screenshot for error detection
```

- Screenshot is taken at parse_ui time (start of iteration), showing the CURRENT screen
- This is the screen AFTER the previous action — the one that may have a validation error
- learn_node uses this screenshot later in the same iteration (before the screen changes from execute)
- Works uniformly for both algorithm and LLM modes
- In LLM mode, `capture_screenshot_node` takes a separate screenshot for LLM consumption — redundant but harmless

## 2. Key Components

| Component | Location | Action |
|-----------|----------|--------|
| `VisualErrorDetector` | `rv_agent/services/error_detection.py` (new) | Wraps rv-screen-parser's `ErrorDetector` with false-positive filtering (size, count) |
| `parse_ui_node` | `rv_agent/agent/nodes/parse_node.py` (modify) | Conditional screenshot capture when screen hash repeats |
| `learn_node` | `rv_agent/agent/nodes/learn_node.py` (modify) | Add `_detect_validation_error()`, set `force_fill_input`, suppress stuck counter |
| `decision_node` | `rv_agent/agent/nodes/decision_node.py` (modify) | Route `force_fill_input` to algorithm |
| `algorithm_node` | `rv_agent/agent/nodes/algorithm_node.py` (modify) | Handle `force_fill_input`, spatial association (`_find_associated_input_action`), sequential fallback (`_find_next_input_action`), generate SET_TEXT or CLICK |
| `AgentState` | `rv_agent/domain/state.py` (modify) | Add `force_fill_input: bool`, `error_detection_screenshot: Optional[str]`, `error_indicators: Optional[List]` |
| `RVAgentConfig` | `rv_agent/config/agent_config.py` (modify) | Add `error_detection_enabled`, `error_detection_confidence`, `error_max_indicator_size`, `error_max_indicator_count` |
| `RVAgent` | `rv_agent/agent/rv_agent.py` (modify) | Wire config, init state fields, init `error_recovery_count` |
| `tracking` | `rv_agent/tracking.py` (modify) | Add `track.error()`, update `track.learn()` with `error_detected` param |

## Mapping: Spec → Implementation

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-AG-20: Validation Error Detection After Action | `learn_node._detect_validation_error()` calls `VisualErrorDetector.detect()` | `test_learn_node_error_detection.py` |
| INV-AG-21: Stuck Counter Suppression | `learn_node()`: `agent.stuck_screen_count = 0` when error detected | `test_learn_node_error_detection::test_stuck_counter_reset` |
| INV-AG-22: Input Filling Guidance via Flag | `algorithm_node()`: `force_fill_input` check → `_find_associated_input_action()` | `test_algorithm_node_error_recovery.py` |
| INV-AG-23: No Action Penalization | Enforced by omission — gh18 does not call `record_action_failure()` | Grep verification (task 9.6) |
| INV-AG-24: Error Recovery Loop Protection | `learn_node._detect_validation_error()`: `error_recovery_count >= MAX_ERROR_RECOVERY` guard | `test_learn_node_error_detection::test_max_recovery` |
| INV-AG-25: Conditional Screenshot Capture | `parse_node.py`: `screen_hash == previous_screen_hash` → `take_screenshot()` | `test_parse_node_screenshot.py` |
| INV-AG-26: Spatial Association | `algorithm_node._find_associated_input_action()`, `_calculate_association_score()` | `test_find_associated_input.py` |
| INV-AG-27: System Region Masking | `VisualErrorDetector.detect()`: region filter stage (top 5%, bottom 6%) | `test_visual_error_detector::test_region_filter_*` |

## 3. API Design

### VisualErrorDetector

```python
from rv_screen_parser.screenshot.models import ErrorIndicator

@dataclass
class ValidationErrorResult:
    detected: bool                        # True if any indicator has confidence >= threshold
    error_indicators: list[ErrorIndicator] # ErrorIndicator objects with x, y, width, height, confidence
    confidence: float                     # max(ind.confidence) across filtered indicators, or 0.0
    detection_method: str                 # "visual_color"

class VisualErrorDetector:
    """Visual validation error detection using rv-screen-parser's ErrorDetector.

    Analyzes screenshots for color-based error indicators (red regions, error
    icons) using ErrorDetector._detect_color_errors(). Reuses the existing
    component via get_error_detector().detect_errors(image, []).

    Confidence flow:
    1. ErrorDetector internally uses an adaptive threshold (0.3-0.95 depending
       on screen content — colorful UIs get higher thresholds to avoid false positives)
    2. VisualErrorDetector filters the returned indicators by the caller's
       confidence_threshold (default 0.7)
    3. Each ErrorIndicator carries its own confidence (0.0 to 1.0)
    4. ValidationErrorResult.confidence = max across filtered indicators

    False-positive filtering:
    ErrorDetector has a known false-positive problem with red/pink-themed apps.
    Empirical testing on 14 apps (70 screenshots) showed:
    - CryptoApp errors: 2 indicators, ~52x51 px each (correct)
    - hourlyreminder (pink theme): 15+ indicators, 5-147 px (all false positives)
    - dnshero (red mascot): 5 indicators, 100-200 px (all false positives)
    - hex (red header): 2 indicators, large regions (all false positives)

    Pattern: real validation errors are small (icons ~30-60 px) and few (1-3).
    False positives are large (buttons, FABs, mascots >80 px) or numerous (>5).

    VisualErrorDetector applies three filters AFTER confidence filtering:
    - max_indicator_size: reject indicators where width OR height > threshold (default 80 px)
    - region filter: reject indicators in system bar areas — top 5% of screenshot
      height (status bar with notification icons, clock, battery) and bottom 6% (navigation
      bar with back/home/recents). These areas contain system-drawn icons that the app
      developer does not control, and validation errors never appear there. With 188+ apps
      in the corpus, system bar false positives would otherwise accumulate across diverse
      device themes. The percentages match the existing thresholds in RVAgentStrategy
      (STATUSBAR_Y_PERCENT=0.05, NAVBAR_Y_PERCENT=0.94) used for system action filtering.
    - max_indicator_count: if total indicators > threshold (default 5), assume red-themed
      UI and reject all — real validation errors don't produce 5+ indicators simultaneously

    Size and count filters are configurable for gh9 calibration. Region filter uses
    percentage-based constants (SYSTEM_BAR_TOP_PERCENT=0.05, SYSTEM_BAR_BOTTOM_PERCENT=0.06)
    consistent with the existing strategy thresholds, making the filter resolution-independent.

    Graceful fallback: returns detected=False if cv2 import fails or image
    cannot be loaded.

    Validated on CryptoApp:
    - Error screenshot (009.png): 2 errors detected, 52x51 px, conf=0.80 → PASS both filters
    - Normal screenshot (005.png): 0 errors detected → PASS
    - hourlyreminder (003.png): 15 errors, sizes 5-147 px → REJECTED by count filter (>5)
    - dnshero (002.png): 5 errors, sizes 100-200 px → REJECTED by size filter (>80 px)
    """

    # System bar exclusion zones — indicators in these areas are system icons,
    # not validation errors. Percentages match RVAgentStrategy thresholds
    # (STATUSBAR_Y_PERCENT=0.05, NAVBAR_Y_PERCENT=0.94) for consistency.
    SYSTEM_BAR_TOP_PERCENT = 0.05    # Top 5%: status bar (notifications, clock, battery)
    SYSTEM_BAR_BOTTOM_PERCENT = 0.06 # Bottom 6%: navigation bar (back, home, recents)

    def detect(
        self,
        screenshot_path: str,
        confidence_threshold: float = 0.7,
        max_indicator_size: int = 80,
        max_indicator_count: int = 5,
    ) -> ValidationErrorResult:
        """Detect visual error indicators in a screenshot.

        Loads the image via cv2.imread(), passes it to ErrorDetector.detect_errors(),
        and applies four filtering stages:
        1. Confidence filter: reject indicators below confidence_threshold
        2. Size filter: reject indicators where width OR height > max_indicator_size
        3. Region filter: reject indicators in system bar areas (top 5% or bottom 6%
           of the screenshot height) — these contain system icons, not validation errors.
           Uses the same percentages as RVAgentStrategy's system action detection.
        4. Count filter: if remaining indicators > max_indicator_count, return detected=False
           (assumes red-themed UI, not real validation errors)

        Coordinates are in device pixel space — screenshot coordinates equal device
        coordinates (adb screencap = device resolution, no conversion needed).

        Args:
            screenshot_path: Path to screenshot file (PNG).
            confidence_threshold: Minimum confidence to consider error detected.
            max_indicator_size: Maximum width or height in pixels for a valid
                error indicator. Indicators larger than this are likely UI elements
                (buttons, FABs), not error icons. Default 80 px.
            max_indicator_count: Maximum number of indicators before assuming
                the screen has a red/pink theme rather than actual errors.
                Default 5.

        Returns:
            ValidationErrorResult with detection status and ErrorIndicator objects.
        """
```

### learn_node Integration

```python
# Maximum consecutive error recovery attempts before giving up and letting
# normal flow handle the situation (prevents infinite fill-detect loops).
MAX_ERROR_RECOVERY = 3

def _detect_validation_error(agent: "RVAgent", state: AgentState) -> Optional[ValidationErrorResult]:
    """Detect validation errors on current screen via visual analysis.

    Called before stuck detection. When a validation error is detected,
    resets stuck_screen_count to prevent false stuck detection and
    signals algorithm_node to prioritize input filling.

    Visual detection requires a screenshot (captured by parse_ui_node when
    screen hash repeats). If no screenshot is available, detection is skipped
    — this means the screen changed normally and there is no error to detect.

    Note: Loop protection (MAX_ERROR_RECOVERY) and counter reset logic are
    handled by the 3-way branching in learn_node BEFORE this function is
    called. This function only performs the actual detection.

    Args:
        agent: RVAgent with error_confidence config.
        state: Current agent state with error_detection_screenshot.

    Returns:
        ValidationErrorResult if error detected (with error_indicators),
        None if no error detected or detection skipped.
    """
    if not getattr(agent, 'error_detection_enabled', True):
        return None

    screenshot_path = state.get("error_detection_screenshot")
    if not screenshot_path:
        return None

    detector = VisualErrorDetector()
    result = detector.detect(
        screenshot_path,
        confidence_threshold=agent.error_confidence,
        max_indicator_size=agent.error_max_indicator_size,
        max_indicator_count=agent.error_max_indicator_count,
    )

    if result.detected:
        logger.info(
            f"Validation error detected: {len(result.error_indicators)} indicators, "
            f"confidence={result.confidence:.2f}"
        )

    return result if result.detected else None
```

Integration in `learn_node()`:
```python
# Before stuck detection (before the Level 1 check at line ~148):
# Three-way branching: separate "screen changed" from "max recovery reached"
# to avoid resetting the counter when the limit is hit (which would create
# an infinite 4-iteration cycle — see Claude analysis Bug #1).
screenshot_path = state.get("error_detection_screenshot")
error_result = None

if not screenshot_path:
    # Screen changed (hash differs) → no screenshot → reset counter
    agent.error_recovery_count = 0
    # Defensive clear: prevent phantom fills if flags persisted from a previous
    # iteration (e.g., force_restart_app took priority over force_fill_input)
    result["force_fill_input"] = False
    result["error_indicators"] = None
elif agent.error_recovery_count >= MAX_ERROR_RECOVERY:
    # At limit → skip detection, do NOT reset counter
    # This lets stuck_screen_count accumulate normally until BACK triggers
    pass
else:
    error_result = _detect_validation_error(agent, state)
    if error_result:
        agent.stuck_screen_count = 0  # Suppress false stuck
        agent.error_recovery_count += 1
    else:
        # Detection ran but found no error → reset counter
        agent.error_recovery_count = 0

# ... existing stuck detection runs (but won't trigger because count was reset) ...

# In result dict construction (after the force_restart/force_back block):
if error_result:
    result["force_fill_input"] = True
    result["error_indicators"] = error_result.error_indicators
```

### parse_ui_node Screenshot Capture

```python
# After computing screen_hash (line 55), check if hash repeats:
error_detection_screenshot = None
if (getattr(agent, 'error_detection_enabled', False)
    and screen_hash
    and screen_hash == state.get("previous_screen_hash")):
    try:
        error_detection_screenshot = agent.device.take_screenshot()
    except Exception as e:
        logger.warning(f"Error detection screenshot failed: {e}")

# Add to return dict:
# "error_detection_screenshot": error_detection_screenshot
```

### algorithm_node Handling

```python
# Spatial association constants (adapted from rvandroid ErrorAssociationStrategy)
SPATIAL_EDITTEXT_BOOST = 1.2      # EditText is the primary error target
SPATIAL_SPINNER_BOOST = 1.1       # Spinner also shows validation errors
SPATIAL_BELOW_FIELD_SCORE = 0.7   # Error positioned below a field (common validation pattern)
SPATIAL_BELOW_FIELD_MAX_PX = 100  # Max pixels below field to consider "below"
SPATIAL_MIN_MATCH_THRESHOLD = 0.1 # Minimum score to accept a spatial match

# After force_back_action return (line 75), before deadlock detection (line 78):
if state.get("force_fill_input", False):
    input_action = _find_associated_input_action(agent, state)
    if input_action:
        coords = input_action.get_execution_coordinates()
        x, y = coords if coords else (0, 0)
        action_type = input_action.action_type.upper()
        # Action type depends on matched item: SET_TEXT for text inputs, CLICK for others
        if action_type == "SET_TEXT":
            logger.info(f"Error recovery: filling input at ({x}, {y})")
            return {
                "current_action": {
                    "action_type": "SET_TEXT",
                    "x": x,
                    "y": y,
                    "text": input_action.text_input or "",
                    "source": "algorithm",
                    "reason": "error_recovery_fill_input",
                },
                "current_item_action": input_action,
                "decision_maker": "error_recovery",
                "force_fill_input": False,
                "error_indicators": None,
            }
        else:
            # CLICK for Spinner, Button, or any other actionable component
            logger.info(f"Error recovery: clicking component at ({x}, {y})")
            return {
                "current_action": {
                    "action_type": "CLICK",
                    "x": x,
                    "y": y,
                    "text": "",
                    "source": "algorithm",
                    "reason": "error_recovery_interact",
                },
                "current_item_action": input_action,
                "decision_maker": "error_recovery",
                "force_fill_input": False,
                "error_indicators": None,
            }
    else:
        # No actionable field found — clear flags, fall through to normal flow
        logger.info("Error recovery: no actionable field found, resuming normal flow")
        # Fall through with flags cleared — next line is deadlock detection
```

### `_find_associated_input_action()` — Spatial Association

```python
def _find_associated_input_action(
    agent: "RVAgent", state: AgentState
) -> Optional[Any]:
    """Find the actionable screen item closest to an error indicator via spatial association.

    Uses geometric overlap between ErrorIndicator bounding boxes and screen item
    bounds, with widget-type boosts and a below-field heuristic. Adapted from the
    rvandroid ErrorAssociationStrategy (geometric overlap for error→field mapping).

    Error indicators can appear near any component type (EditText, Spinner, Button,
    etc.). The algorithm is generic — it matches any screen item with actionable
    events. Widget-type boosts (1.2x EditText, 1.1x Spinner) serve as prioritization
    tiebreakers, not filters.

    Algorithm:
    1. Get error_indicators from state (ErrorIndicator objects with x, y, width, height)
    2. Get screen_description items with their bounds
    3. For each ErrorIndicator:
       a. For each screen item with actionable events (CLICK, TEXT_CHANGE, etc.):
          - Skip items where target_view or target_view["bounds"] is None
          - Calculate overlap between error bounds and item bounds
          - Apply widget-type boost: 1.2x for EditText, 1.1x for Spinner (tiebreakers)
          - If overlap < 0.1: check below-field heuristic (error up to 100px below item,
            horizontally aligned within item width)
          - Track best (item, action, score)
    4. If best score >= SPATIAL_MIN_MATCH_THRESHOLD (0.1):
       - TEXT_CHANGE action → _prepare_input_action() for SET_TEXT with test value
       - CLICK action → return the CLICK action directly
    5. If no spatial match: fallback to _find_next_input_action() (sequential)

    Coordinate space: ErrorIndicator coordinates and screen item bounds are both
    in device pixel space (screenshot == device resolution, no conversion needed).

    Args:
        agent: RVAgent with strategy containing _prepare_input_action()
        state: Current agent state with error_indicators, screen_description, screen_hash

    Returns:
        ItemAction ready for execution, or None if no suitable input found.
    """
```

### `_calculate_association_score()` — Scoring Algorithm

```python
def _calculate_association_score(
    error_bounds: tuple,  # (x, y, width, height) from ErrorIndicator
    item_bounds: tuple,   # (x, y, width, height) from screen item
    item_class: str       # Widget class name (e.g., "EditText", "Spinner")
) -> float:
    """Calculate how strongly an error indicator is associated with a screen item.

    Works with any component type. Widget boosts are tiebreakers, not filters.

    Score components:
    1. Overlap: intersection area / smaller area (0.0-1.0)
    2. Widget boost (tiebreaker): 1.2x for EditText, 1.1x for Spinner, 1.0x for others
    3. Below-field heuristic: if overlap < 0.1 and error is positioned below the
       item (within SPATIAL_BELOW_FIELD_MAX_PX), horizontally aligned within item
       width → return SPATIAL_BELOW_FIELD_SCORE (0.7)

    Returns:
        Association score (higher = stronger association)
    """
```

### `_find_next_input_action()` — Sequential Fallback

```python
def _find_next_input_action(
    agent: "RVAgent", state: AgentState
) -> Optional[Any]:
    """Find the next unfilled input action on the current screen (sequential).

    Used as fallback when spatial association finds no match. Iterates all
    screen items looking for TEXT_CHANGE actions with remaining test values.

    Algorithm:
    1. Get current screen_hash and screen_description from state
    2. Iterate screen_desc.items looking for items with TEXT_CHANGE actions
       (these are EditText/input fields)
    3. For each TEXT_CHANGE ItemAction found:
       a. Call agent.strategy._prepare_input_action(item_action, screen_hash)
       b. If it returns an ItemAction (has remaining test values), return it
       c. If it returns None (all values exhausted for this field), try next
    4. If no input field has remaining values, return None

    This reuses the existing _prepare_input_action() which:
    - Computes element_id from the action's widget_id
    - Checks InputValueGenerator for remaining test values
    - Returns an ItemAction with text_input set, or None if exhausted

    Args:
        agent: RVAgent with strategy containing _prepare_input_action()
        state: Current agent state with screen_description and screen_hash

    Returns:
        ItemAction with text_input set, or None if no input available.
    """
    screen_hash = state.get("current_screen_hash")
    screen_desc = state.get("screen_description")
    if not screen_hash or not screen_desc:
        return None

    for item in screen_desc.items:
        for item_action in item.actions:
            if item_action.event == WidgetEventType.TEXT_CHANGE:
                prepared = agent.strategy._prepare_input_action(
                    item_action, screen_hash
                )
                if prepared:
                    return prepared

    return None
```

### decision_node Handling

```python
# After force_back_action check (line 47):
if state.get("force_fill_input", False):
    track.route(iter=iteration, mode=mode, path="algorithm(fill_input)")
    return {"decision_path": "algorithm", "decision_maker": "error_recovery"}
```

### Tracking

```python
# New function in tracking.py:
def error(iter: int, indicators_count: int, confidence: float,
          method: str = "visual") -> None:
    """Log validation error detection."""
    logger.info(_fmt("ERROR", iter=iter, indicators=indicators_count,
                     confidence=f"{confidence:.2f}", method=method))

# Updated learn() signature:
def learn(iter: int, stuck: bool, memory_updated: bool,
          stuck_reason: Optional[str] = None,
          error_detected: bool = False) -> None:
```

## 4. Error Handling

| Condition | Handling | Recovery |
|-----------|----------|----------|
| No screenshot available (screen changed) | Skip detection, continue normally | Normal flow — screen change means no validation error |
| cv2 import fails | `VisualErrorDetector.detect()` returns `detected=False` | Graceful degradation — no error detection available |
| Image cannot be loaded (corrupted/missing) | `cv2.imread()` returns None, detect returns `detected=False` | Continue without detection |
| No TEXT_CHANGE actions on screen | Clear `force_fill_input`, fall through to normal algorithm flow | Agent continues exploring normally |
| All input values exhausted for all fields | `_find_next_input_action()` returns None, clear flag | Normal algorithm flow selects next action |
| False positive (large red UI element) | Size filter rejects indicators > `max_indicator_size` (80 px) | Buttons, FABs, mascots filtered out |
| False positive (system bar icons) | Region filter rejects indicators in top 5% or bottom 6% of screenshot | Status bar notifications, nav bar buttons excluded |
| False positive (red/pink themed app) | Count filter rejects when > `max_indicator_count` (5) indicators | Entire detection result discarded |
| Repeated error detection (loop) | `error_recovery_count >= MAX_ERROR_RECOVERY` (3) disables detection | Agent falls through to normal flow, eventually triggers stuck detection or backtracking |

### Loop Protection

Without a counter, this scenario could loop indefinitely:
1. Error detected → fill input A → error still detected (input B also empty) → fill input B → error still detected (validation requires specific format) → ...

`error_recovery_count` (on the RVAgent instance) tracks consecutive iterations where error detection triggered. When it reaches `MAX_ERROR_RECOVERY` (3), detection is disabled and the counter stays at 3 — it does NOT reset while the screen remains the same. This lets `stuck_screen_count` accumulate normally until Level 1 stuck detection triggers BACK. The counter resets to 0 only when the screen changes (no screenshot available, meaning `previous_screen_hash` differs), which happens when the agent navigates away or when input filling changes the UI.

## 5. Decisions

### D1: Detection in learn_node (not parse_node)

**Context**: Error detection could run in parse_node (during screen parsing) or learn_node (after action evaluation).
**Decision**: learn_node, before stuck detection.
**Rationale**: learn_node handles post-execution analysis. Error detection needs the screen state AFTER the action was executed — this is the screen that may show validation errors. parse_node runs at the beginning of each iteration to capture the current screen for decision-making, not to evaluate the result of the previous action. Placing detection before stuck detection allows resetting `stuck_screen_count` to prevent false positives.

### D2: Guidance via `force_fill_input` flag (not scorer modification)

**Context**: Could use FailedActionScorer (-9999 penalty) or a state flag.
**Decision**: State flag following the `force_back_action` / `force_restart_app` pattern.
**Rationale**: A -9999 penalty permanently blacklists the action on that screen. For validation errors, the action (e.g., "GENERATE HASH" button) should be retried after filling inputs. The flag pattern is simpler and already proven for learn_node-to-algorithm_node communication.

### D3: Visual detection via ErrorDetector (not text-based)

**Context**: Four alternatives analyzed: (A) full ScreenshotAnalyzer, (B) color-only OpenCV, (C) text-based UIAutomator, (D) visual via ErrorDetector.
**Decision**: Visual detection via rv-screen-parser's `ErrorDetector` (Alt D).
**Rationale**: CryptoApp validation errors are purely visual — the UIAutomator dump is identical before and after the error. Text-based detection (Alt C) cannot detect these. ErrorDetector already exists and is validated (0.80 confidence on CryptoApp errors, 0 false positives on normal screens). Reusing it avoids implementing new image analysis. The `opencv-python-headless` dependency is already transitive via rv-screen-parser.

### D4: Do NOT connect FailedActionScorer or record_action_failure()

**Context**: `record_action_failure()` (`screen_node.py:112`) and `FailedActionScorer` (`scorers.py:311`) exist in the codebase but are **never called** — `failed_actions` is always empty, the scorer always returns 0.0. The TODO at `screen_node.py:120` (issue #19) tracks this. Could be connected for error detection.
**Decision**: Do not connect them for validation errors.
**Rationale**: Validation errors are temporary precondition failures — the action works correctly once inputs are filled. Even if FailedActionScorer were functional, its -9999 permanent blacklisting is wrong for validation errors. Connecting them is issue #19 scope (crash/timeout detection), not gh18.

### D5: Access `_prepare_input_action()` directly (no public wrapper)

**Context**: `_find_associated_input_action()` and `_find_next_input_action()` in `algorithm_node` call `agent.strategy._prepare_input_action()`, a private method on `RVAgentStrategy`.
**Decision**: Call the private method directly without creating a public wrapper.
**Rationale**: Both `algorithm_node` and `rvagent_strategy` are internal to rv-agent — there is no cross-module boundary. Python's `_` prefix is a naming convention, not access control. Creating a public `prepare_input_action()` wrapper for a single caller adds ceremony without value (P1: simplicity).

### D6: Reuse ErrorDetector from rv-screen-parser directly

**Context**: Could copy ErrorDetector logic into rv-agent, create a wrapper module, or import directly.
**Decision**: Import and call `get_error_detector().detect_errors(image, [])` directly from rv-screen-parser.
**Rationale**: ErrorDetector is stable, tested, and designed for this purpose. rv-agent already depends on rv-screen-parser. Copying logic would create duplication; a wrapper adds indirection without value (P1: simplicity).

### D7: Screenshot capture in parse_ui_node, only when screen hash repeats

**Context**: Could capture screenshots every iteration, only when hash repeats, or only in learn_node.
**Decision**: Conditional capture in parse_ui_node when `screen_hash == previous_screen_hash`.
**Rationale**: Taking a screenshot every iteration wastes ~100ms per iteration. The hash-repeat condition targets the exact scenario where validation errors occur: the agent performed an action but the screen didn't change (or changed back). learn_node cannot take the screenshot because execute_node runs between learn_node and the next parse_ui_node, changing the screen.

### D8: opencv-python-headless instead of opencv-python

**Context**: rv-screen-parser depends on `opencv-python>=4.10.0`. Docker slim images lack `libGL`.
**Decision**: Change dependency to `opencv-python-headless>=4.10.0`.
**Rationale**: Same API, same functionality, but doesn't require `libgl1-mesa-glx`. No Docker apt-get install needed. The headless variant is the standard choice for server/container environments.

### D9: Spatial association over sequential iteration

**Context**: When `force_fill_input` is set, `algorithm_node` needs to choose which component to interact with. Could fill the first TEXT_CHANGE action found (sequential), or use spatial proximity to the error indicator (spatial).
**Decision**: Spatial association as primary, sequential as fallback.
**Rationale**: Error indicators can appear near any component type (EditText, Spinner, Button, etc.), not just text inputs. CryptoApp screenshot 009.png shows errors on both EditText AND Spinner simultaneously. Sequential iteration would always fill the first field encountered regardless of which error indicator it corresponds to. Spatial association maps each error indicator to its nearest actionable screen item by geometric overlap, ensuring the correct component is addressed. Widget-type boosts (1.2x EditText, 1.1x Spinner) serve as prioritization tiebreakers when multiple items have similar overlap, not as filters. The algorithm reuses the overlap + below-field + widget-boost pattern from the old rvandroid `ErrorAssociationStrategy`. Sequential fallback handles edge cases where ErrorIndicator coordinates don't match any screen item bounds.

### D10: False-positive filtering in VisualErrorDetector (not in ErrorDetector)

**Context**: ErrorDetector in rv-screen-parser has a known false-positive problem with red/pink-themed apps. Empirical testing showed 14 out of 70 screenshots (20%) produce false positives at conf>=0.7. Could improve ErrorDetector itself or add filtering in the rv-agent wrapper.
**Decision**: Add size and count filters in `VisualErrorDetector` (rv-agent), leave ErrorDetector unchanged.
**Rationale**: ErrorDetector is a general-purpose component in rv-screen-parser used by multiple consumers. Changing its detection algorithm risks breaking other use cases. The false-positive patterns are well-characterized (large elements, many indicators) and easily filtered post-hoc. The filters are specific to the validation-error use case (small icons near input fields). Keeping them in the rv-agent wrapper preserves separation of concerns. The filter parameters are configurable for gh9 calibration.

### D11: System region masking for false-positive reduction

**Context**: rv-agent explores 188+ Android apps. The status bar (top ~5% of screen) and navigation bar (bottom ~6%) contain system-drawn icons (notification, alarm, battery, back/home/recents) that the app developer does not control. These icons may be red on certain device themes, causing false positives when ErrorDetector scans the full screenshot. rv-agent already has system bar detection in `RVAgentStrategy._is_system_action()` using percentage thresholds (`STATUSBAR_Y_PERCENT=0.05`, `NAVBAR_Y_PERCENT=0.94`).
**Decision**: Filter out indicators whose y-coordinate falls within the top 5% or bottom 6% of the screenshot height, as a stage between size filtering and count filtering. Use the same percentage thresholds as the existing strategy for consistency.
**Alternatives considered**: (a) Filter ItemActions in spatial association instead of filtering indicators — this would use `_is_system_action()` to exclude system bar items from matching. Rejected because: system bar indicators must be removed BEFORE the count filter (otherwise they inflate the count and may trigger the "red-themed UI" rejection), and `_is_system_action()` already filters system actions from the normal ranking pipeline, so spatial association rarely encounters system bar items anyway.
**Rationale**: Validation errors appear near input fields in the content area, never in system bars. The filter is trivial (coordinate comparison against image height) and eliminates an entire class of false positives that would otherwise affect any app on any device with colored system icons. Percentage-based thresholds adapt to different device resolutions (unlike fixed pixel values). The percentages are hardcoded constants matching the existing strategy thresholds — they represent physical UI layout, not detection parameters.

### D12: gh18 scope is visual-only detection (text-based is future work)

**Context**: gh18 detects validation errors via visual analysis (color-based) when the screen hash repeats. However, most Android apps using standard Material Design 3 `TextInputLayout.setError()` will change the UIAutomator dump (new `TextView` element with error text), causing the screen hash to change. In this case, gh18's hash-repeat trigger does not fire and the error goes undetected.
**Decision**: gh18 implements visual detection only. Text-based detection (analyzing UIAutomator dump content for error keywords when the hash changes) is documented as a future enhancement.
**Rationale**: Visual and text-based detection have different triggers (hash repeats vs hash changes), different signals (screenshot color analysis vs UIAutomator text parsing), and would require different implementation paths. Combining both in a single change increases scope and risk. The `force_fill_input` response mechanism is the same for both, so a future text-based change can reuse gh18's infrastructure. CryptoApp (the primary validation target) uses visual-only errors, so gh18 provides immediate value while text-based detection extends coverage to the broader 188-app corpus.

## 6. Calibration Parameters

All error detection parameters are exposed via `RVAgentConfig` for gh9-docker-calibration to tune via Optuna. They follow the same pattern as existing scorer weights (injected via tool spec DSL: `rvagent:pure_algorithm@error_detection_confidence=0.5`).

| Parameter | Type | Default | Range | Purpose |
|-----------|------|---------|-------|---------|
| `error_detection_enabled` | bool | `True` | on/off | Master switch — gh9 can disable for baseline comparison |
| `error_detection_confidence` | float | `0.7` | [0.3, 0.95] | Confidence threshold for ErrorDetector indicators |
| `error_max_indicator_size` | int | `80` | [30, 200] | Max px (width or height) for valid error indicator |
| `error_max_indicator_count` | int | `5` | [2, 20] | Max indicators before assuming red-themed UI |

Constants that remain hardcoded (promote to config only if gh9 calibration reveals sensitivity):

| Constant | Value | Location | Why hardcoded |
|----------|-------|----------|---------------|
| `MAX_ERROR_RECOVERY` | 3 | learn_node | Loop protection — unlikely to need tuning |
| `SYSTEM_BAR_TOP_PERCENT` | 0.05 | VisualErrorDetector | Matches RVAgentStrategy.STATUSBAR_Y_PERCENT — top 5% is status bar |
| `SYSTEM_BAR_BOTTOM_PERCENT` | 0.06 | VisualErrorDetector | Matches 1 - RVAgentStrategy.NAVBAR_Y_PERCENT (0.94) — bottom 6% is nav bar |
| `SPATIAL_EDITTEXT_BOOST` | 1.2 | algorithm_node | Tiebreaker, not a primary scoring factor |
| `SPATIAL_SPINNER_BOOST` | 1.1 | algorithm_node | Tiebreaker, not a primary scoring factor |
| `SPATIAL_BELOW_FIELD_SCORE` | 0.7 | algorithm_node | Heuristic threshold — geometric, not empirical |
| `SPATIAL_BELOW_FIELD_MAX_PX` | 100 | algorithm_node | Physical constraint — error indicators don't appear >100px below |
| `SPATIAL_MIN_MATCH_THRESHOLD` | 0.1 | algorithm_node | Minimum noise floor — below this is no match |

## 7. Testing Strategy

### rv-screen-parser: ErrorDetector integration tests (robust, real screenshots)

Detection accuracy testing belongs in rv-screen-parser, where ErrorDetector lives. Tests use real screenshots from `tests/images/` and characterize the detector's behavior — true positives, true negatives, and known false positives. These tests serve as a baseline: if ErrorDetector is improved later, the false-positive tests become regression tests.

| Test | Screenshot | Expected | Purpose |
|------|-----------|----------|---------|
| True positive | `cryptoapp_009_errors.png` | 2 indicators, conf=0.80, ~52x51 px | Validation errors detected |
| True negative | `cryptoapp_005_normal.png` | 0 indicators | Normal screen, no false positives |
| True negative | `cryptoapp_001_initial.png` | 0 indicators | App launch screen, no false positives |
| Known FP | `hourlyreminder_003_settings.png` | 15+ indicators (pink UI) | Documents false-positive behavior |
| Known FP | `dnshero_002_main.png` | 5 indicators (red mascot) | Documents false-positive behavior |
| Known FP | `hex_003_gameplay.png` | 2+ indicators (red header/icons) | Documents false-positive behavior |

### rv-agent: VisualErrorDetector unit tests (basic, mocked)

rv-agent tests validate the wrapper logic (filtering, graceful degradation) using mocks. No real screenshots — detection accuracy is rv-screen-parser's responsibility.

| Test Type | Scope | What It Verifies |
|-----------|-------|-----------------|
| Unit | `VisualErrorDetector` | Mock ErrorDetector: error detected, no error, missing image returns False, cv2 import failure returns False, confidence filter, size filter (indicator >80px rejected), region filter (indicator in top 5% or bottom 6% rejected), count filter (>5 indicators rejected) |
| Unit | `parse_ui_node` screenshot capture | Hash repeats -> screenshot taken; hash differs -> no screenshot; detection disabled -> no screenshot |
| Unit | `learn_node._detect_validation_error()` | Screenshot available + error detected -> stuck suppressed + flag set; no screenshot -> no detection; disabled via config -> skipped; max recovery count -> skipped |
| Unit | `algorithm_node` force_fill_input | Flag + inputs -> SET_TEXT or CLICK selected; flag + no inputs -> normal flow; flag off -> unchanged |
| Unit | `_find_associated_input_action()` | Overlap match -> correct field; below-field heuristic -> 0.7 score; Spinner match -> CLICK; no match -> falls back to sequential; empty indicators -> None; multiple indicators -> highest score wins |
| Unit | `_find_next_input_action()` | TEXT_CHANGE actions found -> prepared with value; no TEXT_CHANGE -> None; all values exhausted -> None |
| Unit | `_calculate_association_score()` | Full overlap -> high score; EditText boost 1.2x; Spinner boost 1.1x; below-field within 100px -> 0.7; no overlap + not below -> 0.0 |
| Integration | learn_node -> algorithm_node | Error screenshot -> detection -> flag + indicators -> spatial match -> input filled -> flags cleared |
| Integration | Full cycle | Fill input -> retry button -> no error -> normal flow |
| Integration | Spinner + EditText | Two indicators -> spatial: Spinner CLICK first, EditText SET_TEXT second |

## 8. Scenario Walkthrough: CryptoApp 009.png (Both Errors)

Steps 1-2 happen in iteration N. Steps 3-7 happen in iteration N+1. Steps 8-12 happen in iterations N+2 through N+4.

1. Agent clicks "GENERATE HASH" with empty Spinner (hash algorithm) + empty EditText (input text)
2. App shows red `!` icon on Spinner AND red `!` icon on EditText (UIAutomator dump unchanged)
3. **parse_ui_node** (iteration N+1): `screen_hash == previous_screen_hash` → takes screenshot, stores path in `state["error_detection_screenshot"]`
4. **learn_node** (iteration N+1): `VisualErrorDetector.detect(screenshot_path)` finds 2 error indicators:
   - ErrorIndicator at (680, 260, 30, 30), confidence=0.80 (near Spinner)
   - ErrorIndicator at (790, 390, 30, 30), confidence=0.80 (near EditText)
   - `agent.stuck_screen_count = 0` (suppress false stuck)
   - `agent.error_recovery_count = 1`
   - `result["force_fill_input"] = True`
   - `result["error_indicators"] = [2 ErrorIndicator objects]`
   - `track.error(iter=5, indicators=2, confidence=0.80, method="visual")`
5. **decision_node** (iteration N+1): sees `force_fill_input` → routes to algorithm
6. **algorithm_node** (iteration N+1): sees `force_fill_input` flag + `error_indicators`
   - `_find_associated_input_action()` calculates association scores:
     - ErrorIndicator(680,260) vs Spinner bounds [0,261,1080,63]: high overlap, score * 1.1 = 0.88
     - ErrorIndicator(790,390) vs EditText bounds [0,375,1080,48]: high overlap, score * 1.2 = 0.96
   - Best match: EditText (highest score 0.96)
   - But Spinner also has high score → first ErrorIndicator with best item match wins
   - `_prepare_input_action()` → EditText SET_TEXT with "test123" (or Spinner CLICK, depending on first indicator processed)
   - Returns action with `decision_maker="error_recovery"`, clears `force_fill_input` + `error_indicators`
7. **execute_node** (iteration N+1): types "test123" into EditText (or clicks Spinner)
8. **parse_ui_node** (iteration N+2): screen changed (input filled) → no screenshot, no detection
9. **learn_node** (iteration N+2): no error → `error_recovery_count = 0`
10. **Normal exploration** (iteration N+2): Spinner still empty → agent ranks it high (untested), clicks it, selects "SHA-256"
11. **Iteration N+3**: Agent clicks "GENERATE HASH" with filled Spinner + filled EditText
12. Crypto operation triggered → MOP detected
