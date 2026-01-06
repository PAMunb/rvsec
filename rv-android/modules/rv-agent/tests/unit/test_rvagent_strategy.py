"""
Unit tests for RVAgentStrategy and helper components.

Tests for:
- RVAgentStrategy: Main exploration strategy
- CoverageMetrics: Coverage aggregation
- PlateauDetector: Exploration plateau detection
- SuccessorTracker: State successor tracking
- InputValueGenerator: Text input generation
"""

import pytest
from unittest.mock import MagicMock, patch
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker
from rv_agent.strategies.rvagent_strategy.plateau_detector import PlateauDetector
from rv_agent.strategies.rvagent_strategy.coverage_metrics import CoverageMetrics
from rv_agent.strategies.rvagent_strategy.input_value_generator import InputValueGenerator
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction, WidgetEventType

class TestRVAgentStrategy:
    @pytest.fixture
    def strategy(self):
        graph = MagicMock(spec=DynamicStateGraph)
        ui_coverage = MagicMock(spec=UICoverageTracker)
        return RVAgentStrategy(graph, ui_coverage)

    def test_initialization(self, strategy):
        assert isinstance(strategy.successor_tracker, SuccessorTracker)
        assert isinstance(strategy.plateau_detector, PlateauDetector)
        assert isinstance(strategy.coverage_metrics, CoverageMetrics)
        assert strategy.current_depth == 0

    def test_select_next_action_plateau(self, strategy):
        # Mock plateau detector to return True
        strategy.plateau_detector.is_plateau_reached = MagicMock(return_value=True)

        # Even if plateau is reached, it should NOT stop exploration (informational only)
        # We need to mock other components to ensure it proceeds to selection
        strategy.graph.states = {}
        strategy.graph.get_or_create_state = MagicMock()
        strategy.successor_tracker.update_action_availability = MagicMock(return_value=0)

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.activity = "MainActivity"
        screen_desc.items = []

        # Mock _get_untested_actions to return empty so it returns BACK (continuous exploration)
        strategy._get_untested_actions = MagicMock(return_value=[])

        action = strategy.select_next_action("hash123", screen_desc)
        # Continuous exploration: returns BACK action instead of None when exhausted
        assert action is not None
        assert action.text == "BACK"
        assert action.event == WidgetEventType.BACK

    def test_select_next_action_new_state(self, strategy):
        current_hash = "new_state_hash"
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.activity = "MainActivity"
        screen_desc.items = []

        # Mock graph behavior
        strategy.graph.states = {}
        mock_node = MagicMock()
        mock_node.total_actions = 5
        strategy.graph.get_or_create_state.return_value = mock_node

        # Mock internal methods
        strategy.successor_tracker.update_action_availability = MagicMock(return_value=0)
        strategy._get_untested_actions = MagicMock(return_value=[])

        strategy.select_next_action(current_hash, screen_desc)

        # Verify state creation
        strategy.graph.get_or_create_state.assert_called_with(current_hash, "MainActivity", screen_desc)
        assert current_hash in strategy.visited_states
        assert len(strategy.state_stack) == 1
        assert strategy.state_stack[0].screen_hash == current_hash

    def test_priority_selection(self, strategy):
        # Create mock actions with different priorities
        action_dm = MagicMock(spec=ItemAction)
        action_dm.directly_reaches_mop = True
        action_dm.reaches_mop = True

        action_m = MagicMock(spec=ItemAction)
        action_m.directly_reaches_mop = False
        action_m.reaches_mop = True

        action_ui = MagicMock(spec=ItemAction)
        action_ui.directly_reaches_mop = False
        action_ui.reaches_mop = False

        untested_actions = [action_ui, action_dm, action_m]
        screen_desc = MagicMock(spec=ScreenDescription)

        selected = strategy._select_priority_action(untested_actions, screen_desc)

        # Should prioritize Direct MOP
        assert selected == action_dm


