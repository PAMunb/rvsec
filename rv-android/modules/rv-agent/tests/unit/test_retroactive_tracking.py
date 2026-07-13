"""
Unit tests for Group 40: Retroactive RVTRACK tracking additions.

Tests the tracking calls added retroactively to existing code paths:
(40.3) Plateau tracking in record_transition
(40.4) Level 2 BFS backtrack tracking and stuck recovery form action tracking
(40.6) system_action_filtered counter in _select_with_score_decay
(40.7) Aggregate counters in rv_agent.run() results
"""

import logging
from unittest.mock import MagicMock

import pytest
from rv_agent import tracking as track
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.domain.screen_node import ScreenNode
from support_config import make_agent_config


@pytest.fixture(autouse=True)
def reset_tracking_counters():
    """Reset tracking counters before and after each test."""
    track.reset_counters()
    yield
    track.reset_counters()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides):
    """Create a real RVAgentConfig with test defaults (shared factory)."""
    return make_agent_config(package_name="com.example.app", **overrides)


def _make_strategy(config=None):
    """Create a RVAgentStrategy with minimal dependencies."""
    from rv_agent.memory.ui_coverage import UICoverageTracker
    from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy

    if config is None:
        config = _make_config()

    graph = DynamicStateGraph(
        multi_value_saturation_threshold=config.multi_value_saturation_threshold
    )
    ui_coverage = UICoverageTracker()

    strategy = RVAgentStrategy(
        graph=graph,
        ui_coverage=ui_coverage,
        config=config,
        static_data=None,
        transition_manager=None,
    )
    return strategy


# ---------------------------------------------------------------------------
# 40.3 — Plateau tracking in record_transition
# ---------------------------------------------------------------------------


class TestPlateauTracking:
    """Test that record_transition emits RVTRACK:STRATEGY with mode=plateau."""

    def test_plateau_tracking_emitted_on_new_state(self, caplog):
        """record_transition emits plateau tracking with discovered_new=True
        when a new state was discovered in the preceding select_next_action."""
        strategy = _make_strategy()
        strategy._current_iteration = 5
        # Simulate that select_next_action discovered a new state
        strategy._last_is_new_state = True

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            strategy.record_transition(
                from_hash="aaa111222333",
                to_hash="bbb444555666",
                action_signature=((100, 200), "click"),
            )

        rvtrack_msgs = [
            r.message for r in caplog.records if "RVTRACK:STRATEGY" in r.message
        ]
        assert len(rvtrack_msgs) >= 1, "Expected RVTRACK:STRATEGY log for plateau"
        plateau_msgs = [m for m in rvtrack_msgs if "mode=plateau" in m]
        assert len(plateau_msgs) == 1
        assert "discovered_new=True" in plateau_msgs[0]

    def test_plateau_tracking_emitted_on_revisited_state(self, caplog):
        """record_transition emits plateau tracking with discovered_new=False
        when revisiting an existing state."""
        strategy = _make_strategy()
        strategy._current_iteration = 10
        strategy._last_is_new_state = False

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            strategy.record_transition(
                from_hash="aaa111222333",
                to_hash="bbb444555666",
                action_signature=((300, 400), "click"),
            )

        rvtrack_msgs = [
            r.message for r in caplog.records if "RVTRACK:STRATEGY" in r.message
        ]
        plateau_msgs = [m for m in rvtrack_msgs if "mode=plateau" in m]
        assert len(plateau_msgs) == 1
        assert "discovered_new=False" in plateau_msgs[0]

    def test_plateau_tracking_uses_correct_iteration(self, caplog):
        """The iter= field in the plateau tracking log matches _current_iteration."""
        strategy = _make_strategy()
        strategy._current_iteration = 42
        strategy._last_is_new_state = False

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            strategy.record_transition(
                from_hash="aaa111222333",
                to_hash="bbb444555666",
                action_signature=((100, 200), "click"),
            )

        plateau_msgs = [
            r.message
            for r in caplog.records
            if "RVTRACK:STRATEGY" in r.message and "mode=plateau" in r.message
        ]
        assert len(plateau_msgs) == 1
        assert "iter=42" in plateau_msgs[0]

    def test_plateau_tracking_emitted_on_self_loop(self, caplog):
        """Plateau tracking is emitted even for self-loop transitions
        (same from_hash and to_hash), because plateau detector records
        all iterations including self-loops."""
        strategy = _make_strategy()
        strategy._current_iteration = 7
        strategy._last_is_new_state = False

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            strategy.record_transition(
                from_hash="same_hash_123",
                to_hash="same_hash_123",
                action_signature=((100, 200), "click"),
            )

        plateau_msgs = [
            r.message
            for r in caplog.records
            if "RVTRACK:STRATEGY" in r.message and "mode=plateau" in r.message
        ]
        assert len(plateau_msgs) == 1
        assert "discovered_new=False" in plateau_msgs[0]


