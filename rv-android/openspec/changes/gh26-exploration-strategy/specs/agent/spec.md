# Delta Specification: LLM Agent (gh26-exploration-strategy)

## Purpose

This delta specification modifies the LLM Agent domain to address architectural bottlenecks in rv-agent's exploration strategy. The current implementation wastes 20-40% of its iteration budget in saturated states because it retries already-tested actions (continuous mode) instead of proactively navigating to unexplored states. The scorer weights undervalue MOP-reaching actions relative to WTG navigation, the text input generator produces low-quality values, and there is no reward propagation to learn which action sequences lead to productive outcomes.

These changes fall into three categories: (1) proactive backtracking and saturation-aware navigation to replace passive continuous mode as the primary response to action exhaustion, (2) scorer rebalancing and reward propagation to steer the agent toward MOP-reaching action sequences, and (3) quality improvements to text input generation and speed optimization for pure_algorithm iterations. Together, they give the downstream calibration campaign (gh9) a sound architectural foundation to optimize.

This delta spec assumes gh18 (validation error detection) has already been implemented. The changes here do not conflict with gh18's modifications — file conflict analysis shows non-overlapping insertion points in all shared files (see `docs/20260216_rvagent_refatoracao.md` Section 9.1).

## Data Contracts

### Input

- `config.backtrack_saturation_threshold: float` -- Saturation rate threshold for proactive backtracking (0.5-1.0, default 0.8). When a state's saturation rate exceeds this value, the strategy triggers a BACK action instead of entering continuous mode. (from `RVAgentConfig`)
- `config.path_buffer_enabled: bool` -- Enable/disable PathBuffer for multi-step navigation (default True). (from `RVAgentConfig`)
- `config.mop_nav_weight: float` -- Weight of MOP density vs path length in BFS path planning (0.5-5.0, default 2.0). (from `RVAgentConfig`)
- `config.max_backtrack_hops: int` -- Maximum BACK actions PathBuffer can buffer for Strategy A backtrack paths (3-20, default 8). If the nearest unsaturated ancestor is farther than this limit, `plan_backtrack_path` returns False and the caller falls through to the next tier. (from `RVAgentConfig`)
- `config.mop_max_input_variations: int` -- Maximum input variations for MOP-relevant fields (5-15, default 11). (from `RVAgentConfig`)
- `config.reward_gamma: float` -- Discount factor for N-step reward propagation (0.5-0.99, default 0.8). (from `RVAgentConfig`)
- `config.reward_mop_weight: float` -- Reward value for reaching a MOP method (1.0-10.0, default 5.0). (from `RVAgentConfig`)
- `config.reward_propagation_n: int` -- Number of steps for backward reward propagation (3-8, default 5). (from `RVAgentConfig`)
- `config.reward_score_weight: float` -- Weight of cumulative_reward in StrengthScorer formula: `weight * strength + reward_score_weight * cumulative_reward` (0.1-3.0, default 1.0). Controls how much reward propagation influences action ranking relative to historical strength. (from `RVAgentConfig`)
- `config.coverage_density_weight: float` -- Weight for CoverageDensityScorer (50-400, default 200.0). Controls how strongly cross-screen coverage gap influences action ranking. Calibratable via gh9. (from `RVAgentConfig`)
- `config.max_coverage_hops: int` -- Maximum BFS depth for PathBuffer Strategy C coverage-based navigation (2-10, default 5). Limits how far the agent will navigate through learned transitions to reach a high-potential screen. (from `RVAgentConfig`)

### Output

- `results.backtrack_count: int` -- Number of proactive BACK actions triggered by `should_backtrack()` during the experiment
- `results.path_buffer_hit_rate: float` -- Percentage of buffered paths that successfully reached their target Activity
- `results.reward_propagation_events: int` -- Number of N-step reward propagation events during the experiment
- `results.coverage_navigation_events: int` -- Number of PathBuffer Strategy C coverage-based navigation events during the experiment

### Side-Effects

- **Tracking**: New `[RVTRACK:STRATEGY]` log entries for proactive backtracking events, path buffer hits/misses, reward propagation triggers, and `[RVTRACK:COVERAGE]` entries for coverage-based navigation events (Strategy C activations, target screen, exploration_potential score)

### Error

No new error types. Existing `RVAgentError` hierarchy applies.

## Invariants

- **INV-AGT-28**: The `PathBuffer` MUST clear its buffered path when a buffered action produces no state change (post-execution hash equals pre-execution hash). A navigation action that does not change the screen state (BACK that didn't navigate, click that didn't transition, dialog that blocked navigation) indicates the buffered path is no longer valid. The invalidation check uses hash comparison, not a predicted "expected next hash" — the PathBuffer does not need to predict exact destination hashes.

- **INV-AGT-29**: N-step reward propagation MUST propagate backward through at most `reward_propagation_n` actions (default 5). Each step MUST apply the discount factor `reward_gamma` (default 0.8) multiplicatively. The propagated reward for step k MUST be `reward_value * gamma^k`.

- **INV-AGT-30**: The `GradualDecayScorer` MUST be included in the active scorer list registered with `ActionRanker`. Its score formula MUST be `base_score * decay_rate^visits` where `base_score` defaults to 200 and `decay_rate` defaults to 0.7. When `visits >= min_visits` (default 5), the scorer MUST return 0.0 (full decay cutoff). This existing `min_visits` behavior is preserved; gh9 calibration may adjust or remove the cutoff.

- **INV-AGT-31**: When `backtrack_saturation_threshold` is configured, the strategy MUST trigger proactive backtracking when the current state's saturation rate exceeds the threshold. Saturation rate is defined as `actions_executed_at_least_threshold_times / total_actions` for the current `ScreenNode`, where `threshold` defaults to 2 (matching `ScreenNode.get_saturation_rate(threshold=2)`). An action counts as "saturated" when it has been executed at least `threshold` times, not merely once.

- **INV-AGT-32**: The `InputValueGenerator` MUST call `device.clear_text()` before `input_text()` for all SET_TEXT actions. Text MUST NOT be appended to existing field content.

- **INV-AGT-33**: The speed optimization for algorithm iterations operates at two levels. First, existing LangGraph graph topology: the `decision_router_node` routes to the `"algorithm"` edge, which bypasses `capture_screenshot_node` and `llm_generate_node` entirely — this is existing per-iteration routing behavior (not a compile-time flag), so multimode algorithm iterations also benefit. Second, NEW from gh26: in `parse_node`, when the current `screen_hash` equals `previous_screen_hash`, the node MUST reuse the cached `screen_desc` from the previous iteration instead of recomputing it. This screen_desc caching eliminates redundant UI parsing when the screen has not changed between iterations. The cache (`RVAgent._cached_screen_desc`) MUST be explicitly set to None on `force_restart_app` — an app restart may return to the same splash screen with identical hash, and reusing a stale cached screen_desc in that scenario would skip the fresh UI parse needed after restart.

- **INV-AGT-34**: `SuccessorTracker.find_nearest_unsaturated()` MUST return `Optional[Tuple[str, int]]` where the tuple contains `(state_hash, hop_count)` instead of the previous `Optional[str]`. The `hop_count` indicates the BFS distance (number of BACK actions) to reach the unsaturated ancestor. This return type is a prerequisite for `PathBuffer.plan_backtrack_path()`, which uses the hop_count to determine how many BACK actions to buffer for backtrack navigation.

- **INV-AGT-35**: `RewardPropagator` MUST cap `action_cumulative_reward` at `MAX_CUMULATIVE_REWARD_FACTOR * reward_mop_weight` (default 3.0 * 5.0 = 15.0). When a cumulative reward addition would exceed this cap, the value MUST be clamped to the cap instead of growing further. Without this cap, `StrengthScorer` scores could grow unbounded over long sessions (300+ iterations), inflating the reward signal and drowning out other scorer contributions.

