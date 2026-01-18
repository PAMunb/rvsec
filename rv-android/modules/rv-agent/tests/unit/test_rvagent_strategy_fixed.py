"""
Unit tests for RVAgentStrategy functionality.

Tests the RVAgentStrategy class which implements the core exploration strategy.
"""

import pytest
from unittest.mock import MagicMock
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.ui_coverage import UICoverageTracker


class TestRVAgentStrategyInitialization:
    """Test RVAgentStrategy initialization and setup."""

    def test_initialization_with_required_params(self):
        """RVAgentStrategy initializes with required parameters."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Verify initialization
        assert strategy.graph == mock_graph
        assert strategy.ui_coverage == mock_ui_coverage
        assert strategy.current_depth == 0
        assert strategy.previous_hash is None
        assert strategy.state_stack == []
        assert strategy.visited_states == set()

    def test_initialization_with_optional_params(self):
        """RVAgentStrategy initializes with optional parameters."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        mock_converter = MagicMock()
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage,
            coordinate_converter=mock_converter,
            plateau_window=20,
            max_input_variations=5,
            target_package="com.example.test",
            device_dimensions=(720, 1280),
            stochastic_probability=0.5,
            stochastic_temperature=1.5
        )
        
        assert strategy.graph == mock_graph
        assert strategy.ui_coverage == mock_ui_coverage
        assert strategy.converter == mock_converter
        assert strategy.stochastic_probability == 0.5
        assert strategy.stochastic_temperature == 1.5
        assert strategy.target_package == "com.example.test"
        assert strategy.device_dimensions == (720, 1280)


class TestRVAgentStrategyCoreMethods:
    """Test RVAgentStrategy core methods."""

    def test_select_next_action_method_exists(self):
        """RVAgentStrategy has select_next_action method."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Verify the method exists
        assert hasattr(strategy, 'select_next_action')
        assert callable(getattr(strategy, 'select_next_action'))

    def test_record_transition_method_exists(self):
        """RVAgentStrategy has record_transition method."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Verify the method exists
        assert hasattr(strategy, 'record_transition')
        assert callable(getattr(strategy, 'record_transition'))

    def test_should_backtrack_method_exists(self):
        """RVAgentStrategy has should_backtrack method."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Verify the method exists
        assert hasattr(strategy, 'should_backtrack')
        assert callable(getattr(strategy, 'should_backtrack'))

    def test_reset_method_exists(self):
        """RVAgentStrategy has reset method."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Verify the method exists
        assert hasattr(strategy, 'reset')
        assert callable(getattr(strategy, 'reset'))

    def test_get_statistics_method_exists(self):
        """RVAgentStrategy has get_statistics method."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Verify the method exists
        assert hasattr(strategy, 'get_statistics')
        assert callable(getattr(strategy, 'get_statistics'))


class TestRVAgentStrategyActionSelection:
    """Test RVAgentStrategy action selection functionality."""

    def test_select_next_action_with_empty_state(self):
        """RVAgentStrategy handles empty state for action selection."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Mock the required attributes and methods
        strategy.graph.states = {}
        strategy._get_all_filtered_actions = MagicMock(return_value=[])
        strategy._get_untested_actions = MagicMock(return_value=[])
        strategy.plateau_detector = MagicMock()
        strategy.plateau_detector.has_plateau.return_value = False

        # Create mock screen description
        mock_screen_desc = MagicMock()

        result = strategy.select_next_action(
            current_hash="test_hash",
            screen_desc=mock_screen_desc
        )

        # When no actions are available, it might return a back action or None depending on internal logic
        # The important thing is that it doesn't crash
        assert result is not None  # Method should return some action (likely BACK action)


