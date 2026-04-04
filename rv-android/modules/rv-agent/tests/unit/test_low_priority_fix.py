"""
Tests for low-priority fixes (gh26 Group 38).

Covers:
(a) MOP BFS depth limit — paths > 8 hops are rejected
(b) get_overall_statistics denominator — uses all registered elements
(c) form_fill reward short-circuit — base_reward=0.0 returns early
(d) restart/error_recovery counters — tracked in get_decision_counters()
(e) coverage_cache invalidation — record_successor clears from_hash cache
(f) RVTRACK aggregate counters — include new counter fields
"""

from unittest.mock import MagicMock

import pytest

from rv_agent import tracking as track
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.domain.screen_node import ScreenNode
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.strategies.rvagent_strategy.reward_propagator import (
    REWARD_VALUES,
    RewardPropagator,
)
from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker

# ---------------------------------------------------------------------------
# (a) MOP BFS depth limit
# ---------------------------------------------------------------------------


class TestMopBfsDepthLimit:
    """Verify that MOP BFS rejects paths longer than MAX_MOP_BFS_DEPTH (8) hops."""

    def _make_transition_manager_with_linear_wtg(self, chain_length):
        """Build a TransitionManager with a linear WTG chain of given length.

        Creates window nodes w0 -> w1 -> ... -> w{chain_length} connected by
        single transitions. The last node has a MOP activity.

        The mock structure mirrors TransitionManager's internal lookups:
        - _find_activity_for_window_id: iterates static_data.windows.windows
        - _count_mop_methods_for_activity: iterates static_data.classes.methods
        - _resolve_wtg_action: resolves step 1 against possible_actions
        """
        from rv_agent.services.transition_manager import TransitionManager

        graph = DynamicStateGraph()

        # Build mock static_data
        static_data = MagicMock()

        # Build window objects for _find_activity_for_window_id
        mock_windows = []
        for i in range(chain_length + 1):
            w = MagicMock()
            w.id = f"w{i}"
            w.activity = f"com.example.Activity_{i}"
            w.name = f"Activity_{i}"
            mock_windows.append(w)
        static_data.windows.windows = mock_windows

        # Build classes.methods for _count_mop_methods_for_activity
        mop_activity_name = f"com.example.Activity_{chain_length}"
        static_data.classes.methods = {
            f"{mop_activity_name}.doSomething()V": MagicMock(
                class_name=mop_activity_name,
                reaches_mop=True,
                directly_reaches_mop=False,
            ),
            f"{mop_activity_name}.doMore()V": MagicMock(
                class_name=mop_activity_name,
                reaches_mop=True,
                directly_reaches_mop=False,
            ),
        }

        # Build WTG mock
        wtg = MagicMock()
        static_data.wtg = wtg
        wtg.get_windows.return_value = mock_windows

        # Transitions: w_i -> w_{i+1} (linear chain)
        def get_transitions(window_id):
            idx = int(window_id[1:])
            if idx < chain_length:
                return [{"target": f"w{idx + 1}", "widget_id": f"btn_{idx}"}]
            return []

        wtg.get_window_transitions = get_transitions

        tm = TransitionManager(static_data, graph)

        # Pre-populate the activity -> window_id cache
        for i in range(chain_length + 1):
            tm._activity_to_window_id[f"com.example.Activity_{i}"] = f"w{i}"

        # Mock _resolve_wtg_action so step 1 resolution succeeds when BFS
        # finds a candidate. Returns a mock with coordinates for any call.
        mock_action = MagicMock()
        mock_action.coordinates = (540, 960)
        mock_action.target_view = {}
        mock_action.id = 1
        tm._resolve_wtg_action = MagicMock(return_value=mock_action)

        return tm

    def test_path_within_depth_limit_accepted(self):
        """Path with exactly 8 hops should be accepted (not depth-limited)."""
        tm = self._make_transition_manager_with_linear_wtg(chain_length=8)

        # Provide possible_actions so resolution path is exercised
        possible_actions = [MagicMock()]

        result = tm.plan_path_to_mop_activity(
            current_activity="com.example.Activity_0",
            mop_data=None,
            possible_actions=possible_actions,
        )

        # 8 hops = exactly at limit, should find a path
        assert result is not None

    def test_path_exceeding_depth_limit_rejected(self):
        """Path with > 8 hops should be rejected by depth limit."""
        track._counters["mop_bfs_depth_limited"] = 0

        tm = self._make_transition_manager_with_linear_wtg(chain_length=10)

        possible_actions = [MagicMock()]

        result = tm.plan_path_to_mop_activity(
            current_activity="com.example.Activity_0",
            mop_data=None,
            possible_actions=possible_actions,
        )

        # MOP is only at Activity_10 (10 hops), beyond the 8-hop limit
        assert result is None

        # Depth limit counter should have been incremented
        assert track._counters["mop_bfs_depth_limited"] > 0

    def test_short_path_not_depth_limited(self):
        """Path with 3 hops is well within depth limit."""
        track._counters["mop_bfs_depth_limited"] = 0

        tm = self._make_transition_manager_with_linear_wtg(chain_length=3)

        possible_actions = [MagicMock()]

        result = tm.plan_path_to_mop_activity(
            current_activity="com.example.Activity_0",
            mop_data=None,
            possible_actions=possible_actions,
        )

        assert result is not None
        assert track._counters["mop_bfs_depth_limited"] == 0


