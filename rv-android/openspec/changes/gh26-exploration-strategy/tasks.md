<!-- Subagent dispatch hints:
     - Group 0 (Baseline Experiment) must run BEFORE any code changes.
     - Group 1 (Config & Models) must complete first — all other groups depend on it.
     - Groups 2, 3, 4 are independent and can run in parallel after Group 1.
     - Group 5 depends on Group 1 only. Group 6 depends on Group 1 AND Group 5
       (task 5.5 changes find_nearest_unsaturated() return type needed by PathBuffer).
       Run Group 5 first, then Group 6, or split task 6.7 wiring to run after both.
     - Groups 7, 8 are independent — can run in parallel with 2/3/4/5.
     - Group 9 integrates everything — must run after all other groups are done.
     - Group 10 (Validation Experiment) must run AFTER Group 9 and rv-verify pass.
     Pre-condition: gh18 must be implemented before starting Group 5+.
     This change touches 14+ files — use subagent orchestration (3-4 parallel dispatches). -->

## 0. Baseline Experiment (BEFORE implementation)

Run a controlled experiment to establish baseline metrics before any gh26 code changes. Uses the 10 APKs from experiment 02 (exp02 dataset), 3 testing tools, 5-minute timeout, and 3 repetitions. Results serve as the control group for post-implementation comparison.

**Experiment parameters:**
- APKs: 10 from exp02 (see task 0.1 for list)
- Tools: `ape`, `fastbot`, `rvagent:pure_algorithm`
- Spec set: `jca`
- Timeout: 300s (5 min)
- Repetitions: 3
- Total tasks: 10 × 3 × 3 = 90
- Parallelism: 2 Docker containers on laptop
- Original APKs: `/home/pedro/desenvolvimento/RV_ANDROID/apks`

- [ ] 0.1 Create experiment directory `docker/data/gh26_experiment/` with filter file `exp02_apks.txt` containing the 10 exp02 APK filenames (one per line): `com.blogspot.e_kanivets.moneytracker_38.apk`, `com.gianlu.dnshero_40.apk`, `com.github.axet.hourlyreminder_476.apk`, `com.pindroid_69.apk`, `com.rafapps.simplenotes_7.apk`, `com.thibaudperso.sonycamera_24.apk`, `li.klass.fhem_141.apk`, `org.pulpdust.lesserpad_42.apk`, `org.secuso.privacyfriendlydicer_8.apk`, `org.secuso.privacyfriendlyludo_5.apk`. Create two batch filter files: `batch_0.txt` (first 5 APKs) and `batch_1.txt` (last 5 APKs).
- [ ] 0.2 Create `docker/data/gh26_experiment/docker-compose.preprocess.yml`: single container using `phtcosta/rvandroid` image with `RV_SKIP_EXECUTION=true` to run instrumentation + static analysis only. Mount original APKs from `/home/pedro/desenvolvimento/RV_ANDROID/apks` (read-only), filter to 10 exp02 APKs. Output: instrumented APKs + `.gesda` + `.wtg` + `.reach` files in `docker/data/gh26_experiment/instrumented_apks/`. Verify all 10 APKs have complete SA files (reject if any `.reach` is missing). Follow gh9 preprocessing pattern from `docker/docker-compose.parallel.yml`.
- [ ] 0.3 Run preprocessing: `docker compose -f docker/data/gh26_experiment/docker-compose.preprocess.yml up`. Validate output: 10 instrumented APKs, 10 `.gesda`, 10 `.wtg`, 10 `.reach` files. Expected duration: ~20-30 min.
- [ ] 0.4 Create `docker/data/gh26_experiment/docker-compose.baseline.yml`: 2 containers (`batch_0`, `batch_1`) each running `rv-experiment` with `RV_TOOLS=ape,fastbot,rvagent:pure_algorithm`, `RV_TIMEOUTS=300`, `RV_REPETITIONS=3`, `RV_NO_WINDOW=true`. Each container gets its batch filter file (5 APKs). Use `RV_SKIP_MONITORS=true`, `RV_SKIP_INSTRUMENT=true`, `RV_SKIP_STATIC_ANALYSIS=true` (pre-processed). Mount `instrumented_apks/` as APK source. Stagger start: `RV_DELAY=0` and `RV_DELAY=10`. Resource limits: `cpus: 4, memory: 8g` per container. Results in `docker/data/gh26_experiment/results/baseline/batch_0/` and `batch_1/`.
- [ ] 0.5 Run baseline experiment: `docker compose -f docker/data/gh26_experiment/docker-compose.baseline.yml up`. Monitor progress. Each container runs 5 APKs × 3 tools × 3 reps = 45 tasks. Expected duration: ~4-5 hours with 2 containers. Resume on failure via `RV_EXPERIMENT_NAME`.
- [ ] 0.6 Aggregate baseline metrics: merge `summary.csv` from both batches into `docker/data/gh26_experiment/baseline_metrics.csv`. Compute per (apk, tool): mean and std of `cov_method`, `cov_act`, `cov_rv_method`, `errors`. Archive rv-agent tracking JSONL logs for post-implementation comparison of UI coverage metrics.

