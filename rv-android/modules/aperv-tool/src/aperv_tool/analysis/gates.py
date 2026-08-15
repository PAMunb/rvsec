"""Validity before outcome: the five gates, run before any number is read.

The organising rule is carried verbatim from the decisive campaign, because it is
the most reusable thing that campaign produced: **a failed gate invalidates what it
protects; the analysis is not adjusted to work around it.** No outcome is read until
the gates have run. That is what makes a null publishable — a null over runs whose
control arm was contaminated, or whose binary was the previous build, is not a null
about anything.

The five:

1. **Clean control** — over every control-arm run, the treatment's signal count is
   zero. Parameterised by the arm predicate (the manifest's control arms) and the
   signal pattern.
2. **Correct binary** — the digest of the artefact that ran, against the digest the
   campaign declared. Captured per run, never back-filled from configuration.
3. **Arm attribution** — evidenced from the artefact, never from the orchestrator's
   filename label. The filename is written by the same code that was supposed to
   apply the configuration, so a mis-resolved variant is still labelled correctly;
   the label is the claim under test, not the evidence for it.
4. **Task integrity** — counted by identity, not by line: at least one completed
   record and the full declared budget.
5. **Corpse detection** — three independent signals, with the corpse class beside
   the boolean.

**Gate 1 ships with a hard lesson: the field pattern must be anchored.** The
unanchored form matched the tail of ``activity_has_mop=1`` and produced hundreds of
phantom violations in a campaign that had none. ``ANCHORED_MOP`` encodes the
anchoring rather than the memory of it (INV-CAN-07).

**Gates 2 and 3 have a per-arm evidence form and the code names it** (INV-CAN-06),
because one form does not fit every arm. An ``aperv`` run's jar writes a header
declaring the preset, features, parameters and its own build; a ``droidbot`` run
announces its policy in one line and emits no digest at all; an ``ape`` run offers
only negative evidence — a trace with zero NDJSON records proves the upstream jar
ran and not the instrumented one, and a single such record is a failure naming the
line. Where no evidence form exists, the result is ``not-run``, reported as such and
never as a pass: a pass claims a comparison was made.

**Every per-run liveness question is delegated** (INV-CAN-05). Gates 4 and 5 call
``liveness.verdict`` and hold no predicate of their own over duration, trace size,
coverage or a fatal exception, so a run excluded by liveness is excluded once and
counted once. A structural test reads this module's source to keep that true.

**An arm passes only when every one of its runs was evidenced.** A single run whose
evidence is missing makes the arm ``not-run`` rather than letting a pass over the
evidenced subset stand as a statement about the arm. Failure dominates both: one
failing run fails the arm.

The gates read frames, never files. Evidence extraction from a trace or a sidecar
belongs to the readers; what arrives here is one row per identity with the extracted
facts, so the whole module is pure and a test needs three literals rather than a
campaign.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Optional, Pattern, Sequence

import pandas as pd

from aperv_tool.analysis import liveness
from aperv_tool.analysis.run_identity import (
    IDENTITY_COLUMNS,
    RunKey,
    decompose_arm,
)
from aperv_tool.analysis.runspec import (
    CHECK_DIGEST,
    AttributionEvidence,
    ManifestArm,
    Verdict,
    attribution_evidence,
)

#: The forbidden-signal pattern for the clean-control gate, anchored so that a field
#: whose name *ends* in the field being looked for — ``activity_has_mop=1`` — does not
#: match (INV-CAN-07). The lookbehind rejects a preceding lowercase letter or
#: underscore, which is what a longer field name always has.
ANCHORED_MOP: Pattern[str] = re.compile(r"(?<![a-z_])mop=")

GATE_CLEAN_CONTROL = 1
GATE_CORRECT_BINARY = 2
GATE_ARM_ATTRIBUTION = 3
GATE_TASK_INTEGRITY = 4
GATE_CORPSE_DETECTION = 5

#: What each gate is called in a report, so a caller prints the name it was given.
GATE_NAMES: Mapping[int, str] = {
    GATE_CLEAN_CONTROL: "clean control",
    GATE_CORRECT_BINARY: "correct binary",
    GATE_ARM_ATTRIBUTION: "arm attribution",
    GATE_TASK_INTEGRITY: "task integrity",
    GATE_CORPSE_DETECTION: "corpse detection",
}

# The identity columns. Everything else a gate reads is optional and its absence is
# reported as `not-run`, but a frame that cannot name its runs cannot be gated.
#
# Taken from the seat rather than restated. This module used to restate it with
# `repetition` where the loader writes `rep`, which meant `run_all` raised on
# every frame the loader has ever produced.
_IDENTITY_COLUMNS = IDENTITY_COLUMNS

# The evidence columns, named here so the frame's producer has one list to satisfy:
#   forbidden_signal_count — matches of the signal pattern in the run's own stream,
#       counted with `count_forbidden_signal` so the anchored pattern has one seat
#   jar_sha256             — digest of the artefact that ran, from a sidecar
#   ndjson_line_count      — `{`-leading lines in the trace, for the ape arms
#   first_ndjson_line_no   — the line number of the first of them, for the message
#   policy_line            — droidbot's `start sending events, policy is …` line
#   run_start              — the header `TraceReader` read, for the aperv arms
_EVIDENCE_COLUMNS = (
    "forbidden_signal_count",
    "jar_sha256",
    "ndjson_line_count",
    "first_ndjson_line_no",
    "policy_line",
    "run_start",
)

# How droidbot announces the policy it is about to run under. The gate reads the
# policy out of this line and compares it with what the arm declared.
DROIDBOT_POLICY_PREFIX = "start sending events, policy is"

#: The collaborator gate 3 uses for arms whose jar writes a header. It is a
#: parameter so a campaign whose header differs supplies its own comparison rather
#: than this module growing a second one.
AttributionEvidenceFn = Callable[[Any, ManifestArm], AttributionEvidence]

# Which evidence form gate 3 has for which tool. The form is a property of the tool
# — whether its artefact says anything about the configuration that produced it —
# so the dispatch is by tool and a tool absent from all three lists is `not-run`
# rather than assumed.
_HEADER_TOOLS = ("aperv",)
_POLICY_TOOLS = ("droidbot",)
_NEGATIVE_EVIDENCE_TOOLS = ("ape",)


def count_forbidden_signal(
    lines: Iterable[str], pattern: Pattern[str] = ANCHORED_MOP
) -> int:
    """Matches of the forbidden signal across ``lines``.

    Exists so the anchored pattern is applied in exactly one place: a caller that
    wrote its own scan would be free to write the unanchored form, which is the
    defect this gate was built around.

    Args:
        lines: The run's stream, one line at a time. Streamed, never materialised —
        a campaign trace runs to gigabytes.
        pattern: The signal to look for.

    Returns:
        The total number of matches, counting every match on a line.
    """
    return sum(len(pattern.findall(line)) for line in lines)


@dataclass(frozen=True)
class ArmSpec:
    """What the campaign declares about one arm, as data (INV-APV-59).

    Attributes:
        tool: The tool the arm runs, e.g. ``aperv``, ``ape``, ``droidbot``. Supplied
            rather than split out of the arm string (INV-CAN-02).
        variant: The variant, empty for a tool that has none.
        declaration: The header expectations — declared jar digest, preset, features
            and parameters — in the form ``runspec`` compares against.
        control: Whether this is a control arm, i.e. one over which the treatment's
            signal must never appear.
        policy: The policy a ``droidbot`` arm is expected to announce, or None for a
            tool that announces none.
    """

    tool: str
    variant: str
    declaration: ManifestArm
    control: bool = False
    policy: Optional[str] = None


@dataclass(frozen=True)
class ArmManifest:
    """The campaign's roster: every arm it declares, and what it declares about it.

    Supplied by the caller at runtime. No digest, preset or feature set is written
    into this library, which outlives any one campaign (INV-APV-59).
    """

    arms: Mapping[str, ArmSpec]

    @property
    def arm_table(self) -> Mapping[str, tuple[str, str]]:
        """The roster in the shape ``run_identity.decompose_arm`` consumes."""
        return {arm: (spec.tool, spec.variant) for arm, spec in self.arms.items()}

    @property
    def control_arms(self) -> tuple[str, ...]:
        """The arms gate 1 ranges over, sorted."""
        return tuple(sorted(arm for arm, spec in self.arms.items() if spec.control))


@dataclass(frozen=True, slots=True)
class GateResult:
    """One gate's answer for one arm.

    Attributes:
        status: ``pass``, ``fail`` or ``not-run``. The third is a result, never an
            error and never a pass (INV-CAN-06).
        evidence_form: What was actually compared, named — ``negative: 0 NDJSON
            lines``, ``build.sha``, ``provenance sidecar``. A report quotes this
            instead of asserting that something was verified.
        detail: Why, in a sentence, with the offending identities named when there
            are any.
    """

    status: Verdict
    evidence_form: str
    detail: str


@dataclass(frozen=True)
class GateReport:
    """Every gate's answer for every arm, plus the per-run verdicts behind them.

    Attributes:
        results: ``(gate, arm) -> GateResult``. Gate 1 appears for the control arms
            only, since it makes no claim about the others.
        verdicts: The admissibility verdict per run, computed once and shared by
            gates 4 and 5 so an excluded run is counted once.
        corpse_census: How many runs ended in each corpse class. Printed beside the
            boolean because the classification, not the boolean, is what refuted the
            decisive run's causal story.
    """

    results: Mapping[tuple[int, str], GateResult] = field(default_factory=dict)
    verdicts: Mapping[RunKey, liveness.Admissibility] = field(default_factory=dict)
    corpse_census: Mapping[str, int] = field(default_factory=dict)

    def status(self, gate: int, arm: str) -> Optional[Verdict]:
        """The status of one gate on one arm, or None when the gate did not apply."""
        result = self.results.get((gate, arm))
        return None if result is None else result.status

    @property
    def failed(self) -> tuple[tuple[int, str], ...]:
        """Every ``(gate, arm)`` that failed, sorted. Empty means nothing failed."""
        return tuple(
            sorted(
                key for key, result in self.results.items() if result.status == "fail"
            )
        )

    @property
    def not_run(self) -> tuple[tuple[int, str], ...]:
        """Every ``(gate, arm)`` that could not be evidenced, sorted."""
        return tuple(
            sorted(
                key
                for key, result in self.results.items()
                if result.status == "not-run"
            )
        )


def _aggregate(verdicts: Sequence[Verdict]) -> Verdict:
    """One arm's status from its runs': fail dominates, then ``not-run``.

    A pass therefore means every run of the arm was evidenced and every one passed.
    Anything weaker would let a claim about an arm rest on the subset of its runs
    that happened to carry evidence.
    """
    if not verdicts:
        return "not-run"
    if "fail" in verdicts:
        return "fail"
    if "not-run" in verdicts:
        return "not-run"
    return "pass"


def _name(identity: RunKey) -> str:
    """A run named the way a reader finds it on disk."""
    return str(identity)


def _first_names(identities: Sequence[RunKey], limit: int = 3) -> str:
    """Up to ``limit`` identities, named, with the remainder counted."""
    shown = ", ".join(_name(identity) for identity in identities[:limit])
    if len(identities) > limit:
        return f"{shown}, and {len(identities) - limit} more"
    return shown


def _value(row: Mapping[str, Any], column: str) -> Any:
    """A row's value, with a missing or unmeasured cell coming back as None."""
    value = row.get(column)
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    return value


