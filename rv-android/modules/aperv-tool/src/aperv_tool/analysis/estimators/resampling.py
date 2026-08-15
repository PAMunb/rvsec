"""The resampling kernel: the campaign's pinned estimand, and pair hygiene.

Two of the three functions here are an extraction rather than a design. The
calibration campaign pinned its estimand as **the difference of 10 % trimmed
means, recomputed on every resample** — never the trimmed mean of the
differences, never the plain mean — and resampled applications with replacement
under a fixed seed so the interval is deterministic. That choice lives in
``experimento-cal/scripts/stats_utils.py`` and is duplicated byte for byte in
``experimento-rearch-aperv/scripts/``; ``diff_of_trimmed_means`` and
``paired_bootstrap_ci`` below carry it unchanged, defaults included
(``B=10_000``, ``seed=42``, ``trim=0.10``), so a number recomputed here is the
number those campaigns reported. The campaign copies stay where they are: they
are the frozen proof this extraction is faithful to, not a duplicate to delete.

Those two return plain values, not envelopes, and that is deliberate. They are
the arithmetic kernel; the seat that reports a trimmed-mean difference for
publication is ``paired_continuous.trimmed_mean_difference``, which wraps this
interval together with the raw mean, the paired median and the count of non-zero
pairs that INV-CAN-15 requires beside it. Wrapping the kernel itself in an
envelope would put the same number in two reportable places and invite the
version without its companions to be the one that gets quoted.

``align_pairs`` sits here for a reason that is written into the extracted
docstring: ``paired_bootstrap_ci`` asserts equal shapes and does not handle
missing values — "broken pairs must be removed BEFORE (listwise) by the caller".
The cleaner belongs beside the precondition it satisfies, and it returns the
dropped units as ``Exclusion`` records so the loss reaches the envelope instead
of a log line.

``permutation`` is the one estimator in the module and does return an envelope.
It exists for statistics with no tractable null: the label assignment is shuffled
under a fixed seed and the observed statistic is placed in that distribution.
Its p-value uses the add-one correction, so an unreached tail reports
``1/(n_perm+1)`` rather than the impossible ``0``.
"""

from __future__ import annotations

from typing import Callable, Sequence, Union

import numpy as np
import pandas as pd
from scipy.stats import trim_mean

from aperv_tool.analysis.envelope import Denominator, Envelope, Exclusion

#: Anything a paired estimator accepts on either side of a pair. A ``Series``
#: carries the unit labels that make an exclusion nameable; a bare array does
#: not, and its exclusions are named by position.
PairInput = Union[pd.Series, Sequence[float], np.ndarray]


def diff_of_trimmed_means(a: np.ndarray, b: np.ndarray, trim: float = 0.10) -> float:
    """Difference of the two samples' trimmed means.

    Carried unchanged from the calibration campaign's kernel. The order matters
    and is not symmetric in reporting: the value is ``a - b``, so the sign is
    read as "how much the first arm exceeds the second".

    Args:
        a: First sample.
        b: Second sample, paired element-wise with ``a``.
        trim: Fraction cut from *each* tail before averaging.

    Returns:
        ``trim_mean(a, trim) - trim_mean(b, trim)``.
    """
    return float(trim_mean(a, trim) - trim_mean(b, trim))


def paired_bootstrap_ci(
    a: PairInput,
    b: PairInput,
    *,
    B: int = 10_000,
    seed: int = 42,
    trim: float = 0.10,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Percentile interval of the pinned estimand, resampling units with replacement.

    The unit of resampling is the pair, not the observation: one index vector is
    drawn per resample and used on both sides, which is what keeps the pairing
    intact. The estimand is recomputed from scratch on every resample — trimming
    the resampled samples, then differencing — because trimming and differencing
    do not commute and the campaign pinned this order.

    Broken pairs must already be gone; see ``align_pairs``.

    Args:
        a: First sample, one value per unit.
        b: Second sample, aligned with ``a``.
        B: Number of resamples. The campaign's floor is 10,000.
        seed: Seed of the generator, so the interval is reproducible.
        trim: Fraction cut from each tail.
        alpha: One minus the interval's coverage.

    Returns:
        ``(point, lo, hi)`` — the estimand on the observed pairs and the
        percentile bounds over the resamples.

    Raises:
        AssertionError: The two samples are not one-dimensional and equal-length,
            which means the listwise cleaning was skipped.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    assert a.shape == b.shape and a.ndim == 1
    n = len(a)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(B, n))
    stats = np.array([diff_of_trimmed_means(a[i], b[i], trim) for i in idx])
    lo, hi = np.percentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return diff_of_trimmed_means(a, b, trim), float(lo), float(hi)


