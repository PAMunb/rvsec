# Delta Spec: Validation Error Detection (agent domain)

**Change**: gh18-error-detection
**Base spec**: `openspec/specs/agent/spec.md`
**Action**: Add validation error detection and input-filling guidance to the agent

## New Invariants

### INV-AG-20: Validation Error Detection After Action

The agent detects validation error indicators on the current screen after each action execution. Detection uses visual analysis (color-based) on a screenshot via `VisualErrorDetector`, which wraps rv-screen-parser's `ErrorDetector`. Screenshots are only available when `parse_ui_node` detects that the screen hash repeats (same screen after action), indicating the previous action did not cause a screen transition. Detection runs in `learn_node` before stuck detection.

**Rationale**: Without error detection, the agent clicks submit buttons with empty input fields, gets validation errors, and never fills the inputs. This prevents the agent from reaching monitored operations (MOP) behind form submissions. rv-agent explores 188+ Android apps; some display validation errors as purely visual indicators (red icons, colored underlines) where the UIAutomator dump is identical before and after the error — CryptoApp is the validated case. For these apps, text-based detection on UI element text is insufficient, and visual detection via screenshot analysis is required. Note: apps using standard Material Design `TextInputLayout.setError()` change the UIAutomator dump (different screen hash), so gh18's hash-repeat trigger does not cover them — this is documented as future work (text-based detection).

### INV-AG-21: Stuck Counter Suppression on Validation Error

When a validation error is detected, the agent resets `stuck_screen_count` to 0. This prevents the stuck detection system from forcing a BACK action, which would navigate away from a screen where the agent should stay and fill inputs.

**Rationale**: Validation errors may not change the screen hash (the error indicator appears on the same screen), which would trigger stuck detection. But backing out is the wrong response — the agent should stay and fill the required inputs.

### INV-AG-22: Input Filling Guidance via `force_fill_input` Flag

When a validation error is detected, `learn_node` sets `force_fill_input = True` and `error_indicators` (list of `ErrorIndicator` objects with coordinates) in the agent state. `algorithm_node` responds by using spatial association to find the input field closest to an error indicator and generating an appropriate action: SET_TEXT for EditText fields, CLICK for Spinner/dropdown fields. If spatial association finds no match, it falls back to sequential iteration of TEXT_CHANGE actions. After the input action is generated, the flag and indicators are cleared.

**Rationale**: The `force_fill_input` flag follows the same communication pattern as `force_back_action` (Level 1 stuck) and `force_restart_app` (Level 2 stuck). learn_node detects conditions, algorithm_node generates the appropriate action. Spatial association ensures the right input is filled when multiple fields show errors simultaneously.

### INV-AG-23: Validation Errors Do NOT Penalize Actions

