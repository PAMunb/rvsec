# CLAUDE.md - rv-agent

## Purpose

RV-Agent is the core LLM-driven testing module for Android application exploration. It implements an autonomous agent that uses vision-language models (Qwen3-VL) to understand Android UI screenshots and interact with applications intelligently, combining LLM-based semantic understanding with algorithmic exploration strategies.

### Key Capabilities

- **Vision-Based UI Understanding**: Uses Qwen3-VL multimodal model to analyze screenshots and identify interactive elements
- **Hybrid Exploration**: Combines LLM intelligence (70%) with algorithmic strategies (30%) for optimal coverage
- **Three Execution Modes**: `pure_algorithm`, `llm_only`, and `multimode`
- **MOP-Aware Prioritization**: Prioritizes actions that reach monitored operations from static analysis
- **WTG-Guided Navigation**: Uses Window Transition Graph from GATOR for intelligent navigation
- **Stateless LLM Context**: Fresh context each iteration (~2500 tokens) prevents context overflow
- **Coordinate Normalization**: Handles Qwen3-VL [0, 1000) coordinate space conversion to device pixels

## Architecture

### LangGraph Workflow

The agent uses LangGraph for workflow orchestration with externalized node functions:

```
              start
                |
            parse_ui
                |
         decision_router
        /       |        \
   algorithm   llm       end
        |       |
        |  capture_screenshot
        |       |
        |  llm_generate
        |       |
        +-> validate_action
                |
            execute
                |
             learn
                |
               END
```

### Key Design Decisions

1. **Component-Based Architecture**: All components injected via constructor (dependency injection)
2. **Stateless LLM Context**: Each iteration builds fresh messages from summaries
3. **Hybrid Tool Call Parsing**: Native tool_calls + fallback XML/JSON parsing for SGLang
4. **Coordinate-Based Action Tracking**: Actions tracked by (x, y) coordinates, not volatile IDs
5. **Pre-Marking Actions**: Actions marked as executed BEFORE execution to prevent crash loops
6. **Continuous Exploration**: Never "exhausted" - explores until timeout using least-executed actions
7. **Unified Tracking System**: All decision logging uses `[RVTRACK:<CATEGORY>]` prefix for grep filtering

### Tracking System

All agent decision logs use a unified prefix `[RVTRACK:<CATEGORY>]` for easy filtering and analysis.
The tracking module is at `tracking.py`.

**Categories:**
| Category | Description | Key Fields |
|----------|-------------|------------|
| PARSE | UI parsing results | iter, activity, elements, hash |
| ROUTE | Decision routing | iter, mode, path |
| RANK | Action ranking | iter, top (top-5 actions with scores) |
| SELECT | Action selection | iter, mode, action, coords, score, priority |
| VALIDATE | Action validation | iter, status, action, coords, reason |
| EXEC | Action execution | iter, action, coords, source |
| STATE | State changes | iter, changed, activity_from, activity_to, hash |
| LEARN | Learning updates | iter, stuck, memory_updated, stuck_reason |
| LLM | LLM call metrics | iter, tokens_in, tokens_out, time_ms, tool_calls, success |
| NAV | Navigation guidance | iter, wtg_available, unvisited_targets, suggested_action_id |
| STRATEGY | Tier selection and routing | iter, mode, action, reason |
| BACKTRACK | Reactive and proactive backtracking | iter, from_state, to_state, reason, strategy, remaining, target |
| REWARD | Reward propagation events | iter, type, value, steps |
| COVERAGE | Coverage-directed navigation | iter, target, potential, hops |

**Usage:**
```bash
# Filter tracking logs
grep "RVTRACK" agent.log

# Filter specific category
grep "RVTRACK:SELECT" agent.log

# Remove tracking logs for production
grep -v "RVTRACK" agent.log > clean.log
```

**NOTE**: The project uses uv workspace with editable mode. Source changes are reflected immediately without reinstalling. Only run `uv sync` from root if `pyproject.toml` dependencies change.

### Key Components

