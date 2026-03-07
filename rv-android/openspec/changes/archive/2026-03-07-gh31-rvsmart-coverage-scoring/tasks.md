<!-- Dependency hints:
     - Group 1 (Config + Foundation) must complete first — all other groups depend on updated Config defaults.
     - Groups 2, 3, 4 are independent and can run in parallel after Group 1.
     - Group 5 (Integration + Observability) must run after Groups 2, 3, 4.
     - Group 6 (Validation + Verification) must run after all other groups.
     - Critical path: 1 -> 2 -> 5 -> 6.
     - This change touches ~22 files — subagent orchestration recommended for Groups 2-4. -->

<!-- Common references:
     Build/test: source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test
     Source root: $RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/
     Test root:   $RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/test/java/br/unb/cic/rvsmart/
     IMPORTANT: All scorer files are under strategy/scorers/ (e.g., strategy/scorers/WtgScorer.java), NOT scorers/.
     Design reference: openspec/changes/gh31-rvsmart-coverage-scoring/design.md (API contracts, decisions D1-D7)

     RVTRACK LOGCAT LIMITATION: RvTrack.java logs via Log.i("RVSMART", ...) to Android logcat.
     rv-platform's LogcatReader only captures RVSEC:V and RVSEC-COV:V tags — RVTRACK data is NOT
     captured in .logcat files or .trace files (stdout). To observe RVTRACK data during validation,
     either: (a) add a separate adb logcat -s RVSMART:I capture in RVSmartTool.py, or (b) write
     observability data to stdout (trace JSON) instead of/in addition to logcat. Task 5.2 should
     address this by writing score breakdown to the trace JSON output, not just RVTRACK logcat. -->

## 1. Configuration and Scoring Defaults

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Skill**: Use `/superpowers:test-driven-development`.

