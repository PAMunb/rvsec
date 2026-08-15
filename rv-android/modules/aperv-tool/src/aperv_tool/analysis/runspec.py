"""What a run actually was, evidenced from the trace's own header.

Every artefact a campaign writes carries an arm label in its filename —
``com.example_1.apk__1__300__aperv:mop_on_llm_off`` — and it is tempting to read
that label as the answer to "which configuration ran". It is not. The label is
written by the same orchestrator that was supposed to *apply* the configuration,
so it records an intention; whether the intention reached the jar is exactly the
question. **The filename is the claim under test, never the evidence for it.**

The evidence is the header the jar writes into the trace as it starts: the
preset it resolved, the features it activated, the parameters someone chose, and
the git sha of the jar itself. That record exists because of a specific failure:
a stale jar once shipped to an entire campaign, its MOP boost fired zero times
across 147,153 evaluations, and nothing in 2,028 tasks' worth of output said
which jar had run. ``build.sha`` was created to end that, and this module is
where the comparison against what the campaign *declared* is made.

**Three-valued, and the third value is load-bearing.** A comparison returns
``pass``, ``fail`` or ``not-run`` (INV-CAN-06). A header that carries no
``build.sha`` has not proved the wrong jar ran — it has proved nothing at all,
and calling that a pass would launder the absence of evidence into evidence of
absence. The overall verdict therefore degrades: any failed check makes the
whole ``fail``, and otherwise any check that could not run makes it ``not-run``.
Only an evidence set that is both complete and matching yields ``pass``.

**No expected digest lives here.** What the campaign declares — the jar sha, the
preset, the feature set, the parameters — arrives as a ``ManifestArm`` the
caller supplies as data (INV-APV-59). A digest literal committed under
``modules/`` would be a claim about one campaign frozen into a library that
outlives it.

This module holds derived logic only. ``RUN_START`` is parsed in exactly one
place, ``trace_ndjson.TraceReader`` (INV-APV-61), and there is deliberately no
second header type here (D-3): two parsers of one record is the defect being
closed, not a design to repeat.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, Optional

from aperv_tool.analysis.trace_ndjson import RunStart

#: The gate vocabulary, fixed for every validity gate in the library
#: (INV-CAN-06). ``not-run`` is a result, not an error, and never a pass.
Verdict = Literal["pass", "fail", "not-run"]

# The four comparisons this module can make, named so a gate report can quote
# the evidence form it used rather than asserting "attribution verified".
CHECK_DIGEST = "build.sha"
CHECK_PRESET = "preset"
CHECK_FEATURES = "features"
CHECK_PARAMS = "params"


@dataclass(frozen=True)
class ManifestArm:
    """What the campaign declares one arm should have been.

    Supplied by the caller as data. Every field is explicit — ``None`` is the
    way to say "the manifest declares nothing here", and it is recorded as a
    ``not-run`` check rather than skipped silently, because a caller who
    declared nothing has not verified anything.

    Attributes:
        arm: The arm label this declaration is for, as written on disk. Carried
            through to the evidence so a report names the arm it judged.
        digest: The git sha of the jar the campaign intended to run, or None
            when the manifest declares none.
        preset: The named preset the arm resolves from (cmp162's ``aperv`` arms
            resolve from ``mop``), or None.
        features: The exact feature set expected, or None. Compared as a set,
            in both directions: a *missing* feature says the arm lost a
            capability it declared, and an *unexpected* one says a different
            arm's jar or configuration ran under this label — which is the
            mislabelling this whole comparison exists to catch. An empty tuple
            therefore means "this arm activates no feature", not "do not check".
        params: The parameter values the campaign fixed, compared by declared
            key only. The header's ``params`` carries whatever someone chose
            plus each active feature's activation key, so an exhaustive
            comparison would break on any parameter the manifest does not care
            about. An empty mapping declares nothing and yields ``not-run``.
    """

    arm: str
    digest: Optional[str]
    preset: Optional[str]
    features: Optional[tuple[str, ...]]
    params: Mapping[str, Any]


@dataclass(frozen=True)
class EvidenceCheck:
    """One comparison between the header and the manifest.

    Attributes:
        name: Which comparison — one of the four ``CHECK_*`` constants.
        verdict: ``pass``, ``fail``, or ``not-run`` when the comparison could
            not be made at all.
        detail: Why, in words a gate report can print unmodified. A passing
            check still says what it compared, so a reader of the report can
            tell a verified arm from an unverified one without re-running it.
    """

    name: str
    verdict: Verdict
    detail: str


@dataclass(frozen=True)
class AttributionEvidence:
    """The verdict on "did this run carry the configuration it is labelled with".

    Attributes:
        arm: The arm label judged.
        verdict: ``fail`` if any check failed; otherwise ``not-run`` if any
            check could not run; otherwise ``pass``. The ordering is the point:
            an incomplete evidence set never yields a clean pass, and a real
            mismatch is never hidden behind a missing one.
        evidence_form: The checks that actually ran, comma-joined — the phrase
            a ``GateReport`` prints as its evidence form. ``none`` when the
            header and the manifest between them supported no comparison.
        checks: Every comparison attempted, in a fixed order, so gate 2
            (correct binary, the digest) and gate 3 (arm attribution, the
            configuration) can each read their own verdict out of one call.
    """

    arm: str
    verdict: Verdict
    evidence_form: str
    checks: tuple[EvidenceCheck, ...]

    @property
    def reasons(self) -> tuple[str, ...]:
        """The detail of every check that did not pass, in check order."""
        return tuple(check.detail for check in self.checks if check.verdict != "pass")


@dataclass(frozen=True)
class ResolvedParams:
    """What the run's parameters were, and what they demonstrably were not.

    Attributes:
        chosen: The parameters the header recorded, verbatim.
        unresolved: The asked-about keys ``chosen`` does not carry. Read this
            together with ``params_recorded``: with a recorded ``params``
            member an absent key means the run was at the jar default for
            ``build_sha``; without one it means the header did not say. The two
            are different states and the library never merges them into a value.
        params_recorded: Whether the header carried a ``params`` member at all.
        build_sha: The jar whose defaults ``unresolved`` refers to, or None —
            in which case "at the jar default" names no jar and the parameters
            of the run are not recoverable from the artefact at all.
    """

    chosen: Mapping[str, Any]
    unresolved: tuple[str, ...]
    params_recorded: bool
    build_sha: Optional[str]


def params_resolved(
    run_start: Optional[RunStart], *, keys: Iterable[str] = ()
) -> ResolvedParams:
    """Resolve what a run's parameters were, without inventing any.

    The jar writes into ``params`` only what someone chose plus the activation
    key of each active feature; everything else it omits. **An absent key
    therefore means "at the jar default for this ``build.sha``", never
    "unset".** Those two readings differ by the whole default table of a
    particular jar build, which is why the resolution is reported as a set of
    names rather than substituted with values: this module has no default table,
    and inventing one would answer a provenance question with a guess.

    Args:
        run_start: The trace's header, or None when the trace carried none.
        keys: The parameters the caller cares about. Only these are reported as
            unresolved; the header's own keys always come back in ``chosen``.

    Returns:
        The ``ResolvedParams``.
    """
    recorded = run_start is not None and run_start.params is not None
    chosen: Mapping[str, Any] = dict(run_start.params) if recorded else {}
    build_sha = (
        run_start.build.sha
        if run_start is not None and run_start.build is not None
        else None
    )
    unresolved = tuple(key for key in keys if key not in chosen)
    return ResolvedParams(
        chosen=chosen,
        unresolved=unresolved,
        params_recorded=recorded,
        build_sha=build_sha,
    )


def attribution_evidence(
    run_start: Optional[RunStart], manifest_arm: ManifestArm
) -> AttributionEvidence:
    """Judge a run's configuration against what its arm declared.

    Intended for the arms whose jar writes a header — an ``ape`` or ``droidbot``
    trace has none, and its attribution evidence is a different form entirely
    (the absence of NDJSON records, the policy line) owned by ``gates``.

    Args:
        run_start: The header as ``TraceReader`` read it, or None when the trace
            carried none. None is not a failure: a capture that began late, or a
            trace cut before its first record, has no evidence to offer and says
            so.
        manifest_arm: What the campaign declared for this arm, as data.

    Returns:
        The ``AttributionEvidence``, with one ``EvidenceCheck`` per comparison
        attempted and the degrading overall verdict described on that class.
    """
    if run_start is None:
        absent = "no RUN_START record in the trace, so nothing is evidenced"
        checks = tuple(
            EvidenceCheck(name=name, verdict="not-run", detail=f"{name}: {absent}")
            for name in (CHECK_DIGEST, CHECK_PRESET, CHECK_FEATURES, CHECK_PARAMS)
        )
        return AttributionEvidence(
            arm=manifest_arm.arm,
            verdict="not-run",
            evidence_form="none",
            checks=checks,
        )

    checks = (
        _check_digest(run_start, manifest_arm),
        _check_preset(run_start, manifest_arm),
        _check_features(run_start, manifest_arm),
        _check_params(run_start, manifest_arm),
    )
    ran = tuple(check.name for check in checks if check.verdict != "not-run")

    if any(check.verdict == "fail" for check in checks):
        verdict: Verdict = "fail"
    elif any(check.verdict == "not-run" for check in checks):
        verdict = "not-run"
    else:
        verdict = "pass"

    return AttributionEvidence(
        arm=manifest_arm.arm,
        verdict=verdict,
        evidence_form=", ".join(ran) if ran else "none",
        checks=checks,
    )


def _check_digest(run_start: RunStart, manifest_arm: ManifestArm) -> EvidenceCheck:
    """Compare the jar that ran against the jar the campaign declared."""
    expected = manifest_arm.digest
    found = run_start.build.sha if run_start.build is not None else None

    if expected is None:
        return EvidenceCheck(
            CHECK_DIGEST,
            "not-run",
            f"{CHECK_DIGEST}: the manifest declares no digest for arm "
            f"{manifest_arm.arm!r}",
        )
    if found is None:
        return EvidenceCheck(
            CHECK_DIGEST,
            "not-run",
            f"{CHECK_DIGEST}: the header carries no build.sha, so the jar that "
            f"ran is unknown; expected {expected!r}",
        )
    if found != expected:
        return EvidenceCheck(
            CHECK_DIGEST,
            "fail",
            f"{CHECK_DIGEST}: expected {expected!r}, the header carries {found!r}",
        )
    return EvidenceCheck(CHECK_DIGEST, "pass", f"{CHECK_DIGEST}: {found!r} as declared")


def _check_preset(run_start: RunStart, manifest_arm: ManifestArm) -> EvidenceCheck:
    """Compare the preset the jar resolved against the declared one."""
    expected = manifest_arm.preset
    found = run_start.preset

    if expected is None:
        return EvidenceCheck(
            CHECK_PRESET,
            "not-run",
            f"{CHECK_PRESET}: the manifest declares no preset for arm "
            f"{manifest_arm.arm!r}",
        )
    if found is None:
        return EvidenceCheck(
            CHECK_PRESET,
            "not-run",
            f"{CHECK_PRESET}: the header carries no preset; expected {expected!r}",
        )
    if found != expected:
        return EvidenceCheck(
            CHECK_PRESET,
            "fail",
            f"{CHECK_PRESET}: expected {expected!r}, the header carries {found!r}",
        )
    return EvidenceCheck(CHECK_PRESET, "pass", f"{CHECK_PRESET}: {found!r} as declared")


def _check_features(run_start: RunStart, manifest_arm: ManifestArm) -> EvidenceCheck:
    """Compare the active feature set, in both directions.

    Features are derived from the configuration, whereas the passes the jar
    assembles depend on the application's substrate — two arms print identical
    passes on an application with no transitions — so this is the member that
    identifies the arm, and an unexpected feature is as strong a signal as a
    missing one.
    """
    expected = manifest_arm.features
    found = run_start.features

    if expected is None:
        return EvidenceCheck(
            CHECK_FEATURES,
            "not-run",
            f"{CHECK_FEATURES}: the manifest declares no feature set for arm "
            f"{manifest_arm.arm!r}",
        )
    if found is None:
        return EvidenceCheck(
            CHECK_FEATURES,
            "not-run",
            f"{CHECK_FEATURES}: the header carries no features; expected "
            f"{list(expected)}",
        )

    missing = sorted(set(expected) - set(found))
    unexpected = sorted(set(found) - set(expected))
    if missing or unexpected:
        return EvidenceCheck(
            CHECK_FEATURES,
            "fail",
            f"{CHECK_FEATURES}: missing {missing}, unexpected {unexpected}",
        )
    return EvidenceCheck(
        CHECK_FEATURES,
        "pass",
        f"{CHECK_FEATURES}: {len(expected)} declared features, exactly as declared",
    )


def _check_params(run_start: RunStart, manifest_arm: ManifestArm) -> EvidenceCheck:
    """Compare each declared parameter value against the header's.

    A declared key the header does not carry is a mismatch, not a match: the
    run was at the jar default for its own build, and whether that default
    equals the declared value is not knowable from the artefact.
    """
    expected = manifest_arm.params
    if not expected:
        return EvidenceCheck(
            CHECK_PARAMS,
            "not-run",
            f"{CHECK_PARAMS}: the manifest declares no parameters for arm "
            f"{manifest_arm.arm!r}",
        )

    resolved = params_resolved(run_start, keys=expected.keys())
    if not resolved.params_recorded:
        return EvidenceCheck(
            CHECK_PARAMS,
            "not-run",
            f"{CHECK_PARAMS}: the header carries no params member, so the "
            f"{len(expected)} declared parameters are unevidenced",
        )

    at_default = ", ".join(
        f"{key}: expected {expected[key]!r}, absent — at the jar default for "
        f"build.sha={resolved.build_sha!r}"
        for key in resolved.unresolved
    )
    differing = ", ".join(
        f"{key}: expected {expected[key]!r}, the header carries "
        f"{resolved.chosen[key]!r}"
        for key in sorted(expected)
        if key in resolved.chosen and resolved.chosen[key] != expected[key]
    )
    if at_default or differing:
        detail = "; ".join(part for part in (differing, at_default) if part)
        return EvidenceCheck(CHECK_PARAMS, "fail", f"{CHECK_PARAMS}: {detail}")
    return EvidenceCheck(
        CHECK_PARAMS,
        "pass",
        f"{CHECK_PARAMS}: {len(expected)} declared parameters, all as declared",
    )
