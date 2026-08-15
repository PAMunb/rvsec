"""Adjustment for multiple testing, over a family the caller has to name.

Holm and Benjamini-Hochberg are three lines of arithmetic each. The part worth a
module is the family: an adjusted p-value means nothing without the set it was
adjusted over, and that set is a decision about what the study is claiming, not a
property of the numbers handed in. Two comparisons adjusted as one family and the
same two adjusted as members of a family of twelve give different answers, and
neither the p-values nor the method reveal which happened.

So ``family`` is a required, freeze-item argument: omitting it raises
``FreezeItemUnset`` rather than defaulting to "whatever was passed in this call".
The envelope then carries the family's name and ``m`` beside every adjusted
value, so a table of adjusted p-values states what it was adjusted against.

Both procedures return **monotone** adjusted values, enforced by the running
maximum in Holm's step-down and the running minimum in BH's step-up. Without it a
larger raw p-value can come back with a smaller adjusted one, which reverses the
ordering the reader is looking at.

Rejection is not decided here. An adjusted p-value compared against a level is a
decision, and decisions have one seat: ``decision``.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence, Union

from aperv_tool.analysis.corpus import FreezeItemUnset
from aperv_tool.analysis.envelope import Denominator, Envelope

#: Sentinel for a freeze item the caller did not supply. Typed as ``Any`` so the
#: parameter keeps its real annotation while still defaulting to a value that is
#: not a legal one.
_UNSET: Any = object()

#: The adjustment procedures this module implements.
METHODS = ("holm", "fdr_bh")


def holm(p_values: Sequence[float]) -> list[float]:
    """Holm's step-down adjustment, in the input's order.

    Sorted ascending, the i-th smallest raw value is multiplied by ``m - i`` and
    capped at 1; a running maximum then enforces monotonicity, so an adjusted
    value never falls below one belonging to a smaller raw p-value.

    Args:
        p_values: Raw p-values of one family.

    Returns:
        Adjusted values aligned with the input.
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda k: p_values[k])
    adjusted = [0.0] * m
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * float(p_values[index])))
        adjusted[index] = running
    return adjusted


def fdr_bh(p_values: Sequence[float]) -> list[float]:
    """Benjamini-Hochberg adjustment controlling the false discovery rate.

    Walked from the largest raw value down: the i-th largest is scaled by
    ``m / rank`` and a running minimum enforces monotonicity in the other
    direction from Holm's. BH controls the expected share of false positives
    among the rejections rather than the chance of any, so it is the weaker
    guarantee and the caller declares which one the family gets.

    Args:
        p_values: Raw p-values of one family.

    Returns:
        Adjusted values aligned with the input.
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda k: p_values[k])
    adjusted = [0.0] * m
    running = 1.0
    for position in range(m - 1, -1, -1):
        index = order[position]
        running = min(running, min(1.0, m / (position + 1) * float(p_values[index])))
        adjusted[index] = running
    return adjusted


def adjust(
    p: Union[Mapping[str, float], Sequence[float]],
    *,
    family: str = _UNSET,
    method: str,
    provenance_ref: str = "",
) -> Envelope:
    """Adjust a family of p-values and report what the family was.

    Args:
        p: The raw p-values. A mapping keeps each hypothesis's name in the
            envelope; a sequence is named by position, which is enough for a
            caller that keeps its own ordering but loses the join.
        family: The declared family. A freeze item — the same p-values adjusted
            over a different family give different answers, so the code must not
            pick one.
        method: ``"holm"`` or ``"fdr_bh"``.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        An envelope carrying ``family``, ``method``, ``m`` and, per hypothesis,
        ``p_raw__<name>`` and ``p_adj__<name>``.

    Raises:
        FreezeItemUnset: ``family`` was not supplied.
        ValueError: ``method`` is not one of ``METHODS``, the family is empty, or
            a value lies outside [0, 1].
    """
    if family is _UNSET:
        raise FreezeItemUnset(
            "family: the set a p-value is adjusted over is a declaration about "
            "the study, and adjusting over 'whatever was passed' is not one"
        )
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}, got {method!r}")

    if isinstance(p, Mapping):
        names = list(p)
        raw = [float(p[name]) for name in names]
    else:
        raw = [float(value) for value in p]
        names = [str(index) for index in range(len(raw))]
    if not raw:
        raise ValueError("an empty family has nothing to adjust")
    outside = [value for value in raw if not 0.0 <= value <= 1.0]
    if outside:
        raise ValueError(f"p-values outside [0, 1]: {outside[:5]}")

    adjusted = holm(raw) if method == "holm" else fdr_bh(raw)

    estimate: dict[str, Union[float, int, str, bool]] = {
        "family": family,
        "method": method,
        "m": len(raw),
    }
    for name, value, value_adj in zip(names, raw, adjusted):
        estimate[f"p_raw__{name}"] = float(value)
        estimate[f"p_adj__{name}"] = float(value_adj)

    return Envelope(
        estimand=f"multiplicity_{method}",
        n=len(raw),
        denominator=Denominator(reachable=len(raw), analysed=len(raw)),
        estimate=estimate,
        ci=None,
        convention={
            "family": family,
            "method": method,
            "control": (
                "family-wise error rate" if method == "holm" else "false discovery rate"
            ),
            "monotonicity": "enforced, so the adjusted ordering matches the raw one",
            "rejection": "not decided here; an adjusted p-value compared against a "
            "level is a decision and belongs to the decision module",
        },
        exclusions=(),
        provenance_ref=provenance_ref,
    )


__all__ = ["METHODS", "adjust", "fdr_bh", "holm"]
