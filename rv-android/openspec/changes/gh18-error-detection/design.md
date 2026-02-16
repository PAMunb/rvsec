# Design: Validation Error Detection

**Change**: gh18-error-detection
**GitHub Issue**: [#18](https://github.com/PAMunb/rvsec/issues/18)
**Schema**: rv-sdd

## 1. Architecture

### Detection Strategy: Text-Based (Zero Dependencies)

Error detection scans UI element text from the UIAutomator dump (already parsed in `parse_node`) for validation error patterns using regex. No image processing, no new system dependencies.

The detection:
1. Extracts `text` and `content_description` attributes from `ScreenDescription.items` (available from UIAutomator parsing)
2. Matches against validation error patterns (regex derived from `ErrorDetector._detect_text_errors()` in rv-screen-parser)
3. Returns a result with detected error texts and a confidence score

### Integration Point: learn_node

Error detection runs in `learn_node` before stuck detection. learn_node already handles post-execution analysis (stuck detection, action success recording). Error detection is the same category of post-execution analysis.

When a validation error is detected:
- `stuck_screen_count` is reset to 0 (suppress false stuck — the screen may be unchanged, but backing out is wrong)
- `force_fill_input = True` is set in the result state
- `error_recovery_count` is incremented (loop protection — see Section 4)

### Response: Guidance via `force_fill_input` State Flag

The `force_fill_input` flag follows the same pattern as `force_back_action` and `force_restart_app` for learn_node-to-algorithm_node communication. When `algorithm_node` sees this flag, it finds the next unfilled TEXT_CHANGE action on the current screen and generates a SET_TEXT action using `InputValueGenerator`.

This is guidance, not punishment: the agent stays on the screen, fills inputs, and retries the submit action on the next iteration.

### Data Flow

```
execute_node (action) -> learn_node:
  1. Update memories (existing)
  2. [NEW] Detect validation errors via ErrorPatternMatcher
  3. If error detected AND error_recovery_count < MAX_ERROR_RECOVERY (3):
     a. Reset stuck_screen_count = 0
     b. Increment error_recovery_count
     c. Set force_fill_input = True
     d. Log via track.error()
  4. If no error detected: reset error_recovery_count = 0
  5. Stuck detection (existing, runs normally — but stuck_screen_count was reset, so it won't trigger)
  6. Normal learn flow continues

decision_node:
  [NEW] Check force_fill_input -> route to algorithm

algorithm_node:
  [NEW] Check force_fill_input flag (after force_restart_app and force_back_action checks)
  1. Find TEXT_CHANGE actions on current screen via _find_next_input_action()
  2. Use _prepare_input_action() to get ItemAction with test value from InputValueGenerator
  3. Return SET_TEXT action with decision_maker="error_recovery"
  4. If no input found: clear flag, fall through to normal flow
```

## 2. Key Components

| Component | Location | Action |
|-----------|----------|--------|
| `ErrorPatternMatcher` | `rv_agent/services/error_detection.py` (new) | Regex matching on ScreenDescription item texts |
| `learn_node` | `rv_agent/agent/nodes/learn_node.py` (modify) | Add `_detect_validation_error()`, set `force_fill_input`, suppress stuck counter |
| `decision_node` | `rv_agent/agent/nodes/decision_node.py` (modify) | Route `force_fill_input` to algorithm |
| `algorithm_node` | `rv_agent/agent/nodes/algorithm_node.py` (modify) | Handle `force_fill_input`, find input action, generate SET_TEXT |
| `AgentState` | `rv_agent/domain/state.py` (modify) | Add `force_fill_input: bool` field |
| `RVAgentConfig` | `rv_agent/config/agent_config.py` (modify) | Add `error_detection_enabled`, `error_detection_confidence` |
| `RVAgent` | `rv_agent/agent/rv_agent.py` (modify) | Wire config, init `force_fill_input` in state, store `error_confidence`, init `error_recovery_count` |
| `tracking` | `rv_agent/tracking.py` (modify) | Add `track.error()`, update `track.learn()` with `error_detected` param |

## 3. API Design

### ErrorPatternMatcher

```python
@dataclass
class ValidationErrorResult:
    detected: bool           # True if confidence >= threshold
    error_texts: list[str]   # Matched error text strings
    confidence: float        # 0.0 to 1.0

class ErrorPatternMatcher:
    """Text-based validation error detection on UI hierarchy elements.

    Scans item.view['text'] and item.view['content_description'] from
    ScreenDescription against regex patterns for common validation error messages.

    Patterns derived from ErrorDetector._detect_text_errors() in rv-screen-parser.

    Confidence calculation:
    - Each UI element text is checked against all VALIDATION_PATTERNS
    - If matched text also matches an EXCLUSION_PATTERN, it is discarded
    - Confidence = (number of matched elements) / (total elements with non-empty text)
    - If only 1 element matches out of 20: confidence = 0.05 (below threshold, no detection)
    - If 3 elements match out of 5: confidence = 0.6 (near threshold)
    - A single strong match (e.g., "Field is required") gets a minimum confidence of 0.8
      because specific multi-word patterns are high-signal

    Minimum confidence rule: If any pattern from the STRONG_PATTERNS subset matches,
    confidence is at least 0.8 regardless of element ratio. STRONG_PATTERNS are
    multi-word patterns unlikely to appear outside error contexts:
    - r'field\s+(is\s+)?required'
    - r'enter\s+a\s+valid'
    - r'(cannot|can.t)\s+be\s+(empty|blank)'
    - r'(please|must)\s+(enter|provide|fill)'
    """

    VALIDATION_PATTERNS = [
        r'\b(required|mandatory)\b',
        r'\b(invalid|incorrect)\s+(format|input|data|value)\b',
        r'\b(cannot|can.t)\s+be\s+(empty|blank)\b',
        r'\b(please|must)\s+(enter|provide|fill)\b',
        r'\bfield\s+(is\s+)?required\b',
        r'\benter\s+a\s+valid\b',
    ]

    # Multi-word patterns that are high-signal for validation errors.
    # If any matches, confidence is at least 0.8.
    STRONG_PATTERNS = [
        r'\b(cannot|can.t)\s+be\s+(empty|blank)\b',
        r'\b(please|must)\s+(enter|provide|fill)\b',
        r'\bfield\s+(is\s+)?required\b',
        r'\benter\s+a\s+valid\b',
    ]

    EXCLUSION_PATTERNS = [
        r'error\s*log',
        r'report\s*error',
        r'error\s*code',
    ]

    def detect(
        self,
        screen_desc: ScreenDescription,
        confidence_threshold: float = 0.7,
    ) -> ValidationErrorResult:
        """Scan UI element texts for validation error patterns.

        Iterates screen_desc.items, reads item.view.get('text', '') and
        item.view.get('content_description', '') for each item.

        Args:
            screen_desc: Parsed screen state from state["screen_description"].
            confidence_threshold: Minimum confidence to consider error detected.

        Returns:
            ValidationErrorResult with detection status, matched texts, and confidence.
        """
```

### learn_node Integration

```python
# Maximum consecutive error recovery attempts before giving up and letting
# normal flow handle the situation (prevents infinite fill-detect loops).
MAX_ERROR_RECOVERY = 3

def _detect_validation_error(agent: "RVAgent", state: AgentState) -> bool:
    """Detect validation errors on current screen.

    Called before stuck detection. When a validation error is detected,
    resets stuck_screen_count to prevent false stuck detection and
    signals algorithm_node to prioritize input filling.

    Loop protection: If error_recovery_count >= MAX_ERROR_RECOVERY,
    detection is skipped and the agent falls through to normal flow
    (which will eventually trigger stuck detection or backtracking).

    Args:
        agent: RVAgent with error_confidence and error_recovery_count.
        state: Current agent state with screen_description.

    Returns:
        True if validation error detected (above confidence threshold).
    """
    if not getattr(agent, 'error_detection_enabled', True):
        return False

    if agent.error_recovery_count >= MAX_ERROR_RECOVERY:
        logger.info(
            f"Error recovery limit reached ({MAX_ERROR_RECOVERY}), "
            f"skipping detection"
        )
        return False

    screen_desc = state.get("screen_description")
    if not screen_desc:
        return False

    matcher = ErrorPatternMatcher()
    result = matcher.detect(screen_desc, confidence_threshold=agent.error_confidence)

    if result.detected:
        logger.info(f"Validation error detected: {result.error_texts[:3]}")

    return result.detected
```

Integration in `learn_node()`:
```python
# Before stuck detection (before the Level 1 check at line ~148):
error_detected = _detect_validation_error(agent, state)
if error_detected:
    agent.stuck_screen_count = 0  # Suppress false stuck
    agent.error_recovery_count += 1
else:
    agent.error_recovery_count = 0  # Reset on success

# ... existing stuck detection runs (but won't trigger because count was reset) ...

# In result dict construction (after the force_restart/force_back block):
if error_detected:
    result["force_fill_input"] = True
```

### algorithm_node Handling

```python
# After force_back_action return (line 75), before deadlock detection (line 78):
if state.get("force_fill_input", False):
    input_action = _find_next_input_action(agent, state)
    if input_action:
        coords = input_action.get_execution_coordinates()
        x, y = coords if coords else (0, 0)
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
        }
    else:
        # No input field found — clear flag, fall through to normal flow
        logger.info("Error recovery: no input field found, resuming normal flow")
        # Fall through with flag cleared — next line is deadlock detection
```

### `_find_next_input_action()` Algorithm

```python
def _find_next_input_action(
    agent: "RVAgent", state: AgentState
) -> Optional[Any]:
    """Find the next unfilled input action on the current screen.

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
def error(iter: int, error_texts: list[str], confidence: float) -> None:
    """Log validation error detection."""
    texts_str = "; ".join(error_texts[:3])
    logger.info(_fmt("ERROR", iter=iter, texts=f'"{texts_str}"',
                     confidence=f"{confidence:.2f}"))

# Updated learn() signature:
def learn(iter: int, stuck: bool, memory_updated: bool,
          stuck_reason: Optional[str] = None,
          error_detected: bool = False) -> None:
```

## 4. Error Handling

| Condition | Handling | Recovery |
|-----------|----------|----------|
| `screen_description` is None | Skip detection, continue normally | Normal stuck detection handles screen issues |
| No TEXT_CHANGE actions on screen | Clear `force_fill_input`, fall through to normal algorithm flow | Agent continues exploring normally |
| All input values exhausted for all fields | `_find_next_input_action()` returns None, clear flag | Normal algorithm flow selects next action |
| False positive (normal text matched) | Confidence threshold filters low-confidence matches | Agent fills one input (low cost), resumes next iteration |
| Repeated error detection (loop) | `error_recovery_count >= MAX_ERROR_RECOVERY` (3) disables detection | Agent falls through to normal flow, eventually triggers stuck detection or backtracking |

### Loop Protection

Without a counter, this scenario could loop indefinitely:
1. Error detected → fill input A → error still detected (input B also empty) → fill input B → error still detected (validation requires specific format) → ...

`error_recovery_count` (on the RVAgent instance) tracks consecutive iterations where error detection triggered. When it reaches `MAX_ERROR_RECOVERY` (3), detection is disabled for the remainder of the screen visit. The counter resets to 0 when no error is detected (successful recovery or screen change).

## 5. Decisions

### D1: Detection in learn_node (not parse_node)

**Context**: Error detection could run in parse_node (during screen parsing) or learn_node (after action evaluation).
**Decision**: learn_node, before stuck detection.
**Rationale**: learn_node handles post-execution analysis. Error detection needs the screen state AFTER the action was executed — this is the screen that may show validation errors. parse_node runs at the beginning of each iteration to capture the current screen for decision-making, not to evaluate the result of the previous action. Placing detection before stuck detection allows resetting `stuck_screen_count` to prevent false positives.

### D2: Guidance via `force_fill_input` flag (not scorer modification)

**Context**: Could use FailedActionScorer (-9999 penalty) or a state flag.
**Decision**: State flag following the `force_back_action` / `force_restart_app` pattern.
**Rationale**: A -9999 penalty permanently blacklists the action on that screen. For validation errors, the action (e.g., "GENERATE HASH" button) should be retried after filling inputs. The flag pattern is simpler and already proven for learn_node-to-algorithm_node communication.

### D3: Text-based detection (zero dependencies)

**Context**: Four alternatives analyzed (full ScreenshotAnalyzer, color-only OpenCV, text-based UIAutomator, conditional).
**Decision**: Text-based on UIAutomator dump.
**Rationale**: Zero new dependencies, ~5ms latency, no Docker image changes. Handles common validation errors (textual messages in input fields, snackbars, toasts). If insufficient for non-textual error indicators, can be extended in a future change.

### D4: Do NOT use FailedActionScorer or record_action_failure()

**Context**: `record_action_failure()` and `FailedActionScorer` exist but are unused. Could be activated for error detection.
**Decision**: Do not activate them for validation errors.
**Rationale**: These are designed for **permanent action failures** (crashes, ANR). Validation errors are temporary precondition failures — the action works correctly once inputs are filled. Blacklisting the action would prevent the agent from reaching monitored operations behind submit buttons. The TODO at `screen_node.py:120` (issue #19) covers crash/timeout/error detection broadly and remains for future work.

### D5: Access `_prepare_input_action()` directly (no public wrapper)

**Context**: `_find_next_input_action()` in `algorithm_node` calls `agent.strategy._prepare_input_action()`, a private method on `RVAgentStrategy`.
**Decision**: Call the private method directly without creating a public wrapper.
**Rationale**: Both `algorithm_node` and `rvagent_strategy` are internal to rv-agent — there is no cross-module boundary. Python's `_` prefix is a naming convention, not access control. Creating a public `prepare_input_action()` wrapper for a single caller adds ceremony without value (P1: simplicity).

## 6. Testing Strategy

| Test Type | Scope | What It Verifies |
|-----------|-------|-----------------|
| Unit | `ErrorPatternMatcher` | Known error texts match, normal texts don't, exclusion patterns work, confidence threshold and strong pattern logic, `content_description` attribute access |
| Unit | `learn_node._detect_validation_error()` | Error detected -> stuck suppressed + flag set; no error -> unchanged; disabled via config -> skipped; max recovery count -> skipped |
| Unit | `algorithm_node` force_fill_input | Flag + inputs -> SET_TEXT selected; flag + no inputs -> normal flow; flag off -> unchanged |
| Unit | `_find_next_input_action()` | TEXT_CHANGE actions found -> prepared with value; no TEXT_CHANGE -> None; all values exhausted -> None |
| Integration | learn_node -> algorithm_node | Error screen -> detection -> flag -> input filled -> flag cleared |
| Integration | Full cycle | Fill input -> retry button -> no error -> normal flow |

## 7. Scenario Walkthrough: Crypto App

Steps 1-2 happen in iteration N. Steps 3-6 happen in iteration N+1. Steps 7-8 happen in iteration N+2.

1. Agent clicks "GENERATE HASH" with empty input field
2. App shows "Field required" validation error on the EditText
3. **learn_node** (end of iteration N): `ErrorPatternMatcher.detect()` matches "Field required" (confidence 0.8, strong pattern match)
   - `agent.stuck_screen_count = 0` (suppress false stuck)
   - `agent.error_recovery_count = 1`
   - `result["force_fill_input"] = True`
   - `track.error(iter=5, error_texts=["Field required"], confidence=0.8)`
4. **decision_node** (iteration N+1): sees `force_fill_input` -> routes to algorithm
5. **algorithm_node** (iteration N+1): sees `force_fill_input` flag
   - `_find_next_input_action()` iterates `screen_desc.items`, finds EditText with TEXT_CHANGE event
   - `agent.strategy._prepare_input_action()` calls `InputValueGenerator.get_next_value()` -> returns "test123"
   - Returns SET_TEXT at EditText coordinates, `decision_maker="error_recovery"`
   - Clears `force_fill_input = False`
6. **execute_node** (iteration N+1): types "test123" into the EditText
7. **learn_node** (end of iteration N+1): no error detected -> `agent.error_recovery_count = 0`
8. **Iteration N+2**: Agent clicks "GENERATE HASH" again -> crypto operation triggered -> MOP detected
