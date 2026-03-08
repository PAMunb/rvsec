## Context

After gh29 implemented rvsmart as a Java exploration agent running via `app_process`, and gh30/gh31 added bug fixes, speed improvements, coverage tracking, and scoring enhancements, experiment gh31_mini revealed that the static analysis guidance system — rvsmart's central design purpose — has never functioned. The `StaticMap` JSON parser cannot read the output format produced by `RvsecAnalysisClient` (gh27), making `MopScorer` and `WtgScorer` return 0 in 100% of iterations. The `RewardScorer` fills the vacuum with infinitely accumulating values that cause ping-pong loops. Recovery mechanisms fail silently. AccessibilityNodeInfo objects leak.

This change fixes 10 bugs (A-J), removes 2 harmful scorers (RewardScorer, RewardPropagator), fixes CoverageDensityScorer indirectly via UICoverageTracker ID fix, and corrects 5 anomalies. ~200 lines of change across 12 Java files + 1 Python file. No new classes. No new mechanisms.

**Proposal**: `openspec/changes/gh32-rvsmart-scoring-recovery/proposal.md`
**Delta spec**: `openspec/changes/gh32-rvsmart-scoring-recovery/specs/tools/spec.md`
**Diagnostic**: `docs/20260307_rvsmart_refactoring.md`
**PRD references**: FR18 (Tool Registration), FR19 (External Tool Support), NFR01 (Performance), NFR04 (Reliability)

## Architecture

No architectural changes — the component structure remains identical. The change fixes broken components and removes harmful ones within the existing architecture.

```
AgentLoop (orchestrator)
  |
  +-- UiCapture (existing) -----> UICoverageTracker (gh31, ID fix here)
  |
  +-- StaticMap (REWRITTEN parser)
  |     |
  |     +-- parseReachability() : JsonArray format + activity name normalization
  |     +-- parseTransitions()  : JsonArray format + window ID cross-reference
  |     |
  +-- ActionSelector (existing, simplified scorer chain)
  |     |
  |     +-- MopScorer (FIXED via StaticMap)
  |     +-- WtgScorer (FIXED via StaticMap, vestigial param removed)
  |     +-- GradualDecayScorer (unchanged)
  |     +-- SystemElementFilter (unchanged)
  |     +-- ComponentPriorityScorer (unchanged)
  |     +-- ConfirmedCoverageScorer (unchanged)
  |     +-- CoverageDensityScorer (FUNCTIONAL after UICoverageTracker ID fix — INV-RSM-39)
  |     +-- [REMOVED: RewardScorer]
  |
  +-- [REMOVED: RewardPropagator]
  |
  +-- StuckDetector (existing, AgentLoop now calls updateWithActionType)
  |
  +-- PathBuffer (existing, off-by-one fix)
  |
  +-- ScreenNode (existing, totalActions update fix)
  |
  +-- OOA Recovery (ENHANCED: multi-stage with foreground forceStop)
  |
  +-- AccessibilityNodeInfo lifecycle (NEW: try/finally recycle)
```

### Key Components

