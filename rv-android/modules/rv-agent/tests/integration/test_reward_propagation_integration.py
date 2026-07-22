"""
Integration tests for reward propagation (gh26 Group 9, task 9.2).

Validates 5-iteration propagation sequences with real RewardPropagator and
ScreenNode instances. Tests cross-group interactions between reward propagation
(Group 4) and DynamicStateGraph node state (Groups 1-2).
"""

from unittest.mock import MagicMock

import pytest
from rv_agent.domain.screen_node import ScreenNode
from rv_agent.strategies.rvagent_strategy.reward_propagator import (
    MAX_CUMULATIVE_REWARD_FACTOR,
    REWARD_MOP_WEIGHT,
    REWARD_VALUES,
    RewardPropagator,
)


def _make_graph_with_nodes(*hashes):
    """Create a mock graph with real ScreenNodes for given state hashes."""
    graph = MagicMock()
    nodes = {}
    for h in hashes:
        nodes[h] = ScreenNode(screen_hash=h, activity="TestActivity")
    graph.states = nodes
    return graph


def _make_propagator(gamma=0.8):
    """Create RewardPropagator with given gamma discount factor."""
    config = MagicMock()
    config.reward_gamma = gamma
    return RewardPropagator(config=config)


class TestMopRewardPropagatesBackwards:
    """Verify 5-step backward propagation with gamma discounting."""

    def test_mop_reward_propagates_backwards_5_steps(self):
        """
        Record 5 actions, propagate MOP reward, verify cumulative_reward values
        in ScreenNode decay with gamma=0.8.

        Most recent action: 5.0 * 0.8^0 = 5.0
        4th action:         5.0 * 0.8^1 = 4.0
        3rd action:         5.0 * 0.8^2 = 3.2
        2nd action:         5.0 * 0.8^3 = 2.56
        1st action:         5.0 * 0.8^4 = 2.048
        """
        prop = _make_propagator(gamma=0.8)
        hashes = [f"state_{i}" for i in range(5)]
        graph = _make_graph_with_nodes(*hashes)

        sigs = [((i * 50, i * 50), "CLICK") for i in range(5)]
        for i, (h, sig) in enumerate(zip(hashes, sigs)):
            prop.record_action(h, sig)

        prop.propagate("mop_reached", graph)

        # Most recent (index 4): gamma^0
        assert graph.states["state_4"].action_cumulative_reward[
            sigs[4]
        ] == pytest.approx(5.0)
        # Index 3: gamma^1
        assert graph.states["state_3"].action_cumulative_reward[
            sigs[3]
        ] == pytest.approx(4.0)
        # Index 2: gamma^2
        assert graph.states["state_2"].action_cumulative_reward[
            sigs[2]
        ] == pytest.approx(3.2)
        # Index 1: gamma^3
        assert graph.states["state_1"].action_cumulative_reward[
            sigs[1]
        ] == pytest.approx(2.56)
        # Index 0: gamma^4
        assert graph.states["state_0"].action_cumulative_reward[
            sigs[0]
        ] == pytest.approx(2.048)

    def test_propagation_window_limited_to_n(self):
        """
        Record N+2 actions; only N most recent receive reward (sliding window = deque(maxlen=N)).

        REWARD_PROPAGATION_N = 5, so recording 7 actions means only the last 5 get reward.
        """
        prop = _make_propagator(gamma=0.8)
        # Create 7 states, but only last 5 should receive reward
        hashes = [f"s{i}" for i in range(7)]
        graph = _make_graph_with_nodes(*hashes)

        sigs = [((i * 30, 100), "CLICK") for i in range(7)]
        for h, sig in zip(hashes, sigs):
            prop.record_action(h, sig)

        prop.propagate("mop_reached", graph)

        # States 0 and 1 are outside the N=5 window -> no reward
        assert graph.states["s0"].action_cumulative_reward.get(
            sigs[0], 0.0
        ) == pytest.approx(0.0)
        assert graph.states["s1"].action_cumulative_reward.get(
            sigs[1], 0.0
        ) == pytest.approx(0.0)

        # State 6 (most recent): reward = 5.0 * 0.8^0
        assert graph.states["s6"].action_cumulative_reward[sigs[6]] == pytest.approx(
            5.0
        )