- **INV-AGT-36**: The `CoverageDensityScorer` MUST be always active — always registered in the scorer list, not gated on whether `StaticAnalysisData` is present. When tracking data is unavailable (`context.successor_tracker` is None or `context.ui_coverage` is None), the scorer MUST return 0.0 (neutral, does not block action selection). For each candidate action, the scorer MUST query `SuccessorTracker.get_action_destination()` to determine the action's known destination state. If the destination is known, the score MUST be `coverage_density_weight * coverage_gap` where `coverage_gap = untested_elements / total_elements` for the destination screen (from `UICoverageTracker`). If the destination is unknown (action has never been executed or leads to an unrecorded state), the score MUST be `coverage_density_weight * 0.5` (exploration bonus for the unknown). The default `coverage_density_weight` is 200.0, placing CoverageDensityScorer in the same magnitude as `GradualDecayScorer` without overshadowing `MopScorer` (+500). The relative ordering is preserved: MOP-direct (500) > MOP-transitive (300) > Coverage (200) > WTG (150).

- **INV-AGT-37**: Saturation rate MUST only consider actionable (non-system) actions in both numerator and denominator. System actions (BACK, RESTART with `coordinates=None`) injected by the visitor MUST NOT inflate `total_actions` in `DynamicStateGraph.get_or_create_state()`. Without this correction, `get_saturation_rate()` returns N/(N+2) at maximum — screens with fewer than 8 real actions can never reach the 80% `backtrack_saturation_threshold`, rendering proactive backtracking (INV-AGT-31) ineffective for small screens. The visitor still injects BACK/RESTART for action selection; only the saturation denominator is affected.

- **INV-AGT-38**: When all path planning strategies fail in Tier 3 (all reachable states saturated — `plan_coverage_path()`, `plan_mop_path()`, and `plan_backtrack_path()` all return False), the agent MUST fall through to Tier 4 (scored continuous mode) and MUST NOT return a plain BACK action. In Tier 4, the agent MUST use `ActionRanker.rank_actions()` on ALL filtered actions (tested + untested) instead of `_select_least_executed_action()`. This ensures CoverageDensityScorer, MopScorer, GradualDecayScorer, and SaturationScorer guide re-testing priority during long runs (60-90% of 3-hour experiments operate in Tier 4). The agent MUST never stop selecting actions until timeout — the "never stop" contract is maintained by Tier 4's scored selection, not by a plain BACK fallback.

## MODIFIED Requirements

### Requirement: Coverage-Optimized DFS Strategy (FR26)

The `RVAgentStrategy` MUST implement a coverage-optimized depth-first search with successor state tracking, proactive saturation-based backtracking, path buffer integration, continuous exploration as a fallback, and pre-marking of actions.

**Action Selection Order**: The `select_next_action()` method MUST evaluate action sources in the following priority order:

1. **Path buffer**: If `PathBuffer` has a buffered path with remaining steps, execute the next buffered action. This takes highest priority because buffered paths represent multi-step navigation plans toward high-value targets (unsaturated ancestors or MOP-rich Activities).
2. **Untested actions**: If untested actions exist on the current screen, select one using `ActionRanker` with the full scorer system.
3. **Proactive backtracking**: If the state's saturation rate exceeds `backtrack_saturation_threshold` (default 0.8), try path planning (Strategy C > B > A). If a plan succeeds, buffer it and return the first action. If all plans fail (all reachable states saturated), fall through to Tier 4 — do NOT return a plain BACK. The `should_backtrack()` method — previously dead code — is activated to perform this saturation check.
4. **Scored continuous exploration**: Use `ActionRanker.rank_actions()` on ALL filtered actions (tested + untested) with the full scorer system (MopScorer, CoverageDensityScorer, GradualDecayScorer, SaturationScorer, etc.). This replaces the previous `_select_least_executed_action()` to ensure scorer improvements benefit long runs where 60-90% of iterations operate in this tier.
5. **BACK**: If no actions are available at all (e.g., all permanently failed or ranked list empty), return a BACK action.

**Proactive Backtracking**: When the saturation rate of the current `ScreenNode` exceeds `backtrack_saturation_threshold`, the strategy MUST return a BACK action without entering continuous mode. The `backtrack_saturation_threshold` parameter (float, 0.5-1.0, default 0.8) controls when this triggers. A threshold of 0.8 means that once 80% of actions in a state have been tested, the strategy proactively navigates away. Navigation distance is determined by `SuccessorTracker.find_nearest_unsaturated()` BFS, which returns the hop count to the nearest unsaturated ancestor.

**Path Buffer Integration**: When `path_buffer_enabled` is True and the `PathBuffer` has a buffered path, the strategy MUST execute buffered actions before considering untested actions. The PathBuffer is populated by three strategies defined in the Path Buffer requirement: (A) backtrack to unsaturated ancestor, (B) navigate to MOP-rich Activity via WTG BFS, and (C) navigate toward high-coverage-potential screens via BFS on learned transitions. See the Path Buffer requirement for details on buffer creation, validation, and invalidation.

**Successor Tracking**: The `SuccessorTracker` records which state each action leads to. If a destination state has untested actions, the original action is re-enabled for re-execution. This prevents premature backtracking from "gateway" states (e.g., a Settings button leading to a screen with many sub-options).

**Scored Continuous Exploration**: When the saturation rate is below the threshold and all actions have been tested, the strategy MUST use `ActionRanker.rank_actions()` on ALL filtered actions (tested + untested) to select the highest-scored action. This ensures CoverageDensityScorer, MopScorer, GradualDecayScorer, and SaturationScorer guide re-testing priority. The strategy MUST never report being "exhausted." The timeout is the only termination condition. When all Tier 3 path plans also fail (all reachable states saturated), the agent falls through to this tier rather than returning a plain BACK, maintaining productive exploration throughout the session.

**Pre-Marking**: Actions are marked as executed in `DynamicStateGraph` BEFORE device execution. If the app crashes during execution, the action is already marked and will not be retried. Failed actions are tracked separately for permanent exclusion.

#### Scenario: Untested Action Selection

- **WHEN** `select_next_action()` is called on a screen with 5 untested actions and no buffered path
- **THEN** the strategy MUST select one of the untested actions
- **AND** the selection MUST use `ActionRanker` for priority-based ranking

#### Scenario: Proactive Backtracking on Saturated State

- **WHEN** `select_next_action()` is called on a screen with 10 total actions where 9 have been tested (saturation rate = 0.9)
- **AND** `backtrack_saturation_threshold` is 0.8
- **AND** no path is buffered in `PathBuffer`
- **THEN** `should_backtrack()` MUST return True
- **AND** the strategy MUST try path planning: `plan_coverage_path()` > `plan_mop_path()` > `plan_backtrack_path()` (C > B > A ordering)
- **AND** if any plan succeeds, the first buffered action MUST be returned
- **AND** if ALL plans fail (all reachable states saturated), the strategy MUST fall through to Tier 4 (scored continuous mode) — it MUST NOT return a plain BACK from Tier 3

#### Scenario: Saturation Below Threshold Falls Through to Continuous

- **WHEN** `select_next_action()` is called on a screen with 10 total actions where 7 have been tested (saturation rate = 0.7)
- **AND** `backtrack_saturation_threshold` is 0.8
- **AND** no untested actions remain after package filtering
- **THEN** `should_backtrack()` MUST return False
- **AND** the strategy MUST use `ActionRanker.rank_actions()` on all filtered actions to select the highest-scored action (scored continuous mode)

#### Scenario: Path Buffer Takes Priority Over Untested Actions

