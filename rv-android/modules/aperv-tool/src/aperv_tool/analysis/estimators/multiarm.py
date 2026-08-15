"""Ranking several arms at once, descriptively and never as a verdict.

Extracted from the calibration campaign's ``multiarm_stats.py``, where it served
a screening gate: the Friedman omnibus over all arms, the per-arm mean rank, the
Holm-adjusted pairwise Wilcoxon table, and the matched-pairs rank-biserial
effect size beside every pair. The campaign's own invariant is carried over with
it and is the reason the module says so twice: **screening selects candidates,
it never declares a winner by a p-value**. Every number here is a decision input.

Two properties of the arithmetic are worth stating because they are easy to
break in a reimplementation:

- **Complete cases only.** Friedman is a repeated-measures test and needs every
  arm present on every unit. Dropping a unit missing one arm changes the sample
  for *all* the pairwise tests too, so the drop happens once, up front, and the
  surviving count is reported.
- **Ranks are averaged over ties.** A block of tied values shares the mean of the
  ranks it spans, which is what keeps the mean ranks comparable when an outcome
  is coarse — and the outcomes this is used on are coarse, with unit values
  repeating across arms.

The per-arm summary carries the raw arithmetic mean beside the trimmed mean, for
the same reason the paired estimators carry the raw mean beside the trimmed one:
an effect that lives entirely in the tail the trim discards is invisible in the
trimmed number alone, and that failure mode has already been recorded once in
this project.

Holm's arithmetic is not reimplemented here — it is ``multiplicity.holm``, so the
adjustment a table shows is the same code the multiplicity envelopes report.
"""

from __future__ import annotations

from itertools import combinations
from typing import Sequence, Union

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, trim_mean
from scipy.stats import wilcoxon as _scipy_wilcoxon

from aperv_tool.analysis.envelope import Denominator, Envelope, Exclusion
from aperv_tool.analysis.estimators.multiplicity import holm

#: Why the omnibus is undefined. Friedman needs three arms to rank and enough
#: complete units for the chi-square approximation to mean anything.
MIN_ARMS = 3
MIN_COMPLETE_UNITS = 3


def average_ranks(values: np.ndarray) -> np.ndarray:
    """Average ranks of one vector, ties sharing the mean of the ranks they span.

    Each distinct value occupies a contiguous block of 1-based ranks in sorted
    order, so its average rank is ``start + (count + 1) / 2``.

    Args:
        values: The vector to rank. Larger values receive larger ranks.

    Returns:
        The ranks, aligned with the input.
    """
    _, inverse, counts = np.unique(values, return_inverse=True, return_counts=True)
    cumulative = np.cumsum(counts)
    start = cumulative - counts
    average = (start + cumulative + 1) / 2.0
    return np.asarray(average)[np.asarray(inverse).ravel()]


def rank_biserial(a: np.ndarray, b: np.ndarray) -> float:
    """Matched-pairs rank-biserial correlation of ``a - b``.

    ``r = (W+ - W-) / (W+ + W-)`` over the signed ranks of the non-zero paired
    differences. It reads directly: ``+1`` means the first arm exceeds the second
    on every unit that moved, ``-1`` the reverse, ``0`` no directional tendency.
    Zero differences are dropped, as the signed-rank test drops them.

    Args:
        a: First arm's values.
        b: Second arm's values, paired element-wise.

    Returns:
        The correlation, or ``0.0`` when no pair moved.
    """
    differences = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    differences = differences[differences != 0]
    if differences.size == 0:
        return 0.0
    ranks = average_ranks(np.abs(differences))
    positive = float(ranks[differences > 0].sum())
    negative = float(ranks[differences < 0].sum())
    total = positive + negative
    if total == 0:
        return 0.0
    return (positive - negative) / total