class TestCoverageMetrics:
    """Test CoverageMetrics class."""

    @pytest.fixture
    def metrics(self):
        graph = MagicMock(spec=DynamicStateGraph)
        graph.states = {}
        graph.transitions = []
        graph.get_coverage_summary.return_value = {"overall_coverage": 0.75}
        ui_coverage = MagicMock(spec=UICoverageTracker)
        ui_coverage.get_overall_statistics.return_value = {
            "total_elements": 10,
            "tested_elements": 5,
            "coverage_rate": 0.5
        }
        return CoverageMetrics(graph, ui_coverage)

    def test_initialization(self, metrics):
        """CoverageMetrics initializes correctly."""
        assert metrics.mop_methods_reached == set()
        assert metrics.graph is not None
        assert metrics.ui_coverage is not None

    def test_record_mop_execution(self, metrics):
        """record_mop_execution tracks unique methods."""
        metrics.record_mop_execution("javax.crypto.Cipher.init")
        assert len(metrics.mop_methods_reached) == 1

        # Same method again - no duplicate
        metrics.record_mop_execution("javax.crypto.Cipher.init")
        assert len(metrics.mop_methods_reached) == 1

        # Different method
        metrics.record_mop_execution("javax.crypto.Cipher.doFinal")
        assert len(metrics.mop_methods_reached) == 2

    def test_record_mop_empty_string(self, metrics):
        """Empty callback signature is ignored."""
        metrics.record_mop_execution("")
        assert len(metrics.mop_methods_reached) == 0

    def test_get_mop_count(self, metrics):
        """get_mop_count returns correct count."""
        assert metrics.get_mop_count() == 0
        metrics.record_mop_execution("method1")
        assert metrics.get_mop_count() == 1

    def test_get_summary(self, metrics):
        """get_summary aggregates data from all sources."""
        summary = metrics.get_summary()

        assert "states_discovered" in summary
        assert "graph_overall_coverage" in summary
        assert "ui_elements_discovered" in summary
        assert "mop_methods_reached" in summary
        assert summary["ui_coverage_rate"] == 0.5

    def test_get_summary_with_states(self, metrics):
        """get_summary counts actions from graph states."""
        mock_node = MagicMock()
        mock_node.executed_actions = {1, 2, 3}
        metrics.graph.states = {"hash1": mock_node}

        summary = metrics.get_summary()
        assert summary["total_actions_executed"] == 3

    def test_reset_mop_tracking(self, metrics):
        """reset_mop_tracking clears MOP set."""
        metrics.record_mop_execution("method1")
        assert metrics.get_mop_count() == 1

        metrics.reset_mop_tracking()
        assert metrics.get_mop_count() == 0

    def test_repr(self, metrics):
        """__repr__ returns formatted string."""
        result = repr(metrics)
        assert "CoverageMetrics" in result
        assert "states=" in result

    def test_get_detailed_metrics(self, metrics):
        """get_detailed_metrics includes state details."""
        mock_node = MagicMock()
        mock_node.activity = "MainActivity"
        mock_node.total_actions = 10
        mock_node.executed_actions = {1, 2, 3}
        mock_node.visit_count = 2
        metrics.graph.states = {"hash1234567890": mock_node}

        result = metrics.get_detailed_metrics()

        assert "state_details" in result
        assert "mop_methods_list" in result
        assert len(result["state_details"]) == 1
        assert result["state_details"][0]["activity"] == "MainActivity"
        assert result["state_details"][0]["total_actions"] == 10
        assert result["state_details"][0]["executed_actions"] == 3
        assert result["state_details"][0]["coverage"] == 0.3

    def test_get_detailed_metrics_zero_actions(self, metrics):
        """get_detailed_metrics handles state with zero actions."""
        mock_node = MagicMock()
        mock_node.activity = "EmptyActivity"
        mock_node.total_actions = 0
        mock_node.executed_actions = set()
        mock_node.visit_count = 1
        metrics.graph.states = {"hash123": mock_node}

        result = metrics.get_detailed_metrics()
        assert result["state_details"][0]["coverage"] == 1.0

    def test_get_progress_report(self, metrics):
        """get_progress_report returns formatted string."""
        result = metrics.get_progress_report()

        assert "=== Coverage Report ===" in result
        assert "States:" in result
        assert "Graph Coverage:" in result
        assert "Actions Executed:" in result
        assert "UI Elements:" in result
        assert "MOP Methods:" in result
        assert "Transitions:" in result