| Component | Change | Input | Output |
|-----------|--------|-------|--------|
| `staticdata/StaticMap.java` | Rewrite parseReachability() and parseTransitions() to read JsonArray; normalize activity names | `static_analysis.json` (device) | `Map<activity, Set<mopMethods>>`, `Map<activity, List<transitions>>` |
| `core/AgentLoop.java` | OOA multi-stage recovery, splash wait, SET_TEXT effect, error trace, ANI recycle, remove RewardPropagator wiring | ScreenState, AccessibilityNodeInfo | Trace JSON lines |
| `strategy/ActionSelector.java` | Remove RewardScorer from scorer chain | Candidate actions, scoring context | Scored and selected action |
| `strategy/PathBuffer.java` | Fix off-by-one in invalidateIfDiverged() | Current hash, expected path | Boolean diverged |
| `core/UICoverageTracker.java` | Unify element ID scheme between register and interact; scope interactions by screen hash (composite key) | ScreenItems, action target | Coverage gap float |
| `device/HeapMonitor.java` | Use dynamic return value for adaptive sleep | Heap stats | Throttle duration ms |
| `graph/ScreenNode.java` | Update totalActions on every visit, remove cumulativeRewards | Element count per visit | Saturation rate |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|------------------------|----------------|------|
| INV-RSM-30: Reachability JsonArray parsing | `StaticMap.parseReachability()` | `StaticMapTest.testParseReachabilityJsonArray` |
| INV-RSM-31: Transitions JsonArray parsing | `StaticMap.parseTransitions()` | `StaticMapTest.testParseTransitionsJsonArray` |
| INV-RSM-30: Activity name normalization | `StaticMap.qualifiedPrefix()` / normalize method | `StaticMapTest.testActivityNameNormalization` |
| INV-RSM-32: 7-scorer chain | `ActionSelector` constructor | `ActionSelectorTest.testScorerChainComposition` |
| INV-RSM-33: OOA multi-stage recovery | `AgentLoop.handleOoaRestart()` | `AgentLoopTest.testOoaMultiStageRecovery` |
| INV-RSM-34: Empty screen wait | `AgentLoop.runIteration()` | `AgentLoopTest.testEmptyScreenWait` |
| INV-RSM-35: SET_TEXT implicit effect | `AgentLoop` post-action effect detection | `AgentLoopTest.testSetTextImplicitEffect` |
| INV-RSM-36: Exception trace line | `AgentLoop.run()` catch block + all 6 early-return paths in `runIteration()` | `AgentLoopTest.testExceptionWritesTrace`, `AgentLoopTest.testEarlyReturnTrace` (x3) |
| INV-RSM-37: ANI recycle | `AgentLoop` try/finally blocks | (verified by code review — no mock for native objects) |
| INV-RSM-38: PathBuffer off-by-one | `PathBuffer.invalidateIfDiverged()` | `PathBufferTest.testDivergedAtCorrectPosition` |
| INV-RSM-39: UICoverageTracker ID | `UICoverageTracker` register/interact | `UICoverageTrackerTest.testIdConsistency` |
| INV-RSM-41: UICoverageTracker screen scoping | `UICoverageTracker.recordInteraction()` composite key | `UICoverageTrackerTest.testScreenScopedInteraction` |
| INV-RSM-42: HeapMonitor throttle used | `AgentLoop` sleep after `check()` call | `AgentLoopTest.testHeapMonitorDynamicThrottle` |
| INV-RSM-40: ScreenNode totalActions update | `ScreenNode.setTotalActions()` | `ScreenNodeTest.testTotalActionsUpdatedOnRevisit` |
| Scoring chain removal | `ActionSelector`, `Main.java` | `ActionSelectorTest.testNoRewardScorer` |
| Empty trace detection | `rvsmart_tool/tools/rvsmart/tool.py` | `test_rvsmart_tool.testEmptyTraceWarning` |

## Goals / Non-Goals

**Goals:**
- Restore MopScorer and WtgScorer to operational status by fixing the StaticMap JSON parser
- Eliminate RewardScorer's infinite accumulation that dominates scoring and causes ping-pong loops
- Fix OOA recovery to close the foreground app, not just restart the target
- Handle empty screens (splash) with wait-and-recapture instead of immediate RESTART
- Make SET_TEXT count as effect to prevent false stuck detection in forms
- Make all iteration exit paths visible in trace output — exceptions in `run()` AND all 6 early-return paths in `runIteration()` (crash-at-start, null root, system dialog, post-action crash, native crash, OOA in-progress)
- Prevent AccessibilityNodeInfo native object leaks
- Fix PathBuffer off-by-one that breaks multi-hop BFS recovery
- Fix UICoverageTracker: (1) ID mismatch that makes coverage gap always maximum; (2) interaction scoping by screen hash to prevent cross-screen contamination
- Fix ScreenNode.totalActions permanent lock from transient first-visit state
- Fix HeapMonitor adaptive throttle: use the dynamic return value of `check()` instead of always sleeping fixed `config.getThrottleMs()` — the adaptive heap protection was effectively dead code

**Non-Goals:**
- Adding new scorers or scoring mechanisms — the goal is to fix what exists and remove what's harmful
- Changing the hash algorithm — the structural hash (className + resourceId + interactMask) is correct by design (FastBot pattern)
- Adding a dedicated cycle detector for ping-pong — the RewardScorer removal eliminates the root cause
- Changing the softmax temperature — addressed by removing RewardScorer (which made softmax useless due to 14000+ deltas)
- Fixing the HeapMonitor *formula* (`freeMemory/maxMemory` vs `(max-total+free)/max`) — deferred; the no-op bug (return value of `check()` never read by the caller) is fixed in this change
- Adding CrashInterceptor race condition fix — deferred (MODERATE, requires careful thread-safety analysis)

