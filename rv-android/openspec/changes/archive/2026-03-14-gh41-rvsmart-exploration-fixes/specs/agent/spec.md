## Purpose

Delta spec for the agent domain addressing 4 exploration bugs in RVSmart that cause coverage regression. These bugs affect phase transition logic, tarpit detection, retry gating, and cluster forcing thresholds.

## MODIFIED Requirements

### Requirement: Phase Transition from DFS to Stochastic

The PhaseController SHALL transition from PHASE_1 (systematic DFS) to PHASE_3 (stochastic escape) only when all reachable content states have had all their *widget* actions tested. The untested action check MUST exclude system action types (BACK, RESTART) from the `executedActions` count before comparing against `totalActions`, because `totalActions` counts only interactive widgets while `executedActions` includes BACK/RESTART signatures recorded via `graph.recordAction()`.

The comparison in `hasUntestedActionsInAnyReachableState()` SHALL filter signatures matching system action patterns (e.g., signatures starting with "back@" or "restart@") before comparing `executedActions.size()` against `totalActions`.

#### Scenario: Screen with 5 widgets and BACK/RESTART recorded
- **WHEN** a ContentNode has `totalActions=5` and `executedActions` contains 3 widget signatures plus "back@0,0" and "restart@0,0" (size=5)
- **THEN** `hasUntestedActionsInAnyReachableState()` SHALL return `true` because only 3 widget actions were tested (not 5)
- **AND** the phase SHALL remain PHASE_1

#### Scenario: All widget actions tested with system actions also recorded
- **WHEN** a ContentNode has `totalActions=5` and `executedActions` contains 5 widget signatures plus "back@0,0" and "restart@0,0" (size=7)
- **THEN** `hasUntestedActionsInAnyReachableState()` SHALL return `false` because all 5 widget actions were tested
- **AND** phase transition to PHASE_3 MAY proceed if plateau is also detected

### Requirement: Tarpit Detection Threshold and Reset Conditions

The TarpitDetector SHALL mark a screen as tarpit only after `tarpitThreshold` (default 50) consecutive iterations on the same screen hash with no new state, no new MOP coverage, AND no action effect (hadEffect=false). The `recordIteration()` method SHALL accept a 4th parameter `hadEffect` (boolean) indicating whether the previous action caused a screen hash change.

The tarpit counter for a screen hash SHALL reset to 0 when ANY of these conditions is true:
1. The screen hash changed from the previous iteration
2. A new state was discovered (`hasNewState=true`)
3. New MOP coverage was detected (`hasNewMop=true`)
4. The action had effect (`hadEffect=true`)

The default `tarpit_threshold` in Config SHALL be 50, overridable via properties file.

#### Scenario: Hub screen with many widgets explored within threshold
- **WHEN** the agent spends 49 consecutive iterations on a hub Activity with 20 widgets, no new state or MOP, and no hadEffect
- **THEN** the screen SHALL NOT be marked as tarpit
- **AND** systematic DFS exploration SHALL continue

#### Scenario: Screen marked as tarpit after threshold
- **WHEN** the agent spends 50 consecutive iterations on a screen with no new state, no new MOP, and no hadEffect
- **THEN** the screen SHALL be marked as tarpit
- **AND** the hash SHALL be excluded from BacktrackBfs and FrontierFinder recovery targets

#### Scenario: Tarpit counter resets on hadEffect
- **WHEN** the agent has spent 45 iterations on a screen (approaching threshold) and then executes an action where `hadEffect=true` (navigated to a different screen hash)
- **THEN** the tarpit counter for that screen SHALL reset to 0

### Requirement: Retry Saturation Gate Threshold

The AgentLoop retry gate SHALL skip multi-attempt retries only when screen saturation reaches `retrySaturationThreshold` (default 0.95). At saturation below this threshold, the retry loop SHALL execute normally (up to `maxRetriesPerCycle` attempts).

The default `retry_saturation_threshold` in Config SHALL be 0.95, overridable via properties file.

#### Scenario: Screen at 80% saturation retries normally
- **WHEN** a screen has saturation rate 0.80 (4/5 widgets saturated) and the agent selects an action that has no effect
- **THEN** the retry loop SHALL execute (up to `maxRetriesPerCycle` additional attempts)

#### Scenario: Screen at 96% saturation skips retry
- **WHEN** a screen has saturation rate 0.96 (exceeds 0.95 threshold)
- **THEN** the retry loop SHALL be skipped (`maxRetries=0`)

### Requirement: Cluster Forcing Threshold for Phase 3

The PhaseController SHALL force a cluster to Phase 3 stochastic selection only after `CLUSTER_FORCE_THRESHOLD` (50) Phase 1 entries on the same structural hash. This gives the DFS algorithm sufficient time to systematically explore hub screens before falling back to stochastic selection.

#### Scenario: Hub screen visited 49 times in Phase 1
- **WHEN** a structural hash has been entered 49 times during PHASE_1
- **THEN** `isClusterForced()` SHALL return `false`
- **AND** the cluster SHALL use systematic DFS (Phase 1 filterUntested)

#### Scenario: Hub screen visited 50 times in Phase 1
- **WHEN** a structural hash has been entered 50 times during PHASE_1
- **THEN** `isClusterForced()` SHALL return `true`
- **AND** the cluster SHALL use Phase 3 stochastic selection

## Invariants

- **INV-AGT-41-01**: `hasUntestedActionsInAnyReachableState()` MUST NOT count BACK or RESTART signatures when comparing against `totalActions`. The comparison MUST only consider widget action signatures.
- **INV-AGT-41-02**: TarpitDetector MUST reset its counter for a screen hash whenever `hadEffect=true`, preventing false-positive tarpit marking on screens where actions produce navigation.
- **INV-AGT-41-03**: The retry saturation gate MUST NOT suppress retries when screen saturation is below `retrySaturationThreshold` (default 0.95).
