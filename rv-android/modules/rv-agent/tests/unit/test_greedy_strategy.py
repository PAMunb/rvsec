"""
Unit tests for GreedyStrategy.

Tests value calculation, action selection, and transition recording.
"""

import pytest
from unittest.mock import MagicMock, Mock, patch

from rv_agent.strategies.greedy_strategy import GreedyStrategy
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction


class TestGreedyStrategyInit:
    """Test strategy initialization."""

    def test_initialization(self):
        """Strategy initializes with default values."""
        graph = DynamicStateGraph()
        strategy = GreedyStrategy(graph=graph)

        assert strategy.graph is graph
        assert strategy.exploration_probability == 0.1
        assert len(strategy.action_values) == 0
        assert len(strategy.visited_states) == 0


class TestRecordTransition:
    """Test record_transition method."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return GreedyStrategy(graph=graph)

    def test_record_transition_basic(self, strategy):
        """Record basic transition."""
        action = MagicMock(spec=ItemAction)
        action.coords_for_matching = ((100, 200), "click")

        strategy.record_transition(
            from_hash="hash1",
            to_hash="hash2",
            action=action
        )

        # Should increment attempt counter
        signature = ((100, 200), "click")
        assert strategy.action_attempts[signature] == 1

    def test_record_transition_new_state_discovery(self, strategy):
        """Record transition to new state."""
        action = MagicMock(spec=ItemAction)
        action.coords_for_matching = ((100, 200), "click")

        # to_hash is not in visited_states, so it's a new state
        strategy.record_transition(
            from_hash="hash1",
            to_hash="hash2",
            action=action
        )

        signature = ((100, 200), "click")
        assert strategy.action_new_states[signature] == 1

    def test_record_transition_existing_state(self, strategy):
        """Record transition to already visited state."""
        action = MagicMock(spec=ItemAction)
        action.coords_for_matching = ((100, 200), "click")

        # Pre-mark as visited
        strategy.visited_states.add("hash2")

        strategy.record_transition(
            from_hash="hash1",
            to_hash="hash2",
            action=action
        )

        signature = ((100, 200), "click")
        # Should not count as new state
        assert signature not in strategy.action_new_states

    def test_record_multiple_transitions(self, strategy):
        """Record multiple transitions with same action."""
        action = MagicMock(spec=ItemAction)
        action.coords_for_matching = ((100, 200), "click")

        strategy.record_transition("hash1", "hash2", action)
        strategy.visited_states.add("hash2")  # Mark as visited
        strategy.visited_states.add("hash3")  # Mark hash3 as visited too
        strategy.record_transition("hash2", "hash3", action)

        signature = ((100, 200), "click")
        assert strategy.action_attempts[signature] == 2
        # Only first transition discovered new state (hash3 was already visited)
        assert strategy.action_new_states.get(signature, 0) == 1


class TestShouldBacktrack:
    """Test should_backtrack method."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return GreedyStrategy(graph=graph)

    def test_should_backtrack_unknown_state(self, strategy):
        """Unknown state should not trigger backtrack."""
        result = strategy.should_backtrack("unknown_hash")
        assert result is False

    def test_should_backtrack_exhausted_state(self, strategy):
        """Exhausted state should trigger backtrack."""
        # Create a state with some executed actions
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "Test"

        node = strategy.graph.get_or_create_state(
            "test_hash", "Test", screen_desc
        )

        # Set total_actions = executed_actions
        node.total_actions = 3
        node.executed_actions.add(((100, 200), "click"))
        node.executed_actions.add(((200, 300), "click"))
        node.executed_actions.add(((300, 400), "click"))

        result = strategy.should_backtrack("test_hash")
        assert result is True

    def test_should_backtrack_partial_state(self, strategy):
        """Partial state should not trigger backtrack."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "Test"

        node = strategy.graph.get_or_create_state(
            "test_hash", "Test", screen_desc
        )

        node.total_actions = 5
        node.executed_actions.add(((100, 200), "click"))

        result = strategy.should_backtrack("test_hash")
        assert result is False


class TestCalculateActionValue:
    """Test action value calculation."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return GreedyStrategy(graph=graph)

    def test_base_value_unknown_action(self, strategy):
        """Unknown action starts with base value 0.5."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = False
        action.reaches_mop = False

        signature = ((100, 200), "click")
        value = strategy._calculate_action_value(action, signature)

        # Base (0.5) + exploration bonus (0.2 for untried)
        assert value >= 0.5

    def test_value_with_direct_mop(self, strategy):
        """Direct MOP action gets +0.3 bonus."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = True
        action.reaches_mop = False

        signature = ((100, 200), "click")
        value = strategy._calculate_action_value(action, signature)

        # Should be higher than base
        assert value >= 0.8  # 0.5 base + 0.3 MOP

    def test_value_with_transitive_mop(self, strategy):
        """Transitive MOP action gets +0.2 bonus."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = False
        action.reaches_mop = True

        signature = ((100, 200), "click")
        value = strategy._calculate_action_value(action, signature)

        # Should be higher than base
        assert value >= 0.7  # 0.5 base + 0.2 MOP

    def test_value_with_discovery_history(self, strategy):
        """Action with discovery history gets bonus."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = False
        action.reaches_mop = False

        signature = ((100, 200), "click")

        # Set up discovery history
        strategy.action_attempts[signature] = 5
        strategy.action_new_states[signature] = 3

        value = strategy._calculate_action_value(action, signature)

        # Should include discovery bonus
        assert value > 0.5

    def test_value_diminishing_exploration_bonus(self, strategy):
        """Tried actions get diminishing exploration bonus."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = False
        action.reaches_mop = False

        signature = ((100, 200), "click")
        strategy.action_attempts[signature] = 10

        value = strategy._calculate_action_value(action, signature)

        # Bonus should be small: 0.1 / sqrt(10) ≈ 0.03
        assert value < 0.7


class TestUpdateActionValue:
    """Test action value updates."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return GreedyStrategy(graph=graph)

    def test_update_value_success(self, strategy):
        """Successful action updates value positively."""
        signature = ((100, 200), "click")
        strategy.action_attempts[signature] = 1

        strategy._update_action_value(signature, success=True, new_state=False)

        assert signature in strategy.action_values
        assert strategy.action_values[signature] >= 0.5

    def test_update_value_new_state(self, strategy):
        """New state discovery gives high reward."""
        signature = ((100, 200), "click")
        strategy.action_attempts[signature] = 1

        strategy._update_action_value(signature, success=True, new_state=True)

        # Should have high value due to new state reward (+0.5)
        assert strategy.action_values[signature] >= 0.8

    def test_update_value_clamped(self, strategy):
        """Values are clamped to [0.0, 2.0]."""
        signature = ((100, 200), "click")
        strategy.action_attempts[signature] = 1

        # Try to push value very high
        for _ in range(20):
            strategy._update_action_value(signature, success=True, new_state=True)
            strategy.action_attempts[signature] += 1

        assert strategy.action_values[signature] <= 2.0


