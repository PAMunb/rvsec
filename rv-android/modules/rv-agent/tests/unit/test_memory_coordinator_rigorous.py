"""
MemoryCoordinator rigorous unit tests.

Tests coordination of all 5 memory systems: DynamicStateGraph, ShortTermMemory,
LongTermMemory, UICoverageTracker, and AgentMemoryManager.
"""

import pytest
import time
from unittest.mock import MagicMock, patch, call

from rv_agent.memory.memory_coordinator import MemoryCoordinator
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.domain.screen_node import ScreenNode
from rv_agent.memory.short_term import ShortTermMemory
from rv_agent.memory.long_term import LongTermMemory
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.memory.agent_memory import AgentMemoryManager
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

pytestmark = pytest.mark.unit


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_graph():
    """Mock DynamicStateGraph."""
    graph = MagicMock(spec=DynamicStateGraph)
    graph.current_trace = []
    graph.states = {}
    graph.transitions = []
    graph.get_or_create_state.return_value = MagicMock(spec=ScreenNode, visit_count=1)
    return graph


@pytest.fixture
def mock_short_term():
    """Mock ShortTermMemory."""
    return MagicMock(spec=ShortTermMemory)


@pytest.fixture
def mock_long_term():
    """Mock LongTermMemory."""
    return MagicMock(spec=LongTermMemory)


@pytest.fixture
def mock_ui_coverage():
    """Mock UICoverageTracker."""
    return MagicMock(spec=UICoverageTracker)


@pytest.fixture
def mock_agent_memory():
    """Mock AgentMemoryManager."""
    memory = MagicMock(spec=AgentMemoryManager)
    memory.get_action_history_summary.return_value = "Action history summary"
    memory.get_exploration_summary.return_value = "Exploration summary"
    memory.get_memory_insights.return_value = "Memory insights"
    memory.get_navigation_path.return_value = "Navigation path"
    return memory


@pytest.fixture
def coordinator(
    mock_graph, mock_short_term, mock_long_term, mock_ui_coverage, mock_agent_memory
):
    """MemoryCoordinator with all mocked dependencies."""
    return MemoryCoordinator(
        dynamic_graph=mock_graph,
        short_term_memory=mock_short_term,
        long_term_memory=mock_long_term,
        ui_coverage=mock_ui_coverage,
        agent_memory=mock_agent_memory,
        action_window_size=10,
    )


@pytest.fixture
def screen_desc():
    """Screen description with items."""
    item = MagicMock()
    item.view = {"resource_id": "btn_ok", "class": "android.widget.Button"}

    desc = MagicMock(spec=ScreenDescription)
    desc.items = [item]
    return desc


# =============================================================================
# Initialization Tests
# =============================================================================


class TestMemoryCoordinatorInit:
    """Test MemoryCoordinator initialization."""

    def test_initialization(self, coordinator):
        """Coordinator initializes with all memory systems."""
        assert coordinator.dynamic_graph is not None
        assert coordinator.short_term is not None
        assert coordinator.long_term is not None
        assert coordinator.ui_coverage is not None
        assert coordinator.agent_memory is not None
        assert coordinator.action_window_size == 10

    def test_initialization_without_long_term(
        self, mock_graph, mock_short_term, mock_ui_coverage, mock_agent_memory
    ):
        """Coordinator works without LongTermMemory."""
        coordinator = MemoryCoordinator(
            dynamic_graph=mock_graph,
            short_term_memory=mock_short_term,
            long_term_memory=None,  # No long-term memory
            ui_coverage=mock_ui_coverage,
            agent_memory=mock_agent_memory,
        )

        assert coordinator.long_term is None


# =============================================================================
# Update Memories Tests
# =============================================================================


