# Specification: LLM Agent

## Purpose

The LLM Agent domain encompasses rv-agent, implementing an autonomous Android application exploration agent that combines vision-language model (VLM) intelligence with algorithmic graph traversal strategies. The agent explores Android applications running on an emulator, generating test inputs to maximize code coverage -- specifically coverage of methods monitored by runtime verification specifications (MOP methods).

For the complete methodology and results of the VLM evaluation that led to the Qwen3-VL selection, see `docs/VISION.md`.

### Problem Context

Traditional automated Android test generation tools achieve limited method coverage. The best observed overall coverage in the ICST study was 26.77% (Humanoid at 300 seconds), and the best MOP method coverage was 17.16%. This means over 80% of methods that directly use monitored APIs are never exercised. The LLM Agent addresses this gap by using a vision-language model (Qwen3-VL) to understand screen content and make semantically informed exploration decisions, combined with algorithmic strategies that provide systematic coverage guarantees.

### Position in the Pipeline

The LLM Agent operates in the **execution phase** of the RV-Android pipeline. It receives an instrumented APK (from rv-instrumentation) and optional static analysis data (from rv-static-analysis), explores the running application on an Android emulator, and produces exploration metrics. Coverage and violation data are captured by rv-coverage via logcat monitoring, which runs in parallel during execution.

```
rv-static-analysis ──→ StaticAnalysisData (WTG, REACH) ──→ rv-agent
                                                              │
rv-instrumentation ──→ Instrumented APK ──→ emulator ←───────┘
                                              │
                                        logcat output ──→ rv-coverage
```

The agent can run in two modes:
1. **Standalone** (`rv-agent` CLI): User manages emulator and APK installation
2. **Managed** (via `rv-experiment`): rv-platform manages emulator lifecycle, APK installation, and coverage tracking

### Core Architecture

The agent uses **LangGraph** for workflow orchestration, implementing a directed graph of processing nodes that execute sequentially each iteration. The workflow runs inside an external timeout loop that invokes the graph repeatedly until the configured timeout expires.

```
External Loop (timeout-based)
  │
  └──→ LangGraph Workflow (one iteration)
         │
         parse_ui ──→ decision_router ──┬──→ algorithm_node ──→ validate_action ──→ execute ──→ learn ──→ END
                                        │
                                        └──→ capture_screenshot ──→ llm_generate ──→ validate_action ──→ execute ──→ learn ──→ END
```

Each workflow node is **externalized** as a standalone function in `agent/nodes/`, receiving the `RVAgent` instance and the `AgentState` TypedDict. Nodes read from state, perform their work, and return a dictionary of state updates. This design keeps orchestration logic minimal and allows independent testing of each node.

### Three Execution Modes

The agent supports three execution modes that determine how actions are selected:

| Mode | LLM Usage | Algorithm Usage | Description |
|------|-----------|-----------------|-------------|
| `pure_algorithm` | None | 100% | Algorithmic DFS exploration without LLM calls |
| `llm_only` | 100% | None | LLM decides all actions via Qwen3-VL vision |
| `multimode` | 70% (default) | 30% (default) | Probabilistic routing between LLM and algorithm |

In `multimode`, the `RoutingManager` uses `random.random()` to select between LLM and algorithm paths each iteration, with the split controlled by `llm_probability` (default 0.7). This balances the LLM's semantic understanding (recognizing login forms, understanding UI context) with the algorithm's systematic coverage.

### Dependency Injection via AgentFactory

All components are created by `AgentFactory.create_agent()`, which handles dependency wiring in the correct order:

```
AgentFactory.create_agent(config, static_data?, device?)
  │
  ├── DeviceInterface
  ├── DynamicStateGraph
  ├── TransitionManager(static_data, dynamic_graph)
  ├── NavigationGuidance(transition_manager)
  ├── UICoverageTracker
  ├── ExplorationStrategy (via StrategyRegistry)
  ├── ImageHandler
  ├── ScreenProcessor(device, dynamic_graph, ui_coverage, static_data)
  ├── LLMClient(config, prompt_module)  [if mode requires LLM]
  ├── FallbackManager
  ├── RoutingManager(config, fallback_manager, strategy)
  ├── ToolExecutor(device, image_handler)
  ├── ActionNormalizer(device_width, device_height)
  ├── ShortTermMemory, LongTermMemory, AgentMemoryManager
  ├── MemoryCoordinator(graph, short_term, long_term, ui_coverage, agent_memory)
  │
  └──→ RVAgent(config, device, graph, strategy, image_handler, screen_processor,
               llm_client, routing_manager, tool_executor, memory_coordinator,
               navigation_guidance, action_normalizer, static_data, ui_coverage)
```

### Stateless LLM Context

Each LLM call receives fresh messages constructed from pre-formatted summaries (~2500 tokens/iteration). No conversation history accumulates between iterations. This prevents context window overflow and maintains constant token usage regardless of exploration duration. The summaries include:
- `action_history_summary`: Last N actions as formatted text
- `exploration_summary`: Coverage metrics
- `memory_insights`: Activity visit patterns
- `navigation_path`: Navigation history

### Hybrid Tool Calling

SGLang does not have official tool calling support for Qwen3-VL. The observed behavior is non-deterministic: approximately 50% of responses use native `tool_calls` (structured), while 50% embed tool calls as XML `<tool_call>` tags in the `content` field. The `LLMClient` handles this with a two-stage extraction:

1. **Native extraction**: Check `response.tool_calls` for structured tool calls
2. **Fallback parsing**: If empty, parse from `response.content` using strategies in priority order: XML tags (Hermes format), JSON array, JSON object, markdown code blocks, pythonic function calls

The combined approach achieves 100% tool call extraction success. The XML fallback parser achieves a higher hit rate (69.5%) than native tool calls (60.2%).

### Qwen3-VL Coordinate System

Qwen3-VL returns coordinates in a normalized [0, 1000) range for both x and y axes, regardless of input image resolution. The `ActionNormalizer` converts these to device pixel coordinates:

```
pixel_x = int((x / 1000) * device_width)
pixel_y = int((y / 1000) * device_height)
```

Example: raw (499, 547) on a 1080x1920 screen converts to pixel (539, 1050).

### Action Ranking System

The `RVAgentStrategy` uses a composite scoring system with 7 registered scorers. Each scorer evaluates one aspect of action priority; scores are summed to determine final ranking:

**Prioritization scorers:**
- `MopScorer`: +300 (directly reaches MOP), +150 (transitively reaches MOP)
- `WtgScorer`: +250 (WTG-guided navigation to unvisited screen)
- `SaturationScorer`: +80 * (1 - saturation_rate) (bonus for unsaturated states)
- `ComponentPriorityScorer`: +50 (buttons/inputs), +40 (toggles/sliders)
- `StrengthScorer`: +50 * success_rate (historical state-transition success)

**Penalty scorers:**
- `SystemElementFilter`: -5000 (filters system UI elements like systemui)
- `VisitationPenaltyScorer`: -10 * log(1 + visits) (logarithmic penalty for over-visited states)

All scorer weights are configurable via `RVAgentConfig` fields for calibration (24 tunable parameters total).

### Two-Level Stuck Detection

Stuck detection is performed in `learn_node` based on evidence (screen hash changes):