def friedman_holm(
    frame: pd.DataFrame,
    *,
    arms: Sequence[str],
    trim: float,
    provenance_ref: str = "",
) -> Envelope:
    """Friedman omnibus, mean ranks, Holm-adjusted pairwise Wilcoxon, effect sizes.

    Args:
        frame: One row per unit, one column per arm, indexed by the unit id so a
            dropped unit can be named.
        arms: The arm columns to rank, in the order the caller wants them
            reported.
        trim: Fraction cut from each tail of the per-arm trimmed mean. Required
            without a default because it changes the summary that is printed
            beside the ranks.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        An envelope carrying ``available``, the omnibus ``statistic`` and
        ``p_value``, ``mean_rank__<arm>``, ``raw_mean__<arm>``,
        ``trimmed_mean__<arm>``, ``median__<arm>``, and per pair
        ``p_raw__<a>|<b>``, ``p_holm__<a>|<b>`` and ``rank_biserial__<a>|<b>``.
        When the omnibus is undefined the envelope carries ``available=False``
        and the reason rather than raising.

    Raises:
        KeyError: An arm column is absent from the frame.
    """
    labels = [str(arm) for arm in arms]
    missing = [label for label in labels if label not in frame.columns]
    if missing:
        raise KeyError(f"arm columns absent from the frame: {missing}")

    numeric = frame[labels].astype(float)
    complete = numeric.notna().all(axis=1)
    exclusions = tuple(
        Exclusion(identity=str(label), reason="incomplete across the arms")
        for label in numeric.index[~complete]
    )
    kept = numeric[complete]
    n_complete = int(len(kept))

    estimate: dict[str, Union[float, int, str, bool]] = {
        "n_complete": n_complete,
        "n_arms": len(labels),
        "trim": float(trim),
    }
    convention = {
        "scope": "descriptive: the ranking and the adjusted p-values are decision "
        "inputs, never a verdict on an arm",
        "cases": "complete cases only — a unit missing any arm is dropped once, "
        "for the omnibus and for every pairwise test alike",
        "ranks": "averaged over ties",
        "summary": "the raw arithmetic mean is reported beside the trimmed mean so "
        "an effect living in the discarded tail stays visible",
        "multiplicity": "Holm over all pairs, from the multiplicity module",
    }

    for label in labels:
        column = kept[label].to_numpy(dtype=float)
        estimate[f"raw_mean__{label}"] = (
            float(np.mean(column)) if column.size else float("nan")
        )
        estimate[f"trimmed_mean__{label}"] = (
            float(trim_mean(column, trim)) if column.size else float("nan")
        )
        estimate[f"median__{label}"] = (
            float(np.median(column)) if column.size else float("nan")
        )

    if len(labels) < MIN_ARMS or n_complete < MIN_COMPLETE_UNITS:
        estimate.update(
            {
                "available": False,
                "reason": f"{len(labels)} arms and {n_complete} complete units; "
                f"the omnibus needs {MIN_ARMS} arms and {MIN_COMPLETE_UNITS} units",
                "statistic": float("nan"),
                "p_value": float("nan"),
            }
        )
        return Envelope(
            estimand="friedman_holm",
            n=n_complete,
            denominator=Denominator(
                reachable=int(len(frame)),
                analysed=n_complete,
                reason="incomplete units dropped" if exclusions else "",
            ),
            estimate=estimate,
            ci=None,
            convention=convention,
            exclusions=exclusions,
            provenance_ref=provenance_ref,
        )

    matrix = kept[labels].to_numpy(dtype=float).T  # arms x units
    statistic, p_value = friedmanchisquare(*[matrix[i] for i in range(len(labels))])

    ranks = np.vstack(
        [average_ranks(matrix[:, unit]) for unit in range(matrix.shape[1])]
    ).T
    for index, label in enumerate(labels):
        estimate[f"mean_rank__{label}"] = float(ranks[index].mean())

    pairs = list(combinations(range(len(labels)), 2))
    raw_p: list[float] = []
    for left, right in pairs:
        differences = matrix[left] - matrix[right]
        if np.all(differences == 0):
            raw_p.append(1.0)
            continue
        try:
            raw_p.append(
                float(
                    _scipy_wilcoxon(
                        matrix[left], matrix[right], zero_method="wilcox"
                    ).pvalue
                )
            )
        except ValueError:
            # scipy refuses a comparison it cannot rank; a p-value of 1 records
            # "nothing to test here" without dropping the pair from the family.
            raw_p.append(1.0)
    adjusted = holm(raw_p)

    for (left, right), p_value_raw, p_value_adj in zip(pairs, raw_p, adjusted):
        key = f"{labels[left]}|{labels[right]}"
        estimate[f"p_raw__{key}"] = float(p_value_raw)
        estimate[f"p_holm__{key}"] = float(p_value_adj)
        estimate[f"rank_biserial__{key}"] = rank_biserial(matrix[left], matrix[right])

    estimate.update(
        {
            "available": True,
            "reason": "",
            "statistic": float(statistic),
            "p_value": float(p_value),
            "n_pairs": len(pairs),
        }
    )

    return Envelope(
        estimand="friedman_holm",
        n=n_complete,
        denominator=Denominator(
            reachable=int(len(frame)),
            analysed=n_complete,
            reason="incomplete units dropped" if exclusions else "",
        ),
        estimate=estimate,
        ci=None,
        convention=convention,
        exclusions=exclusions,
        provenance_ref=provenance_ref,
    )


__all__ = ["average_ranks", "friedman_holm", "rank_biserial"]