## 1. Configuration & Models

New config fields, constants, and data model changes that all other groups depend on.

- [ ] 1.1 Add 8 new fields to `RVAgentConfig` in `config/agent_config.py`: `backtrack_saturation_threshold` (float, default 0.8, range 0.5-1.0), `path_buffer_enabled` (bool, default True), `mop_nav_weight` (float, default 2.0, range 0.5-5.0), `mop_max_input_variations` (int, default 11, range 5-15), `reward_gamma` (float, default 0.8, range 0.5-0.99), `reward_mop_weight` (float, default 5.0, range 1.0-10.0), `reward_propagation_n` (int, default 5, range 3-8), `reward_score_weight` (float, default 1.0, range 0.1-3.0 — controls cumulative_reward influence in StrengthScorer). Each field uses `Field()` with `ge`/`le` constraints. Satisfies Data Contracts in delta spec.
- [ ] 1.2 Update default scorer weights in `config/agent_config.py`: `mop_direct_score` 300->500, `mop_transitive_score` 150->300, `wtg_guided_score` 250->150, `saturation_weight` 80->100, `visitation_penalty` -10->-15, `stochastic_probability` 0.3->0.15. Satisfies FR27 scorer rebalancing.
- [ ] 1.3 Add `action_cumulative_reward: Dict[str, float]` field (default empty dict) to `ScreenNode` in `domain/screen_node.py`. Stores per-action cumulative reward from N-step propagation. Satisfies INV-AGT-20.
- [ ] 1.4 Create unit tests in `tests/unit/config/test_config_new_params.py`: verify 8 new fields have correct defaults, verify range constraints reject out-of-bounds values, verify updated scorer weight defaults. Run `uv run pytest modules/rv-agent/tests/unit/config/ -v`. (~6 tests)
- [ ] 1.5 Run `/rv-doc-code modules/rv-agent/src/rv_agent/domain/screen_node.py`
- [ ] 1.6 Update langchain/langgraph version constraints in `modules/rv-agent/pyproject.toml`: `langchain>=0.3` → `langchain>=1.2`, `langchain-core>=0.3` → `langchain-core>=1.2`, `langchain-openai>=0.3` → `langchain-openai>=1.1`, `langgraph>=0.3` → `langgraph>=1.0`, `langgraph-checkpoint>=2.0` → `langgraph-checkpoint>=4.0`, `langgraph-checkpoint-sqlite>=2.0` → `langgraph-checkpoint-sqlite>=3.0`. These reflect the actual installed versions (1.x/4.x/3.x) and prevent accidental downgrade to 0.x. Run `uv sync` from project root, then `uv run pytest modules/rv-agent/tests/unit/ -v` to verify no regressions. Check for `DeprecationWarning` in test output — fix any deprecated API calls from the 0.x→1.x migration.

## 2. Text Input Quality (7.9)

Standalone bug fixes in `InputValueGenerator`. No dependencies on Groups 3-8.

