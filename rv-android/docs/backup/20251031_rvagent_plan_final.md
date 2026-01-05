# RVAgent: Architecture Plan - Final Version

## 🎯 Objective
Autonomous LLM+vision agent that **prioritizes [DM]/[M] elements** (static analysis) and explores systematically via **DFS/BFS** with **structural hash** of UI states.

---

## 📋 Code Quality Guidelines

### Language and Comments
- **All code and comments in English**
- **Comment template** (see EventBus, TaskExecutor for reference):
  ```python
  """
  Module description.

  Brief module overview in one paragraph.
  """

  class ClassName:
      """
      Brief class description.

      ### Architectural Decisions:
      - Bullet point 1
      - Bullet point 2

      ### Role in the System:
      - Bullet point 1
      - Bullet point 2

      ### Key Features (optional):
      - Bullet point 1
      """
  ```

### Comment Content Rules
- ✅ **DO**: Describe current state and architecture
- ✅ **DO**: Focus on decisions, patterns, and integration points
- ✅ **DO**: Use objective technical language
- ❌ **DON'T**: Reference migration history (Phase 0, legacy, etc)
- ❌ **DON'T**: Use promotional language (modern, sophisticated, advanced)
- ❌ **DON'T**: Use bias terms - target audience is developers/researchers

### Code Evolution Policy
- **No legacy code** - complete refactoring, no compatibility layers
- **No adapters** for backward compatibility
- **Move old files** to `modules/rv-agent/backup/YYYY-MM-DD_description/`
- **Overwrite completely** - clean slate approach

---

## 📁 File Structure

```
modules/rv-agent/src/rv_agent/
├── core/
│   ├── rv_agent.py              ⭐ Main agent class (may need updates)
│   ├── dynamic_state_graph.py   ⭐ NEW - Graph with structural hash
│   ├── action_mapper.py         ⭐ NEW - Coordinate → Action mapping
│   └── device_interface.py      ✓ EXISTS - Device interaction
├── llm/
│   ├── graph/
│   │   ├── state.py             ⭐ NEW - AgentState TypedDict
│   │   └── nodes.py             ⭐ NEW - LangGraph workflow nodes
│   └── tools/
│       └── android_tools.py     🔧 ADAPT - Tools return structured data
├── strategies/
│   ├── base_strategy.py         ⭐ NEW - Strategy interface
│   ├── dfs_strategy.py          ⭐ NEW - DFS with soft guidance
│   └── bfs_strategy.py          ⭐ NEW - BFS with soft guidance
├── memory/                       ✓ EXISTS - LongTerm, ShortTerm, UICoverage
├── parsing/                      ✓ EXISTS - ScreenParser integration
└── config/                       ✓ EXISTS - Agent configuration

modules/rv-agent/backup/
└── 2025-01-31_pre-rvagent/      📦 MOVE old prototypes
    └── llm/tmp_001.py
```

**Module Path**: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent`

---

## 🏗️ Core Components

### 1. AgentState (llm/graph/state.py)

**Template:**
```python
"""
Agent state model for LangGraph workflow.

Defines the complete state structure for the RVAgent autonomous exploration
workflow, including UI observations, strategy context, and execution metadata.
"""

from typing import TypedDict, Annotated
from langgraph.graph import add_messages
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

class AgentState(TypedDict):
    """
    Complete state for RVAgent LangGraph workflow.

    ### Architectural Decisions:
    - Uses TypedDict for type safety in LangGraph
    - Includes dimension tracking for coordinate conversion
    - Separates screen hash from activity for precise state tracking
    - Stores ScreenDescription for rich UI understanding

    ### Role in the System:
    - Provides type-safe state contract for workflow nodes
    - Enables coordinate conversion between optimized and device resolutions
    - Tracks exploration progress and termination criteria
    - Maintains strategy context throughout execution
    """
    messages: Annotated[list, add_messages]
    screenshot_b64: str                    # optimized (e.g., 728x1288)
    current_screen_hash: str               # XML hierarchy hash (not activity!)
    screen_description: ScreenDescription  # parsed UI with [M]/[DM]
    strategy_name: str                     # "dfs" or "bfs"
    iteration: int
    should_continue: bool
    start_time: float
    timeout: int
    device_dimensions: tuple[int, int]     # e.g. (1080, 1920)
    optimized_dimensions: tuple[int, int]  # e.g. (728, 1288)
