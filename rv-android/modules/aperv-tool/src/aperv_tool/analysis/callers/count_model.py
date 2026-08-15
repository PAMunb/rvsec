"""A count-model entry: a negative-binomial GLM whose whole table is one envelope.

The shape every count entry has. The frame arrives at the observation grain, the
formula names the response and the covariates with the arm factor written as
``{arm}``, and the fit comes back as a single envelope carrying one rate ratio
per term.

The two freeze items cross the configuration boundary intact. ``count_glm.fit``
refuses to invent an offset or a reference level, and this caller refuses to
invent them either: the catalogue must declare both, and it says "none" by
declaring them empty rather than by leaving them out. That is the whole reason
``Entry.optional`` exists — without it, a TOML file with a typo'd key would fit
the model with no offset and report a perfectly plausible table.

**The offset is used verbatim, on the log scale.** The declared column is passed
to the estimator as it stands; this module applies no transform. A caller that
quietly took a logarithm here would make the elasticity-of-one constraint mean
something different from what the pre-registration says, and nothing downstream
would show it.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd

from aperv_tool.analysis.callers import Entry
from aperv_tool.analysis.callers.basis import with_basis
from aperv_tool.analysis.corpus import CorpusScope
from aperv_tool.analysis.envelope import Envelope, Exclusion
from aperv_tool.analysis.estimators import count_glm


def run(
    entry: Entry,
    frame: pd.DataFrame,
    *,
    scope: Optional[CorpusScope] = None,
    exclusions: Sequence[Exclusion] = (),
    provenance_ref: str = "",
) -> Envelope:
    """Answer one count-model catalogue entry over an observation-grain frame.

    Args:
        entry: The catalogue row. Reads ``formula``, ``offset_column``,
            ``reference_level``, ``cluster`` and ``arm_column``. The two freeze
            items are ``offset_column`` and ``reference_level``; an empty string
            is the explicit "none", an absent key is an error.
        frame: One row per observation, carrying every column the formula, the
            cluster and the offset need.
        scope: The corpus the estimate is asked over, so the envelope's
            denominator is the declared basis rather than the rows that happened
            to survive to the fit.
        exclusions: The units the pipeline already dropped, by identity and
            reason, carried into the envelope ahead of the estimator's own.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        The estimator's envelope, re-issued against the declared basis and
        extended with the conventions this caller decided — the entry, the
        formula as declared, and what the offset was.

    Raises:
        FreezeItemUnset: A parameter is missing from the catalogue, or the
            estimator's own freeze items were not satisfied.
        ValueError: The declared offset column is absent from the frame, or the
            estimator refused the fit.
    """
    formula = entry.parameter("formula")
    offset_column = entry.optional("offset_column")
    reference_level = entry.optional("reference_level")
    cluster = entry.parameter("cluster")
    arm_column = entry.parameter("arm_column")

    if offset_column is None:
        offset = None
        offset_note = "none declared"
    else:
        if offset_column not in frame.columns:
            raise ValueError(
                f"offset column {offset_column!r} is not in the frame; columns are "
                f"{', '.join(map(str, frame.columns))}"
            )
        offset = np.asarray(frame[offset_column], dtype=float)
        # A missing or infinite offset does not raise anywhere downstream: patsy
        # never sees the offset, so its dropped-rows check cannot catch it, and
        # the fit returns a table of NaN coefficients that emits as a perfectly
        # well-formed row. Refused here, naming the rows, because the whole
        # library's premise is that a defect is reported rather than absorbed.
        unusable = ~np.isfinite(offset)
        if unusable.any():
            positions = np.flatnonzero(unusable)
            shown = ", ".join(str(position) for position in positions[:5])
            raise ValueError(
                f"offset column {offset_column!r} has {int(unusable.sum())} "
                f"non-finite value(s) at row(s) {shown}; a NaN offset produces a "
                "table of NaN rate ratios rather than an error"
            )
        offset_note = f"{offset_column}, used verbatim on the log scale"

    envelope = count_glm.fit(
        formula,
        frame,
        offset=offset,
        reference_level=reference_level,
        cluster=cluster,
        arm_column=arm_column,
        provenance_ref=provenance_ref,
    )

    return with_basis(
        envelope,
        entry_id=entry.entry_id,
        scope=scope,
        exclusions=exclusions,
        extra={
            "formula": f"{formula} (arm factor = {arm_column})",
            "offset": offset_note,
            "reference_level": (
                "none declared — the formula carries no arm factor"
                if reference_level is None
                else str(reference_level)
            ),
        },
    )