- [ ] 2.1 Create `tests/unit/strategies/test_input_value_generator_fixes.py` with TDD test cases: `test_faker_values_first_for_text` (no PINs for "text" type), `test_pins_only_for_password`, `test_pins_only_for_pin`, `test_no_empty_first_value` (all types), `test_mop_field_extended_variations` (11 edge-case payloads with `mop_max_input_variations=11`), `test_search_type`, `test_url_type`, `test_date_type`, `test_time_type`, `test_number_type`, `test_zip_type`, `test_verification_code_type`. (~12 tests). Satisfies Text Input Quality spec scenarios.
- [ ] 2.2 Fix `_get_regular_values()` in `strategies/rvagent_strategy/input_value_generator.py`: remove PINs from general text path (keep only for "password"/"pin" type), remove empty string as first value, start with Faker values directly. Add Faker generators for missing input types: search, url, date, time, number, zip, verification_code. Satisfies INV-AGT-23 value ordering and missing types.
- [ ] 2.3 Add `mop_max_input_variations` support in `_get_mop_values()`: use `config.mop_max_input_variations` (default 11) instead of `max_variations` (default 5) for MOP-reaching fields, ensuring all 11 edge-case payloads are tested. Satisfies Text Input Quality MOP field scenarios.
- [ ] 2.4 Delete duplicate `_infer_input_type()` from `strategies/rvagent_strategy/rvagent_strategy.py`. Input type inference uses `enhanced_visitor._analyze_input_type()` from rv-screen-parser via action metadata. The only caller is `_prepare_input_action()` (line ~784) — update it to read input type from the action's metadata instead. Satisfies Text Input Quality unified inference.
- [ ] 2.5 Add clear-before-type in `execution/tool_executor.py`: insert `device.clear_text()` after `click(x, y)` and before `input_text(text)` for all SET_TEXT actions. Satisfies INV-AGT-23.
- [ ] 2.6 Add LLM text tracking: when a SET_TEXT action from LLM is executed (multimode/llm_only), record the text value in `InputValueGenerator.tested_values` for the corresponding field to prevent repetition. Run all tests: `uv run pytest modules/rv-agent/tests/unit/strategies/test_input_value_generator_fixes.py -v`. Satisfies Text Input Quality LLM text tracking scenario.
- [ ] 2.7 Run `/rv-doc-code modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/input_value_generator.py`

## 3. Scorer Rebalancing & Dead Scorers (7.2, 7.8)

Weight changes and GradualDecayScorer activation. Independent of Groups 2, 4-8.

- [ ] 3.1 Create `tests/unit/strategies/ranking/test_scorer_weights.py` (TDD): `test_mop_direct_default_500`, `test_mop_transitive_default_300`, `test_mop_transitive_outweighs_wtg`, `test_wtg_default_150`, `test_visitation_penalty_default_minus15`, `test_stochastic_probability_015`. (~6 tests). Satisfies FR27 Updated Default Weights table.
- [ ] 3.2 Create `tests/unit/strategies/ranking/test_gradual_decay_scorer.py` (TDD): `test_gradual_decay_zero_visits` (score=200), `test_gradual_decay_three_visits` (score~68.6), `test_gradual_decay_registered_in_ranker` (9 active scorers). (~3 tests). Satisfies INV-AGT-21.
- [ ] 3.3 Register `GradualDecayScorer` in the active scorer list in `strategies/rvagent_strategy/rvagent_strategy.py` `__init__` (line ~186-197). The scorer is already defined in `scorers.py`. Run `uv run pytest modules/rv-agent/tests/unit/strategies/ranking/ -v` (new + existing). Satisfies INV-AGT-21.

## 4. Reward Propagation (7.5)

New `RewardPropagator` class and `StrengthScorer` integration. Independent of Groups 2, 3.

