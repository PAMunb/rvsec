"""Carrying the corpus and its attrition into the envelope, in one place.

An estimator knows only what it was handed. ``mcnemar_exact`` counts the pairs it
received and reports a denominator of exactly those; ``count_glm.fit`` counts its
observations. Neither can know that four runs were excluded upstream by an
admissibility verdict, or that the corpus was a declared subset of a much larger
campaign — so an envelope built from the estimator alone reports a denominator
that has already quietly shrunk to whatever survived, which is the failure
INV-CAN-09 is about.

The pipeline that dropped those units is the only thing that knows why, so it is
the pipeline that must hand the reasons down. This module is the one seat for
what happens to them then: upstream exclusions are **prepended** to the
estimator's own, and the denominator is rebuilt against the basis the caller was
asked to run over rather than the one that happened to survive.

Both callers use it. Neither implements it, so a fraction cannot come out of one
of them meaning something different from the same fraction out of the other.
"""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from aperv_tool.analysis.corpus import CorpusScope
from aperv_tool.analysis.envelope import Denominator, Envelope, Exclusion


def carried_denominator(
    envelope: Envelope,
    scope: Optional[CorpusScope],
    exclusions: Sequence[Exclusion],
) -> Denominator:
    """The denominator this estimate should carry, given what it was asked over.

    Args:
        envelope: The estimator's own result. Its ``n`` is what was actually
            analysed and is never overridden — only the basis it is read
            against.
        scope: The corpus the caller was asked to run over, or ``None`` to keep
            the estimator's own denominator (nothing upstream to declare).
        exclusions: Every unit left out, upstream ones included. Their reasons
            become the denominator's reason, because a subset whose reason
            nobody wrote down cannot be judged later.

    Returns:
        The ``Denominator``. ``reachable`` is the declared subset's cardinality
        — the units the caller was asked to estimate over — not the campaign
        total, which stays in the convention where it belongs.

    Raises:
        ValueError: The estimate covers more units than the basis holds,
            propagated from ``Denominator``. That means the frame reaching the
            estimator was not the frame the scope describes, which is worth
            stopping on rather than reporting.
    """
    if scope is None:
        return envelope.denominator

    reachable = scope.analysed.cardinality
    if envelope.n == reachable:
        return Denominator(reachable=reachable, analysed=envelope.n, reason="")

    # The two differ, so a reason is mandatory. Dropped units always have one;
    # the fallback covers a shortfall the exclusions do not account for, which is
    # itself worth printing rather than papering over with an empty string.
    reasons = sorted({exclusion.reason for exclusion in exclusions if exclusion.reason})
    reason = (
        "; ".join(reasons)
        if reasons
        else "units absent from the estimate, unattributed"
    )
    return Denominator(reachable=reachable, analysed=envelope.n, reason=reason)


def merged_conventions(
    envelope: Envelope,
    entry_id: str,
    scope: Optional[CorpusScope],
    exclusions: Sequence[Exclusion],
    extra: Mapping[str, str],
) -> dict[str, str]:
    """The estimator's conventions plus the ones the caller decided.

    Args:
        envelope: The estimator's result, whose conventions are kept intact.
        entry_id: The catalogue entry, so a row in an emitted table names the
            question it was produced for.
        scope: The corpus, recorded whole — both its cardinalities and its
            reason — because the denominator carries only the declared subset.
        exclusions: Every unit left out, summarised by count and reason class.
        extra: The caller's own conventions.

    Returns:
        One flat mapping of strings.
    """
    convention = dict(envelope.convention)
    convention["entry"] = entry_id
    if scope is not None:
        convention["corpus"] = (
            f"{scope.reachable.cardinality} reachable -> "
            f"{scope.analysed.cardinality} declared subset: {scope.reason}"
        )
    if exclusions:
        # Named `attrition` rather than `exclusions`: the envelope already has a
        # field by that name carrying the full list, and an emitted table shows
        # both as columns. Two columns with the same name and different contents
        # is how a reader ends up quoting the summary as if it were the list.
        classes: dict[str, int] = {}
        for exclusion in exclusions:
            classes[exclusion.reason] = classes.get(exclusion.reason, 0) + 1
        convention["attrition"] = "; ".join(
            f"{count} x {reason}" for reason, count in sorted(classes.items())
        )
    convention.update(extra)
    return convention


def with_basis(
    envelope: Envelope,
    *,
    entry_id: str,
    scope: Optional[CorpusScope],
    exclusions: Sequence[Exclusion],
    extra: Mapping[str, str],
) -> Envelope:
    """The estimator's envelope, re-issued against the basis it was asked over.

    Args:
        envelope: The estimator's result.
        entry_id: The catalogue entry.
        scope: The corpus, or ``None``.
        exclusions: The units dropped upstream. The estimator's own exclusions
            are appended after these, so the order reads outward-in: the
            pipeline's decisions first, then the estimator's.
        extra: The caller's own conventions.

    Returns:
        A new ``Envelope``. The estimate, ``n``, interval and provenance
        reference are unchanged — only the denominator, the conventions and the
        exclusion list are enriched.
    """
    carried = tuple(exclusions) + envelope.exclusions
    return Envelope(
        estimand=envelope.estimand,
        n=envelope.n,
        denominator=carried_denominator(envelope, scope, carried),
        estimate=envelope.estimate,
        ci=envelope.ci,
        convention=merged_conventions(envelope, entry_id, scope, carried, extra),
        exclusions=carried,
        provenance_ref=envelope.provenance_ref,
    )