| Component | Purpose | Location |
|-----------|---------|----------|
| RVAgent | Main orchestrator using LangGraph workflow | `agent/rv_agent.py` |
| AgentFactory | Centralized dependency injection and creation | `agent/agent_factory.py` |
| DeviceInterface | Android emulator interaction via UIAutomator2 | `agent/device_interface.py` |
| DynamicStateGraph | Graph-based state tracking with structural hashing | `agent/dynamic_state_graph.py` |
| LLMClient | Vision LLM communication with SGLang backend | `llm/llm_client.py` |
| RVAgentStrategy | 5-tier action selection with proactive backtracking | `strategies/rvagent_strategy/rvagent_strategy.py` |
| PathBuffer | Buffered multi-step navigation (Strategies A/B/C) | `strategies/rvagent_strategy/path_buffer.py` |
| RewardPropagator | N-step reward propagation with gamma discounting | `strategies/rvagent_strategy/reward_propagator.py` |
| ActionRanker | Composite scorer with 9 weighted scorers | `strategies/rvagent_strategy/ranking/action_ranker.py` |
| RoutingManager | Decision routing between LLM and algorithm (stuck detection delegated to learn_node) | `routing/routing_manager.py` |
| ToolExecutor | Action execution on Android device | `execution/tool_executor.py` |
| MemoryCoordinator | Multi-component memory management | `memory/memory_coordinator.py` |
| TransitionManager | WTG + DynamicGraph integration | `services/transition_manager.py` |
| NavigationGuidance | Unified navigation hints for LLM/algorithm | `services/navigation_guidance.py` |
| ActionNormalizer | Coordinate conversion and action format unification | `domain/action.py` |
| ScreenProcessor | UI parsing and element formatting with priority scores | `services/screen_analyzer.py` |
| ImageHandler | Screenshot capture and optimization | `services/vision_service.py` |
| RVAgentVisitor | Custom visitor with MOP enrichment and global widget search | `ui/rvagent_visitor.py` |

## Directory Structure

