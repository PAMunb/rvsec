"""One estimator per module, and none of them knows what it is estimating.

The package is deliberately thin. Each module owns one family of estimate —
paired binary, paired continuous, count regression, multiplicity, decision,
resampling, variance, capacity, multi-arm ranking — and every public function in
it returns an ``Envelope`` rather than a number (INV-CAN-14). Nothing here reads
a file, names a metric, or branches on which comparison it is serving: the
arguments arrive as columns and conventions, and the caller layer is the only
place that knows why.

That genericity is what makes the modules reusable across campaigns, and it is
also what makes them testable: an estimator whose answer is known analytically
can be checked against that answer, which is the whole of the correctness
evidence for this layer. The reproductions of a campaign's own output files are
parity checks — they prove the pipeline unchanged, never the estimator right
(INV-CAN-21).

Two conventions run through every module:

- **A pre-registration freeze item has no default.** A margin, an offset, a
  reference level or a multiplicity family that the code chose is a decision
  nobody wrote down, so those arguments are keyword-only and raise
  ``FreezeItemUnset`` when omitted. ``None`` remains a legal *explicit* value
  where it means something (no offset, no arm term); omission does not.
- **Companions travel with the number.** A discordance count without ``b``,
  ``c`` and the direction, or a mean without the median beside it, is a number
  that has already been misread once in this project. The envelope's ``estimate``
  mapping is where the companions live, and the estimators fill it whether or not
  the caller asked.

Offline and read-only: these modules take frames and arrays, compute, and return.
They open nothing and write nothing.
"""

from __future__ import annotations

from aperv_tool.analysis.estimators import (
    capacity,
    count_glm,
    decision,
    multiarm,
    multiplicity,
    paired_binary,
    paired_continuous,
    resampling,
    variance,
)

__all__ = [
    "capacity",
    "count_glm",
    "decision",
    "multiarm",
    "multiplicity",
    "paired_binary",
    "paired_continuous",
    "resampling",
    "variance",
]