def _gate_clean_control(
    arm: str, rows: Sequence[tuple[RunKey, Mapping[str, Any]]], pattern: Pattern[str]
) -> GateResult:
    """Gate 1 over one control arm."""
    unmeasured: list[RunKey] = []
    contaminated: list[RunKey] = []
    total = 0
    for identity, row in rows:
        count = _value(row, "forbidden_signal_count")
        if count is None:
            unmeasured.append(identity)
            continue
        if int(count) > 0:
            contaminated.append(identity)
            total += int(count)

    form = f"anchored field pattern {pattern.pattern!r} over the run's own stream"
    if contaminated:
        return GateResult(
            status="fail",
            evidence_form=form,
            detail=(
                f"{total} forbidden signal(s) over {len(contaminated)} control run(s) "
                f"of {arm}: {_first_names(contaminated)}"
            ),
        )
    if unmeasured:
        return GateResult(
            status="not-run",
            evidence_form=form,
            detail=(
                f"{len(unmeasured)} run(s) of {arm} carry no signal count: "
                f"{_first_names(unmeasured)}"
            ),
        )
    return GateResult(
        status="pass",
        evidence_form=form,
        detail=f"{len(rows)} control run(s) of {arm}, no forbidden signal",
    )


def _gate_correct_binary(
    arm: str,
    spec: ArmSpec,
    rows: Sequence[tuple[RunKey, Mapping[str, Any]]],
    header_evidence: Mapping[RunKey, AttributionEvidence],
) -> GateResult:
    """Gate 2 over one arm: the digest that ran against the digest declared."""
    declared = spec.declaration.digest
    if declared is None:
        return GateResult(
            status="not-run",
            evidence_form="none",
            detail=f"the manifest declares no digest for {arm}",
        )

    statuses: list[Verdict] = []
    forms: set[str] = set()
    mismatched: list[RunKey] = []
    unevidenced: list[RunKey] = []
    for identity, row in rows:
        observed = _value(row, "jar_sha256")
        if observed is not None:
            forms.add("provenance sidecar jar_sha256")
            if str(observed) == declared:
                statuses.append("pass")
            else:
                statuses.append("fail")
                mismatched.append(identity)
            continue
        check = _digest_check(header_evidence.get(identity))
        if check is None:
            statuses.append("not-run")
            unevidenced.append(identity)
            continue
        forms.add(CHECK_DIGEST)
        statuses.append(check.verdict)
        if check.verdict == "fail":
            mismatched.append(identity)
        elif check.verdict == "not-run":
            unevidenced.append(identity)

    status = _aggregate(statuses)
    form = ", ".join(sorted(forms)) if forms else "none"
    if mismatched:
        detail = f"digest differs from the declared one on {_first_names(mismatched)}"
    elif unevidenced:
        detail = (
            f"no digest emitted, no sidecar on {len(unevidenced)} run(s) of {arm}: "
            f"{_first_names(unevidenced)}"
        )
    else:
        detail = f"{len(rows)} run(s) of {arm} carry the declared digest"
    return GateResult(status=status, evidence_form=form, detail=detail)


