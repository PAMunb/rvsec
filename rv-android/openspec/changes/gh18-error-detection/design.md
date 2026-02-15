# Design: Error Detection Integration

**Change**: gh18-error-detection
**GitHub Issue**: [#18](https://github.com/PAMunb/rvsec/issues/18)
**Schema**: rv-sdd

## 1. Architecture

### Detection Strategy: Text-Based (Alternative C)

Error detection is implemented as a lightweight text analysis pass on the UIAutomator XML dump, which is already parsed in `parse_node`. No new system dependencies (OpenCV, Tesseract) are required.

The detection works by:
1. Extracting all `text` and `content-desc` attributes from the UI hierarchy (already available from UIAutomator parsing)
2. Matching against regex patterns derived from `ErrorDetector._detect_text_errors()` in rv-screen-parser
3. Returning a list of detected error indicators with type and confidence

### Integration Point: learn_node

Error detection runs in `learn_node` after action execution and screen capture, as part of the "learn from action result" phase. This is the natural location because:
- The new screen state is already captured and parsed
- The previous action is known (needed for `record_action_failure()`)
- `learn_node` already handles stuck detection — error detection is a complementary signal

### Data Flow

```
execute_node (action) → learn_node:
  1. Capture new screen (existing)
  2. Parse UI hierarchy (existing)
  3. [NEW] Run error detection on parsed elements
  4. If error detected:
     a. Call screen_node.record_action_failure(action, error_type)
     b. Set recovery_action = BACK
     c. Skip normal stuck detection (error takes priority)
  5. Normal learn flow continues
```

## 2. Key Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `ErrorPatternMatcher` | `rv_agent/services/error_detection.py` (new) | Regex matching on UI element texts, returns error indicators |
| `learn_node` | `rv_agent/agent/nodes/learn_node.py` (modified) | Calls ErrorPatternMatcher after action, triggers failure recording |
| `ScreenNode` | `rv_agent/domain/screen_node.py` (existing) | `record_action_failure()` — already implemented, currently uncalled |
| `FailedActionScorer` | `rv_agent/strategies/rvagent_strategy/ranking/scorers.py` (existing) | Returns -9999 for recorded failures — already implemented |

## 3. Spec-to-Implementation Mapping

| Spec (INV/Scenario) | Implementation | Test |
|---------------------|----------------|------|
| INV-AG-20 (error detection) | `ErrorPatternMatcher.detect()` | `test_error_pattern_matcher.py` |
| INV-AG-21 (failure recording) | `learn_node._check_for_errors()` → `screen_node.record_action_failure()` | `test_learn_node_error_detection.py` |
| INV-AG-22 (failed action penalty) | `FailedActionScorer.score()` (existing) | `test_failed_action_scorer.py` (verify with real data) |
| INV-AG-23 (error recovery) | `learn_node._check_for_errors()` sets recovery action | `test_learn_node_error_recovery.py` |
| Scenario: no false positive | `ErrorPatternMatcher` confidence threshold + context check | `test_error_pattern_matcher_false_positives.py` |

## 4. API Design

### ErrorPatternMatcher

```python
@dataclass
class ErrorIndicator:
    error_type: str        # "permission_error", "network_error", "crash", "validation_error", "system_error"
    matched_text: str      # The text that triggered the match
    confidence: float      # 0.0 to 1.0
    element_id: str | None # UIAutomator resource-id if available

class ErrorPatternMatcher:
    """Text-based error detection using regex patterns on UI hierarchy elements.

    Patterns are derived from ErrorDetector._detect_text_errors() in rv-screen-parser.
    Operates on already-parsed UI elements — no image processing, no new dependencies.
    """

    CONFIDENCE_THRESHOLD: float = 0.7

    def detect(self, ui_elements: list[dict]) -> list[ErrorIndicator]:
        """Check all UI element texts against error patterns.

        Args:
            ui_elements: List of parsed UI elements with 'text' and 'content_desc' fields.
                         These come from the UIAutomator dump already parsed in parse_node.

        Returns:
            List of ErrorIndicator for elements matching error patterns above confidence threshold.
            Empty list if no errors detected.
        """
```

### learn_node Integration

```python
# In learn_node.py, after capturing new screen:

def _check_for_errors(self, state: AgentState) -> tuple[bool, str | None]:
    """Check current screen for error indicators.

    Returns:
        Tuple of (error_detected: bool, error_type: str | None)
    """
    matcher = ErrorPatternMatcher()
    indicators = matcher.detect(state["current_ui_elements"])

    if not indicators:
        return False, None

    # Use highest-confidence indicator
    best = max(indicators, key=lambda i: i.confidence)

    # Record failure on current screen node
    current_node = state["current_screen_node"]
    current_node.record_action_failure(
        action=state["last_action"],
        error_type=best.error_type
    )

    return True, best.error_type
```

## 5. Error Handling

| Error Condition | Handling | Recovery |
|----------------|----------|----------|
| UIAutomator dump unavailable | Skip error detection, continue normally | Log warning, rely on hash-based stuck detection |
| All actions on a screen are failed | Backtrack via StuckRecovery (existing) | DFS backtracks to parent screen |
| BACK doesn't dismiss error dialog | Hash-based stuck detection triggers after N same-screen iterations | StuckRecovery escalates (HOME, restart) |
| False positive (normal text matched) | Confidence threshold filters low-confidence matches | Action penalty is per-screen-node, so same action on different screen is unaffected |

## 6. Testing Strategy

| Test Type | Scope | What It Verifies |
|-----------|-------|-----------------|
| Unit | `ErrorPatternMatcher` | Regex patterns match known error strings, reject normal strings |
| Unit | `ErrorPatternMatcher` false positives | "Error Log", "Report Error" etc. do NOT trigger detection |
| Unit | `learn_node._check_for_errors()` | Integration with ScreenNode.record_action_failure() |
| Unit | `FailedActionScorer` with real data | Scorer returns -9999 when failure data is populated |
| Integration | learn_node → ScreenNode → FailedActionScorer | Full chain from error detection to scoring penalty |
| Smoke | Manual with known-error APK | App with permission dialog triggers detection + recovery |

## 7. Decisions

### D1: Text-based detection first (Alternative C)

**Context**: Four alternatives were analyzed (see proposal.md Section 2).
**Decision**: Start with Alternative C (text-based on UIAutomator dump).
**Rationale**: Zero new dependencies, ~5ms latency, no Docker image changes. Covers ~80% of error cases (textual errors). If insufficient, escalate to Alternative B (OpenCV) or A (full ScreenshotAnalyzer) in a future change.

### D2: Integration in learn_node (not parse_node)

**Context**: Error detection could run in parse_node (during screen parsing) or learn_node (after action evaluation).
**Decision**: learn_node, after action execution and screen capture.
**Rationale**: learn_node has access to the previous action (needed for `record_action_failure()`), already handles stuck detection, and is the "evaluate action result" phase. parse_node is about understanding screen structure, not evaluating action outcomes.

### D3: Single ErrorPatternMatcher class (not extending ErrorDetector)

**Context**: Could subclass or wrap rv-screen-parser's `ErrorDetector`.
**Decision**: New standalone `ErrorPatternMatcher` in rv-agent that extracts only the regex patterns.
**Rationale**: P1 — avoid pulling in OpenCV/Tesseract dependency chain. The text patterns are simple regex strings that can be copied. If later escalating to Alt A/B, the class can be replaced with an ErrorDetector wrapper.

### D4: Confidence threshold at 0.7

**Context**: Need to balance detection sensitivity vs. false positives.
**Decision**: Default threshold at 0.7, configurable in agent_config.
**Rationale**: Conservative default reduces false positives. Can be tuned during calibration. Values below 0.5 risk matching partial text fragments.
