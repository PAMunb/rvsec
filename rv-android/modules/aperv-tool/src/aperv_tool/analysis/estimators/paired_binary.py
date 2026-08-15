"""Exact McNemar, and the floor below which its non-rejection means nothing.

A paired binary comparison reduces to the two off-diagonal cells of the 2x2 table
of agreements: ``b`` units the first arm caught and the second did not, ``c`` the
reverse. Everything else — how many units both arms caught, how many neither —
carries no information about the difference, which is why the exact test
conditions on ``n_disc = b + c`` and asks whether ``b`` looks like a fair coin.

The module exists in this shape because of a specific misreading. A discordance
count was once reported on its own, with neither ``b``, ``c`` nor a direction
beside it, and a reader could not tell which arm the discordance favoured, let
alone whether the comparison had any chance of resolving. Both halves of that are
fixed structurally here: the envelope always carries ``b``, ``c``, ``n_disc``, the
direction and ``p`` together, and it always carries the **power floor** beside
them (INV-CAN-15).

The floor is the arithmetic that a small paired study most often gets wrong. The
smallest two-sided p the exact test can produce on ``n`` discordant pairs is
``2 * 0.5**n`` — the whole of the discordance falling on one side. At alpha =
0.025 that is below alpha only from ``n = 7`` upward, so a comparison with six
discordant pairs *cannot* reject however lopsided it is. Reporting "no
significant difference" there describes the design, not the arms, and the
envelope says so in as many words.

Stratification pools rather than combines-with-weights, and that is exact rather
than approximate: under the conditional null every stratum's discordance is a
fair coin, so the sum of the strata's ``b`` counts is Binomial(sum of
``n_disc``, 0.5) and the pooled exact test *is* the exact stratified test. What
strata buy is visibility — the per-stratum ``b`` and ``c`` ride along in the
envelope, so a pooled null that is really two cancelling halves is legible.
"""

from __future__ import annotations

from typing import Optional, Union

import numpy as np
import pandas as pd
from scipy.stats import binomtest

from aperv_tool.analysis.envelope import Denominator, Envelope
from aperv_tool.analysis.estimators.resampling import PairInput, align_pairs

#: What the envelope says beside a result that did not reject and could not have.
#: Kept as a constant because it is the sentence the reporting rule exists to
#: force onto the page, and a sentence retyped per caller is a sentence that
#: eventually goes missing.
BELOW_FLOOR_NOTE = (
    "below the power floor, non-rejection is construction, not evidence: "
    "no assignment of the discordant pairs could have reached this alpha"
)

#: How far the floor search runs before giving up. A floor beyond this needs an
#: alpha under 2^-200, which is not a level anyone declared on purpose.
_FLOOR_SEARCH_LIMIT = 200


