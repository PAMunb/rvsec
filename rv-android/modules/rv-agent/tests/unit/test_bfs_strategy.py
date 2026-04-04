"""
Unit tests for BFSStrategy - Breadth-first exploration with MOP prioritization.

Tests verify:
- BFSState dataclass behavior
- Queue-based (FIFO) state traversal
- Action filtering and coordinate-based tracking
- MOP prioritization for action selection
- Level-by-level exploration (exhaust current state before next)
- Coordinate conversion between device and optimized spaces
"""

import pytest
from unittest.mock import MagicMock, patch
from collections import deque

from rv_agent.strategies.bfs_strategy import BFSState, BFSStrategy
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_graph():
    """Create mock DynamicStateGraph."""
    graph = MagicMock(spec=DynamicStateGraph)
    graph.states = {}
    return graph


@pytest.fixture
def mock_screen_node():
    """Create mock ScreenNode for graph states."""
    node = MagicMock()
    node.total_actions = 5
    node.executed_actions = set()
    node.visit_count = 1
    return node


@pytest.fixture
def mock_action():
    """Create mock ItemAction."""
    action = MagicMock(spec=ItemAction)
    action.id = "1"
    action.action_type = "CLICK"
    action.target_view = {"class": "android.widget.Button", "resource-id": "btn_test"}
    action.get_execution_coordinates.return_value = (540, 960)
    action.coords_for_matching = ((540, 960), "CLICK")
    return action


@pytest.fixture
def mock_screen_desc(mock_action):
    """Create mock ScreenDescription."""
    screen = MagicMock(spec=ScreenDescription)
    screen.activity = "com.test.MainActivity"
    screen.get_all_actions.return_value = [mock_action]
    screen.items = []  # Empty items to avoid scroll detection
    return screen


@pytest.fixture
def bfs_strategy(mock_graph):
    """Create BFSStrategy instance."""
    return BFSStrategy(graph=mock_graph)


# =============================================================================
# BFSState Tests
# =============================================================================


class TestBFSState:
    """Tests for BFSState dataclass."""

    def test_creation(self):
        """Test BFSState creation with all fields."""
        state = BFSState(
            screen_hash="hash123", depth=2, parent_hash="parent_hash", untested_count=5
        )

        assert state.screen_hash == "hash123"
        assert state.depth == 2
        assert state.parent_hash == "parent_hash"
        assert state.untested_count == 5

    def test_creation_no_parent(self):
        """Test BFSState creation for root state (no parent)."""
        state = BFSState(
            screen_hash="root_hash", depth=0, parent_hash=None, untested_count=10
        )

        assert state.screen_hash == "root_hash"
        assert state.depth == 0
        assert state.parent_hash is None
        assert state.untested_count == 10


# =============================================================================
# BFSStrategy Initialization Tests
# =============================================================================


class TestBFSStrategyInit:
    """Tests for BFSStrategy initialization."""

    def test_init_basic(self, mock_graph):
        """Test basic initialization with graph only."""
        strategy = BFSStrategy(graph=mock_graph)

        assert strategy.graph is mock_graph
        assert strategy.static_data is None
        assert strategy.converter is None
        assert isinstance(strategy.state_queue, deque)
        assert len(strategy.state_queue) == 0
        assert len(strategy.visited_states) == 0
        assert strategy.current_state_hash is None
        assert strategy.current_depth == 0

    def test_init_with_static_data(self, mock_graph):
        """Test initialization with static analysis data."""
        static_data = MagicMock()
        strategy = BFSStrategy(graph=mock_graph, static_data=static_data)

        assert strategy.static_data is static_data

    def test_init_with_converter(self, mock_graph):
        """Test initialization with coordinate converter."""
        converter = MagicMock()
        strategy = BFSStrategy(graph=mock_graph, coordinate_converter=converter)

        assert strategy.converter is converter


# =============================================================================
# BFSStrategy Reset Tests
# =============================================================================


