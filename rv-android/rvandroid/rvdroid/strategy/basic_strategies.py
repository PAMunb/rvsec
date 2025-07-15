# rvandroid/rvdroid/strategy/basic_strategies.py

"""
Basic strategies module for RVDroid.

This module provides fundamental exploration strategies for testing
Android applications, including random, systematic, and monitored
operations-focused approaches.
"""

import random
import time
from typing import Dict, Any, List, Optional, Set, Tuple

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.model import ItemAction, ScreenDescription
from rvandroid.util.error.decorators import handle_error
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager

from rvandroid.rvdroid.strategy.strategy import Strategy, StrategyRegistry


class RandomStrategy(Strategy):
    """
    Random exploration strategy.
    
    ### Architectural Decisions:
    - Implements a baseline random exploration strategy with weighted selection
    - Provides intelligent prioritization of unexplored elements
    - Balances exploration vs. exploitation through configurable randomness
    - Enables basic navigation awareness for improved exploration
    
    ### Role in the System:
    - Serves as a baseline exploration strategy
    - Provides good coverage with minimal assumptions
    - Serves as a fallback when more sophisticated strategies fail
    - Works effectively when application behavior is uniform
    """
    
    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "RandomStrategy"):
        """
        Initialize random strategy.
        
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
        
        # Activity tracking to improve exploration
        self.visited_activities = set()
        self.activity_transitions = {}  # Map of activity -> list of target activities
        
        # Track buttons that might lead to different activities
        self.potential_navigation_buttons = {}  # Button ID -> activity where it was found
        
    @handle_error(level="WARN")
    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                       history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate a random action with intelligent prioritization.
        
        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions
            
        Returns:
            Selected action or None if no actions available
        """
        if not screen.items:
            return None
            
        # Get current activity
        current_activity = state_data.get("activity", "unknown")
        
        # Track activity
        self.visited_activities.add(current_activity)
        
        # First check for "back to main menu" or navigation buttons
        back_actions = []
        
        # Identify text fields and spinners for high priority
        text_fields = []
        spinners = []
        potential_nav_buttons = []
        
        # Collect all actions with classification
        for item in screen.items:
            for action in item.actions:
                # Skip already executed actions
                if action.id in self.executed_actions:
                    continue
                    
                # Check for back button or navigation
                if "BACK" in action.text.upper():
                    back_actions.append(action)
                    continue
                    
                # Check element type
                if hasattr(action, 'target_view') and action.target_view:
                    class_name = action.target_view.get("class", "")
                    element_text = action.target_view.get("text", "")
                    
                    # Text fields
                    if "EditText" in class_name:
                        if "SET_TEXT" in action.text:
                            text_fields.append(action)
                            
                    # Spinners (dropdowns)
                    elif "Spinner" in class_name or "DropDown" in class_name:
                        if "CLICK" in action.text:
                            spinners.append(action)
                            
                    # Potential navigation buttons
                    elif "Button" in class_name and element_text:
                        # Buttons with text are likely navigation
                        if "CLICK" in action.text:
                            potential_nav_buttons.append(action)
                            # Track this button with its activity
                            self.potential_navigation_buttons[action.id] = current_activity
                            
        # Prioritization logic:
        # 1. Untested text fields - users typically need to enter data
        if text_fields:
            self.logger.info(f"Prioritizing text field interaction")
            return random.choice(text_fields)
            
        # 2. Untested spinners - these often need configuration
        if spinners:
            self.logger.info(f"Prioritizing spinner interaction")
            return random.choice(spinners)
            
        # 3. Untested potential navigation buttons - expand exploration
        if potential_nav_buttons and len(self.visited_activities) < 5:
            self.logger.info(f"Prioritizing potential navigation button")
            return random.choice(potential_nav_buttons)
            
        # 4. If we've been in many screens, try a back action to get to main menu
        if back_actions and len(self.visited_activities) >= 3:
            self.logger.info(f"Trying to navigate back after visiting {len(self.visited_activities)} activities")
            return random.choice(back_actions)
            
        # 5. Weighted random selection from all available actions
        weighted_actions = []
        
        for item in screen.items:
            for action in item.actions:
                # Skip executed actions
                if action.id in self.executed_actions:
                    continue
                    
                # Determine action type
                action_type = self._get_action_type(action.text)
                
                # Get weight for this action type
                weight = self.weights.get(action_type, 0.5)
                
                # Boost weight for operations reaching monitored operations
                if hasattr(action, 'reaches_mop') and action.reaches_mop:
                    weight *= 2.0
                    
                # Track if this is a potential navigation button seen before
                if action.id in self.potential_navigation_buttons:
                    # If this button was seen in a different activity, boost it
                    prev_activity = self.potential_navigation_buttons[action.id]
                    if prev_activity != current_activity:
                        weight *= 1.5
                        
                weighted_actions.append((action, weight))
                
        if not weighted_actions:
            # If no unexecuted actions are available, allow re-execution
            for item in screen.items:
                for action in item.actions:
                    action_type = self._get_action_type(action.text)
                    weight = self.weights.get(action_type, 0.5) * 0.5  # Half weight for repeats
                    weighted_actions.append((action, weight))
                    
        if not weighted_actions:
            return None
            
        # Select using weighted random
        return self._weighted_random_selection(weighted_actions)
        
    @handle_error(level="WARN")
    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update strategy based on action execution feedback.
        
        Args:
            action: Action that was executed
            result: Execution result
        """
        # Call parent implementation for basic statistics
        super().update_feedback(action, result)
        
        # Record executed action
        self.executed_actions.add(action.id)
        
        # Track activity transitions
        prev_activity = result.get("previous_state_activity")
        current_activity = result.get("current_state_activity")
        
        if prev_activity and current_activity and prev_activity != current_activity:
            # Record this transition
            if prev_activity not in self.activity_transitions:
                self.activity_transitions[prev_activity] = set()
                
            self.activity_transitions[prev_activity].add(current_activity)
            
            # If this was a potential navigation button, confirm it
            if action.id in self.potential_navigation_buttons:
                self.logger.info(f"Confirmed navigation button from {prev_activity} to {current_activity}")
                
        # Reset executed actions after many actions to allow reexploration
        if len(self.executed_actions) > 30:
            self.executed_actions.clear()
            
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
    Systematic exploration strategy.
    
    ### Architectural Decisions:
    - Implements a methodical, prioritized exploration approach
    - Categorizes UI elements by importance for focused testing
    - Maintains exploration history to ensure complete coverage
    - Orders action execution by element and action type
    
    ### Role in the System:
    - Ensures methodical exploration of application states
    - Provides predictable and reproducible testing behavior
    - Efficiently handles applications with complex navigation
    - Enables systematic exploration of UI components
    """
    
    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "SystematicStrategy"):
        """
        Initialize systematic strategy.
        
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
        
    @handle_error(level="WARN")
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
            
        # Create prioritized categories to ensure important elements are tested first
        categories = {
            "high_value": [],  # Operations reaching monitored methods, labeled buttons
            "medium_value": [],  # Other interactive elements
            "low_value": []  # Basic elements with no special properties
        }
        
        # Group actions by priority category
        for item_idx, item in enumerate(screen.items):
            for action_idx, action in enumerate(item.actions):
                action_type = self._get_action_type(action.text)
                
                # Create action entry with indices
                action_entry = (item_idx, action_idx, action)
                
                # Check for descriptive text/label
                element_text = ""
                if hasattr(action, 'target_view') and action.target_view:
                    element_text = action.target_view.get("text", "")
                    
                # Operations that reach monitored methods go to high_value category
                reaches_monitored_op = False
                if hasattr(action, 'reaches_mop'):
                    reaches_monitored_op = action.reaches_mop
                    
                directly_reaches_monitored_op = False
                if hasattr(action, 'directly_reaches_mop'):
                    directly_reaches_monitored_op = action.directly_reaches_mop
                    
                if reaches_monitored_op or directly_reaches_monitored_op:
                    categories["high_value"].append(action_entry)
                    continue
                    
                # Buttons with text are high value
                if element_text and "Button" in str(action.target_view.get("class", "")):
                    categories["high_value"].append(action_entry)
                    continue
                    
                # Elements with text are medium value
                if element_text:
                    categories["medium_value"].append(action_entry)
                    continue
                    
                # Everything else is low value
                categories["low_value"].append(action_entry)
                
        # Within each category, prioritize by action type
        for category in categories.values():
            category.sort(key=lambda entry:
                self.action_priorities.index(self._get_action_type(entry[2].text))
                if self._get_action_type(entry[2].text) in self.action_priorities 
                else len(self.action_priorities)
            )
            
        # For each category, prioritize unexplored actions
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
        
    @handle_error(level="WARN")
    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update strategy based on action execution feedback.
        
        Args:
            action: Action that was executed
            result: Execution result with success status and state change info
        """
        # Call parent implementation for basic statistics
        super().update_feedback(action, result)
        
        # Mark action as explored
        self.explored_actions.add(action.id)
        
        # If we've explored a high percentage of actions, reset with a higher threshold
        # This ensures we eventually revisit all elements while still prioritizing new actions
        if len(self.explored_actions) > 100:
            # Rather than clearing completely, keep track of operations reaching monitored methods
            monitored_actions = set()
            
            # We would need a way to identify which actions reach monitored operations
            # For now, just reset the exploration history completely
            self.explored_actions = monitored_actions
            
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


