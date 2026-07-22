## Context

This change fixes 4 secondary exploration bugs in RVSmart (refs #40) that cause coverage regression even after the ActivityBudgetTracker death spiral was fixed. The bugs were identified through experiment analysis (20 APKs x 6 reps x 300s) and source code correlation with the top 5 regressing APKs.

All fixes are in the RVSmart Java agent at `rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/`. No Python module changes are needed — only JAR rebuild.

References: FR28 (exploration strategy), FR30 (stuck recovery), NFR02 (performance).

## Architecture

All 4 bugs are in the exploration decision pipeline:

```
AgentLoop (iteration)
  │
  ├── PhaseController.onIteration() ─── Bug 1: premature PHASE_3 transition
  │     └── hasUntestedActionsInAnyReachableState()
  │           counts BACK/RESTART in executedActions ← FIX: filter system actions
  │
  ├── ActionSelector.select()
  │     ├── isClusterForced() ─── Bug 4: threshold=20 too low
  │     │     └── phase1ReentriesByCluster >= CLUSTER_FORCE_THRESHOLD ← FIX: raise to 50
  │     └── selectPhase1() → retry loop
  │           └── saturation >= 0.8 → skip retry ─── Bug 3: too aggressive
  │                 └── RetrySaturationThreshold ← FIX: raise to 0.95
  │
  └── TarpitDetector.recordIteration() ─── Bug 2: threshold=15 too low
        └── consecutive no-progress >= threshold
              ← FIX: raise to 50, add hadEffect reset
```

### Key Components

| Component | Responsibility | Fix |
|-----------|---------------|-----|
| `PhaseController.hasUntestedActionsInAnyReachableState()` | Decides if DFS exploration is complete | Filter BACK/RESTART from executedActions count |
| `TarpitDetector.recordIteration()` | Marks screens with no progress as tarpits | Raise threshold 15→50, add hadEffect reset |
| `AgentLoop` (retry gate) | Skips retries on saturated screens | Raise threshold 0.8→0.95 |
| `PhaseController.isClusterForced()` | Forces clusters to Phase 3 stochastic | Raise threshold 20→50 |
| `Config` | Default values for all thresholds | Update 3 defaults |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Phase transition excludes system actions | `PhaseController.hasUntestedActionsInAnyReachableState()` | `PhaseControllerTest.testSystemActionsExcludedFromUntestedCheck` |
| Tarpit threshold configurable, default 50 | `Config.getTarpitThreshold()`, `TarpitDetector` | `ConfigTest.tarpitThresholdDefault`, `TarpitDetectorTest` |
| Tarpit resets on hadEffect | `TarpitDetector.recordIteration(hash, newState, newMop, hadEffect)` | `TarpitDetectorTest.testResetOnHadEffect` |
| Retry gate threshold 0.95 | `Config.getRetrySaturationThreshold()` | `ConfigTest.testRetrySaturationThresholdDefault` |
| Cluster force threshold 50 | `PhaseController.CLUSTER_FORCE_THRESHOLD` | `PhaseControllerTest.testClusterForceThreshold` |

## Goals / Non-Goals

**Goals:**
- Restore MOP and method coverage to baseline levels by fixing 4 identified bugs
- All fixes are simple threshold adjustments or small logic corrections — no architectural changes
- All fixes are configurable via properties file for future tuning

**Non-Goals:**
- Redesign the phase transition system
- Redesign the tarpit detection approach
- Redesign the ActivityBudgetTracker (remains disabled at 999_999)
- Add new scorers or change scorer weights

## Decisions

### Decision 1: Filter system actions in PhaseController (not change recording)

**Choice**: Filter BACK/RESTART signatures in `hasUntestedActionsInAnyReachableState()` rather than stopping their recording in `graph.recordAction()`.

**Rationale**: `graph.recordAction()` feeds other consumers (reward propagation, execution counts for decay scorer). Changing what gets recorded would have cascading effects. Filtering at the comparison point is isolated and safe.

**Alternative rejected**: Add a separate `executedWidgetActions` set in ContentNode — more invasive, adds state duplication.

### Decision 2: Raise tarpit threshold to 50 AND add hadEffect reset

**Choice**: Both changes together. Threshold alone would be insufficient for apps with many widgets per screen.

**Rationale**: At 14 evt/s, 50 iterations = ~3.5 seconds — enough to explore a screen with 15-20 widgets. The hadEffect reset ensures the counter resets when the agent successfully navigates, even if no new state is discovered (revisiting a known screen).

### Decision 3: Add hadEffect parameter to TarpitDetector.recordIteration()

**Choice**: Add a 4th boolean parameter `hadEffect` to the existing method signature.

**Rationale**: The method already takes 3 booleans. Adding a 4th keeps the API simple. The caller (AgentLoop) already has `hadEffect` computed from hash comparison.

### Decision 4: Raise retry saturation from 0.8 to 0.95

**Choice**: 0.95 rather than 1.0.

**Rationale**: At 1.0, the gate never fires (all widgets must be fully saturated). At 0.95, it fires only when essentially all widgets are explored (e.g., 19/20 saturated), preserving the gate's intent while avoiding premature suppression.

### Decision 5: Raise cluster force threshold from 20 to 50

**Choice**: Simple constant change in PhaseController.

**Rationale**: 50 visits at ~14 evt/s = ~3.5 seconds. This gives the DFS algorithm enough time to systematically explore a hub screen before forcing stochastic selection.

## Data Flow

No data flow changes. All fixes modify thresholds or filtering logic within existing data paths.

## Error Handling

No new error conditions. All changes are to threshold values and boolean logic.

## Risks / Trade-offs

- **[Tarpit never fires]** → Threshold 50 means screens need 50 consecutive no-progress iterations before tarpit marking. With hadEffect reset, a navigating agent may never trigger tarpit on any screen. This is acceptable — tarpit was causing more harm than good at threshold=15. Stuck detection (threshold=7) provides faster recovery for truly stuck situations.
- **[Retry gate rarely fires]** → At 0.95, the gate only fires on nearly-fully-explored screens. This means the agent may spend extra time retrying on explored screens. Acceptable trade-off vs missing productive unexplored widgets.
- **[Cluster forcing delay]** → At 50, hub screens keep DFS for ~3.5 seconds instead of ~1.4. If the hub is truly exhausted, this delays Phase 3 stochastic by ~2 seconds. Negligible cost vs the benefit of systematic DFS.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | PhaseController system action filtering | JUnit 5 with mock ContentGraph | ~3 tests |
| Unit | TarpitDetector threshold + hadEffect reset | JUnit 5 | ~4 tests |
| Unit | Config default values | JUnit 5 | ~3 tests |
| Integration | Full exploration loop (no regressions) | Existing test suite | existing |

## Open Questions

None — all fixes are straightforward threshold/logic corrections with clear rationale from experiment data.
