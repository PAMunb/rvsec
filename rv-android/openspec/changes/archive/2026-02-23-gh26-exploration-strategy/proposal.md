# Proposal: Exploration Strategy Improvements

**GitHub Issue**: #26
**Track**: Full SDD (rv-sdd schema)
**Pre-condition**: gh18 (error detection) must be implemented first
**Downstream**: gh9 (calibration campaign) happens after this change

## Why

rv-agent's exploration strategy wastes 20-40% of its iteration budget in saturated states because it retries already-tested actions instead of proactively navigating to unexplored states. The scorer weights undervalue MOP-reaching actions relative to WTG navigation, the text input generator produces low-quality values (PINs in non-PIN fields, no clear-before-type), and there is no reward propagation to learn which action sequences lead to productive outcomes. These issues are architectural -- calibration alone (gh9) cannot fix them because the strategy logic, not the parameter values, is the bottleneck. Fixing the architecture first gives gh9 a sound foundation to optimize.

## What Changes

Ten improvements to the rv-agent exploration strategy, grouped by impact:

**Critical impact:**
- **7.1 Proactive backtracking**: When all untested actions in a state are exhausted, immediately return BACK instead of entering continuous mode. Use the existing (but currently dead) `should_backtrack()` method with a configurable saturation threshold. Navigation distance is determined by `SuccessorTracker.find_nearest_unsaturated()` BFS, not `state_stack` (which is append-only and does not reflect actual navigation depth). Adds `backtrack_saturation_threshold` parameter.
- **7.3 Speed optimization**: In `pure_algorithm` mode, skip `capture_screenshot_node` and LLM nodes; cache `screen_desc` when screen hash is unchanged. Preserve gh18's conditional screenshot in `parse_node`. Target: <1s per iteration. Must be mode-aware (per-iteration decision in `decision_router_node`, not a global flag).

**High impact:**
- **7.2 Scorer rebalancing**: Change default weights so MOP-direct (+500) > MOP-transitive (+300) > WTG (+150). Current weights have WTG (+250) nearly equal to MOP-direct (+300) and higher than MOP-transitive (+150), causing the agent to prefer new screens over MOP paths.
- **7.4 MOP-directed navigation / path buffer**: Build a `PathBuffer` that computes multi-step paths using WTG and static analysis data. Two strategies: (A) backtrack to nearest unsaturated ancestor via existing `SuccessorTracker`, (B) navigate toward MOP-dense Activities via BFS on WTG with MOP density weighting. PathBuffer is always active (no toggle). Adds `mop_nav_weight` parameter. Uses module-level constants for `MAX_BACKTRACK_HOPS` (8).
- **7.10 Dual Guidance**: Add coverage-directed exploration to complement MOP targeting. Two new components: (1) `CoverageDensityScorer` — an always-active scorer (weight=200) that scores actions based on their destination screen's UI coverage gap, using `SuccessorTracker` (learned transitions) and `UICoverageTracker`. Unknown destinations receive an exploration bonus (`weight * 0.5`). This addresses the "small island" problem: when MOP methods represent only 1-5% of app code, broad UI coverage increases the probability of reaching monitored operations, including those not mapped by static analysis. (2) `PathBuffer Strategy C` — coverage-based BFS navigation on learned transitions toward screens with highest exploration potential (`coverage_gap * element_count`), positioned before Strategy B in Tier 3 (C > B > A ordering). Adds `coverage_density_weight` parameter. Uses module-level constant `MAX_COVERAGE_HOPS` (5).
- **7.9 Text input quality**: Fix 6 bugs in `InputValueGenerator` -- duplicate input type inference, wrong default value ordering (PINs in non-PIN fields), LLM path bypassing the generator, `max_variations=3` blocking MOP edge cases, missing input types, and no clear-before-type. Adds `mop_max_input_variations` parameter.