- [x] 1.1a **Config scoring defaults** — In `core/Config.java`: change `DEFAULT_BACK_BASE_SCORE` from `-500` to `-100`; change `DEFAULT_MAX_RETRIES_PER_CYCLE` from `1` to `3`. Add tests in `core/ConfigTest.java` verifying both new defaults.
- [x] 1.1b **Saturation thresholds** — In `graph/ScreenNode.java`: change `DEFAULT_SATURATION_THRESHOLD` from `2` to `4` and `multiValueThreshold` from `4` to `6` (prevents premature backtracking — actions marked "done" after just 2 executions is too aggressive). Add tests in `graph/ScreenNodeTest.java` verifying new thresholds.
- [x] 1.1c **Saturation-based proactive backtrack (INV-RSM-28)** — In `strategy/ActionSelector.java`: replace the score-based proactive backtrack trigger (`bestScore < PROACTIVE_BACKTRACK_THRESHOLD`) with saturation-based: `screenNode.getSaturationRate() >= 0.8` (self-calibrating, robust to scorer weight changes; depends on gh30 task 0.1 fixing `getSaturationRate()`). Add test in `strategy/ActionSelectorTest.java` verifying Tier 3 activates at saturation >= 0.8 and does NOT activate below.
- [x] 1.1d **ConfirmedCoverageScorer decay** — In `strategy/scorers/ConfirmedCoverageScorer.java`: change flat `+150` boost to decaying `150 / (1 + revisits)` — prevents overfitting to already-productive screens while preserving the "this screen has MOP" signal on first visits. Add tests in `strategy/scorers/ConfirmedCoverageScorerTest.java` verifying: score at revisit=0 is 150, at revisit=1 is 75, at revisit=5 is 25.
- [x] 1.2 **Implement softmax-weighted stochastic selection** — In `strategy/ActionSelector.java`, replace uniform random selection with softmax-weighted selection. Compute `p(a) = exp(score(a) / temperature) / sum(exp(scores / temperature))` with temperature=50. Subtract max score before `exp()` for numerical stability. Add tests verifying score ordering affects selection probability and that equal scores degenerate to uniform random.
- [x] 1.3 **Enhance stuck detection** — Three additions to `recovery/StuckDetector.java`: (a) **Time-based trigger**: add `lastNewScreenTime` field, return stuck when elapsed > 30 seconds. (b) **Form action exemption**: SET_TEXT and checkable toggle actions do not increment the stuck counter — they change field content but not the screen hash, so counting them as "no progress" triggers premature BACK during form filling. (c) **Dynamic threshold**: replace fixed iteration count with `max(8, num_elements * 1.5)` — screens with 30 interactive elements deserve more patience than screens with 3 buttons. In `core/AgentLoop.java`, check both iteration-based and time-based stuck detection. Add tests in `recovery/StuckDetectorTest.java` for all three additions.
- [x] 1.4 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test` — verify all existing + new tests pass

## 2. UI Coverage Tracking (INV-RSM-20, INV-RSM-21)

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Skill**: Use `/superpowers:test-driven-development`.

- [x] 2.1 **Create UICoverageTracker.java** — New file at `core/UICoverageTracker.java` (`package br.unb.cic.rvsmart.core;`). Fields: `elementsByScreen: Map<String, Set<String>>` (screen hash → element IDs), `interactionCounts: Map<String, Integer>` (element ID → count), `elementTypes: Map<String, String>` (element ID → widget class). **Hybrid element ID**: use `"res:{resource_id}"` when resourceId is present and non-empty, fall back to `"coords:{centerX},{centerY}"` otherwise. API methods (see design.md for full contract):
    - `void registerScreenElements(String screenHash, List<ScreenItem> items)` — idempotent
    - `void recordInteraction(String screenHash, String elementId)` — increment count
    - `float getCoverageGap(String screenHash)` — returns 0.0–1.0, 1.0 for unknown hash
    - `int getTotalElements()`, `int getTotalInteractions()`
- [x] 2.2 **Integrate UICoverageTracker into AgentLoop** — In `core/AgentLoop.java`, after `UiCapture.capture()`, call `uiCoverageTracker.registerScreenElements(hash, items)`. After action execution, call `uiCoverageTracker.recordInteraction(hash, elementId)` where elementId is derived from the action's target using the hybrid ID strategy.
- [x] 2.3 **Re-enable CoverageDensityScorer** — In `strategy/ActionSelector.java`, add `CoverageDensityScorer` back to the scorer chain. Modify `strategy/scorers/CoverageDensityScorer.java` to read `UICoverageTracker.getCoverageGap(screenHash)` from the scoring context. Score = `coverageGap * weight` (default weight 100).
- [x] 2.4 **Add UICoverageTracker tests** — New file at `core/UICoverageTrackerTest.java` (`package br.unb.cic.rvsmart.core;`). Tests: element registration with hybrid IDs (resourceId-primary, coords-fallback), idempotent re-registration, coverage gap (0.0, 0.5, 1.0, unknown hash), interaction recording, overlapping widget dedup via resourceId, element type tracking. Target: ~8 tests.
- [x] 2.5 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

## 3. Plateau Detection (INV-RSM-22, INV-RSM-23)

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Skill**: Use `/superpowers:test-driven-development`.

- [x] 3.1 **Create PlateauDetector.java** — New file at `strategy/PlateauDetector.java` (`package br.unb.cic.rvsmart.strategy;`). Sliding window of `WINDOW_SIZE = 10` iterations tracking boolean pairs (isNewState, hasNewMopCoverage). Plateau detected when all 10 entries are (false, false). Clears immediately on any true value. API methods (see design.md):
    - `void recordIteration(boolean isNewState, boolean hasNewMopCoverage)`
    - `boolean isPlateauDetected()`
    - `int getConsecutiveNoProgress()` — for RVTRACK logging
- [x] 3.2 **Integrate PlateauDetector into AgentLoop** — In `core/AgentLoop.java`, after each iteration, call `plateauDetector.recordIteration(isNewState, hasNewMopCoverage)`. Pass `plateauDetector.isPlateauDetected()` to `ActionSelector` via the scoring context. When plateau detected, temporarily set stochastic probability to 0.5.
- [x] 3.3 **Add PlateauDetector tests** — New file at `strategy/PlateauDetectorTest.java` (`package br.unb.cic.rvsmart.strategy;`). Tests: plateau detected after 10 no-progress iterations, plateau clears on new state, plateau clears on new MOP, no plateau when progress ongoing, window boundary (exactly 10). Target: ~5 tests.
- [x] 3.4 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

## 4. Text Input, WTG Scoring, and UI Filtering

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Skill**: Use `/superpowers:test-driven-development`.

- [x] 4.1 **Create InputValueGenerator.java** — New file at `strategy/InputValueGenerator.java` (`package br.unb.cic.rvsmart.strategy;`). Category detection via hint/resource_id/inputType pattern matching (Email, Password, Number, Phone, URL, Generic). Value rotation tracked per element hybrid ID. API methods (see design.md):
    - `String generateInput(ScreenItem item)` — returns context-appropriate value
    - `String getCategory(ScreenItem item)` — returns detected category name
    - Categories and values: see delta spec "Context-Aware Text Input Generation" requirement table
- [x] 4.2 **Integrate InputValueGenerator into ActionSelector** — In `strategy/ActionSelector.java` `generateCandidateActions()`, for SET_TEXT actions, use `inputValueGenerator.generateInput(item)` instead of hardcoded `"test"` (currently at line ~309). Pass the generator instance to ActionSelector via constructor.
- [x] 4.3 **Implement WtgScorer with multi-hop BFS (INV-RSM-25)** — In existing `strategy/scorers/WtgScorer.java` (currently a stub returning 0 — see TODO comment on line 28). Read `StaticMap.getTransitions(currentActivity)` (exposed by gh30 task 0.3). Implement BFS of depth 3 on the transitions graph: for each candidate CLICK/LONG_CLICK action, match widget resource_id against known transitions. Score: +200 (1-hop to unvisited activity), +100 (2-hop), +50 (3-hop), 0 (no match or no data). Track visited nodes in BFS to handle cycles. Return 0 for SCROLL, BACK, RESTART, and SET_TEXT actions. Existing test file: `strategy/scorers/WtgScorerTest.java`.
- [x] 4.4 **Add system UI element filtering (INV-RSM-27)** — In `strategy/ActionSelector.java` `generateCandidateActions()`, filter out elements where `item.getPackageName()` equals `"com.android.systemui"`. Keep elements with null/empty package.
- [x] 4.5 **Add LLM coordinate boundary protection** — In `core/AgentLoop.java`, before executing LLM-generated CLICK actions, validate y-coordinate is not in top 5% (status bar) or bottom 6% (nav bar) of screen height. If invalid, substitute with BACK action. Log via RVTRACK as `llm_boundary_reject`.
- [x] 4.6 **Add tests for Group 4** — New file `strategy/InputValueGeneratorTest.java` (`package br.unb.cic.rvsmart.strategy;`, ~8 tests: category detection for each type, rotation, fallback). Update `strategy/scorers/WtgScorerTest.java` (~8 tests: 1-hop unvisited +200, 2-hop +100, 3-hop +50, under-visited, no data, no match, action-type filter for SCROLL/BACK/SET_TEXT returning 0, BFS cycle handling). Update `strategy/ActionSelectorTest.java` (~2 tests: system UI filtering). Update `core/AgentLoopTest.java` (~2 tests: LLM boundary protection).
- [x] 4.7 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

## 5. Integration and Observability

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Skill**: Use `/superpowers:test-driven-development`.

- [x] 5.1 **Wire all new components in AgentLoop constructor** — In `core/AgentLoop.java`, add `UICoverageTracker`, `PlateauDetector`, and `InputValueGenerator` to the constructor. Pass them to `strategy/ActionSelector` where needed. Update the scoring context to include coverage gap and plateau state.
- [x] 5.2 **Add score breakdown to trace JSON output** — In `output/TraceWriter.java`, add a `"scores"` field to the iteration JSON (stdout → `.trace` file) with per-action score decomposition: each scorer's contribution, stochastic flag, and fallback reason. Format: JSON object with named fields (e.g., `{"mop": 300, "decay": -45, "coverage": 80, "wtg": 200, "confirmed": 75, "component": 50, "total": 660, "stochastic": false}`). Builds on gh30 Group C2 (task 3b.1) which adds basic observability fields (`scoreTier`, `saturationRate`, cycle timing, OOA) to the trace JSON. This task adds the full per-scorer breakdown. Also continue logging via RVTRACK for real-time debugging. Add tests in `output/TraceWriterTest.java`.
- [x] 5.3 **Add integration tests** — Test full AgentLoop iteration with UICoverageTracker + PlateauDetector + InputValueGenerator wired together. Verify: (a) coverage gap decreases after interactions, (b) plateau boosts stochastic probability, (c) InputValueGenerator values appear in SET_TEXT actions. Target: ~3 integration tests.
- [x] 5.4 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test` — all tests (existing + ~56 new) must pass