```

---

### 2. LangGraph Workflow (llm/graph/nodes.py)

**Flow:**
```
START → init_app → observe → assistant → tools_condition
                     ↑                      ↓
                     ←─ update_memories ← ToolNode (executes tools)
                     ↓
                  check_termination → END
```

**Key Nodes:**
- `init_app()`: Launch app, capture initial state
- `observe()`: Screenshot + XML → ScreenDescription + structural hash + strategy guidance
- `assistant`: LLM with tools receives system prompt + guidance
- `ToolNode`: Executes tools (LangGraph built-in)
- `update_memories()`: Maps coordinates → action, updates memories, captures next state
- `check_termination()`: Timeout check → route to observe or END

**Critical Decision: Tools DO NOT access state directly**
- Tools return structured data: `{"success": bool, "llm_coords": (x, y), "description": str, "action_type": str}`
- `update_memories` node handles all state-dependent logic:
  1. Map LLM coordinates → ScreenItem (via bounds)
  2. Select appropriate ItemAction from ScreenItem.actions
  3. Update all memories (LongTerm, ShortTerm, UICoverage)
  4. Capture next screen state

**Template:**
```python
"""
LangGraph workflow nodes for RVAgent autonomous exploration.

Implements the observe-decide-act-learn cycle for Android application testing
with integrated memory systems and strategy-guided exploration.
"""

def observe(state: AgentState) -> dict:
    """
    Capture current application state and prepare for decision.

    ### Architectural Decisions:
    - Computes structural hash for state identification
    - Integrates static analysis markers when available
    - Queries strategy for exploration guidance
    - Enriches UI description with coverage annotations

    ### Integration Points:
    - DeviceInterface for screenshot and XML capture
    - ScreenshotOptimizer for dimension-preserving compression
    - ScreenParser for UI element extraction with MOP markers
    - Strategy for priority guidance computation
    - UICoverageTracker for element testing status
    """
    # Get device interface from config
    device = state['_device']  # Injected during graph construction

    # Capture current state
    screenshot_bytes = device.get_screenshot()
    xml_hierarchy = device.get_ui_hierarchy()
    activity = device.get_current_activity()

    # Optimize screenshot for LLM
    optimized_b64 = optimize_screenshot(screenshot_bytes, state['optimized_dimensions'])

    # Compute structural hash
    screen_hash = compute_screen_hash(xml_hierarchy)

    # Parse UI with static analysis integration
    parser = state['_parser']
    static_data = state.get('_static_data')
    screen_desc = parser.parse_screen(
        {"xml": xml_hierarchy, "activity": activity},
        static_data=static_data
    )

    # Get strategy guidance
    strategy = state['_strategy']
    guidance = strategy.get_guidance(screen_hash, screen_desc)

    # Build system prompt with guidance
    system_msg = build_system_prompt(activity, screen_hash, screen_desc, guidance)

    return {
        "screenshot_b64": optimized_b64,
        "current_screen_hash": screen_hash,
        "screen_description": screen_desc,
        "messages": [system_msg]
    }


def update_memories(state: AgentState) -> dict:
    """
    Map LLM action to ScreenItem/ItemAction and update memories.

    ### Architectural Decisions:
    - Handles coordinate conversion from optimized to device space
    - Maps coordinates to ScreenItem using bounds lookup
    - Selects appropriate ItemAction from ScreenItem.actions
    - Updates all memory systems in centralized location
    - Captures next state after action execution

    ### Integration Points:
    - ActionMapper for coordinate → action resolution
    - DynamicStateGraph for state tracking
    - LongTermMemory, ShortTermMemory, UICoverageTracker
    - DeviceInterface for next state capture
    """
    # Extract tool call result from last message
    last_msg = state['messages'][-1]
    tool_result = extract_tool_result(last_msg)

    if not tool_result.get('success'):
        # Tool failed, just log and continue
        return {"iteration": state['iteration'] + 1}

    # Map LLM coordinates to action
    llm_coords = tool_result['llm_coords']
    action_type = tool_result.get('action_type', 'click')

    action_id = map_coordinates_to_action(
        llm_coords=llm_coords,
        action_type=action_type,
        screen_description=state['screen_description'],
        optimized_dims=state['optimized_dimensions'],
        device_dims=state['device_dimensions']
    )

    # Update memories
    long_term = state['_long_term']
    short_term = state['_short_term']
    ui_coverage = state['_ui_coverage']
    graph = state['_graph']

    # Update graph
    current_hash = state['current_screen_hash']
    graph.record_action(current_hash, action_id)

    # Update memories
    long_term.record_action(action_id, ...)
    short_term.record_iteration(...)
    ui_coverage.record_interaction(action_id, ...)

    # Capture next state (for transition tracking)
    # Note: Next observe() will capture full state

    return {"iteration": state['iteration'] + 1}


