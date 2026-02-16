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

1. **Detect**: After each action, scan UI element texts for validation error patterns (regex on UIAutomator dump)
2. **Suppress stuck counter**: Reset `stuck_screen_count` so the agent stays on the current screen instead of backing out
3. **Signal**: Set `force_fill_input = True` in agent state
4. **Fill**: algorithm_node finds the next unfilled input field and generates a SET_TEXT action with a test value
5. **Resume**: On the next iteration, if no error is detected, normal exploration flow resumes

### Detection Approach: Text-Based (Zero Dependencies)

Scan `ScreenDescription.items` for error text patterns via regex. The patterns are derived from `ErrorDetector._detect_text_errors()` in rv-screen-parser. This approach runs in ~5ms, requires no new dependencies (no OpenCV, no Tesseract), and handles the most common validation error cases (textual errors displayed in input fields, snackbars, and toasts).

## 3. Impact Assessment

### Modules Affected

| Module | Impact | Changes |
|--------|--------|---------|
| rv-agent | Primary | New `ErrorPatternMatcher` service, modifications to `learn_node`, `decision_node`, `algorithm_node`, `RVAgent`, `AgentState`, `RVAgentConfig`, `tracking` |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| False positives (normal text matched as error) | Medium | Low | Configurable confidence threshold, exclusion patterns for common false positives ("Error Log", "Report Error") |
| No input field available on error screen | Low | Low | Clear flag and fall through to normal flow |
| Performance overhead in hot loop | Low | Low | ~5ms text matching, only on parsed UI elements |

## 4. Pre-conditions

- gh17-refactoring-cleanup completed (cleans up related TODOs in the same files)

## 5. What This Change Does NOT Do

- Does NOT call `record_action_failure()` — validation errors are not action failures
- Does NOT use `FailedActionScorer` — the -9999 penalty blacklists actions permanently, which is wrong for validation errors (the action should be retried after filling inputs)
- Does NOT force BACK — the agent should stay on the current screen and fill inputs
- Does NOT modify `screen_node.py` — the TODO at line 120 (issue #19) covers crash/timeout/error detection broadly, which is a separate concern
- Does NOT add OpenCV or Tesseract dependencies
