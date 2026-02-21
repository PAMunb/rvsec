"""
Breadth-first exploration strategy with MOP prioritization and coordinate-based action tracking.

Implements BFS algorithm for systematic state space exploration with static analysis guidance
for monitored operation coverage. Uses coordinate-based action tracking to handle non-deterministic
UI parsing across sessions.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from collections import deque
import logging

from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_agent.constants import RVAgentConstants
from rv_agent.services.coordinate_utils import device_to_optimized

logger = logging.getLogger(__name__)


@dataclass
class BFSState:
    """
    BFS queue state for level-by-level exploration.

    ### Architectural Decisions:
    - Represents node in BFS traversal queue
    - Maintains depth for exploration metrics
    - Tracks parent reference for path reconstruction
    - Records untested action count for exhaustion detection

    ### Role in the System:
    - Enables breadth-first traversal with level exhaustion
    - Supports path reconstruction for analysis
    - Provides state exhaustion detection
    - Maintains exploration hierarchy
    """

    screen_hash: str
    depth: int
    parent_hash: Optional[str]
    untested_count: int


class BFSStrategy(ExplorationStrategy):
    """
    Breadth-first exploration strategy with MOP prioritization and coordinate-based action tracking.

    ### Architectural Decisions:
    - Implements pure algorithmic BFS traversal
    - Prioritizes actions with monitored operation markers
    - Uses queue-based level tracking (FIFO - First In First Out)
    - Tracks actions by coordinates for parsing stability
    - Filters system actions and navigation bar interactions

    ### Key Difference from DFS:
    BFS exhausts ALL actions in current state before moving to next state.
    DFS deepens immediately when untested action is found.

    BFS uses a QUEUE (FIFO): explores states level-by-level
    DFS uses a STACK (LIFO): explores states depth-first

    ### Key Innovation: Coordinate-Based Action Tracking
    Problem: UIAutomator dumps can return elements in different orders, causing
    sequential action IDs (1, 2, 3...) to change between visits to the same screen.
    This leads to repeated execution of previously tested actions.

    Solution: Track executed actions by their (x, y) coordinates instead of IDs.
    Coordinates remain stable for the same UI element regardless of parsing order,
    ensuring accurate exploration progress tracking.

    ### Role in the System:
    - Provides systematic breadth-first state space exploration
    - Selects actions based on traversal algorithm and MOP priority
    - Manages exploration queue for level-by-level operations
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
        coordinate_converter=None,
        target_package: Optional[str] = None,
    ):
        """
        Initialize BFS exploration strategy.

        Args:
            graph: Dynamic state graph for history tracking
            static_data: Optional static analysis data for MOP markers
            coordinate_converter: CoordinateConverter for device/optimized space conversion
            target_package: Target app package name for filtering external elements
        """
        self.graph = graph
        self.static_data = static_data
        self.converter = coordinate_converter
        self.target_package = target_package

        # BFS traversal state - QUEUE (FIFO)
        self.state_queue: deque = deque()
        self.visited_states: Set[str] = set()
        self.current_state_hash: Optional[str] = None
        self.current_depth = 0

        # Scroll tracking to avoid infinite scrolling loops
        self.scrolled_positions: Set[Tuple[str, str, str]] = set()

        if target_package:
            logger.info(f"BFS: Filtering actions to package '{target_package}'")

    def select_next_action(
        self, current_hash: str, screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Select next action using breadth-first traversal algorithm.

        ### Algorithm Implementation:
        1. Create node for new states, update visit count for known states
        2. Filter system actions and navigation bar interactions
        3. Identify untested actions by coordinate signatures
        4. Select highest priority untested action (BREADTH - exhaust current level)
        5. If no untested actions in current state, move to next state in queue

        ### BFS Logic:
        Unlike DFS which deepens immediately, BFS exhausts ALL actions in current
        state before moving to the next state. This ensures level-by-level exploration.

        ### Action Prioritization:
        - Direct MOP markers [DM] prioritized highest
        - Transitive MOP markers [M] prioritized medium
        - Regular actions prioritized lowest

        Args:
            current_hash: Structural hash of current UI state
            screen_desc: Parsed screen with UI elements and actions

        Returns:
            Selected ItemAction to execute, or None if current state exhausted
        """
        logger.debug(
            f"BFS: Processing state {current_hash[:8]}, depth={self.current_depth}"
        )

        # Create or update graph node
        if current_hash not in self.graph.states:
            node = self.graph.get_or_create_state(
                current_hash, screen_desc.activity, screen_desc
            )

            parent_hash = self.current_state_hash

            bfs_state = BFSState(
                screen_hash=current_hash,
                depth=self.current_depth,
                parent_hash=parent_hash,
                untested_count=node.total_actions,
            )

            # Add to queue for BFS exploration
            self.state_queue.append(bfs_state)
            self.visited_states.add(current_hash)
            self.current_state_hash = current_hash

            logger.info(
                f"BFS: New state at depth {self.current_depth}, {node.total_actions} actions"
            )
            logger.info(f"     Hash: {current_hash[:16]}...")
            logger.info(f"     Queue size: {len(self.state_queue)}")
        else:
            node = self.graph.states[current_hash]
            self.current_state_hash = current_hash
            logger.info(
                f"BFS: Revisited state (visit {node.visit_count}, executed: {len(node.executed_actions)})"
            )
            logger.info(f"     Hash: {current_hash[:16]}...")

        # Get all available actions
        all_actions = screen_desc.get_all_actions()

        # Filter actions: remove system actions and navigation bar elements
        filtered_actions = self._filter_actions(all_actions)

        # Identify untested actions by coordinate signatures
        untested_actions = self._get_untested_actions(node, filtered_actions)

        # Log exploration state
        logger.info(f"BFS State Analysis - {current_hash[:8]}:")
        logger.info(f"  Total actions: {len(filtered_actions)}")
        logger.info(f"  Executed: {len(node.executed_actions)}")
        logger.info(f"  Untested: {len(untested_actions)}")
        logger.info(f"  Queue size: {len(self.state_queue)}")

        # BREADTH: Select untested action if available (highest priority)
        if untested_actions:
            selected_action = self._select_priority_action(untested_actions)

            # Mark action as executed before execution to handle crashes
            action_signature = self._convert_signature_to_optimized(
                selected_action.coords_for_matching
            )
            logger.info(
                f"BFS BREADTH: Selected UNTESTED action ID={selected_action.id}"
            )
            logger.info(f"  Signature: {action_signature}")
            logger.info(f"  Priority: {self._get_mop_priority(selected_action)}")
            logger.info(f"  Execution count: 0 (first time)")
            logger.info(f"  Pre-marking as executed on state {current_hash[:8]}")

            self.graph.record_action(
                screen_hash=current_hash, action_signature=action_signature
            )

            return selected_action

        # CONTINUOUS: All actions tested
        # Before re-testing, try scroll to reveal hidden content (15% probability)
        if filtered_actions:
            scroll_action = self._try_generate_scroll_action(
                screen_desc, node, self.scrolled_positions, probability=0.15
            )
            if scroll_action:
                logger.info(
                    f"BFS SCROLL: All visible actions tested, scrolling to reveal more content"
                )
                return scroll_action

            # No scroll - select LEAST-EXECUTED action
            # Algorithm continues until timeout, never stops when "exhausted"
            # Filters out permanently failed actions to avoid repeated crashes
            selected_action = self._select_least_executed_action(node, filtered_actions)

            # If all actions have failed, fall through to BACK
            if selected_action is not None:
                action_signature = self._convert_signature_to_optimized(
                    selected_action.coords_for_matching
                )
                exec_count = node.get_action_execution_count(action_signature)
                logger.info(
                    f"BFS CONTINUOUS: Selected LEAST-EXECUTED action ID={selected_action.id}"
                )
                logger.info(f"  Signature: {action_signature}")
                logger.info(f"  Priority: {self._get_mop_priority(selected_action)}")
                logger.info(f"  Execution count: {exec_count} -> {exec_count + 1}")
                logger.info(f"  Pre-marking as executed on state {current_hash[:8]}")

                self.graph.record_action(
                    screen_hash=current_hash, action_signature=action_signature
                )

                return selected_action

        # No actions available (edge case) - return BACK to navigate
        logger.info(
            f"BFS: No actions available on state {current_hash[:8]}, returning BACK"
        )

        # Create a BACK ItemAction for navigation
        back_action = ItemAction(
            id=999,
            text="BACK",
            event=WidgetEventType.BACK,
            reaches_mop=False,
            directly_reaches_mop=False,
            target_view={"system_action": True, "class": "SystemAction_BACK"},
            coordinates=None,
            text_input=None,
        )
        return back_action

    def record_transition(self, from_hash: str, to_hash: str, action: ItemAction):
        """
        Record state transition for strategy bookkeeping.

        BFS maintains queue of states to explore. When transition occurs,
        depth tracking is updated for new states.

        Args:
            from_hash: Structural hash of source state
            to_hash: Structural hash of destination state
            action: Action that triggered the transition
        """
        # Update depth when moving to new state
        if to_hash not in self.visited_states:
            self.current_depth += 1
            logger.debug(
                f"BFS: Transition to new state, depth now {self.current_depth}"
            )

    def should_backtrack(self, current_hash: str) -> bool:
        """
        Determine if backtracking/navigation is needed from current state.

        In BFS, "backtracking" means current state is exhausted and we need
        to navigate to the next state in the queue (not necessarily going backwards).

        Args:
            current_hash: Structural hash of current state

        Returns:
            True if all actions explored and should move to next queued state, False otherwise
        """
        node = self.graph.states.get(current_hash)
        if not node:
            return False

        # Move to next queued state if all actions have been executed
        is_exhausted = len(node.executed_actions) >= node.total_actions

        if is_exhausted:
            logger.info(
                f"BFS: State {current_hash[:8]} exhausted, need navigation to next queued state"
            )

        return is_exhausted

    def reset(self):
        """
        Reset strategy state for new exploration session.

        Clears all traversal state including queue, visited states, depth tracking,
        and scroll positions. Graph state is maintained separately and not reset here.
        """
        self.state_queue.clear()
        self.visited_states.clear()
        self.current_state_hash = None
        self.current_depth = 0
        self.scrolled_positions.clear()
        logger.info("BFS strategy state reset")

    def _filter_actions(self, actions: List[ItemAction]) -> List[ItemAction]:
        """
        Filter out system actions, external package elements, and navigation bar interactions.

        ### Filtering Rules:
        - Remove actions marked as system_action (SYSTEM_BACK, RESTART_APP)
        - Remove actions from packages other than target app (systemui, launcher, etc)
        - Remove actions without valid execution coordinates
        - Remove actions in navigation bar area (y > NAVBAR_THRESHOLD_Y in device space)
        - BFS controls navigation algorithmically, does not need system actions

        Args:
            actions: List of all available actions

        Returns:
            Filtered list of actionable items (only from target app package)
        """
        filtered = []
        external_count = 0

        for action in actions:
            # Skip system actions
            if action.target_view.get("system_action", False):
                logger.debug(f"Filtered system action: ID={action.id}")
                continue

            # Filter by package - only include actions from target app
            action_package = action.target_view.get("package", "")
            if self.target_package and action_package:
                if action_package != self.target_package:
                    external_count += 1
                    logger.debug(
                        f"Filtered external package: ID={action.id} "
                        f"package='{action_package}' (target='{self.target_package}')"
                    )
                    continue

            # Get coordinates for validation and nav bar check
            coords = action.get_execution_coordinates()

            # Skip actions without valid coordinates (e.g., SystemAction_BACK)
            if not coords:
                logger.debug(
                    f"Filtered action without coordinates: ID={action.id}, class={action.target_view.get('class', 'unknown')}"
                )
                continue

            # Skip navigation bar actions (above NAVBAR_THRESHOLD_Y in device space)
            x, y = coords
            if y > RVAgentConstants.NAVBAR_THRESHOLD_Y:
                logger.debug(
                    f"Filtered nav bar action: ID={action.id} coords=({x},{y})"
                )
                continue

            filtered.append(action)

        if external_count > 0:
            logger.info(f"Filtered {external_count} external package elements")

        return filtered

    def _get_untested_actions(
        self, node, actions: List[ItemAction]
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
            action_signature = self._convert_signature_to_optimized(
                action.coords_for_matching
            )

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
            actions, key=lambda a: self._get_mop_priority(a), reverse=True
        )

        return priority_sorted[0]

    def _select_least_executed_action(
        self, node, actions: List[ItemAction]
    ) -> Optional[ItemAction]:
        """
        Select action with fewest executions for continuous exploration.

        When all actions have been tested at least once, prioritizes:
        1. Actions with fewer execution counts (least visited first)
        2. MOP priority as tiebreaker (higher MOP = selected first)

        This enables continuous exploration until timeout, always making
        progress on less-explored paths.

        Args:
            node: ScreenNode with action execution counts
            actions: List of all available actions (already tested)

        Returns:
            Action with lowest execution count, or None if no actions available
        """
        if not actions:
            return None

        def sort_key(action: ItemAction):
            action_signature = self._convert_signature_to_optimized(
                action.coords_for_matching
            )
            exec_count = node.get_action_execution_count(action_signature)
            mop_priority = self._get_mop_priority(action)
            # Sort by: (exec_count ASC, -mop_priority DESC)
            # Lower exec_count first, then higher MOP priority
            return (exec_count, -mop_priority)

        sorted_actions = sorted(actions, key=sort_key)
        return sorted_actions[0]

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
        self, signature: Tuple[Tuple[int, int], str]
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
            optimized_x, optimized_y = self.converter.device_to_optimized(
                device_x, device_y
            )
        else:
            # Fallback to direct conversion if converter unavailable
            optimized_x, optimized_y = device_to_optimized(
                device_x,
                device_y,
                (
                    RVAgentConstants.DEFAULT_DEVICE_WIDTH,
                    RVAgentConstants.DEFAULT_DEVICE_HEIGHT,
                ),
                (
                    RVAgentConstants.SCREENSHOT_TARGET_WIDTH,
                    RVAgentConstants.SCREENSHOT_TARGET_HEIGHT,
                ),
            )

        return ((optimized_x, optimized_y), action_type)
