"""
Basic strategies for RVDroid.

This module provides implementations of fundamental exploration strategies
including random, systematic, greedy, and model-based approaches.
"""

import random
from typing import Dict, Any, List, Optional, Set, Tuple

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.strategy.strategy import Strategy, StrategyRegistry


class RandomStrategy(Strategy):
    """
    Strategy that randomly selects actions from the available options.

    Uses weighted random selection to prioritize certain types of actions
    while maintaining exploration randomness.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "RandomStrategy"):
        """
        Initialize the random strategy.

        Args:
            static_data: Optional static analysis data
            name: Strategy name
        """
        super().__init__(static_data, name)

        # Weights for different action types
        self.weights = {
            "click": 1.0,
            "long_click": 0.5,
            "scroll": 0.7,
            "text_input": 0.8,
            "back": 0.3
        }

        # Tracking for previously executed actions
        self.executed_actions: Set[int] = set()

    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate a random action from the available options.

        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions

        Returns:
            Randomly selected ItemAction or None if no actions available
        """
        if not screen.items:
            self.logger.warning("No UI elements available for interaction")
            return None

        # Collect all available actions with weights
        weighted_actions = []

        for item in screen.items:
            for action in item.actions:
                # Determine action type from text
                action_type = self._get_action_type(action.text)

                # Get weight for this action type
                weight = self.weights.get(action_type, 0.5)

                # Adjust weight if the action reaches security-sensitive code
                if action.reaches_mop:
                    weight *= 1.5

                # Reduce weight for previously executed actions
                if action.id in self.executed_actions:
                    weight *= 0.7

                weighted_actions.append((action, weight))

        if not weighted_actions:
            self.logger.warning("No weighted actions available")
            return None

        # Select an action using weighted random
        return self._weighted_random_selection(weighted_actions)

    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update strategy based on action execution feedback.

        Args:
            action: Action that was executed
            result: Execution result with success status and state change info
        """
        # Record executed action
        self.executed_actions.add(action.id)

        # Adjust weights based on results
        action_type = self._get_action_type(action.text)

        # Increase weight for successful actions that lead to new states
        if result.get("success", False) and result.get("new_state", False):
            self.weights[action_type] = min(2.0, self.weights.get(action_type, 1.0) * 1.1)

        # Decrease weight for failed actions
        elif not result.get("success", False):
            self.weights[action_type] = max(0.1, self.weights.get(action_type, 1.0) * 0.9)

    def _get_action_type(self, action_text: str) -> str:
        """
        Extract action type from action text.

        Args:
            action_text: Text description of the action

        Returns:
            Action type string
        """
        if "CLICK" in action_text:
            return "click"
        elif "LONG_CLICK" in action_text:
            return "long_click"
        elif "SCROLL" in action_text:
            return "scroll"
        elif "SET_TEXT" in action_text:
            return "text_input"
        elif "BACK" in action_text:
            return "back"
        else:
            return "other"

    def _weighted_random_selection(self, weighted_items: List[Tuple[Any, float]]) -> Any:
        """
        Select an item using weighted random selection.

        Args:
            weighted_items: List of (item, weight) tuples

        Returns:
            Selected item
        """
        items, weights = zip(*weighted_items)
        total_weight = sum(weights)

        # If all weights are zero, use uniform selection
        if total_weight <= 0:
            return random.choice(items)

        # Weight-based selection
        selection = random.uniform(0, total_weight)
        current = 0

        for i, weight in enumerate(weights):
            current += weight
            if selection <= current:
                return items[i]

        # Fallback to last item
        return items[-1]


class SystematicStrategy(Strategy):
    """
    Strategy that methodically explores UI elements to ensure coverage.

    Systematically works through all available actions to ensure
    comprehensive coverage of the application's UI.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "SystematicStrategy"):
        """
        Initialize the systematic strategy.

        Args:
            static_data: Optional static analysis data
            name: Strategy name
        """
        super().__init__(static_data, name)

        # Track exploration progress
        self.explored_actions: Set[int] = set()
        self.current_item_index = 0
        self.current_action_index = 0

        # Prioritized action types (in order of execution)
        self.action_priorities = [
            "click",
            "text_input",
            "scroll",
            "long_click",
            "back"
        ]

    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate the next action in a systematic exploration sequence.

        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions

        Returns:
            Next action in systematic sequence or None if no actions available
        """
        if not screen.items:
            self.logger.warning("No UI elements available for interaction")
            return None

        # Reset indices if screen has changed significantly
        if self.current_item_index >= len(screen.items):
            self.current_item_index = 0
            self.current_action_index = 0

        # Group actions by type for prioritized execution
        prioritized_actions = []

        # First, try to find unexplored actions
        for priority_type in self.action_priorities:
            for item_idx, item in enumerate(screen.items):
                for action_idx, action in enumerate(item.actions):
                    action_type = self._get_action_type(action.text)

                    # Check if this action matches the current priority and is unexplored
                    if action_type == priority_type and action.id not in self.explored_actions:
                        prioritized_actions.append((item_idx, action_idx, action))

        # If no unexplored actions found, go through all actions
        if not prioritized_actions:
            for priority_type in self.action_priorities:
                for item_idx, item in enumerate(screen.items):
                    for action_idx, action in enumerate(item.actions):
                        action_type = self._get_action_type(action.text)

                        # Check if this action matches the current priority
                        if action_type == priority_type:
                            prioritized_actions.append((item_idx, action_idx, action))

        if not prioritized_actions:
            self.logger.warning("No prioritized actions available")
            return None

        # Get the first prioritized action
        item_idx, action_idx, action = prioritized_actions[0]

        # Update indices for next call
        self.current_item_index = item_idx
        self.current_action_index = action_idx + 1

        return action

    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update strategy based on action execution feedback.

        Args:
            action: Action that was executed
            result: Execution result with success status and state change info
        """
        # Mark action as explored
        self.explored_actions.add(action.id)

        # If we've explored a high percentage of actions, reset to allow re-exploration
        if len(self.explored_actions) > 50:  # Arbitrary threshold
            self.explored_actions.clear()

    def _get_action_type(self, action_text: str) -> str:
        """
        Extract action type from action text.

        Args:
            action_text: Text description of the action

        Returns:
            Action type string
        """
        if "CLICK" in action_text:
            return "click"
        elif "LONG_CLICK" in action_text:
            return "long_click"
        elif "SCROLL" in action_text:
            return "scroll"
        elif "SET_TEXT" in action_text:
            return "text_input"
        elif "BACK" in action_text:
            return "back"
        else:
            return "other"


