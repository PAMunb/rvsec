# Delta Spec: Error Detection Integration (agent domain)

**Change**: gh18-error-detection
**Base spec**: `openspec/specs/agent/spec.md`
**Action**: Add new capability (error detection) to existing agent domain

## New Invariants

### INV-AG-20: Error Detection After Action

The agent detects application error indicators on the current screen after each action execution. Error detection uses text-based pattern matching on UI hierarchy elements (UIAutomator dump), applying regex patterns derived from `ErrorDetector` in rv-screen-parser.

**Rationale**: Without error detection, the agent repeats actions that cause errors (crashes, permission denials, network failures), wasting exploration budget. Text-based detection covers ~80% of error cases with zero additional dependencies.

### INV-AG-21: Failed Action Recording

When an error is detected after an action, the agent calls `record_action_failure()` on the current `ScreenNode`, recording which action led to the error state. This populates the failure data used by `FailedActionScorer`.

**Rationale**: Connects the existing (but unused) `record_action_failure()` infrastructure to actual error detection, enabling the scoring system to penalize failed actions.

### INV-AG-22: Failed Action Penalty

`FailedActionScorer` assigns a score of -9999 to actions that have been recorded as failures. Once penalized, a failed action is never selected again for the same screen node.

**Rationale**: This invariant already exists in the `FailedActionScorer` implementation but is currently inactive because no failure data is ever recorded (INV-AG-21 addresses this gap).

### INV-AG-23: Error Recovery Action

When an error is detected, the agent executes a BACK action to exit the error state before continuing exploration. This is triggered independently of the hash-based stuck detection.

**Rationale**: Error screens (dialogs, toasts, crash reporters) block further exploration. A BACK action is the standard Android mechanism to dismiss such overlays. The existing `StuckRecovery` handles hash-based stuck states; error recovery handles error-specific states.

## New Scenarios

### Capability: Error Detection

#### Scenario: Text-based error detection on permission denial

WHEN the agent executes a tap action on a UI element
AND the resulting screen contains a dialog with text matching "permission denied" (case-insensitive)
THEN the error detection system identifies an error of type "permission_error"
AND `record_action_failure()` is called with the action and error type
AND `FailedActionScorer` returns -9999 for that action on that screen node
AND the agent executes BACK to dismiss the permission dialog

#### Scenario: Text-based error detection on network error

WHEN the agent executes a tap action
AND the resulting screen contains text matching "no internet|connection failed|network error" (case-insensitive)
THEN the error detection system identifies an error of type "network_error"
AND the agent records the failure and executes BACK

#### Scenario: Text-based error detection on crash dialog

WHEN the agent executes an action
AND the resulting screen contains text matching "has stopped|keeps stopping|isn't responding" (case-insensitive)
THEN the error detection system identifies an error of type "crash"
AND the agent records the failure, executes BACK (or OK to dismiss ANR dialog)

#### Scenario: No false positive on normal error-like text

WHEN the agent analyzes a screen
AND the screen contains the word "Error" as part of a label or menu item (e.g., "Error Log", "Report Error")
AND no error dialog pattern is detected (no modal overlay, no crash indicators)
THEN the error detection system does NOT flag the screen as an error
AND exploration continues normally

#### Scenario: Failed action is never selected again

WHEN an action on screen node S has been recorded as a failure
AND the agent returns to screen node S in a later iteration
THEN `FailedActionScorer` returns -9999 for that action
AND the DFS strategy selects a different action (or backtracks if none available)

#### Scenario: Error detection does not trigger on successful actions

WHEN the agent executes an action
AND the resulting screen does not match any error patterns
THEN no failure is recorded
AND `FailedActionScorer` returns 0 for that action (neutral score)
AND exploration continues with normal scoring
