"""
Tests for RewardPropagator (gh26 Group 4).

Verifies INV-AGT-29 (N-step reward propagation), INV-AGT-35 (symmetric bounds).
"""

import pytest
from unittest.mock import MagicMock
from rv_agent.strategies.rvagent_strategy.reward_propagator import (
    RewardPropagator,
    REWARD_MOP_WEIGHT,
    REWARD_PROPAGATION_N,
    MAX_CUMULATIVE_REWARD_FACTOR,
    REWARD_VALUES,
)
from rv_agent.domain.screen_node import ScreenNode


def _make_graph_with_nodes(*hashes):
    """Create a mock graph with ScreenNodes for given hashes."""
    graph = MagicMock()
    nodes = {}
    for h in hashes:
        nodes[h] = ScreenNode(screen_hash=h, activity="TestActivity")
    graph.states = nodes
    return graph


class TestRewardPropagator:
    """Verify N-step backward propagation."""

    def test_mop_reached_propagation(self):
        """MOP reached: 5.0 * gamma^k for each action in history."""
        config = MagicMock()
        config.reward_gamma = 0.8
        prop = RewardPropagator(config=config)

        graph = _make_graph_with_nodes("s0", "s1", "s2")
        sig0 = ((10, 20), "CLICK")
        sig1 = ((30, 40), "CLICK")
        sig2 = ((50, 60), "CLICK")

        prop.record_action("s0", sig0)
        prop.record_action("s1", sig1)
        prop.record_action("s2", sig2)

        prop.propagate("mop_reached", graph)

        # Most recent (s2, sig2): 5.0 * 0.8^0 = 5.0
        assert graph.states["s2"].action_cumulative_reward[sig2] == pytest.approx(5.0)
        # s1: 5.0 * 0.8^1 = 4.0
        assert graph.states["s1"].action_cumulative_reward[sig1] == pytest.approx(4.0)
        # s0: 5.0 * 0.8^2 = 3.2
        assert graph.states["s0"].action_cumulative_reward[sig0] == pytest.approx(3.2)

    def test_new_activity_propagation(self):
        """New activity: 2.0 * gamma^k."""
        config = MagicMock()
        config.reward_gamma = 0.5
        prop = RewardPropagator(config=config)

        graph = _make_graph_with_nodes("s0", "s1")
        sig0 = ((10, 20), "CLICK")
        sig1 = ((30, 40), "CLICK")

        prop.record_action("s0", sig0)
        prop.record_action("s1", sig1)

        prop.propagate("new_activity", graph)

        assert graph.states["s1"].action_cumulative_reward[sig1] == pytest.approx(2.0)
        assert graph.states["s0"].action_cumulative_reward[sig0] == pytest.approx(1.0)

    def test_new_state_reward(self):
        """New state: 1.0 * gamma^k."""
        prop = RewardPropagator()
        graph = _make_graph_with_nodes("s0")
        sig = ((10, 20), "CLICK")
        prop.record_action("s0", sig)

        prop.propagate("new_state", graph)

        assert graph.states["s0"].action_cumulative_reward[sig] == pytest.approx(1.0)

    def test_same_state_penalty(self):
        """Same state: -0.1 penalty."""
        prop = RewardPropagator()
        graph = _make_graph_with_nodes("s0")
        sig = ((10, 20), "CLICK")
        prop.record_action("s0", sig)

        prop.propagate("same_state", graph)

        assert graph.states["s0"].action_cumulative_reward[sig] == pytest.approx(-0.1)

    def test_cumulative_accumulation(self):
        """Multiple propagations accumulate: 3.2 + 1.6 = 4.8."""
        config = MagicMock()
        config.reward_gamma = 0.8
        prop = RewardPropagator(config=config)

        graph = _make_graph_with_nodes("s0")
        sig = ((10, 20), "CLICK")

        # First propagation: MOP reached with 2 actions
        prop.record_action("s0", sig)
        prop.record_action("s0", sig)
        prop.propagate("mop_reached", graph)

        # sig appears twice in history: 5.0*0.8^0 + 5.0*0.8^1 = 5.0 + 4.0 = 9.0
        assert graph.states["s0"].action_cumulative_reward[sig] == pytest.approx(9.0)

    def test_short_history(self):
        """History shorter than N still propagates correctly."""
        config = MagicMock()
        config.reward_gamma = 0.8
        prop = RewardPropagator(config=config)

        graph = _make_graph_with_nodes("s0", "s1")
        sig0 = ((10, 20), "CLICK")
        sig1 = ((30, 40), "CLICK")

        # Only 2 actions in history (N=5)
        prop.record_action("s0", sig0)
        prop.record_action("s1", sig1)

        prop.propagate("new_state", graph)

        assert graph.states["s1"].action_cumulative_reward[sig1] == pytest.approx(1.0)
        assert graph.states["s0"].action_cumulative_reward[sig0] == pytest.approx(0.8)

    def test_missing_state_in_graph(self):
        """Missing state hash in graph is silently skipped."""
        prop = RewardPropagator()
        graph = _make_graph_with_nodes("s0")  # Only s0 exists
        sig = ((10, 20), "CLICK")

        prop.record_action("missing_state", sig)
        prop.record_action("s0", ((30, 40), "CLICK"))

        # Should not raise
        prop.propagate("new_state", graph)

        # s0 action should still get reward
        assert graph.states["s0"].action_cumulative_reward[
            ((30, 40), "CLICK")
        ] == pytest.approx(1.0)

    def test_discount_calculation(self):
        """Verify gamma^k discount is correct for N=5."""
        config = MagicMock()
        config.reward_gamma = 0.8
        prop = RewardPropagator(config=config)

        graph = _make_graph_with_nodes("s0", "s1", "s2", "s3", "s4")
        sigs = [((i * 10, i * 10), "CLICK") for i in range(5)]

        for i, sig in enumerate(sigs):
            prop.record_action(f"s{i}", sig)

        prop.propagate("mop_reached", graph)

        # Most recent (s4): 5.0 * 0.8^0 = 5.0
        assert graph.states["s4"].action_cumulative_reward[sigs[4]] == pytest.approx(
            5.0
        )
        # s3: 5.0 * 0.8^1 = 4.0
        assert graph.states["s3"].action_cumulative_reward[sigs[3]] == pytest.approx(
            4.0
        )
        # s2: 5.0 * 0.8^2 = 3.2
        assert graph.states["s2"].action_cumulative_reward[sigs[2]] == pytest.approx(
            3.2
        )
        # s1: 5.0 * 0.8^3 = 2.56
        assert graph.states["s1"].action_cumulative_reward[sigs[1]] == pytest.approx(
            2.56
        )
        # s0: 5.0 * 0.8^4 = 2.048
        assert graph.states["s0"].action_cumulative_reward[sigs[0]] == pytest.approx(
            2.048
        )

    def test_cumulative_reward_upper_cap_reached(self):
        """Cumulative reward capped at MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT = 15.0."""
        prop = RewardPropagator()
        graph = _make_graph_with_nodes("s0")
        sig = ((10, 20), "CLICK")

        # Manually set high existing reward
        graph.states["s0"].action_cumulative_reward[sig] = 14.0

        prop.record_action("s0", sig)
        prop.propagate("mop_reached", graph)

        # 14.0 + 5.0 = 19.0, but capped at 15.0
        expected_cap = MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT
        assert graph.states["s0"].action_cumulative_reward[sig] == pytest.approx(
            expected_cap
        )

    def test_cumulative_reward_lower_cap_reached(self):
        """Cumulative reward floored at -MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT = -15.0."""
        prop = RewardPropagator()
        graph = _make_graph_with_nodes("s0")
        sig = ((10, 20), "CLICK")

        # Manually set very negative existing reward
        graph.states["s0"].action_cumulative_reward[sig] = -14.95

        prop.record_action("s0", sig)
        prop.propagate("same_state", graph)

        # -14.95 + (-0.1) = -15.05, but clamped at -15.0
        expected_floor = -MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT
        assert graph.states["s0"].action_cumulative_reward[sig] == pytest.approx(
            expected_floor
        )

    def test_error_recovery_actions_in_reward_history(self):
        """Error recovery actions participate in reward propagation."""
        prop = RewardPropagator()
        graph = _make_graph_with_nodes("s0", "s1")
        sig_recovery = ((10, 20), "CLICK")  # Error recovery action
        sig_normal = ((30, 40), "CLICK")  # Normal action

        # Both actions recorded - error recovery action is just a normal record
        prop.record_action("s0", sig_recovery)
        prop.record_action("s1", sig_normal)

        prop.propagate("mop_reached", graph)

        # Both should receive reward
        assert graph.states["s1"].action_cumulative_reward[sig_normal] == pytest.approx(
            5.0
        )
        assert graph.states["s0"].action_cumulative_reward[
            sig_recovery
        ] == pytest.approx(4.0)

    def test_form_fill_neutral_reward(self):
        """Form fill (SET_TEXT on same screen) gets 0.0 reward, not -0.1 penalty."""
        prop = RewardPropagator()
        graph = _make_graph_with_nodes("s0")
        sig = ((10, 20), "SET_TEXT")

        prop.record_action("s0", sig)
        prop.propagate("form_fill", graph)

        # form_fill reward is 0.0 — no change to cumulative
        assert graph.states["s0"].action_cumulative_reward.get(
            sig, 0.0
        ) == pytest.approx(0.0)

    def test_concurrent_reward_types_highest_wins(self):
        """When multiple reward types apply, only the highest priority fires."""
        # This tests the design contract: caller sends only one reward_type
        # The priority is: mop_reached > new_activity > new_state > form_fill > same_state
        # We verify that REWARD_VALUES[mop_reached] > REWARD_VALUES[new_activity]
        assert REWARD_VALUES["mop_reached"] > REWARD_VALUES["new_activity"]
        assert REWARD_VALUES["new_activity"] > REWARD_VALUES["new_state"]
        assert REWARD_VALUES["new_state"] > REWARD_VALUES["form_fill"]
        assert REWARD_VALUES["form_fill"] > REWARD_VALUES["same_state"]


class TestRewardPropagatorConstants:
    """Verify module-level constants."""

    def test_reward_mop_weight(self):
        assert REWARD_MOP_WEIGHT == 5.0

    def test_reward_propagation_n(self):
        assert REWARD_PROPAGATION_N == 5

    def test_max_cumulative_factor(self):
        assert MAX_CUMULATIVE_REWARD_FACTOR == 3.0