# ---------------------------------------------------------------------------
# 40.4 — Level 2 BFS backtrack tracking in learn_node
# ---------------------------------------------------------------------------


class TestBfsBacktrackTracking:
    """Test that learn_node emits RVTRACK:BACKTRACK with strategy=bfs_stuck
    when Backtrack BFS finds an unsaturated target."""

    def _make_agent_for_learn_node(self, bfs_result=None):
        """Create a mock agent suitable for learn_node Level 2 stuck detection."""
        agent = MagicMock()

        # Level 1 stuck detection setup
        agent.last_screen_hash = "stuck_hash_1"
        agent.stuck_screen_count = 0
        agent.error_recovery_count = 0
        agent.BASE_STUCK_THRESHOLD = 8
        agent.STUCK_THRESHOLD_FACTOR = 1.5
        agent._last_action_was_stuck_back = False
        agent._cached_screen_desc = None

        # Config
        agent.config.error_detection_enabled = False

        # StuckRecovery - triggers "restart" recovery on this call
        stuck_recovery = MagicMock()
        stuck_recovery.max_blocks = 10
        stuck_recovery.check.return_value = "restart"
        agent.stuck_recovery = stuck_recovery

        # SuccessorTracker with BFS result
        successor_tracker = MagicMock()
        successor_tracker.find_nearest_unsaturated.return_value = bfs_result
        agent.strategy.successor_tracker = successor_tracker

        # PathBuffer (mock)
        path_buffer = MagicMock()
        path_buffer.is_active = False
        agent.strategy.path_buffer = path_buffer

        # RewardPropagator (mock)
        agent.strategy.reward_propagator = None

        # Memory coordinator
        agent.memory_coordinator.update_memories.return_value = {
            "recent_action_window": [],
        }
        agent.memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": "",
        }
        agent.memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [],
            "state_transitions": [],
        }
        agent.memory_coordinator.check_continuation.return_value = {
            "should_continue": True,
        }

        # Strategy graph (for _record_action_success)
        agent.strategy.graph = MagicMock()
        agent.strategy.graph.states = {}

        return agent

    def test_bfs_backtrack_emits_strategy_and_remaining_steps(self, caplog):
        """When BFS finds an unsaturated state 3 hops away,
        RVTRACK:BACKTRACK is emitted with strategy=bfs_stuck and remaining=3."""
        from rv_agent.agent.nodes.learn_node import learn_node

        bfs_result = ("unsaturated_target_hash", 3)
        agent = self._make_agent_for_learn_node(bfs_result=bfs_result)

        state = {
            "iteration": 15,
            "current_screen_hash": "stuck_hash_1",
            "previous_screen_hash": "prev_hash_abc",
            "current_action": {"action_type": "CLICK", "x": 100, "y": 200},
            "current_item_action": None,
            "current_activity": ".MainActivity",
            "previous_activity": ".MainActivity",
            "screen_description": None,
            "error_detection_screenshot": None,
            "recent_action_window": [],
            "visited_states": [],
            "state_transitions": [],
            "start_time": 0,
            "timeout": 300,
            "previous_action_signature": None,
        }

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            learn_node(agent, state)

        backtrack_msgs = [
            r.message for r in caplog.records if "RVTRACK:BACKTRACK" in r.message
        ]
        assert len(backtrack_msgs) >= 1, "Expected RVTRACK:BACKTRACK log"

        bfs_msg = [m for m in backtrack_msgs if "strategy=bfs_stuck" in m]
        assert (
            len(bfs_msg) == 1
        ), f"Expected strategy=bfs_stuck in backtrack msgs: {backtrack_msgs}"
        assert "remaining=3" in bfs_msg[0]
        assert "reason=bfs_unsaturated" in bfs_msg[0]

    def test_bfs_backtrack_includes_from_and_to_state(self, caplog):
        """RVTRACK:BACKTRACK includes truncated from_state and to_state hashes."""
        from rv_agent.agent.nodes.learn_node import learn_node

        bfs_result = ("target_hash_abcdef", 2)
        agent = self._make_agent_for_learn_node(bfs_result=bfs_result)

        state = {
            "iteration": 8,
            "current_screen_hash": "stuck_hash_1",
            "previous_screen_hash": "prev_hash_abc",
            "current_action": {"action_type": "CLICK", "x": 50, "y": 60},
            "current_item_action": None,
            "current_activity": ".MainActivity",
            "previous_activity": ".MainActivity",
            "screen_description": None,
            "error_detection_screenshot": None,
            "recent_action_window": [],
            "visited_states": [],
            "state_transitions": [],
            "start_time": 0,
            "timeout": 300,
            "previous_action_signature": None,
        }

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            learn_node(agent, state)

        bfs_msgs = [
            r.message
            for r in caplog.records
            if "RVTRACK:BACKTRACK" in r.message and "strategy=bfs_stuck" in r.message
        ]
        assert len(bfs_msgs) == 1
        # from_state should be the current_screen_hash truncated to 8 chars
        assert "from_state=stuck_ha" in bfs_msgs[0]
        # to_state should be the BFS target truncated to 8 chars
        assert "to_state=target_h" in bfs_msgs[0]


