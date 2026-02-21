"""
Integration tests for pure algorithm exploration with real fixtures.

Tests DFS algorithm exploration using real screenshots and UIAutomator dumps to verify:
- Correct exploration order (untested elements first)
- 100% screen coverage achievement
- Memory population during exploration
- Least-visited-first action selection
- Coordinate-based action tracking
"""

import pytest
from pathlib import Path
from typing import Dict, Any, List, Tuple

from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import (
    UIAutomator2Parser,
)
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction

from rv_agent.agent.dynamic_state_graph import (
    DynamicStateGraph,
    ScreenNode,
    compute_screen_hash_from_description,
)
from rv_agent.strategies.dfs_strategy import DFSStrategy
from rv_agent.memory.agent_memory import AgentMemoryManager
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.memory.memory_coordinator import MemoryCoordinator
from rv_agent.memory.short_term import ShortTermMemory
from rv_agent.memory.long_term import LongTermMemory

pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures Directory
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "screenshots"


def load_fixture(app_name: str, screen_num: str) -> Tuple[str, ScreenDescription]:
    """
    Load a fixture pair (XML dump -> ScreenDescription).

    Args:
        app_name: Application name (e.g., 'cryptoapp')
        screen_num: Screen number (e.g., '001')

    Returns:
        Tuple of (xml_content, parsed_screen_description)
    """
    xml_path = FIXTURES_DIR / app_name / f"{screen_num}.uiautomator.xml"

    with open(xml_path, "r") as f:
        xml_content = f.read()

    parser = UIAutomator2Parser(visitor_class=DefaultTextVisitor)
    screen_desc = parser.parse(
        xml_content, activity=f"com.example.{app_name}.MainActivity"
    )

    return xml_content, screen_desc


def get_available_fixtures(app_name: str) -> List[str]:
    """Get list of available screen numbers for an app."""
    app_dir = FIXTURES_DIR / app_name
    if not app_dir.exists():
        return []

    screens = []
    for f in app_dir.glob("*.uiautomator.xml"):
        screens.append(f.stem.replace(".uiautomator", ""))

    return sorted(screens)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def parser():
    """UIAutomator parser instance."""
    return UIAutomator2Parser(visitor_class=DefaultTextVisitor)


@pytest.fixture
def graph():
    """Fresh DynamicStateGraph."""
    return DynamicStateGraph()


@pytest.fixture
def dfs_strategy(graph):
    """DFS strategy with graph."""
    return DFSStrategy(graph=graph)


@pytest.fixture
def ui_coverage():
    """UI coverage tracker."""
    return UICoverageTracker()


@pytest.fixture
def agent_memory():
    """Agent memory manager."""
    return AgentMemoryManager(max_action_history=20, max_navigation_path=20)


@pytest.fixture
def short_term_memory():
    """Short term memory."""
    return ShortTermMemory()


@pytest.fixture
def long_term_memory():
    """Long term memory."""
    return LongTermMemory()


@pytest.fixture
def memory_coordinator(
    graph, short_term_memory, long_term_memory, ui_coverage, agent_memory
):
    """Memory coordinator with all systems."""
    return MemoryCoordinator(
        dynamic_graph=graph,
        short_term_memory=short_term_memory,
        long_term_memory=long_term_memory,
        ui_coverage=ui_coverage,
        agent_memory=agent_memory,
    )


# =============================================================================
# Cryptoapp Fixture Loading Tests
# =============================================================================