- [ ] 4.1 Create `tests/unit/strategies/test_reward_propagator.py` (TDD): all tests use the `record_action()` + `propagate()` pattern (call `record_action(state_hash, action_sig)` N times to populate internal deque, then call `propagate(reward_type, graph)` to trigger backward propagation). Tests: `test_mop_reached_propagation` (5.0 * 0.8^k formula), `test_new_activity_propagation` (gamma=0.5), `test_new_state_reward`, `test_same_state_penalty` (-0.1), `test_cumulative_accumulation` (3.2 + 1.6 = 4.8), `test_short_history` (2 record_action calls with N=5), `test_missing_state_in_graph` (skipped silently), `test_discount_calculation`. (~8 tests). Satisfies INV-AGT-20, N-Step Reward Propagation spec scenarios.
- [ ] 4.2 Create `strategies/rvagent_strategy/reward_propagator.py` with `RewardPropagator` class: `__init__(config)` (initializes `_action_history: deque(maxlen=config.reward_propagation_n)`), `record_action(state_hash, action_signature)` (appends to internal deque), `propagate(reward_type, graph)` (reads from internal deque, no action_history parameter), reward constants (`REWARD_SAME_STATE=-0.1`, `REWARD_NEW_STATE=1.0`, `REWARD_NEW_ACTIVITY=2.0`; `REWARD_MOP_REACHED` from `config.reward_mop_weight`). Updates `ScreenNode.action_cumulative_reward`. Cap cumulative reward at `MAX_CUMULATIVE_REWARD_FACTOR * config.reward_mop_weight` (default 3.0 * 5.0 = 15.0) to prevent score inflation over long sessions. Run `/rv-doc-code modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/reward_propagator.py`. Satisfies N-Step Reward Propagation API design.
- [ ] 4.3 Create `tests/unit/strategies/ranking/test_strength_scorer_reward.py` (TDD): `test_strength_with_cumulative_reward` (base + reward), `test_strength_without_cumulative_reward` (unchanged), `test_zero_cumulative_reward`. (~3 tests). Satisfies FR27 Reward-Enhanced Strength Scoring.
- [ ] 4.4 Modify `StrengthScorer.score()` in `strategies/rvagent_strategy/ranking/scorers.py`: read `action_cumulative_reward` from `ScreenNode`, add cumulative reward to success-rate-based score. Run `uv run pytest modules/rv-agent/tests/unit/strategies/ -k "reward_propagator or strength_scorer_reward" -v`. Satisfies FR27.
- [ ] 4.5 Modify `agent/nodes/learn_node.py`: after `_record_action_success()`, add two new calls. First, call `agent.strategy.reward_propagator.record_action(previous_hash, action_signature)` using the same `previous_hash` and `action_signature` (optimized coords) already computed by `_record_action_success()` — extract the action_signature computation into a shared helper `_get_action_signature(agent, state)` to avoid duplication. Second, determine `reward_type` by comparing `current_screen_hash` with `previous_screen_hash` (same_state if unchanged, new_state if changed, new_activity if activity changed) and checking `selected_action.callback_signature` (mop_reached if present and non-empty). Then call `agent.strategy.reward_propagator.propagate(reward_type, agent.strategy.graph)` (no action_history parameter — RewardPropagator reads from its internal deque). Run `uv run pytest modules/rv-agent/tests/unit/agent/nodes/ -v`. Satisfies N-Step Reward Propagation integration in learn_node.

## 5. Proactive Backtracking & Saturation (7.1, 7.6)

Activates `should_backtrack()` with saturation threshold. Modifies `rvagent_strategy.py`.

- [ ] 5.1 Create `tests/unit/strategies/test_should_backtrack.py` (TDD): `test_saturated_state_above_threshold` (0.9 > 0.8 -> True), `test_partially_explored_below_threshold` (0.7 < 0.8 -> False), `test_at_exact_threshold` (0.8 >= 0.8 -> True), `test_incomplete_successors` (-> False), `test_state_not_in_graph` (-> True), `test_single_node_graph` (-> True). (~6 tests). Satisfies INV-AGT-22.
- [ ] 5.2 Create `tests/unit/strategies/test_proactive_backtracking.py` (TDD): `test_backtrack_instead_of_continuous` (saturation 0.9 -> BACK with reason "proactive_backtrack"), `test_below_threshold_falls_to_continuous` (saturation 0.7 -> least-executed), `test_action_selection_order` (buffer -> untested -> backtrack -> continuous -> BACK). (~3 tests). Satisfies FR26 Proactive Backtracking scenarios.
- [ ] 5.3 Modify `should_backtrack()` in `strategies/rvagent_strategy/rvagent_strategy.py`: use `config.backtrack_saturation_threshold` instead of binary exhaustion check. Return True when saturation >= threshold. Satisfies INV-AGT-22.
- [ ] 5.4 Modify `select_next_action()` in `strategies/rvagent_strategy/rvagent_strategy.py`: insert proactive backtracking check (Tier 3) after untested actions (Tier 2) and before continuous mode (Tier 4). When `should_backtrack()` returns True, return BACK action. Run new + existing strategy tests: `uv run pytest modules/rv-agent/tests/unit/strategies/ -v`. Satisfies FR26 new action selection order.
- [ ] 5.5 Modify `SuccessorTracker.find_nearest_unsaturated()` in `strategies/rvagent_strategy/successor_tracker.py`: change return type from `Optional[str]` to `Optional[Tuple[str, int]]`. Add depth counter to existing BFS loop: `queue = deque([(current_state, 0)])`, track `(state_hash, depth)` pairs, return `(back_target, depth + 1)` on match. Update callers in `learn_node.py` Level 2 stuck recovery (currently uses only the hash — adapt to unpack tuple). Add unit test `test_find_nearest_unsaturated_returns_hop_count` to verify BFS returns correct distance. Run `uv run pytest modules/rv-agent/tests/unit/strategies/ -v`. Satisfies PathBuffer.plan_backtrack_path() dependency on hop count.