- **WHEN** `select_next_action()` is called
- **AND** the `PathBuffer` has a buffered path with 3 remaining steps
- **AND** untested actions exist on the current screen
- **THEN** the strategy MUST execute the next buffered action
- **AND** untested action selection MUST be skipped

#### Scenario: Scored Continuous Exploration After Exhaustion

- **WHEN** all actions on the current screen have been tested at least once
- **AND** the saturation rate (e.g., 0.75) is below `backtrack_saturation_threshold` (0.8)
- **THEN** the strategy MUST NOT return None
- **AND** MUST use `ActionRanker.rank_actions()` on ALL filtered actions (tested + untested) to select the highest-scored action, guided by the full scorer system (MopScorer, CoverageDensityScorer, GradualDecayScorer, SaturationScorer, StrengthScorer, etc.)

#### Scenario: Successor Re-enablement

- **WHEN** action A in state S1 leads to state S2
- **AND** state S2 has untested actions
- **THEN** `successor_tracker.update_action_availability()` MUST re-enable action A in state S1

#### Scenario: Package Filtering

- **WHEN** actions are available from both target package and external packages
- **THEN** the strategy MUST filter to only target package actions
- **AND** MUST allow actions from `SYSTEM_DIALOG_PACKAGES` (e.g., permission dialogs)

#### Scenario: All Actions Failed

- **WHEN** all available actions on a screen are permanently failed (crash-causing)
- **THEN** `ActionRanker.rank_actions()` MUST return an empty list (all actions excluded)
- **AND** a BACK action MUST be generated to navigate away (Tier 5)

#### Scenario: Strategy C Coverage Navigation in Tier 3

- **WHEN** the current state's saturation rate exceeds `backtrack_saturation_threshold` (0.8)
- **AND** `should_backtrack()` returns True
- **AND** `PathBuffer.plan_coverage_path()` finds a 2-step path to a screen with exploration_potential = 7.5 (15 elements, 50% coverage gap)
- **THEN** the PathBuffer MUST be populated with the 2-step coverage navigation path
- **AND** `select_next_action()` MUST return the first buffered action from Strategy C
- **AND** Strategy B (MOP navigation) and Strategy A (backtrack) MUST NOT be evaluated

#### Scenario: Scored Continuous Mode When All Path Plans Fail

- **WHEN** all actions on the current screen are saturated (saturation rate exceeds `backtrack_saturation_threshold`)
- **AND** `should_backtrack()` returns True
- **AND** `PathBuffer.plan_coverage_path()` returns False (no high-potential screens reachable)
- **AND** `PathBuffer.plan_mop_path()` returns False (no MOP-dense targets or no StaticAnalysisData)
- **AND** `PathBuffer.plan_backtrack_path()` returns False (no unsaturated ancestors within `max_backtrack_hops`)
- **THEN** the strategy MUST NOT return a plain BACK action from Tier 3
- **AND** the strategy MUST fall through to Tier 4 (scored continuous mode)
- **AND** `ActionRanker.rank_actions()` MUST be called on ALL filtered actions (tested + untested)
- **AND** the highest-scored action MUST be selected
- **AND** MopScorer, CoverageDensityScorer, GradualDecayScorer, and SaturationScorer MUST influence the selection
- **AND** this ensures the agent re-tests in MOP-prioritized, coverage-guided order instead of blindly picking the least-executed action

### Requirement: Composite Action Ranking (FR27)

The strategy MUST rank available actions using a composite scoring system with 9 registered scorers. Each scorer implements the `Scorer` abstract base class with a `score(action, context) -> float` method. Scores are summed by `ActionRanker` to determine final ranking.

The scorer list includes the 7 original scorers plus `GradualDecayScorer` and `CoverageDensityScorer`. `GradualDecayScorer` was previously defined but not registered (dead code); it provides smoother priority transitions using exponential decay: `base_score * decay_rate^visits` where `base_score` = 200 and `decay_rate` = 0.7. This replaces the binary untested/tested split with a gradual signal — actions visited once still have value (200 * 0.7 = 140), twice (200 * 0.49 = 98), and so on.

`CoverageDensityScorer` provides cross-screen coverage guidance using learned transition data. While all other scorers operate on the CURRENT screen, CoverageDensityScorer answers the question "which of these actions leads to the most interesting DESTINATION?" by querying `SuccessorTracker` for action destinations and `UICoverageTracker` for destination coverage. This addresses the "small island" problem: when MOP methods represent 1-5% of app code, broad UI coverage increases the probability of reaching monitored operations, including those not mapped by static analysis. The scorer is always active (not gated on `StaticAnalysisData`), creating a dual guidance architecture where MOP targeting provides directed precision and coverage provides broad probabilistic exploration.

**Updated default weights:**

| Scorer | Previous Default | New Default | Rationale |
|--------|-----------------|-------------|-----------|
| `MopScorer` (direct) | 300 | 500 | MOP-direct actions are the primary exploration target; they MUST rank above all other scorers |
| `MopScorer` (transitive) | 150 | 300 | MOP-transitive actions MUST outweigh WTG navigation to prevent the agent from preferring new screens over MOP paths |
| `WtgScorer` | 250 | 150 | WTG provides a support role for screen discovery, not a primary driver |
| `SaturationScorer` | 80 | 100 | Slightly increased to incentivize exploration of unsaturated states |
| `ComponentPriorityScorer` | 50/40 | 50/40 | Unchanged |
| `StrengthScorer` | 50 | 50 | Unchanged base, but now incorporates cumulative reward from N-step propagation |
| `GradualDecayScorer` | N/A (dead code) | 200 * 0.7^visits | Newly activated; provides smooth decay across visits |
| `CoverageDensityScorer` | N/A (new) | 200 * coverage_gap | Always active; cross-screen coverage guidance using learned transitions |
| `SystemElementFilter` | -5000 | -5000 | Unchanged |
| `VisitationPenaltyScorer` | -10 | -15 | Stronger repulsion from over-visited states |

**StrengthScorer with Cumulative Reward**: The `StrengthScorer` MUST incorporate cumulative reward data from N-step reward propagation (see N-Step Reward Propagation requirement). The scorer reads `action_cumulative_reward` from the `ScreenNode` and adds it to the existing success-rate-based score. This means actions that historically led to MOP-reaching sequences accumulate higher scores over time.

Action selection supports two modes: deterministic (always selects highest-scored action) and stochastic (Gumbel-max sampling with configurable temperature). The selection mode is chosen probabilistically based on `stochastic_probability` (default 0.15 — 15% stochastic, 85% deterministic). The reduced stochastic probability increases deterministic MOP focus.

#### Scenario: MOP Prioritization with Updated Weights

- **WHEN** action A has `directly_reaches_mop = True` and action B has `reaches_mop = False`
- **THEN** `MopScorer` MUST assign +500 to A and 0 to B (default config)
- **AND** action A MUST rank higher than B (all other scores being equal)

#### Scenario: MOP-Transitive Outweighs WTG

- **WHEN** action A has `reaches_mop = True` (transitive) and action B is WTG-guided to an unvisited screen
- **THEN** `MopScorer` MUST assign +300 to A
- **AND** `WtgScorer` MUST assign +150 to B
- **AND** action A MUST rank higher than B (all other scores being equal)

#### Scenario: WTG-Guided Navigation Scoring

- **WHEN** `TransitionManager` indicates that action A leads to an unvisited screen
- **THEN** `WtgScorer` MUST assign +150 to that action (default config)

#### Scenario: GradualDecayScorer Behavior

- **WHEN** action A targets an element visited 0 times and action B targets an element visited 3 times
- **THEN** `GradualDecayScorer` MUST assign 200 to A (200 * 0.7^0)
- **AND** `GradualDecayScorer` MUST assign approximately 68.6 to B (200 * 0.7^3)

