# rvandroid/llm/service/transition_manager.py
"""
Transition manager for tracking application state transitions.

This module provides functionality to track and analyze transitions between different
application states, identify navigation patterns, and provide guidance for testing.
"""
from typing import Dict, List, Any

from rv_android_core.domain.dynamic_wtg import DynamicTransitionGraph
from rv_android_core.domain.static import StaticAnalysisData
from rvandroid.llm.constants import StateEntry
from rvandroid.llm.service.action_generator import GeneratedAction
from rvandroid.parser.screen.visitor.model import ScreenDescription
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class TransitionManager:
    """
    Manages application state transitions and provides navigation guidance.

    ### Architectural Decisions:
    - Uses DynamicTransitionGraph for tracking application navigation structure
    - Records state transitions to build a comprehensive exploration model
    - Integrates with MemoryManager for consistent state tracking
    - Provides formatted transition data for template inclusion

    ### Role in the System:
    - Tracks application navigation structure during testing
    - Identifies unexplored paths and activities
    - Provides guidance for efficient exploration coverage
    - Supports memory systems with navigation data
    """

    def __init__(self):
        """Initialize the transition manager."""
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.service.transition_manager",
            {CONTEXT_COMPONENT: "TransitionManager"}
        )

        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()

        # Initialize dynamic transition graph
        self.dynamic_wtg = DynamicTransitionGraph()

        # Track the current activity
        self.current_activity = None
        self.last_activity = None

        self.logger.info("Transition manager initialized")

    def update(self, state: Dict[str, Any]) -> None:
        """
        Update dynamic transition graph with information about the current state.

        Args:
            state: Current application state
        """
        try:
            # Get current activity
            current_activity = state.get(StateEntry.ACTIVITY, "unknown")
            screen_description: ScreenDescription = state.get(StateEntry.STRUCTURED_SCREEN)

            # Normalize activity name
            current_activity = current_activity.replace("/", ".")
            if current_activity.endswith(".."):
                current_activity = current_activity[:-1]

            # Record visit to this activity
            self.dynamic_wtg.record_visit(current_activity)

            # Update current activity
            self.last_activity = self.current_activity
            self.current_activity = current_activity

            self.logger.debug(f"Recorded visit to activity: {current_activity}")

        except Exception as e:
            self.logger.error(f"Error updating transitions: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TransitionManager",
                    "function": "update_transitions"
                }
            )

    def update_with_actions(self, state: Dict[str, Any], actions: List[GeneratedAction]) -> None:
        """
        Update the dynamic transition graph with information about chosen actions.

        Args:
            state: Current application state
            actions: List of selected actions
        """
        if self.last_activity != self.current_activity:
            # TODO: Handle activity change
            try:
                # Get current activity
                activity = state.get(StateEntry.ACTIVITY, "unknown")

                for action in actions:
                    # Record that this action was chosen for this activity
                    self.dynamic_wtg.record_action(activity, str(action.id))
                    self.logger.debug(f"Recorded action {action.id} for activity {activity}")

            except Exception as e:
                self.logger.error(f"Error updating graph with actions: {e}")
                self.error_handler.handle_error(
                    e,
                    context={
                        "component": "TransitionManager",
                        "function": "update_with_actions"
                    }
                )

    # TODO
    def record_transition(self, from_state: Dict[str, Any], to_state: Dict[str, Any],
                          action_id: str, action_type: str) -> None:
        """
        Record a transition between states.

        Args:
            from_state: Source state
            to_state: Destination state
            action_id: ID of the action that caused the transition
            action_type: Type of the action that caused the transition
        """
        try:
            # Get activity names
            from_activity = from_state.get(StateEntry.ACTIVITY, "unknown")
            to_activity = to_state.get(StateEntry.ACTIVITY, "unknown")

            # Normalize activity names
            from_activity = from_activity.replace("/", ".")
            to_activity = to_activity.replace("/", ".")

            if from_activity.endswith(".."):
                from_activity = from_activity[:-1]
            if to_activity.endswith(".."):
                to_activity = to_activity[:-1]

            # Record transition in dynamic WTG
            self.dynamic_wtg.record_transition(
                from_activity,
                to_activity,
                str(action_id),
                action_type
            )

            self.logger.info(f"Recorded transition: {from_activity} -> {to_activity} via action {action_id}")

        except Exception as e:
            self.logger.error(f"Error recording transition: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TransitionManager",
                    "function": "record_transition"
                }
            )

    def get_transition_guidance(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get guidance information based on dynamic transitions for the current state.

        Args:
            state: Current application state

        Returns:
            Dictionary with transition guidance information
        """
        try:
            # Get current activity
            activity = state.get(StateEntry.ACTIVITY, "unknown")
            screen_description: ScreenDescription = state.get(StateEntry.STRUCTURED_SCREEN)
            static_data: StaticAnalysisData = state[StateEntry.STATIC_DATA]

            all_actions_ids: set[str] = set()
            for item in screen_description.items:
                for action in item.actions:
                    all_actions_ids.add(str(action.id))

            # Normalize activity name
            activity = activity.replace("/", ".")
            if activity.endswith(".."):
                activity = activity[:-1]

            # Create guidance dictionary
            guidance = {
                "current_activity": activity,
                "visit_count": 0,
                "explored_actions": [],
                "unexplored_actions": [],
                "visited_activities": [],
                "transistions": []  # transitions from this activity to others
            }

            # Check if the activity exists in the graph
            if activity in self.dynamic_wtg.activities:
                # Get activity node
                activity_node = self.dynamic_wtg.activities[activity]
                guidance["visit_count"] = activity_node.visit_count
                guidance["explored_actions"] = list(activity_node.ui_elements_tested)
                guidance["unexplored_actions"] = list(all_actions_ids - activity_node.ui_elements_tested)

            # Get visited activities
            guidance["visited_activities"] = [
                {"name": name, "visits": node.visit_count}
                for name, node in self.dynamic_wtg.activities.items()
            ]

            # Get suggested target activities
            vizinhos = []
            window = static_data.windows.get_window(activity)
            print(f"window={window.name} ({window.id})")
            if window:
                current_activity_id = window.id
                wtg = static_data.wtg

                edges = wtg.graph.edges(current_activity_id)
                print(f"edges={edges}")

                neighbors = list(wtg.graph.neighbors(current_activity_id))
                for neighbor in neighbors:
                    print(f"neighbor >>> {neighbor} ::: type={type(neighbor)}")
                    _id = neighbor
                    vizinho = static_data.windows.get_window_by_id(neighbor)
                    vizinhos.append(vizinho)
                print(f"vizinhos={vizinhos}")
                exit(1)


            if activity in static_data.wtg.graph:
                print(f"neighbor >>> {activity}")
                neighbors = list(self.dynamic_wtg.graph.neighbors(activity))
                neighbor_visits = []

                for neighbor in neighbors:
                    if neighbor in self.dynamic_wtg.activities:
                        node = self.dynamic_wtg.activities[neighbor]
                        neighbor_visits.append({
                            "name": neighbor,
                            "visits": node.visit_count
                        })

                # Sort by visit count (least visited first)
                neighbor_visits.sort(key=lambda x: x["visits"])
                guidance["suggested_targets"] = neighbor_visits[:3]  # Top 3 suggestions

            # Get least visited activities overall
            least_visited = []
            sorted_activities = sorted(
                [(name, node.visit_count) for name, node in self.dynamic_wtg.activities.items()],
                key=lambda x: x[1]  # Sort by visit count
            )

            for name, visits in sorted_activities[:5]:  # Top 5 least visited
                least_visited.append({
                    "name": name,
                    "visits": visits
                })

            guidance["least_visited_activities"] = least_visited

            # Add summary
            guidance["summary"] = self._format_guidance_summary(guidance)

            return guidance

        except Exception as e:
            self.logger.error(f"Error getting transition guidance: {e}")
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TransitionManager",
                    "function": "get_transition_guidance"
                }
            )
            return {
                "visit_count": 0,
                "suggested_targets": [],
                "explored_actions": [],
                "summary": "Navigation guidance information unavailable."
            }

    def _format_guidance_summary(self, guidance: Dict[str, Any]) -> str:
        """
        Format guidance information as a summary string for templates.

        Args:
            guidance: Guidance dictionary from get_transition_guidance

        Returns:
            Formatted summary string
        """
        summary_parts = []

        # Add current screen visit information
        visit_count = guidance.get("visit_count", 0)
        if visit_count == 0:
            summary_parts.append("This is your first visit to this screen.")
        elif visit_count == 1:
            summary_parts.append("You have visited this screen once before.")
        else:
            summary_parts.append(f"You have visited this screen {visit_count} times.")

        # # Add unexplored elements information
        # unexplored_count = len(guidance.get("unexplored_elements", []))
        # if unexplored_count > 0:
        #     summary_parts.append(
        #         f"There are {unexplored_count} UI elements on this screen that have not yet been tested.")

        # # Add suggested targets information
        # suggested = guidance.get("suggested_targets", [])
        # if suggested:
        #     targets = []
        #     for target in suggested[:3]:  # Limit to 3 suggestions
        #         name = target.get("name", "Unknown")
        #         visits = target.get("visits", 0)
        #         if visits == 0:
        #             targets.append(f"{name} (not visited)")
        #         else:
        #             targets.append(f"{name} ({visits} visit{'s' if visits > 1 else ''})")
        #
        #     summary_parts.append(f"Suggested targets: {', '.join(targets)}")

        # # Add least visited activities
        # least_visited = guidance.get("least_visited_activities", [])
        # if least_visited and not suggested:  # Only show if no suggested targets
        #     activities = []
        #     for activity in least_visited[:2]:  # Limit to 2
        #         name = activity.get("name", "Unknown")
        #         visits = activity.get("visits", 0)
        #         if visits == 0:
        #             activities.append(f"{name} (not visited)")
        #         else:
        #             activities.append(f"{name} ({visits} visit{'s' if visits > 1 else ''})")
        #
        #     if activities:
        #         summary_parts.append(f"Consider exploring: {', '.join(activities)}")

        return "\n".join(summary_parts)

    def get_dtg(self) -> DynamicTransitionGraph:
        """
        Get the dynamic transition graph.

        Returns:
            DynamicTransitionGraph instance
        """
        return self.dynamic_wtg
