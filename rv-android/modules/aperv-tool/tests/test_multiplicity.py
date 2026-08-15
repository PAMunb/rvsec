"""Adjustment procedures against hand-computed answers, and the family that is required.

Both procedures are checked on a family whose adjusted values can be written out
by hand, and both are checked for monotonicity, which is the property a
straightforward transcription of the formula loses.
"""

from __future__ import annotations

import pytest

from aperv_tool.analysis.corpus import FreezeItemUnset
from aperv_tool.analysis.estimators import multiplicity


class TestHolm:
    """Step-down, with the running maximum that keeps the ordering."""

    def test_matches_the_hand_computation(self) -> None:
        """0.01, 0.02, 0.03 at m = 3 adjust to 0.03, 0.04, 0.04."""
        assert multiplicity.holm([0.01, 0.02, 0.03]) == pytest.approx(
            [0.03, 0.04, 0.04]
        )

    def test_the_input_order_is_preserved(self) -> None:
        assert multiplicity.holm([0.03, 0.01, 0.02]) == pytest.approx(
            [0.04, 0.03, 0.04]
        )

    def test_adjusted_values_never_decrease_with_the_raw_ones(self) -> None:
        raw = [0.001, 0.04, 0.049, 0.2, 0.9]
        adjusted = multiplicity.holm(raw)

        assert adjusted == sorted(adjusted)
        assert all(a >= r for a, r in zip(adjusted, raw))

    def test_values_are_capped_at_one(self) -> None:
        assert multiplicity.holm([0.5, 0.6, 0.7]) == pytest.approx([1.0, 1.0, 1.0])


class TestFdrBh:
    """Step-up, with the running minimum."""

    def test_matches_the_hand_computation(self) -> None:
        """0.01, 0.02, 0.03 at m = 3 all adjust to 0.03."""
        assert multiplicity.fdr_bh([0.01, 0.02, 0.03]) == pytest.approx(
            [0.03, 0.03, 0.03]
        )

    def test_it_is_never_more_conservative_than_holm(self) -> None:
        raw = [0.001, 0.01, 0.04, 0.2, 0.9]
        holm = multiplicity.holm(raw)
        bh = multiplicity.fdr_bh(raw)

        assert all(b <= h + 1e-12 for b, h in zip(bh, holm))

    def test_adjusted_values_stay_monotone(self) -> None:
        adjusted = multiplicity.fdr_bh([0.001, 0.04, 0.049, 0.2, 0.9])

        assert adjusted == sorted(adjusted)


class TestAdjust:
    """The envelope, and the declaration it will not make on the caller's behalf."""

    def test_family_required(self) -> None:
        """Omitting the family raises rather than adjusting over 'these'."""
        with pytest.raises(FreezeItemUnset, match="family"):
            multiplicity.adjust([0.01, 0.2], method="holm")

    def test_the_family_and_its_size_reach_the_envelope(self) -> None:
        envelope = multiplicity.adjust(
            {"first": 0.01, "second": 0.02, "third": 0.03},
            family="secondary-variants",
            method="holm",
        )

        assert envelope.estimate["family"] == "secondary-variants"
        assert envelope.estimate["m"] == 3
        assert envelope.estimate["p_raw__first"] == pytest.approx(0.01)
        assert envelope.estimate["p_adj__first"] == pytest.approx(0.03)
        assert envelope.convention["family"] == "secondary-variants"

    def test_a_sequence_is_named_by_position(self) -> None:
        envelope = multiplicity.adjust([0.01, 0.02], family="pairwise", method="fdr_bh")

        assert envelope.estimate["p_raw__0"] == pytest.approx(0.01)
        assert envelope.estimand == "multiplicity_fdr_bh"

    def test_rejection_is_left_to_the_decision_module(self) -> None:
        envelope = multiplicity.adjust([0.01], family="one", method="holm")

        assert not any(key.startswith("reject") for key in envelope.estimate)
        assert "decision module" in envelope.convention["rejection"]

    def test_an_unknown_method_is_refused(self) -> None:
        with pytest.raises(ValueError, match="method"):
            multiplicity.adjust([0.01], family="one", method="bonferroni")

    def test_an_empty_family_is_refused(self) -> None:
        with pytest.raises(ValueError, match="empty family"):
            multiplicity.adjust([], family="one", method="holm")

    def test_values_outside_the_unit_interval_are_refused(self) -> None:
        with pytest.raises(ValueError, match=r"outside \[0, 1\]"):
            multiplicity.adjust([0.5, 1.4], family="one", method="holm")
