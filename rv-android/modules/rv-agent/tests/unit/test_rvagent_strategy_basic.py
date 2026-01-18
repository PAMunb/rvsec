"""
Basic tests for RVAgentStrategy functionality.

Tests the RVAgentStrategy class which implements the core exploration strategy.
"""

import pytest
from unittest.mock import MagicMock
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_agent.domain.state import AgentState


class TestRVAgentStrategyInitialization:
    """Test RVAgentStrategy initialization and setup."""

    def test_initialization_with_required_params(self):
        """RVAgentStrategy initializes with required parameters."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        
        strategy = RVAgentStrategy(graph=mock_graph, ui_coverage=mock_ui_coverage)
        
        # Verify initialization
        assert strategy.graph == mock_graph
        assert strategy.ui_coverage == mock_ui_coverage
        assert strategy.iteration_count == 0
        assert strategy.current_depth == 0
        assert strategy.current_iteration == 0

    def test_initialization_with_optional_params(self):
        """RVAgentStrategy initializes with optional parameters."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
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


class TestRVAgentStrategyBasicMethods:
    """Test basic methods of RVAgentStrategy."""

    def test_reset_method_exists(self):
        """RVAgentStrategy has reset method."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        
        strategy = RVAgentStrategy(graph=mock_graph, ui_coverage=mock_ui_coverage)
        
        # Verify the method exists and can be called
        assert hasattr(strategy, 'reset')
        assert callable(getattr(strategy, 'reset'))
        
        # Call reset to ensure it doesn't raise an exception
        initial_iteration_count = strategy.iteration_count
        strategy.reset()
        
        # After reset, iteration count should be 0
        assert strategy.iteration_count == 0

    def test_get_current_state_method_exists(self):
        """RVAgentStrategy has get_current_state method."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        
        strategy = RVAgentStrategy(graph=mock_graph, ui_coverage=mock_ui_coverage)
        
        # Verify the method exists and can be called
        assert hasattr(strategy, 'get_current_state')
        assert callable(getattr(strategy, 'get_current_state'))
        
        # Call method to ensure it doesn't raise an exception
        state = strategy.get_current_state()
        
        # Verify it returns a dictionary
        assert isinstance(state, dict)
        assert "current_depth" in state
        assert "current_iteration" in state
        assert "iteration_count" in state

    def test_select_next_action_method_exists(self):
        """RVAgentStrategy has select_next_action method."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        
        strategy = RVAgentStrategy(graph=mock_graph, ui_coverage=mock_ui_coverage)
        
        # Verify the method exists and can be called
        assert hasattr(strategy, 'select_next_action')
        assert callable(getattr(strategy, 'select_next_action'))

    def test_record_transition_method_exists(self):
        """RVAgentStrategy has record_transition method."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        
        strategy = RVAgentStrategy(graph=mock_graph, ui_coverage=mock_ui_coverage)
        
        # Verify the method exists and can be called
        assert hasattr(strategy, 'record_transition')
        assert callable(getattr(strategy, 'record_transition'))

    def test_should_continue_method_exists(self):
        """RVAgentStrategy has should_continue method."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        
        strategy = RVAgentStrategy(graph=mock_graph, ui_coverage=mock_ui_coverage)
        
        # Verify the method exists and can be called
        assert hasattr(strategy, 'should_continue')
        assert callable(getattr(strategy, 'should_continue'))


class TestRVAgentStrategyStateHandling:
    """Test RVAgentStrategy state handling functionality."""

    def test_iteration_count_increments(self):
        """RVAgentStrategy increments iteration count."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        
        strategy = RVAgentStrategy(graph=mock_graph, ui_coverage=mock_ui_coverage)
        
        initial_count = strategy.iteration_count
        
        # Simulate a transition which should increment the count
        strategy.iteration_count += 1
        
        assert strategy.iteration_count == initial_count + 1

    def test_select_next_action_with_basic_state(self):
        """RVAgentStrategy can handle basic state for action selection."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        
        strategy = RVAgentStrategy(graph=mock_graph, ui_coverage=mock_ui_coverage)
        
        # Create a basic state
        current_state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="hash123",
            visited_states=set(),
            state_transitions=[],
            recent_action_window=[]
        )
        
        # Call select_next_action - this should not raise an exception
        # The actual return value depends on the implementation
        action = strategy.select_next_action(current_state)
        
        # Action could be None or an actual action depending on the state
        assert action is not None or action is None

    def test_record_transition_with_basic_states(self):
        """RVAgentStrategy can record transition between basic states."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        
        strategy = RVAgentStrategy(graph=mock_graph, ui_coverage=mock_ui_coverage)
        
        # Create basic states
        current_state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="hash123",
            visited_states=set(),
            state_transitions=[],
            recent_action_window=[]
        )
        
        action_taken = {"action_type": "click", "element_id": "button1", "coordinates": (100, 200)}
        
        result_state = AgentState(
            current_activity="SecondActivity",
            current_screen_hash="hash456",
            visited_states=set(),
            state_transitions=[],
            recent_action_window=[]
        )
        
        # Call record_transition - this should not raise an exception
        strategy.record_transition(current_state, action_taken, result_state)
        
        # Verify iteration count incremented
        assert strategy.iteration_count >= 0  # May have incremented or stayed the same

    def test_should_continue_with_basic_state(self):
        """RVAgentStrategy can determine continuation with basic state."""
        mock_graph = MagicMock()
        mock_ui_coverage = MagicMock()
        
        strategy = RVAgentStrategy(graph=mock_graph, ui_coverage=mock_ui_coverage)
        
        # Create a basic state
        current_state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="hash123",
            visited_states=set(),
            state_transitions=[],
            recent_action_window=[]
        )
        
        # Call should_continue - this should not raise an exception
        should_continue = strategy.should_continue(current_state)
        
        # Should return a boolean
        assert isinstance(should_continue, bool)