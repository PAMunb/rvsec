## Context

This redesign addresses three fundamental flaws in rvsmart's exploration algorithm identified by the comparison experiment (100 APKs x 3 reps x 600s). RVsmart loses to ape by 3.93pp and to rvagent by ~1pp in method coverage. The root causes are structural — not fixable with incremental patches.

The change preserves all fixes from gh30-gh32 (StaticMap, OOA recovery, WtgScorer, speed optimizations, resource management) and integrates with LLM capabilities from gh33 when available.

Relevant FRs: FR18 (plugin system), FR19 (external tools), FR26 (coverage-optimized DFS).
Relevant NFRs: NFR04 (resilience), NFR06 (observability).

### Current State

**Hash computation** (`ScreenState.computeHash()`): `Objects.hash(activity, dedupedSortedWidgetSignatures)` where each signature is `className|resourceID|interactMask`. Excludes text, checked state, selected state. CryptoApp Spinner="MD2" and Spinner="SHA-256" produce the same hash.

**Action selection** (`ActionSelector.selectAction()`): 4-tier system — Tier 1 (PathBuffer BACK sequence), Tier 2 (untested actions), Tier 3 (proactive backtrack at saturation >= 0.8), Tier 4 (unified queue with scoring). Between Tier 2 exhaustion and Tier 3 activation, agent wastes iterations in Tier 4 re-executing known actions.

**Backtracking**: BACK press via InputInjector. Unreliable — 65/100 APKs show >15% RESTART rate. No replay mechanism. PathBuffer plans BACK sequences but has no fallback.

**State graph** (`DynamicStateGraph`): single hash identity. `ScreenNode` tracks per-action execution counts and saturation. `SuccessorTracker` records parent-child relationships.

## Architecture

