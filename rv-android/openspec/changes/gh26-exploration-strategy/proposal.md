# Proposal: Exploration Strategy Improvements

**GitHub Issue**: #26
**Track**: Full SDD (rv-sdd schema)
**Pre-condition**: gh18 (error detection) must be implemented first
**Downstream**: gh9 (calibration campaign) happens after this change

## Why

rv-agent's exploration strategy wastes 20-40% of its iteration budget in saturated states because it retries already-tested actions instead of proactively navigating to unexplored states. The scorer weights undervalue MOP-reaching actions relative to WTG navigation, the text input generator produces low-quality values (PINs in non-PIN fields, no clear-before-type), and there is no reward propagation to learn which action sequences lead to productive outcomes. These issues are architectural -- calibration alone (gh9) cannot fix them because the strategy logic, not the parameter values, is the bottleneck. Fixing the architecture first gives gh9 a sound foundation to optimize.

## What Changes

Nine improvements to the rv-agent exploration strategy, grouped by impact:

**Critical impact:**
- **7.1 Proactive backtracking**: When all untested actions in a state are exhausted, immediately return BACK instead of entering continuous mode. Use the existing (but currently dead) `should_backtrack()` method and `state_stack` for DFS navigation. Adds `backtrack_saturation_threshold` parameter.
- **7.3 Speed optimization**: In `pure_algorithm` mode, skip `capture_screenshot_node` and LLM nodes; cache `screen_desc` when screen hash is unchanged. Preserve gh18's conditional screenshot in `parse_node`. Target: <1s per iteration. Must be mode-aware (per-iteration decision in `decision_router_node`, not a global flag).

**High impact:**
- **7.2 Scorer rebalancing**: Change default weights so MOP-direct (+500) > MOP-transitive (+300) > WTG (+150). Current weights have WTG (+250) nearly equal to MOP-direct (+300) and higher than MOP-transitive (+150), causing the agent to prefer new screens over MOP paths.
- **7.4 MOP-directed navigation / path buffer**: Build a `PathBuffer` that computes multi-step paths using WTG and static analysis data. Two strategies: (A) backtrack to nearest unsaturated ancestor via existing `SuccessorTracker`, (B) navigate toward MOP-dense Activities via BFS on WTG with MOP density weighting. Adds `path_buffer_enabled` and `mop_nav_weight` parameters.
- **7.9 Text input quality**: Fix 6 bugs in `InputValueGenerator` -- duplicate input type inference, wrong default value ordering (PINs in non-PIN fields), LLM path bypassing the generator, `max_variations=5` blocking MOP edge cases, missing input types, and no clear-before-type. Adds `mop_max_input_variations` parameter.

**Medium impact:**
- **7.5 N-step reward propagation**: Propagate rewards backward through action chains (N=5 steps, gamma=0.8) when high-value events occur (new state, new Activity, MOP method reached). Extends `StrengthScorer` with cumulative reward data. Adds `reward_gamma`, `reward_mop_weight`, and `reward_propagation_n` parameters.
- **7.6 Saturation threshold**: Use a configurable threshold (default 0.8) instead of requiring 100% action exhaustion before backtracking. Merged with 7.1's `backtrack_saturation_threshold`.
- **7.7 LLM MOP guidance**: In multimode, enrich the LLM prompt with MOP-specific context from static analysis (which buttons lead to monitored API calls, path descriptions).

**Low impact:**
- **7.8 Dead scorers activation**: Add `GradualDecayScorer` (already defined but not registered) to the active scorer list for smoother priority transitions.

## Capabilities

### New Capabilities

None. All changes modify existing behavior within the agent domain.

### Modified Capabilities

**Agent specification** (`openspec/specs/agent/spec.md`):

The following existing requirements have their behavioral contracts changed:

| Requirement | FR | What Changes |
|---|---|---|
| Coverage-Optimized DFS Strategy | FR26 | Proactive backtracking replaces passive continuous mode as the primary response to action exhaustion. The strategy checks saturation threshold and returns BACK before falling through to least-executed selection. Path buffer takes priority over untested action selection when a buffered path exists. New action selection order: buffer -> untested -> backtrack -> continuous -> BACK. |
| Composite Action Ranking | FR27 | Default scorer weights change (MOP-direct 300->500, MOP-transitive 150->300, WTG 250->150, visitation penalty -10->-15, stochastic probability 0.3->0.15). `GradualDecayScorer` added to active scorer list. `StrengthScorer` extended with cumulative reward from N-step propagation. |
| Stuck State Detection and Recovery | FR29 | Proactive backtracking reduces the frequency of stuck detection triggers because the agent leaves saturated states before reaching the stuck threshold. Stuck detection remains as a safety net for cases where proactive backtracking is insufficient (e.g., app hangs, unresponsive UI). |
| WTG-Guided Navigation | FR30 | `TransitionManager` gains path planning capability for the PathBuffer (BFS to MOP-dense Activities with density weighting). `NavigationGuidance` provides MOP-specific hints to LLM prompts (7.7). |
| Vision-Based Exploration | FR24 | LLM prompts enriched with MOP context from static analysis when available. Speed optimization skips screenshot capture and LLM nodes in pure_algorithm iterations (mode-aware, per-iteration). |

Additionally, the `InputValueGenerator` behavior changes (part of FR26 action execution):
- Input type inference unified (removes duplicate implementation)
- Default value ordering fixed (Faker values first, PINs only for password/PIN fields)
- Clear-before-type added to text input execution
- MOP fields use separate `mop_max_input_variations` limit (default 11)
- Missing input types added (search, url, date, time, number, zip, verification_code)

## Impact

**Modules affected:**
- **rv-agent** (primary): `rvagent_strategy.py`, `scorers.py`, `action_ranker.py`, `agent_config.py`, `input_value_generator.py`, `rv_agent.py`, `learn_node.py`, `algorithm_node.py`, `parse_node.py`, `screen_node.py`, `tool_executor.py`, `transition_manager.py`, `navigation_guidance.py`, `prompts/v13.py`
- No other modules are modified.

**APIs affected:**
- `RVAgentStrategy.select_next_action()` gains path buffer priority tier and proactive backtracking
- `StrengthScorer.score()` incorporates cumulative reward data
- `InputValueGenerator.get_next_value()` changes value ordering and type inference
- `RVAgentConfig` adds 7 new configuration fields (calibration parameters)

**Dependencies:**
- **Pre-condition**: gh18 must be implemented first. This change assumes gh18's `VisualErrorDetector`, `force_fill_input` spatial association, and conditional screenshot capture exist in the codebase. File conflict analysis (see `docs/20260216_rvagent_refatoracao.md` Section 9.1) shows no overlapping insertion points between gh18 and this change.
- **Downstream**: gh9's `parameter_space.py` must be updated with 7 new parameters (+ 2 from gh18 = 9 total new params, bringing the total from 24 to 33) before the calibration execution campaign starts.

**FRs/NFRs affected:**
- **FR26** (Coverage-Optimized DFS Strategy): Proactive backtracking, path buffer, saturation threshold
- **FR27** (Composite Action Ranking): Scorer rebalancing, dead scorers activation, reward propagation
- **FR24** (Vision-Based Exploration): Speed optimization, LLM MOP guidance
- **FR30** (WTG-Guided Navigation): Path buffer BFS integration, MOP prompt enrichment
- **FR29** (Stuck Detection): Reduced trigger frequency due to proactive backtracking
- **NFR04** (Resilience): Stuck detection preserved as safety net