class TestPlateauDetector:
    """Test PlateauDetector class."""

    @pytest.fixture
    def detector(self):
        return PlateauDetector(window_size=10)

    def test_initialization(self, detector):
        """PlateauDetector initializes with defaults."""
        assert detector.window_size == 10
        assert len(detector.state_discovery) == 0
        assert len(detector.mop_execution) == 0

    def test_initialization_invalid_window(self):
        """PlateauDetector rejects invalid window_size."""
        with pytest.raises(ValueError):
            PlateauDetector(window_size=0)

    def test_record_iteration(self, detector):
        """record_iteration adds to history."""
        detector.record_iteration(discovered_new_state=True, new_mop_method="method1")

        assert len(detector.state_discovery) == 1
        assert len(detector.mop_execution) == 1
        assert detector.state_discovery[-1] is True
        assert detector.total_iterations == 1

    def test_record_iteration_window_size(self, detector):
        """History is limited to window_size."""
        for i in range(15):
            detector.record_iteration(discovered_new_state=i % 2 == 0)

        assert len(detector.state_discovery) == 10
        assert len(detector.mop_execution) == 10

    def test_is_plateau_reached_not_enough_data(self, detector):
        """Plateau not detected with insufficient data."""
        detector.record_iteration(discovered_new_state=True)
        assert detector.is_plateau_reached() is False

    def test_is_plateau_reached_growing(self, detector):
        """Plateau not detected when growing."""
        for i in range(detector.window_size):
            # Alternate between True and False - some progress
            detector.record_iteration(discovered_new_state=(i % 2 == 0))

        assert detector.is_plateau_reached() is False

    def test_is_plateau_reached_flat(self, detector):
        """Plateau detected when coverage is flat."""
        for i in range(detector.window_size):
            detector.record_iteration(discovered_new_state=False, new_mop_method=None)

        # No new states and no new MOP -> plateau
        assert detector.is_plateau_reached() is True

    def test_reset(self, detector):
        """reset clears all history."""
        detector.record_iteration(discovered_new_state=True)
        detector.reset()

        assert len(detector.state_discovery) == 0
        assert len(detector.mop_execution) == 0
        assert detector.total_iterations == 0

    def test_get_metrics(self, detector):
        """get_metrics returns comprehensive stats."""
        detector.record_iteration(discovered_new_state=True, new_mop_method="method1")

        metrics = detector.get_metrics()

        assert "window_size" in metrics
        assert "total_iterations" in metrics
        assert "plateau_reached" in metrics

    def test_repr(self, detector):
        """__repr__ returns formatted string."""
        result = repr(detector)
        assert "PlateauDetector" in result


