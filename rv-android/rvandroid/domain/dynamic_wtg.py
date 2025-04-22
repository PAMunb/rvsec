# rvandroid/model/dynamic_wtg.py
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from rvandroid.util.logging.manager import LoggingManager


class DynamicTransition:
    """Records information about a dynamic transition between screens"""

    def __init__(self, source_activity: str, target_activity: str,
                 action_id: str, action_type: str, timestamp: datetime = None):
        self.source_activity = source_activity
        self.target_activity = target_activity
        self.action_id = action_id
        self.action_type = action_type
        self.timestamp = timestamp or datetime.now()
        self.count = 1  # Number of times this transition has been observed

    def increment_count(self):
        """Increment the observation count for this transition"""
        self.count += 1
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "source_activity": self.source_activity,
            "target_activity": self.target_activity,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "timestamp": self.timestamp.isoformat(),
            "count": self.count
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DynamicTransition':
        """Create from dictionary representation"""
        transition = cls(
            data["source_activity"],
            data["target_activity"],
            data["action_id"],
            data["action_type"]
        )
        transition.timestamp = datetime.fromisoformat(data["timestamp"])
        transition.count = data["count"]
        return transition

    def __eq__(self, other):
        if not isinstance(other, DynamicTransition):
            return False
        return (self.source_activity == other.source_activity and
                self.target_activity == other.target_activity and
                self.action_id == other.action_id)

    def __hash__(self):
        return hash((self.source_activity, self.target_activity, self.action_id))


