"""How much of an outcome's variation is between units rather than between replicas.

The intraclass correlation answers the question a replicated campaign is really
asking: is the spread in this column the applications differing from each other,
or the same application answering differently each time it is run? A high value
says replicas agree and the unit is the effective sample size; a low one says a
single replica is close to noise.

The module's contract is that it **says why it degenerated**, because the
degenerate cases are common and each of them produces a number that looks like an
answer:

- a saturated binary outcome — every unit at 1, or every unit at 0 — has no
  variance at all to partition, and the ratio is 0/0. Reporting ``0.0`` there
  would read as "replicas disagree completely", the opposite of the truth;
- an outcome that is constant *within* every unit but varies between them gives
  ``1.0`` legitimately, and it is worth distinguishing from a rounded 1.0;
- the between-unit mean square below the within-unit one gives a **negative**
  variance component. The convention is to clip at zero, and the clip is
  recorded, since an unrecorded clip is an estimate quietly replaced by a bound;
- a campaign with one replica per unit has nothing to compare, and the estimator
  is not applicable rather than zero. The final campaign runs at one replica per
  cell by design, so this branch is the expected one there and must not read as a
  failure.

The estimator is the one-way random-effects ICC computed from the analysis of
variance, with the unbalanced correction ``k0`` so unequal replica counts do not
bias it. It is a variance decomposition, not a test: no p-value is produced,
because the question is how large the components are, not whether they are zero.
"""

from __future__ import annotations

from typing import Union

import numpy as np
import pandas as pd

from aperv_tool.analysis.envelope import Denominator, Envelope

#: The reasons the estimate is not a partition of variance. Callers branch on
#: these strings, so they are constants rather than phrasings.
CONSTANT_OUTCOME = "outcome is constant: there is no variance to partition"
NO_REPLICATION = "no unit has more than one replica"
TOO_FEW_UNITS = "fewer than two units"
NO_WITHIN_VARIANCE = "no within-unit variance: replicas agree exactly"
CLIPPED_NEGATIVE = "negative variance component clipped to zero"


def icc(
    frame: pd.DataFrame,
    *,
    unit: str,
    replica: str,
    value: str,
    provenance_ref: str = "",
) -> Envelope:
    """One-way random-effects intraclass correlation, with its degeneracy named.

    Args:
        frame: Long frame with one row per (unit, replica) observation.
        unit: Column holding the unit id — the application, in every current
            campaign.
        replica: Column holding the replica index. Used to count replicas per
            unit and to reject a frame in which one unit appears twice under the
            same replica, which would inflate the within-unit component.
        value: Column holding the measurement.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        An envelope carrying ``icc``, ``ms_between``, ``ms_within``, ``units``,
        ``replicas_mean``, ``degenerate`` and ``degenerate_reason``.

    Raises:
        KeyError: A named column is absent.
        ValueError: A (unit, replica) pair appears more than once.
    """
    for column in (unit, replica, value):
        if column not in frame.columns:
            raise KeyError(f"column {column!r} is not in the frame")

    data = frame[[unit, replica, value]].dropna()
    duplicated = data.duplicated(subset=[unit, replica]).sum()
    if duplicated:
        raise ValueError(
            f"{duplicated} repeated (unit, replica) pairs: the replica index does "
            "not identify an observation"
        )

    groups = data.groupby(unit)[value]
    counts = groups.count().to_numpy(dtype=float)
    means = groups.mean().to_numpy(dtype=float)
    n_units = int(counts.size)
    n_total = int(counts.sum())

    estimate: dict[str, Union[float, int, str, bool]] = {
        "units": n_units,
        "observations": n_total,
        "replicas_mean": float(counts.mean()) if n_units else float("nan"),
    }
    convention = {
        "estimator": "one-way random-effects ICC from the analysis of variance, "
        "with the k0 correction for unequal replica counts",
        "reporting": "a degenerate result is labelled with its reason; it is never "
        "returned as a bare 0.0 or 1.0",
        "scope": "a variance decomposition, not a test — no p-value is produced",
    }

    def degenerate(reason: str, point: float) -> Envelope:
        estimate.update(
            {
                "icc": point,
                "ms_between": float("nan"),
                "ms_within": float("nan"),
                "degenerate": True,
                "degenerate_reason": reason,
            }
        )
        return Envelope(
            estimand="icc_one_way",
            n=n_total,
            denominator=Denominator(reachable=int(len(frame)), analysed=n_total),
            estimate=estimate,
            ci=None,
            convention=convention,
            exclusions=(),
            provenance_ref=provenance_ref,
        )

    if n_units < 2:
        return degenerate(TOO_FEW_UNITS, float("nan"))
    if counts.max() < 2:
        return degenerate(NO_REPLICATION, float("nan"))

    grand_mean = float(data[value].mean())
    ss_between = float(np.sum(counts * (means - grand_mean) ** 2))
    # The within sum of squares as the residual of the total decomposition; the
    # identity is exact and avoids a second pass over the groups.
    ss_total = float(np.sum((data[value].to_numpy(dtype=float) - grand_mean) ** 2))
    # Clamped because the residual of two large, nearly equal sums can land a few
    # units of last place below zero, and a negative sum of squares would travel
    # into the ratio as a plausible-looking number.
    ss_within = max(ss_total - ss_between, 0.0)
    df_between = n_units - 1
    df_within = n_total - n_units
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within if df_within > 0 else 0.0

    estimate["ms_between"] = float(ms_between)
    estimate["ms_within"] = float(ms_within)

    if ms_between == 0.0 and ms_within == 0.0:
        return degenerate(CONSTANT_OUTCOME, float("nan"))
    if ms_within == 0.0:
        estimate.update(
            {
                "icc": 1.0,
                "degenerate": True,
                "degenerate_reason": NO_WITHIN_VARIANCE,
            }
        )
        return Envelope(
            estimand="icc_one_way",
            n=n_total,
            denominator=Denominator(reachable=int(len(frame)), analysed=n_total),
            estimate=estimate,
            ci=None,
            convention=convention,
            exclusions=(),
            provenance_ref=provenance_ref,
        )

    # k0 is the effective replica count under unequal group sizes; it reduces to
    # the common count when the design is balanced.
    k0 = (n_total - float(np.sum(counts**2)) / n_total) / df_between
    point = (ms_between - ms_within) / (ms_between + (k0 - 1.0) * ms_within)

    clipped = point < 0.0
    estimate.update(
        {
            "icc": 0.0 if clipped else float(point),
            "icc_uncorrected": float(point),
            "k0": float(k0),
            "degenerate": bool(clipped),
            "degenerate_reason": CLIPPED_NEGATIVE if clipped else "",
        }
    )

    return Envelope(
        estimand="icc_one_way",
        n=n_total,
        denominator=Denominator(reachable=int(len(frame)), analysed=n_total),
        estimate=estimate,
        ci=None,
        convention=convention,
        exclusions=(),
        provenance_ref=provenance_ref,
    )


__all__ = [
    "CLIPPED_NEGATIVE",
    "CONSTANT_OUTCOME",
    "NO_REPLICATION",
    "NO_WITHIN_VARIANCE",
    "TOO_FEW_UNITS",
    "icc",
]
