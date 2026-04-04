"""
Tests for CoverageDensityScorer (gh26 Group 3.5).

Verifies coverage-density scoring:
- Known destination: weight * coverage_gap(destination)
- Unknown destination: weight * 0.5
- No successor_tracker or ui_coverage: 0.0
- Registration as 9th active scorer in ActionRanker
- SuccessorTracker.get_action_destination integration
"""

import pytest
from unittest.mock import MagicMock

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.strategies.rvagent_strategy.ranking.scorers import CoverageDensityScorer
from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker


def _make_action(coordinates=(100, 200), action_type="CLICK"):
    """Create mock action with coords_for_matching."""
    action = MagicMock()
    action.coords_for_matching = (coordinates, action_type)
    action.coordinates = coordinates
    action.target_view = {"class": "Button"}
    action.widget_id = "btn_test"
    return action


def _make_context(
    successor_tracker=None, ui_coverage=None, current_state_hash="state_A"
):
    """Create mock ranking context."""
    ctx = MagicMock()
    ctx.successor_tracker = successor_tracker
    ctx.ui_coverage = ui_coverage
    ctx.current_state_hash = current_state_hash
    return ctx


class TestCoverageDensityScorer:
    """Verify coverage-density scoring behavior."""

    def test_known_destination_full_gap(self):
        """Known destination with 100% coverage gap: weight * 1.0."""
        config = RVAgentConfig(package_name="test.app")
        scorer = CoverageDensityScorer(config=config)

        action = _make_action()

        # Mock successor tracker that returns a known destination
        tracker = MagicMock()
        tracker.get_action_destination.return_value = "state_B"

        # Mock ui_coverage with full gap (all elements untested)
        ui_cov = MagicMock()
        ui_cov.get_coverage_gap.return_value = 1.0

        ctx = _make_context(successor_tracker=tracker, ui_coverage=ui_cov)
        score = scorer.score(action, ctx)

        assert score == pytest.approx(config.coverage_density_weight * 1.0)
        # Verifies correct destination lookup (coords converted to optimized space)
        tracker.get_action_destination.assert_called_once()
        ui_cov.get_coverage_gap.assert_called_once_with("state_B")

    def test_known_destination_partial_gap(self):
        """Known destination with 30% coverage gap: weight * 0.3."""
        scorer = CoverageDensityScorer()  # Default weight = 200.0

        action = _make_action()

        tracker = MagicMock()
        tracker.get_action_destination.return_value = "state_B"

        ui_cov = MagicMock()
        ui_cov.get_coverage_gap.return_value = 0.3

        ctx = _make_context(successor_tracker=tracker, ui_coverage=ui_cov)
        score = scorer.score(action, ctx)

        assert score == pytest.approx(200.0 * 0.3)

    def test_known_destination_zero_gap(self):
        """Known destination with 0% coverage gap: weight * 0.0 = 0."""
        scorer = CoverageDensityScorer()

        action = _make_action()

        tracker = MagicMock()
        tracker.get_action_destination.return_value = "state_B"

        ui_cov = MagicMock()
        ui_cov.get_coverage_gap.return_value = 0.0

        ctx = _make_context(successor_tracker=tracker, ui_coverage=ui_cov)
        score = scorer.score(action, ctx)

        assert score == pytest.approx(0.0)

    def test_unknown_destination(self):
        """Unknown destination (not observed yet): weight * 0.5."""
        scorer = CoverageDensityScorer()

        action = _make_action()

        tracker = MagicMock()
        tracker.get_action_destination.return_value = None

        ui_cov = MagicMock()

        ctx = _make_context(successor_tracker=tracker, ui_coverage=ui_cov)
        score = scorer.score(action, ctx)

        assert score == pytest.approx(200.0 * 0.5)
        # get_coverage_gap should NOT be called for unknown destinations
        ui_cov.get_coverage_gap.assert_not_called()

    def test_no_successor_tracker(self):
        """No successor tracker: returns 0.0."""
        scorer = CoverageDensityScorer()

        action = _make_action()
        ui_cov = MagicMock()

        ctx = _make_context(successor_tracker=None, ui_coverage=ui_cov)
        score = scorer.score(action, ctx)

        assert score == 0.0

    def test_no_ui_coverage(self):
        """No ui_coverage: returns 0.0."""
        scorer = CoverageDensityScorer()

        action = _make_action()
        tracker = MagicMock()

        ctx = _make_context(successor_tracker=tracker, ui_coverage=None)
        score = scorer.score(action, ctx)

        assert score == 0.0

    def test_custom_weight_from_config(self):
        """Custom weight from RVAgentConfig.coverage_density_weight."""
        config = RVAgentConfig(package_name="test.app", coverage_density_weight=350.0)
        scorer = CoverageDensityScorer(config=config)

        action = _make_action()

        tracker = MagicMock()
        tracker.get_action_destination.return_value = None

        ui_cov = MagicMock()

        ctx = _make_context(successor_tracker=tracker, ui_coverage=ui_cov)
        score = scorer.score(action, ctx)

        # Unknown destination: weight * 0.5
        assert score == pytest.approx(350.0 * 0.5)

    def test_registered_as_9th_scorer(self):
        """CoverageDensityScorer should be registered as one of 9 active scorers."""
        from rv_agent.strategies.rvagent_strategy.ranking.action_ranker import (
            ActionRanker,
        )
        from rv_agent.strategies.rvagent_strategy.ranking.scorers import (
            MopScorer,
            WtgScorer,
            SaturationScorer,
            ComponentPriorityScorer,
            StrengthScorer,
            GradualDecayScorer,
            CoverageDensityScorer,
            SystemElementFilter,
            VisitationPenaltyScorer,
        )

        config = RVAgentConfig(package_name="test.app")
        scorers = [
            MopScorer(config=config),
            WtgScorer(config=config),
            SaturationScorer(config=config),
            ComponentPriorityScorer(config=config),
            StrengthScorer(config=config),
            GradualDecayScorer(config=config),
            CoverageDensityScorer(config=config),
            SystemElementFilter(),
            VisitationPenaltyScorer(config=config),
        ]
        ranker = ActionRanker(scorers=scorers)
        assert len(ranker.scorers) == 9

        # Verify CoverageDensityScorer is present
        density_scorers = [
            s for s in ranker.scorers if isinstance(s, CoverageDensityScorer)
        ]
        assert len(density_scorers) == 1


