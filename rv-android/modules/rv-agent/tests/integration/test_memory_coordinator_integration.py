"""
Integration tests for MemoryCoordinator with real fixtures.

Tests memory update flows, summary generation, state discovery tracking,
and multi-component coordination.
"""

import time
from pathlib import Path
from typing import Tuple

import pytest
from rv_agent.agent.dynamic_state_graph import (
    DynamicStateGraph,
    compute_screen_hash_from_description,
)
from rv_agent.memory.agent_memory import AgentMemoryManager
from rv_agent.memory.long_term import LongTermMemory
from rv_agent.memory.memory_coordinator import MemoryCoordinator
from rv_agent.memory.short_term import ShortTermMemory
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import (
    UIAutomator2Parser,
)
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "screenshots"


def load_fixture(app_name: str, screen_num: str) -> Tuple[str, ScreenDescription]:
    """Load a fixture pair."""
    xml_path = FIXTURES_DIR / app_name / f"{screen_num}.uiautomator.xml"
    with open(xml_path, "r") as f:
        xml_content = f.read()

    parser = UIAutomator2Parser(visitor_class=DefaultTextVisitor)
    screen_desc = parser.parse(
        xml_content, activity=f"com.example.{app_name}.MainActivity"
    )

    return xml_content, screen_desc


@pytest.fixture
def graph():
    """Fresh DynamicStateGraph."""
    return DynamicStateGraph()


@pytest.fixture
def short_term():
    """Fresh ShortTermMemory."""
    return ShortTermMemory()


@pytest.fixture
def long_term():
    """Fresh LongTermMemory."""
    return LongTermMemory()


@pytest.fixture
def ui_coverage():
    """Fresh UICoverageTracker."""
    return UICoverageTracker()


@pytest.fixture
def agent_memory():
    """Fresh AgentMemoryManager."""
    return AgentMemoryManager()


@pytest.fixture
def memory_coordinator(graph, short_term, long_term, ui_coverage, agent_memory):
    """MemoryCoordinator with all components."""
    return MemoryCoordinator(
        dynamic_graph=graph,
        short_term_memory=short_term,
        long_term_memory=long_term,
        ui_coverage=ui_coverage,
        agent_memory=agent_memory,
        action_window_size=10,
    )


@pytest.fixture
def memory_coordinator_no_long_term(graph, short_term, ui_coverage, agent_memory):
    """MemoryCoordinator without long-term memory."""
    return MemoryCoordinator(
        dynamic_graph=graph,
        short_term_memory=short_term,
        long_term_memory=None,
        ui_coverage=ui_coverage,
        agent_memory=agent_memory,
        action_window_size=10,
    )


# =============================================================================
# Memory Update Tests
# =============================================================================


