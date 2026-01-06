"""
Simulated Annealing exploration strategy for RVAgent.

Adapts progressively from exploration (high temperature) to exploitation (low temperature),
similar to the metallurgical annealing process. Starts with random exploration and gradually
focuses on known high-value actions.
"""

import logging
import math
import random
import time
from typing import Dict, List, Optional, Set, Tuple

from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_agent.strategies.base_strategy import ExplorationStrategy
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction
from rv_android_core.domain.static import StaticAnalysisData

logger = logging.getLogger(__name__)


class SimulatedAnnealingStrategy(ExplorationStrategy):
    """
    Simulated annealing strategy that balances exploration and exploitation over time.

    ### Algorithm Implementation:
    - **Temperature**: Controls randomness (high temp = more exploration)
    - **Cooling**: Temperature decreases over time (gradually focuses)
    - **Acceptance**: Accept suboptimal actions with probability based on temperature
    - **Value Learning**: Updates action values based on execution feedback

    ### Temperature Schedule:
    - Initial: 10.0 (very exploratory)
    - Cooling rate: 0.95 every 30 seconds
    - Minimum: 0.1 (mostly exploitative, but not purely greedy)

    ### Comparison to Other Strategies:
    - **DFS/BFS**: Fixed exploration pattern
    - **Greedy**: Always exploits, little exploration
    - **Simulated Annealing**: Adapts exploration/exploitation over time

    ### Trade-offs:
    - **Advantages**: Avoids local optima, adapts to test duration, balanced exploration
    - **Disadvantages**: More complex, slower initial progress
    - **Best for**: Long test sessions, diverse exploration, avoiding getting stuck
    """

    def __init__(
        self,
        graph: DynamicStateGraph,
        static_data: Optional[StaticAnalysisData] = None,
        coordinate_converter = None
    ):
        """
        Initialize simulated annealing exploration strategy.

        Args:
            graph: Dynamic state graph for history tracking
            static_data: Optional static analysis data for MOP markers
            coordinate_converter: Optional coordinate converter for space transformations
        """
        self.graph = graph
        self.static_data = static_data
        self.converter = coordinate_converter

        # Action value tracking
        self.action_values: Dict[Tuple[Tuple[int, int], str], float] = {}
        self.action_attempts: Dict[Tuple[Tuple[int, int], str], int] = {}
        self.action_new_states: Dict[Tuple[Tuple[int, int], str], int] = {}

        # Simulated annealing parameters
        self.initial_temperature = 10.0
        self.temperature = self.initial_temperature
        self.cooling_rate = 0.95
        self.min_temperature = 0.1
        self.start_time = time.time()

        # Visited states tracking
        self.visited_states: Set[str] = set()

        logger.info(f"Simulated Annealing strategy initialized (T={self.temperature:.1f})")

    def select_next_action(
        self,
        current_hash: str,
        screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Select action using simulated annealing principles.

        ### Selection Process:
        1. Update temperature (cooling schedule)
        2. Filter invalid actions
        3. Calculate value for each action
        4. Determine exploration vs exploitation (based on temperature)
        5. Select action:
           - Exploration: Weighted random (favors high-value but probabilistic)
           - Exploitation: Simulated annealing acceptance (best with probability of suboptimal)

        Args:
            current_hash: Structural hash of current UI state
            screen_desc: Parsed screen with UI elements and actions

        Returns:
            Selected action or None if no actions available
        """
        # Update temperature first
        self._update_temperature()

        logger.debug(f"SimAnneal: Processing state {current_hash[:8]}, T={self.temperature:.2f}")

        # Create or update graph node
        if current_hash not in self.graph.states:
            node = self.graph.get_or_create_state(
                current_hash,
                screen_desc.activity,
                screen_desc
            )
            logger.info(f"SimAnneal: New state, {node.total_actions} actions")
        else:
            node = self.graph.states[current_hash]
            logger.info(f"SimAnneal: Revisited state (visit {node.visit_count})")

        self.visited_states.add(current_hash)

        # Get all available actions
        all_actions = screen_desc.get_all_actions()

        # Filter actions
        filtered_actions = self._filter_actions(all_actions)

        # Identify untested actions
        untested_actions = self._get_untested_actions(node, filtered_actions)

        # Log exploration state
        exploration_prob = self._get_exploration_probability()
        logger.info(f"SimAnneal State Analysis - {current_hash[:8]}:")
        logger.info(f"  Temperature: {self.temperature:.2f}")
        logger.info(f"  Exploration prob: {exploration_prob:.2f}")
        logger.info(f"  Total actions: {len(filtered_actions)}")
        logger.info(f"  Untested: {len(untested_actions)}")

        # If no untested actions, state is exhausted
        if not untested_actions:
            logger.info(f"SimAnneal: State {current_hash[:8]} exhausted")
            return None

        # Calculate values for all untested actions
        action_values = {}
        for action in untested_actions:
            action_signature = self._convert_signature_to_optimized(action.coords_for_matching)
            value = self._calculate_action_value(action, action_signature)
            action_values[action.id] = value

        # Decide exploration vs exploitation based on temperature
        if random.random() < exploration_prob:
            # EXPLORATION: Weighted random selection
            selected_action = self._weighted_random_selection(untested_actions, action_values)
            logger.info(f"SimAnneal EXPLORE: Weighted random ID={selected_action.id}")
        else:
            # EXPLOITATION: Annealing selection (best with probabilistic acceptance)
            selected_action = self._annealing_selection(untested_actions, action_values)
            logger.info(f"SimAnneal EXPLOIT: Annealing selection ID={selected_action.id}")

        # Log selection details
        action_signature = self._convert_signature_to_optimized(selected_action.coords_for_matching)
        logger.info(f"  Value: {action_values.get(selected_action.id, 0.5):.2f}")
        logger.info(f"  Signature: {action_signature}")
        logger.info(f"  Priority: {self._get_mop_priority(selected_action)}")

        # Mark action as executed
        self.graph.record_action(screen_hash=current_hash, action_signature=action_signature)

        return selected_action

    def record_transition(
        self,
        from_hash: str,
        to_hash: str,
        action: ItemAction
    ):
        """
        Record state transition and update action values.

        Args:
            from_hash: Structural hash of source state
            to_hash: Structural hash of destination state
            action: Action that triggered the transition
        """
        action_signature = self._convert_signature_to_optimized(action.coords_for_matching)

        # Update attempt counter
        self.action_attempts[action_signature] = self.action_attempts.get(action_signature, 0) + 1

        # Check if new state discovered
        if to_hash not in self.visited_states:
            self.action_new_states[action_signature] = self.action_new_states.get(action_signature, 0) + 1
            logger.debug(f"SimAnneal: Action discovered new state")

        # Update value
        self._update_action_value(action_signature, success=True, new_state=(to_hash not in self.visited_states))

    def should_backtrack(self, current_hash: str) -> bool:
        """
        Determine if backtracking is needed.

        Args:
            current_hash: Structural hash of current state

        Returns:
            True if all actions explored
        """
        node = self.graph.states.get(current_hash)
        if not node:
            return False

        return len(node.executed_actions) >= node.total_actions

    def reset(self):
        """Reset strategy state for new exploration session."""
        self.visited_states.clear()
        self.temperature = self.initial_temperature
        self.start_time = time.time()
        logger.info("SimulatedAnnealing strategy reset")

    def _update_temperature(self):
        """
        Update temperature based on elapsed time (cooling schedule).

        Cools exponentially every 30 seconds, enforces minimum temperature.
        """
        if self.temperature <= self.min_temperature:
            return

        elapsed_time = time.time() - self.start_time
        elapsed_intervals = elapsed_time / 30  # Cool every 30 seconds

        # Exponential cooling
        self.temperature = self.initial_temperature * (self.cooling_rate ** elapsed_intervals)

        # Enforce minimum
        self.temperature = max(self.min_temperature, self.temperature)

    def _get_exploration_probability(self) -> float:
        """
        Calculate probability of exploring vs exploiting.

        Returns:
            Exploration probability [0-1], higher temperature = more exploration
        """
        return self.temperature / self.initial_temperature

    def _weighted_random_selection(
        self,
        actions: List[ItemAction],
        values: Dict[int, float]
    ) -> ItemAction:
        """
        Select action using weighted random sampling.

        Higher-value actions are more likely to be selected, but all have a chance.

        Args:
            actions: Available actions
            values: Action values

        Returns:
            Selected action
        """
        # Calculate weights (exponential to amplify differences)
        weights = []
        for action in actions:
            value = values.get(action.id, 0.5)
            # Exponential weight to make high-value actions more likely
            weight = math.exp(value)
            weights.append(weight)

        # Weighted random choice
        total_weight = sum(weights)
        if total_weight <= 0:
            return random.choice(actions)

        selection_point = random.uniform(0, total_weight)
        cumulative = 0

        for action, weight in zip(actions, weights):
            cumulative += weight
            if cumulative >= selection_point:
                return action

        return actions[-1]  # Fallback

    def _annealing_selection(
        self,
        actions: List[ItemAction],
        values: Dict[int, float]
    ) -> ItemAction:
        """
        Select action using simulated annealing acceptance criterion.

        Selects best action most of the time, but accepts suboptimal actions
        with probability based on temperature (avoids local optima).

        Args:
            actions: Available actions
            values: Action values

        Returns:
            Selected action
        """
        # Find best action
        best_action = max(actions, key=lambda a: values.get(a.id, 0.0))
        best_value = values.get(best_action.id, 0.0)

        # With probability based on temperature, accept a random alternative
        if random.random() < math.exp(-1.0 / self.temperature):
            candidate = random.choice(actions)
            # Only accept if different from best
            if candidate.id != best_action.id:
                logger.debug(f"SimAnneal: Accepted suboptimal action (T={self.temperature:.2f})")
                return candidate

        return best_action

    def _calculate_action_value(
        self,
        action: ItemAction,
        action_signature: Tuple[Tuple[int, int], str]
    ) -> float:
        """
        Calculate action value for annealing selection.

        Args:
            action: ItemAction to evaluate
            action_signature: Optimized coordinate signature

        Returns:
            Estimated value
        """
        # Start with historical value
        value = self.action_values.get(action_signature, 0.5)

        # MOP prioritization
        if getattr(action, 'directly_reaches_mop', False):
            value += 0.3
        elif getattr(action, 'reaches_mop', False):
            value += 0.2

        # New state discovery bonus
        if action_signature in self.action_new_states:
            attempts = self.action_attempts.get(action_signature, 1)
            new_states = self.action_new_states[action_signature]
            value += (new_states / attempts) * 0.3

        # Exploration bonus (decreases with attempts)
        attempts = self.action_attempts.get(action_signature, 0)
        if attempts == 0:
            value += 0.2
        else:
            value += 0.1 / math.sqrt(attempts)

        return value

    def _update_action_value(
        self,
        action_signature: Tuple[Tuple[int, int], str],
        success: bool,
        new_state: bool
    ):
        """
        Update action value based on execution outcome.

        Args:
            action_signature: Action coordinate signature
            success: Whether action executed successfully
            new_state: Whether action led to new state
        """
        reward = 0.5
        if success:
            reward += 0.1
        if new_state:
            reward += 0.4

        current_value = self.action_values.get(action_signature, 0.5)
        attempts = self.action_attempts.get(action_signature, 1)

        # Decreasing learning rate
        learning_rate = 1.0 / math.sqrt(max(1, attempts))
        new_value = current_value + learning_rate * (reward - current_value)

        # Clamp
        new_value = max(0.0, min(2.0, new_value))

        self.action_values[action_signature] = new_value

    # Re-use filtering methods from Greedy (same implementation)
    def _filter_actions(self, actions: List[ItemAction]) -> List[ItemAction]:
        """Filter out system actions and navigation bar interactions."""
        filtered = []
        for action in actions:
            if action.target_view.get('system_action', False):
                continue
            coords = action.get_execution_coordinates()
            if not coords:
                logger.debug(f"Filtered action without coordinates: ID={action.id}")
                continue
            x, y = coords
            if y > 1794:
                continue
            filtered.append(action)
        return filtered

    def _get_untested_actions(self, node, actions: List[ItemAction]) -> List[ItemAction]:
        """Identify actions not yet executed on this state."""
        untested = []
        for action in actions:
            action_signature = self._convert_signature_to_optimized(action.coords_for_matching)
            if action_signature not in node.executed_actions:
                untested.append(action)
        return untested

    def _convert_signature_to_optimized(self, signature: Tuple[Tuple[int, int], str]) -> Tuple[Tuple[int, int], str]:
        """Convert action signature to optimized space."""
        if not self.converter:
            return signature
        coords, action_type = signature
        optimized_coords = self.converter.device_to_optimized(coords)
        return (optimized_coords, action_type)

    def _get_mop_priority(self, action: ItemAction) -> int:
        """Compute MOP priority score."""
        if getattr(action, 'directly_reaches_mop', False):
            return 3
        elif getattr(action, 'reaches_mop', False):
            return 2
        return 1