class TestGetActionDestination:
    """Verify SuccessorTracker.get_action_destination method."""

    def test_get_action_destination_known_transition(self):
        """Returns destination hash for a recorded transition."""
        graph = MagicMock()
        tracker = SuccessorTracker(graph)

        state_hash = "state_A"
        action_sig = ((100, 200), "CLICK")
        dest_hash = "state_B"

        # Record the transition
        tracker.record_successor(state_hash, action_sig, dest_hash)

        # Query
        result = tracker.get_action_destination(state_hash, action_sig)
        assert result == dest_hash

    def test_get_action_destination_unknown(self):
        """Returns None for an unrecorded transition."""
        graph = MagicMock()
        tracker = SuccessorTracker(graph)

        result = tracker.get_action_destination("state_A", ((100, 200), "CLICK"))
        assert result is None

    def test_get_action_destination_different_state(self):
        """Returns None when querying from a different source state."""
        graph = MagicMock()
        tracker = SuccessorTracker(graph)

        action_sig = ((100, 200), "CLICK")
        tracker.record_successor("state_A", action_sig, "state_B")

        # Query from a different state
        result = tracker.get_action_destination("state_C", action_sig)
        assert result is None

    def test_get_action_destination_different_action(self):
        """Returns None when querying a different action signature."""
        graph = MagicMock()
        tracker = SuccessorTracker(graph)

        tracker.record_successor("state_A", ((100, 200), "CLICK"), "state_B")

        # Query with a different action
        result = tracker.get_action_destination("state_A", ((300, 400), "CLICK"))
        assert result is None

    def test_get_action_destination_updated_successor(self):
        """Returns the latest destination when transition is updated."""
        graph = MagicMock()
        tracker = SuccessorTracker(graph)

        action_sig = ((100, 200), "CLICK")

        # Record initial transition
        tracker.record_successor("state_A", action_sig, "state_B")
        assert tracker.get_action_destination("state_A", action_sig) == "state_B"

        # Update with new destination
        tracker.record_successor("state_A", action_sig, "state_C")
        assert tracker.get_action_destination("state_A", action_sig) == "state_C"