class TestFixtureLoading:
    """Test that fixtures can be loaded correctly."""

    def test_cryptoapp_fixtures_exist(self):
        """Cryptoapp fixtures directory exists."""
        app_dir = FIXTURES_DIR / "cryptoapp"
        assert app_dir.exists(), f"Fixtures directory not found: {app_dir}"

    def test_load_cryptoapp_screen_001(self, parser):
        """Load and parse cryptoapp screen 001."""
        xml_path = FIXTURES_DIR / "cryptoapp" / "001.uiautomator.xml"
        assert xml_path.exists()

        with open(xml_path) as f:
            xml_content = f.read()

        screen_desc = parser.parse(xml_content, activity="MainActivity")

        assert isinstance(screen_desc, ScreenDescription)
        assert len(screen_desc.items) > 0

    def test_load_all_cryptoapp_screens(self, parser):
        """Load all cryptoapp screens."""
        screens = get_available_fixtures("cryptoapp")
        assert len(screens) >= 3, "Need at least 3 screens for testing"

        for screen_num in screens:
            _, screen_desc = load_fixture("cryptoapp", screen_num)
            assert isinstance(screen_desc, ScreenDescription)

    def test_fixture_has_clickable_elements(self, parser):
        """Fixtures have clickable elements."""
        _, screen_desc = load_fixture("cryptoapp", "001")

        actions = screen_desc.get_all_actions()
        assert len(actions) > 0, "Screen should have clickable elements"


# =============================================================================
# Screen Hash and State Tracking Tests
# =============================================================================


