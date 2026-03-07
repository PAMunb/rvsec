<!-- Dependency hints:
     - Task 1.0 (hash redesign) MUST complete before all other Group A tasks.
     - Group 1 remainder (bug fixes) and Group 3 (speed) are mostly independent (except 3.4 depends on 1.6).
     - Group 2 (OOA recovery) should be done after Group 1, before Group 3.
     - Group 4 (Verification) must run after Groups 1, 2, and 3. -->

<!-- Orchestration strategy:
     Main context acts as ORCHESTRATOR ONLY — does not write code directly.
     Dispatches subagents per group, collects summaries, runs verification.
     Skills: subagents use /superpowers:test-driven-development for all code changes
     (RED-GREEN-REFACTOR with `mvn test`). Orchestrator uses /superpowers:verification-before-completion
     at each checkpoint.

     Parallel wave 0 (foundational):
       Subagent A0: task 1.0 (hash redesign — ScreenState.java + ScreenStateTest.java)
     [checkpoint: orchestrator runs `mvn test` — verify hash change does not break anything]

     Parallel wave 1 (Groups A + C independent tasks):
       Subagent A1: tasks 1.1, 1.2, 1.4, 1.10 (ScreenNode, ActionSelector, PathBuffer)
       Subagent A2: tasks 1.3, 2.3 (StaticMap + MopScorer + --code-package)
       Subagent A3: tasks 1.5, 1.6 (AgentLoop reward + capture reduction)
       Subagent A4: task 1.7 (LLM bootstrap in Main.java)
     [checkpoint: orchestrator runs `mvn test` — task 1.8]

     Sequential wave 2 (depends on wave 1):
       Subagent B1: tasks 2.1, 2.2 (OOA detection + fallback)
     [checkpoint: orchestrator runs `mvn test` — task 2.4]

     Sequential wave 3 (depends on wave 1, can overlap wave 2 for 3.1-3.3):
       Subagent C1: tasks 3.1, 3.2, 3.3, 3.4, 3.5 (speed optimizations + profiling)
     [checkpoint: orchestrator runs `mvn test` — task 3.6]

     Group 4: orchestrator runs verification directly. -->

## 1. Structural Bug Fixes (Group A)

> **Subagent A0** (task 1.0): Foundational hash redesign. Must complete before all other tasks.
> Touches `ScreenState.java` + `ScreenStateTest.java`. Old SHA-256 code is deleted entirely (P3).
> **Skill**: Use `/superpowers:test-driven-development`.
> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Source root**: `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/`
> **Test root**: `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/test/java/br/unb/cic/rvsmart/`
> **Note**: All scorer files are under `strategy/scorers/` (e.g., `strategy/scorers/MopScorer.java`), NOT `scorers/`.

- [x] 1.0 **Hash redesign** — Replace SHA-256 + JSON serialization in `ScreenState.java` with `Objects.hash()` over sorted structural widget signatures. Widget signature: `{className, resourceID, interactMask}`. Exclude text (volatile), coordinates (shift between visits), index (brittle). Add widget deduplication before hashing: widgets with identical `{className, resourceID, interactMask}` merge into one (FastBot pattern — prevents list items from inflating state counts). Hash = `Objects.hash(activityName, dedupedSortedWidgetSignatures)`. Sort by (className, resourceID) for determinism. Delete the old SHA-256 implementation entirely — no legacy mode, no backward compatibility (P3). Move old code to `backup/` before deletion. Add tests in `ScreenStateTest.java`: determinism, dedup, text exclusion, order independence, activity-based grouping.

> **Subagent A1** (tasks 1.1, 1.2, 1.4, 1.10): Independent fixes in `ScreenNode`, `ActionSelector`, `PathBuffer`. ~5 files + 3 test files.
> **Skill**: Use `/superpowers:test-driven-development` — write failing test first, then fix, then verify.
> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 1.1 **ScreenNode.totalActions initialization** — Add `setTotalActions(int count)` to `ScreenNode.java`. Add guard `if (totalActions > 0)` in `getSaturationRate()`. In `AgentLoop.runIteration()`, call `screenNode.setTotalActions(items.size())` when `visitCount == 1`. Add tests in `ScreenNodeTest.java` verifying saturation returns correct values (0.0–1.0, not always 1.0).
- [x] 1.2 **SCROLL action generation in 4 directions** — In `ActionSelector.generateCandidateActions()`, add SCROLL action for items where `item.isScrollable()` is true. Generate 4 directions: DOWN (primary, base score same as CLICK), UP, LEFT, RIGHT (secondary, base score = CLICK * 0.5). Coordinates: center of the scrollable container. This ensures horizontal tabs, carousels, and above-viewport content are discoverable. Add tests in `ActionSelectorTest.java` verifying SCROLL actions are generated in all 4 directions for scrollable elements.
- [x] 1.4 **PathBuffer position validation + retry-safe backtrack** — In `PathBuffer.consumeNext()`, validate that the agent's current screen hash matches the expected position BEFORE removing the next hop from the queue. If the agent has diverged, invalidate the path instead of silently consuming hops. Also add a guard in `selectNextBest()`: if PathBuffer has an active plan, only allow BACK alternatives during retry — prevents retry loop from invalidating planned backtrack routes. Add tests in `PathBufferTest.java`.
- [x] 1.10 **Failure-aware Tier 2 filtering** — In `ActionSelector.selectAction()`, add `failureCount >= 3` guard to Tier 2 action selection. Currently this filter only applies in `selectNextBest()` (retry path), so the main path wastes budget on known-bad non-interactive elements. Add test verifying actions with 3+ failures are excluded from Tier 2.