class TestBFSStrategyReset:
    """Tests for BFSStrategy.reset()."""

    def test_reset_clears_state(self, bfs_strategy):
        """Test that reset clears all traversal state."""
        # Set up state
        bfs_strategy.state_queue.append(BFSState("hash1", 0, None, 5))
        bfs_strategy.state_queue.append(BFSState("hash2", 1, "hash1", 3))
        bfs_strategy.visited_states.add("hash1")
        bfs_strategy.visited_states.add("hash2")
        bfs_strategy.current_state_hash = "hash2"
        bfs_strategy.current_depth = 3

        bfs_strategy.reset()

        assert len(bfs_strategy.state_queue) == 0
        assert len(bfs_strategy.visited_states) == 0
        assert bfs_strategy.current_state_hash is None
        assert bfs_strategy.current_depth == 0


# =============================================================================
# BFSStrategy Filter Actions Tests
# =============================================================================


class TestBFSStrategyFilterActions:
    """Tests for BFSStrategy._filter_actions()."""

    def test_filter_keeps_regular_actions(self, bfs_strategy, mock_action):
        """Test that regular actions pass filter."""
        actions = [mock_action]

        filtered = bfs_strategy._filter_actions(actions)

        assert len(filtered) == 1
        assert filtered[0] is mock_action

    def test_filter_removes_system_actions(self, bfs_strategy):
        """Test that system actions are filtered out."""
        system_action = MagicMock(spec=ItemAction)
        system_action.id = "sys_1"
        system_action.target_view = {"system_action": True}

        filtered = bfs_strategy._filter_actions([system_action])

        assert len(filtered) == 0

    def test_filter_removes_actions_without_coords(self, bfs_strategy):
        """Test that actions without coordinates are filtered."""
        no_coords_action = MagicMock(spec=ItemAction)
        no_coords_action.id = "no_coord_1"
        no_coords_action.target_view = {}
        no_coords_action.get_execution_coordinates.return_value = None

        filtered = bfs_strategy._filter_actions([no_coords_action])

        assert len(filtered) == 0

    def test_filter_removes_navbar_actions(self, bfs_strategy):
        """Test that navigation bar actions are filtered (y > 1794)."""
        navbar_action = MagicMock(spec=ItemAction)
        navbar_action.id = "nav_1"
        navbar_action.target_view = {}
        navbar_action.get_execution_coordinates.return_value = (540, 1850)  # In nav bar

        filtered = bfs_strategy._filter_actions([navbar_action])

        assert len(filtered) == 0

    def test_filter_keeps_above_navbar(self, bfs_strategy):
        """Test that actions above navigation bar pass filter."""
        above_navbar_action = MagicMock(spec=ItemAction)
        above_navbar_action.target_view = {}
        above_navbar_action.get_execution_coordinates.return_value = (
            540,
            1790,
        )  # Just above nav bar

        filtered = bfs_strategy._filter_actions([above_navbar_action])

        assert len(filtered) == 1

    def test_filter_mixed_actions(self, bfs_strategy):
        """Test filtering with mix of valid and invalid actions."""
        valid_action = MagicMock(spec=ItemAction)
        valid_action.id = "valid_1"
        valid_action.target_view = {}
        valid_action.get_execution_coordinates.return_value = (540, 960)

        system_action = MagicMock(spec=ItemAction)
        system_action.id = "sys_1"
        system_action.target_view = {"system_action": True}

        navbar_action = MagicMock(spec=ItemAction)
        navbar_action.id = "nav_1"
        navbar_action.target_view = {}
        navbar_action.get_execution_coordinates.return_value = (540, 1900)

        filtered = bfs_strategy._filter_actions(
            [valid_action, system_action, navbar_action]
        )

        assert len(filtered) == 1
        assert filtered[0] is valid_action


# =============================================================================
# BFSStrategy Get Untested Actions Tests
# =============================================================================


