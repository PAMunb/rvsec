import pytest
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.domain.screen_node import ScreenNode
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


class TestDynamicStateGraph:
    @pytest.fixture
    def graph(self):
        return DynamicStateGraph()

    def test_get_or_create_state_new(self, graph):
        screen_hash = "state1"
        activity = "MainActivity"
        screen_desc = ScreenDescription(activity=activity, items=[], events_by_id={})

        node = graph.get_or_create_state(screen_hash, activity, screen_desc)

        assert isinstance(node, ScreenNode)
        assert node.screen_hash == screen_hash
        assert node.activity == activity
        assert screen_hash in graph.states

    def test_get_or_create_state_existing(self, graph):
        screen_hash = "state1"
        activity = "MainActivity"
        screen_desc = ScreenDescription(activity=activity, items=[], events_by_id={})

        node1 = graph.get_or_create_state(screen_hash, activity, screen_desc)
        node2 = graph.get_or_create_state(screen_hash, activity, screen_desc)

        assert node1 is node2
        assert len(graph.states) == 1

    def test_record_action(self, graph):
        screen_hash = "state1"
        action_sig = ((0, 0), "click")

        # Setup state
        screen_desc = ScreenDescription(activity="Main", items=[], events_by_id={})
        graph.get_or_create_state(screen_hash, "Main", screen_desc)

        # Record action
        graph.record_action(screen_hash, action_sig)

        node = graph.states[screen_hash]
        assert action_sig in node.executed_actions

    def test_record_transition(self, graph):
        origin = "state1"
        dest = "state2"
        action = "click_btn_next"

        # Setup states
        screen_desc = ScreenDescription(activity="Main", items=[], events_by_id={})
        graph.get_or_create_state(origin, "Main", screen_desc)
        graph.get_or_create_state(dest, "Detail", screen_desc)

        # Record transition
        graph.record_transition(origin, dest)

        assert len(graph.transitions) == 1
        assert graph.transitions[0].from_hash == origin
        assert graph.transitions[0].to_hash == dest
        # assert dest in graph.reverse_transitions
        # assert (origin, action) in graph.reverse_transitions[dest]