class TestSuccessorTracker:
    """Test SuccessorTracker class."""

    @pytest.fixture
    def tracker(self):
        graph = MagicMock(spec=DynamicStateGraph)
        graph.states = {}
        return SuccessorTracker(graph)

    def test_initialization(self, tracker):
        """SuccessorTracker initializes with empty state."""
        assert tracker.successors == {}
        assert tracker.coverage_cache == {}

    def test_record_successor(self, tracker):
        """record_successor tracks action-state mapping."""
        action_sig = ((100, 200), "click")
        tracker.record_successor("state1", action_sig, "state2")

        assert ("state1", action_sig) in tracker.successors
        assert tracker.successors[("state1", action_sig)] == "state2"

    def test_record_successor_invalidates_cache(self, tracker):
        """record_successor invalidates coverage cache."""
        tracker.coverage_cache["state2"] = 0.5
        action_sig = ((100, 200), "click")
        tracker.record_successor("state1", action_sig, "state2")

        assert "state2" not in tracker.coverage_cache

    def test_get_successor_coverage_unknown_state(self, tracker):
        """Unknown state returns 1.0 coverage."""
        result = tracker.get_successor_coverage("unknown_hash")
        assert result == 1.0

    def test_get_successor_coverage_known_state(self, tracker):
        """Known state returns calculated coverage."""
        mock_node = MagicMock()
        mock_node.total_actions = 10
        mock_node.executed_actions = {1, 2, 3}  # 3 executed
        tracker.graph.states = {"state_hash": mock_node}

        result = tracker.get_successor_coverage("state_hash")
        assert result == 0.3

    def test_get_successor_coverage_zero_actions(self, tracker):
        """State with zero actions returns 1.0 coverage."""
        mock_node = MagicMock()
        mock_node.total_actions = 0
        mock_node.executed_actions = set()
        tracker.graph.states = {"state_hash": mock_node}

        result = tracker.get_successor_coverage("state_hash")
        assert result == 1.0

    def test_get_successor_coverage_cache(self, tracker):
        """get_successor_coverage uses cache."""
        tracker.coverage_cache["cached_state"] = 0.75
        result = tracker.get_successor_coverage("cached_state")
        assert result == 0.75

    def test_has_incomplete_successors_none(self, tracker):
        """has_incomplete_successors returns False when no incomplete."""
        mock_node = MagicMock()
        mock_node.executed_actions = {((100, 200), "click")}
        tracker.graph.states = {"state1": mock_node}

        # Record successor that is fully explored
        tracker.successors[("state1", ((100, 200), "click"))] = "state2"
        tracker.coverage_cache["state2"] = 1.0

        result = tracker.has_incomplete_successors("state1")
        assert result is False

    def test_has_incomplete_successors_found(self, tracker):
        """has_incomplete_successors returns True when found."""
        mock_node = MagicMock()
        mock_node.executed_actions = {((100, 200), "click")}
        tracker.graph.states = {"state1": mock_node}

        # Record successor that is NOT fully explored
        tracker.successors[("state1", ((100, 200), "click"))] = "state2"
        mock_successor = MagicMock()
        mock_successor.total_actions = 10
        mock_successor.executed_actions = {1, 2}  # Only 2/10
        tracker.graph.states["state2"] = mock_successor

        result = tracker.has_incomplete_successors("state1")
        assert result is True

    def test_has_incomplete_successors_unknown_state(self, tracker):
        """has_incomplete_successors returns False for unknown state."""
        result = tracker.has_incomplete_successors("unknown")
        assert result is False

    def test_get_incomplete_successors_empty(self, tracker):
        """get_incomplete_successors returns empty for unknown state."""
        result = tracker.get_incomplete_successors("unknown")
        assert result == set()

    def test_get_incomplete_successors_returns_actions(self, tracker):
        """get_incomplete_successors returns action signatures."""
        action_sig = ((100, 200), "click")
        mock_node = MagicMock()
        mock_node.executed_actions = {action_sig}
        tracker.graph.states = {"state1": mock_node}

        # Incomplete successor
        tracker.successors[("state1", action_sig)] = "state2"
        mock_successor = MagicMock()
        mock_successor.total_actions = 5
        mock_successor.executed_actions = {1}  # 1/5
        tracker.graph.states["state2"] = mock_successor

        result = tracker.get_incomplete_successors("state1")
        assert action_sig in result

    def test_update_action_availability_unknown_state(self, tracker):
        """update_action_availability returns 0 for unknown state."""
        result = tracker.update_action_availability("unknown")
        assert result == 0

    def test_update_action_availability_re_enables(self, tracker):
        """update_action_availability re-enables incomplete actions."""
        action_sig = ((100, 200), "click")
        mock_node = MagicMock()
        # Use a real set that we can check after the call
        executed = {action_sig}
        mock_node.executed_actions = executed
        tracker.graph.states = {"state1": mock_node}

        # Record incomplete successor
        tracker.successors[("state1", action_sig)] = "state2"
        mock_successor = MagicMock()
        mock_successor.total_actions = 10
        mock_successor.executed_actions = {1, 2}  # 2/10 = 20%
        tracker.graph.states["state2"] = mock_successor

        result = tracker.update_action_availability("state1")
        assert result == 1
        # Verify action was removed from executed set
        assert action_sig not in executed

    def test_get_statistics_empty(self, tracker):
        """get_statistics returns zeros when empty."""
        stats = tracker.get_statistics()
        assert stats["total_successors_tracked"] == 0
        assert stats["incomplete_successors"] == 0
        assert stats["complete_successors"] == 0

    def test_get_statistics_with_data(self, tracker):
        """get_statistics counts successors correctly."""
        # Add some successors
        tracker.successors[("s1", ("a1",))] = "s2"
        tracker.successors[("s1", ("a2",))] = "s3"

        # Make s2 complete, s3 incomplete
        tracker.coverage_cache["s2"] = 1.0
        tracker.coverage_cache["s3"] = 0.5

        stats = tracker.get_statistics()
        assert stats["total_successors_tracked"] == 2
        assert stats["complete_successors"] == 1
        assert stats["incomplete_successors"] == 1


