<!-- Subagent dispatch hints:
  Groups 1-3 are sequential (each depends on previous).
  Groups 4-6 can be parallelized after Group 3 completes:
    - Group 4 (PhaseController) is independent
    - Group 5 (BacktrackStrategy + NavigationMap) is independent
    - Group 6 (ActionSelector) depends on Group 4 (PhaseController)
  Group 7 (AgentLoop) depends on Groups 4-6.
  Group 8 (Metrics + Trace) can be parallelized with Group 7.
  Group 9 (Final verification) is sequential after all others.

  Critical path: 1 → 2 → 3 → 6 → 7 → 9

  Java source: $RVSEC_HOME/rvsec-android/rvsmart/src/main/java/br/unb/cic/rvsmart/
  Java tests: $RVSEC_HOME/rvsec-android/rvsmart/src/test/java/br/unb/cic/rvsmart/
-->

## 1. ScreenState Dual Hash

- [ ] 1.1 Add `computeContentHash()` to `ScreenState.java`: include activity, className, resourceID, text (≤ 50 chars, trimmed, excluding EditText content), enabled, checked, selected per widget. Use same dedup+sort+Objects.hash pattern as current.
- [ ] 1.2 Rename current `computeHash()` to `computeStructHash()` (no logic change — this is the structural hash).
- [ ] 1.3 Add `getContentHash()` and `getStructHash()` accessors. Remove old `getHash()` — update all callers (compiler will flag them).
- [ ] 1.4 Write `ScreenStateHashTest`: verify content hash differs when text/checked/selected changes but structural hash remains the same. Verify EditText text is excluded from content hash. Verify text > 50 chars is trimmed. ~8 test cases.

## 2. ContentNode (rename ScreenNode)

- [ ] 2.1 Backup `graph/ScreenNode.java` to `backup/`. Rename to `graph/ContentNode.java`. Update package and class name. No behavioral changes.
- [ ] 2.2 Update all imports/references: `DynamicStateGraph.java`, `AgentLoop.java`, `ActionSelector.java`, `StuckDetector.java`, `BacktrackBfs.java`, scorers. Use compiler errors to find all callsites.
- [ ] 2.3 Update existing `ScreenNodeTest` → `ContentNodeTest` (rename, same assertions).

## 3. ContentGraph + StructuralGraph

- [ ] 3.1 Backup `graph/DynamicStateGraph.java` to `backup/`.
- [ ] 3.2 Create `graph/ContentGraph.java`: maps `contentHash → ContentNode`. Same API as DynamicStateGraph (`getOrCreate`, `get`, `recordVisit`, `recordAction`, `recordActionSuccess`, `size`). Drop any methods not used by callers.
- [ ] 3.3 Create `graph/StructuralGraph.java`: maps `structHash → Set<contentHash>`. Methods: `register(structHash, contentHash)`, `getCluster(structHash)`, `getStructHash(contentHash)`, `size()`.
- [ ] 3.4 Update all DynamicStateGraph callers to use ContentGraph (AgentLoop, ActionSelector, Learner, StuckDetector, BacktrackBfs, scorers).
- [ ] 3.5 Write `ContentGraphTest` (~4 tests) and `StructuralGraphTest` (~4 tests).

## 4. PhaseController

- [ ] 4.1 Create `strategy/PhaseController.java` with enum `Phase { PHASE_1, PHASE_2, PHASE_3 }`. State machine: starts at PHASE_1. Transitions: PHASE_1 → PHASE_2 when no reachable content state has untested actions. PHASE_2 → PHASE_3 when UI coverage plateau (no new coverage for configurable N iterations, default 30). Any phase → PHASE_1 when new content state discovered.
- [ ] 4.2 Track Phase 1 re-entries per structural cluster. After 20 re-entries in same cluster, force Phase 2 for that cluster (prevents infinite content hash loops).
- [ ] 4.3 Integrate PlateauDetector into PhaseController for PHASE_2 → PHASE_3 transition. PlateauDetector becomes an internal dependency of PhaseController (not deleted — used for plateau detection logic).
- [ ] 4.4 Write `PhaseControllerTest`: phase transitions, re-entry limits, plateau integration. ~6 tests.

## 5. NavigationMap + BacktrackStrategy

