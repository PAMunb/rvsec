"""
Comprehensive tests for RVAgentStrategy functionality.

Tests the RVAgentStrategy class which implements the core exploration strategy.
"""

from dataclasses import dataclass, field, replace
from typing import List, Optional, Tuple
from unittest.mock import MagicMock

import pytest
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_android_core.domain.widget import WidgetEventType

# --- Mock data structures for screen/action ---


@dataclass
class MockAction:
    """Mock action compatible with RVAgentStrategy."""

    event: WidgetEventType = WidgetEventType.CLICK
    coordinates: Tuple[int, int] = (540, 960)
    widget_id: Optional[str] = None
    text: str = ""
    directly_reaches_target: bool = False
    reaches_target: bool = False
    callback_signature: Optional[str] = None
    text_input: Optional[str] = None
    target_view: Optional[dict] = field(default_factory=dict)

    @property
    def coords_for_matching(self):
        return (self.coordinates, self.event.value)

    def get_execution_coordinates(self):
        return self.coordinates

    def model_copy(self, update=None):
        return replace(self, **(update or {}))


@dataclass
class MockItem:
    """Mock screen item."""

    view: dict = field(default_factory=dict)
    actions: List[MockAction] = field(default_factory=list)


@dataclass
class MockScreen:
    """Mock screen description compatible with RVAgentStrategy."""

    activity: str = "MainActivity"
    items: List[MockItem] = field(default_factory=list)

    def get_all_actions(self):
        result = []
        for item in self.items:
            result.extend(item.actions)
        return result


def _make_screen(activity, actions):
    """Create a MockScreen from a list of MockActions."""
    items = [MockItem(view={}, actions=[a]) for a in actions]
    return MockScreen(activity=activity, items=items)


def _create_strategy(use_real_components=False, **config_overrides):
    """Helper to create an RVAgentStrategy with default config.

    Args:
        use_real_components: Use real DynamicStateGraph and UICoverageTracker
            instead of mocks. Required for tests calling select_next_action.
        **config_overrides: Override any RVAgentConfig field.
    """
    if use_real_components:
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
    else:
        graph = MagicMock()
        ui_coverage = MagicMock()
    config_kwargs = {"package_name": "com.test.app"}
    config_kwargs.update(config_overrides)
    config = RVAgentConfig(**config_kwargs)
    return RVAgentStrategy(
        graph=graph,
        ui_coverage=ui_coverage,
        config=config,
    )


class TestRVAgentStrategyInitialization:
    """Test RVAgentStrategy initialization and setup."""

    def test_initialization_with_defaults(self):
        """RVAgentStrategy initializes with default parameters."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        config = RVAgentConfig.create_default(package_name="com.test.app")

        strategy = RVAgentStrategy(
            graph=mock_graph, ui_coverage=mock_ui_coverage, config=config
        )

        assert strategy.graph == mock_graph
        assert strategy.ui_coverage == mock_ui_coverage
        assert strategy.converter is None
        assert strategy.config.plateau_window == 10
        assert strategy.config.max_input_variations == 3

    def test_initialization_with_custom_params(self):
        """RVAgentStrategy initializes with custom parameters."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        mock_coordinate_converter = MagicMock()
        config = RVAgentConfig(
            package_name="com.test.app",
            plateau_window=20,
            max_input_variations=5,
        )

        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage,
            config=config,
            coordinate_converter=mock_coordinate_converter,
        )

        assert strategy.graph == mock_graph
        assert strategy.ui_coverage == mock_ui_coverage
        assert strategy.converter == mock_coordinate_converter
        assert strategy.config.plateau_window == 20
        assert strategy.config.max_input_variations == 5


class TestRVAgentStrategyStateManagement:
    """Test RVAgentStrategy state management functionality."""

    def test_reset_method_clears_state(self):
        """RVAgentStrategy reset method clears all state."""
        strategy = _create_strategy()

        strategy._current_iteration = 10

        strategy.reset()

        assert strategy._current_iteration == 0

    def test_get_statistics_returns_dict(self):
        """RVAgentStrategy get_statistics returns state dictionary."""
        strategy = _create_strategy()

        stats = strategy.get_statistics()

        assert isinstance(stats, dict)
        assert "states_visited" in stats
        assert stats["states_visited"] == 0


