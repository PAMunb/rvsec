"""
Graph-based state tracking using structural hashes and coordinate-based action identification.

Implement a dynamic graph that tracks UI states and transitions during autonomous
exploration, using structural hashing for state identification and coordinate-based
action tracking to handle non-deterministic action IDs across parsing sessions.

### Architectural Decisions:

- Structural hashing: uses UI capabilities (clickable, scrollable) not content (text)
  to identify states, ignoring volatile attributes
- Coordinate-based tracking: actions tracked by (x, y) coordinates instead of volatile
  sequential IDs to ensure stable matching across parsing sessions
- 12-char hex hash: SHA-256 truncated to 12 chars for readability in logs

### Role in the System:

- Central state tracking for RVAgent exploration
- Used by RVAgentStrategy for action selection and coverage computation
- Updated by execute_node and learn_node during workflow execution

### Integration Points:

- Input: ScreenDescription from UI parsing, action signatures from strategy
- Output: ScreenNode with coverage data, transition history, coverage reports
- Dependencies: ScreenNode and Transition from rv_agent.domain.screen_node
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

from rv_agent import tracking as track
from rv_agent.domain.screen_node import ScreenNode, Transition

logger = logging.getLogger(__name__)


def compute_screen_hash_from_description(screen_desc: ScreenDescription) -> str:
    """
    Compute structural hash from ScreenDescription for state identification.

    ### Architectural Decisions:
    - Uses ONLY structural attributes, ignoring volatile data
    - Sorts elements by resource_id for deterministic ordering
    - Focuses on UI capabilities (clickable, scrollable) not content
    - Ignores text, content-desc, checked, selected (dynamic data)

    ### Canonicalization Rules:
    KEEP attributes:
    - class: UI element type (essential for structure)
    - resource_id: stable identifier (underscored, matching UIAutomator2 parser)
    - package: application context
    - clickable, scrollable, checkable: UI capabilities
    - enabled: availability state
    - long_clickable, editable: interaction capabilities (underscored, matching UIAutomator2 parser)

    IGNORE attributes:
    - text: content (dynamic)
    - content-desc: description (can be dynamic)
    - checked, selected: state (volatile)
    - bounds: position (device-specific)
    - focused, focusable: transient states

    Args:
        screen_desc: Parsed screen description from UIAutomator

    Returns:
        12-character hex hash of structural representation
    """
    # Build structural representation
    structural_items = []

    for item in screen_desc.items:
        view = item.view

        # Extract ONLY structural attributes.
        # Keys use underscored form (resource_id, long_clickable) matching
        # the UIAutomator2 parser output in rv-screen-parser.
        structural_view = {
            "class": view.get("class", ""),
            "resource_id": view.get("resource_id", ""),
            "package": view.get("package", ""),
            "clickable": view.get("clickable", False),
            "scrollable": view.get("scrollable", False),
            "checkable": view.get("checkable", False),
            "enabled": view.get("enabled", True),
            "long_clickable": view.get("long_clickable", False),
            "editable": view.get("editable", False),
        }

        structural_items.append(structural_view)

    # Sort by resource_id for deterministic ordering
    # Elements without resource_id go to end (secondary sort by class)
    structural_items.sort(key=lambda x: (x["resource_id"] or "zzz", x["class"]))

    # Create canonical JSON representation
    canonical = json.dumps(
        {"activity": screen_desc.activity, "items": structural_items},
        sort_keys=True,
        separators=(",", ":"),  # Compact format
    )

    # Compute hash
    screen_hash = hashlib.sha256(canonical.encode()).hexdigest()[:12]

    logger.debug(
        f"Computed structural hash: {screen_hash} for {len(structural_items)} items"
    )

    return screen_hash


class DynamicStateGraph:
    """
    Graph-based state tracking using structural hashes and coordinate-based action identification.

    ### Architectural Decisions:
    - Nodes represent unique UI structures (screen_hash)
    - Actions tracked by coordinates, not volatile sequential IDs
    - Maintains activity reference for context
    - Records total actions on first visit
    - Stores transition history for analysis

    ### Key Innovation: Coordinate-Based Action Tracking
    Problem: UIAutomator dumps can return elements in different orders, causing
    sequential action IDs (1, 2, 3...) to change between visits to the same screen.
    This led to repeated execution of crash-causing actions.

    Solution: Track executed actions by their (x, y) coordinates instead of IDs.
    Coordinates remain stable for the same UI element regardless of parsing order.

    ### Role in the System:
    - Provides state-based exploration tracking
    - Enables coverage computation per screen
    - Supports strategy guidance queries
    - Records transition history for analysis
    - Distinguishes UI variants within same activity

    ### Integration Points:
    - Used by strategies to query exploration history
    - Updated by update_memories node after actions
    - Provides metrics for evaluation
    - Supports structural state identification
    """

    def __init__(self, multi_value_saturation_threshold: int = 4):
        """
        Initialize DynamicStateGraph.

        Args:
            multi_value_saturation_threshold: Saturation threshold for multi-value
                widgets (EditText, Spinner, SeekBar). Passed from RVAgentConfig to
                each ScreenNode created by get_or_create_state().
        """
        self.states: Dict[str, ScreenNode] = {}
        # Chronological list of all transitions. Audit-only — used for post-run
        # reporting and analysis. Not queried for navigation decisions; see
        # SuccessorTracker.successors for O(1) navigation lookups.
        self.transitions: List[Transition] = []
        self.current_trace: List[Dict[str, Any]] = []
        self._multi_value_threshold = multi_value_saturation_threshold

    def get_or_create_state(
        self, screen_hash: str, activity: str, screen_desc: ScreenDescription
    ) -> ScreenNode:
        """
        Get existing state node or create new one.

        ### Architectural Decisions:
        - Creates node on first visit with total_actions count
        - Increments visit_count on subsequent visits
        - Uses ScreenDescription to enumerate total actions
        - Activity stored for context, not for identification

        Args:
            screen_hash: Structural hash of UI state
            activity: Current activity name
            screen_desc: Parsed screen description

        Returns:
            ScreenNode for this state
        """
        if screen_hash in self.states:
            node = self.states[screen_hash]
            node.visit_count += 1
            return node

        # First visit - count only non-system actions (those with coordinates).
        # System actions (BACK, RESTART) have coordinates=None and inflate the
        # denominator, preventing saturation from reaching the backtrack threshold.
        total_actions = sum(
            1 for a in screen_desc.get_all_actions() if a.coordinates is not None
        )

        node = ScreenNode(
            screen_hash=screen_hash,
            activity=activity,
            visit_count=1,
            total_actions=total_actions,
            multi_value_threshold=self._multi_value_threshold,
        )

        self.states[screen_hash] = node

        # Track hash discrimination attributes for validation
        views = [item.view for item in screen_desc.items]
        resource_ids_used = sum(1 for v in views if v.get("resource_id", ""))
        long_clickables_used = sum(1 for v in views if v.get("long_clickable", False))
        track.hash_discrimination(
            iter=0,  # Iteration not available at graph level
            state_hash=screen_hash,
            elements=len(views),
            resource_ids_used=resource_ids_used,
            long_clickables_used=long_clickables_used,
        )

        return node

    def record_action(
        self,
        screen_hash: str,
        action_signature: Tuple[Tuple[int, int], str],
        widget_class: str = "",
    ):
        """
        Record action execution on a screen by signature (coordinates + type).

        Args:
            screen_hash: Hash of current screen
            action_signature: ((x, y), action_type) tuple identifying the action
            widget_class: Android widget class (e.g., "android.widget.EditText").
                Used for per-widget saturation thresholds (D8).
        """
        if screen_hash in self.states:
            node = self.states[screen_hash]
            logger.info(
                f"GRAPH: Recording action signature={action_signature} on state {screen_hash[:8]}"
            )
            logger.info(
                f"   BEFORE: executed_actions = {sorted(node.executed_actions)}"
            )
            node.record_action(action_signature, widget_class=widget_class)
            logger.info(
                f"   AFTER:  executed_actions = {sorted(node.executed_actions)}"
            )
        else:
            logger.warning(
                f"GRAPH: Cannot record action signature={action_signature} - state {screen_hash[:8]} not found!"
            )
            logger.warning(
                f"   Available states: {[h[:8] for h in self.states.keys()]}"
            )

    def record_action_to_trace(self, action: Dict[str, Any]):
        """
        Add action to current trace between states.

        Actions accumulate in trace until state transition occurs,
        then complete sequence is recorded in transition.

        Args:
            action: Action dictionary with type, coordinates, description, etc.
        """
        self.current_trace.append(action)

    def record_transition(
        self, from_hash: str, to_hash: str, timestamp: Optional[float] = None
    ):
        """
        Record state transition with complete action sequence.

        Saves accumulated trace as transition record, then resets
        trace for next transition.

        Args:
            from_hash: Hash of source screen
            to_hash: Hash of destination screen
            timestamp: Transition timestamp (defaults to current time)
        """
        import time

        self.transitions.append(
            Transition(
                from_hash=from_hash,
                to_hash=to_hash,
                action_sequence=self.current_trace.copy(),
                timestamp=timestamp or time.time(),
            )
        )

        # Reset trace for next transition
        self.current_trace = []

    def get_untested_actions(
        self, screen_hash: str, all_actions: List[Any]
    ) -> List[Any]:
        """
        Get actions not yet executed on this screen, identified by action signatures.

        Args:
            screen_hash: Hash of screen
            all_actions: All available actions from ScreenDescription

        Returns:
            List of untested actions
        """
        if screen_hash not in self.states:
            return all_actions

        node = self.states[screen_hash]
        untested = []

        for action in all_actions:
            # Get action signature (coords + type) for matching
            action_signature = action.coords_for_matching
            if action_signature not in node.executed_actions:
                untested.append(action)

        return untested

    def is_action_executed(
        self, screen_hash: str, action_signature: Tuple[Tuple[int, int], str]
    ) -> bool:
        """
        Check if action with given signature was executed on this screen.

        Args:
            screen_hash: Hash of screen
            action_signature: ((x, y), action_type) tuple to check

        Returns:
            True if action was executed, False otherwise
        """
        if screen_hash not in self.states:
            return False

        return self.states[screen_hash].is_action_executed(action_signature)

    def get_coverage_summary(self) -> Dict[str, float]:
        """
        Get coverage summary for all screens.

        Returns:
            Dictionary mapping screen_hash to coverage percentage
        """
        return {hash: node.get_coverage() * 100 for hash, node in self.states.items()}

    def get_avg_coverage(self) -> float:
        """
        Get average coverage across all screens.

        Returns:
            Average coverage percentage (0.0 to 100.0)
        """
        if not self.states:
            return 0.0

        total_coverage = sum(node.get_coverage() for node in self.states.values())
        return (total_coverage / len(self.states)) * 100

    def get_transition_graph_report(self) -> Dict[str, Any]:
        """Generate comprehensive transition graph report.

        Include complete action sequences for each transition,
        enabling workflow analysis and debugging.

        Returns:
            Dictionary with keys:
            - "total_states" (int): Number of unique UI states discovered.
            - "total_transitions" (int): Number of state transitions recorded.
            - "avg_coverage" (float): Average action coverage percentage.
            - "states" (list): Per-state details with screen_hash, activity,
                visit_count, total_actions, executed_count, coverage.
            - "transitions" (list): Per-transition details with from, to,
                action_count, actions sequence, timestamp.
        """
        return {
            "total_states": len(self.states),
            "total_transitions": len(self.transitions),
            "avg_coverage": self.get_avg_coverage(),
            "states": [
                {
                    "screen_hash": node.screen_hash,
                    "activity": node.activity,
                    "visit_count": node.visit_count,
                    "total_actions": node.total_actions,
                    "executed_count": len(node.executed_actions),
                    "coverage": node.get_coverage() * 100,
                }
                for node in self.states.values()
            ],
            "transitions": [
                {
                    "from": t.from_hash,
                    "to": t.to_hash,
                    "action_count": len(t.action_sequence),
                    "actions": t.action_sequence,
                    "timestamp": t.timestamp,
                }
                for t in self.transitions
            ],
        }

    def get_screen_line(self, screen_hash: str) -> str:
        """
        Get screen info line for prompt context.

        Format: "SCREEN: MainActivity | 40% coverage (4/10 actions) | visit #3 | 7 total screens"

        Args:
            screen_hash: Hash of current screen

        Returns:
            Formatted screen info string
        """
        total_screens = len(self.states)

        if screen_hash not in self.states:
            return f"SCREEN: unknown | 0% coverage (0/0 actions) | visit #1 | {total_screens} total screens"

        node = self.states[screen_hash]
        coverage_pct = int(node.get_coverage() * 100)
        tested = len(node.executed_actions)
        total = node.total_actions

        # Extract short activity name (last part after dot)
        activity = node.activity
        if activity and "." in activity:
            activity = activity.split(".")[-1]

        return (
            f"SCREEN: {activity} | {coverage_pct}% coverage ({tested}/{total} actions) | "
            f"visit #{node.visit_count} | {total_screens} total screens"
        )

    def get_action_execution_count(
        self, screen_hash: str, action_signature: Tuple[Tuple[int, int], str]
    ) -> int:
        """
        Get execution count for a specific action on a screen.

        Args:
            screen_hash: Hash of screen
            action_signature: ((x, y), action_type) tuple

        Returns:
            Number of times action was executed (0 if never)
        """
        if screen_hash not in self.states:
            return 0

        return self.states[screen_hash].get_action_execution_count(action_signature)