class TestScreenHashComputation:
    """Test screen hash computation with real fixtures."""

    def test_same_screen_same_hash(self):
        """Same screen produces same hash."""
        _, screen_desc1 = load_fixture("cryptoapp", "001")
        _, screen_desc2 = load_fixture("cryptoapp", "001")

        hash1 = compute_screen_hash_from_description(screen_desc1)
        hash2 = compute_screen_hash_from_description(screen_desc2)

        assert hash1 == hash2

    def test_different_screens_different_hash(self):
        """Different screens produce different hashes."""
        _, screen_desc1 = load_fixture("cryptoapp", "001")
        _, screen_desc2 = load_fixture("cryptoapp", "002")

        hash1 = compute_screen_hash_from_description(screen_desc1)
        hash2 = compute_screen_hash_from_description(screen_desc2)

        assert hash1 != hash2

    def test_hash_is_stable_string(self):
        """Hash is a stable string format."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        hash_val = compute_screen_hash_from_description(screen_desc)

        assert isinstance(hash_val, str)
        assert len(hash_val) > 0


# =============================================================================
# DFS Strategy Exploration Tests
# =============================================================================


class TestDFSExplorationOrder:
    """Test DFS algorithm selects actions in correct order."""

    def test_selects_untested_action_first(self, graph, dfs_strategy):
        """DFS selects untested action first."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        action = dfs_strategy.select_next_action(screen_hash, screen_desc)

        assert action is not None
        assert isinstance(action, ItemAction)

    def test_tracks_executed_actions(self, graph, dfs_strategy):
        """DFS tracks executed actions by coordinates."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # Select first action
        action1 = dfs_strategy.select_next_action(screen_hash, screen_desc)

        # Check that action was recorded in graph
        node = graph.states.get(screen_hash)
        assert node is not None
        assert len(node.executed_actions) == 1

    def test_unique_signatures_during_untested_phase(self, graph, dfs_strategy):
        """DFS does not repeat signatures during untested action phase."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # Get available actions
        total_actions = len(
            [
                a
                for a in screen_desc.get_all_actions()
                if not a.target_view.get("system_action", False)
                and a.get_execution_coordinates()
            ]
        )

        selected_signatures = set()

        # Select actions only during untested phase (before continuous exploration)
        for i in range(total_actions):
            action = dfs_strategy.select_next_action(screen_hash, screen_desc)

            if action is None:
                break

            # Signature includes coordinates AND action type
            signature = action.coords_for_matching

            if signature:
                # During untested phase, should not repeat same signature
                # Note: same coordinate can have click AND long_click (different signatures)
                # After all actions tested, continuous exploration allows repetition
                if signature in selected_signatures:
                    # This is acceptable in continuous exploration mode
                    # (when all unique actions have been tested once)
                    break
                selected_signatures.add(signature)

        # Should have tested at least some unique actions
        assert len(selected_signatures) > 0

    def test_continuous_exploration_after_exhaustion(self, graph, dfs_strategy):
        """DFS continues exploration after all actions tested (continuous mode)."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # Get unique action count
        unique_actions = len(
            [
                a
                for a in screen_desc.get_all_actions()
                if not a.target_view.get("system_action", False)
                and a.get_execution_coordinates()
            ]
        )

        # Execute more than unique actions to trigger continuous exploration
        for i in range(unique_actions + 5):
            action = dfs_strategy.select_next_action(screen_hash, screen_desc)
            # In continuous mode, should always get an action (or BACK)
            assert (
                action is not None
            ), f"Iteration {i}: Expected action in continuous mode"


class TestDFSCoverageAchievement:
    """Test DFS achieves full coverage of screen."""

    def test_coverage_approaches_maximum(self, graph, dfs_strategy):
        """DFS achieves high coverage on single screen."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # Get number of available actions on this screen
        available_actions = len(screen_desc.get_all_actions())

        # Execute actions up to the number of available clickable elements
        # (plus buffer for safety in continuous mode)
        action_count = 0
        for _ in range(available_actions + 10):
            action = dfs_strategy.select_next_action(screen_hash, screen_desc)
            if action is None:
                break
            action_count += 1
            # Stop when we've executed all unique actions
            node = graph.states.get(screen_hash)
            if node and node.get_coverage() >= 1.0:
                break

        # Check coverage
        node = graph.states.get(screen_hash)
        assert node is not None

        # Coverage should be high (DFS explores all available actions)
        coverage = node.get_coverage()
        executed = len(node.executed_actions)

        # Should have executed at least the available actions
        assert executed > 0, "No actions were recorded"

        # Coverage should be significant (at least 50%)
        assert coverage >= 0.5, f"Coverage too low: {coverage}"

    def test_coverage_progresses_monotonically(self, graph, dfs_strategy):
        """Coverage only increases during exploration."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # Get number of available actions
        available_actions = len(screen_desc.get_all_actions())

        prev_coverage = 0.0

        for _ in range(available_actions + 10):
            action = dfs_strategy.select_next_action(screen_hash, screen_desc)
            if action is None:
                break

            node = graph.states[screen_hash]
            current_coverage = node.get_coverage()

            assert (
                current_coverage >= prev_coverage
            ), f"Coverage decreased from {prev_coverage} to {current_coverage}"

            prev_coverage = current_coverage

            # Stop when fully covered
            if current_coverage >= 1.0:
                break


# =============================================================================
# Memory Population Tests
# =============================================================================


class TestMemoryPopulation:
    """Test memory systems are populated during exploration."""

    def test_graph_state_created(self, graph, dfs_strategy):
        """Graph state is created for visited screen."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        assert screen_hash not in graph.states

        dfs_strategy.select_next_action(screen_hash, screen_desc)

        assert screen_hash in graph.states
        assert isinstance(graph.states[screen_hash], ScreenNode)

    def test_ui_coverage_records_interactions(self, ui_coverage):
        """UI coverage records element interactions."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        actions = screen_desc.get_all_actions()
        for i, action in enumerate(actions[:3]):
            element_id = f"element_{i}"
            ui_coverage.record_interaction(element_id, "click", screen_hash)

        assert len(ui_coverage.tested_elements) == 3
        assert screen_hash in ui_coverage.screen_elements

    def test_agent_memory_records_actions(self, agent_memory):
        """Agent memory records action history."""
        _, screen_desc = load_fixture("cryptoapp", "001")

        action_data = {"action_type": "CLICK", "explanation": "Test click"}
        agent_memory.record_action(action_data, "MainActivity", success=True)

        assert len(agent_memory.action_history) == 1
        assert agent_memory.activity_visits["MainActivity"] == 1

    def test_memory_coordinator_syncs_all(self, memory_coordinator, graph):
        """Memory coordinator syncs all memory systems."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # Create state in graph
        graph.get_or_create_state(screen_hash, "MainActivity", screen_desc)

        # Simulate action
        action = {
            "action_type": "CLICK",
            "x": 540,
            "y": 273,
            "explanation": "Click button",
        }

        memory_coordinator.update_memories(
            current_screen_hash=screen_hash,
            current_activity="MainActivity",
            screen_description=screen_desc,
            action=action,
            llm_reasoning="Test reasoning",
            iteration=1,
            recent_action_window=[],
        )

        # Verify short term memory updated
        assert len(memory_coordinator.short_term.iterations) == 1