class TestBFSStrategyGetUntestedActions:
    """Tests for BFSStrategy._get_untested_actions()."""

    def test_all_actions_untested(self, bfs_strategy, mock_screen_node, mock_action):
        """Test when all actions are untested."""
        mock_screen_node.executed_actions = set()

        untested = bfs_strategy._get_untested_actions(mock_screen_node, [mock_action])

        assert len(untested) == 1
        assert untested[0] is mock_action

    def test_all_actions_tested(self, bfs_strategy, mock_screen_node, mock_action):
        """Test when all actions are already tested."""
        # Mark the action's signature as executed
        expected_sig = ((int(540 * 704 / 1080), int(960 * 1248 / 1920)), "CLICK")
        mock_screen_node.executed_actions = {expected_sig}

        untested = bfs_strategy._get_untested_actions(mock_screen_node, [mock_action])

        assert len(untested) == 0

    def test_mixed_tested_untested(self, bfs_strategy, mock_screen_node):
        """Test with mix of tested and untested actions."""
        action1 = MagicMock(spec=ItemAction)
        action1.id = "1"
        action1.coords_for_matching = ((100, 200), "CLICK")

        action2 = MagicMock(spec=ItemAction)
        action2.id = "2"
        action2.coords_for_matching = ((300, 400), "CLICK")

        # Mark only first action as executed
        sig1 = ((int(100 * 704 / 1080), int(200 * 1248 / 1920)), "CLICK")
        mock_screen_node.executed_actions = {sig1}

        untested = bfs_strategy._get_untested_actions(
            mock_screen_node, [action1, action2]
        )

        assert len(untested) == 1
        assert untested[0] is action2


# =============================================================================
# BFSStrategy MOP Priority Tests
# =============================================================================


class TestBFSStrategyMOPPriority:
    """Tests for BFSStrategy._get_mop_priority()."""

    def test_direct_mop_priority(self, bfs_strategy):
        """Test priority for direct MOP action [DM]."""
        action = MagicMock(spec=ItemAction)
        action.action_type = "CLICK"
        action.target_view = {"text": "[DM] Encrypt Data"}
        action.directly_reaches_mop = True
        action.reaches_mop = True

        priority = bfs_strategy._get_mop_priority(action)

        assert priority == 3

    def test_transitive_mop_priority(self, bfs_strategy):
        """Test priority for transitive MOP action [M]."""
        action = MagicMock(spec=ItemAction)
        action.action_type = "CLICK"
        action.target_view = {"text": "[M] Settings"}
        action.directly_reaches_mop = False
        action.reaches_mop = True

        priority = bfs_strategy._get_mop_priority(action)

        assert priority == 2

    def test_regular_action_priority(self, bfs_strategy):
        """Test priority for regular action without markers."""
        action = MagicMock(spec=ItemAction)
        action.action_type = "CLICK"
        action.target_view = {"text": "Cancel"}
        action.directly_reaches_mop = False
        action.reaches_mop = False

        priority = bfs_strategy._get_mop_priority(action)

        assert priority == 1


# =============================================================================
# BFSStrategy Select Priority Action Tests
# =============================================================================