**Medium impact:**
- **7.5 N-step reward propagation**: Propagate rewards backward through action chains (N=5 steps, gamma=0.8) when high-value events occur (new state, new Activity, MOP method reached). Extends `StrengthScorer` with cumulative reward data. Adds `reward_gamma` parameter. Uses module-level constants for `REWARD_PROPAGATION_N` (5) and `REWARD_MOP_WEIGHT` (5.0).
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
| Coverage-Optimized DFS Strategy | FR26 | Proactive backtracking replaces passive continuous mode as the primary response to action exhaustion. The strategy checks saturation threshold and returns BACK before falling through to least-executed selection. Path buffer takes priority over untested action selection when a buffered path exists. Strategy C adds coverage-based navigation in Tier 3 before Strategy B (C > B > A ordering). New action selection order: buffer -> untested -> backtrack (C > B > A) -> continuous -> BACK. |
| Composite Action Ranking | FR27 | Default scorer weights change (MOP-direct 300->500, MOP-transitive 150->300, WTG 250->150, visitation penalty -10->-15, stochastic probability 0.3->0.15). `GradualDecayScorer` added to active scorer list. `CoverageDensityScorer` added as 9th active scorer (always-active, weight=200, cross-screen coverage guidance). `StrengthScorer` extended with cumulative reward from N-step propagation. |
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
- **rv-agent** (primary): `rvagent_strategy.py`, `scorers.py`, `action_ranker.py`, `agent_config.py`, `input_value_generator.py`, `rv_agent.py`, `learn_node.py`, `algorithm_node.py`, `parse_node.py`, `screen_node.py`, `tool_executor.py`, `transition_manager.py`, `navigation_guidance.py`, `prompts/v17.py` (new — v16 already exists)
- No other modules are modified.

**APIs affected:**
- `RVAgentStrategy.select_next_action()` gains path buffer priority tier and proactive backtracking
- `StrengthScorer.score()` incorporates cumulative reward data
- `InputValueGenerator.get_next_value()` changes value ordering and type inference
- `RVAgentConfig` adds 6 new configuration fields (calibration parameters: `backtrack_saturation_threshold`, `mop_nav_weight`, `mop_max_input_variations`, `reward_gamma`, `reward_score_weight`, `coverage_density_weight`). Five additional values use module-level constants: `PATH_BUFFER_ENABLED` (True), `MAX_BACKTRACK_HOPS` (8), `REWARD_PROPAGATION_N` (5), `REWARD_MOP_WEIGHT` (5.0), `MAX_COVERAGE_HOPS` (5)
- `CoverageDensityScorer.score()` computes cross-screen coverage guidance using SuccessorTracker and UICoverageTracker
- `PathBuffer.plan_coverage_path()` performs BFS on learned transitions toward screens with highest exploration potential
- `SuccessorTracker.get_action_destination()` provides clean accessor for action-to-destination mapping

**Dependencies:**
- **Pre-condition**: gh18 (error detection) — COMPLETE (archived 2026-02-17). This change assumes gh18's `VisualErrorDetector`, `force_fill_input` spatial association, and conditional screenshot capture exist in the codebase. File conflict analysis (see `docs/20260216_rvagent_refatoracao.md` Section 9.1) shows no overlapping insertion points between gh18 and this change.
- **Downstream**: gh9's `parameter_space.py` must be updated with 6 new parameters (+ 7 from gh18 = 13 total new params, bringing the total from 24 to 37) before the calibration execution campaign starts. Five additional values are module-level constants not subject to calibration.

**FRs/NFRs affected:**
- **FR26** (Coverage-Optimized DFS Strategy): Proactive backtracking, path buffer, saturation threshold
- **FR27** (Composite Action Ranking): Scorer rebalancing, dead scorers activation, reward propagation
- **FR24** (Vision-Based Exploration): Speed optimization, LLM MOP guidance
- **FR30** (WTG-Guided Navigation): Path buffer BFS integration, MOP prompt enrichment
- **FR29** (Stuck Detection): Reduced trigger frequency due to proactive backtracking
- **NFR04** (Resilience): Stuck detection preserved as safety net
