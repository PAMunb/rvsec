"""
Window Transition Graph models for Android application navigation analysis.

This module provides validated data models for representing navigation flows
between application windows and their associated UI interaction events.
"""

from typing import Any, Dict, List, Set

import networkx as nx
from pydantic import ConfigDict, Field

from rv_android_core.domain.widget import WidgetEventType
from rv_android_core.domain.window import Window
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model


@validated_model(["widget_id", "event_type", "method"])
class WindowTransition(BaseValidatedModel):
    """
    Validated data model for window navigation transitions triggered by UI events.

    This model represents navigation events between application windows,
    capturing the UI element, interaction type, and associated callback method
    for comprehensive navigation analysis.

    ### Architectural Role:
    - Models individual navigation events between application windows
    - Links UI interactions to specific callback method implementations
    - Provides structured data for navigation graph construction
    - Enables analysis of user interaction flows and reachability

    ### Integration Points:
    - Created during static analysis of window transition patterns
    - Used by WindowTransitionGraph for navigation modeling
    - Consumed by exploration tools for systematic navigation
    - Integrated with coverage analysis for transition coverage metrics
    """

    widget_id: str = Field(
        description="Unique identifier of the UI widget that triggers the transition"
    )
    event_type: WidgetEventType = Field(
        description="Type of user interaction that triggers the navigation"
    )
    method: str = Field(
        description="Complete method signature of the callback that handles the transition"
    )

    @property
    def transition_type(self) -> WidgetEventType:
        """Compatibility property for accessing event_type."""
        return self.event_type

    @property
    def method_signature(self) -> str:
        """Compatibility property for accessing method."""
        return self.method

    def to_json(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "event_type": self.event_type.name,
            "method": self.method,
        }

    def __str__(self) -> str:
        return (
            f"WindowTransition=[widget_id={self.widget_id}, "
            f"event_type={self.event_type}, method={self.method}]"
        )

    def __repr__(self) -> str:
        return self.method


class WindowTransitionGraph(BaseValidatedModel):
    """
    Validated data model for comprehensive window navigation graph analysis.

    This class provides structured representation of application navigation
    flows using NetworkX graph algorithms for efficient path analysis and
    reachability computation.

    ### Architectural Role:
    - Models complete navigation structure of Android applications
    - Provides efficient path-finding algorithms for exploration optimization
    - Enables reachability analysis between application screens
    - Supports systematic navigation planning and coverage analysis

    ### Integration Points:
    - Populated during static analysis of application navigation flows
    - Used by exploration tools for optimal navigation path planning
    - Consumed by coverage analysis for navigation coverage metrics
    - Integrated with monitoring systems for navigation tracking

    ### Performance Optimization:
    Uses NetworkX DiGraph for efficient graph algorithms including shortest
    path computation and reachability analysis essential for exploration.

    ### Validation Strategy:
    Validates structured data (transitions, window_ids) while allowing
    NetworkX graph as arbitrary type for algorithm efficiency.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    transitions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of all window transitions with detailed metadata",
    )
    window_ids: Set[str] = Field(
        default_factory=set,
        description="Set of all window identifiers in the navigation graph",
    )
    graph: nx.DiGraph = Field(
        default_factory=nx.DiGraph,
        exclude=True,
        description="NetworkX directed graph for efficient path algorithms (excluded from serialization)",
    )

    def add_transition(
        self, from_window: Window, to_window: Window, events: List[WindowTransition]
    ) -> None:
        """
        Adds a transition edge between windows with associated events.

        Args:
            from_window: Source window
            to_window: Target window
            events: List of events that trigger the transition
        """
        # Add edge to the graph
        self.graph.add_edge(from_window.id, to_window.id, events=events)

        # Update the set of window IDs
        self.window_ids.add(from_window.id)
        self.window_ids.add(to_window.id)

        # Store transition in the list of transitions
        for event in events:
            transition = {
                "source": from_window.id,
                "target": to_window.id,
                "widget_id": event.widget_id,
                "event_type": event.event_type,
                "method": event.method,
            }
            self.transitions.append(transition)

    def get_transitions(self) -> List[Dict[str, Any]]:
        """
        Get all transitions in the graph.

        Returns:
            List of all transitions
        """
        return self.transitions

    def has_window(self, window_id: str) -> bool:
        """
        Check if a window exists in the graph.

        Args:
            window_id: Window ID to check

        Returns:
            True if window exists, False otherwise
        """
        return window_id in self.window_ids

    def get_paths_from_window(self, source_id: str) -> dict:
        """
        Get shortest paths from a source window to all other windows.

        Args:
            source_id: Source window ID

        Returns:
            Dictionary mapping target window IDs to paths (lists of window IDs)
        """
        # Check if the window exists in the graph
        if not self.has_window(source_id):
            return {}

        # Use Dijkstra's algorithm to calculate shortest paths
        try:
            # Calculate shortest paths to all accessible windows
            # This returns {target_id: [node_list_from_source_to_target]}
            paths = nx.single_source_shortest_path(self.graph, source_id)

            # Make sure each path is a list of strings (window IDs)
            result = {}
            for target_id, path_nodes in paths.items():
                # Ensure all path nodes are strings
                result[target_id] = [str(node) for node in path_nodes]

            return result
        except nx.NetworkXError:
            # In case of error, return an empty dictionary
            return {}

    def get_window_transitions(self, window_id: str) -> List[Dict[str, Any]]:
        """
        Get all transitions originating from a specific window.

        Args:
            window_id: Source window ID

        Returns:
            List of transitions from the specified window
        """
        if not self.has_window(window_id):
            return []

        result = []
        for transition in self.transitions:
            if transition["source"] == window_id:
                result.append(transition)

        return result

    def get_path_between_windows(self, source_id: str, target_id: str) -> List[str]:
        """
        Find the shortest path between two windows.

        Args:
            source_id: Source window ID
            target_id: Target window ID

        Returns:
            List of window IDs representing the path or empty list if no path
        """
        if not self.has_window(source_id) or not self.has_window(target_id):
            return []

        try:
            # Calculate shortest path between source and target
            path = nx.shortest_path(self.graph, source_id, target_id)

            # Ensure all nodes in the path are strings
            return [str(node) for node in path]
        except nx.NetworkXNoPath:
            return []

    def to_json(self):
        """
        Convert graph to JSON format.

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "graph": [
                {
                    "from_window": from_window,
                    "to_window": to_window,
                    "events": [
                        {
                            "widget_id": event.widget_id,
                            "event_type": event.event_type.name,
                            "method": event.method,
                        }
                        for event in events
                    ],
                }
                for from_window, to_window, events in self.graph.edges(data="events")
            ],
            "windows": list(self.window_ids),
            "transitions_count": len(self.transitions),
            "transitions": self.transitions,
        }

    def __str__(self) -> str:
        """
        Get string representation of this graph.

        Returns:
            String representation
        """
        return f"WindowTransitionGraph=[windows={len(self.window_ids)}, transitions={len(self.transitions)}]"