```
AgentLoop.run()
  ├── capture → ScreenState (produces contentHash + structHash)
  ├── register in ContentGraph (contentHash → ContentNode)
  │   └── register in StructuralGraph (structHash → cluster of contentHashes)
  ├── phase routing: PhaseController.currentPhase()
  │   ├── PHASE_1: DFS (untested actions per content state)
  │   ├── PHASE_2: coverage-guided (UI coverage gaps, value variations)
  │   └── PHASE_3: stochastic diversification (boosted randomness)
  ├── action selection: ActionSelector.selectAction(phase, screen, ...)
  ├── execute action
  ├── post-action capture → new contentHash + structHash
  ├── record transition in NavigationMap (structHash-level)
  └── learn + trace
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `ScreenState` | Compute dual hash from UI items | `List<ScreenItem>`, activity | contentHash, structHash |
| `ContentGraph` | Track content-hash states + per-action execution data | contentHash, activity | `ContentNode` (replaces `ScreenNode`) |
| `StructuralGraph` | Cluster content states by structural identity | structHash, contentHash | structHash → Set<contentHash> |
| `NavigationMap` | Record structural-level transitions for replay | (fromStruct, action, toStruct) | path: List<Action> |
| `PhaseController` | Determine current exploration phase | ContentGraph state, UI coverage | PHASE_1/2/3 |
| `ActionSelector` | Select action based on current phase | phase, screen, graphs | Action (never null) |
| `BacktrackStrategy` | Reliable backtracking: BACK first, replay fallback | target structHash, NavigationMap | Action or Action sequence |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Dual hash identity | `ScreenState.computeContentHash()`, `computeStructHash()` | `ScreenStateHashTest` |
| Phase 1 DFS | `ActionSelector` untested-in-content-state | `ActionSelectorPhase1Test` |
| Phase 2 coverage-guided | `PhaseController.selectPhase2Action()` | `PhaseControllerTest` |
| Phase 3 stochastic | Existing softmax with boosted probability | `ActionSelectorStochasticTest` |
| Navigation map recording | `NavigationMap.record()` | `NavigationMapTest` |
| Replay backtracking | `BacktrackStrategy.planReplay()` | `BacktrackStrategyTest` |
| Phase transitions | `PhaseController.currentPhase()` | `PhaseControllerTransitionTest` |
| Metrics output | `MetricsCollector` extended fields | `MetricsCollectorTest` |
| INV-TOOL-TRACE-01 | TraceWriter format preserved | Regression tests |
| INV-TOOL-METRICS-01 | RVSMART_METRICS superset | `MetricsOutputTest` |

## Goals / Non-Goals

**Goals:**
- Replace single structural hash with dual hash (content-aware + structural)
- Replace 4-tier action selection with 3-phase exploration
- Add structural navigation graph with replay-based backtracking
- Preserve all gh30-gh32 fixes and gh33 LLM integration
- Maintain trace output compatibility (RVTRACK format, RVSMART_METRICS superset)

**Non-Goals:**
- CEGAR-style dynamic abstraction refinement (complexity not justified yet — dual hash is the pragmatic step)
- Changes to the rvsmart-tool Python wrapper (external interface unchanged)
- Changes to rv-platform, rv-experiment, or rv-tools modules
- Modifying the scoring chain (MopScorer, WtgScorer, etc.) — scorers work as-is with the new phase system
- Changes to `RoutingManager` — it controls LLM vs. algorithm routing (orthogonal concern). The 3-phase exploration is entirely within the algorithm path. When RoutingManager routes to LLM, the LLM makes a free-form decision regardless of phase. RoutingManager is unchanged.

## Decisions

### D1: Content Hash Composition

**Content hash** includes fields that distinguish semantically different states:
- Activity name
- Per-widget: className, resourceID, **text** (≤ 50 chars, trimmed), **enabled**, **checked**, **selected**
- **Exclusion**: EditText content is excluded (agent-generated text causes infinite state explosion)
- **Exclusion**: Coordinates and index excluded (position changes between devices)
- Deduplication: same as current (LinkedHashSet), sort, Objects.hash()

**Structural hash** retains the current computation: `className|resourceID|interactMask` — unchanged from gh30.

**Why text ≤ 50 chars**: Prevents long dynamic content (log output, WebView text) from creating false state distinctions. Spinner labels, button text, and checkbox labels are typically short. The 50-char limit matches droidbot's approach.

**Why exclude EditText**: The agent generates its own text input via InputValueGenerator. Including agent-generated text would create a new state on every SET_TEXT, causing infinite Phase 1 loops. This is the same rationale droidbot uses.

**Alternative considered**: CEGAR (ape's approach) — dynamically discovers which fields matter. More precise but significantly more complex. Dual hash provides 80% of the benefit with 20% of the complexity.

### D2: 3-Phase Exploration (replaces 4-tier system)

| Phase | Trigger | Behavior | Exit |
|-------|---------|----------|------|
| **Phase 1 — DFS** | Default (start of exploration + each new content state) | Test untested actions in current content state. Navigate to nearest content state with untested actions when current state exhausted. | No reachable content state with untested actions |
| **Phase 2 — Coverage-Guided** | Phase 1 exhausted (all content states fully explored once) | Re-explore states with UI coverage gaps. Try value variations (different SET_TEXT inputs, trigger state changes that create new content hashes). Navigate toward uncovered activities via NavigationMap. | UI coverage plateau (no new coverage for N iterations) |
| **Phase 3 — Stochastic** | Phase 2 plateau | Boost stochastic probability to 0.5. Random exploration with softmax-weighted scoring. May discover new content states (→ re-enter Phase 1). | Timeout only |

**Phase transitions are reversible**: discovering a new content state at any phase re-activates Phase 1 for that state. PhaseController tracks global phase but always checks for local Phase 1 opportunities.

**Relationship to existing code**: Phase 1 corresponds to current Tier 2 + navigation. Phase 2 integrates with PlateauDetector (for phase transition detection) and UICoverageTracker (for coverage gap identification) — both classes remain, no deletion. Phase 3 reuses the existing stochastic selection with a boosted probability. Tier 1 (PathBuffer) is replaced by BacktrackStrategy. Tier 3 (proactive backtrack at saturation) is replaced by NavigationMap-based navigation. Tier 4 (unified queue) is eliminated — its iterations become productive Phase 2/3 iterations.

**Phase 1 navigation**: When the current content state is exhausted, Phase 1 navigates to the nearest structural cluster that contains a discovered content state with untested actions. Navigation uses BacktrackStrategy (structural-level BACK + replay). Upon arriving at the structural cluster, the agent gets some content state within that cluster; DFS continues from whatever content state is found there, testing its untested actions. This is sufficient — content states within the same structural cluster are reachable from each other by executing the actions that differentiate them (e.g., selecting a different Spinner option), which are themselves untested Phase 1 candidates. "Nearest" is defined as minimum structural-level BFS hops via NavigationMap from the current structHash.

**Why not keep tiers**: The Tier 4 trap (28.3% wasted iterations) is a direct consequence of the tiered architecture. Phases eliminate the gap because Phase 2 always has productive work (coverage gaps, value variations), and Phase 3 uses stochasticity to discover new states.

### D3: Structural Navigation Map + Replay Backtracking

**NavigationMap** records `(fromStructHash, actionSignature) → toStructHash` for every action that causes a structural transition. This creates a directed graph at the structural level (coarser than content, more stable for navigation).

**BacktrackStrategy** replaces PathBuffer with a two-stage approach:
1. **Try BACK** (fast, 1-2s): Press BACK, check result. If reached a known structural state, done.
2. **Replay fallback** (5-8s): If BACK fails (OOA, unexpected state), RESTART + replay shortest action sequence via NavigationMap BFS to reach the target structural cluster.

**Why structural-level navigation**: Content hashes change with widget state (Spinner selection, checkbox toggle). Navigation paths are more stable at the structural level — "Main screen" is always structurally the same regardless of which Spinner option is selected. The NavigationMap records how to reach structural clusters, not specific content states.

**Why replace PathBuffer**: PathBuffer only plans BACK sequences and has no recovery mechanism. When BACK fails mid-path, the entire path is invalidated. NavigationMap can replay any recorded path, using structural identity to verify each step.

### D4: ContentGraph replaces DynamicStateGraph + ScreenNode

Current `DynamicStateGraph` maps `hash → ScreenNode`. The redesign replaces this with:

- **ContentGraph**: maps `contentHash → ContentNode` (action execution tracking, visit counts, saturation — same role as ScreenNode but keyed by content hash)
- **StructuralGraph**: maps `structHash → Set<contentHash>` (clustering)
- **NavigationMap**: maps `(structHash, actionSig) → structHash` (transitions)

`ContentNode` is a renamed `ScreenNode` with the same fields. The only behavioral change is that the same structural screen with different content creates multiple ContentNodes.

**Why not modify ScreenNode in place**: ScreenNode is keyed by the old single hash. Adding dual hashing to the existing structure would require changing every callsite that references `screenHash`. Renaming to ContentNode and introducing StructuralGraph as a separate structure is simpler (P1).

### D5: Files to Delete, Backup, and Create

**Delete (move to backup/):**
- `graph/DynamicStateGraph.java` — replaced by ContentGraph + StructuralGraph
- `strategy/PathBuffer.java` — replaced by BacktrackStrategy using NavigationMap

**Rename:**
- `graph/ScreenNode.java` → `graph/ContentNode.java` (same fields, new name reflecting content hash identity)

**Create:**
- `graph/ContentGraph.java` — replaces DynamicStateGraph, keyed by contentHash
- `graph/StructuralGraph.java` — structural clustering
- `graph/NavigationMap.java` — structural transition recording + BFS path finding
- `strategy/PhaseController.java` — phase state machine (PHASE_1/2/3 transitions)
- `strategy/BacktrackStrategy.java` — BACK + replay fallback

**Modify:**
- `core/ScreenState.java` — add `computeContentHash()`, keep `computeStructHash()` (current logic renamed)
- `core/AgentLoop.java` — dual hash registration, phase-based routing, NavigationMap recording
- `core/Config.java` — remove the 4 PathBuffer config params (`path_buffer_strategy_priority`, `path_buffer_backtrack_hops`, `path_buffer_coverage_weight`, `path_buffer_mop_weight`) that become dead when PathBuffer is backed up
- `strategy/ActionSelector.java` — phase-aware action selection (replace tiers with phase dispatch)
- `output/MetricsCollector.java` — extended metrics fields
- `output/TraceWriter.java` — optional new fields in score breakdown
- `output/RvTrack.java` — migrate from `Log.i()` (logcat) to `System.out.println()` (stdout). RvTrack was designed to emit structured `[RVTRACK:<CATEGORY>]` lines to the trace captured by rvsmart-tool, but was implemented using Android logcat. This change fixes the design intent: all structured trace data (TraceWriter JSON + RvTrack diagnostic lines) goes to stdout, captured by the Python wrapper. Remove `import android.util.Log` and `TAG` constant; the `logEnabled` flag is kept for test suppression. The trace file will have two line types: JSON lines (TraceWriter) and `[RVTRACK:]` text lines, both distinguishable by prefix.
- `llm/PromptBuilder.java` — remove 2 `Log.d("RVSMART-PROMPT", ...)` calls (V13 and V17 templates). LLM prompt text is debug-only and not needed in production trace; relevant LLM data (tokens, timing) is already in MetricsCollector.
- `llm/ToolCallParser.java` — remove `Log.d("RVSMART-LLM-RESP", rawContent)` call. Same rationale as RVSMART-PROMPT.
- `recovery/BacktrackBfs.java` — **keep and adapt**: BacktrackBfs finds unsaturated ancestors via BFS on SuccessorTracker parent-child relationships (used by stuck detection), while BacktrackStrategy provides BACK+replay navigation fallback. They serve different purposes and coexist. Since Task 7.5 makes SuccessorTracker operate at structHash level, BacktrackBfs operates naturally on structHashes — no logic change, just type-level consistency.

**Unchanged (preserved from gh30-gh32):**
- All scorers (`strategy/scorers/*`) — work as-is, receive ContentNode data through same interface
- `core/UICoverageTracker.java` — used by Phase 2 for coverage gap detection
- `strategy/PlateauDetector.java` — integrated into PhaseController for phase transition decisions
- `strategy/SuccessorTracker.java` — adapted to use structHash for parent/child relationships
- `strategy/InputValueGenerator.java` — used in Phase 2 for value variations
- `recovery/StuckDetector.java` — unchanged, works with contentHash
- `staticdata/StaticMap.java` — unchanged, scorers access it through same interface
- All `device/*` classes — unchanged
- All `llm/*` classes — unchanged, LLM integration from gh33 works as-is
- All `output/*` classes except MetricsCollector and TraceWriter — unchanged

## Data Flow

```
1. UiCapture.capture(root) → List<ScreenItem>
2. ScreenState(items, activity) → contentHash + structHash
3. ContentGraph.getOrCreate(contentHash) → ContentNode
4. StructuralGraph.register(structHash, contentHash) → cluster update
5. PhaseController.currentPhase(contentGraph, uiCoverageTracker) → PHASE_1/2/3
6. ActionSelector.selectAction(phase, screen, contentGraph, ...) → Action
7. InputInjector.execute(action)
8. Post-action: ScreenState(newItems, newActivity) → newContentHash + newStructHash
9. NavigationMap.record(structHash, action.signature(), newStructHash)
10. ContentNode.recordAction(signature, widgetClass)
11. ContentNode.recordActionSuccess(signature, hadEffect)
12. SuccessorTracker.record(structHash, newStructHash)  // structural level
13. Learner.update(action, hadEffect, ...)
14. TraceWriter.writeLine(...)
```

**Key difference from current flow**: Steps 2-5 are new (dual hash, phase routing). Step 9 records structural transitions. Step 12 now operates at structural level instead of content level.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| BACK fails (OOA) | BacktrackStrategy step 1 | Detected by OOA check in AgentLoop | RESTART + replay via NavigationMap |
| Replay path broken | NavigationMap BFS returns path, but intermediate state changed | Verify each step matches expected structHash | Abandon replay, RESTART to root, re-navigate |
| Content hash explosion | App generates infinite distinct content (e.g., timestamp in TextView) | 50-char text limit + EditText exclusion | If ContentGraph exceeds 1000 nodes, degrade to structural hash only |
| Phase 1 infinite loop | New content state → Phase 1 → action creates another new state → ... | PhaseController tracks Phase 1 entries per structHash cluster | After 20 Phase 1 re-entries in same cluster, force Phase 2 for that cluster. This fires before the global 1000-node safety valve (which triggers later). After forcing Phase 2, the cluster is explored with coverage-guided approach instead of DFS. |
| NavigationMap stale | App state changed externally (notification, background process) | Structural hash verification at each replay step | Abort replay, fall back to BACK or RESTART |

## Risks / Trade-offs

**[Content hash creates too many states]** → The 50-char text limit and EditText exclusion prevent explosion. Safety valve: degrade to structural hash if ContentGraph exceeds 1000 nodes. Monitoring via metrics (`content_states` field).

**[Replay backtracking is slow (5-8s)]** → Only triggered when BACK fails. For the 65% of APKs with BACK reliability issues, 5-8s replay is still faster than the OOA → RESTART → re-explore cycle (15-30s). Net gain even in worst case.

**[Phase transitions add complexity]** → PhaseController is a simple state machine with 3 states. The current 4-tier system + PlateauDetector + UICoverageTracker + SuccessorTracker re-enabling is more complex. Net simplification.

**[Breaking change: DynamicStateGraph removed]** → All callers updated in the same change. No backward-compatibility shims (P3). Backup to `backup/` before deletion.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | Content hash vs structural hash computation | Fixed ScreenItem lists with varying text/checked | ~8 tests |
| Unit | PhaseController state transitions | Mock ContentGraph + UICoverageTracker | ~6 tests |
| Unit | NavigationMap BFS path finding | Build graph manually, verify paths | ~5 tests |
| Unit | BacktrackStrategy BACK+replay logic | Mock NavigationMap, simulate BACK failures | ~4 tests |
| Unit | ActionSelector phase-based dispatch | Verify Phase 1 returns untested, Phase 2 uses coverage, Phase 3 boosts stochastic | ~6 tests |
| Unit | ContentNode (renamed ScreenNode) | Same tests as existing ScreenNodeTest, verify rename | ~4 tests |
| Integration | AgentLoop with dual hash + phases | Mock device, verify content/structural graph population | ~3 tests |
| Regression | Trace output format compatibility | Parse RVTRACK lines, verify same fields present | ~2 tests |
| Regression | Metrics JSON superset | Parse RVSMART_METRICS, verify gh32 fields + new fields | ~2 tests |

Total: ~40 tests.

## Resolved Design Questions

1. **Content hash text exclusion for dynamic views**: Exclude text from `EditText` only (agent-generated input). For all other widgets, include text ≤ 50 chars. Dynamic TextViews (clocks, counters) typically exceed 50 chars or contain digits that are filtered at the trim level. The `content_states` metric monitors for unexpected explosion. If explosion occurs (ContentGraph > 1000 nodes safety valve), the system degrades to structural hash — making this self-correcting without upfront complexity.

2. **NavigationMap memory**: No cap needed. At 14 evt/s over 600s = ~8400 actions, structural transitions are bounded by `unique_struct_states × actions_per_screen`. Android apps typically have 20–100 structural screens with 10–50 actions each = at most ~5000 map entries (~1MB). This is negligible. No memory management code needed (P1).

3. **Phase 2 re-exploration heuristic**: Use `UICoverageTracker.getCoverageGap()` (already implemented) to identify screens with uninteracted elements (coverage gap > `config.uiCoverageThreshold`, default 0.3). Navigate to the highest-gap screen via NavigationMap, breaking ties by MOP reachability score from WtgScorer. This reuses existing infrastructure with no new heuristics.
