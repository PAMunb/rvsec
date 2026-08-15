"""The intraclass correlation on a design whose value can be written out by hand,
and every way it degenerates.

The balanced three-unit design below has mean squares of 32 and 2 and an
effective replica count of 2, so the coefficient is 30/34 exactly. Anything that
drifts in the sums of squares moves that number, which is what makes it worth
asserting to full precision rather than approximately.

The degenerate cases are the point of the module: a saturated binary outcome is
the expected shape of several campaign columns, and it must come back labelled
rather than as a plausible 0.0.
"""

from __future__ import annotations

import pandas as pd
import pytest

from aperv_tool.analysis.estimators import variance


def balanced_frame() -> pd.DataFrame:
    """Three units, two replicas each; unit means 2, 6, 10 and spread 1."""
    return pd.DataFrame(
        {
            "apk": ["a", "a", "b", "b", "c", "c"],
            "rep": [1, 2, 1, 2, 1, 2],
            "value": [1.0, 3.0, 5.0, 7.0, 9.0, 11.0],
        }
    )


class TestKnownAnswer:
    """The hand computation, to full precision."""

    def test_the_balanced_design_gives_thirty_over_thirty_four(self) -> None:
        envelope = variance.icc(
            balanced_frame(), unit="apk", replica="rep", value="value"
        )

        assert envelope.estimate["ms_between"] == pytest.approx(32.0)
        assert envelope.estimate["ms_within"] == pytest.approx(2.0)
        assert envelope.estimate["k0"] == pytest.approx(2.0)
        assert envelope.estimate["icc"] == pytest.approx(30.0 / 34.0)
        assert envelope.estimate["degenerate"] is False

    def test_the_envelope_reports_the_design(self) -> None:
        envelope = variance.icc(
            balanced_frame(), unit="apk", replica="rep", value="value"
        )

        assert envelope.estimate["units"] == 3
        assert envelope.estimate["observations"] == 6
        assert envelope.estimate["replicas_mean"] == pytest.approx(2.0)
        assert envelope.estimand == "icc_one_way"

    def test_an_unbalanced_design_uses_the_effective_replica_count(self) -> None:
        frame = pd.DataFrame(
            {
                "apk": ["a", "a", "a", "b", "b", "c", "c"],
                "rep": [1, 2, 3, 1, 2, 1, 2],
                "value": [1.0, 2.0, 3.0, 5.0, 7.0, 9.0, 11.0],
            }
        )

        envelope = variance.icc(frame, unit="apk", replica="rep", value="value")

        assert envelope.estimate["k0"] != pytest.approx(2.0)
        assert 0.0 < envelope.estimate["icc"] < 1.0


class TestDegenerate:
    """Every branch that cannot produce a partition of variance."""

    def test_icc_degenerate_reason(self) -> None:
        """A saturated binary outcome: every unit at 1, nothing to partition."""
        frame = pd.DataFrame(
            {
                "apk": ["a", "a", "b", "b", "c", "c"],
                "rep": [1, 2, 1, 2, 1, 2],
                "value": [1.0] * 6,
            }
        )

        envelope = variance.icc(frame, unit="apk", replica="rep", value="value")

        assert envelope.estimate["degenerate"] is True
        assert envelope.estimate["degenerate_reason"] == variance.CONSTANT_OUTCOME
        assert "never returned as a bare 0.0" in envelope.convention["reporting"]

    def test_a_single_replica_per_unit_is_not_applicable(self) -> None:
        """The final campaign's design; it must not read as a failure."""
        frame = pd.DataFrame(
            {
                "apk": ["a", "b", "c"],
                "rep": [1, 1, 1],
                "value": [1.0, 5.0, 9.0],
            }
        )

        envelope = variance.icc(frame, unit="apk", replica="rep", value="value")

        assert envelope.estimate["degenerate_reason"] == variance.NO_REPLICATION

    def test_one_unit_cannot_be_compared_to_anything(self) -> None:
        frame = pd.DataFrame({"apk": ["a", "a"], "rep": [1, 2], "value": [1.0, 3.0]})

        envelope = variance.icc(frame, unit="apk", replica="rep", value="value")

        assert envelope.estimate["degenerate_reason"] == variance.TOO_FEW_UNITS

    def test_replicas_that_agree_exactly_give_a_labelled_one(self) -> None:
        frame = pd.DataFrame(
            {
                "apk": ["a", "a", "b", "b"],
                "rep": [1, 2, 1, 2],
                "value": [2.0, 2.0, 8.0, 8.0],
            }
        )

        envelope = variance.icc(frame, unit="apk", replica="rep", value="value")

        assert envelope.estimate["icc"] == 1.0
        assert envelope.estimate["degenerate_reason"] == variance.NO_WITHIN_VARIANCE

    def test_a_negative_component_is_clipped_and_says_so(self) -> None:
        """Replicas spread wider than the units, which the ratio reads as below zero."""
        frame = pd.DataFrame(
            {
                "apk": ["a", "a", "b", "b", "c", "c"],
                "rep": [1, 2, 1, 2, 1, 2],
                "value": [0.0, 20.0, 1.0, 19.0, 2.0, 18.0],
            }
        )

        envelope = variance.icc(frame, unit="apk", replica="rep", value="value")

        assert envelope.estimate["icc"] == 0.0
        assert envelope.estimate["icc_uncorrected"] < 0.0
        assert envelope.estimate["degenerate_reason"] == variance.CLIPPED_NEGATIVE


class TestDefectiveInput:
    """States that would silently inflate a component."""

    def test_a_repeated_replica_index_is_refused(self) -> None:
        frame = pd.DataFrame(
            {
                "apk": ["a", "a", "b", "b"],
                "rep": [1, 1, 1, 2],
                "value": [1.0, 3.0, 5.0, 7.0],
            }
        )

        with pytest.raises(ValueError, match="repeated"):
            variance.icc(frame, unit="apk", replica="rep", value="value")

    def test_a_missing_column_names_itself(self) -> None:
        with pytest.raises(KeyError, match="coverage"):
            variance.icc(balanced_frame(), unit="apk", replica="rep", value="coverage")
