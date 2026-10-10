# CLAUDE.md - rv-agent

## Purpose

Host-side exploration agent for Android apps (layer L2). It drives a device through UIAutomator2,
chooses each action either with an algorithmic strategy or with a vision-language model (Qwen3-VL
served by SGLang), and stops only on timeout (INV-AGT-07). Static analysis data (WTG + MOP
reachability), when supplied, steers exploration toward monitored operations.

Three modes, chosen by `RVAgentConfig.agent_mode` (overridable by `RVAGENT_MODE`):
`pure_algorithm` (no LLM), `llm_only`, and `multimode` (default; LLM with probability
`llm_probability` = 0.7, algorithm otherwise).

Two ways to run it: the standalone CLI `rv-agent` (the user manages emulator and APK), or the
`rvagent` tool of rv-platform/rv-experiment (`modules/rvagent-tool`, platform manages everything).

## Architecture

### LangGraph workflow (`agent/rv_agent.py::RVAgent._build_agent_graph`)

```
parse_ui -> decision_router -+-> algorithm_node ----------------------+-> validate_action -> execute -> learn -> END
                             +-> capture_screenshot -> llm_generate --+
                             +-> END ("end" path)
```

One `graph.invoke()` is one iteration. `RVAgent.run()` is the external loop: it launches the app,
invokes the graph until `config.timeout`, and merges each returned `AgentState` (`domain/state.py`)
back. `decision_router_node` delegates to `RoutingManager.route_decision()` (`"llm"` /
`"algorithm"`). Node functions live in `agent/nodes/` and receive `(agent, state)`.

### Key components

| Component | Location (under `src/rv_agent/`) | Purpose |
|---|---|---|
| `RVAgent` | `agent/rv_agent.py` | Graph definition and timeout loop |
| `AgentFactory.create_agent(config, static_data=None, device=None)` | `agent/agent_factory.py` | Builds and injects every component; loads the prompt module `rv_agent.prompts.<prompt_version>` |
| `DeviceInterface` | `agent/device_interface.py` | Device operations over `rv_uiautomator.UIAutomator2Adapter` |
| `DynamicStateGraph` | `agent/dynamic_state_graph.py` | Runtime state graph, structural hashing (`compute_screen_hash_from_description`) |
| `NodeExplorationPolicy` | `agent/nodes/exploration_policy.py` | Idle-timeout cap, dynamic epsilon, per-activity budget (INV-AGT-51), applied by `learn_node` |
| `RVAgentStrategy` | `strategies/rvagent_strategy/rvagent_strategy.py` | Default algorithmic strategy (5-tier selection, below) |
| `ScoringPipeline.from_config` | `strategies/rvagent_strategy/ranking/pipeline.py` | The only place scorers are instantiated into an `ActionRanker` (INV-AGT-42); applies `pure_mode` |
| `ActionRanker` / scorers | `strategies/rvagent_strategy/ranking/{action_ranker,scorers}.py` | Composite scoring; deterministic or Gumbel-max stochastic selection |
| `PathBuffer` | `strategies/rvagent_strategy/path_buffer.py` | Multi-hop navigation plans (strategies A/B/C) |
| `RewardPropagator` | `strategies/rvagent_strategy/reward_propagator.py` | N-step (N=5) discounted reward, clamped to ±15 |
| `SuccessorTracker`, `PlateauDetector`, `InputValueGenerator` | `strategies/rvagent_strategy/` | Action re-enabling, stagnation detection, Faker-based input values |
| `LLMClient` | `llm/llm_client.py` | `ChatOpenAI` against SGLang, tool binding, fresh context per iteration |
| `tool_call_parser` | `llm/tools/tool_call_parser.py` | Native-then-text tool-call parsing; `denormalize_qwen_coords()` |
| `ActionNormalizer` | `domain/action.py` | Maps LLM tool calls / algorithm actions to one action dict; `from_llm()` calls `denormalize_qwen_coords()` |
| `RoutingManager`, `StuckRecovery`, `FallbackManager` | `routing/` | LLM/algorithm routing, backtrack-BFS stuck recovery, LLM-failure fallback |
| `MemoryCoordinator` | `memory/memory_coordinator.py` | Updates `ShortTermMemory` (10 iterations), `LongTermMemory` (1000 states), `UICoverageTracker`, `AgentMemoryManager` |
| `TransitionManager` | `services/transition_manager.py` | Maps GATOR WTG windows to runtime activities; `validate_static_data()` (INV-AGT-49) |
| `NavigationGuidance` | `services/navigation_guidance.py` | WTG/MOP hints shared by LLM and algorithm |
| `ComponentTriggerService` | `services/component_trigger.py` | Plateau-gated `am start-service` / `am broadcast` of MOP-reaching components (INV-AGT-48) |
| `ScreenProcessor` / `ImageHandler` | `services/screen_analyzer.py` / `services/vision_service.py` | UI parsing (`ParserFactory` UIAUTOMATOR + `RVAgentVisitor`) / screenshot capture and resize |
| `VisualErrorDetector` | `services/error_detection.py` | Form-validation error detection via rv-screen-parser's `ErrorDetector` |
| `RVAgentVisitor` | `ui/rvagent_visitor.py` | Visitor with MOP enrichment and global widget search |
| `ToolExecutor` | `execution/tool_executor.py` | Executes normalized actions on the device |
| `MetricsExporter` / `StepTraceWriter` | `metrics/exporter.py` / `metrics/step_trace.py` | Metrics JSON / per-step `decision_source` CSV (INV-AGT-52) |

