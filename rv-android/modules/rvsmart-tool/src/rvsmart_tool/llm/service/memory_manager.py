"""
Memory Manager Module

This module provides the MemoryManager class, which is responsible for coordinating
short-term and long-term memory systems in the RV-Android platform. The memory
manager tracks action execution history, maintains statistics about visited
screens, and enriches state with historical context.

The memory system is organized into:
1. Short-term memory: Stores actions within the current activity (cleared on activity change)
2. Long-term memory: Persists data throughout a task execution (not between executions)
"""

import hashlib
import json
import time
from typing import Dict, List, Any, Optional

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.llm.constants import StateEntry
from rvsmart_tool.core.memory.long_term_memory import LongTermMemory, MemoryAction, MemoryState
from rvsmart_tool.core.memory.short_term_memory import ShortTermMemory
from rvsmart_tool.llm.service.action_generator import GeneratedAction


class MemoryManager:
    """
    Manages both short-term and long-term memory systems.
    
    The MemoryManager coordinates the memory systems, handling activity
    transitions, action recording, and state enrichment with historical
    context. It provides a unified interface for memory operations.
    
    ### Architectural Decisions:
    - Utilizes and integrates with the core memory systems (ShortTermMemory, LongTermMemory)
    - Acts as the primary storage for all action history
    - Provides methods to retrieve actions for transition management 
    - Does not duplicate action storage across components
    - Maintains consistent activity naming and state hashing
    
    ### Role in the System:
    - Provides historical context for LLM prompts
    - Tracks action execution and activity navigation
    - Supplies action data to TransitionManager when transitions occur
    - Enriches states with memory insights for better LLM context
    
    Attributes:
        short_term: Short-term memory system (per activity)
        long_term: Long-term memory system (per task execution)
        logger: Logger instance for this class
        error_handler: Error handler for managing exceptions
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None,
                 max_short_term_iterations: int = 10):
        """
        Initialize the memory manager with memory systems.
        
        Args:
            static_data: Optional static analysis data
            max_short_term_iterations: Maximum number of iterations in short-term memory
        """
        # Initialize memory systems using the core implementations
        self.short_term = ShortTermMemory(max_iterations=max_short_term_iterations)
        self.long_term = LongTermMemory(static_data)

        # Set up error handling and logging
        self.error_handler = ErrorHandler.get_instance()
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvsmart_tool.llm.service.memory_manager",
            {CONTEXT_COMPONENT: "MemoryManager"}
        )

        self.logger.info("Initialized memory manager")

    def update(self, state: Dict[str, Any]) -> None:
        """
        Update memory systems based on current state.
        
        This method extracts state information and updates both memory systems.
        The ShortTermMemory will automatically handle activity transitions
        and clearing memory when needed.
        
        Args:
            state: Current application state
        """
        try:
            # Update long-term memory with state information
            activity = self._get_activity_from_state(state)
            state_hash = self._compute_state_hash(state)
            self.logger.info(f"Activity ({activity}) hash: {state_hash}")

            # Create or update memory state in long-term memory
            if state_hash not in self.long_term.states:
                memory_state = MemoryState(state_hash, activity)
                self.logger.info(f"Create or update memory state: {memory_state.to_dict()}")

                # Set screenshot if available
                if StateEntry.SCREENSHOT_PATH in state:
                    memory_state.set_screenshot(state[StateEntry.SCREENSHOT_PATH])

                # Set interactive element count if available
                if StateEntry.STRUCTURED_SCREEN in state:
                    screen_description = state[StateEntry.STRUCTURED_SCREEN]
                    memory_state.interactive_elements_count = len(screen_description.items)

                # Record in long-term memory
                self.long_term.record_state(memory_state)
            else:
                # Update existing state
                memory_state = self.long_term.states[state_hash]
                memory_state.record_visit()
                self.logger.info(f"Update existing state: {memory_state}")

                # Update screenshot if available
                if StateEntry.SCREENSHOT_PATH in state:
                    memory_state.set_screenshot(state[StateEntry.SCREENSHOT_PATH])

            self.logger.debug(f"Updated state: activity={activity}, hash={state_hash}")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "MemoryManager",
                    "method": "update",
                    "state": str(state)[:100]
                }
            )

    def record_actions(self, state: Dict[str, Any], actions: List[GeneratedAction],
                       action_selection_reason: str = "", succeeded: bool = True) -> None:
        """
        Record actions in both memory systems.
        
        This method stores the executed actions in both short-term and long-term
        memory, along with contextual information about where they were executed.
        
        Args:
            state: State where actions were executed
            actions: List of actions that were executed
            action_selection_reason: Optional explanation for why these actions were selected
            succeeded: Whether the actions executed successfully
        """
        try:
            if not actions:
                return

            # Record in short-term memory
            self.short_term.record_iteration(state, actions)

            # Record in long-term memory
            state_hash = state.get(StateEntry.HASH_SCREEN_CONTENT,
                                   state.get(StateEntry.HASH_SCREEN, "unknown"))

            for action in actions:
                # Create memory action
                memory_action = MemoryAction.from_action(action)

                # Record in long-term memory
                self.long_term.record_action(memory_action, state_hash, succeeded)

            activity = self._get_activity_from_state(state)
            self.logger.debug(f"Recorded {len(actions)} actions in activity '{activity}'")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "MemoryManager",
                    "method": "record_actions",
                    "actions_count": len(actions) if actions else 0
                }
            )

    # TODO deprecated ??
    def record_transition(self, from_state: Dict[str, Any], to_state: Dict[str, Any],
                          action: GeneratedAction, succeeded: bool = True) -> None:
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
            self.long_term.record_transition(from_hash, to_hash, memory_action, succeeded)

            self.logger.debug(f"Recorded transition: {from_hash} -> {to_hash}, action={action.id}")

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "MemoryManager",
                    "method": "record_transition"
                }
            )

    def get_recent_activity_actions(self) -> List[Dict[str, Any]]:
        """
        Get actions from the current activity for transition tracking.
        
        Returns:
            List of action dictionaries from the current activity
        """
        try:
            # Convert Iteration objects to compatible dictionary format
            recent_iterations = self.short_term.get_recent_iterations()
            all_actions = []

            for iteration in recent_iterations:
                for action in iteration.actions:
                    action_dict = {
                        "action_id": action.id,
                        "action_type": action.action_type,
                        "text": action.text,
                        "coordinates": action.coordinates if hasattr(action, 'coordinates') else None,
                        "explanation": action.explanation if hasattr(action, 'explanation') else None,
                        "params": action.params if hasattr(action, 'params') else {}
                    }
                    all_actions.append(action_dict)

            return all_actions

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "MemoryManager",
                    "method": "get_recent_activity_actions"
                }
            )
            return []

    def enrich_state_with_history(self, state: Dict[str, Any],
                                  short_term_limit: int = 5,
                                  long_term_limit: int = 10) -> Dict[str, Any]:
        """
        Enrich state with historical context from memory systems.
        
        This method adds memory information to the state, including recent
        iterations from short-term memory and historical context from long-term
        memory. This enriched state provides valuable context for LLM decisions.
        
        Args:
            state: Current application state
            short_term_limit: Maximum number of recent iterations to include
            long_term_limit: Maximum number of recent actions from long-term memory
            
        Returns:
            Enriched state with added historical context
        """
        try:
            # Add short-term memory context
            formatted_history = self.short_term.format_for_template(short_term_limit)
            state[StateEntry.ACTION_HISTORY] = formatted_history
            self.logger.info(f"Action history: {formatted_history}")

            # Add long-term memory insights
            activity = self._get_activity_from_state(state)
            # TODO rever esta pegando do droidbot ou calculando?
            state_hash = state.get(StateEntry.HASH_SCREEN_CONTENT,
                                   state.get(StateEntry.HASH_SCREEN, "unknown"))

            # Generate insights
            insights = self._get_long_term_insights(state_hash, activity)
            state[StateEntry.MEMORY_INSIGHTS] = insights
            self.logger.info(f"Insights: {insights}")

            # Add activity visit information
            state[StateEntry.ACTIVITY_VISITS] = {
                "current_activity": activity,
                "visit_count": self.long_term.get_activity_visit_count(activity),
                "activity_statistics": self.long_term.get_activity_statistics()
            }
            self.logger.info(f"Activity visits: {state[StateEntry.ACTIVITY_VISITS]}")

            # Add navigation history
            navigation_path = self.long_term.get_visited_activities()
            state[StateEntry.NAVIGATION_PATH] = navigation_path
            self.logger.info(f"Navigation path: {navigation_path}")

            # For backward compatibility with the old format
            # TODO rever backward
            recent_iterations = self.short_term.get_recent_iterations(short_term_limit)
            compat_iterations = []

            for i, iteration in enumerate(recent_iterations):
                compat_actions = []
                for action in iteration.actions:
                    compat_action = {
                        "action_id": action.id,
                        "action_type": action.action_type,
                        "text": action.text
                    }
                    if hasattr(action, 'coordinates'):
                        compat_action["coordinates"] = action.coordinates
                    if hasattr(action, 'explanation'):
                        compat_action["explanation"] = action.explanation
                    if hasattr(action, 'params'):
                        compat_action["params"] = action.params
                    compat_actions.append(compat_action)

                compat_iteration = {
                    "iteration_number": i + 1,
                    "timestamp": iteration.timestamp.timestamp(),
                    "actions": compat_actions,
                    "action_selection_reason": ""  # Not tracked in original implementation
                }
                compat_iterations.append(compat_iteration)

            state[StateEntry.RECENT_ITERATIONS] = compat_iterations
            self.logger.info(f"Recent iterations: {state[StateEntry.RECENT_ITERATIONS]}")

            self.logger.debug("Enriched state with history data")
            return state

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "MemoryManager",
                    "method": "enrich_state_with_history"
                }
            )
            return state  # Return original state if enrichment fails

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
        memory_state = self.long_term.get_state_by_fingerprint(state_hash)

        if memory_state:
            # Visit frequency
            insights.append(f"This screen has been visited {memory_state.visit_count} times")

            # Interactive elements
            if memory_state.interactive_elements_count > 0:
                tested_count = len(memory_state.all_actions)
                insights.append(
                    f"You have interacted with {tested_count} of {memory_state.interactive_elements_count} elements on this screen")

        # Get available transitions
        if activity in self.long_term.activities:
            activity_info = self.long_term.activities[activity]
            if "states" in activity_info and activity_info["states"]:
                transitions = set()

                # Collect all transitions from all states in this activity
                for state_id in activity_info["states"]:
                    if state_id in self.long_term.states:
                        state = self.long_term.states[state_id]
                        for target in state.outgoing_transitions.keys():
                            if target in self.long_term.states:
                                target_state = self.long_term.states[target]
                                transitions.add(target_state.activity)

                # Format transitions
                if transitions:
                    transitions_list = list(transitions)
                    if len(transitions_list) == 1:
                        insights.append(f"This screen navigates to: {transitions_list[0]}")
                    else:
                        insights.append(f"This screen navigates to: {', '.join(transitions_list)}")

        # Get least visited activities for exploration guidance
        least_visited = self.long_term.get_least_visited_activities(3)
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

    def _get_activity_from_state(self, state: Dict[str, Any]) -> str:
        """
        Extract the activity name from the state.
        
        Args:
            state: Current application state
            
        Returns:
            Name of the current activity, or 'unknown' if not found
        """
        # Try different possible locations of activity information
        if isinstance(state, dict):
            # Look for activity in different possible locations
            if StateEntry.ACTIVITY in state:
                return state[StateEntry.ACTIVITY]
            if "activity" in state:
                return state["activity"]
            if "foreground_activity" in state:
                return state["foreground_activity"]

        return "unknown"

    def _compute_state_hash(self, state: Dict[str, Any]) -> str:
        """
        Compute a hash of the state for change detection.
        
        Args:
            state: Current application state
            
        Returns:
            Hash string representing the state
        """
        try:
            # Check if state already has a hash
            if StateEntry.HASH_SCREEN in state:
                return state[StateEntry.HASH_SCREEN]

            # Use a stable JSON serialization for hashing with SHA-256
            stable_dict = self._create_stable_dict_for_hashing(state)
            state_json = json.dumps(stable_dict, sort_keys=True)
            state[StateEntry.HASH_SCREEN] = hashlib.sha256(state_json.encode()).hexdigest()
            return state[StateEntry.HASH_SCREEN]
        except Exception as e:
            self.logger.warning(f"Error computing state hash: {e}")
            return str(time.time())  # Fallback to timestamp if hashing fails

    def _create_stable_dict_for_hashing(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a stable dictionary for consistent hashing.
        
        This filters out volatile components of the state that shouldn't
        affect state identity (like timestamps, exact coordinates, etc.)
        
        Args:
            state: Original state dictionary
            
        Returns:
            Filtered dictionary suitable for stable hashing
        """
        # Keep only elements that contribute to state identity
        if not isinstance(state, dict):
            return {}

        result = {}

        # Include only relevant keys
        keys_to_include = ["activity", "package_name", "views", "state_id"]
        for key in keys_to_include:
            if key in state:
                result[key] = state[key]

        # Special handling for views - remove volatile properties
        if "views" in result and isinstance(result["views"], list):
            processed_views = []
            for view in result["views"]:
                if isinstance(view, dict):
                    processed_view = {}
                    # Include only stable properties
                    for prop in ["class", "resource_id", "text", "content_desc"]:
                        if prop in view:
                            processed_view[prop] = view[prop]
                    processed_views.append(processed_view)
            result["views"] = processed_views

        return result
        
    def cleanup(self) -> None:
        """
        Clean up resources used by the memory manager.
        
        This method should be called when the memory manager is no longer needed
        to ensure proper cleanup of resources.
        """
        try:
            # Clear short-term memory
            if hasattr(self, 'short_term_memory'):
                self.short_term_memory.clear()
                
            # Clear long-term memory references
            if hasattr(self, 'long_term_memory'):
                # The long_term_memory doesn't have a cleanup method yet,
                # but we can clear its references to help with garbage collection
                if hasattr(self.long_term_memory, 'states'):
                    self.long_term_memory.states.clear()
                if hasattr(self.long_term_memory, 'actions'):
                    self.long_term_memory.actions.clear()
                if hasattr(self.long_term_memory, 'activities'):
                    self.long_term_memory.activities.clear()
                if hasattr(self.long_term_memory, 'transitions'):
                    self.long_term_memory.transitions.clear()
            
            self.logger.info("Memory manager cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during memory manager cleanup: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "MemoryManager",
                    "function": "cleanup"
                }
            )