class TestUpdateMemories:
    """Test update_memories method."""

    def test_update_memories_basic(self, coordinator, screen_desc):
        """update_memories calls all memory systems."""
        result = coordinator.update_memories(
            current_screen_hash="hash123",
            current_activity="MainActivity",
            screen_description=screen_desc,
            action=None,
            llm_reasoning="Test reasoning",
            iteration=1,
            recent_action_window=[],
        )

        assert result["success"] is True
        coordinator.dynamic_graph.get_or_create_state.assert_called_once()
        coordinator.short_term.record_iteration.assert_called_once()

    def test_update_memories_with_action(self, coordinator, screen_desc):
        """update_memories records action in graph."""
        action = {"action_type": "CLICK", "x": 100, "y": 200, "id": "action_1"}

        coordinator.update_memories(
            current_screen_hash="hash123",
            current_activity="Main",
            screen_description=screen_desc,
            action=action,
            llm_reasoning="Click OK",
            iteration=1,
            recent_action_window=[],
        )

        coordinator.dynamic_graph.record_action_to_trace.assert_called()
        coordinator.dynamic_graph.record_action.assert_called()

    def test_update_memories_action_window(self, coordinator, screen_desc):
        """update_memories maintains action window."""
        action = {"action_type": "CLICK", "x": 100, "y": 200}

        result = coordinator.update_memories(
            current_screen_hash="hash123",
            current_activity="Main",
            screen_description=screen_desc,
            action=action,
            llm_reasoning="Test",
            iteration=1,
            recent_action_window=[],
        )

        assert len(result["recent_action_window"]) == 1
        assert result["recent_action_window"][0] == action

    def test_update_memories_action_window_limit(self, coordinator, screen_desc):
        """update_memories limits action window size."""
        coordinator.action_window_size = 3

        existing_window = [{"action_type": "CLICK", "x": i, "y": i} for i in range(3)]
        new_action = {"action_type": "SCROLL", "direction": "down"}

        result = coordinator.update_memories(
            current_screen_hash="hash123",
            current_activity="Main",
            screen_description=screen_desc,
            action=new_action,
            llm_reasoning="Test",
            iteration=4,
            recent_action_window=existing_window,
        )

        # Window should be limited to 3
        assert len(result["recent_action_window"]) == 3
        # Most recent should be last
        assert result["recent_action_window"][-1] == new_action

    def test_update_memories_with_llm_coords(self, coordinator, screen_desc):
        """update_memories handles llm_coords format."""
        action = {"action_type": "click", "llm_coords": (352, 624), "id": "action_1"}

        coordinator.update_memories(
            current_screen_hash="hash123",
            current_activity="Main",
            screen_description=screen_desc,
            action=action,
            llm_reasoning="Click",
            iteration=1,
            recent_action_window=[],
        )

        # Should use llm_coords for action signature
        coordinator.dynamic_graph.record_action.assert_called_once()
        call_args = coordinator.dynamic_graph.record_action.call_args
        assert call_args[1]["action_signature"][0] == (352, 624)

    def test_update_memories_action_type_mapping(self, coordinator, screen_desc):
        """update_memories maps action types correctly."""
        test_cases = [
            ("CLICK", "click"),
            ("LONG_CLICK", "long_click"),
            ("SET_TEXT", "set_text"),
            ("SCROLL", "scroll"),
            ("BACK", "key_event"),
            ("click", "click"),  # Lowercase preserved
        ]

        for raw_type, expected_type in test_cases:
            coordinator.dynamic_graph.record_action.reset_mock()

            action = {"action_type": raw_type, "x": 100, "y": 200}
            coordinator.update_memories(
                current_screen_hash="hash123",
                current_activity="Main",
                screen_description=screen_desc,
                action=action,
                llm_reasoning="Test",
                iteration=1,
                recent_action_window=[],
            )

            call_args = coordinator.dynamic_graph.record_action.call_args
            assert (
                call_args[1]["action_signature"][1] == expected_type
            ), f"Expected {expected_type} for {raw_type}"

    def test_update_memories_ui_coverage_per_element(self, coordinator, screen_desc):
        """update_memories no longer records UI coverage per element (moved to execute_node/parse_node)."""
        # Add more items
        for i in range(3):
            item = MagicMock()
            item.view = {"resource_id": f"element_{i}", "class": "Button"}
            screen_desc.items.append(item)

        coordinator.update_memories(
            current_screen_hash="hash123",
            current_activity="Main",
            screen_description=screen_desc,
            action=None,
            llm_reasoning="Test",
            iteration=1,
            recent_action_window=[],
        )

        # record_interaction is no longer called from MemoryCoordinator
        # (visibility tracked via parse_node, interactions via execute_node)
        coordinator.ui_coverage.record_interaction.assert_not_called()

    def test_update_memories_long_term_optional(
        self,
        mock_graph,
        mock_short_term,
        mock_ui_coverage,
        mock_agent_memory,
        screen_desc,
    ):
        """update_memories works when long_term is None."""
        coordinator = MemoryCoordinator(
            dynamic_graph=mock_graph,
            short_term_memory=mock_short_term,
            long_term_memory=None,
            ui_coverage=mock_ui_coverage,
            agent_memory=mock_agent_memory,
        )

        result = coordinator.update_memories(
            current_screen_hash="hash123",
            current_activity="Main",
            screen_description=screen_desc,
            action=None,
            llm_reasoning="Test",
            iteration=1,
            recent_action_window=[],
        )

        assert result["success"] is True