# ---------------------------------------------------------------------------
# (b) get_overall_statistics denominator
# ---------------------------------------------------------------------------


class TestGetOverallStatisticsDenominator:
    """Verify get_overall_statistics uses all registered elements as denominator."""

    def test_total_unique_elements_equals_all_registered(self):
        """total_unique_elements should equal len(element_types), not len(tested_elements).

        Scenario: register 10 elements, test 3 -> total_unique_elements = 10.
        """
        tracker = UICoverageTracker()

        # Register 10 elements via element_types
        for i in range(10):
            element_id = f"coords:{100 + i * 50},{200}"
            tracker.element_types[element_id] = "Button"

        # Only test 3 of them
        for i in range(3):
            element_id = f"coords:{100 + i * 50},{200}"
            tracker.tested_elements[element_id] = 1

        stats = tracker.get_overall_statistics()

        # Denominator must be ALL registered (10), not just tested (3)
        assert stats["total_unique_elements"] == 10
        assert stats["total_interactions"] == 3

    def test_total_unique_elements_zero_when_nothing_registered(self):
        """When no elements are registered, total_unique_elements is 0."""
        tracker = UICoverageTracker()
        stats = tracker.get_overall_statistics()
        assert stats["total_unique_elements"] == 0

    def test_total_unique_elements_with_all_tested(self):
        """When all elements are tested, total_unique_elements still equals element_types."""
        tracker = UICoverageTracker()

        for i in range(5):
            element_id = f"coords:{i * 100},{300}"
            tracker.element_types[element_id] = "EditText"
            tracker.tested_elements[element_id] = 2

        stats = tracker.get_overall_statistics()
        assert stats["total_unique_elements"] == 5
        assert stats["total_interactions"] == 10  # 5 elements * 2 each

    def test_average_interactions_uses_registered_denominator(self):
        """average_interactions_per_element uses total_unique_elements as denominator."""
        tracker = UICoverageTracker()

        # Register 10 elements
        for i in range(10):
            eid = f"coords:{i},{0}"
            tracker.element_types[eid] = "Button"

        # Test 2 elements with 5 interactions each
        tracker.tested_elements["coords:0,0"] = 5
        tracker.tested_elements["coords:1,0"] = 5

        stats = tracker.get_overall_statistics()
        # average = 10 interactions / 10 registered elements = 1.0
        assert stats["average_interactions_per_element"] == 1.0


# ---------------------------------------------------------------------------
# (c) form_fill reward short-circuit
# ---------------------------------------------------------------------------


