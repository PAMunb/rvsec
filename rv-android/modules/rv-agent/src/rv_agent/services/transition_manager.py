"""
Transition manager integrating WTG (static) with DynamicStateGraph (runtime).

Combine static analysis navigation knowledge with dynamic exploration history
to provide navigation guidance for the exploration agent. Map runtime activity
names to static Window IDs from GATOR analysis, track visited activities, and
suggest unvisited targets prioritized by MOP reachability.

### Architectural Decisions:

- Multi-strategy matching: exact, name, and partial match for activity-to-window mapping
- Graceful degradation: functions return empty results when static data unavailable
- Priority scoring: unvisited targets +100, direct MOP +50, MOP-reaching +25

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
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenDescription

# Max hops for MOP BFS path (matches Strategy A's MAX_BACKTRACK_HOPS)
MAX_MOP_BFS_DEPTH = 8


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
        dynamic_graph: DynamicStateGraph,
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
        if static_data and hasattr(static_data, "wtg"):
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

        if not self.static_data or not hasattr(self.static_data, "windows"):
            return None

        windows = self.static_data.windows
        if not windows or not hasattr(windows, "windows"):
            return None

        # Multi-strategy matching because GATOR's static analysis window names
        # don't always match Android's runtime activity names exactly.
        # Example: GATOR may record "MainActivity" while runtime reports
        # "com.example.app.MainActivity". Each strategy is progressively looser.

        # Strategy 1: Exact match on activity field
        for window in windows.windows:
            if hasattr(window, "activity") and window.activity == activity:
                self._activity_to_window_id[activity] = window.id
                return window.id

        # Strategy 2: Exact match on name field
        for window in windows.windows:
            if window.name == activity:
                self._activity_to_window_id[activity] = window.id
                return window.id

        # Strategy 3: Partial match using class simple name.
        # Handles cases like runtime "com.example.SettingsActivity" matching
        # GATOR window "SettingsActivity" or vice versa.
        activity_parts = activity.split(".")
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
            visited = (
                target_activity in self._visited_activities
                if target_activity
                else False
            )

            # Priority scoring combines three factors to rank navigation targets:
            # +100 for unvisited (maximize coverage), +50 for direct MOP access
            # (maximize monitored operation triggering), +25 for transitive MOP reach.
            priority = self._calculate_target_priority(
                target_id=target_id,
                visited=visited,
                widget_id=transition.get("widget_id"),
            )

            suggestions.append(
                {
                    "target_activity": target_activity or f"window_{target_id}",
                    "target_window_id": target_id,
                    "widget_id": transition.get("widget_id"),
                    "event_type": transition.get("event_type"),
                    "method": transition.get("method"),
                    "visited": visited,
                    "priority": priority,
                }
            )

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
        if not self.static_data or not hasattr(self.static_data, "windows"):
            return None

        for window in self.static_data.windows.windows:
            if window.id == window_id:
                return window.activity or window.name

        return None

    def _calculate_target_priority(
        self, target_id: str, visited: bool, widget_id: Optional[str]
    ) -> int:
        """
        Calculate priority score for a navigation target.

        Priority factors:
        - Unvisited targets get +100
        - Direct MOP targets get +50
        - MOP-reaching targets get +25

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
        if widget_id and self.static_data and hasattr(self.static_data, "windows"):
            widget = self._find_widget_globally(widget_id)
            if widget and hasattr(widget, "events"):
                for event in widget.events:
                    if hasattr(event, "signature"):
                        method = self._get_method(event.signature)
                        if method:
                            if getattr(method, "directly_reaches_mop", False):
                                priority += 50
                            elif getattr(method, "reaches_mop", False):
                                priority += 25

        return priority

    def _find_widget_globally(self, widget_id: str):
        """
        Find widget by ID across all windows.

        Args:
            widget_id: Widget ID to find.

        Returns:
            Widget or None.
        """
        if not self.static_data or not hasattr(self.static_data, "windows"):
            return None

        # Try global widgets dict
        if hasattr(self.static_data.windows, "widgets"):
            widget = self.static_data.windows.widgets.get(widget_id)
            if widget:
                return widget

        # Search in all windows
        for window in self.static_data.windows.windows:
            if hasattr(window, "widgets") and widget_id in window.widgets:
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
        if not self.static_data or not hasattr(self.static_data, "classes"):
            return None

        return self.static_data.classes.methods.get(signature)

    def get_navigation_guidance(
        self, current_activity: str, screen_desc: ScreenDescription
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
            "has_static_guidance": False,
        }

        # Mark current activity as visited
        self.mark_activity_visited(current_activity)

        # Get unvisited targets
        unvisited = self.get_unvisited_targets(current_activity)
        guidance["unvisited_targets"] = unvisited
        guidance["has_static_guidance"] = len(unvisited) > 0

        # Map static WTG targets to actual on-screen ItemActions.
        # The mapping bridges the gap between static analysis (widget IDs from
        # GATOR) and runtime UI (parsed actions with coordinates). Only targets
        # that match a visible action on the current screen are returned.
        suggested_actions = self._map_targets_to_actions(unvisited, screen_desc)
        guidance["suggested_actions"] = suggested_actions

        # Exploration progress
        if self.wtg and self.static_data:
            total_windows = (
                len(self.static_data.windows.windows)
                if hasattr(self.static_data, "windows")
                else 0
            )
            visited_count = len(self._visited_activities)
            guidance["exploration_progress"] = {
                "total_windows": total_windows,
                "visited_activities": visited_count,
                "coverage_percent": (
                    (visited_count / total_windows * 100) if total_windows > 0 else 0
                ),
            }

        return guidance

    def _map_targets_to_actions(
        self, targets: List[Dict[str, Any]], screen_desc: ScreenDescription
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
                suggested.append(
                    {
                        **target,
                        "action_id": action.id,
                        "action_text": action_text,
                        "action_type": action.action_type,
                        "coordinates": action.get_execution_coordinates(),
                    }
                )

        return suggested

    def _get_action_description(self, action: ItemAction) -> str:
        """
        Build descriptive text for an action from its target_view properties.

        Prioritizes: content_description > text > resource_id > class name

        Args:
            action: ItemAction to describe.

        Returns:
            Human-readable description of the action target.
        """
        target = action.target_view
        if not target:
            return action.text  # Fallback to original text

        # Try content_description first (accessibility label)
        content_desc = target.get("content_description", "")
        if content_desc:
            return content_desc

        # Try view text
        text = target.get("text", "")
        if text:
            return text

        # Try resource_id (extract meaningful name)
        resource_id = target.get("resource_id", "")
        if resource_id:
            # Extract name from "com.example:id/button_name" -> "button_name"
            parts = resource_id.split("/")
            if len(parts) > 1:
                return parts[-1].replace("_", " ")

        # Fall back to class name
        class_name = target.get("class", "")
        if class_name:
            # Extract simple name from "android.widget.Button" -> "Button"
            return class_name.split(".")[-1]

        return action.text  # Final fallback

    def _find_action_by_widget_id(
        self, widget_id: str, screen_desc: ScreenDescription
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
            if hasattr(action, "widget_id") and action.widget_id == widget_id:
                self.logger.debug(
                    f"WTG match found: widget_id={widget_id}, action_id={action.id}"
                )
                return action

        self.logger.debug(f"WTG match not found: widget_id={widget_id}")
        return None

    def plan_path_to_mop_activity(
        self,
        current_activity: str,
        mop_data: Any,
        possible_actions: Optional[List] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        BFS on WTG transitions to find path to activity with MOP methods.

        Starting from the current activity, performs breadth-first search on
        the WTG graph. For each reachable activity, checks if it has MOP methods
        (from static analysis classes data). Scores candidates by MOP density
        (number of MOP methods in the activity) and returns the path to the
        best candidate as a list of action dicts.

        Args:
            current_activity: Current runtime activity name.
            mop_data: Static analysis data or MOP data dict. Currently unused
                directly -- MOP information is extracted from self.static_data.classes.

        Returns:
            List of action dicts for the path to the best MOP activity, or None
            if no MOP activity is reachable. Each action dict contains:
            - action_type: "BACK" or event type
            - target_activity: Target activity name
            - widget_id: Widget triggering the transition (if available)
        """
        if not self.wtg or not self.static_data:
            return None

        current_window_id = self.find_window_id_for_activity(current_activity)
        if not current_window_id:
            self.logger.debug(
                f"plan_path_to_mop_activity: No window ID for {current_activity}"
            )
            return None

        # BFS on the static WTG graph to find shortest path to an activity
        # containing MOP methods. Unlike runtime navigation (which goes screen
        # by screen), this plans the full path ahead of time using static knowledge.
        # Only step 1 is resolved against current screen actions; subsequent steps
        # are re-planned when the agent reaches each intermediate screen.
        visited: Set[str] = {current_window_id}
        queue: deque = deque()

        # Seed BFS with direct transitions from current window
        for transition in self.wtg.get_window_transitions(current_window_id):
            target_id = transition.get("target")
            if target_id and target_id not in visited:
                queue.append((target_id, [transition]))
                visited.add(target_id)

        # Collect candidates: (mop_count, path)
        candidates: List[Tuple[int, List[Dict[str, Any]]]] = []

        while queue:
            window_id, path = queue.popleft()

            # Depth limit: skip nodes beyond MAX_MOP_BFS_DEPTH hops
            if len(path) > MAX_MOP_BFS_DEPTH:
                from rv_agent import tracking as track

                track._counters["mop_bfs_depth_limited"] += 1
                self.logger.debug(
                    f"plan_path_to_mop_activity: BFS depth limited at {len(path)} hops"
                )
                continue

            # Check MOP density for this window's activity
            activity_name = self._find_activity_for_window_id(window_id)
            if activity_name:
                mop_count = self._count_mop_methods_for_activity(activity_name)
                if mop_count > 0:
                    candidates.append((mop_count, path))
                    # Continue BFS to find potentially better candidates,
                    # but don't expand further from MOP activities (greedy)
                    continue

            # Expand neighbors
            for transition in self.wtg.get_window_transitions(window_id):
                target_id = transition.get("target")
                if target_id and target_id not in visited:
                    visited.add(target_id)
                    queue.append((target_id, path + [transition]))

        if not candidates:
            self.logger.debug("plan_path_to_mop_activity: No MOP activity reachable")
            return None

        # Select best candidate by MOP density (highest first), then shortest path.
        # MOP density (number of monitored methods) is preferred over path length
        # because reaching a screen with 10 MOP methods is more valuable than
        # reaching one with 1 MOP method, even if the path is slightly longer.
        candidates.sort(key=lambda c: (-c[0], len(c[1])))
        best_mop_count, best_path = candidates[0]

        # Only resolve step 1 (first transition) against possible_actions.
        # Subsequent steps exist on intermediate screens that we haven't
        # reached yet — they will be re-planned on arrival at each screen.
        first_step = best_path[0]
        target_activity = self._find_activity_for_window_id(
            first_step.get("target", "")
        )
        wtg_widget_id = first_step.get("widget_id", "")

        # Try to resolve step 1 coordinates from possible_actions
        resolved_coords = None
        resolved_target_view = {}
        resolved_action_id = 0

        if possible_actions and wtg_widget_id:
            matched = self._resolve_wtg_action(
                wtg_widget_id, target_activity, possible_actions
            )
            if matched:
                resolved_coords = matched.coordinates
                resolved_target_view = matched.target_view or {}
                resolved_action_id = matched.id

        if resolved_coords is None:
            self.logger.info(
                f"plan_path_to_mop_activity: Step 1 unresolvable "
                f"(widget_id={wtg_widget_id}, target={target_activity})"
            )
            return None

        action_dict = {
            "action_type": "CLICK",
            "action_id": resolved_action_id,
            "widget_id": wtg_widget_id,
            "target_activity": target_activity or f"window_{first_step.get('target')}",
            "text": f"Navigate to {target_activity or 'unknown'}",
            "reaches_mop": True,
            "directly_reaches_mop": False,
            "coordinates": resolved_coords,
            "target_view": resolved_target_view,
        }

        self.logger.info(
            f"plan_path_to_mop_activity: Found path to MOP activity "
            f"({best_mop_count} MOP methods, {len(best_path)} total hops, "
            f"returning step 1 only)"
        )
        return [action_dict]

    def _count_mop_methods_for_activity(self, activity_name: str) -> int:
        """
        Count MOP methods associated with an activity.

        Searches static analysis classes data for methods in the activity's
        class that reach monitored operations.

        Args:
            activity_name: Activity class name (e.g., "com.example.MainActivity").

        Returns:
            Number of MOP methods found in the activity's class.
        """
        if not self.static_data or not hasattr(self.static_data, "classes"):
            return 0

        classes = self.static_data.classes
        if not hasattr(classes, "methods"):
            return 0

        count = 0
        for sig, method in classes.methods.items():
            # Match method's class_name with the activity name
            if not hasattr(method, "class_name"):
                continue
            if method.class_name != activity_name:
                continue
            if getattr(method, "reaches_mop", False) or getattr(
                method, "directly_reaches_mop", False
            ):
                count += 1

        return count

    def _resolve_wtg_action(
        self,
        wtg_widget_id: str,
        target_activity: Optional[str],
        possible_actions: List,
    ) -> Optional[Any]:
        """
        Match a WTG widget_id to a real on-screen ItemAction with coordinates.

        Matching strategy (in priority order):
        1. widget_id equality match against action.widget_id
        2. Target activity simple name in action.text or content_description
        3. Target activity simple name substring in action.widget_id

        Args:
            wtg_widget_id: Widget ID from WTG transition edge.
            target_activity: Target activity name (e.g., "com.example.SettingsActivity").
            possible_actions: List of ItemAction from current screen's parsed UI.

        Returns:
            Matched ItemAction with valid coordinates, or None.
        """
        if not possible_actions:
            return None

        # Strategy 1: widget_id equality match
        for action in possible_actions:
            if not action.coordinates:
                continue
            if action.widget_id and wtg_widget_id == action.widget_id:
                self.logger.debug(
                    f"Resolved WTG widget {wtg_widget_id} via widget_id match: "
                    f"action.widget_id={action.widget_id}"
                )
                return action

        # Strategy 2: target activity simple name in action text/content_description
        if target_activity:
            simple_name = target_activity.split(".")[-1].lower()
            for action in possible_actions:
                if not action.coordinates:
                    continue
                action_text = (action.text or "").lower()
                content_desc = (
                    (action.target_view or {}).get("content_description", "") or ""
                ).lower()
                if simple_name in action_text or simple_name in content_desc:
                    self.logger.debug(
                        f"Resolved WTG widget {wtg_widget_id} via activity name "
                        f"'{simple_name}' in text/desc"
                    )
                    return action

        # Strategy 3: target activity simple name in widget_id
        if target_activity:
            simple_name = target_activity.split(".")[-1].lower()
            for action in possible_actions:
                if not action.coordinates:
                    continue
                if action.widget_id and simple_name in action.widget_id.lower():
                    self.logger.debug(
                        f"Resolved WTG widget {wtg_widget_id} via activity name "
                        f"'{simple_name}' in widget_id"
                    )
                    return action

        self.logger.debug(
            f"Could not resolve WTG widget {wtg_widget_id} "
            f"(target={target_activity}) from {len(possible_actions)} actions"
        )
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
            "avg_coverage": self.dynamic_graph.get_avg_coverage(),
        }

        if self.wtg and self.static_data and hasattr(self.static_data, "windows"):
            total_windows = len(self.static_data.windows.windows)
            summary["total_static_windows"] = total_windows
            summary["static_coverage_percent"] = (
                (len(self._visited_activities) / total_windows * 100)
                if total_windows > 0
                else 0
            )

        return summary