def check_termination(state: AgentState) -> str:
    """
    Check termination criteria and route workflow.

    ### Termination Criteria:
    - Timeout exceeded

    Returns:
        "observe" to continue, "END" to terminate
    """
    elapsed = time.time() - state['start_time']

    if elapsed >= state['timeout']:
        return "END"

    return "observe"
```

---

### 3. Action Mapping: Coordinates → ScreenItem → ItemAction

**Critical Clarification**: The mapping process is:

1. **LLM provides** → Coordinates (x, y) in optimized image space + action type (click, type, etc.)
2. **Convert** → Coordinates to device space using scale factors
3. **Locate ScreenItem** → Find which `ScreenItem` contains device coordinates (using `item.view['bounds']`)
4. **Select ItemAction** → Choose appropriate action from `item.actions` list based on action type
5. **Generate action_id** → Use `action.id` from the selected ItemAction

**File: `core/action_mapper.py`**

```python
"""
Action mapping from LLM coordinates to ScreenDescription actions.

Maps visual coordinates from LLM analysis to executable actions in the
ScreenDescription model, handling coordinate conversion and action selection.
"""

def map_coordinates_to_action(
    llm_coords: tuple[int, int],
    action_type: str,
    screen_description: ScreenDescription,
    optimized_dims: tuple[int, int],
    device_dims: tuple[int, int]
) -> int:
    """
    Map LLM coordinates and action type to ItemAction ID.

    ### Architectural Decisions:
    - Converts coordinates from optimized to device space
    - Uses bounding box intersection for element identification
    - Selects action from ScreenItem.actions based on type
    - Falls back to first action if specific type not found
    - Returns action.id for tracking

    ### Mapping Steps:
    1. Convert coordinates: optimized → device space
    2. Find ScreenItem: device coords → item.view['bounds']
    3. Select ItemAction: item.actions filtered by action_type
    4. Return action.id for tracking

    Args:
        llm_coords: Coordinates in optimized image space
        action_type: Requested action type (click, long_click, type, etc.)
        screen_description: Parsed UI with items and actions
        optimized_dims: Optimized screenshot dimensions
        device_dims: Device screen dimensions

    Returns:
        ItemAction.id for the selected action

    Raises:
        ValueError: If no element found at coordinates or no action available
    """
    llm_x, llm_y = llm_coords

    # Step 1: Convert coordinates
    scale_x = device_dims[0] / optimized_dims[0]
    scale_y = device_dims[1] / optimized_dims[1]
    device_x = int(llm_x * scale_x)
    device_y = int(llm_y * scale_y)

    # Validate bounds
    if not (0 <= device_x < device_dims[0] and 0 <= device_y < device_dims[1]):
        logger.warning(f"Converted coords out of bounds: ({device_x}, {device_y})")
        device_x = max(0, min(device_x, device_dims[0] - 1))
        device_y = max(0, min(device_y, device_dims[1] - 1))

    # Step 2: Find ScreenItem containing coordinates
    containing_items = []
    for item in screen_description.items:
        bounds = item.view.get('bounds')
        if not bounds or not isinstance(bounds, list) or len(bounds) != 2:
            continue

        x1, y1 = bounds[0]
        x2, y2 = bounds[1]

        if x1 <= device_x <= x2 and y1 <= device_y <= y2:
            area = (x2 - x1) * (y2 - y1)
            containing_items.append((item, area))

    if not containing_items:
        raise ValueError(f"No element found at coordinates ({device_x}, {device_y})")

    # Choose smallest containing element (most specific)
    target_item, _ = min(containing_items, key=lambda x: x[1])

    # Step 3: Select ItemAction from target_item.actions
    if not target_item.actions:
        raise ValueError(f"Element has no actions: {target_item.base_description}")

    # Filter by action type
    matching_actions = [
        action for action in target_item.actions
        if action.action_type == action_type
    ]

    # Fallback to first action if no match
    selected_action = matching_actions[0] if matching_actions else target_item.actions[0]

    # Step 4: Return action.id
    logger.info(f"Mapped coords ({llm_x},{llm_y}) → action_id={selected_action.id} "
                f"({selected_action.text})")

    return selected_action.id
