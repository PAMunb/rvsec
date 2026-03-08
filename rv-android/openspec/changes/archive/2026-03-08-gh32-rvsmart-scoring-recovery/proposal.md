## Why

GitHub Issue: [#32](https://github.com/PAMunb/rvsec/issues/32)

Experiment gh31_mini (5 APKs × rvsmart:mvp × 1 rep × 300s) revealed that rvsmart's static analysis guidance system — the central design purpose of the agent — has never functioned. The `StaticMap` JSON parser cannot read the output format produced by `RvsecAnalysisClient` (gh27), causing `MopScorer` and `WtgScorer` to return 0 in 100% of iterations across all APKs. The `RewardScorer` fills the scoring vacuum with infinitely accumulating rewards that dominate 96.8% of total score, causing deterministic ping-pong loops between 2 states for hundreds of iterations. Recovery mechanisms fail silently: OOA recovery doesn't close the foreground app (57.8% iterations lost), empty screens trigger infinite RESTART storms (93.6% wasted), and exceptions in the main loop produce zero trace output. These 10 bugs (4 CRITICAL, 3 SEVERE, 3 MODERATE) were cross-validated by 5 independent LLMs with full consensus.

## What Changes

**Scoring chain fix and simplification (8 → 7 scorers):**
- Rewrite `StaticMap.parseReachability()` and `StaticMap.parseTransitions()` to read JsonArray format (not JsonObject) from `RvsecAnalysisClient` output, with correct field-level mapping and activity name normalization — unblocks MopScorer and WtgScorer
- **BREAKING**: Remove `RewardScorer` and `RewardPropagator` — infinite accumulation dominates scoring and causes ping-pong loops. With MOP and WTG functional, the agent has real static analysis guidance and no longer needs TD learning as compensation
- Fix `CoverageDensityScorer` via `UICoverageTracker` ID mismatch fix (Bug H) — the scorer was re-enabled by gh31 but returns constant values due to the ID inconsistency
- Remove vestigial `WtgScorer` constructor parameter, `Config` reward constants, `ScreenNode.cumulativeRewards`

**Recovery mechanism fixes:**
- OOA recovery: send `input keyevent BACK` then `forceStop(foregroundPkg)` before restarting target app — closes modal activities (SoundPicker, Chrome) that block the target
- Empty screen strategy: when 0 interactive candidates and no parents in graph, `Thread.sleep(2000)` and recapture before falling back to RESTART — allows splash screen auto-transitions to complete
- SET_TEXT implicit effect: treat SET_TEXT as always having effect (text content changes but structural hash doesn't capture it by design)
- Exception trace: write ERROR trace line in the `catch` block of `run()` AND in all 6 early-return paths of `runIteration()` (crash-at-start, null root, system dialog dismiss, post-action crash, native crash, OOA tolerance-not-exceeded) — currently any of these exits produces an invisible gap in the `.trace` file

**Resource management and internal consistency:**
- `AccessibilityNodeInfo.recycle()` in try/finally at all 4 `getRootInActiveWindow()` call sites in AgentLoop — prevents ~4000 native object leaks per 300s run
- Fix `PathBuffer.invalidateIfDiverged()` off-by-one: compare hash with correct expected position
- Fix `UICoverageTracker` (two bugs): (1) ID mismatch — unify key scheme between `registerScreenElements()` and `recordInteraction()` so resource-ID-based elements match interaction records; (2) screen scoping — `recordInteraction()` receives `screenHash` but never uses it, causing cross-screen contamination; use composite key `(screenHash, elementId)` in the interaction map
- Use `StuckDetector.updateWithActionType()` in AgentLoop (currently dead code) to exempt SET_TEXT from stuck counter
- Add `stuckDetector.reset()` to `executeAction(RESTART)` for consistency with `recoverApp()`
- Update `ScreenNode.totalActions` on every visit via `Math.max(existing, newCount)` to handle transient first-visit states
- Fix `HeapMonitor` adaptive throttle: the dynamic sleep value returned by `check()` is never read — `AgentLoop` always sleeps `config.getThrottleMs()`. Use the returned value so heap pressure actually reduces throughput when needed

**Python plugin (minimal):**
- Detect empty trace file as error condition in `rvsmart-tool`

## Capabilities

### New Capabilities

None — all changes are within the existing rvsmart Java codebase and its Python plugin wrapper.

### Modified Capabilities

- `tools`: The rvsmart section of the tools spec changes in three areas: (1) scoring chain contracts updated to reflect 7-scorer architecture with functional MOP, WTG, and CoverageDensity scorers, removal of RewardScorer/RewardPropagator; (2) recovery behavior contracts added for OOA multi-stage recovery, empty screen wait strategy, SET_TEXT implicit effect, and exception trace output; (3) `StaticMap` data contract updated to document the actual JSON format consumed from `RvsecAnalysisClient`.

## Impact

**Modules affected:**
- `$RVSEC_HOME/rvsec/rvsec-android/rvsmart/` (Java) — 13 files affected (10 modified, 1 caller-only change, 2 deleted)
- `modules/rvsmart-tool/` (Python) — 1 file modified (empty trace detection)

**Files changed (Java):**

| File | Change |
|------|--------|
| `staticdata/StaticMap.java` | Rewrite parseReachability() + parseTransitions() + activity name normalization |
| `core/AgentLoop.java` | OOA fix, splash wait, SET_TEXT effect, error trace, stuck detector call, RESTART reset, ANI recycle, remove RewardPropagator wiring |
| `Main.java` | Remove RewardPropagator instantiation, adjust ActionSelector constructor |
| `strategy/ActionSelector.java` | Remove RewardScorer from constructor |
| `strategy/scorers/WtgScorer.java` | Remove vestigial constructor parameter |
| `core/Config.java` | Remove reward-related constants |
| `graph/ScreenNode.java` | Remove cumulativeRewards, fix totalActions update |
| `strategy/PathBuffer.java` | Fix off-by-one in invalidateIfDiverged() |
| `core/UICoverageTracker.java` | Fix ID mismatch between register and interact + screen-scoped interaction tracking (composite key) |
| `device/HeapMonitor.java` | Use dynamic `check()` return value as sleep duration instead of fixed `config.getThrottleMs()` |
| `recovery/StuckDetector.java` | No code change — AgentLoop starts calling existing updateWithActionType() |
| `strategy/RewardPropagator.java` | DELETE (backup/) |
| `strategy/scorers/RewardScorer.java` | DELETE (backup/) |

**FRs/NFRs:**
- FR18 (Tool Registration): rvsmart scoring chain contracts change
- FR19 (External Tool Support): recovery behavior changes
- NFR01 (Performance): eliminate wasted iterations (RESTART storms, OOA loops, ping-pong)
- NFR04 (Reliability): resource leak prevention, exception visibility

**Cross-module interfaces:**
- No changes to the rvsmart-tool Python plugin interface (JAR invocation, trace parsing)
- No changes to rv-platform's integration with rvsmart-tool
- StaticMap now correctly consumes the JSON format that `RvsecAnalysisClient` (gh27) produces — this is a compatibility FIX, not a change

**Dependencies:**
- gh30 must complete first (tasks 0.1, 0.2, 0.6, 0.7, 4.1-4.4 remain relevant). This change supersedes gh30 tasks 0.3 and 0.5
- gh31 must complete first (provides UICoverageTracker that Bug H fixes here)
