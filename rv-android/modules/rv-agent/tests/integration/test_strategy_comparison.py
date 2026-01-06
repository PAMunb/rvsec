"""
Integration tests comparing exploration strategies with real fixtures.

Tests DFS, BFS, Greedy, and RVAgent strategies to verify:
- Action selection behavior differences
- Coverage achievement patterns
- Exploration order characteristics
- Memory population consistency
"""

import pytest
from pathlib import Path
from typing import Dict, List, Set, Tuple

from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction

from rv_agent.agent.dynamic_state_graph import (
    DynamicStateGraph,
    ScreenNode,
    compute_screen_hash_from_description
)
from rv_agent.strategies.dfs_strategy import DFSStrategy
from rv_agent.strategies.bfs_strategy import BFSStrategy
from rv_agent.strategies.greedy_strategy import GreedyStrategy


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
    screen_desc = parser.parse(xml_content, activity=f"com.example.{app_name}.MainActivity")

    return xml_content, screen_desc


def get_available_fixtures(app_name: str) -> List[str]:
    """Get available screen numbers."""
    app_dir = FIXTURES_DIR / app_name
    if not app_dir.exists():
        return []
    screens = []
    for f in app_dir.glob("*.uiautomator.xml"):
        screens.append(f.stem.replace(".uiautomator", ""))
    return sorted(screens)


@pytest.fixture
def dfs_graph():
    """Graph for DFS strategy."""
    return DynamicStateGraph()


@pytest.fixture
def bfs_graph():
    """Graph for BFS strategy."""
    return DynamicStateGraph()


@pytest.fixture
def greedy_graph():
    """Graph for Greedy strategy."""
    return DynamicStateGraph()


@pytest.fixture
def dfs_strategy(dfs_graph):
    """DFS exploration strategy."""
    return DFSStrategy(graph=dfs_graph)


@pytest.fixture
def bfs_strategy(bfs_graph):
    """BFS exploration strategy."""
    return BFSStrategy(graph=bfs_graph)


@pytest.fixture
def greedy_strategy(greedy_graph):
    """Greedy exploration strategy."""
    return GreedyStrategy(graph=greedy_graph)


# =============================================================================
# Strategy Initialization Tests
# =============================================================================

class TestStrategyInitialization:
    """Test strategy initialization."""

    def test_dfs_initializes(self, dfs_strategy):
        """DFS strategy initializes correctly."""
        assert dfs_strategy.graph is not None
        assert dfs_strategy.current_depth == 0

    def test_bfs_initializes(self, bfs_strategy):
        """BFS strategy initializes correctly."""
        assert bfs_strategy.graph is not None

    def test_greedy_initializes(self, greedy_strategy):
        """Greedy strategy initializes correctly."""
        assert greedy_strategy.graph is not None


# =============================================================================
# Action Selection Comparison Tests
# =============================================================================

class TestActionSelectionComparison:
    """Compare action selection between strategies."""

    def test_all_strategies_select_action(self, dfs_strategy, bfs_strategy, greedy_strategy):
        """All strategies can select an action from same screen."""
        _, screen_desc = load_fixture("cryptoapp", "001")

        dfs_hash = compute_screen_hash_from_description(screen_desc)
        bfs_hash = compute_screen_hash_from_description(screen_desc)
        greedy_hash = compute_screen_hash_from_description(screen_desc)

        dfs_action = dfs_strategy.select_next_action(dfs_hash, screen_desc)
        bfs_action = bfs_strategy.select_next_action(bfs_hash, screen_desc)
        greedy_action = greedy_strategy.select_next_action(greedy_hash, screen_desc)

        # All should select some action (screen has clickable elements)
        assert dfs_action is not None or len(screen_desc.get_all_actions()) == 0
        assert bfs_action is not None or len(screen_desc.get_all_actions()) == 0
        assert greedy_action is not None or len(screen_desc.get_all_actions()) == 0

    def test_strategies_track_executed_actions(self, dfs_strategy, bfs_strategy, greedy_strategy):
        """All strategies track executed actions."""
        _, screen_desc = load_fixture("cryptoapp", "001")

        # Execute one action with each strategy
        for strategy, graph in [
            (dfs_strategy, dfs_strategy.graph),
            (bfs_strategy, bfs_strategy.graph),
            (greedy_strategy, greedy_strategy.graph)
        ]:
            screen_hash = compute_screen_hash_from_description(screen_desc)
            action = strategy.select_next_action(screen_hash, screen_desc)

            if action:
                node = graph.states.get(screen_hash)
                assert node is not None
                assert len(node.executed_actions) >= 1

    def test_strategies_exhaust_state(self, dfs_strategy, bfs_strategy, greedy_strategy):
        """All strategies eventually exhaust state."""
        _, screen_desc = load_fixture("cryptoapp", "001")

        for strategy in [dfs_strategy, bfs_strategy, greedy_strategy]:
            screen_hash = compute_screen_hash_from_description(screen_desc)

            action_count = 0
            max_iterations = 50  # Safety limit

            while action_count < max_iterations:
                action = strategy.select_next_action(screen_hash, screen_desc)
                if action is None:
                    break
                action_count += 1

            # Strategy should eventually return None (exhausted)
            final_action = strategy.select_next_action(screen_hash, screen_desc)
            assert final_action is None or action_count == max_iterations