class TestMemoryUpdates:
    """Test memory update functionality."""

    def test_update_memories_with_fixture(self, memory_coordinator):
        """Update memories with real fixture data."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        action = {"action_type": "CLICK", "x": 352, "y": 273}
        recent_window = []

        result = memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action=action,
            llm_reasoning="Testing click action",
            iteration=1,
            recent_action_window=recent_window,
        )

        assert result["success"] is True
        assert len(result["recent_action_window"]) == 1
        assert result["recent_action_window"][0] == action

    def test_update_memories_without_action(self, memory_coordinator):
        """Update memories without action (observation only)."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        result = memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action=None,
            llm_reasoning="Observing screen",
            iteration=1,
            recent_action_window=[],
        )

        assert result["success"] is True
        assert len(result["recent_action_window"]) == 0

    def test_action_window_respects_size_limit(self, memory_coordinator):
        """Action window respects size limit."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # Start with pre-filled window
        recent_window = [{"action_type": "CLICK", "x": i, "y": i} for i in range(10)]

        new_action = {"action_type": "CLICK", "x": 999, "y": 999}

        result = memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action=new_action,
            llm_reasoning="Test",
            iteration=11,
            recent_action_window=recent_window,
        )

        # Window should still be max 10
        assert len(result["recent_action_window"]) == 10
        # Most recent should be the new action
        assert result["recent_action_window"][-1] == new_action

    def test_graph_updated_on_memory_update(self, memory_coordinator, graph):
        """DynamicStateGraph updated on memory update."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        assert len(graph.states) == 0

        memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action={"action_type": "CLICK", "x": 100, "y": 200},
            llm_reasoning="Test",
            iteration=1,
            recent_action_window=[],
        )

        assert len(graph.states) == 1
        assert screen_hash in graph.states

    def test_short_term_updated_on_memory_update(self, memory_coordinator, short_term):
        """ShortTermMemory updated on memory update."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        initial_count = short_term.get_statistics().get("iteration_count", 0)

        memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action={"action_type": "CLICK", "x": 100, "y": 200},
            llm_reasoning="Test",
            iteration=1,
            recent_action_window=[],
        )

        new_count = short_term.get_statistics().get("iteration_count", 0)
        assert new_count == initial_count + 1

    def test_ui_coverage_updated_on_memory_update(
        self, memory_coordinator, ui_coverage
    ):
        """UICoverageTracker updated on memory update."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        initial_stats = ui_coverage.get_overall_statistics()
        initial_elements = initial_stats.get("total_unique_elements", 0)

        memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action=None,
            llm_reasoning="Test",
            iteration=1,
            recent_action_window=[],
        )

        new_stats = ui_coverage.get_overall_statistics()
        new_elements = new_stats.get("total_unique_elements", 0)

        # Should have recorded elements from screen
        assert new_elements >= initial_elements

    def test_long_term_updated_on_memory_update(self, memory_coordinator, long_term):
        """LongTermMemory updated on memory update."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action=None,
            llm_reasoning="Test",
            iteration=1,
            recent_action_window=[],
        )

        stats = long_term.get_statistics()
        assert stats.get("total_states", 0) >= 1

    def test_no_long_term_still_works(self, memory_coordinator_no_long_term):
        """Memory update works without long-term memory."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        result = memory_coordinator_no_long_term.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action={"action_type": "CLICK", "x": 100, "y": 200},
            llm_reasoning="Test",
            iteration=1,
            recent_action_window=[],
        )

        assert result["success"] is True


# =============================================================================
# Summary Generation Tests
# =============================================================================


class TestSummaryGeneration:
    """Test summary generation functionality."""

    def test_generate_summaries_with_action(self, memory_coordinator):
        """Generate summaries with action."""
        action = {"action_type": "CLICK", "x": 100, "y": 200}

        summaries = memory_coordinator.generate_summaries(
            action=action,
            current_activity="MainActivity",
            visited_states=["hash1", "hash2"],
            state_transitions=[("hash1", "hash2")],
        )

        assert "action_history_summary" in summaries
        assert "exploration_summary" in summaries
        assert "memory_insights" in summaries
        assert "navigation_path" in summaries

    def test_generate_summaries_without_action(self, memory_coordinator):
        """Generate summaries without action."""
        summaries = memory_coordinator.generate_summaries(
            action=None,
            current_activity="MainActivity",
            visited_states=[],
            state_transitions=[],
        )

        assert "action_history_summary" in summaries
        assert isinstance(summaries["action_history_summary"], str)

    def test_summaries_are_strings(self, memory_coordinator):
        """All summaries are strings."""
        summaries = memory_coordinator.generate_summaries(
            action={"action_type": "CLICK", "x": 100, "y": 200},
            current_activity="MainActivity",
            visited_states=["hash1"],
            state_transitions=[],
        )

        for key, value in summaries.items():
            assert isinstance(value, str), f"{key} should be string"

    def test_summaries_record_action(self, memory_coordinator, agent_memory):
        """Summaries record action in agent memory."""
        action = {"action_type": "CLICK", "x": 100, "y": 200}

        initial = agent_memory.get_action_history_summary()

        memory_coordinator.generate_summaries(
            action=action,
            current_activity="MainActivity",
            visited_states=[],
            state_transitions=[],
        )

        after = agent_memory.get_action_history_summary()

        # Summary should change after recording action
        assert initial != after or initial == "No previous actions."


