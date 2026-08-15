"""Exact McNemar, its companions, and the floor it must never be read without.

The scenarios here are the reporting rule made executable (INV-CAN-15): a
discordance count never appears without ``b``, ``c`` and a direction; the power
floor always appears beside the p-value; and the two states that a naive
implementation turns into exceptions — no discordance at all — come back as
labelled results.

The floor itself is checked against ``binomtest`` rather than against the
constant 7, so the closed form in the module is verified rather than restated.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.stats import binomtest

from aperv_tool.analysis.estimators import paired_binary


def paired_frame(both: int, b_only: int, c_only: int, neither: int):
    """Two aligned binary Series with the four cell counts requested.

    Args:
        both: Pairs where both arms read positive.
        b_only: Pairs the first arm caught and the second did not.
        c_only: Pairs the second arm caught and the first did not.
        neither: Pairs neither arm caught.

    Returns:
        ``(first, second)`` as ``Series`` indexed by a synthetic unit id.
    """
    first: list[float] = [1] * both + [1] * b_only + [0] * c_only + [0] * neither
    second: list[float] = [1] * both + [0] * b_only + [1] * c_only + [0] * neither
    index = [f"unit{i:03d}" for i in range(len(first))]
    return (
        pd.Series(first, index=index, dtype=float),
        pd.Series(second, index=index, dtype=float),
    )


class TestPowerFloor:
    """The arithmetic that decides whether a comparison could have resolved."""

    def test_power_floor_7_at_0025(self) -> None:
        """Seven discordant pairs are the first that can reject at 0.025."""
        assert paired_binary.power_floor(0.025) == 7

        assert binomtest(0, 6, 0.5, alternative="two-sided").pvalue > 0.025
        assert binomtest(0, 7, 0.5, alternative="two-sided").pvalue <= 0.025

    def test_the_closed_form_matches_binomtest(self) -> None:
        """Non-vacuity: the module's shortcut is the exact test's own best case."""
        for n_disc in range(1, 13):
            best_case = binomtest(0, n_disc, 0.5, alternative="two-sided").pvalue
            assert 2.0 * 0.5**n_disc == pytest.approx(best_case)

    def test_the_floor_moves_with_alpha(self) -> None:
        assert paired_binary.power_floor(0.05) == 6
        assert paired_binary.power_floor(0.01) == 8

    def test_an_impossible_alpha_is_refused(self) -> None:
        with pytest.raises(ValueError):
            paired_binary.power_floor(0.0)


class TestReportingRule:
    """A discordance count never travels alone."""

    def test_never_n_disc_alone(self) -> None:
        """Forty pairs at b=3, c=1: every companion is in the envelope."""
        first, second = paired_frame(both=20, b_only=3, c_only=1, neither=16)

        envelope = paired_binary.mcnemar_exact(first, second, alpha=0.025)

        assert envelope.n == 40
        assert envelope.estimate["b"] == 3
        assert envelope.estimate["c"] == 1
        assert envelope.estimate["n_disc"] == 4
        assert envelope.estimate["direction"] == "first>second"
        assert envelope.estimate["p_two_sided"] == pytest.approx(
            binomtest(3, 4, 0.5, alternative="two-sided").pvalue
        )
        assert envelope.estimate["power_floor_n_disc"] == 7
        assert envelope.estimate["below_floor"] is True

    def test_below_the_floor_the_envelope_says_what_that_means(self) -> None:
        first, second = paired_frame(both=20, b_only=3, c_only=1, neither=16)

        envelope = paired_binary.mcnemar_exact(first, second, alpha=0.025)

        assert envelope.convention["below_floor"] == paired_binary.BELOW_FLOOR_NOTE
        assert "construction, not evidence" in envelope.convention["below_floor"]

    def test_above_the_floor_the_note_is_not_shown(self) -> None:
        first, second = paired_frame(both=10, b_only=9, c_only=1, neither=20)

        envelope = paired_binary.mcnemar_exact(first, second, alpha=0.025)

        assert envelope.estimate["below_floor"] is False
        assert envelope.convention["below_floor"] != paired_binary.BELOW_FLOOR_NOTE

    def test_the_direction_follows_the_larger_cell(self) -> None:
        first, second = paired_frame(both=5, b_only=1, c_only=8, neither=6)

        envelope = paired_binary.mcnemar_exact(first, second, alpha=0.05)

        assert envelope.estimate["direction"] == "second>first"

    def test_equal_cells_have_no_direction(self) -> None:
        first, second = paired_frame(both=5, b_only=4, c_only=4, neither=6)

        envelope = paired_binary.mcnemar_exact(first, second, alpha=0.05)

        assert envelope.estimate["direction"] == "none"
        assert envelope.estimate["p_two_sided"] == pytest.approx(1.0)


class TestDegenerateAndDefective:
    """The cases a naive implementation raises on."""

    def test_zero_discordant_valid(self) -> None:
        """Perfect agreement is a result: p = 1, n_disc = 0, below the floor."""
        first, second = paired_frame(both=30, b_only=0, c_only=0, neither=12)

        envelope = paired_binary.mcnemar_exact(first, second, alpha=0.025)

        assert envelope.estimate["n_disc"] == 0
        assert envelope.estimate["p_two_sided"] == 1.0
        assert envelope.estimate["below_floor"] is True
        assert envelope.estimate["power_floor_n_disc"] == 7
        assert envelope.ci is None

    def test_a_non_binary_side_is_refused(self) -> None:
        first = pd.Series([0.0, 1.0, 4.0])
        second = pd.Series([0.0, 1.0, 1.0])

        with pytest.raises(ValueError, match="not binary"):
            paired_binary.mcnemar_exact(first, second, alpha=0.05)

    def test_incomplete_pairs_reach_the_envelope(self) -> None:
        first = pd.Series([1.0, 0.0, np.nan], index=["x", "y", "z"])
        second = pd.Series([0.0, 0.0, 1.0], index=["x", "y", "z"])

        envelope = paired_binary.mcnemar_exact(first, second, alpha=0.05)

        assert envelope.n == 2
        assert envelope.denominator.reachable == 3
        assert envelope.denominator.analysed == 2
        assert [item.identity for item in envelope.exclusions] == ["z"]


class TestStratified:
    """Strata add visibility, not a different p-value."""

    def test_stratified(self) -> None:
        first, second = paired_frame(both=10, b_only=6, c_only=2, neither=10)
        strata = pd.Series(
            ["small"] * 14 + ["large"] * 14, index=first.index, dtype=object
        )

        plain = paired_binary.mcnemar_exact(first, second, alpha=0.05)
        stratified = paired_binary.mcnemar_exact(
            first, second, alpha=0.05, strata=strata
        )

        # Pooling is exact here, so the p-value cannot move.
        assert stratified.estimate["p_two_sided"] == plain.estimate["p_two_sided"]
        assert stratified.estimate["n_strata"] == 2
        assert (
            stratified.estimate["b__small"] + stratified.estimate["b__large"]
            == stratified.estimate["b"]
        )
        assert (
            stratified.estimate["c__small"] + stratified.estimate["c__large"]
            == stratified.estimate["c"]
        )
        assert "pooled" in stratified.convention["strata"]

    def test_a_cancelling_split_stays_visible(self) -> None:
        """The pooled null is flat; the strata show it is two opposite halves."""
        first, second = paired_frame(both=0, b_only=8, c_only=8, neither=0)
        strata = pd.Series(
            ["small"] * 8 + ["large"] * 8, index=first.index, dtype=object
        )

        envelope = paired_binary.mcnemar_exact(first, second, alpha=0.05, strata=strata)

        assert envelope.estimate["direction"] == "none"
        assert envelope.estimate["b__small"] == 8
        assert envelope.estimate["c__small"] == 0
        assert envelope.estimate["b__large"] == 0
        assert envelope.estimate["c__large"] == 8
