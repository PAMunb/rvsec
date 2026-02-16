# Deep Analysis: rv-agent Action Selection Logic

**Date**: 2026-02-16 (cross-validated 2026-02-16)
**Author**: Claude Code analysis (requested by Pedro H. T. Costa)
**Scope**: Rigorous evaluation of rv-agent's exploration and action selection mechanisms, compared against APE and Fastbot source code, with assessment of whether calibration (gh9) alone can achieve competitive method/MOP coverage.
**Related changes**: gh18 (pre-condition), gh9 (downstream calibration)
**Cross-validation**: Independently reviewed by Gemini and Qwen (both approved). Adopted suggestions and identified gaps incorporated in Section 11.

---

## 1. Executive Summary

**Can calibration alone make rv-agent beat APE and Fastbot?**

**No.** After analyzing rv-agent's source code, APE's source (Java), Fastbot's source (C++), and the ICST paper results, calibration of the existing parameters (24 base + 2 from gh18 = 26) is necessary but **insufficient** to surpass APE and Fastbot in method coverage.

The core issues are **architectural**, not parametric:

1. **Passive backtracking** wastes 20-40% of the iteration budget by retrying already-tested actions instead of proactively navigating to unexplored states.
2. **Iteration speed gap**: rv-agent executes ~60-150 actions in 300s; APE executes ~300-600; Fastbot achieves similar throughput. This 2-10x disadvantage in actions-per-experiment means each rv-agent action must be proportionally more effective.
3. **No adaptive learning**: APE refines its UI model (under/over-abstraction detection); Fastbot uses SARSA RL with Q-values that converge over time. rv-agent's scoring is static throughout the experiment.

**However**, rv-agent has a **unique advantage** that neither APE nor Fastbot possesses: **MOP-aware action prioritization** using static analysis data (GATOR/REACH). This means rv-agent can potentially beat them on **MOP-specific coverage** (the metric that matters most for the thesis) if the architectural issues are addressed.

**Recommended path**: Fix the 3 high-impact architectural issues (proactive backtracking, speed optimization, MOP-directed navigation), THEN calibrate parameters. This gives the best chance of surpassing APE/Fastbot on MOP coverage within the thesis timeline.

### Execution Order

This refactoring fits into the broader development pipeline:

```
gh17 (DONE) → gh18 (error detection) → THIS REFACTORING → gh9 (calibration campaign)
```

- **gh18** (validation error detection) is a **pre-condition** — it will be implemented first. This refactoring assumes gh18's code already exists in the codebase (new `VisualErrorDetector` service, `force_fill_input` flag with spatial association in learn_node/algorithm_node/decision_node, conditional screenshot capture in parse_node).
- **gh9** (Docker-based calibration, ~312 hours) is **downstream** — the calibration campaign must happen AFTER this refactoring, because the refactoring changes the architecture, adds new parameters, and rebalances scorer weights. Calibrating first and then changing the architecture would invalidate all calibrated values.
- The gh9 infrastructure (scripts, tests, Tasks 1-12) is already complete and unaffected. Only `parameter_space.py` needs updating to include new parameters from this refactoring before the execution campaign starts (gh9 Tasks 13-27).

---

## 2. ICST Benchmark Data (Reference)

From the ICST paper (Tables I, II, III), at **300 seconds timeout**:

### Table: JCA Violations Detected (Table I)

| Tool | 60s | 120s | 180s | 300s | % Gain (60→300) |
|------|-----|------|------|------|-----------------|
| APE | 155 | 182 | 191 | **198** | 28.2 |
| Fastbot | 154 | 174 | 193 | **213** | 37.9 |
| Humanoid | 152 | 197 | 208 | **221** | 45.8 |
| Monkey | 138 | 157 | 152 | 166 | 20.5 |
| DroidBot BFS Greedy | 137 | 179 | 189 | **202** | 47.0 |

### Table: Method Coverage at 300s (Tables II and III)

| Tool | Overall Coverage (%) | MOP Coverage (%) |
|------|---------------------|------------------|
| **Humanoid** | **26.77** | **17.16** |
| **Fastbot** | **26.60** | **15.81** |
| **APE** | **25.27** | **14.56** |
| DroidBot BFS Greedy | 24.45 | 15.16 |
| QTesting | 22.36 | 13.42 |
| Monkey | 21.00 | 12.35 |

**Key ICST finding**: "each additional percentage point of coverage over API-relevant methods (MOP methods) increases the expected number of detected violations by roughly 0.7%". **MOP coverage is the critical metric.**

### Target for rv-agent

To claim the thesis contribution, rv-agent must achieve:
- MOP Coverage > 15.81% (beats Fastbot) — ideally > 17.16% (beats Humanoid)
- Overall Method Coverage > 25.27% (beats APE) — ideally > 26.60% (beats Fastbot)

---

## 3. rv-agent Action Selection Flow Trace

### 3.1 Core Flow (per iteration)

```
parse_node → decision_router_node → [algorithm_node | llm_path] → validation_node → execute_node → learn_node
```

In **pure_algorithm** mode (the most relevant for comparison with APE/Fastbot):

```
parse_node: UIAutomator dump → visitor pattern → ScreenDescription + hash
  ↓
decision_router_node: always routes to "algorithm"
  ↓
algorithm_node: calls strategy.select_next_action(hash, screen_desc)
  ↓
RVAgentStrategy.select_next_action():
  1. Plateau check (informational, never stops exploration)
  2. Get/create graph node for current state
  3. Re-enable actions with incomplete successors (SuccessorTracker)
  4. _get_untested_actions() → filter by package, exclude system actions
  5. IF untested actions exist:
     → _select_priority_action(untested) → ActionRanker scores with 8 scorers
     → Gumbel-max stochastic selection (30% probability)
  6. ELSE IF any filtered actions exist:
     → Try scroll (15% probability)
     → _select_least_executed_action() → sort by (exec_count ASC, -mop_priority DESC)
  7. ELSE: return BACK action
  8. Pre-mark action as executed
  9. Return ItemAction
  ↓
validation_node: coordinate validation, loop detection
  ↓
execute_node: execute on device, record UI coverage
  ↓
learn_node:
  - Update memories
  - [gh18] Detect validation errors → force_fill_input (suppresses stuck counter)
  - Level 1 stuck detection: screen hash unchanged for dynamic_threshold iterations → force_back
  - Level 2 stuck recovery: StuckRecovery.check() after max_blocks → Backtrack BFS or RESTART
  - Record BACK transitions for BFS navigation graph
```

**Note**: After gh18 implementation, `decision_node` also checks `force_fill_input` → routes to algorithm. And `algorithm_node` handles `force_fill_input` using **spatial association** — mapping each `ErrorIndicator` (with coordinates) to the nearest actionable screen item via overlap scoring + widget-type boosts (1.2x EditText, 1.1x Spinner), with sequential TEXT_CHANGE fallback. The priority chain in algorithm_node becomes: `force_restart_app` → `force_back_action` → `force_fill_input` (spatial association) → deadlock → `strategy.select_next_action()`.

### 3.2 Scorer System (8 Scorers)

Active scorers in `RVAgentStrategy.__init__` (rvagent_strategy.py:186-197):

| Scorer | Score | Role |
|--------|-------|------|
| MopScorer | +300 (DM), +150 (M) | Prioritize MOP-reaching actions |
| WtgScorer | +250 | Guide to unvisited screens |
| SaturationScorer | +80 × (1 - sat_rate) | Favor unsaturated states |
| ComponentPriorityScorer | +50 (buttons), +40 (toggles) | Widget type priority |
| StrengthScorer | +50 × success_rate | Historical effectiveness |
| FailedActionScorer | -9999 | Blacklist crash-causing actions |
| SystemElementFilter | -5000 | Filter system UI |
| VisitationPenaltyScorer | -10 × log(1+visits) | Penalize over-visited states |