## 6. Path Buffer & MOP Navigation (7.4)

New `PathBuffer` class and `TransitionManager` BFS integration.

- [ ] 6.1 Create `tests/unit/strategies/test_path_buffer.py` (TDD): `test_plan_backtrack_path` (3 BACKs buffered), `test_get_next_action_sequence` (sequential retrieval + empty after exhaustion), `test_invalidate_clears_buffer`, `test_buffer_disabled` (plan methods return False), `test_plan_mop_path` (2-step path buffered), `test_plan_mop_path_no_static_data` (Strategy B returns False, A still works), `test_buffer_priority_over_untested`. (~7 tests). Satisfies Path Buffer spec scenarios, INV-AGT-19.
- [ ] 6.2 Create `strategies/rvagent_strategy/path_buffer.py` with `PathBuffer` class: `__init__(transition_manager, successor_tracker, config)`, `get_next_action()`, `plan_backtrack_path(current_hash)`, `plan_mop_path(current_activity, mop_data)`, `invalidate()`, `is_active` property, `remaining_steps` property. Run `/rv-doc-code modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/path_buffer.py`. Satisfies Path Buffer API design.
- [ ] 6.3 Create `tests/unit/services/test_transition_manager_bfs.py` (TDD): `test_bfs_finds_mop_dense_activity`, `test_bfs_mop_density_weighting` (0.3 > 0.1), `test_bfs_saturation_aware` (prefer less-saturated path), `test_bfs_no_wtg_returns_none`. (~4 tests). Satisfies FR30 BFS Path Planning scenarios.
- [ ] 6.4 Add `plan_path_to_mop_activity(current_activity, mop_data)` to `services/transition_manager.py`: BFS on WTG with MOP density weighting and saturation-aware path preference. Returns list of action dicts or None. Satisfies FR30 path planning.
- [ ] 6.5 Integrate `PathBuffer` into `RVAgentStrategy.__init__()` and `select_next_action()`: add Tier 1 (buffer check) before Tier 2 (untested), add buffer planning in Tier 3 (try plan_mop_path then plan_backtrack_path before plain BACK). Satisfies FR26 Path Buffer Integration.
- [ ] 6.6 Add buffer invalidation in `agent/nodes/learn_node.py`: after action execution, check `if agent.strategy.path_buffer.is_active and current_hash == previous_hash` — a buffered action that produces no state change (hash unchanged) means the navigation failed (BACK didn't work, click didn't transition, dialog blocked). Call `agent.strategy.path_buffer.invalidate()` and log warning. No "expected next hash" API is needed — hash-unchanged is the universal failure signal (P1 Simplicity). Run tests: `uv run pytest modules/rv-agent/tests/unit/strategies/test_path_buffer.py modules/rv-agent/tests/unit/services/test_transition_manager_bfs.py -v`. Satisfies INV-AGT-19.
- [ ] 6.7 Wire `PathBuffer` and `RewardPropagator` in `AgentFactory`: create `PathBuffer(transition_manager, successor_tracker, config)` and `RewardPropagator(config)`, pass both to `RVAgentStrategy.__init__()`. Without this wiring, the new components are never instantiated. Satisfies FR26 + N-Step Reward Propagation integration.

## 7. Speed Optimization (7.3)

Per-iteration node skipping in `decision_router_node` and `parse_node` caching.