Other strategies registered in `strategies/strategy_registry.py`: `rvagent` (default), `dfs`,
`bfs`, `greedy`; all implement `ExplorationStrategy` (`strategies/base_strategy.py`).

### Design decisions

1. **Constructor injection everywhere** — `AgentFactory` is the only assembly point.
2. **Stateless LLM context** — each iteration builds fresh messages from memory summaries plus the
   screenshot, so context size does not grow with the run.
3. **Coordinate-based action identity** — actions are tracked by device-space coordinates
   (`ItemAction.coords_for_matching`, INV-AGT-40), not volatile view IDs.
4. **Pre-marking** — an action is marked executed *before* execution, so a crash on it does not
   cause a crash loop.
5. **Continuous exploration** — no state is ever "exhausted"; plateau detection raises stochastic
   probability to 0.5 instead of terminating.

### 5-tier action selection (`RVAgentStrategy.select_next_action`)

| Tier | Condition | Behavior |
|---|---|---|
| 1 | `PathBuffer` active | Dispense next buffered action |
| 2 | Untested actions on screen | `ActionRanker` over untested actions |
| 3 | Saturation ≥ `backtrack_saturation_threshold` (0.8) | Plan path C (coverage) > B (MOP, WTG BFS) > A (nearest unsaturated ancestor); no plan → fall through to Tier 4 (RESTART only if no actions at all) |
| 4 | All visible actions tested | Optional scroll (`scroll_probability`), else scoring with execution-count decay |
| 5 | No actions | BACK |

Before the tiers, `foreign_activity_guard` (if on) escapes a foreign foreground with BACK.
TEXT_CHANGE actions get values from `InputValueGenerator` (up to `max_input_variations`, or
`mop_max_input_variations` on MOP-reaching screens).

### Scoring pipeline

`ScoringPipeline.from_config` builds 12 candidate `Scorer` subclasses and keeps those whose
`is_enabled(config)` is true. Values below are the `RVAgentConfig` defaults.

| Scorer | Score | Enabled when |
|---|---|---|
| `MopScorer` | +500 direct (`[DM]`), +300 transitive (`[M]`) | `mop_direct_score` or `mop_transitive_score` > 0 |
| `WtgScorer` | +150 toward unvisited WTG targets | `wtg_guided_score` > 0 |
| `MopFrontierScorer` | +`mop_frontier_weight` toward unvisited MOP activities | weight > 0 (default 0) |
| `StateMopDensityScorer` | 100 × MOP-widget density of the state | `state_mop_density_enabled` |
| `FormCompletionScorer` | +150 fill empty input, +100 submit when filled | `form_completion_enabled` |
| `SaturationScorer` | 100 × (1 − saturation) | always |
| `ComponentPriorityScorer` | +50 buttons/inputs, +40 toggles/sliders | always |
| `StrengthScorer` | 50 × success rate + `reward_score_weight` × cumulative reward | always |
| `GradualDecayScorer` | 200 × 0.7^visits, 0 after 5 visits | always |
| `CoverageDensityScorer` | 200 × coverage gap | always |
| `SystemElementFilter` | −5000 for system UI elements | always |
| `VisitationPenaltyScorer` | −15 × log(1 + visits) | always |

With defaults, 9 scorers are active; under `pure_mode`, 7.