# ---------------------------------------------------------------------------
# 40.4 — Stuck recovery form action tracking in learn_node
# ---------------------------------------------------------------------------


class TestFormActionStuckTracking:
    """Test that learn_node emits RVTRACK:STRATEGY with mode=stuck
    when stuck_recovery.check() is called and the action is a form action."""

    def _make_agent_for_form_tracking(self):
        """Create a mock agent for form action stuck tracking."""
        agent = MagicMock()

        agent.last_screen_hash = "form_hash_12"
        agent.stuck_screen_count = 0
        agent.error_recovery_count = 0
        agent.BASE_STUCK_THRESHOLD = 8
        agent.STUCK_THRESHOLD_FACTOR = 1.5
        agent._last_action_was_stuck_back = False
        agent._cached_screen_desc = None

        agent.config.error_detection_enabled = False

        # StuckRecovery returns None (not triggered)
        stuck_recovery = MagicMock()
        stuck_recovery.max_blocks = 10
        stuck_recovery.check.return_value = None
        agent.stuck_recovery = stuck_recovery

        # Strategy components
        agent.strategy.successor_tracker = MagicMock()
        agent.strategy.path_buffer = MagicMock()
        agent.strategy.path_buffer.is_active = False
        agent.strategy.reward_propagator = None
        agent.strategy.graph = MagicMock()
        agent.strategy.graph.states = {}
        agent.strategy.value_generator = MagicMock()
        agent.strategy.value_generator.tested_values = {}

        # Memory coordinator
        agent.memory_coordinator.update_memories.return_value = {
            "recent_action_window": [],
        }
        agent.memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": "",
        }
        agent.memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [],
            "state_transitions": [],
        }
        agent.memory_coordinator.check_continuation.return_value = {
            "should_continue": True,
        }

        return agent

    def test_form_action_set_text_emits_strategy_stuck(self, caplog):
        """When action_type is SET_TEXT (a form action), RVTRACK:STRATEGY
        is emitted with mode=stuck and reason=is_form=True."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = self._make_agent_for_form_tracking()

        state = {
            "iteration": 12,
            "current_screen_hash": "form_hash_12",
            "previous_screen_hash": "prev_hash_xyz",
            "current_action": {
                "action_type": "SET_TEXT",
                "x": 300,
                "y": 500,
                "text": "hello",
            },
            "current_item_action": None,
            "current_activity": ".FormActivity",
            "previous_activity": ".FormActivity",
            "screen_description": None,
            "error_detection_screenshot": None,
            "recent_action_window": [],
            "visited_states": [],
            "state_transitions": [],
            "start_time": 0,
            "timeout": 300,
            "previous_action_signature": None,
            "decision_maker": "algorithm",
        }

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            learn_node(agent, state)

        strategy_msgs = [
            r.message
            for r in caplog.records
            if "RVTRACK:STRATEGY" in r.message and "mode=stuck" in r.message
        ]
        assert len(strategy_msgs) >= 1, (
            f"Expected RVTRACK:STRATEGY with mode=stuck, got: "
            f"{[r.message for r in caplog.records if 'RVTRACK' in r.message]}"
        )
        assert "action=SET_TEXT" in strategy_msgs[0]
        assert "reason=is_form=True" in strategy_msgs[0]

    def test_form_action_text_change_emits_strategy_stuck(self, caplog):
        """TEXT_CHANGE actions also trigger the form action tracking."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = self._make_agent_for_form_tracking()

        state = {
            "iteration": 20,
            "current_screen_hash": "form_hash_12",
            "previous_screen_hash": "prev_hash_xyz",
            "current_action": {
                "action_type": "TEXT_CHANGE",
                "x": 300,
                "y": 500,
                "text": "world",
            },
            "current_item_action": None,
            "current_activity": ".FormActivity",
            "previous_activity": ".FormActivity",
            "screen_description": None,
            "error_detection_screenshot": None,
            "recent_action_window": [],
            "visited_states": [],
            "state_transitions": [],
            "start_time": 0,
            "timeout": 300,
            "previous_action_signature": None,
            "decision_maker": "algorithm",
        }

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            learn_node(agent, state)

        strategy_msgs = [
            r.message
            for r in caplog.records
            if "RVTRACK:STRATEGY" in r.message and "mode=stuck" in r.message
        ]
        assert len(strategy_msgs) >= 1
        assert "action=TEXT_CHANGE" in strategy_msgs[0]

    def test_checkable_action_emits_strategy_stuck(self, caplog):
        """Checkable widget actions (checkbox, toggle) also count as form actions."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = self._make_agent_for_form_tracking()

        # Create a checkable item_action
        mock_item_action = MagicMock()
        mock_item_action.target_view = {"checkable": True}

        state = {
            "iteration": 25,
            "current_screen_hash": "form_hash_12",
            "previous_screen_hash": "prev_hash_xyz",
            "current_action": {"action_type": "CLICK", "x": 300, "y": 500},
            "current_item_action": mock_item_action,
            "current_activity": ".SettingsActivity",
            "previous_activity": ".SettingsActivity",
            "screen_description": None,
            "error_detection_screenshot": None,
            "recent_action_window": [],
            "visited_states": [],
            "state_transitions": [],
            "start_time": 0,
            "timeout": 300,
            "previous_action_signature": None,
            "decision_maker": "algorithm",
        }

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            learn_node(agent, state)

        strategy_msgs = [
            r.message
            for r in caplog.records
            if "RVTRACK:STRATEGY" in r.message and "mode=stuck" in r.message
        ]
        assert len(strategy_msgs) >= 1
        # is_form_action should be True because the widget is checkable
        assert "reason=is_form=True" in strategy_msgs[0]

    def test_non_form_action_does_not_emit_stuck_tracking(self, caplog):
        """Regular CLICK actions (not form actions) should NOT emit
        RVTRACK:STRATEGY with mode=stuck."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = self._make_agent_for_form_tracking()

        state = {
            "iteration": 30,
            "current_screen_hash": "changed_hash",
            "previous_screen_hash": "prev_hash_xyz",
            "current_action": {"action_type": "CLICK", "x": 100, "y": 200},
            "current_item_action": None,
            "current_activity": ".MainActivity",
            "previous_activity": ".MainActivity",
            "screen_description": None,
            "error_detection_screenshot": None,
            "recent_action_window": [],
            "visited_states": [],
            "state_transitions": [],
            "start_time": 0,
            "timeout": 300,
            "previous_action_signature": None,
            "decision_maker": "algorithm",
        }

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            learn_node(agent, state)

        strategy_msgs = [
            r.message
            for r in caplog.records
            if "RVTRACK:STRATEGY" in r.message and "mode=stuck" in r.message
        ]
        assert (
            len(strategy_msgs) == 0
        ), f"Non-form CLICK should not emit mode=stuck, but got: {strategy_msgs}"


