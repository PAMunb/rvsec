"""
Graph-based state tracking using structural hashes and coordinate-based action identification.

Implements a dynamic graph that tracks UI states and transitions during autonomous exploration,
using structural hashing for state identification and coordinate-based action tracking to handle
non-deterministic action IDs across parsing sessions.
"""

import xml.etree.ElementTree as ET
import hashlib
import json
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Any, Tuple
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


def compute_screen_hash_from_description(screen_desc: ScreenDescription) -> str:
    """
    Compute structural hash from ScreenDescription for state identification.

    ### Architectural Decisions:
    - Uses ONLY structural attributes, ignoring volatile data
    - Sorts elements by resource-id for deterministic ordering
    - Focuses on UI capabilities (clickable, scrollable) not content
    - Ignores text, content-desc, checked, selected (dynamic data)

    ### Canonicalization Rules:
    KEEP attributes:
    - class: UI element type (essential for structure)
    - resource-id: stable identifier
    - package: application context
    - clickable, scrollable, checkable: UI capabilities
    - enabled: availability state
    - long-clickable, editable: interaction capabilities

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
    import logging
    logger = logging.getLogger(__name__)

    # Build structural representation
    structural_items = []

    for item in screen_desc.items:
        view = item.view

        # Extract ONLY structural attributes
        structural_view = {
            'class': view.get('class', ''),
            'resource-id': view.get('resource-id', ''),
            'package': view.get('package', ''),
            'clickable': view.get('clickable', False),
            'scrollable': view.get('scrollable', False),
            'checkable': view.get('checkable', False),
            'enabled': view.get('enabled', True),
            'long-clickable': view.get('long-clickable', False),
            'editable': view.get('editable', False)
        }

        structural_items.append(structural_view)

    # Sort by resource-id for deterministic ordering
    # Elements without resource-id go to end (secondary sort by class)
    structural_items.sort(key=lambda x: (x['resource-id'] or 'zzz', x['class']))

    # Create canonical JSON representation
    canonical = json.dumps(
        {
            'activity': screen_desc.activity,
            'items': structural_items
        },
        sort_keys=True,
        separators=(',', ':')  # Compact format
    )

    # Compute hash
    screen_hash = hashlib.sha256(canonical.encode()).hexdigest()[:12]

    logger.debug(f"Computed structural hash: {screen_hash} for {len(structural_items)} items")

    # DEBUG: Log canonical representation for ALL screens (debugging enabled)
    if True:  # Always log for debugging
        import os
        debug_dir = '/tmp/screendesc_debug'
        os.makedirs(debug_dir, exist_ok=True)

        canonical_file = f'{debug_dir}/{screen_hash}_canonical.json'
        with open(canonical_file, 'w') as f:
            f.write(canonical)

        logger.info(f"🔍 SCREENDESC DEBUG: Saved CryptoApp canonical JSON")
        logger.info(f"   Hash: {screen_hash}")
        logger.info(f"   Activity: {screen_desc.activity}")
        logger.info(f"   Items: {len(structural_items)}")
        logger.info(f"   File: {canonical_file}")

    return screen_hash


@dataclass
class ScreenNode:
    """
    Node representing a unique UI structure state with coordinate-based action tracking.

    ### Architectural Decisions:
    - Identified by structural hash, not activity name
    - Captures total actions count on first visit
    - Tracks executed actions by coordinates (not IDs) for stability across parsing sessions
    - Tracks execution COUNT per action for continuous exploration prioritization
    - Computes coverage as ratio of executed/total actions

    ### Key Design: Coordinate-Based Tracking
    - Action IDs are non-deterministic across UIAutomator dumps
    - Same UI element can receive different IDs on different parses
    - Coordinates are stable identifiers for the same screen element
    - Solves the "repeated crash action" problem caused by ID instability

    ### Continuous Exploration Design:
    - Tracks how many times each action was executed (not just boolean)
    - Enables prioritizing least-executed actions when all have been tried
    - Algorithm continues until timeout, never stops when "exhausted"

    ### Role in the System:
    - Represents unique UI state in exploration graph
    - Tracks action execution for coverage computation
    - Provides context for strategy decision-making
    - Records activity name for interpretability
    """

    screen_hash: str
    activity: str
    visit_count: int = 0
    total_actions: int = 0
    executed_actions: Set[Tuple[Tuple[int, int], str]] = field(default_factory=set)
    action_execution_counts: Dict[Tuple[Tuple[int, int], str], int] = field(default_factory=dict)

    def get_coverage(self) -> float:
        """
        Compute action coverage percentage for this screen.

        Returns:
            Coverage ratio (0.0 to 1.0)
        """
        if self.total_actions == 0:
            return 0.0
        return len(self.executed_actions) / self.total_actions

    def record_action(self, action_signature: Tuple[Tuple[int, int], str]):
        """
        Record action execution by signature (coordinates + action type).
        Increments execution count for continuous exploration prioritization.

        Args:
            action_signature: ((x, y), action_type) tuple identifying the action
        """
        self.executed_actions.add(action_signature)
        self.action_execution_counts[action_signature] = self.action_execution_counts.get(action_signature, 0) + 1

    def get_action_execution_count(self, action_signature: Tuple[Tuple[int, int], str]) -> int:
        """
        Get execution count for an action signature.

        Args:
            action_signature: ((x, y), action_type) tuple to check

        Returns:
            Number of times action was executed (0 if never executed)
        """
        return self.action_execution_counts.get(action_signature, 0)

    def is_action_executed(self, action_signature: Tuple[Tuple[int, int], str]) -> bool:
        """
        Check if action with given signature was already executed.

        Args:
            action_signature: ((x, y), action_type) tuple to check

        Returns:
            True if action was executed, False otherwise
        """
        return action_signature in self.executed_actions


@dataclass
class Transition:
    """
    Represents a state transition with complete action sequence.

    ### Architectural Decisions:
    - Records all actions executed between states
    - Captures multi-step workflows (e.g., form filling)
    - Includes timestamp for temporal analysis
    - Stores both source and destination hashes

    ### Role in the System:
    - Enables transition graph reconstruction
    - Supports temporal analysis of exploration
    - Provides audit trail for debugging
    - Preserves complete workflow sequences
    """

    from_hash: str
    to_hash: str
    action_sequence: List[Dict[str, Any]]
    timestamp: float


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

    def __init__(self):
        self.states: Dict[str, ScreenNode] = {}
        self.transitions: List[Transition] = []
        self.current_trace: List[Dict[str, Any]] = []

    def get_or_create_state(
        self,
        screen_hash: str,
        activity: str,
        screen_desc: ScreenDescription
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

        # First visit - count total actions
        total_actions = len(screen_desc.get_all_actions())

        node = ScreenNode(
            screen_hash=screen_hash,
            activity=activity,
            visit_count=1,
            total_actions=total_actions
        )

        self.states[screen_hash] = node
        return node

    def record_action(
        self,
        screen_hash: str,
        action_signature: Tuple[Tuple[int, int], str]
    ):
        """
        Record action execution on a screen by signature (coordinates + type).

        Args:
            screen_hash: Hash of current screen
            action_signature: ((x, y), action_type) tuple identifying the action
        """
        import logging
        logger = logging.getLogger(__name__)

        if screen_hash in self.states:
            node = self.states[screen_hash]
            logger.info(f"🔒 GRAPH: Recording action signature={action_signature} on state {screen_hash[:8]}")
            logger.info(f"   BEFORE: executed_actions = {sorted(node.executed_actions)}")
            self.states[screen_hash].record_action(action_signature)
            logger.info(f"   AFTER:  executed_actions = {sorted(node.executed_actions)}")
        else:
            logger.warning(f"⚠️  GRAPH: Cannot record action signature={action_signature} - state {screen_hash[:8]} not found!")
            logger.warning(f"   Available states: {[h[:8] for h in self.states.keys()]}")

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
        self,
        from_hash: str,
        to_hash: str,
        timestamp: Optional[float] = None
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
                timestamp=timestamp or time.time()
            )
        )

        # Reset trace for next transition
        self.current_trace = []

    def get_untested_actions(
        self,
        screen_hash: str,
        all_actions: List[Any]
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
        self,
        screen_hash: str,
        action_signature: Tuple[Tuple[int, int], str]
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
        return {
            hash: node.get_coverage() * 100
            for hash, node in self.states.items()
        }

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
        """
        Generate comprehensive transition graph report.

        Includes complete action sequences for each transition,
        enabling workflow analysis and debugging.

        Returns:
            Dictionary with states and transitions with full sequences
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
                    "coverage": node.get_coverage() * 100
                }
                for node in self.states.values()
            ],
            "transitions": [
                {
                    "from": t.from_hash,
                    "to": t.to_hash,
                    "action_count": len(t.action_sequence),
                    "actions": t.action_sequence,
                    "timestamp": t.timestamp
                }
                for t in self.transitions
            ]
        }