class TestConvertSignature:
    """Test signature conversion."""

    def test_convert_without_converter(self):
        """Without converter, signature is unchanged."""
        graph = DynamicStateGraph()
        strategy = GreedyStrategy(graph=graph, coordinate_converter=None)

        signature = ((100, 200), "click")
        result = strategy._convert_signature_to_optimized(signature)

        assert result == signature

    def test_convert_with_converter(self):
        """With converter, coordinates are transformed."""
        graph = DynamicStateGraph()
        converter = MagicMock()
        converter.device_to_optimized.return_value = (50, 100)

        strategy = GreedyStrategy(graph=graph, coordinate_converter=converter)

        signature = ((100, 200), "click")
        result = strategy._convert_signature_to_optimized(signature)

        assert result == ((50, 100), "click")
        converter.device_to_optimized.assert_called_once_with((100, 200))


class TestGetMopPriority:
    """Test MOP priority calculation."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return GreedyStrategy(graph=graph)

    def test_priority_direct_mop(self, strategy):
        """Direct MOP action has priority 3."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = True
        action.reaches_mop = False

        priority = strategy._get_mop_priority(action)
        assert priority == 3

    def test_priority_transitive_mop(self, strategy):
        """Transitive MOP action has priority 2."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = False
        action.reaches_mop = True

        priority = strategy._get_mop_priority(action)
        assert priority == 2

    def test_priority_no_mop(self, strategy):
        """Non-MOP action has priority 1."""
        action = MagicMock(spec=ItemAction)
        action.directly_reaches_mop = False
        action.reaches_mop = False

        priority = strategy._get_mop_priority(action)
        assert priority == 1


class TestFilterActions:
    """Test action filtering."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return GreedyStrategy(graph=graph)

    def test_filter_nav_bar_actions(self, strategy):
        """Nav bar actions (y > 1794) are filtered."""
        action1 = MagicMock(spec=ItemAction)
        action1.id = "action1"
        action1.target_view = {"system_action": False}
        action1.get_execution_coordinates.return_value = (500, 1000)  # Valid

        action2 = MagicMock(spec=ItemAction)
        action2.id = "action2"
        action2.target_view = {"system_action": False}
        action2.get_execution_coordinates.return_value = (500, 1800)  # Nav bar

        result = strategy._filter_actions([action1, action2])

        assert len(result) == 1
        assert result[0].id == "action1"

    def test_filter_system_actions(self, strategy):
        """System actions are filtered."""
        action1 = MagicMock(spec=ItemAction)
        action1.id = "action1"
        action1.target_view = {"system_action": False}
        action1.get_execution_coordinates.return_value = (500, 1000)

        action2 = MagicMock(spec=ItemAction)
        action2.id = "action2"
        action2.target_view = {"system_action": True}
        action2.get_execution_coordinates.return_value = (500, 1000)

        result = strategy._filter_actions([action1, action2])

        assert len(result) == 1
        assert result[0].id == "action1"

    def test_filter_no_coords_actions(self, strategy):
        """Actions without coordinates are filtered."""
        action1 = MagicMock(spec=ItemAction)
        action1.id = "action1"
        action1.target_view = {"system_action": False}
        action1.get_execution_coordinates.return_value = (500, 1000)

        action2 = MagicMock(spec=ItemAction)
        action2.id = "action2"
        action2.target_view = {"system_action": False, "class": "SomeClass"}
        action2.get_execution_coordinates.return_value = None

        result = strategy._filter_actions([action1, action2])

        assert len(result) == 1
        assert result[0].id == "action1"