**Note**: `GradualDecayScorer` and `ExecutionCountScorer` are defined in `scorers.py` but **not included** in the active ranker. These scorers are dead code in the current configuration.

### 3.3 Timing Analysis

Per-iteration cost estimate:
- UIAutomator dump + parsing: ~0.5-1.0s
- Strategy selection: <0.01s
- Action execution: ~0.3-0.5s
- Learn/memory update: ~0.1s
- **Total (pure_algorithm)**: ~1-2s per iteration → **~150-300 iterations in 300s**
- **Total (multimode, 70% LLM)**: ~5-7s average → **~43-60 iterations in 300s**

---

## 4. Comparison with APE

**Source analyzed**: `tmp_tools/ape/src/com/android/commands/monkey/ape/agent/SataAgent.java`

### 4.1 APE's 6-Tier Action Selection Hierarchy

APE's `selectNewActionNonnull()` (SataAgent.java:289-340) uses a **6-tier hierarchy**:

| Tier | Method | Purpose |
|------|--------|---------|
| 1 | `selectNewActionFromBuffer()` | Execute pre-planned path (from backtracking BFS) |
| 2 | `selectNewActionBackToActivity()` | Navigate back to specific under-explored activities |
| 3 | `selectNewActionEarlyStageForward()` | Greedy forward exploration to NEW states |
| 4 | `selectNewActionForTrivialActivity()` | Handle trivial/transition activities |
| 5 | `selectNewActionEarlyStageBackward()` | Greedy backward when forward exhausted |
| 6 | `selectNewActionEpsilonGreedyRandomly()` | Epsilon-greedy (ε from config) |

**rv-agent has only 2 tiers**: untested (scored) → continuous (least-executed). It lacks the nuanced navigation strategies of tiers 1-5.

### 4.2 APE's Proactive Backtracking

`checkBackTrack()` (SataAgent.java:235-278):

```java
// When state is SATURATED (all actions visited ≥ 2 times):
// 1. BFS from current state following BACK edges
// 2. Find nearest UNSATURATED ancestor
// 3. Compute PATH to that ancestor
// 4. Store path in BUFFER
// 5. Execute buffered actions sequentially
```

**Critical difference**: APE backtracks **immediately** when a state is saturated. rv-agent enters "continuous" mode (retrying least-executed actions) and only backtracks after **stuck detection fires** (8+ iterations on unchanged screen).

**Impact**: In a state with 10 actions, after testing all 10, APE immediately goes BACK. rv-agent retries the same 10 actions for ~8 iterations before stuck detection triggers BACK. That's **8 wasted iterations per saturated state**.

### 4.3 APE's Dynamic State Abstraction

APE implements **model refinement** (StatefulAgent.java:687-776):

- `checkUnderAbstractedState()`: Detects when different UI screens map to the same abstract state
- `checkAndRefineOverAbstractedState()`: Detects when similar screens are treated as different states
- Naming hierarchy adjusts dynamically during exploration

rv-agent uses **fixed structural hashing** (`DynamicStateGraph`). The hash function doesn't adapt. This means:
- Similar screens may get different hashes (over-precise → too many states)
- Truly different screens may get the same hash (under-precise → confusion)

### 4.4 APE's Priority System

APE assigns action priorities dynamically (StatefulAgent.java:1059-1115):
- **Unvisited**: +20 priority
- **Transition to unsaturated state**: +10
- **Same activity transition**: +10
- **Multiple nodes reached**: +priority per node

Then uses **epsilon-greedy**: with probability ε → random; else → greedy (least-visited).

rv-agent's scoring is more complex (8 scorers) but doesn't adapt based on exploration progress.

---

## 5. Comparison with Fastbot

**Source analyzed**: `tmp_tools/Fastbot_Android/native/agent/ModelReusableAgent.cpp`

### 5.1 Fastbot's 6-Stage Action Selection

`selectNewAction()` (ModelReusableAgent.cpp:248-285):

| Stage | Method | Purpose |
|-------|--------|---------|
| 1 | `selectUnperformedActionNotInReuseModel()` | NEW actions not in learned model (explore unknown) |
| 2 | `selectUnperformedActionInReuseModel()` | Unvisited actions with learned model guidance |
| 3 | `randomPickUnvisitedAction()` | Random unvisited fallback |
| 4 | `selectActionByQValue()` | Q-value greedy (exploit learned values) |
| 5 | `selectNewActionEpsilonGreedyRandomly()` | Epsilon-greedy (ε=0.05) |
| 6 | `handleNullAction()` | Null handling |

### 5.2 Fastbot's SARSA Reinforcement Learning

**Algorithm**: SARSA n-step (n=5)
- α (learning rate): 0.25, decreasing with total visits
- γ (discount): 0.8
- ε (exploration): 0.05

**Reward function** (ModelReusableAgent.cpp:66-96):
```
reward = P(visiting_new_activities | action) / √(visit_count + 1)
       + state_expectation / √(state_visit_count + 1)
```

This reward specifically incentivizes **reaching new Activities** — the key driver of method coverage. The Q-values converge over time so that actions leading to unexplored areas get higher scores.

**rv-agent has no learning mechanism.** The scorer weights are fixed from start to end. An action that fails to lead anywhere useful continues to get the same MOP/WTG/Component score.

### 5.3 Fastbot's Model Reuse

Fastbot persists learned models to `/sdcard/fastbot_<package>.fbm` using FlatBuffers:
- Maps action hashes → set of reachable activities
- Reused across multiple runs of the same app
- Gumbel noise added for stochastic selection within model-guided actions

rv-agent has no persistence between experiment runs.

### 5.4 Fastbot's Speed

Fastbot is implemented in **C++ (native)** with:
- FlatBuffers for fast model I/O
- Priority-weighted random selection (O(1) per action)
- Background async model saves
- Dynamic learning rate decay (α reduces at 20K, 50K, 100K, 250K visits)

This implies Fastbot processes **thousands of actions per minute**.

---

## 6. Identified Problems (Ranked by Impact)

### Problem 1: PASSIVE BACKTRACKING (Critical)

**Location**: `rvagent_strategy.py:312-352` (the untested/continuous/BACK flow)

**Issue**: When all untested actions in a state are exhausted, rv-agent enters "continuous" mode: it re-executes the least-tested action. It does NOT proactively navigate BACK to explore other states. The agent only goes BACK when:
- Stuck detection fires (learn_node, 8+ unchanged iterations)
- Level 2 StuckRecovery triggers (max_blocks iterations)
- All actions permanently failed

**Waste estimate**: For each saturated state with N actions, rv-agent wastes ~8 iterations before BACK. In a 300s experiment with ~50 states visited, this wastes ~400 iterations (more than the total budget in multimode).

**APE comparison**: APE backtracks **immediately** via `checkBackTrack()`. Zero wasted iterations.

**Note**: The `state_stack` (line 200) and `should_backtrack()` (line 447) are maintained but **never used for navigation decisions**. The DFS stack is effectively dead code.

### Problem 2: ITERATION SPEED GAP (Critical)

**Issue**: In multimode (default), rv-agent averages ~5-7s per iteration due to LLM calls (Qwen3-VL). Even in pure_algorithm, UIAutomator parsing adds ~1-2s per iteration.