def power_floor(alpha: float) -> int:
    """Smallest discordance count at which the exact test can reject at ``alpha``.

    The most extreme table on ``n`` discordant pairs puts all of them on one
    side, giving a two-sided p of ``2 * 0.5**n`` — this is ``binomtest(0, n, 0.5,
    alternative="two-sided").pvalue``, evaluated in closed form because it is
    called for every result and the identity is exact.

    Args:
        alpha: The level the caller declared.

    Returns:
        The smallest ``n_disc`` whose best case reaches ``alpha``. For the
        two-sided 0.05 family split across a pair of comparisons — alpha =
        0.025 — the answer is 7.

    Raises:
        ValueError: ``alpha`` is outside ``(0, 1)``, or so small that no
            reachable discordance count clears it.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must lie in (0, 1), got {alpha}")
    for n_disc in range(1, _FLOOR_SEARCH_LIMIT + 1):
        if 2.0 * 0.5**n_disc <= alpha:
            return n_disc
    raise ValueError(
        f"no discordance count under {_FLOOR_SEARCH_LIMIT} reaches {alpha}"
    )


def _as_indicator(series: pd.Series, side: str) -> np.ndarray:
    """Cast a cleaned pair side to booleans, refusing anything not 0/1.

    Args:
        series: One side of the aligned pairs, already free of missing values.
        side: Which side, for the error message.

    Returns:
        The values as a boolean array.

    Raises:
        ValueError: A value is neither 0 nor 1 — a count or a rate reaching a
            binary estimator is a builder defect, and silently thresholding it
            here would hide the defect behind a plausible number.
    """
    values = series.to_numpy(dtype=float)
    if not np.all(np.isin(values, (0.0, 1.0))):
        offending = sorted({float(v) for v in values if v not in (0.0, 1.0)})[:5]
        raise ValueError(f"{side} side is not binary; saw {offending}")
    return values.astype(bool)


def mcnemar_exact(
    a: PairInput,
    b: PairInput,
    *,
    alpha: float,
    strata: Optional[pd.Series] = None,
    provenance_ref: str = "",
) -> Envelope:
    """Exact McNemar test over the discordant pairs, reported with its floor.

    Args:
        a: First arm's binary outcome, one value per unit. A ``Series`` pairs by
            index and names its exclusions.
        b: Second arm's binary outcome, aligned with ``a``.
        alpha: The level the caller declared. Used for the power floor and for
            the coverage of the conditional interval; it is not a threshold this
            function applies to anything.
        strata: Optional per-unit stratum label. Changes no p-value — the pooled
            exact test is already the exact stratified one — and adds the
            per-stratum ``b``/``c`` counts to the envelope.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        An envelope whose estimate carries ``b``, ``c``, ``n_disc``, both
        concordant cells, ``direction``, ``p_two_sided``, ``power_floor_n_disc``
        and ``below_floor``, and whose ``ci`` is the exact (Clopper-Pearson)
        interval for the share of discordance favouring the first arm — ``None``
        when there is no discordance to bound.

    Raises:
        ValueError: Either side is not binary, or ``alpha`` is outside (0, 1).
    """
    left, right, exclusions = align_pairs(a, b)
    first = _as_indicator(left, "first")
    second = _as_indicator(right, "second")

    b_count = int(np.sum(first & ~second))
    c_count = int(np.sum(~first & second))
    n_disc = b_count + c_count
    both = int(np.sum(first & second))
    neither = int(np.sum(~first & ~second))

    floor = power_floor(alpha)
    below_floor = n_disc < floor

    if n_disc == 0:
        p_two_sided = 1.0
        interval: Optional[tuple[float, float]] = None
    else:
        result = binomtest(b_count, n_disc, 0.5, alternative="two-sided")
        p_two_sided = float(result.pvalue)
        bounds = result.proportion_ci(confidence_level=1.0 - alpha, method="exact")
        interval = (float(bounds.low), float(bounds.high))

    if b_count > c_count:
        direction = "first>second"
    elif c_count > b_count:
        direction = "second>first"
    else:
        direction = "none"

    estimate: dict[str, Union[float, int, str, bool]] = {
        "b": b_count,
        "c": c_count,
        "n_disc": n_disc,
        "n_both": both,
        "n_neither": neither,
        "direction": direction,
        "p_two_sided": p_two_sided,
        "alpha": float(alpha),
        "power_floor_n_disc": floor,
        "below_floor": bool(below_floor),
    }

    convention: dict[str, str] = {
        "test": "exact McNemar: binomial(n_disc, 0.5) over the discordant pairs",
        "direction": "'first>second' means the first arm holds the larger "
        "off-diagonal cell",
        "ci": "Clopper-Pearson interval for b / n_disc at 1 - alpha; None when "
        "n_disc is 0",
        "power_floor": f"smallest n_disc able to reach alpha={alpha} is {floor}",
        "below_floor": BELOW_FLOOR_NOTE if below_floor else "n_disc reaches the floor",
    }

    if strata is not None:
        labels = strata.reindex(left.index) if isinstance(strata, pd.Series) else None
        if labels is None:
            raise ValueError("strata must be a Series aligned with the pairs")
        for stratum in sorted({str(value) for value in labels.dropna()}):
            mask = (labels.astype(str) == stratum).to_numpy()
            estimate[f"b__{stratum}"] = int(np.sum(first[mask] & ~second[mask]))
            estimate[f"c__{stratum}"] = int(np.sum(~first[mask] & second[mask]))
        estimate["n_strata"] = len({str(value) for value in labels.dropna()})
        convention["strata"] = (
            "pooled: under the conditional null every stratum is a fair coin, so "
            "the pooled exact test is the exact stratified test; the per-stratum "
            "cells are reported so a cancelling split stays visible"
        )

    reachable = len(left) + len(exclusions)
    return Envelope(
        estimand="mcnemar_exact",
        n=int(len(left)),
        denominator=Denominator(
            reachable=reachable,
            analysed=int(len(left)),
            reason="incomplete pairs dropped listwise" if exclusions else "",
        ),
        estimate=estimate,
        ci=interval,
        convention=convention,
        exclusions=exclusions,
        provenance_ref=provenance_ref,
    )


__all__ = ["BELOW_FLOOR_NOTE", "mcnemar_exact", "power_floor"]