class TestBFSStrategySelectPriorityAction:
    """Tests for BFSStrategy._select_priority_action()."""

    def test_selects_highest_priority(self, bfs_strategy):
        """Test that highest priority action is selected."""
        regular_action = MagicMock(spec=ItemAction)
        regular_action.target_view = {"text": "Cancel"}
        regular_action.action_type = "CLICK"
        regular_action.directly_reaches_mop = False
        regular_action.reaches_mop = False

        mop_action = MagicMock(spec=ItemAction)
        mop_action.target_view = {"text": "[M] Settings"}
        mop_action.action_type = "CLICK"
        mop_action.directly_reaches_mop = False
        mop_action.reaches_mop = True

        direct_mop_action = MagicMock(spec=ItemAction)
        direct_mop_action.target_view = {"text": "[DM] Encrypt"}
        direct_mop_action.action_type = "CLICK"
        direct_mop_action.directly_reaches_mop = True
        direct_mop_action.reaches_mop = True

        actions = [regular_action, mop_action, direct_mop_action]

        selected = bfs_strategy._select_priority_action(actions)

        assert selected is direct_mop_action

    def test_selects_from_single_action(self, bfs_strategy):
        """Test selection with single action."""
        action = MagicMock(spec=ItemAction)
        action.target_view = {"text": "OK"}
        action.action_type = "CLICK"
        action.directly_reaches_mop = False
        action.reaches_mop = False

        selected = bfs_strategy._select_priority_action([action])

        assert selected is action

    def test_selects_first_when_equal_priority(self, bfs_strategy):
        """Test selection when multiple actions have same priority."""
        action1 = MagicMock(spec=ItemAction)
        action1.target_view = {"text": "Button 1"}
        action1.action_type = "CLICK"
        action1.directly_reaches_mop = False
        action1.reaches_mop = False

        action2 = MagicMock(spec=ItemAction)
        action2.target_view = {"text": "Button 2"}
        action2.action_type = "CLICK"
        action2.directly_reaches_mop = False
        action2.reaches_mop = False

        # Both have priority 1 (regular actions)
        selected = bfs_strategy._select_priority_action([action1, action2])

        # Sorted by priority, first in list should be selected
        assert selected in [action1, action2]


# =============================================================================
# BFSStrategy Convert Signature Tests
# =============================================================================


class TestBFSStrategyConvertSignature:
    """Tests for BFSStrategy._convert_signature_to_optimized()."""

    def test_convert_without_converter(self, bfs_strategy):
        """Test conversion using fallback calculation."""
        signature = ((540, 960), "CLICK")

        converted = bfs_strategy._convert_signature_to_optimized(signature)

        # 540 * 704 / 1080 = 352
        # 960 * 1248 / 1920 = 624
        expected = ((352, 624), "CLICK")
        assert converted == expected

    def test_convert_with_converter(self, mock_graph):
        """Test conversion using CoordinateConverter."""
        converter = MagicMock()
        converter.device_to_optimized.return_value = (350, 620)

        strategy = BFSStrategy(graph=mock_graph, coordinate_converter=converter)
        signature = ((540, 960), "CLICK")

        converted = strategy._convert_signature_to_optimized(signature)

        converter.device_to_optimized.assert_called_once_with(540, 960)
        assert converted == ((350, 620), "CLICK")

    def test_convert_preserves_action_type(self, bfs_strategy):
        """Test that action type is preserved during conversion."""
        click_sig = ((100, 200), "CLICK")
        long_click_sig = ((100, 200), "LONG_CLICK")

        click_converted = bfs_strategy._convert_signature_to_optimized(click_sig)
        long_click_converted = bfs_strategy._convert_signature_to_optimized(
            long_click_sig
        )

        assert click_converted[1] == "CLICK"
        assert long_click_converted[1] == "LONG_CLICK"


# =============================================================================
# BFSStrategy Should Backtrack Tests
# =============================================================================


class TestBFSStrategyShouldBacktrack:
    """Tests for BFSStrategy.should_backtrack()."""

    def test_should_backtrack_when_exhausted(
        self, bfs_strategy, mock_graph, mock_screen_node
    ):
        """Test returns True when all actions executed."""
        mock_screen_node.total_actions = 3
        mock_screen_node.executed_actions = {"sig1", "sig2", "sig3"}  # All executed
        mock_graph.states = {"hash123": mock_screen_node}

        should_backtrack = bfs_strategy.should_backtrack("hash123")

        assert should_backtrack is True

    def test_should_not_backtrack_with_untested(
        self, bfs_strategy, mock_graph, mock_screen_node
    ):
        """Test returns False when untested actions exist."""
        mock_screen_node.total_actions = 5
        mock_screen_node.executed_actions = {"sig1", "sig2"}  # Only 2 of 5 executed
        mock_graph.states = {"hash123": mock_screen_node}

        should_backtrack = bfs_strategy.should_backtrack("hash123")

        assert should_backtrack is False

    def test_should_not_backtrack_unknown_state(self, bfs_strategy, mock_graph):
        """Test returns False for unknown state."""
        mock_graph.states = {}

        should_backtrack = bfs_strategy.should_backtrack("unknown_hash")

        assert should_backtrack is False