```

**Action ID Stability Note**:
- Action IDs (`action.id`) are generated sequentially during parsing (using Counter)
- Same element in same screen will have consistent action IDs across visits
- IDs are stable within a single parsing session
- For coverage tracking across sessions, we use ScreenItem properties (resource-id, bounds hash)

---

### 4. RVAgent (core/rv_agent.py)

**Structure:**
```python
"""
Autonomous Android testing agent with vision-guided exploration.

Implements an LLM-based agent that explores Android applications using
multimodal understanding, static analysis guidance, and graph-based
state tracking for systematic coverage.
"""

class RVAgent:
    """
    Main agent class coordinating autonomous Android application exploration.

    ### Architectural Decisions:
    - Uses LangGraph for workflow orchestration
    - Implements structural hashing for state identification
    - Integrates optional static analysis for MOP guidance
    - Delegates exploration strategy to pluggable components
    - Manages multiple memory systems for context tracking

    ### Role in the System:
    - Coordinates LLM-based exploration with device interaction
    - Maintains exploration graph with state coverage tracking
    - Provides strategy-guided action prioritization
    - Collects metrics for evaluation and analysis

    ### Key Features:
    - Multimodal LLM with vision capabilities
    - Structural state hashing (not activity-based)
    - DFS/BFS exploration strategies
    - Optional MOP-guided prioritization
    - Standalone operation without external dependencies
    """

    def __init__(self, config: RVAgentConfig,
                 static_data: Optional[StaticAnalysisData]):
        # Device interaction
        self.device = DeviceInterface(config.device_id)
        self.screenshot_optimizer = ScreenshotOptimizer()
        self.parser = UIAutomator2Parser(DefaultTextVisitor)

        # Memory systems
        self.long_term = LongTermMemory(static_data)
        self.short_term = ShortTermMemory()
        self.ui_coverage = UICoverageTracker()

        # Dynamic exploration graph (structural hash)
        self.dynamic_graph = DynamicStateGraph()

        # Pluggable strategy (DFS or BFS)
        if config.strategy == "dfs":
            self.strategy = DFSStrategy(self.dynamic_graph, static_data)
        elif config.strategy == "bfs":
            self.strategy = BFSStrategy(self.dynamic_graph, static_data)
        else:
            raise ValueError(f"Unknown strategy: {config.strategy}")

        # LLM with tools
        self.tools = create_android_tools()
        self.llm = ChatOllama(
            model=config.llm_model,
            temperature=config.llm_temperature,
            top_p=config.llm_top_p,
            top_k=config.llm_top_k
        ).bind_tools(self.tools)

        # LangGraph workflow
        self.graph = self._build_agent_graph()

    def _build_agent_graph(self):
        """Build LangGraph workflow with nodes and edges."""
        from langgraph.graph import StateGraph, END
        from langgraph.prebuilt import ToolNode, tools_condition

        # Create graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("init_app", init_app)
        workflow.add_node("observe", observe)
        workflow.add_node("assistant", self._create_assistant_node())
        workflow.add_node("tools", ToolNode(self.tools))
        workflow.add_node("update_memories", update_memories)

        # Add edges
        workflow.set_entry_point("init_app")
        workflow.add_edge("init_app", "observe")
        workflow.add_edge("observe", "assistant")
        workflow.add_conditional_edges("assistant", tools_condition)
        workflow.add_edge("tools", "update_memories")
        workflow.add_conditional_edges("update_memories", check_termination)

        # Compile with checkpointer
        from langgraph.checkpoint.sqlite import SqliteSaver
        memory = SqliteSaver.from_conn_string(":memory:")

        return workflow.compile(checkpointer=memory)

    def run(self) -> dict:
        """
        Execute agent until timeout.

        Returns:
            Metrics dictionary with exploration results
        """
        # Initial state (inject dependencies)
        initial_state = {
            "messages": [],
            "iteration": 0,
            "should_continue": True,
            "start_time": time.time(),
            "timeout": self.config.timeout,
            "device_dimensions": self.config.device_dimensions,
            "optimized_dimensions": self.config.optimized_dimensions,
            "strategy_name": self.config.strategy,
            # Injected dependencies
            "_device": self.device,
            "_parser": self.parser,
            "_static_data": self.static_data,
            "_strategy": self.strategy,
            "_long_term": self.long_term,
            "_short_term": self.short_term,
            "_ui_coverage": self.ui_coverage,
            "_graph": self.dynamic_graph
        }

        # Run workflow
        final_state = self.graph.invoke(initial_state)

        # Collect metrics
        return self._collect_metrics()

    def _collect_metrics(self) -> dict:
        """Collect comprehensive exploration metrics."""
        graph = self.dynamic_graph

        # Per-screen metrics
        screen_metrics = {
            hash: {
                "activity": node.activity,
                "visit_count": node.visit_count,
                "actions_executed": len(node.executed_actions),
                "total_actions": node.total_actions,
                "coverage_%": node.get_coverage() * 100
            }
            for hash, node in graph.states.items()
        }

        return {
            "execution_time_s": time.time() - self.start_time,
            "total_iterations": self.iteration,
            "unique_screens": len(graph.states),
            "unique_activities": len(set(n.activity for n in graph.states.values())),
            "transitions": len(graph.transitions),
            "screen_metrics": screen_metrics,
            "avg_screen_coverage_%": self._compute_avg_coverage(screen_metrics)
            # NOTE: MOP coverage computed via external rv-coverage module
        }
