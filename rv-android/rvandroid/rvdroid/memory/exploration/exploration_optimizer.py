# rvandroid/rvdroid/memory/exploration/exploration_optimizer.py

"""
Exploration optimizer for RVDroid.

This module provides functionality to optimize exploration strategies based
on memory systems, detecting and escaping local minimums, and balancing
exploration versus exploitation.
"""

import time
from typing import Dict, Any, List, Optional, Set

from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.memory.long_term.long_term_memory import LongTermMemory
from rvandroid.rvdroid.memory.patterns.pattern_recognition import PatternRecognition
from rvandroid.rvdroid.memory.short_term.short_term_memory import ShortTermMemory
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ExplorationOptimizer:
    """
    Optimizes exploration strategies using memory systems.

    ### Architectural Decisions:
    - Implements intelligent exploration-exploitation balancing
    - Uses memory systems to guide exploration decision making
    - Provides mechanisms to detect and escape local minimums
    - Supports adaptation to different application contexts
    - Maintains exploration state to promote discovery of new behavior

    ### Role in the System:
    - Guides exploration to maximize test coverage
    - Detects and helps overcome exploration plateaus
    - Optimizes action selection to discover new states
    - Balances between exploring new areas and exploiting known paths
    - Adapts exploration strategy based on application domain
    """

    def __init__(self, short_term_memory: ShortTermMemory,
                 long_term_memory: Optional[LongTermMemory] = None,
                 pattern_recognition: Optional[PatternRecognition] = None):
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
        self.pattern_recognition = pattern_recognition

        # Exploration parameters
        self.exploration_factor = 0.2  # Balance of exploration vs exploitation
        self.diversity_factor = 0.3  # Importance of exploring diverse actions
        self.security_focus_factor = 0.5  # Focus on security-sensitive operations

        # Track exploration status
        self.exploration_phase = "exploration"  # exploration, exploitation, security_focus
        self.phase_start_time = time.time()
        self.phase_duration = 300  # 5 minutes per phase
        self.plateaus_escaped = 0
        self.local_minimums_detected = 0

        # Action history for diversity tracking
        self.recent_actions: Set[int] = set()

        # Current state tracking
        self.current_state: Optional[str] = None
        self.current_activity: Optional[str] = None

        self.logger.info("Initialized exploration optimizer")

    def optimize_action_selection(self, screen: ScreenDescription, state_data: Dict[str, Any],
                                  available_actions: List[ItemAction]) -> List[ItemAction]:
        """
        Optimize action selection based on exploration strategy.

        Args:
            screen: Parsed screen description
            state_data: State data dictionary
            available_actions: List of available actions

        Returns:
            Re-prioritized list of actions
        """
        if not available_actions:
            return []

        # Update exploration phase if needed
        self._update_exploration_phase(state_data)

        # Update current state tracking
        self.current_state = state_data.get("fingerprint", "unknown")
        self.current_activity = state_data.get("activity", "unknown")

        # Check for stuck in local minimum or cycle
        in_local_minimum = self._detect_local_minimum()

        # If stuck, prioritize escape actions
        if in_local_minimum:
            self.logger.info("Detected local minimum, prioritizing escape actions")
            return self._prioritize_escape_actions(available_actions)

        # Otherwise, prioritize based on current phase
        if self.exploration_phase == "exploration":
            return self._prioritize_exploration(available_actions)

        elif self.exploration_phase == "exploitation":
            return self._prioritize_exploitation(available_actions, state_data)

        elif self.exploration_phase == "security_focus":
            return self._prioritize_security_operations(available_actions)

        # Default prioritization
        return available_actions

    def record_action_result(self, action: ItemAction, result: Dict[str, Any]) -> None:
        """
        Record action execution result for optimization.

        Args:
            action: Action that was executed
            result: Execution result
        """
        # Track recent actions for diversity
        self.recent_actions.add(action.id)

        # Keep recent actions set to a reasonable size
        if len(self.recent_actions) > 100:
            self.recent_actions.clear()

        # Check if we escaped a local minimum
        if getattr(self, "_in_local_minimum", False) and result.get("new_state", False):
            self._in_local_minimum = False
            self.plateaus_escaped += 1
            self.logger.info("Escaped from local minimum/plateau")

    def _update_exploration_phase(self, state_data: Dict[str, Any]) -> None:
        """
        Update the exploration phase based on elapsed time and coverage.

        Args:
            state_data: Current state data
        """
        current_time = time.time()
        elapsed_in_phase = current_time - self.phase_start_time

        # Check if we should transition to next phase
        if elapsed_in_phase >= self.phase_duration:
            # Determine next phase
            if self.exploration_phase == "exploration":
                next_phase = "exploitation"
            elif self.exploration_phase == "exploitation":
                next_phase = "security_focus"
            else:
                # Cycle back to exploration
                next_phase = "exploration"

            # Log phase transition
            self.logger.info(f"Transitioning from {self.exploration_phase} phase to {next_phase} phase")

            # Update phase tracking
            self.exploration_phase = next_phase
            self.phase_start_time = current_time

            # Adjust exploration parameters for the new phase
            self._adjust_parameters_for_phase(next_phase)

    def _adjust_parameters_for_phase(self, phase: str) -> None:
        """
        Adjust exploration parameters based on the current phase.

        Args:
            phase: Current exploration phase
        """
        if phase == "exploration":
            self.exploration_factor = 0.8  # High exploration
            self.diversity_factor = 0.7
            self.security_focus_factor = 0.2

        elif phase == "exploitation":
            self.exploration_factor = 0.2  # Low exploration
            self.diversity_factor = 0.3
            self.security_focus_factor = 0.5

        elif phase == "security_focus":
            self.exploration_factor = 0.3  # Moderate exploration
            self.diversity_factor = 0.2
            self.security_focus_factor = 0.9  # High security focus

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

        return getattr(self, "_in_local_minimum", False)

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

            # Factor 4: Prefer actions in different parts of the screen
            if hasattr(action, 'coordinates') and action.coordinates:
                x, y = action.coordinates

                # Check if recent actions were in same screen area
                recent_coordinates = []
                for recent_action in recent_actions:
                    if hasattr(recent_action, 'coordinates') and recent_action.coordinates:
                        recent_coordinates.append(recent_action.coordinates)

                # Rough screen area check (divide screen into quadrants)
                in_different_area = True
                for rx, ry in recent_coordinates:
                    # Check if in same quadrant
                    if (x < 500 and rx < 500 and y < 800 and ry < 800) or \
                            (x < 500 and rx < 500 and y >= 800 and ry >= 800) or \
                            (x >= 500 and rx >= 500 and y < 800 and ry < 800) or \
                            (x >= 500 and rx >= 500 and y >= 800 and ry >= 800):
                        in_different_area = False
                        break

                if in_different_area:
                    score += 1.0

            # Store score
            action_scores[action.id] = score

        # Sort actions by score
        sorted_actions = sorted(available_actions, key=lambda a: action_scores.get(a.id, 0), reverse=True)

        # Log top scores for debugging
        top_scores = [(a.id, action_scores.get(a.id, 0)) for a in sorted_actions[:3]] if sorted_actions else []
        self.logger.info(f"Prioritized actions for exploration. Top scores: {top_scores}")

        return sorted_actions

    def _prioritize_exploration(self, available_actions: List[ItemAction]) -> List[ItemAction]:
        """
        Prioritize actions for exploration phase.

        Args:
            available_actions: List of available actions

        Returns:
            Re-prioritized list of actions for exploration
        """
        # In exploration phase, we want to maximize state discovery
        # Use similar approach to escape actions but with different weights

        # Assign scores to actions
        action_scores = {}

        for action in available_actions:
            # Base score
            score = 1.0

            # Prefer actions we haven't tried
            if action.id not in self.recent_actions:
                score += 2.0

            # Prefer buttons and interactive elements
            if hasattr(action, 'target_view') and action.target_view:
                element_class = action.target_view.get("class", "")

                if "Button" in str(element_class):
                    score += 1.5
                elif "EditText" in str(element_class):
                    score += 1.0

            # Moderately prefer security operations
            if action.reaches_mop:
                score *= 1.2

            # Store score
            action_scores[action.id] = score

        # Sort actions by score
        sorted_actions = sorted(available_actions, key=lambda a: action_scores.get(a.id, 0), reverse=True)

        return sorted_actions

    def _prioritize_exploitation(self, available_actions: List[ItemAction],
                                 state_data: Dict[str, Any]) -> List[ItemAction]:
        """
        Prioritize actions for exploitation phase.

        Args:
            available_actions: List of available actions
            state_data: Current state data

        Returns:
            Re-prioritized list of actions for exploitation
        """
        # In exploitation phase, we want to follow previously successful paths
        # Use long-term memory to guide action selection if available

        if not self.long_term_memory:
            # Fall back to exploration
            return self._prioritize_exploration(available_actions)

        # Get current state fingerprint
        current_state = state_data.get("fingerprint", "unknown")

        # Get successful actions for this state
        successful_actions = self.long_term_memory.get_successful_actions_for_state(current_state)

        # Find matches in available actions
        preferred_actions = []
        other_actions = []

        for action in available_actions:
            if action.id in successful_actions:
                preferred_actions.append(action)
            else:
                other_actions.append(action)

        # Combine with preference for successful actions
        return preferred_actions + other_actions

    def _prioritize_security_operations(self, available_actions: List[ItemAction]) -> List[ItemAction]:
        """
        Prioritize security-sensitive operations.

        Args:
            available_actions: List of available actions

        Returns:
            Re-prioritized list of actions for security testing
        """
        # In security focus phase, we want to prioritize security operations
        security_actions = []
        other_actions = []

        for action in available_actions:
            if action.reaches_mop:
                security_actions.append(action)
            else:
                other_actions.append(action)

        # Sort security actions by directness
        security_actions.sort(key=lambda a: a.directly_reaches_mop, reverse=True)

        # Combine with preference for security actions
        return security_actions + other_actions

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
