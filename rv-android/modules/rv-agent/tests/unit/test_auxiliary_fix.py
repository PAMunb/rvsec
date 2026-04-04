"""
Unit tests for Group 37: Auxiliary fixes (gh26-exploration-strategy).

Tests:
(a) previous_activity -- learn_node sets previous_activity in result and
    activity_changed detects transitions correctly.
(b) _update_cached_bounds -- updates elements without widget_id via
    coordinate proximity fallback.
(c) restart delay -- ToolExecutor._execute_restart has time.sleep(1)
    between stop_app and start_app.
(d) RVTRACK:STATE tracking -- track.state() includes activity_from when
    activity changes and omits it when unchanged.
"""

import logging
from unittest.mock import MagicMock, patch


from rv_agent.agent.nodes.learn_node import learn_node
from rv_agent.agent.nodes.parse_node import _update_cached_bounds
from rv_agent.execution.tool_executor import ToolExecutor
from rv_agent import tracking as track

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_agent():
    """Create a minimally mocked RVAgent for learn_node tests.

    Mocks every dependency that learn_node touches so the function can
    execute without side effects.
    """
    agent = MagicMock()

    # MemoryCoordinator returns
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

    # Stuck recovery
    agent.stuck_recovery = None
    agent.stuck_screen_count = 0
    agent.last_screen_hash = None
    agent.error_recovery_count = 0
    agent._last_action_was_stuck_back = False
    agent._cached_screen_desc = None

    # Config for error detection
    agent.config.error_detection_enabled = False

    # Strategy attributes that learn_node may access
    agent.strategy.successor_tracker = MagicMock()
    agent.strategy.reward_propagator = None
    agent.strategy.path_buffer = None
    agent.strategy.value_generator = None

    # Dynamic threshold attributes
    agent.BASE_STUCK_THRESHOLD = 8
    agent.STUCK_THRESHOLD_FACTOR = 1.5

    return agent


def _make_minimal_state(**overrides):
    """Create a minimal AgentState dict for learn_node tests."""
    state = {
        "iteration": 1,
        "current_screen_hash": "hash_abc",
        "current_activity": "com.example.MainActivity",
        "previous_screen_hash": "hash_xyz",
        "previous_activity": None,
        "current_action": {"action_type": "CLICK", "x": 100, "y": 200},
        "current_item_action": None,
        "screen_description": None,
        "error_detection_screenshot": None,
        "start_time": 0.0,
        "timeout": 300,
        "recent_action_window": [],
        "visited_states": [],
        "state_transitions": [],
        "llm_reasoning": "",
        "decision_maker": "algorithm",
        "previous_action_signature": None,
    }
    state.update(overrides)
    return state


# ---------------------------------------------------------------------------
# (a) previous_activity -- learn_node sets it and activity_changed detects
#     transitions
# ---------------------------------------------------------------------------


class TestPreviousActivity:
    """(a) learn_node sets previous_activity from current_activity."""

    def test_learn_node_sets_previous_activity_from_current(self):
        """Result dict should contain previous_activity = state's current_activity."""
        agent = _make_minimal_agent()
        state = _make_minimal_state(
            current_activity="com.example.SettingsActivity",
        )

        result = learn_node(agent, state)

        assert "previous_activity" in result
        assert result["previous_activity"] == "com.example.SettingsActivity"

    def test_learn_node_sets_previous_activity_none_when_no_current(self):
        """When current_activity is missing, previous_activity is None."""
        agent = _make_minimal_agent()
        state = _make_minimal_state()
        # Remove current_activity so state.get returns default
        del state["current_activity"]

        result = learn_node(agent, state)

        # state.get("current_activity") returns None when key is missing
        assert result["previous_activity"] is None

    def test_activity_changed_true_when_different(self):
        """activity_changed is True when previous != current and previous is not None."""
        agent = _make_minimal_agent()
        state = _make_minimal_state(
            previous_activity="com.example.ActivityA",
            current_activity="com.example.ActivityB",
        )

        # Capture track.state call to verify changed=True
        with patch.object(track, "state") as mock_state:
            learn_node(agent, state)
            mock_state.assert_called_once()
            call_kwargs = mock_state.call_args[1]
            assert call_kwargs["changed"] is True
            assert call_kwargs["activity_from"] == "com.example.ActivityA"
            assert call_kwargs["activity_to"] == "com.example.ActivityB"

    def test_activity_changed_false_when_same(self):
        """activity_changed is False when previous == current."""
        agent = _make_minimal_agent()
        state = _make_minimal_state(
            previous_activity="com.example.MainActivity",
            current_activity="com.example.MainActivity",
        )

        with patch.object(track, "state") as mock_state:
            learn_node(agent, state)
            mock_state.assert_called_once()
            call_kwargs = mock_state.call_args[1]
            assert call_kwargs["changed"] is False

    def test_activity_changed_false_when_previous_is_none(self):
        """activity_changed is False when previous_activity is None (first iteration)."""
        agent = _make_minimal_agent()
        state = _make_minimal_state(
            previous_activity=None,
            current_activity="com.example.MainActivity",
        )

        with patch.object(track, "state") as mock_state:
            learn_node(agent, state)
            mock_state.assert_called_once()
            call_kwargs = mock_state.call_args[1]
            assert call_kwargs["changed"] is False


