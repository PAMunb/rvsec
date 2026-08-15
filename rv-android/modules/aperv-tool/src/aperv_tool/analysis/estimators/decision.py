"""Turning an interval into a verdict, against a margin the author supplied.

An interval says where the effect plausibly lies. It does not say whether that is
enough, and nothing in the data can: "enough" is a threshold about the domain —
how much coverage a tool has to gain before the gain matters — and it is a
pre-registration freeze item. This module is where the two meet, and its only
real rule is that it will not invent the threshold.

``margin`` therefore has no default and raises ``FreezeItemUnset`` when omitted.
A default here would be the most expensive kind of silent decision: every table
downstream would carry verdicts, each one defensible-looking, none of them the
author's.

The four verdicts are deliberately coarse, because an interval supports no finer
statement:

- ``above_margin`` — the whole interval sits at or above ``+margin``;
- ``below_margin`` — the whole interval sits at or below ``-margin``;
- ``within_margin`` — the whole interval lies strictly inside the band, which is
  the only evidence a comparison can offer for practical equivalence;
- ``inconclusive`` — the interval straddles a boundary, so the data are
  compatible with both a difference that matters and one that does not.

``inconclusive`` is not a synonym for "no effect", and the envelope's convention
says so, because that substitution is how an underpowered comparison becomes a
negative result.
"""

from __future__ import annotations

from typing import Any, Optional, Union

from aperv_tool.analysis.corpus import FreezeItemUnset
from aperv_tool.analysis.envelope import Denominator, Envelope

#: Sentinel for a freeze item the caller did not supply.
_UNSET: Any = object()

#: What an interval can be said to have decided.
VERDICTS = ("above_margin", "below_margin", "within_margin", "inconclusive")


def decide(
    estimate: float,
    ci: Optional[tuple[float, float]],
    *,
    margin: float = _UNSET,
    estimand: str = "decision",
    n: int = 0,
    provenance_ref: str = "",
) -> Envelope:
    """Classify an interval against a symmetric margin.

    Args:
        estimate: The point estimate, on the same scale as ``margin``.
        ci: The interval, or ``None``. ``None`` yields ``inconclusive`` with the
            reason recorded — an estimator that computed no interval has decided
            nothing, and reading the point estimate against the margin on its own
            would be a decision with no uncertainty attached.
        margin: The smallest difference that matters, as a non-negative number on
            the estimate's scale. A freeze item: no default.
        estimand: What was estimated, carried through so the verdict stays
            attached to the quantity it judges.
        n: Units behind the estimate, carried through from the estimator.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        An envelope carrying ``verdict``, ``margin``, the interval bounds and
        ``excludes_zero``.

    Raises:
        FreezeItemUnset: ``margin`` was not supplied.
        ValueError: ``margin`` is negative, or the interval bounds are reversed.
    """
    if margin is _UNSET:
        raise FreezeItemUnset(
            "margin: the smallest difference that matters is a domain decision, "
            "and no interval implies one"
        )
    if margin < 0:
        raise ValueError(f"margin is a magnitude and cannot be negative, got {margin}")

    estimate_value = float(estimate)
    reason = ""
    if ci is None:
        verdict = "inconclusive"
        reason = "no interval was computed, so nothing was decided"
        low = high = float("nan")
        excludes_zero = False
    else:
        low, high = float(ci[0]), float(ci[1])
        if low > high:
            raise ValueError(f"interval bounds are reversed: ({low}, {high})")
        excludes_zero = low > 0.0 or high < 0.0
        if low >= margin:
            verdict = "above_margin"
        elif high <= -margin:
            verdict = "below_margin"
        elif -margin < low and high < margin:
            verdict = "within_margin"
        else:
            verdict = "inconclusive"
            reason = (
                "the interval straddles a margin boundary: the data are "
                "compatible with a difference that matters and with one that "
                "does not"
            )

    estimate_fields: dict[str, Union[float, int, str, bool]] = {
        "estimate": estimate_value,
        "ci_lo": low,
        "ci_hi": high,
        "margin": float(margin),
        "verdict": verdict,
        "excludes_zero": bool(excludes_zero),
        "reason": reason,
    }

    return Envelope(
        estimand=f"decision_on_{estimand}",
        n=int(n),
        denominator=Denominator(reachable=int(n), analysed=int(n)),
        estimate=estimate_fields,
        ci=None if ci is None else (low, high),
        convention={
            "margin": f"supplied by the caller as {margin}; the code has no default",
            "verdicts": ", ".join(VERDICTS),
            "inconclusive": "not a negative result — it states that the interval "
            "crosses a boundary, which an underpowered comparison also does",
            "within_margin": "the only evidence an interval offers for practical "
            "equivalence",
        },
        exclusions=(),
        provenance_ref=provenance_ref,
    )


__all__ = ["VERDICTS", "decide"]
