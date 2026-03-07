<!-- Dependency hints:
     - Group 1 (StaticMap parser) must complete first — MopScorer and WtgScorer depend on it.
     - Groups 2, 3 are independent and can run in parallel after Group 1.
     - Group 4 (Cleanup + Removal) can run after Groups 1-3.
     - Group 5 (Python + Final Verification) must run after all other groups.
     - Critical path: 1 -> 4 -> 5.
     - This change touches ~14 files (13 Java + 1 Python + tests) — subagent orchestration optional for Groups 2-3. -->

<!-- Common references:
     Build/test: source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test
     Source root: $RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/
     Test root:   $RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/test/java/br/unb/cic/rvsmart/
     Python plugin: modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/tool.py
     Python tests:  modules/rvsmart-tool/tests/test_rvsmart_tool.py
     Design reference: openspec/changes/gh32-rvsmart-scoring-recovery/design.md (decisions D1-D5)
     Delta spec reference: openspec/changes/gh32-rvsmart-scoring-recovery/specs/tools/spec.md (INV-RSM-30 through INV-RSM-42)
     Diagnostic reference: docs/20260307_rvsmart_refactoring.md (Bugs A-J, Anomalies 1-8, Sections 12-19)
     Real JSON example: results/gh31_mini/com.crazyhitty.chdev.ks.munch_14.apk/*.json -->

## 1. StaticMap Parser Rewrite (INV-RSM-30, INV-RSM-31 — Bug A)

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Skill**: Use `/superpowers:test-driven-development`.
> **Diagnostic ref**: Section 13, Bug A — "Triplice Falha" (Sections 19.6)

This is the most critical group. MopScorer and WtgScorer have returned 0 in 100% of iterations since gh29 because the parser cannot read the JSON format. Three problems must be fixed together — partial fix (format only) still fails because activity names don't match.

- [ ] 1.1 **Rewrite `parseReachability()` to read JsonArray** — In `staticdata/StaticMap.java`: change `json.getAsJsonObject("reachability")` to `json.getAsJsonArray("reachability")`. Iterate the JsonArray: each element is a JsonObject with `"className"` (String, fully qualified) and `"methods"` (JsonArray). Each method has `"signature"`, `"reachable"`, `"reachesMop"`, `"directlyReachesMop"`. Populate the `mopMethods` map keyed by normalized activity name. Use a real JSON from `results/gh31_mini/` as reference for the exact structure.

- [ ] 1.2 **Rewrite `parseTransitions()` to read JsonArray** — In `staticdata/StaticMap.java`: change `json.getAsJsonObject("transitions")` to `json.getAsJsonArray("transitions")`. Each element has `"sourceId"` (int), `"targetId"` (int), `"events"` (JsonArray of {type, widgetClass}). Add a `parseWindows()` step first: read the `"windows"` JsonArray to build `windowIdToActivity: Map<Integer, String>`. Then use this map to cross-reference sourceId/targetId into activity names. Build `activityTransitions: Map<String, List<TransitionTarget>>`.

- [ ] 1.3 **Implement activity name normalization** — In `staticdata/StaticMap.java`: the trace uses names like `"uiactivitiesSplashActivity"` (dots stripped from relative path). The JSON uses `"com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity"` (fully qualified). Create a normalization method that: (a) takes the trace-format name and code package, (b) re-inserts dots at camelCase boundaries where a lowercase letter precedes an uppercase letter (split `"uiactivities"` → `"ui.activities"`), (c) prepends the code package. Verify against at least 3 real examples from traces and JSONs.

- [ ] 1.4 **Add StaticMap tests** — New or updated file at `staticdata/StaticMapTest.java`. Tests: (a) parse reachability from JsonArray with real JSON structure, verify MOP methods populated; (b) parse transitions from JsonArray, verify adjacency map built correctly; (c) activity name normalization for `"uiactivitiesSplashActivity"` → `"com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity"`; (d) parse empty/missing sections gracefully (isLoaded=true, empty maps); (e) verify `getMopMethodsForActivity()` returns non-empty for activity with `directlyReachesMop=true`; (f) verify `getTransitions()` returns transitions. Target: ~6 tests.

- [ ] 1.5 **Verify MopScorer and WtgScorer integration** — Update `strategy/scorers/MopScorerTest.java` and `strategy/scorers/WtgScorerTest.java`: add tests that create a StaticMap loaded with the new JsonArray format and verify the scorers return non-zero values for appropriate actions. This confirms the end-to-end fix from JSON parsing through to score output.

- [ ] 1.6 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test` — all existing + new tests pass

## 2. Recovery Mechanism Fixes (INV-RSM-33, INV-RSM-34, INV-RSM-35, INV-RSM-36 — Bugs C, D, E, F)

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Skill**: Use `/superpowers:test-driven-development`.
> **Diagnostic ref**: Section 13, Bugs C-F

These 4 fixes are independent of each other and independent of Group 1. Each is a small, focused change in `AgentLoop.java`.

- [ ] 2.1 **OOA multi-stage recovery (Bug C, INV-RSM-33)** — In `core/AgentLoop.java`, modify `handleOoaRestart()`: when `consecutiveOoaAfterRestart >= MAX_CONSECUTIVE_OOA_AFTER_RESTART`, execute: (1) `devController.executeShellCommand("input keyevent BACK")`, (2) `sleep(500)`, (3) re-check foreground package via `getRootInActiveWindow().getPackageName()`, (4) if still OOA, `devController.executeShellCommand("am force-stop " + foregroundPkg)`, (5) then proceed with existing `forceStop(packageName) + startApp(packageName)`. The `foregroundPkg` is already available from the OOA detection in `runIteration()` — pass it to `handleOoaRestart()` as parameter.

- [ ] 2.2 **Empty screen wait strategy (Bug D, INV-RSM-34)** — In `core/AgentLoop.java`, in the action selection flow: after `generateCandidateActions()` returns 0 candidates, AND `successorTracker.getParents(currentHash)` is empty (no backtrack path), add `Thread.sleep(2000)` and recapture via `uiCapture.capture(getRootInActiveWindow())`. If recapture has candidates, proceed with normal selection. If still empty, fall through to Tier 4 (RESTART). This handles splash screens that auto-transition after 2-3s.

- [ ] 2.3 **SET_TEXT implicit effect (Bug E, INV-RSM-35)** — In `core/AgentLoop.java`, after action execution and hash comparison: if `action.getType() == Action.Type.SET_TEXT`, set `hadEffect = true` unconditionally. This is a 2-line change: `if (action.getType() == Action.Type.SET_TEXT) hadEffect = true;` after the existing `boolean hadEffect = !hash.equals(hashAfter) || !activity.equals(activityAfter);`.

- [ ] 2.4 **Exception trace line + early returns (Bug F + N13, INV-RSM-36)** — In `core/AgentLoop.java`: (a) in the `run()` catch block, call `traceWriter.writeLine(...)` with `action_type="ERROR"` and the exception message instead of silent `Log.w`; (b) add a trace line (`action_type="SKIP"`, with a `reason` field) to all 6 early-return paths in `runIteration()`: crash-at-start (~lines 215-219), root null (~224-227), system dialog dismiss (~230-235), post-action crash (~399-406), post-action native crash (~414-421), OOA tolerance-not-exceeded (~261-277). Simplest implementation for (b): wrap the body of `runIteration()` in try/finally and write a catch-all "SKIP" trace in the finally if no trace was written that iteration — single location, no risk of missing a path.

- [ ] 2.5 **Add recovery tests** — Tests for each fix: (a) OOA multi-stage: mock AppController, verify BACK sent before forceStop(foreground), verify sequence completes; (b) Empty screen wait: mock UiCapture returning 0 elements then >0, verify sleep called; (c) SET_TEXT effect: verify hadEffect=true after SET_TEXT regardless of hash change; (d) Exception trace: mock traceWriter, trigger exception in runIteration, verify ERROR line written; (e) Early return — null root: simulate null from getRootInActiveWindow(), verify SKIP trace written; (f) Early return — OOA in-progress: simulate consecutive OOA below threshold, verify SKIP trace written. Target: ~6 tests.

- [ ] 2.6 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

## 3. Resource Management and Internal Consistency (INV-RSM-37 through INV-RSM-42 — Bugs G, H, I, J + Anomalies)

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Skill**: Use `/superpowers:test-driven-development`.
> **Diagnostic ref**: Section 13 (Bugs G-J), Section 14 (Anomalies 2, 6)

These fixes are independent of Groups 1 and 2. They address resource leaks, off-by-one errors, and inconsistencies.

- [ ] 3.1 **AccessibilityNodeInfo recycle (Bug G, INV-RSM-37)** — In `core/AgentLoop.java`, wrap all 4 `getRootInActiveWindow()` call sites in try/finally blocks that call `root.recycle()` in the finally. The 4 sites are: (a) initial capture at iteration start, (b) post-action capture, (c) adaptive wait recapture, (d) OOA detection capture. Handle null root (no recycle needed). Note: for the initial and post-action captures, the `root` reference is used across the method — restructure as needed to keep the recycle in a finally block without breaking the data flow.

- [ ] 3.2 **PathBuffer off-by-one fix (Bug I, INV-RSM-38)** — In `strategy/PathBuffer.java`, fix `invalidateIfDiverged()`: the method must compare `currentHash` against `expectedHashes[currentIndex]` (the expected hash at the current position), not `expectedHashes[currentIndex + 1]`. This ensures multi-hop BFS paths are validated correctly — currently, all paths of 2+ hops fail on the first hop because the comparison target is off by one.

- [ ] 3.3 **UICoverageTracker fixes (Bug H + N16, INV-RSM-39 + INV-RSM-41)** — Two bugs in `core/UICoverageTracker.java`: (a) **ID mismatch**: `registerScreenElements()` uses `"res:{resourceId}"` for elements with resource IDs, but `AgentLoop.java` calls `recordInteraction()` with always-coords `"coords:x,y"` — IDs never match. Unify ID construction into a shared method (`elementId(ScreenItem)` or similar) used in both places; (b) **Screen scoping**: `recordInteraction(String screenHash, String elementId)` receives `screenHash` but never uses it — `interactionCounts` is a flat map keyed only by elementId. Change to a composite key `screenHash + "|" + elementId` so interactions in screen A don't count toward elements in screen B with the same resource ID. Both fixes are needed for `CoverageDensityScorer` to report accurate coverage gaps.

- [ ] 3.4 **StuckDetector call fix (Anomaly 2)** — In `core/AgentLoop.java`, replace the direct `stuckDetector.getConsecutiveUnchanged()` check with a call to `stuckDetector.updateWithActionType(currentHash, action.getType())`. The `updateWithActionType()` method already exists but is never called — it exempts SET_TEXT from incrementing the stuck counter, preventing premature RESTART during form filling.

- [ ] 3.5 **RESTART resets StuckDetector (Anomaly 6)** — In `core/AgentLoop.java`, in the `executeAction()` method's `RESTART` case, add `stuckDetector.reset()` to match the behavior in `recoverApp()`. Currently, `executeAction(RESTART)` only resets `cachedScreenState` but not the stuck detector, causing the stuck counter to persist across app restarts.

- [ ] 3.6 **ScreenNode.totalActions update (Bug J, INV-RSM-40)** — In `graph/ScreenNode.java`, change the `setTotalActions()` or equivalent method to update on every visit using `this.totalActions = Math.max(this.totalActions, newCount)`. If the first visit captures 0 elements (transient state), subsequent visits with more elements must update the count. This prevents `getSaturationRate()` from permanently returning 1.0.

- [ ] 3.7 **HeapMonitor adaptive throttle (INV-RSM-42)** — In `core/AgentLoop.java`, the return value of `heapMonitor.check()` (a throttle duration in ms) is never read — the loop always sleeps `config.getThrottleMs()`. Fix: assign the return value of `check()` and use it as the actual sleep duration. When heap pressure is normal, `check()` returns `config.getThrottleMs()` (no change in behavior); under pressure, it returns a larger value that now actually delays the next iteration.

- [ ] 3.8 **Add consistency tests** — Tests: (a) PathBuffer divergence at correct position with 2+ hop path; (b) UICoverageTracker ID scheme: register with resource ID, interact with same scheme, verify gap decreases; (c) UICoverageTracker screen scoping: same element ID in two screens does not cross-contaminate coverage; (d) ScreenNode.totalActions updated from 0 to N on revisit; (e) StuckDetector: SET_TEXT does not increment counter; (f) HeapMonitor: dynamic throttle value used for sleep when pressure is high. Target: ~6 tests.

- [ ] 3.9 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

## 4. Cleanup and Removal (INV-RSM-32 — P1/P3)

> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Diagnostic ref**: Section 16 (Proposed Scoring Chain), Section 14 (Anomalies 1, 5)

This group removes dead/harmful code. Must run AFTER Groups 1-3 to avoid breaking intermediate builds.

- [ ] 4.1 **Backup and delete RewardPropagator** — Copy `strategy/RewardPropagator.java` to `backup/RewardPropagator.java.bak` (in rv-android dir). Delete `strategy/RewardPropagator.java` from the rvsmart source tree. Delete the test file `strategy/RewardPropagatorTest.java` (if exists) or any test referencing `RewardPropagator`.

- [ ] 4.2 **Backup and delete RewardScorer** — Copy `strategy/scorers/RewardScorer.java` to `backup/RewardScorer.java.bak`. Delete `strategy/scorers/RewardScorer.java`. Delete `strategy/scorers/RewardScorerTest.java` (if exists).

- [ ] 4.3 **Remove RewardPropagator wiring from AgentLoop** — In `core/AgentLoop.java`, remove: (a) the `RewardPropagator` field declaration, (b) the `rewardPropagator.propagate()` call in the iteration loop, (c) the `rewardPropagator.propagateConfirmedCoverage()` call, (d) any `rewardPropagator.addReward()` calls. Remove the `RewardPropagator` import.

- [ ] 4.4 **Remove RewardScorer from ActionSelector** — In `strategy/ActionSelector.java`, remove `new RewardScorer(...)` from the scorers list in the constructor. Remove the corresponding import. Verify the scorer list has exactly 7 entries (INV-RSM-32). CoverageDensityScorer stays — it was re-enabled by gh31 and will work correctly once Bug H (UICoverageTracker ID fix, task 3.3) is applied.

- [ ] 4.5 **Update Main.java** — In `Main.java`, remove: (a) `RewardPropagator` instantiation, (b) any passing of `RewardPropagator` to `AgentLoop` constructor. Adjust the `AgentLoop` or `ActionSelector` constructor calls if their signature changed due to removing the propagator parameter.

- [ ] 4.6 **Clean Config.java** — In `core/Config.java`, remove: (a) `DEFAULT_MAX_CUMULATIVE_FACTOR` and `getMaxCumulativeFactor()` (never used), (b) any other reward-specific constants (`GAMMA`, `REWARD_WINDOW_SIZE`, etc.) that are only used by the deleted `RewardPropagator`. Keep constants used by other components.

- [ ] 4.7 **Clean ScreenNode.java** — In `graph/ScreenNode.java`, remove the `cumulativeRewards` field and any getter/setter for it — this field was only read by `RewardScorer`.

- [ ] 4.8 **Clean WtgScorer parameter** — In `strategy/scorers/WtgScorer.java`, remove the vestigial `wtgScore` constructor parameter and field (Anomaly 1). The scorer uses internal constants (`BOOST_1_HOP=200`, etc.), not the parameter. Update the constructor call in `ActionSelector.java` (remove the `0` argument).

- [ ] 4.9 **Verify no dangling references** — Grep the entire rvsmart source tree for: `RewardPropagator`, `RewardScorer`, `cumulativeRewards`, `maxCumulativeFactor`, `accumulatedRewards`. All must return 0 results. Note: `CoverageDensityScorer` is expected to exist (kept, fixed via Bug H).

- [ ] 4.10 Run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test` — all tests pass, no compilation errors

## 5. Python Plugin + Final Verification

> **Build/test (Java)**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Build/test (Python)**: `cd $RVSEC_HOME/rvsec/rvsec-android && uv run pytest modules/rvsmart-tool/tests/ -v`

- [ ] 5.1 **Empty trace detection in rvsmart-tool** — In `modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/tool.py`, after execution completes: check if the trace file exists and has 0 bytes. If empty, log a warning "rvsmart produced empty trace file — possible silent hang or startup crash". Do not mark as failure (the agent ran for the full timeout).

- [ ] 5.2 **Python tests** — In `modules/rvsmart-tool/tests/test_rvsmart_tool.py`, add test: mock a 0-byte trace file, verify warning is logged.

- [ ] 5.3 Run `cd $RVSEC_HOME/rvsec/rvsec-android && uv run pytest modules/rvsmart-tool/tests/ -v` — Python tests pass

- [ ] 5.4 Run full Java test suite: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test` — all tests pass (existing + ~34 new)

- [ ] 5.5 **E2E validation** — Run rvsmart on the same 5 APKs from gh31_mini: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android && uv run rv-experiment run --tools rvsmart:mvp --apks-dir results/gh31_mini/instrumented_apks/ --skip-monitors --skip-instrument --skip-static --timeout 300 --name gh32_validation`. Compare against gh31_mini baseline:
    - MOP scorer values > 0 in APKs with static analysis data
    - WTG scorer values > 0 in APKs with transition data
    - RESTART percentage < 10% (was 24.3%)
    - No silent hangs (dnshero should produce trace output)
    - OOA recovery in hourly should resolve within 3-5 iterations (was 155)

- [ ] 5.6 Review all changes against P1-P4 principles

- [ ] 5.7 Sync delta spec to main tools spec via `/opsx:sync`

- [ ] 5.8 Verify implementation matches change artifacts via `/opsx:verify`

- [ ] 5.9 Archive the change via `/opsx:archive`. Final commit message uses `closes #32`.
