"""
Transition Manager Module

This module provides the TransitionManager class, which is responsible for tracking transitions
between activities in Android applications. It maintains a dynamic transition graph that
combines static analysis data with runtime observations to track navigation patterns.

The manager is responsible for:
1. Tracking transitions between activities using both static and dynamic data
2. Maintaining a dynamic transition graph (DynamicTransitionGraph)
3. Providing transition guidance in a standardized data format
4. Handling the mapping between static window IDs and dynamic activity names

Author: Claude
Date: 2025-05-04
"""

from typing import Dict, List, Any, Optional, Set, Tuple
import time
import copy

from rvandroid.domain.dynamic_wtg import DynamicTransitionGraph
from rvandroid.domain.window import Window
from rvandroid.domain.wtg import WindowTransitionGraph
from rvandroid.llm.constants import StateEntry
from rvandroid.llm.data_structures import Action
from rvandroid.util.error.error_handler import error_handler
from rvandroid.util.logging.manager import get_logger


class TransitionManager:
    """
    Manager for tracking and analyzing transitions between activities.
    
    The TransitionManager tracks transitions between activities, integrates static Window
    Transition Graph (WTG) data with runtime observations, and provides guidance for
    navigating the application effectively.
    
    Attributes:
        dynamic_wtg: Dynamic transition graph tracking runtime transitions
        static_wtg: Static window transition graph from analysis (if available)
        current_activity: Name of the current activity
        previous_activity: Name of the previous activity 
        current_actions: Actions chosen in the current state
        previous_state_hash: Hash of the previous state for detecting changes
        current_state_hash: Hash of the current state for detecting changes
        activity_visits: Dictionary mapping activity names to visit counts
        logger: Logger instance for this class
    """
    
    def __init__(self, static_data: Optional[Any] = None):
        """
        Initialize the transition manager.
        
        Args:
            static_data: Optional static analysis data containing the WTG
        """
        self.dynamic_wtg = DynamicTransitionGraph()
        self.static_wtg: Optional[WindowTransitionGraph] = None
        
        # Initialize tracking variables
        self.current_activity: str = ""
        self.previous_activity: str = ""
        self.current_actions: List[Action] = []
        self.previous_state_hash: str = ""
        self.current_state_hash: str = ""
        self.activity_visits: Dict[str, int] = {}
        self.visited_activities: List[str] = []
        
        # Set up logger
        self.logger = get_logger(self.__class__.__name__)
        
        # Extract static WTG if available
        if static_data and hasattr(static_data, 'wtg'):
            self.static_wtg = static_data.wtg
    
    @error_handler.catch_and_log_errors
    def update(self, state: Dict[str, Any]) -> bool:
        """
        Update the transition manager with the current state.
        
        This method processes the new state, detects activity changes,
        and records transitions when appropriate.
        
        Args:
            state: Current application state
            
        Returns:
            True if a transition was detected, False otherwise
        """
        # Extract current activity and state hash
        activity = self._get_activity_from_state(state)
        state_hash = self._get_state_hash(state)
        
        # Save previous state information
        previous_activity = self.current_activity
        
        # Update current state information
        self.previous_activity = previous_activity
        self.current_activity = activity
        self.previous_state_hash = self.current_state_hash
        self.current_state_hash = state_hash
        
        # Check for activity change
        transition_detected = False
        if activity != previous_activity and previous_activity:
            self.logger.info(f"Transition detected: {previous_activity} -> {activity}")
            
            # Record transition 
            if self.current_actions:
                # Find the action that might have caused the transition
                for action in self.current_actions:
                    self.record_transition(previous_activity, activity, str(action.action_id), action.action_type)
            else:
                # If no actions recorded, use unknown action
                self.record_transition(previous_activity, activity, "unknown", "unknown")
            
            transition_detected = True
        
        # Update activity visit count
        self._update_activity_visit(activity)
        
        return transition_detected
    
    @error_handler.catch_and_log_errors
    def update_with_actions(self, state: Dict[str, Any], actions: List[Action]) -> None:
        """
        Update the transition manager with selected actions.
        
        This method stores the actions chosen in the current state for later
        transition detection when the state changes.
        
        Args:
            state: Current application state
            actions: Actions selected for execution
        """
        if not actions:
            return
        
        # Store actions for potential transition detection
        self.current_actions = actions.copy()
        
        # Record actions in dynamic WTG
        activity = self._get_activity_from_state(state)
        for action in actions:
            self.dynamic_wtg.add_action_from_window(activity, action.action_id)
    
    @error_handler.catch_and_log_errors
    def record_transition(self, from_activity: str, to_activity: str, 
                         action_id: str, action_type: str) -> None:
        """
        Record a transition in the dynamic transition graph.
        
        Args:
            from_activity: Source activity name
            to_activity: Target activity name
            action_id: ID of the action that caused the transition
            action_type: Type of the action that caused the transition
        """
        if not from_activity or not to_activity:
            return
        
        # Normalize activity names
        from_activity = self._normalize_activity_name(from_activity)
        to_activity = self._normalize_activity_name(to_activity)
        
        # Record in dynamic WTG
        try:
            self.dynamic_wtg.add_edge(from_activity, to_activity, action_id)
            self.logger.debug(f"Recorded transition: {from_activity} -> {to_activity} via action {action_id}")
        except Exception as e:
            self.logger.error(f"Error recording transition: {e}")
    
    @error_handler.catch_and_log_errors
    def get_transition_guidance(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get transition guidance information for the current state.
        
        This method creates a comprehensive dictionary containing information about
        static and dynamic transitions, visit counts, unexplored actions, and
        suggested targets for exploration.
        
        Args:
            state: Current application state
            
        Returns:
            Dictionary containing transition guidance information
        """
        activity = self._get_activity_from_state(state)
        
        # Initialize guidance dictionary
        guidance = {
            "current_activity": activity,
            "visit_count": self.activity_visits.get(activity, 0),
            "navigation_path": self.visited_activities.copy(),
            "visited_activities": [],
            "unexplored_actions": [],
            "static_transitions": [],
            "dynamic_transitions": [],
            "suggested_targets": []
        }
        
        # Add visited activities information
        for act, count in self.activity_visits.items():
            guidance["visited_activities"].append({
                "name": act,
                "visits": count
            })
        
        # Sort by visit count (descending)
        guidance["visited_activities"].sort(key=lambda x: x["visits"], reverse=True)
        
        # Add static transitions if available
        self._add_static_transitions(guidance, activity)
        
        # Add dynamic transitions
        self._add_dynamic_transitions(guidance, activity)
        
        # Add unexplored actions
        self._add_unexplored_actions(guidance, activity, state)
        
        # Add suggested targets for exploration
        self._add_suggested_targets(guidance, activity)
        
        return guidance
    
    def get_dtg(self) -> DynamicTransitionGraph:
        """
        Get the dynamic transition graph.
        
        Returns:
            The dynamic transition graph instance
        """
        return self.dynamic_wtg
    
    def _normalize_activity_name(self, activity: str) -> str:
        """
        Normalize activity name for consistent tracking.
        
        This removes common suffixes and ensures consistent formatting.
        
        Args:
            activity: Original activity name
            
        Returns:
            Normalized activity name
        """
        if not activity:
            return "unknown"
        
        # Remove common suffixes
        suffixes = ["Activity", "Fragment"]
        normalized = activity
        for suffix in suffixes:
            if normalized.endswith(suffix) and len(normalized) > len(suffix):
                normalized = normalized[:-len(suffix)]
        
        return normalized
    
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
    
    def _get_state_hash(self, state: Dict[str, Any]) -> str:
        """
        Get a hash for the state to detect state changes.
        
        Args:
            state: Current application state
            
        Returns:
            Hash string or state ID
        """
        # Try to use an existing state ID if available
        if isinstance(state, dict):
            if "state_id" in state:
                return state["state_id"]
        
        # Fallback to timestamp as a simple hash
        return str(time.time())
    
    def _update_activity_visit(self, activity: str) -> None:
        """
        Update the visit count for an activity.
        
        Args:
            activity: Name of the activity being visited
        """
        if not activity:
            return
        
        # Update visit count
        if activity in self.activity_visits:
            self.activity_visits[activity] += 1
        else:
            self.activity_visits[activity] = 1
            
        # Add to visited activities list
        self.visited_activities.append(activity)
    
    def _add_static_transitions(self, guidance: Dict[str, Any], activity: str) -> None:
        """
        Add static transition information to the guidance dictionary.
        
        Args:
            guidance: Guidance dictionary to update
            activity: Current activity name
        """
        if not self.static_wtg:
            return
        
        # Try to find corresponding window in static WTG
        static_window = self._find_static_window(activity)
        if not static_window:
            return
        
        # Get outgoing transitions from static WTG
        static_transitions = []
        for edge in self.static_wtg.get_outgoing_edges(static_window):
            target_window = edge.target
            target_activity = target_window.name if target_window else "unknown"
            
            # Check if this transition has been observed in dynamic WTG
            visited = self.dynamic_wtg.has_edge(activity, target_activity)
            
            for action in edge.actions:
                static_transitions.append({
                    "target": target_activity,
                    "action_id": str(action.id) if hasattr(action, 'id') else "unknown",
                    "visited": visited
                })
        
        guidance["static_transitions"] = static_transitions
    
    def _add_dynamic_transitions(self, guidance: Dict[str, Any], activity: str) -> None:
        """
        Add dynamic transition information to the guidance dictionary.
        
        Args:
            guidance: Guidance dictionary to update
            activity: Current activity name
        """
        dynamic_transitions = []
        
        # Get outgoing edges from dynamic WTG
        for target, edges in self.dynamic_wtg.get_outgoing_edges(activity).items():
            for action_id, count in edges.items():
                dynamic_transitions.append({
                    "target": target,
                    "action_id": str(action_id),
                    "count": count
                })
        
        guidance["dynamic_transitions"] = dynamic_transitions
    
    def _add_unexplored_actions(self, guidance: Dict[str, Any], 
                               activity: str, state: Dict[str, Any]) -> None:
        """
        Add information about unexplored actions to the guidance dictionary.
        
        Args:
            guidance: Guidance dictionary to update
            activity: Current activity name
            state: Current application state
        """
        # Get all available actions
        available_actions: Set[str] = set()
        
        # Try to extract actions from state
        if StateEntry.AVAILABLE_ACTIONS in state and isinstance(state[StateEntry.AVAILABLE_ACTIONS], list):
            for action in state[StateEntry.AVAILABLE_ACTIONS]:
                if isinstance(action, dict) and "action_id" in action:
                    available_actions.add(str(action["action_id"]))
        
        # Get actions that have been used in transitions
        used_actions: Set[str] = set()
        for target, edges in self.dynamic_wtg.get_outgoing_edges(activity).items():
            for action_id in edges.keys():
                used_actions.add(str(action_id))
        
        # Find unexplored actions
        unexplored = available_actions - used_actions
        guidance["unexplored_actions"] = sorted(list(unexplored))
    
    def _add_suggested_targets(self, guidance: Dict[str, Any], activity: str) -> None:
        """
        Add suggested exploration targets to the guidance dictionary.
        
        Args:
            guidance: Guidance dictionary to update
            activity: Current activity name
        """
        # Start with activities mentioned in static transitions but not visited yet
        static_but_unvisited = []
        
        # Extract from static transitions
        for transition in guidance["static_transitions"]:
            target = transition["target"]
            action_id = transition["action_id"]
            
            # If target not visited or rarely visited
            visits = self.activity_visits.get(target, 0)
            if visits == 0 or visits < 2:  # Prioritize unvisited or rarely visited
                # Check if it's already in the list
                found = False
                for item in static_but_unvisited:
                    if item["name"] == target:
                        if action_id not in item["action_ids"]:
                            item["action_ids"].append(action_id)
                        found = True
                        break
                
                if not found:
                    static_but_unvisited.append({
                        "name": target,
                        "visits": visits,
                        "action_ids": [action_id]
                    })
        
        # Sort by visit count (ascending) to prioritize least visited
        static_but_unvisited.sort(key=lambda x: x["visits"])
        
        guidance["suggested_targets"] = static_but_unvisited
    
    def _find_static_window(self, activity_name: str) -> Optional[Window]:
        """
        Find the static window corresponding to an activity name.
        
        Args:
            activity_name: Name of the activity
            
        Returns:
            Matching Window object or None if not found
        """
        if not self.static_wtg:
            return None
        
        # Try exact match first
        for window in self.static_wtg.get_windows():
            if window.name == activity_name:
                return window
        
        # Try matching by substring
        normalized = self._normalize_activity_name(activity_name)
        for window in self.static_wtg.get_windows():
            if normalized in window.name or window.name in normalized:
                return window
        
        # Try matching by package name and activity name parts
        parts = activity_name.split('.')
        if len(parts) > 1:
            activity_class = parts[-1]
            for window in self.static_wtg.get_windows():
                if activity_class in window.name:
                    return window
        
        return None