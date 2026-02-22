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

The `RVAgentStrategy` MUST implement a coverage-optimized depth-first search with successor state tracking, continuous exploration, and pre-marking of actions.

**Successor Tracking**: The `SuccessorTracker` records which state each action leads to. If a destination state has untested actions, the original action is re-enabled for re-execution. This prevents premature backtracking from "gateway" states (e.g., a Settings button leading to a screen with many sub-options).

**Continuous Exploration**: The strategy MUST never report being "exhausted." When all actions on a screen have been tested at least once, it selects the least-executed action and continues. The timeout is the only termination condition.

**Pre-Marking**: Actions are marked as executed in `DynamicStateGraph` BEFORE device execution. If the app crashes during execution, the action is already marked and will not be retried. Failed actions are tracked separately for permanent exclusion.

#### Scenario: Untested Action Selection

- **WHEN** `select_next_action()` is called on a screen with 5 untested actions
- **THEN** the strategy MUST select one of the untested actions
- **AND** the selection MUST use `ActionRanker` for priority-based ranking

#### Scenario: Continuous Exploration After Exhaustion

- **WHEN** all actions on the current screen have been tested at least once
- **THEN** the strategy MUST NOT return None
- **AND** MUST select the least-executed action (sorted by execution count ascending, MOP priority descending)

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
- **THEN** `_select_least_executed_action()` MUST return None
- **AND** a BACK action MUST be generated to navigate away

### Requirement: Composite Action Ranking (FR27)

The strategy MUST rank available actions using a composite scoring system with 7 registered scorers. Each scorer implements the `Scorer` abstract base class with a `score(action, context) -> float` method. Scores are summed by `ActionRanker` to determine final ranking.

Action selection supports two modes: deterministic (always selects highest-scored action) and stochastic (Gumbel-max sampling with configurable temperature). The selection mode is chosen probabilistically based on `stochastic_probability` (default 0.3 = 30% stochastic, 70% deterministic).

#### Scenario: MOP Prioritization

- **WHEN** action A has `directly_reaches_mop = True` and action B has `reaches_mop = False`
- **THEN** `MopScorer` MUST assign +300 to A and 0 to B (assuming default config)
- **AND** action A MUST rank higher than B (all other scores being equal)

#### Scenario: WTG-Guided Navigation

- **WHEN** `TransitionManager` indicates that action A leads to an unvisited screen
- **THEN** `WtgScorer` MUST assign +250 to that action (default config)

#### Scenario: Stochastic Selection

- **WHEN** `stochastic_probability` = 0.3 and `random.random()` returns a value < 0.3
- **THEN** `ActionRanker.select_stochastic()` MUST be used with `stochastic_temperature`
- **AND** the selection MUST use Gumbel-max sampling (adding Gumbel noise to log-scores)

#### Scenario: Component Priority

- **WHEN** action A targets a `Button` widget and action B targets a `TextView`
- **THEN** `ComponentPriorityScorer` MUST assign +50 to A (high priority) and 0 to B (not in priority list)

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

### Requirement: WTG-Guided Navigation (FR30)

rv-agent MUST use the Window Transition Graph (from GATOR static analysis) to guide exploration when `StaticAnalysisData` is available. The integration operates through three components:

1. `TransitionManager`: Integrates WTG data with `DynamicStateGraph`, mapping static window IDs to runtime activities
2. `NavigationGuidance`: Provides unified navigation context to both LLM and algorithm
3. `WtgScorer`: Gives priority scores to actions that WTG indicates lead to unvisited screens

When static data is not available, all three components gracefully degrade: `NavigationGuidance.is_enabled` returns False, `WtgScorer` returns 0 for all actions, and `TransitionManager` provides empty guidance.

#### Scenario: WTG Guidance Available

- **WHEN** `StaticAnalysisData` with WTG is provided
- **THEN** `NavigationGuidance.is_enabled` MUST return True
- **AND** `get_context()` MUST return an `ExplorationContext` with `has_guidance = True`

#### Scenario: WTG Guidance Unavailable

- **WHEN** `StaticAnalysisData` is None
- **THEN** `NavigationGuidance.is_enabled` MUST return False
- **AND** `get_context()` MUST return an `ExplorationContext` with `has_guidance = False`
- **AND** `format_for_llm()` MUST return an empty string

#### Scenario: LLM Navigation Hint

- **WHEN** WTG guidance is available and there are unvisited screens reachable from the current activity
- **THEN** `format_for_llm()` MUST return a non-empty string starting with "Navigation guidance:"
- **AND** the string MUST list up to 3 unvisited screens and priority targets

#### Scenario: Algorithm WTG Scoring

- **WHEN** WTG indicates action A leads to an unvisited screen
- **THEN** `WtgScorer` MUST assign `wtg_guided_score` (default 250.0) to action A

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