### Steering arms and the `pure_mode` kill-switch

Config fields marked `json_schema_extra={"arm_defining": True}` (MOP/WTG weights, frontier,
launcher `trigger_mop_first`, `component_trigger_enabled`, density, form completion, and the
guards/caps `foreign_activity_guard`, `back_menu_pick_cap`, `mop_target_pick_cap`,
`idle_timeout_cap`, `dynamic_epsilon`, `activity_budget_enabled`) must also appear in
`RV_STEERING_FLAGS` (`ranking/pipeline.py`), which maps each to its off value. Assembly raises
`ConfigurationError` when a marked field is missing (INV-AGT-43). `pure_mode=True` forces every
registered flag off before assembly (INV-AGT-44). The pipeline logs its composition once as an
`[RV-ARCH]` line. Adding a steering flag means: mark the field, add it to `RV_STEERING_FLAGS`, and
add it to `RV_STEERING_OFF` in `modules/rvagent-tool/src/rvagent_tool/tools/rvagent/config.py`
(a rvagent-tool test asserts the two dicts are equal).

### Tracking logs

Decision logs use `[RVTRACK:<CATEGORY>] key=value ...` (`tracking.py`). Categories: PARSE, ROUTE,
RANK, RANK_FULL, SELECT, VALIDATE, EXEC, STATE, LEARN, LLM, NAV, ERROR, STRATEGY, BACKTRACK,
REWARD, COVERAGE, SATURATION, STRENGTH, SCROLL, SCORE_DETAIL, ATTRIBUTION, MOP_RESOLVE,
INPUT_VAR, HASH_DETAIL, SELF_LOOP, ELEMENT_MATCH, PATH_BUFFER, GUARD. `tracking.get_aggregate_counters()`
holds per-run counters (backtracks, restarts, guard escapes, ...).

When `metrics_output_dir` is set, a run writes, with base name
`<package>__<repetition>__<timeout>__rvagent:<mode>`: `.rvagent_metrics.json`, `.trace` (all
`rv_agent` logs at DEBUG), and `.trace.csv` (one row per step with `decision_source` ∈
mop/wtg/menu/form/coverage/base/component_trigger/llm).

## Directory structure

```
src/rv_agent/
├── constants.py, tracking.py
├── agent/        rv_agent.py, agent_factory.py, device_interface.py, dynamic_state_graph.py
│   └── nodes/    parse, decision, algorithm, capture, llm, validation, execute, learn nodes; exploration_policy.py
├── cli/main.py   click group: run, test, install
├── config/agent_config.py   RVAgentConfig
├── domain/       action.py, state.py, screen_node.py, exceptions.py
├── execution/tool_executor.py
├── llm/          llm_client.py; tools/sglang_tools.py, tools/tool_call_parser.py
├── memory/       memory_coordinator.py, agent_memory.py, short_term.py, long_term.py, ui_coverage.py, element_id.py
├── metrics/      exporter.py, step_trace.py
├── prompts/      v12.py … v17.py (default v13)
├── routing/      routing_manager.py, fallback_manager.py, stuck_recovery.py
├── services/     screen_analyzer.py, vision_service.py, transition_manager.py, navigation_guidance.py,
│                 component_trigger.py, error_detection.py, coordinate_utils.py, coordinate_extractor.py,
│                 action_mapper.py, screenshot_optimizer.py
├── strategies/   base_strategy.py, strategy_registry.py, dfs/bfs/greedy_strategy.py
│   └── rvagent_strategy/  rvagent_strategy.py, path_buffer.py, reward_propagator.py, successor_tracker.py,
│                          plateau_detector.py, input_value_generator.py, coverage_metrics.py
│       └── ranking/       pipeline.py, action_ranker.py, scorers.py, context.py
└── ui/rvagent_visitor.py
```

## Entry points

### Standalone CLI (`rv-agent = rv_agent.cli.main:cli`)

The user starts the emulator and installs the APK; Claude never starts or stops emulators (root
`CLAUDE.md`). For a Claude-driven run, use rv-experiment (below). LLM modes need a reachable
SGLang server.

```bash
cd modules/rv-agent
uv run rv-agent run --package br.unb.cic.cryptoapp --mode pure_algorithm --timeout 60
uv run rv-agent run --package br.unb.cic.cryptoapp --mode multimode --timeout 300 --llm-probability 0.7
uv run rv-agent run --package br.unb.cic.cryptoapp --mode llm_only --timeout 300 --debug
uv run rv-agent test                     # device connection check
uv run rv-agent install path/to/app.apk  # adb install convenience
```