# =============================================================================
# BFSStrategy Record Transition Tests
# =============================================================================


class TestBFSStrategyRecordTransition:
    """Tests for BFSStrategy.record_transition()."""

    def test_record_transition_new_state_increases_depth(self, bfs_strategy):
        """Test that transition to new state increases depth."""
        bfs_strategy.current_depth = 1
        bfs_strategy.visited_states = {"hash1"}

        action = MagicMock(spec=ItemAction)
        bfs_strategy.record_transition("hash1", "hash2", action)

        assert bfs_strategy.current_depth == 2

    def test_record_transition_visited_state_no_depth_change(self, bfs_strategy):
        """Test that transition to visited state doesn't change depth."""
        bfs_strategy.current_depth = 2
        bfs_strategy.visited_states = {"hash1", "hash2"}

        action = MagicMock(spec=ItemAction)
        bfs_strategy.record_transition("hash1", "hash2", action)

        assert bfs_strategy.current_depth == 2


# =============================================================================
# BFSStrategy Select Next Action Tests
# =============================================================================


class TestBFSStrategySelectNextAction:
    """Tests for BFSStrategy.select_next_action()."""

    def test_new_state_creates_node(
        self, bfs_strategy, mock_graph, mock_screen_node, mock_screen_desc, mock_action
    ):
        """Test that new state creates graph node."""
        mock_graph.get_or_create_state.return_value = mock_screen_node
        mock_graph.states = {}

        bfs_strategy.select_next_action("new_hash", mock_screen_desc)

        mock_graph.get_or_create_state.assert_called_once()

    def test_new_state_added_to_queue(
        self, bfs_strategy, mock_graph, mock_screen_node, mock_screen_desc, mock_action
    ):
        """Test that new state is added to BFS queue."""
        mock_graph.get_or_create_state.return_value = mock_screen_node
        mock_graph.states = {}

        bfs_strategy.select_next_action("new_hash", mock_screen_desc)

        assert len(bfs_strategy.state_queue) == 1
        assert bfs_strategy.state_queue[0].screen_hash == "new_hash"

    def test_new_state_selects_action(
        self, bfs_strategy, mock_graph, mock_screen_node, mock_screen_desc, mock_action
    ):
        """Test that untested action is selected for new state."""
        mock_screen_node.executed_actions = set()
        mock_graph.get_or_create_state.return_value = mock_screen_node
        mock_graph.states = {}

        selected = bfs_strategy.select_next_action("new_hash", mock_screen_desc)

        assert selected is mock_action

    def test_revisited_state_uses_existing_node(
        self, bfs_strategy, mock_graph, mock_screen_node, mock_screen_desc, mock_action
    ):
        """Test that revisited state uses existing graph node."""
        mock_screen_node.executed_actions = set()
        mock_graph.states = {"existing_hash": mock_screen_node}

        bfs_strategy.select_next_action("existing_hash", mock_screen_desc)

        mock_graph.get_or_create_state.assert_not_called()

    def test_exhausted_state_returns_back_action(
        self, bfs_strategy, mock_graph, mock_screen_node, mock_screen_desc, mock_action
    ):
        """Test that exhausted state (no available actions) returns BACK action.

        With continuous exploration mode, when no actions are available,
        the strategy returns a BACK action for navigation instead of None.
        """
        # Empty screen — no actions at all
        mock_screen_desc.get_all_actions.return_value = []
        mock_screen_node.executed_actions = set()
        mock_screen_node.total_actions = 0
        mock_graph.states = {"exhausted_hash": mock_screen_node}

        with patch.object(
            bfs_strategy, "_try_generate_text_input", return_value=None
        ), patch.object(bfs_strategy, "_try_generate_scroll_action", return_value=None):
            selected = bfs_strategy.select_next_action(
                "exhausted_hash", mock_screen_desc
            )

        # With continuous exploration, BACK is returned when no actions available
        assert selected is not None
        assert selected.text == "BACK"
        assert selected.id == 999

    def test_exhausted_state_stays_in_queue_with_continuous_exploration(
        self, bfs_strategy, mock_graph, mock_screen_node, mock_screen_desc, mock_action
    ):
        """Test that state stays in queue with continuous exploration.

        With continuous exploration mode, states are not removed from queue when
        exhausted - they can be re-explored with least-executed actions.
        """
        # Setup exhausted state at front of queue
        bfs_state = BFSState("exhausted_hash", 0, None, 0)
        bfs_strategy.state_queue.append(bfs_state)

        # Empty screen — no actions at all
        mock_screen_desc.get_all_actions.return_value = []
        mock_screen_node.executed_actions = set()
        mock_screen_node.total_actions = 0
        mock_graph.states = {"exhausted_hash": mock_screen_node}

        with patch.object(
            bfs_strategy, "_try_generate_text_input", return_value=None
        ), patch.object(bfs_strategy, "_try_generate_scroll_action", return_value=None):
            bfs_strategy.select_next_action("exhausted_hash", mock_screen_desc)

        # With continuous exploration, state stays in queue for potential re-exploration
        assert len(bfs_strategy.state_queue) == 1

    def test_records_action_before_returning(
        self, bfs_strategy, mock_graph, mock_screen_node, mock_screen_desc, mock_action
    ):
        """Test that selected action is recorded before returning."""
        mock_screen_node.executed_actions = set()
        mock_graph.get_or_create_state.return_value = mock_screen_node
        mock_graph.states = {}

        bfs_strategy.select_next_action("new_hash", mock_screen_desc)

        mock_graph.record_action.assert_called_once()


