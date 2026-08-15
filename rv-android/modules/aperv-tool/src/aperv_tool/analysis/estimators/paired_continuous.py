"""Paired continuous comparisons, each reported beside the summary that contradicts it.

Two estimators, one discipline. The Wilcoxon signed-rank test answers whether the
paired differences are centred at zero; the trimmed-mean difference answers by how
much they differ. Neither is allowed to leave alone.

The rule comes from a reading that was wrong on numbers that were each right. A
mean gain of ``+14 pp`` was reported for a comparison whose paired median was
``0.000``: the mean was correct, and it was carried by a handful of applications
in a distribution where almost no pair moved at all. A reader given only the mean
concluded that the arms differed everywhere. So a paired-continuous envelope here
carries the trimmed mean, the raw mean and the paired median together, plus the
count of pairs whose difference is not zero — the single number that would have
made that reading impossible (INV-CAN-15).

The second discipline is exact before approximate (INV-CAN-16). ``wilcoxon``
computes the exact conditional tail whenever the number of non-zero differences
is within the caller's budget and reports it **beside** the tie- and
continuity-corrected normal approximation, never instead of it. The two disagree
most exactly where a small paired study lives, and seeing them together is what
tells a reader which regime they are in. When the exact computation is out of
budget the envelope says so by name rather than quietly returning the
approximation under the same key.

The tie correction to the approximation's variance is unconditional — without it
the statistic is simply wrong on a coarse outcome, and the outcomes here are
coarse. The continuity correction is the caller's declaration, because it is the
one knob that separates two defensible numbers: ``scipy``'s default omits it, and
the campaign artefacts this library reproduces were produced under that default,
so a parity check and a report can want opposite settings. It is required rather
than defaulted so a table states which one it is showing.

All-zero differences are a result, not an error. Both estimators return a
labelled degenerate envelope in that case: ``scipy`` raises, and an exception
there would push the caller into a ``try`` block whose except branch is where
degenerate comparisons go to be forgotten.
"""

from __future__ import annotations

import warnings
from typing import Union

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon as _scipy_wilcoxon

from aperv_tool.analysis.envelope import Denominator, Envelope
from aperv_tool.analysis.estimators.resampling import (
    PairInput,
    align_pairs,
    paired_bootstrap_ci,
)

#: Why a degenerate paired comparison is degenerate. One string, because the
#: caller that branches on it should be matching a constant, not a phrasing.
ALL_ZERO_REASON = "every paired difference is zero"


def _differences(d: PairInput) -> pd.Series:
    """The differences as a float ``Series`` with missing values dropped."""
    series = (
        d.astype(float)
        if isinstance(d, pd.Series)
        else pd.Series(np.asarray(d, dtype=float))
    )
    return series.dropna()


def wilcoxon(
    d: PairInput,
    *,
    exact_max_n: int,
    continuity_correction: bool,
    provenance_ref: str = "",
) -> Envelope:
    """Wilcoxon signed-rank on paired differences, exact and approximate side by side.

    Args:
        d: The paired differences, one per unit. Missing values are dropped and
            counted; zero differences are discarded by the test itself
            (``zero_method="wilcox"``), which is what makes ``n_nonzero`` the
            test's real sample size and worth reporting separately from ``n``.
        exact_max_n: Largest ``n_nonzero`` for which the exact conditional tail
            is computed. Required and without a default: the exact computation
            is combinatorial, and where a caller draws that line changes which
            p-value they are quoting.
        continuity_correction: Whether the normal approximation carries the
            continuity correction. Required: ``scipy``'s default is ``False`` and
            a report that wants the corrected number and a parity check that
            wants the campaign's are both legitimate, so the choice is stated
            rather than inherited. The tie correction applies either way.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        An envelope carrying ``statistic``, ``n_nonzero``, ``p_exact``,
        ``p_approx``, ``exact_available``, and the raw mean, paired median and
        ``pairs_delta_nonzero`` that INV-CAN-15 requires beside them. On
        all-zero differences the envelope is labelled degenerate with
        ``p_exact = p_approx = 1.0`` rather than raising.
    """
    values = _differences(d)
    dropped = (len(d) if hasattr(d, "__len__") else len(values)) - len(values)
    array = values.to_numpy(dtype=float)
    nonzero = int(np.count_nonzero(array))

    estimate: dict[str, Union[float, int, str, bool]] = {
        "n_nonzero": nonzero,
        "pairs_delta_nonzero": nonzero,
        "mean_difference": float(np.mean(array)) if array.size else float("nan"),
        "median_difference": float(np.median(array)) if array.size else float("nan"),
        "exact_max_n": int(exact_max_n),
        "continuity_correction": bool(continuity_correction),
    }
    convention: dict[str, str] = {
        "test": "Wilcoxon signed-rank on the paired differences",
        "zero_method": "wilcox — zero differences are discarded before ranking",
        "reporting": "the exact tail and the normal approximation are both "
        "reported; neither replaces the other",
        "approximation": "tie-corrected always; continuity correction "
        f"{'applied' if continuity_correction else 'omitted'} by the caller",
    }

    if nonzero == 0:
        estimate.update(
            {
                "statistic": float("nan"),
                "p_exact": 1.0,
                "p_approx": 1.0,
                "exact_available": False,
                "degenerate": True,
                "degenerate_reason": ALL_ZERO_REASON,
            }
        )
        convention["degenerate"] = (
            "no pair moved, so the test has no sample; p = 1 describes the data, "
            "not an absence of effect"
        )
    else:
        with warnings.catch_warnings():
            # scipy warns that the exact tail is only approximate under ties.
            # That is exactly why the approximation is reported beside it, and
            # the warning would otherwise fire once per comparison in a table.
            warnings.simplefilter("ignore")
            approx = _scipy_wilcoxon(
                array,
                zero_method="wilcox",
                method="approx",
                correction=continuity_correction,
            )
            exact_available = nonzero <= exact_max_n
            p_exact = (
                float(
                    _scipy_wilcoxon(array, zero_method="wilcox", method="exact").pvalue
                )
                if exact_available
                else float("nan")
            )
        estimate.update(
            {
                "statistic": float(approx.statistic),
                "p_exact": p_exact,
                "p_approx": float(approx.pvalue),
                "exact_available": bool(exact_available),
                "degenerate": False,
                "degenerate_reason": "",
            }
        )
        if not exact_available:
            convention["exact"] = (
                f"not computed: {nonzero} non-zero differences exceed the "
                f"caller's exact_max_n of {exact_max_n}"
            )

    return Envelope(
        estimand="wilcoxon_signed_rank",
        n=int(len(values)),
        denominator=Denominator(
            reachable=int(len(values) + max(dropped, 0)),
            analysed=int(len(values)),
            reason="missing differences dropped" if dropped > 0 else "",
        ),
        estimate=estimate,
        ci=None,
        convention=convention,
        exclusions=(),
        provenance_ref=provenance_ref,
    )


