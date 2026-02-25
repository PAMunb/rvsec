"""
Tests for MopScorer scoring behavior.

The original deferral logic (INV-AGT-39) checked action.action_type, which
doesn't exist on ItemAction — it was dead code. The deferral block was removed.
MopScorer now always scores based on MOP reachability flags.
"""

import pytest
from unittest.mock import MagicMock

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.strategies.rvagent_strategy.ranking.scorers import MopScorer


@pytest.fixture
def config():
    return RVAgentConfig(package_name="test.app")


@pytest.fixture
def context_with_untested_inputs():
    ctx = MagicMock()
    ctx.has_untested_inputs = True
    return ctx


@pytest.fixture
def context_without_untested_inputs():
    ctx = MagicMock()
    ctx.has_untested_inputs = False
    return ctx


class TestMopScorerScoring:
    """Verify MopScorer scores based on MOP reachability."""

    def test_direct_mop_gets_full_score(
        self, config, context_with_untested_inputs
    ):
        """directly_reaches_mop=True gets direct score regardless of untested inputs."""
        scorer = MopScorer(config=config)

        action = MagicMock()
        action.directly_reaches_mop = True
        action.reaches_mop = True

        score = scorer.score(action, context_with_untested_inputs)
        assert score == config.mop_direct_score

    def test_transitive_mop_gets_transitive_score(self, config, context_with_untested_inputs):
        """reaches_mop=True (not direct) gets transitive score."""
        scorer = MopScorer(config=config)

        action = MagicMock()
        action.directly_reaches_mop = False
        action.reaches_mop = True

        score = scorer.score(action, context_with_untested_inputs)
        assert score == config.mop_transitive_score

    def test_full_score_when_no_untested_inputs(
        self, config, context_without_untested_inputs
    ):
        """directly_reaches_mop=True gets full score when no untested inputs."""
        scorer = MopScorer(config=config)

        action = MagicMock()
        action.directly_reaches_mop = True
        action.reaches_mop = True

        score = scorer.score(action, context_without_untested_inputs)
        assert (
            score == config.mop_direct_score
        ), f"MOP action should get full score ({config.mop_direct_score})"