class TestReset:
    """Test reset method."""

    def test_reset_clears_visited_states(self):
        """Reset clears visited states."""
        graph = DynamicStateGraph()
        strategy = GreedyStrategy(graph=graph)

        strategy.visited_states.add("hash1")
        strategy.visited_states.add("hash2")

        strategy.reset()

        assert len(strategy.visited_states) == 0

    def test_reset_keeps_action_values(self):
        """Reset keeps action value history."""
        graph = DynamicStateGraph()
        strategy = GreedyStrategy(graph=graph)

        signature = ((100, 200), "click")
        strategy.action_values[signature] = 0.8

        strategy.reset()

        assert strategy.action_values[signature] == 0.8


class TestGetUntestedActions:
    """Test _get_untested_actions method."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return GreedyStrategy(graph=graph)

    def test_all_actions_untested(self, strategy):
        """All actions are returned when none executed."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "Test"

        node = strategy.graph.get_or_create_state(
            "test_hash", "Test", screen_desc
        )
        node.total_actions = 3

        action1 = MagicMock(spec=ItemAction)
        action1.id = "action1"
        action1.coords_for_matching = ((100, 200), "click")

        action2 = MagicMock(spec=ItemAction)
        action2.id = "action2"
        action2.coords_for_matching = ((200, 300), "click")

        result = strategy._get_untested_actions(node, [action1, action2])

        assert len(result) == 2

    def test_some_actions_executed(self, strategy):
        """Only untested actions are returned."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "Test"

        node = strategy.graph.get_or_create_state(
            "test_hash", "Test", screen_desc
        )
        node.total_actions = 3
        node.executed_actions.add(((100, 200), "click"))

        action1 = MagicMock(spec=ItemAction)
        action1.id = "action1"
        action1.coords_for_matching = ((100, 200), "click")

        action2 = MagicMock(spec=ItemAction)
        action2.id = "action2"
        action2.coords_for_matching = ((200, 300), "click")

        result = strategy._get_untested_actions(node, [action1, action2])

        assert len(result) == 1
        assert result[0].id == "action2"

    def test_all_actions_executed(self, strategy):
        """Empty list when all actions executed."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "Test"

        node = strategy.graph.get_or_create_state(
            "test_hash", "Test", screen_desc
        )
        node.total_actions = 2
        node.executed_actions.add(((100, 200), "click"))
        node.executed_actions.add(((200, 300), "click"))

        action1 = MagicMock(spec=ItemAction)
        action1.id = "action1"
        action1.coords_for_matching = ((100, 200), "click")

        action2 = MagicMock(spec=ItemAction)
        action2.id = "action2"
        action2.coords_for_matching = ((200, 300), "click")

        result = strategy._get_untested_actions(node, [action1, action2])

        assert len(result) == 0


