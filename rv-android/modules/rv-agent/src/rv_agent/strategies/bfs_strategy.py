"""
Breadth-first exploration strategy with MOP prioritization.

Implements BFS exploration that exhausts each level (screen) before moving
to the next, while prioritizing MOP-marked actions within each level.
"""

from typing import Dict, List, Any, Optional
from collections import deque
from rv_agent.strategies.base_strategy import BaseStrategy
from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_android_core.domain.static import StaticAnalysisData


class BFSStrategy(BaseStrategy):
    """
    Breadth-first exploration strategy with MOP prioritization.

    ### Architectural Decisions:
    - Explores level-by-level (all actions in current screen first)
    - Maintains queue of discovered but not fully explored screens
    - Prioritizes MOP-marked actions within each level
    - Moves to next screen only after current exhausted
    - Provides queue size information for exploration awareness

    ### Role in the System:
    - Generates priority rankings for system prompt
    - Determines when to transition to next screen
    - Tracks exploration queue for breadth-first traversal
    - Formats suggestions for LLM consumption
    - Maintains explicit queue of screens to explore

    ### Integration Points:
    - Called by observe node to generate guidance
    - Queries DynamicStateGraph for state history
    - Accesses ScreenDescription for action enumeration
    - Uses StaticAnalysisData for MOP marker prioritization
    - Updates queue when new screens discovered
    """

    def __init__(
        self,
        graph: DynamicStateGraph,
        static_data: Optional[StaticAnalysisData] = None
    ):
        """
        Initialize BFS strategy.

        Args:
            graph: Dynamic state graph for history tracking
            static_data: Optional static analysis data for MOP markers
        """
        self.graph = graph
        self.static_data = static_data
        self.screen_queue: deque = deque()
        self.queued_screens: set = set()  # Track what's in queue to avoid duplicates

    def get_guidance(
        self,
        current_hash: str,
        screen_desc: ScreenDescription
    ) -> Dict[str, Any]:
        """
        Compute BFS guidance for current state.

        ### Architectural Decisions:
        - Prioritizes untested actions in current screen
        - Ranks by MOP priority within current level
        - Suggests breadth focus if untested actions exist
        - Suggests navigation to queued screen when current exhausted
        - Provides queue size for exploration awareness

        BFS explores all actions in current screen before moving to next.
        Prioritizes MOP-marked actions within current level.
        """
        node = self.graph.states.get(current_hash)

        # Get all actions from screen description
        all_actions = screen_desc.get_all_actions()

        # Identify untested actions in current screen
        if node:
            untested = [
                action for action in all_actions
                if action.id not in node.executed_actions
            ]
        else:
            # First visit - all actions untested
            untested = all_actions

        # Sort by MOP priority
        priority = sorted(
            untested,
            key=lambda a: self._get_mop_priority(a),
            reverse=True
        )

        # BFS logic: exhaust current screen, then move to queued screen
        if priority:
            focus = f"breadth (explore {len(priority)} remaining in current screen)"
        else:
            if self.screen_queue:
                next_hash = self.screen_queue[0]
                focus = f"navigate to next queued screen ({next_hash[:6]}...)"
            else:
                focus = "exploration complete (no queued screens)"

        # Get coverage if node exists
        coverage = f"{node.get_coverage() * 100:.1f}%" if node else "0.0%"

        return {
            "priority_actions": [self._format_action(a) for a in priority[:5]],
            "exploration_focus": focus,
            "coverage_current": coverage,
            "untested_count": len(priority),
            "total_count": len(all_actions),
            "queue_size": len(self.screen_queue)
        }

    def record_transition(self, from_hash: str, to_hash: str):
        """
        Record transition and update screen queue for BFS.

        ### Architectural Decisions:
        - Adds newly discovered screens to queue
        - Avoids duplicate entries via queued_screens set
        - Maintains FIFO order for breadth-first traversal

        Args:
            from_hash: Structural hash of source state
            to_hash: Structural hash of destination state
        """
        # If discovered new screen, add to queue
        if to_hash not in self.graph.states and to_hash not in self.queued_screens:
            self.screen_queue.append(to_hash)
            self.queued_screens.add(to_hash)

        # Remove from queue if we've now visited it
        if to_hash in self.queued_screens and to_hash in self.graph.states:
            # Remove from queue (may not be at front if we deviated)
            try:
                # Create new queue without this hash
                self.screen_queue = deque(h for h in self.screen_queue if h != to_hash)
                self.queued_screens.discard(to_hash)
            except ValueError:
                pass  # Already removed

    def _get_mop_priority(self, action: Any) -> int:
        """
        Compute priority score for action.

        ### Priority Levels:
        - 3: [DM] - Directly reaches monitored operation
        - 2: [M] - Reaches monitored operation transitively
        - 1: No marker - Regular action

        Args:
            action: ItemAction from ScreenDescription

        Returns:
            Priority score (higher = more important)
        """
        if getattr(action, 'directly_reaches_mop', False):
            return 3  # [DM]
        elif getattr(action, 'reaches_mop', False):
            return 2  # [M]
        else:
            return 1  # no marker