# =============================================================================
# Generate Summaries Tests
# =============================================================================


class TestGenerateSummaries:
    """Test generate_summaries method."""

    def test_generate_summaries_basic(self, coordinator):
        """generate_summaries returns all summary types."""
        summaries = coordinator.generate_summaries(
            action=None,
            current_activity="MainActivity",
            visited_states=["hash1"],
            state_transitions=[],
        )

        assert "action_history_summary" in summaries
        assert "exploration_summary" in summaries
        assert "memory_insights" in summaries
        assert "navigation_path" in summaries

    def test_generate_summaries_with_action(self, coordinator):
        """generate_summaries records action in agent memory."""
        action = {"action_type": "CLICK", "x": 100, "y": 200}

        coordinator.generate_summaries(
            action=action,
            current_activity="MainActivity",
            visited_states=["hash1"],
            state_transitions=[],
        )

        coordinator.agent_memory.record_action.assert_called_once()

    def test_generate_summaries_calls_all_generators(self, coordinator):
        """generate_summaries calls all summary generators."""
        coordinator.generate_summaries(
            action={"action_type": "CLICK"},
            current_activity="Main",
            visited_states=["hash1", "hash2"],
            state_transitions=[("hash1", "hash2")],
        )

        coordinator.agent_memory.get_action_history_summary.assert_called_once()
        coordinator.agent_memory.get_exploration_summary.assert_called_once_with(
            visited_states=["hash1", "hash2"], state_transitions=[("hash1", "hash2")]
        )
        coordinator.agent_memory.get_memory_insights.assert_called_once_with("Main")
        coordinator.agent_memory.get_navigation_path.assert_called_once()

    def test_generate_summaries_error_handling(self, coordinator):
        """generate_summaries returns fallback on error."""
        coordinator.agent_memory.get_action_history_summary.side_effect = Exception(
            "Test error"
        )

        summaries = coordinator.generate_summaries(
            action=None,
            current_activity="Main",
            visited_states=[],
            state_transitions=[],
        )

        # Should return fallback summaries
        assert "No previous actions" in summaries["action_history_summary"]


# =============================================================================
# Track State Discovery Tests
# =============================================================================


class TestTrackStateDiscovery:
    """Test track_state_discovery method."""

    def test_track_new_state(self, coordinator):
        """track_state_discovery detects new states."""
        result = coordinator.track_state_discovery(
            current_hash="hash_new",
            previous_hash=None,
            visited_states=[],
            state_transitions=[],
        )

        assert result["new_state_discovered"] is True
        assert "hash_new" in result["visited_states"]

    def test_track_existing_state(self, coordinator):
        """track_state_discovery ignores existing states."""
        result = coordinator.track_state_discovery(
            current_hash="hash_existing",
            previous_hash=None,
            visited_states=["hash_existing"],
            state_transitions=[],
        )

        assert result["new_state_discovered"] is False
        assert len(result["visited_states"]) == 1

    def test_track_new_transition(self, coordinator):
        """track_state_discovery records new transitions."""
        result = coordinator.track_state_discovery(
            current_hash="hash2",
            previous_hash="hash1",
            visited_states=["hash1", "hash2"],
            state_transitions=[],
        )

        assert result["new_transition_discovered"] is True
        assert ("hash1", "hash2") in result["state_transitions"]

    def test_track_existing_transition(self, coordinator):
        """track_state_discovery ignores existing transitions."""
        result = coordinator.track_state_discovery(
            current_hash="hash2",
            previous_hash="hash1",
            visited_states=["hash1", "hash2"],
            state_transitions=[("hash1", "hash2")],
        )

        assert result["new_transition_discovered"] is False
        assert len(result["state_transitions"]) == 1

    def test_track_no_transition_same_state(self, coordinator):
        """track_state_discovery ignores self-transitions."""
        result = coordinator.track_state_discovery(
            current_hash="hash1",
            previous_hash="hash1",  # Same state
            visited_states=["hash1"],
            state_transitions=[],
        )

        assert result["new_transition_discovered"] is False
        assert len(result["state_transitions"]) == 0


# =============================================================================
# Check Continuation Tests
# =============================================================================