#### Scenario: Reward-Enhanced Strength Scoring

- **WHEN** action A in state S has `action_cumulative_reward` = 3.2 (from prior MOP-reaching sequences)
- **AND** action A has `success_rate` = 0.8
- **AND** `reward_score_weight` = 1.0 (default)
- **THEN** `StrengthScorer` MUST compute base score as 50 * 0.8 = 40
- **AND** MUST add the weighted cumulative reward: 40 + 1.0 * 3.2 = 43.2

#### Scenario: Stochastic Selection with Reduced Probability

- **WHEN** `stochastic_probability` = 0.15 and `random.random()` returns a value < 0.15
- **THEN** `ActionRanker.select_stochastic()` MUST be used with `stochastic_temperature`
- **AND** the selection MUST use Gumbel-max sampling (adding Gumbel noise to log-scores)

#### Scenario: Component Priority

- **WHEN** action A targets a `Button` widget and action B targets a `TextView`
- **THEN** `ComponentPriorityScorer` MUST assign +50 to A (high priority) and 0 to B (not in priority list)

#### Scenario: CoverageDensityScorer with Known Destination

- **WHEN** action A leads to a known destination screen (via SuccessorTracker) with 15 total elements and 12 untested elements (coverage_gap = 0.8)
- **AND** `coverage_density_weight` = 200
- **THEN** `CoverageDensityScorer` MUST assign 200 * 0.8 = 160 to action A

#### Scenario: CoverageDensityScorer with Unknown Destination

- **WHEN** action B has never been executed (destination unknown to SuccessorTracker)
- **AND** `coverage_density_weight` = 200
- **THEN** `CoverageDensityScorer` MUST assign 200 * 0.5 = 100 to action B (exploration bonus)

#### Scenario: CoverageDensityScorer Synergy with MopScorer

- **WHEN** action A leads to a MOP-rich screen with high coverage gap (coverage_gap = 0.8)
- **AND** `MopScorer` assigns +500 to action A (directly_reaches_mop = True)
- **AND** `CoverageDensityScorer` assigns +160 to action A (200 * 0.8)
- **THEN** the combined score for action A MUST include both contributions (+660 from these two scorers)
- **AND** action A MUST rank higher than an action B with only MopScorer +500 but CoverageDensityScorer +20 (well-covered destination, coverage_gap = 0.1)

### Requirement: Stuck State Detection and Recovery (FR29, NFR04)

rv-agent MUST detect and recover from stuck states through a two-level system implemented in `learn_node`. Stuck detection is evidence-based, relying on screen hash comparisons rather than action pattern heuristics.

With proactive backtracking (FR26) active, stuck detection triggers less frequently because the strategy leaves saturated states before reaching the stuck threshold. Stuck detection remains as a **safety net** for cases where proactive backtracking is insufficient — for example, when the app hangs and does not respond to BACK actions, when the UI becomes unresponsive, or when the agent is trapped in a cycle of states that are each individually below the saturation threshold but collectively unproductive.

Level 1 uses a dynamic threshold: `max(BASE_STUCK_THRESHOLD, num_elements * STUCK_THRESHOLD_FACTOR)` where `BASE_STUCK_THRESHOLD` = 8 and `STUCK_THRESHOLD_FACTOR` = 1.5. Level 2 uses `StuckRecovery` with `max_blocks` = 10, attempting Backtrack BFS before app restart.

#### Scenario: Level 1 Screen Unchanged Recovery

- **WHEN** the screen hash remains the same for `dynamic_threshold` consecutive iterations
- **AND** the actions are not form actions (SET_TEXT, checkable elements)
- **THEN** `force_back_action` MUST be set to True in the state
- **AND** `stuck_screen_count` MUST be reset to 0

#### Scenario: Form Actions Excluded from Stuck Counting

- **WHEN** the screen hash remains the same after a SET_TEXT or checkable element action
- **THEN** `stuck_screen_count` MUST NOT be incremented

#### Scenario: Level 2 Backtrack BFS Success

- **WHEN** Level 2 stuck recovery triggers
- **AND** `successor_tracker.find_nearest_unsaturated()` finds an ancestor state
- **THEN** `force_back_action` MUST be set to True (to navigate toward the ancestor)
- **AND** app restart MUST NOT be triggered

#### Scenario: Level 2 App Restart

- **WHEN** Level 2 stuck recovery triggers
- **AND** `successor_tracker.find_nearest_unsaturated()` returns None (no unsaturated ancestor)
- **THEN** `force_restart_app` MUST be set to True
- **AND** `stuck_recovery.record_restart()` MUST be called

#### Scenario: Deadlock Detection

- **WHEN** `consecutive_no_action` reaches `NO_ACTION_THRESHOLD` (3) in `algorithm_node`
- **THEN** a BACK action MUST be generated with reason "deadlock_escape"
- **AND** `consecutive_no_action` MUST be reset to 0

#### Scenario: Proactive Backtracking Reduces Stuck Frequency

- **WHEN** the agent explores a screen with 10 actions and `backtrack_saturation_threshold` is 0.8
- **AND** 9 of 10 actions have been tested (saturation rate = 0.9)
- **THEN** `should_backtrack()` in the strategy MUST trigger a BACK action before the screen hash remains unchanged for `dynamic_threshold` iterations
- **AND** Level 1 stuck detection MUST NOT fire for this state because the agent has already left

### Requirement: WTG-Guided Navigation (FR30)

rv-agent MUST use the Window Transition Graph (from GATOR static analysis) to guide exploration when `StaticAnalysisData` is available. The integration operates through three components:

1. `TransitionManager`: Integrates WTG data with `DynamicStateGraph`, mapping static window IDs to runtime activities. Provides path planning capability for the `PathBuffer` via `plan_path_to_mop_activity()`.
2. `NavigationGuidance`: Provides unified navigation context to both LLM and algorithm. Enriches LLM prompts with MOP-specific hints when static analysis data is available.
3. `WtgScorer`: Gives priority scores to actions that WTG indicates lead to unvisited screens.

**Path Planning via BFS**: The `TransitionManager` MUST provide a `plan_path_to_mop_activity()` method that performs BFS on the WTG from the current activity to find the nearest Activity containing MOP methods. The BFS MUST use MOP density weighting: edge priority toward a target Activity is weighted by `mop_methods_in_target / total_methods_in_target`. Activities with higher MOP density are preferred targets. The `mop_nav_weight` parameter (default 2.0) controls the influence of MOP density relative to path length.

**Saturation-Aware Path Preference**: When multiple BFS paths of equal MOP density exist, the `TransitionManager` MUST prefer paths through less-saturated states. This combines directed MOP navigation with opportunistic exploration of under-tested intermediate screens.

**MOP-Specific LLM Guidance**: When static analysis data is available and the execution mode includes LLM iterations (multimode or llm_only), `NavigationGuidance` MUST enrich the LLM prompt with MOP-specific context. This includes which interactive elements on the current screen lead to monitored API calls, and path descriptions toward MOP-rich Activities (e.g., "Button 'Configure Encryption' directly calls Cipher.getInstance"). This is formatted via `format_for_llm()` and passed as navigation hints.

When static data is not available, all three components gracefully degrade: `NavigationGuidance.is_enabled` returns False, `WtgScorer` returns 0 for all actions, `TransitionManager` provides empty guidance, and `plan_path_to_mop_activity()` returns None.

#### Scenario: WTG Guidance Available

- **WHEN** `StaticAnalysisData` with WTG is provided
- **THEN** `NavigationGuidance.is_enabled` MUST return True
- **AND** `get_context()` MUST return an `ExplorationContext` with `has_guidance = True`

#### Scenario: WTG Guidance Unavailable