```

---

## 🔑 Critical Architectural Decisions

### 1. Structural Hash (Not Activity-Based!)

**Rationale:** Same activity can display different UI structures (e.g., normal screen vs expanded combobox).

```python
def compute_screen_hash(xml_hierarchy: str) -> str:
    """
    Compute structural hash from XML hierarchy for state identification.

    ### Architectural Decisions:
    - Uses structural content, not volatile attributes
    - Removes bounds, timestamps, and instance-specific data
    - Enables distinction of UI variants within same activity
    - Compatible with DroidBot-style state identification

    ### Canonicalization Rules:
    KEEP attributes:
    - class: UI element type (essential for structure)
    - resource-id: stable identifier
    - package: application context
    - enabled, clickable, checkable, scrollable: UI capabilities
    - selected, checked: semantic state

    REMOVE attributes:
    - bounds: positional (volatile across devices/orientations)
    - index: order-dependent (volatile)
    - text, content-desc: content (can be dynamic)
    - NAF, instance: metadata (not structural)

    Args:
        xml_hierarchy: Raw UIAutomator XML dump

    Returns:
        12-character hex hash of canonical structure
    """
    import xml.etree.ElementTree as ET
    import hashlib

    root = ET.fromstring(xml_hierarchy)

    # Remove volatile attributes
    for elem in root.iter():
        for attr in ['bounds', 'index', 'text', 'content-desc',
                     'NAF', 'instance', 'focusable', 'focused',
                     'long-clickable', 'password']:
            elem.attrib.pop(attr, None)

    # Serialize to canonical string
    canonical = ET.tostring(root, encoding='unicode')

    # Compute hash
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]
```

**Note on Granularity**: This hash preserves semantic state (checked, selected) but removes content (text). This means:
- ✅ Checkbox unchecked vs checked = different states
- ✅ Spinner collapsed vs expanded = different states (different children)
- ❌ TextField empty vs filled = same state (text removed)
- ❌ Counter "3 items" vs "5 items" = same state (text removed)

This is acceptable for our use case since we focus on **structural coverage**, not content coverage.

---

### 2. Dynamic State Graph

**Design:**
```python
class DynamicStateGraph:
    """
    Graph-based state tracking using structural hashes.

    ### Architectural Decisions:
    - Nodes represent unique UI structures (screen_hash)
    - Maintains activity reference for context
    - Tracks action execution per screen
    - Records total actions on first visit

    ### Role in the System:
    - Provides state-based exploration tracking
    - Enables coverage computation per screen
    - Supports strategy guidance queries
    - Records transition history for analysis
    """

    states: Dict[str, ScreenNode]
    transitions: List[Transition]

    class ScreenNode:
        """
        Node representing a unique UI structure state.

        ### Architectural Decisions:
        - Identified by structural hash, not activity name
        - Captures total actions count on first visit
        - Maintains set of executed action IDs
        - Computes coverage as ratio of executed/total
        """
        screen_hash: str
        activity: str              # Reference for context
        visit_count: int
        total_actions: int         # Discovered on first visit
        executed_actions: Set[int] # action.id from ItemAction

        def get_coverage(self) -> float:
            """Compute action coverage percentage for this screen."""
            return len(self.executed_actions) / max(1, self.total_actions)
