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
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction, WidgetEventType, ScreenItem

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

    def test_select_next_action_scroll_action(self, strategy):
        """Test that a scroll action is prioritized if generated."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "MainActivity"
        strategy.graph.states = {}
        scroll_action = ItemAction(id=1, event=WidgetEventType.SCROLL, text="scroll", reaches_mop=False, directly_reaches_mop=False, target_view={}, coordinates=None, text_input=None)
        
        with patch.object(strategy, '_try_generate_scroll_action', return_value=scroll_action) as mock_scroll:
            strategy.graph.get_or_create_state = MagicMock()
            strategy.successor_tracker.update_action_availability = MagicMock(return_value=0)
            action = strategy.select_next_action("hash1", screen_desc)
            mock_scroll.assert_called_once()
            assert action == scroll_action
            assert strategy.current_depth == 1

    def test_select_next_action_no_untested_uses_least_executed(self, strategy):
        """Test that it falls back to least executed action when no untested actions are left."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "MainActivity"
        mock_node = MagicMock()
        strategy.graph.states = {"hash1": mock_node}
        
        least_executed_action = ItemAction(id=1, event=WidgetEventType.CLICK, text="click", reaches_mop=False, directly_reaches_mop=False, target_view={}, coordinates=(1,1), text_input=None)

        strategy._get_untested_actions = MagicMock(return_value=[]) # No untested
        strategy._get_all_filtered_actions = MagicMock(return_value=[least_executed_action])
        strategy._select_least_executed_action = MagicMock(return_value=least_executed_action)
        strategy._convert_signature_to_optimized = MagicMock(return_value='sig') # Mock conversion

        action = strategy.select_next_action("hash1", screen_desc)
        
        strategy._select_least_executed_action.assert_called_once()
        assert action == least_executed_action

    def test_select_next_action_all_failed_returns_back(self, strategy):
        """Test that it returns BACK if all actions have failed."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "MainActivity"
        mock_node = MagicMock()
        strategy.graph.states = {"hash1": mock_node}
        
        failed_action = ItemAction(id=1, event=WidgetEventType.CLICK, text="click", reaches_mop=False, directly_reaches_mop=False, target_view={}, coordinates=(1,1), text_input=None)

        strategy._get_untested_actions = MagicMock(return_value=[])
        strategy._get_all_filtered_actions = MagicMock(return_value=[failed_action])
        strategy._select_least_executed_action = MagicMock(return_value=None) # All failed

        action = strategy.select_next_action("hash1", screen_desc)
        
        assert action.event == WidgetEventType.BACK

    def test_record_transition(self, strategy):
        """Test that record_transition calls its helper components."""
        strategy.successor_tracker = MagicMock(spec=SuccessorTracker)
        strategy.plateau_detector = MagicMock(spec=PlateauDetector)
        
        # Fix: Create a mock with the property, don't set it
        action = MagicMock(spec=ItemAction)
        action.event = WidgetEventType.CLICK
        action.callback_signature="mop.method"
        type(action).coords_for_matching = ((1,1), "click")
        strategy._convert_signature_to_optimized = MagicMock(return_value='sig')


        strategy.record_transition("hash1", "hash2", action)

        strategy.graph.record_transition.assert_called_once()
        strategy.successor_tracker.record_successor.assert_called_once()
        strategy.plateau_detector.record_iteration.assert_called_once_with(
            discovered_new_state=True,
            new_mop_method="mop.method"
        )

    def test_should_backtrack_incomplete_successors(self, strategy):
        """Test that it does not backtrack if successors are incomplete."""
        strategy.graph.states = {"hash1": MagicMock()}
        strategy.successor_tracker = MagicMock(spec=SuccessorTracker)
        strategy.successor_tracker.has_incomplete_successors.return_value = True
        
        assert strategy.should_backtrack("hash1") is False

    def test_should_backtrack_state_exhausted(self, strategy):
        """Test that it backtracks if state is exhausted."""
        mock_node = MagicMock()
        mock_node.total_actions = 5
        mock_node.executed_actions = {1, 2, 3, 4, 5} # Exhausted
        strategy.graph.states = {"hash1": mock_node}
        
        # Fix: Patch the method on the real object
        with patch.object(strategy.successor_tracker, 'has_incomplete_successors', return_value=False):
            assert strategy.should_backtrack("hash1") is True

class TestRVAgentStrategyHelpers:
    """Test helper methods of RVAgentStrategy."""

    @pytest.fixture
    def strategy(self):
        graph = MagicMock(spec=DynamicStateGraph)
        ui_coverage = MagicMock(spec=UICoverageTracker)
        return RVAgentStrategy(graph, ui_coverage, target_package="com.example.app")

    def test_get_untested_actions_filtering(self, strategy):
        """Test that actions are filtered by package and system type."""
        mock_node = MagicMock()
        mock_node.executed_actions = set()
        
        # Action from the correct package
        action_good = MagicMock(spec=ItemAction)
        type(action_good).coords_for_matching = ((1,1), "click")
        
        # Action from a different package
        action_external = MagicMock(spec=ItemAction)
        type(action_external).coords_for_matching = ((2,2), "click")

        # System action (e.g., in nav bar)
        action_system = MagicMock(spec=ItemAction)
        type(action_system).coords_for_matching = ((3, 1850), "click") # y > 1800

        item_good = MagicMock()
        item_good.view = {'package': 'com.example.app'}
        item_good.actions = [action_good]

        item_external = MagicMock()
        item_external.view = {'package': 'com.android.systemui'}
        item_external.actions = [action_external]
        
        item_system = MagicMock()
        item_system.view = {'package': 'com.example.app'}
        item_system.actions = [action_system]

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = [item_good, item_external, item_system]
        
        strategy._is_system_action = lambda action: action == action_system # Mock private method

        untested = strategy._get_untested_actions(mock_node, screen_desc)

        assert len(untested) == 1
        assert untested[0] == action_good

    def test_select_least_executed_action(self, strategy):
        """Test sorting and selection of the least executed action."""
        mock_node = MagicMock()
        
        action1 = MagicMock(spec=ItemAction); type(action1).coords_for_matching = ((1,1),"c"); action1.directly_reaches_mop=False; action1.reaches_mop=False
        action2 = MagicMock(spec=ItemAction); type(action2).coords_for_matching = ((2,2),"c"); action2.directly_reaches_mop=False; action2.reaches_mop=True # MOP
        action3 = MagicMock(spec=ItemAction); type(action3).coords_for_matching = ((3,3),"c"); action3.directly_reaches_mop=False; action3.reaches_mop=False
        action4_failed = MagicMock(spec=ItemAction); type(action4_failed).coords_for_matching = ((4,4),"c");

        actions = [action1, action2, action3, action4_failed]
        
        # Mock execution counts and failed status
        strategy._convert_signature_to_optimized = lambda x: x # Passthrough
        mock_node.get_action_execution_count.side_effect = lambda sig: {
            ((1,1),"c"): 2,
            ((2,2),"c"): 1,
            ((3,3),"c"): 1,
        }.get(sig, 0)
        mock_node.is_action_failed.side_effect = lambda sig: sig == ((4,4),"c")

        selected = strategy._select_least_executed_action(mock_node, actions)

        # action4 is skipped (failed)
        # action2 and action3 both have 1 execution
        # action2 is chosen because it has MOP priority
        assert selected == action2

    def test_prepare_input_action_exhausted(self, strategy):
        """Test that _prepare_input_action returns None when values are exhausted."""
        action = MagicMock(spec=ItemAction)
        action.widget_id = "input1"
        action.reaches_mop = False
        action.directly_reaches_mop = False
        
        # Mock value generator to be exhausted
        strategy.value_generator.get_next_value = MagicMock(return_value=None)
        
        result = strategy._prepare_input_action(action, "hash1")
        
        assert result is None
        strategy.value_generator.get_next_value.assert_called_once()


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

    def test_plateau_detection_with_slow_progress(self, detector):
        """
        Tests that plateau is NOT detected if there is slow but consistent progress
        (e.g., discovering a new state just within the window).

        The deque has maxlen=window_size, so after recording a True at iteration 10,
        we need 10 more iterations (not 9) to push the True out of the window.
        """
        # Simulate 9 iterations with no progress
        for _ in range(detector.window_size - 1):  # 9 iterations
            detector.record_iteration(discovered_new_state=False, new_mop_method=None)

        # On the 10th iteration (last of the window), discover a new state
        detector.record_iteration(discovered_new_state=True, new_mop_method=None)

        # Plateau should NOT be detected because there was progress within the window
        assert detector.is_plateau_reached() is False

        # Simulate 9 more iterations with no progress
        # After this: window = [T,F,F,F,F,F,F,F,F,F] - True still in window!
        for _ in range(detector.window_size - 1):
            detector.record_iteration(discovered_new_state=False, new_mop_method=None)

        # Plateau should still NOT be detected because the True is at position 0
        assert detector.is_plateau_reached() is False

        # One more iteration pushes the True out of the window
        # After this: window = [F,F,F,F,F,F,F,F,F,F] - all False!
        detector.record_iteration(discovered_new_state=False, new_mop_method=None)

        # Now plateau should be detected (no progress in entire window)
        assert detector.is_plateau_reached() is True


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
        assert result == 0

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
        result = generator.get_next_value("element1", is_mop=False, input_type="text")
        assert result is not None

    def test_get_next_value_tracks_tested(self, generator):
        """get_next_value tracks tested values."""
        result1 = generator.get_next_value("element1", input_type="text")
        result2 = generator.get_next_value("element1", input_type="text")

        # Should return different values
        assert result1 != result2 or result1 is None or result2 is None

    def test_get_next_value_exhausted(self, generator):
        """get_next_value returns None when exhausted."""
        # Use all variations
        for _ in range(generator.max_variations + 5):
            result = generator.get_next_value("element1", input_type="text")
            if result is None:
                break

        # Eventually returns None
        final_result = generator.get_next_value("element1", input_type="text")
        assert final_result is None

    def test_get_next_value_mop_element(self, generator):
        """get_next_value handles MOP elements."""
        result = generator.get_next_value("element1", is_mop=True, input_type="text")
        assert result is not None

    def test_get_next_value_with_different_types(self, generator):
        """get_next_value works with different input types."""
        result_email = generator.get_next_value("element1", is_mop=False, input_type="email")
        result_name = generator.get_next_value("element2", is_mop=False, input_type="name")
        result_phone = generator.get_next_value("element3", is_mop=False, input_type="phone")

        assert result_email is not None
        assert result_name is not None
        assert result_phone is not None

    def test_get_next_value_with_locales(self):
        """InputValueGenerator works with different locales."""
        generator = InputValueGenerator(max_variations=3, locales=['en_US', 'pt_BR'])
        result = generator.get_next_value("element1", is_mop=False, input_type="name")
        assert result is not None

    def test_get_next_value_all_input_types(self, generator):
        """get_next_value works with all input types."""
        input_types = ["email", "name", "phone", "address", "text", "username",
                      "password", "city", "country", "company", "unknown_type"]

        for input_type in input_types:
            result = generator.get_next_value(f"element_{input_type}", is_mop=False, input_type=input_type)
            assert result is not None

            # Get a second value to ensure variety
            result2 = generator.get_next_value(f"element_{input_type}", is_mop=False, input_type=input_type)
            assert result2 is not None

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

class TestRVAgentStrategyIntegration:
    """Integration-style tests for RVAgentStrategy."""

    def _assert_item_action_equal(self, actual: ItemAction, expected: ItemAction, msg: str = ""):
        """Helper to compare ItemAction objects by their key attributes."""
        assert actual.id == expected.id, f"{msg}: Action ID mismatch"
        assert actual.event == expected.event, f"{msg}: Action Event mismatch"
        assert actual.text == expected.text, f"{msg}: Action Text mismatch"
        assert actual.coords_for_matching == expected.coords_for_matching, f"{msg}: Action Coordinates mismatch"
        # Add other critical attributes if necessary for logical equality
        assert actual.reaches_mop == expected.reaches_mop, f"{msg}: Action reaches_mop mismatch"
        assert actual.directly_reaches_mop == expected.directly_reaches_mop, f"{msg}: Action directly_reaches_mop mismatch"


    def test_full_cycle_deepen_and_backtrack(self):
        """
        Test a full cycle:
        1. Discover state A, select action to go to B
        2. Discover state B, exhaust it
        3. Backtrack to A
        4. Select another action in A
        """
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph, ui_coverage)

        # --- State A ---
        action_to_b = ItemAction(id=1, event=WidgetEventType.CLICK, text="to_b", reaches_mop=False, directly_reaches_mop=False, target_view={}, coordinates=(100,100), text_input=None)
        action_to_c = ItemAction(id=2, event=WidgetEventType.CLICK, text="to_c", reaches_mop=False, directly_reaches_mop=False, target_view={}, coordinates=(100,200), text_input=None)
        item_b = ScreenItem(view={"resource_id": "button_to_b"}, base_description="Button to B", actions=[action_to_b])
        item_c = ScreenItem(view={"resource_id": "button_to_c"}, base_description="Button to C", actions=[action_to_c])
        screen_a = ScreenDescription(activity="A", items=[item_b, item_c])
        
        # 1. Select action in A -> should be action_to_b
        selected_a1 = strategy.select_next_action("hash_a", screen_a)
        self._assert_item_action_equal(selected_a1, action_to_b, "First action in A")
        strategy.record_transition("hash_a", "hash_b", selected_a1)

        # --- State B ---
        action_in_b = ItemAction(id=3, event=WidgetEventType.CLICK, text="in_b", reaches_mop=False, directly_reaches_mop=False, target_view={}, coordinates=(100,300), text_input=None)
        item_in_b = ScreenItem(view={"resource_id": "button_in_b"}, base_description="Button in B", actions=[action_in_b])
        screen_b = ScreenDescription(activity="B", items=[item_in_b])

        # 2. Select action in B -> should be action_in_b
        selected_b1 = strategy.select_next_action("hash_b", screen_b)
        self._assert_item_action_equal(selected_b1, action_in_b, "Action in B")
        strategy.record_transition("hash_b", "hash_d", selected_b1) # Goes to some other state D

        # Now, re-enter state B, but it's exhausted
        # The strategy should return BACK
        selected_b2 = strategy.select_next_action("hash_b", screen_b)
        self._assert_item_action_equal(selected_b2, action_in_b, "Re-selected action in B after exhaustion") # Corrected assertion

        # 3. Check if we should backtrack from B -> True (exhausted)
        assert strategy.should_backtrack("hash_b") is True

        # --- Back in State A ---
        # 4. Select action again in A -> should now be action_to_c
        selected_a2 = strategy.select_next_action("hash_a", screen_a)
        self._assert_item_action_equal(selected_a2, action_to_c, "Second action in A")
        strategy.record_transition("hash_a", "hash_c", selected_a2)

        # Verify graph state
        assert "hash_a" in graph.states
        assert "hash_b" in graph.states
        assert len(graph.states["hash_a"].executed_actions) == 2
        assert len(graph.states["hash_b"].executed_actions) == 1
        assert len(graph.transitions) == 3

    def test_mop_action_is_prioritized_over_incomplete_successor(self):
        """
        Tests that MOP actions are prioritized over re-enabled actions
        from the SuccessorTracker.
        """
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph, ui_coverage)

        # --- State A: has a regular action and a MOP action ---
        action_successor = ItemAction(id=1, event=WidgetEventType.CLICK, text="to_b", reaches_mop=False, directly_reaches_mop=False, target_view={}, coordinates=(100,100), text_input=None)
        action_mop = ItemAction(id=2, event=WidgetEventType.CLICK, text="mop_action", reaches_mop=True, directly_reaches_mop=True, target_view={}, coordinates=(100,200), text_input=None)
        item_successor = ScreenItem(view={"resource_id": "item_successor_view"}, base_description="Successor Item", actions=[action_successor])
        item_mop = ScreenItem(view={"resource_id": "item_mop_view"}, base_description="MOP Item", actions=[action_mop])
        screen_a = ScreenDescription(activity="A", items=[item_successor, item_mop])

        # --- State B: successor state with one action ---
        action_in_b = ItemAction(id=3, event=WidgetEventType.CLICK, text="in_b", reaches_mop=False, directly_reaches_mop=False, target_view={}, coordinates=(100,300), text_input=None)
        item_in_b = ScreenItem(view={"resource_id": "item_in_b_view"}, base_description="Item in B", actions=[action_in_b])
        screen_b = ScreenDescription(activity="B", items=[item_in_b])

        # 1. Manually mark action_successor as executed and record its transition to B
        graph.get_or_create_state("hash_a", "A", screen_a)
        graph.record_action("hash_a", strategy._convert_signature_to_optimized(action_successor.coords_for_matching))
        strategy.record_transition("hash_a", "hash_b", action_successor)

        # 2. Partially explore State B
        graph.get_or_create_state("hash_b", "B", screen_b)
        graph.states["hash_b"].total_actions = 1 # Corrected: only one action in screen_b
        graph.record_action("hash_b", strategy._convert_signature_to_optimized(action_in_b.coords_for_matching)) # Execute one

        # Sanity check: State B is now 100% explored
        assert strategy.successor_tracker.get_successor_coverage("hash_b") == 1.0

        # 3. Now, select the next action from State A.
        # The SuccessorTracker will re-enable action_successor because hash_b is incomplete.
        # However, action_mop is an untested, high-priority action.
        selected_action = strategy.select_next_action("hash_a", screen_a)

        # 4. Assert that the MOP action was selected over the re-enabled one
        self._assert_item_action_equal(selected_action, action_mop, "MOP action priority")

    def test_input_value_exhaustion_leads_to_fallback(self):
        """
        Tests that when input values for a TEXT_CHANGE action are exhausted,
        the strategy marks the action as executed and falls back to another action (or BACK).
        """
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        # Set max_input_variations to a small number for testing
        strategy = RVAgentStrategy(graph, ui_coverage, max_input_variations=2)

        # --- State A: has a TEXT_CHANGE action and another CLICK action ---
        input_action = ItemAction(id=1, event=WidgetEventType.TEXT_CHANGE, text="Enter text", reaches_mop=False, directly_reaches_mop=False, target_view={}, coordinates=(100,100), text_input=None)
        other_action = ItemAction(id=2, event=WidgetEventType.CLICK, text="Click me", reaches_mop=False, directly_reaches_mop=False, target_view={}, coordinates=(100,200), text_input=None)
        item_input = ScreenItem(view={"resource_id": "input_field"}, base_description="Input Field", actions=[input_action])
        item_other = ScreenItem(view={"resource_id": "other_button"}, base_description="Other Button", actions=[other_action])
        screen_a = ScreenDescription(activity="A", items=[item_input, item_other])

        # 1. First call: should select input_action with first value
        selected_1 = strategy.select_next_action("hash_a", screen_a)
        self._assert_item_action_equal(selected_1, input_action, "First input action selection")
        assert selected_1.text_input is not None
        strategy.record_transition("hash_a", "hash_a_input1", selected_1) # Assume it stays on same screen

        # 2. Second call: should select input_action with second value
        selected_2 = strategy.select_next_action("hash_a", screen_a)
        self._assert_item_action_equal(selected_2, input_action, "Second input action selection")
        assert selected_2.text_input is not None
        assert selected_2.text_input != selected_1.text_input # Ensure different value
        strategy.record_transition("hash_a", "hash_a_input2", selected_2) # Assume it stays on same screen

        # 3. Third call: input values for input_action are exhausted.
        # Strategy should mark input_action as executed and select other_action.
        selected_3 = strategy.select_next_action("hash_a", screen_a)
        self._assert_item_action_equal(selected_3, other_action, "Fallback to other action after input exhaustion")
        
        # Verify input_action is now marked as executed in the graph
        node_a = graph.states["hash_a"]
        input_action_sig = strategy._convert_signature_to_optimized(input_action.coords_for_matching)
        assert input_action_sig in node_a.executed_actions

    def test_multiple_actions_same_incomplete_successor(self):
        """
        Cenário 4: Múltiplas Ações com o Mesmo Sucessor Incompleto

        Tests that when multiple actions lead to the same incomplete successor state,
        both actions are re-enabled by SuccessorTracker and can be selected again.

        Setup:
        - State A has two distinct actions (action_1 and action_2)
        - Both actions lead to State B
        - State B is partially explored (50% coverage)

        Expected:
        - When revisiting State A, both actions should be re-enabled
        - Strategy should select one of the re-enabled actions

        Note: We manually record transitions to ensure both actions get properly
        registered in the SuccessorTracker, simulating the scenario where both
        paths have been explored.
        """
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph, ui_coverage)

        # --- State A: has two actions that both lead to State B ---
        action_1 = ItemAction(
            id=1, event=WidgetEventType.CLICK, text="path_1_to_b",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(100, 100), text_input=None
        )
        action_2 = ItemAction(
            id=2, event=WidgetEventType.CLICK, text="path_2_to_b",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(100, 200), text_input=None
        )
        item_1 = ScreenItem(view={"resource_id": "button_1"}, base_description="Button 1", actions=[action_1])
        item_2 = ScreenItem(view={"resource_id": "button_2"}, base_description="Button 2", actions=[action_2])
        screen_a = ScreenDescription(activity="A", items=[item_1, item_2])

        # --- State B: has two actions (one will be executed, one not) ---
        action_b1 = ItemAction(
            id=3, event=WidgetEventType.CLICK, text="action_b1",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(100, 300), text_input=None
        )
        action_b2 = ItemAction(
            id=4, event=WidgetEventType.CLICK, text="action_b2",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(100, 400), text_input=None
        )
        item_b1 = ScreenItem(view={"resource_id": "button_b1"}, base_description="Button B1", actions=[action_b1])
        item_b2 = ScreenItem(view={"resource_id": "button_b2"}, base_description="Button B2", actions=[action_b2])
        screen_b = ScreenDescription(activity="B", items=[item_b1, item_b2])

        # Setup: Manually configure the graph and successor tracker to simulate
        # the scenario where both action_1 and action_2 have been executed and
        # both lead to state B (which is incomplete)

        # Create state A with both actions marked as executed
        node_a = graph.get_or_create_state("hash_a", "A", screen_a)
        action_1_sig = strategy._convert_signature_to_optimized(action_1.coords_for_matching)
        action_2_sig = strategy._convert_signature_to_optimized(action_2.coords_for_matching)
        graph.record_action("hash_a", action_1_sig)
        graph.record_action("hash_a", action_2_sig)

        # Create state B with only one action executed (50% coverage)
        node_b = graph.get_or_create_state("hash_b", "B", screen_b)
        action_b1_sig = strategy._convert_signature_to_optimized(action_b1.coords_for_matching)
        graph.record_action("hash_b", action_b1_sig)

        # Register that both action_1 and action_2 from A lead to B
        strategy.successor_tracker.record_successor("hash_a", action_1_sig, "hash_b")
        strategy.successor_tracker.record_successor("hash_a", action_2_sig, "hash_b")

        # Verify B is at 50% coverage
        coverage_b = strategy.successor_tracker.get_successor_coverage("hash_b")
        assert coverage_b == 0.5, f"Expected 50% coverage for B, got {coverage_b}"

        # Now test the core functionality:
        # 1. Both actions should be identified as having incomplete successors
        assert strategy.successor_tracker.has_incomplete_successors("hash_a") is True

        incomplete_actions = strategy.successor_tracker.get_incomplete_successors("hash_a")
        # Should have 2 actions with incomplete successors
        assert len(incomplete_actions) == 2, \
            f"Expected 2 actions with incomplete successors, got {len(incomplete_actions)}: {incomplete_actions}"

        # Verify both action signatures are in the incomplete set
        assert action_1_sig in incomplete_actions, \
            f"action_1_sig {action_1_sig} should be in incomplete_actions"
        assert action_2_sig in incomplete_actions, \
            f"action_2_sig {action_2_sig} should be in incomplete_actions"

        # 2. When selecting from A, the update_action_availability should re-enable both
        # and the strategy should select one of them
        selected = strategy.select_next_action("hash_a", screen_a)
        assert selected.id in [action_1.id, action_2.id], \
            f"Expected re-enabled action (1 or 2), got {selected.id}"

        # 3. After selection, verify re-enablement occurred
        # (the action should be removed from executed_actions temporarily)
        # Note: select_next_action marks the action as executed again, so we check
        # that it was re-enabled during the call (via update_action_availability)

    def test_plateau_detection_in_cyclic_loop_with_reactivation(self):
        """
        Cenário 6: Interação entre Plateau Detector e Successor Tracker em Loop

        Tests that PlateauDetector correctly identifies a plateau even when
        SuccessorTracker is actively re-enabling actions, but no new states
        or MOPs are being discovered.

        Setup:
        - Create a loop: State A -> action_1 -> State B -> action_2 -> State A
        - State B is always partially explored (triggers reactivation of action_1)
        - Agent cycles A -> B -> A -> B... without discovering new states/MOPs

        Expected:
        - After window_size iterations of cycling, PlateauDetector should detect plateau
        - Even though actions are being "reactivated" and executed, there's no real progress
        """
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph, ui_coverage)

        # Use a smaller window for testing
        strategy.plateau_detector = PlateauDetector(window_size=5)

        # --- State A: action that leads to B ---
        action_a_to_b = ItemAction(
            id=1, event=WidgetEventType.CLICK, text="go_to_b",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(100, 100), text_input=None
        )
        item_a = ScreenItem(view={"resource_id": "btn_a"}, base_description="Button A", actions=[action_a_to_b])
        screen_a = ScreenDescription(activity="A", items=[item_a])

        # --- State B: action that leads back to A, plus an unexplored action ---
        action_b_to_a = ItemAction(
            id=2, event=WidgetEventType.CLICK, text="go_to_a",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(100, 200), text_input=None
        )
        action_b_other = ItemAction(
            id=3, event=WidgetEventType.CLICK, text="other_in_b",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(100, 300), text_input=None
        )
        item_b1 = ScreenItem(view={"resource_id": "btn_b1"}, base_description="Button B1", actions=[action_b_to_a])
        item_b2 = ScreenItem(view={"resource_id": "btn_b2"}, base_description="Button B2", actions=[action_b_other])
        screen_b = ScreenDescription(activity="B", items=[item_b1, item_b2])

        # Initial setup: discover both states
        # First iteration: A -> B (discovers B)
        selected = strategy.select_next_action("hash_a", screen_a)
        strategy.record_transition("hash_a", "hash_b", selected)
        # Record iteration with new state discovery
        strategy.plateau_detector.record_iteration(discovered_new_state=True, new_mop_method=None)

        # Second iteration: B -> A (back to known state)
        selected = strategy.select_next_action("hash_b", screen_b)
        self._assert_item_action_equal(selected, action_b_to_a, "First action in B should be action_b_to_a")
        strategy.record_transition("hash_b", "hash_a", selected)
        # No new state discovered
        strategy.plateau_detector.record_iteration(discovered_new_state=False, new_mop_method=None)

        # State B still has action_b_other unexplored (50% coverage)
        coverage_b = strategy.successor_tracker.get_successor_coverage("hash_b")
        assert coverage_b == 0.5, f"Expected 50% coverage for B, got {coverage_b}"

        # Verify that action_a_to_b is re-enabled (leads to incomplete B)
        assert strategy.successor_tracker.has_incomplete_successors("hash_a") is True

        # Now simulate the loop: keep cycling A -> B -> A without new discoveries
        # The SuccessorTracker will keep re-enabling action_a_to_b
        # but PlateauDetector should still detect plateau after window_size iterations

        for i in range(strategy.plateau_detector.window_size):
            # A -> B (re-enabled action)
            selected = strategy.select_next_action("hash_a", screen_a)
            strategy.record_transition("hash_a", "hash_b", selected)
            strategy.plateau_detector.record_iteration(discovered_new_state=False, new_mop_method=None)

            # B -> A
            selected = strategy.select_next_action("hash_b", screen_b)
            strategy.record_transition("hash_b", "hash_a", selected)
            strategy.plateau_detector.record_iteration(discovered_new_state=False, new_mop_method=None)

        # After window_size cycles (2 * window_size iterations) of no progress,
        # plateau should be detected
        assert strategy.plateau_detector.is_plateau_reached() is True, \
            "PlateauDetector should detect plateau after cycling without new discoveries"

        # Verify that the loop was indeed happening (actions were being executed)
        node_a = graph.states["hash_a"]
        node_b = graph.states["hash_b"]

        # action_a_to_b should have been executed multiple times
        action_a_sig = strategy._convert_signature_to_optimized(action_a_to_b.coords_for_matching)
        assert action_a_sig in node_a.executed_actions, "action_a_to_b should be marked as executed"

        # action_b_to_a should have been executed multiple times
        action_b_sig = strategy._convert_signature_to_optimized(action_b_to_a.coords_for_matching)
        assert action_b_sig in node_b.executed_actions, "action_b_to_a should be marked as executed"

    def test_comprehensive_action_filtering(self):
        """
        Cenário 7: Filtragem Abrangente de Ações (Pacotes Externos e Sistema)

        Tests that actions from external packages and system actions are correctly
        filtered and never selected by the strategy.

        Filters tested:
        1. Actions from target package - INCLUDED
        2. Actions from external package (e.g., com.android.systemui) - EXCLUDED
        3. Actions in navigation bar area (y > 1800) - EXCLUDED
        4. Actions in status bar area (y < 100) - EXCLUDED
        5. Actions with coordinates=None - EXCLUDED
        """
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph, ui_coverage, target_package="com.example.app")

        # Create actions with different filtering criteria
        # 1. Valid action from target package (should be INCLUDED)
        action_valid = ItemAction(
            id=1, event=WidgetEventType.CLICK, text="valid_action",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(500, 500), text_input=None
        )
        item_valid = ScreenItem(
            view={"resource_id": "btn_valid", "package": "com.example.app"},
            base_description="Valid Button",
            actions=[action_valid]
        )

        # 2. Action from external package (should be EXCLUDED)
        action_external = ItemAction(
            id=2, event=WidgetEventType.CLICK, text="external_action",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(500, 600), text_input=None
        )
        item_external = ScreenItem(
            view={"resource_id": "btn_external", "package": "com.android.systemui"},
            base_description="External Button",
            actions=[action_external]
        )

        # 3. Action in navigation bar (y > 1800) (should be EXCLUDED)
        action_navbar = ItemAction(
            id=3, event=WidgetEventType.CLICK, text="navbar_action",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(500, 1850), text_input=None
        )
        item_navbar = ScreenItem(
            view={"resource_id": "btn_navbar", "package": "com.example.app"},
            base_description="NavBar Button",
            actions=[action_navbar]
        )

        # 4. Action in status bar (y < 100) (should be EXCLUDED)
        action_statusbar = ItemAction(
            id=4, event=WidgetEventType.CLICK, text="statusbar_action",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(500, 50), text_input=None
        )
        item_statusbar = ScreenItem(
            view={"resource_id": "btn_statusbar", "package": "com.example.app"},
            base_description="StatusBar Button",
            actions=[action_statusbar]
        )

        # 5. Action with coordinates=None (should be EXCLUDED)
        action_no_coords = ItemAction(
            id=5, event=WidgetEventType.CLICK, text="no_coords_action",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=None, text_input=None
        )
        item_no_coords = ScreenItem(
            view={"resource_id": "btn_no_coords", "package": "com.example.app"},
            base_description="No Coords Button",
            actions=[action_no_coords]
        )

        # Create screen with all items
        screen = ScreenDescription(
            activity="TestActivity",
            items=[item_valid, item_external, item_navbar, item_statusbar, item_no_coords]
        )

        # Create state node
        node = graph.get_or_create_state("hash_test", "TestActivity", screen)

        # Test _get_untested_actions - should only return valid action
        untested = strategy._get_untested_actions(node, screen)
        assert len(untested) == 1, f"Expected 1 untested action, got {len(untested)}"
        assert untested[0].id == action_valid.id, "Only valid action should be returned"

        # Test _get_all_filtered_actions - should only return valid action
        filtered = strategy._get_all_filtered_actions(screen)
        assert len(filtered) == 1, f"Expected 1 filtered action, got {len(filtered)}"
        assert filtered[0].id == action_valid.id, "Only valid action should be returned"

        # Test _is_system_action for each case
        assert strategy._is_system_action(action_valid) is False, "Valid action should not be system"
        assert strategy._is_system_action(action_navbar) is True, "NavBar action should be system"
        assert strategy._is_system_action(action_statusbar) is True, "StatusBar action should be system"
        assert strategy._is_system_action(action_no_coords) is True, "No coords action should be system"

        # Test that select_next_action returns the valid action
        selected = strategy.select_next_action("hash_test", screen)
        assert selected.id == action_valid.id, \
            f"Expected valid action (id=1), got action with id={selected.id}"

    def test_wtg_guided_action_prioritization(self):
        """
        Cenário 8: Priorização de Ações Guiadas por WTG (TransitionManager)

        Tests that when TransitionManager is configured and provides guidance,
        actions that lead to unvisited screens are prioritized over regular
        untested actions.

        Setup:
        - State A has three actions:
          1. action_regular - regular untested action
          2. action_tested - already executed action
          3. action_wtg - action that TransitionManager suggests leads to unvisited screen

        Expected:
        - Strategy should select action_wtg due to WTG guidance (Priority 3)
        - Even though action_regular is also untested (would be Priority 4)
        """
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        # Create a mock TransitionManager
        mock_transition_manager = MagicMock()

        # Create actions
        action_regular = ItemAction(
            id=1, event=WidgetEventType.CLICK, text="regular_action",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(100, 100), text_input=None
        )
        action_tested = ItemAction(
            id=2, event=WidgetEventType.CLICK, text="tested_action",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(100, 200), text_input=None
        )
        action_wtg = ItemAction(
            id=3, event=WidgetEventType.CLICK, text="wtg_guided_action",
            reaches_mop=False, directly_reaches_mop=False,
            target_view={}, coordinates=(100, 300), text_input=None
        )

        item_regular = ScreenItem(
            view={"resource_id": "btn_regular"},
            base_description="Regular Button",
            actions=[action_regular]
        )
        item_tested = ScreenItem(
            view={"resource_id": "btn_tested"},
            base_description="Tested Button",
            actions=[action_tested]
        )
        item_wtg = ScreenItem(
            view={"resource_id": "btn_wtg"},
            base_description="WTG Button",
            actions=[action_wtg]
        )

        screen = ScreenDescription(
            activity="TestActivity",
            items=[item_regular, item_tested, item_wtg]
        )

        # Configure mock TransitionManager to suggest action_wtg
        # The get_navigation_guidance method should return guidance that
        # matches action_wtg's coordinates
        mock_guidance = MagicMock()
        mock_guidance.has_guidance = True
        mock_guidance.suggested_actions = [
            {"widget_id": "btn_wtg", "target_window": "UnvisitedActivity", "priority": 1}
        ]
        mock_transition_manager.get_navigation_guidance.return_value = mock_guidance

        # Create strategy with mock TransitionManager
        strategy = RVAgentStrategy(
            graph, ui_coverage,
            transition_manager=mock_transition_manager
        )

        # Mock _get_wtg_guided_action to return action_wtg
        # This simulates the TransitionManager finding a match
        original_get_wtg = strategy._get_wtg_guided_action
        def mock_get_wtg_guided_action(actions, screen_desc):
            # Return action_wtg if it's in the candidate actions
            for action in actions:
                if action.id == action_wtg.id:
                    return action
            return None
        strategy._get_wtg_guided_action = mock_get_wtg_guided_action

        # Pre-mark action_tested as executed
        node = graph.get_or_create_state("hash_test", "TestActivity", screen)
        action_tested_sig = strategy._convert_signature_to_optimized(action_tested.coords_for_matching)
        graph.record_action("hash_test", action_tested_sig)

        # Now select_next_action should prioritize action_wtg
        # Even though action_regular is also untested
        selected = strategy.select_next_action("hash_test", screen)

        # The WTG-guided action should be selected (Priority 3 > Priority 4)
        assert selected.id == action_wtg.id, \
            f"Expected WTG-guided action (id=3), got action with id={selected.id}"

        # Verify the order of priorities by testing without WTG guidance
        strategy._get_wtg_guided_action = lambda a, s: None  # Disable WTG guidance

        # Reset executed actions to test fresh
        node.executed_actions.clear()

        # Now without WTG guidance, action_regular should be selected first
        # (as the first untested action in Priority 4)
        selected_no_wtg = strategy.select_next_action("hash_test", screen)
        assert selected_no_wtg.id == action_regular.id, \
            f"Without WTG, expected regular action (id=1), got action with id={selected_no_wtg.id}"
