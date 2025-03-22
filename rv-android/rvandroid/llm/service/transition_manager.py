# rvandroid/llm/service/transition_manager.py
from typing import Dict, List, Any

from rvandroid.experiment.event_system import EventBus
from rvandroid.model.dynamic_wtg import DynamicTransitionGraph
from rvandroid.util.logging_manager import LoggingManager
from rvandroid.util.performance_monitor import PerformanceMonitor


class TransitionManager:
    """
    Manages application state transitions and provides navigation guidance.

    ### Architectural Decisions:
    - Encapsulates dynamic transition graph management as a distinct responsibility
    - Tracks state transitions to build a comprehensive navigation model
    - Provides transition history and exploration recommendations
    - Implements performance monitoring for transition operations

    ### Role in the System:
    - Builds and maintains a dynamic model of application navigation
    - Provides guidance for effective UI exploration
    - Tracks visited activities and tested elements
    - Supports intelligent test navigation decisions
    """

    def __init__(self, dynamic_wtg_file: str = "dynamic_wtg.json"):
        """
        Initialize the transition manager.

        Args:
            dynamic_wtg_file: File to store/load dynamic transition graph
        """
        # Get system services
        self.event_bus = EventBus.get_instance()
        self.performance_monitor = PerformanceMonitor.get_instance()
        logging_manager = LoggingManager.get_instance()

        # Configure logging
        self.logger = logging_manager.get_logger(
            "llm.service.transition_manager",
            {LoggingManager.CONTEXT_COMPONENT: "TransitionManager"}
        )

        # Initialize dynamic transition graph or load from file
        self.dynamic_wtg_file = dynamic_wtg_file
        saved_graph = DynamicTransitionGraph.load_from_file(dynamic_wtg_file)
        self.dynamic_wtg = saved_graph if saved_graph else DynamicTransitionGraph()

        self.logger.info(f"Transition manager initialized with graph file: {dynamic_wtg_file}")

    def update_transitions(self, state: Dict[str, Any], executed_action: Dict[str, Any] = None) -> None:
        """
        Update dynamic transition graph with information about the current state.

        Args:
            state: Current application state
            executed_action: The action that was executed to reach this state (if known)
        """
        try:
            # Get current activity
            current_activity = state.get("activity", "unknown")

            # Record visit to this activity
            self.dynamic_wtg.record_visit(current_activity)

            # If we have an executed action and we're tracking transitions
            if executed_action and 'previous_activity' in state:
                previous_activity = state['previous_activity']
                action_id = executed_action.get('action_id', 'unknown')
                action_type = executed_action.get('action_type', 'unknown')

                # Record transition
                self.dynamic_wtg.record_transition(
                    previous_activity,
                    current_activity,
                    action_id,
                    action_type
                )

                self.logger.info(
                    f"Recorded transition: {previous_activity} -> {current_activity} via action {action_id}"
                )

        except Exception as e:
            self.logger.error(f"Error updating dynamic transitions: {e}", exc_info=True)

    def update_with_actions(self, state: Dict[str, Any], actions: List[Dict[str, Any]]) -> None:
        """
        Update the dynamic transition graph with information about chosen actions.

        Args:
            state: Current application state
            actions: List of selected actions
        """
        try:
            activity = state.get("activity", "unknown")

            for action in actions:
                action_id = action.get("action_id", None)
                if action_id:
                    # Record that this action was chosen for this activity
                    self.dynamic_wtg.record_action(activity, action_id)

        except Exception as e:
            self.logger.error(f"Error updating graph with actions: {e}", exc_info=True)

    def get_transition_guidance(self, activity: str) -> Dict[str, Any]:
        """
        Get guidance information based on dynamic transitions for the current activity.

        Args:
            activity: Current activity name

        Returns:
            Dictionary with transition guidance information
        """
        guidance = {
            "current_activity": activity,
            "visit_count": 0,
            "suggested_targets": [],
            "unexplored_elements": [],
            "visited_activities": [],
            "least_visited_activities": []
        }

        try:
            # Normalize activity name by removing the '/' character if present
            normalized_activity = activity.replace("/", ".")
            if normalized_activity.endswith(".."):
                normalized_activity = normalized_activity[:-1]

            # Get activity node
            activity_node = self.dynamic_wtg.activities.get(normalized_activity)
            if activity_node:
                guidance["visit_count"] = activity_node.visit_count
                guidance["unexplored_elements"] = list(activity_node.ui_elements_tested)

            # Get visited activities
            guidance["visited_activities"] = [
                {"name": name, "visits": node.visit_count}
                for name, node in self.dynamic_wtg.activities.items()
            ]

            # Get suggested target activities - use normalized activity name for lookup
            if normalized_activity in self.dynamic_wtg.graph:
                neighbors = list(self.dynamic_wtg.graph.neighbors(normalized_activity))
                least_visited = []

                if neighbors:
                    # Sort neighbors by visit count
                    neighbor_visits = [
                        {"name": n, "visits": self.dynamic_wtg.activities[n].visit_count}
                        for n in neighbors
                    ]
                    neighbor_visits.sort(key=lambda x: x["visits"])
                    guidance["suggested_targets"] = neighbor_visits[:3]
            else:
                # If the activity is not in the graph yet, add it
                self.dynamic_wtg.add_activity(normalized_activity)
                guidance["suggested_targets"] = []

            # Get overall least visited activities
            least_visited_tuples = self.dynamic_wtg.get_least_visited_activities(5)
            guidance["least_visited_activities"] = [
                {"name": name, "visits": count} for name, count in least_visited_tuples
            ]

        except Exception as e:
            self.logger.error(f"Error getting transition guidance: {e}", exc_info=True)

        return guidance

    def save(self) -> bool:
        """
        Save the dynamic transition graph to file.

        Returns:
            True if successful, False otherwise
        """
        return self.dynamic_wtg.save_to_file(self.dynamic_wtg_file)
