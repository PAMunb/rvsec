"""Attribution is evidenced from the header, and absent evidence is not a pass.

The tests are built on hand-written ``RunStart`` values shaped like the headers
cmp162's ``aperv`` arms actually wrote: the ``mop_on_llm_off`` arm carries
``MOP_FRONTIER`` among its features and the ``mop_off_llm_off`` arm does not,
which is the one-feature difference that separates the two arms and therefore
the difference a mislabelled run would show.

Verdicts alone would make these tests nearly vacuous — three strings, and a
function returning a constant would satisfy half of them — so each one asserts
the reason the module produced as well.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest

from aperv_tool.analysis.runspec import (
    CHECK_DIGEST,
    CHECK_FEATURES,
    CHECK_PARAMS,
    CHECK_PRESET,
    AttributionEvidence,
    ManifestArm,
    attribution_evidence,
    params_resolved,
)
from aperv_tool.analysis.trace_ndjson import BuildStamp, RunStart

# The jar sha is supplied as data on both sides of every comparison here, as it
# is in production: no expected digest may be committed under `modules/`
# (INV-APV-59), and a test literal would be one.
JAR_SHA = "9e948102"

MOP_ON_FEATURES = (
    "ACTIVITY_BUDGET",
    "ACTIVITY_TRIGGER",
    "MOP",
    "MOP_FRONTIER",
    "WTG",
)
MOP_OFF_FEATURES = (
    "ACTIVITY_BUDGET",
    "ACTIVITY_TRIGGER",
    "MOP",
    "WTG",
)
DECLARED_PARAMS = {"ape.frontierBoostWeight": 200, "ape.mopBoostWeight": 500}


def header(**overrides: Any) -> RunStart:
    """A cmp162-shaped ``mop_on_llm_off`` header, with the given members replaced."""
    fields: dict[str, Any] = {
        "v": 1,
        "run_id": "20260812T230905Z-0001",
        "t0_ms": 1786576145777,
        "seed": 1786617113360,
        "agent": "sata",
        "preset": "mop",
        "features": MOP_ON_FEATURES,
        "params": dict(DECLARED_PARAMS),
        "inert": ("ape.llmPercentageNoSubstrate",),
        "corpus_basis": "selected162:3bbc5fa9",
        "digest": "ad537a816a19f154",
        "props_digest": "81feabbc",
        "build": BuildStamp(sha=JAR_SHA, time="2026-08-05T17:22:00Z"),
    }
    fields.update(overrides)
    return RunStart(**fields)


def manifest(**overrides: Any) -> ManifestArm:
    """The campaign's declaration for ``aperv:mop_on_llm_off``."""
    fields: dict[str, Any] = {
        "arm": "aperv:mop_on_llm_off",
        "digest": JAR_SHA,
        "preset": "mop",
        "features": MOP_ON_FEATURES,
        "params": dict(DECLARED_PARAMS),
    }
    fields.update(overrides)
    return ManifestArm(**fields)


def check_of(evidence: AttributionEvidence, name: str) -> Any:
    """The single check named ``name``."""
    matches = [check for check in evidence.checks if check.name == name]
    assert len(matches) == 1, f"expected one {name} check, got {matches}"
    return matches[0]


def test_matching_header_passes() -> None:
    """All four comparisons run and agree, and the evidence form names them."""
    evidence = attribution_evidence(header(), manifest())

    assert evidence.verdict == "pass"
    assert evidence.arm == "aperv:mop_on_llm_off"
    assert evidence.evidence_form == "build.sha, preset, features, params"
    assert evidence.reasons == ()
    assert [check.verdict for check in evidence.checks] == ["pass"] * 4


def test_digest_mismatch_fails_naming_both_shas() -> None:
    """A jar other than the declared one is the failure build.sha exists for."""
    evidence = attribution_evidence(
        header(build=BuildStamp(sha="deadbeef", time="2026-07-01T00:00:00Z")),
        manifest(),
    )

    assert evidence.verdict == "fail"
    detail = check_of(evidence, CHECK_DIGEST).detail
    assert "deadbeef" in detail and JAR_SHA in detail
    assert detail in evidence.reasons


def test_preset_mismatch_fails() -> None:
    """The preset the jar resolved is compared, not the one the label implies."""
    evidence = attribution_evidence(header(preset="baseline"), manifest())

    assert evidence.verdict == "fail"
    detail = check_of(evidence, CHECK_PRESET).detail
    assert "'baseline'" in detail and "'mop'" in detail


def test_missing_feature_fails_naming_it() -> None:
    """An arm that lost a declared feature is not the arm it is labelled."""
    evidence = attribution_evidence(header(features=MOP_OFF_FEATURES), manifest())

    assert evidence.verdict == "fail"
    detail = check_of(evidence, CHECK_FEATURES).detail
    assert "missing ['MOP_FRONTIER']" in detail
    assert "unexpected []" in detail


def test_unexpected_feature_fails_the_control_arm() -> None:
    """A ``mop_on`` header under the ``mop_off`` declaration is caught.

    This is the mislabelling direction the filename can never detect: the
    orchestrator wrote ``mop_off_llm_off`` and the jar activated the frontier
    boost anyway, which would contaminate the control arm silently.
    """
    control = manifest(
        arm="aperv:mop_off_llm_off",
        features=MOP_OFF_FEATURES,
        params={"ape.mopBoostWeight": 500},
    )
    evidence = attribution_evidence(header(), control)

    assert evidence.verdict == "fail"
    detail = check_of(evidence, CHECK_FEATURES).detail
    assert "unexpected ['MOP_FRONTIER']" in detail


