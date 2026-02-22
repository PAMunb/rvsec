"""
Tests for GradualDecayScorer ID fix (gh26 Group 34).

GradualDecayScorer previously resolved element IDs via widget_id, which could
differ from the coordinate-based IDs recorded by execute_node via
find_nearest_element(). The fix makes GradualDecayScorer always use
make_element_id_from_action() (coordinate-based), so scorer lookups and
execution recordings use the same key.

Verifies:
  (a) An action whose coordinates have been tested multiple times receives a
      decayed score (< DEFAULT_BASE_SCORE).
  (b) An action whose coordinates have never been tested receives the full
      DEFAULT_BASE_SCORE (200.0).
  (c) track.score_detail() emits a RVTRACK:SCORE_DETAIL log line with the
      decayed value for the tested element.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple
from unittest.mock import MagicMock

import pytest

from rv_agent.memory.element_id import make_element_id
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.strategies.rvagent_strategy.ranking.context import RankingContext
from rv_agent.strategies.rvagent_strategy.ranking.scorers import GradualDecayScorer


# ---------------------------------------------------------------------------
# Minimal mock action — only the fields GradualDecayScorer reads
# ---------------------------------------------------------------------------


@dataclass
class _MockAction:
    """Minimal stand-in for rv_screen_parser ItemAction."""

    coordinates: Optional[Tuple[int, int]]
    widget_id: Optional[str] = None
    target_view: dict = field(default_factory=dict)

    @property
    def coords_for_matching(self):
        return (self.coordinates, "click") if self.coordinates else ((0, 0), "click")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_context(ui_coverage: UICoverageTracker) -> RankingContext:
    """Build a minimal RankingContext with the given coverage tracker."""
    context = MagicMock(spec=RankingContext)
    context.ui_coverage = ui_coverage
    context.iteration = 1
    return context


def _record_interactions(
    tracker: UICoverageTracker, element_id: str, count: int
) -> None:
    """Record `count` interactions for `element_id`."""
    for _ in range(count):
        tracker.record_interaction(element_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGradualDecayScorerIdFix:
    """GradualDecayScorer uses coordinate-based IDs matching execute_node."""

    def test_tested_action_returns_decayed_score(self):
        """Action interacted with 3 times gets score < DEFAULT_BASE_SCORE.

        With the old widget_id lookup, the scorer would not find the element
        (recorded under a coordinate key) and would return 200.0 every time.
        The fix ensures the same coordinate key is used for both recording and
        scoring, so exponential decay is applied correctly.
        """
        tracker = UICoverageTracker()
        element_id = make_element_id(100, 200)
        _record_interactions(tracker, element_id, 3)

        scorer = GradualDecayScorer()
        action = _MockAction(coordinates=(100, 200))
        context = _make_context(tracker)

        score = scorer.score(action, context)

        expected = GradualDecayScorer.DEFAULT_BASE_SCORE * (
            GradualDecayScorer.DEFAULT_DECAY_RATE ** 3
        )
        assert score == pytest.approx(expected)
        assert score < GradualDecayScorer.DEFAULT_BASE_SCORE

    def test_untested_action_returns_base_score(self):
        """Action never interacted with returns the full base score (200.0)."""
        tracker = UICoverageTracker()

        scorer = GradualDecayScorer()
        action = _MockAction(coordinates=(300, 400))
        context = _make_context(tracker)

        score = scorer.score(action, context)

        assert score == pytest.approx(GradualDecayScorer.DEFAULT_BASE_SCORE)

    def test_score_detail_log_emitted_with_decayed_value(self, caplog):
        """track.score_detail() emits RVTRACK:SCORE_DETAIL with the actual score.

        The log line must contain:
          - '[RVTRACK:SCORE_DETAIL]'
          - 'scorer=GradualDecay'
          - The decayed score value (not 200)
        """
        tracker = UICoverageTracker()
        element_id = make_element_id(500, 600)
        _record_interactions(tracker, element_id, 2)

        scorer = GradualDecayScorer()
        action = _MockAction(coordinates=(500, 600))
        context = _make_context(tracker)

        # Capture INFO-level logs from the tracking module
        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            score = scorer.score(action, context)

        # Verify a SCORE_DETAIL line was emitted
        score_detail_lines = [
            rec.message
            for rec in caplog.records
            if "RVTRACK:SCORE_DETAIL" in rec.message
        ]
        assert score_detail_lines, "Expected at least one RVTRACK:SCORE_DETAIL log line"

        detail_line = score_detail_lines[0]
        assert "scorer=GradualDecay" in detail_line

        # The logged score must match the decayed value, not 200
        expected = GradualDecayScorer.DEFAULT_BASE_SCORE * (
            GradualDecayScorer.DEFAULT_DECAY_RATE ** 2
        )
        expected_str = f"{expected:.0f}"
        assert expected_str in detail_line, (
            f"Expected decayed score '{expected_str}' in log line: {detail_line}"
        )
        assert "200" not in detail_line.split("score=")[1].split(" ")[0], (
            "Log must not show base score 200 for a tested element"
        )
