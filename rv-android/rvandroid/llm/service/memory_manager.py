"""
Memory Manager Module

This module provides the MemoryManager class, which is responsible for coordinating
short-term and long-term memory systems in the RV-Android platform. The memory
manager tracks action execution history, maintains statistics about visited
screens, and enriches state with historical context.

The memory system is organized into:
1. Short-term memory: Stores actions within the current activity (cleared on activity change)
2. Long-term memory: Persists data throughout a task execution (not between executions)

Author: Claude
Date: 2025-05-04
"""

from typing import Dict, List, Any, Optional, Tuple
import time
import copy
import hashlib
import json

from rvandroid.llm.constants import StateEntry
from rvandroid.llm.service.action_generator import GeneratedAction
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
# from rvandroid.core.memory.short_term_memory import ShortTermMemory

class ShortTermMemory:
    """
    Short-term memory system that stores recent interactions within a single activity.
    
    This memory is cleared when the activity changes. It stores iterations
    (LLM consultations) and their associated actions for the current activity.
    
    Attributes:
        iterations: List of iterations with associated actions and timestamps
        current_activity: The activity this memory is associated with
        current_state_hash: Hash of the current state for change detection
    """
    
    def __init__(self):
        """Initialize an empty short-term memory."""
        self.iterations: List[Dict[str, Any]] = []
        self.current_activity: str = ""
        self.current_state_hash: str = ""
    
    def add_iteration(self, actions: List[GeneratedAction], action_selection_reason: str = "") -> None:
        """
        Add a new iteration with actions to the short-term memory.
        
        Args:
            actions: List of actions executed in this iteration
            action_selection_reason: Optional explanation for why these actions were selected
        """
        iteration = {
            "timestamp": time.time(),
            "actions": [self._convert_action_to_dict(action) for action in actions],
            "action_selection_reason": action_selection_reason
        }
        self.iterations.append(iteration)
    
    def _convert_action_to_dict(self, action: GeneratedAction) -> Dict[str, Any]:
        """
        Convert a GeneratedAction to a dictionary for storage.
        
        Args:
            action: The GeneratedAction to convert
            
        Returns:
            Dictionary representation of the action
        """
        return {
            "action_id": action.id,
            "action_type": action.action_type,
            "text": action.text,
            "coordinates": action.coordinates,
            "explanation": action.explanation,
            "params": action.params
        }
    
    def get_recent_iterations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most recent iterations from short-term memory.
        
        Args:
            limit: Maximum number of iterations to return
            
        Returns:
            List of recent iterations, newest first
        """
        return self.iterations[-limit:] if self.iterations else []
    
    def get_all_actions_since_activity_change(self) -> List[Dict[str, Any]]:
        """
        Get all actions recorded since entering the current activity.
        
        Returns:
            List of all actions from all iterations in the current activity
        """
        all_actions = []
        for iteration in self.iterations:
            all_actions.extend(iteration["actions"])
        return all_actions
    
    def clear(self) -> None:
        """Clear the short-term memory."""
        self.iterations = []


class LongTermMemory:
    """
    Long-term memory system that persists throughout a task execution.
    
    This memory tracks information across activity changes but is not
    persisted between different task executions. It stores activity
    visit history, action execution history, and aggregate statistics.
    
    Attributes:
        activity_visits: Dictionary mapping activity names to visit counts
        visited_activities: List of activities in visit order
        action_history: List of executed actions with context
        start_time: Timestamp when this memory was initialized
    """
    
    def __init__(self):
        """Initialize an empty long-term memory."""
        self.activity_visits: Dict[str, int] = {}
        self.visited_activities: List[str] = []
        self.action_history: List[Dict[str, Any]] = []
        self.start_time: float = time.time()
    
    def record_activity_visit(self, activity: str) -> None:
        """
        Record a visit to an activity.
        
        Args:
            activity: Name of the activity being visited
        """
        # Update visit count
        if activity in self.activity_visits:
            self.activity_visits[activity] += 1
        else:
            self.activity_visits[activity] = 1
        
        # Add to visited activities list
        self.visited_activities.append(activity)
    
    def record_actions(self, actions: List[Dict[str, Any]], activity: str) -> None:
        """
        Record actions executed in an activity.
        
        Args:
            actions: List of actions (as dictionaries) that were executed
            activity: Name of the activity where actions were executed
        """
        for action in actions:
            entry = {
                "timestamp": time.time(),
                "activity": activity,
                "action": action
            }
            self.action_history.append(entry)
    
    def get_activity_visit_count(self, activity: str) -> int:
        """
        Get the number of times an activity has been visited.
        
        Args:
            activity: Name of the activity
            
        Returns:
            Number of visits to the activity
        """
        return self.activity_visits.get(activity, 0)
    
    def get_visited_activities(self, limit: Optional[int] = None) -> List[str]:
        """
        Get the list of visited activities in chronological order.
        
        Args:
            limit: Optional limit on the number of activities to return
            
        Returns:
            List of visited activities
        """
        if limit:
            return self.visited_activities[-limit:]
        return self.visited_activities
    
    def get_activity_statistics(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all visited activities.
        
        Returns:
            List of dictionaries with activity name and visit count
        """
        return [
            {"name": activity, "visits": count}
            for activity, count in self.activity_visits.items()
        ]
    
    def get_recent_actions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent actions from long-term memory.
        
        Args:
            limit: Maximum number of actions to return
            
        Returns:
            List of recent actions with context, newest first
        """
        return self.action_history[-limit:] if self.action_history else []
    
    def get_navigation_path(self) -> List[str]:
        """
        Get the full navigation path (sequence of visited activities).
        
        Returns:
            List of activities in visitation order
        """
        return self.visited_activities


class MemoryManager:
    """
    Manages both short-term and long-term memory systems.
    
    The MemoryManager coordinates the memory systems, handling activity
    transitions, action recording, and state enrichment with historical
    context. It provides a unified interface for memory operations.
    
    ### Architectural Decisions:
    - Separates short-term (per-activity) and long-term (per-execution) memory
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
    
    def __init__(self):
        """Initialize the memory manager with empty memory systems."""
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.error_handler = ErrorHandler.get_instance()
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.service.memory_manager",
            {CONTEXT_COMPONENT: "MemoryManager"}
        )
    
    def update(self, state: Dict[str, Any]) -> None:
        """
        Update memory systems based on current state.
        
        This method checks for activity transitions and updates memory accordingly.
        If the activity has changed, short-term memory is cleared and the new
        activity is recorded in long-term memory.
        
        Args:
            state: Current application state
        """
        try:
            # Extract activity and state hash
            activity = self._get_activity_from_state(state)
            state_hash = self._compute_state_hash(state)
            
            # Check for activity change
            if activity != self.short_term.current_activity:
                self.logger.info(f"Activity changed from '{self.short_term.current_activity}' to '{activity}'")
                
                # Clear short-term memory on activity change
                self.short_term.clear()
                self.short_term.current_activity = activity
                
                # Record activity visit in long-term memory
                self.long_term.record_activity_visit(activity)
            
            # Update current state hash
            self.short_term.current_state_hash = state_hash
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
            
            activity = self._get_activity_from_state(state)
            
            # Record in short-term memory as a new iteration
            self.short_term.add_iteration(actions, action_selection_reason)
            
            # Convert actions to dictionaries for long-term storage
            action_dicts = [self.short_term._convert_action_to_dict(action) for action in actions]
            
            # Record in long-term memory
            self.long_term.record_actions(action_dicts, activity)
            
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
    
    def get_recent_activity_actions(self) -> List[Dict[str, Any]]:
        """
        Get actions from the current activity for transition tracking.
        
        This method retrieves all actions executed in the current activity,
        which can be used to determine which actions caused a transition.
        
        Returns:
            List of action dictionaries from the current activity
        """
        try:
            return self.short_term.get_all_actions_since_activity_change()
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
            state[StateEntry.RECENT_ITERATIONS] = self.short_term.get_recent_iterations(short_term_limit)
            
            # Add long-term memory insights
            activity = self._get_activity_from_state(state)
            visit_count = self.long_term.get_activity_visit_count(activity)
            
            # Add activity visit information
            state[StateEntry.ACTIVITY_VISITS] = {
                "current_activity": activity,
                "visit_count": visit_count,
                "activity_statistics": self.long_term.get_activity_statistics()
            }
            
            # Add navigation history
            state[StateEntry.NAVIGATION_PATH] = self.long_term.get_navigation_path()
        except Exception as e:
            self.error_handler.handle_error(
                e, 
                context={
                    "component": "MemoryManager", 
                    "method": "enrich_state_with_history"
                }
            )
            return state  # Return original state if enrichment fails
    
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
            # Use a stable JSON serialization for hashing
            stable_dict = self._create_stable_dict_for_hashing(state)
            state_json = json.dumps(stable_dict, sort_keys=True)
            return hashlib.md5(state_json.encode()).hexdigest()
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