class TestFormFillRewardShortCircuit:
    """Verify that form_fill reward with base_reward=0 is short-circuited."""

    def _make_graph_with_state(self):
        """Create a DynamicStateGraph with one state and recorded action."""
        graph = DynamicStateGraph()
        node = ScreenNode(
            screen_hash="state_a",
            activity="TestActivity",
            total_actions=5,
        )
        graph.states["state_a"] = node
        return graph, node

    def test_form_fill_does_not_propagate(self):
        """form_fill has base_reward=0.0, so propagate() returns early."""
        graph, node = self._make_graph_with_state()
        propagator = RewardPropagator()

        # Record an action in history
        action_sig = ((540, 960), "click")
        propagator.record_action("state_a", action_sig)

        # Propagate form_fill reward
        propagator.propagate("form_fill", graph, iteration=1)

        # No reward should have been written (short-circuited)
        assert action_sig not in node.action_cumulative_reward

    def test_new_state_does_propagate(self):
        """new_state has base_reward=1.0, so propagate() writes to graph."""
        graph, node = self._make_graph_with_state()
        propagator = RewardPropagator()

        action_sig = ((540, 960), "click")
        propagator.record_action("state_a", action_sig)

        propagator.propagate("new_state", graph, iteration=1)

        # Reward should have been written
        assert action_sig in node.action_cumulative_reward
        assert node.action_cumulative_reward[action_sig] == pytest.approx(1.0)

    def test_same_state_negative_propagation(self):
        """same_state has base_reward=-0.1, so it propagates negative reward."""
        graph, node = self._make_graph_with_state()
        propagator = RewardPropagator()

        action_sig = ((100, 200), "click")
        propagator.record_action("state_a", action_sig)

        propagator.propagate("same_state", graph, iteration=1)

        assert action_sig in node.action_cumulative_reward
        assert node.action_cumulative_reward[action_sig] == pytest.approx(-0.1)

    def test_form_fill_reward_value_is_zero(self):
        """Confirm that REWARD_VALUES['form_fill'] == 0.0."""
        assert REWARD_VALUES["form_fill"] == 0.0

    def test_mop_reached_propagates_large_reward(self):
        """mop_reached should propagate with REWARD_MOP_WEIGHT (5.0)."""
        graph, node = self._make_graph_with_state()
        propagator = RewardPropagator()

        action_sig = ((300, 400), "click")
        propagator.record_action("state_a", action_sig)

        propagator.propagate("mop_reached", graph, iteration=1)

        assert action_sig in node.action_cumulative_reward
        assert node.action_cumulative_reward[action_sig] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# (d) restart/error_recovery counters
# ---------------------------------------------------------------------------


class TestRestartErrorRecoveryCounters:
    """Verify that restart_count and error_recovery_count appear in get_decision_counters."""

    def _make_routing_manager(self):
        """Create a RoutingManager with mocked dependencies."""
        from rv_agent.config.agent_config import RVAgentConfig
        from rv_agent.routing.fallback_manager import FallbackManager
        from rv_agent.routing.routing_manager import RoutingManager

        config = RVAgentConfig(
            package_name="test.app",
            agent_mode="pure_algorithm",
        )
        fallback_manager = MagicMock(spec=FallbackManager)

        return RoutingManager(config, fallback_manager)

    def test_restart_count_in_decision_counters(self):
        """get_decision_counters() includes restart_count from tracking module."""
        # Reset counters
        track._counters["restart_count"] = 0
        track._counters["error_recovery_count"] = 0

        rm = self._make_routing_manager()

        # Simulate restarts
        track._counters["restart_count"] = 3

        counters = rm.get_decision_counters()
        assert "restart_count" in counters
        assert counters["restart_count"] == 3

    def test_error_recovery_count_in_decision_counters(self):
        """get_decision_counters() includes error_recovery_count from tracking module."""
        track._counters["restart_count"] = 0
        track._counters["error_recovery_count"] = 0

        rm = self._make_routing_manager()

        track._counters["error_recovery_count"] = 7

        counters = rm.get_decision_counters()
        assert "error_recovery_count" in counters
        assert counters["error_recovery_count"] == 7

    def test_both_counters_default_to_zero(self):
        """Both counters are 0 when no restarts or error recoveries occurred."""
        track._counters["restart_count"] = 0
        track._counters["error_recovery_count"] = 0

        rm = self._make_routing_manager()
        counters = rm.get_decision_counters()

        assert counters["restart_count"] == 0
        assert counters["error_recovery_count"] == 0

    def test_counters_increment_independently(self):
        """restart_count and error_recovery_count track independently."""
        track._counters["restart_count"] = 5
        track._counters["error_recovery_count"] = 2

        rm = self._make_routing_manager()
        counters = rm.get_decision_counters()

        assert counters["restart_count"] == 5
        assert counters["error_recovery_count"] == 2


# ---------------------------------------------------------------------------
# (e) coverage_cache invalidation
# ---------------------------------------------------------------------------