- [ ] 7.1 Create `tests/unit/agent/nodes/test_speed_optimization.py` (TDD): `test_pure_algorithm_skips_screenshot`, `test_pure_algorithm_preserves_gh18_screenshot` (parse_node conditional capture still fires), `test_multimode_algorithm_iteration_skips_screenshot`, `test_multimode_llm_iteration_includes_screenshot`, `test_screen_desc_cache_on_same_hash`, `test_screen_desc_cache_invalidated_on_hash_change`. (~6 tests). Satisfies INV-AGT-24, FR24 Speed Optimization scenarios.
- [ ] 7.2 Add `[RVTRACK:STRATEGY]` logging in `agent/nodes/decision_node.py` for algorithm-fast-path tracking: log when an iteration routes to "algorithm" (pure_algorithm or multimode algorithm iteration). The algorithm path already skips `capture_screenshot_node` via LangGraph graph topology — no skip logic is needed here. Satisfies INV-AGT-24 tracking.
- [ ] 7.3 Add screen_desc caching in `agent/nodes/parse_node.py`: when `screen_hash == previous_screen_hash` and cached `screen_desc` exists, reuse cached value. Preserve gh18's conditional screenshot capture (independent hash-repeat check for error detection). Run `uv run pytest modules/rv-agent/tests/unit/agent/nodes/ -v` (new + existing). Satisfies FR24 speed optimization.

## 8. LLM MOP Guidance (7.7)

`NavigationGuidance` enrichment and prompt update for MOP context.

- [ ] 8.1 Create `tests/unit/services/test_mop_guidance.py` (TDD): `test_format_for_llm_with_mop_data` (non-empty string starting with "Navigation guidance:" with MOP descriptions), `test_format_for_llm_without_static_data` (empty string), `test_mop_descriptions_in_guidance` (element-to-MOP-method mapping). (~3 tests). Satisfies FR30 MOP-Specific LLM Guidance, FR24 LLM Prompt with MOP Context.
- [ ] 8.2 Modify `services/navigation_guidance.py`: extend `format_for_llm()` to include MOP-specific context when StaticAnalysisData is available (elements reaching monitored API calls, path descriptions). Update prompt template in `prompts/v13.py` with MOP navigation hints placeholder. Run `uv run pytest modules/rv-agent/tests/unit/services/test_mop_guidance.py -v`. Satisfies FR30, FR24 Navigation Hint Inclusion.

## 9. Integration Testing & Verification

Full integration tests, regression checks, and final verification. Must run after all other groups.

- [ ] 9.1 Create integration tests for strategy flow: `tests/integration/test_proactive_backtracking_integration.py` (DynamicStateGraph with saturated states -> verify BACK at threshold, ~3 tests), `tests/integration/test_path_buffer_strategy_integration.py` (buffer plan + execute + invalidation, ~3 tests). Satisfies FR26 + FR29 interaction, Path Buffer scenarios.
- [ ] 9.2 Create integration tests for reward and input: `tests/integration/test_reward_propagation_integration.py` (5 iterations + MOP reward -> verify cumulative_reward in ScreenNode, ~3 tests), `tests/integration/test_text_input_integration.py` (clear_text before input_text + LLM text tracking, ~2 tests). Satisfies INV-AGT-20, INV-AGT-23.
- [ ] 9.3 Create `tests/integration/test_mop_guidance_integration.py`: with mock static analysis data, verify LLM prompt contains MOP-specific hints from NavigationGuidance. (~2 tests). Satisfies FR24 + FR30 integration.
- [ ] 9.4 Create edge-case integration tests in `tests/integration/test_exploration_edge_cases.py`: `test_oscillation_trap` (two states A,B cycling with saturation < threshold; after ~20 iterations, negative reward accumulation on cycling actions MUST cause strategy to select a different action like BACK), `test_path_buffer_does_not_reset_stuck_count` (PathBuffer invalidation on unexpected state MUST NOT reset stuck_screen_count — stuck detection must still fire if screen stays unchanged), `test_config_backward_compatibility` (load JSON config without gh26 fields — all 8 new fields MUST use Pydantic defaults, no error), `test_graceful_degradation_without_static_analysis` (with StaticAnalysisData=None: PathBuffer Strategy B disabled, MopScorer returns 0, WtgScorer returns 0, NavigationGuidance returns empty, reward propagation operates with non-MOP rewards only, agent MUST NOT crash). (~5 tests). Satisfies cross-LLM review findings.
- [ ] 9.5 Add tracking metrics to `tracking.py`: `backtrack_count` (proactive BACK actions), `path_buffer_hit_rate` (buffered paths reaching target Activity), `reward_propagation_events` (N-step propagation triggers). Satisfies Data Contracts output fields.
- [ ] 9.6 Run full test suites and verification: `uv run pytest modules/rv-agent/tests/unit/ -v`, `uv run pytest modules/rv-agent/tests/integration/ -v`, then `/rv-verify rv-agent` (tests + lint + type checks).
- [ ] 9.7 Invoke `rv-code-reviewer` via Task tool: `subagent_type=rv-code-reviewer, prompt="Review gh26-exploration-strategy implementation: PathBuffer, RewardPropagator, proactive backtracking in select_next_action(), scorer rebalancing, GradualDecayScorer activation, InputValueGenerator fixes, speed optimization in decision_router_node, MOP guidance in NavigationGuidance. Focus on: INV-AGT-19 to INV-AGT-24 compliance, P1 Simplicity, P3 completeness (no dangling references to deleted _infer_input_type), error handling for None static analysis data."`