| Tool | Est. actions in 300s | Speed factor |
|------|---------------------|--------------|
| Monkey | ~50,000 | 333x |
| APE | ~300-600 | 2-4x |
| Fastbot | ~300-600 | 2-4x |
| rv-agent (pure_algo) | ~150-300 | 1x |
| rv-agent (multimode) | ~43-60 | 0.3-0.4x |

For rv-agent's precision to compensate for speed, each action must be 2-4x more effective than APE's. This is a very high bar.

### Problem 3: WTG vs MOP SCORER IMBALANCE (High)

**Location**: `scorers.py`, `agent_config.py:229-248`

**Issue**: WTG score (+250) is almost as high as MOP-direct (+300) and higher than MOP-transitive (+150):

```
MOP-direct:     +300
WTG-guided:     +250  ← nearly equal to MOP-direct
MOP-transitive: +150  ← LOWER than WTG
```

This means a **non-MOP action to an unvisited screen** (250) outscores a **MOP-transitive action** (150). The agent prefers exploring new screens over following paths to MOP methods.

**For MOP coverage optimization**, the hierarchy should be:
```
MOP-direct:     +500  (highest priority — these directly call JCA API)
MOP-transitive: +300  (second — these eventually reach JCA API)
WTG-guided:     +150  (third — useful for screen coverage, not MOP)
```

### Problem 4: NO MULTI-STEP PLANNING (High)

**Issue**: rv-agent makes **one action at a time** with no planning horizon. To reach a MOP method, the agent may need to execute a sequence: Menu → Settings → Security → Configure Encryption. Each step is decided independently without awareness of the full path.

APE solves this with the **buffer system**: when backtracking to a specific state, it computes a full path and executes it step by step.

Fastbot solves this with **Q-value propagation**: SARSA n-step (n=5) propagates rewards 5 steps backward, so actions leading toward high-reward paths accumulate value.

rv-agent has neither mechanism. The MopScorer gives the same +150 to "Click Menu" and "Click Configure Encryption" if both transitively reach the MOP, but doesn't know that "Click Menu" is 3 steps away while "Click Configure Encryption" is 0 steps away.

### Problem 5: NO ADAPTIVE LEARNING (Medium)

**Issue**: rv-agent's scorer weights are **fixed** throughout the experiment. An action that gets +300 (MOP-direct) on iteration 1 still gets +300 on iteration 100, even if:
- The MOP method was already executed 50 times
- The action always leads to the same state (no new exploration)
- A different path was discovered to reach the same MOP

APE adapts through model refinement. Fastbot adapts through Q-value convergence. rv-agent doesn't adapt.

**Partial mitigation**: The `StrengthScorer` uses historical success rates, and `VisitationPenaltyScorer` penalizes over-visited states. But these are weak signals compared to full RL (Fastbot) or model refinement (APE).

### Problem 6: DEAD SCORERS (Low-Medium)

**Location**: `scorers.py` defines `GradualDecayScorer` and `ExecutionCountScorer`, but they are **not registered** in `RVAgentStrategy.__init__` (line 186-197).

- `GradualDecayScorer`: Exponential decay by visits (200 × 0.7^visits). Would provide smoother priority transitions than the binary untested/tested split.
- `ExecutionCountScorer`: Inverse proportion to execution count (10/(1+count)). Would differentiate within the "continuous" mode.

These scorers would add value if the architecture changes to include proactive backtracking (where all actions are scored together, not split into untested/tested tiers).

### Problem 7: CONTINUOUS MODE INEFFICIENCY (Low-Medium)

**Location**: `rvagent_strategy.py:323-348`

**Issue**: When all visible actions are tested, the strategy:
1. Tries scroll (15% probability) — can waste iterations on non-scrollable screens
2. Selects least-executed action — retries actions that already proven ineffective

The `StrengthScorer` and `VisitationPenaltyScorer` only run during `_select_priority_action` (for untested actions). The `_select_least_executed_action` method uses its own simple sort: (exec_count ASC, -mop_priority DESC). The 8-scorer system is **not used** for continuous mode selection.

---

## 7. Concrete Improvement Recommendations

### 7.1 PROACTIVE BACKTRACKING (Impact: Critical, Effort: Medium)

**Files to modify**: `rvagent_strategy.py`, `algorithm_node.py`
**gh18 interaction**: None — gh18 does not touch `rvagent_strategy.py`. Clean integration.
**New calibration parameters**: `backtrack_saturation_threshold` (float, 0.0-1.0, default 0.8) — when saturation rate exceeds this, trigger proactive BACK. Must be added to `parameter_space.py` MACRO_PARAMETERS before gh9 execution.

**Change**: When all untested actions in current state are exhausted, immediately return a BACK action instead of entering continuous mode. Use the existing `state_stack` for DFS navigation.

```python
# Current flow (rvagent_strategy.py:312-352):
if untested_actions:
    selected = _select_priority_action(untested)
elif all_filtered_actions:       # ← THIS is the problem
    scroll_or_least_executed()    # ← Wastes iterations
else:
    return BACK

# Proposed flow:
if untested_actions:
    selected = _select_priority_action(untested)
elif should_backtrack(current_hash):  # ← Use the existing method!
    return BACK                        # ← Proactive backtracking
elif all_filtered_actions:
    scroll_or_least_executed()         # ← Only as last resort
else:
    return BACK
```

**Pre-condition**: `should_backtrack()` (line 447) is currently dead code — never called in production. Before relying on it, write unit tests to verify it returns correct results for: saturated states, partially-explored states, states with incomplete successors, and single-node graphs. Fix any bugs found before integrating.

**Expected impact**: Recovers ~20-40% of wasted iterations. The existing `should_backtrack()` method (line 447) already implements the logic — it just needs to be tested and called.

### 7.2 SCORER REBALANCING (Impact: High, Effort: Low)

**Files to modify**: `agent_config.py` (default values only)
**gh18 interaction**: gh18 adds `error_detection_enabled` and `error_detection_confidence` to `agent_config.py`. Scorer weight changes are in different fields — no conflict.
**New calibration parameters**: None — only changes default values of existing parameters already in `parameter_space.py`.

Proposed weight changes (initial defaults — gh9 calibration will fine-tune):

| Scorer | Current | Proposed | Rationale |
|--------|---------|----------|-----------|
| MOP-direct | 300 | 500 | Increase gap over WTG |
| MOP-transitive | 150 | 300 | Should outweigh WTG |
| WTG | 250 | 150 | Support role, not primary |
| Saturation | 80 | 100 | Slightly increase exploration incentive |
| Component | 50/40 | 50/40 | Keep unchanged |
| Visitation penalty | -10 | -15 | Stronger repulsion from over-visited states |
| Stochastic prob | 0.3 | 0.15 | More deterministic MOP focus |

### 7.3 PURE_ALGORITHM SPEED OPTIMIZATION (Impact: High, Effort: Medium)

**Files to modify**: `rv_agent.py`, `agent/nodes/*.py`
**gh18 interaction**: gh18 adds error detection in `learn_node` (~5ms). This is cheap and must be preserved even in the fast path. The speed optimization targets screenshot capture and LLM nodes, not learn_node.
**New calibration parameters**: None.

In pure_algorithm mode:
- Skip `capture_screenshot_node` (the LLM screenshot node — unnecessary without LLM)
- **Preserve** gh18's conditional screenshot in `parse_node` (only fires on hash-repeat, ~50ms, needed for error detection). These are two different screenshot mechanisms: `capture_screenshot_node` is for LLM consumption, `parse_node`'s conditional capture is for `VisualErrorDetector`
- Skip LLM-related nodes
- Minimize UIAutomator dump frequency (cache screen_desc if hash unchanged)
- Preserve gh18's error detection in learn_node (cheap, valuable for MOP coverage via form filling)
- Target: <1s per iteration → ~300+ iterations in 300s