def align_pairs(
    a: PairInput, b: PairInput
) -> tuple[pd.Series, pd.Series, tuple[Exclusion, ...]]:
    """Drop incomplete pairs listwise and name every unit that left.

    Alignment is by index when both sides are ``Series``, so two frames built by
    different builders pair on the application id rather than on row order — the
    failure mode where a shorter arm silently shifts every pair by one. A unit
    present on one side only, or missing on either, is dropped and reported.

    Both sides come back as ``float64``: a boolean outcome survives the cast
    exactly, and the alternative — preserving ``bool`` — turns into ``object``
    the moment alignment introduces a missing value.

    Args:
        a: First sample.
        b: Second sample.

    Returns:
        ``(a_clean, b_clean, exclusions)`` with a shared index and no missing
        values, and one ``Exclusion`` per dropped unit.
    """
    left = (
        a.astype(float)
        if isinstance(a, pd.Series)
        else pd.Series(np.asarray(a, dtype=float))
    )
    right = (
        b.astype(float)
        if isinstance(b, pd.Series)
        else pd.Series(np.asarray(b, dtype=float))
    )
    if not left.index.equals(right.index):
        left, right = left.align(right)
    keep = left.notna() & right.notna()
    exclusions = tuple(
        Exclusion(identity=str(label), reason="incomplete pair")
        for label in left.index[~keep]
    )
    return left[keep], right[keep], exclusions


def permutation(
    values: PairInput,
    groups: Sequence[str],
    *,
    statistic: Callable[[np.ndarray, np.ndarray], float],
    n_perm: int,
    seed: int,
    provenance_ref: str = "",
) -> Envelope:
    """Two-sample permutation test of an arbitrary statistic.

    The null is exchangeability of the group labels, so the labels — not the
    values — are shuffled. Any statistic of the two value vectors is admissible,
    which is the point: this is the fallback for a quantity whose sampling
    distribution nobody wants to derive.

    The p-value is ``(1 + #{|perm| >= |obs|}) / (n_perm + 1)``. The add-one
    correction is not cosmetic: without it a statistic no resample reaches
    reports ``p = 0``, a claim no finite number of shuffles can support.

    Args:
        values: The observations, in the order of ``groups``.
        groups: Exactly two distinct labels, one per observation.
        statistic: Called as ``statistic(values_of_first, values_of_second)``,
            with the groups in sorted label order so the sign is reproducible.
        n_perm: Number of label shuffles.
        seed: Seed of the generator.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        An envelope whose estimate carries the observed statistic, the p-value,
        the two group sizes and the statistic's name.

    Raises:
        ValueError: ``groups`` does not hold exactly two distinct labels, or its
            length differs from ``values``.
    """
    observations = np.asarray(values, dtype=float)
    labels = np.asarray(list(groups), dtype=object)
    if labels.shape[0] != observations.shape[0]:
        raise ValueError(
            f"{observations.shape[0]} values against {labels.shape[0]} labels"
        )
    distinct = sorted({str(label) for label in labels})
    if len(distinct) != 2:
        raise ValueError(f"a two-sample permutation needs two labels, got {distinct}")

    first_mask = np.array([str(label) == distinct[0] for label in labels])
    observed = float(statistic(observations[first_mask], observations[~first_mask]))

    rng = np.random.default_rng(seed)
    at_least_as_extreme = 0
    for _ in range(n_perm):
        shuffled = rng.permutation(first_mask)
        candidate = float(statistic(observations[shuffled], observations[~shuffled]))
        if abs(candidate) >= abs(observed):
            at_least_as_extreme += 1
    p_value = (1 + at_least_as_extreme) / (n_perm + 1)

    name = getattr(statistic, "__name__", "statistic")
    return Envelope(
        estimand=f"permutation_{name}",
        n=int(observations.shape[0]),
        denominator=Denominator(
            reachable=int(observations.shape[0]), analysed=int(observations.shape[0])
        ),
        estimate={
            "statistic": observed,
            "p_two_sided": float(p_value),
            "n_first": int(first_mask.sum()),
            "n_second": int((~first_mask).sum()),
            "first_label": distinct[0],
            "second_label": distinct[1],
            "n_perm": int(n_perm),
        },
        ci=None,
        convention={
            "test": "two-sample label permutation, two-sided on |statistic|",
            "p_value": "add-one corrected; the smallest reportable p is "
            f"{1 / (n_perm + 1):.3g}",
            "seed": str(seed),
            "statistic": name,
        },
        exclusions=(),
        provenance_ref=provenance_ref,
    )
