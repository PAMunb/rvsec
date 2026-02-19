# Design: Exploration Strategy Improvements

**GitHub Issue**: #26
**Proposal**: `openspec/changes/gh26-exploration-strategy/proposal.md`
**Analysis**: `docs/20260216_rvagent_refatoracao.md`

## Context

rv-agent's exploration strategy (`RVAgentStrategy`) selects one action per iteration using a scorer-ranked list of untested actions, falling back to least-executed actions when all have been tested at least once. This approach has five architectural bottlenecks that calibration alone cannot fix:

1. **Passive backtracking**: When all actions in a state are tested, the strategy enters "continuous mode" -- re-executing the least-tested action instead of navigating BACK to explore other states. The existing `should_backtrack()` method and `state_stack` are maintained but never called for navigation decisions. This wastes an estimated 20-40% of the iteration budget in saturated states, because the agent only leaves via stuck detection (8+ unchanged iterations) or Level 2 recovery.

2. **Scorer weight imbalance**: WTG score (+250) is nearly equal to MOP-direct (+300) and higher than MOP-transitive (+150). A non-MOP action leading to an unvisited screen outscores a MOP-transitive action. This causes the agent to prefer general screen exploration over paths to monitored operations.

3. **No adaptive learning**: Scorer weights are fixed throughout the experiment. An action that consistently fails to produce new states receives the same MOP/WTG score as one that leads to productive exploration. Neither APE-style model refinement nor Fastbot-style Q-value convergence exists.