**Level 1 -- Screen Unchanged**: If the screen hash does not change for a dynamic threshold of consecutive iterations, forces a BACK action. The threshold is `max(BASE_STUCK_THRESHOLD, num_elements * STUCK_THRESHOLD_FACTOR)`, allowing more iterations on complex screens. Form actions (SET_TEXT, checkable elements) are excluded from stuck counting because they may change internal state without altering the screen hash.

**Level 2 -- Persistent Stuck (StuckRecovery)**: After `max_blocks` iterations in the same state, attempts Backtrack BFS via `SuccessorTracker.find_nearest_unsaturated()` to locate an ancestor state with unexplored actions. If an unsaturated ancestor is found, forces BACK to navigate there. If no unsaturated ancestor exists, forces an app restart (force stop and relaunch).

### Memory Systems

The agent maintains five coordinated memory systems managed by `MemoryCoordinator`:

| System | Class | Purpose | Retention |
|--------|-------|---------|-----------|
| Dynamic State Graph | `DynamicStateGraph` | Graph of explored states and transitions with structural screen hashing | All discovered states |
| Short-Term Memory | `ShortTermMemory` | Recent iteration records (state, actions, reasoning) | Last 10 iterations |
| Long-Term Memory | `LongTermMemory` | Persistent state visit patterns and element counts | Up to 1000 states |
| UI Coverage Tracker | `UICoverageTracker` | Per-element interaction tracking and coverage metrics | Per-element counts |
| Agent Memory | `AgentMemoryManager` | Summary generation for stateless LLM context | Rolling window |

### WTG-Guided Navigation

When static analysis data is available, the `TransitionManager` integrates the Window Transition Graph (from GATOR) with the `DynamicStateGraph`, mapping static window IDs to runtime activities. `NavigationGuidance` provides a unified interface for both the LLM (via `format_for_llm()` returning text hints for the prompt) and the algorithm (via `WtgScorer` giving priority to WTG-guided actions).

### Key Data Models

```
RVAgentConfig:
  package_name: str                # Target app package (required)
  agent_mode: str                  # pure_algorithm | llm_only | multimode
  llm_probability: float           # Multimode routing probability (0.0-1.0, default 0.7)
  timeout: int                     # Execution timeout in seconds (default 300)
  strategy: str                    # Exploration strategy name (default "rvagent")
  llm_model: str                   # Model identifier (default "Qwen/Qwen3-VL-4B-Instruct")
  llm_base_url: str                # SGLang server URL (default "http://192.168.0.36:30000/v1")
  llm_temperature: float           # Temperature for tool calling (default 0.01)
  llm_top_p: float                 # Top-p parameter (default 0.6)
  prompt_version: str              # Prompt module version (default "v13")
  device_dimensions: (int, int)    # Device screen size (default 1080x1920)
  optimized_dimensions: (int, int) # Screenshot size for LLM (default 704x1248)
  stochastic_probability: float    # Gumbel-max selection probability (default 0.3)
  stochastic_temperature: float    # Gumbel-max temperature (default 1.0)
  seed: int?                       # Random seed for reproducibility
  mop_direct_score: float          # MopScorer direct MOP score (default 300.0)
  mop_transitive_score: float      # MopScorer transitive MOP score (default 150.0)
  wtg_guided_score: float          # WtgScorer guided score (default 250.0)
  # ... 24 total calibration parameters

AgentState (TypedDict):
  iteration: int                   # Current iteration number
  start_time: float                # Exploration start timestamp
  timeout: int                     # Configured timeout
  current_screen_hash: str         # Structural hash of current UI
  current_activity: str            # Current Android activity
  screen_description: ScreenDescription  # Parsed UI with MOP markers
  ui_elements_text: str            # Formatted UI for LLM prompt
  screenshot_b64: str              # Base64-encoded optimized screenshot
  current_action: dict?            # Action to execute (unified format)
  decision_path: str               # "llm" | "algorithm" | "end"
  decision_maker: str              # Who decided: "llm" | "algorithm" | "stuck_recovery"
  force_back_action: bool          # Level 1 stuck recovery flag
  force_restart_app: bool          # Level 2 stuck recovery flag
  llm_action: dict?                # Action generated by LLM
  visited_states: list[str]        # List of visited state hashes
  state_transitions: list[tuple]   # List of (from_hash, to_hash)

Unified Action Format (dict):
  action_type: str     # CLICK | SET_TEXT | LONG_CLICK | BACK | SCROLL | SWIPE | DRAG | RESTART_APP
  x: int               # Device-space X coordinate (pixels)
  y: int               # Device-space Y coordinate (pixels)
  text: str            # Text for SET_TEXT actions
  source: str          # "llm" | "algorithm" | "validation"
  original_coords: tuple?  # Raw LLM [0,1000) coordinates (for debugging)
```

### Relationships with Other Domains

**Consumes:**
- `StaticAnalysisData` from rv-static-analysis (WTG for navigation, REACH for MOP prioritization)
- `ScreenDescription`, `ItemAction` from rv-screen-parser (UI parsing with visitor patterns)
- `DeviceInterface` wraps rv-uiautomator for device interaction
- `BaseValidatedModel` from rv-android-core (Pydantic configuration base)

**Produces:**
- Exploration metrics dictionary (iterations, unique states, transitions, LLM token usage, decision proportions)
- Device interactions (clicks, text input, swipes, navigation) on the running emulator
- `[RVTRACK:<CATEGORY>]` log entries for structured analysis (10 categories)

**Consumed by:**
- rv-platform via `rvagent-tool` wrapper (tool plugin system integration)
- rv-experiment for managed execution with emulator lifecycle
- rv-agent-validation for calibration and benchmarking

## Data Contracts

### Input

- `config: RVAgentConfig` -- Agent configuration with all parameters (from caller or CLI)
- `static_data: StaticAnalysisData?` -- Optional static analysis data containing WTG and REACH (from rv-static-analysis)
- `device: DeviceInterface?` -- Optional injected device interface (from AgentFactory or test mock)
- `package_name: str` -- Target application package name (from config, required)

### Output

- `results: Dict[str, Any]` -- Exploration results dictionary containing:
  - `status: str` -- "completed" or "error"
  - `iterations: int` -- Total iterations executed
  - `execution_time_s: float` -- Total execution time in seconds
  - `unique_states: int` -- Number of unique screen states discovered
  - `total_transitions: int` -- Number of state transitions recorded
  - `llm_tokens_input: int` -- Total LLM input tokens consumed
  - `llm_tokens_output: int` -- Total LLM output tokens generated
  - `llm_time_ms: float` -- Total LLM latency in milliseconds
  - `total_actions: int` -- Total actions executed
  - `llm_executed: int` -- LLM actions that passed validation
  - `algorithm_chosen: int` -- Algorithm path selections
  - `llm_percentage: float` -- Percentage of LLM actions
  - `algorithm_percentage: float` -- Percentage of algorithm actions
  - `llm_validation_failed: int` -- LLM actions that failed validation
  - `forced_back: int` -- BACK actions from stuck detection
  - `memory_stats: dict` -- Statistics from all memory systems
  - `ui_coverage: dict` -- UI element coverage metrics

### Side-Effects