```

---

### 3. Strategy Pattern (Soft Guidance)

**Design Philosophy:** Strategy suggests, LLM decides autonomously.

Both DFS and BFS strategies implemented:

```python
class DFSStrategy:
    """
    Depth-first exploration strategy with MOP prioritization.

    ### Architectural Decisions:
    - Provides guidance, does not force actions
    - Prioritizes untested actions with MOP markers
    - Implements stack-based depth-first logic
    - Computes coverage context for informed decisions

    ### Role in the System:
    - Generates priority rankings for system prompt
    - Determines exploration focus (deepen vs backtrack)
    - Queries graph state for guidance computation
    - Formats suggestions for LLM consumption
    """

    def get_guidance(self, current_hash: str,
                    screen_desc: ScreenDescription) -> dict:
        """
        Compute exploration guidance for current state.

        Returns guidance dictionary for system prompt integration:
        - priority_actions: Ranked list of suggested actions
        - exploration_focus: Current strategy directive
        - coverage_current: Coverage percentage for context
        """
        node = self.graph.states.get(current_hash)

        # Identify untested actions
        all_actions = screen_desc.get_all_actions()
        untested = [
            action for action in all_actions
            if action.id not in node.executed_actions
        ]

        # Sort by MOP priority: [DM] > [M] > no marker
        priority = sorted(untested,
                         key=lambda a: self._get_mop_priority(a),
                         reverse=True)

        # DFS logic: deepen if untested exist, else backtrack
        if priority:
            focus = f"deepen (explore {len(priority)} untested)"
        else:
            focus = "backtrack (all tested, try back/navigation)"

        return {
            "priority_actions": [self._format_action(a) for a in priority[:5]],
            "exploration_focus": focus,
            "coverage_current": f"{node.get_coverage():.1f}%"
        }

    def _get_mop_priority(self, action: ItemAction) -> int:
        """Compute priority score for action."""
        if action.directly_reaches_mop:
            return 3  # [DM]
        elif action.reaches_mop:
            return 2  # [M]
        else:
            return 1  # no marker


class BFSStrategy:
    """
    Breadth-first exploration strategy with MOP prioritization.

    ### Architectural Decisions:
    - Explores level-by-level (all actions in current screen first)
    - Maintains queue of discovered but not fully explored screens
    - Prioritizes MOP-marked actions within each level
    - Moves to next screen only after current exhausted

    ### Role in the System:
    - Generates priority rankings for system prompt
    - Determines when to transition to next screen
    - Tracks exploration queue for breadth-first traversal
    - Formats suggestions for LLM consumption
    """

    def __init__(self, graph: DynamicStateGraph, static_data: Optional[StaticAnalysisData]):
        self.graph = graph
        self.static_data = static_data
        self.screen_queue = deque()  # Queue of screen hashes to explore

    def get_guidance(self, current_hash: str,
                    screen_desc: ScreenDescription) -> dict:
        """
        Compute BFS guidance for current state.

        BFS explores all actions in current screen before moving to next.
        Prioritizes MOP-marked actions within current level.
        """
        node = self.graph.states.get(current_hash)

        # Identify untested actions in current screen
        all_actions = screen_desc.get_all_actions()
        untested = [
            action for action in all_actions
            if action.id not in node.executed_actions
        ]

        # Sort by MOP priority
        priority = sorted(untested,
                         key=lambda a: self._get_mop_priority(a),
                         reverse=True)

        # BFS logic: exhaust current screen, then move to queued screen
        if priority:
            focus = f"breadth (explore {len(priority)} remaining in current screen)"
        else:
            if self.screen_queue:
                next_hash = self.screen_queue[0]
                focus = f"navigate to next queued screen ({next_hash[:6]}...)"
            else:
                focus = "exploration complete (no queued screens)"

        return {
            "priority_actions": [self._format_action(a) for a in priority[:5]],
            "exploration_focus": focus,
            "coverage_current": f"{node.get_coverage():.1f}%",
            "queue_size": len(self.screen_queue)
        }

    def record_transition(self, from_hash: str, to_hash: str):
        """Record transition and update screen queue for BFS."""
        # If discovered new screen, add to queue
        if to_hash not in self.graph.states:
            self.screen_queue.append(to_hash)