class TestInputValueGenerator:
    """Test InputValueGenerator class."""

    @pytest.fixture
    def generator(self):
        return InputValueGenerator(max_variations=3)

    def test_initialization(self, generator):
        """InputValueGenerator initializes correctly."""
        assert generator.max_variations == 3
        assert generator.tested_values is not None

    def test_initialization_invalid_max(self):
        """InputValueGenerator rejects invalid max_variations."""
        with pytest.raises(ValueError):
            InputValueGenerator(max_variations=0)

    def test_get_next_value(self, generator):
        """get_next_value returns test value."""
        result = generator.get_next_value("element1", is_mop=False)
        assert result is not None

    def test_get_next_value_tracks_tested(self, generator):
        """get_next_value tracks tested values."""
        result1 = generator.get_next_value("element1")
        result2 = generator.get_next_value("element1")

        # Should return different values
        assert result1 != result2 or result1 is None or result2 is None

    def test_get_next_value_exhausted(self, generator):
        """get_next_value returns None when exhausted."""
        # Use all variations
        for _ in range(generator.max_variations + 5):
            result = generator.get_next_value("element1")
            if result is None:
                break

        # Eventually returns None
        final_result = generator.get_next_value("element1")
        assert final_result is None

    def test_get_next_value_mop_element(self, generator):
        """get_next_value handles MOP elements."""
        result = generator.get_next_value("element1", is_mop=True)
        assert result is not None

    def test_get_tested_count(self, generator):
        """get_tested_count returns correct count."""
        assert generator.get_tested_count("element1") == 0
        generator.get_next_value("element1")
        assert generator.get_tested_count("element1") == 1
        generator.get_next_value("element1")
        assert generator.get_tested_count("element1") == 2

    def test_has_remaining_values(self, generator):
        """has_remaining_values returns correct status."""
        assert generator.has_remaining_values("element1") is True
        for _ in range(3):
            generator.get_next_value("element1")
        assert generator.has_remaining_values("element1") is False

    def test_get_statistics(self, generator):
        """get_statistics returns comprehensive stats."""
        generator.get_next_value("element1")
        generator.get_next_value("element2")
        for _ in range(3):
            generator.get_next_value("element3")

        stats = generator.get_statistics()
        assert stats["total_elements_tested"] == 3
        assert stats["exhausted_elements"] == 1  # element3
        assert stats["active_elements"] == 2  # element1, element2
        assert stats["total_values_tested"] == 5  # 1 + 1 + 3

    def test_reset(self, generator):
        """reset clears all tested values."""
        generator.get_next_value("element1")
        generator.get_next_value("element2")
        assert generator.get_tested_count("element1") == 1

        generator.reset()

        assert generator.get_tested_count("element1") == 0
        assert generator.get_tested_count("element2") == 0

    def test_repr(self, generator):
        """__repr__ returns formatted string."""
        generator.get_next_value("element1")
        result = repr(generator)
        assert "InputValueGenerator" in result
        assert "max_variations=3" in result
        assert "elements=1" in result