# =============================================================================
# BFSStrategy Queue Behavior Tests (Key Difference from DFS)
# =============================================================================


class TestBFSStrategyQueueBehavior:
    """Tests for BFS queue behavior (FIFO - First In First Out)."""

    def test_queue_is_fifo(self, bfs_strategy):
        """Test that queue operates as FIFO."""
        # Add states in order
        bfs_strategy.state_queue.append(BFSState("first", 0, None, 5))
        bfs_strategy.state_queue.append(BFSState("second", 1, "first", 3))
        bfs_strategy.state_queue.append(BFSState("third", 1, "first", 4))

        # First added should be first out
        first_out = bfs_strategy.state_queue.popleft()
        assert first_out.screen_hash == "first"

        second_out = bfs_strategy.state_queue.popleft()
        assert second_out.screen_hash == "second"

    def test_queue_level_order_traversal(
        self, bfs_strategy, mock_graph, mock_screen_node
    ):
        """Test that BFS explores level-by-level."""
        # Simulate exploration: root -> child1, child2 -> grandchild1
        # BFS should visit in order: root, child1, child2, grandchild1

        # Create mock screen descriptions for different states
        mock_screen_root = MagicMock(spec=ScreenDescription)
        mock_screen_root.activity = "RootActivity"
        mock_screen_root.items = []  # Empty items to avoid scroll detection
        mock_action_root = MagicMock(spec=ItemAction)
        mock_action_root.id = "root_action"
        mock_action_root.target_view = {}
        mock_action_root.get_execution_coordinates.return_value = (100, 200)
        mock_action_root.coords_for_matching = ((100, 200), "CLICK")
        mock_screen_root.get_all_actions.return_value = [mock_action_root]

        mock_node_root = MagicMock()
        mock_node_root.total_actions = 1
        mock_node_root.executed_actions = set()
        mock_node_root.visit_count = 1

        mock_graph.get_or_create_state.return_value = mock_node_root
        mock_graph.states = {}

        # Visit root state
        bfs_strategy.select_next_action("root_hash", mock_screen_root)

        # State should be in queue
        assert len(bfs_strategy.state_queue) == 1
        assert bfs_strategy.state_queue[0].screen_hash == "root_hash"
        assert bfs_strategy.state_queue[0].depth == 0


