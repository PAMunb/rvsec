"""
Tests for StrengthScorer reward integration (gh26 Group 4).

Verifies FR27 Reward-Enhanced Strength Scoring.
"""

import pytest
from unittest.mock import MagicMock

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.domain.screen_node import ScreenNode
from rv_agent.strategies.rvagent_strategy.ranking.scorers import StrengthScorer


def _make_context_with_node(node, state_hash="test_hash"):
    """Create mock context with a ScreenNode in graph."""
    context = MagicMock()
    context.graph.states = {state_hash: node}
    context.current_state_hash = state_hash
    return context


def _make_action(x=100, y=200, action_type="CLICK"):
    """Create mock action with device-space coordinates."""
    action = MagicMock()
    action.coords_for_matching = ((x, y), action_type)
    return action


class TestStrengthScorerReward:
    """Verify StrengthScorer includes cumulative reward."""

    def test_strength_with_cumulative_reward(self):
        """Score = weight * strength + reward_score_weight * cumulative_reward."""
        config = RVAgentConfig(package_name="test.app")
        scorer = StrengthScorer(config=config)

        node = ScreenNode(screen_hash="test_hash", activity="TestActivity")
        action = _make_action()

        # Action signature in device space (INV-AGT-40)
        sig = action.coords_for_matching

        # Set up node with strength data
        node.action_execution_counts[sig] = 4
        node.action_success_counts[sig] = 2
        # strength = 2/4 = 0.5

        # Set cumulative reward
        node.action_cumulative_reward[sig] = 3.0

        context = _make_context_with_node(node)

        score = scorer.score(action, context)

        # weight=50, strength=0.5, reward_score_weight=1.0, cumulative_reward=3.0
        # score = 50 * 0.5 + 1.0 * 3.0 = 25.0 + 3.0 = 28.0
        expected = config.strength_weight * 0.5 + config.reward_score_weight * 3.0
        assert score == pytest.approx(expected)

    def test_strength_without_cumulative_reward(self):
        """No cumulative reward: score = weight * strength (unchanged)."""
        config = RVAgentConfig(package_name="test.app")
        scorer = StrengthScorer(config=config)

        node = ScreenNode(screen_hash="test_hash", activity="TestActivity")
        action = _make_action()
        action.coords_for_matching

        # Untested action, no cumulative reward
        context = _make_context_with_node(node)

        score = scorer.score(action, context)

        # Untested: strength = 0.5, no cumulative reward
        expected = config.strength_weight * 0.5
        assert score == pytest.approx(expected)

    def test_zero_cumulative_reward(self):
        """Zero cumulative reward: score = weight * strength."""
        config = RVAgentConfig(package_name="test.app")
        scorer = StrengthScorer(config=config)

        node = ScreenNode(screen_hash="test_hash", activity="TestActivity")
        action = _make_action()
        sig = action.coords_for_matching

        node.action_execution_counts[sig] = 2
        node.action_success_counts[sig] = 1
        node.action_cumulative_reward[sig] = 0.0

        context = _make_context_with_node(node)

        score = scorer.score(action, context)

        expected = config.strength_weight * 0.5
        assert score == pytest.approx(expected)