`run` options: `--package/-p` (required), `--device/-d` (`emulator-5554`), `--timeout/-t` (300),
`--mode/-m`, `--strategy/-s` (`rvagent`), `--results-dir/-o` (`./rvagent_results`, becomes
`metrics_output_dir`), `--debug/-v`, `--llm-probability` (0.7). The CLI passes no static data, so
MOP/WTG scorers score 0.

### Programmatic

```python
from rv_agent.agent.agent_factory import AgentFactory
from rv_agent.config.agent_config import RVAgentConfig

config = RVAgentConfig(package_name="br.unb.cic.cryptoapp", agent_mode="pure_algorithm", timeout=120)
agent = AgentFactory.create_agent(config, static_data=None)  # StaticAnalysisData from rv-android-core
results = agent.run()  # keys: status, iterations, execution_time_s, unique_states, total_transitions, ...
```

### Via rv-experiment (`rvagent` tool, no hyphen)

```bash
uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --timeouts 60
uv run rv-experiment run --tools monkey,rvagent:multimode --apks-dir ./apks_examples --timeouts 300
```

Variants (`rvagent-tool` `get_variants()`): `default`, `multimode`, `pure_algorithm`
(`pure_mode=True`), `mop_frontier`, `llm_only`, `thorough`. The tool passes `task.static_data`
to `AgentFactory.create_agent`.

## Dependencies

**Internal** (`pyproject.toml`):
- `rv-android-core` — `StaticAnalysisData`, `WidgetEventType`, WTG/window/component models, `ConfigurationError`, `LoggingManager`.
- `rv-screen-parser` — `ParserFactory`, `ScreenDescription`/`ItemAction`, `DefaultTextVisitor` (base of `RVAgentVisitor`), `ErrorDetector`.
- `rv-uiautomator` — `UIAutomator2Adapter` only.

**Internal, tests only** (`[dependency-groups] dev`):
- `rv-static-analysis` — imported by six test files (`tests/unit/test_gh77_mop_reach.py`, `test_rvagent_visitor.py`, `test_transition_manager.py`, `test_navigation_guidance.py`, `tests/online/test_static_analysis.py`, `tests/online/conftest.py`) to build `StaticAnalysisData` from static-analysis documents (`parse_file`, `StaticAnalysisLoader`). No `src/` file imports it: at run time static data arrives as an already-parsed `StaticAnalysisData` object.

**External (used)**: `langgraph`, `langchain-core`, `langchain-openai`, `pydantic`, `pillow`,
`faker`, `click`.

**Dependents**: `rvagent-tool` (imports `rv_agent` lazily inside `execute`).

## Configuration

### Environment variables

| Variable | Effect | Default |
|---|---|---|
| `RVAGENT_MODE` | Overrides `agent_mode` in `RVAgentConfig.get_agent_mode()`; invalid values ignored | unset |
| `RVAGENT_LOG_LEVEL` | Overrides `log_level` in `get_log_level()` | unset (`INFO`) |
| `SGLANG_URL`, `SGLANG_MODEL` | Tests only (`tests/conftest.py`) | `http://192.168.0.36:30000/v1`, `Qwen/Qwen3-VL-4B-Instruct` |

### `RVAgentConfig` (`config/agent_config.py`, Pydantic with range constraints)

| Field | Default | Note |
|---|---|---|
| `package_name` | required | |
| `device_id` | `emulator-5554` | |
| `agent_mode` / `llm_probability` | `multimode` / 0.7 | |
| `timeout` | 300 | ≥ 60 |
| `strategy` | `rvagent` | `rvagent`, `dfs`, `bfs`, `greedy` |
| `seed` | None | Seeds the ranker RNG (INV-AGT-53) |
| `llm_base_url` / `llm_model` | `http://192.168.0.36:30000/v1` / `Qwen/Qwen3-VL-4B-Instruct` | |
| `llm_temperature` / `llm_top_p` / `llm_top_k` / `llm_max_tokens` / `llm_timeout` | 0.01 / 0.6 / 50 / 2048 / 30.0 s | `top_k` sent via `extra_body` |
| `prompt_version` | `v13` | `v12`–`v17` |
| `stochastic_probability` / `stochastic_temperature` | 0.15 / 1.0 | Gumbel-max selection |
| `plateau_window` / `max_input_variations` / `mop_max_input_variations` | 10 / 3 / 11 | |
| `backtrack_saturation_threshold` / `multi_value_saturation_threshold` | 0.8 / 4 | |
| `reward_gamma` / `reward_score_weight` / `coverage_density_weight` | 0.8 / 1.0 / 200.0 | |
| `scroll_probability` | 0.15 | Tier 4 scroll |
| `metrics_output_dir` | None | None → no metrics/trace files |
| `pure_mode` and steering flags | off / 0 | See "Steering arms" |