def _digest_check(evidence: Optional[AttributionEvidence]):
    """The digest comparison inside a header evidence set, or None if absent."""
    if evidence is None:
        return None
    for check in evidence.checks:
        if check.name == CHECK_DIGEST:
            return check
    return None


def _gate_attribution_header(
    arm: str,
    rows: Sequence[tuple[RunKey, Mapping[str, Any]]],
    header_evidence: Mapping[RunKey, AttributionEvidence],
) -> GateResult:
    """Gate 3 for an arm whose jar writes a header: the collaborator's verdict."""
    statuses: list[Verdict] = []
    forms: set[str] = set()
    failing: list[RunKey] = []
    unevidenced: list[RunKey] = []
    for identity, _row in rows:
        evidence = header_evidence.get(identity)
        if evidence is None:
            statuses.append("not-run")
            unevidenced.append(identity)
            continue
        # The digest belongs to gate 2; gate 3 asks what configuration resolved.
        checks = [check for check in evidence.checks if check.name != CHECK_DIGEST]
        verdict = _aggregate([check.verdict for check in checks])
        statuses.append(verdict)
        forms.update(check.name for check in checks if check.verdict != "not-run")
        if verdict == "fail":
            failing.append(identity)
        elif verdict == "not-run":
            unevidenced.append(identity)

    status = _aggregate(statuses)
    form = ", ".join(sorted(forms)) if forms else "none"
    if failing:
        detail = (
            f"the resolved configuration differs from {arm} on {_first_names(failing)}"
        )
    elif unevidenced:
        detail = (
            f"no header evidence on {len(unevidenced)} run(s) of {arm}: "
            f"{_first_names(unevidenced)}"
        )
    else:
        detail = f"{len(rows)} run(s) of {arm} resolved what the manifest declares"
    return GateResult(status=status, evidence_form=form, detail=detail)