- **Android Emulator**: Actions executed on the running emulator (clicks, text input, swipes, back navigation, app restarts)
- **File System**: Screenshots saved to `screenshot_dir` (default `/tmp/rvagent_screenshots`) with rotation limit
- **File System**: Metrics JSON saved to `metrics_output_dir` if configured
- **Logcat**: Agent actions generate logcat entries captured by rv-coverage for method coverage and violation tracking
- **SGLang Server**: HTTP requests to the inference server for LLM-based action generation

### Error

- `RVAgentError` -- Base exception for all rv-agent errors
- `DeviceError` -- Device communication or action execution failure (emulator not reachable, app crash)
- `LLMError` -- LLM service unavailable, timeout, or invalid response (SGLang server down, malformed output)
- `ValidationError` -- Invalid action, state, or configuration (bad coordinates, missing required fields)
- `ValueError` -- Invalid configuration (wrong mode, missing LLM client for LLM modes)

## Invariants

- **INV-AGT-01**: The agent MUST validate that `llm_client` is not None when `agent_mode` is `llm_only` or `multimode`. If None, a `ValueError` MUST be raised during initialization.

- **INV-AGT-02**: The LangGraph workflow MUST contain exactly 8 nodes: `parse_ui`, `decision_router`, `algorithm_node`, `capture_screenshot`, `llm_generate`, `validate_action`, `execute`, and `learn`. The entry point MUST be `parse_ui`.

- **INV-AGT-03**: In `pure_algorithm` mode, the agent MUST NOT make any LLM API calls. All actions MUST be generated by the algorithmic strategy.

- **INV-AGT-04**: In `multimode`, the observed ratio of LLM-to-algorithm decisions MUST converge toward the configured `llm_probability` over a sufficient number of iterations (statistical convergence, not exact per-iteration).

- **INV-AGT-05**: Qwen3-VL coordinates in the [0, 1000) range MUST be converted to device pixel coordinates before execution using `pixel = int((normalized / 1000) * device_dimension)`. Raw normalized coordinates MUST NOT be passed to device actions.

- **INV-AGT-06**: Actions MUST be pre-marked as executed in `DynamicStateGraph` BEFORE device execution for LLM actions. This ensures crash-causing actions are not retried. Algorithm actions are pre-marked in `RVAgentStrategy.select_next_action()`.

- **INV-AGT-07**: The agent MUST continue executing until the configured `timeout` expires. The timeout is the ONLY permitted termination condition for the main execution loop in `rv_agent.py`. No other mechanism — including but not limited to plateau detection, global saturation detection, early termination flags, coverage thresholds, or iteration counters — MUST cause the loop to break. Internal strategy signals (plateau detection, saturation) are informational only: they MAY influence action selection (e.g., boost randomness, force RESTART) but MUST NEVER terminate the loop. Any code that adds a `break` or exit path to the main loop for reasons other than timeout or `KeyboardInterrupt` violates this invariant.

- **INV-AGT-08**: Each LLM call MUST receive fresh messages constructed from summaries. No conversation history MUST accumulate between iterations. Token usage per iteration MUST remain approximately constant (~2500 tokens).

- **INV-AGT-09**: Tool call extraction MUST first attempt native `response.tool_calls`, then fall back to content parsing if empty. The combined approach MUST achieve near-100% extraction success for well-formed responses.

- **INV-AGT-11**: `ActionNormalizer.from_llm()` MUST preserve the original [0, 1000) coordinates in the `original_coords` field of the returned action dictionary for debugging purposes.

- **INV-AGT-12**: The `validate_action_node` MUST check LLM action coordinates against screen boundaries (status bar top 5%, navigation bar bottom 6%). Actions outside the app boundary MUST be replaced with a BACK action.

- **INV-AGT-13**: The `decision_router_node` MUST check for forced recovery actions (`force_restart_app`, `force_back_action`) before delegating to `RoutingManager`. Recovery actions take precedence over mode-based routing.

- **INV-AGT-14**: `RVAgentStrategy` MUST filter actions to the target application package. Actions from packages not matching `target_package` MUST be excluded, except for system dialog packages (permission dialogs, alerts) listed in `SYSTEM_DIALOG_PACKAGES`.

- **INV-AGT-15**: Screenshot dimensions MUST be multiples of 32 for Qwen3-VL compatibility. The default optimized dimensions are 704x1248 (22x32 and 39x32 respectively).

- **INV-AGT-16**: The `MemoryCoordinator` MUST coordinate updates to all five memory systems (DynamicStateGraph, ShortTermMemory, LongTermMemory, UICoverageTracker, AgentMemoryManager) in a single `update_memories()` call. Partial failures MUST NOT prevent other systems from updating.

- **INV-AGT-17**: `SuccessorTracker` MUST re-enable actions whose destination states have untested actions. This prevents premature backtracking when an action leads to a state with multiple unexplored sub-options.

- **INV-AGT-18**: The environment variable `RVAGENT_MODE` MUST override the `agent_mode` configuration setting when set to a valid mode value.

- **INV-AGT-20**: The agent detects validation error indicators on the current screen after each action execution. Detection uses visual analysis (color-based) on a screenshot via `VisualErrorDetector`, which wraps rv-screen-parser's `ErrorDetector`. Screenshots are only available when `parse_ui_node` detects that the screen hash repeats (same screen after action). Detection runs in `learn_node` before stuck detection.

- **INV-AGT-21**: When a validation error is detected, the agent resets `stuck_screen_count` to 0. This prevents the stuck detection system from forcing a BACK action on a screen where the agent should stay and fill inputs.

- **INV-AGT-22**: When a validation error is detected, `learn_node` sets `force_fill_input = True` and `error_indicators` in the agent state. `algorithm_node` responds by using spatial association to find the input field closest to an error indicator and generating an appropriate action: SET_TEXT for EditText fields, CLICK for Spinner/dropdown fields. If spatial association finds no match, it falls back to sequential iteration of TEXT_CHANGE actions. After the action is generated, the flag and indicators are cleared.

- **INV-AGT-23**: Validation errors MUST NOT be treated as permanent action failures. The action that caused the validation error is correct — it only fails because input preconditions are not met. Once inputs are filled, the same action should be retried.

- **INV-AGT-24**: The agent MUST limit consecutive error recovery attempts to `MAX_ERROR_RECOVERY` (3) per screen visit. When the limit is reached, detection is disabled and the counter stays at MAX — it does NOT reset while the screen remains the same. The counter resets to 0 only when the screen changes (no screenshot available). This 3-way branching prevents an infinite cycle where reaching MAX → resetting counter → re-enabling detection → reaching MAX again.

- **INV-AGT-25**: `parse_ui_node` captures a screenshot for error detection ONLY when the current screen hash equals the previous screen hash (same screen after action). When the screen hash differs, `error_detection_screenshot` is set to None.

- **INV-AGT-26**: When `force_fill_input` is set, `algorithm_node` uses spatial association to map each `ErrorIndicator` (with coordinates in device pixel space) to the nearest actionable screen item. Widget-type boosts (1.2x for EditText, 1.1x for Spinner) serve as prioritization tiebreakers. A below-field heuristic handles error indicators positioned up to 100px below a field. The highest-scoring match above the minimum threshold (0.1) is selected. If no spatial match is found, the algorithm falls back to `_find_next_input_action()`.