# ---------------------------------------------------------------------------
# 40.6 — system_action_filtered counter in _select_with_score_decay
# ---------------------------------------------------------------------------


class TestSystemActionFilteredCounter:
    """Test that filtering system actions (BACK/RESTART) in Tier 4
    increments track._counters['system_action_filtered']."""

    def test_filtering_back_increments_counter(self):
        """A BACK action in the actions list is filtered out and increments
        the system_action_filtered counter."""
        from rv_android_core.domain.widget import WidgetEventType
        from rv_screen_parser.parser.screen.visitor.model import (
            ItemAction,
            ScreenDescription,
        )

        strategy = _make_strategy()

        # Create a screen node in the graph
        screen_hash = "test_hash_abc"
        node = ScreenNode(
            screen_hash=screen_hash, activity=".MainActivity", total_actions=2
        )
        strategy.graph.states[screen_hash] = node
        strategy._current_hash = screen_hash

        # Create a real action and a BACK system action
        real_action = ItemAction(
            id=1,
            text="Button1",
            event=WidgetEventType.CLICK,
            reaches_target=False,
            directly_reaches_target=False,
            target_view={
                "class": "android.widget.Button",
                "package": "com.example.app",
            },
            coordinates=(540, 500),
            text_input=None,
        )
        back_action = ItemAction(
            id=999,
            text="BACK",
            event=WidgetEventType.BACK,
            reaches_target=False,
            directly_reaches_target=False,
            target_view={"system_action": True, "class": "SystemAction_BACK"},
            coordinates=None,
            text_input=None,
        )

        # Create a minimal screen description
        mock_screen_desc = MagicMock(spec=ScreenDescription)
        mock_screen_desc.items = []
        mock_screen_desc.activity = ".MainActivity"

        assert track._counters["system_action_filtered"] == 0

        strategy._select_with_score_decay(
            actions=[real_action, back_action],
            screen_desc=mock_screen_desc,
            node=node,
        )

        assert track._counters["system_action_filtered"] == 1

    def test_filtering_restart_increments_counter(self):
        """A RESTART action in the actions list is filtered and counted."""
        from rv_android_core.domain.widget import WidgetEventType
        from rv_screen_parser.parser.screen.visitor.model import (
            ItemAction,
            ScreenDescription,
        )

        strategy = _make_strategy()

        screen_hash = "test_hash_def"
        node = ScreenNode(
            screen_hash=screen_hash, activity=".MainActivity", total_actions=2
        )
        strategy.graph.states[screen_hash] = node
        strategy._current_hash = screen_hash

        real_action = ItemAction(
            id=1,
            text="Submit",
            event=WidgetEventType.CLICK,
            reaches_target=False,
            directly_reaches_target=False,
            target_view={
                "class": "android.widget.Button",
                "package": "com.example.app",
            },
            coordinates=(540, 600),
            text_input=None,
        )
        restart_action = ItemAction(
            id=999,
            text="RESTART_APP:com.example.app",
            event=WidgetEventType.RESTART,
            reaches_target=False,
            directly_reaches_target=False,
            target_view={
                "system_action": True,
                "class": "SystemAction_RESTART",
                "package_name": "com.example.app",
            },
            coordinates=None,
            text_input=None,
        )

        mock_screen_desc = MagicMock(spec=ScreenDescription)
        mock_screen_desc.items = []
        mock_screen_desc.activity = ".MainActivity"

        assert track._counters["system_action_filtered"] == 0

        strategy._select_with_score_decay(
            actions=[real_action, restart_action],
            screen_desc=mock_screen_desc,
            node=node,
        )

        assert track._counters["system_action_filtered"] == 1

    def test_multiple_system_actions_counted(self):
        """When both BACK and RESTART are in the list, counter increments by 2."""
        from rv_android_core.domain.widget import WidgetEventType
        from rv_screen_parser.parser.screen.visitor.model import (
            ItemAction,
            ScreenDescription,
        )

        strategy = _make_strategy()

        screen_hash = "test_hash_ghi"
        node = ScreenNode(
            screen_hash=screen_hash, activity=".MainActivity", total_actions=3
        )
        strategy.graph.states[screen_hash] = node
        strategy._current_hash = screen_hash

        real_action = ItemAction(
            id=1,
            text="OK",
            event=WidgetEventType.CLICK,
            reaches_target=False,
            directly_reaches_target=False,
            target_view={
                "class": "android.widget.Button",
                "package": "com.example.app",
            },
            coordinates=(540, 700),
            text_input=None,
        )
        back_action = ItemAction(
            id=998,
            text="BACK",
            event=WidgetEventType.BACK,
            reaches_target=False,
            directly_reaches_target=False,
            target_view={"system_action": True, "class": "SystemAction_BACK"},
            coordinates=None,
            text_input=None,
        )
        restart_action = ItemAction(
            id=999,
            text="RESTART_APP:com.example.app",
            event=WidgetEventType.RESTART,
            reaches_target=False,
            directly_reaches_target=False,
            target_view={
                "system_action": True,
                "class": "SystemAction_RESTART",
                "package_name": "com.example.app",
            },
            coordinates=None,
            text_input=None,
        )

        mock_screen_desc = MagicMock(spec=ScreenDescription)
        mock_screen_desc.items = []
        mock_screen_desc.activity = ".MainActivity"

        strategy._select_with_score_decay(
            actions=[real_action, back_action, restart_action],
            screen_desc=mock_screen_desc,
            node=node,
        )

        assert track._counters["system_action_filtered"] == 2

    def test_no_system_actions_counter_stays_zero(self):
        """When there are no system actions, the counter remains 0."""
        from rv_android_core.domain.widget import WidgetEventType
        from rv_screen_parser.parser.screen.visitor.model import (
            ItemAction,
            ScreenDescription,
        )

        strategy = _make_strategy()

        screen_hash = "test_hash_jkl"
        node = ScreenNode(
            screen_hash=screen_hash, activity=".MainActivity", total_actions=2
        )
        strategy.graph.states[screen_hash] = node
        strategy._current_hash = screen_hash

        action1 = ItemAction(
            id=1,
            text="Login",
            event=WidgetEventType.CLICK,
            reaches_target=False,
            directly_reaches_target=False,
            target_view={
                "class": "android.widget.Button",
                "package": "com.example.app",
            },
            coordinates=(540, 500),
            text_input=None,
        )
        action2 = ItemAction(
            id=2,
            text="Register",
            event=WidgetEventType.CLICK,
            reaches_target=False,
            directly_reaches_target=False,
            target_view={
                "class": "android.widget.Button",
                "package": "com.example.app",
            },
            coordinates=(540, 700),
            text_input=None,
        )

        mock_screen_desc = MagicMock(spec=ScreenDescription)
        mock_screen_desc.items = []
        mock_screen_desc.activity = ".MainActivity"

        strategy._select_with_score_decay(
            actions=[action1, action2],
            screen_desc=mock_screen_desc,
            node=node,
        )

        assert track._counters["system_action_filtered"] == 0