- [ ] 5.1 Create `graph/NavigationMap.java`: maps `(fromStructHash, actionSignature) → toStructHash`. Methods: `record(from, actionSig, to)`, `findPath(from, to) → List<ActionSignature>` (BFS shortest path), `hasPath(from, to)`.
- [ ] 5.2 Create `strategy/BacktrackStrategy.java`: two-stage backtracking. Stage 1: press BACK, verify result structHash against expected. Stage 2 (BACK failure): build replay sequence via `NavigationMap.findPath()`, return action list. Needs reference to NavigationMap and StructuralGraph.
- [ ] 5.3 Backup `strategy/PathBuffer.java` to `backup/`. Remove all PathBuffer references from ActionSelector and AgentLoop.
- [ ] 5.4 Evaluate `recovery/BacktrackBfs.java` — if BacktrackStrategy subsumes its functionality, backup and remove. Otherwise adapt to use StructuralGraph.
- [ ] 5.5 Write `NavigationMapTest` (~5 tests: record, BFS pathfinding, no-path case, cycle handling) and `BacktrackStrategyTest` (~4 tests: BACK success, BACK failure + replay, broken replay, root screen).

## 6. ActionSelector Redesign

- [ ] 6.1 Replace 4-tier `selectAction()` with phase-based dispatch: receive `Phase` from PhaseController. Phase 1: return untested action in current content state (scored by existing chain). Phase 2: return action targeting UI coverage gap (use UICoverageTracker data). Phase 3: return softmax-selected action with boosted stochastic probability (0.5).
- [ ] 6.2 Remove Tier 1 (PathBuffer), Tier 3 (proactive backtrack at saturation >= 0.8), Tier 4 (unified queue). Keep Tier 2 logic as Phase 1 core. Keep existing scoring chain (MopScorer, GradualDecayScorer, SystemElementFilter, ComponentPriorityScorer, WtgScorer, CoverageDensityScorer, ConfirmedCoverageScorer).
- [ ] 6.3 Phase 1 navigation: when current content state exhausted, query ContentGraph for nearest content state with untested actions. Use BacktrackStrategy to navigate there.
- [ ] 6.4 Update `selectNextBest()` (retry logic) to work with phase-based selection.
- [ ] 6.5 Update trace observability: replace `lastSelectedTier` with `lastSelectedPhase`. Update score breakdown to include phase info.
- [ ] 6.6 Write `ActionSelectorPhase1Test`, `ActionSelectorPhase2Test`, `ActionSelectorPhase3Test`. ~6 tests total.

## 7. AgentLoop Integration

- [ ] 7.1 Update `runIteration()`: compute dual hash (contentHash + structHash). Register in ContentGraph and StructuralGraph. Pass phase to ActionSelector.
- [ ] 7.2 Wire PhaseController: initialize in constructor, call `currentPhase()` each iteration, notify on new content state discovery.
- [ ] 7.3 Wire NavigationMap: record structural transitions after each action with effect.
- [ ] 7.4 Wire BacktrackStrategy: replace PathBuffer BACK sequences with BacktrackStrategy calls. Connect to OOA recovery (RESTART + replay instead of just RESTART).
- [ ] 7.5 Update SuccessorTracker to operate on structHash instead of contentHash. Record parent-child at structural level.
- [ ] 7.6 Add content hash explosion safety valve: if ContentGraph exceeds 1000 nodes, log warning and degrade to structural hash only (contentHash = structHash).
- [ ] 7.7 Update constructors: replace DynamicStateGraph with ContentGraph + StructuralGraph + NavigationMap. Add PhaseController and BacktrackStrategy. Remove PathBuffer parameter.
- [ ] 7.8 Integration test: mock device, verify dual hash registration, phase transitions, NavigationMap population. ~3 tests.

## 8. Metrics + Trace

- [ ] 8.1 Extend `MetricsCollector`: add `content_states`, `structural_clusters`, `phase_distribution` (phase1/phase2/phase3 iteration counts), `nav_map_edges`, `backtrack_replays` fields. Wire counting in AgentLoop.
- [ ] 8.2 Verify RVSMART_METRICS JSON output is a strict superset of gh32 format (all existing fields preserved, new fields added).
- [ ] 8.3 Update TraceWriter score breakdown: add `phase` field to breakdown map.
- [ ] 8.4 Write `MetricsCollectorTest` and `TraceWriterTest` for new fields. ~4 tests.

## 9. Final Verification

- [ ] 9.1 Compile full project: `cd $RVSEC_HOME/rvsec-android/rvsmart && gradle build` (or equivalent). Fix any remaining compiler errors from the refactoring.
- [ ] 9.2 Run all unit tests. Fix failures.
- [ ] 9.3 Build rvsmart JAR and verify it can be pushed to emulator via rvsmart-tool.
- [ ] 9.4 Run a single smoke test: `uv run rv-experiment run --tools rvsmart --apks-dir ./apks_examples --timeout 60`. Verify trace output, metrics JSON, and that dual hash + phases are active in logs.
- [ ] 9.5 Rebuild Docker image if applicable.
