# rvandroid/rvdroid/strategy/basic_strategies.py

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

    ### Architectural Decisions:
    - Implements a weighted random selection algorithm for action prioritization
    - Tracks previously executed actions to prevent repetitive behavior
    - Adapts weights based on execution results to improve future selection
    - Uses configurable weights for different action types

    ### Role in the System:
    - Provides baseline exploration functionality with randomized selection
    - Ensures adequate coverage through probabilistic selection patterns
    - Balances exploration by giving higher weights to important elements
    - Learns from execution feedback to improve selection effectiveness
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "RandomStrategy"):
        """
        Initialize the random strategy.

        Args:
            static_data: Optional static analysis data
            name: Strategy name
        """
        super().__init__(static_data, name)

        # Weights for different action types - these affect selection probability
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
        Generate a random action from the available options with improved prioritization for text fields and spinners.

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

        # First, check if there are any text fields or spinners we should prioritize
        text_fields = []
        spinners = []

        # Identify text fields and spinners
        for item in screen.items:
            if hasattr(item, 'view') and item.view:
                class_name = item.view.get("class", "")

                # Check for EditText
                if "EditText" in class_name:
                    for action in item.actions:
                        if "SET_TEXT" in action.text:
                            text_fields.append(action)

                # Check for Spinner
                if "Spinner" in class_name or "DropDown" in class_name:
                    for action in item.actions:
                        if "CLICK" in action.text:
                            spinners.append(action)

        # Prioritize text fields and spinners that haven't been interacted with yet
        for priority_list, priority_name, weight_multiplier in [
            (text_fields, "text field", 3.0),
            (spinners, "spinner", 2.5)
        ]:
            if priority_list and not all(a.id in self.executed_actions for a in priority_list):
                # Find ones we haven't executed yet
                unexecuted = [a for a in priority_list if a.id not in self.executed_actions]
                if unexecuted:
                    # Highly prioritize unexecuted text fields and spinners
                    self.logger.info(f"Prioritizing unexecuted {priority_name}: {len(unexecuted)} available")
                    selected = random.choice(unexecuted)
                    return selected

        # Regular weighted action selection (existing code) with increased weights for text fields and spinners
        for item in screen.items:
            for action in item.actions:
                # Determine action type from text
                action_type = self._get_action_type(action.text)

                # Get weight for this action type
                weight = self.weights.get(action_type, 0.5)

                # Get element class
                element_class = ""
                if hasattr(action, 'target_view') and action.target_view:
                    element_class = action.target_view.get("class", "")

                # Significantly boost weight for text fields and spinners
                if "EditText" in element_class:
                    weight *= 3.0  # Triple weight for text fields
                elif "Spinner" in element_class or "DropDown" in element_class:
                    weight *= 2.5  # 2.5x weight for spinners

                # IMPROVEMENT: Check for element text/label - prioritize elements with text
                element_text = ""
                if hasattr(action, 'target_view') and action.target_view:
                    element_text = action.target_view.get("text", "")

                # IMPROVEMENT: Significantly boost weight for buttons with descriptive text
                if element_text and len(element_text) > 3:
                    # Prioritize important-looking buttons with descriptive labels
                    weight *= 2.0

                    # Extra boost for elements containing key terms
                    key_terms = ["message", "digest", "cipher", "encrypt", "decrypt",
                                 "generate", "key", "hash", "security", "login", "password"]
                    if any(term.lower() in element_text.lower() for term in key_terms):
                        weight *= 1.5

                # IMPROVEMENT: Better handling of security-related operations
                # Significantly increase weight for security-sensitive operations
                if action.reaches_mop:
                    weight *= 3.0  # Triple the weight (was 1.5)

                    # Even higher priority for direct security operations
                    if action.directly_reaches_mop:
                        weight *= 1.5

                # IMPROVEMENT: Check static analysis for potential transitions
                # If we have static data, prioritize actions that lead to new activities
                if self.static_data and hasattr(self.static_data, 'wtg'):
                    # This would check if the action could lead to a transition in the Window Transition Graph
                    # Since we can't access the full details, we'll prioritize clicks on Buttons
                    # which are more likely to trigger transitions
                    if "Button" in str(action.target_view.get("class", "")) and "CLICK" in action.text:
                        weight *= 1.8

                # Reduce weight for previously executed actions
                if action.id in self.executed_actions:
                    weight *= 0.5  # Reduced further to prioritize unexplored actions

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

    ### Architectural Decisions:
    - Implements a prioritized, methodical exploration approach
    - Tracks exploration progress to ensure complete UI coverage
    - Uses a structured ordering of action types for systematic testing
    - Rotates through all UI elements before revisiting previously tested ones

    ### Role in the System:
    - Provides methodical, comprehensive coverage of the application
    - Ensures all UI elements are tested in a predictable order
    - Complements random strategies by guaranteeing exploration completeness
    - Prevents exploration bias by following a predetermined element order
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

        # IMPROVEMENT: Create prioritized categories to ensure important elements are tested first
        categories = {
            "high_value": [],  # Security-related, labeled buttons
            "medium_value": [],  # Other interactive elements
            "low_value": []  # Basic elements with no special properties
        }

        # Group actions by priority category
        for item_idx, item in enumerate(screen.items):
            for action_idx, action in enumerate(item.actions):
                action_type = self._get_action_type(action.text)

                # Create action entry with indices
                action_entry = (item_idx, action_idx, action)

                # IMPROVEMENT: Check for descriptive text/label
                element_text = ""
                if hasattr(action, 'target_view') and action.target_view:
                    element_text = action.target_view.get("text", "")

                # Security-sensitive operations go to high_value category
                if action.reaches_mop or action.directly_reaches_mop:
                    categories["high_value"].append(action_entry)
                    continue

                # IMPROVEMENT: Buttons with text are high value
                if element_text and "Button" in str(action.target_view.get("class", "")):
                    categories["high_value"].append(action_entry)
                    continue

                # IMPROVEMENT: Elements with text are medium value
                if element_text:
                    categories["medium_value"].append(action_entry)
                    continue

                # Everything else is low value
                categories["low_value"].append(action_entry)

        # IMPROVEMENT: Within each category, prioritize by action type
        for category in categories.values():
            category.sort(key=lambda entry:
            self.action_priorities.index(self._get_action_type(entry[2].text))
            if self._get_action_type(entry[2].text) in self.action_priorities else len(self.action_priorities)
                          )

        # IMPROVEMENT: For each category, prioritize unexplored actions
        prioritized_actions = []

        # Process high value elements first, then medium, then low
        for category_name in ["high_value", "medium_value", "low_value"]:
            category = categories[category_name]

            # First try unexplored actions in this category
            unexplored = [entry for entry in category if entry[2].id not in self.explored_actions]
            if unexplored:
                prioritized_actions.extend(unexplored)
            else:
                # If all explored, add them anyway for completeness
                prioritized_actions.extend(category)

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

        # IMPROVEMENT: If we've explored a high percentage of actions, reset with a higher threshold
        # This ensures we eventually revisit all elements while still prioritizing new actions
        if len(self.explored_actions) > 100:  # Higher threshold
            # Rather than clearing completely, keep track of security-sensitive operations
            security_actions = set()
            for action_id in self.explored_actions:
                # We don't have a way to check if an action reaches MOP by its ID alone
                # This would require maintaining a separate mapping
                pass

            # Reset but keep security-sensitive operations marked
            self.explored_actions = security_actions

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

    ### Architectural Decisions:
    - Implements a utility-maximizing approach to action selection
    - Uses a comprehensive scoring system for action evaluation
    - Adapts to execution results to improve future action selection
    - Maintains detailed tracking of action outcomes in different states

    ### Role in the System:
    - Optimizes exploration efficiency by prioritizing high-value actions
    - Focuses on security-sensitive operations and unexplored UI elements
    - Maximizes discovery of new application states
    - Balances between exploitation of known good actions and exploration of new ones
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
                # IMPROVEMENT: Calculate base score with more sophisticated approach
                score = self._calculate_action_score(action, state_fingerprint)

                # IMPROVEMENT: Significantly boost score for UI elements with text
                element_text = ""
                if hasattr(action, 'target_view') and action.target_view:
                    element_text = action.target_view.get("text", "")
                    element_class = action.target_view.get("class", "")

                    # Significant boost for buttons with descriptive text
                    if element_text and "Button" in str(element_class):
                        score += 5.0

                        # Extra boost for security-related terms in button text
                        security_terms = ["message", "digest", "cipher", "encrypt", "decrypt",
                                          "generate", "key", "hash", "security", "login", "password"]
                        if any(term.lower() in element_text.lower() for term in security_terms):
                            score += 3.0
                    # Moderate boost for any element with descriptive text
                    elif element_text:
                        score += 2.0

                # IMPROVEMENT: Major boost for security-sensitive operations
                if action.reaches_mop:
                    score *= 3.0  # Triple the score for security-sensitive operations

                    # Additional boost for direct security operations
                    if action.directly_reaches_mop:
                        score *= 1.5  # 50% extra boost for directly reaching security operations

                # IMPROVEMENT: Use static analysis data for better decision making
                if self.static_data:
                    # If we have WTG data, check if this action might trigger transitions
                    if hasattr(self.static_data, 'wtg') and self.static_data.wtg:
                        # Boost clicks on elements that may trigger transitions
                        if "CLICK" in action.text and "Button" in str(action.target_view.get("class", "")):
                            score += 3.0  # Substantial boost for potential transitions

                # Adjust for previously executed actions
                if action.id in self.executed_actions:
                    score *= 0.7  # Reduce score but still allow revisiting

                # Store score for future reference
                self.action_scores[action.id] = score
                scored_actions.append((action, score))

        if not scored_actions:
            self.logger.warning("No scored actions available")
            return None

        # Sort by score (highest first)
        scored_actions.sort(key=lambda x: x[1], reverse=True)

        # IMPROVEMENT: Log the top actions for debugging
        top_3 = scored_actions[:3] if len(scored_actions) >= 3 else scored_actions
        self.logger.debug(f"Top scored actions: {[(a[0].id, a[1], getattr(a[0], 'text', '')) for a in top_3]}")

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

        # Initialize state action results if not already tracked
        if state_fingerprint not in self.state_action_results:
            self.state_action_results[state_fingerprint] = {}

        # Record result for this action in this state
        self.state_action_results[state_fingerprint][action.id] = result.get("success", False)

        # Update action score based on result
        current_score = self.action_scores.get(action.id, 1.0)

        # IMPROVEMENT: More sophisticated feedback processing
        # Increase score for successful actions that lead to new states
        if result.get("success", False) and result.get("new_state", False):
            # Significant boost for actions that discover new states
            self.action_scores[action.id] = current_score * 1.5
        # Moderate boost for successful actions
        elif result.get("success", False):
            self.action_scores[action.id] = current_score * 1.1
        # Decrease score for failed actions
        else:
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

        # IMPROVEMENT: More nuanced scoring system

        # Factor 1: Prioritize actions we haven't tried in this state
        if state_fingerprint in self.state_action_results:
            if action.id not in self.state_action_results[state_fingerprint]:
                score += 3.0  # Major boost for untried actions in current state
        else:
            # New state, prioritize all actions
            score += 2.0

        # Factor 2: Prioritize actions we haven't tried anywhere
        if action.id not in self.executed_actions:
            score += 2.5  # Major boost for completely new actions

        # Factor 3: Action type preference
        if "CLICK" in action.text:
            score += 1.0  # Favor clicks as they're most likely to trigger transitions
        elif "SET_TEXT" in action.text:
            score += 0.8  # Text input fields are also valuable
        elif "LONG_CLICK" in action.text:
            score += 0.5  # Long clicks may reveal context menus

        # Factor 4: Element type preference
        if hasattr(action, 'target_view') and action.target_view:
            element_class = action.target_view.get("class", "")

            # Prioritize interactive elements
            if "Button" in str(element_class):
                score += 1.5  # Buttons are high-value targets
            elif "EditText" in str(element_class):
                score += 1.2  # Input fields are also valuable

        # Factor 5: Security operations (core calculation moved to main generate_action)
        if action.reaches_mop:
            score += 2.0

        return score


