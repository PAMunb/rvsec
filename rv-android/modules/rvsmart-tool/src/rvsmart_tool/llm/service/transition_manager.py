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
"""

import time
from typing import Dict, List, Any, Optional, Set

from rv_android_core.domain.dynamic_wtg import DynamicTransitionGraph
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_android_core.domain.window import Window
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_llm.llm.constants import StateEntry
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


class TransitionManager:
    """
    Manager for tracking and analyzing transitions between activities.
    
    The TransitionManager tracks transitions between activities, integrates static Window
    Transition Graph (WTG) data with runtime observations, and provides guidance for
    navigating the application effectively.
    
    ### Architectural Decisions:
    - Focuses solely on transition tracking and analysis without duplicating action storage
    - Maintains a dynamic transition graph that builds over time from observed transitions
    - Integrates static analysis when available for better exploration recommendations
    - Maps between static and dynamic activity names for consistent identification
    - Does not store actions directly (actions are stored in MemoryManager)
    
    ### Role in the System:
    - Detects and records transitions between activities
    - Maintains statistics about activity visits and transitions
    - Provides guidance for effective application exploration
    - Integrates with TransitionGuidanceFragment for LLM prompt generation
    - Coordinates with MemoryManager for action retrieval when transitions occur
    
    Attributes:
        dynamic_wtg: Dynamic transition graph tracking runtime transitions
        static_wtg: Static window transition graph from analysis (if available)
        current_activity: Name of the current activity
        previous_activity: Name of the previous activity 
        current_state_hash: Hash of the current state for change detection
        previous_state_hash: Hash of the previous state for change detection
        activity_visits: Dictionary mapping activity names to visit counts
        visited_activities: List of activities in visit order
        logger: Logger instance for this class
        error_handler: Error handler for managing exceptions
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """
        Initialize the transition manager.
        
        Args:
            static_data: Optional static analysis data containing the WTG
        """
        self.static_data = static_data
        self.dynamic_wtg = DynamicTransitionGraph()
        self.static_wtg: Optional[WindowTransitionGraph] = None

        # Initialize tracking variables
        self.current_activity: str = ""
        self.previous_activity: str = ""
        self.current_state_hash: str = ""
        self.previous_state_hash: str = ""
        self.activity_visits: Dict[str, int] = {}
        self.visited_activities: List[str] = []

        # Set up logger and error handler
        self.error_handler = ErrorHandler.get_instance()
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvsmart_tool.llm.service.transition_manager",
            {CONTEXT_COMPONENT: "TransitionManager"}
        )

        # Extract static WTG if available
        if static_data and hasattr(static_data, 'wtg'):
            self.static_wtg = static_data.wtg
            self.logger.info("Static WTG loaded from analysis data")

    def update(self, state: Dict[str, Any]) -> bool:
        """
        Update the transition manager with the current state.
        
        This method processes the new state, detects activity changes,
        and records visit statistics. Note that it does NOT record transitions
        directly - transition recording happens separately when actions 
        are provided via record_transition.
        
        Args:
            state: Current application state
            
        Returns:
            True if a transition was detected, False otherwise
        """
        try:
            # Extract current activity and state hash
            activity = self._get_activity_from_state(state)
            state_hash = self._get_state_hash(state)

            # Save previous state information
            previous_activity = self.current_activity

            # Detect transition
            transition_detected = False
            if activity != previous_activity and previous_activity:
                self.logger.info(f"Transition detected: {previous_activity} -> {activity}")
                transition_detected = True

            # Update current state information
            self.previous_activity = previous_activity
            self.current_activity = activity
            self.previous_state_hash = self.current_state_hash
            self.current_state_hash = state_hash

            # Update activity visit count
            self._update_activity_visit(activity)

            return transition_detected
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TransitionManager",
                    "method": "update",
                    "state": str(state)[:100]
                }
            )
            return False

    def record_transition(self, from_activity: str, to_activity: str, actions: List[Dict[str, Any]]) -> None:
        """
        Record a transition in the dynamic transition graph.
        
        This method takes actions from MemoryManager and records them as causing
        a transition between activities in the dynamic transition graph.
        
        Args:
            from_activity: Source activity name
            to_activity: Destination activity name
            actions: List of actions that led to this transition
        """
        print(f"*** Recording transition: {from_activity} -> {to_activity}")
        try:
            if not from_activity or not to_activity or from_activity == to_activity:
                return

            # Normalize activity names
            from_activity = self._normalize_activity_name(from_activity)
            to_activity = self._normalize_activity_name(to_activity)

            # Convert actions to dictionary format if they're GeneratedAction objects
            actions_dict = []
            for action in actions:
                if hasattr(action, 'to_dict'):
                    actions_dict.append(action.to_dict())
                else:
                    # Assume it's already a dictionary
                    actions_dict.append(action)

            # Record in dynamic WTG
            self.dynamic_wtg.record_transition(from_activity, to_activity, actions_dict)

            # Update current state information
            self.previous_activity = from_activity
            self.current_activity = to_activity

            self.logger.debug(
                f"Recorded transition: {from_activity} -> {to_activity} with {len(actions)} actions"
            )
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TransitionManager",
                    "method": "record_transition",
                    "from_activity": from_activity,
                    "to_activity": to_activity,
                    "actions_count": len(actions) if actions else 0
                }
            )

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
        try:
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
            self._add_static_transitions(guidance, activity, state)

            # Add dynamic transitions
            self._add_dynamic_transitions(guidance, activity)

            # Add unexplored actions
            self._add_unexplored_actions(guidance, activity, state)

            # Add suggested targets for exploration
            # self._add_suggested_targets(guidance, activity)

            self.logger.info(f"Transition guidance: {guidance}")

            return guidance
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TransitionManager",
                    "method": "get_transition_guidance",
                    "activity": self._get_activity_from_state(state)
                }
            )
            # Return minimal guidance in case of error
            return {
                "current_activity": self._get_activity_from_state(state),
                "visit_count": 0,
                "navigation_path": [],
                "visited_activities": [],
                "unexplored_actions": [],
                "static_transitions": [],
                "dynamic_transitions": [],
                "suggested_targets": []
            }

    def get_dtg(self) -> DynamicTransitionGraph:
        """
        Get the dynamic transition graph.
        
        Returns:
            The dynamic transition graph instance
        """
        return self.dynamic_wtg

    # TODO deprecated
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
        # suffixes = ["Activity", "Fragment"]
        # normalized = activity
        # for suffix in suffixes:
        #     if normalized.endswith(suffix) and len(normalized) > len(suffix):
        #         normalized = normalized[:-len(suffix)]

        return activity

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
            if "hash" in state:
                return state["hash"]
            if "hash_code" in state:
                return state["hash_code"]

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

        # Record in dynamic WTG
        self.dynamic_wtg.record_visit(activity)

    def _add_static_transitions(self, guidance: Dict[str, Any], activity: str, state: Dict[str, Any]) -> None:
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

        # Get window transitions for this window
        window_transitions = self.static_wtg.get_window_transitions(static_window.id)

        for transition in window_transitions:
            source_id = transition.get("source", "")
            target_id = transition.get("target", "")

            # if source_id == static_window.id:
            #     continue

            target_window = None

            # Find the target window
            static_window = self.static_data.windows.get_window_by_id(target_id)
            if static_window:
                target_window = static_window.activity
            else:
                continue
            # for window in self.static_wtg.window_ids:
            #     if window == target_id:
            #         target_window = window
            #         break

            # if target_window:
            # Check if this transition has been observed in dynamic WTG
            visited = self.dynamic_wtg.graph.has_edge(activity, target_window)

            # Get widget info
            # widget_id = transition.get("widget_id", "unknown")
            #
            screen_description = state[StateEntry.STRUCTURED_SCREEN]

            item_action = self.get_item_action(transition, screen_description)

            # Skip transitions where item_action is not found
            if item_action is None:
                continue

            static_transitions.append({
                "target": target_window,
                "action_id": item_action.id,
                "action_text": item_action.text,
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

        # Check if the activity exists in the graph
        if activity not in self.dynamic_wtg.graph:
            guidance["dynamic_transitions"] = dynamic_transitions
            return

        # Get outgoing edges from dynamic WTG for this activity
        successor_nodes = list(self.dynamic_wtg.graph.successors(activity))

        for target_activity in successor_nodes:
            if self.dynamic_wtg.graph.has_edge(activity, target_activity):
                edge_data = self.dynamic_wtg.graph[activity][target_activity]
                transitions = edge_data.get("transitions", [])

                for transition in transitions:
                    # Extract action information from transition
                    for action in transition.actions:
                        action_id = action.get("action_id", "unknown")

                        dynamic_transitions.append({
                            "target": target_activity,
                            "action_id": str(action_id),
                            "count": transition.count
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

        # Check if activity exists in the graph
        if activity in self.dynamic_wtg.graph:
            # Get actions used from the activity in dynamic transitions
            successor_nodes = list(self.dynamic_wtg.graph.successors(activity))

            for target_activity in successor_nodes:
                if self.dynamic_wtg.graph.has_edge(activity, target_activity):
                    edge_data = self.dynamic_wtg.graph[activity][target_activity]
                    transitions = edge_data.get("transitions", [])

                    for transition in transitions:
                        for action in transition.actions:
                            action_id = action.get("action_id", "unknown")
                            used_actions.add(str(action_id))

        # Find unexplored actions
        unexplored = available_actions - used_actions
        guidance["unexplored_actions"] = sorted(list(unexplored))

    # def _add_suggested_targets(self, guidance: Dict[str, Any], activity: str) -> None:
    #     """
    #     Add suggested exploration targets to the guidance dictionary.
    #
    #     Args:
    #         guidance: Guidance dictionary to update
    #         activity: Current activity name
    #     """
    #     # Start with activities mentioned in static transitions but not visited yet
    #     static_but_unvisited = []
    #
    #     # Extract from static transitions
    #     for transition in guidance["static_transitions"]:
    #         target = transition["target"]
    #         action_id = transition["action_id"]
    #
    #         # If target not visited or rarely visited
    #         visits = self.activity_visits.get(target, 0)
    #         if visits == 0 or visits < 2:  # Prioritize unvisited or rarely visited
    #             # Check if it's already in the list
    #             found = False
    #             for item in static_but_unvisited:
    #                 if item["name"] == target:
    #                     if action_id not in item["action_ids"]:
    #                         item["action_ids"].append(action_id)
    #                     found = True
    #                     break
    #
    #             if not found:
    #                 static_but_unvisited.append({
    #                     "name": target,
    #                     "visits": visits,
    #                     "action_ids": [action_id]
    #                 })
    #
    #     # Also include suggestions from dynamic WTG
    #     least_visited = self.dynamic_wtg.get_least_visited_activities(5)
    #     for activity_name, visit_count in least_visited:
    #         # Check if this activity is reachable from current
    #         paths = self.dynamic_wtg.graph.get_paths_between(activity, activity_name)
    #         if paths:
    #             # Find actions that lead there
    #             action_ids = []
    #
    #             # Only consider if not already in the list
    #             found = False
    #             for item in static_but_unvisited:
    #                 if item["name"] == activity_name:
    #                     found = True
    #                     break
    #
    #             if not found:
    #                 static_but_unvisited.append({
    #                     "name": activity_name,
    #                     "visits": visit_count,
    #                     "action_ids": action_ids
    #                 })
    #
    #     # Sort by visit count (ascending) to prioritize least visited
    #     static_but_unvisited.sort(key=lambda x: x["visits"])
    #
    #     guidance["suggested_targets"] = static_but_unvisited

    def _find_static_window(self, activity_name: str) -> Optional[Window]:
        """
        Find the static window corresponding to an activity name.
        
        Args:
            activity_name: Name of the activity
            
        Returns:
            Matching Window object or None if not found
        """
        if not self.static_data:
            return None

        # Get all windows
        windows = list(self.static_data.windows.get_windows())

        # Try exact match first
        for window in windows:
            if window.name == activity_name:
                return window

        # Try matching by substring
        normalized = self._normalize_activity_name(activity_name)
        for window in windows:
            if normalized in window.name or window.name in normalized:
                return window

        # Try matching by package name and activity name parts
        parts = activity_name.split('.')
        if len(parts) > 1:
            activity_class = parts[-1]
            for window in windows:
                if activity_class in window.name:
                    return window

        return None

    def get_item_action(self, transition, screen_description: ScreenDescription):
        # Get widget info
        widget_id = transition.get("widget_id", "unknown")
        for event in screen_description.events_by_id.values():
            if event.widget_id == widget_id: # Check if event has WidgetEventType and event.event == WidgetEventType.
                return event
        return None