```

---

### 4. Android Tools (Return Structured Data)

**Approach:** Tools return structured data, `update_memories` node handles state updates.

```python
def create_android_tools() -> list[Tool]:
    """
    Create Android interaction tools that return structured data.

    ### Architectural Decisions:
    - Tools do NOT access AgentState directly
    - Return structured data for update_memories node
    - Execute device actions via DeviceInterface
    - Provide clear success/failure status

    Returns:
        List of LangChain Tool instances for LLM binding
    """

    @tool
    def android_click(element_description: str, x: int, y: int) -> dict:
        """
        Click on UI element at specified coordinates.

        Coordinates should be provided in the OPTIMIZED image space
        (e.g., 728x1288). They will be converted to device coordinates
        automatically by the update_memories node.

        Args:
            element_description: Human-readable element description
            x: X coordinate in optimized image
            y: Y coordinate in optimized image

        Returns:
            Structured result: {"success": bool, "llm_coords": tuple,
                               "description": str, "action_type": str}
        """
        # Note: DeviceInterface access needs to be passed via closure
        # or global context (implementation detail)
        success = device.click(x, y)  # Simplified - actual impl needs proper device access

        return {
            "success": success,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "click"
        }

    @tool
    def android_type_text(element_description: str, x: int, y: int, text: str) -> dict:
        """
        Type text into element at specified coordinates.

        Args:
            element_description: Human-readable element description
            x: X coordinate in optimized image
            y: Y coordinate in optimized image
            text: Text to type

        Returns:
            Structured result
        """
        success = device.click(x, y) and device.type_text(text)

        return {
            "success": success,
            "llm_coords": (x, y),
            "description": element_description,
            "action_type": "set_text",
            "text": text
        }

    @tool
    def android_back() -> dict:
        """Press back button."""
        success = device.press_back()
        return {
            "success": success,
            "action_type": "back"
        }

    @tool
    def android_home() -> dict:
        """Press home button."""
        success = device.press_home()
        return {
            "success": success,
            "action_type": "home"
        }

    return [android_click, android_type_text, android_back, android_home]
```

---

## 🎨 Static Analysis Integration (Optional)

### With static_data Available

```python
# ScreenDescription includes [M]/[DM] via parser
screen_desc = parser.parse_screen(xml, static_data)

for item in screen_desc.items:
    for action in item.actions:
        if action.directly_reaches_mop:
            # Mark in display (used in system prompt)
            item.complement['priority_marker'] = "[DM]"
        elif action.reaches_mop:
            item.complement['priority_marker'] = "[M]"
```

### Without static_data

- Parser operates normally (no markers)
- Strategy uses only coverage and visit_count
- System remains **fully functional** without static analysis

---

## 📊 Metrics Collection

```python
def _collect_metrics(self) -> dict:
    """
    Collect comprehensive exploration metrics.

    ### Architectural Decisions:
    - Organizes metrics by screen, not activity
    - Computes coverage from first-visit total_actions
    - Excludes MOP coverage (requires external integration)
    - Provides detailed per-screen statistics

    Returns:
        Metrics dictionary for analysis and comparison
    """
    graph = self.dynamic_graph

    # Per-screen metrics
    screen_metrics = {
        hash: {
            "activity": node.activity,
            "visit_count": node.visit_count,
            "actions_executed": len(node.executed_actions),
            "total_actions": node.total_actions,
            "coverage_%": node.get_coverage() * 100
        }
        for hash, node in graph.states.items()
    }

    return {
        "execution_time_s": time.time() - start_time,
        "total_iterations": iteration,
        "unique_screens": len(graph.states),
        "unique_activities": len(set(n.activity for n in graph.states.values())),
        "transitions": len(graph.transitions),
        "screen_metrics": screen_metrics,
        "avg_screen_coverage_%": compute_avg(screen_metrics)
        # NOTE: MOP coverage computed via external rv-coverage module
    }
```

---

## 💬 System Prompt Template

```
You are an autonomous Android testing agent for security analysis.

CURRENT SCREEN: {screen_hash} (Activity: {activity})
VISIT #{visit_count} | Coverage: {coverage}%

STRATEGY: {strategy_name} (DFS/BFS)
FOCUS: {exploration_focus}

UI ACTIONS (priority order):
{formatted_actions_with_markers}