- **INV-AGT-27**: `VisualErrorDetector` filters out error indicators located in system bar areas: top 5% of the screenshot height (status bar) and bottom 6% (navigation bar). The percentages match the existing thresholds used by `RVAgentStrategy._is_system_action()` for consistency.
## Requirements
### Requirement: LangGraph Workflow with Externalized Nodes (FR21)

rv-agent MUST use LangGraph for workflow orchestration with 8 externalized node functions. The workflow is a `StateGraph` operating on the `AgentState` TypedDict. Each node is implemented as a standalone function in the `agent/nodes/` directory, receiving the `RVAgent` instance and current state, returning a dictionary of state updates.

The workflow graph defines the following edges:
- `parse_ui` -> `decision_router` (unconditional)
- `decision_router` -> `capture_screenshot` | `algorithm_node` | END (conditional on `decision_path`)
- `capture_screenshot` -> `llm_generate` (unconditional)
- `llm_generate` -> `validate_action` (unconditional)
- `algorithm_node` -> `validate_action` (unconditional)
- `validate_action` -> `execute` (unconditional, no fallback cycle)
- `execute` -> `learn` (unconditional)
- `learn` -> END (unconditional)

The external execution loop invokes the compiled graph repeatedly with `graph.invoke(state, {"recursion_limit": 100})` until the timeout expires or the user interrupts.

#### Scenario: Workflow Builds Successfully

- **WHEN** `AgentFactory.create_agent()` is called with a valid `RVAgentConfig`
- **THEN** the `RVAgent._build_agent_graph()` method MUST compile a `StateGraph` with 8 nodes
- **AND** the entry point MUST be `parse_ui`
- **AND** the graph MUST compile without errors

#### Scenario: External Loop Respects Timeout

- **WHEN** the agent `run()` method starts with a timeout of T seconds
- **THEN** the external loop MUST invoke the graph repeatedly
- **AND** MUST stop when `time.time() - start_time >= T`
- **AND** the final results dictionary MUST have `status` = "completed"

#### Scenario: Consecutive Error Tolerance

- **WHEN** an iteration raises an exception
- **THEN** the agent MUST increment a consecutive error counter
- **AND** MUST continue execution (not terminate) even after `max_consecutive_errors` (10) errors
- **AND** MUST reset the counter after a successful iteration

#### Scenario: Node State Updates

- **WHEN** `parse_ui_node` executes successfully
- **THEN** the returned dictionary MUST contain `current_screen_hash`, `current_activity`, `screen_description`, `ui_elements_text`, `is_external`, and `external_navigation_count`

### Requirement: Three Execution Modes (FR22, NFR02)

rv-agent MUST support three execution modes configured via `RVAgentConfig.agent_mode` or the `RVAGENT_MODE` environment variable. The mode determines how the `RoutingManager.route_decision()` method selects between the LLM and algorithm paths.

In `pure_algorithm` mode, `route_decision()` always returns `"algorithm"`. In `llm_only` mode, it always returns `"llm"`. In `multimode`, it uses `random.random() < llm_probability` to select probabilistically, with the default `llm_probability` being 0.7 (70% LLM / 30% algorithm).

#### Scenario: Pure Algorithm Mode

- **WHEN** `agent_mode` is `"pure_algorithm"`
- **THEN** `route_decision()` MUST always return `"algorithm"`
- **AND** `llm_client` MAY be None
- **AND** no LLM API calls MUST be made

#### Scenario: LLM Only Mode

- **WHEN** `agent_mode` is `"llm_only"`
- **THEN** `route_decision()` MUST always return `"llm"`
- **AND** `llm_client` MUST NOT be None (ValueError raised otherwise)

#### Scenario: Multimode Default Routing

- **WHEN** `agent_mode` is `"multimode"` with `llm_probability` = 0.7
- **THEN** over 1000 iterations, approximately 700 SHOULD route to `"llm"` and 300 to `"algorithm"`
- **AND** each individual decision MUST use `random.random() < 0.7`

#### Scenario: Environment Variable Override

- **WHEN** the environment variable `RVAGENT_MODE` is set to `"pure_algorithm"`
- **AND** `agent_mode` in config is `"multimode"`
- **THEN** `config.get_agent_mode()` MUST return `"pure_algorithm"`

#### Scenario: Invalid Mode Rejected

- **WHEN** `AgentFactory.create_agent()` is called with `agent_mode` = `"invalid"`
- **THEN** a `ValueError` MUST be raised

### Requirement: UI Parsing via UIAutomator XML + Screen Processor (FR23)

rv-agent MUST capture and parse the Android UI state using UIAutomator2 XML hierarchy dumps. The `ScreenProcessor` coordinates device interaction (via `DeviceInterface`), XML parsing (via rv-screen-parser), and element formatting (with MOP enrichment from static analysis data).

The parsing produces a `ScreenDescription` containing `ScreenItem` elements with `ItemAction` objects. Each `ItemAction` includes coordinates, MOP tracking metadata (`reaches_mop`, `directly_reaches_mop`), and widget type information.

UI elements are formatted as text for the LLM prompt, with coordinates presented in the [0, 1000) normalized space so the VLM can reference them directly in tool calls.

#### Scenario: Successful UI Parse

- **WHEN** `parse_ui_node` executes on a running application
- **THEN** `screen_processor.parse_current_screen()` MUST return a dictionary with `screen_hash`, `activity`, `screen_description`, `ui_elements_text`, `is_external`, and `external_navigation_count`
- **AND** the `screen_description` MUST be a `ScreenDescription` with interactive elements

#### Scenario: External App Detection

- **WHEN** the current foreground activity does not match the target `package_name`
- **THEN** `is_external` MUST be `True`
- **AND** `external_navigation_count` MUST be incremented

#### Scenario: UI Coverage Registration

- **WHEN** a non-null `screen_hash` and `screen_description` are available
- **AND** `ui_coverage` tracker is present
- **THEN** `ui_coverage.register_screen_elements()` MUST be called to register all elements on the screen

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

### Requirement: Probabilistic Routing (FR25, NFR08)

In `multimode`, the `RoutingManager` MUST route decisions between the LLM and the algorithm using configurable probabilities. The routing uses `random.random()` for stochastic selection, with the threshold set by `config.llm_probability`.

The `RoutingManager` maintains counters for metrics validation: `llm_executed` (LLM actions that passed validation), `algorithm_chosen` (algorithm path selections), `forced_back_count` (BACK from stuck detection), and `llm_validation_failed` (null LLM actions).

#### Scenario: Probabilistic Selection

- **WHEN** mode is `multimode` with `llm_probability` = 0.7
- **THEN** each call to `route_decision()` MUST use `random.random() < 0.7` to select
- **AND** `algorithm_chosen` counter MUST increment when algorithm is selected

#### Scenario: Reproducible Routing with Seed

- **WHEN** `config.seed` is not None
- **THEN** `random.seed(config.seed)` MUST be called during initialization
- **AND** the same seed MUST produce the same routing sequence

#### Scenario: Decision Counter Reporting

- **WHEN** `get_decision_counters()` is called after execution
- **THEN** the returned dictionary MUST contain `llm_executed`, `algorithm_chosen`, `llm_percentage`, `algorithm_percentage`, `forced_back`, `llm_validation_failed`, `primary_total`, and `total_actions`