```
src/rv_agent/
├── __init__.py              # Package exports
├── constants.py             # Validated constants (LLM params, thresholds)
├── tracking.py              # Unified [RVTRACK:<CATEGORY>] tracking module
│
├── agent/                   # Core agent components
│   ├── rv_agent.py          # Main RVAgent class with LangGraph workflow
│   ├── agent_factory.py     # Factory for agent creation with DI
│   ├── device_interface.py  # Android device interaction
│   ├── dynamic_state_graph.py # State tracking with structural hashing
│   └── nodes/               # LangGraph workflow nodes
│       ├── __init__.py
│       ├── parse_node.py        # UI capture and parsing
│       ├── decision_node.py     # LLM/algorithm routing
│       ├── algorithm_node.py    # Algorithmic action generation
│       ├── capture_node.py      # Screenshot capture for LLM
│       ├── llm_node.py          # LLM action generation
│       ├── validation_node.py   # Action validation
│       ├── execute_node.py      # Device action execution
│       └── learn_node.py        # Memory updates and stuck detection
│
├── config/                  # Configuration
│   └── agent_config.py      # RVAgentConfig with SGLang settings
│
├── domain/                  # Domain models
│   ├── action.py            # ActionNormalizer, coordinate conversion
│   ├── state.py             # AgentState TypedDict for LangGraph
│   ├── screen_node.py       # ScreenNode for graph tracking
│   └── exceptions.py        # Custom exceptions
│
├── strategies/              # Exploration strategies
│   ├── base_strategy.py     # ExplorationStrategy interface
│   ├── strategy_registry.py # Strategy factory and registry
│   ├── dfs_strategy.py      # Basic DFS strategy
│   ├── bfs_strategy.py      # Basic BFS strategy
│   ├── greedy_strategy.py   # Greedy strategy
│   └── rvagent_strategy/    # Main RVAgent strategy
│       ├── rvagent_strategy.py   # 5-tier action selection with proactive backtracking
│       ├── successor_tracker.py  # Successor state tracking
│       ├── plateau_detector.py   # Stagnation detection
│       ├── input_value_generator.py # Test value generation (clear-before-type)
│       ├── coverage_metrics.py   # Coverage tracking
│       ├── path_buffer.py        # Buffered multi-step navigation (Strategies A/B/C)
│       ├── reward_propagator.py  # N-step reward propagation with gamma discounting
│       └── ranking/              # Action ranking system
│           ├── action_ranker.py  # Composite scorer (9 active scorers)
│           ├── scorers.py        # MOP, WTG, Decay, Coverage, Saturation, etc.
│           └── context.py        # RankingContext dataclass
│
├── llm/                     # LLM interaction
│   ├── llm_client.py        # LLMClient with tool binding
│   └── tools/               # LLM tools
│       ├── sglang_tools.py      # Android action tools
│       └── tool_call_parser.py  # Hybrid native/XML parsing
│
├── memory/                  # Memory systems
│   ├── memory_coordinator.py # Coordinates all memory updates
│   ├── agent_memory.py      # Summary generation
│   ├── short_term.py        # Recent iterations
│   ├── long_term.py         # State patterns
│   ├── ui_coverage.py       # UI element coverage
│   └── element_id.py        # Element identification
│
├── metrics/                 # Metrics collection
│   └── exporter.py          # MetricsExporter - saves exploration metrics to JSON
│
├── routing/                 # Decision routing
│   ├── routing_manager.py   # LLM/algorithm routing (stuck detection via learn_node)
│   ├── fallback_manager.py  # Fallback strategy management
│   └── stuck_recovery.py    # Stuck state recovery (backtrack BFS)
│
├── services/                # Support services
│   ├── screen_analyzer.py   # ScreenProcessor
│   ├── vision_service.py    # ImageHandler
│   ├── transition_manager.py # WTG integration
│   ├── navigation_guidance.py # Navigation hints
│   ├── coordinate_utils.py  # Coordinate utilities
│   ├── coordinate_extractor.py # Coordinate extraction
│   ├── action_mapper.py     # Action mapping
│   ├── error_detection.py   # Validation error detection with false-positive filtering
│   └── screenshot_optimizer.py # Screenshot optimization
│
├── prompts/                 # LLM prompts
│   ├── v12.py               # Base prompt with navigation hints
│   ├── v13.py               # Dialog handling (default)
│   ├── v14.py               # Structured reasoning
│   ├── v15.py               # Priority scores and graph metadata inline
│   ├── v16.py               # Navigation-first exploration with variety enforcement
│   └── v17.py               # MOP-aware navigation with monitored operation context
│
├── ui/                      # UI processing
│   └── rvagent_visitor.py   # Custom visitor for screen parsing
│
├── cli/                     # Command-line interface
│   └── main.py              # CLI commands (run, test)
│
└── execution/               # Action execution
    └── tool_executor.py     # ToolExecutor
```

## Key Files

| File | Purpose |
|------|---------|
| `agent/rv_agent.py` | Main RVAgent class - LangGraph workflow, execution loop |
| `agent/agent_factory.py` | Factory pattern for agent creation with dependency injection |
| `agent/device_interface.py` | DeviceInterface - UIAutomator2 wrapper for emulator control |
| `agent/dynamic_state_graph.py` | DynamicStateGraph - structural hashing, coordinate-based tracking |
| `config/agent_config.py` | RVAgentConfig - Pydantic model with all configuration options |
| `strategies/rvagent_strategy/rvagent_strategy.py` | Main exploration strategy with successor tracking, MOP prioritization |
| `llm/llm_client.py` | LLMClient - multimodal LLM interaction with tool binding |
| `routing/routing_manager.py` | RoutingManager - decides between LLM and algorithm paths |
| `memory/memory_coordinator.py` | MemoryCoordinator - coordinates all memory system updates |
| `services/transition_manager.py` | TransitionManager - integrates static WTG with dynamic graph |
| `domain/action.py` | ActionNormalizer - coordinate conversion from [0,1000) to device pixels |
| `domain/state.py` | AgentState TypedDict - complete state for LangGraph workflow |
| `prompts/v13.py` | Default prompt with dialog handling instructions |

## Dependencies

### Internal (RV-Android Modules)

| Module | Purpose |
|--------|---------|
| rv-android-core | Foundation: domain models, event system, logging, validation |
| rv-screen-parser | UI parsing with visitor patterns for screen analysis |
| rv-uiautomator | UIAutomator2 adapter for device interaction |
| rv-static-analysis | Unified GATOR analysis for WTG and MOP data |