class TestCheckContinuation:
    """Test check_continuation method."""

    def test_check_continuation_should_continue(self, coordinator):
        """check_continuation returns True when time remaining."""
        start_time = time.time()

        result = coordinator.check_continuation(
            start_time=start_time, timeout=180.0  # 3 minutes
        )

        assert result["should_continue"] is True
        assert result["elapsed_time"] < 1.0
        assert result["remaining_time"] > 179.0

    def test_check_continuation_should_stop(self, coordinator):
        """check_continuation returns False when timeout exceeded."""
        start_time = time.time() - 200  # 200 seconds ago

        result = coordinator.check_continuation(
            start_time=start_time, timeout=180.0  # 3 minutes
        )

        assert result["should_continue"] is False
        assert result["elapsed_time"] >= 180.0
        assert result["remaining_time"] == 0


# =============================================================================
# Get All Statistics Tests
# =============================================================================


class TestGetAllStatistics:
    """Test get_all_statistics method."""

    def test_get_all_statistics(self, coordinator):
        """get_all_statistics returns complete structure."""
        coordinator.ui_coverage.get_overall_statistics.return_value = {
            "total_unique_elements": 10
        }
        coordinator.short_term.get_statistics.return_value = {"iteration_count": 5}
        coordinator.long_term.get_statistics.return_value = {"total_states": 3}
        coordinator.dynamic_graph.states = {"h1": MagicMock(), "h2": MagicMock()}
        coordinator.dynamic_graph.transitions = [MagicMock()]

        stats = coordinator.get_all_statistics()

        assert "ui_coverage" in stats
        assert "short_term" in stats
        assert "long_term" in stats
        assert "dynamic_graph" in stats
        assert stats["dynamic_graph"]["total_states"] == 2
        assert stats["dynamic_graph"]["total_transitions"] == 1

    def test_get_all_statistics_without_long_term(
        self, mock_graph, mock_short_term, mock_ui_coverage, mock_agent_memory
    ):
        """get_all_statistics works without long_term."""
        coordinator = MemoryCoordinator(
            dynamic_graph=mock_graph,
            short_term_memory=mock_short_term,
            long_term_memory=None,
            ui_coverage=mock_ui_coverage,
            agent_memory=mock_agent_memory,
        )

        mock_ui_coverage.get_overall_statistics.return_value = {}
        mock_short_term.get_statistics.return_value = {}

        stats = coordinator.get_all_statistics()

        assert stats["long_term"] == {}

    def test_get_all_statistics_error_handling(self, coordinator):
        """get_all_statistics handles errors gracefully."""
        coordinator.ui_coverage.get_overall_statistics.side_effect = Exception("Test")

        stats = coordinator.get_all_statistics()

        # Should return empty structure
        assert stats["ui_coverage"] == {}
        assert stats["dynamic_graph"]["total_states"] == 0


# =============================================================================
# Integration with Real Components Tests
# =============================================================================


class TestIntegrationRealComponents:
    """Test MemoryCoordinator with real (non-mocked) components."""

    def test_with_real_graph(self):
        """Test with real DynamicStateGraph."""
        graph = DynamicStateGraph()
        coordinator = MemoryCoordinator(
            dynamic_graph=graph,
            short_term_memory=MagicMock(),
            long_term_memory=None,
            ui_coverage=MagicMock(),
            agent_memory=MagicMock(),
        )

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.get_all_actions.return_value = []

        coordinator.update_memories(
            current_screen_hash="real_hash",
            current_activity="RealActivity",
            screen_description=screen_desc,
            action=None,
            llm_reasoning="Test",
            iteration=1,
            recent_action_window=[],
        )

        assert "real_hash" in graph.states
        assert graph.states["real_hash"].activity == "RealActivity"

    def test_with_real_agent_memory(self):
        """Test with real AgentMemoryManager."""
        agent_memory = AgentMemoryManager(max_action_history=3)
        coordinator = MemoryCoordinator(
            dynamic_graph=MagicMock(),
            short_term_memory=MagicMock(),
            long_term_memory=None,
            ui_coverage=MagicMock(),
            agent_memory=agent_memory,
        )
        coordinator.dynamic_graph.current_trace = []

        action = {"action_type": "CLICK", "explanation": "Test click"}

        coordinator.generate_summaries(
            action=action,
            current_activity="TestActivity",
            visited_states=["h1"],
            state_transitions=[],
        )

        # Agent memory should have recorded the action
        assert len(agent_memory.action_history) == 1
        assert "TestActivity" in agent_memory.activity_visits
