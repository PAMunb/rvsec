from typing import List

import networkx as nx

from rvandroid.domain.widget import WidgetEventType
from rvandroid.domain.window import Window


class WindowTransition:
    """
    Represents a transition between windows triggered by a widget event.
    """

    def __init__(
            self,
            widget_id: str,
            transition_type: WidgetEventType,
            method_signature: str
    ):
        self.widget_id = widget_id
        self.event_type = transition_type
        self.method = method_signature

    def to_json(self):
        return {
            "widget_id": self.widget_id,
            "event_type": self.event_type.name,
            "method": self.method
        }

    def __str__(self) -> str:
        return (f"WindowTransition=[widget_id={self.widget_id}, "
                f"event_type={self.event_type}, method={self.method}]")

    def __repr__(self) -> str:
        return self.method


class WindowTransitionGraph:
    """
    Manages the graph of transitions between windows.
    Uses NetworkX for graph representation.
    
    ### Architectural Decisions:
    - Uses NetworkX DiGraph for efficient graph operations and algorithms
    - Maintains window IDs and transitions separately for quick access
    - Provides path-finding capabilities for navigation between windows
    - Maintains references between UI elements and transition events
    
    ### Role in the System:
    - Models the navigation structure of the application
    - Enables analysis of reachability between windows
    - Supports exploration optimization with path finding
    - Integrates with enhanced static analysis for navigation planning
    """

    def __init__(self):
        """Initialize the window transition graph."""
        self.graph = nx.DiGraph()
        self.transitions = []  # List of all transitions
        self.window_ids = set()  # Set of window IDs in the graph

    def add_transition(
            self,
            from_window: Window,
            to_window: Window,
            events: List[WindowTransition]
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
                "method": event.method
            }
            self.transitions.append(transition)

    def get_transitions(self) -> list:
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
            
    def get_window_transitions(self, window_id: str) -> list:
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
        
    def get_path_between_windows(self, source_id: str, target_id: str) -> list:
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
                            "method": event.method
                        } for event in events
                    ]
                }
                for from_window, to_window, events in self.graph.edges(data="events")
            ],
            "windows": list(self.window_ids),
            "transitions_count": len(self.transitions),
            "transitions": self.transitions
        }

    def __str__(self) -> str:
        """
        Get string representation of this graph.
        
        Returns:
            String representation
        """
        return f"WindowTransitionGraph=[windows={len(self.window_ids)}, transitions={len(self.transitions)}]"
