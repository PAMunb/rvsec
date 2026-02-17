# Design: Exploration Strategy Improvements

**GitHub Issue**: #26
**Proposal**: `openspec/changes/gh26-exploration-strategy/proposal.md`
**Analysis**: `docs/20260216_rvagent_refatoracao.md`

## Context

rv-agent's exploration strategy (`RVAgentStrategy`) selects one action per iteration using a scorer-ranked list of untested actions, falling back to least-executed actions when all have been tested at least once. This approach has five architectural bottlenecks that calibration alone cannot fix:

1. **Passive backtracking**: When all actions in a state are tested, the strategy enters "continuous mode" -- re-executing the least-tested action instead of navigating BACK to explore other states. The existing `should_backtrack()` method and `state_stack` are maintained but never called for navigation decisions. This wastes an estimated 20-40% of the iteration budget in saturated states, because the agent only leaves via stuck detection (8+ unchanged iterations) or Level 2 recovery.

2. **Scorer weight imbalance**: WTG score (+250) is nearly equal to MOP-direct (+300) and higher than MOP-transitive (+150). A non-MOP action leading to an unvisited screen outscores a MOP-transitive action. This causes the agent to prefer general screen exploration over paths to monitored operations.

3. **No adaptive learning**: Scorer weights are fixed throughout the experiment. An action that consistently fails to produce new states receives the same MOP/WTG score as one that leads to productive exploration. Neither APE-style model refinement nor Fastbot-style Q-value convergence exists.

4. **Text input bugs**: The `InputValueGenerator` has six bugs that waste 20-40% of text input iterations: duplicate input type inference (shallow `_infer_input_type()` in strategy ignores hint/content_description data), wrong default value ordering (PINs as first values for non-PIN fields), LLM path bypassing the generator entirely, `max_variations=5` blocking MOP edge cases (only 5 of 11 payloads tested), missing input types (search, url, date, time, number, zip, verification_code), and no clear-before-type causing text to append to existing field content.

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
  │    ├── 1. PathBuffer.get_next_action() ──→ if buffered path, return action
  │    ├── 2. _get_untested_actions() ──→ ActionRanker.score_action()
  │    │       │                              │
  │    │       │                    ┌─────────┼─────────────────┐
  │    │       │                    ▼         ▼                 ▼
  │    │       │              MopScorer  WtgScorer  GradualDecayScorer
  │    │       │              (+500/+300) (+150)     (200*0.7^visits)
  │    │       │                    │         │                 │
  │    │       │                    ▼         ▼                 ▼
  │    │       │              StrengthScorer (+ cumulative_reward)
  │    │       │              [reward from RewardPropagator]
  │    │       │
  │    ├── 3. should_backtrack(saturation_threshold) ──→ BACK
  │    ├── 4. PathBuffer.plan_mop_path() / plan_backtrack_path()
  │    ├── 5. _select_least_executed_action() (continuous fallback)
  │    └── 6. BACK (final fallback)
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
| `RVAgentStrategy.select_next_action()` | New 6-tier action selection flow | `strategies/rvagent_strategy/rvagent_strategy.py` | Modified |
| `PathBuffer` | Multi-step navigation path management | `strategies/rvagent_strategy/path_buffer.py` | New |
| `RewardPropagator` | N-step backward reward propagation | `strategies/rvagent_strategy/reward_propagator.py` | New |
| `ActionRanker` | Composite scoring with rebalanced weights + GradualDecayScorer | `strategies/rvagent_strategy/ranking/action_ranker.py` | Modified |
| `StrengthScorer` | Historical success rate + cumulative reward | `strategies/rvagent_strategy/ranking/scorers.py` | Modified |
| `InputValueGenerator` | Text value generation with bug fixes | `strategies/rvagent_strategy/input_value_generator.py` | Modified |
| `TransitionManager` | Gains BFS path planning to MOP-dense Activities | `services/transition_manager.py` | Modified |
| `NavigationGuidance` | MOP-specific LLM prompt enrichment | `services/navigation_guidance.py` | Modified |
| `RVAgentConfig` | 8 new calibration parameters | `config/agent_config.py` | Modified |
| `ScreenNode` | New `action_cumulative_reward` field | `domain/screen_node.py` | Modified |
| `SuccessorTracker.find_nearest_unsaturated()` | Return type change: `Optional[str]` → `Optional[Tuple[str, int]]` (ancestor_hash, bfs_hop_count) | `strategies/rvagent_strategy/successor_tracker.py` | Modified |
| `RVAgent._build_agent_graph()` | No topology change needed — algorithm path already bypasses screenshot/LLM nodes via existing conditional edges | `agent/rv_agent.py` | Unchanged |
| `decision_router_node` | Mode-aware routing (existing); add tracking log for algorithm-fast-path | `agent/nodes/decision_node.py` | Modified |
| `learn_node` | Reward propagation trigger after action success recording | `agent/nodes/learn_node.py` | Modified |