class ActivityNode:
    """Represents an activity node in the dynamic graph"""

    def __init__(self, activity_name: str):
        self.name = activity_name
        self.visit_count = 0
        self.first_visit = None
        self.last_visit = None
        self.ui_elements_tested: Set[str] = set()  # Set of action_ids that have been tested

    def record_visit(self):
        """Record a visit to this activity"""
        self.visit_count += 1
        now = datetime.now()
        if not self.first_visit:
            self.first_visit = now
        self.last_visit = now

    def record_tested_element(self, action_id: str):
        """Record that a UI element was tested"""
        self.ui_elements_tested.add(action_id)

    def get_coverage_percentage(self, total_elements: int) -> float:
        """Calculate the coverage percentage for this activity"""
        if total_elements == 0:
            return 100.0
        return (len(self.ui_elements_tested) / total_elements) * 100

    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "name": self.name,
            "visit_count": self.visit_count,
            "first_visit": self.first_visit.isoformat() if self.first_visit else None,
            "last_visit": self.last_visit.isoformat() if self.last_visit else None,
            "ui_elements_tested": list(self.ui_elements_tested)
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ActivityNode':
        """Create from dictionary representation"""
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
    Tracks the dynamic transitions between activities observed during testing.
    Uses NetworkX for efficient graph operations and provides analysis methods.
    """

    def __init__(self):
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger("domain.dynamic_wtg")
        self.graph = nx.DiGraph()
        self.activities: Dict[str, ActivityNode] = {}
        self.transitions: List[DynamicTransition] = []
        self.current_activity = None

    def add_activity(self, activity_name: str) -> ActivityNode:
        """Add or get an activity node"""
        if activity_name not in self.activities:
            self.activities[activity_name] = ActivityNode(activity_name)
            self.graph.add_node(activity_name)
            self.logger.debug(f"Added new activity: {activity_name}")
        return self.activities[activity_name]

    def record_visit(self, activity_name: str):
        """Record a visit to an activity"""
        # Normalize activity name
        normalized_name = activity_name.replace("/", ".")
        if normalized_name.endswith(".."):
            normalized_name = normalized_name[:-1]

        node = self.add_activity(normalized_name)
        node.record_visit()
        self.current_activity = normalized_name
        self.logger.debug(f"Recorded visit to activity: {normalized_name}, count: {node.visit_count}")

    def record_transition(self, source_activity: str, target_activity: str,
                          action_id: str, action_type: str) -> DynamicTransition:
        """Record a transition between activities"""

        # Normalize activity names
        source_activity = source_activity.replace("/", "")
        target_activity = target_activity.replace("/", "")

        if source_activity.endswith(".."):
            source_activity = source_activity[:-1]
        if target_activity.endswith(".."):
            target_activity = target_activity[:-1]

        # Ensure both activities exist
        self.add_activity(source_activity)
        self.add_activity(target_activity)

        # Check if this transition already exists
        transition = None
        for t in self.transitions:
            if (t.source_activity == source_activity and
                    t.target_activity == target_activity and
                    t.action_id == action_id):
                transition = t
                transition.increment_count()
                self.logger.debug(
                    f"Incremented transition: {source_activity} -> {target_activity}, count: {transition.count}")
                break

        if not transition:
            transition = DynamicTransition(source_activity, target_activity, action_id, action_type)
            self.transitions.append(transition)
            self.logger.debug(f"Added new transition: {source_activity} -> {target_activity}")

        # Update graph edge
        if self.graph.has_edge(source_activity, target_activity):
            self.graph[source_activity][target_activity]["count"] += 1
            self.graph[source_activity][target_activity]["transitions"].append(transition)
        else:
            self.graph.add_edge(source_activity, target_activity, count=1, transitions=[transition])

        return transition

    def record_action(self, activity_name: str, action_id: str):
        """Record that an action was tested on an activity"""
        # Normalize activity name
        normalized_name = activity_name.replace("/", ".")
        if normalized_name.endswith(".."):
            normalized_name = normalized_name[:-1]

        node = self.add_activity(normalized_name)
        node.record_tested_element(action_id)
        self.logger.debug(f"Recorded action {action_id} on activity: {normalized_name}")

    def record_current_to_next(self, next_activity: str, action_id: str, action_type: str):
        """Record transition from current activity to next activity"""
        if not self.current_activity:
            self.logger.warning(f"Cannot record transition: no current activity set")
            return None

        transition = self.record_transition(self.current_activity, next_activity, action_id, action_type)
        self.current_activity = next_activity
        return transition

    def get_unexplored_activities(self, visited_activities: Set[str]) -> List[str]:
        """Get activities that exist in the graph but have not been visited"""
        return [name for name in self.graph.nodes() if name not in visited_activities]

    def get_least_visited_activities(self, limit: int = 5) -> List[Tuple[str, int]]:
        """Get the least visited activities with their visit counts"""
        sorted_activities = sorted(
            [(name, node.visit_count) for name, node in self.activities.items()],
            key=lambda x: x[1]
        )
        return sorted_activities[:limit]

    def get_actions_for_coverage(self, activity_name: str, current_actions: List[str]) -> List[str]:
        """Get actions that would increase coverage for an activity"""
        node = self.activities.get(activity_name)
        if not node:
            return []

        return [action_id for action_id in current_actions
                if action_id not in node.ui_elements_tested]

    def suggest_next_activity(self) -> Optional[str]:
        """Suggest which activity to visit next based on coverage and transition history"""
        if not self.current_activity or not self.graph.nodes():
            return None

        # Get least visited neighbors
        neighbors = list(self.graph.neighbors(self.current_activity))
        if not neighbors:
            return None

        # Sort neighbors by visit count
        neighbor_visits = [(n, self.activities[n].visit_count) for n in neighbors]
        neighbor_visits.sort(key=lambda x: x[1])

        # Return the least visited neighbor
        return neighbor_visits[0][0] if neighbor_visits else None

    def to_dict(self) -> Dict:
        """Convert to dictionary representation"""
        return {
            "activities": {name: node.to_dict() for name, node in self.activities.items()},
            "transitions": [t.to_dict() for t in self.transitions],
            "current_activity": self.current_activity
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DynamicTransitionGraph':
        """Create from dictionary representation"""
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

    def save_to_file(self, filename: str) -> bool:
        """
        Save the dynamic transition graph to a file.

        Args:
            filename: Path to save the file

        Returns:
            True if successful, False otherwise
        """
        # TODO: Implement this method
        pass
        # try:
        #     data = self.to_dict()
        #     os.makedirs(os.path.dirname(filename), exist_ok=True)
        #     with open(filename, 'w') as f:
        #         json.dump(data, f, indent=2)
        #     self.logger.info(f"Dynamic transition graph saved to {filename}")
        #     return True
        # except Exception as e:
        #     self.logger.error(f"Error saving dynamic transition graph: {e}")
        #     return False

    @classmethod
    def load_from_file(cls, filename: str) -> Optional['DynamicTransitionGraph']:
        """
        Load the dynamic transition graph from a file.

        Args:
            filename: Path to the file

        Returns:
            DynamicTransitionGraph instance or None if loading failed
        """
        try:
            if not os.path.exists(filename):
                return None

            with open(filename, 'r') as f:
                data = json.load(f)

            graph = cls.from_dict(data)
            logger = logging.getLogger(__name__)
            logger.info(f"Dynamic transition graph loaded from {filename}")
            return graph
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error loading dynamic transition graph: {e}")
            return None
