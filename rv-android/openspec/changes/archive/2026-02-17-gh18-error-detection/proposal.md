# Proposal: Validation Error Detection in rv-agent

**Date**: 2026-02-15
**Author**: Pedro Henrique Teixeira Costa (with Claude Code assistance)
**GitHub Issue**: [#18](https://github.com/PAMunb/rvsec/issues/18)
**Domains**: agent

## 1. Problem Statement

rv-agent explores Android applications using DFS-based algorithmic strategies and LLM-guided exploration. During exploration, the agent triggers actions that produce validation errors — "Field required", "Invalid format", "Please enter a valid email" — but has no mechanism to detect or react to them.

The consequence is that the agent gets stuck in unproductive loops:

1. Agent clicks a submit button (e.g., "GENERATE HASH") with empty input fields
2. The app shows a validation error on the input field
3. The agent sees a different screen hash (error indicator changed the UI), so stuck detection does not trigger
4. The agent selects the same button again, or moves on without ever filling the input
5. The crypto operation behind the button is never triggered

This is particularly harmful because submit buttons often trigger the monitored operations (MOP) that rv-agent is designed to reach. An unfilled input field prevents the agent from exercising the primary functionality of the app.

### Distinction: Validation Errors vs. App Crashes

Validation errors (precondition not met) and app crashes (action breaks the app) require opposite responses:

| Error Type | Example | Correct Response |
|------------|---------|-----------------|
| Validation error | "Field required" on empty input | Fill the input field, retry the action |
| App crash | ANR dialog, force-close | Avoid the action, backtrack |

This change addresses **validation errors only**. Crash detection is a separate concern (tracked by the TODO at `screen_node.py:120`).

## 2. Proposed Solution

Detect validation errors on screen and guide the agent to fill input fields before retrying. The approach uses a state flag (`force_fill_input`) following the same pattern as `force_back_action` and `force_restart_app` for learn_node-to-algorithm_node communication.

1. **Detect**: After each action, detect validation errors via visual analysis (screenshot color analysis)
2. **Suppress stuck counter**: Reset `stuck_screen_count` so the agent stays on the current screen instead of backing out
3. **Signal**: Set `force_fill_input = True` in agent state
4. **Fill**: algorithm_node uses spatial association to find the input field closest to the error indicator (EditText → SET_TEXT, Spinner → CLICK). Falls back to sequential iteration if no spatial match is found
5. **Resume**: On the next iteration, if no error is detected, normal exploration flow resumes

### Detection Approach: Visual (Color-Based via ErrorDetector)

Some Android apps display validation errors as purely visual indicators (red icons, colored underlines) where the UIAutomator dump is **identical** before and after the error — CryptoApp is the validated case. Text-based detection on the UIAutomator dump cannot detect these errors because there is no text change.

The visual approach uses `ErrorDetector` from rv-screen-parser, which analyzes screenshots for color-based error indicators (red regions, error icons). This component already exists and was validated:
- `ErrorDetector` on CryptoApp error screenshot (006.png): 1 error detected, type=VISUAL_INDICATOR, method=COLOR, conf=0.80
- `ErrorDetector` on CryptoApp normal screenshot (005.png): 0 errors detected (no false positives)

Screenshots are captured conditionally by `parse_ui_node`: only when the screen hash repeats (same screen after action), indicating a potential validation error. This avoids unnecessary screenshot overhead on normal screen transitions.

`VisualErrorDetector` (rv-agent wrapper) applies 4-stage false-positive filtering on the raw ErrorDetector results: confidence threshold, size filter (reject large UI elements), region filter (exclude status/navigation bar areas), and count filter (reject red-themed UIs with many indicators). These filters were designed from empirical testing on 14 apps (70 screenshots) where 20% produced false positives at conf>=0.7.

`opencv-python-headless` (already a transitive dependency via rv-screen-parser) provides the image processing. No Tesseract, no new apt packages, no Docker image changes needed. The headless variant avoids `libGL` requirements in Docker slim images.

## 3. Impact Assessment

### Modules Affected

| Module | Impact | Changes |
|--------|--------|---------|
| rv-agent | Primary | New `VisualErrorDetector` service, modifications to `parse_node`, `learn_node`, `decision_node`, `algorithm_node`, `RVAgent`, `AgentState`, `RVAgentConfig`, `tracking` |
| rv-screen-parser | Minimal | Change `opencv-python` to `opencv-python-headless` in pyproject.toml |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Visual false positives (red UI elements not errors) | Low | Low | 4-stage filtering: confidence threshold, size filter (>80px), region filter (top 5% / bottom 6% of screen), count filter (>5 indicators) |
| No input field available on error screen | Low | Low | Clear flag and fall through to normal flow |
| Performance overhead in hot loop | Low | Low | ~50ms visual analysis, but only on hash-repeat screens |
| cv2 import failure | Very Low | Low | `VisualErrorDetector.detect()` returns `detected=False` on import/load failure — graceful degradation |

## 4. Pre-conditions

- gh17-refactoring-cleanup completed (cleans up related TODOs in the same files)

## 5. What This Change Does NOT Do

- Does NOT connect `record_action_failure()` or `FailedActionScorer` — these exist in the code but are never called in the workflow (TODO #19). Validation errors are not action failures; the action should be retried after filling inputs
- Does NOT force BACK — the agent should stay on the current screen and fill inputs
- Does NOT modify `screen_node.py` — the TODO at line 120 (issue #19) covers crash/timeout/error detection broadly, which is a separate concern
- Does NOT require Tesseract or new apt packages — `opencv-python-headless` is a pip-only dependency, already transitive via rv-screen-parser
- Does NOT add new system-level dependencies — only switches `opencv-python` to `opencv-python-headless` (same API, no `libGL` requirement)
- Does NOT detect text-based validation errors — apps that use `TextInputLayout.setError()` change the UIAutomator dump (screen hash changes), so the hash-repeat trigger does not fire. See Section 6 for details

## 6. Scope and Future Directions

### 6.1 gh18 Scope: Visual Detection on Same-Screen Errors

gh18 implements visual error detection for the specific case where an action produces a validation error but the UIAutomator dump does **not** change (screen hash repeats). This covers apps with purely visual error indicators (red icons, colored underlines) where the UI hierarchy is unchanged. CryptoApp is the validated case.

rv-agent explores 188+ Android apps with diverse UIs (ICST study). The visual detector must work generically across all of them, which is why `VisualErrorDetector` applies 4-stage false-positive filtering (confidence, size, region, count) validated empirically on 14 apps. The filter parameters are exposed via `RVAgentConfig` for Optuna calibration in gh9-docker-calibration.

### 6.2 Known Limitation: Standard Material Design TextInputLayout

Most Android apps that follow Material Design 3 guidelines use `TextInputLayout.setError("message")` to show validation errors. When `setError()` is called:

1. A new `TextView` child element appears in the UI hierarchy with the error text
2. The UIAutomator dump **changes** (new text element)
3. The screen hash **changes** (dump content is different)
4. The `hash-repeat` condition is **false**
5. No error detection screenshot is captured — the validation error goes **undetected** by gh18

For these apps, the agent sees the error screen as a "new screen" and explores it normally — which may or may not lead to filling the input, depending on the ranking algorithm. The error text is visible in the `ScreenDescription` but the agent has no mechanism to recognize it as an error or to prioritize filling the associated field.

This is a legitimate coverage gap. CryptoApp (visual-only errors, dump unchanged) is the less common pattern. Standard M3 apps (text-based errors, dump changed) are more common across the 188-app corpus.

### 6.3 Future Work: Text-Based Error Detection (separate change)

A complementary detection method could analyze UIAutomator dump content for error keywords when the screen hash **changes**. This would cover the standard M3 case:

- **Trigger**: Screen hash changes AND new text elements contain error keywords
- **Signal**: Keywords in UIAutomator text/content-desc: "required", "invalid", "error", "inválido", "obrigatório", "campo obrigatório"
- **Source**: Standard M3 `TextInputLayout.setError()` — error text appears as a child `TextView` in the UI hierarchy, with Material Design's `error` color role (#B3261E light, #F2B8B5 dark)
- **Response**: Same `force_fill_input` mechanism as gh18
- **Scope**: Separate change — different trigger, different detection method, same response mechanism

The combination of visual detection (gh18, hash repeats) and text-based detection (future, hash changes) would cover both categories of Android apps. The Gemini deep research analysis identified additional signals (accessibility metadata `error` attribute, template matching for M3 error icons, dominant palette analysis) that could further refine detection, but these require incremental evaluation against the 188-app corpus.