## Decisions

### D1: Remove RewardScorer entirely vs. cap accumulation

**Decision**: Remove entirely.

**Rationale**: The RewardScorer was designed as TD(λ) learning to guide exploration toward productive states. However, it has two fundamental problems: (1) `accumulatedRewards` grows without bound because `maxCumulativeFactor` is defined but never enforced, and (2) with MOP and WTG scorers fixed, the agent has real static analysis guidance and doesn't need reward learning as a substitute. Capping the accumulation would add complexity to fix a scorer whose entire purpose is redundant when the static analysis system works.

**Alternative considered**: Add cap via `maxCumulativeFactor`. Rejected because it treats the symptom (overflow) not the cause (redundancy), and adds maintenance complexity for a feature with no demonstrated value.

### D2: Activity name normalization strategy

**Decision**: Reconstruct fully-qualified names from trace-format names by prepending code package and re-inserting dots at camelCase word boundaries.

**Rationale**: Trace-format names (e.g., `"uiactivitiesSplashActivity"`) are produced by stripping the code package prefix and removing dots from the relative class path. The inverse operation is deterministic: split on uppercase letters that follow lowercase letters to recover the package segments, then prepend the code package. This handles standard Android naming conventions (packages use lowercase, class names use PascalCase).

**Alternative considered**: Store both formats in StaticMap and do double lookup. Rejected for P1 (unnecessary complexity) — one normalization function is simpler.

### D3: OOA recovery: BACK first vs. forceStop first

**Decision**: BACK first, then forceStop if needed.

**Rationale**: `input keyevent BACK` is less disruptive than `forceStop` — it dismisses modal activities (file pickers, permission dialogs) without killing the entire app process. If BACK succeeds, the target app may already be in the foreground without needing a full restart. `forceStop` is the escalation for apps that don't respond to BACK (e.g., apps with `onBackPressed()` override or system components like SoundPicker that ignore BACK).

### D4: Empty screen wait duration

**Decision**: 2000ms fixed wait.

**Rationale**: Most splash screens use `Handler.postDelayed()` with 1500-3000ms delay. A 2000ms wait covers the majority of cases while keeping the delay bounded. Adaptive wait (measure actual transition time) would add complexity without clear benefit — if 2000ms doesn't work, the app likely requires user input to proceed, and RESTART is the correct fallback.

### D5: SET_TEXT implicit effect vs. text-aware hash

**Decision**: Implicit effect (SET_TEXT always counts as having effect), not text-aware hash.

**Rationale**: Including text in the hash would cause state explosion in apps with dynamic content (news feeds, timestamps, chat messages change text every second). The structural hash (FastBot pattern) is correct by design. The problem is limited to effect detection — comparing hashes before/after SET_TEXT shows no change because text is excluded. Treating SET_TEXT as implicit effect is a 2-line fix that solves the problem without touching the hash algorithm.

## Data Flow

### StaticMap Parsing (Fixed)

```
RvsecAnalysisClient (gh27)
  |
  v
static_analysis.json (on device)
  |  "reachability": [                          <-- JsonArray
  |    {"className": "com.example.MainActivity",
  |     "methods": [{"signature": "...", "directlyReachesMop": true}]}
  |  ],
  |  "windows": [                               <-- JsonArray
  |    {"id": 1, "type": "activity", "name": "com.example.MainActivity"}
  |  ],
  |  "transitions": [                           <-- JsonArray
  |    {"sourceId": 1, "targetId": 2, "events": [...]}
  |  ]
  |
  v
StaticMap.load(jsonPath, codePackage)
  |
  +-- parseReachability(json)
  |     Read JsonArray, iterate classes
  |     For each method with directlyReachesMop=true:
  |       mopMethods[normalizedActivity].add(signature)
  |
  +-- parseWindows(json)
  |     Build windowIdToActivity map
  |
  +-- parseTransitions(json)
        Read JsonArray, iterate transitions
        Cross-ref sourceId/targetId with windowIdToActivity
        Build activityTransitions[sourceActivity].add(targetActivity)
```

### OOA Recovery (Fixed)

