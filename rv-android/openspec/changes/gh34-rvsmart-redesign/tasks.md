<!-- =============================================================================
  ENVIRONMENT (required before any Maven or adb command):
    source /etc/profile
  This sets RVSEC_HOME, ANDROID_HOME, JAVA_HOME, and PATH (d8, mvn, adb).

  PATHS:
    Java source : $RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/
    Java tests  : $RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/test/java/br/unb/cic/rvsmart/
    Build root  : $RVSEC_HOME/rvsec/rvsec-android/rvsmart/
    Backup dir  : $RVSEC_HOME/rv-android/backup/
    APK examples: $RVSEC_HOME/rv-android/apks_examples/
    Emulator script: $RVSEC_HOME/rv-android/scripts/run_emulator.sh

  SKILLS (Java): superpowers:test-driven-development, superpowers:systematic-debugging,
                 superpowers:verification-before-completion
  SKILLS (Python/rv-*): NOT used here — rv-* skills are Python-only
  SUBAGENTS: use Agent tool for each independent group (Groups 4+5+8+9 can run in parallel
             after Group 3; see dependency graph below)

  DEPENDENCY GRAPH:
    Groups 1 → 2 → 3 (sequential)
    After Group 3:
      Group 4  (PhaseController)            — independent
      Group 5  (NavigationMap+Backtrack)    — depends on Group 2 (ContentNode rename)
      Group 6  (ActionSelector)             — depends on Groups 3 AND 4
      Group 8  (Metrics+Trace)              — independent (only MetricsCollector+TraceWriter)
      Group 9  (Logging Centralization)     — independent (only RvTrack+PromptBuilder+ToolCallParser)
    Group 7  (AgentLoop Integration)        — depends on Groups 4, 5, 6
    Group 10 (Final Verification)           — sequential, after all others

  Critical path: 1 → 2 → 3 → 5 → 7 → 10
  Secondary:     3 → 4 → 6 → 7
  Parallel wave after Group 3: dispatch subagents for Groups 4, 5, 8, 9 simultaneously
============================================================================= -->

## 1. ScreenState Dual Hash

<!-- DISPATCH: subagent — files: core/ScreenState.java, ScreenStateHashTest.java -->
<!-- SKILL: superpowers:test-driven-development (write test first, then implement) -->

- [x] 1.1 Add `computeContentHash()` to `ScreenState.java` (`$RVSEC_HOME/rvsec/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/core/ScreenState.java`): include activity, className, resourceID, text (≤ 50 chars, trimmed, excluding EditText content), enabled, checked, selected per widget. Use same dedup+sort+Objects.hash pattern as current `computeHash()`.
- [x] 1.2 Rename current `computeHash()` to `computeStructHash()` (no logic change — this is the structural hash).
- [x] 1.3 Add `getContentHash()` and `getStructHash()` accessors. Remove old `getHash()` — update all callers (compiler will flag them).
- [x] 1.4 Write `ScreenStateHashTest` (`src/test/java/.../core/ScreenStateHashTest.java`): verify content hash differs when text/checked/selected changes but structural hash remains the same. Verify EditText text is excluded from content hash. Verify text > 50 chars is trimmed. ~8 test cases.

## 2. ContentNode (rename ScreenNode)

<!-- DISPATCH: subagent — files: graph/ScreenNode.java → ContentNode.java + all callers -->

- [x] 2.1 Backup `graph/ScreenNode.java` to `$RVSEC_HOME/rv-android/backup/`. Rename to `graph/ContentNode.java`. Update package declaration and class name. No behavioral changes.
- [x] 2.2 Update all imports/references: `DynamicStateGraph.java`, `AgentLoop.java`, `ActionSelector.java`, `StuckDetector.java`, `BacktrackBfs.java`, scorers. Use compiler errors to find all callsites.
- [x] 2.3 Update existing `ScreenNodeTest` → `ContentNodeTest` (rename file and class, same assertions).

## 3. ContentGraph + StructuralGraph

<!-- DISPATCH: subagent — files: graph/DynamicStateGraph.java (backup), ContentGraph.java (new),
     StructuralGraph.java (new), all DynamicStateGraph callers -->

- [x] 3.1 Backup `graph/DynamicStateGraph.java` to `$RVSEC_HOME/rv-android/backup/`.
- [x] 3.2 Create `graph/ContentGraph.java`: maps `contentHash → ContentNode`. Same API as DynamicStateGraph (`getOrCreate`, `get`, `recordVisit`, `recordAction`, `recordActionSuccess`, `size`). Drop any methods not used by callers.
- [x] 3.3 Create `graph/StructuralGraph.java`: maps `structHash → Set<contentHash>`. Methods: `register(structHash, contentHash)`, `getCluster(structHash)`, `getStructHash(contentHash)`, `size()`.
- [x] 3.4 Update all DynamicStateGraph callers to use ContentGraph (AgentLoop, ActionSelector, Learner, StuckDetector, BacktrackBfs, scorers).
- [x] 3.5 Write `ContentGraphTest` (~4 tests) and `StructuralGraphTest` (~4 tests).

## 4. PhaseController