Scorer weights (`mop_direct_score`, `wtg_guided_score`, `gradual_decay_*`, `component_*_priority`,
...) are fields too; their defaults are in the scorer table. `static_analysis_path` exists but no
code reads it.

## Testing

```bash
# From rv-android root; the CI contract flags are mandatory
uv run pytest modules/rv-agent/tests --import-mode=importlib -o "addopts=" \
  -m "not (slow or online or sglang or performance or dataset)"        # what CI runs
uv run pytest modules/rv-agent/tests/unit --import-mode=importlib -o "addopts=" -q
uv run pytest modules/rv-agent/tests/unit/strategies/ranking --import-mode=importlib -o "addopts=" -q
```

| Directory | Content | Needs |
|---|---|---|
| `tests/unit/` | Components, nodes (`unit/agent/nodes/`), strategies and ranking (`unit/strategies/ranking/`, incl. `test_scoring_pipeline.py`, `test_pure_arm_parity.py`), Hypothesis tests (`test_*_hypothesis.py`) | nothing |
| `tests/integration/` | Multi-component flows (routing, path buffer, reward, MOP guidance) | nothing |
| `tests/smoke/` | Imports, config; `sglang`-marked connectivity/tool binding | SGLang for `sglang` marker |
| `tests/online/` | Device, LLM client, end-to-end | device + SGLang |
| `tests/performance/`, `tests/regression/` | LLM latency, multimode proportion; baseline comparison | SGLang |
| `tests/fixtures/` | `screenshots/{cryptoapp,hashpass,ludo}/`, `static_analysis/cryptoapp/cryptoapp.apk.json` | |

`tests/conftest.py` adds `src/` and `tests/` to `sys.path`; `tests/support_config.py` holds
shared config factories. The `require_sglang` fixture skips when SGLang is unreachable.

## Implementation notes and gotchas

- **Qwen3-VL coordinates** are normalized to `[0, 1000)`. `denormalize_qwen_coords()`
  (`llm/tools/tool_call_parser.py`) converts with `int(x / 1000 * width)`; values outside
  `[0, 1000)` are treated as pixels already. Reference: https://github.com/QwenLM/Qwen3-VL/issues/1486
- **Hybrid tool calling**: SGLang returns native `tool_calls` for Qwen3-VL only about half the
  time. `LLMClient` reads native `tool_calls` first, then parses `response.content` (Hermes XML,
  JSON array/object, markdown, pythonic) via `parse_tool_calls_from_text_with_strategy()`.
- **Defaults differ by entry point**: `RVAgentConfig` defaults enable `MopScorer` and `WtgScorer`,
  but every `rvagent-tool` variant spreads `RV_STEERING_OFF`, so `rvagent:multimode` runs with
  those weights at 0. Only `mop_frontier` turns WTG/frontier steering on.
- **Static data validation**: present-but-invalid `StaticAnalysisData` fails fast in
  `AgentFactory.create_agent` (INV-AGT-49); absent static data is a supported degraded mode.
- **Stuck detection** lives in `learn_node`: level 1 forces BACK when the screen hash is
  unchanged beyond a threshold of `max(base, elements × factor)`; level 2 uses `StuckRecovery`
  (backtrack BFS to an unsaturated ancestor, else RESTART). Validation-error detection runs
  before stuck detection so form errors are not mistaken for stuck screens.
- **`android_press_enter` does not work**: `ToolExecutor` calls `DeviceInterface.press_keycode(66)`,
  which calls `UIAutomator2Adapter.press_keycode`, a method the adapter does not define; the
  `AttributeError` is caught and the action returns False.
- **CLI prints `Execution time: 0.0s`**: `cli/main.py` reads `results["execution_time"]`, but
  `RVAgent.run()` returns `execution_time_s`.
- `example_usage.py` at the module root imports `rv_agent.core.agent_factory`, which does not
  exist; use the snippets above.
