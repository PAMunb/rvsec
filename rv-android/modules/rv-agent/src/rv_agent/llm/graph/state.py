"""
Agent state model for LangGraph workflow.

Defines the complete state structure for the RVAgent autonomous exploration
workflow, including UI observations, strategy context, and execution metadata.

### Stateless Context Architecture:
This state uses a stateless messaging pattern inspired by rvsmart-tool, where
each LLM call receives a fresh message constructed from pre-formatted summaries.
NO message history is accumulated, preventing context window overflow.

### V5 Tool Calling Support:
For native LangGraph tool calling, messages are accumulated WITHIN a single
graph invocation (observe → assistant → tools → learn), then cleared between
iterations by the external loop.
"""

from typing import TypedDict, Optional, Any, Dict, Set, List
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


class AgentState(TypedDict):
    """
    Complete state for RVAgent LangGraph workflow with stateless context.

    ### Architectural Decisions:
    - **HYBRID MESSAGING**: Messages accumulate within a single iteration for tool calling
    - External loop clears messages between iterations (stateless across iterations)
    - Uses pre-formatted summary strings for historical context
    - Each iteration builds fresh message from summaries
    - Constant token usage (~2500 tokens/iteration) vs exponential growth
    - Memory summaries managed by AgentMemoryManager

    ### Stateless Pattern:
    - action_history_summary: Last N actions as formatted string
    - exploration_summary: Coverage metrics as string
    - memory_insights: Activity visits and patterns as string
    - navigation_path: Activity navigation history as string

    ### Tool Calling Pattern (V5):
    - messages: List of LangChain messages (UserMessage, AIMessage, ToolMessage)
    - Accumulates within graph invocation: [UserMsg, AIMsg with tool_calls, ToolMsg]
    - Cleared by external loop between iterations (stateless across iterations)
    - Enables native LangGraph tool calling with proper message flow

    ### Role in the System:
    - Provides type-safe state contract for workflow nodes
    - Enables coordinate conversion between optimized and device resolutions
    - Tracks exploration progress and termination criteria
    - Maintains strategy context throughout execution
    - Carries injected dependencies without serialization overhead

    ### Integration Points:
    - LangGraph workflow nodes consume and produce this state
    - ScreenDescription provides UI structure with MOP markers
    - Strategy name determines exploration behavior
    - Injected objects (_device, _parser, etc.) enable node functionality
    """

    # LangChain messages for tool calling (V5 - accumulated within iteration)
    messages: List[Any]                  # LangChain messages (User, AI, Tool)

    # Memory summaries (PRE-FORMATTED STRINGS - stateless context)
    action_history_summary: str          # Last N actions formatted as string
    exploration_summary: str             # States/transitions visited summary
    memory_insights: str                 # Activity visits, patterns discovered
    navigation_path: str                 # Activity navigation path history

    # Screen observation state
    screenshot_b64: str                     # Optimized screenshot (e.g., 704x1248)
    current_screen_hash: str                # XML hierarchy hash (not activity!)
    current_activity: str                   # Activity name for context
    screen_description: ScreenDescription   # Parsed UI with [M]/[DM] markers

    # Exploration state
    strategy_name: str                      # "dfs" or "bfs"
    iteration: int                          # Current iteration number
    should_continue: bool                   # Workflow continuation flag
    visited_states: List[str]               # List of visited state hashes
    state_transitions: List[tuple[str, str]]  # List of transitions: (prev_hash, current_hash)
    previous_screen_hash: Optional[str]     # Previous screen hash for transition tracking

    # Timing and termination
    start_time: float                       # Timestamp of exploration start
    timeout: int                            # Timeout in seconds

    # Coordinate conversion
    device_dimensions: tuple[int, int]      # Device screen (e.g., 1080x1920)
    optimized_dimensions: tuple[int, int]   # Optimized for LLM (e.g., 704x1248)

    # App retention tracking
    external_navigation_count: int          # Number of times navigated outside app
    is_external: bool                       # Currently outside target app

    # LLM usage tracking
    llm_tokens_input: int                   # Input tokens from last LLM call
    llm_tokens_output: int                  # Output tokens from last LLM call
    llm_time_ms: float                      # LLM response time in milliseconds

    # Transient action (passed from assistant to act node)
    current_action: Optional[Dict[str, Any]]  # Action to execute (added by assistant node)

    # Retry mechanism (V7 - progressive creativity on failures)
    retry_count: int                           # Current retry attempt (0-max_retries)
    max_retries: int                           # Maximum retries before fallback (default: 2)
    last_action_success: bool                  # Whether last action succeeded
    retry_reason: str                          # Reason for retry ("no_tool_calls", "action_failed", etc.)

    # Sampling parameters (V7 - modified progressively across retries)
    sampling_temperature: float                # Temperature: 0.1 → 0.5 → 0.9
    sampling_top_p: float                      # Top-p: 0.9 → 0.95 → 0.99
    sampling_top_k: int                        # Top-k: 40 → 50 → 60

    # Multi-mode execution control
    decision_path: str                         # Current decision path: "llm", "dfs", or "end"
    decision_maker: str                        # Who decided action: "llm", "dfs", "strategy_fallback"
    recent_action_window: List[Dict[str, Any]] # Last N actions for loop detection
    loop_detected: bool                        # Loop detected in current iteration
    used_fallback: bool                        # DFS fallback was used
    consecutive_llm_failures: int              # Consecutive LLM failures for fallback trigger
    llm_timeout_occurred: bool                 # LLM timeout occurred in last call
    last_screen_hash: Optional[str]            # Previous screen hash for transition detection

    # Injected dependencies (not serialized, prefixed with _)
    _device: Optional[Any]                  # DeviceInterface instance
    _parser: Optional[Any]                  # ScreenParser instance
    _static_data: Optional[Any]             # StaticAnalysisData (optional)
    _strategy: Optional[Any]                # Strategy instance (DFS/BFS)
    _long_term: Optional[Any]               # LongTermMemory instance
    _short_term: Optional[Any]              # ShortTermMemory instance
    _ui_coverage: Optional[Any]             # UICoverageTracker instance
    _graph: Optional[Any]                   # DynamicStateGraph instance
    _converter: Optional[Any]               # CoordinateConverter instance
    _package_name: Optional[str]            # Target app package name