class TestCumulativeRewardAccumulation:
    """Verify multiple propagation passes accumulate rewards correctly."""

    def test_cumulative_reward_survives_multiple_propagations(self):
        """
        Two MOP propagations to the same action accumulate: 5.0 + 5.0 = 10.0.

        Each propagation adds its discounted reward to the existing cumulative value.
        """
        prop = _make_propagator(gamma=0.8)
        graph = _make_graph_with_nodes("state_A")
        sig = ((100, 200), "CLICK")

        # First propagation
        prop.record_action("state_A", sig)
        prop.propagate("mop_reached", graph)
        first = graph.states["state_A"].action_cumulative_reward[sig]
        assert first == pytest.approx(5.0)

        # Second propagation (new record -> new propagation)
        prop.record_action("state_A", sig)
        prop.propagate("mop_reached", graph)
        second = graph.states["state_A"].action_cumulative_reward[sig]
        # First propagation: 5.0; second adds at least 5.0 * 0.8^1 = 4.0 (from position 1)
        # Both records are in history for second propagation
        assert second > first  # Cumulative increases

    def test_same_state_penalty_accumulates(self):
        """Multiple same_state penalties accumulate negatively."""
        prop = _make_propagator(gamma=0.8)
        graph = _make_graph_with_nodes("state_X")
        sig = ((50, 50), "CLICK")

        # Apply 3 penalties
        for _ in range(3):
            prop.record_action("state_X", sig)
            prop.propagate("same_state", graph)

        final = graph.states["state_X"].action_cumulative_reward.get(sig, 0.0)
        # Each propagation adds -0.1 contribution -> final should be negative
        assert final < 0.0


class TestNegativeRewardCap:
    """Verify cumulative reward is bounded at symmetric caps."""

    def test_negative_reward_caps_at_lower_bound(self):
        """
        Many same_state penalties must not exceed the lower cap.

        Cap = -MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT = -15.0
        """
        prop = _make_propagator(gamma=0.8)
        graph = _make_graph_with_nodes("state_Z")
        sig = ((200, 300), "CLICK")

        # Pre-set reward just below the floor
        graph.states["state_Z"].action_cumulative_reward[sig] = -14.95

        # One more penalty
        prop.record_action("state_Z", sig)
        prop.propagate("same_state", graph)

        expected_floor = -(MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT)
        actual = graph.states["state_Z"].action_cumulative_reward[sig]
        # Must not go below the floor (-15.0)
        assert actual >= expected_floor - 1e-9

    def test_positive_reward_caps_at_upper_bound(self):
        """
        Reward addition beyond cap is clamped at upper bound = 15.0.
        """
        prop = _make_propagator(gamma=0.8)
        graph = _make_graph_with_nodes("state_W")
        sig = ((10, 20), "CLICK")

        # Pre-set near cap
        expected_cap = MAX_CUMULATIVE_REWARD_FACTOR * REWARD_MOP_WEIGHT
        graph.states["state_W"].action_cumulative_reward[sig] = expected_cap - 0.1

        # MOP reward pushes past cap
        prop.record_action("state_W", sig)
        prop.propagate("mop_reached", graph)

        actual = graph.states["state_W"].action_cumulative_reward[sig]
        # Must not exceed the cap (15.0)
        assert actual <= expected_cap + 1e-9

    def test_reward_values_ordering(self):
        """
        REWARD_VALUES priority order: mop_reached > new_activity > new_state > form_fill > same_state.

        This is a cross-group contract: scorers that read cumulative_reward depend on
        the propagator producing consistent relative magnitudes.
        """
        assert REWARD_VALUES["mop_reached"] > REWARD_VALUES["new_activity"]
        assert REWARD_VALUES["new_activity"] > REWARD_VALUES["new_state"]
        assert REWARD_VALUES["new_state"] > REWARD_VALUES["form_fill"]
        assert REWARD_VALUES["form_fill"] > REWARD_VALUES["same_state"]