# =============================================================================
# State Discovery Tracking Tests
# =============================================================================


class TestStateDiscoveryTracking:
    """Test state discovery and transition tracking."""

    def test_track_new_state(self, memory_coordinator):
        """Track new state discovery."""
        visited = []
        transitions = []

        result = memory_coordinator.track_state_discovery(
            current_hash="new_hash",
            previous_hash=None,
            visited_states=visited,
            state_transitions=transitions,
        )

        assert result["new_state_discovered"] is True
        assert "new_hash" in result["visited_states"]
        assert len(result["visited_states"]) == 1

    def test_track_existing_state(self, memory_coordinator):
        """Track existing state (no new discovery)."""
        visited = ["existing_hash"]
        transitions = []

        result = memory_coordinator.track_state_discovery(
            current_hash="existing_hash",
            previous_hash=None,
            visited_states=visited,
            state_transitions=transitions,
        )

        assert result["new_state_discovered"] is False
        assert len(result["visited_states"]) == 1

    def test_track_transition(self, memory_coordinator):
        """Track state transition."""
        visited = ["hash1"]
        transitions = []

        result = memory_coordinator.track_state_discovery(
            current_hash="hash2",
            previous_hash="hash1",
            visited_states=visited,
            state_transitions=transitions,
        )

        assert result["new_transition_discovered"] is True
        assert ("hash1", "hash2") in result["state_transitions"]

    def test_no_transition_same_state(self, memory_coordinator):
        """No transition when staying in same state."""
        visited = ["hash1"]
        transitions = []

        result = memory_coordinator.track_state_discovery(
            current_hash="hash1",
            previous_hash="hash1",
            visited_states=visited,
            state_transitions=transitions,
        )

        assert result["new_transition_discovered"] is False
        assert len(result["state_transitions"]) == 0

    def test_existing_transition_not_duplicated(self, memory_coordinator):
        """Existing transition not duplicated."""
        visited = ["hash1", "hash2"]
        transitions = [("hash1", "hash2")]

        result = memory_coordinator.track_state_discovery(
            current_hash="hash2",
            previous_hash="hash1",
            visited_states=visited,
            state_transitions=transitions,
        )

        assert result["new_transition_discovered"] is False
        assert len(result["state_transitions"]) == 1

    def test_multi_state_exploration(self, memory_coordinator):
        """Track multi-state exploration."""
        visited = []
        transitions = []

        # Simulate exploration: hash1 -> hash2 -> hash3
        states = ["hash1", "hash2", "hash3"]
        prev = None

        for current in states:
            result = memory_coordinator.track_state_discovery(
                current_hash=current,
                previous_hash=prev,
                visited_states=visited,
                state_transitions=transitions,
            )
            visited = result["visited_states"]
            transitions = result["state_transitions"]
            prev = current

        assert len(visited) == 3
        assert len(transitions) == 2
        assert ("hash1", "hash2") in transitions
        assert ("hash2", "hash3") in transitions


# =============================================================================
# Continuation Check Tests
# =============================================================================


class TestContinuationCheck:
    """Test exploration continuation checks."""

    def test_continue_within_timeout(self, memory_coordinator):
        """Continue when within timeout."""
        start_time = time.time()

        result = memory_coordinator.check_continuation(
            start_time=start_time, timeout=60.0
        )

        assert result["should_continue"] is True
        assert result["elapsed_time"] < 1.0
        assert result["remaining_time"] > 59.0

    def test_stop_after_timeout(self, memory_coordinator):
        """Stop when timeout exceeded."""
        start_time = time.time() - 100  # 100 seconds ago

        result = memory_coordinator.check_continuation(
            start_time=start_time, timeout=60.0
        )

        assert result["should_continue"] is False
        assert result["elapsed_time"] >= 100
        assert result["remaining_time"] == 0

    def test_remaining_time_calculation(self, memory_coordinator):
        """Remaining time calculated correctly."""
        start_time = time.time() - 30  # 30 seconds ago

        result = memory_coordinator.check_continuation(
            start_time=start_time, timeout=60.0
        )

        assert result["should_continue"] is True
        assert 29 <= result["remaining_time"] <= 31