- **WHEN** `StaticAnalysisData` is None
- **THEN** `NavigationGuidance.is_enabled` MUST return False
- **AND** `get_context()` MUST return an `ExplorationContext` with `has_guidance = False`
- **AND** `format_for_llm()` MUST return an empty string
- **AND** `plan_path_to_mop_activity()` MUST return None

#### Scenario: LLM Navigation Hint with MOP Context

- **WHEN** WTG guidance is available and there are unvisited screens reachable from the current activity
- **AND** the current screen contains elements that directly reach MOP methods
- **THEN** `format_for_llm()` MUST return a non-empty string starting with "Navigation guidance:"
- **AND** the string MUST list up to 3 unvisited screens and priority targets
- **AND** the string MUST include MOP-specific descriptions for elements that reach monitored API calls (e.g., "Button 'Security Settings' leads to Cipher.getInstance via 2 steps")
- **AND** the MOP context MUST be formatted for inclusion in `prompts/v17.py` (the MOP navigation prompt template)

#### Scenario: Algorithm WTG Scoring

- **WHEN** WTG indicates action A leads to an unvisited screen
- **THEN** `WtgScorer` MUST assign `wtg_guided_score` (default 150.0) to action A

#### Scenario: BFS Path Planning to MOP Activity

- **WHEN** `plan_path_to_mop_activity()` is called from the current activity "MainActivity"
- **AND** the WTG contains a path: MainActivity -> SettingsActivity -> SecurityActivity
- **AND** SecurityActivity contains 5 MOP methods out of 20 total methods (density = 0.25)
- **AND** another path exists: MainActivity -> AboutActivity with 1 MOP method out of 10 (density = 0.1)
- **THEN** the method MUST return the path to SecurityActivity (higher MOP density)
- **AND** the path MUST be a list of transition actions: [action_to_settings, action_to_security]

#### Scenario: MOP Density Weighting in BFS

- **WHEN** BFS finds two candidate MOP Activities at the same graph distance (2 hops each)
- **AND** Activity A has MOP density 0.3 (6 MOP methods / 20 total)
- **AND** Activity B has MOP density 0.1 (2 MOP methods / 20 total)
- **AND** `mop_nav_weight` is 2.0
- **THEN** the BFS MUST prefer the path to Activity A
- **AND** the effective priority for A MUST be higher by a factor proportional to `(0.3 / 0.1) * mop_nav_weight`

#### Scenario: Saturation-Aware Path Selection

- **WHEN** two BFS paths of equal MOP density lead to the same target Activity
- **AND** path 1 traverses through a state with saturation rate 0.9
- **AND** path 2 traverses through a state with saturation rate 0.3
- **THEN** the BFS MUST prefer path 2 (less-saturated intermediate states)

### Requirement: Vision-Based Exploration via Qwen3-VL and SGLang (FR24, NFR07)

rv-agent MUST support vision-based exploration using the Qwen3-VL model served via SGLang (OpenAI-compatible API). The `LLMClient` sends a multimodal message containing a system prompt, formatted UI elements text, and a base64-encoded optimized screenshot to the model. The model returns tool calls specifying actions to execute.

**Speed Optimization for Pure Algorithm**: In `pure_algorithm` mode, the `decision_router_node` MUST skip `capture_screenshot_node` and `llm_generate_node` entirely. This is a per-iteration routing decision, not a compile-time flag. In `multimode`, algorithm iterations (30% by default) MUST also skip these nodes, while LLM iterations (70% by default) use the full pipeline. This optimization reduces per-iteration time in pure_algorithm from ~2s to <1s, targeting ~300+ iterations in 300 seconds.

The conditional screenshot capture in `parse_node` added by gh18 (fires on hash-repeat for error detection) MUST be preserved regardless of mode. The speed optimization targets the LLM screenshot path (`capture_screenshot_node`), not the error detection screenshot path.

**MOP-Enriched LLM Prompts**: When static analysis data is available and the current iteration routes to the LLM path, the `LLMClient` MUST include MOP-specific context from `NavigationGuidance.format_for_llm()` in the user message. This provides the VLM with information about which screen elements lead to monitored API calls, enabling semantically informed exploration toward MOP methods. The MOP context is integrated into the prompt template via `prompts/v17.py` (new — v16 already exists as "Navigation-first exploration"; v17 adds MOP-specific navigation hints).

The `LLMClient` is initialized with `ChatOpenAI` from langchain-openai, configured with parameters from `RVAgentConfig.get_langchain_config()`. Tools are bound via `llm.bind_tools()` using the Android action tool definitions from `sglang_tools.py`.

Default configuration: `Qwen/Qwen3-VL-4B-Instruct`, temperature=0.01, top_p=0.6, max_tokens=2048, via SGLang at `http://192.168.0.36:30000/v1`.

#### Scenario: Successful LLM Action Generation

- **WHEN** `llm_generate_node` calls `llm_client.generate_action()` with valid screen data and screenshot
- **THEN** the response MUST contain a `response` field with an AIMessage
- **AND** `success` MUST be `True`
- **AND** `tokens_input`, `tokens_output`, and `time_ms` MUST be populated

#### Scenario: Multimodal Message Construction

- **WHEN** `_build_messages()` is called with UI elements text and a base64 screenshot
- **THEN** the message list MUST contain exactly 2 messages: a `SystemMessage` and a `HumanMessage`
- **AND** the `HumanMessage` MUST have multimodal content with both text and image_url parts

#### Scenario: Navigation Hint Inclusion

- **WHEN** `navigation_guidance` is enabled and has guidance for the current screen
- **THEN** the navigation hint text MUST be passed to `llm_client.generate_action()` as the `navigation_hint` parameter
- **AND** the hint MUST be included in the user message via `build_user_message()`

#### Scenario: LLM Timeout Handling

- **WHEN** the LLM invocation exceeds `llm_timeout` seconds or raises an exception
- **THEN** an `LLMError` MUST be raised
- **AND** the latency MUST be recorded before the exception propagates

#### Scenario: Pure Algorithm Fast Path

- **WHEN** `decision_router_node` executes in `pure_algorithm` mode
- **THEN** the routing MUST return `"algorithm"` without evaluating screenshot capture
- **AND** `capture_screenshot_node` MUST NOT execute
- **AND** `llm_generate_node` MUST NOT execute
- **AND** gh18's conditional screenshot in `parse_node` MUST still execute when `screen_hash == previous_screen_hash`

#### Scenario: Mode-Aware Node Skipping in Multimode

- **WHEN** `decision_router_node` executes in `multimode` with `llm_probability` = 0.7
- **AND** `random.random()` returns 0.85 (routes to algorithm for this iteration)
- **THEN** `capture_screenshot_node` MUST NOT execute for this iteration
- **AND** `llm_generate_node` MUST NOT execute for this iteration
- **AND** `algorithm_node` MUST execute

#### Scenario: LLM Prompt with MOP Context

- **WHEN** the iteration routes to the LLM path
- **AND** `StaticAnalysisData` is available with MOP data for the current screen
- **THEN** `NavigationGuidance.format_for_llm()` MUST return MOP-specific guidance
- **AND** the guidance MUST be included in the user message to `llm_client.generate_action()` via `prompts/v17.py`

## ADDED Requirements

### Requirement: N-Step Reward Propagation (FR27)

The agent MUST implement backward reward propagation through action chains to learn which action sequences lead to productive outcomes. This is a simplified adaptation of Fastbot's SARSA n-step approach, tailored to rv-agent's architecture. Instead of maintaining a separate Q-table, rewards are stored in the existing `ScreenNode` data structure via a new `action_cumulative_reward` dictionary.

**Reward Constants**: The system defines four reward values corresponding to progressively more valuable exploration outcomes:

| Event | Constant | Value | Description |
|-------|----------|-------|-------------|
| Same state | `REWARD_SAME_STATE` | -0.1 | Action did not change the screen state |
| New state | `REWARD_NEW_STATE` | 1.0 | Discovered a previously unseen screen |
| New Activity | `REWARD_NEW_ACTIVITY` | 2.0 | Discovered a previously unseen Activity |
| MOP reached | `REWARD_MOP_REACHED` | Configurable via `reward_mop_weight` (default 5.0) | The executed action has a non-empty `callback_signature`, indicating it is structurally associated with a monitored operation method. This is a **proxy signal** — the action CAN reach MOP, not confirmation that a MOP method was actually invoked at runtime. Real-time MOP confirmation would require logcat parsing within the iteration loop, which is not feasible within the 300s time budget. |

The `REWARD_MOP_REACHED` value is the key differentiator from Fastbot's reward function, which only rewards new Activities. rv-agent's reward function specifically incentivizes reaching monitored API calls, which is the primary objective for MOP coverage.

**Backward Propagation**: When a reward event occurs (any non-zero reward), the system MUST propagate the reward backward through the last `reward_propagation_n` actions (default 5) with discount factor `reward_gamma` (default 0.8). For each step k backward from the event (k=1 to N), the propagated reward is `reward_value * gamma^k`. This reward is added to the `action_cumulative_reward` dictionary in the corresponding `ScreenNode`.

The propagation reads from `RewardPropagator`'s internal action history — a deque of `(state_hash, action_signature)` tuples maintained via `record_action()`, called by `learn_node` after each iteration. Each entry contains the state hash where the action was executed and the optimized-coordinate action signature, enabling the reward to be attributed to the correct `ScreenNode` and action. This is separate from the shared `recent_action_window` (which stores raw action dicts without state hashes or optimized coordinates).

**Integration with StrengthScorer**: The `StrengthScorer` MUST read `action_cumulative_reward` from the `ScreenNode` and add the cumulative reward value to its existing success-rate-based score. This means actions that historically started productive sequences (leading to MOP methods or new states) accumulate higher scores over time, steering the strategy toward repeating successful exploration patterns.

**Error Recovery Participation**: Actions with `decision_maker="error_recovery"` (from gh18) MUST participate in reward propagation. If an error recovery SET_TEXT action leads to a successful MOP trigger on a subsequent iteration, that reward MUST propagate back through the error recovery action chain.

#### Scenario: Reward Propagation on MOP Reached

- **WHEN** iteration 100 triggers a MOP method (detected via `callback_signature` in learn_node)
- **AND** `reward_mop_weight` = 5.0, `reward_gamma` = 0.8, `reward_propagation_n` = 5
- **THEN** the action at iteration 100 MUST receive reward 5.0
- **AND** the action at iteration 99 MUST receive propagated reward 5.0 * 0.8^1 = 4.0
- **AND** the action at iteration 98 MUST receive propagated reward 5.0 * 0.8^2 = 3.2
- **AND** the action at iteration 97 MUST receive propagated reward 5.0 * 0.8^3 = 2.56
- **AND** the action at iteration 96 MUST receive propagated reward 5.0 * 0.8^4 = 2.048
- **AND** iteration 95 and earlier MUST NOT receive any propagated reward (beyond N=5)

#### Scenario: Discount Factor Application

- **WHEN** `reward_gamma` = 0.5 and a `REWARD_NEW_ACTIVITY` (2.0) event occurs
- **THEN** the action 1 step back MUST receive 2.0 * 0.5 = 1.0
- **AND** the action 2 steps back MUST receive 2.0 * 0.25 = 0.5
- **AND** the action 3 steps back MUST receive 2.0 * 0.125 = 0.25

#### Scenario: New State Reward

- **WHEN** an action leads to a state whose hash is not in `graph.states`
- **THEN** `REWARD_NEW_STATE` = 1.0 MUST be assigned to the action
- **AND** backward propagation MUST be triggered through the last N actions

#### Scenario: Same State Penalty

- **WHEN** an action does not change the screen hash (same state before and after)
- **THEN** `REWARD_SAME_STATE` = -0.1 MUST be assigned to the action
- **AND** backward propagation MUST still be triggered (with negative reward)

#### Scenario: Cumulative Reward Accumulation

- **WHEN** action A in state S receives propagated reward 3.2 from one event
- **AND** later receives propagated reward 1.6 from a different event
- **THEN** `action_cumulative_reward[A]` in ScreenNode S MUST be 4.8 (3.2 + 1.6)

#### Scenario: No Static Analysis Partial Degradation

- **WHEN** `StaticAnalysisData` is None
- **THEN** `REWARD_MOP_REACHED` events MUST NOT fire (no `callback_signature` without monitors)
- **AND** `REWARD_NEW_STATE` and `REWARD_NEW_ACTIVITY` events MUST still fire normally
- **AND** reward propagation MUST still operate with the remaining reward types

#### Scenario: Concurrent Reward Types — Highest Wins

- **WHEN** an action leads to a new Activity (REWARD_NEW_ACTIVITY = 2.0)
- **AND** that action also has `callback_signature` present (REWARD_MOP_REACHED = 5.0)
- **THEN** only one `propagate()` call MUST be made per iteration
- **AND** the reward type MUST be `mop_reached` (5.0), not `new_activity` (2.0)
- **AND** the priority order MUST be: mop_reached > new_activity > new_state > same_state

#### Scenario: MOP Detection is Proxy Signal

- **WHEN** an action has `callback_signature` from static analysis (REACH)
- **THEN** `REWARD_MOP_REACHED` (5.0) MUST be assigned
- **AND** this is a structural proxy signal ("action CAN reach MOP"), not a runtime confirmation that MOP was actually triggered
- **AND** the reward MAY be given for actions that did not trigger a monitored API call at runtime (accepted trade-off)

#### Scenario: Oscillation Trap Resolution via Negative Rewards

- **WHEN** the agent cycles between two states A and B (A→B→A→B) for 20+ iterations
- **AND** both states have saturation rates below `backtrack_saturation_threshold` (so proactive backtracking does not fire)
- **AND** the screen hash changes on each transition (so stuck detection does not fire)
- **THEN** after the initial exploration of A→B and B→A, subsequent transitions become `REWARD_SAME_STATE` (-0.1) because the destination states are already known
- **AND** cumulative negative rewards MUST accumulate on the cycling actions in both states
- **AND** StrengthScorer MUST eventually assign lower scores to the cycling actions than to alternative actions (e.g., BACK or other untested actions), breaking the cycle

#### Scenario: Graceful Degradation Without Static Analysis (End-to-End)

- **WHEN** `StaticAnalysisData` is None (e.g., `--skip-static` flag or GATOR/GESDA failure)
- **THEN** PathBuffer Strategy B (MOP navigation) MUST be disabled (plan_mop_path returns False)
- **AND** PathBuffer Strategy A (backtrack to unsaturated ancestor) MUST still function
- **AND** PathBuffer Strategy C (coverage navigation) MUST still function (operates on runtime data)
- **AND** CoverageDensityScorer MUST still function (operates on runtime data, always active)
- **AND** MopScorer MUST return 0.0 for all actions
- **AND** WtgScorer MUST return 0.0 for all actions
- **AND** NavigationGuidance.format_for_llm() MUST return an empty string
- **AND** reward propagation MUST operate with non-MOP reward types only (same_state, new_state, new_activity)
- **AND** the agent MUST NOT crash or produce errors — it operates as a coverage-directed UI explorer with dual guidance (CDS + Strategy C) providing cross-screen navigation even without MOP data

#### Scenario: Error Recovery Actions Participate in Reward Propagation