### External

| Package | Version | Purpose |
|---------|---------|---------|
| langchain | ^0.3 | LLM framework |
| langchain-openai | ^0.3 | OpenAI-compatible API (SGLang) |
| langgraph | ^0.3 | Workflow orchestration |
| pydantic | ^2.9 | Configuration validation |
| pillow | ^10.0 | Image processing for screenshots |
| httpx | ^0.28 | HTTP client for LLM API |
| click | ^8.1 | CLI framework |
| faker | ^29.0 | Test data generation |
| scipy | ^1.14 | Statistical functions (Gumbel-max) |

## Testing

### Test Structure

```
tests/
├── unit/                    # Isolated unit tests (no external deps)
│   ├── test_rv_agent.py
│   ├── test_rvagent_strategy.py
│   ├── test_llm_client.py
│   ├── test_device_interface.py
│   ├── test_memory_coordinator_rigorous.py
│   ├── test_*_hypothesis.py  # Property-based tests
│   └── ...
├── integration/             # Component integration tests
│   ├── test_component_integration.py
│   ├── test_routing_manager_integration.py
│   └── ...
├── smoke/                   # Quick sanity checks
│   ├── test_imports.py
│   ├── test_sglang_connectivity.py
│   ├── test_tool_binding.py
│   └── test_config_sglang.py
├── online/                  # Tests requiring device/LLM server
│   ├── test_llm_client.py
│   ├── test_device_interface.py
│   ├── test_agent_e2e.py
│   └── ...
├── performance/             # Performance and latency tests
│   ├── test_llm_latency.py
│   └── test_multimode_proportion.py
├── regression/              # Regression tests
│   └── test_baseline_comparison.py
├── system/                  # Full system tests
│   └── __init__.py
├── fixtures/                # Test data
│   ├── screenshots/         # Sample screenshots
│   │   ├── cryptoapp/
│   │   ├── hashpass/
│   │   └── ludo/
│   ├── static_analysis/     # Static analysis fixtures
│   └── ui_dumps/            # UIAutomator XML dumps
└── conftest.py              # Shared fixtures
```

### Running Tests

```bash
cd modules/rv-agent

# Unit tests only (fast, no external dependencies)
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/unit/ -v

# Smoke tests (quick sanity checks)
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/smoke/ -v

# Integration tests
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/integration/ -v

# Online tests (requires device and LLM server)
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/online/ -v

# All tests with coverage
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/ -v --cov=src/rv_agent

# Property-based tests (Hypothesis)
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/unit/test_*_hypothesis.py -v

# Specific test file
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/unit/test_rvagent_strategy.py -v
```

## Common Tasks

### Two Execution Modes

rv-agent can run in two modes:

1. **Standalone CLI** (`rv-agent`): User manages emulator and APK installation
2. **Via rv-experiment** (`rvagent` tool): Platform manages emulator and APK installation

### Prerequisites (Standalone Mode)

```bash
# 1. Start emulator (from project root)
./scripts/run_emulator.sh

# 2. Wait for device to be ready
adb wait-for-device

# 3. Install APK
adb install apks_examples/cryptoapp.apk
# Or use the convenience command:
uv run rv-agent install apks_examples/cryptoapp.apk

# 4. For LLM modes (multimode, llm_only): start SGLang server
# (see LLM Configuration section below)
```

### Running the Agent (Standalone CLI)

```bash
cd modules/rv-agent

# Pure algorithm mode (no LLM needed - good for quick testing)
uv run rv-agent run --package br.unb.cic.cryptoapp --mode pure_algorithm --timeout 60

# Multimode (default: 70% LLM / 30% algorithm) - requires SGLang server
uv run rv-agent run --package br.unb.cic.cryptoapp --mode multimode --timeout 300

# LLM only mode - requires SGLang server
uv run rv-agent run --package br.unb.cic.cryptoapp --mode llm_only --timeout 300

# With debug logging
uv run rv-agent run --package br.unb.cic.cryptoapp --mode pure_algorithm --timeout 60 --debug

# Test device connection
uv run rv-agent test
```