### Requirement: Coverage-Optimized DFS Strategy (FR26)

The `RVAgentStrategy` MUST implement a coverage-optimized depth-first search with successor state tracking, proactive saturation-based backtracking, path buffer integration, continuous exploration as a fallback, and pre-marking of actions.

**Action Selection Order**: The `select_next_action()` method MUST evaluate action sources in the following priority order:

1. **Path buffer**: If `PathBuffer` has a buffered path with remaining steps, execute the next buffered action. This takes highest priority because buffered paths represent multi-step navigation plans toward high-value targets (unsaturated ancestors or MOP-rich Activities).
2. **Untested actions**: If untested actions exist on the current screen, select one using `ActionRanker` with the full scorer system. **MopScorer is deferred for CLICK actions when untested SET_TEXT/TEXT_CHANGE actions exist** (INV-AGT-39), ensuring form fields are filled before submit buttons are clicked.
3. **Proactive backtracking**: If the state's saturation rate exceeds `backtrack_saturation_threshold` (default 0.8), try path planning (Strategy C > B > A). If a plan succeeds, buffer it and return the first action. If all plans fail (all reachable states saturated), fall through to Tier 4 — do NOT return a plain BACK. The `should_backtrack()` method — previously dead code — is activated to perform this saturation check.
4. **Scored continuous exploration**: Use `ActionRanker.rank_actions()` on ALL filtered actions (tested + untested) with the full scorer system (MopScorer, CoverageDensityScorer, GradualDecayScorer, SaturationScorer, etc.). This replaces the previous `_select_least_executed_action()` to ensure scorer improvements benefit long runs where 60-90% of iterations operate in this tier.
5. **BACK**: If no actions are available at all (e.g., all permanently failed or ranked list empty), return a BACK action.

**Proactive Backtracking**: When the saturation rate of the current `ScreenNode` exceeds `backtrack_saturation_threshold`, the strategy MUST return a BACK action without entering continuous mode. The `backtrack_saturation_threshold` parameter (float, 0.5-1.0, default 0.8) controls when this triggers. A threshold of 0.8 means that once 80% of actions in a state have been tested, the strategy proactively navigates away. Navigation distance is determined by `SuccessorTracker.find_nearest_unsaturated()` BFS, which returns the hop count to the nearest unsaturated ancestor.

**Path Buffer Integration**: When the `PathBuffer` has a buffered path, the strategy MUST execute buffered actions before considering untested actions. The PathBuffer is populated by three strategies defined in the Path Buffer requirement: (A) backtrack to unsaturated ancestor, (B) navigate to MOP-rich Activity via WTG BFS, and (C) navigate toward high-coverage-potential screens via BFS on learned transitions. See the Path Buffer requirement for details on buffer creation, validation, and invalidation.

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

#### Scenario: Form-First Action Sequencing (CryptoApp)

CryptoApp main screen has 3 interactive components:
- Action A: CLICK on Spinner (combobox, "Message Digest" selector — leads to dropdown with 12+ algorithms)
- Action B: SET_TEXT on EditText (text input field — stays on same screen)
- Action C: CLICK on Button ("GENERATE HASH" — MOP-reaching, `directly_reaches_mop=True`)

**Expected iteration-by-iteration flow:**

- **WHEN** the agent visits S0 (fresh CryptoApp screen, all 3 actions untested)
- **THEN** Tier 2 activates (3 untested actions)
- **AND** MopScorer is deferred for Action C (CLICK) because Action B (SET_TEXT) is untested (INV-AGT-39)
- **AND** Action C scores ~475 (no MOP), Action A scores ~425, Action B scores ~425
- **AND** Action C (GENERATE HASH) is selected (ComponentPriority +50 tiebreaker) — first click on empty form is acceptable, produces error indicators
- **AND** after execution, 2 untested actions remain [A, B]

- **WHEN** Tier 2 evaluates 2 remaining untested actions [A (CLICK Spinner), B (SET_TEXT)]
- **THEN** MopScorer is not relevant (neither A nor B has MOP)
- **AND** Action A and B score ~425 each, UI ordering selects Action A (Spinner above EditText)
- **AND** Action A navigates to S_spinner (dropdown with 12+ algorithms)

- **WHEN** agent is on S_spinner and selects "MD5"
- **THEN** returns to S1 (new state with MD5 selected, different structural hash from S0)
- **AND** on S1, all 3 actions are untested again

- **WHEN** Tier 2 evaluates S1's 3 untested actions
- **THEN** MopScorer is deferred for Action C' (CLICK) because Action B' (SET_TEXT) is untested
- **AND** Action C' scores ~475 (no MOP), Action A' and B' score ~425 each
- **AND** Action C' (GENERATE HASH) is selected again — second click, still no text but has MD5 selected

- **WHEN** Tier 2 evaluates S1's 2 remaining untested [A', B']
- **THEN** Action A' (Spinner) wins by UI ordering → navigates to S_spinner
- **AND** OR Action B' (SET_TEXT) wins → fills text field

- **WHEN** Action B' is eventually selected (either by UI ordering after A' is tested, or by stochastic selection)
- **THEN** 5 text input variations are entered (form_fill reward = 0.0 per INV-AGT-35)
- **AND** after B' exhausted, all 3 actions on S1 are in `executed_actions`

- **WHEN** all actions on S1 are tested (saturation = 33% with threshold=2, well below 80%)
- **THEN** Tier 3 (`should_backtrack()`) returns False
- **AND** Tier 4 activates: `ActionRanker.rank()` on ALL actions
- **AND** MopScorer applies at FULL weight (+500) because `has_untested_inputs` is False
- **AND** Action C' (GENERATE HASH) scores ~877 (MOP +500 + cumulative_reward from prior mop_reached)
- **AND** GENERATE HASH is re-executed with MD5 selected AND text field filled → valid MOP trigger

- **WHEN** the agent continues on S1 in Tier 4
- **THEN** saturation increases as actions are re-executed (each needs count ≥ 2 to be "saturated")
- **AND** after 6-9 iterations, saturation reaches 80-100%
- **AND** Tier 3 activates: proactive backtracking or path planning

**Key outcomes:**
1. GENERATE HASH is clicked on empty form at most ONCE per screen state (first Tier 2 pass)
2. Form fields are filled BEFORE the button is re-executed via Tier 4
3. Each combobox algorithm selection creates a new state where the flow repeats
4. The agent covers multiple (algorithm, text) combinations with valid MOP triggers
5. Saturation (threshold=2) gives 6-9 iterations per state, sufficient for thorough testing

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
- **AND** `PathBuffer.plan_backtrack_path()` returns False (no unsaturated ancestors within `MAX_BACKTRACK_HOPS`)
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
| `MopScorer` (direct) | 300 | 500 | MOP-direct actions are the primary exploration target; they MUST rank above all other scorers (deferred in Tier 2 when untested inputs exist — INV-AGT-39) |
| `MopScorer` (transitive) | 150 | 300 | MOP-transitive actions MUST outweigh WTG navigation to prevent the agent from preferring new screens over MOP paths (deferred in Tier 2 when untested inputs exist — INV-AGT-39) |
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

