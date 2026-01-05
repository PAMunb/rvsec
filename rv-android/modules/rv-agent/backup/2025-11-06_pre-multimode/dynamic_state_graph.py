"""
Graph-based state tracking using structural hashes.

Implements a dynamic graph that tracks UI states and transitions during
autonomous exploration, using structural hashing for precise state identification.
"""

import xml.etree.ElementTree as ET
import hashlib
from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Any
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


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
    try:
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
    except ET.ParseError:
        # Fallback for invalid XML
        return hashlib.sha256(xml_hierarchy.encode()).hexdigest()[:12]


@dataclass
class ScreenNode:
    """
    Node representing a unique UI structure state.

    ### Architectural Decisions:
    - Identified by structural hash, not activity name
    - Captures total actions count on first visit
    - Maintains set of executed action IDs
    - Computes coverage as ratio of executed/total

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
    executed_actions: Set[int] = field(default_factory=set)

    def get_coverage(self) -> float:
        """
        Compute action coverage percentage for this screen.

        Returns:
            Coverage ratio (0.0 to 1.0)
        """
        if self.total_actions == 0:
            return 0.0
        return len(self.executed_actions) / self.total_actions

    def record_action(self, action_id: int):
        """
        Record action execution.

        Args:
            action_id: ID of executed action
        """
        self.executed_actions.add(action_id)


@dataclass
class Transition:
    """
    Represents a state transition.

    ### Architectural Decisions:
    - Records action that triggered transition
    - Includes timestamp for temporal analysis
    - Stores both source and destination hashes

    ### Role in the System:
    - Enables transition graph reconstruction
    - Supports temporal analysis of exploration
    - Provides audit trail for debugging
    """

    from_hash: str
    to_hash: str
    action_id: int
    timestamp: float


class DynamicStateGraph:
    """
    Graph-based state tracking using structural hashes.

    ### Architectural Decisions:
    - Nodes represent unique UI structures (screen_hash)
    - Maintains activity reference for context
    - Tracks action execution per screen
    - Records total actions on first visit
    - Stores transition history for analysis

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
        action_id: int,
        next_hash: Optional[str] = None,
        timestamp: Optional[float] = None
    ):
        """
        Record action execution and optional transition.

        Args:
            screen_hash: Hash of current screen
            action_id: ID of executed action
            next_hash: Hash of resulting screen (if known)
            timestamp: Transition timestamp (defaults to current time)
        """
        import time

        if screen_hash in self.states:
            self.states[screen_hash].record_action(action_id)

        if next_hash is not None:
            self.transitions.append(
                Transition(
                    from_hash=screen_hash,
                    to_hash=next_hash,
                    action_id=action_id,
                    timestamp=timestamp or time.time()
                )
            )

    def get_untested_actions(
        self,
        screen_hash: str,
        all_actions: List[Any]
    ) -> List[Any]:
        """
        Get actions not yet executed on this screen.

        Args:
            screen_hash: Hash of screen
            all_actions: All available actions from ScreenDescription

        Returns:
            List of untested actions
        """
        if screen_hash not in self.states:
            return all_actions

        node = self.states[screen_hash]
        return [
            action for action in all_actions
            if action.id not in node.executed_actions
        ]

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