### Programmatic Usage

```python
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.agent.agent_factory import AgentFactory

# Create configuration
config = RVAgentConfig(
    package_name="br.unb.cic.cryptoapp",
    device_id="emulator-5554",
    agent_mode="multimode",
    llm_probability=0.7,
    timeout=300,
    strategy="rvagent"
)

# Create agent with factory
agent = AgentFactory.create_agent(config)

# Run exploration
results = agent.run()
print(f"Explored {results['unique_states']} states in {results['iterations']} iterations")
```

### Integration with rv-experiment (Recommended)

When running via rv-experiment, the platform handles:
- Emulator startup/shutdown
- APK installation
- Static analysis data loading
- Results collection

```bash
# Run via rv-experiment (handles emulator and APK installation)
uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --timeout 60

# Run multimode with longer timeout
uv run rv-experiment run --tools rvagent:multimode --apks-dir ./apks_examples --timeout 300

# Multiple tools in one experiment
uv run rv-experiment run --tools monkey,rvagent:multimode,droidbot:dfs_greedy --apks-dir ./apks_examples
```

**Note**: The tool name is `rvagent` (no hyphen) when used via rv-experiment.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RVAGENT_MODE` | Override agent mode (pure_algorithm, llm_only, multimode) | multimode |
| `RVAGENT_LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `RVAGENT_VERBOSE_COUNTERS` | Enable detailed counter logging | false |

### RVAgentConfig Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `package_name` | str | required | Target application package name |
| `device_id` | str | emulator-5554 | Android device/emulator ID |
| `agent_mode` | str | multimode | Execution mode |
| `llm_probability` | float | 0.7 | LLM probability in multimode (0.0-1.0) |
| `timeout` | int | 300 | Execution timeout in seconds |
| `strategy` | str | rvagent | Exploration strategy (rvagent, dfs, bfs, greedy) |
| `llm_model` | str | Qwen/Qwen3-VL-4B-Instruct | LLM model identifier |
| `llm_base_url` | str | http://192.168.0.36:30000/v1 | SGLang server URL |
| `llm_temperature` | float | 0.01 | LLM temperature (0.01 optimal for tool calling) |
| `prompt_version` | str | v13 | Prompt version (v12, v13, v14, v15, v16, v17) |
| `stochastic_probability` | float | 0.15 | Gumbel-max stochastic selection probability |
| `stochastic_temperature` | float | 1.0 | Gumbel-max temperature (higher = more random) |
| `backtrack_saturation_threshold` | float | 0.8 | Saturation threshold triggering proactive backtrack |
| `mop_nav_weight` | float | 2.0 | Weight for MOP-reaching targets in navigation scoring |
| `mop_max_input_variations` | int | 11 | Max input value variations for MOP-reaching screens |
| `reward_gamma` | float | 0.8 | Discount factor for N-step reward propagation |
| `reward_score_weight` | float | 1.0 | Cumulative reward weight in StrengthScorer |
| `coverage_density_weight` | float | 200.0 | CoverageDensityScorer weight for untested elements |

### LLM Configuration (SGLang)

The agent uses SGLang server with Qwen3-VL model. Key parameters validated from extensive benchmarking:

```python
# Optimal parameters for tool calling (from rvsec-vision-llm benchmark)
llm_temperature = 0.01  # Low for consistent tool calls
llm_top_p = 0.6         # Controlled sampling
llm_top_k = 50          # Controlled diversity
llm_max_tokens = 2048   # Sufficient for responses
```

## Important Implementation Notes

### Qwen3-VL Coordinate System

Qwen3-VL returns coordinates in a normalized [0, 1000) range:

```python
# Conversion to device pixels (in ActionNormalizer)
pixel_x = int((x / 1000) * device_width)
pixel_y = int((y / 1000) * device_height)
```

Reference: https://github.com/QwenLM/Qwen3-VL/issues/1486

### Hybrid Tool Call Parsing

SGLang does not have official tool calling support for Qwen3-VL. The behavior is non-deterministic (~50% native tool_calls, ~50% XML in content).

