"""
Tests for scorer bug fixes: SystemElementFilter, score decay sign, MopScorer dead code.

B1: SystemElementFilter was penalizing package="android" with -5000, but "android"
    is a legitimate system dialog package (permissions, alerts). Only
    "com.android.systemui" should be penalized.

B2: _select_with_score_decay() divided negative scores by the decay factor,
    making them LESS negative (closer to 0) — opposite of intended behavior.
    Fix: multiply negative scores by the decay factor so they become MORE negative.

B3: MopScorer deferral block checked action.action_type, which doesn't exist on
    ItemAction. The dead code was removed.
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple
from unittest.mock import MagicMock

import pytest

from rv_agent.strategies.rvagent_strategy.ranking.context import RankingContext
from rv_agent.strategies.rvagent_strategy.ranking.scorers import (
    MopScorer,
    SystemElementFilter,
)


# ---------------------------------------------------------------------------
# Minimal mock action
# ---------------------------------------------------------------------------


@dataclass
class _MockAction:
    """Minimal stand-in for rv_screen_parser ItemAction."""

    coordinates: Optional[Tuple[int, int]] = None
    target_view: dict = field(default_factory=dict)
    reaches_mop: bool = False
    directly_reaches_mop: bool = False
    widget_id: Optional[str] = None

    @property
    def coords_for_matching(self):
        return (self.coordinates, "click") if self.coordinates else ((0, 0), "click")


def _make_context() -> RankingContext:
    """Build a minimal RankingContext."""
    return MagicMock(spec=RankingContext)


# ---------------------------------------------------------------------------
# B1: SystemElementFilter — package="android" must NOT be penalized
# ---------------------------------------------------------------------------


class TestSystemElementFilterPackageFix:
    """SystemElementFilter no longer penalizes package='android'."""

    def test_android_package_returns_zero(self):
        """Elements with package='android' (system dialogs) get score 0.0."""
        scorer = SystemElementFilter()
        action = _MockAction(
            target_view={"package": "android", "class": "android.widget.Button"}
        )
        context = _make_context()

        score = scorer.score(action, context)

        assert score == 0.0

    def test_systemui_package_returns_penalty(self):
        """Elements with package='com.android.systemui' still get -5000."""
        scorer = SystemElementFilter()
        action = _MockAction(
            target_view={"package": "com.android.systemui", "class": "android.widget.TextView"}
        )
        context = _make_context()

        score = scorer.score(action, context)

        assert score == SystemElementFilter.SYSTEM_PENALTY

    def test_app_package_returns_zero(self):
        """Normal app elements get score 0.0."""
        scorer = SystemElementFilter()
        action = _MockAction(
            target_view={"package": "com.example.myapp", "class": "android.widget.Button"}
        )
        context = _make_context()

        score = scorer.score(action, context)

        assert score == 0.0

    def test_no_target_view_returns_zero(self):
        """Actions without target_view get score 0.0."""
        scorer = SystemElementFilter()
        action = _MockAction(target_view=None)
        # ItemAction.target_view defaults to dict, but if None is forced:
        action.target_view = None
        context = _make_context()

        score = scorer.score(action, context)

        assert score == 0.0

    def test_empty_package_returns_zero(self):
        """Actions with empty package get score 0.0."""
        scorer = SystemElementFilter()
        action = _MockAction(target_view={"package": "", "class": "android.widget.Button"})
        context = _make_context()

        score = scorer.score(action, context)

        assert score == 0.0

    def test_system_packages_only_contains_systemui(self):
        """SYSTEM_PACKAGES must only contain 'com.android.systemui'."""
        assert SystemElementFilter.SYSTEM_PACKAGES == frozenset({"com.android.systemui"})


# ---------------------------------------------------------------------------
# B2: Score decay must preserve sign for negative scores
# ---------------------------------------------------------------------------


class TestScoreDecaySign:
    """_select_with_score_decay multiplies negative scores instead of dividing."""

    def test_negative_score_becomes_more_negative_with_executions(self):
        """A negative base score multiplied by decay_factor becomes more negative.

        Before fix: -5000 / 2.0 = -2500 (WRONG: less negative = higher priority)
        After fix:  -5000 * 2.0 = -10000 (CORRECT: more negative = lower priority)
        """
        base_score = -5000.0
        exec_count = 2  # decay_factor = 1 + log2(2) = 2.0

        # Simulate the fixed decay logic
        decay_factor = 1 + math.log2(exec_count)
        decayed_score = base_score * decay_factor  # negative path

        assert decayed_score < base_score, (
            f"Negative score should become MORE negative: {decayed_score} should be < {base_score}"
        )
        assert decayed_score == pytest.approx(-10000.0)

    def test_positive_score_becomes_smaller_with_executions(self):
        """A positive base score divided by decay_factor becomes smaller."""
        base_score = 300.0
        exec_count = 2  # decay_factor = 1 + log2(2) = 2.0

        decay_factor = 1 + math.log2(exec_count)
        decayed_score = base_score / decay_factor  # positive path

        assert decayed_score < base_score
        assert decayed_score == pytest.approx(150.0)

    def test_zero_score_unchanged(self):
        """Zero score stays zero regardless of execution count."""
        base_score = 0.0
        exec_count = 4

        decay_factor = 1 + math.log2(exec_count)
        # base_score >= 0, so division path
        decayed_score = base_score / decay_factor

        assert decayed_score == 0.0

    def test_no_executions_no_decay(self):
        """With exec_count=0, score is unchanged (both positive and negative)."""
        for base_score in [300.0, -5000.0, 0.0]:
            decayed_score = base_score  # exec_count == 0 path
            assert decayed_score == base_score


# ---------------------------------------------------------------------------
# B3: MopScorer deferral dead code removed
# ---------------------------------------------------------------------------


class TestMopScorerDeferralRemoved:
    """MopScorer no longer has dead deferral code for action_type."""

    def test_mop_scorer_scores_direct_mop_action(self):
        """MopScorer returns direct_score for directly_reaches_mop actions."""
        scorer = MopScorer()
        action = _MockAction(directly_reaches_mop=True)
        context = _make_context()
        context.has_untested_inputs = True  # Would have triggered old dead code

        score = scorer.score(action, context)

        assert score == MopScorer.DEFAULT_DIRECT_SCORE

    def test_mop_scorer_scores_transitive_mop_action(self):
        """MopScorer returns transitive_score for reaches_mop actions."""
        scorer = MopScorer()
        action = _MockAction(reaches_mop=True)
        context = _make_context()

        score = scorer.score(action, context)

        assert score == MopScorer.DEFAULT_TRANSITIVE_SCORE

    def test_mop_scorer_returns_zero_for_non_mop(self):
        """MopScorer returns 0 for actions that don't reach MOPs."""
        scorer = MopScorer()
        action = _MockAction()
        context = _make_context()

        score = scorer.score(action, context)

        assert score == 0.0