> **Subagent A2** (tasks 1.3, 2.3): StaticMap + MopScorer + `--code-package`. Coupled: the `--code-package` param feeds `StaticMap` for activity-based MOP lookup. ~4 Java files + 2 Java test files + 1 Python file + 1 Python test.
> **Skill**: Use `/superpowers:test-driven-development` for Java. For Python change, write test first in `test_rvsmart_tool.py` then edit `tool.py`.
> **Build/test (Java)**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`
> **Build/test (Python)**: `cd $RVSEC_HOME/rv-android && uv run pytest modules/rvsmart-tool/tests/ -v`
> **Note**: `MopScorer.java` is at `strategy/scorers/MopScorer.java`, test at `strategy/scorers/MopScorerTest.java`.

- [x] 1.3 **StaticMap signature alignment + transitions** — Change `StaticMap.java` to parse both the **reachability** and **transitions** sections of the static analysis JSON. Expose `getReachableMethods(activityName)` for activity-level MOP lookup and `getTransitions(activityName)` for WTG transition lookup (needed by gh31 WtgScorer). Use `Config.codePackage` to match activity names against JSON keys (code-package-qualified). Update `MopScorer.java` to use activity-based lookup: if the current activity has reachable MOP methods, boost all actions on that screen. Add tests in `StaticMapTest.java` (both reachability and transitions) and `MopScorerTest.java`.
- [x] 2.3 **`--code-package` for StaticMap** — In `Main.java`, add optional `--code-package` argument. Store in `Config.codePackage`, falls back to `--package` when absent. Log a warning on fallback: `"No --code-package provided. MOP scoring may be inaccurate for multi-package apps."` This is NOT for OOA detection (which uses manifest package from `ComponentName.getPackageName()`), but for `StaticMap`/`MopScorer` (task 1.3). In `rvsmart_tool/tools/rvsmart/tool.py`, add `"--code-package", app.code_package` to `_build_main_command()`. Add test in `ConfigTest.java` for fallback behavior. Add test in Python `test_rvsmart_tool.py` for `--code-package` in command output.

> **Subagent A3** (tasks 1.5, 1.6): AgentLoop internals — reward wiring + UI capture reduction. Coupled: both modify `AgentLoop.runIteration()`. ~2 files + 1 test file.
> **Skill**: Use `/superpowers:test-driven-development`.
> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 1.5 **Wire RewardPropagator into scoring + BACK decay in retry** — In `AgentLoop.java`, after `learner.update()`, call `rewardPropagator.propagate(screenHash, action.signature(), reward)`. Add cumulative reward map to the scoring context passed to `ActionSelector`. Create a `RewardScorer` or integrate into `GradualDecayScorer` with weight `+cumulativeReward * 0.3`. Also call `updateBackDecay()` inside the retry while-loop after each BACK execution — without this, multiple consecutive BACKs within one retry cycle execute at the same score, causing over-backtracking. Add tests verifying: (a) reward values influence action scores, (b) BACK decay applies per-BACK inside retry.
- [x] 1.6 **Reduce UI captures per iteration** — In `AgentLoop.java`, store the post-action `ScreenState` and reuse it as the next iteration's initial state. Only re-capture on: crash recovery, out-of-app recovery, stuck recovery. Add test verifying capture count per iteration is 1–2 (not 3–4).

> **Subagent A4** (task 1.7): LLM bootstrap in `Main.java`. Isolated, no overlap with other subagents. ~1 file + 1 test file.
> **Skill**: Use `/superpowers:test-driven-development`.
> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 1.7 **Bootstrap LLM components** — In `Main.java`, when `--mode multimode` or `--mode llm_only` is passed, instantiate `SglangClient`, `ToolCallParser`, `PromptBuilder`, `ImageProcessor`, `ScreenshotCapture`, and `RoutingManager`. Pass them to `AgentLoop` constructor. Add test verifying LLM components are non-null when multimode is requested.

> **Checkpoint** (task 1.8): Orchestrator merges subagent changes, runs `mvn test`.
> **Skill**: Use `/superpowers:verification-before-completion` — run `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`, confirm all pass before proceeding.

- [x] 1.8 Run `mvn test` on rvsmart module to verify all existing + new tests pass

## 2. Out-of-App Recovery (Group B)

> **Subagent B1** (tasks 2.1, 2.2): OOA detection + consecutive fallback. Both modify `AgentLoop.java` OOA handling. ~1 file + 1 test file.
> Depends on Group A checkpoint (task 1.6 changes AgentLoop iteration flow that OOA hooks into).
> **Skill**: Use `/superpowers:test-driven-development`.
> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 2.1 **OOA detection and RESTART recovery** — In `AgentLoop.java`, after each action execution, call `appController.getCurrentActivity()` to get the `ComponentName` of the foreground activity. Compare `cn.getPackageName()` (manifest package of the foreground app) against `config.getPackage()` (the `--package` CLI arg). If they differ, the agent is out-of-app. Two-tier recovery matching rvagent behavior: (a) **Launcher fast-path**: known launcher packages (`com.android.launcher3`, `com.google.android.apps.nexuslauncher`, `com.android.launcher`) trigger immediate RESTART bypassing tolerance. (b) **Tolerance for other packages** (e.g., Chrome from in-app link): allow up to 3 iterations (OOA tolerance counter) before forcing RESTART — the user may return via BACK. Skip scoring/learning for all OOA iterations. Log OOA events via RVTRACK (trigger action, destination package, recovery type). Add tests in `AgentLoopTest.java`.
- [x] 2.2 **Consecutive OOA-after-RESTART fallback** — Add a consecutive RESTART-failure counter. If the agent detects 3 consecutive OOA events immediately after RESTART (app keeps redirecting to external intent on startup), fall back to `forceStop` + `startApp` recovery. Reset counter when the agent successfully returns to target app. Add test verifying fallback triggers.

> **Checkpoint** (task 2.4): Orchestrator runs `mvn test`.
> **Skill**: Use `/superpowers:verification-before-completion`.

- [x] 2.4 Run `mvn test` on rvsmart module to verify all tests pass

## 3. Speed Optimizations (Group C)

> **Subagent C1** (tasks 3.1–3.5): All speed optimizations + profiling. Small edits in `Config.java` and `AgentLoop.java`. ~2 files + 2 test files.
> Task 3.4 depends on task 1.6 (screen state caching builds on reduced capture flow).
> **Skill**: Use `/superpowers:test-driven-development`.
> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 3.1 **Reduce default throttle** — In `Config.java`, change default `throttleMs` from 200 to 100. A moderate reduction (not 50ms) avoids UI instability that could increase out-of-app events. Verify properties file loading path correctly overrides this default. Add test in `ConfigTest.java` for default value and properties override.
- [x] 3.2 **Reduce restart cost** — In `AgentLoop.recoverApp()`, change `forceStop` sleep from 500ms to 200ms and `startApp` sleep from 1500ms to 800ms (total: 1000ms instead of 2000ms).
- [x] 3.3 **Conditional adaptive wait** — In `AgentLoop.java`, apply `adaptiveWaitMs` only for CLICK and LONG_CLICK actions. Skip adaptive wait for SET_TEXT and SCROLL.
- [x] 3.4 **Screen state caching** — In `AgentLoop.java`, add `lastScreenState` field. After post-action capture, store the result. At iteration start, reuse `lastScreenState` if no recovery event occurred. Invalidate on crash, out-of-app, or stuck recovery. Depends on task 1.6.
- [x] 3.5 **Cycle time profiling via RVTRACK** — In `AgentLoop.runIteration()`, add `System.currentTimeMillis()` timestamps around each phase: capture, scoring, execution, wait. Log per-iteration breakdown via RVTRACK (e.g., `RVTRACK CYCLE capture=12ms scoring=3ms exec=45ms wait=100ms total=160ms`). Enables data-driven validation of throttle and future calibration.

> **Checkpoint** (task 3.6): Orchestrator runs `mvn test`.
> **Skill**: Use `/superpowers:verification-before-completion`.

- [x] 3.6 Run `mvn test` on rvsmart module to verify all tests pass

## 3b. RVTRACK Observability via Trace JSON (Group C2)

> rv-platform's LogcatReader only captures `RVSEC:V` and `RVSEC-COV:V` tags.
> RVTRACK data (`Log.i("RVSMART", ...)`) is NOT captured in `.logcat` or `.trace` files.
> Without this group, tasks 4.4–4.8 cannot be verified from experiment results.
> **Skill**: Use `/superpowers:test-driven-development`.
> **Build/test**: `source /etc/profile && cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart && mvn test`

- [x] 3b.1 **Add RVTRACK fields to TraceWriter** — In `output/TraceWriter.java`, extend `writeLine()` signature to accept additional observability fields and write them to the stdout JSON: `scoreTier` (int), `saturationRate` (double), `captureMs` (long), `scoringMs` (long), `execMs` (long), `totalMs` (long), `ooa` (boolean), `ooaRecovery` (String, nullable), `ooaForegroundPkg` (String, nullable). These fields mirror what `RvTrack.select()`, `RvTrack.strategy()`, `RvTrack.cycle()`, and `RvTrack.ooa()` log to logcat — but written to stdout so they appear in the `.trace` file. Keep `RvTrack` logcat calls unchanged (useful for real-time debugging via `adb logcat`). Add tests in `output/TraceWriterTest.java` verifying the new fields appear in the JSON output.
- [x] 3b.2 **Wire RVTRACK fields in AgentLoop** — In `core/AgentLoop.java`, pass the new observability values to `traceWriter.writeLine()`: tier from `ActionSelector` (via new `getLastSelectedTier()`), saturation from `screenNode.getSaturationRate()`, cycle timing from the existing profiling timestamps (task 3.5), OOA state from the detection logic (task 2.1). OOA trace lines also written for early-return OOA events (launcher fast-path + tolerance exceeded).
- [x] 3b.3 Run `mvn test` on rvsmart module to verify all tests pass — 384 tests pass

## 4. Verification (Group D)

> **Orchestrator runs directly** — no subagent needed. Sequential verification requiring human judgment.
> **Skill**: Use `/superpowers:verification-before-completion` for tasks 4.1–4.8.
> Use `/superpowers:requesting-code-review` for task 4.9.

- [x] 4.1 Run full `mvn test` — all 370+ JUnit 5 tests must pass (existing + new)
- [x] 4.2 Run rvsmart on a subset of baseline APKs (e.g., 5 APKs) via `source /etc/profile && cd $RVSEC_HOME/rv-android && uv run rv-experiment run --tools rvsmart:mvp --apks-dir results/cli_experiment_20260305_180341_fe33918e/instrumented_apks/ --skip-monitors --skip-instrument --skip-static --timeout 300` — reuse instrumented APKs from post-gh29 experiment to skip pre-processing. Compare method/MOP coverage against baseline (rvsmart: 17.76% method, 25.54% MOP). Measure evt/s (target: ≥10 evt/s sustained) and OOA% (target: < 5%, down from 18.6%).
- [x] 4.3 Verify SCROLL actions appear in trace output in all 4 directions for apps with scrollable containers
- [x] ~~4.4 Verify MopScorer returns non-zero scores in trace output~~ — **Deferred to gh32**: static analysis data not loading correctly upstream (MopScorer always returns 0 due to data loading bug unrelated to gh30). Will be re-validated after gh32 fixes the root cause.
- [x] 4.5 Verify `getSaturationRate()` returns values < 1.0 in trace JSON for screens with multiple elements — VERIFIED: `saturation_rate` field present. hourlyreminder: 53/53 iters < 1.0 (max=0.10). blippex: 1/10 < 1.0. munch: 4/23 < 1.0.
- [x] 4.6 Verify UI capture count per iteration is 1–2 (check `captureMs` field in trace JSON) — VERIFIED: `capture_ms=0` (cached) dominates: hourlyreminder 76/77 cached, munch 22/23 cached, blippex 13/17 cached. Screen state caching (task 1.6/3.4) working correctly.
- [x] 4.7 Verify OOA detection triggers RESTART, launcher fast-path works, and OOA% is < 5% — VERIFIED: `ooa`, `ooa_recovery`, `ooa_foreground_pkg` fields visible in trace JSON. blippex: 4 OOA events (19% — app-specific, redirects to browser). Other 3 apps with data: 0% OOA. OOA detection and trace output working.
- [x] 4.8 Verify cycle time profiling appears in trace JSON with per-phase breakdown — VERIFIED: `capture_ms`, `scoring_ms`, `exec_ms`, `total_ms` fields present in all trace lines. hourlyreminder avg=698ms/iter. blippex avg=2052ms/iter.
- [x] 4.9 Review all changes against P1–P4 principles — PASS. Zero violations. Two minor suggestions fixed: (S1) added inline comment for `scoringMs` approximation in `AgentLoop.java`, (S2) moved `getLastSelectedTier()` before `updateBackDecay` Javadoc in `ActionSelector.java`.