## 6. Validation and Verification

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 6.1 Run full `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test` — all tests must pass
- [x] 6.2 **E2E validation on baseline APKs** — Run rvsmart on a subset of baseline APKs (e.g., 5 APKs) via `source /etc/profile && cd $RVSEC_HOME/rv-android && uv run rv-experiment run --tools rvsmart:mvp --apks-dir results/cli_experiment_20260305_180341_fe33918e/instrumented_apks/ --skip-monitors --skip-instrument --skip-static --timeout 300`. Compare method/MOP coverage against gh30 post-fix baseline and against the original baseline (rvsmart: 17.76% method, 25.54% MOP; ape: 20.36% method, 31.57% MOP). Target: surpass APE averages.
- [x] 6.3 **Verify trace JSON output** — Check `.trace` file for: score breakdown per action in `"scores"` field (each scorer's contribution — written to stdout JSON per task 5.2), CoverageDensityScorer scores > 0, WtgScorer multi-hop scores > 0 (when static data available), plateau detection events, InputValueGenerator-generated values in SET_TEXT actions, ConfirmedCoverageScorer decay visible across revisits. Note: RVTRACK logcat data (tag `RVSMART`) is NOT captured by rv-platform — verify via trace JSON fields instead.
- [x] 6.4 Review all changes against P1–P4 principles
- [x] 6.5 Sync delta spec to main tools spec via `/opsx:sync` — done (9 invariants INV-RSM-20..28 + 8 requirements merged into openspec/specs/tools/spec.md)