Validation errors MUST NOT connect to `record_action_failure()` or `FailedActionScorer`. These components exist in the codebase but are not called anywhere in the workflow (TODO #19). The action that caused the validation error (e.g., a "GENERATE HASH" button) is correct — it only fails because input preconditions are not met. Once inputs are filled, the same action should be retried.

**Rationale**: `FailedActionScorer` assigns -9999, permanently blacklisting the action on that screen. Even though it is currently dead code (never triggered), gh18 must not connect validation errors to it. Blacklisting a submit button would prevent the agent from reaching the monitored operations behind it.

### INV-AG-24: Error Recovery Loop Protection

The agent MUST limit consecutive error recovery attempts to `MAX_ERROR_RECOVERY` (3) per screen visit. `error_recovery_count` increments each iteration where error detection triggers. When the limit is reached, detection is disabled and the counter stays at MAX — it does NOT reset while the screen remains the same (screenshot still available). The counter resets to 0 only when the screen changes (no screenshot available, meaning the screen hash differs from the previous iteration). This 3-way branching prevents an infinite cycle where reaching MAX → resetting counter → re-enabling detection → reaching MAX again every 4 iterations.

**Rationale**: Without a limit, the agent could loop indefinitely filling inputs on a screen where validation errors persist (e.g., the app requires a specific format that InputValueGenerator cannot produce). Without the 3-way branching (separating "screen changed" from "max reached"), resetting the counter unconditionally when detection returns None would create a 4-iteration infinite cycle: 3 detection iterations + 1 skip-and-reset iteration, repeating forever. The correct behavior after MAX is reached: `stuck_screen_count` accumulates normally (3, 4, 5, ... 8) until Level 1 stuck detection triggers BACK, navigating the agent away from the screen.

### INV-AG-25: Conditional Screenshot Capture for Error Detection

`parse_ui_node` captures a screenshot for error detection ONLY when the current screen hash equals the previous screen hash (same screen after action). The screenshot path is stored in `state["error_detection_screenshot"]`. When the screen hash differs (normal screen transition), no screenshot is captured and `error_detection_screenshot` is set to None.

**Rationale**: Taking a screenshot every iteration wastes ~100ms. The hash-repeat condition targets the exact scenario where validation errors occur: the agent performed an action but the screen didn't change. If the screen changed, there is no validation error to detect.

### INV-AG-26: Spatial Association for Error-to-Input Mapping

When `force_fill_input` is set, `algorithm_node` uses spatial association to map each `ErrorIndicator` (with x, y, width, height coordinates in device pixel space) to the nearest actionable screen item. Error indicators can appear near any component type — not just EditText and Spinner. The association algorithm calculates an overlap score between each error indicator's bounding box and each screen item's bounds. Widget-type boosts (1.2x for EditText, 1.1x for Spinner) serve as prioritization tiebreakers when multiple items overlap similarly, not as filters. A below-field heuristic handles error indicators positioned up to 100px below a field. The highest-scoring match above the minimum threshold (0.1) is selected. The action generated depends on the matched item's available actions: TEXT_CHANGE → SET_TEXT with test value, CLICK → CLICK to interact. If no spatial match is found, the algorithm falls back to sequential iteration of TEXT_CHANGE actions via `_find_next_input_action()`.

**Rationale**: CryptoApp screenshot 009.png shows errors on both EditText AND Spinner fields simultaneously, but validation errors can appear near any interactive component. Spatial association ensures the correct field is addressed based on proximity to the error indicator, rather than arbitrarily filling the first input found. The algorithm is adapted from the rvandroid tool's `ErrorAssociationStrategy` which used geometric overlap for error→field mapping.

### INV-AG-27: System Region Masking for Error Indicators

`VisualErrorDetector` filters out error indicators located in system bar areas: top 5% of the screenshot height (status bar) and bottom 6% (navigation bar). These areas contain system-drawn icons (notifications, clock, battery, back/home/recents) that the app developer does not control. The percentages match the existing thresholds used by `RVAgentStrategy._is_system_action()` (`STATUSBAR_Y_PERCENT=0.05`, `NAVBAR_Y_PERCENT=0.94`) for consistency across the system.

**Rationale**: rv-agent explores 188+ Android apps across diverse device themes. System bar icons may appear red on certain themes (e.g., alarm icon, notification badges), causing false positives when ErrorDetector scans the full screenshot. Validation errors appear near input fields in the content area, never in system bars. The region filter uses percentage-based thresholds rather than fixed pixel values so it adapts to different device resolutions. The filter runs between size filtering and count filtering — after removing oversized indicators but before the count check, so system bar icons don't inflate the indicator count.

## New Scenarios

### Capability: Validation Error Detection

#### Scenario: Visual error detected via color analysis (CryptoApp case)

WHEN the agent clicks a submit button (e.g., "GENERATE HASH") with empty input fields
AND the resulting screen shows a red `!` icon and red underline on the EditText
AND the UIAutomator dump is **identical** before and after the error (same screen hash)
THEN `parse_ui_node` takes a screenshot (hash repeats)
AND `VisualErrorDetector.detect()` returns `detected=True` with `error_indicators` containing `ErrorIndicator` objects with coordinates and per-indicator confidence >= 0.7
AND `learn_node` resets `stuck_screen_count` to 0
AND `learn_node` sets `force_fill_input = True` and `error_indicators` in the result state
AND `algorithm_node` uses spatial association to find the input field closest to the error indicator
AND for an EditText field: generates SET_TEXT action with test value from `InputValueGenerator`
AND the agent fills the input field

#### Scenario: Screenshot captured only when screen hash repeats

WHEN the agent performs an action
AND `parse_ui_node` computes the new screen hash
AND the new hash equals `previous_screen_hash`
THEN `parse_ui_node` calls `agent.device.take_screenshot()` and stores the path in `state["error_detection_screenshot"]`

WHEN the agent performs an action
AND `parse_ui_node` computes the new screen hash
AND the new hash differs from `previous_screen_hash`
THEN `state["error_detection_screenshot"]` is set to None
AND no screenshot overhead is incurred

#### Scenario: Normal flow resumes after input is filled

WHEN the agent has filled an input field due to `force_fill_input`
AND the next screen has a different screen hash (input changed the UI)
THEN `parse_ui_node` does NOT capture a screenshot (hash differs)
AND `_detect_validation_error()` returns `False` (no screenshot available)
AND `force_fill_input` is NOT set
AND the agent proceeds with normal exploration
AND the submit button is available for selection (NOT blacklisted)

#### Scenario: Spinner validation error (CLICK to open dropdown)

WHEN validation errors are detected on both a Spinner and an EditText field
AND `error_indicators` contains two `ErrorIndicator` objects with coordinates
THEN `algorithm_node` spatially associates each error indicator to the nearest input field
AND for the Spinner field: generates CLICK action to open the dropdown (not SET_TEXT)
AND for the EditText field (in a subsequent iteration): generates SET_TEXT action with test value
AND both fields are handled in priority order by spatial proximity to error indicators

#### Scenario: Spatial fallback to sequential iteration

WHEN a validation error is detected
AND `error_indicators` are available with coordinates
AND spatial association finds no screen item above the minimum match threshold (0.1)
THEN `algorithm_node` falls back to `_find_next_input_action()` which iterates TEXT_CHANGE actions sequentially
AND the first available input field with remaining test values is selected

#### Scenario: No input fields available after error detection

WHEN a validation error is detected
AND the current screen has no TEXT_CHANGE actions AND no Spinner actions available
AND both spatial and sequential search find no match
THEN `algorithm_node` clears `force_fill_input` and `error_indicators`
AND falls through to normal action selection
AND the submit action is NOT penalized

#### Scenario: Error detection disabled via configuration

WHEN `error_detection_enabled` is set to `False` in `RVAgentConfig`
THEN `parse_ui_node` does NOT capture error detection screenshots
AND `_detect_validation_error()` returns `False` without analyzing
AND `force_fill_input` is never set
AND no `track.error()` events are logged

#### Scenario: Error recovery loop protection

WHEN validation errors are detected for 3 consecutive iterations on the same screen
AND `error_recovery_count` reaches `MAX_ERROR_RECOVERY` (3)
THEN detection is skipped (3-way branch: screenshot exists BUT count >= MAX)
AND `error_recovery_count` stays at 3 (does NOT reset to 0)
AND `force_fill_input` is NOT set
AND `stuck_screen_count` accumulates normally (not suppressed)
AND after ~5 more iterations, Level 1 stuck detection triggers BACK

WHEN the agent navigates to a different screen after MAX_ERROR_RECOVERY
AND the new screen hash differs from the previous hash
THEN `error_detection_screenshot` is None (no screenshot taken)
AND `error_recovery_count` resets to 0 (3-way branch: no screenshot → screen changed)
AND error detection is re-enabled for the new screen

#### Scenario: False-positive filtering on red/pink-themed apps

WHEN `VisualErrorDetector.detect()` is called on a screenshot
AND `ErrorDetector` returns indicators where individual width OR height exceeds `error_max_indicator_size` (default 80 px)
THEN those oversized indicators are filtered out before the region and count checks
AND only small indicators (likely real error icons) are considered

WHEN `VisualErrorDetector.detect()` is called on a screenshot
AND after confidence, size, and region filtering, the remaining indicator count exceeds `error_max_indicator_count` (default 5)
THEN `detect()` returns `ValidationErrorResult(detected=False, ...)` — the screen is assumed to have a red/pink theme, not real validation errors
AND the agent continues with normal exploration

#### Scenario: System region masking excludes status and navigation bar

WHEN `VisualErrorDetector.detect()` is called on a screenshot
AND `ErrorDetector` returns indicators where the y-coordinate is within the top 5% of the screenshot height (status bar area)
THEN those indicators are filtered out as system bar icons (notifications, clock, battery)
AND they do not count toward the indicator total

WHEN `VisualErrorDetector.detect()` is called on a screenshot
AND `ErrorDetector` returns indicators where the y-coordinate is within the bottom 6% of the screenshot height (navigation bar area)
THEN those indicators are filtered out as navigation bar elements (back, home, recents)
AND they do not count toward the indicator total

WHEN `VisualErrorDetector.detect()` is called on a screenshot
AND all indicators after confidence, size, and region filtering are in the content area (between 5% and 94% of screen height)
THEN only those content-area indicators proceed to the count check
AND the filtering is resolution-independent (percentage-based, matching RVAgentStrategy thresholds)

#### Scenario: Graceful degradation when cv2 unavailable

WHEN `VisualErrorDetector.detect()` is called
AND `cv2` cannot be imported or `cv2.imread()` returns None
THEN `detect()` returns `ValidationErrorResult(detected=False, error_indicators=[], confidence=0.0, detection_method="visual_color")`
AND the agent continues without error detection
AND no exception is raised