## Mapping: Spec → Implementation → Test

| Requirement / Change | FR | Implementation Files | Test Files |
|---|---|---|---|
| Proactive backtracking (new action selection order) | FR26 | `rvagent_strategy.py` (select_next_action) | `test_proactive_backtracking.py`, `test_should_backtrack.py` |
| PathBuffer integration | FR26, FR30 | `path_buffer.py` (new), `rvagent_strategy.py` | `test_path_buffer.py`, `test_strategy_path_buffer_integration.py` |
| Saturation threshold | FR26 | `rvagent_strategy.py`, `agent_config.py` | `test_saturation_threshold.py` |
| Scorer rebalancing (new defaults) | FR27 | `agent_config.py` (default values) | `test_scorer_weights.py` |
| GradualDecayScorer activation | FR27 | `rvagent_strategy.py` (__init__ scorer list) | `test_gradual_decay_scorer.py` |
| N-step reward propagation | FR27 | `reward_propagator.py` (new), `learn_node.py`, `scorers.py` (StrengthScorer), `screen_node.py` | `test_reward_propagator.py`, `test_strength_scorer_reward.py` |
| Speed optimization (parse_node caching) | FR24 | `parse_node.py`, `decision_node.py` (tracking only) | `test_speed_optimization.py` |
| LLM MOP guidance | FR24, FR30 | `navigation_guidance.py`, `prompts/v13.py` | `test_mop_guidance.py` |
| Text input quality (6 bug fixes) | FR26 | `input_value_generator.py`, `rvagent_strategy.py`, `execution/tool_executor.py` | `test_input_value_generator.py` |
| BFS path planning to MOP Activities | FR30 | `transition_manager.py` | `test_transition_manager_bfs.py` |
| SuccessorTracker return type change | FR26 | `successor_tracker.py` (find_nearest_unsaturated returns Tuple[str, int]) | `test_find_nearest_unsaturated_hop_count.py` |
| Reduced stuck trigger frequency | FR29 | (indirect -- proactive backtracking leaves saturated states earlier) | `test_stuck_detection_with_backtracking.py` |
| New config parameters (8 fields) | -- | `agent_config.py` | `test_config_new_params.py` |

## Goals / Non-Goals

**Goals:**

- Fix passive backtracking by introducing proactive BACK when saturation threshold is exceeded, recovering ~20-40% of wasted iterations
- Rebalance scorer weights so MOP-direct (+500) > MOP-transitive (+300) > WTG (+150), ensuring the agent prioritizes monitored operation paths
- Fix six text input bugs in `InputValueGenerator` to stop wasting iterations on PINs in non-PIN fields and enable all 11 MOP edge-case payloads
- Add `PathBuffer` for multi-step navigation paths (backtrack to unsaturated ancestor, navigate to MOP-dense Activity via BFS)
- Add `RewardPropagator` for simplified N-step reward propagation through action chains, extending `StrengthScorer` with cumulative reward data
- Optimize speed in `pure_algorithm` iterations by skipping screenshot capture and LLM nodes (per-iteration decision, mode-aware)
- Activate `GradualDecayScorer` for smoother action priority transitions
- Enrich LLM prompts with MOP-specific guidance from static analysis
- Add 8 new calibration parameters to `RVAgentConfig` for downstream gh9 tuning (including `reward_score_weight` to control cumulative reward influence in StrengthScorer)

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

**Rationale**: A separate class with clear lifecycle (`plan_backtrack_path()`, `plan_mop_path()`, `get_next_action()`, `invalidate()`) is independently testable and keeps `select_next_action()` focused on action selection. The PathBuffer holds transient state (a list of planned actions) that is conceptually different from the DFS graph state.

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

## API Design

### PathBuffer