class GreedyStrategy(Strategy):
    """
    Strategy that prioritizes unexplored UI elements and security-sensitive operations.

    Greedily selects actions that lead to unexplored areas of the application
    or that trigger security-sensitive operations.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "GreedyStrategy"):
        """
        Initialize the greedy strategy.

        Args:
            static_data: Optional static analysis data
            name: Strategy name
        """
        super().__init__(static_data, name)

        # Track exploration progress
        self.executed_actions: Set[int] = set()
        self.action_scores: Dict[int, float] = {}

        # State history tracking
        self.visited_states: Set[str] = set()
        self.state_action_results: Dict[str, Dict[int, bool]] = {}

    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate an action using a greedy approach prioritizing unexplored elements.

        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions

        Returns:
            Action with highest exploration value or None if no actions available
        """
        if not screen.items:
            self.logger.warning("No UI elements available for interaction")
            return None

        # Get current state fingerprint
        state_fingerprint = state_data.get("fingerprint", "unknown")

        # Track visited state
        self.visited_states.add(state_fingerprint)

        # Initialize state action results if not already tracked
        if state_fingerprint not in self.state_action_results:
            self.state_action_results[state_fingerprint] = {}

        # Score each action based on exploration value
        scored_actions = []

        for item in screen.items:
            for action in item.actions:
                # Calculate base score
                score = self._calculate_action_score(action, state_fingerprint)

                # Adjust for security-sensitivity
                if action.reaches_mop:
                    score *= 1.5

                # Adjust for previously executed actions
                if action.id in self.executed_actions:
                    score *= 0.7

                # Store score for future reference
                self.action_scores[action.id] = score

                scored_actions.append((action, score))

        if not scored_actions:
            self.logger.warning("No scored actions available")
            return None

        # Sort by score (highest first)
        scored_actions.sort(key=lambda x: x[1], reverse=True)

        # Return highest-scoring action
        return scored_actions[0][0]

    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update strategy based on action execution feedback.

        Args:
            action: Action that was executed
            result: Execution result with success status and state change info
        """
        # Record executed action
        self.executed_actions.add(action.id)

        # Get current state fingerprint
        state_fingerprint = result.get("state_fingerprint", "unknown")

        # Record result for this action in this state
        self.state_action_results[state_fingerprint][action.id] = result.get("success", False)

        # Update action score based on result
        current_score = self.action_scores.get(action.id, 1.0)

        # Increase score for successful actions that lead to new states
        if result.get("success", False) and result.get("new_state", False):
            self.action_scores[action.id] = current_score * 1.2

        # Decrease score for failed actions
        elif not result.get("success", False):
            self.action_scores[action.id] = current_score * 0.8

    def _calculate_action_score(self, action: ItemAction, state_fingerprint: str) -> float:
        """
        Calculate exploration score for an action.

        Args:
            action: Action to score
            state_fingerprint: Current state fingerprint

        Returns:
            Exploration score
        """
        # Base score
        score = 1.0

        # Prioritize actions we haven't tried in this state
        if state_fingerprint in self.state_action_results:
            if action.id not in self.state_action_results[state_fingerprint]:
                score += 2.0
        else:
            # New state, prioritize all actions
            score += 1.0

        # Prioritize actions we haven't tried anywhere
        if action.id not in self.executed_actions:
            score += 1.5

        # Prioritize clicks on interactive elements
        if "CLICK" in action.text:
            score += 0.5

        # Prioritize text input on editable fields
        if "SET_TEXT" in action.text:
            score += 0.7

        return score


class ModelBasedStrategy(Strategy):
    """
    Strategy that learns from exploration to build a model of the application.

    Builds a model of the application's behavior during exploration and
    uses that model to guide future testing decisions.
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "ModelBasedStrategy"):
        """
        Initialize the model-based strategy.

        Args:
            static_data: Optional static analysis data
            name: Strategy name
        """
        super().__init__(static_data, name)

        # Model components
        self.state_transitions: Dict[str, Dict[int, str]] = {}
        self.action_success_rates: Dict[int, Dict[str, float]] = {}
        self.state_values: Dict[str, float] = {}

        # Exploration parameters
        self.exploration_factor = 0.2  # Balance exploration vs exploitation
        self.learning_rate = 0.1  # Rate of model updates
        self.discount_factor = 0.9  # Value of future rewards

    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate an action based on learned model and exploration policy.

        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions

        Returns:
            Action selected by model or exploration policy
        """
        if not screen.items:
            self.logger.warning("No UI elements available for interaction")
            return None

        # Get current state fingerprint
        current_state = state_data.get("fingerprint", "unknown")

        # Collect all available actions
        available_actions = []
        for item in screen.items:
            available_actions.extend(item.actions)

        if not available_actions:
            self.logger.warning("No available actions")
            return None

        # Decide whether to explore or exploit
        if random.random() < self.exploration_factor:
            # Exploration: choose a random action
            self.logger.debug("Using exploration strategy")
            return random.choice(available_actions)
        else:
            # Exploitation: choose action based on model
            self.logger.debug("Using exploitation strategy")
            return self._select_best_action(available_actions, current_state)

    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update model based on action execution feedback.

        Args:
            action: Action that was executed
            result: Execution result with success status and state change info
        """
        # Extract information from result
        success = result.get("success", False)
        previous_state = result.get("previous_state", "unknown")
        current_state = result.get("state_fingerprint", "unknown")
        new_state = result.get("new_state", False)

        # Update state transitions
        if previous_state not in self.state_transitions:
            self.state_transitions[previous_state] = {}

        self.state_transitions[previous_state][action.id] = current_state

        # Update action success rates
        if action.id not in self.action_success_rates:
            self.action_success_rates[action.id] = {}

        if previous_state not in self.action_success_rates[action.id]:
            self.action_success_rates[action.id][previous_state] = 0.5  # Initial estimate

        # Update success rate using learning rate
        current_rate = self.action_success_rates[action.id][previous_state]
        updated_rate = current_rate + self.learning_rate * (1.0 if success else 0.0 - current_rate)
        self.action_success_rates[action.id][previous_state] = updated_rate

        # Update state values
        if current_state not in self.state_values:
            self.state_values[current_state] = 0.0

        if previous_state not in self.state_values:
            self.state_values[previous_state] = 0.0

        # Calculate reward
        reward = 0.0
        if success:
            reward += 0.1
        if new_state:
            reward += 1.0

        # Update state value using temporal difference learning
        current_value = self.state_values[previous_state]
        next_value = self.state_values[current_state]
        updated_value = current_value + self.learning_rate * (
                reward + self.discount_factor * next_value - current_value)
        self.state_values[previous_state] = updated_value

    def _select_best_action(self, available_actions: List[ItemAction], current_state: str) -> ItemAction:
        """
        Select the best action based on the learned model.

        Args:
            available_actions: List of available actions
            current_state: Current state fingerprint

        Returns:
            Best action according to model
        """
        best_action = None
        best_value = float('-inf')

        for action in available_actions:
            # Calculate action value
            action_value = self._calculate_action_value(action, current_state)

            if action_value > best_value:
                best_value = action_value
                best_action = action

        # If no good action found, choose randomly
        if best_action is None:
            best_action = random.choice(available_actions)

        return best_action

    def _calculate_action_value(self, action: ItemAction, current_state: str) -> float:
        """
        Calculate the value of an action in the current state.

        Args:
            action: Action to evaluate
            current_state: Current state fingerprint

        Returns:
            Estimated value of the action
        """
        # Check if we have transition data for this action
        next_state = None
        if current_state in self.state_transitions and action.id in self.state_transitions[current_state]:
            next_state = self.state_transitions[current_state][action.id]

        # Get success rate for this action in this state
        success_rate = 0.5  # Default estimate
        if action.id in self.action_success_rates and current_state in self.action_success_rates[action.id]:
            success_rate = self.action_success_rates[action.id][current_state]

        # Get next state value
        next_state_value = 0.0
        if next_state and next_state in self.state_values:
            next_state_value = self.state_values[next_state]

        # Calculate action value using a combination of success rate and expected next state value
        action_value = success_rate + self.discount_factor * next_state_value

        # Adjust for security-sensitive operations
        if action.reaches_mop:
            action_value *= 1.2

        return action_value


# Register strategies with the registry
StrategyRegistry.register(RandomStrategy)
StrategyRegistry.register(SystematicStrategy)
StrategyRegistry.register(GreedyStrategy)
StrategyRegistry.register(ModelBasedStrategy)
