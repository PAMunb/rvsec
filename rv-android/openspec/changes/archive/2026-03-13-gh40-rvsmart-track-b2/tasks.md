<!-- SUBAGENT DISPATCH HINTS
File inventory: ~8 files modified/created (Java), ~6 test files
Groups A, B, C are independent (no shared files) → dispatch in parallel
Group D depends on A+B+C → sequential after all complete
Group E (verification) → sequential after D

Critical path: A+B+C (parallel) → D → E

Group A: ActivityBudgetTracker (NEW + Config + 2 test files) — MEDIUM complexity
Group B: TarpitDetector + ContentGraph tarpit fields (NEW + graph edit + 2 test files) — MEDIUM complexity
Group C: PhaseController simplification (PhaseController + ActionSelector + 2 test files) — MEDIUM complexity (deletion + refactoring)
Group D: Integration wiring in AgentLoop + BacktrackBfs/StuckDetector tarpit pass-through — MEDIUM (depends on A+B+C)
Group E: Verification — sequential

All Java files at: $RVSEC_HOME/rvsec/rvsec-android/rvsmart/
Source: src/main/java/br/unb/cic/rvsmart/
Tests: src/test/java/br/unb/cic/rvsmart/
Use /superpowers:test-driven-development for Groups A and B (new classes)
-->

# Tasks: gh40-rvsmart-track-b2

GitHub Issue: #40

## 1. Per-Activity Iteration Budget (Group A — independent, TDD)

- [x] 1.1 Add 2 new config parameters to `Config.java`: `activity_base_budget` (default 10), `budget_per_widget` (default 3). Add getters `getActivityBaseBudget()` and `getBudgetPerWidget()`.
- [x] 1.2 Write `ActivityBudgetTrackerTest.java` (TDD): (a) budget computed correctly (10 + 20×3 = 70), (b) isBudgetExhausted returns false before budget, (c) isBudgetExhausted returns true at budget, (d) unregistered Activity returns false, (e) BACK/RESTART actions not affected by budget, (f) budget is permanent (no reset) — ≥6 tests
- [x] 1.3 Create `strategy/ActivityBudgetTracker.java`: `registerActivity(activityName, widgetCount)` computes budget, `recordIteration(activityName)` increments counter, `isBudgetExhausted(activityName)` returns true when counter >= budget. Config params passed via constructor.
- [x] 1.4 Update `ConfigTest.java`: assert new defaults (activity_base_budget=10, budget_per_widget=3)

## 2. Anti-Tarpit Detection (Group B — independent, TDD)

- [x] 2.1 Add 1 new config parameter to `Config.java`: `tarpit_threshold` (default 15). Add getter `getTarpitThreshold()`.
- [x] 2.2 Add tarpit tracking to `ContentGraph.java`: `tarpitHashes: Set<String>`, methods `markTarpit(hash)`, `isTarpit(hash)`, `getTarpitHashes()` returning unmodifiable set. Same pattern as sterile hashes.
- [x] 2.3 Write `TarpitDetectorTest.java` (TDD): (a) no tarpit before threshold, (b) tarpit declared at threshold, (c) counter resets on new state discovery, (d) counter resets on MOP coverage, (e) counter resets on hash change, (f) null hash ignored, (g) different hashes have independent counters — ≥7 tests
- [x] 2.4 Create `recovery/TarpitDetector.java`: tracks per-hash consecutive no-progress iterations. `recordIteration(hash, hasNewState, hasNewMop)` increments or resets counter. `isTarpit(hash)` returns true when counter >= threshold. `getTarpitHashes()` returns all declared tarpits.
- [x] 2.5 Update `ConfigTest.java`: assert new default (tarpit_threshold=15)

## 3. PhaseController Simplification (Group C — independent)

- [x] 3.1 Modify `PhaseController.Phase` enum: remove `PHASE_2`, keep `PHASE_1` and `PHASE_3` only
- [x] 3.2 Modify `PhaseController.onIteration()`: Phase 1 transitions directly to Phase 3 when plateau detected (remove PHASE_2 case)
- [x] 3.3 Remove `ActionSelector.selectPhase2()` method and `findHighestGapCluster()` private method
- [x] 3.4 Modify `ActionSelector.selectAction()`: remove PHASE_2 case from switch (dispatch to Phase 1 fallback or delete case)
- [x] 3.5 Update `PhaseControllerTest.java`: remove Phase 2 tests, add test that Phase 1 transitions directly to Phase 3 on plateau
- [x] 3.6 Update `ActionSelectorTest.java`: remove any Phase 2 test cases, verify Phase 2 enum reference compilation errors are resolved
- [x] 3.7 Grep for any remaining `PHASE_2` references in the codebase and fix them

## 4. Integration Wiring (Group D — depends on A+B+C)

- [x] 4.1 Wire `ActivityBudgetTracker` in `AgentLoop.java`: instantiate with config params, call `registerActivity()` on first visit to each Activity, call `recordIteration()` each iteration, override widget actions with BACK/RESTART when budget exhausted
- [x] 4.2 Wire `TarpitDetector` in `AgentLoop.java`: instantiate with config param, call `recordIteration()` after learning step, on tarpit detection call `graph.markTarpit(hash)` and force RESTART
- [x] 4.3 Pass combined exclusion set (sterile + tarpit hashes) to `BacktrackBfs` and `StuckDetector.recover()`: modify `StuckDetector.recover()` to merge `graph.getSterileHashes()` and `graph.getTarpitHashes()`
- [x] 4.4 Wire `TarpitDetector` in `Main.java`: instantiate and pass to AgentLoop
- [x] 4.5 Wire `ActivityBudgetTracker` in `Main.java`: instantiate and pass to AgentLoop
- [x] 4.6 Update existing tests that construct StuckDetector/BacktrackBfs to handle combined exclusion sets

## 5. Verification (Group E — sequential after D)

- [x] 5.1 Run `mvn test` — all tests pass, 0 failures, 0 errors
- [x] 5.2 Run `mvn install -q` — JAR built
- [x] 5.3 Grep for `PHASE_2` — 0 references in source (only in backup/ or docs allowed)
- [x] 5.4 Smoke test with cryptoapp (300s)