```python
# strategies/rvagent_strategy/path_buffer.py

class PathBuffer:
    """
    Manages multi-step navigation paths for proactive exploration.

    Two strategies:
    A) Backtrack to nearest unsaturated ancestor via SuccessorTracker
    B) Navigate toward MOP-dense Activity via BFS on WTG
    """

    def __init__(
        self,
        transition_manager: Optional["TransitionManager"],
        successor_tracker: "SuccessorTracker",
        config: "RVAgentConfig"
    ):
        """
        Args:
            transition_manager: For WTG-based BFS (Strategy B). None disables Strategy B.
            successor_tracker: For ancestor navigation (Strategy A).
            config: Configuration with path_buffer_enabled and mop_nav_weight.
        """

    def get_next_action(self) -> Optional[ItemAction]:
        """
        Get next buffered action, or None if buffer is empty.

        Postcondition: Advances internal pointer. If this was the last action in the
        buffer, the buffer becomes empty.

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
        """

    @property
    def is_active(self) -> bool:
        """True if buffer contains actions to execute."""

    @property
    def remaining_steps(self) -> int:
        """Number of actions remaining in the buffer."""
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
    REWARD_NEW_STATE: float = 1.0
    REWARD_NEW_ACTIVITY: float = 2.0
    REWARD_MOP_REACHED: float = 5.0

    # Cumulative reward cap: prevents score inflation from repeated MOP sequences.
    # Max cumulative reward = MAX_CUMULATIVE_REWARD_FACTOR * config.reward_mop_weight
    # With default reward_mop_weight=5.0, cap = 3.0 * 5.0 = 15.0
    MAX_CUMULATIVE_REWARD_FACTOR: float = 3.0

    def __init__(self, config: "RVAgentConfig"):
        """
        Args:
            config: Configuration with reward_gamma, reward_mop_weight,
                    reward_propagation_n.

        Internal state:
            _action_history: deque(maxlen=reward_propagation_n) of
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
        reward_propagation_n entries.

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

        Args:
            reward_type: One of "same_state", "new_state", "new_activity", "mop_reached".
            graph: DynamicStateGraph for accessing ScreenNode data.

        Postcondition: Updates action_cumulative_reward in ScreenNode for each
        action within the propagation window. Cumulative reward is capped at
        `MAX_CUMULATIVE_REWARD_FACTOR * config.reward_mop_weight` (default 3.0 * 5.0
        = 15.0) to prevent score inflation from repeated MOP-reaching sequences.

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

New 6-tier action selection flow:

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
        selected = self._select_priority_action(untested_actions, screen_desc)
        # ... existing pre-marking and input handling ...
        return selected

    # Tier 3: Proactive backtracking — check saturation threshold
    if self.should_backtrack(current_hash):
        # Try to plan a path before plain BACK
        if self.path_buffer.plan_mop_path(screen_desc.activity, self._get_mop_data()):
            return self.path_buffer.get_next_action()
        if self.path_buffer.plan_backtrack_path(current_hash):
            return self.path_buffer.get_next_action()
        return self._create_back_action()

    # Tier 4: Continuous mode (least-executed) — only as last resort
    all_filtered = self._get_all_filtered_actions(screen_desc)
    if all_filtered:
        scroll_action = self._try_generate_scroll_action(...)
        if scroll_action:
            return scroll_action
        selected = self._select_least_executed_action(node, all_filtered)
        if selected:
            return selected

    # Tier 5: Final BACK fallback
    return self._create_back_action()
```

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
    # MAX_CUMULATIVE_REWARD_FACTOR * config.reward_mop_weight (default 15.0),
    # so no additional capping is needed here.
    cumulative_reward = node.action_cumulative_reward.get(action_signature, 0.0)

    return self.weight * strength + config.reward_score_weight * cumulative_reward
```

### Modified: InputValueGenerator.get_next_value()

Key changes:
- `_get_regular_values()`: Faker values first; PINs only for password/pin type; no empty string as first value
- `_get_mop_values()`: Uses `mop_max_input_variations` (default 11) instead of `max_variations` (default 5)
- New input types: search, url, date, time, number, zip, verification_code with Faker generators
- `_infer_input_type()` deleted from strategy; input type extracted from action's `text` field or `enhanced_visitor` data

### New RVAgentConfig fields

```python
# Added to config/agent_config.py

