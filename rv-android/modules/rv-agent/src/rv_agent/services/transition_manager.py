"""
Transition manager integrating WTG (static) with DynamicStateGraph (runtime).

Combine static analysis navigation knowledge with dynamic exploration history
to provide navigation guidance for the exploration agent. Map runtime activity
names to static Window IDs from GATOR analysis, track visited activities, and
suggest unvisited targets prioritized by MOP reachability.

### Architectural Decisions:

- Multi-strategy matching: exact, name, and partial match for activity-to-window mapping
- Graceful degradation: functions return empty results when static data unavailable
- Priority scoring: unvisited targets +100, MOP-reaching +50, direct MOP +25

### Role in the System:

- Used by NavigationGuidance for unified exploration context
- Used by RVAgentStrategy via WtgScorer for action prioritization
- Consumes WTG and window data from StaticAnalysisData

### Integration Points:

- Input: StaticAnalysisData (WTG, windows), DynamicStateGraph (runtime states)
- Output: Navigation targets, suggested actions, exploration progress metrics
- Dependencies: rv-android-core (StaticAnalysisData, WindowTransitionGraph)
"""

import logging
from typing import Optional, Dict, List, Any, Set

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_android_core.domain.window import Window
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph


class TransitionManager:
    """
    Integrates static WTG with dynamic exploration graph.

    ### Architectural Decisions:
    - Combines static navigation knowledge with runtime exploration
    - Maps activity names to static Window IDs
    - Provides navigation suggestions prioritizing unexplored paths
    - Handles graceful degradation when static data unavailable

    ### Role in the System:
    - Guides exploration towards unvisited screens
    - Prioritizes MOP-reaching paths
    - Maps WTG widget_ids to executable ItemActions
    - Tracks exploration progress across the app

    ### Integration Points:
    - Used by strategies for navigation decisions
    - Receives updates from DynamicStateGraph
    - Consumes WTG data from static analysis
    - Provides guidance to LLM prompts
    """

    def __init__(
        self,
        static_data: Optional[StaticAnalysisData],
        dynamic_graph: DynamicStateGraph
    ):
        """
        Initialize TransitionManager.

        Args:
            static_data: Static analysis data (optional).
            dynamic_graph: Dynamic state graph for runtime tracking.

        State:
            self.wtg: WindowTransitionGraph extracted from static data, or None.
            self._activity_to_window_id: Cache mapping runtime activity names
                to static Window IDs. Populated lazily on first lookup.
            self._visited_activities: Set of activity names visited during exploration.
        """
        self.static_data = static_data
        self.dynamic_graph = dynamic_graph
        self.logger = logging.getLogger(__name__)

        # Extract WTG from static data if available
        self.wtg: Optional[WindowTransitionGraph] = None
        if static_data and hasattr(static_data, 'wtg'):
            self.wtg = static_data.wtg

        # Cache for activity -> window ID mapping
        self._activity_to_window_id: Dict[str, str] = {}

        # Track visited activities
        self._visited_activities: Set[str] = set()

        self.logger.info(
            f"TransitionManager initialized. "
            f"WTG: {'available' if self.wtg else 'not available'}"
        )

    def find_window_id_for_activity(self, activity: str) -> Optional[str]:
        """
        Find the static Window ID for a runtime activity.

        Uses multiple matching strategies:
        1. Exact match on activity field
        2. Exact match on name field
        3. Partial match (activity class name in window name)

        Args:
            activity: Runtime activity name (e.g., "com.example.MainActivity")

        Returns:
            Window ID or None if not found
        """
        # Check cache first
        if activity in self._activity_to_window_id:
            return self._activity_to_window_id[activity]

        if not self.static_data or not hasattr(self.static_data, 'windows'):
            return None

        windows = self.static_data.windows
        if not windows or not hasattr(windows, 'windows'):
            return None

        # Strategy 1: Exact match on activity field
        for window in windows.windows:
            if hasattr(window, 'activity') and window.activity == activity:
                self._activity_to_window_id[activity] = window.id
                return window.id

        # Strategy 2: Exact match on name field
        for window in windows.windows:
            if window.name == activity:
                self._activity_to_window_id[activity] = window.id
                return window.id

        # Strategy 3: Partial match
        activity_parts = activity.split('.')
        activity_class = activity_parts[-1] if activity_parts else activity

        for window in windows.windows:
            if activity_class in window.name:
                self._activity_to_window_id[activity] = window.id
                return window.id

            if window.name in activity:
                self._activity_to_window_id[activity] = window.id
                return window.id

        return None

    def mark_activity_visited(self, activity: str):
        """
        Mark an activity as visited during exploration.

        Args:
            activity: Activity name that was visited.
        """
        self._visited_activities.add(activity)

    def get_unvisited_targets(self, current_activity: str) -> List[Dict[str, Any]]:
        """
        Get unvisited activities reachable from current activity.

        Combines static WTG knowledge with dynamic exploration history.

        Args:
            current_activity: Current runtime activity name.

        Returns:
            List of dicts with target info:
            - target_activity: Target activity name
            - target_window_id: Static window ID
            - widget_id: Widget that triggers transition
            - event_type: Event type (click, etc.)
            - priority: Priority score (higher = more important)
        """
        suggestions = []

        if not self.wtg:
            return suggestions

        # Find current window ID
        current_window_id = self.find_window_id_for_activity(current_activity)
        if not current_window_id:
            self.logger.debug(f"No window ID found for activity: {current_activity}")
            return suggestions

        # Get transitions from current window
        transitions = self.wtg.get_window_transitions(current_window_id)

        for transition in transitions:
            target_id = transition.get("target")
            if not target_id:
                continue

            # Find target window to get activity name
            target_activity = self._find_activity_for_window_id(target_id)

            # Check if visited
            visited = target_activity in self._visited_activities if target_activity else False

            # Calculate priority
            priority = self._calculate_target_priority(
                target_id=target_id,
                visited=visited,
                widget_id=transition.get("widget_id")
            )

            suggestions.append({
                "target_activity": target_activity or f"window_{target_id}",
                "target_window_id": target_id,
                "widget_id": transition.get("widget_id"),
                "event_type": transition.get("event_type"),
                "method": transition.get("method"),
                "visited": visited,
                "priority": priority
            })

        # Sort by priority (descending)
        suggestions.sort(key=lambda x: x["priority"], reverse=True)

        return suggestions

    def _find_activity_for_window_id(self, window_id: str) -> Optional[str]:
        """
        Find activity name for a window ID.

        Args:
            window_id: Static window ID.

        Returns:
            Activity name or None.
        """
        if not self.static_data or not hasattr(self.static_data, 'windows'):
            return None

        for window in self.static_data.windows.windows:
            if window.id == window_id:
                return window.activity or window.name

        return None

    def _calculate_target_priority(
        self,
        target_id: str,
        visited: bool,
        widget_id: Optional[str]
    ) -> int:
        """
        Calculate priority score for a navigation target.

        Priority factors:
        - Unvisited targets get +100
        - MOP-reaching targets get +50
        - Direct MOP targets get +25

        Args:
            target_id: Target window ID.
            visited: Whether target was visited.
            widget_id: Widget that triggers navigation.

        Returns:
            Priority score.
        """
        priority = 0

        # Unvisited targets are highest priority
        if not visited:
            priority += 100

        # Check MOP reachability for the widget
        if widget_id and self.static_data and hasattr(self.static_data, 'windows'):
            widget = self._find_widget_globally(widget_id)
            if widget and hasattr(widget, 'events'):
                for event in widget.events:
                    if hasattr(event, 'signature'):
                        method = self._get_method(event.signature)
                        if method:
                            if getattr(method, 'directly_reaches_mop', False):
                                priority += 25
                            elif getattr(method, 'reaches_mop', False):
                                priority += 50

        return priority

    def _find_widget_globally(self, widget_id: str):
        """
        Find widget by ID across all windows.

        Args:
            widget_id: Widget ID to find.

        Returns:
            Widget or None.
        """
        if not self.static_data or not hasattr(self.static_data, 'windows'):
            return None

        # Try global widgets dict
        if hasattr(self.static_data.windows, 'widgets'):
            widget = self.static_data.windows.widgets.get(widget_id)
            if widget:
                return widget

        # Search in all windows
        for window in self.static_data.windows.windows:
            if hasattr(window, 'widgets') and widget_id in window.widgets:
                return window.widgets[widget_id]

        return None

    def _get_method(self, signature: str):
        """
        Get method by signature from Classes.

        Args:
            signature: Method signature.

        Returns:
            Method or None.
        """
        if not self.static_data or not hasattr(self.static_data, 'classes'):
            return None

        return self.static_data.classes.methods.get(signature)

    def get_navigation_guidance(
        self,
        current_activity: str,
        screen_desc: ScreenDescription
    ) -> Dict[str, Any]:
        """
        Get comprehensive navigation guidance for the current screen.

        Combines:
        - Static WTG transitions
        - Dynamic exploration history
        - MOP reachability information

        Args:
            current_activity: Current runtime activity.
            screen_desc: Current screen description.

        Returns:
            Dict with navigation guidance:
            - unvisited_targets: Unvisited targets from WTG
            - suggested_actions: Actions that lead to unvisited targets
            - exploration_progress: Current exploration metrics
        """
        guidance = {
            "unvisited_targets": [],
            "suggested_actions": [],
            "exploration_progress": {},
            "has_static_guidance": False
        }

        # Mark current activity as visited
        self.mark_activity_visited(current_activity)

        # Get unvisited targets
        unvisited = self.get_unvisited_targets(current_activity)
        guidance["unvisited_targets"] = unvisited
        guidance["has_static_guidance"] = len(unvisited) > 0

        # Map WTG targets to executable actions
        suggested_actions = self._map_targets_to_actions(unvisited, screen_desc)
        guidance["suggested_actions"] = suggested_actions

        # Exploration progress
        if self.wtg and self.static_data:
            total_windows = len(self.static_data.windows.windows) if hasattr(self.static_data, 'windows') else 0
            visited_count = len(self._visited_activities)
            guidance["exploration_progress"] = {
                "total_windows": total_windows,
                "visited_activities": visited_count,
                "coverage_percent": (visited_count / total_windows * 100) if total_windows > 0 else 0
            }

        return guidance

    def _map_targets_to_actions(
        self,
        targets: List[Dict[str, Any]],
        screen_desc: ScreenDescription
    ) -> List[Dict[str, Any]]:
        """
        Map WTG targets to executable ItemActions in current screen.

        Args:
            targets: List of target dicts from get_unvisited_targets.
            screen_desc: Current screen description.

        Returns:
            List of action suggestions with mapped actions.
        """
        suggested = []

        for target in targets:
            widget_id = target.get("widget_id")
            if not widget_id:
                continue

            # Find matching action in screen description
            action = self._find_action_by_widget_id(widget_id, screen_desc)
            if action:
                # Build descriptive action text from target_view properties
                action_text = self._get_action_description(action)
                suggested.append({
                    **target,
                    "action_id": action.id,
                    "action_text": action_text,
                    "action_type": action.action_type,
                    "coordinates": action.get_execution_coordinates()
                })

        return suggested

    def _get_action_description(self, action: ItemAction) -> str:
        """
        Build descriptive text for an action from its target_view properties.

        Prioritizes: content-desc > text > resource-id > class name

        Args:
            action: ItemAction to describe.

        Returns:
            Human-readable description of the action target.
        """
        target = action.target_view
        if not target:
            return action.text  # Fallback to original text

        # Try content-desc first (accessibility label)
        content_desc = target.get('content-desc', '')
        if content_desc:
            return content_desc

        # Try view text
        text = target.get('text', '')
        if text:
            return text

        # Try resource-id (extract meaningful name)
        resource_id = target.get('resource-id', '')
        if resource_id:
            # Extract name from "com.example:id/button_name" -> "button_name"
            parts = resource_id.split('/')
            if len(parts) > 1:
                return parts[-1].replace('_', ' ')

        # Fall back to class name
        class_name = target.get('class', '')
        if class_name:
            # Extract simple name from "android.widget.Button" -> "Button"
            return class_name.split('.')[-1]

        return action.text  # Final fallback

    def _find_action_by_widget_id(
        self,
        widget_id: str,
        screen_desc: ScreenDescription
    ) -> Optional[ItemAction]:
        """
        Find ItemAction that corresponds to a static widget ID.

        The visitor (RVAgentVisitor) sets widget_id on actions during parsing.
        This method simply looks up the action by that ID.

        Args:
            widget_id: Static widget ID (e.g., "2131755177").
            screen_desc: Current screen description.

        Returns:
            Matching ItemAction or None.
        """
        # Direct match via events_by_id
        # The visitor should have set widget_id during parsing
        for action in screen_desc.events_by_id.values():
            if hasattr(action, 'widget_id') and action.widget_id == widget_id:
                self.logger.debug(f"WTG match found: widget_id={widget_id}, action_id={action.id}")
                return action

        self.logger.debug(f"WTG match not found: widget_id={widget_id}")
        return None

    def get_exploration_summary(self) -> Dict[str, Any]:
        """Get summary of exploration progress.

        Returns:
            Dictionary with keys:
            - "visited_activities" (list): List of visited activity names.
            - "visited_count" (int): Number of visited activities.
            - "dynamic_states" (int): Total states in dynamic graph.
            - "dynamic_transitions" (int): Total transitions recorded.
            - "avg_coverage" (float): Average action coverage across states.
            - "total_static_windows" (int): Total WTG windows (if available).
            - "static_coverage_percent" (float): Visited/total windows percentage.
        """
        summary = {
            "visited_activities": list(self._visited_activities),
            "visited_count": len(self._visited_activities),
            "dynamic_states": len(self.dynamic_graph.states),
            "dynamic_transitions": len(self.dynamic_graph.transitions),
            "avg_coverage": self.dynamic_graph.get_avg_coverage()
        }

        if self.wtg and self.static_data and hasattr(self.static_data, 'windows'):
            total_windows = len(self.static_data.windows.windows)
            summary["total_static_windows"] = total_windows
            summary["static_coverage_percent"] = (
                len(self._visited_activities) / total_windows * 100
            ) if total_windows > 0 else 0

        return summary
