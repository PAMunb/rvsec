# rvandroid/rvdroid/memory/exploration/exploration_optimizer.py

"""
Exploration optimizer for RVDroid.

This module provides functionality to optimize exploration strategies based
on memory systems, detecting and escaping local minimums, and balancing
exploration versus exploitation.
"""

import time
from typing import Dict, Any, List, Optional

from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.memory.long_term.long_term_memory import LongTermMemory
from rvandroid.rvdroid.memory.short_term.short_term_memory import ShortTermMemory
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ExplorationOptimizer:
    """
    Optimizes exploration strategies using memory systems.

    Balances exploration and exploitation while ensuring thorough
    coverage of the application, with special focus on preventing
    redundant exploration of already visited activities.

    ### Architectural Decisions:
    - Implements a simplified exploration-exploitation balance
    - Tracks activity coverage to prevent overexploration of single areas
    - Provides clear mechanisms to detect and escape exploration plateaus
    - Prioritizes undiscovered areas of the application
    """

    def __init__(self, short_term_memory: ShortTermMemory,
                 long_term_memory: Optional[LongTermMemory] = None,
                 pattern_recognition=None):  # Added pattern_recognition parameter with default None
        """
        Initialize the exploration optimizer.

        Args:
            short_term_memory: Short-term memory instance
            long_term_memory: Optional long-term memory instance
            pattern_recognition: Optional pattern recognition instance
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.memory.exploration_optimizer",
            {CONTEXT_COMPONENT: "ExplorationOptimizer"}
        )

        # Store memory references
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.pattern_recognition = pattern_recognition  # Store pattern recognition reference

        # Exploration parameters
        self.exploration_factor = 0.7  # Higher default for better exploration
        self.diversity_factor = 0.5
        self.security_focus_factor = 0.5  # For security-focused exploration

        # Activity tracking for balancing exploration
        self.visited_activities = set()
        self.activity_visit_counts = {}
        self.overexplored_threshold = 10  # Consider an activity overexplored after 10 visits

        # Track exploration phase and timing
        self.exploration_phase = "exploration"  # exploration, exploitation, focus
        self.phase_start_time = time.time()
        self.phase_duration = 300  # 5 minutes per phase

        # Track potentially interesting actions
        self.navigation_actions = set()  # Actions that led to activity transitions
        self.security_actions = set()  # Security-sensitive actions

        # Track tested actions
        self.tested_actions = set()  # Actions that have been tested

        # Track local minimums
        self._in_local_minimum = False
        self.local_minimums_detected = 0
        self.recent_actions = set()

        self.logger.info("Initialized exploration optimizer")

    def optimize_action_selection(self, screen: ScreenDescription, state_data: Dict[str, Any],
                                  available_actions: List[ItemAction]) -> List[ItemAction]:
        """
        Optimize action selection based on current state and exploration needs.

        Args:
            screen: Parsed screen description
            state_data: Raw state data
            available_actions: List of available actions

        Returns:
            Re-prioritized list of actions
        """
        if not available_actions:
            return []

        # Safely get current activity with default
        current_activity = state_data.get("activity", "unknown")

        # Track activity
        self.visited_activities.add(current_activity)

        # Track activity visit count
        self.activity_visit_counts[current_activity] = self.activity_visit_counts.get(current_activity, 0) + 1

        # Check if this activity is potentially overexplored
        activity_count = self.activity_visit_counts.get(current_activity, 0)
        is_overexplored = activity_count > self.overexplored_threshold and len(self.visited_activities) > 1

        # Assign scores to actions based on exploration value
        action_scores = {}

        for action in available_actions:
            # Calculate base score from element type
            score = self._calculate_base_score(action, current_activity)

            # Adjust for security sensitivity
            if action.reaches_mop:
                score *= 1.5
                self.security_actions.add(action.id)

            # Adjust for exploration value (prefer untested actions)
            if action.id in self.tested_actions:
                score *= 0.5

            # Prioritize actions that might lead to a new activity if current one is overexplored
            if is_overexplored:
                if hasattr(action, 'target_view') and action.target_view:
                    class_name = action.target_view.get("class", "")
                    element_text = action.target_view.get("text", "")

                    # Buttons with text are likely navigation elements
                    if "Button" in class_name and element_text:
                        score *= 2.0

            # Store score
            action_scores[action.id] = score

        # Sort actions by score (highest first)
        sorted_actions = sorted(available_actions, key=lambda a: action_scores.get(a.id, 0), reverse=True)

        return sorted_actions

    def _calculate_base_score(self, action: ItemAction, current_activity: str) -> float:
        """
        Calculate a base score for an action based on its properties.

        Args:
            action: Action to score
            current_activity: Current activity name

        Returns:
            Base score value
        """
        # Start with a base score of 1.0
        score = 1.0

        # Boost score for untested actions
        if action.id not in self.tested_actions:
            score += 1.0

        # Boost for security-sensitive operations
        if action.reaches_mop:
            score += 1.5
            if action.directly_reaches_mop:
                score += 0.5

        # Check for element type if available
        if hasattr(action, 'target_view') and action.target_view:
            class_name = action.target_view.get("class", "")
            element_text = action.target_view.get("text", "")

            # Boost for buttons with text (likely navigation)
            if "Button" in class_name and element_text:
                score += 1.0

            # Boost for text fields (form interaction)
            elif "EditText" in class_name:
                score += 0.8

            # Boost for checkboxes and other interactive elements
            elif any(c in class_name for c in ["CheckBox", "RadioButton", "Switch"]):
                score += 0.6

        # Boost for actions in the exploration phase
        if self.exploration_phase == "exploration":
            if action.id not in self.tested_actions:
                score *= 1.2

        # Boost for security operations in the security_focus phase
        elif self.exploration_phase == "security_focus":
            if action.reaches_mop:
                score *= 1.5

        return score

    def record_action_result(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Record the result of an action for future optimization.

        Args:
            action: Action that was executed
            result: Execution result
        """
        # Mark action as tested
        self.tested_actions.add(action.id)

        # Track recent actions for local minimum detection
        self.recent_actions.add(action.id)
        if len(self.recent_actions) > 20:  # Keep only the last 20 actions
            self.recent_actions.pop()

        # Check if this action caused an activity transition
        activity_changed = result.get("activity_changed", False)

        if activity_changed:
            self.logger.info(f"Recording activity transition action: {action.id}")
            self.navigation_actions.add(action.id)

        # Record security operations
        if action.reaches_mop:
            self.security_actions.add(action.id)

    def _adjust_parameters_for_phase(self, phase: str) -> None:
        """
        Adjust exploration parameters based on the current phase.

        Args:
            phase: Current exploration phase
        """
        if phase == "exploration":
            self.exploration_factor = 0.8  # High exploration
            self.diversity_factor = 0.7
            self.security_focus_factor = 0.3
        elif phase == "exploitation":
            self.exploration_factor = 0.3  # Moderate exploration
            self.diversity_factor = 0.4
            self.security_focus_factor = 0.4
        elif phase == "security_focus":
            self.exploration_factor = 0.2  # Low exploration
            self.diversity_factor = 0.3
            self.security_focus_factor = 0.8

    def _detect_local_minimum(self) -> bool:
        """
        Detect if exploration is stuck in a local minimum or cycle.

        Returns:
            True if stuck in local minimum, False otherwise
        """
        # Check for cycles in state transitions
        is_cycle, _ = self.short_term_memory.detect_cycles()

        if is_cycle:
            self._in_local_minimum = True
            self.local_minimums_detected += 1
            return True

        # Check for repetitive actions
        repetitive_actions = self.short_term_memory.detect_repetitive_actions()

        if repetitive_actions:
            self._in_local_minimum = True
            self.local_minimums_detected += 1
            return True

        return self._in_local_minimum

    def _prioritize_escape_actions(self, available_actions: List[ItemAction]) -> List[ItemAction]:
        """
        Prioritize actions to escape local minimums.

        Args:
            available_actions: List of available actions

        Returns:
            Re-prioritized list of actions for exploration
        """
        if not available_actions:
            return []

        # Assign scores to actions
        action_scores = {}

        # Score actions based on exploration value
        for action in available_actions:
            # Start with base score
            score = 1.0

            # Factor 1: Prefer actions not tried recently
            if action.id not in self.recent_actions:
                score += 1.5

            # Factor 2: Prefer security operations
            if action.reaches_mop:
                score += 1.0
                if action.directly_reaches_mop:
                    score += 0.5

            # Factor 3: Prefer diverse action types
            # Determine action type by text
            action_type = self._get_action_type_from_text(action.text)

            # Check recent actions for diversity
            recent_actions = self.short_term_memory.get_recent_actions(10)
            recent_types = [self._get_action_type_from_text(a.text) for a in recent_actions]

            # Boost score if this type is underrepresented
            if action_type not in recent_types:
                score += 1.0
            elif recent_types.count(action_type) <= 2:
                score += 0.5

            # Store the score
            action_scores[action.id] = score

        # Sort actions by score
        sorted_actions = sorted(available_actions, key=lambda a: action_scores.get(a.id, 0), reverse=True)

        return sorted_actions

    def _get_action_type_from_text(self, action_text: str) -> str:
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
