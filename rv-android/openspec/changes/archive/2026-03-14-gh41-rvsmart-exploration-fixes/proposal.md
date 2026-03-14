## Why

GitHub Issue: #40

Experiment with 20 APKs x 6 reps x 300s revealed 4 secondary exploration bugs introduced by gh35+gh39+gh40 that cause coverage regression even after the ActivityBudgetTracker death spiral was fixed (budget=999_999). Mean MOP coverage dropped from 28.1% (baseline mvp) to 24.4% (-3.7%), with worst cases reaching -21.2 MOP (ApkTrack) and -12.9 MOP (hourlyreminder). Root cause analysis identified premature phase transitions, aggressive tarpit detection, over-eager retry gating, and low cluster forcing thresholds as the four contributing factors.

## What Changes

- **Fix PhaseController premature PHASE_3 transition**: `hasUntestedActionsInAnyReachableState()` inflates `executedActions` count with BACK/RESTART signatures, causing early PHASE_1→PHASE_3 transition. Fix by filtering system action types from the comparison.
- **Fix TarpitDetector aggressive hub marking**: Threshold=15 marks hub Activities as tarpits within ~1 second, excluding them from BacktrackBfs and FrontierFinder recovery. Fix by raising threshold and/or adding `hadEffect` as a counter-reset condition.
- **Fix retry saturation gate over-suppression**: `RetrySaturationThreshold=0.8` skips retries when 4/5 widgets are saturated, missing the potentially productive 5th widget. Fix by raising threshold to 0.95.
- **Fix cluster forcing threshold too low**: `CLUSTER_FORCE_THRESHOLD=20` forces home screen clusters to Phase 3 stochastic after ~1-2 minutes. Fix by raising to 50.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `agent`: PhaseController phase transition logic, TarpitDetector threshold and reset conditions, retry saturation gate threshold, cluster forcing threshold — all affect FR28 (exploration strategy) and FR30 (stuck recovery).

## Impact

- **rvsmart** (`rvsec/rvsec-android/rvsmart`): All 4 fixes are in the Java exploration agent
  - `strategy/PhaseController.java` — Bug 1 (premature PHASE_3)
  - `recovery/TarpitDetector.java` — Bug 2 (aggressive tarpit marking)
  - `core/AgentLoop.java` — Bugs 2, 3 (tarpit hadEffect, retry gate)
  - `core/Config.java` — Bugs 2, 3, 4 (default thresholds)
  - `strategy/ActionSelector.java` — Bug 4 (cluster forcing)
- **rvsmart-tool** (Python wrapper): No changes needed, but JAR must be rebuilt with `mvn install`
- References: FR28 (exploration strategy), FR30 (stuck recovery), NFR02 (performance)