### Requirement: Memory Systems (FR28)

rv-agent MUST maintain five coordinated memory systems orchestrated by `MemoryCoordinator`. The coordinator provides two main operations: `update_memories()` (called from `learn_node` after each iteration) and `generate_summaries()` (generating stateless LLM context).

The `MemoryCoordinator.update_memories()` method updates DynamicStateGraph, ShortTermMemory, UICoverageTracker, and LongTermMemory in sequence. If any individual system update fails, it MUST log the error but MUST NOT prevent other systems from updating.

#### Scenario: Memory Update After Action

- **WHEN** `learn_node` calls `memory_coordinator.update_memories()` with current state data
- **THEN** all five memory systems MUST be updated
- **AND** the `recent_action_window` MUST be maintained at `action_window_size` (default 10) entries

#### Scenario: Summary Generation

- **WHEN** `generate_summaries()` is called
- **THEN** it MUST return a dictionary with `action_history_summary`, `exploration_summary`, `memory_insights`, and `navigation_path`
- **AND** each summary MUST be a non-empty string

#### Scenario: Summary Generation Fallback

- **WHEN** `generate_summaries()` encounters an error
- **THEN** it MUST return fallback summaries: "No previous actions.", "Starting exploration.", "No insights yet.", "Starting navigation."

#### Scenario: State Discovery Tracking

- **WHEN** `track_state_discovery()` is called with a new `current_hash` not in `visited_states`
- **THEN** the hash MUST be appended to `visited_states`
- **AND** `new_state_discovered` MUST be True in the return value

#### Scenario: Statistics Collection

- **WHEN** `get_all_statistics()` is called
- **THEN** the returned dictionary MUST contain keys `ui_coverage`, `short_term`, `long_term`, and `dynamic_graph`
- **AND** `dynamic_graph` MUST contain `total_states` and `total_transitions`

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

### Requirement: Qwen3-VL Coordinate Normalization (FR31)

rv-agent MUST convert coordinates from Qwen3-VL's normalized [0, 1000) range to device pixel coordinates. The `ActionNormalizer.from_llm()` method handles this conversion, storing the original coordinates for debugging.

The conversion formula is: `pixel = int((normalized / 1000) * device_dimension)`. The `denormalize_qwen_coords()` function in `tool_call_parser.py` implements the actual conversion, with special handling for coordinates that appear to already be in pixel space (values >= 1000).

#### Scenario: Standard Coordinate Conversion

- **WHEN** `ActionNormalizer.from_llm()` receives a tool call with x=499, y=547 on a 1080x1920 device
- **THEN** the converted coordinates MUST be x=539, y=1050 (approximately)
- **AND** `original_coords` MUST be (499, 547)

#### Scenario: Already-Pixel Coordinates

- **WHEN** `denormalize_qwen_coords()` receives x=540, y=1054 (values >= 1000 for y)
- **THEN** the coordinates MUST be returned as-is (int(540), int(1054))

#### Scenario: String Coordinate Handling

- **WHEN** tool args contain x="499" and y="547" (string values)
- **THEN** `normalize_tool_args()` MUST convert them to integers: x=499, y=547

#### Scenario: Array Coordinate Handling

- **WHEN** tool args contain x=[499, 547] (Qwen3-VL array format)
- **THEN** `normalize_tool_args()` MUST extract x=499, y=547 from the array

#### Scenario: Tool Name Mapping

- **WHEN** the LLM returns tool_name="android_click"
- **THEN** `ActionNormalizer.from_llm()` MUST map it to action_type="CLICK"
- **AND** unknown tool names MUST result in None being returned

### Requirement: Hybrid Tool Calling (FR32)

rv-agent MUST support hybrid tool call parsing to handle SGLang's non-deterministic behavior with Qwen3-VL. The `LLMClient._extract_tool_calls()` method implements the two-stage extraction. The `tool_call_parser.py` module implements the fallback parsing strategies.

The parsing strategies are attempted in priority order:
1. **Native**: `response.tool_calls` (structured, from LangChain)
2. **XML**: `<tool_call>` tags in content (Hermes format, most common fallback)
3. **JSON array**: `[{"name": ..., "parameters": ...}]`
4. **JSON object**: `{"name": ..., "parameters": ...}`
5. **Markdown**: Code blocks containing JSON
6. **Pythonic**: Function call syntax `android_click(x=540, y=1054)`

The `_fix_malformed_json()` function handles common malformations: missing leading zeros in floats, double colons, trailing quotes on numeric values, coordinates as arrays instead of separate x/y fields, and truncated JSON with missing closing braces.

#### Scenario: Native Tool Call Extraction

- **WHEN** the LLM response contains native `tool_calls` in the AIMessage
- **THEN** `_extract_tool_calls()` MUST use them directly
- **AND** `parser_strategy` MUST be "native"
- **AND** `normalize_tool_args()` MUST be called on each tool call's arguments

#### Scenario: XML Fallback Parsing

- **WHEN** the LLM response has empty `tool_calls` but contains `<tool_call>{"name": "android_click", "arguments": {"x": 499, "y": 547}}</tool_call>` in content
- **THEN** `parse_tool_calls_with_strategy()` MUST extract the tool call
- **AND** the returned strategy MUST be "xml"

#### Scenario: Malformed JSON Fix

- **WHEN** the XML content contains `"x": 352, 782` (missing "y" key)
- **THEN** `_fix_malformed_json()` MUST transform it to `"x": 352, "y": 782`

#### Scenario: All Strategies Fail

- **WHEN** the response content contains no recognizable tool call format
- **THEN** `parse_tool_calls_with_strategy()` MUST return ([], "none")
- **AND** `parser_stats` MUST record a failure with an appropriate reason

#### Scenario: Injecting Parsed Tool Calls

- **WHEN** tool calls are extracted via fallback parser and `response.tool_calls` is empty
- **THEN** `LLMClient._extract_tool_calls()` returns the parsed calls
- **AND** the caller (`generate_action()`) MUST inject them into `response.tool_calls`

#### Scenario: Parser Statistics Tracking

- **WHEN** tool calls are successfully parsed using any strategy
- **THEN** `parser_stats.record_success()` MUST be called with the strategy name
- **AND** `parser_stats.get_stats()` MUST return cumulative statistics including `success_rate`, `strategy_success_counts`, and `failure_reasons`

### Requirement: Validation Error Detection and Input-Filling Recovery (FR32)