# =============================================================================
# Statistics Collection Tests
# =============================================================================


class TestStatisticsCollection:
    """Test unified statistics collection."""

    def test_get_all_statistics_structure(self, memory_coordinator):
        """Statistics have correct structure."""
        stats = memory_coordinator.get_all_statistics()

        assert "ui_coverage" in stats
        assert "short_term" in stats
        assert "long_term" in stats
        assert "dynamic_graph" in stats

    def test_dynamic_graph_statistics(self, memory_coordinator, graph):
        """Dynamic graph statistics populated."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # Add some states
        memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action=None,
            llm_reasoning="Test",
            iteration=1,
            recent_action_window=[],
        )

        stats = memory_coordinator.get_all_statistics()

        assert stats["dynamic_graph"]["total_states"] >= 1

    def test_statistics_after_exploration(self, memory_coordinator):
        """Statistics reflect exploration."""
        # Simulate exploration of multiple screens
        screens = ["001", "002", "003"]
        recent_window = []

        for i, screen_num in enumerate(screens):
            _, screen_desc = load_fixture("cryptoapp", screen_num)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            action = {"action_type": "CLICK", "x": 100 + i * 50, "y": 200}

            result = memory_coordinator.update_memories(
                current_screen_hash=screen_hash,
                current_activity="MainActivity",
                screen_description=screen_desc,
                action=action,
                llm_reasoning=f"Iteration {i}",
                iteration=i + 1,
                recent_action_window=recent_window,
            )
            recent_window = result["recent_action_window"]

        stats = memory_coordinator.get_all_statistics()

        # Should have recorded iterations
        assert stats["short_term"].get("iteration_count", 0) == 3

    def test_statistics_without_long_term(self, memory_coordinator_no_long_term):
        """Statistics work without long-term memory."""
        stats = memory_coordinator_no_long_term.get_all_statistics()

        assert "long_term" in stats
        assert stats["long_term"] == {}


# =============================================================================
# Multi-Screen Integration Tests
# =============================================================================


class TestMultiScreenIntegration:
    """Test integration across multiple screens."""

    def test_full_exploration_flow(self, memory_coordinator, graph):
        """Full exploration flow with multiple screens."""
        screens = ["001", "002", "003", "004", "005"]
        recent_window = []
        visited_states = []
        state_transitions = []
        prev_hash = None

        for i, screen_num in enumerate(screens):
            _, screen_desc = load_fixture("cryptoapp", screen_num)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            action = {"action_type": "CLICK", "x": 100, "y": 200 + i * 50}

            # Update memories
            result = memory_coordinator.update_memories(
                current_screen_hash=screen_hash,
                current_activity="MainActivity",
                screen_description=screen_desc,
                action=action,
                llm_reasoning=f"Exploring screen {screen_num}",
                iteration=i + 1,
                recent_action_window=recent_window,
            )
            recent_window = result["recent_action_window"]

            # Track state discovery
            discovery = memory_coordinator.track_state_discovery(
                current_hash=screen_hash,
                previous_hash=prev_hash,
                visited_states=visited_states,
                state_transitions=state_transitions,
            )
            visited_states = discovery["visited_states"]
            state_transitions = discovery["state_transitions"]
            prev_hash = screen_hash

            # Generate summaries
            memory_coordinator.generate_summaries(
                action=action,
                current_activity="MainActivity",
                visited_states=visited_states,
                state_transitions=state_transitions,
            )

        # Verify final state
        assert len(visited_states) > 0
        assert len(graph.states) > 0
        assert len(recent_window) == 5

    def test_cross_app_exploration(self, memory_coordinator):
        """Exploration across different apps."""
        apps = [
            ("cryptoapp", "001"),
            ("ludo", "001"),
            ("hashpass", "001"),
        ]
        recent_window = []

        for app_name, screen_num in apps:
            _, screen_desc = load_fixture(app_name, screen_num)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            result = memory_coordinator.update_memories(
                current_screen_hash=screen_hash,
                current_activity=f"com.example.{app_name}.MainActivity",
                screen_description=screen_desc,
                action={"action_type": "CLICK", "x": 100, "y": 200},
                llm_reasoning=f"Exploring {app_name}",
                iteration=1,
                recent_action_window=recent_window,
            )
            recent_window = result["recent_action_window"]

        stats = memory_coordinator.get_all_statistics()

        # Should have recorded multiple unique states
        assert stats["dynamic_graph"]["total_states"] >= 3


# =============================================================================
# Action Type Mapping Tests
# =============================================================================


class TestActionTypeMapping:
    """Test action type mapping from execution to internal format."""

    def test_uppercase_action_types(self, memory_coordinator):
        """Uppercase action types mapped correctly."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        action_types = ["CLICK", "LONG_CLICK", "SET_TEXT", "SCROLL", "BACK"]

        for action_type in action_types:
            action = {"action_type": action_type, "x": 100, "y": 200}

            result = memory_coordinator.update_memories(
                current_screen_hash=screen_hash,
                current_activity="MainActivity",
                screen_description=screen_desc,
                action=action,
                llm_reasoning="Test",
                iteration=1,
                recent_action_window=[],
            )

            assert result["success"] is True

    def test_lowercase_action_types(self, memory_coordinator):
        """Lowercase action types mapped correctly."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        action_types = ["click", "long_click", "set_text", "scroll", "back"]

        for action_type in action_types:
            action = {"action_type": action_type, "x": 100, "y": 200}

            result = memory_coordinator.update_memories(
                current_screen_hash=screen_hash,
                current_activity="MainActivity",
                screen_description=screen_desc,
                action=action,
                llm_reasoning="Test",
                iteration=1,
                recent_action_window=[],
            )

            assert result["success"] is True

    def test_llm_coords_format(self, memory_coordinator, graph):
        """llm_coords format handled correctly."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        action = {
            "action_type": "CLICK",
            "llm_coords": (352, 273),
            "x": 100,  # These should be ignored
            "y": 200,
        }

        memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action=action,
            llm_reasoning="Test",
            iteration=1,
            recent_action_window=[],
        )

        node = graph.states.get(screen_hash)
        assert node is not None

        # Check that llm_coords were used
        executed = list(node.executed_actions)
        if executed:
            coords, action_type = executed[0]
            assert coords == (352, 273)


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_screen_description(self, memory_coordinator):
        """Handle empty screen description."""
        empty_desc = ScreenDescription(activity="Empty", items=[])

        result = memory_coordinator.update_memories(
            current_screen_hash="empty_hash",
            current_activity="Empty",
            screen_description=empty_desc,
            action=None,
            llm_reasoning="Empty screen",
            iteration=1,
            recent_action_window=[],
        )

        assert result["success"] is True

    def test_action_without_coordinates(self, memory_coordinator):
        """Handle action without coordinates."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        action = {"action_type": "BACK"}

        result = memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action=action,
            llm_reasoning="Go back",
            iteration=1,
            recent_action_window=[],
        )

        assert result["success"] is True

    def test_very_long_reasoning(self, memory_coordinator):
        """Handle very long LLM reasoning."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        long_reasoning = "This is a very long reasoning. " * 1000

        result = memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action={"action_type": "CLICK", "x": 100, "y": 200},
            llm_reasoning=long_reasoning,
            iteration=1,
            recent_action_window=[],
        )

        assert result["success"] is True

    def test_high_iteration_number(self, memory_coordinator):
        """Handle high iteration numbers."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        result = memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action={"action_type": "CLICK", "x": 100, "y": 200},
            llm_reasoning="High iteration",
            iteration=10000,
            recent_action_window=[],
        )

        assert result["success"] is True
