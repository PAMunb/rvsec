"""
Unit tests for DFSStrategy.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass

from rv_agent.strategies.dfs_strategy import DFSStrategy, DFSState
from rv_agent.core.dynamic_state_graph import DynamicStateGraph


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_graph():
    """Create a mock DynamicStateGraph."""
    graph = MagicMock(spec=DynamicStateGraph)
    graph.states = {}
    graph.transitions = []
    return graph


@pytest.fixture
def mock_screen_node():
    """Create a mock ScreenNode."""
    node = MagicMock()
    node.total_actions = 5
    node.visit_count = 1
    node.executed_actions = set()
    return node


@pytest.fixture
def mock_action():
    """Create a mock ItemAction."""
    action = MagicMock()
    action.id = 1
    action.action_type = "CLICK"
    action.bounds = [[100, 100], [200, 200]]
    action.target_view = {'class': 'android.widget.Button', 'system_action': False}
    action.get_execution_coordinates.return_value = (150, 150)
    action.coords_for_matching = ((150, 150), "CLICK")
    action.directly_reaches_mop = False
    action.reaches_mop = False
    return action


@pytest.fixture
def mock_screen_desc(mock_action):
    """Create a mock ScreenDescription."""
    screen_desc = MagicMock()
    screen_desc.activity = "com.example.MainActivity"
    screen_desc.get_all_actions.return_value = [mock_action]
    screen_desc.items = []
    return screen_desc


@pytest.fixture
def dfs_strategy(mock_graph):
    """Create a DFSStrategy instance."""
    return DFSStrategy(graph=mock_graph)


# =============================================================================
# DFSState Dataclass Tests
# =============================================================================

class TestDFSState:
    """Tests for DFSState dataclass."""

    def test_creation(self):
        """Test DFSState creation."""
        state = DFSState(
            screen_hash="abc123",
            depth=3,
            parent_hash="parent123",
            untested_count=5
        )

        assert state.screen_hash == "abc123"
        assert state.depth == 3
        assert state.parent_hash == "parent123"
        assert state.untested_count == 5

    def test_creation_no_parent(self):
        """Test DFSState creation without parent."""
        state = DFSState(
            screen_hash="root",
            depth=0,
            parent_hash=None,
            untested_count=10
        )

        assert state.parent_hash is None
        assert state.depth == 0


# =============================================================================
# DFSStrategy Initialization Tests
# =============================================================================

class TestDFSStrategyInit:
    """Tests for DFSStrategy initialization."""

    def test_init_basic(self, mock_graph):
        """Test basic initialization."""
        strategy = DFSStrategy(graph=mock_graph)

        assert strategy.graph == mock_graph
        assert strategy.static_data is None
        assert strategy.converter is None
        assert strategy.state_stack == []
        assert strategy.visited_states == set()
        assert strategy.current_depth == 0

    def test_init_with_static_data(self, mock_graph):
        """Test initialization with static data."""
        static_data = MagicMock()
        strategy = DFSStrategy(graph=mock_graph, static_data=static_data)

        assert strategy.static_data == static_data

    def test_init_with_converter(self, mock_graph):
        """Test initialization with coordinate converter."""
        converter = MagicMock()
        strategy = DFSStrategy(graph=mock_graph, coordinate_converter=converter)

        assert strategy.converter == converter


# =============================================================================
# Reset Tests
# =============================================================================

class TestDFSStrategyReset:
    """Tests for DFSStrategy.reset()."""

    def test_reset_clears_state(self, dfs_strategy):
        """Test that reset clears all state."""
        # Add some state
        dfs_strategy.state_stack.append(DFSState("hash1", 1, None, 5))
        dfs_strategy.visited_states.add("hash1")
        dfs_strategy.current_depth = 3

        dfs_strategy.reset()

        assert dfs_strategy.state_stack == []
        assert dfs_strategy.visited_states == set()
        assert dfs_strategy.current_depth == 0


# =============================================================================
# Filter Actions Tests
# =============================================================================

class TestDFSStrategyFilterActions:
    """Tests for DFSStrategy._filter_actions()."""

    def test_filter_keeps_regular_actions(self, dfs_strategy, mock_action):
        """Test that regular actions are kept."""
        actions = [mock_action]
        filtered = dfs_strategy._filter_actions(actions)

        assert len(filtered) == 1
        assert filtered[0] == mock_action

    def test_filter_removes_system_actions(self, dfs_strategy):
        """Test that system actions are filtered."""
        action = MagicMock()
        action.target_view = {'system_action': True}
        action.get_execution_coordinates.return_value = (100, 100)

        actions = [action]
        filtered = dfs_strategy._filter_actions(actions)

        assert len(filtered) == 0

    def test_filter_removes_actions_without_coords(self, dfs_strategy):
        """Test that actions without coordinates are filtered."""
        action = MagicMock()
        action.target_view = {'system_action': False}
        action.get_execution_coordinates.return_value = None

        actions = [action]
        filtered = dfs_strategy._filter_actions(actions)

        assert len(filtered) == 0

    def test_filter_removes_navbar_actions(self, dfs_strategy):
        """Test that navigation bar actions are filtered (y > 1794)."""
        action = MagicMock()
        action.target_view = {'system_action': False}
        action.get_execution_coordinates.return_value = (540, 1850)  # In navbar

        actions = [action]
        filtered = dfs_strategy._filter_actions(actions)

        assert len(filtered) == 0

    def test_filter_keeps_above_navbar(self, dfs_strategy):
        """Test that actions above navbar are kept."""
        action = MagicMock()
        action.target_view = {'system_action': False}
        action.get_execution_coordinates.return_value = (540, 1700)  # Above navbar

        actions = [action]
        filtered = dfs_strategy._filter_actions(actions)

        assert len(filtered) == 1


# =============================================================================
# Get Untested Actions Tests
# =============================================================================

class TestDFSStrategyGetUntestedActions:
    """Tests for DFSStrategy._get_untested_actions()."""

    def test_all_actions_untested(self, dfs_strategy, mock_screen_node, mock_action):
        """Test when all actions are untested."""
        mock_screen_node.executed_actions = set()

        untested = dfs_strategy._get_untested_actions(mock_screen_node, [mock_action])

        assert len(untested) == 1

    def test_all_actions_tested(self, dfs_strategy, mock_screen_node, mock_action):
        """Test when all actions have been tested."""
        # Mark action as executed (in optimized space)
        optimized_sig = ((97, 97), "CLICK")  # 150 * 704/1080, 150 * 1248/1920
        mock_screen_node.executed_actions = {optimized_sig}

        untested = dfs_strategy._get_untested_actions(mock_screen_node, [mock_action])

        assert len(untested) == 0

    def test_mixed_tested_untested(self, dfs_strategy, mock_screen_node):
        """Test with mix of tested and untested actions."""
        action1 = MagicMock()
        action1.coords_for_matching = ((100, 100), "CLICK")

        action2 = MagicMock()
        action2.coords_for_matching = ((200, 200), "CLICK")

        # Mark action1 as executed (in optimized space)
        optimized_sig1 = ((65, 65), "CLICK")  # 100 * 704/1080, 100 * 1248/1920
        mock_screen_node.executed_actions = {optimized_sig1}

        untested = dfs_strategy._get_untested_actions(mock_screen_node, [action1, action2])

        assert len(untested) == 1
        assert untested[0] == action2


# =============================================================================
# MOP Priority Tests
# =============================================================================

class TestDFSStrategyMOPPriority:
    """Tests for DFSStrategy._get_mop_priority()."""

    def test_direct_mop_priority(self, dfs_strategy):
        """Test [DM] priority = 3."""
        action = MagicMock()
        action.directly_reaches_mop = True
        action.reaches_mop = True

        priority = dfs_strategy._get_mop_priority(action)

        assert priority == 3

    def test_transitive_mop_priority(self, dfs_strategy):
        """Test [M] priority = 2."""
        action = MagicMock()
        action.directly_reaches_mop = False
        action.reaches_mop = True

        priority = dfs_strategy._get_mop_priority(action)

        assert priority == 2

    def test_regular_action_priority(self, dfs_strategy):
        """Test regular action priority = 1."""
        action = MagicMock()
        action.directly_reaches_mop = False
        action.reaches_mop = False

        priority = dfs_strategy._get_mop_priority(action)

        assert priority == 1


# =============================================================================
# Select Priority Action Tests
# =============================================================================

class TestDFSStrategySelectPriorityAction:
    """Tests for DFSStrategy._select_priority_action()."""

    def test_selects_highest_priority(self, dfs_strategy):
        """Test that highest priority action is selected."""
        action_dm = MagicMock()
        action_dm.directly_reaches_mop = True
        action_dm.reaches_mop = True

        action_m = MagicMock()
        action_m.directly_reaches_mop = False
        action_m.reaches_mop = True

        action_regular = MagicMock()
        action_regular.directly_reaches_mop = False
        action_regular.reaches_mop = False

        # Order doesn't matter - should select DM
        actions = [action_regular, action_m, action_dm]
        selected = dfs_strategy._select_priority_action(actions)

        assert selected == action_dm

    def test_selects_from_single_action(self, dfs_strategy, mock_action):
        """Test selection with single action."""
        selected = dfs_strategy._select_priority_action([mock_action])

        assert selected == mock_action


# =============================================================================
# Convert Signature Tests
# =============================================================================

class TestDFSStrategyConvertSignature:
    """Tests for DFSStrategy._convert_signature_to_optimized()."""

    def test_convert_without_converter(self, dfs_strategy):
        """Test conversion using fallback calculation."""
        signature = ((540, 960), "CLICK")  # Device space

        result = dfs_strategy._convert_signature_to_optimized(signature)

        # 540 * 704/1080 = 352, 960 * 1248/1920 = 624
        assert result == ((352, 624), "CLICK")

    def test_convert_with_converter(self, mock_graph):
        """Test conversion using CoordinateConverter."""
        converter = MagicMock()
        converter.device_to_optimized.return_value = (350, 620)

        strategy = DFSStrategy(graph=mock_graph, coordinate_converter=converter)

        signature = ((540, 960), "CLICK")
        result = strategy._convert_signature_to_optimized(signature)

        assert result == ((350, 620), "CLICK")
        converter.device_to_optimized.assert_called_once_with(540, 960)

    def test_convert_preserves_action_type(self, dfs_strategy):
        """Test that action type is preserved."""
        for action_type in ["CLICK", "LONG_CLICK", "SET_TEXT", "SCROLL"]:
            signature = ((100, 100), action_type)
            result = dfs_strategy._convert_signature_to_optimized(signature)

            assert result[1] == action_type


# =============================================================================
# Should Backtrack Tests
# =============================================================================

class TestDFSStrategyShouldBacktrack:
    """Tests for DFSStrategy.should_backtrack()."""

    def test_should_backtrack_when_exhausted(self, dfs_strategy, mock_graph, mock_screen_node):
        """Test backtrack when all actions executed."""
        mock_screen_node.total_actions = 3
        mock_screen_node.executed_actions = {("a",), ("b",), ("c",)}  # 3 executed
        mock_graph.states = {"hash1": mock_screen_node}

        result = dfs_strategy.should_backtrack("hash1")

        assert result is True

    def test_should_not_backtrack_with_untested(self, dfs_strategy, mock_graph, mock_screen_node):
        """Test no backtrack when actions remain."""
        mock_screen_node.total_actions = 5
        mock_screen_node.executed_actions = {("a",), ("b",)}  # 2 of 5 executed
        mock_graph.states = {"hash1": mock_screen_node}

        result = dfs_strategy.should_backtrack("hash1")

        assert result is False

    def test_should_not_backtrack_unknown_state(self, dfs_strategy, mock_graph):
        """Test no backtrack for unknown state."""
        mock_graph.states = {}

        result = dfs_strategy.should_backtrack("unknown")

        assert result is False


# =============================================================================
# Select Next Action Tests
# =============================================================================

class TestDFSStrategySelectNextAction:
    """Tests for DFSStrategy.select_next_action()."""

    def test_new_state_creates_node(self, dfs_strategy, mock_graph, mock_screen_desc, mock_action, mock_screen_node):
        """Test that new state creates graph node."""
        mock_graph.states = {}
        mock_graph.get_or_create_state.return_value = mock_screen_node

        with patch.object(dfs_strategy, '_try_generate_text_input', return_value=None):
            result = dfs_strategy.select_next_action("new_hash", mock_screen_desc)

        mock_graph.get_or_create_state.assert_called_once()
        assert "new_hash" in dfs_strategy.visited_states
        assert len(dfs_strategy.state_stack) == 1

    def test_new_state_selects_action(self, dfs_strategy, mock_graph, mock_screen_desc, mock_action, mock_screen_node):
        """Test that action is selected for new state."""
        mock_graph.states = {}
        mock_graph.get_or_create_state.return_value = mock_screen_node

        with patch.object(dfs_strategy, '_try_generate_text_input', return_value=None):
            result = dfs_strategy.select_next_action("new_hash", mock_screen_desc)

        assert result == mock_action
        assert dfs_strategy.current_depth == 1

    def test_revisited_state_uses_existing_node(self, dfs_strategy, mock_graph, mock_screen_desc, mock_action, mock_screen_node):
        """Test that revisited state uses existing node."""
        mock_graph.states = {"existing_hash": mock_screen_node}

        with patch.object(dfs_strategy, '_try_generate_text_input', return_value=None):
            result = dfs_strategy.select_next_action("existing_hash", mock_screen_desc)

        mock_graph.get_or_create_state.assert_not_called()

    def test_exhausted_state_returns_none(self, dfs_strategy, mock_graph, mock_screen_desc, mock_screen_node):
        """Test that exhausted state returns None."""
        # Mark all actions as executed
        mock_screen_node.executed_actions = {((97, 97), "CLICK")}  # Optimized coords
        mock_graph.states = {"exhausted_hash": mock_screen_node}

        with patch.object(dfs_strategy, '_try_generate_text_input', return_value=None):
            result = dfs_strategy.select_next_action("exhausted_hash", mock_screen_desc)

        assert result is None

    def test_records_action_before_returning(self, dfs_strategy, mock_graph, mock_screen_desc, mock_action, mock_screen_node):
        """Test that action is recorded before returning."""
        mock_graph.states = {}
        mock_graph.get_or_create_state.return_value = mock_screen_node

        with patch.object(dfs_strategy, '_try_generate_text_input', return_value=None):
            dfs_strategy.select_next_action("hash", mock_screen_desc)

        mock_graph.record_action.assert_called_once()


# =============================================================================
# Record Transition Tests
# =============================================================================

class TestDFSStrategyRecordTransition:
    """Tests for DFSStrategy.record_transition()."""

    def test_record_transition_is_noop(self, dfs_strategy, mock_action):
        """Test that record_transition does nothing (DFS uses implicit stack)."""
        # Should not raise
        dfs_strategy.record_transition("from_hash", "to_hash", mock_action)

        # No state changes expected
        assert dfs_strategy.state_stack == []


# =============================================================================
# Integration Tests
# =============================================================================

class TestDFSStrategyIntegration:
    """Integration tests for DFSStrategy."""

    def test_full_exploration_flow(self, mock_graph):
        """Test complete exploration flow."""
        strategy = DFSStrategy(graph=mock_graph)

        # Create mock nodes
        node1 = MagicMock()
        node1.total_actions = 2
        node1.visit_count = 1
        node1.executed_actions = set()

        node2 = MagicMock()
        node2.total_actions = 1
        node2.visit_count = 1
        node2.executed_actions = set()

        mock_graph.get_or_create_state.side_effect = [node1, node2]
        mock_graph.states = {}

        # Create actions
        action1 = MagicMock()
        action1.id = 1
        action1.coords_for_matching = ((100, 100), "CLICK")
        action1.target_view = {'system_action': False}
        action1.get_execution_coordinates.return_value = (100, 100)
        action1.directly_reaches_mop = False
        action1.reaches_mop = False

        action2 = MagicMock()
        action2.id = 2
        action2.coords_for_matching = ((200, 200), "CLICK")
        action2.target_view = {'system_action': False}
        action2.get_execution_coordinates.return_value = (200, 200)
        action2.directly_reaches_mop = False
        action2.reaches_mop = False

        screen_desc = MagicMock()
        screen_desc.activity = "MainActivity"
        screen_desc.get_all_actions.return_value = [action1, action2]
        screen_desc.items = []

        # First call - should select first action
        with patch.object(strategy, '_try_generate_text_input', return_value=None):
            result1 = strategy.select_next_action("state1", screen_desc)

        assert result1 is not None
        assert strategy.current_depth == 1
        assert len(strategy.visited_states) == 1

    def test_depth_tracking(self, mock_graph, mock_screen_desc, mock_action, mock_screen_node):
        """Test that depth is tracked correctly."""
        strategy = DFSStrategy(graph=mock_graph)
        mock_graph.states = {}
        mock_graph.get_or_create_state.return_value = mock_screen_node

        with patch.object(strategy, '_try_generate_text_input', return_value=None):
            # First action
            strategy.select_next_action("state1", mock_screen_desc)
            assert strategy.current_depth == 1

            # Second action (different state)
            mock_screen_node.executed_actions = set()
            mock_graph.states = {}
            strategy.select_next_action("state2", mock_screen_desc)
            assert strategy.current_depth == 2