# ---------------------------------------------------------------------------
# (b) _update_cached_bounds -- updates elements without widget_id via
#     coordinate proximity fallback
# ---------------------------------------------------------------------------


def _make_item_action(widget_id, bounds):
    """Create a mock ItemAction with widget_id and bounds in target_view."""
    action = MagicMock()
    action.widget_id = widget_id
    action.target_view = {"bounds": list(bounds)} if bounds else None
    return action


def _make_screen_desc_with_actions(action_specs):
    """Create a mock ScreenDescription with items containing actions.

    Args:
        action_specs: list of (widget_id, bounds) tuples.
            Each tuple becomes one action inside one item.
    """
    desc = MagicMock()
    items = []
    for widget_id, bounds in action_specs:
        item = MagicMock()
        item.actions = [_make_item_action(widget_id, bounds)]
        items.append(item)
    desc.items = items
    return desc


class TestUpdateCachedBounds:
    """(b) _update_cached_bounds updates elements with and without widget_id."""

    def test_updates_element_with_widget_id(self):
        """Element with widget_id gets its bounds updated from fresh parse."""
        cached = _make_screen_desc_with_actions(
            [
                ("btn_ok", [[0, 0], [200, 100]]),
            ]
        )
        fresh = _make_screen_desc_with_actions(
            [
                ("btn_ok", [[0, 50], [200, 150]]),
            ]
        )

        _update_cached_bounds(cached, fresh)

        updated_bounds = cached.items[0].actions[0].target_view["bounds"]
        assert updated_bounds == [[0, 50], [200, 150]]

    def test_updates_element_without_widget_id_by_proximity(self):
        """Element without widget_id gets updated via coordinate proximity fallback."""
        # Cached element center: ((0+200)//2, (0+100)//2) = (100, 50)
        cached = _make_screen_desc_with_actions(
            [
                (None, [[0, 0], [200, 100]]),
            ]
        )
        # Fresh element shifted down by 30px -- center (100, 80), still within threshold=50
        fresh = _make_screen_desc_with_actions(
            [
                (None, [[0, 30], [200, 130]]),
            ]
        )

        _update_cached_bounds(cached, fresh)

        updated_bounds = cached.items[0].actions[0].target_view["bounds"]
        assert updated_bounds == [[0, 30], [200, 130]]

    def test_no_update_when_proximity_exceeds_threshold(self):
        """Element without widget_id is NOT updated when distance exceeds threshold."""
        # Cached element center: (100, 50)
        cached = _make_screen_desc_with_actions(
            [
                (None, [[0, 0], [200, 100]]),
            ]
        )
        # Fresh element center: ((0+200)//2, (150+250)//2) = (100, 200) -- too far
        fresh = _make_screen_desc_with_actions(
            [
                (None, [[0, 150], [200, 250]]),
            ]
        )

        _update_cached_bounds(cached, fresh)

        # Should remain unchanged
        updated_bounds = cached.items[0].actions[0].target_view["bounds"]
        assert updated_bounds == [[0, 0], [200, 100]]

    def test_widget_id_match_takes_priority(self):
        """Element with widget_id matches by ID, not by proximity."""
        cached = _make_screen_desc_with_actions(
            [
                ("input_email", [[10, 100], [500, 160]]),
            ]
        )
        # Fresh has same widget_id but very different bounds
        fresh = _make_screen_desc_with_actions(
            [
                ("input_email", [[10, 400], [500, 460]]),
            ]
        )

        _update_cached_bounds(cached, fresh)

        updated_bounds = cached.items[0].actions[0].target_view["bounds"]
        assert updated_bounds == [[10, 400], [500, 460]]

    def test_no_update_when_bounds_unchanged(self):
        """No update occurs when cached and fresh bounds are identical."""
        cached = _make_screen_desc_with_actions(
            [
                ("btn_save", [[100, 200], [300, 260]]),
            ]
        )
        fresh = _make_screen_desc_with_actions(
            [
                ("btn_save", [[100, 200], [300, 260]]),
            ]
        )

        _update_cached_bounds(cached, fresh)

        # Bounds remain the same (no unnecessary mutation)
        updated_bounds = cached.items[0].actions[0].target_view["bounds"]
        assert updated_bounds == [[100, 200], [300, 260]]

    def test_mixed_elements_with_and_without_widget_id(self):
        """Both widget_id and no-widget_id elements get updated in same screen."""
        cached = _make_screen_desc_with_actions(
            [
                ("btn_ok", [[0, 0], [200, 100]]),  # Has widget_id
                (None, [[300, 0], [500, 100]]),  # No widget_id, center (400, 50)
            ]
        )
        fresh = _make_screen_desc_with_actions(
            [
                ("btn_ok", [[0, 50], [200, 150]]),  # Shifted down
                (None, [[300, 30], [500, 130]]),  # Shifted down, center (400, 80)
            ]
        )

        _update_cached_bounds(cached, fresh)

        # widget_id element updated
        assert cached.items[0].actions[0].target_view["bounds"] == [[0, 50], [200, 150]]
        # no-widget_id element also updated via proximity
        assert cached.items[1].actions[0].target_view["bounds"] == [
            [300, 30],
            [500, 130],
        ]

    def test_no_update_when_fresh_has_no_items(self):
        """When fresh parse returns no items, cached bounds remain unchanged."""
        cached = _make_screen_desc_with_actions(
            [
                ("btn_ok", [[0, 0], [200, 100]]),
            ]
        )
        fresh = _make_screen_desc_with_actions([])

        _update_cached_bounds(cached, fresh)

        # Unchanged
        assert cached.items[0].actions[0].target_view["bounds"] == [[0, 0], [200, 100]]