Solution in `tool_call_parser.py`:
1. Try native `response.tool_calls` first
2. If empty, parse from `response.content` (XML/JSON formats)
3. Supports: XML (Hermes), JSON array, JSON object, markdown, pythonic

### Action Ranking Scorers (9 scorers)

The `RVAgentStrategy` uses a composite scoring system with 9 scorers for action selection:

| Scorer | Score Range | Purpose |
|--------|-------------|---------|
| MopScorer | +500 (DM), +300 (M) | Prioritize MOP-reaching actions (Tier 4 only, deferred in Tier 2) |
| GradualDecayScorer | 200 * 0.7^visits (0 after 5) | Exponential decay prevents cliff effect |
| CoverageDensityScorer | 200 * coverage_gap | Prioritize actions leading to screens with untested elements |
| WtgScorer | +150 | Prioritize WTG-guided transitions to unvisited screens |
| SaturationScorer | +100 | Bonus for unsaturated states |
| ComponentPriorityScorer | +50 (buttons), +40 (toggles) | Widget type priority |
| StrengthScorer | weight * strength + rsw * cumulative_reward | Historical success rate + reward propagation |
| SystemElementScorer | -5000 | Deprioritize system elements |
| VisitationPenaltyScorer | -15 * log(1 + visits) | Logarithmic penalty for over-visited states |

### 5-Tier Action Selection

| Tier | Name | Condition | Behavior |
|------|------|-----------|----------|
| 1 | PathBuffer | Buffer has pending actions | Dispense next buffered action |
| 2 | Untested | Untested actions available | Priority selection (MOP deferred) |
| 3 | Proactive Backtrack | Saturation >= 0.8 threshold | Plan path: C (coverage) > B (MOP) > A (ancestor) |
| 4 | Scored Continuous | All actions tested, not saturated | ActionRanker with all 9 scorers |
| 5 | BACK Fallback | No actions available | Return BACK action |

### PathBuffer (Strategies A/B/C)

PathBuffer stores a sequence of actions and dispenses one per iteration for multi-hop navigation:

| Strategy | Name | Target | Method |
|----------|------|--------|--------|
| A | Backtrack | Nearest unsaturated ancestor | BFS on SuccessorTracker.back_successors |
| B | MOP | Activity with monitored operations | BFS on WTG via TransitionManager |
| C | Coverage | Ancestor with highest exploration potential | BFS scored by coverage_gap * element_count |

### RewardPropagator

N-step temporal difference reward propagation with gamma discounting. When events occur (MOP reached, new state, etc.), rewards propagate backward through the last N=5 actions. Cumulative rewards are clamped to [-15.0, +15.0] to prevent score inflation.

### Memory Systems

| System | Purpose | Retention |
|--------|---------|-----------|
| ShortTermMemory | Recent iterations | Last 10 iterations |
| LongTermMemory | State visit patterns | Up to 1000 states |
| UICoverageTracker | Element interaction tracking | Per-element counts |
| AgentMemory | Summary generation | Rolling window |
| DynamicStateGraph | State/transition graph | All discovered states |

### Stuck Detection

Stuck detection is handled by `learn_node` based on screen hash changes (evidence-based):
- Screen unchanged for N iterations triggers recovery
- Dynamic threshold based on element count
- `StuckRecovery` uses backtrack BFS to find unsaturated ancestors

The algorithmic strategy (`RVAgentStrategy`) has additional loop prevention:
- Action pre-marking (executed BEFORE execution)
- Successor tracking
- Plateau detection

### Static Analysis Integration

When `static_data` is provided:
- WTG guides navigation toward unvisited screens
- MOP data prioritizes actions reaching monitored operations
- TransitionManager maps static Window IDs to runtime activities
- NavigationGuidance provides hints to both LLM and algorithm

## Development Notes

This module is part of the RV-Android uv workspace. All modules are installed in **editable mode** via the root `pyproject.toml`.

**Key points:**
- Run `uv sync` from the project root to install all modules
- Source code changes are reflected immediately (no reinstall needed)
- Only reinstall if `pyproject.toml` dependencies change

```bash
# From project root
uv sync             # Install/update all modules (also removes unused packages)
```