# ---------------------------------------------------------------------------
# 40.7 — Aggregate counters in rv_agent.run() results
# ---------------------------------------------------------------------------


class TestAggregateCountersInResults:
    """Test that rv_agent.run() includes tracking_counters in its results dict."""

    def test_results_contain_tracking_counters_key(self):
        """The results dict from run() includes 'tracking_counters' with
        the output of track.get_aggregate_counters()."""
        from rv_agent.agent.rv_agent import RVAgent

        # Create a fully-mocked RVAgent. We mock enough to make run() complete
        # immediately via timeout.
        config = MagicMock()
        config.get_agent_mode.return_value = "pure_algorithm"
        config.package_name = "com.example.app"
        config.timeout = 0  # Expire immediately
        config.metrics_output_dir = None
        config.strategy = "rvagent"
        config.agent_mode = "pure_algorithm"

        device = MagicMock()
        dynamic_graph = MagicMock()
        strategy = MagicMock()
        image_handler = MagicMock()
        screen_processor = MagicMock()
        routing_manager = MagicMock()
        routing_manager.get_decision_counters.return_value = {
            "total_actions": 0,
            "llm_executed": 0,
            "algorithm_chosen": 0,
            "llm_percentage": 0.0,
            "algorithm_percentage": 0.0,
            "llm_validation_failed": 0,
            "screenshot_failed": 0,
            "forced_back": 0,
        }
        tool_executor = MagicMock()
        memory_coordinator = MagicMock()
        memory_coordinator.get_all_statistics.return_value = {}
        ui_coverage = MagicMock()
        ui_coverage.get_comprehensive_metrics.return_value = {}

        agent = RVAgent(
            config=config,
            device=device,
            dynamic_graph=dynamic_graph,
            exploration_strategy=strategy,
            image_handler=image_handler,
            screen_processor=screen_processor,
            llm_client=None,
            routing_manager=routing_manager,
            tool_executor=tool_executor,
            memory_coordinator=memory_coordinator,
            ui_coverage=ui_coverage,
        )

        results = agent.run()

        assert (
            "tracking_counters" in results
        ), f"Expected 'tracking_counters' key in results, got keys: {list(results.keys())}"
        counters = results["tracking_counters"]
        assert isinstance(counters, dict)
        # Verify it contains known counter keys
        assert "backtrack_count" in counters
        assert "system_action_filtered" in counters
        assert "path_buffer_hit_rate_pct" in counters

    def test_tracking_counters_reflect_current_values(self):
        """The tracking_counters in results reflect the actual counter values
        from the tracking module."""
        from rv_agent.agent.rv_agent import RVAgent

        # Pre-set a counter value to verify it appears in results
        track._counters["backtrack_count"] = 7
        track._counters["system_action_filtered"] = 3

        config = MagicMock()
        config.get_agent_mode.return_value = "pure_algorithm"
        config.package_name = "com.example.app"
        config.timeout = 0
        config.metrics_output_dir = None
        config.strategy = "rvagent"
        config.agent_mode = "pure_algorithm"

        device = MagicMock()
        routing_manager = MagicMock()
        routing_manager.get_decision_counters.return_value = {
            "total_actions": 0,
            "llm_executed": 0,
            "algorithm_chosen": 0,
            "llm_percentage": 0.0,
            "algorithm_percentage": 0.0,
            "llm_validation_failed": 0,
            "screenshot_failed": 0,
            "forced_back": 0,
        }
        memory_coordinator = MagicMock()
        memory_coordinator.get_all_statistics.return_value = {}
        ui_coverage = MagicMock()
        ui_coverage.get_comprehensive_metrics.return_value = {}

        agent = RVAgent(
            config=config,
            device=device,
            dynamic_graph=MagicMock(),
            exploration_strategy=MagicMock(),
            image_handler=MagicMock(),
            screen_processor=MagicMock(),
            llm_client=None,
            routing_manager=routing_manager,
            tool_executor=MagicMock(),
            memory_coordinator=memory_coordinator,
            ui_coverage=ui_coverage,
        )

        results = agent.run()

        assert results["tracking_counters"]["backtrack_count"] == 7
        assert results["tracking_counters"]["system_action_filtered"] == 3
