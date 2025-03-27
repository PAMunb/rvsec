# rvandroid/rvdroid/memory/patterns/pattern_recognition.py

"""
Pattern recognition system for RVDroid.

This module provides functionality to detect recurring patterns in user
interactions and application behavior, enabling more intelligent testing.
"""

import time
from collections import defaultdict
from typing import Dict, Any, List, Optional, Sequence

from rvandroid.rvdroid.memory.long_term.long_term_memory import LongTermMemory
from rvandroid.rvdroid.memory.short_term.short_term_memory import ShortTermMemory
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class InteractionPattern:
    """
    Represents a pattern of interactions detected in the application.

    ### Architectural Decisions:
    - Stores both the sequence of actions and resulting states
    - Tracks pattern statistics including occurrences and success rate
    - Provides self-contained pattern analysis capabilities
    - Enables efficient pattern matching and evaluation

    ### Role in the System:
    - Encapsulates detected interaction patterns for reuse
    - Supports pattern-based testing strategies
    - Enables learning from successful interaction sequences
    - Facilitates identification of critical application workflows
    """

    def __init__(self, action_ids: List[int], state_fingerprints: List[str]):
        """
        Initialize an interaction pattern.

        Args:
            action_ids: List of action IDs in the pattern
            state_fingerprints: List of state fingerprints in the pattern
        """
        self.action_ids = action_ids
        self.state_fingerprints = state_fingerprints
        self.occurrences = 1
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.success_count = 0
        self.failure_count = 0
        self.pattern_id = self._generate_pattern_id()

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

    def matches(self, action_ids: List[int], min_match_length: int = 2) -> bool:
        """
        Check if this pattern matches a sequence of actions.

        Args:
            action_ids: List of action IDs to match against
            min_match_length: Minimum match length to consider a match

        Returns:
            True if pattern matches, False otherwise
        """
        if len(action_ids) < min_match_length:
            return False

        # Check if the action_ids list contains this pattern
        pattern_length = len(self.action_ids)

        for i in range(len(action_ids) - pattern_length + 1):
            if action_ids[i:i + pattern_length] == self.action_ids:
                return True

        return False

    def _generate_pattern_id(self) -> str:
        """
        Generate a unique ID for this pattern.

        Returns:
            Pattern ID string
        """
        import hashlib

        # Combine action IDs and state fingerprints
        components = [str(aid) for aid in self.action_ids]
        components.extend(self.state_fingerprints)

        # Generate hash
        pattern_string = "|".join(components)
        return hashlib.md5(pattern_string.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert pattern to dictionary.

        Returns:
            Dictionary representation of pattern
        """
        return {
            "pattern_id": self.pattern_id,
            "action_ids": self.action_ids,
            "state_fingerprints": self.state_fingerprints,
            "occurrences": self.occurrences,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.get_success_rate()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InteractionPattern':
        """
        Create pattern from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            InteractionPattern instance
        """
        pattern = cls(
            action_ids=data["action_ids"],
            state_fingerprints=data["state_fingerprints"]
        )

        pattern.occurrences = data["occurrences"]
        pattern.first_seen = data["first_seen"]
        pattern.last_seen = data["last_seen"]
        pattern.success_count = data["success_count"]
        pattern.failure_count = data["failure_count"]
        pattern.pattern_id = data["pattern_id"]

        return pattern


class PatternRecognition:
    """
    Recognizes patterns in application interactions.

    ### Architectural Decisions:
    - Uses a simplified pattern detection algorithm with reduced computational complexity
    - Focuses on actionable patterns that can guide testing
    - Integrates with memory systems to track patterns throughout the test session
    - Implements optimized pattern matching with minimal overhead
    - Provides clear pattern classification and prioritization mechanisms

    ### Role in the System:
    - Analyzes interactions stored in memory to identify recurring patterns
    - Guides exploration by identifying valuable interaction sequences
    - Helps predict action outcomes based on historical patterns
    - Identifies potential test scenarios for systematic validation
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
        self.state_patterns: Dict[str, InteractionPattern] = {}
        self.form_patterns: List[Dict[str, Any]] = []
        self.navigation_patterns: List[Dict[str, Any]] = []

        # Configuration
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
        action_ids = [a.id for a in recent_actions]

        # Find patterns of different lengths
        new_patterns = []

        for pattern_length in range(self.min_pattern_length,
                                    min(self.max_pattern_length + 1, len(action_ids) // 2)):
            # Find repeating subsequences
            subsequences = self._find_repeating_subsequences(action_ids, pattern_length)

            for subsequence in subsequences:
                # Get corresponding states if possible
                state_fingerprints = []
                for i in range(len(subsequence)):
                    action_idx = action_ids.index(subsequence[i])
                    if i < len(recent_actions) and action_idx < len(recent_actions):
                        # Try to get state from transitions if available
                        # This is a simplified approach
                        pass

                # Create pattern key
                pattern_key = "|".join(str(aid) for aid in subsequence)

                # Check if we've seen this pattern before
                if pattern_key in self.action_patterns:
                    # Update existing pattern
                    self.action_patterns[pattern_key].update(True)
                else:
                    # Create new pattern
                    new_pattern = InteractionPattern(subsequence, state_fingerprints)
                    self.action_patterns[pattern_key] = new_pattern
                    new_patterns.append(new_pattern)

        return new_patterns

    def analyze_state_transitions(self) -> List[InteractionPattern]:
        """
        Analyze short-term memory for recurring state transitions.

        Returns:
            List of detected state transition patterns
        """
        # Get recent states from memory
        recent_states = self.short_term_memory.get_recent_states(20)  # Last 20 states
        state_fingerprints = [s.fingerprint for s in recent_states]

        # Find patterns of different lengths
        new_patterns = []

        for pattern_length in range(self.min_pattern_length,
                                    min(self.max_pattern_length + 1, len(state_fingerprints) // 2)):
            # Find repeating subsequences
            subsequences = self._find_repeating_subsequences(state_fingerprints, pattern_length)

            for subsequence in subsequences:
                # Create pattern key
                pattern_key = "|".join(subsequence)

                # Create corresponding action IDs if possible
                action_ids = []

                # Check if we've seen this pattern before
                if pattern_key in self.state_patterns:
                    # Update existing pattern
                    self.state_patterns[pattern_key].update(True)
                else:
                    # Create new pattern
                    new_pattern = InteractionPattern(action_ids, subsequence)
                    self.state_patterns[pattern_key] = new_pattern
                    new_patterns.append(new_pattern)

        return new_patterns

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
            # Collect text input actions
            if action.type == "text_input":
                text_inputs.append((i, action))

            # Look for submit actions after text inputs
            elif action.type == "click" and text_inputs:
                # Check if this might be a form submission
                is_submit = False

                # Check element properties if available
                if "Button" in action.element_properties.get("class", "") and action.element_properties.get("text", ""):
                    text = action.element_properties["text"].lower()
                    submit_keywords = ["submit", "login", "sign", "register", "confirm", "ok", "next", "continue"]
                    is_submit = any(keyword in text for keyword in submit_keywords)

                if is_submit:
                    # Find all text inputs that precede this submit action
                    form_inputs = [text_inputs[j][1] for j in range(len(text_inputs)) if text_inputs[j][0] < i]

                    if form_inputs:
                        form_pattern = {
                            "inputs": [a.id for a in form_inputs],
                            "submit": action.id,
                            "count": 1
                        }

                        # Check for duplicates before adding
                        is_duplicate = False
                        for existing in form_patterns:
                            if existing["submit"] == action.id:
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
                    "pattern_id": pattern.pattern_id,
                    "action_ids": pattern.action_ids,
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

    def _find_repeating_subsequences(self, items: Sequence[Any], length: int) -> List[List[Any]]:
        """
        Find repeating subsequences in a list of items.

        Args:
            items: List of items to search
            length: Length of subsequences to find

        Returns:
            List of repeating subsequences
        """
        if len(items) < length * 2:
            return []

        # Find all subsequences of the given length
        subsequence_counts = defaultdict(int)
        subsequences = []

        for i in range(len(items) - length + 1):
            # Convert subsequence to tuple for hashing
            if isinstance(items[i], str):
                subsequence = tuple(items[i:i + length])
            else:
                subsequence = tuple(str(item) for item in items[i:i + length])

            subsequence_counts[subsequence] += 1

            # If this is a repeat and we haven't added it yet
            if subsequence_counts[subsequence] == 2 and subsequence not in subsequences:
                # Convert back to list of original type
                if isinstance(items[i], str):
                    subsequences.append(list(subsequence))
                else:
                    subsequences.append([int(item) if item.isdigit() else item for item in subsequence])

        return subsequences

    def find_matching_patterns(self, action_ids: List[int]) -> List[InteractionPattern]:
        """
        Find patterns that match a sequence of actions.

        Args:
            action_ids: List of action IDs to match

        Returns:
            List of matching patterns
        """
        matching_patterns = []

        for pattern in self.action_patterns.values():
            if pattern.matches(action_ids):
                matching_patterns.append(pattern)

        # Sort by success rate and occurrences
        matching_patterns.sort(
            key=lambda p: (p.get_success_rate(), p.occurrences),
            reverse=True
        )

        return matching_patterns

    def get_pattern_stats(self) -> Dict[str, Any]:
        """
        Get statistics about detected patterns.

        Returns:
            Dictionary with pattern statistics
        """
        return {
            "action_patterns": len(self.action_patterns),
            "state_patterns": len(self.state_patterns),
            "form_patterns": len(self.form_patterns),
            "navigation_patterns": len(self.navigation_patterns),
            "detection_threshold": self.detection_threshold
        }