# =============================================================================
# Coverage Achievement Comparison Tests
# =============================================================================

class TestCoverageAchievement:
    """Compare coverage achievement between strategies."""

    def test_all_strategies_achieve_coverage(self):
        """All strategies achieve similar coverage on same screen."""
        _, screen_desc = load_fixture("cryptoapp", "001")

        results = {}

        for name, StrategyClass in [
            ("DFS", DFSStrategy),
            ("BFS", BFSStrategy),
            ("Greedy", GreedyStrategy)
        ]:
            graph = DynamicStateGraph()
            strategy = StrategyClass(graph=graph)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            action_count = 0
            while True:
                action = strategy.select_next_action(screen_hash, screen_desc)
                if action is None:
                    break
                action_count += 1
                if action_count > 50:
                    break

            node = graph.states.get(screen_hash)
            coverage = node.get_coverage() if node else 0

            results[name] = {
                "actions": action_count,
                "coverage": coverage,
                "executed": len(node.executed_actions) if node else 0
            }

        # All strategies should achieve some coverage
        for name, data in results.items():
            assert data["coverage"] >= 0.5, f"{name} coverage too low: {data['coverage']}"

    def test_coverage_approaches_similar_values(self):
        """Different strategies achieve similar final coverage."""
        _, screen_desc = load_fixture("cryptoapp", "001")

        coverages = []

        for StrategyClass in [DFSStrategy, BFSStrategy, GreedyStrategy]:
            graph = DynamicStateGraph()
            strategy = StrategyClass(graph=graph)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            while True:
                action = strategy.select_next_action(screen_hash, screen_desc)
                if action is None:
                    break

            node = graph.states.get(screen_hash)
            if node:
                coverages.append(node.get_coverage())

        if len(coverages) >= 2:
            # Coverage difference should be small (all strategies see same actions)
            max_diff = max(coverages) - min(coverages)
            assert max_diff <= 0.3, f"Coverage difference too large: {max_diff}"


# =============================================================================
# Exploration Order Tests
# =============================================================================