def test_header_without_build_is_not_run_not_fail() -> None:
    """No ``build.sha`` proves nothing about the jar, so it is not a failure."""
    evidence = attribution_evidence(header(build=None), manifest())

    assert evidence.verdict == "not-run"
    digest_check = check_of(evidence, CHECK_DIGEST)
    assert digest_check.verdict == "not-run"
    assert "carries no build.sha" in digest_check.detail
    # The configuration evidence still ran and still passed; only the jar's
    # identity is unevidenced.
    assert evidence.evidence_form == "preset, features, params"
    assert [
        check_of(evidence, name).verdict
        for name in (CHECK_PRESET, CHECK_FEATURES, CHECK_PARAMS)
    ] == ["pass"] * 3


def test_failure_outranks_an_unevidenced_check() -> None:
    """A real mismatch is never hidden behind a missing comparison."""
    evidence = attribution_evidence(header(build=None, preset="baseline"), manifest())

    assert evidence.verdict == "fail"
    assert check_of(evidence, CHECK_DIGEST).verdict == "not-run"


def test_no_run_start_is_not_run_on_every_check() -> None:
    """A trace whose capture began late has no evidence to offer, and says so."""
    evidence = attribution_evidence(None, manifest())

    assert evidence.verdict == "not-run"
    assert evidence.evidence_form == "none"
    assert len(evidence.reasons) == 4
    assert all("no RUN_START record" in reason for reason in evidence.reasons)


def test_manifest_declaring_nothing_evidences_nothing() -> None:
    """A caller who declared no expectation has verified no expectation."""
    evidence = attribution_evidence(
        header(),
        ManifestArm(
            arm="aperv:mop_on_llm_off",
            digest=None,
            preset=None,
            features=None,
            params={},
        ),
    )

    assert evidence.verdict == "not-run"
    assert evidence.evidence_form == "none"
    assert all("the manifest declares no" in reason for reason in evidence.reasons)


def test_declared_param_absent_is_reported_as_a_jar_default() -> None:
    """An omitted key means "at the jar default", which is not a match."""
    evidence = attribution_evidence(
        header(params={"ape.frontierBoostWeight": 200}), manifest()
    )

    assert evidence.verdict == "fail"
    detail = check_of(evidence, CHECK_PARAMS).detail
    assert "ape.mopBoostWeight: expected 500, absent" in detail
    assert f"at the jar default for build.sha='{JAR_SHA}'" in detail


def test_declared_param_with_a_different_value_fails() -> None:
    """The value someone chose is compared to the value the campaign froze."""
    evidence = attribution_evidence(
        header(params={"ape.frontierBoostWeight": 200, "ape.mopBoostWeight": 300}),
        manifest(),
    )

    assert evidence.verdict == "fail"
    detail = check_of(evidence, CHECK_PARAMS).detail
    assert "ape.mopBoostWeight: expected 500, the header carries 300" in detail


def test_header_without_params_member_is_not_run_on_params() -> None:
    """An absent ``params`` member is unknown, not empty."""
    evidence = attribution_evidence(header(params=None), manifest())

    assert evidence.verdict == "not-run"
    detail = check_of(evidence, CHECK_PARAMS).detail
    assert "carries no params member" in detail


def test_params_resolved_reports_chosen_and_unresolved() -> None:
    """Chosen values come back verbatim; the rest are named, never invented."""
    resolved = params_resolved(
        header(params={"ape.frontierBoostWeight": 200}),
        keys=("ape.frontierBoostWeight", "ape.mopBoostWeight"),
    )

    assert resolved.chosen == {"ape.frontierBoostWeight": 200}
    assert resolved.unresolved == ("ape.mopBoostWeight",)
    assert resolved.params_recorded is True
    assert resolved.build_sha == JAR_SHA


def test_params_resolved_separates_absent_from_empty() -> None:
    """A header that did not say and a jar that recorded none are different."""
    absent = params_resolved(header(params=None), keys=("ape.mopBoostWeight",))
    empty = params_resolved(header(params={}), keys=("ape.mopBoostWeight",))

    assert absent.params_recorded is False
    assert empty.params_recorded is True
    assert absent.unresolved == empty.unresolved == ("ape.mopBoostWeight",)


def test_params_resolved_without_a_jar_names_no_default_table() -> None:
    """Unresolved keys with no ``build.sha`` refer to no jar at all."""
    resolved = params_resolved(
        header(build=None, params={}), keys=("ape.mopBoostWeight",)
    )

    assert resolved.build_sha is None
    assert resolved.unresolved == ("ape.mopBoostWeight",)


def test_params_resolved_on_a_missing_header() -> None:
    """No header resolves nothing, and raises nothing."""
    resolved = params_resolved(None, keys=("ape.mopBoostWeight",))

    assert resolved.chosen == {}
    assert resolved.params_recorded is False
    assert resolved.build_sha is None
    assert resolved.unresolved == ("ape.mopBoostWeight",)


def test_evidence_is_frozen() -> None:
    """The verdict cannot be edited after the comparison that produced it."""
    evidence = attribution_evidence(header(), manifest())
    with pytest.raises(FrozenInstanceError):
        evidence.verdict = "pass"  # type: ignore[misc]