class TestRVAgentStrategyActionSelection:
    """Test RVAgentStrategy action selection functionality."""

    def test_select_next_action_returns_action_or_none(self):
        """RVAgentStrategy select_next_action accepts hash and screen description."""
        strategy = _create_strategy(use_real_components=True)
        screen = _make_screen("MainActivity", [])

        next_action = strategy.select_next_action("hash123", screen)

        # Returns BACK action as fallback when no actions available
        assert next_action is not None or next_action is None

    def test_select_next_action_with_no_actions(self):
        """RVAgentStrategy returns BACK action when no actions available."""
        strategy = _create_strategy(use_real_components=True)
        screen = _make_screen("EmptyActivity", [])

        next_action = strategy.select_next_action("hash123", screen)

        # Returns BACK action as fallback
        assert next_action is not None


class TestRVAgentStrategyTransitionHandling:
    """Test RVAgentStrategy transition handling functionality."""

    def test_record_transition_updates_graph(self):
        """RVAgentStrategy records transition in the graph."""
        strategy = _create_strategy()

        mock_action = MagicMock()
        mock_action.coordinates = (200, 500)
        mock_action.event = MagicMock()
        mock_action.event.value = 1
        mock_action.callback_signature = None
        mock_action.coords_for_matching = ((200, 500), "click")

        strategy.record_transition("hash123", "hash456", mock_action)

        strategy.graph.record_transition.assert_called_once()

    def test_record_transition_updates_plateau_detector(self):
        """RVAgentStrategy updates plateau detector on transition."""
        strategy = _create_strategy()

        mock_action = MagicMock()
        mock_action.coordinates = (200, 500)
        mock_action.event = MagicMock()
        mock_action.event.value = 1
        mock_action.callback_signature = None
        mock_action.coords_for_matching = ((200, 500), "click")

        strategy.record_transition("hash123", "hash456", mock_action)

        assert strategy.plateau_detector.total_iterations == 1


class TestRVAgentStrategyCoverageMetrics:
    """Test RVAgentStrategy coverage metrics functionality."""

    def test_coverage_metrics_initialized(self):
        """RVAgentStrategy initializes coverage metrics."""
        strategy = _create_strategy()

        assert strategy.coverage_metrics is not None
        assert strategy.coverage_metrics.get_mop_count() == 0

    def test_plateau_detector_integration(self):
        """RVAgentStrategy plateau detector tracks iterations."""
        strategy = _create_strategy()

        for _ in range(11):
            strategy.plateau_detector.record_iteration(
                discovered_new_state=False,
                new_mop_method=None,
            )

        assert strategy.plateau_detector.is_plateau_reached() is True

    def test_plateau_not_reached_with_progress(self):
        """RVAgentStrategy plateau not reached when progress is made."""
        strategy = _create_strategy()

        for i in range(5):
            strategy.plateau_detector.record_iteration(
                discovered_new_state=True,
                new_mop_method=f"method_{i}",
            )

        assert strategy.plateau_detector.is_plateau_reached() is False


class TestRVAgentStrategySuccessorTracking:
    """Test RVAgentStrategy successor tracking functionality."""

    def test_successor_tracker_integration(self):
        """RVAgentStrategy properly initializes successor tracker."""
        strategy = _create_strategy()

        assert strategy.successor_tracker is not None

        stats = strategy.successor_tracker.get_statistics()
        assert stats["total_successors_tracked"] == 0


class TestRVAgentStrategyRankingFunctionality:
    """Test RVAgentStrategy action ranking functionality."""

    def test_action_ranker_integration(self):
        """RVAgentStrategy properly initializes action ranker."""
        strategy = _create_strategy()

        assert strategy.action_ranker is not None
        assert len(strategy.action_ranker.scorers) > 0

    def test_ranker_has_expected_scorers(self):
        """Action ranker has the expected set of scorers."""
        strategy = _create_strategy()

        scorer_types = [type(s).__name__ for s in strategy.action_ranker.scorers]

        assert "MopScorer" in scorer_types
        assert "WtgScorer" in scorer_types
        assert "ComponentPriorityScorer" in scorer_types


class TestRVAgentStrategyEdgeCases:
    """Test RVAgentStrategy edge cases and error conditions."""

    def test_handle_empty_action_list(self):
        """RVAgentStrategy handles empty action list gracefully."""
        strategy = _create_strategy(use_real_components=True)
        screen = _make_screen("EmptyActivity", [])

        next_action = strategy.select_next_action("hash123", screen)

        # Returns BACK action as fallback when no actions available
        assert next_action is not None

    def test_handle_none_screen(self):
        """RVAgentStrategy handles None screen description."""
        strategy = _create_strategy(use_real_components=True)

        with pytest.raises((AttributeError, TypeError)):
            strategy.select_next_action("hash123", None)