# =============================================================================
# BFSStrategy Integration Tests
# =============================================================================


class TestBFSStrategyIntegration:
    """Integration tests for BFSStrategy."""

    def test_full_exploration_flow(self, mock_graph):
        """Test complete BFS exploration flow with multiple states."""
        strategy = BFSStrategy(graph=mock_graph)

        # Setup nodes
        node1 = MagicMock()
        node1.total_actions = 2
        node1.executed_actions = set()
        node1.visit_count = 1

        node2 = MagicMock()
        node2.total_actions = 1
        node2.executed_actions = set()
        node2.visit_count = 1

        mock_graph.get_or_create_state.side_effect = [node1, node2]

        # Setup screens with actions
        action1 = MagicMock(spec=ItemAction)
        action1.id = "1"
        action1.target_view = {}
        action1.get_execution_coordinates.return_value = (100, 200)
        action1.coords_for_matching = ((100, 200), "CLICK")

        action2 = MagicMock(spec=ItemAction)
        action2.id = "2"
        action2.target_view = {}
        action2.get_execution_coordinates.return_value = (300, 400)
        action2.coords_for_matching = ((300, 400), "CLICK")

        screen1 = MagicMock(spec=ScreenDescription)
        screen1.activity = "Activity1"
        screen1.get_all_actions.return_value = [action1, action2]
        screen1.items = []  # Empty items to avoid scroll detection

        action3 = MagicMock(spec=ItemAction)
        action3.id = "3"
        action3.target_view = {}
        action3.get_execution_coordinates.return_value = (500, 600)
        action3.coords_for_matching = ((500, 600), "CLICK")

        screen2 = MagicMock(spec=ScreenDescription)
        screen2.activity = "Activity2"
        screen2.get_all_actions.return_value = [action3]
        screen2.items = []  # Empty items to avoid scroll detection

        # First state - should select first action
        mock_graph.states = {}
        selected1 = strategy.select_next_action("hash1", screen1)
        assert selected1 is action1

        # Simulate executing action1
        sig1 = strategy._convert_signature_to_optimized(((100, 200), "CLICK"))
        node1.executed_actions.add(sig1)

        # Same state - should select action2 (BFS exhausts current state)
        mock_graph.states = {"hash1": node1}
        selected2 = strategy.select_next_action("hash1", screen1)
        assert selected2 is action2

    def test_depth_tracking(self, mock_graph):
        """Test that depth is correctly tracked during BFS."""
        strategy = BFSStrategy(graph=mock_graph)

        # Initial depth
        assert strategy.current_depth == 0

        # Transition to new state
        strategy.visited_states.add("hash1")
        action = MagicMock(spec=ItemAction)
        strategy.record_transition("hash1", "hash2", action)

        assert strategy.current_depth == 1

        # Another transition to new state
        strategy.visited_states.add("hash2")
        strategy.record_transition("hash2", "hash3", action)

        assert strategy.current_depth == 2

    def test_breadth_first_vs_depth_first(self, mock_graph):
        """Verify BFS explores breadth-first (all children before grandchildren)."""
        strategy = BFSStrategy(graph=mock_graph)

        # In BFS, when at root with 2 children, we should:
        # 1. Explore all actions at root before going to children
        # 2. Add children to queue as we discover them
        # 3. Process children in FIFO order

        # Add two children to queue (simulating discovery from root)
        strategy.state_queue.append(BFSState("child1", 1, "root", 3))
        strategy.state_queue.append(BFSState("child2", 1, "root", 2))

        # First dequeue should be child1 (FIFO)
        first = strategy.state_queue.popleft()
        assert first.screen_hash == "child1"

        # Second should be child2
        second = strategy.state_queue.popleft()
        assert second.screen_hash == "child2"
