"""Multi-arm ranking on constructed frames with a known ordering.

The synthetic frame below is a strict dominance: every unit's value rises across
the three arms, so the mean ranks must come out 1, 2, 3 and every rank-biserial
must be -1 in the direction of the dominance. That is a stronger check than a
p-value, which would pass on a mildly ordered frame too.

The degenerate branches — two arms, too few complete units — return an envelope
saying so, because the screening caller has to print something either way.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aperv_tool.analysis.estimators import multiarm


def dominance_frame(units: int = 12) -> pd.DataFrame:
    """Three arms in strict ascending order on every unit."""
    index = [f"app{i:02d}" for i in range(units)]
    base = np.linspace(10.0, 40.0, units)
    return pd.DataFrame(
        {"low": base, "mid": base + 2.0, "high": base + 5.0}, index=index
    )


class TestAverageRanks:
    """Ties share the mean of the ranks they span."""

    def test_distinct_values_rank_one_to_n(self) -> None:
        assert list(multiarm.average_ranks(np.array([5.0, 1.0, 3.0]))) == [
            3.0,
            1.0,
            2.0,
        ]

    def test_a_tied_block_shares_its_ranks(self) -> None:
        ranks = multiarm.average_ranks(np.array([1.0, 2.0, 2.0, 4.0]))

        assert list(ranks) == [1.0, 2.5, 2.5, 4.0]

    def test_everything_tied_gives_the_same_rank(self) -> None:
        ranks = multiarm.average_ranks(np.array([7.0, 7.0, 7.0]))

        assert list(ranks) == [2.0, 2.0, 2.0]


class TestRankBiserial:
    """Direction and magnitude on hand-built pairs."""

    def test_total_dominance_is_minus_one(self) -> None:
        first = np.array([1.0, 2.0, 3.0])
        second = np.array([2.0, 3.0, 4.0])

        assert multiarm.rank_biserial(first, second) == pytest.approx(-1.0)

    def test_the_reverse_is_plus_one(self) -> None:
        first = np.array([5.0, 6.0, 7.0])
        second = np.array([1.0, 2.0, 3.0])

        assert multiarm.rank_biserial(first, second) == pytest.approx(1.0)

    def test_no_moving_pair_is_zero(self) -> None:
        values = np.array([1.0, 2.0, 3.0])

        assert multiarm.rank_biserial(values, values) == 0.0

    def test_zero_differences_are_dropped_not_counted(self) -> None:
        """Two moving pairs, one flat: the flat one changes nothing."""
        first = np.array([2.0, 4.0, 9.0])
        second = np.array([1.0, 3.0, 9.0])

        assert multiarm.rank_biserial(first, second) == pytest.approx(1.0)


class TestFriedmanHolm:
    """The ranking, the adjusted table, and the summaries beside them."""

    def test_a_dominance_frame_ranks_in_order(self) -> None:
        envelope = multiarm.friedman_holm(
            dominance_frame(), arms=["low", "mid", "high"], trim=0.10
        )

        assert envelope.estimate["available"] is True
        assert envelope.estimate["mean_rank__low"] == pytest.approx(1.0)
        assert envelope.estimate["mean_rank__mid"] == pytest.approx(2.0)
        assert envelope.estimate["mean_rank__high"] == pytest.approx(3.0)
        assert envelope.estimate["p_value"] < 0.01

    def test_every_pair_carries_its_effect_size(self) -> None:
        envelope = multiarm.friedman_holm(
            dominance_frame(), arms=["low", "mid", "high"], trim=0.10
        )

        assert envelope.estimate["n_pairs"] == 3
        assert envelope.estimate["rank_biserial__low|mid"] == pytest.approx(-1.0)
        assert envelope.estimate["rank_biserial__low|high"] == pytest.approx(-1.0)
        assert (
            envelope.estimate["p_holm__low|mid"] >= envelope.estimate["p_raw__low|mid"]
        )

    def test_the_raw_mean_sits_beside_the_trimmed_one(self) -> None:
        frame = dominance_frame()
        frame.loc["app00", "high"] = 10_000.0

        envelope = multiarm.friedman_holm(frame, arms=["low", "mid", "high"], trim=0.10)

        assert (
            envelope.estimate["raw_mean__high"]
            > envelope.estimate["trimmed_mean__high"]
        )
        assert "discarded tail" in envelope.convention["summary"]

    def test_it_never_returns_a_verdict(self) -> None:
        envelope = multiarm.friedman_holm(
            dominance_frame(), arms=["low", "mid", "high"], trim=0.10
        )

        assert "never a verdict" in envelope.convention["scope"]
        assert not any(key.startswith("winner") for key in envelope.estimate)

    def test_incomplete_units_are_dropped_once_and_named(self) -> None:
        frame = dominance_frame()
        frame.loc["app03", "mid"] = np.nan

        envelope = multiarm.friedman_holm(frame, arms=["low", "mid", "high"], trim=0.10)

        assert envelope.estimate["n_complete"] == 11
        assert [item.identity for item in envelope.exclusions] == ["app03"]
        assert envelope.denominator.reachable == 12
        assert envelope.denominator.analysed == 11

    def test_two_arms_leave_the_omnibus_undefined(self) -> None:
        envelope = multiarm.friedman_holm(
            dominance_frame(), arms=["low", "high"], trim=0.10
        )

        assert envelope.estimate["available"] is False
        assert "2 arms" in envelope.estimate["reason"]
        assert np.isnan(envelope.estimate["p_value"])

    def test_too_few_complete_units_leave_it_undefined(self) -> None:
        envelope = multiarm.friedman_holm(
            dominance_frame(units=2), arms=["low", "mid", "high"], trim=0.10
        )

        assert envelope.estimate["available"] is False
        assert "2 complete units" in envelope.estimate["reason"]

    def test_arms_that_never_move_do_not_break_the_table(self) -> None:
        index = [f"app{i:02d}" for i in range(8)]
        flat = pd.Series([3.0] * 8, index=index)
        frame = pd.DataFrame({"a": flat, "b": flat, "c": flat + 1.0})

        envelope = multiarm.friedman_holm(frame, arms=["a", "b", "c"], trim=0.10)

        assert envelope.estimate["p_raw__a|b"] == 1.0

    def test_a_missing_arm_column_names_itself(self) -> None:
        with pytest.raises(KeyError, match="absent"):
            multiarm.friedman_holm(
                dominance_frame(), arms=["low", "missing"], trim=0.10
            )