**Mode-awareness caveat**: These optimizations must be conditioned on the current execution mode at runtime, not compiled out globally. In multimode (70% LLM / 30% algorithm), algorithm iterations should still benefit from speed optimizations (skip screenshot when routing to algorithm), while LLM iterations need the full pipeline. The decision happens per-iteration in `decision_router_node`, not at startup.

### 7.4 MOP-DIRECTED NAVIGATION / PATH BUFFER (Impact: High, Effort: High)

**Files to modify**: `rvagent_strategy.py` (new `PathBuffer` class or separate file), `services/transition_manager.py`
**gh18 interaction**: None — gh18 does not touch `rvagent_strategy.py` or `transition_manager.py`. Clean integration. The path buffer integrates inside `select_next_action()`, which is called AFTER algorithm_node's force-flag checks (including gh18's `force_fill_input`).
**New calibration parameters**: `path_buffer_enabled` (bool, default True), `mop_nav_weight` (float, default 2.0 — weight of MOP density vs path length). Must be added to `parameter_space.py` MACRO_PARAMETERS before gh9 execution.

**Concept**: Use static analysis to build a **MOP Target Queue** — a priority-ordered list of Activities containing MOP-relevant code. Navigate toward these proactively using a buffered path.

Two planning strategies:

**A) Backtrack to unsaturated ancestor** (like APE's `checkBackTrack`):
- Uses existing `successor_tracker.find_nearest_unsaturated()` — already implemented
- Computes number of BACKs needed, buffers them
- Validates each step: if unexpected state → clear buffer

**B) Navigate toward MOP-rich Activity** (rv-agent's unique advantage):
- From static analysis: which Activities contain MOP methods
- From WTG: transitions between Activities
- BFS on WTG from current_activity to nearest MOP-rich unvisited Activity
- Buffer actions along the WTG path

**BFS edge weighting refinements** (from cross-validation review):
- **MOP density weighting**: Scale BFS edge priority by `mop_methods_in_target / total_methods_in_target`. Activities with higher MOP density are preferred targets. This merges WTG and MOP scoring at the navigation level, making the flat WTG score less critical.
- **Saturation-aware path preference**: When multiple BFS paths exist, prefer paths through less-saturated states. This combines directed navigation with opportunistic exploration of under-tested intermediate screens.

**Integration in `select_next_action()`**:
```
CURRENT: untested → continuous → BACK
PROPOSED: buffer → untested → plan_path → continuous → BACK
```

Strategy B is the **key differentiator** — APE has no MOP data, Fastbot has no WTG paths. Only rv-agent can combine path planning + MOP targeting.

### 7.5 N-STEP REWARD PROPAGATION (Impact: Medium, Effort: Medium)

**Files to modify**: `learn_node.py`, `domain/screen_node.py`, `strategies/rvagent_strategy/ranking/scorers.py` (StrengthScorer)
**gh18 interaction**: gh18 adds `_detect_validation_error()` to learn_node, which runs BEFORE stuck detection. Reward propagation goes AFTER `_record_action_success()` (line 123) — different insertion point, no conflict. The data flow becomes: error detection → stuck detection → action success recording → reward propagation. **Note**: `error_recovery` actions (SET_TEXT/CLICK with `decision_maker="error_recovery"`) should participate in reward propagation — if an error recovery SET_TEXT leads to a successful MOP trigger on the next iteration, that reward should propagate back through the error recovery action and the submit button that caused the validation error.
**New calibration parameters**: `reward_gamma` (float, 0.5-0.99, default 0.8), `reward_mop_weight` (float, 1.0-10.0, default 5.0), `reward_propagation_n` (int, 3-8, default 5). Must be added to `parameter_space.py` MICRO_PARAMETERS before gh9 execution.

**Concept**: Simplified version of Fastbot's SARSA n-step. Extend the existing `StrengthScorer` with backward reward propagation through action chains.

**MOP-aware rewards** (rv-agent's unique advantage over Fastbot):
```
REWARD_SAME_STATE  = -0.1   # Action didn't change state
REWARD_NEW_STATE   = 1.0    # Discovered new screen
REWARD_NEW_ACTIVITY = 2.0   # Discovered new Activity (like Fastbot)
REWARD_MOP_REACHED = 5.0    # Reached a MOP method ← UNIQUE to rv-agent
```

When a high reward occurs (e.g., MOP_REACHED = 5.0), propagate backward through the last N actions with discount factor γ=0.8:
```
Iteration 100: Action E → MOP reached! reward = 5.0
Iteration  99: Action D gets 5.0 × 0.8¹ = 4.0
Iteration  98: Action C gets 5.0 × 0.8² = 3.2
Iteration  97: Action B gets 5.0 × 0.8³ = 2.56
Iteration  96: Action A gets 5.0 × 0.8⁴ = 2.05
```

Over time, actions that START productive sequences accumulate higher reward, and the StrengthScorer naturally steers toward them.

**Simpler than SARSA** (P1 Simplicity):
- No Q-table: reuses existing ScreenNode dictionaries (new `action_cumulative_reward` dict)
- No learning rate schedule: fixed α=0.25
- No ε-greedy: keeps existing Gumbel-max
- ~80 lines of new code total

### 7.6 SATURATION-BASED BACKTRACKING THRESHOLD (Impact: Medium, Effort: Low)

**Files to modify**: `rvagent_strategy.py`
**gh18 interaction**: None.
**New calibration parameters**: Merged with 7.1's `backtrack_saturation_threshold`.

Instead of binary untested/tested, use a configurable saturation threshold:
- When saturation_rate > 0.8 (80% of actions tested) → backtrack
- This is a compromise between APE's aggressive backtracking and rv-agent's continuous exploration

### 7.7 LLM MOP GUIDANCE (Impact: Medium, Effort: Medium)

**Files to modify**: `prompts/v13.py`, `navigation_guidance.py`
**gh18 interaction**: None — gh18 does not touch prompts or navigation guidance.
**New calibration parameters**: None (prompt content, not a numeric parameter).

In multimode, enrich the LLM prompt with MOP-specific guidance:
```
"The following buttons lead to cryptographic API calls: [Button: Configure Encryption (directly calls Cipher.getInstance), Button: Security Settings (path to KeyGenerator)]"
```

This leverages the LLM's semantic understanding for directed MOP exploration — something APE and Fastbot cannot do.

### 7.8 ACTIVATE DEAD SCORERS (Impact: Low, Effort: Low)

**Files to modify**: `rvagent_strategy.py`
**gh18 interaction**: None.
**New calibration parameters**: None — `GradualDecayScorer` params already exist in `agent_config.py`.

Add `GradualDecayScorer` to the active scorer list. This provides smoother action priority transitions instead of the binary untested/tested split. Most useful if proactive backtracking is also implemented (since the continuous mode would still benefit from gradual decay).

### 7.9 TEXT INPUT QUALITY (Impact: Medium-High, Effort: Medium)

**Files to modify**: `strategies/rvagent_strategy/input_value_generator.py`, `strategies/rvagent_strategy/rvagent_strategy.py`, `execution/tool_executor.py`
**gh18 interaction**: Strong synergy — gh18's `_find_associated_input_action()` spatial association calls `agent.strategy._prepare_input_action()` which uses `InputValueGenerator` directly. Bug 2 (wrong defaults) means error recovery fills EditText with "1234" (a PIN) instead of context-appropriate Faker text, wasting recovery iterations. Bug 6 (no clear before type) is **critical** for gh18: the exact scenario gh18 handles (validation error → fill input) often involves fields with placeholder text or previous input — without clearing, text appends ("Enter password" + "1234" → "Enter password1234"). Fixing the generator means fewer validation errors to detect, and gh18's error recovery becomes reliable instead of a source of further errors.
**New calibration parameters**: `mop_max_input_variations` (int, 5-15, default 11) — separate limit for MOP fields to ensure all edge-case payloads are tested. Must be added to `parameter_space.py` MICRO_PARAMETERS before gh9 execution.

**Analysis**: The text generation system has 6 bugs that collectively waste 20-40% of text input iterations and prevent MOP-relevant edge case testing.

**Bug 1: Duplicate & inconsistent input type inference**

Two implementations exist:
- `enhanced_visitor.py:_analyze_input_type()` (line 1235): Rich — checks `resource_id`, `hint`, `content_description`, `view_text`. Detects 15+ types (email, phone, search, URL, date, time, ZIP, verification code, first/last name, numeric, multi-line text).
- `rvagent_strategy.py:_infer_input_type()` (line 738): Shallow — only checks `resource_id` + `password` flag. Detects 6 types (password, email, phone, username, name, address).

The strategy already receives the full `node.data` in `target_view` (which contains `hint`, `content_description`, `text`, `class`) but `_infer_input_type()` ignores them. ~80% of fields fall through to "text" default.

**Fix**: Delete `_infer_input_type()` from strategy. Reuse `enhanced_visitor._analyze_input_type()` or extract the input type from the action's `text` field which already contains it (e.g., `"SET_TEXT (5) [email address]"`).

**Bug 2: Wrong default value ordering**

For `input_type == "text"` (the default for most fields), `_get_regular_values()` returns:
```python
common_pins[:3] + unique_list  # → ["1234", "0000", "123456", faker.text(), ...]
```
A search field gets "1234" as its first value. A message field gets "0000". Only the 4th+ value is actual Faker text. With `max_variations=5`, 60% of iterations are PINs in non-PIN fields.

For recognized types (email, name, etc.):
```python
["", "test"] + unique_list  # → ["", "test", faker_email_1, faker_email_2, ...]
```
First value is empty string — typing nothing into an email field wastes an iteration.

**Fix**: Remove PINs from the general text path (only use for `password`/`pin` type). Remove empty string as first value. Start with Faker values directly.

**Bug 3: LLM path bypasses InputValueGenerator entirely**

When the LLM (multimode/llm_only) decides to type text via `android_type_text(x, y, text="...")`, it invents its own text. Qwen3-VL-4B doesn't know about MOP edge cases, proper test data formats, or what was already tested. The `InputValueGenerator` is ONLY used in the algorithm path.

**Fix**: In `validation_node`, when LLM produces a SET_TEXT action, enrich the text through `InputValueGenerator` if the LLM's text is generic (e.g., "test", "hello", single character). Or: track LLM-generated text in the same `tested_values` dict to avoid repetition.

**Bug 4: max_variations=5 blocks MOP edge cases**

MOP fields get 11 edge-case payloads, but `max_variations=5` means only the first 5 are tested:
```
["", "0", "-1", "2147483647", "../../../etc/passwd"]  ← tested
["' OR '1'='1", "<script>...", "%s%n%x%t"*5, "A"*100, "${jndi:...}", "() { :; }; ..."]  ← NEVER reached
```
SQL injection, XSS, format string, buffer overflow, JNDI, and Shellshock payloads are never tested.

**Fix**: Use separate `mop_max_input_variations` (default 11) for MOP fields. Regular fields keep `max_variations=5`.

**Bug 5: Missing input types in generator**

`_get_regular_values()` doesn't handle: search, url, date, time, number, zip, verification_code. All fall through to "text" → get PINs first (Bug 2).

**Fix**: Add Faker generators:
```python
"search": faker.sentence(nb_words=3)
"url": faker.url()
"date": faker.date()
"time": faker.time()
"number": str(faker.random_int(min=1, max=9999))
"zip": faker.zipcode()
"verification_code": str(faker.random_int(min=1000, max=9999))
```

**Bug 6: No clear before typing**

`_execute_type_text()` does `click(x,y)` then `input_text(text)` but doesn't clear existing content. If a field has a default value or previous input, text is appended: "Enter password" + "1234" → "Enter password1234".

**Fix**: Add `device.clear_text()` or select-all + delete before `input_text()`.

**Expected impact**: Recovers 20-40% of text input iterations from waste (PINs in non-PIN fields, empty strings), enables all 11 MOP edge cases to be tested, and reduces validation error loops (synergy with gh18).

---

## 8. Strategic Assessment for the Thesis

### 8.1 What the ICST Paper Established

The paper proved that:
1. Automated test generation + RV effectively detects JCA API misuses
2. Code coverage correlates with violation detection
3. MOP-specific coverage is the key driver (0.7% more violations per 1% MOP coverage)
4. Best tools achieve ~17% MOP coverage and ~27% method coverage at 300s

### 8.2 What rv-agent Must Prove

The thesis (Cycle 4 — LLM-guided exploration) must demonstrate:
1. **LLM + MOP awareness** achieves higher MOP coverage than blind exploration
2. rv-agent surpasses at least APE and Fastbot on MOP coverage
3. The approach is **novel** (no existing tool combines LLM + MOP + WTG)

### 8.3 Risk Assessment

| Scenario | Probability | Outcome |
|----------|-------------|---------|
| Calibration alone | 20% | Might match APE but unlikely to beat Fastbot/Humanoid |
| Calibration + proactive backtracking | 50% | Competitive with APE, possibly beats Fastbot on MOP |
| Calibration + backtracking + MOP navigation | 75% | Beats APE and Fastbot on MOP coverage |
| Full improvements (all 7) | 85% | Beats all tools on MOP, competitive on overall coverage |

### 8.4 Recommended Implementation Order

| Priority | Improvement | Effort | Expected MOP Gain (isolated) | New Calibration Params |
|----------|-------------|--------|------------------------------|----------------------|
| 1 | Proactive backtracking (7.1) | 2 days | +3-5% MOP coverage | 1 (backtrack threshold) |
| 2 | Scorer rebalancing (7.2) | 0.5 days | +1-2% MOP coverage | 0 (existing params) |
| 3 | Text input quality (7.9) | 1.5 days | +1-3% MOP coverage | 1 (mop_max_input_variations) |
| 4 | pure_algorithm speed (7.3) | 2 days | +2-4% MOP coverage | 0 |
| 5 | MOP-directed navigation (7.4) | 3-5 days | +3-5% MOP coverage | 2 (buffer, nav weight) |
| 6 | N-step reward propagation (7.5) | 2 days | +1-2% MOP coverage | 3 (gamma, mop_weight, n) |
| 7 | Saturation threshold (7.6) | 0.5 days | +1% MOP coverage | 0 (merged with 7.1) |
| 8 | LLM MOP guidance (7.7) | 1 day | +1-2% MOP coverage | 0 |
| 9 | Dead scorers (7.8) | 0.5 days | +0.5% MOP coverage | 0 |

**Non-independence caveat**: The "isolated" gains above are NOT additive. Improvements interact non-linearly: faster iterations (7.3) amplify better decisions (7.1, 7.4); scorer rebalancing (7.2) only matters WITH proactive backtracking (7.1) since continuous mode bypasses scorers. The realistic combined gain is **~60-70% of the naive sum**: ~+7-15% MOP coverage (full set) or ~+4-8% (MVP set). Starting from an estimated ~12-15% baseline, this still targets 19-30% — enough to beat APE (14.56%) and Fastbot (15.81%), and competitive with Humanoid (17.16%). The ablation study (Section 11.2) will quantify actual per-improvement contribution.

**Minimum viable improvement set**: Items 1 + 2 + 3 + 4 (6 days) for a realistic shot at beating APE/Fastbot on MOP coverage. Text input quality (7.9) is included in MVP because it's low-effort (1.5 days) and synergizes directly with gh18's error detection.

**Full set**: Items 1-6 (~11.5 days) for maximum advantage. Items 7-9 are low-effort polish.

**New calibration parameters total**: 7 params added to `parameter_space.py` by this refactoring. With gh18's 2 params (`error_detection_enabled`, `error_detection_confidence`), the total is 24 existing + 2 gh18 + 7 refactoring = **33 total**. This moderately increases the search space for gh9's Optuna TPE sampler but remains tractable.

### 8.5 Full Execution Timeline

```
           CURRENT STATE               IMPLEMENTATION              CALIBRATION
           ────────────                ──────────────              ───────────
gh17 ✓     gh18 artifacts ✓       gh18 implement (3-5d)
                                        │
                                  BASELINE MEASUREMENT (0.5d)
                                  └── 5 apps × 1 rep × 300s (~25 min)
                                        │
                                  THIS REFACTORING (Full SDD)
                                  ├── Explore + Propose (1d)
                                  ├── Design + Tasks (1d)
                                  ├── Implement (11.5d)
                                  │   ├── 7.1 Proactive backtrack (2d)
                                  │   ├── 7.2 Scorer rebalance (0.5d)
                                  │   ├── 7.9 Text input quality (1.5d)
                                  │   ├── 7.3 Speed optimization (2d)
                                  │   ├── 7.4 Path buffer (3-5d)
                                  │   ├── 7.5 Reward propagation (2d)
                                  │   ├── 7.6 Saturation threshold (0.5d)
                                  │   ├── 7.7 LLM MOP guidance (1d)
                                  │   └── 7.8 Dead scorers (0.5d)
                                  ├── Verify + Archive (1d)
                                  │
                                  ABLATION STUDY (~3h execution)
                                  └── 5 apps × 8 configs × 300s
                                        │
                                  Update parameter_space.py (+9 params: 2 gh18 + 7 refactoring)
                                        │
                                  gh9 Tasks 13-14: commit + desktop transfer
                                  gh9 Tasks 15-16: Phase A preprocessing (~2h)
                                  gh9 Tasks 17-18: Phase B baseline (~18h)
                                  gh9 Tasks 19-20: Phase C macro cal (~122h)
                                  gh9 Tasks 21-22: Phase D micro cal (~160h)
                                  gh9 Tasks 23-24: Phase E validation (~6h)
                                  gh9 Tasks 25-27: apply params + archive
```

### 8.6 SDD Workflow for This Refactoring

**Track**: Full SDD (`rv-sdd` schema)

**Justification**: This change requires design decisions (path buffer architecture, reward propagation model, scorer weight strategy), touches multiple subsystems within rv-agent (strategy, nodes, scorers, config, graph), and impacts the downstream calibration campaign (gh9).

**Recommended approach**:
1. Create a new GitHub Issue for this refactoring
2. Follow Full SDD: Explore → Propose → Design → Tasks → Implement → Verify → Archive
3. Implementation uses subagent orchestration (Section 5 of WORKFLOW.md) — the 9 improvements can be grouped into 3-4 independent task groups
4. Implementation tasks.md uses component skills (not orchestrators) per WORKFLOW Section 9. See gh18 tasks.md as reference pattern
5. After all implementation groups, invoke `rv-code-reviewer` via Task tool for code review
6. Follow closing protocol: final commit with `closes #N`, move Kanban card to Done
7. After archiving, update `parameter_space.py` with new params before starting gh9's execution campaign

### 8.7 Thesis Narrative Opportunity

Even if rv-agent doesn't beat Humanoid on overall coverage, it can claim novelty through:
1. **First LLM-guided tool with MOP awareness** — no other tool combines these
2. **Specification-driven exploration** — the thesis contribution is the APPROACH, not just the numbers
3. **Complementarity**: rv-agent may find different violations than APE/Fastbot (testing different paths via MOP guidance)
4. **The ICST paper already suggests this direction**: "We envision adapting Android test-generation tools so they can guide the exploration process toward API-relevant methods" (Section VI, page 8). rv-agent IS this vision realized.

---

## 9. Integration with Active Changes

### 9.1 gh18 — Validation Error Detection (Pre-condition)

**Status**: All 4 SDD artifacts complete (proposal, delta specs, design, tasks). Implementation NOT started.
**Change dir**: `openspec/changes/gh18-error-detection/`
**Track**: FF SDD (rv-sdd schema)

**What gh18 adds to the codebase** (assumed complete when this refactoring starts):

| File | Changes |
|------|---------|
| `services/error_detection.py` | NEW — `VisualErrorDetector` (wraps rv-screen-parser's `ErrorDetector` for color-based detection), `ValidationErrorResult` dataclass |
| `agent/nodes/parse_node.py` | Conditional screenshot capture when `screen_hash == previous_screen_hash` (for error detection) |
| `agent/nodes/learn_node.py` | `_detect_validation_error()` before stuck detection, `error_recovery_count` tracking, stuck counter suppression |
| `agent/nodes/algorithm_node.py` | `force_fill_input` handling with spatial association: 5 constants (`SPATIAL_EDITTEXT_BOOST`, etc.), `_find_associated_input_action()` (overlap scoring + widget boosts), `_calculate_association_score()`, `_find_next_input_action()` (sequential fallback). ~100+ lines of new code |
| `agent/nodes/decision_node.py` | `force_fill_input` routing to algorithm |
| `domain/state.py` | `force_fill_input: bool`, `error_detection_screenshot: Optional[str]`, `error_indicators: Optional[List]` in AgentState |
| `config/agent_config.py` | `error_detection_enabled: bool = True`, `error_detection_confidence: float = 0.7` |
| `agent/rv_agent.py` | Wire config, init state fields, store `error_recovery_count` |
| `tracking.py` | `track.error()`, updated `track.learn(error_detected=...)` |
| `rv-screen-parser/pyproject.toml` | `opencv-python` → `opencv-python-headless` (same API, no libGL requirement) |

**File conflict analysis for this refactoring**:

| File | gh18 changes | Refactoring changes | Conflict? |
|------|-------------|---------------------|-----------|
| `rvagent_strategy.py` | Not touched | Heavy (7.1, 7.4, 7.6, 7.8) | **None** |
| `parse_node.py` | Conditional screenshot capture (hash-repeat) | 7.3 may cache screen_desc on hash unchanged | **Low** — 7.3 must preserve gh18's screenshot logic; both check hash-repeat but for different purposes |
| `learn_node.py` | Before stuck detection | After _record_action_success (7.5) | **None** — different insertion points |
| `algorithm_node.py` | Spatial association (~100+ lines: constants, 3 helper functions, handling block) | Not modified by refactoring (path buffer is in strategy) | **None** |
| `agent_config.py` | 2 new fields (`error_detection_enabled`, `error_detection_confidence`) | Default value changes + new fields | **None** — different fields |
| `scorers.py` | Not touched | StrengthScorer modification (7.5) | **None** |
| `domain/screen_node.py` | Not touched | New `action_cumulative_reward` dict (7.5) | **None** |

**Conclusion**: gh18 and this refactoring are architecturally compatible. All shared files have non-overlapping insertion points.

### 9.2 gh9 — Docker-Based Calibration (Downstream)

**Status**: Infrastructure COMPLETE (Tasks 1-12, 84 tests). Execution campaign PENDING (Tasks 13-27).
**Change dir**: `openspec/changes/gh9-docker-calibration/`
**Track**: Full SDD (rv-sdd schema)
**GitHub Issue**: [#9](https://github.com/PAMunb/rvsec/issues/9)

**What gh9 needs from this refactoring**:

1. **`parameter_space.py` update** — Add 9 new calibration parameters (2 from gh18 + 7 from this refactoring) before starting the execution campaign:

   | Parameter | Source | Section | Type | Range | Default |
   |-----------|--------|---------|------|-------|---------|
   | `error_detection_enabled` | gh18 | MACRO | bool | — | True |
   | `error_detection_confidence` | gh18 | MICRO | float | 0.5-0.95 | 0.7 |
   | `backtrack_saturation_threshold` | refactoring | MACRO | float | 0.5-1.0 | 0.8 |
   | `path_buffer_enabled` | refactoring | MACRO | bool | — | True |
   | `mop_nav_weight` | refactoring | MACRO | float | 0.5-5.0 | 2.0 |
   | `mop_max_input_variations` | refactoring | MICRO | int | 5-15 | 11 |
   | `reward_gamma` | refactoring | MICRO | float | 0.5-0.99 | 0.8 |
   | `reward_mop_weight` | refactoring | MICRO | float | 1.0-10.0 | 5.0 |
   | `reward_propagation_n` | refactoring | MICRO | int | 3-8 | 5 |

2. **Updated scorer defaults** — The new default values (MOP-direct=500, WTG=150, etc.) change the baseline for calibration. Optuna will fine-tune around these new defaults.

3. **Timing**: The `parameter_space.py` update must happen AFTER this refactoring is merged and BEFORE gh9 Task 13 (commit + desktop transfer). This is a simple code change — add 9 `ParameterDef` entries to the existing MACRO_PARAMETERS and MICRO_PARAMETERS lists.

**What does NOT change in gh9**:
- Scripts (`calibration_orchestrator.py`, `baseline_docker.py`) — param-agnostic
- `ObjectiveFunction` scoring — coverage metrics, not parameter-dependent
- Docker infrastructure — unchanged
- Phases B-E methodology — unchanged
- Test infrastructure (84 tests) — unchanged

### 9.3 Synergy: gh18 + Refactoring + gh9

The three changes create a compounding improvement cycle:

```
gh18 (error detection)
  ├── Agent fills form inputs instead of getting stuck
  ├── Reaches MOP behind submit buttons (direct coverage gain)
  ├── Reduces wasted iterations on validation error loops
  └── Depends on InputValueGenerator quality (→ 7.9 fixes make error recovery reliable)
         │
THIS REFACTORING (architectural fixes)
  ├── Proactive backtracking → less wasted time
  ├── Path buffer → multi-step MOP navigation
  ├── Reward propagation → learns productive sequences
  ├── Scorer rebalancing → MOP-first prioritization
  └── Speed optimization → 2x more iterations per experiment
         │
gh9 CALIBRATION (parameter tuning)
  ├── Optuna fine-tunes ALL 33 parameters together
  ├── Finds optimal balance between exploration and MOP focus
  └── Validated against APE/Fastbot on holdout set
```

Each layer amplifies the previous: gh18 prevents a class of failures, the refactoring makes each iteration count, and calibration optimizes the whole system.

---

## 10. Behavior Without Static Analysis

Static analysis (GATOR/REACH via `RVSEC_HOME`) is **optional** in rv-agent. When `static_data=None`, the system degrades gracefully — no crashes, no exceptions. All components check for None and return neutral values (0.0 scores, empty lists, disabled guidance). This is by design, not accident: `MopScorer` returns 0.0, `WtgScorer` returns 0.0, `TransitionManager` returns empty navigation lists, `NavigationGuidance` disables itself, and `RVAgentVisitor` skips MOP enrichment on actions.

### 10.1 Impact on Recommendations

| Recommendation | With static analysis | Without static analysis |
|---|---|---|
| **7.1** Proactive backtracking | Full | **Full** — uses SuccessorTracker (runtime-only) |
| **7.2** Scorer rebalancing | MOP=500, WTG=150 effective | **Inert** — both return 0.0; effective max score drops from ~730 to ~180 |
| **7.3** Speed optimization | Full | **Full** — targets UIAutomator/LLM overhead, not static data |
| **7.4** Path buffer | Strategy A (backtrack unsaturated) + Strategy B (MOP-directed via WTG) | **Strategy A only** — Strategy B requires WTG for BFS to MOP-rich Activities |
| **7.5** N-step rewards | `REWARD_MOP_REACHED=5.0` fires when `callback_signature` present | **Partial** — MOP reward never fires (no `callback_signature`); `REWARD_NEW_STATE=1.0` and `REWARD_NEW_ACTIVITY=2.0` still work |
| **7.6** Saturation threshold | Full | **Full** — uses local node saturation rate |
| **7.7** LLM MOP guidance | Enriched prompts with MOP context | **No effect** — NavigationGuidance returns empty string |
| **7.8** Dead scorers | Full | **Full** — GradualDecayScorer uses local visit counts |
| **7.9** Text input quality | MOP edge cases use `mop_max_input_variations=11` | **Partial** — Faker values and clear-before-type work fully; MOP payloads less meaningful without MOP tracking, but still useful for general robustness testing |

**Summary**: 5 recommendations work fully (7.1, 7.3, 7.6, 7.8, 7.9 core fixes), 1 partially (7.5 — learns paths to new screens but not to MOP), 1 is half-disabled (7.4 — only Strategy A), and 2 are effectively inert (7.2 MOP/WTG weights, 7.7). 7.9's MOP edge cases are less meaningful without static data but the core fixes (value ordering, type inference, clear-before-type) benefit all modes.

### 10.2 Effective Scoring Without Static Data

With static analysis, the scoring range for an untested action is:

```
MopScorer:              0 to +500  (direct MOP)
WtgScorer:              0 to +250  (WTG guidance)
SaturationScorer:       0 to +100
ComponentPriorityScorer: 0 to +50
StrengthScorer:         0 to +50
                        ─────────
Max positive:           ~950
```

Without static analysis, MopScorer and WtgScorer always contribute 0:

```
SaturationScorer:       0 to +100
ComponentPriorityScorer: 0 to +50
StrengthScorer:         0 to +50
                        ─────────
Max positive:           ~200
```

The scoring dynamic collapses: action selection depends only on **saturation rate**, **widget type** (buttons > toggles > text fields), and **historical success rate**. There is no guidance toward monitored operations or unvisited screens. The agent behaves as a **generic UI structure explorer**.

### 10.3 Competitive Position Without Static Data

Without static analysis, rv-agent loses its unique differentiator (MOP awareness). It competes on the same terms as APE and Fastbot — general screen exploration efficiency — but with a **2-4x speed disadvantage** (Section 6, Problem 2).

In this scenario:
- **7.1 + 7.3 + 7.6** close the efficiency gap (proactive backtracking recovers wasted iterations, speed optimization doubles throughput, saturation threshold triggers earlier backtracking)
- **7.5** learns paths to new screens/Activities (like Fastbot's SARSA) but without the MOP reward signal, it has no advantage over Fastbot's approach
- The agent is competitive but has **no reason to outperform** APE or Fastbot on MOP coverage

**Conclusion**: Static analysis is the **force multiplier** that transforms generic exploration improvements into MOP-directed exploration. Without it, the refactoring makes rv-agent a better generic explorer. With it, the refactoring makes rv-agent a uniquely MOP-focused explorer that neither APE nor Fastbot can match. For the thesis contribution, static analysis is effectively **required** — the refactoring's value is maximized when combined with GATOR/REACH data.

---

## 11. Cross-Validation Review (Gemini + Qwen)

**Date**: 2026-02-16
**Reviewers**: Gemini (Google), Qwen Code (Alibaba) — independent reviews
**Input**: This document + PRD + ICST paper + rv-agent source code
**Full reviews**: `docs/analise_gemini.md`, `docs/analise_qwen.md`

### 11.1 Consensus

Both reviewers independently **approved the plan for implementation**. Points of agreement:

- Diagnosis is correct — passive backtracking, scorer imbalance, dead code, no learning
- Integration with gh18/gh9 is clean (no merge conflicts)
- MOP awareness is the unique differentiator vs all competitors
- Calibration alone is insufficient — architectural fixes come first
- Implementation order (7.1→7.8) is logical and well-prioritized
- 75-85% probability of success with all 8 improvements

### 11.2 Adopted Suggestions

**Ablation Study** (Qwen): After implementation, run an incremental measurement to quantify each improvement's individual contribution. Methodology: 5 representative apps, 1 repetition, 300s timeout, 8 configurations (baseline → +7.1 → +7.2 → +7.3 → +7.4 → +7.5 → +7.6+7.7+7.8 → all). Total execution: ~3 hours. This answers the thesis reviewer question "which improvement helped the most?" and validates that the gain estimates are realistic. Added to timeline in Section 8.5.

**Baseline Measurement** (identified as gap): Before implementation, measure rv-agent's current MOP coverage on the same 5 apps used for the ablation study. The plan estimates "~12-15%" but this is unverified. A concrete baseline anchors all gain claims. Added to timeline in Section 8.5.

**New Tracking Metrics** (Qwen): Add to `tracking.py` during implementation:
- `backtrack_count`: Number of proactive BACK actions triggered by `should_backtrack()` (validates 7.1)
- `path_buffer_hit_rate`: Percentage of buffered paths that successfully reach their target Activity (validates 7.4)
- `reward_propagation_events`: Number of N-step reward propagations per experiment (validates 7.5)

**BFS Refinements for 7.4** (Gemini + Qwen): Folded into Section 7.4 — MOP density weighting of BFS edges and saturation-aware path preference. These make the PathBuffer smarter without adding a separate improvement item.

### 11.3 Evaluated and Skipped

| Suggestion | Source | Why Skipped |
|-----------|--------|-------------|
| Curiosity bonus in reward function | Gemini | Violates P1 (Simplicity). VisitationPenaltyScorer already discourages repetition. Adding intrinsic motivation on top of N-step rewards creates unnecessary complexity. |
| Early stopping / Optuna pruning | Qwen | gh9 scope (calibration infrastructure), not this refactoring. Noted for gh9 implementation. |
| Multi-app calibration diversity | Qwen | gh9 scope (app selection for calibration). Valid concern — noted for gh9 Tasks 13-14. |
| Graph embeddings / Hierarchical RL | Gemini | Post-thesis scope. Valuable for "Future Work" section of the thesis, not actionable now. |

### 11.4 Identified Gaps (Not Flagged by Either Reviewer)

1. **`should_backtrack()` is untested dead code**: The method exists (line 447) but was never called in production. It may have bugs. Added as a pre-condition to Section 7.1 — unit tests must pass before integration.

2. **MOP gain estimates are non-independent**: Improvements interact non-linearly. The naive sum of +12-21% overestimates. Realistic combined gain is ~60-70% of sum → +7-15%. Updated in Section 8.4 with a caveat and adjusted expectations.

3. **WTG score reduction risk**: Reducing WTG from 250→150 (Section 7.2) could hurt navigation through non-MOP intermediate screens that are necessary to reach MOP screens. The ablation study will catch this — if the +7.2 step shows a regression, the WTG default should stay at 200-250 and let gh9 calibration find the optimal value.

4. **Speed optimization must be mode-aware**: The pure_algorithm optimizations (skip screenshots, skip LLM nodes) must be per-iteration decisions conditioned on the current routing mode, not global flags. In multimode, algorithm iterations should be fast while LLM iterations use the full pipeline. Added as a caveat to Section 7.3.

### 11.5 Thesis Narrative Additions (from Gemini)

Gemini highlighted two post-thesis directions valuable for the "Future Work" section:
- **Semantic state representation** via graph embeddings (instead of structural hashing) — addresses over/under-abstraction without APE's CEGAR complexity
- **Hierarchical RL** — a meta-agent defines strategic goals ("navigate to Security Settings"), a low-level agent learns action sequences to achieve them. Natural evolution of the PathBuffer concept.

---

## Appendix A: Key Source Files Reference

| Component | File | Key Methods |
|-----------|------|-------------|
| Strategy | `strategies/rvagent_strategy/rvagent_strategy.py` | `select_next_action()`, `_select_priority_action()` |
| Scorers | `strategies/rvagent_strategy/ranking/scorers.py` | 8 scorer classes |
| Ranker | `strategies/rvagent_strategy/ranking/action_ranker.py` | `rank()`, `select_best()`, `select_stochastic()` |
| Successor | `strategies/rvagent_strategy/successor_tracker.py` | `update_action_availability()`, `find_nearest_unsaturated()` |
| Algorithm | `agent/nodes/algorithm_node.py` | `algorithm_node()` |
| Stuck detect | `agent/nodes/learn_node.py` | `learn_node()`, `_get_dynamic_stuck_threshold()` |
| Recovery | `routing/stuck_recovery.py` | `StuckRecovery.check()` |
| Router | `routing/routing_manager.py` | `route_decision()` |
| Input gen | `strategies/rvagent_strategy/input_value_generator.py` | `get_next_value()`, `_get_regular_values()`, `_get_mop_values()` |
| Config | `config/agent_config.py` | 24 existing + 2 gh18 + 7 refactoring = 33 calibration parameters |

## Appendix B: APE Key Source Files

| Component | File |
|-----------|------|
| Action selection | `ape/agent/SataAgent.java` — `selectNewActionNonnull()` (line 289) |
| Backtracking | `ape/agent/SataAgent.java` — `checkBackTrack()` (line 235) |
| State abstraction | `ape/agent/StatefulAgent.java` — `checkAndRefineOverAbstractedState()` (line 737) |
| Epsilon-greedy | `ape/agent/SataAgent.java` — `egreedy()` (line 624) |
| Saturation | `ape/model/ModelAction.java` — `isSaturated()` (line 91) |
| Path planning | `ape/model/Graph.java` — `moveToState()` (line 900) |

## Appendix C: Fastbot Key Source Files

| Component | File |
|-----------|------|
| Action selection | `native/agent/ModelReusableAgent.cpp` — `selectNewAction()` (line 248) |
| SARSA RL | `native/agent/ModelReusableAgent.cpp` — `updateStrategy()` (line 169) |
| Reward | `native/agent/ModelReusableAgent.cpp` — `computeRewardOfLatestAction()` (line 66) |
| Q-value select | `native/agent/ModelReusableAgent.cpp` — `selectActionByQValue()` (line 331) |
| Model reuse | `native/agent/ModelReusableAgent.cpp` — FlatBuffers persistence (line 443) |
| Priority adjust | `native/agent/AbstractAgent.cpp` — `adjustActions()` (line 69) |