# Backtracking
backtrack_saturation_threshold: float = Field(
    default=0.8, ge=0.5, le=1.0,
    description="Saturation rate threshold for proactive backtracking"
)

# Path buffer
path_buffer_enabled: bool = Field(
    default=True,
    description="Enable PathBuffer for multi-step navigation"
)
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
reward_mop_weight: float = Field(
    default=5.0, ge=1.0, le=10.0,
    description="Reward value for reaching a MOP method"
)
reward_propagation_n: int = Field(
    default=5, ge=3, le=8,
    description="Number of steps for backward reward propagation"
)
reward_score_weight: float = Field(
    default=1.0, ge=0.1, le=3.0,
    description="Weight of cumulative_reward in StrengthScorer. Controls how much "
                "reward propagation influences action ranking relative to historical "
                "strength. Formula: weight * strength + reward_score_weight * cumulative_reward"
)
```

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
   │     ├── MopScorer: +500 (DM), +300 (M)
   │     ├── WtgScorer: +150
   │     ├── GradualDecayScorer: 200 * 0.7^visits [NEW — activated; visits from UICoverageTracker]
   │     ├── SaturationScorer: +100 * (1 - sat_rate)
   │     ├── ComponentPriorityScorer: +50/+40
   │     ├── StrengthScorer: weight * strength + reward_score_weight * cumulative_reward [NEW]
   │     ├── FailedActionScorer: -9999
   │     ├── SystemElementFilter: -5000
   │     └── VisitationPenaltyScorer: -15 * log(1 + visits)
   ├── Tier 3: should_backtrack(threshold=0.8) → plan path or BACK
   │     ├── PathBuffer.plan_mop_path() → BFS to MOP-dense Activity
   │     └── PathBuffer.plan_backtrack_path() → BACK to unsaturated ancestor
   ├── Tier 4: Continuous mode (scroll + least-executed)
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
   │     ├── Determine reward_type from state change + MOP proxy signal
   │     │     ├── same_state → -0.1
   │     │     ├── new_state → 1.0
   │     │     ├── new_activity → 2.0
   │     │     └── mop_reached → 5.0 (when selected_action.callback_signature is present)
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

The `learn_node` determines the `REWARD_MOP_REACHED` reward type by checking `selected_action.callback_signature` from `AgentState`. When `callback_signature` is present (non-None, non-empty), it means the selected action is associated with a monitored operation method — this is a proxy signal that "the action CAN reach MOP." This is not real-time MOP detection (which would require logcat parsing within the 300s window), but a pragmatic heuristic: actions linked to `callback_signature` have the structural potential to trigger monitored API calls. The reward values for the other types (same state, new state, new Activity) are determined by comparing `current_screen_hash` with `previous_screen_hash` and checking whether the Activity has been seen before.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| PathBuffer reaches unexpected state | `learn_node` detects hash mismatch with buffer expectation | Call `PathBuffer.invalidate()`, log warning | Normal action selection resumes (Tier 2-5) |
| PathBuffer BFS finds no path | `plan_mop_path()` or `plan_backtrack_path()` returns False | Return False, caller falls through to next tier | Strategy proceeds to continuous mode or BACK |
| Reward propagation on short history | Internal action history has < N items | Propagate through all available items | No error; works correctly with any history length >= 1 |
| Missing static analysis data | `TransitionManager` has no WTG, or `StaticAnalysisData` is None | MopScorer returns 0.0, WtgScorer returns 0.0, PathBuffer Strategy B disabled, NavigationGuidance returns empty | Agent operates as generic UI structure explorer; Strategy A (backtrack to unsaturated ancestor) still works |
| `should_backtrack()` on empty graph | State hash not in `graph.states` | Return True (backtrack from unknown state) | Agent navigates BACK, which is safe behavior for unknown states |
| `should_backtrack()` on single-node graph | Only one state, no parent | Return based on saturation check; no infinite BACK loop because Tier 4 continuous mode catches this | Least-executed action selected |
| `GradualDecayScorer` with missing element_id | Action has no `widget_id` and coordinates are None | Return 0.0 (neutral score) | Other scorers determine ranking |
| `InputValueGenerator` unknown input type | `_get_regular_values()` receives unrecognized type | Falls through to text default with Faker values (no longer PINs) | Generates sensible text input |
| Speed optimization skip in multimode | LLM iteration needs screenshot but algorithm iteration does not | Per-iteration decision in `decision_router_node`: "llm" path includes screenshot, "algorithm" path skips it | Both paths work correctly |

## Risks / Trade-offs

**[WTG score reduction]** Reducing WTG from 250 to 150 could hurt navigation through non-MOP intermediate screens that are necessary to reach MOP-containing Activities. For example, a "Settings" screen (no MOP methods) that leads to "Security Settings" (with MOP methods) would get lower WTG priority.
Mitigation: The ablation study (post-implementation) will measure this. If the +7.2 configuration step shows a regression, the WTG default should stay at 200-250 and gh9 calibration will find the optimal value. Additionally, PathBuffer Strategy B navigates through intermediate screens explicitly, partially compensating for lower WTG scores on individual actions.

**[should_backtrack() is untested dead code]** The method exists at `rvagent_strategy.py:447` but has never been called in production. It may contain bugs in edge cases (single-node graph, states removed from graph, successor tracker inconsistency).
Mitigation: Write comprehensive unit tests for `should_backtrack()` BEFORE integrating it into the action selection flow. Test cases must cover: saturated state, partially-explored state, state with incomplete successors, single-node graph, state not in graph, and the new saturation threshold behavior.

**[Non-independent gain estimates]** The 9 improvements interact non-linearly. Faster iterations (speed optimization) amplify better decisions (proactive backtracking, path buffer). Scorer rebalancing only matters WITH proactive backtracking since continuous mode bypasses the scorer system. The realistic combined gain is ~60-70% of the naive sum of individual estimates.
Mitigation: The ablation study quantifies actual per-improvement contribution by adding one improvement at a time to a baseline configuration (5 apps, 1 rep, 300s, 8 configurations). This provides thesis-quality evidence for each improvement's contribution.

**[Speed optimization mode-awareness]** Skipping screenshot capture in algorithm iterations must not break multimode LLM iterations. If the routing check has a bug, LLM iterations could run without screenshots, producing invalid actions.
Mitigation: The speed optimization is a conditional skip in `decision_router_node`, not a removal of the screenshot node from the graph. The LangGraph workflow still contains all nodes; the router simply sends algorithm iterations on the "algorithm" edge (which bypasses `capture_screenshot_node` by graph topology) while LLM iterations follow the "llm" edge (which includes `capture_screenshot_node`). This is the existing routing mechanism -- no new skip logic is needed for the LangGraph graph itself. The speed optimization focuses on caching `screen_desc` when hash is unchanged in `parse_node` and skipping unnecessary UIAutomator re-dumps.

**[PathBuffer stale path]** A buffered path may become invalid if the app's state changes unexpectedly (e.g., a notification dialog appears, app auto-navigates). The agent would execute the next buffered action on the wrong screen.
Mitigation: `learn_node` validates that the actual next state hash matches the PathBuffer's expectation. On mismatch, `PathBuffer.invalidate()` clears the buffer and normal action selection resumes. This adds one hash comparison per iteration when the buffer is active -- negligible cost.

## Testing Strategy

| Layer | What to Test | How | Count |
|-------|-------------|-----|-------|
| **Unit** | `PathBuffer.plan_backtrack_path()` with mock SuccessorTracker | Mock SuccessorTracker returns known ancestors, verify BACK actions buffered | ~5 tests |
| **Unit** | `PathBuffer.plan_mop_path()` with mock TransitionManager | Mock WTG with known graph, verify BFS finds correct MOP-dense target | ~5 tests |
| **Unit** | `PathBuffer.get_next_action()` sequencing | Buffer 3 actions, verify sequential retrieval, verify empty after exhaustion | ~3 tests |
| **Unit** | `PathBuffer.invalidate()` | Buffer actions then invalidate, verify empty state | ~2 tests |
| **Unit** | `RewardPropagator.propagate()` correctness | Known action history + reward, verify cumulative_reward values in ScreenNode | ~5 tests |
| **Unit** | `RewardPropagator.propagate()` with short history | History < N items, verify no crash and correct partial propagation | ~2 tests |
| **Unit** | `RewardPropagator.propagate()` discount calculation | Verify reward * gamma^distance formula for each step | ~2 tests |
| **Unit** | `should_backtrack()` with saturation threshold | States at 0.7, 0.8, 0.9, 1.0 saturation with threshold=0.8 | ~4 tests |
| **Unit** | `should_backtrack()` edge cases | Empty graph, single node, state not found, incomplete successors | ~4 tests |
| **Unit** | Scorer weight defaults verification | Verify MopScorer=500/300, WtgScorer=150, VisitationPenalty=-15, Stochastic=0.15 | ~2 tests |
| **Unit** | `GradualDecayScorer` in active scorer list | Verify 9 scorers registered (8 existing + GradualDecayScorer) | ~1 test |
| **Unit** | `StrengthScorer` with cumulative reward | Known strength + known cumulative_reward, verify combined score | ~3 tests |
| **Unit** | `InputValueGenerator` value ordering fix | Verify Faker values first for "text" type, PINs only for "password"/"pin" | ~3 tests |
| **Unit** | `InputValueGenerator` MOP limit | Verify `mop_max_input_variations=11` allows all 11 edge-case payloads | ~2 tests |
| **Unit** | `InputValueGenerator` new types | Verify search, url, date, time, number, zip, verification_code produce valid values | ~7 tests |
| **Unit** | `InputValueGenerator` no empty first value | Verify first value for all types is non-empty | ~2 tests |
| **Unit** | `TransitionManager.plan_path_to_mop_activity()` BFS | Mock WTG with known structure, verify shortest path to MOP-dense Activity | ~4 tests |
| **Unit** | Config new fields | Verify 8 new fields with defaults, ranges, and serialization | ~3 tests |
| **Integration** | Full strategy flow with proactive backtracking | Create graph with saturated states, verify BACK at threshold instead of continuous | ~3 tests |
| **Integration** | PathBuffer + strategy interaction | Buffer path, execute through strategy, verify buffer exhaustion triggers normal selection | ~3 tests |
| **Integration** | Reward propagation through learn_node | Execute 5 iterations, trigger MOP reward, verify ScreenNode cumulative_reward updated | ~3 tests |
| **Integration** | Speed optimization: algorithm iteration timing | Measure iteration time in pure_algorithm mode, verify < 1.5s per iteration | ~2 tests |
| **Integration** | Text input with clear-before-type | Set field content, call input, verify old content cleared before new text | ~2 tests |
| **Integration** | LLM MOP guidance prompt content | With mock static data, verify prompt contains MOP-specific hints | ~2 tests |
| **Regression** | Existing strategy unit tests | All existing `test_rvagent_strategy.py` tests pass unchanged | ~existing |
| **Regression** | Existing scorer tests | All existing scorer tests pass with new defaults | ~existing |
| **Regression** | Existing input generator tests | All existing InputValueGenerator tests pass with fixed ordering | ~existing |

**Estimated totals**: ~40 unit tests (new), ~15 integration tests (new), existing regression tests pass.

## Open Questions

1. **GradualDecayScorer initial weight and decay rate**: The current defaults (base=200, rate=0.7, min_visits=5) were set when the scorer was written but never tested in production. These values may need adjustment during gh9 calibration. The design uses the existing defaults and defers optimization to gh9. Note: `visits` in the formula refers to per-element visit counts from `UICoverageTracker` (accessed via `context.ui_coverage.get_element_test_count(element_id)`), not ScreenNode action counts.

2. **LLM-generated text tracking**: **Resolved — use `tested_values`.** When the LLM generates a SET_TEXT action, the text is recorded in `InputValueGenerator.tested_values` for the corresponding field. This prevents the algorithm path from repeating the same value when it later encounters the same field. The risk of conflating LLM creativity with algorithmic exhaustion is acceptable because: (a) the LLM rarely generates the same text twice, so collision is rare; (b) preventing repetition is more important than preserving LLM variability. See task 2.6.

3. **PathBuffer Strategy B priority over Strategy A**: When both strategies can produce a path, which takes priority? The current design tries Strategy B (MOP-directed) first and Strategy A (backtrack to unsaturated ancestor) second, because MOP coverage is the primary metric. This ordering may need to be configurable if gh9 calibration reveals different optimal behavior.

4. **Reward propagation for error recovery actions**: gh18's error recovery actions (SET_TEXT/CLICK with `decision_maker="error_recovery"`) should participate in reward propagation -- if an error recovery SET_TEXT leads to a successful MOP trigger, that reward should propagate back through the error recovery sequence. The implementation must include error recovery actions in the action history, not filter them out.