- **WHEN** an error recovery action sequence (from gh18, with `decision_maker="error_recovery"`) executes a SET_TEXT on a form field
- **AND** the SET_TEXT leads to a state transition where a subsequent action triggers a MOP method (detected via `callback_signature`)
- **AND** `reward_mop_weight` = 5.0, `reward_gamma` = 0.8
- **THEN** the `REWARD_MOP_REACHED` reward (5.0 * gamma^k for each step k) MUST propagate backward through the error recovery action sequence
- **AND** the error recovery actions MUST NOT be filtered from `RewardPropagator`'s internal action history based on their `decision_maker` field
- **AND** the cumulative reward MUST accumulate on the error recovery actions in their respective `ScreenNode` entries, making those recovery paths more attractive in future visits

### Requirement: Text Input Quality (FR26)

The `InputValueGenerator` and text input execution pipeline MUST produce context-appropriate input values and handle text field interaction correctly. This requirement addresses six bugs in the current implementation that collectively waste 20-40% of text input iterations and prevent MOP-relevant edge case testing.

**Unified Input Type Inference**: The duplicate `_infer_input_type()` method in `rvagent_strategy.py` MUST be deleted. Input type inference MUST use a simplified inline helper in `_prepare_input_action()` (~15 lines) that extracts input type from `hint`, `content_description`, and `resource_id` fields directly available on the `ItemAction.target_view` Node object. The helper checks fields in priority order: `hint` (most reliable, e.g. "Email", "Password"), then `content_description`, then `resource_id` pattern matching (e.g. `*_email*` → "email"). This approach has no dependency on `EnhancedTextVisitor` or rv-screen-parser internals (P1 Simplicity). The helper detects 15+ input types (email, phone, search, URL, date, time, ZIP, verification code, first/last name, numeric, multi-line text, password, PIN).

**Fixed Value Ordering**: The `_get_regular_values()` method MUST return Faker-generated values first for all input types. PIN values ("1234", "0000", "123456") MUST only appear for `password` and `pin` input types. Empty string ("") MUST NOT be the first generated value for any input type. The ordering for a typical text field MUST be: `[faker.sentence(), faker.word(), faker.paragraph()[:50], ...]` — not `["1234", "0000", "123456", faker.sentence(), ...]`.

**Clear-Before-Type**: The text input execution pipeline MUST call `device.clear_text()` before `input_text()` for all SET_TEXT actions. This prevents text from being appended to existing field content (placeholder text, previous input, or default values). The sequence MUST be: `click(x, y)` -> `device.clear_text()` -> `input_text(text)`.

**MOP Field Input Variations**: Fields associated with MOP methods MUST use a separate `mop_max_input_variations` parameter (default 11) instead of the standard `max_variations` (default 5). This ensures all 11 MOP edge-case payloads are tested, including SQL injection, XSS, format string, buffer overflow, and other security-relevant inputs that would otherwise be truncated by the standard 5-variation limit.

**Missing Input Types**: The `InputValueGenerator` MUST handle the following input types that currently fall through to the generic "text" default: `search` (faker.sentence with 3 words), `url` (faker.url), `date` (faker.date), `time` (faker.time), `number` (faker.random_int as string), `zip` (faker.zipcode), `verification_code` (faker.random_int 1000-9999 as string).

**LLM Text Tracking**: When the LLM generates a SET_TEXT action (in multimode or llm_only), the text value MUST be recorded in the `tested_values` dictionary for the corresponding field. This prevents the `InputValueGenerator` from repeating the same value when the algorithm path later encounters the same field.

#### Scenario: Unified Input Type Inference

- **WHEN** a SET_TEXT action targets an EditText with `hint="Enter your email address"` and `resource_id="input_email"`
- **THEN** the input type MUST be inferred as "email" using the inline helper in `_prepare_input_action()` (checks `hint` → `content_description` → `resource_id`)
- **AND** the strategy's `_infer_input_type()` method MUST NOT exist (deleted)

#### Scenario: Faker Values First for Text Fields

- **WHEN** `get_next_value()` is called for a field with input type "text"
- **THEN** the first value MUST be a Faker-generated sentence (e.g., faker.sentence())
- **AND** PIN values ("1234", "0000", "123456") MUST NOT appear in the generated values

#### Scenario: PINs Only for Password and PIN Fields

- **WHEN** `get_next_value()` is called for a field with input type "password"
- **THEN** the generated values MUST include PIN values ("1234", "0000", "123456")
- **AND** Faker password values MUST also be included

#### Scenario: Clear-Before-Type Execution

- **WHEN** a SET_TEXT action is executed via `tool_executor`
- **THEN** `device.clear_text()` MUST be called after `click(x, y)` and before `input_text(text)`
- **AND** the field MUST be empty before the new text is typed

#### Scenario: MOP Field Extended Variations

- **WHEN** `get_next_value()` is called for a field with `reaches_mop = True`
- **AND** `mop_max_input_variations` = 11
- **THEN** up to 11 unique values MUST be generated before cycling
- **AND** the values MUST include MOP edge-case payloads (empty string, "0", "-1", "2147483647", path traversal, SQL injection, XSS, format string, buffer overflow, JNDI, Shellshock)

#### Scenario: Missing Input Type - Search Field

- **WHEN** `get_next_value()` is called for a field with input type "search"
- **THEN** the first value MUST be a short Faker sentence (e.g., faker.sentence(nb_words=3))
- **AND** the value MUST NOT be a PIN or empty string

#### Scenario: Missing Input Type - URL Field

- **WHEN** `get_next_value()` is called for a field with input type "url"
- **THEN** the first value MUST be a Faker URL (e.g., faker.url())

#### Scenario: Missing Input Type - Date Field

- **WHEN** `get_next_value()` is called for a field with input type "date"
- **THEN** the first value MUST be a Faker date (e.g., faker.date())

#### Scenario: LLM Text Recorded in Tested Values

- **WHEN** the LLM generates a SET_TEXT action with text "john.doe@example.com" for field F
- **AND** the action is executed successfully
- **THEN** "john.doe@example.com" MUST be added to `tested_values[F]`
- **AND** subsequent `get_next_value()` calls for field F MUST NOT return "john.doe@example.com"

### Requirement: Path Buffer (FR26, FR30)

The `PathBuffer` class MUST manage multi-step navigation paths for the `RVAgentStrategy`. It provides an execution buffer that stores a sequence of actions to be executed in order, enabling the strategy to plan and execute multi-step navigation instead of making isolated single-action decisions.

**Three Planning Strategies**: The PathBuffer is populated by three strategies, selected based on the current exploration state:

**Strategy A — Backtrack to Unsaturated Ancestor**: When the current state is saturated (saturation rate exceeds `backtrack_saturation_threshold`), the PathBuffer uses `SuccessorTracker.find_nearest_unsaturated()` to locate the nearest ancestor state with untested actions. `find_nearest_unsaturated()` returns `Optional[Tuple[str, int]]` — the ancestor hash and BFS hop count. The hop count determines the number of BACK actions to buffer.

**Strategy B — Navigate to MOP-Rich Activity via WTG BFS**: When `StaticAnalysisData` is available and `path_buffer_enabled` is True, the PathBuffer can request a path from `TransitionManager.plan_path_to_mop_activity()`. This performs BFS on the WTG to find the nearest MOP-rich Activity, weighted by MOP density (see WTG-Guided Navigation requirement). The resulting path is a sequence of actions that navigate through intermediate Activities toward the target. This strategy is rv-agent's unique advantage over APE and Fastbot — neither tool combines path planning with MOP targeting.

