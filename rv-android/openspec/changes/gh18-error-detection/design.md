# Design: Validation Error Detection

**Change**: gh18-error-detection
**GitHub Issue**: [#18](https://github.com/PAMunb/rvsec/issues/18)
**Schema**: rv-sdd

## 1. Architecture

### Detection Strategy: Text-Based (Zero Dependencies)

Error detection scans UI element text from the UIAutomator dump (already parsed in `parse_node`) for validation error patterns using regex. No image processing, no new system dependencies.

The detection:
1. Extracts `text` and `content-desc` attributes from `ScreenDescription.items` (available from UIAutomator parsing)
2. Matches against validation error patterns (regex derived from `ErrorDetector._detect_text_errors()` in rv-screen-parser)
3. Returns a result with detected error texts and a confidence score

### Integration Point: learn_node

Error detection runs in `learn_node` before stuck detection. learn_node already handles post-execution analysis (stuck detection, action success recording). Error detection is the same category of post-execution analysis.

When a validation error is detected:
- `stuck_screen_count` is reset to 0 (suppress false stuck — the screen may be unchanged, but backing out is wrong)
- `force_fill_input = True` is set in the result state

### Response: Guidance via `force_fill_input` State Flag

The `force_fill_input` flag follows the same pattern as `force_back_action` and `force_restart_app` for learn_node-to-algorithm_node communication. When `algorithm_node` sees this flag, it finds the next unfilled TEXT_CHANGE action on the current screen and generates a SET_TEXT action using `InputValueGenerator`.

This is guidance, not punishment: the agent stays on the screen, fills inputs, and retries the submit action on the next iteration.

### Data Flow

```
execute_node (action) -> learn_node:
  1. Update memories (existing)
  2. [NEW] Detect validation errors via ErrorPatternMatcher
  3. If error detected:
     a. Reset stuck_screen_count = 0
     b. Set force_fill_input = True
     c. Log via track.error()
  4. Stuck detection (existing, runs normally — but stuck_screen_count was reset, so it won't trigger)
  5. Normal learn flow continues

decision_node:
  [NEW] Check force_fill_input -> route to algorithm

algorithm_node:
  [NEW] Check force_fill_input flag (after force_restart_app and force_back_action checks)
  1. Find TEXT_CHANGE actions on current screen
  2. Use InputValueGenerator to get next test value
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
| `RVAgent` | `rv_agent/agent/rv_agent.py` (modify) | Wire config, init `force_fill_input` in state, store `error_confidence` |
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

    Scans item.view['text'] and item.view['content-desc'] from ScreenDescription
    against regex patterns for common validation error messages.

    Patterns derived from ErrorDetector._detect_text_errors() in rv-screen-parser.
    """

    VALIDATION_PATTERNS = [
        r'\b(required|mandatory)\b',
        r'\b(invalid|incorrect)\s+(format|input|data|value)\b',
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

        Args:
            screen_desc: Parsed screen state from state["screen_description"].
            confidence_threshold: Minimum confidence to consider error detected.

        Returns:
            ValidationErrorResult with detection status, matched texts, and confidence.
        """
```

### learn_node Integration

```python
def _detect_validation_error(agent: "RVAgent", state: AgentState) -> bool:
    """Detect validation errors on current screen.

    Called before stuck detection. When a validation error is detected,
    resets stuck_screen_count to prevent false stuck detection and
    signals algorithm_node to prioritize input filling.

    Args:
        agent: RVAgent with error_confidence from config.
        state: Current agent state with screen_description.

    Returns:
        True if validation error detected (above confidence threshold).
    """
    if not getattr(agent, 'error_detection_enabled', True):
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
# Before stuck detection (line ~125 in current code):
error_detected = _detect_validation_error(agent, state)
if error_detected:
    agent.stuck_screen_count = 0  # Suppress false stuck

# ... existing stuck detection runs (but won't trigger because count was reset) ...

# In result dict construction:
if error_detected:
    result["force_fill_input"] = True
```

### algorithm_node Handling

```python
# After force_back_action check (line ~75), before deadlock detection:
if state.get("force_fill_input", False):
    input_action = _find_next_input_action(agent, state)
    if input_action:
        logger.info(f"Error recovery: filling input at ({input_action.x}, {input_action.y})")
        # Return SET_TEXT action
        return {
            "current_action": {
                "action_type": "SET_TEXT",
                "x": input_action.x,
                "y": input_action.y,
                "text": input_action.text_input,
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
```

`_find_next_input_action()` iterates TEXT_CHANGE actions on the current screen, uses `agent.strategy._prepare_input_action()` to find one with remaining test values from `InputValueGenerator`.

### decision_node Handling

```python
# After force_back_action check:
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
| All input values exhausted for a field | `_prepare_input_action()` returns None, try next field | If all fields exhausted, clear flag |
| False positive (normal text matched) | Confidence threshold filters low-confidence matches | Agent fills one input (low cost), resumes next iteration |

## 5. Decisions

### D1: Detection in learn_node (not parse_node)

**Context**: Error detection could run in parse_node (during screen parsing) or learn_node (after action evaluation).
**Decision**: learn_node, before stuck detection.
**Rationale**: learn_node handles post-execution analysis. The previous action's result is available. Placing detection before stuck detection allows resetting `stuck_screen_count` to prevent false positives.

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
**Rationale**: These are designed for **permanent action failures** (crashes, ANR). Validation errors are temporary precondition failures — the action works correctly once inputs are filled. Blacklisting the action would prevent the agent from reaching monitored operations behind submit buttons. The TODO at `screen_node.py:120` remains for future crash detection work.

## 6. Testing Strategy

| Test Type | Scope | What It Verifies |
|-----------|-------|-----------------|
| Unit | `ErrorPatternMatcher` | Known error texts match, normal texts don't, exclusion patterns work, confidence threshold filters |
| Unit | `learn_node._detect_validation_error()` | Error detected -> stuck suppressed + flag set; no error -> unchanged; disabled via config -> skipped |
| Unit | `algorithm_node` force_fill_input | Flag + inputs -> SET_TEXT selected; flag + no inputs -> normal flow; flag off -> unchanged |
| Integration | learn_node -> algorithm_node | Error screen -> detection -> flag -> input filled -> flag cleared |
| Integration | Full cycle | Fill input -> retry button -> no error -> normal flow |

## 7. Scenario Walkthrough: Crypto App

1. Agent clicks "GENERATE HASH" with empty input field
2. App shows "Field required" validation error on the EditText
3. **learn_node**: `ErrorPatternMatcher.detect()` matches "Field required" (confidence 0.9)
   - `agent.stuck_screen_count = 0` (suppress false stuck)
   - `result["force_fill_input"] = True`
   - `track.error(iter=5, error_texts=["Field required"], confidence=0.9)`
4. **decision_node**: sees `force_fill_input` -> routes to algorithm
5. **algorithm_node**: sees `force_fill_input` flag
   - `_find_next_input_action()` finds the EditText with TEXT_CHANGE event
   - `InputValueGenerator.get_next_value()` returns "test123"
   - Returns SET_TEXT at EditText coordinates, `decision_maker="error_recovery"`
   - Clears `force_fill_input = False`
6. **execute_node**: types "test123" into the EditText
7. **Next iteration**: learn_node detects no error -> normal flow
8. Agent clicks "GENERATE HASH" again -> crypto operation triggered -> MOP detected