def _gate_attribution_negative(
    arm: str, rows: Sequence[tuple[RunKey, Mapping[str, Any]]]
) -> GateResult:
    """Gate 3 for an arm that must emit no NDJSON: the absence is the evidence.

    An ``ape`` run is the upstream jar. The instrumented jar is the only thing in the
    workspace that writes NDJSON records into a trace, so zero such records is proof
    the label is honest — and one record is proof it is not, which is why the failure
    names the line rather than counting it.
    """
    form = "negative: 0 NDJSON lines"
    offenders: list[tuple[RunKey, Any]] = []
    unmeasured: list[RunKey] = []
    for identity, row in rows:
        count = _value(row, "ndjson_line_count")
        if count is None:
            unmeasured.append(identity)
            continue
        if int(count) > 0:
            offenders.append((identity, _value(row, "first_ndjson_line_no")))

    if offenders:
        named = ", ".join(
            f"{_name(identity)} (first at line "
            f"{int(line) if line is not None else 'unknown'})"
            for identity, line in offenders[:3]
        )
        remainder = f", and {len(offenders) - 3} more" if len(offenders) > 3 else ""
        return GateResult(
            status="fail",
            evidence_form=form,
            detail=f"NDJSON records in an {arm}-labelled trace: {named}{remainder}",
        )
    if unmeasured:
        return GateResult(
            status="not-run",
            evidence_form="none",
            detail=(
                f"{len(unmeasured)} run(s) of {arm} were not scanned for NDJSON lines: "
                f"{_first_names(unmeasured)}"
            ),
        )
    return GateResult(
        status="pass",
        evidence_form=form,
        detail=f"{len(rows)} run(s) of {arm} carry no NDJSON record",
    )