class MonitoredOperationsFocusedStrategy(Strategy):
    """
    Strategy that specifically targets monitored operations and related UI elements.
    
    ### Architectural Decisions:
    - Implements a focused strategy that prioritizes monitored operations
    - Uses static and dynamic analysis to identify relevant code paths
    - Maintains persistent memory of elements that reach monitored operations
    - Combines systematic and greedy approaches for targeted testing
    
    ### Role in the System:
    - Provides specialized testing for monitored operations
    - Complements general exploration strategies with focused exploration
    - Maximizes coverage of monitored operation code paths
    - Enables targeted testing of operations with potential issues
    """
    
    def __init__(self, static_data: Optional[StaticAnalysisData] = None, name: str = "MonitoredOperationsFocusedStrategy"):
        """
        Initialize the monitored operations focused strategy.
        
        Args:
            static_data: Optional static analysis data
            name: Strategy name
        """
        super().__init__(static_data, name)
        
        # Track operations of interest
        self.monitored_actions: Set[int] = set()
        self.executed_actions: Set[int] = set()
        self.monitored_states: Set[str] = set()
        
        # Track labeled buttons
        self.labeled_buttons: Dict[int, str] = {}
        
        # Track success rates
        self.action_success_rates: Dict[int, float] = {}
        
    @handle_error(level="WARN")
    def generate_action(self, screen: ScreenDescription, state_data: Dict[str, Any],
                       history: Optional[List[Dict[str, Any]]] = None) -> Optional[ItemAction]:
        """
        Generate an action focusing on monitored operations and related UI elements.
        
        Args:
            screen: Parsed screen description
            state_data: Raw state data
            history: Optional history of previous states and actions
            
        Returns:
            Action prioritizing monitored operations or None if no actions available
        """
        if not screen.items:
            self.logger.warning("No UI elements available for interaction")
            return None
            
        # Get current state fingerprint
        current_state = state_data.get("fingerprint", "unknown")
        
        # Build action candidate pools
        action_pools = {
            "monitored": [],  # Operations that reach monitored methods
            "labeled_buttons": [],  # Buttons with text labels
            "interactive": [],  # Other interactive elements
            "fallback": []  # Everything else
        }
        
        # Process all available actions
        for item in screen.items:
            for action in item.actions:
                # Check if this action reaches monitored methods
                reaches_monitored_op = False
                if hasattr(action, 'reaches_mop'):
                    reaches_monitored_op = action.reaches_mop
                    
                if reaches_monitored_op:
                    action_pools["monitored"].append(action)
                    self.monitored_actions.add(action.id)
                    # Mark this state as having operations of interest
                    self.monitored_states.add(current_state)
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
        
        # Priority 1: Unexplored operations that reach monitored methods
        unexplored_monitored = [a for a in action_pools["monitored"] if a.id not in self.executed_actions]
        if unexplored_monitored:
            self.logger.debug("Selecting unexplored operation that reaches monitored methods")
            selected_action = self._select_best_from_pool(unexplored_monitored)
            
        # Priority 2: Any operation reaching monitored methods (even if explored)
        elif action_pools["monitored"]:
            self.logger.debug("Selecting operation that reaches monitored methods")
            selected_action = self._select_best_from_pool(action_pools["monitored"])
            
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
                
            # Boost for directly reaching monitored methods
            if hasattr(action, 'directly_reaches_mop') and action.directly_reaches_mop:
                score *= 1.5
                
            # Boost for labeled buttons with monitored operation terms
            if action.id in self.labeled_buttons:
                text = self.labeled_buttons[action.id].lower()
                operation_terms = ["message", "digest", "cipher", "encrypt", "decrypt", "generate", 
                                "key", "hash", "iterator", "next", "hasNext", "compare", 
                                "check", "validate", "login", "password", "verify"]
                if any(term in text for term in operation_terms):
                    score *= 1.8
                    
            scored_actions.append((action, score))
            
        # If we have scored actions, select the best
        if scored_actions:
            scored_actions.sort(key=lambda x: x[1], reverse=True)
            return scored_actions[0][0]
            
        # Fallback to random selection
        return random.choice(action_pool)
        
    @handle_error(level="WARN")
    def update_feedback(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Update strategy based on action execution feedback.
        
        Args:
            action: Action that was executed
            result: Execution result with success status and state change info
        """
        # Call parent implementation for basic statistics
        super().update_feedback(action, result)
        
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
        
        # If this was an operation reaching monitored methods, log it
        if action.id in self.monitored_actions:
            self.logger.info(f"Operation reaching monitored method executed: {action.id}, success: {success}")
            
            # If we have a label, log it too
            if action.id in self.labeled_buttons:
                self.logger.info(f"Operation button label: '{self.labeled_buttons[action.id]}'")
                
        # Reset after reaching a threshold of actions
        if len(self.executed_actions) > 100:
            # Keep track of operations of interest and labeled buttons
            monitored_actions = self.monitored_actions.copy()
            labeled_buttons = self.labeled_buttons.copy()
            success_rates = self.action_success_rates.copy()
            
            # Reset executed actions but preserve critical knowledge
            self.executed_actions = set()
            self.monitored_actions = monitored_actions
            self.labeled_buttons = labeled_buttons
            self.action_success_rates = success_rates
            

# Register strategies with the registry
StrategyRegistry.register(RandomStrategy)
StrategyRegistry.register(SystematicStrategy)
StrategyRegistry.register(MonitoredOperationsFocusedStrategy)