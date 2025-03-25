"""
Exploration optimizer for RVDroid.

This module provides functionality to optimize exploration strategies based
on memory systems, detecting and escaping local minimums, and balancing
exploration versus exploitation.
"""

import random
import time
from typing import Dict, Any, List, Optional, Set, Tuple

from rvandroid.parser.screen.visitor.base_visitor import ScreenDescription, ItemAction
from rvandroid.rvdroid.memory.short_term.short_term_memory import ShortTermMemory
from rvandroid.rvdroid.memory.long_term.long_term_memory import LongTermMemory
from rvandroid.rvdroid.memory.patterns.pattern_recognition import PatternRecognition
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ExplorationOptimizer:
    """
    Optimizes exploration strategies using memory systems.

    Provides mechanisms to detect and escape local minimums, balance
    exploration and exploitation, and promote diversity in exploration.
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

        self.logger.info("Initialized exploration optimizer")

    def optimize_action_selection(self, screen: ScreenDescription, state_data: Dict[str, Any],
                                  available_actions: List[ItemAction]) -> List[ItemAction]:
        """
        Optimize action selection based on exploration strategy.

        Args:
            screen: Parsed screen description
            state_data: Raw state data
            available_actions: List of available actions

        Returns:
            Re-prioritized list of actions
        """
        if not available_actions:
            return []

        # Update exploration phase if needed
        self._update_exploration_phase(state_data)

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
        Prioritize actions to escape local minimums or explore previously unexplored paths.

        Uses window transition graphs (static and dynamic) to identify promising escape
        actions that may lead to unexplored areas of the application.

        Args:
            available_actions: List of available actions

        Returns:
            Re-prioritized list of actions for exploration
        """
        if not available_actions:
            return []

        # Action scores will determine priorities
        action_scores = {}

        # Get state information
        current_state = getattr(self, "current_state", None)
        current_activity = getattr(self, "current_activity", None)

        # 1. Analyze dynamic window transition graph for unexplored paths
        dyn_wtg = None
        if self.long_term_memory and hasattr(self.long_term_memory, "dynamic_wtg"):
            dyn_wtg = self.long_term_memory.dynamic_wtg

        # 2. Check static window transition graph for potential transitions
        static_wtg = None
        if self.long_term_memory and hasattr(self.long_term_memory, "static_wtg"):
            static_wtg = self.long_term_memory.static_wtg

        # Score each action
        for action in available_actions:
            score = 1.0  # Base score

            # Score factor 1: Security-sensitive operations get high priority
            if action.reaches_mop:
                score += 5.0
                if action.directly_reaches_mop:
                    score += 3.0

            # Score factor 2: Prioritize actions not tried in current state
            if current_state and self.long_term_memory:
                state_info = self.long_term_memory.state_knowledge.get(current_state, {})
                tried_actions = set()
                tried_actions.update(state_info.get("successful_actions", set()))
                tried_actions.update(state_info.get("failed_actions", set()))

                if action.id not in tried_actions:
                    score += 4.0

            # Score factor 3: From static WTG, prioritize actions that might lead to unexplored activities
            if static_wtg and current_activity:
                potential_transitions = []
                for edge in static_wtg.graph.edges():
                    if edge[0].name == current_activity:
                        potential_transitions.append((edge[1].name, edge[2]))  # target activity, events

                # Check if this action might trigger an unexplored transition
                for target_activity, events in potential_transitions:
                    # Try to match event with action
                    for event in events:
                        if event.event_type.name == self._get_event_type(action.text):
                            # Check if target activity is unexplored
                            if self.long_term_memory and target_activity not in self.long_term_memory.activity_knowledge:
                                score += 4.5
                            else:
                                # Otherwise, still prioritize but less
                                score += 2.0

            # Score factor 4: From dynamic WTG, prioritize transitions to less visited activities
            if dyn_wtg and current_activity:
                # Get least visited neighboring activities
                neighbor_visits = dyn_wtg.get_least_visited_activities(3)
                if neighbor_visits:
                    # Clickable actions might trigger transitions to these activities
                    if "CLICK" in action.text:
                        score += 2.5
                    # Buttons are even more likely to trigger transitions
                    if "Button" in str(action.target_view.get("class", "")):
                        score += 1.5

            # Score factor 5: Prioritize actions that access unexplored UI elements
            if self.short_term_memory:
                recent_actions = set(a["action_id"] for a in self.short_term_memory.get_recent_actions(20))
                if action.id not in recent_actions:
                    score += 2.0

            # Store action score
            action_scores[action.id] = score

        # Sort actions by score (descending)
        sorted_actions = sorted(available_actions, key=lambda a: action_scores.get(a.id, 0), reverse=True)

        # Log selection for debugging
        top_scores = [(a.id, action_scores.get(a.id, 0)) for a in sorted_actions[:3]] if sorted_actions else []
        self.logger.info(f"Prioritized {len(sorted_actions)} actions for exploration. Top scores: {top_scores}")

        return sorted_actions

    def _get_event_type(self, action_text: str) -> str:
        """Map action text to event type name for WTG comparison."""
        if "CLICK" in action_text:
            return "CLICK"
        elif "LONG_CLICK" in action_text:
            return "LONG_CLICK"
        elif "SCROLL" in action_text:
            return "SCROLL"
        elif "SET_TEXT" in action_text:
            return "TEXT_CHANGE"
        else:
            return "OTHER"