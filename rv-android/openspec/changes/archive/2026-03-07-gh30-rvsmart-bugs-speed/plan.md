# Change Plan: gh30-rvsmart-bugs-speed

**Date**: 2026-03-06
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#30](https://github.com/PAMunb/rvsec/issues/30)
**PRD Reference**: FR18, FR19, NFR01
**Domains**: tools

## 1. Context

RVSmart is a Java exploration agent running via `app_process` inside the Android emulator, achieving ~14 evt/s theoretical throughput. In practice, on 22 APKs the measured throughput is 1.1–4.1 evt/s — a 70–92% loss. Five independent LLM analyses (Claude, Codex, Gemini, MiniMax, Qwen) and comparison with the rvagent Python codebase identified 7 structural bugs and 5 speed bottlenecks that explain this gap.

The bugs are not subtle. `ScreenNode.totalActions` is never initialized, so `getSaturationRate()` always returns 1.0 — every screen appears fully saturated. `generateCandidateActions()` omits SCROLL entirely, making any app with lists unexplorable. `StaticMap` queries use a signature format that does not match the static analysis JSON keys, so `MopScorer` (rvsmart's key differentiator) returns 0 for every action. The `RewardPropagator` computes cumulative rewards but no scorer reads them. The agent performs 3–4 UI tree captures per iteration instead of 1–2. The LLM hybrid mode is not bootstrapped even when `--mode multimode` is passed.

The screen state hash uses SHA-256 over JSON-serialized widget trees — a crypto hash is overkill for state identity and the JSON serialization step adds unnecessary overhead at 14 evt/s. APE uses Java `hashCode()` (31-polynomial) and FastBot uses `std::hash` + XOR. Both exclude text from the hash by default (too volatile). FastBot deduplicates structurally identical widgets before hashing (list items with same class/resourceID/interactMask merge into one). rvsmart should follow these practices: replace SHA-256 with `Objects.hash()` over sorted structural fields, deduplicate widgets, and exclude text. This is a foundational change — every state-based decision (saturation, backtracking, learning, scoring) depends on correct and efficient state identity.

Beyond these code-level bugs, a post-gh29 experiment (22 APKs × 3 tools × 2 reps, 300s, JCA specs) revealed that **18.6% of total rvsmart exploration time is wasted on out-of-app activities** — the agent leaves the target app (via external intents, BACK presses, or link clicks) and has no mechanism to detect or recover from this state. 75% of traces are affected. CLICK triggers 78% of out-of-app events, and the dominant destination is `NexusLauncherActivity` (79% of out-of-app segments). Once in the launcher, the agent flounders with BACK/CLICK instead of immediately restarting. The worst case (pyconza.schedule) spent 84.3% of its time outside the app. This is the single most impactful problem to fix.

The speed bottlenecks compound these bugs. The default throttle is 200ms (dominates 80% of cycle time when variants set 50ms), app restarts cost 2000ms, adaptive wait is unconditional, and screen state is re-captured at each iteration start even when the previous post-action capture is still valid. However, reducing throttle too aggressively (e.g., to 50ms) risks the UI not stabilizing before the next action, potentially increasing out-of-app events. A moderate reduction to 100ms is safer.

Additional issues flagged by cross-LLM consensus: (a) the `selectAction()` Tier 2 path does not filter actions with 3+ failures, wasting budget on known-bad elements (only the retry path filters); (b) `selectNextBest()` during retry can choose a non-BACK action that breaks an active PathBuffer plan; (c) multiple BACKs within one retry cycle execute at the same score (no decay update inside the loop); (d) no cycle time profiling exists to validate throttle choices with data.

These must be fixed before any feature work (gh31: coverage tracking, scoring improvements) can have meaningful impact. Calibrating parameters on a broken base is counterproductive.

Full analysis: `docs/20260306_rvsmart_refactoring.md` (Phase 0 + Phase 4).

**Baseline experiment** (post-gh29): `results/cli_experiment_20260305_180341_fe33918e/` — 22 APKs × 3 tools (rvsmart, ape, fastbot) × 2 reps, 300s, JCA specs. Instrumented APKs with static analysis JSON available at `instrumented_apks/` subdirectory — reuse for validation to skip pre-processing.

| Tool | Avg Method | Avg MOP | Avg Activities |
|------|-----------|---------|----------------|
| rvsmart:mvp | 17.76% | 25.54% | 48.86% |
| ape | 20.36% | 31.57% | 49.18% |
| fastbot | 16.95% | 25.05% | 44.57% |

## 2. Scope

Changes are primarily in the rvsmart Java codebase at `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/`. One small change in the Python rvsmart-tool plugin (`modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/tool.py`): pass `--code-package app.code_package` so the Java agent's `StaticMap`/`MopScorer` can correctly match activity names against the static analysis JSON (which uses code-package-qualified class names). OOA detection does **not** need `--code-package` — it uses `ComponentName.getPackageName()` (manifest package) compared against the existing `--package` arg.

The changes are organized into 4 groups:

**Group A — Structural Bug Fixes (tasks 0.0–0.10)**: Fix the hash, the 7 bugs that break core agent mechanics, and the action selection gaps. Task 0.0 (hash redesign) is foundational and should be implemented first. The remaining tasks are independent of each other.

**Group B — Out-of-App Recovery (tasks 0.8–0.9)**: Detect when the agent leaves the target app and recover immediately. This is the highest-impact fix: 18.6% of experiment time is wasted on out-of-app activities. Must be implemented before speed optimizations — reducing throttle without OOA recovery would increase wasted iterations.

**Group C — Speed Optimizations (tasks 4.1–4.5)**: Reduce cycle time to close the gap between theoretical and actual throughput. Task 4.4 (screen state caching) depends on task 0.6 (reduce UI captures) because the caching strategy builds on the simplified capture flow. Task 4.5 (cycle time profiling) provides data to validate the throttle choice. Throttle reduced to 100ms (not 50ms) to avoid UI instability.

**Group D — Validation (task 4.6)**: Benchmark run on baseline APKs to validate improvements. Depends on Groups A, B, and C being complete.

## 3. File Inventory

All paths relative to `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/`.

### Group A — Structural Bug Fixes

| File | Action | Detail |
|------|--------|--------|
| `core/ScreenState.java` | Edit | **Task 0.0**: Replace SHA-256 + JSON serialization hash with `Objects.hash()` over sorted structural widget signatures. Widget signature fields: `{className, resourceID, interactMask}` (clickable, scrollable, checkable, long-clickable, enabled). Exclude text (too volatile — APE and FastBot both exclude it by default). Exclude coordinates (shift between visits). Exclude index (brittle). Add widget deduplication: widgets with identical signatures merge before hashing (FastBot pattern — prevents list items from inflating state counts). Hash components: `Objects.hash(activityName, dedupedSortedWidgetSignatures)`. Sort widgets by (className, resourceID) for determinism. Old SHA-256 implementation is deleted entirely (P3). |
| `graph/ScreenNode.java` | Edit | **Task 0.1**: Add `setTotalActions(int count)` method. Currently `totalActions` defaults to 0 and is never set, causing `getSaturationRate()` to always return `1.0`. The method should set `totalActions` to the count of interactive elements discovered on the first visit. Also add a guard: `if (totalActions > 0)` in `getSaturationRate()` to prevent division by zero. |
| `core/AgentLoop.java` | Edit | **Task 0.1**: After `uiCapture.capture()` in `runIteration()`, call `screenNode.setTotalActions(items.size())` on the first visit to that screen (when `visitCount == 1`). This initializes the element count that drives saturation computation. |
| `strategy/ActionSelector.java` | Edit | **Task 0.2**: In `generateCandidateActions()`, add SCROLL action generation for items where `item.isScrollable()` is true. Generate SCROLL actions in 4 directions: DOWN (primary, same base score as CLICK), UP, LEFT, RIGHT (secondary, base score = CLICK * 0.5). Coordinates: center of the scrollable container. This ensures horizontal tabs, carousels, and above-viewport content are discoverable. |
| `staticdata/StaticMap.java` | Edit | **Task 0.3**: Parse both the **reachability** and **transitions** sections of `static_analysis.json`. Expose `getReachableMethods(activityName)` for activity-level MOP lookup (used by MopScorer) and `getTransitions(activityName)` for WTG transition lookup (used by WtgScorer in gh31). Use `Config.codePackage` to match activity names against JSON keys (code-package-qualified). The JSON keys use class-qualified method signatures (e.g., `"br.unb.cic.cryptoapp.MainActivity.onCreate(android.os.Bundle)"`), but rvsmart queries with coordinate-based action signatures (e.g., `"click@540,960"`). Fix: change the lookup strategy to query by current activity name instead of action signature — if the current activity has reachable MOP methods, all actions on that screen get a MOP boost. This is a coarser but functional approach. |
| `strategy/scorers/MopScorer.java` | Edit | **Task 0.3**: Update `score()` to use the activity-based lookup from `StaticMap` instead of the action-signature-based lookup. Receive the current activity name as part of the scoring context. |
| `strategy/PathBuffer.java` | Edit | **Task 0.4**: In `consumeNext()`, validate that the agent's current position matches the expected position BEFORE consuming (removing) the next hop from the queue. Currently, the hop is consumed first, and if the agent diverges (e.g., due to a system dialog), the remaining path is invalidated because the consumed hop cannot be restored. Also add a guard in `selectNextBest()`: if PathBuffer has an active plan, only allow BACK alternatives during retry — prevents retry from invalidating planned backtrack routes. |
| `core/AgentLoop.java` | Edit | **Task 0.5**: After calling `learner.update()`, pass the computed reward to `rewardPropagator.propagate(screenHash, action.signature(), reward)`. Then in the scoring context passed to `ActionSelector`, include the cumulative reward map from `rewardPropagator`. Also call `updateBackDecay()` inside the retry while-loop after each BACK execution — without this, multiple consecutive BACKs within one retry cycle execute at the same score, causing over-backtracking. |
| `strategy/ActionSelector.java` | Edit | **Task 0.5**: Create a `RewardScorer` (or integrate into `GradualDecayScorer`) that reads cumulative reward values from the scoring context. Actions with higher cumulative reward (from previous successful explorations) get a score boost. Suggested weight: `+cumulativeReward * 0.3` to keep it as a secondary signal. |
| `core/AgentLoop.java` | Edit | **Task 0.6**: Eliminate redundant UI captures. The current flow does: (1) initial capture, (2) action execution, (3) post-action capture, (4) optional adaptive wait capture. Optimize: store the post-action capture result and reuse it as the next iteration's "initial" capture. Only re-capture when: crash recovery, out-of-app recovery, or stuck recovery. This reduces captures from 3–4 to 1–2 per iteration. |
| `Main.java` | Edit | **Task 0.7**: When `--mode multimode` or `--mode llm_only` is passed, create and wire the LLM components: `SglangClient`, `ToolCallParser`, `PromptBuilder`, `ImageProcessor`, `ScreenshotCapture`, and `RoutingManager`. Currently these are all null regardless of mode, making `tryLlmAction()` in `AgentLoop` always skip the LLM path. |
| `strategy/ActionSelector.java` | Edit | **Task 0.10**: Add failure-aware filtering in the main `selectAction()` Tier 2 path. Currently, the `failureCount >= 3` guard only applies in `selectNextBest()` (retry path), so the main path wastes budget on known-bad non-interactive elements in polluted screens. Apply the same guard to Tier 2 action selection. |

### Group B — Out-of-App Recovery

| File | Action | Detail |
|------|--------|--------|
| `core/AgentLoop.java` | Edit | **Task 0.8**: After each action execution and UI capture, check if the foreground app matches the target. Use `AppController.getCurrentActivity().getPackageName()` (returns the manifest package of the top activity) and compare against `Config.getPackage()` (the `--package` CLI arg, also the manifest package). If they differ, the agent is out-of-app. On OOA detection: log the event (trigger action, destination package) via RVTRACK, and skip scoring/learning for that iteration. Known launcher packages (`com.android.launcher3`, `com.google.android.apps.nexuslauncher`, `com.android.launcher`) trigger immediate RESTART bypassing the tolerance counter (rvagent-style fast-path). |
| `core/AgentLoop.java` | Edit | **Task 0.9**: Add an OOA tolerance counter (default: 3, matching rvagent's `out_of_app_tolerance`). For non-launcher OOA packages (e.g., Chrome opened by an in-app link), allow up to 3 iterations before forcing RESTART — the user may return via BACK. For launcher packages, bypass tolerance and restart immediately. If the agent detects 3 consecutive OOA events after RESTART (app keeps redirecting), fall back to `forceStop` + `startApp`. Reset counter on successful return to target app. |

### `--code-package` for StaticMap/MopScorer (task 0.3 support)

The `--code-package` parameter is **not** needed for OOA detection (which uses manifest package from `ComponentName.getPackageName()`). It is needed for **MopScorer/StaticMap** (task 0.3): the static analysis JSON uses class-qualified method signatures keyed by the **code package** (e.g., `org.godotengine.godot.GodotLib.initialize(...)` for an app whose manifest says `ir.hsn6.trans`). In ~27.5% of APKs, manifest and code package differ. Without `--code-package`, the activity-based MOP lookup in task 0.3 would fail for these APKs.

| File | Action | Detail |
|------|--------|--------|
| `Main.java` | Edit | **Task 0.3a**: Add optional `--code-package` CLI argument. Store in `Config.codePackage`. Falls back to `--package` when absent. Log a warning when falling back: `"No --code-package provided. MOP scoring may be inaccurate for multi-package apps."` — aids debugging when MopScorer returns 0 for the 27.5% of APKs where manifest and code package differ. |
| `core/Config.java` | Edit | **Task 0.3a**: Add `codePackage` field. Populated from `--code-package` CLI arg, falls back to `package` (manifest) if not provided. |
| `staticdata/StaticMap.java` | Edit | **Task 0.3**: (Already listed in Group A.) Use `codePackage` to match activity names against the static analysis JSON keys. The JSON keys use `code_package`-qualified class names. |

### Python-side (rv-android)

| File | Action | Detail |
|------|--------|--------|
| `modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/tool.py` | Edit | **Task 0.3b**: In `_build_main_command()`, pass `--code-package app.code_package` after `--package app.package_name`. The `App.code_package` property is already computed by `PackageDetector` during APK loading. When running standalone (no rv-android), the user omits `--code-package` and the Java agent falls back to `--package`. |

### Group C — Speed Optimizations

| File | Action | Detail |
|------|--------|--------|
| `core/Config.java` | Edit | **Task 4.1**: Change the default `throttleMs` from 200 to 100. A moderate reduction avoids UI instability (50ms risks acting before the screen stabilizes, increasing out-of-app events). Also verify that the properties file loading path correctly overrides this default — the Claude analysis flagged a potential issue where the Java default overrides the properties value. |
| `core/AgentLoop.java` | Edit | **Task 4.2**: In `recoverApp()`, reduce `forceStop` sleep from 500ms to 200ms and `startApp` sleep from 1500ms to 800ms. Total restart cost drops from 2000ms to 1000ms. The `app_process` execution model resumes immediately after the app starts — no ADB reconnection needed. |
| `core/AgentLoop.java` | Edit | **Task 4.3**: Make adaptive wait conditional on action type. Apply the `adaptiveWaitMs` (150ms) wait only for CLICK and LONG_CLICK actions on interactive widgets (buttons, links). Skip adaptive wait for SET_TEXT (immediate effect) and SCROLL (effect is immediate or absent). |
| `core/AgentLoop.java` | Edit | **Task 4.4**: Implement screen state caching. After the post-action capture, store the resulting `ScreenState` in a field (`lastScreenState`). At the start of the next iteration, reuse `lastScreenState` instead of re-capturing if: (a) no crash recovery occurred, (b) no out-of-app recovery occurred, (c) no stuck recovery occurred. Invalidate the cache on any recovery event. Depends on task 0.6. |
| `core/AgentLoop.java` | Edit | **Task 4.5**: Add cycle time profiling via RVTRACK. Add `System.currentTimeMillis()` timestamps around each phase of `runIteration()`: capture, scoring, execution, wait. Log per-iteration breakdown via RVTRACK (e.g., `RVTRACK CYCLE capture=12ms scoring=3ms exec=45ms wait=100ms total=160ms`). This enables data-driven validation of the 100ms throttle choice in task 4.6 and future calibration. |

### Group D — Validation

| File | Action | Detail |
|------|--------|--------|
| Test infrastructure | Run | **Task 4.6**: Run rvsmart on a subset of baseline APKs (e.g., 5 APKs) via `rv-experiment run`. Measure: evt/s, unique states/min, methods/min, OOA%, cycle time breakdown. Compare against pre-fix baseline. Target: ≥10 evt/s sustained, OOA% < 5%. Use cycle time profiling data (task 4.5) to validate the 100ms throttle choice. |

### Test Files (new or modified)

All paths relative to `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/test/java/br/unb/cic/rvsmart/`.

| File | Action | Detail |
|------|--------|--------|
| `core/ScreenStateTest.java` | Edit | Add tests for new hash: verify determinism, widget deduplication, text exclusion, activity-based grouping. Verify that structurally identical screens produce the same hash regardless of widget order. |
| `graph/ScreenNodeTest.java` | Edit | Add tests for `setTotalActions()` and verify `getSaturationRate()` returns correct values (not always 1.0) |
| `strategy/ActionSelectorTest.java` | Edit | Add tests for SCROLL action generation in 4 directions from scrollable items. Add tests for failure-aware Tier 2 filtering (failureCount >= 3 excluded). |
| `staticdata/StaticMapTest.java` | Edit | Add tests for activity-based MOP lookup and `getTransitions()` method |
| `strategy/scorers/MopScorerTest.java` | Edit | Update tests for activity-based scoring |
| `strategy/PathBufferTest.java` | Edit | Add test for position validation before hop consumption. Add test for retry-safe backtrack protection (PathBuffer active → only BACK in retry). |
| `core/AgentLoopTest.java` | Edit | Add tests for screen state caching, reduced capture count, OOA detection, OOA recovery via RESTART, consecutive OOA fallback to forceStop, BACK decay inside retry loop, and cycle time profiling output. |
| `core/ConfigTest.java` | Edit | Verify default throttle is 100ms. Verify `--code-package` fallback to `--package`. |

## 4. Execution Order

```
Task 0.0 (hash redesign) — foundational, must be first
     |
     v
Group A remainder (bug fixes, tasks 0.1–0.10) — all tasks independent, can be done in parallel
     |
     v
Group B (OOA recovery, tasks 0.8–0.9) — depends on A being stable
     |
     v
Group C (speed, tasks 4.1–4.5) — 4.4 depends on 0.6, rest independent
     |
     v
Group D (validation, task 4.6) — depends on A + B + C
```

Task 0.0 (hash redesign) must complete first because it changes the state identity that all other components depend on. After 0.0, Groups A and C can overlap: tasks 4.1, 4.2, 4.3, 4.5 have no dependency on Group A and can start immediately. Only task 4.4 depends on task 0.6. Group B (OOA recovery) should be implemented before Group C speed optimizations — reducing throttle without OOA recovery would increase wasted iterations in the launcher. Group D must wait for all previous groups.

This change touches ~14 source files + ~8 test files = ~22 files total. Subagent orchestration recommended for parallel wave execution.

## 5. Acceptance Criteria

- [ ] Screen state hash uses `Objects.hash()` over `{activityName, dedupedSortedWidgetSignatures}` — no SHA-256, no JSON serialization
- [ ] Widget signatures include `{className, resourceID, interactMask}` — no text, no coordinates, no index
- [ ] Structurally identical widgets are deduplicated before hashing (list items with same class/resourceID/interactMask merge)
- [ ] Old SHA-256 hash implementation is deleted entirely (P3: no legacy code, no backward compat mode)
- [ ] `ScreenNode.getSaturationRate()` returns values between 0.0 and 1.0 based on actual element coverage (not always 1.0)
- [ ] `generateCandidateActions()` produces SCROLL actions in 4 directions (DOWN, UP, LEFT, RIGHT) for scrollable elements
- [ ] `MopScorer` returns non-zero scores when static analysis data is available and the current activity has reachable MOP methods
- [ ] `StaticMap` exposes both `getReachableMethods(activityName)` and `getTransitions(activityName)` from the static analysis JSON
- [ ] `PathBuffer.consumeNext()` validates position before consuming the next hop
- [ ] `selectNextBest()` only allows BACK alternatives when PathBuffer has an active plan
- [ ] `RewardPropagator` values are consumed by at least one scorer during action selection
- [ ] `updateBackDecay()` is called inside the retry while-loop after each BACK execution
- [ ] UI captures per iteration reduced to 1–2 (from 3–4), measured via RVTRACK logs
- [ ] LLM components are instantiated when `--mode multimode` is passed (verified by `tryLlmAction()` not returning null-check early)
- [ ] `selectAction()` Tier 2 excludes actions with `failureCount >= 3`
- [ ] OOA detection uses `AppController.getCurrentActivity().getPackageName()` vs `Config.getPackage()` (both manifest package)
- [ ] `--code-package` CLI arg accepted by rvsmart Java agent for StaticMap/MopScorer, falls back to `--package` when absent
- [ ] Warning logged when `--code-package` falls back to `--package`
- [ ] `rvsmart_tool` passes `--code-package app.code_package` in command construction
- [ ] `StaticMap` uses `codePackage` for activity-based MOP lookup against static analysis JSON keys
- [ ] Launcher packages bypass tolerance counter and trigger immediate RESTART
- [ ] Non-launcher OOA allows 3 iterations tolerance before RESTART (matching rvagent behavior)
- [ ] 3 consecutive OOA-after-RESTART triggers forceStop+startApp fallback
- [ ] OOA iterations are skipped for scoring/learning (no wasted computation on non-exploration data)
- [ ] Default throttle is 100ms (verified in `Config.java` default and properties loading)
- [ ] Restart cost ≤1000ms (verified in `recoverApp()` sleep durations)
- [ ] Adaptive wait skipped for SET_TEXT and SCROLL actions
- [ ] Screen state cached and reused across iterations when no recovery event occurred
- [ ] Cycle time profiling logged via RVTRACK per iteration (capture, scoring, execution, wait durations)
- [ ] OOA% < 5% on validation benchmark (down from 18.6% baseline)
- [ ] Sustained throughput ≥10 evt/s on cryptoapp 60s benchmark
- [ ] All 370 existing JUnit 5 tests pass without regression
- [ ] New tests added for all bug fixes and optimizations
