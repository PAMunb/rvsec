"""
Greedy exploration strategy for RVAgent.

Prioritizes actions with highest immediate value, focusing on code paths
reaching monitored operations and actions that have historically led to
new state discoveries.
"""

import logging
import math
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType

logger = logging.getLogger(__name__)


class GreedyStrategy(ExplorationStrategy):
    """
    Greedy exploration strategy that always selects the action with highest immediate value.

    ### Algorithm Implementation:
    - Prioritizes actions with MOP markers (monitored operations)
    - Favors actions that have discovered new states in the past
    - Maintains action value estimates based on success rates
    - Uses coordinate-based action tracking for repeatability
    - Includes small exploration bonus to avoid local optima

    ### Comparison to DFS/BFS:
    - DFS: Explores depth-first with backtracking
    - BFS: Explores breadth-first level by level
    - Greedy: Explores highest-value actions regardless of structure

    ### Trade-offs:
    - **Advantages**: Fast convergence to valuable areas, efficient MOP coverage
    - **Disadvantages**: May miss less-obvious paths, can get stuck in local optima
    - **Best for**: Runtime verification, targeted exploration, short test durations
    """

    def __init__(
        self,
        graph: DynamicStateGraph,
        static_data: Optional[StaticAnalysisData] = None,
        coordinate_converter = None,
        target_package: Optional[str] = None
    ):
        """
        Initialize greedy exploration strategy.

        Args:
            graph: Dynamic state graph for history tracking
            static_data: Optional static analysis data for MOP markers
            coordinate_converter: Optional coordinate converter for space transformations
            target_package: Target app package name for filtering external elements
        """
        self.graph = graph
        self.static_data = static_data
        self.converter = coordinate_converter
        self.target_package = target_package

        # Action value tracking
        self.action_values: Dict[Tuple[Tuple[int, int], str], float] = {}
        self.action_attempts: Dict[Tuple[Tuple[int, int], str], int] = {}
        self.action_new_states: Dict[Tuple[Tuple[int, int], str], int] = {}

        # Exploration parameters
        self.exploration_probability = 0.1  # 10% random exploration to avoid local optima

        # Visited states tracking
        self.visited_states: Set[str] = set()

        # Scroll tracking to avoid infinite scrolling loops
        self.scrolled_positions: Set[Tuple[str, str, str]] = set()

        if target_package:
            logger.info(f"Greedy: Filtering actions to package '{target_package}'")

    def select_next_action(
        self,
        current_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Select action with highest immediate value using greedy approach.

        ### Selection Process:
        1. Filter invalid actions (no coords, system actions, nav bar)
        2. Calculate value for each action based on:
           - Historical success rate
           - MOP markers (direct and transitive)
           - New state discovery history
           - Exploration bonus for untried actions
        3. Select highest-value action (90% greedy, 10% random)

        Args:
            current_hash: Structural hash of current UI state
            screen_desc: Parsed screen with UI elements and actions

        Returns:
            Highest-value action to execute, or None if no actions available
        """
        logger.debug(f"Greedy: Processing state {current_hash[:8]}")

        # Create or update graph node
        if current_hash not in self.graph.states:
            node = self.graph.get_or_create_state(
                current_hash,
                screen_desc.activity,
                screen_desc
            )
            logger.info(f"Greedy: New state, {node.total_actions} actions")
        else:
            node = self.graph.states[current_hash]
            logger.info(f"Greedy: Revisited state (visit {node.visit_count})")

        self.visited_states.add(current_hash)

        # Get all available actions
        all_actions = screen_desc.get_all_actions()

        # Filter actions (including coordinate validation)
        filtered_actions = self._filter_actions(all_actions)

        # Identify untested actions
        untested_actions = self._get_untested_actions(node, filtered_actions)

        # Log exploration state
        logger.info(f"Greedy State Analysis - {current_hash[:8]}:")
        logger.info(f"  Total actions: {len(filtered_actions)}")
        logger.info(f"  Executed: {len(node.executed_actions)}")
        logger.info(f"  Untested: {len(untested_actions)}")

        # Try to generate SET_TEXT action for EditText fields (20% probability)
        # This provides algorithmic text input capability for form exploration
        text_action = self._try_generate_text_input(screen_desc, node, probability=0.2)
        if text_action:
            # Mark action as executed before execution
            action_signature = self._convert_signature_to_optimized(text_action.coords_for_matching)
            logger.info(f"Greedy SELECT (TEXT): SET_TEXT action")
            logger.info(f"  Signature: {action_signature}")
            logger.info(f"  Pre-marking as executed on state {current_hash[:8]}")

            self.graph.record_action(screen_hash=current_hash, action_signature=action_signature)

            return text_action

        # Try to generate SWIPE action for scrollable containers (30% probability)
        # This reveals hidden content in lists, feeds, and scrollable views
        scroll_action = self._try_generate_scroll_action(
            screen_desc, node, self.scrolled_positions, probability=0.3
        )
        if scroll_action:
            logger.info(f"Greedy SCROLL: Generating scroll action to reveal content")
            return scroll_action

        # Select action based on availability
        import random

        if untested_actions:
            # UNTESTED: Prioritize untested actions with value-based selection
            action_values = {}
            for action in untested_actions:
                action_signature = self._convert_signature_to_optimized(action.coords_for_matching)
                value = self._calculate_action_value(action, action_signature)
                action_values[action.id] = value

            # Select action: 90% greedy (highest value), 10% random exploration
            if random.random() < self.exploration_probability:
                # Random exploration
                selected_action = random.choice(untested_actions)
                logger.info(f"Greedy EXPLORE: Random UNTESTED action ID={selected_action.id}")
            else:
                # Greedy selection (highest value)
                best_action_id = max(action_values.items(), key=lambda x: x[1])[0]
                selected_action = next((a for a in untested_actions if a.id == best_action_id), None)

                if not selected_action:
                    selected_action = untested_actions[0]

                logger.info(f"Greedy SELECT: Highest-value UNTESTED action ID={selected_action.id}")
                logger.info(f"  Value: {action_values[selected_action.id]:.2f}")
                logger.info(f"  Execution count: 0 (first time)")

        elif filtered_actions:
            # CONTINUOUS: All actions tested - select LEAST-EXECUTED action
            # Algorithm continues until timeout, never stops when "exhausted"
            # Filters out permanently failed actions to avoid repeated crashes
            selected_action = self._select_least_executed_action(node, filtered_actions)

            # If all actions have failed, fall through to BACK
            if selected_action is None:
                logger.info(f"Greedy: All actions failed on state {current_hash[:8]}, returning BACK")
                back_action = ItemAction(
                    id=999,
                    text="BACK",
                    event=WidgetEventType.BACK,
                    reaches_mop=False,
                    directly_reaches_mop=False,
                    target_view={"system_action": True, "class": "SystemAction_BACK"},
                    coordinates=None,
                    text_input=None
                )
                return back_action

            action_signature = self._convert_signature_to_optimized(selected_action.coords_for_matching)
            exec_count = node.get_action_execution_count(action_signature)
            logger.info(f"Greedy CONTINUOUS: Selected LEAST-EXECUTED action ID={selected_action.id}")
            logger.info(f"  Execution count: {exec_count} -> {exec_count + 1}")

        else:
            # No actions available (edge case) - return BACK to navigate
            logger.info(f"Greedy: No actions available on state {current_hash[:8]}, returning BACK")
            back_action = ItemAction(
                id=999,
                text="BACK",
                event=WidgetEventType.BACK,
                reaches_mop=False,
                directly_reaches_mop=False,
                target_view={"system_action": True, "class": "SystemAction_BACK"},
                coordinates=None,
                text_input=None
            )
            return back_action

        # Mark action as executed before execution
        action_signature = self._convert_signature_to_optimized(selected_action.coords_for_matching)
        logger.info(f"  Signature: {action_signature}")
        logger.info(f"  Priority: {self._get_mop_priority(selected_action)}")

        self.graph.record_action(screen_hash=current_hash, action_signature=action_signature)

        return selected_action

    def record_transition(
        self,
        from_hash: str,
        to_hash: str,
        action: ItemAction
    ):
        """
        Record state transition and update action value estimates.

        Args:
            from_hash: Structural hash of source state
            to_hash: Structural hash of destination state
            action: Action that triggered the transition
        """
        # Convert action to optimized signature
        action_signature = self._convert_signature_to_optimized(action.coords_for_matching)

        # Increment attempt counter
        self.action_attempts[action_signature] = self.action_attempts.get(action_signature, 0) + 1

        # Check if this led to a new state
        if to_hash not in self.visited_states:
            self.action_new_states[action_signature] = self.action_new_states.get(action_signature, 0) + 1
            logger.debug(f"Greedy: Action {action_signature} discovered new state")

        # Update action value based on outcome
        self._update_action_value(action_signature, success=True, new_state=(to_hash not in self.visited_states))

    def should_backtrack(self, current_hash: str) -> bool:
        """
        Determine if backtracking is needed from current state.

        Greedy strategy considers a state exhausted when all actions have been tried.
        Unlike DFS, it doesn't have an explicit backtracking mechanism - it relies on
        the agent's global backtrack logic.

        Args:
            current_hash: Structural hash of current state

        Returns:
            True if all actions explored, False otherwise
        """
        node = self.graph.states.get(current_hash)
        if not node:
            return False

        # State is exhausted if all actions have been executed
        return len(node.executed_actions) >= node.total_actions

    def reset(self):
        """
        Reset strategy state for new exploration session.

        Maintains action value history across resets for learning,
        but clears visited states and scroll positions to allow re-exploration.
        """
        # Keep action values/history for learning
        # Only clear visited states and scroll positions
        self.visited_states.clear()
        self.scrolled_positions.clear()
        logger.info("Greedy strategy reset (maintaining value history)")

    def _filter_actions(self, actions: List[ItemAction]) -> List[ItemAction]:
        """
        Filter out system actions, external package elements, and navigation bar interactions.

        ### Filtering Rules:
        - Remove actions marked as system_action
        - Remove actions from packages other than target app (systemui, launcher, etc)
        - Remove actions without valid execution coordinates
        - Remove actions in navigation bar area (y > 1794 in device space)

        Args:
            actions: List of all available actions

        Returns:
            Filtered list of actionable items (only from target app package)
        """
        filtered = []
        external_count = 0

        for action in actions:
            # Skip system actions
            if action.target_view.get('system_action', False):
                logger.debug(f"Filtered system action: ID={action.id}")
                continue

            # Filter by package - only include actions from target app
            action_package = action.target_view.get('package', '')
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

            # Skip actions without valid coordinates
            if not coords:
                logger.debug(f"Filtered action without coordinates: ID={action.id}, class={action.target_view.get('class', 'unknown')}")
                continue

            # Skip navigation bar actions (y > 1794 in device space 1080x1920)
            x, y = coords
            if y > 1794:
                logger.debug(f"Filtered nav bar action: ID={action.id} coords=({x},{y})")
                continue

            filtered.append(action)

        if external_count > 0:
            logger.info(f"Filtered {external_count} external package elements")

        return filtered

    def _get_untested_actions(
        self,
        node,
        actions: List[ItemAction]
    ) -> List[ItemAction]:
        """
        Identify actions not yet executed on this state.

        Args:
            node: ScreenNode with execution history
            actions: List of available actions

        Returns:
            List of actions not yet executed
        """
        untested = []

        for action in actions:
            action_signature = self._convert_signature_to_optimized(action.coords_for_matching)

            if action_signature not in node.executed_actions:
                untested.append(action)
                logger.debug(f"Untested action: ID={action.id} sig={action_signature}")

        return untested

    def _calculate_action_value(self, action: ItemAction, action_signature: Tuple[Tuple[int, int], str]) -> float:
        """
        Calculate the greedy value for an action.

        ### Value Components:
        - Base value: Historical success rate (0.5 if unknown)
        - MOP bonus: +0.3 for direct, +0.2 for transitive
        - Discovery bonus: Based on new state discovery rate
        - Exploration bonus: Higher for untried actions

        Args:
            action: ItemAction to evaluate
            action_signature: Optimized coordinate signature

        Returns:
            Estimated value [0.0-2.0+]
        """
        # Start with historical value or neutral
        value = self.action_values.get(action_signature, 0.5)

        # MOP prioritization (monitored operations)
        if getattr(action, 'directly_reaches_mop', False):
            value += 0.3
        elif getattr(action, 'reaches_mop', False):
            value += 0.2

        # New state discovery bonus
        if action_signature in self.action_new_states:
            attempts = self.action_attempts.get(action_signature, 1)
            new_states = self.action_new_states[action_signature]
            discovery_rate = new_states / attempts
            value += discovery_rate * 0.4

        # Exploration bonus for untried actions
        attempts = self.action_attempts.get(action_signature, 0)
        if attempts == 0:
            value += 0.2  # Bonus for completely untried actions
        else:
            value += 0.1 / math.sqrt(attempts)  # Diminishing bonus

        return value

    def _update_action_value(self, action_signature: Tuple[Tuple[int, int], str], success: bool, new_state: bool):
        """
        Update action value based on execution outcome.

        Uses exponential moving average with decreasing learning rate.

        Args:
            action_signature: Action coordinate signature
            success: Whether action executed successfully
            new_state: Whether action led to new state discovery
        """
        # Calculate reward
        reward = 0.5  # Neutral base

        if success:
            reward += 0.1

        if new_state:
            reward += 0.5  # High reward for discovering new states

        # Get current value and attempts
        current_value = self.action_values.get(action_signature, 0.5)
        attempts = self.action_attempts.get(action_signature, 1)

        # Update with decreasing learning rate
        learning_rate = 1.0 / math.sqrt(max(1, attempts))
        new_value = current_value + learning_rate * (reward - current_value)

        # Clamp to reasonable range
        new_value = max(0.0, min(2.0, new_value))

        # Store updated value
        self.action_values[action_signature] = new_value

    def _convert_signature_to_optimized(self, signature: Tuple[Tuple[int, int], str]) -> Tuple[Tuple[int, int], str]:
        """
        Convert action signature from device space to optimized space.

        Args:
            signature: ((x, y), action_type) in device space

        Returns:
            ((x, y), action_type) in optimized space
        """
        if not self.converter:
            return signature

        coords, action_type = signature
        optimized_coords = self.converter.device_to_optimized(coords)
        return (optimized_coords, action_type)

    def _get_mop_priority(self, action: ItemAction) -> int:
        """
        Compute priority score for action based on MOP markers.

        Args:
            action: ItemAction to evaluate

        Returns:
            Priority score (3=direct MOP, 2=transitive MOP, 1=none)
        """
        if getattr(action, 'directly_reaches_mop', False):
            return 3
        elif getattr(action, 'reaches_mop', False):
            return 2
        else:
            return 1

    def _select_least_executed_action(self, node, actions: List[ItemAction]) -> Optional[ItemAction]:
        """
        Select action with fewest executions for continuous exploration.

        When all actions have been tested at least once, prioritizes:
        1. Filter out permanently failed actions (crash-causing)
        2. Actions with fewer execution counts (least visited first)
        3. MOP priority as tiebreaker (higher MOP = selected first)

        This enables continuous exploration until timeout, always making
        progress on less-explored paths while avoiding repeated crashes.

        Args:
            node: ScreenNode with action execution counts
            actions: List of all available actions (already tested)

        Returns:
            Action with lowest execution count, or None if all actions failed
        """
        # Filter out permanently failed actions
        safe_actions = []
        for action in actions:
            action_signature = self._convert_signature_to_optimized(action.coords_for_matching)
            if not node.is_action_failed(action_signature):
                safe_actions.append(action)
            else:
                logger.debug(f"Skipping permanently failed action: {action_signature}")

        if not safe_actions:
            logger.warning(f"All actions have permanently failed on state {node.screen_hash[:8]}")
            return None

        def sort_key(action: ItemAction):
            action_signature = self._convert_signature_to_optimized(action.coords_for_matching)
            exec_count = node.get_action_execution_count(action_signature)
            mop_priority = self._get_mop_priority(action)
            # Sort by: (exec_count ASC, -mop_priority DESC)
            # Lower exec_count first, then higher MOP priority
            return (exec_count, -mop_priority)

        sorted_actions = sorted(safe_actions, key=sort_key)
        return sorted_actions[0]