def trimmed_mean_difference(
    a: PairInput,
    b: PairInput,
    *,
    B: int,
    seed: int,
    trim: float = 0.10,
    alpha: float = 0.05,
    provenance_ref: str = "",
) -> Envelope:
    """Paired bootstrap of the difference of trimmed means, with its companions.

    The estimand is the campaign's pinned one and is named in the envelope:
    the difference of trimmed means recomputed on every resample, not the
    trimmed mean of the differences. ``resampling.paired_bootstrap_ci`` does the
    arithmetic; this function is the seat that reports it, which is why the raw
    mean, the paired median and the count of moving pairs are assembled here and
    not there.

    Args:
        a: First arm's values, one per unit.
        b: Second arm's values, aligned with ``a``.
        B: Number of resamples. Required without a default so a run's precision
            is a recorded choice rather than an inherited one.
        seed: Seed of the resampling generator, likewise required — an interval
            whose seed nobody wrote down cannot be reproduced.
        trim: Fraction cut from each tail. The campaign's pinned value is 0.10
            and it names the estimand.
        alpha: One minus the interval's coverage.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        An envelope whose ``ci`` is the percentile interval and whose estimate
        carries ``trimmed_mean_difference``, ``raw_mean_difference``,
        ``median_difference`` and ``pairs_delta_nonzero`` together.

    Raises:
        ValueError: No complete pair survives the listwise cleaning.
    """
    left, right, exclusions = align_pairs(a, b)
    if len(left) == 0:
        raise ValueError("no complete pair survived listwise cleaning")

    first = left.to_numpy(dtype=float)
    second = right.to_numpy(dtype=float)
    differences = first - second
    nonzero = int(np.count_nonzero(differences))

    point, lo, hi = paired_bootstrap_ci(
        first, second, B=B, seed=seed, trim=trim, alpha=alpha
    )
    trim_pct = int(round(trim * 100))

    estimate: dict[str, Union[float, int, str, bool]] = {
        "trimmed_mean_difference": float(point),
        "raw_mean_difference": float(np.mean(first) - np.mean(second)),
        "median_difference": float(np.median(differences)),
        "pairs_delta_nonzero": nonzero,
        "trim": float(trim),
        "n_resamples": int(B),
        "degenerate": bool(nonzero == 0),
        "degenerate_reason": ALL_ZERO_REASON if nonzero == 0 else "",
    }

    reachable = len(left) + len(exclusions)
    return Envelope(
        estimand=f"diff_of_trimmed_means_{trim_pct}",
        n=int(len(left)),
        denominator=Denominator(
            reachable=reachable,
            analysed=int(len(left)),
            reason="incomplete pairs dropped listwise" if exclusions else "",
        ),
        estimate=estimate,
        ci=(float(lo), float(hi)),
        convention={
            "estimand": f"difference of {trim_pct} % trimmed means, recomputed on "
            "every resample — not the trimmed mean of the differences",
            "resampling": "paired: units are drawn with replacement and the same "
            "draw is applied to both arms",
            "ci": f"percentile interval at {1 - alpha:.0%}",
            "seed": str(seed),
            "companions": "the raw mean and the paired median are reported beside "
            "the trimmed mean, with the count of pairs that moved at all",
        },
        exclusions=exclusions,
        provenance_ref=provenance_ref,
    )


__all__ = ["ALL_ZERO_REASON", "trimmed_mean_difference", "wilcoxon"]