4. **Text input bugs**: The `InputValueGenerator` has six bugs that waste 20-40% of text input iterations: duplicate input type inference (shallow `_infer_input_type()` in strategy ignores hint/content_description data), wrong default value ordering (PINs as first values for non-PIN fields), LLM path bypassing the generator entirely, `max_variations=3` blocking MOP edge cases (config default is 3, overriding InputValueGenerator's local default of 5; only 3 of 11 payloads tested), missing input types (search, url, date, time, number, zip, verification_code), and no clear-before-type causing text to append to existing field content.

5. **Speed gap**: In `pure_algorithm` mode, rv-agent executes ~150-300 iterations in 300 seconds. Skipping unnecessary screenshot capture and LLM nodes in algorithm-routed iterations can push throughput toward ~300+ iterations.

These issues affect FR26 (Coverage-Optimized DFS Strategy), FR27 (Composite Action Ranking), FR24 (Vision-Based Exploration), FR29 (Stuck State Detection and Recovery), and FR30 (WTG-Guided Navigation). The improvements described here give the downstream calibration campaign (gh9) a sound architectural foundation to optimize.

**Pre-condition**: gh18 (error detection) must be implemented first. This design assumes gh18's `VisualErrorDetector`, `force_fill_input` spatial association in `algorithm_node`, and conditional screenshot capture in `parse_node` already exist.

## Architecture

### Component Interaction Diagram

```
RVAgent.run() → External Loop → LangGraph Workflow (one iteration)
  │
  parse_node ──→ decision_router_node
  │                   │
  │    ┌──────────────┼──────────────┐
  │    ▼              ▼              ▼
  │  algorithm_node  llm_path      end
  │    │
  │    ▼
  │  strategy.select_next_action()
  │    │
  │    ├── Tier 1: PathBuffer.get_next_action() ──→ if buffered path, return action
  │    ├── Tier 2: _get_untested_actions() ──→ ActionRanker.score_action()
  │    │       │                              │
  │    │       │                    ┌─────────┼─────────────────┐
  │    │       │                    ▼         ▼                 ▼
  │    │       │              MopScorer  WtgScorer  GradualDecayScorer
  │    │       │              (+500/+300) (+150)     (200*0.7^visits)
  │    │       │                    │                        │
  │    │       │                    ▼                        ▼
  │    │       │              CoverageDensityScorer (200*coverage_gap)
  │    │       │              [always active, queries SuccessorTracker+UICoverage]
  │    │       │                    │         │                 │
  │    │       │                    ▼         ▼                 ▼
  │    │       │              StrengthScorer (+ cumulative_reward)
  │    │       │              [reward from RewardPropagator]
  │    │       │
  │    ├── Tier 3: should_backtrack(saturation_threshold) ──→ plan path or fall through
  │    │     └── PathBuffer: plan_coverage_path() > plan_mop_path() > plan_backtrack_path()
  │    ├── Tier 4: ActionRanker.rank_actions(all_actions) (scored continuous mode)
  │    └── Tier 5: BACK (final fallback)
  │
  │  ──→ validation_node ──→ execute_node ──→ learn_node
  │                                              │
  │                                    RewardPropagator.propagate()
  │                                    (backward N-step through action history)
  │                                              │
  │                                    ScreenNode.action_cumulative_reward updated
```

### Key Components

| Component | Responsibility | Location | Status |
|-----------|---------------|----------|--------|
| `RVAgentStrategy.select_next_action()` | New 5-tier action selection flow | `strategies/rvagent_strategy/rvagent_strategy.py` | Modified |
| `PathBuffer` | Multi-step navigation path management | `strategies/rvagent_strategy/path_buffer.py` | New |
| `RewardPropagator` | N-step backward reward propagation | `strategies/rvagent_strategy/reward_propagator.py` | New |
| `ActionRanker` | Composite scoring with rebalanced weights + GradualDecayScorer | `strategies/rvagent_strategy/ranking/action_ranker.py` | Modified |
| `StrengthScorer` | Historical success rate + cumulative reward | `strategies/rvagent_strategy/ranking/scorers.py` | Modified |
| `InputValueGenerator` | Text value generation with bug fixes | `strategies/rvagent_strategy/input_value_generator.py` | Modified |
| `TransitionManager` | Gains BFS path planning to MOP-dense Activities | `services/transition_manager.py` | Modified |
| `NavigationGuidance` | MOP-specific LLM prompt enrichment | `services/navigation_guidance.py` | Modified |
| `CoverageDensityScorer` | Cross-screen coverage guidance using learned transitions | `strategies/rvagent_strategy/ranking/scorers.py` | New |
| `RankingContext.successor_tracker`, `RankingContext.has_untested_inputs` | SuccessorTracker reference for CoverageDensityScorer destination lookups; `has_untested_inputs` flag for MopScorer form-context deferral (INV-AGT-39) | `strategies/rvagent_strategy/ranking/context.py` | Modified |
| `RVAgentConfig` | 6 new calibration parameters + 5 module-level constants | `config/agent_config.py` | Modified |
| `ScreenNode` | New `action_cumulative_reward: Dict[Tuple[Tuple[int,int], str], float]` field (same key type as `action_execution_counts`) | `domain/screen_node.py` | Modified |
| `SuccessorTracker.find_nearest_unsaturated()` | Return type change: `Optional[str]` → `Optional[Tuple[str, int]]` (ancestor_hash, bfs_hop_count) | `strategies/rvagent_strategy/successor_tracker.py` | Modified |
| `AgentFactory` | Modified to instantiate and wire `PathBuffer(transition_manager, successor_tracker, ui_coverage_tracker, config)` and `RewardPropagator(config)` into `RVAgentStrategy` during agent construction | `agent/agent_factory.py` | Modified |
| `RVAgent._build_agent_graph()` | No topology change needed — algorithm path already bypasses screenshot/LLM nodes via existing conditional edges | `agent/rv_agent.py` | Unchanged |
| `RVAgent.run()` | FileHandler for RVTRACK `.trace` file: attach after app launch, remove before return. Reuses `metrics_output_dir` | `agent/rv_agent.py` | Modified |
| `decision_router_node` | Mode-aware routing (existing); add tracking log for algorithm-fast-path | `agent/nodes/decision_node.py` | Modified |
| `learn_node` | Reward propagation trigger after action success recording | `agent/nodes/learn_node.py` | Modified |

### Navigation Component Architecture

The navigation/graph system consists of five components in a layered architecture. Understanding their relationships is essential for gh26 implementation because the new features (PathBuffer, CoverageDensityScorer, RewardPropagator) interact with multiple layers.

```
                    RVAgentStrategy (orchestrator)
                   /       |        \
          SuccessorTracker  |  TransitionManager
           (dynamic edges)  |   (static WTG edges)
                   \       |        /
                  DynamicStateGraph
                   (state lifecycle)
                        |
                    ScreenNode
                   (pure data model)
```

| Component | Core Data | Decision Role |
|-----------|-----------|---------------|
| **ScreenNode** | Per-action execution/success counts, failures, saturation, `action_cumulative_reward` (gh26) | Scorer inputs, saturation checks |
| **DynamicStateGraph** | `states: Dict[hash, ScreenNode]` + `transitions: List[Transition]` | States: used for decisions. Transitions: **audit-only** (chronological log for post-run reporting, never queried for navigation) |
| **SuccessorTracker** | `successors: Dict[(hash, action_sig) → hash]` + `back_successors: Dict[hash → Set[hash]]` | O(1) navigation lookups: re-enabling, BFS, CoverageDensityScorer destination queries |
| **TransitionManager** | WTG static graph, `_visited_activities` (single source of truth), activity↔window_id mapping | WTG scoring, path planning (Strategy B), navigation guidance |
| **PathBuffer** (gh26) | Transient buffered actions (consumed step-by-step, then empty) | Tier 1 action selection; no parallel graph structure |

**Key distinction — DynamicStateGraph.transitions vs SuccessorTracker.successors**: Both store edge data written by `RVAgentStrategy.record_transition()`, but in different structures for different query patterns. `transitions` is a `List[Transition]` preserving chronological order and full action dicts — used only for post-run analysis/reports. `successors` is a `Dict[(from_hash, action_sig) → to_hash]` — used for all runtime navigation decisions (re-enabling, BFS pathfinding, `get_action_destination()` for CoverageDensityScorer). This dual storage is intentional: the list preserves context for analysis while the dict enables O(1) navigation lookups.

**Dead code removed in gh26**: `state_stack` (append-only, never popped — navigation distance determined by SuccessorTracker BFS), `RVAgentState` dataclass (only used as state_stack entries), `parent_hash` (stored but never read), `visited_states` Set (identical to `graph.states.keys()` — redundant), `ExecutionCountScorer` (defined in `scorers.py` but never registered — dead code similar to pre-gh26 `GradualDecayScorer`, but unlike GradualDecayScorer it is not being activated; removing it keeps the scorer list clean per P3). See Decision D6.

## Mapping: Spec → Implementation → Test

| Requirement / Change | FR | Implementation Files | Test Files |
|---|---|---|---|
| Proactive backtracking (new action selection order) | FR26 | `rvagent_strategy.py` (select_next_action) | `test_proactive_backtracking.py`, `test_should_backtrack.py` |
| PathBuffer integration | FR26, FR30 | `path_buffer.py` (new), `rvagent_strategy.py` | `test_path_buffer.py`, `test_strategy_path_buffer_integration.py` |
| Saturation threshold | FR26 | `rvagent_strategy.py`, `agent_config.py` | `test_saturation_threshold.py` |
| Scorer rebalancing (new defaults) | FR27 | `agent_config.py` (default values) | `test_scorer_weights.py` |
| MopScorer form-context deferral | FR27 | `scorers.py` (MopScorer.score), `context.py` (has_untested_inputs), `rvagent_strategy.py` (Tier 2/4 context) | `test_mop_scorer_deferral.py` |
| GradualDecayScorer activation | FR27 | `rvagent_strategy.py` (__init__ scorer list) | `test_gradual_decay_scorer.py` |
| N-step reward propagation | FR27 | `reward_propagator.py` (new), `learn_node.py`, `scorers.py` (StrengthScorer), `screen_node.py` | `test_reward_propagator.py`, `test_strength_scorer_reward.py` |
| Speed optimization (parse_node caching) | FR24 | `parse_node.py`, `decision_node.py` (tracking only) | `test_speed_optimization.py` |
| LLM MOP guidance | FR24, FR30 | `navigation_guidance.py`, `prompts/v17.py` (new — v16 already exists) | `test_mop_guidance.py` |
| Text input quality (6 bug fixes) | FR26 | `input_value_generator.py`, `rvagent_strategy.py`, `execution/tool_executor.py` | `test_input_value_generator.py` |
| BFS path planning to MOP Activities | FR30 | `transition_manager.py` | `test_transition_manager_bfs.py` |
| SuccessorTracker return type change | FR26 | `successor_tracker.py` (find_nearest_unsaturated returns Tuple[str, int]) | `test_find_nearest_unsaturated_hop_count.py` |
| Reduced stuck trigger frequency | FR29 | (indirect -- proactive backtracking leaves saturated states earlier) | `test_stuck_detection_with_backtracking.py` |
| CoverageDensityScorer (cross-screen coverage) | FR27 | `scorers.py` (CoverageDensityScorer), `rvagent_strategy.py` (registration) | `test_coverage_density_scorer.py` |
| PathBuffer Strategy C (coverage navigation) | FR26 | `path_buffer.py` (plan_coverage_path), `rvagent_strategy.py` (Tier 3) | `test_path_buffer_coverage.py` |
| New config parameters (6 fields + 5 constants) | -- | `agent_config.py`, `path_buffer.py`, `reward_propagator.py` | `test_config_new_params.py` |
| Dead code removal: state_stack, RVAgentState, parent_hash, visited_states | P3 | `rvagent_strategy.py` | `test_dead_code_removal.py` |
| Consolidate visited_activities tracking | P3 | `rvagent_strategy.py`, `transition_manager.py` | existing strategy + transition_manager tests |
| Delegate coverage formula to ScreenNode | P1 | `successor_tracker.py` | existing successor_tracker tests |
| Document DynamicStateGraph.transitions as audit-only | P2 | `dynamic_state_graph.py` | (documentation only) |

## Goals / Non-Goals

**Goals:**

- Fix passive backtracking by introducing proactive BACK when saturation threshold is exceeded, recovering ~20-40% of wasted iterations
- Rebalance scorer weights so MOP-direct (+500) > MOP-transitive (+300) > WTG (+150), ensuring the agent prioritizes monitored operation paths. Also reduce the existing `stochastic_probability` config field from 0.3 to 0.15 — this parameter controls the probability that `ActionRanker` selects a random action via Gumbel-max sampling instead of the highest-scored one; reducing it makes the agent follow the scorer ranking more deterministically, which is important now that the rebalanced weights carry stronger MOP-directed signal
- Fix six text input bugs in `InputValueGenerator` to stop wasting iterations on PINs in non-PIN fields and enable all 11 MOP edge-case payloads
- Add `PathBuffer` for multi-step navigation paths (backtrack to unsaturated ancestor, navigate to MOP-dense Activity via BFS)
- Add `RewardPropagator` for simplified N-step reward propagation through action chains, extending `StrengthScorer` with cumulative reward data
- Optimize speed in `pure_algorithm` iterations by skipping screenshot capture and LLM nodes (per-iteration decision, mode-aware)
- Activate `GradualDecayScorer` for smoother action priority transitions
- Add `CoverageDensityScorer` (always-active, weight=200) for cross-screen coverage guidance using learned transitions from `SuccessorTracker` and `UICoverageTracker`, addressing the "small island" problem where MOP methods represent only 1-5% of app code
- Add PathBuffer Strategy C for coverage-based BFS navigation on learned transitions toward screens with highest exploration potential (`coverage_gap * element_count`), positioned before Strategy B (C > B > A ordering) to prioritize broad UI coverage
- Enrich LLM prompts with MOP-specific guidance from static analysis
- Add 6 new calibration parameters to `RVAgentConfig` for downstream gh9 tuning (`backtrack_saturation_threshold`, `mop_nav_weight`, `mop_max_input_variations`, `reward_gamma`, `reward_score_weight`, `coverage_density_weight`). Five additional values use module-level constants (not calibratable): `PATH_BUFFER_ENABLED` (True), `MAX_BACKTRACK_HOPS` (8), `REWARD_PROPAGATION_N` (5), `REWARD_MOP_WEIGHT` (5.0), `MAX_COVERAGE_HOPS` (5). Constants were separated from configurable params because: `reward_score_weight` already controls reward influence (calibrating `reward_mop_weight` too creates redundancy), `reward_propagation_n` has negligible impact beyond 5 (gamma^5 = 0.33), `max_backtrack_hops` and `max_coverage_hops` are safety bounds not performance knobs, and `path_buffer_enabled` is a toggle with no benefit since strategies already return False when conditions aren't met
- Remove dead code before implementing new features (P3): `state_stack` (append-only, never popped), `RVAgentState` dataclass (only used as stack entries), `parent_hash` (stored but never read), `visited_states` Set (redundant with `graph.states.keys()`). Consolidate `visited_activities` tracking to a single source of truth (`TransitionManager`), delegate coverage formula in `SuccessorTracker` to `ScreenNode.get_coverage()`, and document `DynamicStateGraph.transitions` as audit-only

**Non-Goals:**

- **State abstraction refinement** (APE-style CEGAR over/under-abstraction detection) -- requires fundamental changes to `DynamicStateGraph` hashing, out of scope
- **Full reinforcement learning** (Fastbot-style full SARSA with Q-table, learning rate schedule, epsilon-greedy) -- violates P1 Simplicity; the simplified N-step reward propagation captures ~80% of the benefit at ~10% of the complexity
- **Model persistence between runs** -- Fastbot persists models to disk for reuse across runs; this requires FlatBuffers-style serialization infrastructure that is not justified for 300-second experiments
- **Cross-module changes** -- all changes are confined to rv-agent; no modifications to rv-platform, rv-experiment, rv-screen-parser, or other modules
- **Calibration parameter optimization** -- this change establishes the architecture and default values; gh9's Optuna campaign finds optimal values

## Decisions

### D1: PathBuffer as separate class vs inline in strategy

**Decision**: Separate class in `strategies/rvagent_strategy/path_buffer.py`.

**Alternatives considered**:
- Inline path management in `select_next_action()`: simpler but makes the already-long method harder to test and reason about
- PathBuffer as part of SuccessorTracker: conflates two concerns (successor tracking is about action re-enabling, not path planning)

**Rationale**: A separate class with clear lifecycle (`plan_backtrack_path()`, `plan_mop_path()`, `plan_coverage_path()`, `get_next_action()`, `invalidate()`) is independently testable and keeps `select_next_action()` focused on action selection. The PathBuffer holds transient state (a list of planned actions) that is conceptually different from the DFS graph state.

### D2: Reward propagation model -- simplified N-step vs full SARSA

**Decision**: Simplified N-step propagation (~80 lines) reusing existing `ScreenNode` data structures.

**Alternatives considered**:
- Full SARSA: Q-table, learning rate schedule (alpha decay at 20K/50K/100K visits), epsilon-greedy selection. ~300+ lines, requires new data structures, significantly changes selection logic.
- No learning at all: keep scorer weights static. Misses the opportunity to adapt during the 300-second experiment window.

**Rationale**: P1 Simplicity. The simplified approach adds a `action_cumulative_reward` dict to `ScreenNode` (the same dict pattern already used for `action_execution_counts` and `action_success_counts`). It uses a fixed learning rate (alpha=0.25), fixed discount (gamma=0.8 configurable), and propagates backward through the last N actions in `learn_node`. No new selection mechanism -- the existing `StrengthScorer` incorporates the cumulative reward as an additive term. This captures the most valuable aspect of SARSA (actions that lead to productive outcomes get higher scores) without the complexity of Q-tables, learning rate schedules, or epsilon-greedy selection.

### D3: Scorer rebalancing -- static defaults vs config-driven

**Decision**: Config-driven via existing `RVAgentConfig` fields (change default values only).

**Alternatives considered**:
- Hard-coded constants in scorer classes: simpler but prevents gh9 from calibrating scorer weights
- Dynamic weight adjustment during exploration: adds complexity (when to adjust? based on what signal?) without clear benefit before calibration data exists

**Rationale**: The existing `RVAgentConfig` already has fields for all scorer weights (`mop_direct_score`, `mop_transitive_score`, `wtg_guided_score`, etc.). Changing the defaults is a one-line-per-field modification. gh9's Optuna campaign will search around these defaults for optimal values. This approach is zero-risk: if the new defaults perform worse, gh9 will find better values.

**Saturation calculation correction**: The `total_actions` field in `DynamicStateGraph.get_or_create_state()` currently includes system actions (BACK, RESTART) injected by the visitor with `coordinates=None`. These inflate the denominator of `get_saturation_rate()`: with 8 real actions + 2 system actions, max saturation = 8/10 = 0.8, not 1.0. This means screens with fewer than 8 real actions can never reach the 80% backtrack threshold. Fix: compute `total_actions` excluding system actions (`coordinates is None`). The visitor still injects BACK/RESTART for other consumers (action selection, fallback navigation); only the saturation denominator changes. This is a pre-condition for correct proactive backtracking behavior — without it, the scorer rebalancing and threshold-based backtracking cannot function as designed.

### D4: Text input fixes -- fix in place vs rewrite

**Decision**: Fix in place with 6 targeted changes to `InputValueGenerator` and `_infer_input_type()`.

**Alternatives considered**:
- Full rewrite of text input system: higher risk of regressions, more effort, the existing structure is sound (the bugs are in specific methods, not in the architecture)
- New `SmartInputGenerator` class replacing `InputValueGenerator`: unnecessary indirection for what are essentially bug fixes

**Rationale**: The 6 bugs have precise locations and clear fixes. Deleting `_infer_input_type()` from the strategy (Bug 1), reordering values in `_get_regular_values()` (Bug 2), adding LLM text tracking (Bug 3), adding `mop_max_input_variations` (Bug 4), adding Faker generators for missing types (Bug 5), and adding `device.clear_text()` before input (Bug 6) are all surgical changes. The `InputValueGenerator` class structure (with `get_next_value()`, `tested_values` tracking, MOP vs regular paths) remains unchanged.

### D5: Speed optimization -- compile-time vs runtime mode check

**Decision**: Runtime per-iteration check in `decision_router_node`.

**Alternatives considered**:
- Compile-time: build two separate LangGraph graphs (one with LLM nodes, one without). Simpler runtime but prevents multimode from benefiting from speed optimization on algorithm iterations.
- Global flag at startup: set once based on `agent_mode`. Breaks multimode where each iteration may route differently.

**Rationale**: In multimode (70% LLM / 30% algorithm), algorithm iterations already skip `capture_screenshot_node` and `llm_generate_node` via the existing LangGraph graph topology — the conditional edge from `decision_router_node` routes "algorithm" directly to `algorithm_node`, bypassing both nodes. No new skip logic is needed in the graph or decision_router for this behavior. The actual new speed optimization is **parse_node screen_desc caching**: when `screen_hash` is unchanged between iterations, reuse the cached `ScreenDescription` instead of re-running the visitor pipeline (~50ms saved per same-state iteration). This preserves gh18's conditional screenshot in `parse_node` (which fires on hash-repeat for error detection, independent of the LLM screenshot path).

**Caching lifecycle**: The cache is a single variable on the `RVAgent` instance (`self._cached_screen_desc: Optional[ScreenDescription]`). It is invalidated (set to None) when `screen_hash != previous_screen_hash`. The UIAutomator dump and hash computation ALWAYS execute every iteration — only the visitor pipeline (ScreenDescription construction from parsed XML) is cached. On app restart (`force_restart_app`), `_cached_screen_desc` MUST be explicitly set to None. Although the next iteration's hash will typically differ from the pre-restart hash, there is an edge case where the app restarts to the same splash screen with the same UI elements, producing the same hash — in this case, the stale cached screen_desc would be reused without explicit invalidation.

### D6: Dead code removal and consolidation during gh26

**Decision**: Remove dead code and consolidate duplicate tracking as part of gh26, before implementing new features.

**What is removed (per P3 — delete entirely, backup to `backup/`):**

| Item | Location | Why Dead |
|------|----------|----------|
| `state_stack: List[RVAgentState]` | `rvagent_strategy.py:200` | Append-only (never popped). gh26's `should_backtrack()` uses SuccessorTracker BFS for navigation distance, not stack depth. |
| `RVAgentState` dataclass | `rvagent_strategy.py:56` | Only used as `state_stack` entry. Fields: `screen_hash`, `depth`, `parent_hash`, `untested_count` — all available from `DynamicStateGraph.states` and `ScreenNode`. |
| `parent_hash` computation | `rvagent_strategy.py:265,270` | Stored in `RVAgentState` but never read by any production code. |
| `current_depth` | `rvagent_strategy.py:265` | Computed from `len(state_stack)`, only used for `RVAgentState` and metrics. |
| `visited_states: Set[str]` | `rvagent_strategy.py:201` | Always identical to `graph.states.keys()` — both populated at the same point in `handle_state_entry()`. |
| `ExecutionCountScorer` | `ranking/scorers.py` | Defined but never registered in the scorer list. Similar to pre-gh26 `GradualDecayScorer` (dead code), but unlike GDS it is not being activated. Its function (penalizing frequently-executed actions) is subsumed by `GradualDecayScorer` (exponential decay) + `VisitationPenaltyScorer` (logarithmic penalty). |

**What is consolidated:**

| Item | Before | After | Rationale |
|------|--------|-------|-----------|
| Visited activities tracking | Two independent sources: `TransitionManager._visited_activities` (explicit Set) and `RVAgentStrategy._get_visited_activities()` (computed from graph.states) | TransitionManager is single source of truth; strategy delegates to it | Prevents divergence between the two sources |
| Coverage formula in SuccessorTracker | Reimplements `executed / total` inline at `successor_tracker.py:144-148` with different zero-actions semantics (1.0 vs ScreenNode's 0.0) | Delegates to `node.get_coverage()` with explicit zero-actions override (`total_actions == 0` → 1.0 for successor tracking, meaning "nothing to explore") | Eliminates subtle formula divergence risk |

**What is documented:**

| Item | What | Where |
|------|------|-------|
| `DynamicStateGraph.transitions` | Audit-only: chronological log for post-run reporting, never queried for navigation decisions | Docstring in `dynamic_state_graph.py` |

**Alternatives considered**:
- Do consolidation in a separate change after gh26: increases risk of building new features on dead infrastructure; the new `should_backtrack()` activation and PathBuffer would need to carefully avoid `state_stack` references. Cleaning up first is safer.
- Keep `visited_states` as a performance cache: `graph.states.keys()` is O(1) for `in` checks on dict keys, and the set is only ~50-100 entries. No measurable performance benefit.

**Rationale**: P3 (No Backward Compatibility) mandates removing dead code entirely. gh26 already modifies `rvagent_strategy.py` extensively — consolidating now avoids building new features on top of dead code. The removals simplify the file by ~30 lines and eliminate 3 sources of confusion for future implementers (what is state_stack for? why are there two visited_activities sources? why does coverage differ between SuccessorTracker and ScreenNode?).

## API Design

### PathBuffer

```python
# strategies/rvagent_strategy/path_buffer.py

class PathBuffer:
    """
    Manages multi-step navigation paths for proactive exploration.

    Three strategies:
    A) Backtrack to nearest unsaturated ancestor via SuccessorTracker
    B) Navigate toward MOP-dense Activity via BFS on WTG
    C) Navigate toward high-coverage-potential screen via BFS on learned transitions
    """

    def __init__(
        self,
        transition_manager: Optional["TransitionManager"],
        successor_tracker: "SuccessorTracker",
        ui_coverage_tracker: "UICoverageTracker",
        config: "RVAgentConfig"
    ):
        """
        Args:
            transition_manager: For WTG-based BFS (Strategy B). None disables Strategy B.
            successor_tracker: For ancestor navigation (Strategy A) and learned
                transitions (Strategy C).
            ui_coverage_tracker: For coverage gap queries (Strategy C).
            config: Configuration with mop_nav_weight.
                Uses module-level constants MAX_BACKTRACK_HOPS and MAX_COVERAGE_HOPS.
        """

    def get_next_action(self) -> Optional[ItemAction]:
        """
        Get next buffered action, or None if buffer is empty.

        Postcondition: Advances internal pointer. If this was the last action in the
        buffer, the buffer becomes empty.

        Logs the action via [RVTRACK:BACKTRACK] with a visual path representation
        (e.g., "[BACK] → [BACK] → [Click 'Settings']") showing current position
        in the planned path.

        Returns:
            Next ItemAction from the buffered path, or None.
        """

    def plan_backtrack_path(self, current_hash: str) -> bool:
        """
        Plan a path to the nearest unsaturated ancestor (Strategy A).

        Uses SuccessorTracker.find_nearest_unsaturated() which returns
        Optional[Tuple[str, int]] — (ancestor_hash, bfs_hop_count). The
        hop count determines the number of BACK actions to buffer. This
        replaces using state_stack depth difference, which is unreliable
        because state_stack is append-only and does not reflect actual
        navigation depth.

        Implementation prerequisite: find_nearest_unsaturated() must be
        modified to return Optional[Tuple[str, int]] instead of the current
        Optional[str]. The current implementation at successor_tracker.py:329
        returns only the ancestor hash. The hop_count (BFS depth) must be
        tracked during the BFS traversal and returned alongside the hash.
        Without this change, PathBuffer cannot determine how many BACK
        actions to buffer.

        The hop count is capped at MAX_BACKTRACK_HOPS (constant = 8).
        If the nearest unsaturated ancestor is farther than MAX_BACKTRACK_HOPS,
        plan_backtrack_path returns False (no path planned). This prevents
        wasteful sequences of 15-20 consecutive BACK actions that are unlikely
        to succeed due to intermediate dialogs, app restarts, or navigation
        inconsistencies. Since Strategy A is evaluated last (C > B > A
        ordering), a failure here means all three strategies failed — the
        caller falls through to Tier 4 (scored continuous mode).

        Args:
            current_hash: Current state hash.

        Returns:
            True if a path was planned and buffered, False otherwise.
        """

    def plan_mop_path(
        self,
        current_activity: str,
        mop_data: Optional[Dict]
    ) -> bool:
        """
        Plan a path to a MOP-dense Activity via BFS on WTG (Strategy B).

        Requires transition_manager with WTG data. Uses BFS with MOP density
        weighting: edges toward Activities with higher mop_methods/total_methods
        ratio are preferred. Saturation-aware: prefers paths through less-saturated states.

        Conversion from WTG transitions to ItemAction: TransitionManager.
        plan_path_to_mop_activity() returns List[Dict] where each dict has
        'target_activity' and 'action_type'. PathBuffer converts these to
        ItemAction objects using the same pattern as TransitionManager.
        _map_targets_to_actions() (~line 350): for each transition dict,
        create an ItemAction with the target coordinates and action type from
        the WTG edge data. If a transition cannot be mapped to a concrete
        ItemAction (no matching UI element on current screen), the path is
        discarded and plan_mop_path returns False.

        Args:
            current_activity: Current Activity name.
            mop_data: Static analysis MOP data (from StaticAnalysisData).

        Returns:
            True if a path was planned and buffered, False otherwise.
        """

    def invalidate(self):
        """
        Clear the buffered path.

        Called when the agent reaches an unexpected state (screen hash does not
        match what the buffer expects). Safe to call when buffer is already empty.

        Logs the discarded path via [RVTRACK:BACKTRACK] with remaining_steps and
        reason="invalidated".
        """

    @property
    def is_active(self) -> bool:
        """True if buffer contains actions to execute."""

    @property
    def remaining_steps(self) -> int:
        """Number of actions remaining in the buffer."""
```

### CoverageDensityScorer

```python
# strategies/rvagent_strategy/ranking/scorers.py

class CoverageDensityScorer(Scorer):
    """
    Cross-screen coverage guidance using learned transitions.

    Scores actions based on their destination screen's UI coverage gap,
    querying SuccessorTracker for action destinations and UICoverageTracker
    for destination coverage. Always active — not gated on StaticAnalysisData.

    When MOP methods represent 1-5% of app code, broad UI coverage increases
    the probability of reaching monitored operations. This scorer provides
    the "broad surface" strategy that complements MopScorer's "precision
    targeting" — together they form the dual guidance architecture.

    Scoring formula:
    - Known destination: weight * coverage_gap
      where coverage_gap = untested_elements / total_elements
    - Unknown destination: weight * 0.5 (exploration bonus)

    The default weight (200) places this scorer below MopScorer (+500/+300)
    but equal to GradualDecayScorer, providing meaningful guidance without
    overshadowing MOP targeting.
    """

    def __init__(self, weight: float = 200.0):
        self.weight = weight

    def score(self, action: "ItemAction", context: "RankingContext") -> float:
        """
        Score action based on destination screen's coverage gap.

        Requires context.successor_tracker and context.ui_coverage.
        Returns 0.0 if either is unavailable.
        """
        if not context.successor_tracker or not context.ui_coverage:
            return 0.0

        action_sig = self._convert_signature(action.coords_for_matching)
        destination = context.successor_tracker.get_action_destination(
            context.current_state_hash, action_sig
        )

        if destination is None:
            # Unknown destination — exploration bonus
            return self.weight * 0.5

        coverage_gap = context.ui_coverage.get_coverage_gap(destination)
        # Guard: zero total_elements → 0.0 (neutral). get_coverage_gap returns
        # 0.0 for unknown states or states with no elements, preventing division
        # by zero in the untested_elements / total_elements formula.
        return self.weight * coverage_gap
```

### SuccessorTracker.get_action_destination() (new method)

```python
# Added to strategies/rvagent_strategy/successor_tracker.py

def get_action_destination(
    self,
    state_hash: str,
    action_signature: tuple
) -> Optional[str]:
    """
    Look up where an action leads based on learned transitions.

    Provides clean accessor to the internal successors dictionary,
    which records (from_hash, action_signature) -> to_hash mappings
    from observed transitions.

    Args:
        state_hash: Hash of the state where the action is available.
        action_signature: Tuple of ((opt_x, opt_y), action_type).

    Returns:
        Destination state hash, or None if transition not recorded.
    """
    return self.successors.get((state_hash, action_signature))
```

### RankingContext.successor_tracker (new field)

```python
# Modified in strategies/rvagent_strategy/ranking/context.py

@dataclass
class RankingContext:
    # ... existing fields ...
    successor_tracker: Optional["SuccessorTracker"] = None  # For CoverageDensityScorer
    has_untested_inputs: bool = False  # True when untested SET_TEXT/TEXT_CHANGE exist (INV-AGT-39)
```

### Modified: MopScorer.score() — Form-Context Deferral (INV-AGT-39)

```python
# strategies/rvagent_strategy/ranking/scorers.py

class MopScorer(Scorer):
    """
    Scores actions based on proximity to monitored operations (MOP).

    Form-context deferral (INV-AGT-39): In Tier 2, when the screen has untested
    SET_TEXT/TEXT_CHANGE actions, MopScorer returns 0.0 for CLICK actions. This
    prevents the agent from clicking submit buttons on empty forms — a common
    waste pattern where MOP-reaching buttons like "GENERATE HASH" are clicked
    before form fields are filled, producing error indicators instead of valid
    MOP triggers.

    In Tier 4 (scored continuous mode), has_untested_inputs is always False
    because all actions have been tested by definition. MopScorer applies at
    full weight, ensuring the button is re-executed AFTER form fields are filled.

    The deferral only affects CLICK actions — SET_TEXT actions with MOP association
    (e.g., a text field whose content is passed to Cipher.getInstance) still
    receive full MOP scoring, which is correct: filling a MOP-relevant field
    should be prioritized regardless of other untested inputs.
    """

    def score(self, action, context) -> float:
        # Form-context deferral (INV-AGT-39): suppress MOP for CLICK
        # when untested input actions exist on the screen.
        # In Tier 4, has_untested_inputs is always False (all tested).
        if context.has_untested_inputs and action.action_type == "CLICK":
            return 0.0
        if action.directly_reaches_mop:
            return self.direct_score  # +500
        elif action.reaches_mop:
            return self.transitive_score  # +300
        return 0.0
```

**Design rationale**: The MOP-first bias is the root cause of wasted iterations on form-heavy screens. Without deferral, MopScorer (+500) forces GENERATE HASH to be selected before any text input field is tested in every fresh screen state. The button click on an empty form produces error indicators but no valid MOP trigger, wasting an iteration. With deferral, the button still gets selected in Tier 2 (it has ComponentPriority +50 tiebreaker) but without the +500 MOP boost, so it competes on equal footing with other CLICK actions. The critical payoff comes in Tier 4: after all actions are tested (including SET_TEXT), MopScorer applies at full weight, ensuring the button is re-executed with valid form data. This creates the natural form-first flow: fill inputs → click button → Tier 4 re-executes button with valid data. The `has_untested_inputs` flag is computed per-tier, not stored — it is True in Tier 2 when at least one untested action is SET_TEXT/TEXT_CHANGE, and always False in Tier 4.

### PathBuffer.plan_coverage_path() (new method)

```python
# Added to strategies/rvagent_strategy/path_buffer.py

def plan_coverage_path(self) -> bool:
    """
    Plan a path to the screen with highest exploration potential (Strategy C).

    Performs BFS on SuccessorTracker's learned transitions (not the static WTG)
    to find reachable screens with the highest exploration_potential, defined as:
        exploration_potential = coverage_gap * element_count

    This metric prefers screens with MANY untested elements, not just a high
    untested percentage. A Settings screen with 15 elements at 50% coverage
    (potential = 7.5) is more valuable than an About screen with 2 elements
    at 0% coverage (potential = 2.0).

    BFS depth is limited by MAX_COVERAGE_HOPS (constant = 5). Screens
    beyond this hop distance are not considered as navigation targets.

    Strategy C is positioned before Strategy B in Tier 3 because broad UI
    coverage addresses the "small island" problem: it increases the probability
    surface for finding MOP methods, including those not mapped by static
    analysis. Strategy C operates entirely on runtime data and is always
    available, even without StaticAnalysisData.

    Returns:
        True if a path was planned and buffered, False otherwise.
        Returns False during cold start (fewer than 3 discovered screens)
        or when no screen with exploration_potential > 0 is reachable.
    """
```

### Modified: SuccessorTracker.find_nearest_unsaturated()

```python
# Modified in strategies/rvagent_strategy/successor_tracker.py

def find_nearest_unsaturated(self, current_state: str) -> Optional[Tuple[str, int]]:
    """
    BFS to find the nearest unsaturated ancestor state.

    Returns:
        Tuple of (ancestor_hash, bfs_hop_count) or None if all saturated.
        The hop_count determines how many BACK actions PathBuffer should buffer.
    """
    visited = {current_state}
    queue = deque([(current_state, 0)])

    while queue:
        state_hash, depth = queue.popleft()

        for back_target in self.back_successors.get(state_hash, []):
            if back_target in visited:
                continue

            visited.add(back_target)
            hop_count = depth + 1

            if not self._is_saturated(back_target):
                logger.info(
                    f"Backtrack BFS: Found unsaturated state {back_target[:8]} "
                    f"(distance: {hop_count} BACK actions)"
                )
                return (back_target, hop_count)

            queue.append((back_target, hop_count))

    logger.info("Backtrack BFS: All reachable states are saturated")
    return None
```

### RewardPropagator

```python
# strategies/rvagent_strategy/reward_propagator.py

class RewardPropagator:
    """
    Simplified N-step reward propagation.

    When a high-value event occurs (new state, new Activity, MOP method reached),
    propagates reward backward through the last N actions with discount gamma.
    Updates ScreenNode.action_cumulative_reward for use by StrengthScorer.

    Maintains its own internal sliding window of (state_hash, action_signature)
    tuples, populated by learn_node via record_action(). This avoids enriching
    the shared recent_action_window (which stores raw action dicts without
    state_hash or optimized coordinates).
    """

    # Reward values
    REWARD_SAME_STATE: float = -0.1
    REWARD_FORM_FILL: float = 0.0  # Neutral reward for SET_TEXT/TEXT_CHANGE on same screen
    REWARD_NEW_STATE: float = 1.0
    REWARD_NEW_ACTIVITY: float = 2.0
    REWARD_MOP_REACHED: float = 5.0

    # Cumulative reward bounds: prevents unbounded score inflation/deflation.
    # Max cumulative reward = MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT
    # Min cumulative reward = -MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT
    # With REWARD_MOP_WEIGHT=5.0, bounds = [-15.0, +15.0]
    MAX_CUMULATIVE_REWARD_FACTOR: float = 3.0

    def __init__(self, config: "RVAgentConfig"):
        """
        Args:
            config: Configuration with reward_gamma.
                Uses module-level constants REWARD_MOP_WEIGHT and REWARD_PROPAGATION_N.

        Internal state:
            _action_history: deque(maxlen=REWARD_PROPAGATION_N) of
                (state_hash, action_signature) tuples. Populated by
                record_action(), consumed by propagate().
        """

    def record_action(self, state_hash: str, action_signature: tuple) -> None:
        """
        Record an action for future reward propagation.

        Called by learn_node after each iteration, using the same state_hash
        (previous_screen_hash, i.e. the state where the action was executed)
        and action_signature (optimized coordinates, as computed by
        _record_action_success()). Maintains a deque of max
        REWARD_PROPAGATION_N entries.

        Args:
            state_hash: Hash of the state where the action was executed.
            action_signature: Tuple of ((opt_x, opt_y), action_type) in
                optimized [0, 1000) coordinate space.
        """

    def propagate(
        self,
        reward_type: str,
        graph: "DynamicStateGraph"
    ) -> None:
        """
        Propagate reward backward through the internal action history.

        Each action in the history receives: reward * gamma^(distance_from_event).
        The reward is added to ScreenNode.action_cumulative_reward for the
        corresponding state and action signature.

        Reward type determination: When multiple reward conditions apply
        simultaneously (e.g., action leads to new Activity AND has
        callback_signature), the HIGHEST reward value is used. The priority
        order is: mop_reached (5.0) > new_activity (2.0) > new_state (1.0)
        > form_fill (0.0) > same_state (-0.1). The form_fill type applies
        when hash is unchanged AND the action was SET_TEXT or TEXT_CHANGE —
        this prevents penalizing form filling actions that legitimately do
        not change the screen hash. This is implemented as if/elif in
        learn_node, not if/if — only one propagate() call per iteration.

        Propagation indexing: The most recent action in the deque (index -1)
        receives reward * gamma^0 (i.e., the full reward). The second-most-recent
        receives reward * gamma^1, and so on. Index k=0 corresponds to the
        action that caused/preceded the reward event.

        Args:
            reward_type: One of "same_state", "form_fill", "new_state", "new_activity", "mop_reached".
            graph: DynamicStateGraph for accessing ScreenNode data.

        Postcondition: Updates action_cumulative_reward in ScreenNode for each
        action within the propagation window. Cumulative reward is bounded:
        upper cap at `MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT`
        (+15.0) and lower cap at `-MAX_CUMULATIVE_REWARD_FACTOR *
        REWARD_MOP_WEIGHT` (-15.0). The upper cap prevents
        score inflation from repeated MOP-reaching sequences; the lower cap
        prevents unbounded negative accumulation from repeated same_state
        penalties that would permanently suppress actions.

        Error behavior: If the internal history has fewer than N items, propagates
        through all available items. If graph.states does not contain a state_hash,
        skips that action silently.
        """
```

### TransitionManager (new method)

```python
# Added to services/transition_manager.py

def plan_path_to_mop_activity(
    self,
    current_activity: str,
    mop_data: Optional[Dict]
) -> Optional[List[Dict]]:
    """
    BFS on WTG to find shortest path to a MOP-dense unvisited Activity.

    Edge weighting:
    - MOP density: mop_methods_in_target / total_methods_in_target
    - Saturation awareness: prefer paths through less-saturated states
    - Weight = (1 / (1 + mop_density * mop_nav_weight)) * (1 + saturation_rate)
      Lower weight = preferred path.

    Args:
        current_activity: Current Activity name.
        mop_data: Static analysis data with MOP method counts per Activity.

    Returns:
        List of action dicts representing the path, or None if no path found.
        Each dict contains 'target_activity' and 'action_type'.

    Precondition: self.wtg is not None and mop_data is not None.
    Returns None if either precondition is not met.
    """
```

### Modified: RVAgentStrategy.select_next_action()

New 5-tier action selection flow:

```python
def select_next_action(self, current_hash, screen_desc) -> Optional[ItemAction]:
    # ... existing plateau check, node creation, successor re-enabling ...

    # NEW FLOW:
    # Tier 1: PathBuffer — execute pre-planned path
    if self.path_buffer.is_active:
        buffered = self.path_buffer.get_next_action()
        if buffered:
            return buffered  # Skip pre-marking (buffer manages its own state)

    # Tier 2: Untested actions — score with rebalanced ActionRanker
    untested_actions = self._get_untested_actions(node, screen_desc)
    if untested_actions:
        # Check if any untested action is a text input (INV-AGT-39)
        has_untested_inputs = any(
            a.action_type in ("SET_TEXT", "TEXT_CHANGE")
            for a in untested_actions
        )
        ranking_context = RankingContext(
            ...,
            has_untested_inputs=has_untested_inputs,
        )
        selected = self._select_priority_action(untested_actions, screen_desc, ranking_context)
        # ... existing pre-marking and input handling ...
        return selected

    # Tier 3: Proactive backtracking — only if plan succeeds
    if self.should_backtrack(current_hash):
        if self.path_buffer.plan_coverage_path():
            return self.path_buffer.get_next_action()
        if self.path_buffer.plan_mop_path(screen_desc.activity, self._get_mop_data()):
            return self.path_buffer.get_next_action()
        if self.path_buffer.plan_backtrack_path(current_hash):
            return self.path_buffer.get_next_action()
        # All plans failed (all reachable states saturated) — fall through to Tier 4
        # Do NOT return _create_back_action() here: preserves continuous exploration

    # Tier 4: Scored continuous mode — ALL actions ranked by full scorer system
    # has_untested_inputs always False in Tier 4 (all actions tested → MopScorer at full weight)
    ranking_context = RankingContext(
        ...,
        has_untested_inputs=False,
    )
    all_filtered = self._get_all_filtered_actions(screen_desc)
    if all_filtered:
        scroll_action = self._try_generate_scroll_action(...)
        if scroll_action:
            return scroll_action
        scored_actions = self.action_ranker.rank(all_filtered, ranking_context)
        selected = scored_actions[0].action if scored_actions else None
        if selected:
            return selected

    # Tier 5: Final BACK fallback
    return self._create_back_action()
```

**Design rationale for Tier 4 scored selection**: In the previous design, Tier 4 used `_select_least_executed_action()` which selects purely by execution count — no scorer involvement. This means all gh26 scorer improvements (CoverageDensityScorer, rebalanced MopScorer, GradualDecayScorer) have zero effect once the agent enters continuous mode. In 3-hour experiments, 60-90% of iterations operate in Tier 4, so the majority of the run would not benefit from the new scorers. By replacing `_select_least_executed_action()` with `ActionRanker.rank()` on ALL actions (tested + untested), the scorers naturally handle the transition from untested to re-testing: `GradualDecayScorer` gives exponential decay (heavily-tested actions get near-zero score), `MopScorer` gives priority regardless of test count, `CoverageDensityScorer` prefers actions leading to less-explored screens, and `SaturationScorer` gives bonus inversely proportional to saturation. This makes continuous mode "smart" — re-tests in MOP-prioritized, coverage-guided order instead of just "pick least-executed." The Tier 3 conditional change (removing the plain BACK fallback when all path plans fail) ensures that when all reachable states are saturated, the agent falls through to Tier 4's scored selection rather than entering an unproductive BACK cycling loop.

### Modified: should_backtrack()

```python
def should_backtrack(self, current_hash: str) -> bool:
    """
    Determine if backtracking needed based on saturation threshold.

    Uses configurable backtrack_saturation_threshold instead of binary
    100% exhaustion check.

    Returns True when:
    - State not in graph (unknown state)
    - No incomplete successors AND saturation >= threshold
    """
    node = self.graph.states.get(current_hash)
    if not node:
        return True
    if self.successor_tracker.has_incomplete_successors(current_hash):
        return False
    saturation = node.get_saturation_rate(threshold=2)
    return saturation >= self.config.backtrack_saturation_threshold
```

### Modified: StrengthScorer.score()

```python
def score(self, action, context) -> float:
    node = context.graph.states.get(context.current_state_hash)
    if not node:
        return self.weight * 0.5

    action_signature = self._convert_signature(action.coords_for_matching)
    strength = node.get_action_strength(action_signature)

    # NEW: incorporate cumulative reward from N-step propagation.
    # Note: cumulative_reward is already capped by RewardPropagator at
    # MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT (15.0),
    # so no additional capping is needed here.
    cumulative_reward = node.action_cumulative_reward.get(action_signature, 0.0)

    return self.weight * strength + self.reward_score_weight * cumulative_reward
```

### Modified: InputValueGenerator.get_next_value()

Key changes:
- `_get_regular_values()`: Faker values first; PINs only for password/pin type; no empty string as first value
- `_get_mop_values()`: Uses `mop_max_input_variations` (default 11) instead of `max_variations` (default 5)
- New input types: search, url, date, time, number, zip, verification_code with Faker generators
- `_infer_input_type()` deleted from strategy; input type inferred from `hint`, `content_description`, and `resource_id` fields directly available on the `ItemAction.target_view` Node object (no dependency on `EnhancedTextVisitor`). A simplified inline helper in `_prepare_input_action()` checks these fields in priority order: `hint` (most reliable), then `content_description`, then `resource_id` pattern matching. This is P1-compatible: ~15 lines replacing the duplicated 40-line method

### New RVAgentConfig fields (6 calibratable parameters)

```python
# Added to config/agent_config.py

# Backtracking
backtrack_saturation_threshold: float = Field(
    default=0.8, ge=0.5, le=1.0,
    description="Saturation rate threshold for proactive backtracking"
)

# Path buffer
mop_nav_weight: float = Field(
    default=2.0, ge=0.5, le=5.0,
    description="Weight of MOP density in BFS path planning"
)

# Text input
mop_max_input_variations: int = Field(
    default=11, ge=5, le=15,
    description="Maximum input variations for MOP-reaching fields"
)

# Reward propagation
reward_gamma: float = Field(
    default=0.8, ge=0.5, le=0.99,
    description="Discount factor for N-step reward propagation"
)
reward_score_weight: float = Field(
    default=1.0, ge=0.1, le=3.0,
    description="Weight of cumulative_reward in StrengthScorer. Controls how much "
                "reward propagation influences action ranking relative to historical "
                "strength. Formula: weight * strength + reward_score_weight * cumulative_reward"
)

# Coverage-based guidance (Dual Guidance)
coverage_density_weight: float = Field(
    default=200.0, ge=50.0, le=400.0,
    description="Weight for CoverageDensityScorer. Controls cross-screen coverage "
                "guidance strength. Default 200 places it below MopScorer (+500) "
                "but equal to GradualDecayScorer. Calibratable via gh9."
)
```

### Module-level constants (5 fixed values, not calibratable)

```python
# In strategies/rvagent_strategy/path_buffer.py
PATH_BUFFER_ENABLED: bool = True  # Always active; strategies return False when conditions aren't met
MAX_BACKTRACK_HOPS: int = 8       # Sequences of >8 BACKs unreliable due to dialog interference
MAX_COVERAGE_HOPS: int = 5        # Learned transition accuracy degrades with hop distance

# In strategies/rvagent_strategy/reward_propagator.py
REWARD_MOP_WEIGHT: float = 5.0    # reward_score_weight controls scorer influence; calibrating both is redundant
REWARD_PROPAGATION_N: int = 5     # gamma^5 = 0.33, rewards beyond 5 steps are negligible
```

### Implementation Prerequisites

The rv-agent `pyproject.toml` dependency constraints must be updated to match the actual installed versions (e.g., `langchain>=1.2`, `langgraph>=1.0`, `langchain-openai>=1.0`). The current constraints (`>=0.3`) are stale and could allow `uv` to resolve an older, incompatible version on a clean install. This is a one-line-per-dependency change with no behavioral impact — it prevents accidental downgrade.

**UICoverageTracker prerequisite**: `CoverageDensityScorer` and PathBuffer Strategy C require `get_coverage_gap(state_hash) -> float` and `get_element_count(state_hash) -> int` methods on `UICoverageTracker` (in `memory/ui_coverage.py`). These methods must be added as part of Group 1 implementation before CoverageDensityScorer (task 3.5.4) and Strategy C (task 3.5.6) can query coverage data per destination screen.

## Data Flow

### Single Iteration (pure_algorithm mode, after all improvements)

```
1. parse_node
   ├── UIAutomator dump → ScreenDescription + screen_hash
   ├── [speed opt] If hash unchanged AND cached screen_desc exists → reuse cache
   └── [gh18] Conditional screenshot on hash-repeat for VisualErrorDetector

2. decision_router_node
   ├── Check force_restart_app / force_back_action (from learn_node)
   ├── [gh18] Check force_fill_input → route to "algorithm"
   ├── Route decision: "algorithm" or "llm"
   └── [speed opt] If "algorithm" → skip capture_screenshot_node

3. algorithm_node
   ├── [gh18] force_fill_input → spatial association → SET_TEXT
   ├── deadlock check (consecutive_no_action >= 3 → BACK)
   └── strategy.select_next_action(hash, screen_desc)

4. strategy.select_next_action() [NEW FLOW]
   ├── Plateau check (informational)
   ├── Create/update graph node, re-enable successors
   ├── Tier 1: PathBuffer.get_next_action()
   │     └── If buffered action available → return it
   ├── Tier 2: _get_untested_actions() → ActionRanker with rebalanced weights
   │     │   has_untested_inputs = any SET_TEXT/TEXT_CHANGE in untested (INV-AGT-39)
   │     ├── MopScorer: +500 (DM), +300 (M) — deferred to 0.0 for CLICK if has_untested_inputs
   │     ├── WtgScorer: +150
   │     ├── GradualDecayScorer: 200 * 0.7^visits [NEW — activated; visits from UICoverageTracker]
   │     ├── CoverageDensityScorer: 200 * coverage_gap [NEW — always active; SuccessorTracker+UICoverage]
   │     ├── SaturationScorer: +100 * (1 - sat_rate)
   │     ├── ComponentPriorityScorer: +50/+40
   │     ├── StrengthScorer: weight * strength + reward_score_weight * cumulative_reward [NEW]
   │     ├── SystemElementFilter: -5000
   │     └── VisitationPenaltyScorer: -15 * log(1 + visits)  [NEW default; current is -10]
   ├── Tier 3: should_backtrack(threshold=0.8) → plan path or fall through (C > B > A)
   │     ├── PathBuffer.plan_coverage_path() → BFS on learned transitions to high-potential screen
   │     ├── PathBuffer.plan_mop_path() → BFS to MOP-dense Activity
   │     ├── PathBuffer.plan_backtrack_path() → BACK to unsaturated ancestor
   │     └── All plans failed → fall through to Tier 4 (do NOT return plain BACK)
   ├── Tier 4: Scored continuous mode (scroll + ActionRanker on ALL actions, has_untested_inputs=False)
   └── Tier 5: BACK fallback

5. validation_node → coordinate validation, loop detection

6. execute_node
   ├── Execute action on device
   ├── [text input] clear_text() before input_text() [NEW — Bug 6 fix]
   └── Record UI coverage

7. learn_node
   ├── [gh18] _detect_validation_error() → force_fill_input
   ├── Stuck detection (Level 1 + Level 2)
   ├── _record_action_success()
   ├── [NEW] RewardPropagator.record_action(previous_hash, action_signature)
   │     └── Appends (state_hash, action_signature) to internal deque
   │         (reuses same previous_hash and optimized coords from _record_action_success)
   ├── [NEW] RewardPropagator.propagate(reward_type, graph)
   │     ├── Determine reward_type (mutually exclusive — highest applicable wins):
   │     │     ├── mop_reached → 5.0 (when callback_signature present, regardless of state change)
   │     │     ├── new_activity → 2.0 (hash changed AND activity not seen before)
   │     │     ├── new_state → 1.0 (hash changed AND activity already seen)
   │     │     ├── form_fill → 0.0 (hash unchanged AND action was SET_TEXT/TEXT_CHANGE)
   │     │     └── same_state → -0.1 (hash unchanged AND action was NOT SET_TEXT/TEXT_CHANGE)
   │     └── Propagate backward through internal history: reward * gamma^distance
   │           → Updates ScreenNode.action_cumulative_reward
   └── Memory updates (MemoryCoordinator)
```

### PathBuffer Invalidation Flow

```
learn_node after action execution:
  ├── If PathBuffer.is_active AND current_hash == previous_hash:
  │     └── Buffered action had no effect (BACK didn't navigate, click didn't transition)
  │     └── PathBuffer.invalidate() — clear buffer, log warning
  │     └── Normal action selection resumes next iteration (Tier 2-5)
  └── If PathBuffer.is_active AND current_hash != previous_hash:
        └── Buffered action succeeded — PathBuffer continues with next step
```

The invalidation check uses hash comparison (`current_hash == previous_hash`),
not an "expected next hash" from the buffer. This is simpler (P1) and catches
all failure cases: BACK that didn't navigate, navigation clicks that didn't
transition, dialogs that blocked navigation. The PathBuffer does not need to
predict what hash the next state will have — only that the state changed.

### Reward Propagation Example

```
Iteration 96: Action A in State S1 → new state (reward 1.0)
Iteration 97: Action B in State S2 → same state (reward -0.1)
Iteration 98: Action C in State S2 → new state (reward 1.0)
Iteration 99: Action D in State S3 → new activity (reward 2.0)
Iteration 100: Action E in State S4 → MOP reached (reward 5.0)

Propagation (N=5, gamma=0.8):
  Action E: 5.0 * 0.8^0 = 5.0   → S4.action_cumulative_reward[E] += 5.0
  Action D: 5.0 * 0.8^1 = 4.0   → S3.action_cumulative_reward[D] += 4.0
  Action C: 5.0 * 0.8^2 = 3.2   → S2.action_cumulative_reward[C] += 3.2
  Action B: 5.0 * 0.8^3 = 2.56  → S2.action_cumulative_reward[B] += 2.56
  Action A: 5.0 * 0.8^4 = 2.05  → S1.action_cumulative_reward[A] += 2.05

Next time the agent visits S1, StrengthScorer gives Action A extra score
proportional to its cumulative_reward (2.05), steering exploration toward
the sequence that led to the MOP method.
```

### MOP Detection in learn_node

The `learn_node` determines the `REWARD_MOP_REACHED` reward type by checking `selected_action.callback_signature` from `AgentState`. When `callback_signature` is present (non-None, non-empty), it means the selected action is associated with a monitored operation method — this is a **proxy signal from static analysis (REACH)** that "the action CAN reach MOP," not a runtime confirmation that MOP was actually triggered. Consequently, the +5.0 reward may be given for actions that did not actually trigger a monitored API call at runtime. This is an accepted trade-off: real-time MOP detection would require logcat parsing within the 300s window (out of scope for gh26), and the proxy signal is sufficiently correlated with actual MOP triggering to steer exploration productively. The reward values for the other types (same state, new state, new Activity) are determined by comparing `current_screen_hash` with `previous_screen_hash` and checking whether the Activity has been seen before. When multiple conditions apply (e.g., new Activity AND callback_signature present), the highest reward is used (mop_reached wins over new_activity).

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| PathBuffer reaches unexpected state | `learn_node` detects hash mismatch with buffer expectation | Call `PathBuffer.invalidate()`, log warning | Normal action selection resumes (Tier 2-5) |
| PathBuffer BFS finds no path | `plan_coverage_path()`, `plan_mop_path()`, or `plan_backtrack_path()` returns False | Return False, caller falls through to next tier | Strategy proceeds to scored continuous mode (Tier 4) |
| Reward propagation on short history | Internal action history has < N items | Propagate through all available items | No error; works correctly with any history length >= 1 |
| Missing static analysis data | `TransitionManager` has no WTG, or `StaticAnalysisData` is None | MopScorer returns 0.0, WtgScorer returns 0.0, PathBuffer Strategy B disabled, NavigationGuidance returns empty | Agent operates as generic UI structure explorer; Strategy A (backtrack to unsaturated ancestor) still works |
| `should_backtrack()` on empty graph | State hash not in `graph.states` | Return True (backtrack from unknown state) | Agent navigates BACK, which is safe behavior for unknown states |
| `should_backtrack()` on single-node graph | Only one state, no parent | Return based on saturation check; no infinite BACK loop because Tier 4 scored continuous mode catches this | Highest-scored action selected via ActionRanker |
| `GradualDecayScorer` with missing element_id | Action has no `widget_id` and coordinates are None | Return 0.0 (neutral score) | Other scorers determine ranking |
| `CoverageDensityScorer` cold start | Fewer than 3 screens discovered, SuccessorTracker has few transitions | Return exploration bonus (weight * 0.5) for unknown destinations | GradualDecayScorer provides element-level guidance during cold start |
| Strategy C no-path found | All reachable screens within `MAX_COVERAGE_HOPS` are well-covered (exploration_potential ≈ 0) | `plan_coverage_path()` returns False | Caller falls through to Strategy B or Strategy A |
| Coverage as imperfect proxy | High UI coverage does not guarantee reaching MOP methods | CoverageDensityScorer increases probability surface, not certainty | MopScorer provides directed precision when SA is available; dual guidance combines both |
| PathBuffer + stuck detection interaction | PathBuffer is active AND screen_hash unchanged for `dynamic_threshold` iterations | Stuck detection takes precedence: invalidates PathBuffer AND sets `force_back_action=True`. PathBuffer invalidation alone MUST NOT reset `stuck_screen_count` — the two mechanisms operate independently on the same hash-unchanged signal | Stuck detection fires, PathBuffer cleared, agent navigates via BACK |
| `InputValueGenerator` unknown input type | `_get_regular_values()` receives unrecognized type | Falls through to text default with Faker values (no longer PINs) | Generates sensible text input |
| Speed optimization skip in multimode | LLM iteration needs screenshot but algorithm iteration does not | Per-iteration decision in `decision_router_node`: "llm" path includes screenshot, "algorithm" path skips it | Both paths work correctly |

## Risks / Trade-offs

**[WTG score reduction]** Reducing WTG from 250 to 150 could hurt navigation through non-MOP intermediate screens that are necessary to reach MOP-containing Activities. For example, a "Settings" screen (no MOP methods) that leads to "Security Settings" (with MOP methods) would get lower WTG priority.
Mitigation: The post-implementation validation experiment (see "Experimental Validation" section) will measure this across 10 APKs with 3 repetitions. If rvagent:pure_algorithm shows regression in method coverage, the WTG default should stay at 200-250 and gh9 calibration will find the optimal value. Additionally, PathBuffer Strategy B navigates through intermediate screens explicitly, partially compensating for lower WTG scores on individual actions.

**[should_backtrack() is untested dead code]** The method exists at `rvagent_strategy.py:447` but has never been called in production. It may contain bugs in edge cases (single-node graph, states removed from graph, successor tracker inconsistency).
Mitigation: Write comprehensive unit tests for `should_backtrack()` BEFORE integrating it into the action selection flow. Test cases must cover: saturated state, partially-explored state, state with incomplete successors, single-node graph, state not in graph, and the new saturation threshold behavior.

**[Non-independent gain estimates]** The 10 improvements interact non-linearly. Faster iterations (speed optimization) amplify better decisions (proactive backtracking, path buffer). Scorer rebalancing now benefits BOTH untested action selection (Tier 2) AND continuous mode (Tier 4, which uses ActionRanker.rank_actions() instead of the previous least-executed selection). The realistic combined gain is ~60-70% of the naive sum of individual estimates.
Mitigation: The validation experiment (see "Experimental Validation" section) measures the combined effect of all 10 improvements against a pre-implementation baseline (10 APKs, 3 tools, 3 reps, 300s, Wilcoxon signed-rank test). Per-improvement ablation is deferred to gh9 calibration, which tests parameter combinations systematically via Optuna.

**[Speed optimization mode-awareness]** Skipping screenshot capture in algorithm iterations must not break multimode LLM iterations. If the routing check has a bug, LLM iterations could run without screenshots, producing invalid actions.
Mitigation: The speed optimization is a conditional skip in `decision_router_node`, not a removal of the screenshot node from the graph. The LangGraph workflow still contains all nodes; the router simply sends algorithm iterations on the "algorithm" edge (which bypasses `capture_screenshot_node` by graph topology) while LLM iterations follow the "llm" edge (which includes `capture_screenshot_node`). This is the existing routing mechanism -- no new skip logic is needed for the LangGraph graph itself. The speed optimization focuses on caching `screen_desc` when hash is unchanged in `parse_node` (the UIAutomator dump and hash computation always execute every iteration — only the visitor pipeline is cached; see D5).

**[PathBuffer stale path]** A buffered path may become invalid if the app's state changes unexpectedly (e.g., a notification dialog appears, app auto-navigates). The agent would execute the next buffered action on the wrong screen.
Mitigation: `learn_node` validates that the actual next state hash matches the PathBuffer's expectation. On mismatch, `PathBuffer.invalidate()` clears the buffer and normal action selection resumes. This adds one hash comparison per iteration when the buffer is active -- negligible cost.

**[Coverage as imperfect proxy for MOP reachability]** CoverageDensityScorer assumes that broad UI coverage increases the probability of reaching MOP methods. While this is statistically sound (more covered UI → more code paths exercised → higher chance of hitting crypto API calls), it is not guaranteed. An app might have 50 screens, all well-covered, with MOP methods only reachable via a specific deep sequence that neither static analysis nor coverage-directed exploration discovers.
Mitigation: This is why the design is "dual" — coverage provides the broad probabilistic surface, MOP targeting provides the directed precision. Neither alone is sufficient for all apps. The validation experiment (Group 10) includes a `--skip-static` variant to measure CoverageDensityScorer + Strategy C effectiveness in isolation.

**[Transition irreproducibility affects Strategy C]** SuccessorTracker records that "clicking at coordinates (x, y) in state S1 led to state S2." On revisiting S1, the same coordinates may not produce the same transition due to dynamic content, scroll position changes, or dialog interference. This affects both CoverageDensityScorer (which may attribute an action to the wrong destination) and Strategy C (which may plan a path that doesn't reproduce).
Mitigation: PathBuffer's existing invalidation mechanism catches this — if a buffered action produces no state change (hash unchanged), the buffer is cleared. Strategy C paths are typically short (2-3 steps on learned transitions), limiting the blast radius of a stale path. The worst case is wasting 1-2 iterations.

**[PathBuffer dialog dismiss in Strategy A]** When PathBuffer plans a backtrack path of N BACK actions, an intermediate BACK may dismiss a dialog instead of popping the navigation stack. The hash changes (dialog dismissed), so the buffer does NOT invalidate, and the next BACK executes on an unexpected screen. This can waste 1-2 iterations before the buffer completes or another invalidation triggers.
Accepted risk: The `MAX_BACKTRACK_HOPS` limit (8) bounds the waste. The hash-unchanged invalidation catches complete failures (BACK had no effect). For Strategy A, a few wasted BACKs are preferable to the complexity of tracking expected-next-hash for each buffered step. Strategy B (MOP navigation with specific clicks) is more vulnerable to this, but Strategy B paths are typically shorter (2-3 steps) and go through real navigation clicks, not just BACKs.

**[PathBuffer uses single-action transitions, not full action sequences]** SuccessorTracker records only the **last action** that triggered a state hash change, not the full action sequence that preceded it. For example, if filling a form required 3 SET_TEXT actions followed by a "Submit" click, SuccessorTracker stores only `(form_hash, submit_click) → result_hash`. `DynamicStateGraph.transitions` stores the complete `action_sequence: List[Dict]` (all 4 actions), but PathBuffer queries SuccessorTracker, not the transition list. This means Strategy C (coverage BFS on learned transitions) may attempt to replay a transition by executing only the final action, without the prerequisite form fills.
Accepted trade-off: The hash-unchanged invalidation handles the most common failure case — the submit click alone has no effect (e.g., form validation prevents navigation), so the hash stays the same and PathBuffer invalidates. However, there are cases where the single action produces a *different* state change than expected (e.g., submitting an empty form triggers an error screen instead of the success screen). In these cases, the hash changes (so invalidation does not trigger) but the agent is on an unexpected screen. The worst case is 1-2 wasted iterations before the buffer completes or Tier 2-5 selection takes over. Using the full `action_sequence` from `DynamicStateGraph.transitions` would require O(n) list scans (vs SuccessorTracker's O(1) dict lookup), replaying prerequisite actions that may not be valid in the current screen state, and tracking which intermediate actions apply to which UI elements — complexity disproportionate to the benefit. PathBuffer is a navigation tool (get to a target screen), not a form-filling tool (reproduce exact input sequences).

## Testing Strategy

| Layer | What to Test | How | Count |
|-------|-------------|-----|-------|
| **Unit** | `PathBuffer.plan_backtrack_path()` with mock SuccessorTracker | Mock SuccessorTracker returns known ancestors, verify BACK actions buffered | ~2 tests |
| **Unit** | `PathBuffer.plan_mop_path()` with mock TransitionManager | Mock WTG with known graph, verify BFS finds correct MOP-dense target | ~2 tests |
| **Unit** | `PathBuffer.get_next_action()` sequencing | Buffer 3 actions, verify sequential retrieval, verify empty after exhaustion | ~2 tests |
| **Unit** | `PathBuffer.invalidate()` | Buffer actions then invalidate, verify empty state | ~1 test |
| **Unit** | `RewardPropagator.propagate()` correctness | Known action history + reward, verify cumulative_reward values in ScreenNode | ~5 tests |
| **Unit** | `RewardPropagator.propagate()` with short history | History < N items, verify no crash and correct partial propagation | ~2 tests |
| **Unit** | `RewardPropagator.propagate()` discount calculation | Verify reward * gamma^distance formula for each step | ~2 tests |
| **Unit** | `should_backtrack()` with saturation threshold | States at 0.7, 0.8, 0.9, 1.0 saturation with threshold=0.8 | ~3 tests |
| **Unit** | `should_backtrack()` edge cases | Empty graph, single node, state not found, incomplete successors | ~3 tests |
| **Unit** | Scorer weight defaults verification | Verify MopScorer=500/300, WtgScorer=150, VisitationPenalty=-15, Stochastic=0.15 | ~2 tests |
| **Unit** | `MopScorer` form-context deferral | Verify MopScorer returns 0.0 for CLICK when `has_untested_inputs=True`, normal score for SET_TEXT, full +500 when `has_untested_inputs=False` | ~3 tests |
| **Unit** | `GradualDecayScorer` in active scorer list | Verify 9 scorers registered (7 existing + GradualDecayScorer + CoverageDensityScorer) | ~1 test |
| **Unit** | `StrengthScorer` with cumulative reward | Known strength + known cumulative_reward, verify combined score | ~3 tests |
| **Unit** | `InputValueGenerator` value ordering fix | Verify Faker values first for "text" type, PINs only for "password"/"pin" | ~3 tests |
| **Unit** | `InputValueGenerator` MOP limit | Verify `mop_max_input_variations=11` allows all 11 edge-case payloads | ~2 tests |
| **Unit** | `InputValueGenerator` new types | Verify search, url, date, time, number, zip, verification_code produce valid values | ~7 tests |
| **Unit** | `InputValueGenerator` no empty first value | Verify first value for all types is non-empty | ~2 tests |
| **Unit** | `TransitionManager.plan_path_to_mop_activity()` BFS | Mock WTG with known structure, verify shortest path to MOP-dense Activity | ~4 tests |
| **Unit** | `CoverageDensityScorer.score()` known destination | Mock SuccessorTracker with known destination, verify weight * coverage_gap | ~2 tests |
| **Unit** | `CoverageDensityScorer.score()` unknown destination | Action with no recorded transition, verify exploration bonus (weight * 0.5) | ~1 test |
| **Unit** | `CoverageDensityScorer` synergy with MopScorer | Both scorers contribute to same action, verify combined score correct | ~1 test |
| **Unit** | `CoverageDensityScorer` cold start | Few screens discovered, verify exploration bonuses dominate | ~1 test |
| **Unit** | `SuccessorTracker.get_action_destination()` | Known transition returns hash, unknown returns None | ~2 tests |
| **Unit** | `PathBuffer.plan_coverage_path()` with learned transitions | Mock SuccessorTracker with known graph, verify BFS finds highest exploration_potential target | ~2 tests |
| **Unit** | `PathBuffer.plan_coverage_path()` cold start | Fewer than 3 screens, verify returns False | ~1 test |
| **Unit** | `PathBuffer.plan_coverage_path()` max_hops limit | Target beyond MAX_COVERAGE_HOPS, verify not selected | ~1 test |
| **Integration** | Strategy C before B ordering | Both Strategy C and B available, verify C evaluated first | ~1 test |
| **Unit** | Config new fields | Verify 6 new config fields with defaults, ranges, serialization; verify 5 module-level constants | ~3 tests |
| **Integration** | Full strategy flow with proactive backtracking | Create graph with saturated states, verify BACK at threshold instead of continuous | ~3 tests |
| **Integration** | PathBuffer + strategy interaction | Buffer path, execute through strategy, verify buffer exhaustion triggers normal selection | ~3 tests |
| **Integration** | Reward propagation through learn_node | Execute 5 iterations, trigger MOP reward, verify ScreenNode cumulative_reward updated | ~3 tests |
| **Integration** | Speed optimization: algorithm iteration timing | Measure iteration time in pure_algorithm mode, verify < 1.5s per iteration | ~2 tests |
| **Integration** | Text input with clear-before-type | Set field content, call input, verify old content cleared before new text | ~2 tests |
| **Integration** | LLM MOP guidance prompt content | With mock static data, verify prompt contains MOP-specific hints | ~2 tests |
| **Regression** | Existing strategy unit tests | All existing `test_rvagent_strategy.py` tests pass unchanged | ~existing |
| **Regression** | Existing scorer tests | All existing scorer tests pass with new defaults | ~existing |
| **Regression** | Existing input generator tests | All existing InputValueGenerator tests pass with fixed ordering | ~existing |

**Estimated totals**: ~44 unit tests (new), ~16 integration tests (new), existing regression tests pass.

## Experimental Validation

Unit and integration tests verify correctness, but the 10 improvements interact non-linearly and their combined effect on exploration quality can only be measured empirically. This section defines a controlled A/B experiment: a baseline run (pre-gh26) and a validation run (post-gh26) on the same APK set, tools, and configuration.

### Experiment Design

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **APK set** | 30 APKs, SA-validated from 188 exp01_jca pool | 3x larger than original exp02 set (10); all 30 confirmed to produce .gesda/.wtg/.reach files with the current GESDA/GATOR/REACH pipeline. Stratified sampling ensures diversity across categories and size buckets |
| **Spec set** | JCA (23 specs) | Thesis focus; MOP coverage is the primary quality metric |
| **Tools** | `ape`, `fastbot`, `rvagent:pure_algorithm` | APE and Fastbot serve as unmodified reference baselines (sanity check); rvagent is the subject under test |
| **Timeout** | 300s (5 min) | Matches the standard experiment duration used in thesis experiments and gh9 calibration |
| **Repetitions** | 3 per (APK, tool) | Enough to compute mean ± std per APK; Wilcoxon paired observations = 30 APKs (mean of 3 reps each) |
| **Total tasks** | 270 (30 × 3 × 3) per phase | Two phases: baseline (270) + validation (270) = 540 total tasks |
| **Parallelism** | 2 Docker containers on laptop | Resource constraints: ~4 CPUs + 8GB RAM per container; staggered start (RV_DELAY=0, 10) to avoid KVM boot races |

### Dataset Rebuild: Why exp02 Was Replaced

The original 10 exp02 APKs could not all be instrumented or produce the 3 required static analysis files (.gesda, .wtg, .reach) with the current GESDA/GATOR/REACH pipeline. The `exp01_jca=True` flag in `apks_complete.csv` only guarantees compatibility with the OLD Androguard-based SA pipeline, not the current pipeline. Additionally, n=10 provides low statistical power for Wilcoxon signed-rank tests — n=30 substantially increases power to detect medium effect sizes.

The replacement uses a 4-step pipeline:

1. **Extract**: Filter `apks_complete.csv` for `exp01_jca=True` → 188 APKs
2. **Pre-select**: Stratified sampling (`scripts/select_dataset.py --cal-size 65 --seed 42`) → 65 APKs balanced across categories and size buckets
3. **SA filter**: Run `scripts/filter_apks_static_analysis.py` on the 65 APKs with GESDA, GATOR, REACH (timeout 600s each, 2 workers). APKs that produce all 3 output files pass; others are discarded. Expected yield: ~40-55 APKs
4. **Final selection**: Stratified sampling on SA-passed set (`scripts/select_dataset.py --cal-size 30 --seed 42`) → 30 APKs for the experiment

The SA filter output from the baseline is reused in the validation experiment via `RV_SKIP_STATIC_ANALYSIS=true` and volume mount of the baseline's `results/` directory for instrumented APKs + SA files.

Data artifacts (gitignored, in `out/`):
- `out/gh26_dataset/all_jca_apks.txt` — 188 APKs from step 1
- `out/gh26_dataset/preselection/` — 65 APKs from step 2
- `out/gh26_sa_filter/` — SA filter results from step 3
- `out/gh26_dataset/final_selection/` — 30 APKs from step 4

### APK Set (SA-validated, 30 APKs)

The 30 APKs are selected via the pipeline above. The specific APK list is recorded in `tasks.md` Group 0 after SA filter completes. Criteria: `exp01_jca=True`, all 3 SA files (.gesda, .wtg, .reach) produced successfully, stratified across categories and size buckets (tiny/small/medium/large/xlarge by method count).

### Docker Execution Architecture

Follows the container-level parallelism pattern from gh9 and rvsec-02. Each phase has its own docker-compose file.

**Phase 0 — Baseline** (2 containers, ~11.5 hours):

Each container runs the full pipeline (monitors + instrument + static analysis + execution). Pre-processing adds ~75 min per container. 2 batches of 15 APKs each, running in parallel.

```
docker-compose.baseline.yml
  ├── batch_0: (15 APKs)
  │     image: phtcosta/rvandroid (pre-gh26 codebase)
  │     RV_TOOLS=ape,fastbot,rvagent:pure_algorithm
  │     RV_TIMEOUTS=300, RV_REPETITIONS=3, RV_JCA_SPEC=true
  │     RV_DELAY=0
  │     volumes: original_apks/:ro → results/baseline/batch_0/
  └── batch_1: (15 APKs)
        same config, RV_DELAY=10
        volumes: → results/baseline/batch_1/
```

Calculation: preprocessing ~75min/container + (135 tasks × 5min) = ~11.5h per container. 2 containers in parallel.

**Phase 1 — Validation** (2 containers, ~11.5 hours):

```
docker-compose.validation.yml
  ├── batch_0: (15 APKs)
  │     image: phtcosta/rvandroid:gh26-validation (post-gh26 codebase)
  │     RV_SKIP_STATIC_ANALYSIS=true (reuse baseline SA artifacts)
  │     volumes: results/baseline/batch_0/:ro → instrumented APKs + SA files
  │     (all other config identical to baseline)
  └── batch_1: (15 APKs)
        same config, volumes: results/baseline/batch_1/:ro
```

All docker-compose files are stored in `docker/data/gh26_experiment/`. Validation containers reuse instrumented APKs and SA files (.gesda/.wtg/.reach) from the baseline via `RV_SKIP_STATIC_ANALYSIS=true` and read-only volume mounts, avoiding redundant ~75-minute preprocessing. Instrumentation is deterministic, so baseline artifacts are valid for validation — only rv-agent code changes between baseline and validation images.

**Phase 1b — No-SA Validation** (optional, 2 containers, ~11.5 hours):

```
docker-compose.validation-nosa.yml
  ├── batch_0: (15 APKs)
  │     image: phtcosta/rvandroid:gh26-validation
  │     RV_SKIP_STATIC_ANALYSIS=true for rvagent:pure_algorithm only
  │     (ape/fastbot unchanged)
  └── batch_1: (15 APKs)
```

This optional variant validates that CoverageDensityScorer + Strategy C provide meaningful exploration efficiency even without static analysis data (the "warm no-SA" scenario). Compares against both baseline and validation-with-SA to isolate the dual guidance contribution.

### Time Budget (12h window)

| Config | APKs | Tools | Reps | Tasks | Per Container | Est. Time |
|--------|------|-------|------|-------|---------------|-----------|
| A (chosen) | 30 | 3 | 3 | 270 | 135 tasks | ~11.5h |
| B (fallback) | 30 | 3 | 2 | 180 | 90 tasks | ~8h |
| C (fallback) | 25 | 3 | 3 | 225 | ~113 tasks | ~10h |

Config A maximizes statistical power (30 observations per tool) and fits within 12h. If SA filter yields fewer than 30 passing APKs, fall back to Config C.

### Comparison Metrics

**Cross-tool metrics** (from `summary.csv`, available for all 3 tools):

| Metric | Source | What it measures |
|--------|--------|-----------------|
| `cov_method` | summary.csv | % of reachable methods executed (REACH denominator) |
| `cov_act` | summary.csv | % of app activities visited |
| `cov_rv_method` | summary.csv | % of MOP-reachable methods executed |
| `errors` | summary.csv | Count of runtime verification violations detected |

**RVAgent-specific metrics** (from `rvagent_metrics.json`, only for `rvagent:pure_algorithm`):

| Metric | Source | What it measures |
|--------|--------|-----------------|
| Unique states | `exploration.unique_states` | Count of distinct screen states — measures exploration breadth |
| Iterations | `exploration.iterations` | Total agent iterations — measures throughput |
| Execution time | `exploration.execution_time_s` | Agent wall-clock time — for computing mean iteration time |
| UI element coverage | `ui_coverage.element_coverage` | % of discovered UI elements tested — measures interaction breadth |
| Screens visited | `ui_coverage.screens_visited` | Count of distinct screens — measures navigation breadth |
| Coverage per screen | `ui_coverage.coverage_per_screen` | Per-screen element coverage — identifies undertested screens |
| Action distribution | `ui_coverage.interactions_by_type` | Actions grouped by element type (Button, EditText, etc.) — measures coverage diversity |

**RVTRACK .trace file**:

RVTRACK entries (`[RVTRACK:<CATEGORY>]`) are persisted to a `.trace` file alongside `rvagent_metrics.json` by reusing the existing `metrics_output_dir` config field. In `RVAgent.run()`, a Python `FileHandler` is attached to the `rv_agent` logger after app launch and removed before return. The file naming follows the same convention as metrics JSON: `{package}__{rep}__{timeout}__rvagent:{mode}.trace`.

This works in both execution paths without any new config field:
- **Via rv-platform**: `rvagent_tool/config.py` already maps `task.results_dir` → `config.metrics_output_dir`. The `.trace` file lands in `results/<experiment>/<apk>/` alongside `.logcat` and `rvagent_metrics.json`.
- **Standalone CLI**: `cli/main.py` already maps `--results-dir` → `config.metrics_output_dir`. The `.trace` file lands in the same directory as metrics.
- **Unconfigured** (`metrics_output_dir=None`): No FileHandler is added; RVTRACK entries go to stdout only (unit tests, no side-effects).

Post-gh26, task 9.5 adds aggregate counters to `rvagent_metrics.json` (backtrack_count, path_buffer_hit_rate, reward_propagation_events, coverage_navigation_events). The `.trace` file captures ALL per-iteration RVTRACK entries (detailed logs), while `rvagent_metrics.json` has aggregate summaries. Both are complementary: `.trace` for debugging, metrics JSON for statistical analysis.

### Statistical Analysis

**Paired comparison design**: Each (APK, tool, repetition) triple in the baseline is paired with the same triple in the validation. This controls for APK complexity and tool characteristics.

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| **Test** | Wilcoxon signed-rank | Non-parametric, paired, does not assume normal distribution |
| **Sample size** | n=30 per tool (30 APKs, mean of 3 reps each) | 3x larger than original n=10; much higher power to detect medium effect sizes. 30 APKs × 3 reps = 90 observations per tool |
| **Effect size** | r = Z / √n | Standardized effect size for non-parametric tests; with n=30, r is more precisely estimated |
| **Significance** | α=0.05, two-tailed | Standard threshold; report exact p-values |
| **Multiple comparisons** | Report per-metric, flag if Bonferroni-corrected p > 0.05 | 4 metrics × 3 tools = 12 tests; conservative correction |

**Expected outcomes**:
- `rvagent:pure_algorithm`: statistically significant improvement in `cov_method` and `errors` (from proactive backtracking + PathBuffer + reward propagation)
- `ape`, `fastbot`: no significant change (unmodified tools — serve as sanity check that the experiment infrastructure is stable)
- If rvagent shows regression in any metric, investigate per-APK breakdown and tracking logs to identify which improvement caused it

### Relationship to gh9 Calibration

This experiment uses **default parameter values** (the 6 new config fields at their defaults, plus 5 module-level constants at their fixed values). It does NOT optimize parameters — that is gh9's responsibility. The purpose is to verify that the gh26 code changes produce measurable improvement even with untuned defaults. gh9 will later find optimal values for the 6 calibratable parameters using Optuna on a larger APK set (75 calibration + 30 holdout).

## Open Questions

1. **GradualDecayScorer initial weight and decay rate**: The current defaults (base=200, rate=0.7, min_visits=5) were set when the scorer was written but never tested in production. These values may need adjustment during gh9 calibration. The design uses the existing defaults and defers optimization to gh9. Note: `visits` in the formula refers to per-element visit counts from `UICoverageTracker` (accessed via `context.ui_coverage.get_element_test_count(element_id)`), not ScreenNode action counts.

2. **LLM-generated text tracking**: **Resolved — use `tested_values`.** When the LLM generates a SET_TEXT action, the text is recorded in `InputValueGenerator.tested_values` for the corresponding field. This prevents the algorithm path from repeating the same value when it later encounters the same field. The risk of conflating LLM creativity with algorithmic exhaustion is acceptable because: (a) the LLM rarely generates the same text twice, so collision is rare; (b) preventing repetition is more important than preserving LLM variability. See task 2.6.

3. **PathBuffer Strategy ordering (C > B > A)**: When multiple strategies can produce a path, the evaluation order is: Strategy C (coverage navigation) first, then Strategy B (MOP-directed), then Strategy A (backtrack to unsaturated ancestor). Strategy C is first because broad UI coverage addresses the "small island" problem, increasing the probability surface for finding MOP methods. Strategy B provides MOP-directed precision when static analysis data is available. Strategy A is the fallback for backtracking to unsaturated ancestors. This ordering may need to be configurable if gh9 calibration reveals different optimal behavior for specific APK categories.

4. **Reward propagation for error recovery actions**: gh18's error recovery actions (SET_TEXT/CLICK with `decision_maker="error_recovery"`) should participate in reward propagation -- if an error recovery SET_TEXT leads to a successful MOP trigger, that reward should propagate back through the error recovery sequence. The implementation must include error recovery actions in the action history, not filter them out.

5. **CoverageDensityScorer cold start transition threshold**: The scorer returns exploration bonuses (weight * 0.5) for unknown destinations during early exploration. When exactly should it transition from exploration-bonus-dominated to learned-data-dominated scoring? The current design uses "fewer than 3 screens" as the cold start threshold for Strategy C's `plan_coverage_path()`. For the scorer itself, the transition is implicit — as more destinations become known, the exploration bonus fraction decreases naturally. gh9 calibration may reveal a need for an explicit cold start threshold parameter.