class TestSelectNextAction:
    """Test select_next_action method."""

    @pytest.fixture
    def strategy(self):
        graph = DynamicStateGraph()
        return GreedyStrategy(graph=graph)

    def test_select_from_new_state(self, strategy):
        """Select action from new state."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.activity = "TestActivity"

        # Mock an action
        action = MagicMock(spec=ItemAction)
        action.id = "action1"
        action.coords_for_matching = ((500, 500), "click")
        action.target_view = {"system_action": False}
        action.get_execution_coordinates.return_value = (500, 500)
        action.directly_reaches_mop = False
        action.reaches_mop = False

        screen_desc.get_all_actions.return_value = [action]
        screen_desc.items = []

        # Create custom mock for _try_generate_text_input
        with patch.object(strategy, '_try_generate_text_input', return_value=None):
            result = strategy.select_next_action("new_hash", screen_desc)

        assert result is not None
        assert result.id == "action1"
        assert "new_hash" in strategy.visited_states

    def test_select_returns_back_when_exhausted(self, strategy):
        """Returns BACK action when all actions exhausted.

        With continuous exploration mode, when no actions are available,
        the strategy returns a BACK action for navigation.
        """
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.activity = "TestActivity"
        screen_desc.items = []
        screen_desc.get_all_actions.return_value = []

        with patch.object(strategy, '_try_generate_text_input', return_value=None), \
             patch.object(strategy, '_try_generate_scroll_action', return_value=None):
            result = strategy.select_next_action("hash1", screen_desc)

        # With continuous exploration, BACK is returned when no actions available
        assert result is not None
        assert result.text == "BACK"
        assert result.id == 999

    def test_select_prioritizes_high_value_actions(self, strategy):
        """Greedy selection prioritizes high-value actions."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.activity = "TestActivity"
        screen_desc.items = []

        # Create two actions: one with MOP, one without
        action_no_mop = MagicMock(spec=ItemAction)
        action_no_mop.id = "action_no_mop"
        action_no_mop.coords_for_matching = ((100, 500), "click")
        action_no_mop.target_view = {"system_action": False}
        action_no_mop.get_execution_coordinates.return_value = (100, 500)
        action_no_mop.directly_reaches_mop = False
        action_no_mop.reaches_mop = False

        action_with_mop = MagicMock(spec=ItemAction)
        action_with_mop.id = "action_with_mop"
        action_with_mop.coords_for_matching = ((200, 500), "click")
        action_with_mop.target_view = {"system_action": False}
        action_with_mop.get_execution_coordinates.return_value = (200, 500)
        action_with_mop.directly_reaches_mop = True
        action_with_mop.reaches_mop = False

        screen_desc.get_all_actions.return_value = [action_no_mop, action_with_mop]

        # Force greedy selection (not random)
        with patch.object(strategy, '_try_generate_text_input', return_value=None):
            with patch('random.random', return_value=0.5):  # > 0.1, so greedy
                result = strategy.select_next_action("hash1", screen_desc)

        # MOP action should be selected due to higher value
        assert result is not None
        assert result.id == "action_with_mop"

    def test_select_random_exploration(self, strategy):
        """Random exploration with 10% probability."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.activity = "TestActivity"
        screen_desc.items = []

        action1 = MagicMock(spec=ItemAction)
        action1.id = "action1"
        action1.coords_for_matching = ((100, 500), "click")
        action1.target_view = {"system_action": False}
        action1.get_execution_coordinates.return_value = (100, 500)
        action1.directly_reaches_mop = False
        action1.reaches_mop = False

        action2 = MagicMock(spec=ItemAction)
        action2.id = "action2"
        action2.coords_for_matching = ((200, 500), "click")
        action2.target_view = {"system_action": False}
        action2.get_execution_coordinates.return_value = (200, 500)
        action2.directly_reaches_mop = False
        action2.reaches_mop = False

        screen_desc.get_all_actions.return_value = [action1, action2]

        # Force random exploration (random < 0.1)
        with patch.object(strategy, '_try_generate_text_input', return_value=None):
            with patch('random.random', return_value=0.05):  # < 0.1, so random
                with patch('random.choice', return_value=action2):
                    result = strategy.select_next_action("hash1", screen_desc)

        assert result is not None
        assert result.id == "action2"

    def test_select_revisited_state(self, strategy):
        """Select action from revisited state."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.activity = "TestActivity"
        screen_desc.items = []

        action = MagicMock(spec=ItemAction)
        action.id = "action1"
        action.coords_for_matching = ((500, 500), "click")
        action.target_view = {"system_action": False}
        action.get_execution_coordinates.return_value = (500, 500)
        action.directly_reaches_mop = False
        action.reaches_mop = False

        screen_desc.get_all_actions.return_value = [action]

        # First visit
        with patch.object(strategy, '_try_generate_text_input', return_value=None):
            strategy.select_next_action("revisit_hash", screen_desc)

        # Create a new action for second visit
        action2 = MagicMock(spec=ItemAction)
        action2.id = "action2"
        action2.coords_for_matching = ((600, 600), "click")
        action2.target_view = {"system_action": False}
        action2.get_execution_coordinates.return_value = (600, 600)
        action2.directly_reaches_mop = False
        action2.reaches_mop = False

        screen_desc.get_all_actions.return_value = [action, action2]

        # Second visit - should skip executed action
        with patch.object(strategy, '_try_generate_text_input', return_value=None):
            result = strategy.select_next_action("revisit_hash", screen_desc)

        assert result is not None
        assert result.id == "action2"
