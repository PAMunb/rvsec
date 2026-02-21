import pytest
from unittest.mock import MagicMock
from rv_agent.memory.memory_coordinator import MemoryCoordinator
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


class TestMemoryCoordinator:
    @pytest.fixture
    def coordinator(self):
        dynamic_graph = MagicMock(spec=DynamicStateGraph)
        dynamic_graph.current_trace = []  # Mock list attribute
        short_term = MagicMock()
        long_term = MagicMock()
        ui_coverage = MagicMock(spec=UICoverageTracker)
        agent_memory = MagicMock()

        return MemoryCoordinator(
            dynamic_graph=dynamic_graph,
            short_term_memory=short_term,
            long_term_memory=long_term,
            ui_coverage=ui_coverage,
            agent_memory=agent_memory,
        )

    def test_initialization(self, coordinator):
        assert isinstance(coordinator.dynamic_graph, DynamicStateGraph)
        assert isinstance(coordinator.ui_coverage, UICoverageTracker)
        # assert len(coordinator.short_term_memory) == 0 # short_term_memory is a mock now

    def test_update_memory(self, coordinator):
        screen_desc = ScreenDescription(activity="Main", items=[], events_by_id={})
        screen_hash = "hash1"

        coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="Main",
            screen_description=screen_desc,
            action=None,
            llm_reasoning="reasoning",
            iteration=1,
            recent_action_window=[],
        )

        coordinator.dynamic_graph.get_or_create_state.assert_called()

    def test_record_action(self, coordinator):
        # Setup
        screen_desc = ScreenDescription(activity="Main", items=[], events_by_id={})
        screen_hash = "hash1"

        action = {"action_type": "CLICK", "x": 100, "y": 100}

        coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="Main",
            screen_description=screen_desc,
            action=action,
            llm_reasoning="reasoning",
            iteration=1,
            recent_action_window=[],
        )

        coordinator.short_term.record_iteration.assert_called()

    def test_generate_summaries(self, coordinator):
        # Setup
        action = {"action_type": "CLICK", "x": 100, "y": 100}

        coordinator.generate_summaries(
            action=action,
            current_activity="Main",
            visited_states=["hash1"],
            state_transitions=[],
        )

        coordinator.agent_memory.get_action_history_summary.assert_called()
        coordinator.agent_memory.get_exploration_summary.assert_called()
