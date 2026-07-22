"""
Base strategy interface for autonomous exploration.

Defines the contract for exploration strategies that guide the RVAgent's
decision-making process during Android application testing.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


class BaseStrategy(ABC):
    """
    Abstract base class for exploration strategies.

    ### Architectural Decisions:
    - Provides soft guidance, does not enforce actions
    - Operates on structural hashes for state identification
    - Integrates with dynamic state graph for history awareness
    - Supports optional static analysis data for MOP prioritization

    ### Role in the System:
    - Defines strategy interface for DFS, BFS, and future variants
    - Computes action priorities based on exploration history
    - Generates natural language guidance for LLM consumption
    - Maintains strategy-specific state (e.g., BFS queue, DFS stack)

    ### Integration Points:
    - Called by observe node to generate guidance
    - Queries DynamicStateGraph for state history
    - Accesses ScreenDescription for action enumeration
    - Uses StaticAnalysisData for MOP marker prioritization
    """

    @abstractmethod
    def get_guidance(
        self,
        current_hash: str,
        screen_desc: ScreenDescription
    ) -> Dict[str, Any]:
        """
        Compute exploration guidance for current state.

        ### Architectural Decisions:
        - Returns structured guidance for system prompt integration
        - Prioritizes actions without forcing selection
        - Provides exploration focus directive for strategy awareness
        - Includes coverage context for informed decision-making

        Args:
            current_hash: Structural hash of current UI state
            screen_desc: Parsed screen with UI elements and actions

        Returns:
            Guidance dictionary containing:
            - priority_actions: Ranked list of suggested actions (top 5)
            - exploration_focus: Strategy directive (e.g., "deepen", "backtrack")
            - coverage_current: Current screen coverage percentage
            - Additional strategy-specific fields (e.g., queue_size for BFS)
        """
        pass

    @abstractmethod
    def record_transition(self, from_hash: str, to_hash: str):
        """
        Record state transition for strategy bookkeeping.

        ### Architectural Decisions:
        - Enables strategy-specific state tracking
        - Called by update_memories node after action execution
        - Allows strategies to maintain exploration queues/stacks

        Args:
            from_hash: Structural hash of source state
            to_hash: Structural hash of destination state
        """
        pass

    def _format_action(self, action: Any) -> str:
        """
        Format action for LLM consumption.

        Args:
            action: ItemAction from ScreenDescription

        Returns:
            Human-readable action description with MOP markers
        """
        marker = ""
        if getattr(action, 'directly_reaches_mop', False):
            marker = "[DM] "
        elif getattr(action, 'reaches_mop', False):
            marker = "[M] "

        return f"{marker}{action.text or action.action_type}"