<!-- DISPATCH: subagent — independent after Group 3 -->
<!-- SKILL: superpowers:test-driven-development -->

- [x] 4.1 Create `strategy/PhaseController.java` with enum `Phase { PHASE_1, PHASE_2, PHASE_3 }`. State machine: starts at PHASE_1. Transitions: PHASE_1 → PHASE_2 when no reachable content state has untested actions. PHASE_2 → PHASE_3 when UI coverage plateau (no new coverage for configurable N iterations, default 30). Any phase → PHASE_1 when new content state discovered.
- [x] 4.2 Track Phase 1 re-entries per structural cluster. After 20 re-entries in same cluster, force Phase 2 for that cluster (prevents infinite content hash loops; fires before the 1000-node global safety valve).
- [x] 4.3 Integrate PlateauDetector into PhaseController for PHASE_2 → PHASE_3 transition. PlateauDetector remains an internal dependency — do not delete.
- [x] 4.4 Write `PhaseControllerTest`: phase transitions, re-entry limits, plateau integration. ~6 tests.

## 5. NavigationMap + BacktrackStrategy

<!-- DISPATCH: subagent — depends on Group 2 (ContentNode rename must be complete) -->
<!-- SKILL: superpowers:test-driven-development -->

- [x] 5.1 Create `graph/NavigationMap.java`: maps `(fromStructHash, actionSignature) → toStructHash`. Methods: `record(from, actionSig, to)`, `findPath(from, to) → List<ActionSignature>` (BFS shortest path), `hasPath(from, to)`, `size()`.
- [x] 5.2 Create `strategy/BacktrackStrategy.java`: two-stage backtracking. Stage 1: press BACK, verify result structHash against expected. Stage 2 (BACK failure): build replay sequence via `NavigationMap.findPath()`, return action list. Needs reference to NavigationMap and StructuralGraph.
- [x] 5.3 Backup `strategy/PathBuffer.java` to `$RVSEC_HOME/rv-android/backup/`. Remove all PathBuffer references from ActionSelector and AgentLoop. In `core/Config.java`, remove the 4 now-dead PathBuffer params: `path_buffer_strategy_priority`, `path_buffer_backtrack_hops`, `path_buffer_coverage_weight`, `path_buffer_mop_weight`.
- [x] 5.4 Adapt `recovery/BacktrackBfs.java` — **do not delete**. BacktrackBfs (unsaturated ancestor BFS for stuck recovery) and BacktrackStrategy (BACK+replay for navigation) serve different purposes and coexist. Since Task 7.5 makes SuccessorTracker record structHashes, BacktrackBfs operates on structHashes by transitivity; verify type consistency.
- [x] 5.5 Write `NavigationMapTest` (~5 tests: record, BFS pathfinding, no-path case, cycle handling) and `BacktrackStrategyTest` (~4 tests: BACK success, BACK failure + replay, broken replay, root screen).

## 6. ActionSelector Redesign

<!-- DISPATCH: subagent — depends on Groups 3 (ContentGraph API) AND 4 (PhaseController) -->
<!-- SKILL: superpowers:test-driven-development -->

- [x] 6.1 Replace 4-tier `selectAction()` with phase-based dispatch: receive `Phase` from PhaseController. Phase 1: return untested action in current content state (scored by existing chain). Phase 2: return action targeting UI coverage gap (use `UICoverageTracker.getCoverageGap()` — coverage gap > `config.uiCoverageThreshold`, navigate to highest-gap screen via NavigationMap). Phase 3: return softmax-selected action with boosted stochastic probability (0.5).
- [x] 6.2 Remove Tier 1 (PathBuffer), Tier 3 (proactive backtrack at saturation >= 0.8), Tier 4 (unified queue). Keep Tier 2 logic as Phase 1 core. Keep existing scoring chain (MopScorer, GradualDecayScorer, SystemElementFilter, ComponentPriorityScorer, WtgScorer, CoverageDensityScorer, ConfirmedCoverageScorer).
- [x] 6.3 Phase 1 navigation: when current content state exhausted, query ContentGraph for nearest structural cluster with untested content states (min BFS hops via NavigationMap). Use BacktrackStrategy to navigate there.
- [x] 6.4 Update `selectNextBest()` (retry logic) to work with phase-based selection.
- [x] 6.5 Update trace observability: replace `lastSelectedTier` with `lastSelectedPhase`. Update score breakdown to include phase info.
- [x] 6.6 Write `ActionSelectorPhase1Test`, `ActionSelectorPhase2Test`, `ActionSelectorPhase3Test`. ~6 tests total.

## 7. AgentLoop Integration

<!-- DISPATCH: subagent — depends on Groups 4, 5, 6 -->