class TestCoverageCacheInvalidation:
    """Verify coverage_cache is invalidated when record_successor is called."""

    def _make_successor_tracker(self):
        """Create a SuccessorTracker with a DynamicStateGraph containing states."""
        graph = DynamicStateGraph()

        # Create states directly
        node_a = ScreenNode(screen_hash="hash_a", activity="ActivityA", total_actions=5)
        node_b = ScreenNode(screen_hash="hash_b", activity="ActivityB", total_actions=3)
        graph.states["hash_a"] = node_a
        graph.states["hash_b"] = node_b

        return SuccessorTracker(graph)

    def test_record_successor_clears_from_hash_cache(self):
        """Calling record_successor(from_hash, ...) clears coverage_cache[from_hash]."""
        st = self._make_successor_tracker()

        # Pre-populate cache for from_hash
        st.coverage_cache["hash_a"] = 0.5

        action_sig = ((100, 200), "click")
        st.record_successor("hash_a", action_sig, "hash_b")

        # Cache for from_hash should be cleared
        assert "hash_a" not in st.coverage_cache

    def test_record_successor_clears_to_hash_cache_if_exists(self):
        """record_successor also clears coverage_cache[to_hash] if present."""
        st = self._make_successor_tracker()

        st.coverage_cache["hash_a"] = 0.3
        st.coverage_cache["hash_b"] = 0.7

        action_sig = ((100, 200), "click")
        st.record_successor("hash_a", action_sig, "hash_b")

        assert "hash_a" not in st.coverage_cache
        assert "hash_b" not in st.coverage_cache

    def test_record_successor_does_not_crash_without_cache(self):
        """record_successor works when no cache entry exists for from_hash."""
        st = self._make_successor_tracker()

        assert "hash_a" not in st.coverage_cache

        action_sig = ((300, 400), "click")
        st.record_successor("hash_a", action_sig, "hash_b")

        # Should complete without error
        assert ("hash_a", action_sig) in st.successors
        assert st.successors[("hash_a", action_sig)] == "hash_b"

    def test_self_loop_does_not_clear_cache(self):
        """Self-loops (from_hash == to_hash) are skipped and do not invalidate cache."""
        st = self._make_successor_tracker()

        st.coverage_cache["hash_a"] = 0.5

        action_sig = ((100, 200), "click")
        st.record_successor("hash_a", action_sig, "hash_a")  # self-loop

        # Cache should NOT be cleared (self-loop is skipped entirely)
        assert "hash_a" in st.coverage_cache
        assert st.coverage_cache["hash_a"] == 0.5

    def test_cache_repopulates_after_invalidation(self):
        """After cache invalidation, get_successor_coverage repopulates it."""
        st = self._make_successor_tracker()

        # Pre-populate and then invalidate
        st.coverage_cache["hash_b"] = 0.8
        action_sig = ((100, 200), "click")
        st.record_successor("hash_a", action_sig, "hash_b")

        assert "hash_b" not in st.coverage_cache

        # Querying coverage repopulates
        coverage = st.get_successor_coverage("hash_b")
        assert "hash_b" in st.coverage_cache
        assert coverage == st.coverage_cache["hash_b"]


# ---------------------------------------------------------------------------
# (f) RVTRACK aggregate counters include new fields
# ---------------------------------------------------------------------------


class TestRvtrackAggregateCounters:
    """Verify that get_aggregate_counters includes new counter fields."""

    def test_mop_bfs_depth_limited_in_counters(self):
        """get_aggregate_counters() includes mop_bfs_depth_limited."""
        result = track.get_aggregate_counters()
        assert "mop_bfs_depth_limited" in result

    def test_restart_count_in_counters(self):
        """get_aggregate_counters() includes restart_count."""
        result = track.get_aggregate_counters()
        assert "restart_count" in result

    def test_error_recovery_count_in_counters(self):
        """get_aggregate_counters() includes error_recovery_count."""
        result = track.get_aggregate_counters()
        assert "error_recovery_count" in result

    def test_all_new_fields_present(self):
        """All three new fields are present in aggregate counters."""
        result = track.get_aggregate_counters()
        expected_keys = {
            "mop_bfs_depth_limited",
            "restart_count",
            "error_recovery_count",
        }
        assert expected_keys.issubset(set(result.keys()))

    def test_new_counters_default_to_zero_after_reset(self):
        """After reset_counters(), new fields are 0."""
        track.reset_counters()
        result = track.get_aggregate_counters()

        assert result["mop_bfs_depth_limited"] == 0
        assert result["restart_count"] == 0
        assert result["error_recovery_count"] == 0

    def test_counters_increment_and_reflect_in_aggregate(self):
        """Incrementing _counters is reflected in get_aggregate_counters()."""
        track.reset_counters()

        track._counters["mop_bfs_depth_limited"] = 4
        track._counters["restart_count"] = 2
        track._counters["error_recovery_count"] = 6

        result = track.get_aggregate_counters()

        assert result["mop_bfs_depth_limited"] == 4
        assert result["restart_count"] == 2
        assert result["error_recovery_count"] == 6

    def test_aggregate_counters_include_path_buffer_hit_rate(self):
        """get_aggregate_counters() computes path_buffer_hit_rate_pct."""
        track.reset_counters()
        track._counters["path_buffer_planned"] = 10
        track._counters["path_buffer_completed"] = 7

        result = track.get_aggregate_counters()

        assert "path_buffer_hit_rate_pct" in result
        assert result["path_buffer_hit_rate_pct"] == 70
