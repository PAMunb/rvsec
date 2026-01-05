"""
Depth-first exploration strategy with MOP prioritization.

Implements DFS exploration that prioritizes depth while incorporating
static analysis guidance for monitored operation coverage.
"""

from typing import Dict, List, Any, Optional
from rv_agent.strategies.base_strategy import BaseStrategy
from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_android_core.domain.static import StaticAnalysisData


class DFSStrategy(BaseStrategy):
    """
    Depth-first exploration strategy with MOP prioritization.

    ### Architectural Decisions:
    - Provides guidance, does not force actions
    - Prioritizes untested actions with MOP markers
    - Implements stack-based depth-first logic
    - Computes coverage context for informed decisions
    - Suggests backtracking when current screen exhausted

    ### Role in the System:
    - Generates priority rankings for system prompt
    - Determines exploration focus (deepen vs backtrack)
    - Queries graph state for guidance computation
    - Formats suggestions for LLM consumption
    - Maintains exploration stack implicitly via graph

    ### Integration Points:
    - Called by observe node to generate guidance
    - Queries DynamicStateGraph for state history
    - Accesses ScreenDescription for action enumeration
    - Uses StaticAnalysisData for MOP marker prioritization
    """

    def __init__(
        self,
        graph: DynamicStateGraph,
        static_data: Optional[StaticAnalysisData] = None
    ):
        """
        Initialize DFS strategy.

        Args:
            graph: Dynamic state graph for history tracking
            static_data: Optional static analysis data for MOP markers
        """
        self.graph = graph
        self.static_data = static_data

    def get_guidance(
        self,
        current_hash: str,
        screen_desc: ScreenDescription
    ) -> Dict[str, Any]:
        """
        Compute exploration guidance for current state.

        ### Architectural Decisions:
        - Prioritizes untested actions first
        - Ranks by MOP priority: [DM] > [M] > no marker
        - Suggests deepening if untested actions exist
        - Suggests backtracking if screen fully explored
        - Provides coverage context for awareness

        Returns guidance dictionary for system prompt integration:
        - priority_actions: Ranked list of suggested actions
        - exploration_focus: Current strategy directive
        - coverage_current: Coverage percentage for context
        """
        node = self.graph.states.get(current_hash)

        # Get all actions from screen description
        all_actions = screen_desc.get_all_actions()

        # Identify untested actions
        if node:
            untested = [
                action for action in all_actions
                if action.id not in node.executed_actions
            ]
        else:
            # First visit - all actions untested
            untested = all_actions

        # Sort by MOP priority: [DM] > [M] > no marker
        priority = sorted(
            untested,
            key=lambda a: self._get_mop_priority(a),
            reverse=True
        )

        # DFS logic: deepen if untested exist, else backtrack
        if priority:
            focus = f"deepen (explore {len(priority)} untested actions)"
        else:
            focus = "backtrack (all actions tested, try back/navigation)"

        # Get coverage if node exists
        coverage = f"{node.get_coverage() * 100:.1f}%" if node else "0.0%"

        return {
            "priority_actions": [self._format_action(a) for a in priority[:5]],
            "exploration_focus": focus,
            "coverage_current": coverage,
            "untested_count": len(priority),
            "total_count": len(all_actions)
        }

    def record_transition(self, from_hash: str, to_hash: str):
        """
        Record state transition for strategy bookkeeping.

        DFS doesn't maintain explicit stack - relies on graph structure.

        Args:
            from_hash: Structural hash of source state
            to_hash: Structural hash of destination state
        """
        # DFS uses implicit stack via graph transitions
        # No additional bookkeeping needed
        pass

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
