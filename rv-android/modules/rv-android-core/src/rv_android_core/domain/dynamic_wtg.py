"""
Provide domain models for tracking dynamic activity transitions during testing.

This module defines the data structures used to represent and analyze the dynamic
window transition graph (WTG) built during Android application testing. The graph
tracks activity visits, UI element coverage, and transitions between activities,
enabling coverage-aware exploration strategies in rv-agent.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any

import networkx as nx

from rv_android_core.util.logging.manager import LoggingManager

# Module-level logger
_logging_manager = LoggingManager.get_instance()
_logger = _logging_manager.get_logger("rv_android_core.domain.dynamic_wtg")


class DynamicTransition:
    """
    Record information about a dynamic transition between screens.

    Store the source and target activities, the actions that triggered the
    transition, and the number of times this transition has been observed.
    Support serialization for graph persistence via to_dict/from_dict.

    ### Key Features:

    - Transition observation counting with timestamp tracking
    - Equality comparison by source, target, and action identity
    - Dictionary serialization for graph persistence

    ### Role in the System:

    - Edge data in DynamicTransitionGraph between ActivityNode pairs
    - Serialized as part of graph persistence via to_dict/from_dict
    """

    def __init__(self, source_activity: str, target_activity: str,
                 actions: List[Dict[str, Any]], timestamp: datetime = None):
        """Initialize transition between two activities.

        Args:
            source_activity: Fully qualified name of the source activity.
            target_activity: Fully qualified name of the target activity.
            actions: List of action dictionaries that triggered this transition.
            timestamp: When the transition was observed. Defaults to now.

        State:
            self.source_activity: Source activity name.
            self.target_activity: Target activity name.
            self.actions: Actions that triggered this transition.
            self.timestamp: Last observation time. Updated on increment_count.
            self.count: Number of times this transition has been observed.
                Starts at 1, incremented by increment_count.
        """
        self.source_activity = source_activity
        self.target_activity = target_activity
        self.actions = actions
        self.timestamp = timestamp or datetime.now()
        self.count = 1

    def increment_count(self):
        """Increment the observation count and update timestamp."""
        self.count += 1
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with keys:
            - "source_activity" (str): Fully qualified source activity name.
            - "target_activity" (str): Fully qualified target activity name.
            - "actions" (list): Action dictionaries that triggered this transition.
            - "timestamp" (str): ISO 8601 formatted observation timestamp.
            - "count" (int): Number of times this transition was observed.
        """
        return {
            "source_activity": self.source_activity,
            "target_activity": self.target_activity,
            "actions": self.actions,
            "timestamp": self.timestamp.isoformat(),
            "count": self.count
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DynamicTransition':
        """Create from dictionary representation.

        Args:
            data: Dictionary with transition data as produced by to_dict.

        Returns:
            DynamicTransition instance with restored state including
            timestamp and observation count.
        """
        transition = cls(
            data["source_activity"],
            data["target_activity"],
            data["actions"]
        )
        transition.timestamp = datetime.fromisoformat(data["timestamp"])
        transition.count = data["count"]
        return transition

    def __eq__(self, other):
        if not isinstance(other, DynamicTransition):
            return False
        return (self.source_activity == other.source_activity and
                self.target_activity == other.target_activity and
                self.actions == other.actions)

    def __hash__(self):
        return hash((self.source_activity, self.target_activity, self.actions))


class ActivityNode:
    """
    Represent an activity node in the dynamic transition graph.

    Track visit history and UI element coverage for a single Android activity.
    Each node records when it was first and last visited, how many times it
    has been visited, and which UI elements have been tested on it.

    ### Key Features:

    - Visit tracking with first/last visit timestamps and count
    - UI element coverage tracking via action IDs
    - Coverage percentage calculation against total available elements
    - Serialization support for graph persistence

    ### Role in the System:

    - Stored in DynamicTransitionGraph.activities as per-activity state
    - Used by rv-agent exploration strategies for coverage-aware decisions
    - Persisted via to_dict/from_dict for experiment continuation
    """

    def __init__(self, activity_name: str):
        """Initialize activity node with the given name.

        Args:
            activity_name: Fully qualified Android activity name.

        State:
            self.name: Activity name.
            self.visit_count: Number of visits recorded. Starts at 0.
            self.first_visit: Timestamp of first visit, or None if unvisited.
            self.last_visit: Timestamp of most recent visit, or None if unvisited.
            self.ui_elements_tested: Set of action IDs tested on this activity.
                Grows as record_tested_element is called.
        """
        self.name = activity_name
        self.visit_count = 0
        self.first_visit = None
        self.last_visit = None
        self.ui_elements_tested: Set[str] = set()

    def record_visit(self):
        """Record a visit to this activity and update timestamps."""
        self.visit_count += 1
        _logger.debug(f"Recording visit to activity: {self.name}, count: {self.visit_count}")
        now = datetime.now()
        if not self.first_visit:
            self.first_visit = now
        self.last_visit = now

    def record_tested_element(self, action_id: str):
        """Record that a UI element was tested on this activity.

        Args:
            action_id: Identifier of the UI element action that was tested.
        """
        self.ui_elements_tested.add(action_id)
        _logger.debug(f"Recording tested element: {action_id} ::: ui_elements_tested={self.ui_elements_tested}")

    def get_coverage_percentage(self, total_elements: int) -> float:
        """Calculate the UI element coverage percentage for this activity.

        Args:
            total_elements: Total number of UI elements available on this
                activity. When 0, returns 100.0 (vacuous coverage).

        Returns:
            Coverage percentage from 0.0 to 100.0.
        """
        if total_elements == 0:
            return 100.0
        return (len(self.ui_elements_tested) / total_elements) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with keys:
            - "name" (str): Activity name.
            - "visit_count" (int): Number of recorded visits.
            - "first_visit" (str or None): ISO 8601 timestamp of first visit.
            - "last_visit" (str or None): ISO 8601 timestamp of last visit.
            - "ui_elements_tested" (list): Action IDs of tested UI elements.
        """
        return {
            "name": self.name,
            "visit_count": self.visit_count,
            "first_visit": self.first_visit.isoformat() if self.first_visit else None,
            "last_visit": self.last_visit.isoformat() if self.last_visit else None,
            "ui_elements_tested": list(self.ui_elements_tested)
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ActivityNode':
        """Create from dictionary representation.

        Args:
            data: Dictionary with activity node data as produced by to_dict.

        Returns:
            ActivityNode instance with restored visit history and coverage data.
        """
        node = cls(data["name"])
        node.visit_count = data["visit_count"]
        if data["first_visit"]:
            node.first_visit = datetime.fromisoformat(data["first_visit"])
        if data["last_visit"]:
            node.last_visit = datetime.fromisoformat(data["last_visit"])
        node.ui_elements_tested = set(data["ui_elements_tested"])
        return node


class DynamicTransitionGraph:
    """
    Track dynamic transitions between activities observed during testing.

    Build and maintain a directed graph of activity transitions discovered
    at runtime, using NetworkX for graph operations. The graph accumulates
    visit counts, transition frequencies, and UI element coverage data
    to support coverage-aware exploration in rv-agent.

    ### Architectural Decisions:

    - NetworkX DiGraph: Leverages established graph library for traversal
      and neighbor queries rather than custom graph implementation
    - Dual storage: Maintains both NetworkX graph (for queries) and
      explicit transitions list (for serialization and detailed data)
    - Activity name normalization: Converts Android component names
      (forward-slash format) to dot-separated format on recording

    ### Role in the System:

    - Built incrementally by rv-agent during testing sessions
    - Provides exploration guidance via suggest_next_activity and
      get_actions_for_coverage
    - Persisted via to_dict/from_dict for experiment continuation

    ### Key Features:

    - Activity visit tracking with per-activity coverage metrics
    - Transition recording with duplicate detection and count tracking
    - Unexplored and least-visited activity queries
    - Coverage gap analysis for targeted exploration

    ### Integration Points:

    - Input: Activity names and action data from rv-agent exploration
    - Output: Navigation suggestions and coverage analysis
    - Dependencies: NetworkX for graph operations, ActivityNode for
      per-activity state, DynamicTransition for edge data
    """

    def __init__(self):
        """Initialize empty dynamic transition graph.

        State:
            self.logger: Logger for graph operations.
            self.graph: NetworkX DiGraph storing activity nodes and edges.
            self.activities: Mapping of activity names to ActivityNode instances.
            self.transitions: List of all recorded DynamicTransition instances.
            self.current_activity: Name of the most recently visited activity,
                or None if no visit has been recorded.
        """
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger("rv_android_core.domain.dynamic_wtg")
        self.graph = nx.DiGraph()
        self.activities: Dict[str, ActivityNode] = {}
        self.transitions: List[DynamicTransition] = []
        self.current_activity = None

    def add_activity(self, activity_name: str) -> ActivityNode:
        """Add an activity node to the graph, or return existing one.

        Args:
            activity_name: Fully qualified Android activity name.

        Returns:
            ActivityNode for the given activity, newly created or existing.
        """
        if activity_name not in self.activities:
            self.activities[activity_name] = ActivityNode(activity_name)
            self.graph.add_node(activity_name)
            self.logger.debug(f"Added new activity: {activity_name}")
        return self.activities[activity_name]

    def record_visit(self, activity_name: str):
        """Record a visit to an activity and set it as current.

        Normalize the activity name from Android component format
        (forward-slash separated) to dot-separated format before recording.

        Args:
            activity_name: Activity name, possibly in Android component format
                (e.g., "com.example/.MainActivity").
        """
        # Android component names use forward-slash format (com.example/.MainActivity)
        # but the graph stores dot-separated format (com.example.MainActivity)
        normalized_name = activity_name.replace("/", ".")
        if normalized_name.endswith(".."):
            normalized_name = normalized_name[:-1]

        node = self.add_activity(normalized_name)
        node.record_visit()
        self.current_activity = normalized_name
        self.logger.debug(f"Recorded visit to activity: {normalized_name}, count: {node.visit_count}")

    def record_transition(self, source_activity: str, target_activity: str,
                          actions: List[Dict[str, Any]]) -> DynamicTransition:
        """Record a transition between two activities.

        Normalize activity names, create or increment an existing transition,
        and update the NetworkX graph edge. If a transition with the same
        source, target, and actions already exists, its count is incremented
        instead of creating a duplicate.

        Args:
            source_activity: Source activity name.
            target_activity: Target activity name.
            actions: List of action dictionaries that triggered the transition.

        Returns:
            DynamicTransition that was created or incremented.
        """

        # Normalize activity names
        source_activity = source_activity.replace("/", "")
        target_activity = target_activity.replace("/", "")

        if source_activity.endswith(".."):
            source_activity = source_activity[:-1]
        if target_activity.endswith(".."):
            target_activity = target_activity[:-1]

        self.logger.info(f"Recording transition: {source_activity} -> {target_activity}")

        # Ensure both activities exist
        self.add_activity(source_activity)
        self.add_activity(target_activity)

        # Check if this transition already exists
        transition = None
        for t in self.transitions:
            if (t.source_activity == source_activity and
                    t.target_activity == target_activity and
                    t.actions == actions):
                transition = t
                transition.increment_count()
                self.logger.info(
                    f"Incremented transition: {source_activity} -> {target_activity}, count: {transition.count}")
                break

        if not transition:
            transition = DynamicTransition(source_activity, target_activity, actions)
            self.transitions.append(transition)
            self.logger.info(f"Added new transition: {source_activity} -> {target_activity}")

        # Update graph edge
        if self.graph.has_edge(source_activity, target_activity):
            self.graph[source_activity][target_activity]["count"] += 1
            self.graph[source_activity][target_activity]["transitions"].append(transition)
        else:
            self.graph.add_edge(source_activity, target_activity, count=1, transitions=[transition])

        return transition

    def record_action(self, activity_name: str, action_id: str):
        """Record that an action was tested on an activity.

        Args:
            activity_name: Activity name where the action was tested.
            action_id: Identifier of the tested UI element action.
        """
        # Normalize activity name
        normalized_name = activity_name.replace("/", ".")
        if normalized_name.endswith(".."):
            normalized_name = normalized_name[:-1]

        node = self.add_activity(normalized_name)
        node.record_tested_element(action_id)
        self.logger.debug(f"Recorded action {action_id} on activity: {normalized_name}")

    def record_current_to_next(self, next_activity: str, action_id: str, action_type: str):
        """Record transition from current activity to next activity.

        Args:
            next_activity: Target activity name.
            action_id: Identifier of the action that triggered the transition.
            action_type: Type of action (e.g., "click", "set_text").

        Returns:
            DynamicTransition if current_activity is set, None otherwise.
        """
        if not self.current_activity:
            self.logger.warning(f"Cannot record transition: no current activity set")
            return None
        # TODO(dynamic-wtg): Review parameter types — record_transition expects
        # actions: List[Dict] but receives action_id: str and action_type: str.
        transition = self.record_transition(self.current_activity, next_activity, action_id, action_type)
        self.current_activity = next_activity
        return transition

    def has_edge(self, source_activity: str, target_activity: str):
        """Check if an edge exists between two activities.

        Args:
            source_activity: Source activity name.
            target_activity: Target activity name.

        Returns:
            True if the graph contains an edge from source to target.
        """
        return self.graph.has_edge(source_activity, target_activity)

    def get_unexplored_activities(self, visited_activities: Set[str]) -> List[str]:
        """Get activities in the graph that have not been visited.

        Args:
            visited_activities: Set of already-visited activity names to exclude.

        Returns:
            List of activity names present in the graph but not in the
            visited set.
        """
        return [name for name in self.graph.nodes() if name not in visited_activities]

    def get_least_visited_activities(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get the least visited activities sorted by visit count.

        Args:
            limit: Maximum number of activities to return. Default 5.

        Returns:
            List of (activity_name, visit_count) tuples sorted by visit count
            ascending.
        """
        sorted_activities = sorted(
            [(name, node.visit_count) for name, node in self.activities.items()],
            key=lambda x: x[1]
        )
        return sorted_activities[:limit]

    def get_actions_for_coverage(self, activity_name: str, current_actions: List[str]) -> List[str]:
        """Get actions that would increase coverage for an activity.

        Filter the given actions to return only those that have not yet been
        tested on the specified activity.

        Args:
            activity_name: Activity to check coverage for.
            current_actions: List of action IDs available on the activity.

        Returns:
            List of action IDs from current_actions that have not been
            tested yet. Empty list if activity is unknown.
        """
        node = self.activities.get(activity_name)
        if not node:
            return []

        return [action_id for action_id in current_actions
                if action_id not in node.ui_elements_tested]

    def suggest_next_activity(self) -> Optional[str]:
        """Suggest which activity to visit next based on visit counts.

        Find the least-visited neighbor of the current activity in the
        transition graph.

        Returns:
            Name of the least-visited neighboring activity, or None if
            no current activity is set or it has no neighbors.
        """
        if not self.current_activity or not self.graph.nodes():
            return None

        # Get least visited neighbors
        neighbors = list(self.graph.neighbors(self.current_activity))
        if not neighbors:
            return None

        # Sort neighbors by visit count
        neighbor_visits = [(n, self.activities[n].visit_count) for n in neighbors]
        neighbor_visits.sort(key=lambda x: x[1])

        self.logger.info(f"Suggested next activity: {neighbor_visits[0][0] if neighbor_visits else None}")

        # Return the least visited neighbor
        return neighbor_visits[0][0] if neighbor_visits else None

    def to_dict(self) -> Dict:
        """Convert graph to dictionary representation.

        Returns:
            Dictionary with keys:
            - "activities" (dict): Mapping of activity names to their
              serialized ActivityNode data.
            - "transitions" (list): List of serialized DynamicTransition
              dictionaries.
            - "current_activity" (str or None): Name of the most recently
              visited activity.
        """
        return {
            "activities": {name: node.to_dict() for name, node in self.activities.items()},
            "transitions": [t.to_dict() for t in self.transitions],
            "current_activity": self.current_activity
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DynamicTransitionGraph':
        """Create graph from dictionary representation.

        Reconstruct the full graph including all activities, transitions,
        and NetworkX edges from serialized data.

        Args:
            data: Dictionary with graph data as produced by to_dict.

        Returns:
            DynamicTransitionGraph instance with fully restored state
            including NetworkX edges and transition counts.
        """
        graph = cls()

        # Load activities
        for name, node_data in data["activities"].items():
            graph.activities[name] = ActivityNode.from_dict(node_data)
            graph.graph.add_node(name)

        # Load transitions
        for t_data in data["transitions"]:
            transition = DynamicTransition.from_dict(t_data)
            graph.transitions.append(transition)

            # Update graph edge
            source = transition.source_activity
            target = transition.target_activity

            if graph.graph.has_edge(source, target):
                graph.graph[source][target]["count"] += transition.count
                graph.graph[source][target]["transitions"].append(transition)
            else:
                graph.graph.add_edge(source, target, count=transition.count, transitions=[transition])

        graph.current_activity = data["current_activity"]
        return graph