**Strategy C — Navigate to High-Coverage-Potential Screen via Learned Transitions**: The PathBuffer performs BFS on `SuccessorTracker`'s learned transitions (not the static WTG) to find reachable screens with the highest exploration potential, defined as `coverage_gap * element_count`. This metric prefers screens with MANY untested elements, not just a high untested percentage: a Settings screen with 15 elements at 50% coverage (potential = 7.5) is more valuable than an About screen with 2 elements at 0% coverage (potential = 2.0). BFS depth is limited by `max_coverage_hops` (default 5). Strategy C is positioned BEFORE Strategy B in the Tier 3 evaluation order (C > B > A) because broad UI coverage addresses the "small island" problem: it increases the probability surface for finding MOP methods, including those not mapped by static analysis. Strategy C operates entirely on runtime data and is always available, even without `StaticAnalysisData`.

**Buffer Validation**: After executing each buffered action, the PathBuffer MUST validate that the resulting state matches expectations. If the actual post-execution state does not match the expected state for the current buffer step (e.g., the app navigated to an unexpected screen), the buffer MUST be cleared immediately. This prevents executing stale navigation paths that are no longer valid.

**Integration in select_next_action()**: The PathBuffer is checked first in the action selection order, before untested actions. When the buffer has remaining steps, the next buffered action is returned without consulting the scorer system. When the buffer is empty, normal action selection proceeds.

**Parameters**: `path_buffer_enabled` (bool, default True) controls whether the PathBuffer is active. `mop_nav_weight` (float, 0.5-5.0, default 2.0) controls MOP density influence in Strategy B's BFS (passed through to `TransitionManager`). `max_backtrack_hops` (int, 3-20, default 8) limits the number of BACK actions Strategy A can buffer — if the nearest unsaturated ancestor is farther than this limit, `plan_backtrack_path` returns False and the caller falls through to the next tier. `max_coverage_hops` (int, 2-10, default 5) limits the BFS depth for Strategy C — screens beyond this hop distance are not considered as navigation targets.

#### Scenario: Buffer Creation via Strategy A (Backtrack)

- **WHEN** the current state has saturation rate 0.9 (above threshold 0.8)
- **AND** `SuccessorTracker.find_nearest_unsaturated()` returns an ancestor 3 BACK actions away
- **THEN** the PathBuffer MUST be populated with 3 BACK actions
- **AND** `select_next_action()` MUST return the first buffered BACK action

#### Scenario: Buffer Creation via Strategy B (MOP Navigation)

- **WHEN** `StaticAnalysisData` is available and `path_buffer_enabled` is True
- **AND** the PathBuffer is empty and the current state has no untested actions
- **AND** `plan_path_to_mop_activity()` returns a 2-step path [action_to_settings, action_to_security]
- **THEN** the PathBuffer MUST be populated with the 2-step path
- **AND** `select_next_action()` MUST return `action_to_settings` (first step)

#### Scenario: Buffer Execution Sequence

- **WHEN** the PathBuffer contains [BACK, BACK, BACK] (3-step backtrack)
- **AND** `select_next_action()` is called 3 times
- **THEN** the first call MUST return BACK (step 1)
- **AND** the second call MUST return BACK (step 2)
- **AND** the third call MUST return BACK (step 3)
- **AND** after the third call, the buffer MUST be empty

#### Scenario: Buffer Invalidation on Failed Navigation

- **WHEN** the PathBuffer contains [action_to_settings, action_to_security]
- **AND** `action_to_settings` is executed
- **AND** the post-execution screen hash equals the pre-execution screen hash (the action had no effect — e.g., a dialog blocked the navigation, the click didn't transition)
- **THEN** the PathBuffer MUST clear all remaining buffered actions
- **AND** the next `select_next_action()` call MUST proceed with normal action selection (untested -> backtrack -> continuous -> BACK)

#### Scenario: Buffer Disabled

- **WHEN** `path_buffer_enabled` is False
- **THEN** the PathBuffer MUST NOT be populated by Strategy A, Strategy B, or Strategy C
- **AND** `select_next_action()` MUST skip the buffer check and proceed directly to untested action selection
- **AND** proactive backtracking (`should_backtrack()`) MUST still operate independently of the buffer

#### Scenario: Backtrack Exceeds max_backtrack_hops

- **WHEN** the current state has saturation rate 0.9 (above threshold 0.8)
- **AND** `SuccessorTracker.find_nearest_unsaturated()` returns an ancestor 12 BACK actions away
- **AND** `max_backtrack_hops` is 8
- **THEN** `plan_backtrack_path` MUST return False (ancestor too far)
- **AND** the PathBuffer MUST NOT be populated
- **AND** the caller MUST fall through to the next action selection tier (scored continuous mode, Tier 4)

#### Scenario: Buffer Creation via Strategy C (Coverage Navigation)

- **WHEN** `path_buffer_enabled` is True and the current state is saturated
- **AND** `SuccessorTracker` has learned transitions to 5 reachable screens
- **AND** screen S1 has 15 elements with 50% coverage (exploration_potential = 7.5)
- **AND** screen S2 has 2 elements with 0% coverage (exploration_potential = 2.0)
- **AND** screen S3 has 20 elements with 90% coverage (exploration_potential = 2.0)
- **THEN** Strategy C MUST select S1 as the navigation target (highest exploration_potential)
- **AND** the PathBuffer MUST be populated with the learned transition path to S1

#### Scenario: Strategy C Before Strategy B Ordering

- **WHEN** the current state is saturated (saturation rate exceeds threshold)
- **AND** Strategy C can plan a path (learned transitions available, high-potential target exists)
- **AND** Strategy B can also plan a path (StaticAnalysisData available, MOP-dense target exists)
- **THEN** Strategy C MUST be evaluated first
- **AND** if Strategy C succeeds, Strategy B MUST NOT be evaluated

#### Scenario: Strategy C Cold Start

- **WHEN** fewer than 3 screens have been discovered (early exploration, < ~30 iterations)
- **AND** `SuccessorTracker` has recorded few transitions
- **THEN** Strategy C MUST return False (insufficient learned data for meaningful navigation)
- **AND** the caller MUST fall through to Strategy B (if available) or Strategy A

#### Scenario: Strategy B Unavailable Without Static Analysis

- **WHEN** `StaticAnalysisData` is None
- **AND** `path_buffer_enabled` is True
- **THEN** Strategy B (MOP navigation) MUST NOT be attempted
- **AND** Strategy C (coverage navigation) MUST still be available (operates on runtime data only)
- **AND** Strategy A (backtrack to unsaturated ancestor) MUST still be available

#### Scenario: Buffer Priority Over Untested Actions

- **WHEN** the PathBuffer has 2 remaining steps
- **AND** the current screen has 3 untested actions
- **THEN** `select_next_action()` MUST return the next buffered action
- **AND** the untested actions MUST NOT be evaluated until the buffer is empty

#### Scenario: Buffer Priority Over Proactive Backtracking

- **WHEN** the PathBuffer has 1 remaining step (from a prior plan)
- **AND** the current state's saturation rate is 0.95 (above `backtrack_saturation_threshold` 0.8)
- **AND** `should_backtrack()` would return True
- **THEN** `select_next_action()` MUST return the buffered action (Tier 1)
- **AND** `should_backtrack()` MUST NOT be evaluated (Tier 3 skipped)
- **AND** proactive backtracking MUST NOT override an active buffer

## Verification Approach

The changes in this delta specification will be validated through a controlled A/B experiment. The experiment uses 10 APKs from the exp02 benchmark set, comparing 3 tools (ape, fastbot, rvagent:pure_algorithm) with 3 repetitions per tool-APK pair at 300 seconds timeout. Primary metrics are method coverage, MOP errors triggered, activity coverage, and UI coverage distribution. Statistical significance is assessed via the Wilcoxon signed-rank test (n=10 per tool — mean of 3 reps per APK; reps are pseudo-replicates). Ape and fastbot serve as unmodified reference baselines for sanity checking. Full experimental design details are in `design.md`.
