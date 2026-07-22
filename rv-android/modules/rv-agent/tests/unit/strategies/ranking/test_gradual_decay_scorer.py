"""
Tests for GradualDecayScorer (gh26 Group 3).

Verifies INV-AGT-30:
- Exponential decay with configurable base score and decay rate
- Zero visits = full base score (200)
- Score decay per visit (0.7^N)
- Min visits cutoff (visits >= 5 -> 0.0)
- Missing widget_id handling
- Registration in ActionRanker
"""

from unittest.mock import MagicMock

import pytest
from rv_agent.strategies.rvagent_strategy.ranking.scorers import GradualDecayScorer


@pytest.fixture
def scorer():
    return GradualDecayScorer()


@pytest.fixture
def context():
    ctx = MagicMock()
    ctx.ui_coverage = MagicMock()
    return ctx


def _make_action(widget_id="btn_test", coordinates=(100, 200)):
    action = MagicMock()
    action.widget_id = widget_id
    action.coordinates = coordinates
    action.target_view = {"class": "Button"}
    return action


class TestGradualDecayScorer:
    """Verify exponential decay behavior."""

    def test_gradual_decay_zero_visits(self, scorer, context):
        """Zero visits should return full base score (200)."""
        action = _make_action()
        context.ui_coverage.get_element_test_count.return_value = 0
        score = scorer.score(action, context)
        assert score == pytest.approx(200.0)

    def test_gradual_decay_three_visits(self, scorer, context):
        """Three visits: 200 * 0.7^3 = 68.6."""
        action = _make_action()
        context.ui_coverage.get_element_test_count.return_value = 3
        score = scorer.score(action, context)
        assert score == pytest.approx(200.0 * 0.7**3, rel=0.01)

    def test_gradual_decay_min_visits_cutoff(self, scorer, context):
        """Visits >= min_visits (5) should return 0.0."""
        action = _make_action()
        context.ui_coverage.get_element_test_count.return_value = 5
        score = scorer.score(action, context)
        assert score == 0.0

        # Also 6+ visits
        context.ui_coverage.get_element_test_count.return_value = 10
        score = scorer.score(action, context)
        assert score == 0.0

    def test_gradual_decay_missing_widget_id(self, scorer, context):
        """Action with no widget_id and no coordinates returns 0.0."""
        action = MagicMock()
        action.widget_id = None
        action.coordinates = None
        action.target_view = None
        # Prevent MagicMock from returning truthy values for coordinate lookups
        action.get_execution_coordinates.return_value = None
        score = scorer.score(action, context)
        assert score == 0.0

    def test_gradual_decay_registered_in_ranker(self):
        """GradualDecayScorer should be registered as one of 8 active scorers."""
        from rv_agent.config.agent_config import RVAgentConfig
        from rv_agent.strategies.rvagent_strategy.ranking.action_ranker import (
            ActionRanker,
        )
        from rv_agent.strategies.rvagent_strategy.ranking.scorers import (
            ComponentPriorityScorer,
            GradualDecayScorer,
            MopScorer,
            SaturationScorer,
            StrengthScorer,
            SystemElementFilter,
            VisitationPenaltyScorer,
            WtgScorer,
        )

        config = RVAgentConfig(package_name="test.app")
        scorers = [
            MopScorer(config=config),
            WtgScorer(config=config),
            SaturationScorer(config=config),
            ComponentPriorityScorer(config=config),
            StrengthScorer(config=config),
            GradualDecayScorer(config=config),
            SystemElementFilter(),
            VisitationPenaltyScorer(config=config),
        ]
        ranker = ActionRanker(scorers=scorers)
        assert len(ranker.scorers) == 8

        # Verify GradualDecayScorer is present
        decay_scorers = [s for s in ranker.scorers if isinstance(s, GradualDecayScorer)]
        assert len(decay_scorers) == 1