```
AgentLoop.runIteration()
  |
  +-- root.getPackageName() != targetPackage
  |     foregroundPkg = root.getPackageName()
  |     outOfAppCounter++
  |
  +-- outOfAppCounter >= tolerance
        |
        +-- consecutiveOoaAfterRestart < MAX (3)
        |     recoverApp()  [forceStop target + startApp target]
        |
        +-- consecutiveOoaAfterRestart >= MAX (3)  [ENHANCED]
              |
              +-- (1) input keyevent BACK
              +-- (2) wait 500ms, check foreground
              +-- (3) if still OOA: am force-stop <foregroundPkg>
              +-- (4) forceStop(target) + startApp(target)
              +-- reset consecutiveOoaAfterRestart
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `getAsJsonArray()` returns null | StaticMap parsing when JSON key missing | Return empty maps, log warning | Agent operates in heuristic mode (MOP/WTG = 0) |
| `JsonSyntaxException` | Malformed JSON file | Catch, log error, set `isLoaded=false` | Agent operates in heuristic mode |
| `NullPointerException` in `runIteration()` | Any component failure | Write ERROR trace line, continue to next iteration | Agent continues exploring |
| `root == null` from `getRootInActiveWindow()` | ANR, activity transition, system overload | Skip iteration (existing behavior) | No recycle needed (null check before recycle) |
| `forceStop(foregroundPkg)` fails | System app that can't be stopped | Log warning, proceed with target restart | Best-effort recovery |

## Risks / Trade-offs

**[Risk] Activity name normalization may fail for non-standard naming**: If an app uses non-standard package naming (e.g., underscores in package segments, all-lowercase class names), the camelCase boundary detection may produce wrong results. → **Mitigation**: Log a warning when normalization produces no match. Fall back to heuristic mode (MOP/WTG = 0) for that activity. Standard Android naming conventions cover >95% of apps.

**[Risk] Removing RewardScorer may reduce exploration diversity in apps without static analysis data**: Without reward accumulation, the agent's scoring in no-static-data mode relies only on 5 scorers (GradualDecay, SystemElement, ComponentPriority, ConfirmedCoverage, CoverageDensity). → **Mitigation**: GradualDecayScorer and the existing stochastic selection (softmax with plateau boost) provide sufficient diversity. The PlateauDetector (gh31) further boosts stochastic probability during stalls.

**[Risk] 2000ms splash wait may slow down apps without splash screens**: If a non-splash screen has 0 elements (e.g., loading screen with only a ProgressBar), the 2s wait delays recovery. → **Mitigation**: The wait only triggers when there are ALSO no parents in the graph (first screen only). Subsequent empty screens with parents trigger Tier 3 backtracking instead.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | StaticMap parsing with real JSON format | Create test JSON matching RvsecAnalysisClient output, verify MOP/WTG data populated | ~6 tests |
| Unit | Activity name normalization | Test trace-format → fully-qualified conversion for various patterns | ~4 tests |
| Unit | ActionSelector scorer chain composition | Verify exactly 7 scorers, no RewardScorer | ~2 tests |
| Unit | PathBuffer off-by-one fix | Test invalidateIfDiverged with 2+ hop paths | ~3 tests |
| Unit | UICoverageTracker ID consistency | Verify register and interact use same ID scheme | ~2 tests |
| Unit | ScreenNode.totalActions update on revisit | Verify Math.max behavior across visits | ~2 tests |
| Unit | StuckDetector.updateWithActionType SET_TEXT exemption | Verify SET_TEXT doesn't increment counter | ~2 tests |
| Integration | OOA multi-stage recovery | Mock AppController, verify BACK → forceStop(fg) → restart sequence | ~3 tests |
| Integration | Empty screen wait + recapture | Mock UiCapture returning 0 then >0 elements | ~2 tests |
| Integration | SET_TEXT implicit effect | Verify hadEffect=true after SET_TEXT | ~1 test |
| Integration | Exception trace line + early returns | Verify ERROR trace line written on exception AND on null root / crash-at-start / OOA in-progress exits | ~4 tests |
| Python | Empty trace file detection | Verify warning logged for 0-byte trace | ~1 test |

**Total**: ~34 new tests. All existing tests must continue to pass.

## Open Questions

None — all design decisions are resolved. The diagnostic document was cross-validated by 5 independent LLMs with full consensus on all bugs and solutions.
