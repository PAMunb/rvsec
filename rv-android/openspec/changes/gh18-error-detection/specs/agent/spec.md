# Delta Spec: Validation Error Detection (agent domain)

**Change**: gh18-error-detection
**Base spec**: `openspec/specs/agent/spec.md`
**Action**: Add validation error detection and input-filling guidance to the agent

## New Invariants

### INV-AG-20: Validation Error Detection After Action

The agent detects validation error indicators on the current screen after each action execution. Detection uses text-based pattern matching on `ScreenDescription.items` (UIAutomator dump), applying regex patterns for common validation messages ("Field required", "Invalid format", "Please enter a valid email"). Detection runs in `learn_node` before stuck detection.

**Rationale**: Without error detection, the agent clicks submit buttons with empty input fields, gets validation errors, and never fills the inputs. This prevents the agent from reaching monitored operations (MOP) behind form submissions.

### INV-AG-21: Stuck Counter Suppression on Validation Error

When a validation error is detected, the agent resets `stuck_screen_count` to 0. This prevents the stuck detection system from forcing a BACK action, which would navigate away from a screen where the agent should stay and fill inputs.

**Rationale**: Validation errors may not change the screen hash (the error indicator appears on the same screen), which would trigger stuck detection. But backing out is the wrong response — the agent should stay and fill the required inputs.

### INV-AG-22: Input Filling Guidance via `force_fill_input` Flag

When a validation error is detected, `learn_node` sets `force_fill_input = True` in the agent state. `algorithm_node` responds by finding the next unfilled TEXT_CHANGE action on the current screen and generating a SET_TEXT action with a test value from `InputValueGenerator`. After the input is filled, the flag is cleared.

**Rationale**: The `force_fill_input` flag follows the same communication pattern as `force_back_action` (Level 1 stuck) and `force_restart_app` (Level 2 stuck). learn_node detects conditions, algorithm_node generates the appropriate action.

### INV-AG-23: Validation Errors Do NOT Penalize Actions

Validation errors MUST NOT trigger `record_action_failure()` or `FailedActionScorer`. The action that caused the validation error (e.g., a "GENERATE HASH" button) is correct — it only fails because input preconditions are not met. Once inputs are filled, the same action should be retried.

**Rationale**: `FailedActionScorer` assigns -9999, permanently blacklisting the action on that screen. This is designed for app crashes, not validation errors. Blacklisting a submit button prevents the agent from reaching the monitored operations behind it.

### INV-AG-24: Error Recovery Loop Protection

The agent MUST limit consecutive error recovery attempts to `MAX_ERROR_RECOVERY` (3) per screen visit. `error_recovery_count` increments each iteration where error detection triggers and resets to 0 when no error is detected. When the limit is reached, detection is disabled and normal flow resumes.

**Rationale**: Without a limit, the agent could loop indefinitely filling inputs on a screen where validation errors persist (e.g., the app requires a specific format that InputValueGenerator cannot produce). The limit allows normal stuck detection to eventually trigger backtracking.

## New Scenarios

### Capability: Validation Error Detection

#### Scenario: Detect validation error and fill input

WHEN the agent clicks a submit button (e.g., "GENERATE HASH")
AND the resulting screen shows a validation error (text matching "Field required")
THEN `ErrorPatternMatcher.detect()` returns `detected=True` with confidence >= 0.7
AND `learn_node` resets `stuck_screen_count` to 0
AND `learn_node` sets `force_fill_input = True` in the result state
AND `algorithm_node` selects a SET_TEXT action targeting an EditText field
AND `InputValueGenerator` provides a test value (e.g., "test123")
AND the agent fills the input field

#### Scenario: Normal flow resumes after input is filled

WHEN the agent has filled an input field due to `force_fill_input`
AND the next screen does NOT contain validation error patterns
THEN `ErrorPatternMatcher.detect()` returns `detected=False`
AND `force_fill_input` is NOT set
AND the agent proceeds with normal exploration
AND the submit button is available for selection (NOT blacklisted)

#### Scenario: No false positive on error-like text

WHEN the agent analyzes a screen
AND the screen contains the word "Error" as part of a label (e.g., "Error Log", "Report Error")
AND the text matches an exclusion pattern
THEN `ErrorPatternMatcher.detect()` returns `detected=False`
AND exploration continues normally

#### Scenario: No input fields available after error detection

WHEN a validation error is detected
AND the current screen has no TEXT_CHANGE actions available
THEN `algorithm_node` clears `force_fill_input`
AND falls through to normal action selection
AND the submit action is NOT penalized

#### Scenario: Error detection disabled via configuration

WHEN `error_detection_enabled` is set to `False` in `RVAgentConfig`
THEN `_detect_validation_error()` returns `False` without scanning
AND `force_fill_input` is never set
AND no `track.error()` events are logged

#### Scenario: Confidence threshold filtering

WHEN a screen element contains a weak match (e.g., single word "required" in a label among 20 elements)
AND the match confidence is below `error_detection_confidence` (default 0.7)
THEN `ErrorPatternMatcher.detect()` returns `detected=False`
AND no error recovery is triggered

#### Scenario: Strong pattern guarantees minimum confidence

WHEN a screen element contains a multi-word validation pattern (e.g., "Field is required", "Cannot be empty")
THEN `ErrorPatternMatcher` assigns a minimum confidence of 0.8 regardless of element ratio
AND the error is detected (above default threshold of 0.7)

Strong patterns (multi-word, high-signal for validation errors):
- `field (is )?required`
- `enter a valid`
- `(cannot|can't) be (empty|blank)`
- `(please|must) (enter|provide|fill)`

#### Scenario: Error recovery loop protection

WHEN validation errors are detected for 3 consecutive iterations on the same screen
AND `error_recovery_count` reaches `MAX_ERROR_RECOVERY` (3)
THEN `_detect_validation_error()` returns `False` without scanning
AND `force_fill_input` is NOT set
AND normal exploration flow resumes (stuck detection may eventually trigger backtracking)
