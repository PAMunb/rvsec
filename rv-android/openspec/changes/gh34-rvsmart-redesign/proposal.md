## Why

GitHub Issue: #34

The comparison experiment (100 APKs x 3 reps x 600s) showed rvsmart losing to ape by 3.93pp and to rvagent by ~1pp in method coverage. A deep architectural analysis identified three fundamental design flaws in rvsmart's exploration algorithm that cannot be addressed with incremental patches:

1. **Single structural hash collapses semantic states**: `className|resourceID|interactMask` treats content-different screens (e.g., CryptoApp Spinner="MD2" vs "SHA-256") as the same state, preventing combinatorial testing of interactive forms.
2. **BACK-dependent backtracking is unreliable**: 65/100 APKs show >15% RESTART rate. BACK closes apps, navigates unpredictably, or does nothing — causing a vicious cycle of OOA -> RESTART -> root -> re-explore.
3. **Tier 4 trap wastes 28.3% of iterations**: Between Tier 2 (untested actions) and Tier 3 (saturation >= 0.8), the agent re-executes known actions without progress.

Previous changes (gh30-gh32) fixed critical bugs but within the existing architecture. This change redesigns the core exploration algorithm to eliminate these structural problems while preserving all fixes.

## What Changes

- **BREAKING**: Replace single structural hash with dual hash system — content-aware hash (activity, class, resourceID, text <= 50 chars, enabled, checked, selected) for exploration identity + structural hash (activity, class, resourceID) for navigation clustering. Two parallel graph structures replace the single `ScreenNode` graph.
- **BREAKING**: Replace 4-tier action selection with 3-phase exploration — Phase 1 DFS (untested actions per content state), Phase 2 coverage-guided deepening (UI coverage gaps, value variations), Phase 3 stochastic diversification (boosted randomness at plateau).
- Add structural navigation graph (`nav_map`): record `(from_struct, action) -> to_struct` transitions. When BACK fails, RESTART + replay known action sequence via structural graph to reach target state.
- Content hash naturally enables combinatorial testing — each Spinner selection, CheckBox toggle, or RadioButton change creates a new content state, activating Phase 1 DFS exploration without explicit combinatorial logic.
- LLM integration via existing gh33 RoutingManager is passive: when RoutingManager routes a decision to the LLM, the LLM makes a free-form action choice that operates alongside the phase system. No changes to RoutingManager — the 3-phase exploration is entirely within the algorithm path.
- Preserve all gh30-gh32 fixes: StaticMap/MopScorer (gh30, gh32), WtgScorer BFS (gh31), OOA recovery with forceStop (gh32), UICoverageTracker (gh31-gh32), PlateauDetector (gh31), InputValueGenerator (gh31), softmax selection (gh31), ANI recycling (gh32), empty screen strategy (gh32), speed optimizations (gh30).

## Capabilities

### New Capabilities

None. The changes are internal to rvsmart's Java exploration algorithm.

### Modified Capabilities

- `tools`: RVSmartTool execution contract remains the same (push JAR, run via app_process, capture trace). The Java agent's internal exploration algorithm changes, but CLI args and trace output format are preserved. The metrics JSON gains new observability fields (backward-compatible superset of gh32 schema: `content_states`, `structural_clusters`, `phase_distribution`, `nav_map_edges`, `backtrack_replays`). The tools spec is updated with new invariants and scenarios for these additions.

## Impact

- **rvsmart Java codebase** (`$RVSEC_HOME/rvsec/rvsec-android/rvsmart/`): Core algorithm rewrite — `ScreenNode`, `ActionSelector`, `AgentLoop`, `PathBuffer`, `StuckDetector`. New classes for dual hash computation and navigation graph.
- **rvsmart-tool** (`modules/rvsmart-tool/`): No changes expected — Python wrapper interface unchanged.
- **rv-tools** (`modules/rv-tools/`): No changes — `RVSmartTool` registration and execution contract unchanged.
- **Relevant FRs**: FR18 (plugin system), FR19 (external tool support), FR26 (coverage-optimized DFS — rvsmart analog).
- **Relevant NFRs**: NFR04 (resilience — backtracking reliability), NFR06 (observability — trace output preserved).
- **Docker images**: Need rebuild after Java changes (`modules/rvsmart-tool/Dockerfile` or equivalent).
- **No cross-module dependency changes**: The change is entirely within the rvsmart Java agent boundaries.