Priority Markers:
- [DM] = Directly reaches monitored operation → HIGHEST PRIORITY
- [M] = Reaches monitored operation → HIGH PRIORITY
- (no marker) = Regular action

GUIDANCE:
{strategy_guidance}

RECENT ACTIONS:
{short_term_memory}

INSTRUCTIONS:
1. Analyze the current screen carefully
2. Prioritize actions with [DM] or [M] markers
3. Consider the strategy guidance ({exploration_focus})
4. Use android_click(description, x, y) to interact
5. Coordinates should be in the visible screenshot space

Time remaining: {remaining}s
```

---

## 🚀 Standalone Usage

```python
from rv_agent import RVAgent, RVAgentConfig
from rv_android_core.domain.static import StaticAnalysisData

# Configuration
config = RVAgentConfig(
    timeout=300,
    device_id="emulator-5554",
    device_dimensions=(1080, 1920),
    optimized_dimensions=(728, 1288),
    package_name="br.unb.cic.cryptoapp",
    llm_model="qwen2.5-vl:7b",
    llm_temperature=0.25,
    llm_top_p=0.8,
    llm_top_k=50,
    strategy="dfs"  # or "bfs"
)

# Execute (static_data optional)
agent = RVAgent(config, static_data=None)
metrics = agent.run()

# Results
print(f"Unique Screens: {metrics['unique_screens']}")
print(f"Avg Coverage: {metrics['avg_screen_coverage_%']:.1f}%")
print(f"Iterations: {metrics['total_iterations']}")
```

---

## 📝 Implementation Sequence

### Phase 1: Foundations
1. `llm/graph/state.py` - AgentState TypedDict with documentation
2. `strategies/base_strategy.py` - Strategy interface
3. Move `llm/tmp_001.py` → `backup/2025-01-31_pre-rvagent/`

### Phase 2: Graph Infrastructure
4. `core/dynamic_state_graph.py` - Structural hash graph
5. `core/action_mapper.py` - Coordinate → Action mapping with validation

### Phase 3: Strategies
6. `strategies/dfs_strategy.py` - Depth-first guidance
7. `strategies/bfs_strategy.py` - Breadth-first guidance

### Phase 4: Workflow
8. `llm/graph/nodes.py` - LangGraph workflow implementation
9. `llm/tools/android_tools.py` - Tools return structured data

### Phase 5: Integration
10. `core/rv_agent.py` - Main agent class updates
11. `config/agent_config.py` - Configuration updates

### Phase 6: Testing
12. Unit tests for critical components (hash, mapper, strategies)
13. Integration test with cryptoapp
14. Validation against manual exploration

---

## ✅ Quality Assurance Checklist

### Code Quality
- [ ] All code in English
- [ ] Comments follow EventBus/TaskExecutor template
- [ ] Module docstrings with brief overview
- [ ] Class docstrings with 3-section format
- [ ] Method docstrings for complex logic
- [ ] No promotional language
- [ ] No bias terms
- [ ] No migration history references

### Architecture
- [ ] Structural hashing (not activity-based)
- [ ] Coordinate conversion with validation
- [ ] ScreenDescription/ItemAction as foundation
- [ ] Static analysis optional
- [ ] Tools return structured data (no state access)
- [ ] update_memories node handles all state updates
- [ ] Soft guidance strategies (DFS + BFS)
- [ ] Clean separation of concerns

### Termination
- [ ] Only timeout criterion (no plateau detection)
- [ ] Proper timeout checking in check_termination node

### Legacy Handling
- [ ] Old files moved to backup folder
- [ ] No compatibility adapters
- [ ] Complete refactoring, not incremental
- [ ] References updated throughout codebase

---

## 🎯 Success Criteria

### Functional Requirements
- ✅ Autonomous exploration until timeout
- ✅ Structural state identification
- ✅ DFS and BFS strategy support
- ✅ [DM]/[M] prioritization (when available)
- ✅ Coordinate conversion with validation
- ✅ Memory system integration
- ✅ Metrics collection
- ✅ Action mapping: coords → ScreenItem → ItemAction

### Performance Targets
- Avg screen coverage comparable to or better than baselines
- Unique screens discovered > activity count
- Iteration efficiency (actions/minute)
- Memory usage acceptable
- LLM inference latency manageable

### Code Quality
- 100% English documentation
- Template adherence
- No legacy artifacts
- Clean architecture
- Extensibility demonstrated
