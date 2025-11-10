"""
Depth-first exploration strategy with MOP prioritization and coordinate-based action tracking.

Implements DFS algorithm for systematic state space exploration with static analysis guidance
for monitored operation coverage. Uses coordinate-based action tracking to handle non-deterministic
UI parsing across sessions.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
import logging

from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction
from rv_android_core.domain.static import StaticAnalysisData

logger = logging.getLogger(__name__)


@dataclass
class DFSState:
    """
    DFS stack state for backtracking operations.

    ### Architectural Decisions:
    - Represents node in DFS traversal tree
    - Maintains depth for exploration metrics
    - Tracks parent reference for backtracking paths
    - Records untested action count for exhaustion detection

    ### Role in the System:
    - Enables depth-first traversal with backtracking
    - Supports path reconstruction for analysis
    - Provides state exhaustion detection
    - Maintains exploration hierarchy
    """
    screen_hash: str
    depth: int
    parent_hash: Optional[str]
    untested_count: int


class DFSStrategy(ExplorationStrategy):
    """
    Depth-first exploration strategy with MOP prioritization and coordinate-based action tracking.

    ### Architectural Decisions:
    - Implements pure algorithmic DFS traversal
    - Prioritizes actions with monitored operation markers
    - Uses stack-based depth tracking with backtracking
    - Tracks actions by coordinates for parsing stability
    - Filters system actions and navigation bar interactions

    ### Key Innovation: Coordinate-Based Action Tracking
    Problem: UIAutomator dumps can return elements in different orders, causing
    sequential action IDs (1, 2, 3...) to change between visits to the same screen.
    This leads to repeated execution of previously tested actions.

    Solution: Track executed actions by their (x, y) coordinates instead of IDs.
    Coordinates remain stable for the same UI element regardless of parsing order,
    ensuring accurate exploration progress tracking.

    ### Role in the System:
    - Provides systematic depth-first state space exploration
    - Selects actions based on traversal algorithm and MOP priority
    - Manages exploration stack for backtracking operations
    - Tracks visited states to prevent infinite loops
    - Maintains exploration depth for metrics

    ### Integration Points:
    - Used by RoutingManager in pure_algorithm mode
    - Queries DynamicStateGraph for state history
    - Accesses ScreenDescription for available actions
    - Uses StaticAnalysisData for MOP marker prioritization
    - Converts coordinates between device and optimized spaces
    """

    def __init__(
        self,
        graph: DynamicStateGraph,
        static_data: Optional[StaticAnalysisData] = None,
        coordinate_converter = None
    ):
        """
        Initialize DFS exploration strategy.

        Args:
            graph: Dynamic state graph for history tracking
            static_data: Optional static analysis data for MOP markers
            coordinate_converter: CoordinateConverter for device/optimized space conversion
        """
        self.graph = graph
        self.static_data = static_data
        self.converter = coordinate_converter

        # DFS traversal state
        self.state_stack: List[DFSState] = []
        self.visited_states: Set[str] = set()
        self.current_depth = 0

    def select_next_action(
        self,
        current_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Select next action using depth-first traversal algorithm.

        ### Algorithm Implementation:
        1. Create node for new states, update visit count for known states
        2. Filter system actions and navigation bar interactions
        3. Identify untested actions by coordinate signatures
        4. Select highest priority untested action (DEEPEN)
        5. If no untested actions, return None to trigger backtracking

        ### Action Prioritization:
        - Direct MOP markers [DM] prioritized highest
        - Transitive MOP markers [M] prioritized medium
        - Regular actions prioritized lowest

        Args:
            current_hash: Structural hash of current UI state
            screen_desc: Parsed screen with UI elements and actions

        Returns:
            Selected ItemAction to execute, or None if state exhausted
        """
        logger.debug(f"DFS: Processing state {current_hash[:8]}, depth={self.current_depth}")

        # Create or update graph node
        if current_hash not in self.graph.states:
            node = self.graph.get_or_create_state(
                current_hash,
                screen_desc.activity,
                screen_desc
            )

            parent_hash = self.state_stack[-1].screen_hash if self.state_stack else None

            dfs_state = DFSState(
                screen_hash=current_hash,
                depth=self.current_depth,
                parent_hash=parent_hash,
                untested_count=node.total_actions
            )
            self.state_stack.append(dfs_state)
            self.visited_states.add(current_hash)

            logger.info(f"DFS: New state at depth {self.current_depth}, {node.total_actions} actions")
            logger.info(f"     Hash: {current_hash[:16]}...")
        else:
            node = self.graph.states[current_hash]
            logger.info(f"DFS: Revisited state (visit {node.visit_count}, executed: {len(node.executed_actions)})")
            logger.info(f"     Hash: {current_hash[:16]}...")

        # Get all available actions
        all_actions = screen_desc.get_all_actions()

        # Filter actions: remove system actions and navigation bar elements
        filtered_actions = self._filter_actions(all_actions)

        # Identify untested actions by coordinate signatures
        untested_actions = self._get_untested_actions(node, filtered_actions)

        # Log exploration state
        logger.info(f"DFS State Analysis - {current_hash[:8]}:")
        logger.info(f"  Total actions: {len(filtered_actions)}")
        logger.info(f"  Executed: {len(node.executed_actions)}")
        logger.info(f"  Untested: {len(untested_actions)}")

        # DEEPEN: Select untested action if available
        if untested_actions:
            selected_action = self._select_priority_action(untested_actions)
            self.current_depth += 1

            # Mark action as executed before execution to handle crashes
            action_signature = self._convert_signature_to_optimized(selected_action.coords_for_matching)
            logger.info(f"DFS DEEPEN: Selected action ID={selected_action.id}")
            logger.info(f"  Signature: {action_signature}")
            logger.info(f"  Priority: {self._get_mop_priority(selected_action)}")
            logger.info(f"  Pre-marking as executed on state {current_hash[:8]}")

            self.graph.record_action(screen_hash=current_hash, action_signature=action_signature)

            return selected_action

        # State exhausted - signal need for backtracking
        logger.info(f"DFS: State {current_hash[:8]} exhausted, backtrack needed")
        return None

    def record_transition(
        self,
        from_hash: str,
        to_hash: str,
        action: ItemAction
    ):
        """
        Record state transition for strategy bookkeeping.

        DFS maintains implicit stack through graph structure and does not
        require explicit transition recording for traversal algorithm.

        Args:
            from_hash: Structural hash of source state
            to_hash: Structural hash of destination state
            action: Action that triggered the transition
        """
        # DFS algorithm uses implicit stack via graph transitions
        # No additional bookkeeping required for traversal
        pass

    def should_backtrack(self, current_hash: str) -> bool:
        """
        Determine if backtracking is needed from current state.

        Checks if current state has unexplored actions. Backtracking is required
        when all actions at current depth have been tested.

        Args:
            current_hash: Structural hash of current state

        Returns:
            True if all actions explored and should backtrack, False otherwise
        """
        node = self.graph.states.get(current_hash)
        if not node:
            return False

        # Backtrack if all actions have been executed
        return len(node.executed_actions) >= node.total_actions

    def reset(self):
        """
        Reset strategy state for new exploration session.

        Clears all traversal state including stack, visited states, and depth tracking.
        Graph state is maintained separately and not reset here.
        """
        self.state_stack.clear()
        self.visited_states.clear()
        self.current_depth = 0
        logger.info("DFS strategy state reset")

    def _filter_actions(self, actions: List[ItemAction]) -> List[ItemAction]:
        """
        Filter out system actions and navigation bar interactions.

        ### Filtering Rules:
        - Remove actions marked as system_action (SYSTEM_BACK, RESTART_APP)
        - Remove actions without valid execution coordinates
        - Remove actions in navigation bar area (y > 1794 in device space)
        - DFS controls navigation algorithmically, does not need system actions

        Args:
            actions: List of all available actions

        Returns:
            Filtered list of actionable items
        """
        filtered = []

        for action in actions:
            # Skip system actions
            if action.target_view.get('system_action', False):
                logger.debug(f"Filtered system action: ID={action.id}")
                continue

            # Get coordinates for validation and nav bar check
            coords = action.get_execution_coordinates()

            # Skip actions without valid coordinates (e.g., SystemAction_BACK)
            if not coords:
                logger.debug(f"Filtered action without coordinates: ID={action.id}, class={action.target_view.get('class', 'unknown')}")
                continue

            # Skip navigation bar actions (y > 1794 in device space 1080x1920)
            x, y = coords
            if y > 1794:
                logger.debug(f"Filtered nav bar action: ID={action.id} coords=({x},{y})")
                continue

            filtered.append(action)

        return filtered

    def _get_untested_actions(
        self,
        node,
        actions: List[ItemAction]
    ) -> List[ItemAction]:
        """
        Identify actions not yet executed on this state.

        Compares action coordinate signatures against node's executed actions set.
        Converts signatures from device space to optimized space for comparison.

        Args:
            node: ScreenNode with execution history
            actions: List of available actions

        Returns:
            List of actions not yet executed
        """
        untested = []

        for action in actions:
            # Convert signature from device to optimized space
            action_signature = self._convert_signature_to_optimized(action.coords_for_matching)

            if action_signature not in node.executed_actions:
                untested.append(action)
                logger.debug(f"Untested action: ID={action.id} sig={action_signature}")
            else:
                logger.debug(f"Tested action: ID={action.id} sig={action_signature}")

        return untested

    def _select_priority_action(self, actions: List[ItemAction]) -> ItemAction:
        """
        Select highest priority action from untested list.

        Sorts actions by MOP priority and returns top candidate.

        Args:
            actions: List of untested actions

        Returns:
            Action with highest priority score
        """
        priority_sorted = sorted(
            actions,
            key=lambda a: self._get_mop_priority(a),
            reverse=True
        )

        return priority_sorted[0]

    def _get_mop_priority(self, action: ItemAction) -> int:
        """
        Compute priority score for action based on MOP markers.

        ### Priority Levels:
        - 3: [DM] - Directly reaches monitored operation
        - 2: [M] - Reaches monitored operation transitively
        - 1: No marker - Regular action

        Args:
            action: ItemAction to evaluate

        Returns:
            Priority score (higher = more important)
        """
        if self._is_direct_mop(action):
            return 3  # [DM]
        elif self._has_mop_marker(action):
            return 2  # [M]
        else:
            return 1  # Regular action

    def _convert_signature_to_optimized(
        self,
        signature: Tuple[Tuple[int, int], str]
    ) -> Tuple[Tuple[int, int], str]:
        """
        Convert action signature from device space to optimized space.

        ### Coordinate Space Conversion:
        RVAgent processes optimized screenshots for LLM efficiency, requiring
        coordinate conversion between device space (1080x1920) and optimized
        space (704x1248). This ensures signature matching consistency.

        Args:
            signature: ((device_x, device_y), action_type) in device space

        Returns:
            ((optimized_x, optimized_y), action_type) in optimized space
        """
        (device_x, device_y), action_type = signature

        if self.converter:
            # Use CoordinateConverter for consistent conversion
            optimized_x, optimized_y = self.converter.device_to_optimized(device_x, device_y)
        else:
            # Fallback to direct conversion if converter unavailable
            optimized_x = int(device_x * 704 / 1080)
            optimized_y = int(device_y * 1248 / 1920)

        return ((optimized_x, optimized_y), action_type)
