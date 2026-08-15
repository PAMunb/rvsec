"""A paired-binary entry: two arms, one application each side, exact McNemar.

The shape every paired-binary entry has. A per-run count becomes a per-cell
boolean under a declared threshold and a declared replica rule, the two arms are
paired **by application id**, and the discordance is tested exactly.

Two things this module deliberately does not do. It does not choose anything:
every knob — which arms, which count, the threshold, the replica rule, alpha —
arrives from the catalogue, and an omitted one raises instead of defaulting. And
it does not touch the numbers between the builder and the estimator; the pairing
is the index, so a caller cannot silently shift one arm against the other by
sorting differently, which is the failure ``align_pairs`` was written against.
"""

from __future__ import annotations

from typing import Optional, Sequence

import pandas as pd

from aperv_tool.analysis import outcomes
from aperv_tool.analysis.callers import Entry
from aperv_tool.analysis.callers.basis import with_basis
from aperv_tool.analysis.corpus import APPLICATION_COLUMN, CorpusScope
from aperv_tool.analysis.envelope import Envelope, Exclusion
from aperv_tool.analysis.estimators import paired_binary
from aperv_tool.analysis.outcomes import REPLICA_LEVEL

#: The column holding the arm label in a loaded campaign frame.
ARM_COLUMN = "arm"


def _side(frame: pd.DataFrame, arm: str, count_column: str) -> pd.Series:
    """One arm's per-run counts, indexed by ``(application, replica)``.

    Args:
        frame: The loaded campaign frame, one row per run identity.
        arm: The arm label to select.
        count_column: The count the outcome is built from.

    Returns:
        The counts, indexed so ``binarize`` can collapse the replica level.

    Raises:
        ValueError: The arm is absent from the frame, or the count column is.
            An absent arm is refused rather than yielding an empty side: an
            empty side pairs with nothing, and the estimator would report a
            perfectly well-formed comparison of zero pairs.
    """
    if count_column not in frame.columns:
        raise ValueError(
            f"count column {count_column!r} is not in the frame; columns are "
            f"{', '.join(map(str, frame.columns))}"
        )
    rows = frame.loc[frame[ARM_COLUMN] == arm]
    if rows.empty:
        present = ", ".join(sorted({str(value) for value in frame[ARM_COLUMN]}))
        raise ValueError(
            f"arm {arm!r} has no runs in the frame; arms present: {present}"
        )
    return rows.set_index([APPLICATION_COLUMN, REPLICA_LEVEL])[count_column]


def run(
    entry: Entry,
    frame: pd.DataFrame,
    *,
    scope: Optional[CorpusScope] = None,
    exclusions: Sequence[Exclusion] = (),
    provenance_ref: str = "",
) -> Envelope:
    """Answer one paired-binary catalogue entry over a loaded campaign frame.

    Args:
        entry: The catalogue row. Reads ``arm_a``, ``arm_b``, ``count_column``,
            ``threshold``, ``replica_rule`` and ``alpha``.
        frame: The campaign at the run grain, as ``loader.load`` returns it —
            already scoped and gated by the caller's own pipeline. This function
            makes no admissibility decision; that belongs to ``liveness`` and is
            taken once, upstream.
        scope: The corpus the estimate is asked over. Supplied so the envelope's
            denominator is the declared basis rather than whatever survived to
            reach the estimator — without it, an application dropped upstream
            takes the denominator down with it and the fraction silently rises.
        exclusions: The units the pipeline already dropped, by identity and
            reason. Carried into the envelope ahead of the estimator's own: a
            table of results has to carry its own attrition, or the count of
            what is missing lives in a log nobody reads beside it.
        provenance_ref: The provenance record this estimate belongs to.

    Returns:
        The estimator's envelope, re-issued against the declared basis and
        extended with the conventions this caller decided — the pairing unit and
        the arms, in the order the direction field reads them.

    Raises:
        FreezeItemUnset: A parameter is missing from the catalogue.
        ValueError: An arm or the count column is absent from the frame, or the
            estimate covers more units than the scope declares.
    """
    arm_a = entry.parameter("arm_a")
    arm_b = entry.parameter("arm_b")
    count_column = entry.parameter("count_column")
    threshold = entry.parameter("threshold")
    replica_rule = entry.parameter("replica_rule")
    alpha = entry.parameter("alpha")

    first = outcomes.binarize(
        _side(frame, arm_a, count_column),
        threshold=threshold,
        replica_rule=replica_rule,
    )
    second = outcomes.binarize(
        _side(frame, arm_b, count_column),
        threshold=threshold,
        replica_rule=replica_rule,
    )

    envelope = paired_binary.mcnemar_exact(
        first.values, second.values, alpha=alpha, provenance_ref=provenance_ref
    )

    return with_basis(
        envelope,
        entry_id=entry.entry_id,
        scope=scope,
        exclusions=exclusions,
        extra={
            "pairing_unit": (
                f"{APPLICATION_COLUMN}; replicas collapsed before pairing, "
                "never paired"
            ),
            "arms": f"first={arm_a}, second={arm_b}",
            "outcome": (
                f"{count_column} >= {threshold} per replica, collapsed by "
                f"{replica_rule}"
            ),
            "mixed_cells": (
                f"first arm {first.mixed} of {first.cells}, second arm "
                f"{second.mixed} of {second.cells} — cells whose replicas "
                "disagreed and the rule decided"
            ),
        },
    )
