from typing import List

import networkx as nx

from rvandroid.model.widget import WidgetEventType
from rvandroid.model.window import Window


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
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_transition(
            self,
            from_window: Window,
            to_window: Window,
            events: List[WindowTransition]
    ) -> None:
        """Adds a transition edge between windows with associated events."""
        self.graph.add_edge(from_window, to_window, events=events)

    def to_json(self):
        return {
            "graph": [
                {
                    "from_window": from_window.name,
                    "to_window": to_window.name,
                    "events": [event.to_json() for event in events]
                }
                for from_window, to_window, events in self.graph.edges(data="events")
            ]
        }

    def __str__(self) -> str:
        return f"WindowTransitionGraph=[graph={self.graph.edges(data=True)}]"