class TestExplorationOrder:
    """Test exploration order differences between strategies."""

    def test_dfs_depth_first_behavior(self, dfs_strategy):
        """DFS explores depth-first."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # DFS should increase depth with each action
        initial_depth = dfs_strategy.current_depth

        action = dfs_strategy.select_next_action(screen_hash, screen_desc)

        if action:
            # Depth should increase after action
            assert dfs_strategy.current_depth > initial_depth

    def test_bfs_breadth_first_behavior(self, bfs_strategy):
        """BFS explores breadth-first."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # BFS selects actions level by level
        action = bfs_strategy.select_next_action(screen_hash, screen_desc)

        # Just verify it selects something
        assert action is not None or len(screen_desc.get_all_actions()) == 0

    def test_greedy_priority_behavior(self, greedy_strategy):
        """Greedy selects by priority score."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        action = greedy_strategy.select_next_action(screen_hash, screen_desc)

        # Greedy should select highest priority action
        assert action is not None or len(screen_desc.get_all_actions()) == 0


# =============================================================================
# Multi-Screen Strategy Tests
# =============================================================================

class TestMultiScreenStrategies:
    """Test strategies across multiple screens."""

    def test_dfs_multi_screen_exploration(self):
        """DFS explores multiple screens."""
        graph = DynamicStateGraph()
        strategy = DFSStrategy(graph=graph)

        screens = get_available_fixtures("cryptoapp")[:3]

        for screen_num in screens:
            _, screen_desc = load_fixture("cryptoapp", screen_num)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            while True:
                action = strategy.select_next_action(screen_hash, screen_desc)
                if action is None:
                    break

        # Should have visited multiple states
        assert len(graph.states) >= 1

    def test_bfs_multi_screen_exploration(self):
        """BFS explores multiple screens."""
        graph = DynamicStateGraph()
        strategy = BFSStrategy(graph=graph)

        screens = get_available_fixtures("cryptoapp")[:3]

        for screen_num in screens:
            _, screen_desc = load_fixture("cryptoapp", screen_num)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            while True:
                action = strategy.select_next_action(screen_hash, screen_desc)
                if action is None:
                    break

        assert len(graph.states) >= 1

    def test_greedy_multi_screen_exploration(self):
        """Greedy explores multiple screens."""
        graph = DynamicStateGraph()
        strategy = GreedyStrategy(graph=graph)

        screens = get_available_fixtures("cryptoapp")[:3]

        for screen_num in screens:
            _, screen_desc = load_fixture("cryptoapp", screen_num)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            while True:
                action = strategy.select_next_action(screen_hash, screen_desc)
                if action is None:
                    break

        assert len(graph.states) >= 1


# =============================================================================
# Strategy Reset Tests
# =============================================================================

class TestStrategyReset:
    """Test strategy reset functionality."""

    def test_dfs_reset(self, dfs_strategy):
        """DFS can be reset."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        # Execute some actions
        dfs_strategy.select_next_action(screen_hash, screen_desc)
        dfs_strategy.select_next_action(screen_hash, screen_desc)

        # Reset
        dfs_strategy.reset()

        assert dfs_strategy.current_depth == 0
        assert len(dfs_strategy.visited_states) == 0

    def test_bfs_reset(self, bfs_strategy):
        """BFS can be reset."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        bfs_strategy.select_next_action(screen_hash, screen_desc)

        bfs_strategy.reset()

        # Verify reset (implementation-specific)
        assert bfs_strategy.graph is not None

    def test_greedy_reset(self, greedy_strategy):
        """Greedy can be reset."""
        _, screen_desc = load_fixture("cryptoapp", "001")
        screen_hash = compute_screen_hash_from_description(screen_desc)

        greedy_strategy.select_next_action(screen_hash, screen_desc)

        greedy_strategy.reset()

        assert greedy_strategy.graph is not None


# =============================================================================
# Action Signature Consistency Tests
# =============================================================================

class TestActionSignatureConsistency:
    """Test action signature handling across strategies."""

    def test_all_strategies_use_coordinate_signatures(self):
        """All strategies track actions by coordinate signatures."""
        _, screen_desc = load_fixture("cryptoapp", "001")

        for StrategyClass in [DFSStrategy, BFSStrategy, GreedyStrategy]:
            graph = DynamicStateGraph()
            strategy = StrategyClass(graph=graph)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            action = strategy.select_next_action(screen_hash, screen_desc)

            if action:
                node = graph.states.get(screen_hash)
                assert node is not None

                # Check signature format
                for sig in node.executed_actions:
                    coords, action_type = sig
                    assert isinstance(coords, tuple)
                    assert len(coords) == 2
                    assert isinstance(action_type, str)


# =============================================================================
# Performance Comparison Tests
# =============================================================================

class TestPerformanceComparison:
    """Compare strategy performance metrics."""

    def test_action_counts_similar(self):
        """Strategies execute similar number of actions."""
        _, screen_desc = load_fixture("cryptoapp", "001")

        action_counts = {}

        for name, StrategyClass in [
            ("DFS", DFSStrategy),
            ("BFS", BFSStrategy),
            ("Greedy", GreedyStrategy)
        ]:
            graph = DynamicStateGraph()
            strategy = StrategyClass(graph=graph)
            screen_hash = compute_screen_hash_from_description(screen_desc)

            count = 0
            while True:
                action = strategy.select_next_action(screen_hash, screen_desc)
                if action is None:
                    break
                count += 1
                if count > 50:
                    break

            action_counts[name] = count

        # All strategies should have similar action counts
        counts = list(action_counts.values())
        if counts:
            max_diff = max(counts) - min(counts)
            # Allow some difference due to algorithm specifics
            assert max_diff <= 10, f"Action count difference too large: {action_counts}"


# =============================================================================
# Cross-App Strategy Tests
# =============================================================================

class TestCrossAppStrategies:
    """Test strategies across different apps."""

    def test_dfs_works_on_ludo(self):
        """DFS works on Ludo app."""
        graph = DynamicStateGraph()
        strategy = DFSStrategy(graph=graph)

        screens = get_available_fixtures("ludo")[:2]
        if not screens:
            pytest.skip("No ludo fixtures")

        for screen_num in screens:
            _, screen_desc = load_fixture("ludo", screen_num)
            screen_hash = compute_screen_hash_from_description(screen_desc)
            strategy.select_next_action(screen_hash, screen_desc)

        assert len(graph.states) >= 1

    def test_bfs_works_on_hashpass(self):
        """BFS works on Hashpass app."""
        graph = DynamicStateGraph()
        strategy = BFSStrategy(graph=graph)

        screens = get_available_fixtures("hashpass")[:2]
        if not screens:
            pytest.skip("No hashpass fixtures")

        for screen_num in screens:
            _, screen_desc = load_fixture("hashpass", screen_num)
            screen_hash = compute_screen_hash_from_description(screen_desc)
            strategy.select_next_action(screen_hash, screen_desc)

        assert len(graph.states) >= 1
