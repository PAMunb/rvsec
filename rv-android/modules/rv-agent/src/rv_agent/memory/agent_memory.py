"""
Agent Memory Manager for Stateless Context.

Manages memory summaries for RVAgent without accumulating message history.
Provides pre-formatted string summaries that enable constant-token LLM calls.

### Architectural Pattern:
Inspired by rvsmart-tool's MemoryManager, this module maintains internal
action history and exploration state, but exports only PRE-FORMATTED STRINGS
for inclusion in fresh LLM messages.

### Key Features:
- Limited action history (default 5 most recent)
- Activity visit tracking
- Navigation path generation
- Exploration progress summaries
- Memory insights for LLM decision-making
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from collections import deque


logger = logging.getLogger(__name__)


class AgentMemoryManager:
    """
    Manages memory summaries for stateless LLM context.

    ### Architectural Overview:
    This manager maintains internal state (action history, activity visits,
    navigation path) but exports only PRE-FORMATTED STRING SUMMARIES. This
    enables stateless LLM messaging where each call receives a fresh message
    with all necessary context embedded as text.

    ### Integration with rvsmart-tool Pattern:
    - Like rvsmart-tool's MemoryManager.enrich_state_with_history()
    - Generates formatted strings, not raw objects
    - Limits history to prevent context bloat
    - Provides exploration guidance based on visit patterns

    ### Memory Components:
    - Action History: Last N actions with types and explanations
    - Activity Visits: Count of visits per activity
    - Navigation Path: Recent activity transition sequence
    - Exploration Insights: Suggestions based on visit patterns
    """

    def __init__(self, max_action_history: int = 5, max_navigation_path: int = 5):
        """
        Initialize memory manager with configuration.

        Args:
            max_action_history: Maximum number of actions to keep in history
            max_navigation_path: Maximum activities to show in navigation path
        """
        self.max_action_history = max_action_history
        self.max_navigation_path = max_navigation_path

        # Internal storage (NOT exposed directly)
        self.action_history = deque(maxlen=max_action_history)
        self.activity_visits: Dict[str, int] = {}
        self.navigation_path: List[str] = []

        logger.info(f"AgentMemoryManager initialized (max_actions={max_action_history}, "
                   f"max_path={max_navigation_path})")

    def record_action(self, action: Dict, activity: str, success: bool = True):
        """
        Record action execution and update internal state.

        Args:
            action: Action dictionary with type, target, explanation
            activity: Activity where action was executed
            success: Whether action succeeded
        """
        # Add to action history (deque auto-limits)
        action_record = {
            "action_type": action.get("action_type", "unknown"),
            "explanation": action.get("explanation", ""),
            "activity": activity,
            "success": success,
            "coords": (action.get("x", 0), action.get("y", 0))
        }
        self.action_history.append(action_record)

        # Update activity visits
        self.activity_visits[activity] = self.activity_visits.get(activity, 0) + 1

        # Update navigation path (only on activity changes)
        if not self.navigation_path or self.navigation_path[-1] != activity:
            self.navigation_path.append(activity)
            # Trim to max length
            if len(self.navigation_path) > self.max_navigation_path:
                self.navigation_path.pop(0)

        logger.debug(f"Recorded action {action_record['action_type']} in {activity}")

    def get_action_history_summary(self) -> str:
        """
        Generate pre-formatted action history summary string with coordinates.

        ### Output Format:
        ```
        Recent actions (5):
          1. CLICK at (540, 633): Tap on login button
          2. SET_TEXT at (540, 268): Enter email address
          3. CLICK at (540, 800): Submit login form
          ...
        ```

        Returns:
            Formatted action history string for LLM context
        """
        if not self.action_history:
            return "No previous actions executed yet."

        lines = [f"Recent actions ({len(self.action_history)}):"]
        for i, action in enumerate(self.action_history, 1):
            action_type = action["action_type"]
            explanation = action["explanation"]
            coords = action.get("coords", (0, 0))
            success_marker = "" if action["success"] else " [FAILED]"

            # Format: "1. CLICK at (540, 633): Explanation text"
            lines.append(f"  {i}. {action_type} at {coords}: {explanation}{success_marker}")

        return "\n".join(lines)

    def get_exploration_summary(self, visited_states: List[str],
                                state_transitions: List[Tuple[str, str]]) -> str:
        """
        Generate exploration progress summary string.

        ### Output Format:
        ```
        Exploration Progress:
        - Unique screens visited: 15
        - State transitions discovered: 23
        - Activities explored: 4
        ```

        Args:
            visited_states: List of visited state hashes
            state_transitions: List of tuples (prev_state, curr_state)

        Returns:
            Formatted exploration summary string
        """
        num_states = len(visited_states)
        num_transitions = len(state_transitions)
        num_activities = len(self.activity_visits)

        lines = [
            "Exploration Progress:",
            f"- Unique screens visited: {num_states}",
            f"- State transitions discovered: {num_transitions}",
            f"- Activities explored: {num_activities}"
        ]

        return "\n".join(lines)

    def get_memory_insights(self, current_activity: str) -> str:
        """
        Generate memory insights summary for LLM guidance.

        ### Output Format:
        ```
        Memory Insights:
        - Current activity 'MainActivity' visited 3 times
        - Total activities explored: 4
        - Least visited: SettingsActivity (1 visit) - consider exploring
        ```

        Args:
            current_activity: Current activity name

        Returns:
            Formatted insights string with exploration suggestions
        """
        visit_count = self.activity_visits.get(current_activity, 1)
        total_activities = len(self.activity_visits)

        lines = [
            "Memory Insights:",
            f"- Current activity '{current_activity}' visited {visit_count} time(s)",
            f"- Total activities explored: {total_activities}"
        ]

        # Suggest least visited activity (if more than 1 activity)
        if total_activities > 1:
            least_visited_activity, least_visits = min(
                self.activity_visits.items(),
                key=lambda x: x[1]
            )

            # Only suggest if it's not the current activity
            if least_visited_activity != current_activity:
                lines.append(
                    f"- Least visited: '{least_visited_activity}' ({least_visits} visit(s)) "
                    "- consider exploring"
                )
        else:
            lines.append("- Try to discover new activities through navigation")

        return "\n".join(lines)

    def get_navigation_path(self) -> str:
        """
        Generate navigation path summary string.

        ### Output Format:
        ```
        Navigation Path: MainActivity → LoginActivity → HomeActivity → SettingsActivity
        ```

        Returns:
            Formatted navigation path string
        """
        if not self.navigation_path:
            return "Navigation Path: Starting exploration"

        # Show last N activities
        recent_path = self.navigation_path[-self.max_navigation_path:]
        path_str = " → ".join(recent_path)

        return f"Navigation Path: {path_str}"

    def clear(self):
        """Clear all memory state (for testing or reset)."""
        self.action_history.clear()
        self.activity_visits.clear()
        self.navigation_path.clear()
        logger.info("Memory cleared")
