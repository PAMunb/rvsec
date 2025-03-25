"""
Pattern recognition system for RVDroid.

This module provides functionality to detect recurring patterns in user
interactions and application behavior, enabling more intelligent testing.
"""

from collections import defaultdict
import time
from typing import Dict, Any, List, Optional, Set, Tuple, Sequence

from rvandroid.parser.screen.visitor.base_visitor import ItemAction
from rvandroid.rvdroid.memory.short_term.short_term_memory import ShortTermMemory
from rvandroid.rvdroid.memory.long_term.long_term_memory import LongTermMemory
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class InteractionPattern:
    """Represents a pattern of interactions detected in the application."""

    def __init__(self, actions: List[Dict[str, Any]], states: List[Dict[str, Any]]):
        """
        Initialize an interaction pattern.

        Args:
            actions: List of action dictionaries
            states: List of state dictionaries
        """
        self.actions = actions
        self.states = states
        self.occurrences = 1
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.success_count = 0
        self.failure_count = 0

    def update(self, success: bool) -> None:
        """
        Update pattern statistics.

        Args:
            success: Whether the pattern execution was successful
        """
        self.occurrences += 1
        self.last_seen = time.time()

        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

    def get_success_rate(self) -> float:
        """
        Get the success rate for this pattern.

        Returns:
            Success rate (0.0 to 1.0)
        """
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.0

        return self.success_count / total

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert pattern to dictionary.

        Returns:
            Dictionary representation of pattern
        """
        return {
            "actions": self.actions,
            "states": self.states,
            "occurrences": self.occurrences,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.get_success_rate()
        }


class PatternRecognition:
    """
    Recognizes patterns in application interactions.

    Analyzes interactions stored in memory to identify recurring patterns,
    which can be used to guide future testing and optimize exploration.
    """

    def __init__(self, short_term_memory: ShortTermMemory, long_term_memory: Optional[LongTermMemory] = None):
        """
        Initialize the pattern recognition system.

        Args:
            short_term_memory: Short-term memory instance
            long_term_memory: Optional long-term memory instance
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.memory.pattern_recognition",
            {CONTEXT_COMPONENT: "PatternRecognition"}
        )

        # Store memory references
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory

        # Pattern storage
        self.action_patterns: Dict[str, InteractionPattern] = {}
        self.state_transition_patterns: Dict[str, InteractionPattern] = {}
        self.navigation_patterns: Dict[str, InteractionPattern] = {}

        # Minimum pattern length and threshold
        self.min_pattern_length = 2
        self.max_pattern_length = 5
        self.detection_threshold = 2  # Minimum occurrences to recognize a pattern

        self.logger.info("Initialized pattern recognition system")

    def analyze_action_sequences(self) -> List[InteractionPattern]:
        """
        Analyze short-term memory for recurring action sequences.

        Returns:
            List of detected action patterns
        """
        # Get recent actions from memory
        recent_actions = self.short_term_memory.get_recent_actions(20)  # Last 20 actions

        # Find patterns of different lengths
        patterns = []

        for pattern_length in range(self.min_pattern_length,
                                    min(self.max_pattern_length + 1, len(recent_actions) // 2)):
            # Scan for repeating subsequences
            action_patterns = self._find_repeating_subsequences(
                recent_actions, pattern_length, key=lambda a: a["action_id"]
            )

            for pattern in action_patterns:
                pattern_key = self._create_pattern_key([a["action_id"] for a in pattern])

                # Check if we've seen this pattern before
                if pattern_key in self.action_patterns:
                    # Update existing pattern
                    self.action_patterns[pattern_key].update(True)
                else:
                    # Create new pattern
                    new_pattern = InteractionPattern(pattern, [])
                    self.action_patterns[pattern_key] = new_pattern
                    patterns.append(new_pattern)

        return patterns

    def analyze_state_transitions(self) -> List[InteractionPattern]:
        """
        Analyze short-term memory for recurring state transitions.

        Returns:
            List of detected state transition patterns
        """
        # Get recent states from memory
        recent_states = self.short_term_memory.get_recent_states(20)  # Last 20 states

        # Find patterns of different lengths
        patterns = []

        for pattern_length in range(self.min_pattern_length, min(self.max_pattern_length + 1, len(recent_states) // 2)):
            # Scan for repeating subsequences
            state_patterns = self._find_repeating_subsequences(
                recent_states, pattern_length, key=lambda s: s["fingerprint"]
            )

            for pattern in state_patterns:
                pattern_key = self._create_pattern_key([s["fingerprint"] for s in pattern])

                # Check if we've seen this pattern before
                if pattern_key in self.state_transition_patterns:
                    # Update existing pattern
                    self.state_transition_patterns[pattern_key].update(True)
                else:
                    # Create new pattern
                    new_pattern = InteractionPattern([], pattern)
                    self.state_transition_patterns[pattern_key] = new_pattern
                    patterns.append(new_pattern)

        return patterns

    def analyze_navigation_flows(self) -> List[Dict[str, Any]]:
        """
        Analyze memory for navigation flows between activities.

        Returns:
            List of navigation flow patterns
        """
        # Get available activity transitions from long-term memory
        if not self.long_term_memory:
            return []

        # Extract activity transitions
        activity_transitions = defaultdict(int)

        for transition in self.long_term_memory.transition_graph.transitions:
            key = f"{transition.source_activity}|{transition.target_activity}"
            activity_transitions[key] += 1

        # Find common navigation flows
        common_flows = []
        for key, count in activity_transitions.items():
            if count >= self.detection_threshold:
                source, target = key.split("|")
                common_flows.append({
                    "source_activity": source,
                    "target_activity": target,
                    "count": count
                })

        # Sort by frequency (descending)
        common_flows.sort(key=lambda x: x["count"], reverse=True)

        return common_flows

    def detect_form_filling_patterns(self) -> List[Dict[str, Any]]:
        """
        Detect patterns related to form filling.

        Returns:
            List of form filling patterns
        """
        # Get recent actions from memory
        recent_actions = self.short_term_memory.get_recent_actions(30)  # Last 30 actions

        # Look for sequences of text input followed by button clicks
        form_patterns = []
        text_inputs = []

        for i, action in enumerate(recent_actions):
            action_text = action["action_text"]

            # Collect text input actions
            if "SET_TEXT" in action_text:
                text_inputs.append((i, action))

            # Look for submit actions after text inputs
            elif "CLICK" in action_text and text_inputs:
                # Check if this might be a form submission
                submit_keywords = ["submit", "login", "sign", "register", "confirm", "ok", "next", "continue"]

                is_submit = any(keyword in action_text.lower() for keyword in submit_keywords)

                if is_submit:
                    # Find all text inputs that precede this submit action
                    form_inputs = [text_inputs[j][1] for j in range(len(text_inputs)) if text_inputs[j][0] < i]

                    if form_inputs:
                        form_pattern = {
                            "inputs": form_inputs,
                            "submit": action,
                            "count": 1
                        }

                        # Check for duplicates before adding
                        is_duplicate = False
                        for existing in form_patterns:
                            if existing["submit"]["action_id"] == action["action_id"]:
                                is_duplicate = True
                                existing["count"] += 1
                                break

                        if not is_duplicate:
                            form_patterns.append(form_pattern)

                        # Reset text inputs after form submission
                        text_inputs = []

        return form_patterns

    def detect_common_action_sequences(self) -> List[Dict[str, Any]]:
        """
        Detect common sequences of actions that occur together.

        Returns:
            List of common action sequences
        """
        common_sequences = []

        # Check all action patterns with sufficient occurrences
        for pattern_key, pattern in self.action_patterns.items():
            if pattern.occurrences >= self.detection_threshold:
                # Create sequence description
                sequence = {
                    "actions": pattern.actions,
                    "occurrences": pattern.occurrences,
                    "success_rate": pattern.get_success_rate(),
                    "last_seen": pattern.last_seen
                }

                common_sequences.append(sequence)

        # Sort by occurrences (descending)
        common_sequences.sort(key=lambda x: x["occurrences"], reverse=True)

        return common_sequences

    def detect_cycles(self) -> List[Dict[str, Any]]:
        """
        Detect cycles in state transitions.

        Returns:
            List of detected cycles
        """
        # Use short-term memory's cycle detection
        is_cycle, cycle_states = self.short_term_memory.detect_cycles()

        if is_cycle and cycle_states:
            # Create cycle description
            cycle = {
                "states": cycle_states,
                "length": len(cycle_states),
                "timestamp": time.time()
            }

            return [cycle]

        return []

    def _find_repeating_subsequences(self, items: List[Dict[str, Any]],
                                     length: int,
                                     key=lambda x: x) -> List[List[Dict[str, Any]]]:
        """
        Find repeating subsequences in a list of items.

        Args:
            items: List of items
            length: Length of subsequences to find
            key: Function to extract key from items

        Returns:
            List of repeating subsequences
        """
        if len(items) < length * 2:
            return []

        # Find all subsequences of the given length
        subsequences = []
        subsequence_keys = {}

        for i in range(len(items) - length + 1):
            subsequence = items[i:i + length]
            subsequence_key = tuple(key(item) for item in subsequence)

            if subsequence_key in subsequence_keys:
                subsequence_keys[subsequence_key].append(i)
            else:
                subsequence_keys[subsequence_key] = [i]

        # Find repeating subsequences
        for subsequence_key, indices in subsequence_keys.items():
            if len(indices) >= self.detection_threshold:
                # Get the actual subsequence (using the first occurrence)
                start_idx = indices[0]
                subsequence = items[start_idx:start_idx + length]
                subsequences.append(subsequence)

        return subsequences

    def _create_pattern_key(self, ids: List[Any]) -> str:
        """
        Create a string key for a pattern.

        Args:
            ids: List of identifiers

        Returns:
            String key
        """
        return "|".join(str(id) for id in ids)

    def get_pattern_stats(self) -> Dict[str, Any]:
        """
        Get statistics about detected patterns.

        Returns:
            Dictionary with pattern statistics
        """
        return {
            "action_patterns": len(self.action_patterns),
            "state_transition_patterns": len(self.state_transition_patterns),
            "navigation_patterns": len(self.navigation_patterns),
            "detection_threshold": self.detection_threshold
        }
   