## 10. Post-Implementation Validation Experiment

Run the same experiment as Group 0 but with gh26 changes applied. Compare against baseline to measure the actual impact of the 9 improvements. Must run after Group 9 passes `/rv-verify` and code review.

**Comparison metrics (all 3 tools, from summary.csv):**
- Method coverage % (`cov_method`)
- Activity coverage % (`cov_act`)
- MOP method coverage % (`cov_rv_method`)
- MOP error count (`errors`)

**RVAgent-specific metrics (from tracking JSONL):**
- Unique states discovered (count of distinct `screen_hash` values)
- Stuck event count (Level 1 BACK + Level 2 restart)
- PathBuffer activation count (new: plan_backtrack + plan_mop)
- Reward propagation events (new: propagate() calls)
- Action distribution by element type (Button, EditText, CheckBox, ImageView, etc.)

**Statistical analysis:**
- Paired observations: 10 APKs × 3 reps = 30 per tool
- Test: Wilcoxon signed-rank (non-parametric, paired, n=30)
- Report: per-metric p-value + effect size (r = Z/√n)

- [ ] 10.1 Build Docker image with gh26 changes: `docker build -t phtcosta/rvandroid:gh26-validation -f docker/rvandroid/Dockerfile .` from project root. Verify image: run `uv run pytest modules/rv-agent/tests/unit/ -v` inside container to confirm all tests pass.
- [ ] 10.2 Create `docker/data/gh26_experiment/docker-compose.validation.yml`: identical to `docker-compose.baseline.yml` but using `phtcosta/rvandroid:gh26-validation` image. Results in `docker/data/gh26_experiment/results/validation/batch_0/` and `batch_1/`.
- [ ] 10.3 Run validation experiment: `docker compose -f docker/data/gh26_experiment/docker-compose.validation.yml up`. Same configuration as baseline: 2 containers, 10 APKs, 3 tools, 3 reps, 300s. Expected duration: ~4-5 hours.
- [ ] 10.4 Aggregate validation metrics: merge `summary.csv` from both batches into `docker/data/gh26_experiment/validation_metrics.csv`. Same format as `baseline_metrics.csv`.
- [ ] 10.5 Create comparison script `docker/data/gh26_experiment/compare_results.py`: reads `baseline_metrics.csv` and `validation_metrics.csv`, computes per (apk, tool) deltas for each metric, runs Wilcoxon signed-rank test per (tool, metric) pair, generates `comparison_report.md` with: (a) per-tool summary table (mean baseline → mean validation, Δ%, p-value), (b) per-APK breakdown for rvagent:pure_algorithm, (c) RVAgent-specific tracking metrics comparison (states, stuck events, buffer activations). Script uses only stdlib + scipy (for stats).
- [ ] 10.6 Run comparison and review: `python docker/data/gh26_experiment/compare_results.py`. Review `comparison_report.md`. Expected outcomes: rvagent:pure_algorithm should show improvement in method coverage and MOP error detection (from proactive backtracking + PathBuffer + reward propagation). Ape and fastbot should show no significant change (they are unmodified — serve as sanity check). If rvagent shows regression, investigate which improvement caused it by checking tracking logs.