rv-agent MUST detect validation error indicators on the current screen after action execution and guide the agent to fill the corresponding input fields. Detection uses `VisualErrorDetector` (wrapping rv-screen-parser's `ErrorDetector`) with a 4-stage filtering pipeline: confidence threshold, size filter, system region masking, and count filter. Error recovery uses spatial association to map error indicators to the nearest actionable input fields. The feature is controlled by `error_detection_enabled` in `RVAgentConfig`.

#### Scenario: Visual error detected via color analysis

- **WHEN** the agent clicks a submit button with empty input fields
- **AND** the resulting screen shows red error indicators (e.g., `!` icon, red underline)
- **AND** the UIAutomator dump is identical before and after (same screen hash)
- **THEN** `parse_ui_node` takes a screenshot (hash repeats)
- **AND** `VisualErrorDetector.detect()` returns `detected=True` with `error_indicators` containing coordinates and confidence >= 0.7
- **AND** `learn_node` resets `stuck_screen_count` to 0
- **AND** `learn_node` sets `force_fill_input = True` and `error_indicators` in the result state
- **AND** `algorithm_node` uses spatial association to find the input field closest to the error indicator
- **AND** for EditText: generates SET_TEXT action with test value from `InputValueGenerator`

#### Scenario: Screenshot captured only when screen hash repeats

- **WHEN** `parse_ui_node` computes the new screen hash and it equals `previous_screen_hash`
- **THEN** `parse_ui_node` calls `agent.device.take_screenshot()` and stores the path in `state["error_detection_screenshot"]`

- **WHEN** `parse_ui_node` computes the new screen hash and it differs from `previous_screen_hash`
- **THEN** `state["error_detection_screenshot"]` is set to None
- **AND** no screenshot overhead is incurred

#### Scenario: Normal flow resumes after input is filled

- **WHEN** the agent has filled an input field due to `force_fill_input`
- **AND** the next screen has a different hash
- **THEN** `parse_ui_node` does NOT capture a screenshot
- **AND** `force_fill_input` is NOT set
- **AND** the submit button is available for selection (NOT blacklisted)

#### Scenario: Spinner validation error triggers CLICK

- **WHEN** validation errors are detected on a Spinner field
- **THEN** `algorithm_node` spatially associates the error indicator to the Spinner
- **AND** generates CLICK action to open the dropdown (not SET_TEXT)

#### Scenario: Spatial fallback to sequential iteration

- **WHEN** a validation error is detected
- **AND** spatial association finds no screen item above the minimum match threshold (0.1)
- **THEN** `algorithm_node` falls back to `_find_next_input_action()` which iterates TEXT_CHANGE actions sequentially

#### Scenario: No input fields available after error detection

- **WHEN** a validation error is detected
- **AND** the current screen has no TEXT_CHANGE or Spinner actions available
- **THEN** `algorithm_node` clears `force_fill_input` and `error_indicators`
- **AND** falls through to normal action selection
- **AND** the submit action is NOT penalized

#### Scenario: Error detection disabled via configuration

- **WHEN** `error_detection_enabled` is set to `False` in `RVAgentConfig`
- **THEN** `parse_ui_node` does NOT capture error detection screenshots
- **AND** `_detect_validation_error()` returns `None`
- **AND** `force_fill_input` is never set

#### Scenario: Error recovery loop protection

- **WHEN** validation errors are detected for 3 consecutive iterations on the same screen
- **AND** `error_recovery_count` reaches `MAX_ERROR_RECOVERY` (3)
- **THEN** detection is skipped (3-way branch: screenshot exists BUT count >= MAX)
- **AND** `error_recovery_count` stays at 3 (does NOT reset to 0)
- **AND** `stuck_screen_count` accumulates normally
- **AND** after ~5 more iterations, Level 1 stuck detection triggers BACK

- **WHEN** the agent navigates to a different screen after MAX_ERROR_RECOVERY
- **THEN** `error_recovery_count` resets to 0
- **AND** error detection is re-enabled for the new screen

#### Scenario: False-positive filtering on themed apps

- **WHEN** `ErrorDetector` returns indicators where individual width OR height exceeds `error_max_indicator_size` (default 80 px)
- **THEN** those oversized indicators are filtered out

- **WHEN** after confidence, size, and region filtering, the remaining indicator count exceeds `error_max_indicator_count` (default 5)
- **THEN** `detect()` returns `detected=False` — the screen is assumed to have a red/pink theme

#### Scenario: System region masking excludes status and navigation bar

- **WHEN** `ErrorDetector` returns indicators in the top 5% (status bar) or bottom 6% (navigation bar) of the screenshot height
- **THEN** those indicators are filtered out as system bar icons
- **AND** they do not count toward the indicator total

#### Scenario: Graceful degradation when cv2 unavailable

- **WHEN** `VisualErrorDetector.detect()` is called and `cv2` cannot be imported or `cv2.imread()` returns None
- **THEN** `detect()` returns `ValidationErrorResult(detected=False, ...)`
- **AND** no exception is raised

#### Scenario: Error recovery bypasses LLM in llm_only mode

- **WHEN** `agent_mode` is `llm_only` and `force_fill_input = True`
- **THEN** `decision_node` routes to `algorithm_node` with `decision_maker="error_recovery"`
- **AND** the LLM is NOT called for this iteration

#### Scenario: Concurrent force_fill_input and force_restart_app

- **WHEN** both `force_fill_input = True` and `force_restart_app = True` are set
- **THEN** `decision_node` routes for restart (higher priority)
- **AND** `force_fill_input` persists until `learn_node`'s defensive clear resets it when the screen changes

#### Scenario: Screenshot state always explicitly set in parse_ui_node

- **WHEN** `parse_ui_node` returns its result dict
- **THEN** `error_detection_screenshot` is ALWAYS included (either file path or None)
- **AND** LangGraph state never retains a stale screenshot path from a previous iteration

### Requirement: N-Step Reward Propagation (FR27)

The agent MUST implement backward reward propagation through action chains to learn which action sequences lead to productive outcomes. This is a simplified adaptation of Fastbot's SARSA n-step approach, tailored to rv-agent's architecture. Instead of maintaining a separate Q-table, rewards are stored in the existing `ScreenNode` data structure via a new `action_cumulative_reward` dictionary.

**Reward Constants**: The system defines four reward values corresponding to progressively more valuable exploration outcomes:

| Event | Constant | Value | Description |
|-------|----------|-------|-------------|
| Same state | `REWARD_SAME_STATE` | -0.1 | Action did not change the screen state (and was not a form fill action) |
| Form fill | `REWARD_FORM_FILL` | 0.0 | SET_TEXT/TEXT_CHANGE action that did not change the screen hash — neutral reward prevents penalizing form filling that legitimately keeps the same screen |
| New state | `REWARD_NEW_STATE` | 1.0 | Discovered a previously unseen screen |
| New Activity | `REWARD_NEW_ACTIVITY` | 2.0 | Discovered a previously unseen Activity |
| MOP reached | `REWARD_MOP_REACHED` | 5.0 (constant `REWARD_MOP_WEIGHT`) | The executed action has a non-empty `callback_signature`, indicating it is structurally associated with a monitored operation method. This is a **proxy signal** — the action CAN reach MOP, not confirmation that a MOP method was actually invoked at runtime. Real-time MOP confirmation would require logcat parsing within the iteration loop, which is not feasible within the 300s time budget. |

The `REWARD_MOP_REACHED` value is the key differentiator from Fastbot's reward function, which only rewards new Activities. rv-agent's reward function specifically incentivizes reaching monitored API calls, which is the primary objective for MOP coverage.

**Backward Propagation**: When a reward event occurs (any non-zero reward), the system MUST propagate the reward backward through the last `REWARD_PROPAGATION_N` actions (constant = 5) with discount factor `reward_gamma` (default 0.8). For each step k backward from the event (k=1 to N), the propagated reward is `reward_value * gamma^k`. This reward is added to the `action_cumulative_reward` dictionary in the corresponding `ScreenNode`.

The propagation reads from `RewardPropagator`'s internal action history — a deque of `(state_hash, action_signature)` tuples maintained via `record_action()`, called by `learn_node` after each iteration. Each entry contains the state hash where the action was executed and the device-space action signature `((device_x, device_y), action_type)` per INV-AGT-40, enabling the reward to be attributed to the correct `ScreenNode` and action. This is separate from the shared `recent_action_window` (which stores raw action dicts without state hashes or device-space signatures).

**Integration with StrengthScorer**: The `StrengthScorer` MUST read `action_cumulative_reward` from the `ScreenNode` and add the cumulative reward value to its existing success-rate-based score. This means actions that historically started productive sequences (leading to MOP methods or new states) accumulate higher scores over time, steering the strategy toward repeating successful exploration patterns.

**Error Recovery Participation**: Actions with `decision_maker="error_recovery"` (from gh18) MUST participate in reward propagation. If an error recovery SET_TEXT action leads to a successful MOP trigger on a subsequent iteration, that reward MUST propagate back through the error recovery action chain.

#### Scenario: Reward Propagation on MOP Reached

- **WHEN** iteration 100 triggers a MOP method (detected via `callback_signature` in learn_node)
- **AND** `REWARD_MOP_WEIGHT` = 5.0, `reward_gamma` = 0.8, `REWARD_PROPAGATION_N` = 5
- **THEN** the action at iteration 100 MUST receive reward 5.0
- **AND** the action at iteration 99 MUST receive propagated reward 5.0 * 0.8^1 = 4.0
- **AND** the action at iteration 98 MUST receive propagated reward 5.0 * 0.8^2 = 3.2
- **AND** the action at iteration 97 MUST receive propagated reward 5.0 * 0.8^3 = 2.56
- **AND** the action at iteration 96 MUST receive propagated reward 5.0 * 0.8^4 = 2.048
- **AND** iteration 95 and earlier MUST NOT receive any propagated reward (beyond REWARD_PROPAGATION_N=5)

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
- **AND** the action is NOT a SET_TEXT or TEXT_CHANGE action
- **THEN** `REWARD_SAME_STATE` = -0.1 MUST be assigned to the action
- **AND** backward propagation MUST still be triggered (with negative reward)

#### Scenario: Form Fill Neutral Reward

- **WHEN** a SET_TEXT or TEXT_CHANGE action does not change the screen hash (same state before and after)
- **THEN** `REWARD_FORM_FILL` = 0.0 MUST be assigned to the action (NOT `REWARD_SAME_STATE` = -0.1)
- **AND** backward propagation MUST still be triggered (with neutral reward)
- **AND** cumulative_reward for the form fill action MUST NOT decrease
- **AND** this prevents a perverse incentive against filling forms that gate MOP methods (e.g., login screens requiring credentials before accessing crypto settings)

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
- **AND** the priority order MUST be: mop_reached > new_activity > new_state > form_fill > same_state

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
- **AND** `REWARD_MOP_WEIGHT` = 5.0, `reward_gamma` = 0.8
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

**Strategy A — Backtrack to Unsaturated Ancestor**: When the current state is saturated (saturation rate exceeds `backtrack_saturation_threshold`), the PathBuffer uses `SuccessorTracker.find_nearest_unsaturated()` to locate the nearest ancestor state with untested actions. `find_nearest_unsaturated()` returns `Optional[Tuple[str, int]]` — the ancestor hash and BFS hop count. The hop count determines the number of BACK actions to buffer, capped at `MAX_BACKTRACK_HOPS` (8).

**Strategy B — Navigate to MOP-Rich Activity via WTG BFS**: When `StaticAnalysisData` is available, the PathBuffer can request a path from `TransitionManager.plan_path_to_mop_activity()`. This performs BFS on the WTG to find the nearest MOP-rich Activity, weighted by MOP density (see WTG-Guided Navigation requirement). The resulting path is a sequence of actions that navigate through intermediate Activities toward the target. This strategy is rv-agent's unique advantage over APE and Fastbot — neither tool combines path planning with MOP targeting.

**Strategy C — Navigate to High-Coverage-Potential Screen via Learned Transitions**: The PathBuffer performs BFS on `SuccessorTracker`'s learned transitions (not the static WTG) to find reachable screens with the highest exploration potential, defined as `coverage_gap * element_count`. This metric prefers screens with MANY untested elements, not just a high untested percentage: a Settings screen with 15 elements at 50% coverage (potential = 7.5) is more valuable than an About screen with 2 elements at 0% coverage (potential = 2.0). BFS depth is limited by `MAX_COVERAGE_HOPS` (constant = 5). Strategy C is positioned BEFORE Strategy B in the Tier 3 evaluation order (C > B > A) because broad UI coverage addresses the "small island" problem: it increases the probability surface for finding MOP methods, including those not mapped by static analysis. Strategy C operates entirely on runtime data and is always available, even without `StaticAnalysisData`.

**Buffer Validation**: After executing each buffered action, the PathBuffer MUST validate that the resulting state matches expectations. If the actual post-execution state does not match the expected state for the current buffer step (e.g., the app navigated to an unexpected screen), the buffer MUST be cleared immediately. This prevents executing stale navigation paths that are no longer valid.

**Integration in select_next_action()**: The PathBuffer is checked first in the action selection order, before untested actions. When the buffer has remaining steps, the next buffered action is returned without consulting the scorer system. When the buffer is empty, normal action selection proceeds.

**Parameters**: `mop_nav_weight` (float, 0.5-5.0, default 2.0, configurable) controls MOP density influence in Strategy B's BFS (passed through to `TransitionManager`). `MAX_BACKTRACK_HOPS` (int, constant = 8) limits the number of BACK actions Strategy A can buffer — if the nearest unsaturated ancestor is farther than this limit, `plan_backtrack_path` returns False and the caller falls through to the next tier. `MAX_COVERAGE_HOPS` (int, constant = 5) limits the BFS depth for Strategy C — screens beyond this hop distance are not considered as navigation targets. PathBuffer is always active (no disable toggle — strategies return False when conditions aren't met).

#### Scenario: Buffer Creation via Strategy A (Backtrack)

- **WHEN** the current state has saturation rate 0.9 (above threshold 0.8)
- **AND** `SuccessorTracker.find_nearest_unsaturated()` returns an ancestor 3 BACK actions away
- **THEN** the PathBuffer MUST be populated with 3 BACK actions
- **AND** `select_next_action()` MUST return the first buffered BACK action

#### Scenario: Buffer Creation via Strategy B (MOP Navigation)

- **WHEN** `StaticAnalysisData` is available
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

#### Scenario: Backtrack Exceeds MAX_BACKTRACK_HOPS

- **WHEN** the current state has saturation rate 0.9 (above threshold 0.8)
- **AND** `SuccessorTracker.find_nearest_unsaturated()` returns an ancestor 12 BACK actions away
- **AND** `MAX_BACKTRACK_HOPS` is 8
- **THEN** `plan_backtrack_path` MUST return False (ancestor too far)
- **AND** the PathBuffer MUST NOT be populated
- **AND** the caller MUST fall through to the next action selection tier (scored continuous mode, Tier 4)

#### Scenario: Buffer Creation via Strategy C (Coverage Navigation)

- **WHEN** the current state is saturated
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

