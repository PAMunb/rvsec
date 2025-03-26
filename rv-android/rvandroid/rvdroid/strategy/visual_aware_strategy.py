# rvandroid/rvdroid/strategy/visual_aware_strategy.py
"""
Visual-aware strategy for RVDroid.

This module provides a strategy implementation that leverages screenshot analysis
to make more informed decisions about action selection, with special focus on
error detection and visual elements not captured in the UI hierarchy.
"""

import random
from typing import Dict, Any, List, Optional, Set

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.strategy.strategy import Strategy, StrategyRegistry


class VisualAwareStrategy(Strategy):
    """
    Strategy that leverages visual analysis to prioritize actions.

    ### Architectural Decisions:
    - Prioritizes actions based on visual cues from screenshot analysis
    - Focuses on error detection and recovery during exploration
    - Treats visual elements as first-class citizens in the exploration process
    - Maintains state awareness to track and resolve visual error conditions

    ### Role in the System:
    - Complements other strategies with visual awareness
    - Improves testing of applications with complex UI rendering
    - Enhances error detection and recovery
    - Provides better support for non-standard UI components
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "VisualAwareStrategy"):
        """
        Initialize the visual-aware strategy.

        Args:
            static_data: Optional static analysis data
            name: Strategy name
        """
        super().__init__(static_data, name)

        # Tracking for visual error states
        self.error_states: Set[str] = set()

        # Tracking for executed actions
        self.executed_actions: Set[int] = set()

        # Action weights
        self.weights = {
            "error_field": 10.0,  # Highest priority for error fields
            "visual_button": 5.0,  # High priority for visual buttons
            "visual_text": 4.0,  # Good priority for visual text
            "security": 8.0,  # Very high for security operations
            "standard": 1.0  # Base priority for standard elements
        }

    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                        history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate an action prioritizing visual elements and error handling.

        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions

        Returns:
            Selected action or None if no actions available
        """
        if not screen.items:
            self.logger.warning("No UI elements available for interaction")
            return None

        # Get current state fingerprint
        current_state = state_data.get("fingerprint", "unknown")

        # Check if we're in an error state
        is_error_state = current_state in self.error_states

        # Group actions by category
        action_groups = {
            "error_field": [],  # Actions for fields with errors
            "visual_element": [],  # Actions for visually detected elements
            "security": [],  # Security-sensitive operations
            "standard": []  # Standard UI elements
        }

        # Process all items and their actions
        for item in screen.items:
            for action in item.actions:
                # Skip already executed actions unless in error state
                if action.id in self.executed_actions and not is_error_state:
                    continue

                # Check if this is a visual element
                is_visual = item.view.get("visual_element", False)

                # Check if this is an error field
                has_error = item.view.get("has_error", False)

                # Check if this is a security operation
                is_security = action.reaches_mop

                # Categorize the action
                if has_error:
                    # Highest priority for error fields
                    action_groups["error_field"].append(action)
                elif is_visual:
                    # High priority for visual elements
                    action_groups["visual_element"].append(action)
                elif is_security:
                    # High priority for security operations
                    action_groups["security"].append(action)
                else:
                    # Standard elements
                    action_groups["standard"].append(action)

        # Determine which group to select from
        selected_action = None

        # If in error state, prioritize error fields
        if is_error_state and action_groups["error_field"]:
            self.logger.info("In error state, prioritizing error field actions")
            selected_action = self._select_from_group(action_groups["error_field"])

        # Otherwise follow priority order
        elif action_groups["error_field"]:
            # Error fields have highest priority
            self.logger.info("Prioritizing error field action")
            selected_action = self._select_from_group(action_groups["error_field"])

        elif action_groups["visual_element"]:
            # Visual elements next
            self.logger.info("Selecting visual element action")
            selected_action = self._select_from_group(action_groups["visual_element"])

        elif action_groups["security"]:
            # Security operations next
            self.logger.info("Selecting security operation")
            selected_action = self._select_from_group(action_groups["security"])

        elif action_groups["standard"]:
            # Standard elements last
            self.logger.info("Selecting standard element action")
            selected_action = self._select_from_group(action_groups["standard"])

        # If no action selected, return None
        if not selected_action:
            self.logger.warning("No action selected")
            return None

        return selected_action

    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update strategy based on action execution feedback.

        Args:
            action: Action that was executed
            result: Execution result
        """
        # Record executed action
        self.executed_actions.add(action.id)

        # Get result details
        success = result.get("success", False)
        current_state = result.get("state_fingerprint", "unknown")
        new_state = result.get("new_state", False)

        # Check if targeting an error field
        is_error_field = False
        if hasattr(action, 'target_view') and action.target_view:
            is_error_field = action.target_view.get("has_error", False)

        # Handle error states
        if is_error_field:
            if success:
                # If successful action on error field, remove from error states
                if current_state in self.error_states:
                    self.error_states.remove(current_state)
                    self.logger.info(f"Resolved error in state {current_state}")
            else:
                # If failed action on error field, mark as error state
                self.error_states.add(current_state)
                self.logger.info(f"Marked {current_state} as error state")

        # Check for visual elements
        is_visual = False
        if hasattr(action, 'target_view') and action.target_view:
            is_visual = action.target_view.get("visual_element", False)

        # Update weights based on results
        if success and new_state:
            # Boost successful actions that lead to new states
            if is_visual:
                self.weights["visual_button"] *= 1.1
                self.weights["visual_text"] *= 1.1

            if is_error_field:
                self.weights["error_field"] *= 1.1

        elif not success:
            # Reduce weight for failed actions
            if is_visual:
                self.weights["visual_button"] *= 0.9
                self.weights["visual_text"] *= 0.9

    def _select_from_group(self, action_group: List[ItemAction]) -> Optional[ItemAction]:
        """
        Select an action from a group using weighted random selection.

        Args:
            action_group: List of actions to choose from

        Returns:
            Selected action or None if group is empty
        """
        if not action_group:
            return None

        # Calculate weights for each action
        weighted_actions = []

        for action in action_group:
            # Start with base weight
            weight = 1.0

            # Adjust based on action type
            if "Error Field" in action.text:
                weight = self.weights["error_field"]
            elif "Visual" in action.text:
                if "Text" in action.text:
                    weight = self.weights["visual_text"]
                else:
                    weight = self.weights["visual_button"]
            elif action.reaches_mop:
                weight = self.weights["security"]
            else:
                weight = self.weights["standard"]

            # Prioritize actions not previously executed
            if action.id not in self.executed_actions:
                weight *= 1.5

            weighted_actions.append((action, weight))

        # Use weighted random selection
        return self._weighted_random_selection(weighted_actions)

    def _weighted_random_selection(self, weighted_items: List[tuple]) -> Any:
        """
        Select an item using weighted random selection.

        Args:
            weighted_items: List of (item, weight) tuples

        Returns:
            Selected item
        """
        if not weighted_items:
            return None

        items, weights = zip(*weighted_items)
        total_weight = sum(weights)

        # If all weights are zero, use uniform selection
        if total_weight <= 0:
            return random.choice(items)

        # Use weighted random selection
        r = random.uniform(0, total_weight)
        cumulative_weight = 0

        for i, weight in enumerate(weights):
            cumulative_weight += weight
            if r <= cumulative_weight:
                return items[i]

        # Fallback to last item
        return items[-1]


# Register strategy with registry
StrategyRegistry.register(VisualAwareStrategy)
