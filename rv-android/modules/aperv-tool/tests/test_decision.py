"""The four verdicts, and the margin the module will not invent.

Every branch is exercised on an interval placed by hand, because the whole
function is a classification of one interval against one threshold and a
mis-placed boundary would be invisible in aggregate.
"""

from __future__ import annotations

import pytest

from aperv_tool.analysis.corpus import FreezeItemUnset
from aperv_tool.analysis.estimators import decision


class TestMarginIsRequired:
    """A threshold nobody declared is a decision nobody made."""

    def test_margin_required(self) -> None:
        with pytest.raises(FreezeItemUnset, match="margin"):
            decision.decide(1.2, (0.4, 2.0))

    def test_a_negative_margin_is_refused(self) -> None:
        with pytest.raises(ValueError, match="magnitude"):
            decision.decide(1.2, (0.4, 2.0), margin=-0.5)

    def test_zero_is_a_legal_margin(self) -> None:
        """Zero says "any difference counts", which is a declaration too."""
        envelope = decision.decide(1.2, (0.4, 2.0), margin=0.0)

        assert envelope.estimate["verdict"] == "above_margin"


class TestVerdicts:
    """One interval per branch."""

    def test_an_interval_clear_of_the_upper_boundary(self) -> None:
        envelope = decision.decide(3.0, (2.0, 4.0), margin=1.0)

        assert envelope.estimate["verdict"] == "above_margin"
        assert envelope.estimate["excludes_zero"] is True

    def test_an_interval_clear_of_the_lower_boundary(self) -> None:
        envelope = decision.decide(-3.0, (-4.0, -2.0), margin=1.0)

        assert envelope.estimate["verdict"] == "below_margin"

    def test_an_interval_inside_the_band(self) -> None:
        envelope = decision.decide(0.1, (-0.4, 0.5), margin=1.0)

        assert envelope.estimate["verdict"] == "within_margin"
        assert envelope.estimate["excludes_zero"] is False

    def test_an_interval_straddling_a_boundary(self) -> None:
        envelope = decision.decide(0.9, (0.2, 1.6), margin=1.0)

        assert envelope.estimate["verdict"] == "inconclusive"
        assert "straddles" in envelope.estimate["reason"]

    def test_the_boundary_itself_counts_as_clearing_it(self) -> None:
        envelope = decision.decide(2.0, (1.0, 3.0), margin=1.0)

        assert envelope.estimate["verdict"] == "above_margin"


class TestNoInterval:
    """An estimator that computed no interval has decided nothing."""

    def test_a_missing_interval_is_inconclusive_with_a_reason(self) -> None:
        envelope = decision.decide(5.0, None, margin=0.1)

        assert envelope.estimate["verdict"] == "inconclusive"
        assert "no interval" in envelope.estimate["reason"]
        assert envelope.ci is None

    def test_inconclusive_is_not_a_negative_result(self) -> None:
        envelope = decision.decide(0.9, (0.2, 1.6), margin=1.0)

        assert "not a negative result" in envelope.convention["inconclusive"]


class TestEnvelopeShape:
    """What the verdict stays attached to."""

    def test_the_estimand_names_what_was_judged(self) -> None:
        envelope = decision.decide(
            3.0, (2.0, 4.0), margin=1.0, estimand="diff_of_trimmed_means_10", n=162
        )

        assert envelope.estimand == "decision_on_diff_of_trimmed_means_10"
        assert envelope.n == 162

    def test_reversed_bounds_are_refused(self) -> None:
        with pytest.raises(ValueError, match="reversed"):
            decision.decide(1.0, (4.0, 2.0), margin=1.0)