def _gate_attribution_policy(
    arm: str, spec: ArmSpec, rows: Sequence[tuple[RunKey, Mapping[str, Any]]]
) -> GateResult:
    """Gate 3 for an arm that announces its policy in one line."""
    form = f"{DROIDBOT_POLICY_PREFIX} …"
    if spec.policy is None:
        return GateResult(
            status="not-run",
            evidence_form="none",
            detail=f"the manifest declares no policy for {arm}",
        )

    mismatched: list[RunKey] = []
    missing: list[RunKey] = []
    for identity, row in rows:
        line = _value(row, "policy_line")
        if line is None or DROIDBOT_POLICY_PREFIX not in str(line):
            missing.append(identity)
            continue
        announced = str(line).split(DROIDBOT_POLICY_PREFIX, 1)[1].strip()
        if announced != spec.policy:
            mismatched.append(identity)

    if mismatched:
        return GateResult(
            status="fail",
            evidence_form=form,
            detail=(
                f"announced policy differs from the declared {spec.policy!r} on "
                f"{_first_names(mismatched)}"
            ),
        )
    if missing:
        return GateResult(
            status="not-run",
            evidence_form="none",
            detail=(
                f"{len(missing)} run(s) of {arm} announce no policy: "
                f"{_first_names(missing)}"
            ),
        )
    return GateResult(
        status="pass",
        evidence_form=form,
        detail=f"{len(rows)} run(s) of {arm} announce the declared policy",
    )


def _gate_task_integrity(
    arm: str,
    rows: Sequence[tuple[RunKey, Mapping[str, Any]]],
    verdicts: Mapping[RunKey, liveness.Admissibility],
) -> GateResult:
    """Gate 4 over one arm, read off the shared liveness verdicts.

    Counted by identity rather than by line, because a resume appends a record with
    a fresh identifier instead of overwriting: counting lines counts the same run
    twice and then reports the loss as zero.
    """
    form = "identity-keyed task records, judged by liveness (C1 completion, C2 budget)"
    incomplete: list[RunKey] = []
    short: list[RunKey] = []
    for identity, _row in rows:
        failed = verdicts[identity].failed_criteria
        if "C1" in failed:
            incomplete.append(identity)
        if "C2" in failed:
            short.append(identity)

    if incomplete or short:
        parts = []
        if incomplete:
            parts.append(
                f"{len(incomplete)} without a completed record "
                f"({_first_names(incomplete)})"
            )
        if short:
            parts.append(
                f"{len(short)} short of the declared budget ({_first_names(short)})"
            )
        return GateResult(
            status="fail",
            evidence_form=form,
            detail=f"{arm}: " + "; ".join(parts),
        )
    return GateResult(
        status="pass",
        evidence_form=form,
        detail=f"{len(rows)} identity(ies) of {arm} completed and ran the full budget",
    )


def _gate_corpse_detection(
    arm: str,
    rows: Sequence[tuple[RunKey, Mapping[str, Any]]],
    facts: Mapping[RunKey, liveness.RunFacts],
    verdicts: Mapping[RunKey, liveness.Admissibility],
) -> GateResult:
    """Gate 5 over one arm, read off the shared liveness verdicts."""
    form = "three signals via liveness: trace floor, coverage, named fatal exception"
    corpses = [identity for identity, _row in rows if verdicts[identity].is_corpse]
    if corpses:
        classes = ", ".join(
            f"{_name(identity)} [{verdicts[identity].corpse_class}]"
            for identity in corpses[:3]
        )
        remainder = f", and {len(corpses) - 3} more" if len(corpses) > 3 else ""
        return GateResult(
            status="fail",
            evidence_form=form,
            detail=f"{len(corpses)} corpse(s) in {arm}: {classes}{remainder}",
        )

    blind = [
        identity
        for identity, _row in rows
        if not liveness.corpse_detectable(facts[identity])
    ]
    if blind:
        return GateResult(
            status="not-run",
            evidence_form="none",
            detail=(
                f"{len(blind)} run(s) of {arm} carry none of the three facts: "
                f"{_first_names(blind)}"
            ),
        )
    return GateResult(
        status="pass",
        evidence_form=form,
        detail=f"{len(rows)} run(s) of {arm}, no corpse",
    )


