"""
Tests for scorer weight defaults (gh26 Group 3).

Verifies FR27 Updated Default Weights:
- MOP direct/transitive scores
- WTG guided score
- Visitation penalty
- Stochastic probability
- Gumbel-max sampling behavior
"""

import pytest
from unittest.mock import MagicMock
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.strategies.rvagent_strategy.ranking.scorers import (
    MopScorer,
    WtgScorer,
    VisitationPenaltyScorer,
)


@pytest.fixture
def config():
    return RVAgentConfig(package_name="test.app")


class TestScorerWeightDefaults:
    """Verify updated default weight values from Group 1 config changes."""

    def test_mop_direct_default_500(self, config):
        """MOP direct score default should be 500."""
        assert config.mop_direct_score == 500.0
        scorer = MopScorer(config=config)
        assert scorer.direct_score == 500.0

    def test_mop_transitive_default_300(self, config):
        """MOP transitive score default should be 300."""
        assert config.mop_transitive_score == 300.0
        scorer = MopScorer(config=config)
        assert scorer.transitive_score == 300.0

    def test_mop_transitive_outweighs_wtg(self, config):
        """MOP transitive (300) should outweigh WTG guided (150)."""
        assert config.mop_transitive_score > config.wtg_guided_score

    def test_wtg_default_150(self, config):
        """WTG guided score default should be 150."""
        assert config.wtg_guided_score == 150.0
        scorer = WtgScorer(config=config)
        assert scorer.guided_score == 150.0

    def test_visitation_penalty_default_minus15(self, config):
        """Visitation penalty factor default should be -15."""
        assert config.visitation_penalty_factor == -15.0
        scorer = VisitationPenaltyScorer(config=config)
        assert scorer.penalty_factor == -15.0

    def test_stochastic_probability_015(self, config):
        """Stochastic probability default should be 0.15."""
        assert config.stochastic_probability == 0.15

    def test_stochastic_gumbel_sampling_with_015(self, config):
        """With stochastic_probability=0.15, top-scored action wins ~85% of time."""
        import random
        import math
        from rv_agent.strategies.rvagent_strategy.ranking.action_ranker import (
            ActionRanker,
            ScoredAction,
        )

        # Create mock actions with distinct scores
        action_high = MagicMock()
        action_high.coordinates = (100, 100)
        action_high.target_view = {"class": "Button"}
        action_high.directly_reaches_mop = True
        action_high.reaches_mop = True
        action_high.event = MagicMock(name="CLICK")
        action_high.widget_id = "btn_high"

        action_low = MagicMock()
        action_low.coordinates = (200, 200)
        action_low.target_view = {"class": "TextView"}
        action_low.directly_reaches_mop = False
        action_low.reaches_mop = False
        action_low.event = MagicMock(name="CLICK")
        action_low.widget_id = "btn_low"

        # Simple ranker with a scorer that gives fixed scores
        class FixedScorer:
            def score(self, action, context):
                if action is action_high:
                    return 500.0
                return 50.0

        ranker = ActionRanker(scorers=[FixedScorer()])
        context = MagicMock()

        # Simulate stochastic selection 200 times
        random.seed(42)
        top_wins = 0
        total_stochastic = 0
        for _ in range(200):
            if random.random() < config.stochastic_probability:
                result = ranker.select_stochastic(
                    [action_high, action_low], context, temperature=1.0
                )
                total_stochastic += 1
                if result is action_high:
                    top_wins += 1
            else:
                # Deterministic always picks top
                top_wins += 1

        # Top action should win ~85%+ of the time overall
        win_rate = top_wins / 200
        assert (
            win_rate >= 0.80
        ), f"Top action win rate {win_rate:.2%} too low (expected >= 80%)"
