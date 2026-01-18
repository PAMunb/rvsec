"""
Unit tests for RVAgentStrategy functionality.

Tests the RVAgentStrategy class which implements the core exploration strategy.
"""

import pytest
from unittest.mock import MagicMock, patch
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
        assert strategy.iteration_count == 0
        assert strategy.current_depth == 0
        assert strategy.current_iteration == 0

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
            max_input_variations=5
        )
        
        assert strategy.graph == mock_graph
        assert strategy.ui_coverage == mock_ui_coverage
        assert strategy.coordinate_converter == mock_converter
        assert strategy.plateau_window == 20
        assert strategy.max_input_variations == 5


class TestRVAgentStrategyCoreMethods:
    """Test RVAgentStrategy core methods."""

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    def test_select_next_action_method_exists(self, mock_action_normalizer, mock_screen_processor):
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

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    def test_record_transition_method_exists(self, mock_action_normalizer, mock_screen_processor):
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

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    def test_should_backtrack_method_exists(self, mock_action_normalizer, mock_screen_processor):
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

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    def test_reset_method_exists(self, mock_action_normalizer, mock_screen_processor):
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

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    def test_get_statistics_method_exists(self, mock_action_normalizer, mock_screen_processor):
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

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ItemAction')
    def test_select_next_action_with_screen_description(self, mock_item_action, mock_action_normalizer, mock_screen_processor):
        """RVAgentStrategy selects next action with screen description."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Create a mock screen description
        mock_screen_desc = MagicMock()
        
        # Mock the internal methods that would be called
        strategy._get_untested_actions = MagicMock(return_value=[])
        
        # Call select_next_action with screen description
        result = strategy.select_next_action(screen_desc=mock_screen_desc)
        
        # Verify that the method returns a valid result
        assert result is not None


class TestRVAgentStrategyTransitionRecording:
    """Test RVAgentStrategy transition recording functionality."""

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    def test_record_transition_updates_iteration_count(self, mock_action_normalizer, mock_screen_processor):
        """RVAgentStrategy updates iteration count when recording transition."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        initial_count = strategy.iteration_count
        
        # Mock the graph's record_transition method
        strategy.graph.record_transition = MagicMock()
        
        # Call record_transition
        strategy.record_transition("hash1", "hash2", MagicMock())
        
        # Verify iteration count was incremented
        assert strategy.iteration_count == initial_count + 1

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    def test_record_transition_calls_graph_record(self, mock_action_normalizer, mock_screen_processor):
        """RVAgentStrategy calls graph record_transition method."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Mock the graph's record_transition method
        strategy.graph.record_transition = MagicMock()
        
        # Create mock action
        mock_action = MagicMock()
        
        # Call record_transition
        strategy.record_transition("hash1", "hash2", mock_action)
        
        # Verify graph record_transition was called with correct parameters
        strategy.graph.record_transition.assert_called_once_with("hash1", "hash2", mock_action)


class TestRVAgentStrategyBacktrackLogic:
    """Test RVAgentStrategy backtrack logic."""

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    def test_should_backtrack_with_known_hash(self, mock_action_normalizer, mock_screen_processor):
        """RVAgentStrategy determines if backtracking is needed for known hash."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Mock the graph to return a known state
        strategy.graph.get_state_by_hash = MagicMock(return_value=MagicMock())
        
        # Call should_backtrack
        result = strategy.should_backtrack("known_hash")
        
        # Should return False since it's a known state
        assert result is False

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    def test_should_backtrack_with_unknown_hash(self, mock_action_normalizer, mock_screen_processor):
        """RVAgentStrategy determines if backtracking is needed for unknown hash."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Mock the graph to return None for unknown state
        strategy.graph.get_state_by_hash = MagicMock(return_value=None)
        
        # Call should_backtrack
        result = strategy.should_backtrack("unknown_hash")
        
        # Should return False since it's an unknown state (new state)
        assert result is False


class TestRVAgentStrategyReset:
    """Test RVAgentStrategy reset functionality."""

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    def test_reset_clears_iteration_count(self, mock_action_normalizer, mock_screen_processor):
        """RVAgentStrategy reset clears iteration count."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Set a non-zero iteration count
        strategy.iteration_count = 10
        strategy.current_depth = 5
        
        # Call reset
        strategy.reset()
        
        # Verify counts were reset
        assert strategy.iteration_count == 0
        assert strategy.current_depth == 0


class TestRVAgentStrategyStatistics:
    """Test RVAgentStrategy statistics functionality."""

    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ScreenProcessor')
    @patch('rv_agent.strategies.rvagent_strategy.rvagent_strategy.ActionNormalizer')
    def test_get_statistics_returns_dict(self, mock_action_normalizer, mock_screen_processor):
        """RVAgentStrategy get_statistics returns a dictionary."""
        mock_graph = MagicMock(spec=DynamicStateGraph)
        mock_ui_coverage = MagicMock(spec=UICoverageTracker)
        
        strategy = RVAgentStrategy(
            graph=mock_graph,
            ui_coverage=mock_ui_coverage
        )
        
        # Mock the graph's get_statistics method
        strategy.graph.get_statistics = MagicMock(return_value={"nodes": 5, "edges": 10})
        
        # Call get_statistics
        stats = strategy.get_statistics()
        
        # Verify it returns a dictionary
        assert isinstance(stats, dict)
        assert "nodes" in stats
        assert "edges" in stats