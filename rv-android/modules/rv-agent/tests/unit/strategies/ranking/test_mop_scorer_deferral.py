"""
Tests for MopScorer form-context deferral (gh26 Group 3).

Verifies INV-AGT-39:
- MOP scoring deferred for CLICK when untested inputs exist
- MOP scoring NOT deferred for SET_TEXT (always prioritized)
- Full MOP score when no untested inputs
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


class TestMopScorerDeferral:
    """Verify form-context deferral behavior."""

    def test_mop_deferred_when_untested_inputs(
        self, config, context_with_untested_inputs
    ):
        """CLICK with directly_reaches_mop=True deferred when untested inputs exist."""
        scorer = MopScorer(config=config)

        action = MagicMock()
        action.directly_reaches_mop = True
        action.reaches_mop = True
        action.action_type = "click"

        score = scorer.score(action, context_with_untested_inputs)
        assert score == 0.0, "MOP click should be deferred when untested inputs exist"

    def test_mop_not_deferred_for_set_text(self, config, context_with_untested_inputs):
        """SET_TEXT with reaches_mop=True NOT deferred even with untested inputs."""
        scorer = MopScorer(config=config)

        action = MagicMock()
        action.directly_reaches_mop = False
        action.reaches_mop = True
        action.action_type = "SET_TEXT"

        score = scorer.score(action, context_with_untested_inputs)
        assert (
            score == config.mop_transitive_score
        ), "MOP SET_TEXT should NOT be deferred when untested inputs exist"

    def test_mop_full_score_when_no_untested_inputs(
        self, config, context_without_untested_inputs
    ):
        """CLICK with directly_reaches_mop=True gets full +500 when no untested inputs."""
        scorer = MopScorer(config=config)

        action = MagicMock()
        action.directly_reaches_mop = True
        action.reaches_mop = True
        action.action_type = "click"

        score = scorer.score(action, context_without_untested_inputs)
        assert (
            score == config.mop_direct_score
        ), f"MOP click should get full score ({config.mop_direct_score}) when no untested inputs"
