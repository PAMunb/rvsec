# Validation Report: gh26-exploration-strategy

**Date**: 2026-02-17
**Validator**: Claude Opus 4.6 (automated validation)
**Change**: `openspec/changes/gh26-exploration-strategy/`
**GitHub Issue**: #26
**Track**: Full SDD (rv-sdd schema)
**Status**: Pre-implementation validation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Methodology](#2-methodology)
3. [Critical Issues](#3-critical-issues)
4. [Consistency and Coherence Analysis](#4-consistency-and-coherence-analysis)
5. [Codebase Validation: Design Claims vs Actual Code](#5-codebase-validation-design-claims-vs-actual-code)
6. [LangGraph Workflow Topology](#6-langgraph-workflow-topology)
7. [Screenshot Handling Analysis](#7-screenshot-handling-analysis)
8. [Traceability: Spec-Design-Task](#8-traceability-spec-design-task)
9. [Acceptance Criteria and Scenario Completeness](#9-acceptance-criteria-and-scenario-completeness)
10. [Design-to-Tasks Coverage](#10-design-to-tasks-coverage)
11. [Impact Assessment: Will This Beat APE and FastBot?](#11-impact-assessment-will-this-beat-ape-and-fastbot)
12. [Strong Points](#12-strong-points)
13. [Weak Points and Risks](#13-weak-points-and-risks)
14. [Contradictions](#14-contradictions)
15. [Missing Scenarios and Improvement Suggestions](#15-missing-scenarios-and-improvement-suggestions)
16. [Executability Assessment](#16-executability-assessment)
17. [PRD Documentation Discrepancies](#17-prd-documentation-discrepancies)
18. [Summary of All Issues](#18-summary-of-all-issues)

---

## 1. Executive Summary

The gh26-exploration-strategy change is an ambitious, well-structured proposal containing 10 improvements across 4 artifacts (proposal, delta spec, design, tasks) totaling ~2,900 lines of specification. The overall quality is high — the design is thorough, the spec scenarios are concrete with WHEN/THEN/AND format and numeric values, and the task decomposition is well-ordered with clear dependency annotations.

**Key finding**: One CRITICAL issue (invariant numbering collision) and several MEDIUM issues were identified. The design claims about the current codebase are largely accurate (18 of 18 major claims confirmed), with 5 minor discrepancies found. The LangGraph topology analysis confirms all design.md claims about node skipping and speed optimization. The plan is executable with the corrections noted below.

**Verdict**: The change is ready for implementation after fixing the CRITICAL invariant numbering issue and addressing the MEDIUM issues. The architecture is sound, the traceability is complete, and the experimental validation design is rigorous.

---

## 2. Methodology

Three parallel validation agents examined different aspects of the change:

1. **Codebase Validation Agent** (a4ff7fc): Read 17+ source files to verify every design.md claim against actual code. Checked method signatures, data structures, scorer weights, dead code, and API contracts.

2. **LangGraph Topology Agent** (a1c2124): Validated the LangGraph workflow graph structure in `rv_agent.py`, compared against PRD FR21, design.md claims, and CLAUDE.md. Verified node skipping behavior and routing logic.

3. **Spec Consistency Agent** (a603b9e): Compared the delta spec against the main agent spec (`openspec/specs/agent/spec.md`). Checked invariant numbering, FR modifications, scenario coverage, and gh18 compatibility.

Additionally, all four change artifacts (proposal.md, specs/agent/spec.md, design.md, tasks.md) were read in full and cross-referenced.

---

## 3. Critical Issues

### 3.1 CRITICAL: Invariant Numbering Collision (INV-AGT-20 through INV-AGT-27)

**Location**: Delta spec `specs/agent/spec.md` lines 46-60

**Problem**: The delta spec defines invariants INV-AGT-19 through INV-AGT-27 for gh26 features. However, the main spec (`openspec/specs/agent/spec.md`) already contains INV-AGT-20 through INV-AGT-27 from gh18 (validation error detection). The content is completely different:

| Invariant | Main Spec (gh18) | Delta Spec (gh26) |
|---|---|---|
| **INV-AGT-20** | Error detection via VisualErrorDetector | N-step reward propagation backward through N actions |
| **INV-AGT-21** | Reset stuck_screen_count on validation error | GradualDecayScorer registration and formula |
| **INV-AGT-22** | force_fill_input and spatial association | Proactive backtracking saturation threshold |
| **INV-AGT-23** | Validation errors not connected to FailedActionScorer | InputValueGenerator clear-before-type |
| **INV-AGT-24** | Error recovery loop protection (MAX_ERROR_RECOVERY) | Speed optimization for algorithm iterations |
| **INV-AGT-25** | parse_ui_node screenshot on hash repeat | SuccessorTracker return type change |
| **INV-AGT-26** | Spatial association with widget-type boosts | RewardPropagator cumulative reward cap |
| **INV-AGT-27** | VisualErrorDetector system bar filtering | CoverageDensityScorer always active |

**Note on INV-AGT-19**: The main spec has a gap (jumps from INV-AGT-18 to INV-AGT-20). The delta spec fills this gap with its INV-AGT-19 (PathBuffer invalidation). This single invariant is fine. The collision starts at INV-AGT-20.

**Required fix**: Renumber gh26 invariants to INV-AGT-28 through INV-AGT-36:

| Current (delta) | Corrected | Content |
|---|---|---|
| INV-AGT-19 | **INV-AGT-28** | PathBuffer invalidation on no state change |
| INV-AGT-20 | **INV-AGT-29** | N-step reward propagation |
| INV-AGT-21 | **INV-AGT-30** | GradualDecayScorer registration |
| INV-AGT-22 | **INV-AGT-31** | Proactive backtracking saturation threshold |
| INV-AGT-23 | **INV-AGT-32** | InputValueGenerator clear-before-type |
| INV-AGT-24 | **INV-AGT-33** | Speed optimization for algorithm iterations |
| INV-AGT-25 | **INV-AGT-34** | SuccessorTracker return type change |
| INV-AGT-26 | **INV-AGT-35** | RewardPropagator cumulative reward cap |
| INV-AGT-27 | **INV-AGT-36** | CoverageDensityScorer always active |

**Impact**: Tasks.md references invariant numbers (e.g., task 1.3 references INV-AGT-20, task 2.5 references INV-AGT-23). All cross-references in tasks.md, design.md, and the delta spec must be updated to use the corrected numbers.

---

## 4. Consistency and Coherence Analysis

### 4.1 Internal Consistency Within Artifacts

**Proposal ↔ Delta Spec**: Consistent. The proposal lists 10 improvements; the delta spec covers all 10 via MODIFIED (FR26, FR27, FR29, FR30, FR24) and ADDED (N-Step Reward, Text Input Quality, Path Buffer) requirements. The proposal says "No new capabilities" which is correct — all changes modify existing behavior.

**Proposal ↔ Design**: Consistent. The proposal's impact section lists 14 files; the design's Key Components table lists 16 components in those files. The extra entries are due to the design correctly distinguishing between modified components within the same file (e.g., multiple scorers in `scorers.py`).

**Delta Spec ↔ Design**: Consistent with one notable difference. The design's API section shows `select_next_action()` with a 5-tier flow and the spec says "5-tier" in the action selection order, but the design diagram at line 29-68 shows a 6-tier flow (Buffer → Untested → Backtrack → PathBuffer strategies → Continuous → BACK). This is not a contradiction — the spec's "5 tiers" counts the PathBuffer planning strategies (C/B/A) as part of Tier 3 (proactive backtracking), while the diagram separates them visually. The spec is the authoritative source and its 5-tier count is correct.

**Design ↔ Tasks**: See [Section 10](#10-design-to-tasks-coverage) for detailed coverage analysis.

### 4.2 Cross-Artifact Coherence

**Config Parameters**: The proposal mentions "11 new configuration fields," the spec's Data Contracts section lists exactly 11, the design's API section shows all 11 with Field() definitions, and task 1.1 creates all 11. Coherent.

**Scorer Weights**: Proposal says "MOP-direct (+500) > MOP-transitive (+300) > WTG (+150)." Spec Table in FR27 confirms: 300→500, 150→300, 250→150. Design's API section shows the same defaults. Task 1.2 implements these changes. Coherent.

**Dead Code**: Design D6 lists 5 items to remove. Task group 1.5 has corresponding removal tasks for each item. The delta spec does not mention dead code removal (correct — dead code is a P3 concern, not a spec concern). Coherent.

**Experimental Validation**: Proposal does not mention it. Spec's Verification Approach section describes the A/B experiment. Design has a full Experimental Validation section. Tasks Groups 0 and 10 implement the experiment. Coherent.

### 4.3 gh18 Pre-condition Handling

The delta spec states: "This delta spec assumes gh18 (validation error detection) has already been implemented." The design similarly states: "Pre-condition: gh18 must be implemented first."

The design correctly identifies gh18-specific features it depends on:
- `VisualErrorDetector` and `force_fill_input` in `algorithm_node` (design line 23)
- Conditional screenshot capture in `parse_node` (design line 23, 220)
- `error_detection_screenshot` state variable (confirmed in `parse_node.py` lines 62-69)

The design also correctly handles gh18 interactions:
- Reward propagation includes error recovery actions (spec line 448, design line 1185)
- Speed optimization preserves gh18's conditional screenshot (design line 220, 994)
- Task 7.4 explicitly tests "gh18 integration after caching"

**Assessment**: gh18 pre-condition is well-handled.

---

## 5. Codebase Validation: Design Claims vs Actual Code

The codebase validation agent read 17+ source files and verified every major design.md claim. Here is the complete report:

### 5.1 Confirmed Claims (18/18 major claims)

| # | Claim | File:Line | Status |
|---|-------|-----------|--------|
| 1 | `should_backtrack()` exists and is dead code (never called) | `rvagent_strategy.py:447-484` | **CONFIRMED** |
| 2 | `state_stack` is append-only (never popped) | `rvagent_strategy.py:200, 273` | **CONFIRMED** |
| 3 | `RVAgentState` dataclass exists with 4 fields | `rvagent_strategy.py:51-57` | **CONFIRMED** |
| 4 | `visited_states` is redundant with `graph.states.keys()` | `rvagent_strategy.py:201, 274` | **CONFIRMED** |
| 5 | `GradualDecayScorer` exists but NOT registered | `scorers.py:138-181` (definition), not in `rvagent_strategy.py:186-197` (registration) | **CONFIRMED** |
| 6 | 8 scorers registered in `__init__` | `rvagent_strategy.py:186-197` | **CONFIRMED** (MopScorer, WtgScorer, SaturationScorer, ComponentPriorityScorer, StrengthScorer, FailedActionScorer, SystemElementFilter, VisitationPenaltyScorer) |
| 7 | Current scorer weights (MOP=300/150, WTG=250, Penalty=-10) | `scorers.py` + `agent_config.py` | **CONFIRMED** exact values |
| 8 | `find_nearest_unsaturated()` returns `Optional[str]` | `successor_tracker.py:329` | **CONFIRMED** |
| 9 | `back_successors: Dict[str, Set[str]]` | `successor_tracker.py:90` | **CONFIRMED** |
| 10 | PINs first in `_get_regular_values()` for unknown types | `input_value_generator.py:168` | **CONFIRMED** |
| 11 | Missing input types (search, url, date, etc.) | `input_value_generator.py:138-161` | **CONFIRMED** |
| 12 | No `clear_text()` before `input_text()` in ToolExecutor | `tool_executor.py:145-162` | **CONFIRMED** |
| 13 | LangGraph topology matches description | `rv_agent.py:186-264` | **CONFIRMED** (see Section 6) |
| 14 | Two independent `_visited_activities` tracking sources | `rvagent_strategy.py:729` + `transition_manager.py:93` | **CONFIRMED** |
| 15 | No PathBuffer, RewardPropagator, or CoverageDensityScorer exist | All source files | **CONFIRMED** |
| 16 | 11 proposed config fields do not exist yet | `agent_config.py` | **CONFIRMED** |
| 17 | `record_action_failure()` is never called | `screen_node.py:120-123` (TODO comment confirms) | **CONFIRMED** |
| 18 | `_infer_input_type()` duplicate exists in strategy | `rvagent_strategy.py:738-760` | **CONFIRMED** |

### 5.2 Discrepancies Found (5 items)

| # | Design Claim | Actual Code | Severity | Impact |
|---|-------------|-------------|----------|--------|
| D1 | `max_variations=5` blocks MOP edge cases | `RVAgentConfig.max_input_variations: int = 3` at `agent_config.py:189`. The `InputValueGenerator.__init__` has default 5, but strategy overrides with config value (3) | LOW | Strengthens the argument — actual situation is worse than claimed. Update design.md to say `max_variations=3` |
| D2 | VisitationPenaltyScorer proposed default -15 | Current default is `-10.0` at `scorers.py:420` | LOW | Not a real discrepancy — design proposes changing from -10 to -15. But the Data Flow section (line 889) shows -15 as if it's already active. Clarify this is the NEW default |
| D3 | `visited_states` described as trivially removable | Used in `_get_visited_activities()` (line 729), `record_transition()` (lines 430, 439), `get_statistics()` (line 929), `reset()` (line 887) — 8+ reference sites total | LOW | Design accounts for updating callers (task 1.5.2) but doesn't enumerate all sites. Task 1.5.2 says "~8 sites" which is approximately correct |
| D4 | `DynamicStateGraph.record_transition()` called with 3 args in strategy | Actual method at `dynamic_state_graph.py:229` takes `(self, from_hash, to_hash, timestamp=None)` — the third arg from strategy (`[{"action": action}]`) maps to `timestamp` | MEDIUM | Possible latent type mismatch where a list is passed as timestamp. Investigate before gh26 implementation — this could cause unexpected behavior in transition logging |
| D5 | Coverage formula divergence noted | `SuccessorTracker.get_successor_coverage()` at line 144-148 returns 1.0 for 0 actions; `ScreenNode.get_coverage()` at line 73-75 returns 0.0 | LOW | Design correctly identifies this and task 1.5.3 fixes it |

---

## 6. LangGraph Workflow Topology

### 6.1 Actual Topology (from rv_agent.py:186-264)

```
Nodes (8):
  parse_ui, decision_router, algorithm_node, capture_screenshot,
  llm_generate, validate_action, execute, learn

Edges (11):
  START → parse_ui (entry point)
  parse_ui → decision_router (unconditional)
  decision_router → capture_screenshot (conditional: "llm")
  decision_router → algorithm_node  (conditional: "algorithm")
  decision_router → END            (conditional: "end")
  capture_screenshot → llm_generate (unconditional)
  llm_generate → validate_action   (unconditional)
  algorithm_node → validate_action  (unconditional)
  validate_action → execute        (unconditional)
  execute → learn                  (unconditional)
  learn → END                      (unconditional)

Execution model: External while loop in run(), graph.invoke() once per iteration.
```

### 6.2 Design.md Claims — All Correct

| Claim | Verdict |
|-------|---------|
| "Algorithm path already bypasses screenshot/LLM nodes" | **CORRECT** — "algorithm" edge goes directly to algorithm_node, skipping capture_screenshot and llm_generate |
| "No topology change needed for speed optimization" | **CORRECT** — existing conditional edges handle node skipping |
| "No new skip logic needed in graph or decision_router" | **CORRECT** — the new speed optimization is only parse_node caching |
| "decision_router_node: add tracking log for algorithm-fast-path" | **CORRECT** — current routing already has tracking via `track.route()`, gh26 adds algorithm-specific tracking |
| "learn_node: reward propagation trigger after action success recording" | **CORRECT** — `_record_action_success()` exists at line 170, insertion point identified |

### 6.3 How gh26 Changes the Flow

gh26 does NOT change the LangGraph graph topology. The 8 nodes and 11 edges remain identical. The changes are:

1. **parse_node**: Adds screen_desc caching (reuse when hash unchanged)
2. **decision_node**: Adds `[RVTRACK:STRATEGY]` logging for algorithm-fast-path
3. **algorithm_node**: `strategy.select_next_action()` gains the new 5-tier flow
4. **learn_node**: Adds `RewardPropagator.record_action()` + `propagate()` after `_record_action_success()`, adds PathBuffer invalidation check

---

## 7. Screenshot Handling Analysis

The change correctly distinguishes between two independent screenshot paths:

### 7.1 LLM Screenshot Path (capture_screenshot_node)
- **Current**: Fires on every LLM iteration via graph topology (decision_router → "llm" → capture_screenshot → llm_generate)
- **gh26 impact**: None. Algorithm iterations already skip this node via the "algorithm" edge. No new skip logic needed.
- **Multimode**: Algorithm iterations (30%) skip; LLM iterations (70%) include. Per-iteration decision via routing_manager.

### 7.2 Error Detection Screenshot Path (parse_node, gh18)
- **Current**: Fires in parse_node when `screen_hash == previous_screen_hash` AND `error_detection_enabled`
- **gh26 impact**: Preserved. The screen_desc caching optimization is independent — it caches the ScreenDescription, not the screenshot. The conditional screenshot check (parse_node.py:62-69) continues to fire on hash-repeat.
- **Confirmed**: Task 7.4 explicitly tests this: "test_screen_desc_cache_preserves_error_detection_screenshot"

### 7.3 Assessment

Screenshot handling is correctly analyzed and preserved. The speed optimization targets the visitor pipeline (ScreenDescription construction), not screenshot capture. Both screenshot paths remain functional.

---

## 8. Traceability: Spec-Design-Task

### 8.1 Mapping Table Verification

The design.md contains a 16-row mapping table (Spec → Implementation → Test) at lines 123-143. Verification:

| Requirement / Change | FR | Has Design API? | Has Task? | Has Test Plan? |
|---|---|---|---|---|
| Proactive backtracking | FR26 | `select_next_action()` + `should_backtrack()` | Tasks 5.1-5.4 | `test_proactive_backtracking.py` |
| PathBuffer integration | FR26, FR30 | `PathBuffer` class + integration | Tasks 6.1-6.7 | `test_path_buffer.py` |
| Saturation threshold | FR26 | `should_backtrack()` | Tasks 5.1-5.3 | `test_saturation_threshold.py` |
| Scorer rebalancing | FR27 | Config defaults | Tasks 1.2, 3.1 | `test_scorer_weights.py` |
| GradualDecayScorer activation | FR27 | Registration in `__init__` | Task 3.3 | `test_gradual_decay_scorer.py` |
| N-step reward propagation | FR27 | `RewardPropagator` class | Tasks 4.1-4.5 | `test_reward_propagator.py` |
| Speed optimization | FR24 | parse_node caching | Tasks 7.1-7.4 | `test_speed_optimization.py` |
| LLM MOP guidance | FR24, FR30 | NavigationGuidance extension | Tasks 8.1-8.2 | `test_mop_guidance.py` |
| Text input quality | FR26 | InputValueGenerator fixes | Tasks 2.1-2.7 | `test_input_value_generator_fixes.py` |
| BFS path planning | FR30 | TransitionManager new method | Tasks 6.3-6.4 | `test_transition_manager_bfs.py` |
| SuccessorTracker return type | FR26 | `find_nearest_unsaturated()` | Task 5.5 | `test_find_nearest_unsaturated_hop_count.py` |
| Reduced stuck trigger | FR29 | (indirect) | (indirect via proactive backtracking) | `test_stuck_detection_with_backtracking.py` |
| CoverageDensityScorer | FR27 | `CoverageDensityScorer` class | Tasks 3.5.1-3.5.6 | `test_coverage_density_scorer.py` |
| PathBuffer Strategy C | FR26 | `plan_coverage_path()` | Tasks 3.5.5-3.5.6 | `test_path_buffer_coverage.py` |
| Config parameters (11) | -- | RVAgentConfig fields | Task 1.1 | `test_config_new_params.py` |
| Dead code removal | P3 | (removal) | Tasks 1.5.1-1.5.5 | `test_dead_code_removal.py` |

**Assessment**: Complete traceability. Every spec requirement has a design API, at least one implementation task, and at least one test.

### 8.2 Cross-Reference Integrity

- **FR26** is traced through: spec scenarios (8) → design `select_next_action()` API → tasks 5.1-5.4, 6.1-6.7 → tests
- **FR27** is traced through: spec scenarios (11) → design scorer APIs → tasks 1.2, 3.1-3.3, 3.5.1-3.5.6, 4.1-4.4 → tests
- **FR29** is traced through: spec scenarios (6) → design (indirect, proactive backtracking reduces frequency) → task 9.4 edge cases → tests
- **FR30** is traced through: spec scenarios (7) → design TransitionManager BFS + NavigationGuidance → tasks 6.3-6.4, 8.1-8.2 → tests
- **FR24** is traced through: spec scenarios (7) → design parse_node caching + MOP prompts → tasks 7.1-7.4, 8.1-8.2 → tests

---

## 9. Acceptance Criteria and Scenario Completeness

### 9.1 Scenario Count by Requirement

| Requirement | Scenarios | Assessment |
|---|---|---|
| FR26 (Coverage-Optimized DFS Strategy) | 8 | Good. Covers untested selection, proactive backtracking, saturation fallthrough, buffer priority, continuous mode, successor re-enablement, package filtering, all failed, Strategy C |
| FR27 (Composite Action Ranking) | 11 | Excellent. Covers MOP prioritization, MOP-transitive vs WTG, failed action blacklisting, WTG scoring, GradualDecay behavior, reward-enhanced strength, stochastic selection, component priority, CoverageDensity known/unknown/synergy |
| FR29 (Stuck State Detection) | 6 | Good. Covers Level 1, form exclusion, Level 2 BFS, Level 2 restart, deadlock, proactive backtracking reduces frequency |
| FR30 (WTG-Guided Navigation) | 7 | Good. Covers available/unavailable, LLM hint with MOP, algorithm scoring, BFS path planning, MOP density weighting, saturation-aware path |
| FR24 (Vision-Based Exploration) | 7 | Good. Covers LLM generation, multimodal message, navigation hints, timeout, pure algorithm fast path, mode-aware skipping, LLM MOP context |
| N-Step Reward Propagation | 13 | Excellent. Covers MOP propagation, discount factor, new state, same state, accumulation, no SA degradation, concurrent types, MOP proxy signal, oscillation trap, end-to-end degradation, error recovery, cap boundary |
| Text Input Quality | 8 | Good. Covers unified inference, Faker first, PINs for password, clear-before-type, MOP variations, search/url/date types, LLM tracking |
| Path Buffer | 12 | Excellent. Covers Strategy A/B/C creation, execution sequence, invalidation, disabled, max hops, cold start, no SA, buffer priority, C before B ordering |

**Total**: ~72 scenarios across all requirements.

### 9.2 Missing Scenarios

| # | Missing Scenario | Where | Severity |
|---|-----------------|-------|----------|
| MS1 | Cumulative reward cap boundary behavior (delta INV-AGT-26) | N-Step Reward Propagation | MINOR — INV-AGT-26 defines the cap but no scenario tests what happens at the boundary. Task 9.4 edge cases does include `test_cumulative_reward_cap_boundary` but the spec itself lacks the scenario |
| MS2 | Text input cycling behavior after max_variations exhausted | Text Input Quality | MINOR — "cycling" is mentioned but not defined. Does it restart from first value? Return None? |
| MS3 | PathBuffer behavior immediately after invalidation | Path Buffer | MINOR — Invalidation clears buffer, but what happens on the VERY NEXT `select_next_action()` call? Does it re-plan immediately or fall through to Tier 2? (Design implies Tier 2-5, but no explicit scenario) |
| MS4 | All three strategies fail in sequence (C fails, B fails, A fails) | Path Buffer | MINOR — Individual failure scenarios exist, but no scenario for cascading failure. Task 9.4 edge cases partially covers this via `test_graceful_degradation_without_static_analysis` |
| MS5 | Strategy C with stale learned transitions | Path Buffer | MINOR — SuccessorTracker records may not reproduce (dynamic content, scroll position). Design acknowledges this in risk section but no spec scenario |

### 9.3 Suggested Additional Scenarios

1. **Reward cap clamping**: "WHEN action A in state S has cumulative_reward = 14.0 AND a new propagation event would add 3.2 THEN cumulative_reward MUST be clamped to 15.0 (not 17.2)"

2. **Input cycling**: "WHEN all `max_variations` values have been generated for field F AND `get_next_value()` is called again THEN the generator MUST return the first value in the cycle (round-robin) AND MUST NOT return None"

3. **Post-invalidation flow**: "WHEN PathBuffer is invalidated due to hash-unchanged AND the next `select_next_action()` call occurs THEN the strategy MUST proceed to Tier 2 (untested actions) AND MUST NOT attempt to re-plan a path in the same iteration"

4. **Cascading strategy failure**: "WHEN the state is saturated AND Strategy C returns False (cold start) AND Strategy B returns False (no SA) AND Strategy A returns False (ancestor too far) THEN a plain BACK action MUST be returned AND the agent MUST NOT crash"

---

## 10. Design-to-Tasks Coverage

### 10.1 Coverage Matrix

Every item in the design.md has a corresponding task. Verification:

| Design Section | Task Group | Coverage |
|---|---|---|
| PathBuffer class (D1) | Group 6 (6.1-6.7) | Complete |
| RewardPropagator class (D2) | Group 4 (4.1-4.5) | Complete |
| Scorer rebalancing (D3) | Group 3 (3.1-3.3) | Complete |
| Text input fixes (D4) | Group 2 (2.1-2.7) | Complete |
| Speed optimization (D5) | Group 7 (7.1-7.4) | Complete |
| Dead code removal (D6) | Group 1.5 (1.5.1-1.5.5) | Complete |
| Config parameters (11) | Group 1 (1.1-1.6) | Complete |
| CoverageDensityScorer | Group 3.5 (3.5.1-3.5.6) | Complete |
| Proactive backtracking | Group 5 (5.1-5.5) | Complete |
| LLM MOP guidance | Group 8 (8.1-8.2) | Complete |
| Experimental validation | Groups 0, 10 | Complete |
| Integration testing | Group 9 | Complete |

### 10.2 Task Dependencies

The dependency annotations in the tasks.md header (lines 1-21) are correct:

```
Group 0 → (before any code changes)
Group 1 → (all others depend on it)
Group 1.5 → (depends on 1; must complete before 5, 6)
Groups 2, 3, 3.5, 4 → (parallel after 1.5)
Group 5 → (depends on 1, 1.5)
Group 6 → (depends on 1, 1.5, 5)
Groups 7, 8 → (parallel with 2-6)
Group 9 → (after all groups)
Group 10 → (after 9 + rv-verify)
```

**One dependency gap**: Task 3.5.6 (implement `plan_coverage_path()` + integrate into Tier 3) explicitly notes "DEPENDS ON: Group 6 (PathBuffer class must exist)." This is correct and properly documented.

### 10.3 Subagent Dispatch Feasibility

The tasks.md suggests "3-4 parallel dispatches" given 16+ files. This is feasible:

- **Parallel batch 1**: Groups 2, 3, 7, 8 (independent, ~15 files total, 4 subagents with 3-4 files each)
- **Sequential**: Group 1 → Group 1.5 → Group 5 → Group 6 (dependency chain)
- **Parallel batch 2**: Groups 3.5, 4 (after Group 1.5)
- **Final**: Group 9 → Group 10

---

## 11. Impact Assessment: Will This Beat APE and FastBot?

### 11.1 Competitive Analysis

The design draws from both APE and FastBot concepts while adding rv-agent's unique MOP targeting:

| Feature | APE | FastBot | rv-agent (gh26) |
|---|---|---|---|
| State abstraction | CEGAR-based | Fixed | DFS with ScreenNode (unchanged) |
| Learning | Model refinement | SARSA Q-table | Simplified N-step reward (new) |
| Navigation | Random/guided | DFS + Q-value | DFS + PathBuffer + BFS + coverage (new) |
| MOP targeting | None | None | Scorer + PathBuffer Strategy B (new) |
| Backtracking | Implicit | Implicit | Proactive saturation-based (new) |
| Coverage guidance | None | None | CoverageDensityScorer + Strategy C (new) |
| Text input | Basic | Basic | Context-aware with Faker + edge cases (improved) |
| Speed | Fast | Fast | Optimized parsing + node skipping (improved) |

### 11.2 Expected Impact per Improvement

| Improvement | Expected Impact | Confidence |
|---|---|---|
| Proactive backtracking | HIGH — recovers 20-40% wasted iterations | High (directly addresses biggest bottleneck) |
| Scorer rebalancing | MEDIUM — better MOP targeting | Medium (depends on app structure) |
| PathBuffer Strategy B (MOP BFS) | HIGH — unique to rv-agent, no competitor has this | Medium (depends on WTG quality) |
| PathBuffer Strategy C (coverage BFS) | MEDIUM-HIGH — addresses "small island" problem | Medium (new, untested concept) |
| N-step reward propagation | MEDIUM — simplified SARSA captures ~80% benefit | Medium (gamma/N values need tuning) |
| Text input fixes | MEDIUM — stops wasting iterations on PINs | High (clear bugs with clear fixes) |
| Speed optimization | LOW-MEDIUM — more iterations = more exploration | High (simple caching) |
| GradualDecayScorer activation | LOW — smoother transitions | Low (never tested) |
| CoverageDensityScorer | MEDIUM — broad coverage surface | Medium (new concept) |
| LLM MOP guidance | LOW — only affects multimode | Medium (only relevant for multimode) |

### 11.3 Realistic Assessment

The design acknowledges (Risk section): "The realistic combined gain is ~60-70% of the naive sum of individual estimates." This is a realistic assessment.

**Will it beat APE and FastBot?** The improvements address the most impactful bottleneck (passive backtracking wasting 20-40% of iterations) and add capabilities neither competitor has (MOP-directed BFS, coverage-guided navigation, MOP-specific reward propagation). The experimental validation design is sound (10 APKs, Wilcoxon test, paired comparison). If the default parameter values are reasonable (which they appear to be), rv-agent should show statistically significant improvement in `cov_method` and `cov_rv_method`.

**Risk**: The validation experiment uses default parameters. If defaults are suboptimal, the improvements may not show statistical significance until gh9 calibration finds better values. However, the proactive backtracking and text input fixes should show immediate improvement regardless of parameter values.

---

## 12. Strong Points

1. **Architectural soundness**: The 5-tier action selection flow is well-structured with clear fallback ordering. Each tier has a specific purpose and the transition conditions are unambiguous.

2. **Dual guidance architecture**: The combination of MOP targeting (precision) + coverage guidance (broad surface) via CoverageDensityScorer is a well-reasoned approach to the "small island" problem. Neither APE nor FastBot has this capability.

3. **PathBuffer design (D1)**: Separating the buffer from the strategy is correct — it keeps `select_next_action()` focused and makes the buffer independently testable. The three strategies (A/B/C) with clear priority ordering (C > B > A) are well-motivated.

4. **RewardPropagator simplicity (D2)**: The decision to use simplified N-step propagation instead of full SARSA is well-justified by P1. The implementation reuses existing ScreenNode data structures instead of introducing new Q-tables.

5. **Dead code removal first (D6)**: Removing dead code BEFORE implementing new features prevents building on dead infrastructure. This is a sound engineering practice.

6. **Comprehensive experimental validation**: The A/B experiment design with 10 APKs, 3 tools, 3 reps, paired Wilcoxon test, and Docker execution architecture is rigorous and reproducible.

7. **Edge case coverage in tasks**: Task 9.4 contains 23 edge-case integration tests covering scenarios like oscillation traps, dialog blocking, cyclic graph termination, dead-end replanning, app restart persistence, and partial static analysis. This is unusually thorough.

8. **Risk documentation**: 8 risks with specific mitigations. The `should_backtrack()` dead code risk (R2) correctly identifies the need for unit tests BEFORE integration.

9. **P1-compatible input type inference**: Replacing the 40-line duplicate `_infer_input_type()` with a ~15-line inline helper that uses Node metadata directly is a clean simplification.

10. **Cumulative reward cap (INV-AGT-26)**: Prevents score inflation over 300+ iterations. This shows awareness of long-running session dynamics.

---

## 13. Weak Points and Risks

### 13.1 Strategy C Novelty Risk

Strategy C (coverage-based BFS on learned transitions) is a novel concept not present in the literature (APE, FastBot, Stoat, etc.). While the rationale is sound, there is no empirical evidence that it works. The cold start threshold ("fewer than 3 screens") is arbitrary.

**Mitigation**: The design includes a `--skip-static` validation variant (task 10.3b) to measure Strategy C in isolation. This is good, but the cold start threshold should be configurable (add to gh9 calibration params).

### 13.2 Transition Irreproducibility

SuccessorTracker records `(from_hash, action_sig) → to_hash` based on observed transitions. These may not reproduce due to dynamic content, scroll position, or timing. Both CoverageDensityScorer and Strategy C depend on this data.

The design acknowledges this (Risk section, line 1002) with mitigation: "PathBuffer's invalidation mechanism catches this." However, CoverageDensityScorer has no invalidation — it queries stale destination data and may score actions based on obsolete transitions.

**Suggestion**: Consider adding a `transition_confidence` metric (e.g., number of times a transition was observed / total observations) and weighting CoverageDensityScorer scores by confidence.

### 13.3 DynamicStateGraph.record_transition() Latent Bug

The codebase validation agent discovered a potential latent bug: `rvagent_strategy.py:424` calls `self.graph.record_transition(from_hash, to_hash, [{"action": action}])` with 3 arguments, but the actual method signature at `dynamic_state_graph.py:229` is `(self, from_hash, to_hash, timestamp=None)`. The third argument (a list of dicts) would be passed as `timestamp`.

**Impact**: This doesn't crash (Python is dynamically typed) but the `timestamp` field would contain a list instead of a float. This is not a gh26 issue, but it should be investigated before gh26 implementation since gh26 modifies `record_transition()` callers.

### 13.4 PathBuffer Single-Action Limitation

The design openly acknowledges (line 1008) that PathBuffer uses single-action transitions, not full action sequences. If navigating to a screen required filling a form first, the PathBuffer would attempt only the final "Submit" click, which may fail.

The hash-unchanged invalidation handles the most common failure case, but the design accepts that some transitions may produce unexpected states (not caught by invalidation). This is a reasonable trade-off given P1, but should be documented as a known limitation for gh9 calibration analysis.

### 13.5 GradualDecayScorer Untested Defaults

The GradualDecayScorer has been defined since the codebase was written but never registered or tested in production. Its defaults (base=200, rate=0.7, min_visits=5) are assumptions, not empirically validated values.

**Mitigation**: The design correctly defers optimization to gh9. However, the `min_visits` cutoff (return 0.0 when visits >= 5) is aggressive — it completely stops scoring an element after just 5 visits. Consider making this configurable via `gradual_decay_min_visits` in gh9.

### 13.6 Reward Propagation Proxy Signal

The MOP reward (+5.0) uses `callback_signature` from static analysis as a proxy signal. This means "the action CAN reach MOP," not that MOP was actually triggered. The design acknowledges this (lines 961-963) and accepts the trade-off.

**Risk**: In apps with many false-positive static analysis mappings (e.g., generic utility methods flagged by REACH), the +5.0 reward may frequently fire for non-productive actions, creating noise in the reward signal.

**Suggestion**: Consider a lower default for `reward_mop_weight` (3.0 instead of 5.0) or add a `callback_confidence` factor. This is better addressed in gh9 calibration.

---

## 14. Contradictions

### 14.1 No Semantic Contradictions Found

Between the proposal, delta spec, design, and tasks, no semantic contradictions were identified. All differences between the main spec and delta spec are intentional modifications properly declared as MODIFIED or ADDED requirements.

### 14.2 Numeric Inconsistency

The design Data Flow section (line 889) shows `VisitationPenaltyScorer: -15 * log(1 + visits)` as if it is the current value. The actual current default is -10.0 (`scorers.py:420`). The design proposes changing it to -15 (task 1.2), but the Data Flow section should clarify this is the NEW default, not the current one.

### 14.3 max_variations Inconsistency

The design says "max_variations=5 blocks MOP edge cases" (line 17), but the actual default in `RVAgentConfig` is `max_input_variations: int = 3` (even worse than claimed). The design should say `max_variations=3` for accuracy. The `InputValueGenerator.__init__` has a local default of 5, but this is overridden by the config value of 3.

### 14.4 Action Selection "5-tier" vs "6-tier"

The spec says "5-tier" action selection. The design architecture diagram (lines 29-68) visually shows 6 levels. This is a presentation difference, not a contradiction — the PathBuffer strategy evaluation (C > B > A) is part of Tier 3 in the spec but shown as a separate level in the diagram.

---

## 15. Missing Scenarios and Improvement Suggestions

### 15.1 Suggested Scenarios (not yet in spec)

1. **Reward cap boundary test** (for INV-AGT-26/35):
   ```
   WHEN action A in state S has cumulative_reward = 14.0
   AND a new propagation event would add 3.2
   THEN cumulative_reward MUST be clamped to 15.0
   ```

2. **Input value cycling**:
   ```
   WHEN all max_variations values have been generated for field F
   AND get_next_value() is called again
   THEN the generator MUST [restart cycle / return None]
   ```

3. **Cascading strategy failure**:
   ```
   WHEN state is saturated AND C fails AND B fails AND A fails
   THEN a plain BACK action MUST be returned
   ```

4. **PathBuffer re-plan after invalidation**:
   ```
   WHEN PathBuffer is invalidated in learn_node
   AND next iteration routes to algorithm_node
   THEN Tier 3 MAY re-plan a new buffer if should_backtrack() returns True
   ```

### 15.2 Architecture Suggestions

1. **Add `gradual_decay_min_visits` to config**: Currently hardcoded to 5. Making it configurable allows gh9 to optimize it.

2. **Add cold start threshold parameter for Strategy C**: Currently hardcoded to "fewer than 3 screens." Making it configurable would allow tuning.

3. **Consider `transition_confidence` for CoverageDensityScorer**: Weight scores by how many times a transition has been reproduced, reducing impact of stale data.

### 15.3 Task Suggestions

1. **Add task 1.5.0**: Investigate the `DynamicStateGraph.record_transition()` latent bug (3rd arg as timestamp) before implementing gh26 changes that modify this area.

2. **Add task 0.3c**: Validate the 10 exp02 APKs still install on current emulator images. Old APKs may have API level compatibility issues with newer Android SDK versions.

---

## 16. Executability Assessment

### 16.1 Is the Plan Executable?

**Yes, with the corrections noted above.** The artifacts are sufficiently detailed for implementation:

- **Tasks are decomposed to implementable granularity**: Each task specifies the file, the change, and the expected test outcome
- **Dependencies are clear**: The subagent dispatch hints and ordering notes prevent out-of-order implementation
- **TDD approach**: Most implementation groups start with test creation (RED), then implementation (GREEN)
- **Acceptance criteria are concrete**: WHEN/THEN/AND format with specific numeric values
- **Error handling is specified**: 11 error scenarios with recovery strategies
- **API signatures are complete**: Python code with full type annotations and docstrings

### 16.2 Estimated Implementation Scope

| Group | New Tests | New Code Files | Modified Files | Estimated Complexity |
|---|---|---|---|---|
| 0 (Baseline) | 0 | 3 docker-compose | 0 | Medium (Docker setup) |
| 1 (Config) | ~9 | 0 | 2 | Low |
| 1.5 (Dead Code) | ~5 | 0 | 4 | Low-Medium |
| 2 (Text Input) | ~12 | 0 | 3 | Medium |
| 3 (Scorers) | ~12 | 0 | 2 | Low |
| 3.5 (Coverage) | ~11 | 0 | 3 | Medium |
| 4 (Reward) | ~14 | 1 | 3 | Medium-High |
| 5 (Backtracking) | ~10 | 0 | 2 | Medium |
| 6 (PathBuffer) | ~9 | 1 | 4 | High |
| 7 (Speed) | ~7 | 0 | 3 | Low-Medium |
| 8 (LLM MOP) | ~5 | 0 | 2 | Low |
| 9 (Integration) | ~23 | 0 | 1 | Medium |
| 10 (Validation) | 0 | 3 docker-compose + 1 script | 0 | Medium |
| **Total** | **~117 tests** | **2 new classes + 6 docker/script** | **~16 modified** | |

### 16.3 Pre-requisites

1. **gh18 must be implemented first** — the design explicitly depends on gh18's `VisualErrorDetector`, `force_fill_input`, and conditional screenshot
2. **Fix INV numbering** (Section 3.1) — must be done before implementation starts
3. **Investigate `record_transition()` bug** (Section 13.3) — should be done as part of Group 1.5

---

## 17. PRD Documentation Discrepancies

The LangGraph topology agent found 3 discrepancies between PRD FR21 and the actual implementation:

| # | PRD FR21 | Actual Code | Severity |
|---|----------|-------------|----------|
| 1 | Shows `learn →|continue| PARSE` (internal loop) | `learn → END` (unconditional); external while loop in `run()` | Documentation — PRD implies internal LangGraph loop |
| 2 | Does not show `"end"` edge from `decision_router` | `decision_router → END` exists at line 245 | Documentation — missing edge |
| 3 | Uses `execute_action` as node name | Code uses `execute` | Documentation — minor naming |

These are PRD documentation inaccuracies, not code bugs. They should be corrected in a future PRD update but do not affect gh26 implementation.

---

## 18. Summary of All Issues

### Critical (Must Fix Before Implementation)

| # | Issue | Location | Resolution |
|---|-------|----------|------------|
| C1 | INV-AGT-20 through INV-AGT-27 numbering collision with gh18 | Delta spec lines 46-60 | Renumber to INV-AGT-28 through INV-AGT-36; update all cross-references in tasks.md, design.md |

### Medium (Should Fix Before Implementation)

| # | Issue | Location | Resolution |
|---|-------|----------|------------|
| M1 | `DynamicStateGraph.record_transition()` possible latent bug (3rd arg passed as timestamp) | `rvagent_strategy.py:424` | Investigate before gh26 implementation; add investigation task to Group 1.5 |
| M2 | Main spec Purpose section (lines 115-129) needs weight updates when delta is synced | Main spec | Update during `/opsx:sync` |

### Low (Nice to Fix)

| # | Issue | Location | Resolution |
|---|-------|----------|------------|
| L1 | Design says `max_variations=5`; actual is 3 | `design.md:17` | Update to say `max_variations=3` |
| L2 | Data Flow shows `-15` as if current; actual is `-10` | `design.md:889` | Clarify this is the NEW default |
| L3 | Missing scenario for cumulative reward cap boundary | Delta spec N-Step Reward | Add scenario (covered by task 9.4 but not in spec) |
| L4 | Missing scenario for text input cycling after exhaustion | Delta spec Text Input Quality | Add scenario defining cycling behavior |
| L5 | Missing scenario for post-invalidation flow | Delta spec Path Buffer | Add scenario clarifying next-iteration behavior |
| L6 | `visited_states` removal has ~8 reference sites not enumerated | `design.md` D6 | Already covered by task 1.5.2's "~8 sites" note |
| L7 | `gradual_decay_min_visits` not configurable | Config design | Consider adding to gh9 calibration params |
| L8 | Strategy C cold start threshold not configurable | Config design | Consider adding to gh9 calibration params |

### Notes (Informational)

| # | Note |
|---|------|
| N1 | PRD FR21 has 3 documentation discrepancies with actual code (internal loop, missing "end" edge, node naming) |
| N2 | INV-AGT-19 fills a gap in the main spec (18 → 20). Using INV-AGT-28 for this item is safer |
| N3 | The design openly accepts several trade-offs (proxy MOP signal, single-action transitions, transition irreproducibility) with clear rationale |
| N4 | The experimental validation design is rigorous (paired Wilcoxon, Bonferroni correction, Docker architecture) |

---

*End of validation report.*