- [x] 7.1 Update `runIteration()`: compute dual hash (contentHash + structHash). Register in ContentGraph and StructuralGraph. Pass phase to ActionSelector.
- [x] 7.2 Wire PhaseController: initialize in constructor, call `currentPhase()` each iteration, notify on new content state discovery.
- [x] 7.3 Wire NavigationMap: record structural transitions after each action with effect.
- [x] 7.4 Wire BacktrackStrategy: replace PathBuffer BACK sequences with BacktrackStrategy calls. Connect to OOA recovery (RESTART + replay instead of just RESTART).
- [x] 7.5 Update SuccessorTracker to operate on structHash instead of contentHash. Record parent-child at structural level.
- [x] 7.6 Add content hash explosion safety valve: if ContentGraph exceeds 1000 nodes, log warning and degrade to structural hash only (contentHash = structHash).
- [x] 7.7 Update constructors: replace DynamicStateGraph with ContentGraph + StructuralGraph + NavigationMap. Add PhaseController and BacktrackStrategy. Remove PathBuffer parameter.
- [x] 7.8 Integration test: mock device, verify dual hash registration, phase transitions, NavigationMap population. ~3 tests.

## 8. Metrics + Trace

<!-- DISPATCH: subagent — independent after Group 3; can run in parallel with Groups 4, 5, 9 -->
<!-- Files: output/MetricsCollector.java, output/TraceWriter.java -->

- [x] 8.1 Extend `MetricsCollector`: add 5 new fields nested in existing JSON sections. In `exploration` section: `content_states` (from `ContentGraph.size()` at finalization), `structural_clusters` (from `StructuralGraph.size()`), `nav_map_edges` (from `NavigationMap.size()`), `phase_distribution` (object `{phase1, phase2, phase3}` — incremented in `AgentLoop.runIteration()` after `PhaseController.currentPhase()`). In `decisions` section: `backtrack_replays` (incremented in `BacktrackStrategy` each time replay executes).
- [x] 8.2 Verify RVSMART_METRICS JSON is a strict superset of gh32 format (all existing fields preserved, new fields added).
- [x] 8.3 Update TraceWriter score breakdown: add `phase` field to breakdown map.
- [x] 8.4 Write `MetricsCollectorTest` and `TraceWriterTest` for new fields. ~4 tests.

## 9. Logging Centralization

<!-- DISPATCH: subagent — independent; can run in parallel with Groups 4, 5, 8 -->
<!-- Files: output/RvTrack.java, llm/PromptBuilder.java, llm/ToolCallParser.java -->

- [x] 9.1 In `output/RvTrack.java`: remove `import android.util.Log` and `private static final String TAG`. In the `log()` method, replace `Log.i(TAG, "[RVTRACK:" + category + "] " + message)` with `System.out.println("[RVTRACK:" + category + "] " + message)`. Keep `logEnabled` flag for test output suppression.
- [x] 9.2 In `llm/PromptBuilder.java`: remove the two `Log.d("RVSMART-PROMPT", ...)` try/catch blocks (one in buildV13, one in buildV17) and their preceding comment lines. LLM prompt text is not production trace data; timing and token counts are already in MetricsCollector.
- [x] 9.3 In `llm/ToolCallParser.java`: remove the `Log.d("RVSMART-LLM-RESP", rawContent)` try/catch block and its preceding comment lines. Keep the `String rawContent = response.getContent()` assignment — it is used by the XML/JSON parsing fallbacks below.

## 10. Final Verification

<!-- DISPATCH: orchestrator runs this directly (sequential, after all groups complete) -->
<!-- SKILL: superpowers:verification-before-completion (run before claiming done) -->

- [x] 10.1 Set up environment and build:
  ```
  source /etc/profile
  cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart
  mvn install -DskipTests
  ```
  The `install` phase (not `package`) triggers maven-resources-plugin which copies the fat JAR to `$RVSEC_HOME/rv-android/modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/rvsmart.jar`. Fix any remaining compiler errors.
- [x] 10.2 Run all unit tests:
  ```
  source /etc/profile
  cd $RVSEC_HOME/rvsec/rvsec-android/rvsmart
  mvn test
  ```
  Fix failures before proceeding. Result: 512 tests, 0 failures.
- [x] 10.3 Verify JAR deployment: confirm file exists at `$RVSEC_HOME/rv-android/modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/rvsmart.jar`. The rvsmart-tool Python wrapper (`tool.py`) handles `adb push` automatically via `_push_file_to_device()` — no manual push needed.
- [x] 10.4 Run standalone smoke test (emulator managed by script for isolated validation only):
  ```
  source /etc/profile
  $RVSEC_HOME/rv-android/scripts/run_emulator.sh
  # install APK and run via rv-platform:
  cd $RVSEC_HOME/rv-android
  uv run rv-platform run --tools rvsmart --apks-dir ./apks_examples --timeout 60
  ```
  Verify trace output contains both JSON lines (TraceWriter) and `[RVTRACK:]` text lines (RvTrack via stdout). Verify `RVSMART_METRICS:` JSON includes new fields (`content_states`, `structural_clusters`, `phase_distribution`, `nav_map_edges`, `backtrack_replays`).
  Result: all verified. unique_activities=5 (all 4 activities explored), content_states=11, structural_clusters=11, nav_map_edges=41, phase_distribution={phase1:74,phase2:0,phase3:0}. [RVTRACK:] lines present in trace.
- [x] 10.5 Rebuild Docker image if applicable. (No Docker image changes required for this change.)