# ---------------------------------------------------------------------------
# (c) restart delay -- time.sleep(1) between stop_app and start_app
# ---------------------------------------------------------------------------


class TestRestartDelay:
    """(c) ToolExecutor restart has delay between stop and start."""

    def test_restart_calls_sleep_between_stop_and_start(self):
        """time.sleep(1) is called after stop_app and before start_app."""
        mock_device = MagicMock()
        mock_device.stop_app.return_value = True
        mock_device.start_app.return_value = True

        executor = ToolExecutor(device=mock_device)

        with patch("rv_agent.execution.tool_executor.time.sleep") as mock_sleep:
            executor.execute_action(
                {
                    "action_type": "RESTART_APP",
                    "package_name": "com.example.app",
                }
            )

            mock_sleep.assert_called_once_with(1)

    def test_restart_order_stop_sleep_start(self):
        """Calls happen in order: stop_app -> sleep(1) -> start_app."""
        mock_device = MagicMock()
        mock_device.stop_app.return_value = True
        mock_device.start_app.return_value = True

        executor = ToolExecutor(device=mock_device)
        call_order = []

        mock_device.stop_app.side_effect = lambda pkg: call_order.append("stop")
        mock_device.start_app.side_effect = lambda pkg: call_order.append("start")

        with patch(
            "rv_agent.execution.tool_executor.time.sleep",
            side_effect=lambda s: call_order.append(f"sleep({s})"),
        ):
            executor.execute_action(
                {
                    "action_type": "RESTART_APP",
                    "package_name": "com.example.app",
                }
            )

        assert call_order == ["stop", "sleep(1)", "start"]

    def test_restart_sleep_called_even_when_stop_fails(self):
        """Delay still happens even when stop_app returns False."""
        mock_device = MagicMock()
        mock_device.stop_app.return_value = False
        mock_device.start_app.return_value = True

        executor = ToolExecutor(device=mock_device)

        with patch("rv_agent.execution.tool_executor.time.sleep") as mock_sleep:
            executor.execute_action(
                {
                    "action_type": "RESTART_APP",
                    "package_name": "com.example.app",
                }
            )

            mock_sleep.assert_called_once_with(1)

    def test_restart_with_fallback_package_name(self):
        """Restart uses device.config.package_name when action lacks package_name."""
        mock_device = MagicMock()
        mock_device.config.package_name = "com.fallback.app"
        mock_device.stop_app.return_value = True
        mock_device.start_app.return_value = True

        executor = ToolExecutor(device=mock_device)

        with patch("rv_agent.execution.tool_executor.time.sleep"):
            result = executor.execute_action({"action_type": "RESTART_APP"})

        mock_device.stop_app.assert_called_once_with("com.fallback.app")
        mock_device.start_app.assert_called_once_with("com.fallback.app")
        assert result["success"] is True


