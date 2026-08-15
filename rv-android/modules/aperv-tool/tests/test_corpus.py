"""A fraction cannot leave this module without both of its denominators.

The tests here are shaped by the failure the module exists to prevent, not by its
line count. Two of them — ``test_both_denominators`` and
``test_basis_relations_by_name`` — assert on what a reader of a report can see: a
rate that says what it is a rate of, and a set difference that names its member.
The rest hold the boundary: the corpus is a freeze item with no default, a subset
carries its reason, and a basis is the size it claims to be.
"""

from __future__ import annotations

import dataclasses

import pandas as pd
import pytest

from aperv_tool.analysis.corpus import (
    Basis,
    CardinalityMismatch,
    CorpusScope,
    FreezeItemUnset,
    Rate,
    scope,
)
from aperv_tool.analysis.envelope import Denominator

# The fixture campaign's shape: 162 applications, ids as APK filenames.
FIXTURE_APPLICATIONS = [f"com.example.app{index:03d}_1.apk" for index in range(162)]

# The one application the neighbouring basis of 163 carries and the campaign does
# not. A real id, so a failure message reads like the data it stands for.
EXTRA_APPLICATION = "com.ds.avare_404.apk"

REASON = "applications whose static analysis reached a monitored operation"


def campaign_frame(applications: list[str] = FIXTURE_APPLICATIONS) -> pd.DataFrame:
    """A Layer-0 shaped frame: three runs per application."""
    return pd.DataFrame(
        [
            {"apk": application, "repetition": repetition, "detected": repetition == 0}
            for application in applications
            for repetition in range(3)
        ]
    )


def test_both_denominators() -> None:
    """A rate over a 40-application subset carries 162, 40 and the reason."""
    subset = FIXTURE_APPLICATIONS[:40]

    analysed, corpus = scope(campaign_frame(), subset=subset, reason=REASON)

    assert isinstance(corpus, CorpusScope)
    assert corpus.reachable.cardinality == 162
    assert corpus.analysed.cardinality == 40
    assert len(analysed) == 40 * 3

    rate = corpus.rate(7, over="analysed")

    assert (rate.reachable, rate.analysed) == (162, 40)
    assert rate.denominator == 40
    assert rate.value == pytest.approx(7 / 40)
    assert rate.reason == REASON

    # The design constraint, checked at the API rather than at one call site: the
    # only field of a Rate that carries a count is the envelope's Denominator, so
    # no formatting step can drop one half of the pair and no caller can obtain
    # the fraction without it.
    assert isinstance(rate.corpus, Denominator)
    assert {field.name for field in dataclasses.fields(Rate)} == {
        "numerator",
        "over",
        "corpus",
    }
    assert corpus.denominator == Denominator(reachable=162, analysed=40, reason=REASON)

    over_reachable = corpus.rate(7, over="reachable")
    assert (over_reachable.reachable, over_reachable.analysed) == (162, 40)
    assert over_reachable.value == pytest.approx(7 / 162)


def test_basis_relations_by_name() -> None:
    """Bases of 163 and 162 report the difference and name the application."""
    census = Basis.declare(
        "substrate_census",
        FIXTURE_APPLICATIONS + [EXTRA_APPLICATION],
        cardinality=163,
    )
    campaign = Basis.declare("fixture_campaign", FIXTURE_APPLICATIONS, cardinality=162)

    report = census.relate(campaign).report()

    assert "|163∖162| = 1" in report
    assert EXTRA_APPLICATION in report
    assert "|162∖163| = 0" in report
    assert "shared = 162" in report


def test_subset_reason_recorded() -> None:
    """The reason travels from the declaration onto the scope and every rate."""
    _, corpus = scope(campaign_frame(), subset=FIXTURE_APPLICATIONS[:10], reason=REASON)

    assert corpus.reason == REASON
    assert corpus.rate(3, over="analysed").reason == REASON
    assert REASON in str(corpus.rate(3, over="analysed"))

    with pytest.raises(ValueError, match="carries the reason"):
        scope(campaign_frame(), subset=FIXTURE_APPLICATIONS, reason="   ")


def test_corpus_is_a_freeze_item() -> None:
    """Omitting the corpus raises rather than scoping to everything."""
    with pytest.raises(FreezeItemUnset, match="corpus"):
        scope(campaign_frame(), reason=REASON)

    with pytest.raises(FreezeItemUnset, match="corpus"):
        scope(campaign_frame(), subset=None, reason=REASON)


def test_cardinality_asserted() -> None:
    """A basis is the size it declares, and no member is counted twice."""
    with pytest.raises(CardinalityMismatch, match="declares 163 members but holds"):
        Basis.declare("miscounted", FIXTURE_APPLICATIONS, cardinality=163)

    with pytest.raises(CardinalityMismatch, match="more than once"):
        Basis.declare(
            "repeated",
            [EXTRA_APPLICATION, EXTRA_APPLICATION],
            cardinality=1,
        )

    with pytest.raises(ValueError, match="absent from the frame"):
        scope(
            campaign_frame(),
            subset=[EXTRA_APPLICATION],
            reason="declared against a different campaign",
        )