class ModelBasedStrategy(Strategy):
    """
    Strategy that learns from exploration to build a model of the application.

    ### Architectural Decisions:
    - Implements a reinforcement learning approach to action selection
    - Builds and maintains a model of application state transitions
    - Uses temporal difference learning to update state and action values
    - Balances exploration and exploitation through an epsilon-greedy approach

    ### Role in the System:
    - Leverages past experience to make informed testing decisions
    - Optimizes action selection based on historical results
    - Adapts to application behavior patterns over time
    - Provides sophisticated decision-making for complex application workflows
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

        # IMPROVEMENT: Track important elements separately
        self.security_actions: Set[int] = set()
        self.text_button_actions: Dict[int, str] = {}  # action_id -> button_text

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

        # IMPROVEMENT: Process all available actions and update knowledge
        available_actions = []
        for item in screen.items:
            for action in item.actions:
                # Track security actions
                if action.reaches_mop:
                    self.security_actions.add(action.id)

                # Track buttons with text
                if hasattr(action, 'target_view') and action.target_view:
                    element_text = action.target_view.get("text", "")
                    element_class = action.target_view.get("class", "")

                    if element_text and "Button" in str(element_class):
                        self.text_button_actions[action.id] = element_text

                available_actions.append(action)

        if not available_actions:
            self.logger.warning("No available actions")
            return None

        # IMPROVEMENT: Dynamic exploration factor based on state value
        # If we've never seen this state before, explore more
        if current_state not in self.state_values:
            exploration_chance = min(0.8, self.exploration_factor * 2)
        else:
            # Calculate based on state value - lower value means more exploration
            state_value = self.state_values.get(current_state, 0)
            # Map state value from [0,1] range to [0.1, 0.4] exploration chance
            exploration_chance = max(0.1, min(0.4, self.exploration_factor + (0.2 * (1 - state_value))))

        # Decide whether to explore or exploit
        if random.random() < exploration_chance:
            # IMPROVEMENT: Smarter exploration - prioritize security and text buttons
            # 40% chance to select a security action if any exist
            security_actions = [a for a in available_actions if a.id in self.security_actions]
            if security_actions and random.random() < 0.4:
                self.logger.debug("Using security-focused exploration")
                return random.choice(security_actions)

            # 30% chance to select a button with text if any exist
            text_button_action_ids = set(self.text_button_actions.keys())
            text_button_actions = [a for a in available_actions if a.id in text_button_action_ids]
            if text_button_actions and random.random() < 0.3:
                self.logger.debug("Using text button exploration")
                return random.choice(text_button_actions)

            # Otherwise choose a random action
            self.logger.debug("Using random exploration")
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

        # IMPROVEMENT: Track security operations for future reference
        if action.reaches_mop:
            self.security_actions.add(action.id)

            # Track if this action has text
            if hasattr(action, 'target_view') and action.target_view:
                element_text = action.target_view.get("text", "")
                if element_text:
                    self.logger.info(f"Security action with text '{element_text}' executed")

        # Update state transitions - ensure dictionaries exist before accessing
        if previous_state not in self.state_transitions:
            self.state_transitions[previous_state] = {}

        self.state_transitions[previous_state][action.id] = current_state

        # Update action success rates - ensure dictionaries exist
        if action.id not in self.action_success_rates:
            self.action_success_rates[action.id] = {}

        if previous_state not in self.action_success_rates[action.id]:
            self.action_success_rates[action.id][previous_state] = 0.5  # Initial estimate

        # Update success rate using learning rate
        current_rate = self.action_success_rates[action.id][previous_state]
        updated_rate = current_rate + self.learning_rate * (1.0 if success else 0.0 - current_rate)
        self.action_success_rates[action.id][previous_state] = updated_rate

        # Update state values - ensure keys exist
        if current_state not in self.state_values:
            self.state_values[current_state] = 0.0

        if previous_state not in self.state_values:
            self.state_values[previous_state] = 0.0

        # IMPROVEMENT: More sophisticated reward calculation
        # Calculate reward with enhanced factors
        reward = 0.0

        # Base reward for successful action
        if success:
            reward += 0.1

        # Major reward for discovering new state
        if new_state:
            reward += 1.0

        # Bonus reward for security operations
        if action.id in self.security_actions:
            reward += 0.5

        # Bonus reward for buttons with text
        if action.id in self.text_button_actions:
            reward += 0.3

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

        # IMPROVEMENT: Track scores for logging
        action_values = []

        for action in available_actions:
            # Calculate action value
            action_value = self._calculate_action_value(action, current_state)
            action_values.append((action, action_value))

            if action_value > best_value:
                best_value = action_value
                best_action = action

        # IMPROVEMENT: Log top actions for debugging
        action_values.sort(key=lambda x: x[1], reverse=True)
        top_actions = action_values[:3] if len(action_values) >= 3 else action_values

        # Format log message with action descriptions
        action_descriptions = []
        for a, value in top_actions:
            desc = f"ID={a.id}, Value={value:.2f}"
            # Add text if available
            if a.id in self.text_button_actions:
                desc += f", Text='{self.text_button_actions[a.id]}'"
            # Add security info
            if a.id in self.security_actions:
                desc += ", Security=True"
            action_descriptions.append(desc)

        self.logger.debug(f"Top actions: {action_descriptions}")

        # If no good action found, choose randomly
        if best_action is None:
            self.logger.debug("No good action found, choosing randomly")
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
        # IMPROVEMENT: More comprehensive action evaluation
        # Start with a base value
        action_value = 0.0

        # Factor 1: Transition data - Check if we have seen this action in this state before
        next_state = None
        if current_state in self.state_transitions and action.id in self.state_transitions[current_state]:
            next_state = self.state_transitions[current_state][action.id]

            # If we've seen this transition before, consider the value of the next state
            if next_state in self.state_values:
                next_state_value = self.state_values[next_state]
                action_value += self.discount_factor * next_state_value

        # Factor 2: Success rate - Actions that succeed more often are preferred
        success_rate = 0.5  # Default estimate
        if action.id in self.action_success_rates and current_state in self.action_success_rates[action.id]:
            success_rate = self.action_success_rates[action.id][current_state]

        action_value += success_rate

        # IMPROVEMENT: Factor 3 - Security operations are highly valuable
        if action.id in self.security_actions:
            action_value *= 2.0  # Double the value for security operations

        # IMPROVEMENT: Factor 4 - Buttons with text are valuable
        if action.id in self.text_button_actions:
            # Extra value for buttons with security-related text
            text = self.text_button_actions[action.id].lower()
            security_terms = ["message", "digest", "cipher", "encrypt", "decrypt",
                              "generate", "key", "hash", "security", "login", "password"]

            if any(term in text for term in security_terms):
                action_value *= 1.8  # 80% boost for security-related buttons
            else:
                action_value *= 1.4  # 40% boost for any button with text

        # IMPROVEMENT: Factor 5 - Use action properties from current screen
        # This ensures we're using the most up-to-date information
        if action.reaches_mop:
            action_value *= 1.5  # 50% boost for any security operation

            if action.directly_reaches_mop:
                action_value *= 1.2  # Additional 20% for direct security operations

        # IMPROVEMENT: Factor 6 - Element type preference
        if hasattr(action, 'target_view') and action.target_view:
            element_class = action.target_view.get("class", "")

            # Buttons are more likely to trigger transitions
            if "Button" in str(element_class):
                action_value *= 1.3  # 30% boost for buttons

        return action_value


class SecurityFocusedStrategy(Strategy):
    """
    Strategy that specifically targets security-sensitive operations.

    ### Architectural Decisions:
    - Implements a focused strategy that prioritizes security operations
    - Uses static analysis data to identify potential security transitions
    - Maintains persistent memory of security-sensitive elements
    - Combines systematic and greedy approaches for security testing

    ### Role in the System:
    - Provides specialized testing for security-critical functionality
    - Complements general exploration strategies with security focus
    - Maximizes coverage of security-sensitive code paths
    - Enables targeted testing of high-risk application components
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "SecurityFocusedStrategy"):
        """
        Initialize the security-focused strategy.

        Args:
            static_data: Optional static analysis data
            name: Strategy name
        """
        super().__init__(static_data, name)

        # Track security operations
        self.security_actions: Set[int] = set()
        self.executed_actions: Set[int] = set()
        self.security_states: Set[str] = set()

        # Track labeled buttons
        self.labeled_buttons: Dict[int, str] = {}

        # Track success rates
        self.action_success_rates: Dict[int, float] = {}

    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate an action focusing on security-sensitive operations.

        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions

        Returns:
            Action prioritizing security operations or None if no actions available
        """
        if not screen.items:
            self.logger.warning("No UI elements available for interaction")
            return None

        # Get current state fingerprint
        current_state = state_data.get("fingerprint", "unknown")

        # Build action candidate pools
        action_pools = {
            "security": [],  # Security-sensitive operations
            "labeled_buttons": [],  # Buttons with text labels
            "interactive": [],  # Other interactive elements
            "fallback": []  # Everything else
        }

        # Process all available actions
        for item in screen.items:
            for action in item.actions:
                # Check if this is a security operation
                if action.reaches_mop:
                    action_pools["security"].append(action)
                    self.security_actions.add(action.id)
                    # Mark this state as having security operations
                    self.security_states.add(current_state)
                    continue

                # Check for element text/label
                element_text = ""
                element_class = ""
                if hasattr(action, 'target_view') and action.target_view:
                    element_text = action.target_view.get("text", "")
                    element_class = action.target_view.get("class", "")

                # Check for buttons with text
                if element_text and "Button" in str(element_class):
                    action_pools["labeled_buttons"].append(action)
                    self.labeled_buttons[action.id] = element_text
                    continue

                # Check for interactive elements
                if "CLICK" in action.text:
                    action_pools["interactive"].append(action)
                else:
                    action_pools["fallback"].append(action)

        # Decision logic for selecting action
        selected_action = None

        # Priority 1: Unexplored security operations
        unexplored_security = [a for a in action_pools["security"] if a.id not in self.executed_actions]
        if unexplored_security:
            self.logger.debug("Selecting unexplored security operation")
            selected_action = self._select_best_from_pool(unexplored_security)

        # Priority 2: Any security operation (even if explored)
        elif action_pools["security"]:
            self.logger.debug("Selecting security operation")
            selected_action = self._select_best_from_pool(action_pools["security"])

        # Priority 3: Unexplored labeled buttons
        elif action_pools["labeled_buttons"]:
            unexplored_buttons = [a for a in action_pools["labeled_buttons"] if a.id not in self.executed_actions]
            if unexplored_buttons:
                self.logger.debug("Selecting unexplored labeled button")
                selected_action = self._select_best_from_pool(unexplored_buttons)
            else:
                self.logger.debug("Selecting labeled button")
                selected_action = self._select_best_from_pool(action_pools["labeled_buttons"])

        # Priority 4: Unexplored interactive elements
        elif action_pools["interactive"]:
            unexplored_interactive = [a for a in action_pools["interactive"] if a.id not in self.executed_actions]
            if unexplored_interactive:
                self.logger.debug("Selecting unexplored interactive element")
                selected_action = random.choice(unexplored_interactive)
            else:
                self.logger.debug("Selecting interactive element")
                selected_action = random.choice(action_pools["interactive"])

        # Priority 5: Fallback to any action
        elif action_pools["fallback"]:
            self.logger.debug("Selecting fallback action")
            selected_action = random.choice(action_pools["fallback"])

        if selected_action:
            return selected_action

        # If we somehow got here with no selection, choose randomly from all available
        all_actions = []
        for pool in action_pools.values():
            all_actions.extend(pool)

        if all_actions:
            self.logger.warning("No action selected by main logic, selecting randomly")
            return random.choice(all_actions)
        else:
            self.logger.warning("No actions available")
            return None

    def _select_best_from_pool(self, action_pool: List[ItemAction]) -> ItemAction:
        """
        Select the best action from a pool based on various criteria.

        Args:
            action_pool: List of actions to choose from

        Returns:
            Best action from the pool
        """
        if not action_pool:
            return None

        # If we have success rates, use them to prioritize
        scored_actions = []
        for action in action_pool:
            # Start with base score from success rate
            success_rate = self.action_success_rates.get(action.id, 0.5)
            score = success_rate

            # Boost for unexplored actions
            if action.id not in self.executed_actions:
                score *= 2.0

            # Boost for directly reaching security operations
            if action.directly_reaches_mop:
                score *= 1.5

            # Boost for labeled buttons with security terms
            if action.id in self.labeled_buttons:
                text = self.labeled_buttons[action.id].lower()
                security_terms = ["message", "digest", "cipher", "encrypt", "decrypt",
                                  "generate", "key", "hash", "security", "login", "password"]
                if any(term in text for term in security_terms):
                    score *= 1.8

            scored_actions.append((action, score))

        # If we have scored actions, select the best
        if scored_actions:
            scored_actions.sort(key=lambda x: x[1], reverse=True)
            return scored_actions[0][0]

        # Fallback to random selection
        return random.choice(action_pool)

    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update strategy based on action execution feedback.

        Args:
            action: Action that was executed
            result: Execution result with success status and state change info
        """
        # Record executed action
        self.executed_actions.add(action.id)

        # Update success rate
        success = result.get("success", False)
        current_rate = self.action_success_rates.get(action.id, 0.5)

        # Simple update rule
        if success:
            # Higher weight for successes to encourage revisiting successful actions
            new_rate = current_rate * 0.8 + 0.2 * 1.0
        else:
            # Lower weight for failures
            new_rate = current_rate * 0.9 + 0.1 * 0.0

        self.action_success_rates[action.id] = new_rate

        # If this was a security operation, log it
        if action.id in self.security_actions:
            self.logger.info(f"Security operation executed: {action.id}, success: {success}")

            # If we have a label, log it too
            if action.id in self.labeled_buttons:
                self.logger.info(f"Security button label: '{self.labeled_buttons[action.id]}'")

        # Reset after reaching a threshold of actions
        if len(self.executed_actions) > 100:
            # Keep track of security actions and labeled buttons
            security_actions = self.security_actions.copy()
            labeled_buttons = self.labeled_buttons.copy()
            success_rates = self.action_success_rates.copy()

            # Reset executed actions but preserve critical knowledge
            self.executed_actions = set()
            self.security_actions = security_actions
            self.labeled_buttons = labeled_buttons
            self.action_success_rates = success_rates


# Register strategies with the registry
StrategyRegistry.register(RandomStrategy)
StrategyRegistry.register(SystematicStrategy)
StrategyRegistry.register(GreedyStrategy)
StrategyRegistry.register(ModelBasedStrategy)
StrategyRegistry.register(SecurityFocusedStrategy)
