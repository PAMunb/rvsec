"""The resampling kernel against answers that were known before it ran.

The two extracted functions are checked three ways: against the closed form of
their own definition, against the property that motivated the pinned estimand
(trimming and differencing do not commute), and against a synthetic location
shift whose true value the interval has to cover. The permutation test is checked
against its floor — the smallest p-value the add-one correction admits — and
against determinism under a fixed seed.

None of this touches a campaign artefact. Correctness for this layer comes only
from constructed data (INV-CAN-21).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy.stats import trim_mean

from aperv_tool.analysis.estimators import resampling


class TestDiffOfTrimmedMeans:
    """The pinned estimand, and what makes it different from its neighbours."""

    def test_matches_the_closed_form(self) -> None:
        """Ten values trimmed at 10 % drop one from each tail."""
        a = np.arange(1.0, 11.0)
        b = np.zeros(10)

        # mean(2..9) = 5.5 with the 1 and the 10 discarded.
        assert resampling.diff_of_trimmed_means(a, b, 0.10) == pytest.approx(5.5)

    def test_the_tails_do_not_reach_the_estimate(self) -> None:
        """Pushing a trimmed observation further out changes nothing."""
        a = np.arange(1.0, 11.0)
        b = np.zeros(10)
        moved = a.copy()
        moved[-1] = 10_000.0

        assert resampling.diff_of_trimmed_means(
            moved, b, 0.10
        ) == resampling.diff_of_trimmed_means(a, b, 0.10)

    def test_it_is_not_the_trimmed_mean_of_the_differences(self) -> None:
        """The distinction the campaign pinned, on data where the two disagree.

        Trimming discards different observations on each side than it does on the
        differences, so the two quantities are not the same estimand. A run that
        computed the wrong one would still produce a plausible number, which is
        why the difference is asserted rather than assumed.
        """
        rng = np.random.default_rng(11)
        a = rng.normal(10.0, 3.0, size=40)
        b = rng.normal(8.0, 5.0, size=40)

        pinned = resampling.diff_of_trimmed_means(a, b, 0.10)
        other = float(trim_mean(a - b, 0.10))

        assert abs(pinned - other) > 1e-9


class TestPairedBootstrapCi:
    """Coverage, determinism, and the pairing the interval depends on."""

    def test_covers_a_known_location_shift(self) -> None:
        """A constructed shift of 2.0 lands inside the interval."""
        rng = np.random.default_rng(3)
        b = rng.normal(20.0, 4.0, size=120)
        a = b + 2.0 + rng.normal(0.0, 0.5, size=120)

        point, low, high = resampling.paired_bootstrap_ci(a, b, B=2000, seed=42)

        assert low < 2.0 < high
        assert point == pytest.approx(2.0, abs=0.3)

    def test_identical_arms_give_a_zero_point_estimate(self) -> None:
        values = np.linspace(1.0, 50.0, 50)

        point, low, high = resampling.paired_bootstrap_ci(
            values, values, B=500, seed=42
        )

        assert point == 0.0
        assert low == 0.0 and high == 0.0

    def test_the_seed_makes_the_interval_reproducible(self) -> None:
        rng = np.random.default_rng(5)
        a, b = rng.normal(size=60), rng.normal(size=60)

        first = resampling.paired_bootstrap_ci(a, b, B=500, seed=42)
        again = resampling.paired_bootstrap_ci(a, b, B=500, seed=42)
        other = resampling.paired_bootstrap_ci(a, b, B=500, seed=43)

        assert first == again
        assert first[1:] != other[1:]

    def test_unequal_lengths_are_refused(self) -> None:
        """The listwise cleaning is a precondition, not something to guess at."""
        with pytest.raises(AssertionError):
            resampling.paired_bootstrap_ci(np.zeros(5), np.zeros(4), B=10, seed=1)


class TestAlignPairs:
    """Listwise cleaning that names what it dropped."""

    def test_pairs_by_index_not_by_position(self) -> None:
        a = pd.Series([1.0, 2.0, 3.0], index=["x", "y", "z"])
        b = pd.Series([30.0, 20.0, 10.0], index=["z", "y", "x"])

        left, right, exclusions = resampling.align_pairs(a, b)

        assert exclusions == ()
        assert list(left.index) == list(right.index)
        assert (right.loc["x"], right.loc["z"]) == (10.0, 30.0)

    def test_incomplete_pairs_leave_by_name(self) -> None:
        a = pd.Series([1.0, np.nan, 3.0], index=["x", "y", "z"])
        b = pd.Series([1.0, 2.0], index=["x", "y"])

        left, _, exclusions = resampling.align_pairs(a, b)

        assert list(left.index) == ["x"]
        assert {item.identity for item in exclusions} == {"y", "z"}
        assert {item.reason for item in exclusions} == {"incomplete pair"}

    def test_bare_sequences_are_paired_by_position(self) -> None:
        left, right, exclusions = resampling.align_pairs([1, 2, 3], [3, 2, 1])

        assert exclusions == ()
        assert list(left) == [1.0, 2.0, 3.0]
        assert list(right) == [3.0, 2.0, 1.0]


class TestPermutation:
    """A p-value with a floor, and a shuffle that is reproducible."""

    @staticmethod
    def mean_gap(first: np.ndarray, second: np.ndarray) -> float:
        return float(np.mean(first) - np.mean(second))

    def test_a_separated_pair_of_groups_reaches_the_floor(self) -> None:
        values = list(np.arange(0.0, 20.0)) + list(np.arange(100.0, 120.0))
        groups = ["low"] * 20 + ["high"] * 20

        envelope = resampling.permutation(
            values, groups, statistic=self.mean_gap, n_perm=200, seed=7
        )

        assert envelope.estimate["p_two_sided"] == pytest.approx(1 / 201)
        assert envelope.estimate["first_label"] == "high"
        assert envelope.estimate["n_first"] == 20

    def test_exchangeable_groups_do_not_reach_the_floor(self) -> None:
        rng = np.random.default_rng(19)
        values = rng.normal(size=60)
        groups = ["a"] * 30 + ["b"] * 30

        envelope = resampling.permutation(
            values, groups, statistic=self.mean_gap, n_perm=400, seed=7
        )

        assert envelope.estimate["p_two_sided"] > 0.05

    def test_the_envelope_states_the_smallest_reportable_p(self) -> None:
        values = [1.0, 2.0, 3.0, 4.0]
        groups = ["a", "a", "b", "b"]

        envelope = resampling.permutation(
            values, groups, statistic=self.mean_gap, n_perm=99, seed=1
        )

        assert "0.01" in envelope.convention["p_value"]
        assert envelope.estimand == "permutation_mean_gap"

    def test_three_labels_are_refused(self) -> None:
        with pytest.raises(ValueError, match="two labels"):
            resampling.permutation(
                [1.0, 2.0, 3.0],
                ["a", "b", "c"],
                statistic=self.mean_gap,
                n_perm=10,
                seed=1,
            )
