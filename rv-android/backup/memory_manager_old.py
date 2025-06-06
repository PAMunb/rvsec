# rvandroid/llm/service/memory_manager.py
"""
Memory manager for coordinating short-term and long-term memory systems.

This module provides a unified interface for memory operations across both
short-term and long-term memory systems, ensuring consistent tracking of
actions, transitions, and application state.
"""

from typing import Dict, List, Any, Optional

from rvandroid.core.memory.long_term_memory import LongTermMemory, MemoryAction, MemoryState
from rvandroid.core.memory.short_term_memory import ShortTermMemory
from rv_android_core.domain.static import StaticAnalysisData
from rvandroid.llm.constants import StateEntry
from rvandroid.llm.service.action_generator import GeneratedAction
from rvandroid.parser.screen.visitor.model import ItemAction
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class MemoryManager:
    """
    Manages both short-term and long-term memory systems.

    ### Architectural Decisions:
    - Provides a unified interface for memory operations
    - Coordinates between short-term and long-term memory systems
    - Abstracts memory complexity from service layer
    - Handles consistent state tracking across memory systems
    - Prepares memory data for template inclusion

    ### Role in the System:
    - Central memory coordination point for LLMActionService
    - Tracks screen states, actions, and transitions
    - Formats historical context for prompt templates
    - Populates state with historical information
    - Maintains application navigation history
    """

    def __init__(self, app_package: str, static_data: Optional[StaticAnalysisData] = None,
                 max_short_term_iterations: int = 10):
        """
        Initialize the memory manager.

        Args:
            app_package: Application package name
            static_data: Optional static analysis data
            max_short_term_iterations: Maximum number of iterations in short-term memory
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.service.memory_manager",
            {CONTEXT_COMPONENT: "MemoryManager"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

        # Initialize memory systems
        self.short_term_memory = ShortTermMemory(max_iterations=max_short_term_iterations)
        self.long_term_memory = LongTermMemory(app_package, static_data)

        # Track the current state
        self.current_state_hash = None
        self.current_activity = None

        self.logger.info(f"Initialized memory manager for {app_package}")

    def update_state(self, state: Dict[str, Any]) -> None:
        """
        Update current state information.

        Args:
            state: Current application state
        """
        try:
            # Get activity and state hash
            activity = state.get(StateEntry.ACTIVITY, "unknown")
            state_hash = state.get(StateEntry.HASH_SCREEN_CONTENT,
                                   state.get(StateEntry.HASH_SCREEN, "unknown"))

            # Update current state
            self.current_state_hash = state_hash
            self.current_activity = activity

            # Create memory state if new
            if state_hash not in self.long_term_memory.states:
                memory_state = MemoryState(state_hash, activity)

                # Set screenshot if available
                if StateEntry.SCREENSHOT_PATH in state:
                    memory_state.set_screenshot(state[StateEntry.SCREENSHOT_PATH])

                # Set interactive element count if available
                if StateEntry.STRUCTURED_SCREEN in state:
                    screen_description = state[StateEntry.STRUCTURED_SCREEN]
                    memory_state.interactive_elements_count = len(screen_description.items)

                # Record in long-term memory
                self.long_term_memory.record_state(memory_state)
            else:
                # Update existing state
                memory_state = self.long_term_memory.states[state_hash]
                memory_state.record_visit()

                # Update screenshot if available
                if StateEntry.SCREENSHOT_PATH in state:
                    memory_state.set_screenshot(state[StateEntry.SCREENSHOT_PATH])

            self.logger.debug(f"Updated state: activity={activity}, hash={state_hash}")

        except Exception as e:
            self.logger.error(f"Error updating state: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "MemoryManager",
                    "function": "update_state",
                    "activity": state.get(StateEntry.ACTIVITY, "unknown")
                }
            )

    def record_actions(self, state: Dict[str, Any], actions: List[GeneratedAction], succeeded = True) -> None:
        """
        Record actions in both memory systems.

        Args:
            state: Current application state
            actions: List of executed actions (as dictionaries from response processor)
            result_message: Optional result message
        """
        try:

            # Record in short-term memory
            self.short_term_memory.record_iteration(state, actions)

            # Record in long-term memory
            state_hash = state.get(StateEntry.HASH_SCREEN_CONTENT,
                                   state.get(StateEntry.HASH_SCREEN, "unknown"))

            for item_action in actions:
                # Create memory action
                memory_action = MemoryAction.from_action(item_action)

                # Record in long-term memory
                self.long_term_memory.record_action(memory_action, state_hash, succeeded)

            self.logger.debug(f"Recorded {len(actions)} actions, success={succeeded}")

        except Exception as e:
            self.logger.error(f"Error recording actions: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "MemoryManager",
                    "function": "record_actions"
                }
            )

    def record_transition(self, from_state: Dict[str, Any], to_state: Dict[str, Any],
                          action: ItemAction, succeeded: bool = True) -> None:
        """
        Record a transition between states.

        Args:
            from_state: Source state
            to_state: Destination state
            action: Action that caused the transition
            succeeded: Whether the transition succeeded
        """
        try:
            # Get state hashes
            from_hash = from_state.get(StateEntry.HASH_SCREEN_CONTENT,
                                       from_state.get(StateEntry.HASH_SCREEN, "unknown"))
            to_hash = to_state.get(StateEntry.HASH_SCREEN_CONTENT,
                                   to_state.get(StateEntry.HASH_SCREEN, "unknown"))

            # Create memory action
            memory_action = MemoryAction.from_action(action)

            # Record in long-term memory
            self.long_term_memory.record_transition(from_hash, to_hash, memory_action, succeeded)

            self.logger.debug(f"Recorded transition: {from_hash} -> {to_hash}, action={action.id}")

        except Exception as e:
            self.logger.error(f"Error recording transition: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "MemoryManager",
                    "function": "record_transition"
                }
            )

    def enrich_state_with_history(self, state: Dict[str, Any], limit: int = 5):
        """
        Enrich the current state with historical information.

        Args:
            state: Current application state
            limit: Maximum number of iterations to include

        Returns:
            Enriched state dictionary
        """
        try:
            # Add short-term memory
            short_term_history = self.short_term_memory.format_for_template(limit)

            # Add insights from long-term memory
            activity = state.get(StateEntry.ACTIVITY, "unknown")
            state_hash = state.get(StateEntry.HASH_SCREEN_CONTENT,
                                   state.get(StateEntry.HASH_SCREEN, "unknown"))

            long_term_insights = self._get_long_term_insights(state_hash, activity)

            # Combine insights
            state[StateEntry.ACTION_HISTORY] = short_term_history
            state[StateEntry.MEMORY_INSIGHTS] = long_term_insights

            self.logger.debug("Enriched state with history data")

        except Exception as e:
            self.logger.error(f"Error enriching state with history: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "MemoryManager",
                    "function": "enrich_state_with_history"
                }
            )
            # Return original state in case of error
            return state

    def _get_long_term_insights(self, state_hash: str, activity: str) -> str:
        """
        Get insights from long-term memory.

        Args:
            state_hash: Current state hash
            activity: Current activity name

        Returns:
            Formatted insights string
        """
        insights = []

        # Get state information
        memory_state = self.long_term_memory.get_state_by_fingerprint(state_hash)

        if memory_state:
            # Visit frequency
            insights.append(f"This screen has been visited {memory_state.visit_count} times")

            # Interactive elements
            if memory_state.interactive_elements_count > 0:
                tested_count = len(memory_state.all_actions)
                insights.append(
                    f"You have interacted with {tested_count} of {memory_state.interactive_elements_count} elements on this screen")

        # Get available transitions
        if activity in self.long_term_memory.activities:
            activity_info = self.long_term_memory.activities[activity]
            if "states" in activity_info and activity_info["states"]:
                transitions = set()

                # Collect all transitions from all states in this activity
                for state_id in activity_info["states"]:
                    if state_id in self.long_term_memory.states:
                        state = self.long_term_memory.states[state_id]
                        for target in state.outgoing_transitions.keys():
                            if target in self.long_term_memory.states:
                                target_state = self.long_term_memory.states[target]
                                transitions.add(target_state.activity)

                # Format transitions
                if transitions:
                    transitions_list = list(transitions)
                    if len(transitions_list) == 1:
                        insights.append(f"This screen navigates to: {transitions_list[0]}")
                    else:
                        insights.append(f"This screen navigates to: {', '.join(transitions_list)}")

        # Get least visited activities for exploration guidance
        least_visited = self.long_term_memory.get_least_visited_activities(3)
        if least_visited:
            suggestions = []
            for activity_info in least_visited:
                if activity_info["visit_count"] == 0:
                    suggestions.append(f"{activity_info['name']} (not visited)")
                else:
                    suggestions.append(f"{activity_info['name']} (visited {activity_info['visit_count']} times)")

            insights.append(f"Consider exploring: {', '.join(suggestions)}")

        # Format insights
        if not insights:
            return "No historical insights available for this screen."

        return "Memory insights:\n- " + "\n- ".join(insights)

    def clear_short_term_memory(self) -> None:
        """Clear short-term memory."""
        self.short_term_memory.clear()
        self.logger.debug("Short-term memory cleared")

    def get_short_term_memory(self) -> ShortTermMemory:
        """
        Get the short-term memory instance.

        Returns:
            ShortTermMemory instance
        """
        return self.short_term_memory

    def get_long_term_memory(self) -> LongTermMemory:
        """
        Get the long-term memory instance.

        Returns:
            LongTermMemory instance
        """
        return self.long_term_memory
