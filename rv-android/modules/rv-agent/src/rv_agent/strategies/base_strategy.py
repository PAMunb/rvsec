"""
Base interface for graph exploration strategies.

Defines the contract for algorithm-based exploration strategies (DFS, BFS, etc.)
that operate independently of LLM guidance. These strategies implement graph
traversal algorithms for systematic state space exploration.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction


class ExplorationStrategy(ABC):
    """
    Abstract base class for graph exploration strategies.

    ### Architectural Decisions:
    - Implements pure algorithmic exploration (no LLM integration)
    - Operates on state graph with coordinate-based action tracking
    - Provides action selection based on traversal algorithm
    - Supports static analysis guidance for MOP prioritization
    - Maintains algorithm-specific state (e.g., stack for DFS, queue for BFS)

    ### Role in the System:
    - Defines interface for DFS, BFS, and future traversal algorithms
    - Selects next action based on algorithm logic and state history
    - Tracks visited states and unexplored transitions
    - Integrates static analysis data for prioritization

    ### Integration Points:
    - Used by RoutingManager in pure_algorithm mode
    - Queries DynamicStateGraph for state history
    - Accesses ScreenDescription for available actions
    - Tracks actions by coordinates for non-deterministic UI parsing
    """

    @abstractmethod
    def select_next_action(
        self,
        current_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Select next action to execute based on traversal algorithm.

        Args:
            current_hash: Structural hash of current UI state
            screen_desc: Parsed screen with UI elements and actions

        Returns:
            Selected ItemAction to execute, or None if exploration complete

        ### Implementation Requirements:
        - Must prioritize untested actions (track by coordinates)
        - Should incorporate MOP markers for prioritization if available
        - Must handle backtracking when current state is exhausted
        - Should track visited states to avoid infinite loops
        """
        pass

    @abstractmethod
    def record_transition(
        self,
        from_hash: str,
        to_hash: str,
        action: ItemAction
    ):
        """
        Record state transition for strategy bookkeeping.

        Args:
            from_hash: Structural hash of source state
            to_hash: Structural hash of destination state
            action: Action that triggered the transition

        ### Implementation Requirements:
        - Must update algorithm-specific state (stack/queue)
        - Should track action by coordinates for repeatability
        - Must handle new state discovery and backtracking logic
        """
        pass

    @abstractmethod
    def should_backtrack(self, current_hash: str) -> bool:
        """
        Determine if backtracking is needed from current state.

        Args:
            current_hash: Structural hash of current state

        Returns:
            True if should backtrack, False if should continue exploring

        ### Implementation Requirements:
        - Must check if current state has unexplored actions
        - Should consider algorithm-specific backtracking conditions
        - Must handle dead-end states appropriately
        """
        pass

    @abstractmethod
    def reset(self):
        """
        Reset strategy state for new exploration session.

        ### Implementation Requirements:
        - Must clear all algorithm-specific state
        - Should reset visited states tracking
        - Must clear transition history
        """
        pass

    def _get_action_signature(self, action: ItemAction) -> Tuple[Tuple[int, int], str]:
        """
        Generate unique signature for action based on coordinates and type.

        Uses coordinates instead of IDs to handle non-deterministic UIAutomator
        parsing where element IDs may change between visits to the same screen.

        Args:
            action: ItemAction to generate signature for

        Returns:
            Tuple of ((x, y), action_type) as unique identifier
        """
        # Use center of bounds as stable coordinate reference
        if action.bounds and len(action.bounds) == 2:
            x1, y1 = action.bounds[0]
            x2, y2 = action.bounds[1]
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
        else:
            center_x, center_y = (0, 0)

        return ((center_x, center_y), action.action_type)

    def _has_mop_marker(self, action: ItemAction) -> bool:
        """
        Check if action has MOP marker for prioritization.

        Args:
            action: ItemAction to check

        Returns:
            True if action has MOP marker
        """
        return (
            getattr(action, 'directly_reaches_mop', False) or
            getattr(action, 'reaches_mop', False)
        )

    def _is_direct_mop(self, action: ItemAction) -> bool:
        """
        Check if action directly reaches MOP.

        Args:
            action: ItemAction to check

        Returns:
            True if action directly reaches MOP
        """
        return getattr(action, 'directly_reaches_mop', False)
