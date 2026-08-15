"""Paired continuous estimators, checked against the misreading that shaped them.

The central case is built to reproduce the reading that went wrong: a raw mean
gain of exactly +14 pp over a distribution whose paired median is 0.000 and where
only seven of fifty pairs moved at all. All three summaries have to appear in one
envelope, and they have to disagree, or the test proves nothing.

The rest covers the exact-beside-approximate rule and the degenerate case that
``scipy`` raises on.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aperv_tool.analysis.estimators import paired_continuous


def misleading_mean_pairs() -> tuple[pd.Series, pd.Series]:
    """Fifty pairs whose raw mean gain is +14 pp and whose median gain is zero.

    Forty-three pairs do not move; seven gain 100 pp. The raw mean is therefore
    700 / 50 = 14.0, the paired median is 0.0, and the 10 % trimmed means differ
    from both because trimming discards five observations from each tail.
    """
    index = [f"app{i:03d}" for i in range(50)]
    reference = pd.Series([0.0] * 50, index=index)
    treated = pd.Series([0.0] * 43 + [100.0] * 7, index=index)
    return treated, reference


class TestWilcoxon:
    """Exact and approximate side by side, and the all-zero result."""

    def test_exact_beside_approx(self) -> None:
        """Twelve non-zero differences with ties: both tails are reported."""
        differences = pd.Series(
            [2.0, 2.0, 2.0, -1.0, -1.0, 3.0, 3.0, 5.0, -4.0, 1.0, 1.0, 6.0]
        )

        envelope = paired_continuous.wilcoxon(
            differences, exact_max_n=25, continuity_correction=True
        )

        assert envelope.estimate["n_nonzero"] == 12
        assert envelope.estimate["exact_available"] is True
        assert np.isfinite(envelope.estimate["p_exact"])
        assert np.isfinite(envelope.estimate["p_approx"])
        assert envelope.estimate["p_exact"] != envelope.estimate["p_approx"]
        assert "neither replaces the other" in envelope.convention["reporting"]

    def test_the_exact_budget_is_reported_when_it_is_exceeded(self) -> None:
        rng = np.random.default_rng(2)
        differences = pd.Series(rng.normal(1.0, 1.0, size=40))

        envelope = paired_continuous.wilcoxon(
            differences, exact_max_n=10, continuity_correction=True
        )

        assert envelope.estimate["exact_available"] is False
        assert np.isnan(envelope.estimate["p_exact"])
        assert "not computed" in envelope.convention["exact"]

    def test_the_continuity_correction_is_the_callers(self) -> None:
        differences = pd.Series([1.0, 1.0, -1.0, 2.0, 3.0, -2.0, 4.0, 5.0])

        corrected = paired_continuous.wilcoxon(
            differences, exact_max_n=25, continuity_correction=True
        )
        plain = paired_continuous.wilcoxon(
            differences, exact_max_n=25, continuity_correction=False
        )

        assert corrected.estimate["p_approx"] != plain.estimate["p_approx"]
        assert corrected.estimate["continuity_correction"] is True
        assert "applied" in corrected.convention["approximation"]
        assert "omitted" in plain.convention["approximation"]

    def test_all_zero_degenerate(self) -> None:
        """Nothing moved: a labelled envelope, not an exception."""
        envelope = paired_continuous.wilcoxon(
            pd.Series([0.0] * 20), exact_max_n=25, continuity_correction=True
        )

        assert envelope.estimate["degenerate"] is True
        assert envelope.estimate["degenerate_reason"] == (
            paired_continuous.ALL_ZERO_REASON
        )
        assert envelope.estimate["p_exact"] == 1.0
        assert envelope.estimate["p_approx"] == 1.0
        assert envelope.estimate["n_nonzero"] == 0
        assert "not an absence of effect" in envelope.convention["degenerate"]

    def test_the_companions_ride_along(self) -> None:
        treated, reference = misleading_mean_pairs()

        envelope = paired_continuous.wilcoxon(
            treated - reference, exact_max_n=25, continuity_correction=False
        )

        assert envelope.estimate["mean_difference"] == pytest.approx(14.0)
        assert envelope.estimate["median_difference"] == pytest.approx(0.0)
        assert envelope.estimate["pairs_delta_nonzero"] == 7

    def test_missing_differences_shrink_the_denominator(self) -> None:
        envelope = paired_continuous.wilcoxon(
            pd.Series([1.0, np.nan, -2.0, 3.0]),
            exact_max_n=25,
            continuity_correction=True,
        )

        assert envelope.n == 3
        assert envelope.denominator.reachable == 4
        assert envelope.denominator.reason == "missing differences dropped"


class TestTrimmedMeanDifference:
    """Trimmed, raw and median in one envelope, disagreeing."""

    def test_trimmed_raw_median(self) -> None:
        """The +14 pp mean, the 0.000 median and the trimmed mean between them."""
        treated, reference = misleading_mean_pairs()

        envelope = paired_continuous.trimmed_mean_difference(
            treated, reference, B=500, seed=42
        )

        assert envelope.estimate["raw_mean_difference"] == pytest.approx(14.0)
        assert envelope.estimate["median_difference"] == pytest.approx(0.0)
        # Trimming five observations from each tail of the treated arm leaves two
        # of the seven movers in forty retained values: 200 / 40 = 5.0.
        assert envelope.estimate["trimmed_mean_difference"] == pytest.approx(5.0)
        assert (
            envelope.estimate["raw_mean_difference"]
            != envelope.estimate["trimmed_mean_difference"]
            != envelope.estimate["median_difference"]
        )

    def test_pairs_delta_nonzero(self) -> None:
        """Seven of fifty pairs moved, and the envelope says so."""
        treated, reference = misleading_mean_pairs()

        envelope = paired_continuous.trimmed_mean_difference(
            treated, reference, B=200, seed=42
        )

        assert envelope.estimate["pairs_delta_nonzero"] == 7
        assert envelope.n == 50

    def test_the_estimand_is_named(self) -> None:
        treated, reference = misleading_mean_pairs()

        envelope = paired_continuous.trimmed_mean_difference(
            treated, reference, B=200, seed=42, trim=0.10
        )

        assert envelope.estimand == "diff_of_trimmed_means_10"
        assert "recomputed on every resample" in envelope.convention["estimand"]

    def test_an_all_zero_comparison_is_labelled_not_raised(self) -> None:
        index = [f"app{i:02d}" for i in range(20)]
        values = pd.Series(np.linspace(1.0, 20.0, 20), index=index)

        envelope = paired_continuous.trimmed_mean_difference(
            values, values, B=200, seed=42
        )

        assert envelope.estimate["degenerate"] is True
        assert envelope.estimate["pairs_delta_nonzero"] == 0
        assert envelope.ci == (0.0, 0.0)

    def test_incomplete_pairs_are_named_in_the_envelope(self) -> None:
        first = pd.Series([1.0, 2.0, np.nan], index=["x", "y", "z"])
        second = pd.Series([0.0, 0.0, 0.0], index=["x", "y", "z"])

        envelope = paired_continuous.trimmed_mean_difference(
            first, second, B=100, seed=1
        )

        assert envelope.n == 2
        assert [item.identity for item in envelope.exclusions] == ["z"]

    def test_no_surviving_pair_is_an_error(self) -> None:
        first = pd.Series([np.nan, np.nan])
        second = pd.Series([1.0, 2.0])

        with pytest.raises(ValueError, match="no complete pair"):
            paired_continuous.trimmed_mean_difference(first, second, B=10, seed=1)