def run_all(
    frame: pd.DataFrame,
    arm_manifest: ArmManifest,
    *,
    alpha_signal: Pattern[str] = ANCHORED_MOP,
    aperv_evidence: AttributionEvidenceFn = attribution_evidence,
    trace_floor_bytes: int = liveness.TRACE_FLOOR_BYTES,
) -> GateReport:
    """Run the five gates over a Layer-0 frame.

    Args:
        frame: One row per identity, at the ``(apk, repetition, timeout_s, arm)``
            grain, carrying the liveness facts ``liveness.RunFacts.from_mapping``
            reads and whichever evidence columns the readers filled in. A missing
            evidence column is a ``not-run``, never a pass.
        arm_manifest: The campaign's roster and declarations, as data. An arm in the
            frame that the manifest does not declare raises rather than being split
            heuristically (INV-CAN-02).
        alpha_signal: The forbidden signal gate 1 counts. Anchored by default
            (INV-CAN-07).
        aperv_evidence: The header comparison gate 3 uses for the arms whose jar
            writes one. Supplied as a collaborator so this module holds no second
            copy of the comparison.
        trace_floor_bytes: Passed through to ``liveness.verdict``.

    Returns:
        The ``GateReport``, with one result per applicable ``(gate, arm)``, the
        per-run verdicts, and the corpse-class census.

    Raises:
        ValueError: The frame lacks an identity column.
        UnknownArm: The frame carries an arm the manifest does not declare.
    """
    missing = [column for column in _IDENTITY_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            f"the frame cannot be gated without its identity columns: {missing}"
        )

    rows_by_arm: dict[str, list[tuple[RunKey, Mapping[str, Any]]]] = defaultdict(list)
    facts: dict[RunKey, liveness.RunFacts] = {}
    verdicts: dict[RunKey, liveness.Admissibility] = {}
    census: dict[str, int] = defaultdict(int)

    for row in frame.to_dict(orient="records"):
        run_facts = liveness.RunFacts.from_mapping(row)
        identity = run_facts.identity
        # Resolved, not split: an arm the manifest does not declare stops the run
        # here rather than being decomposed into a plausible pair.
        decompose_arm(identity.arm, arm_manifest.arm_table)
        rows_by_arm[identity.arm].append((identity, row))
        facts[identity] = run_facts
        admissibility = liveness.verdict(run_facts, trace_floor_bytes=trace_floor_bytes)
        verdicts[identity] = admissibility
        census[admissibility.corpse_class] += 1

    header_evidence: dict[RunKey, AttributionEvidence] = {}
    for arm, rows in rows_by_arm.items():
        spec = arm_manifest.arms[arm]
        if spec.tool not in _HEADER_TOOLS:
            continue
        for identity, row in rows:
            run_start = _value(row, "run_start")
            if run_start is None:
                continue
            header_evidence[identity] = aperv_evidence(run_start, spec.declaration)

    results: dict[tuple[int, str], GateResult] = {}
    for arm, rows in sorted(rows_by_arm.items()):
        spec = arm_manifest.arms[arm]

        if spec.control:
            results[(GATE_CLEAN_CONTROL, arm)] = _gate_clean_control(
                arm, rows, alpha_signal
            )

        results[(GATE_CORRECT_BINARY, arm)] = _gate_correct_binary(
            arm, spec, rows, header_evidence
        )

        if spec.tool in _HEADER_TOOLS:
            attribution = _gate_attribution_header(arm, rows, header_evidence)
        elif spec.tool in _POLICY_TOOLS:
            attribution = _gate_attribution_policy(arm, spec, rows)
        elif spec.tool in _NEGATIVE_EVIDENCE_TOOLS:
            attribution = _gate_attribution_negative(arm, rows)
        else:
            attribution = GateResult(
                status="not-run",
                evidence_form="none",
                detail=f"no evidence form is defined for the tool {spec.tool!r}",
            )
        results[(GATE_ARM_ATTRIBUTION, arm)] = attribution

        results[(GATE_TASK_INTEGRITY, arm)] = _gate_task_integrity(arm, rows, verdicts)
        results[(GATE_CORPSE_DETECTION, arm)] = _gate_corpse_detection(
            arm, rows, facts, verdicts
        )

    return GateReport(results=results, verdicts=verdicts, corpse_census=dict(census))