class TestRVAgentStrategyTransitionRecording:
    """Test RVAgentStrategy transition recording functionality."""

    def test_record_transition_updates_previous_hash(self):
        """RVAgentStrategy updates previous hash when recording transition."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Initially previous_hash should be None
        assert strategy.previous_hash is None
        
        # Mock the graph's record_transition method
        strategy.graph.record_transition = MagicMock()
        strategy._convert_signature_to_optimized = MagicMock(return_value=((100, 200), "click"))

        # Create mock action with proper attributes
        mock_action = MagicMock()
        mock_action.coords_for_matching = ((100, 200), "click")

        # Call record_transition
        strategy.record_transition("hash1", "hash2", mock_action)
        
        # Verify previous_hash was updated to from_hash (not to_hash)
        assert strategy.previous_hash == "hash1"

    def test_record_transition_calls_graph_record(self):
        """RVAgentStrategy calls graph record_transition method."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Mock the graph's record_transition method
        strategy.graph.record_transition = MagicMock()
        strategy._convert_signature_to_optimized = MagicMock(return_value=((100, 200), "click"))

        # Create mock action with proper attributes
        mock_action = MagicMock()
        mock_action.coords_for_matching = ((100, 200), "click")

        # Call record_transition
        strategy.record_transition("hash1", "hash2", mock_action)
        
        # Verify graph record_transition was called with correct parameters
        strategy.graph.record_transition.assert_called_once_with("hash1", "hash2", [{"action": mock_action}])


class TestRVAgentStrategyBacktrackLogic:
    """Test RVAgentStrategy backtrack logic."""

    def test_should_backtrack_with_known_hash(self):
        """RVAgentStrategy determines if backtracking is needed for known hash."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Mock the graph to have states dictionary
        mock_states = MagicMock()
        mock_states.get.return_value = MagicMock()
        strategy.graph.states = mock_states
        strategy.successor_tracker = MagicMock()
        strategy.successor_tracker.has_incomplete_successors.return_value = False

        # Mock the node properties
        mock_node = MagicMock()
        mock_node.executed_actions = []
        mock_node.total_actions = 5
        mock_states.get.return_value = mock_node

        # Call should_backtrack
        result = strategy.should_backtrack("known_hash")

        # Should return True if exhausted (executed_actions >= total_actions)
        # or False if not exhausted
        # In this case, with 0 executed actions and 5 total actions, it should return False
        assert result is False

    def test_should_backtrack_with_unknown_hash(self):
        """RVAgentStrategy determines if backtracking is needed for unknown hash."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Mock the graph to have states dictionary
        mock_states = MagicMock()
        strategy.graph.states = mock_states
        strategy.successor_tracker = MagicMock()
        strategy.successor_tracker.has_incomplete_successors.return_value = False

        # Mock the get method to return None for unknown hash
        mock_states.get.return_value = None

        # Call should_backtrack
        result = strategy.should_backtrack("unknown_hash")

        # Should return True since state is not in graph
        assert result is True


class TestRVAgentStrategyReset:
    """Test RVAgentStrategy reset functionality."""

    def test_reset_clears_state(self):
        """RVAgentStrategy reset clears internal state."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Set some state
        strategy.current_depth = 5
        strategy.previous_hash = "some_hash"
        strategy.state_stack = [MagicMock()]
        strategy.visited_states = {"state1", "state2"}
        
        # Call reset
        strategy.reset()
        
        # Verify state was cleared
        assert strategy.current_depth == 0
        assert strategy.previous_hash is None
        assert strategy.state_stack == []
        assert strategy.visited_states == set()


class TestRVAgentStrategyStatistics:
    """Test RVAgentStrategy statistics functionality."""

    def test_get_statistics_returns_dict(self):
        """RVAgentStrategy get_statistics returns a dictionary."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Mock the coverage_metrics get_statistics method
        strategy.coverage_metrics = MagicMock()
        strategy.coverage_metrics.get_comprehensive_metrics.return_value = {
            "states_visited": 5,
            "actions_executed": 10,
            "coverage_percentage": 25.0
        }

        # Call get_statistics
        stats = strategy.get_statistics()

        # Verify it returns a dictionary
        assert isinstance(stats, dict)
        # The actual method returns a comprehensive dictionary with many keys
        # Just verify it has the expected structure
        assert "coverage" in stats
        assert "depth" in stats
        assert "plateau" in stats