# ---------------------------------------------------------------------------
# (d) RVTRACK:STATE tracking -- activity_from included when activity changes
# ---------------------------------------------------------------------------


class TestRVTRACKStateTracking:
    """(d) RVTRACK:STATE includes activity_from when activity changes."""

    def test_state_changed_logs_activity_from_and_to(self, caplog):
        """When changed=True, log includes from_activity and to_activity."""
        with caplog.at_level(logging.INFO):
            track.state(
                iter=5,
                changed=True,
                activity_from="com.example.ActivityA",
                activity_to="com.example.ActivityB",
                hash="abcdef12345678",
            )

        assert len(caplog.records) == 1
        log_msg = caplog.records[0].message
        assert "RVTRACK:STATE" in log_msg
        assert "changed=True" in log_msg
        assert "from_activity=com.example.ActivityA" in log_msg
        assert "to_activity=com.example.ActivityB" in log_msg

    def test_state_unchanged_logs_only_changed_false(self, caplog):
        """When changed=False, log omits from/to activity fields."""
        with caplog.at_level(logging.INFO):
            track.state(
                iter=5,
                changed=False,
            )

        assert len(caplog.records) == 1
        log_msg = caplog.records[0].message
        assert "RVTRACK:STATE" in log_msg
        assert "changed=False" in log_msg
        # from_activity and to_activity should NOT be in the message
        assert "from_activity" not in log_msg
        assert "to_activity" not in log_msg

    def test_state_changed_includes_hash(self, caplog):
        """When changed=True, hash is truncated to 8 chars in log."""
        with caplog.at_level(logging.INFO):
            track.state(
                iter=10,
                changed=True,
                activity_from=".ActivityA",
                activity_to=".ActivityB",
                hash="abcdef1234567890",
            )

        log_msg = caplog.records[0].message
        assert "hash=abcdef12" in log_msg

    def test_learn_node_emits_state_tracking_on_activity_change(self, caplog):
        """learn_node calls track.state with changed=True when activity changes."""
        agent = _make_minimal_agent()
        state = _make_minimal_state(
            previous_activity="com.example.OldActivity",
            current_activity="com.example.NewActivity",
            current_screen_hash="hashvalue1234",
        )

        with caplog.at_level(logging.INFO):
            learn_node(agent, state)

        state_logs = [r for r in caplog.records if "RVTRACK:STATE" in r.message]
        assert len(state_logs) == 1
        log_msg = state_logs[0].message
        assert "changed=True" in log_msg
        assert "from_activity=com.example.OldActivity" in log_msg
        assert "to_activity=com.example.NewActivity" in log_msg

    def test_learn_node_emits_state_tracking_no_change(self, caplog):
        """learn_node calls track.state with changed=False when same activity."""
        agent = _make_minimal_agent()
        state = _make_minimal_state(
            previous_activity="com.example.SameActivity",
            current_activity="com.example.SameActivity",
            current_screen_hash="hashvalue5678",
        )

        with caplog.at_level(logging.INFO):
            learn_node(agent, state)

        state_logs = [r for r in caplog.records if "RVTRACK:STATE" in r.message]
        assert len(state_logs) == 1
        log_msg = state_logs[0].message
        assert "changed=False" in log_msg
        # from_activity should NOT appear when unchanged
        assert "from_activity" not in log_msg
