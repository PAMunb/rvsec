"""The envelope is the smallest object a number can leave the library inside.

These tests pin the three refusals that make it worth having: it cannot be
mutated after the estimate that produced it, it cannot be built without both
denominators, and a subset with no recorded reason cannot be built at all.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from aperv_tool.analysis.envelope import Denominator, Envelope, Exclusion


def an_envelope(**overrides) -> Envelope:
    """A complete envelope, with the given fields replaced."""
    fields = {
        "estimand": "detection_rate",
        "n": 40,
        "denominator": Denominator(
            reachable=162, analysed=40, reason="declared 40-application subset"
        ),
        "estimate": {"rate": 0.35},
        "ci": (0.21, 0.51),
        "convention": {"replica_rule": "majority", "dedup_key": "class-method-spec"},
        "exclusions": (
            Exclusion(
                identity="com.ds.avare_404.apk__1__300__ape", reason="dead identity"
            ),
        ),
        "provenance_ref": "run-2026-08-15-a",
    }
    fields.update(overrides)
    return Envelope(**fields)  # type: ignore[arg-type]


def test_envelope_is_frozen() -> None:
    """An emitted estimate cannot be edited into agreeing with a claim."""
    envelope = an_envelope()
    with pytest.raises(FrozenInstanceError):
        envelope.estimand = "something_else"  # type: ignore[misc]


def test_denominator_requires_both_counts() -> None:
    """A fraction over one count is not constructible from the API."""
    with pytest.raises(TypeError):
        Denominator(reachable=162)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        Denominator(analysed=40)  # type: ignore[call-arg]


def test_envelope_requires_a_denominator() -> None:
    """No field of the envelope has a default, the denominator least of all."""
    with pytest.raises(TypeError):
        Envelope(  # type: ignore[call-arg]
            estimand="detection_rate",
            n=40,
            estimate={"rate": 0.35},
            ci=None,
            convention={},
            exclusions=(),
            provenance_ref="run-2026-08-15-a",
        )


def test_subset_without_a_reason_is_rejected() -> None:
    """A corpus that shrank for no recorded reason cannot be reported."""
    with pytest.raises(ValueError, match="needs a recorded reason"):
        Denominator(reachable=162, analysed=40)


def test_full_basis_needs_no_reason() -> None:
    """Nothing was excluded, so there is nothing to explain."""
    assert Denominator(reachable=162, analysed=162).reason == ""


def test_analysed_cannot_exceed_reachable() -> None:
    """A fraction above one is caught where it is constructed, not where printed."""
    with pytest.raises(ValueError, match="exceeds reachable"):
        Denominator(reachable=40, analysed=162, reason="mistyped")


def test_exclusions_name_the_unit() -> None:
    """A dropped run is identified, not merely counted."""
    envelope = an_envelope()
    assert envelope.exclusions[0].identity.startswith("com.ds.avare_404.apk")
    assert envelope.exclusions[0].reason == "dead identity"