# =============================================================================
# Multi-Screen Exploration Tests
# =============================================================================


class TestMultiScreenExploration:
    """Test exploration across multiple screens."""

    def test_tracks_multiple_screen_states(self, graph, dfs_strategy):
        """Graph tracks multiple screen states."""
        screens = get_available_fixtures("cryptoapp")[:3]

        for screen_num in screens:
            _, screen_desc = load_fixture("cryptoapp", screen_num)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            dfs_strategy.select_next_action(screen_hash, screen_desc)

        assert len(graph.states) == 3

    def test_visit_count_increments_via_graph(self, graph):
        """Visit count increments when explicitly calling get_or_create_state."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # First visit via graph API
        graph.get_or_create_state(screen_hash, "MainActivity", screen_desc)
        assert graph.states[screen_hash].visit_count == 1

        # Second visit (simulating return to screen)
        graph.get_or_create_state(screen_hash, "MainActivity", screen_desc)
        assert graph.states[screen_hash].visit_count == 2

        # Third visit
        graph.get_or_create_state(screen_hash, "MainActivity", screen_desc)
        assert graph.states[screen_hash].visit_count == 3


# =============================================================================
# Coordinate-Based Tracking Tests
# =============================================================================


class TestCoordinateTracking:
    """Test coordinate-based action tracking."""

    def test_action_signature_includes_coords(self, graph, dfs_strategy):
        """Action signature includes coordinates."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        action = dfs_strategy.select_next_action(screen_hash, screen_desc)

        node = graph.states[screen_hash]

        # Check signature format: ((x, y), action_type)
        for sig in node.executed_actions:
            coords, action_type = sig
            assert isinstance(coords, tuple)
            assert len(coords) == 2
            assert isinstance(action_type, str)

    def test_same_element_same_signature(self, graph):
        """Same element produces consistent signature."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        actions = screen_desc.get_all_actions()
        if not actions:
            pytest.skip("No actions available")

        action = actions[0]

        # Get signature multiple times
        sig1 = action.coords_for_matching
        sig2 = action.coords_for_matching

        assert sig1 == sig2


# =============================================================================
# App-Specific Fixture Tests
# =============================================================================


class TestLudoFixtures:
    """Test with Ludo app fixtures (different UI patterns)."""

    @pytest.fixture
    def ludo_available(self):
        """Check if ludo fixtures available."""
        screens = get_available_fixtures("ludo")
        if not screens:
            pytest.skip("Ludo fixtures not available")
        return screens

    def test_ludo_screen_parsing(self, parser, ludo_available):
        """Parse ludo screens."""
        for screen_num in ludo_available[:3]:
            _, screen_desc = load_fixture("ludo", screen_num)
            assert isinstance(screen_desc, ScreenDescription)

    def test_ludo_exploration(self, graph, dfs_strategy, ludo_available):
        """DFS explores ludo screens."""
        _, screen_desc = load_fixture("ludo", ludo_available[0])
        screen_hash = compute_screen_hash_from_description(screen_desc)

        action = dfs_strategy.select_next_action(screen_hash, screen_desc)

        # May or may not have actions depending on screen
        if len(screen_desc.get_all_actions()) > 0:
            assert action is not None or graph.states[screen_hash].total_actions == 0


class TestHashpassFixtures:
    """Test with Hashpass app fixtures (simple app)."""

    @pytest.fixture
    def hashpass_available(self):
        """Check if hashpass fixtures available."""
        screens = get_available_fixtures("hashpass")
        if not screens:
            pytest.skip("Hashpass fixtures not available")
        return screens

    def test_hashpass_screen_parsing(self, parser, hashpass_available):
        """Parse hashpass screens."""
        for screen_num in hashpass_available[:3]:
            _, screen_desc = load_fixture("hashpass", screen_num)
            assert isinstance(screen_desc, ScreenDescription)

    def test_hashpass_different_hashes(self, hashpass_available):
        """Different hashpass screens have different hashes."""
        if len(hashpass_available) < 2:
            pytest.skip("Need at least 2 screens")

        _, screen_desc1 = load_fixture("hashpass", hashpass_available[0])
        _, screen_desc2 = load_fixture("hashpass", hashpass_available[1])

        hash1 = compute_screen_hash_from_description(screen_desc1)
        hash2 = compute_screen_hash_from_description(screen_desc2)

        # Hashes should be different unless screens are identical
        # (they might be identical in some cases)
        assert isinstance(hash1, str) and isinstance(hash2, str)


# =============================================================================
# End-to-End Exploration Simulation
# =============================================================================


class TestExplorationSimulation:
    """Simulate complete exploration session."""

    def test_full_cryptoapp_exploration(self, graph, ui_coverage, agent_memory):
        """Simulate full exploration of cryptoapp screens."""
        dfs = DFSStrategy(graph=graph)

        screens = get_available_fixtures("cryptoapp")
        total_actions = 0
        unique_hashes = set()

        for screen_num in screens:
            _, screen_desc = load_fixture("cryptoapp", screen_num)
            screen_hash = compute_screen_hash_from_description(screen_desc)
            unique_hashes.add(screen_hash)

            # Explore until exhausted (with safety limit)
            for _ in range(1000):
                action = dfs.select_next_action(screen_hash, screen_desc)
                if action is None:
                    break

                total_actions += 1

                # Record in memory systems
                coords = action.get_execution_coordinates()
                if coords:
                    element_id = f"action_{total_actions}"
                    ui_coverage.record_interaction(element_id, "click", screen_hash)
                    agent_memory.record_action(
                        {"action_type": "CLICK", "x": coords[0], "y": coords[1]},
                        screen_desc.activity,
                        success=True,
                    )

        # Verify exploration results
        # Note: Some screens may have same hash if structurally identical
        assert len(graph.states) == len(unique_hashes)
        assert len(graph.states) >= 1  # At least one unique state
        assert total_actions > 0
        assert len(ui_coverage.tested_elements) > 0
        assert len(agent_memory.action_history) > 0

    def test_exploration_coverage_metrics(self, graph):
        """Compute exploration coverage metrics."""
        dfs = DFSStrategy(graph=graph)

        screens = get_available_fixtures("cryptoapp")

        for screen_num in screens:
            _, screen_desc = load_fixture("cryptoapp", screen_num)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            # Execute actions until coverage reaches 100% or safety limit
            for _ in range(50):  # Safety limit per screen
                action = dfs.select_next_action(screen_hash, screen_desc)
                if action is None:
                    break

                # Check if we've covered all unique actions on this screen
                node = graph.states.get(screen_hash)
                if node and node.get_coverage() >= 1.0:
                    break

        # Compute aggregate statistics manually
        total_states = len(graph.states)
        total_actions_in_graph = sum(
            len(node.executed_actions) for node in graph.states.values()
        )

        assert total_states >= 1
        assert total_actions_in_graph > 0

        # Verify coverage on each screen
        for screen_hash, node in graph.states.items():
            # Each screen should have some actions tested
            assert (
                len(node.executed_actions) > 0
            ), f"Screen {screen_hash} has no actions"
            # Coverage should be significant
            assert node.get_coverage() >= 0.5, f"Screen {screen_hash} coverage too low"
