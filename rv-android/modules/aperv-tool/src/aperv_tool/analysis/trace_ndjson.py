"""
Native reader for the stage-4 NDJSON trace.

From stage 4 of the APE-RV re-architecture onward the run's `.trace` is NDJSON:
one `StepRecord` per exploration step, replacing the `[APE-STEP]` /
`[APE-OUTCOME]` / `[APE-LLM-TEL]` `key=value` line family. This module is the
sole mechanism by which analysis code in `aperv-tool` consumes that file. There
is deliberately **no converter in either direction**: reconstructing the retired
format over the primary artifact would make the file everyone opens a derived
reconstruction, and would re-import the unescaped line-breaking defect the jar's
new serializer exists to eliminate.

The wire format's authority is the other repository, in two `ape` changes. The
`event-sink` spec of `rearch-04-step-ndjson-telemetry` owns the `StepRecord`
schema, the dictionary encoding and the omitted-default rules. The `event-sink`
spec of `isolate-guidance-groups` owns the decision members of the
group-isolation jar (`own`, `cfc`, `draw`, `nav`, `inp`, `restart`, `bmc`,
`strat`, `rot`, `buf`, `trig`, `navf`), the meaning of `dec.src` on that jar,
`RUN_START.variant` and the routing counters of `RUN_END`. This reader conforms
to them rather than restating them.

The reader reads two generations of trace, told apart by `RUN_START.v`: `1` is
the `eea2b1a9` jar and earlier, `2` the group-isolation jar. It carries what
each wrote and does not branch on the version; the version is what tells a
consumer which meaning a field has (INV-APV-67).

What the reader does for its callers, so that no consumer does it again:

- **Resolves the dictionaries.** `act`, `st` and `out.target` are run-local
  integer IDs defined by earlier `ACT` / `STATE` lines. One forward pass is
  enough because the producing spec (INV-SNK-06) requires definition before
  reference; a reference that is nevertheless unresolved makes the record
  malformed rather than yielding a placeholder string (INV-APV-50).
- **Materializes omitted defaults, but only where absence means a default.**
  The seven boosts come back as explicit zeros and the two outcome booleans as
  `False`. `patched`, `cf` and every member of the group-isolation jar are left
  absent when absent: `patched` is a tri-state the jar emits explicitly for
  both `0` and `1`, so defaulting it would erase the difference between "no
  resolved target" and "natively clickable node", and a defaulted `own` or
  `cfc` on an `eea2b1a9` trace would claim a mechanism ran that did not exist
  (INV-APV-49).
- **Re-derives `activity_has_mop` on both sides.** The jar records that static
  per-activity fact once, on the `ACT` entry, instead of on every step: the
  step side reads `ACT[act].mop`, the outcome side follows
  `out.target -> STATE.act -> ACT.mop`. The group-isolation jar writes
  `ACT.mop` only when the MOP group is mounted, so an entry without it gives
  None on both sides, never False (INV-APV-68).
- **Expands the run-relative clock.** `t` is milliseconds since `RUN_START`,
  whose record carries the epoch base `t0`. Without a `RUN_START` — a capture
  that began late, or a truncated file — the epoch expansion is reported as
  unavailable and **no base is inferred** from mtime, from the logcat, or from
  anything else (INV-APV-51).
- **Joins the step's own sections.** `dec`, `llm[]` and `out` arrive on one
  record, so the three-way join by `step=` that the retired format forced on
  every consumer ceases to exist. The sub-event keeps every field it was
  written with, prompt and response dumps included, and every `dec` member
  reaches a typed `StepRow` field (INV-APV-58).
- **Carries the whole header and checks the schema it declares.** `RUN_START`
  is the run answering "what am I": the jar, the preset, the cell, the features
  and every parameter someone chose. All fourteen of its members reach the
  caller (INV-APV-61), because a reader that surfaced three of them would leave
  a trace unable to say which jar or which cell produced it — the exact
  blindness `build.sha` was created to end. Its `v` is checked against
  `SUPPORTED_VERSIONS` and any other version is counted, or raised in strict
  mode (INV-APV-62), so a cross-campaign comparison over incomparable fields
  fails loudly. The header is the first sink record rather than the first
  line, since the jar's AOSP banners print to the same stdout ahead of it.
- **Surfaces the run-level census.** `MOP_DATA`, `PIPELINE`, `LLM_ACK` and
  `RUN_END` are reader attributes beside `run_start`, because a step-row
  iterator has no natural place for them and this module is the only
  sanctioned reader — a record it skipped would be a record no analysis could
  reach. Each is carried verbatim and none is interpreted: in particular the
  reader derives no completeness flag from `RUN_END`, whose absence is a fact
  the analysis reports (INV-APV-53).

Two structural properties are worth stating because they are load-bearing
rather than incidental:

**It streams.** The trace is the largest artifact a run produces (~3.5 GB per
880 tasks before compression), so the file is never held in memory — one
forward pass, two small ID tables, one row at a time.

**It never runs on the collection path.** The reader is read-only and
analysis-time only: it opens recorded files, writes none, and requires no
device, emulator or `adb` (INV-APV-48). Nothing in `tools/aperv/tool.py`
imports it, and a test asserts that.

A malformed record is skipped and counted, never raised (INV-APV-50): a trace
cut by a `SIGKILL` ends in a partial line by construction, and losing a whole
run's analysis over its last line would be the worse failure. A record whose
`dec` member has the wrong shape — an `own` that is not an object, a `draw`
that is not a pair — is malformed in the same way; a value the reader does not
know, such as a new SATA path name, is carried as written and is not.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Tuple

# The record types this module reads. Any other type is well-formed and skipped
# without being counted as malformed, so a type the jar adds later does not
# report a healthy trace as damaged.
_TYPE_RUN_START = "RUN_START"
_TYPE_ACT = "ACT"
_TYPE_STATE = "STATE"
_TYPE_MOP_DATA = "MOP_DATA"
_TYPE_PIPELINE = "PIPELINE"
_TYPE_LLM_ACK = "LLM_ACK"
_TYPE_RUN_END = "RUN_END"

# INV-SNK-11: a trace line is a sink record if and only if it begins with `{`.
# The jar interleaves free-text `[APE] ` diagnostics into the same stdout, so
# those lines are mechanically separable and are skipped without being counted
# as malformed — counting them would report a healthy run as damaged.
RECORD_PREFIX = "{"

# The trace schemas this reader reads, checked against every `RUN_START.v`
# (INV-APV-62). They mirror the jar's `RunSpecEcho.FORMAT_VERSION`: 1 is the
# `eea2b1a9` jar and earlier, 2 is the group-isolation jar, which bumped the
# version because `dec.src` changed meaning from the largest boost to the owner
# that executed the step. The check exists because this study's own legacy
# traces already carry incompatible schemas across campaigns — the calibration
# corpus has no `mop_frontier` field and realises `mop=` over {0,300} where the
# decisive campaign realises {0,500} — and neither trace says which it is. A
# declared version outside this set makes the next such comparison fail loudly
# instead of quietly averaging incomparable fields.
SUPPORTED_VERSIONS = frozenset({1, 2})


class SchemaVersionMismatch(Exception):
    """A trace declares a `RUN_START.v` this reader does not implement.

    Raised only in strict mode, and before any row is yielded, so a caller that
    asked for one schema never receives a single row of another. A non-strict
    reader counts the mismatch in `TraceDiagnostics.schema_version_mismatch`
    instead — that is what lets a survey walk a mixed tree and report its
    composition rather than stopping at the first foreign trace.

    Attributes:
        found: The version the trace declared.
        supported: `SUPPORTED_VERSIONS`, the versions this reader implements.
    """

    def __init__(self, found: Any, supported: frozenset) -> None:
        versions = ", ".join(str(version) for version in sorted(supported))
        super().__init__(
            f"trace declares RUN_START.v={found!r}, reader implements {versions}"
        )
        self.found = found
        self.supported = supported


# The seven per-mechanism boost fields, in the wire names the sink emits, mapped
# to their row attribute. Absent means zero (INV-SNK-05), and the reader
# materializes that zero so no consumer has to remember the rule. `navf` is
# written only by the group-isolation jar; on an older trace it reads as the
# zero it would have been.
_BOOST_FIELDS = (
    ("mop", "mop"),
    ("mopf", "mop_frontier"),
    ("wtg", "wtg"),
    ("navf", "nav_frontier"),
    ("cov", "coverage"),
    ("menu", "menu"),
    ("form", "form"),
)


@dataclass(frozen=True)
class BuildStamp:
    """Which jar wrote the trace, and when that jar was built.

    This is the member the whole header record was created for. A stale jar once
    shipped to an entire campaign, its MOP boost fired zero times across 147,153
    evaluations, and nothing in 2,028 tasks' worth of output said which jar had
    run. `sha` is what makes that question answerable from the artifact alone.

    Attributes:
        sha: Git SHA the jar was built from, as `BuildInfo` stamped it. None
            when the record carried no `sha`.
        time: The jar's build timestamp, verbatim. None when absent.
    """

    sha: Optional[str] = None
    time: Optional[str] = None


@dataclass(frozen=True)
class RunStart:
    """The trace's header record: the run specification the jar resolved.

    The jar echoes preset, cell, features, every parameter someone chose and its
    own build into this one record so that a post-hoc audit can say which jar,
    which cell and which parameters produced a trace without opening the
    harness's source in another repository. This class carries all fourteen
    members of it (INV-APV-61): a reader that surfaced three of them would
    reproduce, one layer up, exactly the blindness `build.sha` was created to
    end. No consumer in `aperv_tool` parses `RUN_START` other than through this
    class.

    **Every member is optional and absence is reported, never defaulted.** The
    distinction is not pedantic: `inert=None` means the record did not say,
    while `inert=()` means the jar declared no inert key, and a reader that
    merged the two would answer a provenance question with its own default.

    Attributes:
        v: The record's format version, checked against `SUPPORTED_VERSIONS`
            (INV-APV-62): 1 for the `eea2b1a9` jar and earlier, 2 for the
            group-isolation jar. It is what tells the two meanings of
            `StepRow.decision_source` apart. None when the record carries no
            `v`, in which case the schema is unknown and is not assumed.
        run_id: The run's identifier, carried only by the border records
            `RUN_START` and `RUN_END` and never repeated on a step (INV-SNK-04).
        t0_ms: Epoch milliseconds at which the run's clock started. Every step's
            `t` is an offset from this, and it is the only source of an absolute
            timestamp the trace offers. None leaves every row's epoch expansion
            unavailable rather than based on a guess (INV-APV-51).
        seed: The seed the jar handed the Monkey. It is what makes two
            repetitions of one arm paired trajectories rather than two
            independent draws, so a run whose seed never arrived is a different
            experiment from the one that was planned.
        agent: The agent type the run instantiated, e.g. `sata`.
        preset: The named preset the run resolved from, e.g. `mop`; on the
            group-isolation jar, the cell's preset, e.g. `as_mop_llm`.
        features: The active feature names, sorted by the jar. Features are
            derived from the configuration, whereas the assembled passes depend
            on the APK's substrate — two different arms print identical passes
            on an application with no transitions — so this is the member that
            identifies the arm.
        params: Every parameter someone chose, plus the activation key of each
            active feature, verbatim. Read as provenance, not as a contract: the
            sink owns these names. A key's absence means "at the jar default for
            this `build.sha`", not "unset" — the jar omits defaults precisely
            because the jar `build` names holds them.
        inert: Keys the jar declared inert — set to the neutral value of a
            feature that is not active. Inertia by design is legitimate; an
            inert key outside the arm's expected set means the owning feature
            left the plan.
        corpus_basis: The application list the run was drawn from, when the
            harness supplied one. The jar omits it rather than inventing one,
            because an invented basis is a claim about the sample.
        digest: The run specification's own digest, as the jar computed it.
        props_digest: Digest of the resolved property set.
        build: The jar's identity, or None when the record carried no `build`.
        variant: The cell name the harness passed as `ape.variant`. None on
            every trace written before the group-isolation jar, and when the
            harness passed none.
    """

    v: Optional[int] = None
    run_id: Optional[str] = None
    t0_ms: Optional[int] = None
    seed: Optional[int] = None
    agent: Optional[str] = None
    preset: Optional[str] = None
    features: Optional[Tuple[str, ...]] = None
    params: Optional[Dict[str, Any]] = None
    inert: Optional[Tuple[str, ...]] = None
    corpus_basis: Optional[str] = None
    digest: Optional[str] = None
    props_digest: Optional[str] = None
    build: Optional[BuildStamp] = None
    variant: Optional[str] = None


@dataclass(frozen=True)
class LlmCall:
    """One LLM routing attempt made during a step's selection.

    Completed calls carry coordinates, classes and costs; an abandoned attempt
    carries `result="error"` with `cause`/`detail`; the once-per-episode breaker
    decline carries `result="breaker_open"` with `trips`. Attribution to the
    step is by construction — the entry lives inside its step's record, so there
    is no join key to get wrong.

    Every field is optional because which ones the sink emits depends on how far
    the call got.

    The prompt and response dumps (`sys`, `user`, `resp`, `tool_calls`) ARE
    surfaced, reversing an earlier decision here to omit them as bulk no
    analysis read. They are the bulk of the record, but the jar writes them by
    default and the stage's throughput gate prices their escaping, so a reader
    that dropped them left the run paying their whole cost for data no
    sanctioned consumer could reach — this module being the only sanctioned
    consumer. The analysis that did read them is real: `decompose_nomatch.py`
    pairs each response with the call that produced it to decompose `no_match`
    causes, and that was the gate of a change decision. It reads the frozen
    corpus and stays on the legacy format; its successor over new traces needs
    `resp` from here. If the dumps are ever judged too expensive, the lever is
    the jar's `llmPromptDump` flag — written-and-unreadable is the one state
    that costs everything and returns nothing.

    Attributes:
        call: Call number within the run, as the router counted it.
        mode: Routing hook that made the call, e.g. `new_state`, `stagnation`.
        result: `matched`, `llm_tap` or `no_match` for a completed call;
            `error` for an abandoned one; `breaker_open` for the decline.
        tool: Tool the model invoked, e.g. `click`.
        qwen: Model-space coordinates as `(x, y)` in Qwen3-VL's normalized
            `[0, 1000)` range — not pixels.
        px: The same point in device pixels, after denormalization.
        reason: Why a completed call produced no usable target: `dead_pair`,
            `degenerate` or `boundary`.
        repair: Provenance of the repair form, when the response had to be
            repaired before it would parse.
        matched_class: Widget class the coordinate landed on (`mcls`).
        nearest_class: Class of the closest widget when nothing matched
            (`ncls`), which is what makes a miss diagnosable.
        nearest_dist: Distance in pixels to that closest widget (`ndist`).
        widgets: How many widgets the prompt offered the model.
        tokens: `(input, output)` token counts (`tok`).
        ms: Call latency in milliseconds.
        text: Text the model asked to type, when the tool was a text entry.
        cause: Failure class on `result="error"`, e.g. `timeout`.
        detail: Message accompanying `cause`.
        trips: How many times the breaker had tripped, on
            `result="breaker_open"`.
        system_prompt: The system message sent for this call (`sys`), when the
            jar's prompt-dump flag was on. Named for the retired
            `[APE-LLM-PROMPT] system=` field it replaces.
        user_text: The user message, carrying the rendered widget list
            (`user`). Its embedded newlines survive the trace as escapes, so
            what comes back here is the prompt the model actually saw.
        response: The model's raw response content (`resp`), which is what
            makes a `no_match` diagnosable after the fact.
        tool_calls: The response's native tool-call payload (`tool_calls`),
            when the model returned one.
    """

    call: Optional[int] = None
    mode: Optional[str] = None
    result: Optional[str] = None
    tool: Optional[str] = None
    qwen: Optional[Tuple[int, int]] = None
    px: Optional[Tuple[int, int]] = None
    reason: Optional[str] = None
    repair: Optional[str] = None
    matched_class: Optional[str] = None
    nearest_class: Optional[str] = None
    nearest_dist: Optional[float] = None
    widgets: Optional[int] = None
    tokens: Optional[Tuple[int, int]] = None
    ms: Optional[int] = None
    text: Optional[str] = None
    cause: Optional[str] = None
    detail: Optional[str] = None
    trips: Optional[int] = None
    system_prompt: Optional[str] = None
    user_text: Optional[str] = None
    response: Optional[str] = None
    tool_calls: Optional[str] = None


@dataclass(frozen=True)
class StepOutcome:
    """What the step's action produced, attached when it resolved at step N+1.

    `resolved` is `False` only for the record the teardown flush wrote while the
    step was still in flight. That is a different fact from a record closed with
    no `out` member at all (a restart, a non-model action, a refinement
    discard), which this reader reports as `StepRow.outcome is None`.

    Attributes:
        resolved: False only on the teardown flush's in-flight record. True on
            every outcome the graph update actually closed.
        new_state: Whether the transition landed on a state never seen before.
        target_state: State key the action led to, resolved from the `STATE`
            dictionary. None when the record carried no `target`.
        target_activity: Activity owning `target_state`, reached by the two-hop
            `target -> STATE.act -> ACT.name`. None under the same condition.
        target_activity_has_mop: Whether that landing activity is in the run's
            MOP set. This is the "reached a monitored screen" half of the
            evidential link whose other half is `StepRow.activity_has_mop`.
            None when there is no target to look it up from, or when its `ACT`
            record carries no `mop` (INV-APV-68).
        activity_changed: Whether the transition crossed an Activity boundary,
            as opposed to moving between states of the same one.
    """

    resolved: bool = True
    new_state: bool = False
    target_state: Optional[str] = None
    target_activity: Optional[str] = None
    target_activity_has_mop: Optional[bool] = None
    activity_changed: bool = False


@dataclass(frozen=True)
class Counterfactual:
    """The MOP-off counterfactual pick of the `eea2b1a9` jar (`dec.cf`).

    It answers, per step, what the agent would have chosen with **only the MOP
    boosts** zeroed, so a `changed` value is evidence about MOP guidance and
    about nothing else. It exists only on traces with `RUN_START.v == 1`, where
    it rides the MOP-sensitive pick channels; the group-isolation jar removed
    `dec.cf` and writes the per-scorer `StepRow.scorer_cf` instead.

    Attributes:
        changed: Whether the counterfactual pick diverges from the factual one.
            False also covers the case where the recomputation failed, so a
            False is "no divergence recorded", not "provably identical".
        action: The diverging action string, present only when `changed`.
    """

    changed: bool
    action: Optional[str] = None


@dataclass(frozen=True)
class ComponentDispatch:
    """The result the platform returned for an activity launch (`dec.comp`).

    Written on the launcher's steps only: it is the MOP launcher's
    activity-launch outcome. A component the STATIC trigger fired is a different
    record, `ComponentTrigger`. A refused intent and an accepted one were the
    same trace evidence in the retired line family; `result` is what
    distinguishes them.

    Attributes:
        result: The platform's own result code for the launch, passed through
            unaltered — `0` is the accepted case.
        error: The platform's message when it refused. None on acceptance.
    """

    result: int
    error: Optional[str] = None


@dataclass(frozen=True)
class Ownership:
    """Which mechanism was meant to take the step, and why another did (`dec.own`).

    Written on every step record by the group-isolation jar; absent on the
    `eea2b1a9` jar and earlier. `intended` against `StepRow.decision_source` is
    the pair that shows a fallback: when they differ, `fallback` says why. The
    enumerated values below are the ones the contract lists; the reader carries
    any other as written.

    Attributes:
        intended: The owner that claimed the step (`i`): `budget`, `restart`,
            `llm`, `launcher`, `mop` or `sata`.
        trigger: The LLM stage behind the step (`trg`): `new_state`,
            `stagnation` or `coin`. It names the stage that made the step's one
            LLM call or, when a gate barred the call, the first stage whose
            trigger held. None when neither the intended nor the executed owner
            is `llm`.
        u_llm: The LLM coin's uniform draw for the step (`uL`), drawn whether or
            not the coin was consulted. None when LLM is not mounted.
        u_mop: The MOP coin's uniform draw for the step (`uM`), under the same
            rule. None when MOP is not mounted.
        gate: The gate that barred the LLM call (`g`): `min_actions` or
            `breaker`. None when no gate barred it.
        fallback: Why the intended owner did not take the step (`fb`): `gate`,
            `screenshot` (the LLM screenshot could not be captured, so no call
            was made), `error`, `decline`, `no_match` or `ineligible`. None when
            it did.
    """

    intended: str
    trigger: Optional[str] = None
    u_llm: Optional[float] = None
    u_mop: Optional[float] = None
    gate: Optional[str] = None
    fallback: Optional[str] = None


@dataclass(frozen=True)
class NavTie:
    """How a navigation extension point broke a tie (`dec.nav`).

    The jar writes it only when the point had at least two candidates. The
    wire's `0`/`1` integers become booleans.

    Attributes:
        point: The extension point (`x`): `X1`, `X3` or `X4`.
        component: The variant that decided (`c`): `ape` or `mop`.
        alternative: True only when the MOP variant decided by its own rule
            (`alt`, `ape` D-B14.8); always False at X1 and on cells without MOP.
        drew: Whether the decision was a random draw among equals (`drew`).
    """

    point: str
    component: str
    alternative: bool
    drew: bool


@dataclass(frozen=True)
class ComponentTrigger:
    """The component the STATIC component trigger fired during the step (`dec.trig`).

    A side effect of the step, never its owner: the record's `src` names who took
    the step. `StepRow.component` stays the launcher's activity-launch outcome.

    Attributes:
        kind: `broadcast`, `service` or `provider` (`k`).
        component_class: The fired component's class name (`c`).
    """

    kind: str
    component_class: str


@dataclass(frozen=True)
class StepRow:
    """One fully-joined exploration step, dictionary references resolved.

    This is the module's whole output surface: everything an analysis needs
    about a step is on the row, so no consumer joins, looks up an ID, or
    remembers an omitted-default rule. Where a field is `None`, the absence is
    itself the fact — the reader never substitutes a value it did not read.

    Attributes:
        step: Exploration step counter (`s`), unique and strictly increasing
            within a run (INV-SNK-03).
        t_rel_ms: Milliseconds since the run's clock started.
        t_epoch_ms: Absolute epoch milliseconds, `RUN_START.t0 + t_rel_ms`.
            None when the trace carried no `RUN_START`, in which case no base
            is inferred from anywhere else (INV-APV-51).
        activity: Activity class name, resolved from the `ACT` dictionary.
        activity_has_mop: Whether the activity the step started on is in the
            run's precomputed MOP set. None when the trace's `ACT` record carries
            no `mop`, which the group-isolation jar omits when MOP is not
            mounted (INV-APV-68).
        state_key: Abstract state key, resolved from the `STATE` dictionary.
            Run-local: the key embeds a JVM identity hash and carries no
            meaning outside the process that produced it (INV-APV-36), so it
            joins within a run and never across runs.
        action: The full action string exactly as the agent printed it; on the
            group-isolation jar, the action the step dispatched.
        decision_source: The `src` member, carried as written, with two
            meanings that `RunStart.v` tells apart (INV-APV-67). Under `v == 2`
            (the group-isolation jar) it is the owner that executed the step:
            `budget`, `restart`, `llm`, `launcher`, `mop` or `sata`, which is
            causal. Under `v == 1` (the `eea2b1a9` jar and earlier) it is the
            stage whose boost was largest, e.g. `MOP_WIDGET`, which is not
            causal, because every stage adds into one shared priority. A count
            of this field across traces of both jars counts two different
            things.
        pick_channel: Label of the channel the pick came through (`ch`),
            carried as written. On the group-isolation jar it is `mop_coin`,
            `budget`, `restart`, `launcher`, `llm` or one of SATA's channels
            (`roulette_greedy`, `roulette_early`, `buffer`, `sata_other`); the
            `short_circuit_*` channels appear only under `v == 1`.
        priority: Model-action priority. None for non-model actions, which
            carry neither a priority nor any boost.
        mop: MOP-widget boost applied to the pick. Zero when not applied.
        mop_frontier: MOP activity-frontier boost. Zero when not applied.
        wtg: Window-transition-graph boost. Zero when not applied.
        nav_frontier: Navigation-frontier boost (`navf`, STATIC). Zero when not
            applied, and on every trace of the `eea2b1a9` jar and earlier.
        coverage: Coverage boost. Zero when not applied.
        menu: Menu boost. Zero when not applied.
        form: Form boost. Zero when not applied.
        wtg_source: Which pass produced the `wtg` boost — `wtg`, `frontier` or
            `both` (`wtgsrc`) — present exactly when `wtg` is non-zero, and only
            on traces with `RUN_START.v == 1`; the group-isolation jar writes the
            navigation frontier in its own `navf` field. The boost is a sum
            of two producers (the WTG pass writes it, the frontier pass
            read-modify-writes on top), so the value alone cannot be attributed:
            with both weights at 200 the decisive campaign realises {0,200,400},
            leaving 10,231 steps at 200 ambiguous and only 91 at 400 proving
            both fired. This field de-aliases them; the decision still sums the
            same number into the same field.
        mop_exposure: `(weighted, total)` — how many of the screen's actions
            carry a positive MOP weight, against how many were eligible at all.
            Present when that pass is constructed. It measures the opportunity,
            not the boost: on the group-isolation jar a weighted action whose
            key was already tried gets no boost and is still counted, while on
            the `eea2b1a9` jar every weighted action was boosted, so the two
            readings coincide there. It is the denominator without
            which "the MOP scorer fired on 0.4% of decisions" cannot be split
            into "the mechanism had no opportunity" and "it had one and lost the
            roulette". It rides the step rather than the `STATE` entry because
            the pair is not constant per abstract state — 14 of 25 campaign
            traces show a state with more than one realised pair.
        patched: Tri-state clickability provenance of the action's target node:
            `1` when the GUI-tree patch wrote that node's clickability, `0`
            when it was read from the accessibility node, None when the action
            has no resolved target at all (`MODEL_BACK`, `MODEL_MENU`,
            `MODEL_LLM_TAP`). The None is never collapsed into `0`
            (INV-APV-49). Read causally only for `MODEL_CLICK`.
        counterfactual: The MOP-off counterfactual pick (`cf`), present exactly
            on the MOP-sensitive pick channels of a `v == 1` trace and None
            everywhere else, including every step of the group-isolation jar.
        component: The launcher's activity-launch outcome (`comp`), present
            only on the steps that dispatched one.
        llm: LLM routing attempts made during this step's selection, in
            occurrence order. Empty when the step made none.
        outcome: What the action produced. None when the record legitimately
            closed with no outcome — which is a different fact from an outcome
            that exists but is unresolved (`StepOutcome.resolved is False`).
        owner: The owner record (`own`), written on every step of the
            group-isolation jar. None on the `eea2b1a9` jar and earlier.
        scorer_cf: Per-scorer counterfactual (`cfc`), scorer name -> whether
            zeroing that one scorer on every candidate, replaying the same draw
            index, would have changed the pick at a roulette or least-visited
            site. On the least-visited pick the candidates are the tied
            least-visited actions, and the jar writes `cfc` only when two or more
            tied. It answers "did this scorer change the choice", one scorer at
            a time; it does not answer "did the guidance as a whole change it".
            None when absent, which is every step outside those sites and every
            least-visited pick with a single least-visited action.
        draw: `(index, total)` the roulette drew (`draw`), enough to replay the
            pick offline. None when the pick was not a roulette.
        nav: The extension-point tie record (`nav`). None when no extension
            point decided between two or more candidates.
        input_source: Origin of the text the action entered (`inp`): `typed`,
            `heuristic`, `random`, `form` or `llm`. None when it entered none.
        restart_kind: Which restart the RESTART guard made (`restart`):
            `graph`, `state`, `activity` or `periodic`. None unless
            `decision_source` is `restart`.
        back_menu_capped: Candidates the BACK/MENU cap removed from the pick
            (`bmc`). None when absent, which is how the jar writes 0.
        sata_path: The SATA path that picked the action (`strat`), one of the
            fifteen path names the contract lists or any later one. None unless
            `decision_source` is `sata`.
        rotation: Display rotation at step open (`rot`), `0..3`, or `-1` when
            it could not be read. Written on every step of the group-isolation
            jar, `0` included, so `0` is a reading and None means the jar wrote
            no rotation at all.
        buffer_abandoned_by: The owner that took the step while the SATA buffer
            was non-empty and abandoned it (`buf`). None when no buffer was
            abandoned.
        component_trigger: The component the STATIC trigger fired during the
            step (`trig`), whatever the step's owner. None when it fired none.
        mop_distance: Distance of the nearest unretired MOP target that gave the
            chosen action its weight (`mopd`), `0..3`; `0` means the handler is
            itself a target. None when the action has no distance-based weight.
        mop_stamp: Source of the chosen action's MOP lookup (`mops`): `s` for
            the handler stamp, `i` for the resource-id key. None when the lookup
            had no source or the action no resolved target.
        retired_targets: Indices into `MOP_DATA.targets` of the targets this
            step's action retired (`ret`), ascending. None when it retired none.
        mop_handler: Binary class name of the handler stamp that answered the
            chosen action's MOP lookup (`hnd`), written exactly when
            `mop_stamp` is `s`. None otherwise, and on every step of a cell
            without MOP.
        fuzz_events: Kinds of the gesture events the step's fuzz action
            queued (`fz`), in order: `rotation`, `app_switch`, `key`,
            `trackball`, `drag`, `pinch` or `click`. `()` when fuzzing fired
            and queued nothing; None when the step did not fuzz.
    """

    step: int
    t_rel_ms: int
    t_epoch_ms: Optional[int]
    activity: str
    activity_has_mop: Optional[bool]
    state_key: str
    action: str
    decision_source: str
    pick_channel: str
    priority: Optional[int] = None
    mop: int = 0
    mop_frontier: int = 0
    wtg: int = 0
    nav_frontier: int = 0
    coverage: int = 0
    menu: int = 0
    form: int = 0
    wtg_source: Optional[str] = None
    mop_exposure: Optional[Tuple[int, int]] = None
    patched: Optional[int] = None
    counterfactual: Optional[Counterfactual] = None
    component: Optional[ComponentDispatch] = None
    llm: Tuple[LlmCall, ...] = ()
    outcome: Optional[StepOutcome] = None
    owner: Optional[Ownership] = None
    scorer_cf: Optional[Mapping[str, bool]] = None
    draw: Optional[Tuple[int, int]] = None
    nav: Optional[NavTie] = None
    input_source: Optional[str] = None
    restart_kind: Optional[str] = None
    back_menu_capped: Optional[int] = None
    sata_path: Optional[str] = None
    rotation: Optional[int] = None
    buffer_abandoned_by: Optional[str] = None
    component_trigger: Optional[ComponentTrigger] = None
    mop_distance: Optional[int] = None
    mop_stamp: Optional[str] = None
    retired_targets: Optional[Tuple[int, ...]] = None
    mop_handler: Optional[str] = None
    fuzz_events: Optional[Tuple[str, ...]] = None


@dataclass
class TraceDiagnostics:
    """What the read itself encountered, so a caller can report it.

    `malformed` is the count this reader exists to make visible rather than
    swallow: it is how a truncated capture or a schema drift announces itself
    to an analysis that would otherwise quietly compute over fewer steps.

    Attributes:
        records_read: Sink records seen, i.e. lines beginning with `{`. The
            jar's free-text `[APE] ` diagnostics are not counted here at all.
        steps_yielded: Rows actually emitted. Below `records_read` by the
            dictionary and run-level records plus anything malformed.
        malformed: Records dropped as unreadable — unparseable JSON, a
            non-object, a missing required field, or a dictionary reference no
            earlier record defined. One is expected at the tail of a trace cut
            by a `SIGKILL`; a larger count means damage or schema drift.
        run_start_present: Whether a `RUN_START` was consumed. False makes
            every row's `t_epoch_ms` None.
        schema_version_mismatch: How many times the header declared a `v`
            outside `SUPPORTED_VERSIONS` — at most one per trace, so over a survey of
            many traces it is the count of foreign ones. It stays 0 when the
            header carries no `v` at all, because unknown is not mismatched.
            A strict reader raises instead of reaching a non-zero value here
            (INV-APV-62).
        activities: `ACT` dictionary entries absorbed.
        states: `STATE` dictionary entries absorbed.
    """

    records_read: int = 0
    steps_yielded: int = 0
    malformed: int = 0
    run_start_present: bool = False
    schema_version_mismatch: int = 0
    activities: int = 0
    states: int = 0


def _as_int_pair(value: Any) -> Optional[Tuple[int, int]]:
    """Coerce a two-element wire array (`qwen`, `px`, `tok`, `mopx`) to a tuple.

    Anything that is not a two-element list becomes None rather than a partial
    pair, so a consumer never reads half a coordinate as a whole one.
    """
    if isinstance(value, list) and len(value) == 2:
        return (value[0], value[1])
    return None


def _as_str_tuple(value: Any) -> Optional[Tuple[str, ...]]:
    """Freeze a wire array of names (`features`, `inert`) into a tuple.

    Anything that is not a list stays None, which keeps "the record did not say"
    distinct from "the jar declared an empty list" — the difference between not
    knowing an arm's features and knowing it had none.
    """
    if isinstance(value, list):
        return tuple(value)
    return None


def _require_object(dec: Dict[str, Any], member: str) -> Dict[str, Any]:
    """Return the `dec` member that the contract writes as a JSON object.

    Raises `TypeError` when it is anything else, so a wrongly shaped member
    joins the malformed count instead of reaching a field half-read
    (INV-APV-50).
    """
    value = dec[member]
    if not isinstance(value, dict):
        raise TypeError(f"{member} is not an object")
    return value


def _parse_ownership(own: Dict[str, Any]) -> Ownership:
    """Build the owner record from `dec.own`; `i` is required, the rest optional."""
    return Ownership(
        intended=own["i"],
        trigger=own.get("trg"),
        u_llm=own.get("uL"),
        u_mop=own.get("uM"),
        gate=own.get("g"),
        fallback=own.get("fb"),
    )


def _parse_nav_tie(nav: Dict[str, Any]) -> NavTie:
    """Build the tie record from `dec.nav`, whose four members are all required.

    `alt` and `drew` are `0`/`1` on the wire and become booleans here; the
    values are not otherwise checked, as no enumerated member is.
    """
    return NavTie(
        point=nav["x"],
        component=nav["c"],
        alternative=bool(nav["alt"]),
        drew=bool(nav["drew"]),
    )


def _parse_draw(value: Any) -> Tuple[int, int]:
    """Freeze `dec.draw` into `(index, total)`.

    Unlike `_as_int_pair`, which reads optional coordinates, a `draw` that is
    not a two-element array raises `TypeError`: the member exists only to make
    the pick replayable, and half of it replays nothing.
    """
    if not isinstance(value, list) or len(value) != 2:
        raise TypeError("draw is not an [index, total] pair")
    return (value[0], value[1])


def _parse_array(dec: Dict[str, Any], key: str) -> Optional[Tuple[Any, ...]]:
    """Freeze the array `dec[key]` into a tuple, None when the member is absent.

    Anything but an array raises `TypeError`, which makes the record malformed.
    """
    if key not in dec:
        return None
    value = dec[key]
    if not isinstance(value, list):
        raise TypeError(f"{key} is not an array")
    return tuple(value)


def _without_type(record: Dict[str, Any]) -> Dict[str, Any]:
    """Copy a run-level record without its discriminator.

    The copy matters: the caller receives a mapping it can hold or mutate
    without reaching back into the reader's state, which is the same isolation
    every `StepRow` already has by being frozen.
    """
    return {key: value for key, value in record.items() if key != "type"}


def _parse_llm_call(entry: Dict[str, Any]) -> LlmCall:
    """Build one `LlmCall` from an `llm[]` entry, keeping absent fields absent.

    Raises `TypeError` when the entry is not an object, so a damaged record joins
    the malformed count instead of aborting the read (INV-APV-50). The list itself
    is checked by the caller; this is the per-entry half of the same rule.
    """
    if not isinstance(entry, dict):
        raise TypeError("llm entry is not an object")
    return LlmCall(
        call=entry.get("call"),
        mode=entry.get("mode"),
        result=entry.get("result"),
        tool=entry.get("tool"),
        qwen=_as_int_pair(entry.get("qwen")),
        px=_as_int_pair(entry.get("px")),
        reason=entry.get("reason"),
        repair=entry.get("repair"),
        matched_class=entry.get("mcls"),
        nearest_class=entry.get("ncls"),
        nearest_dist=entry.get("ndist"),
        widgets=entry.get("widgets"),
        tokens=_as_int_pair(entry.get("tok")),
        ms=entry.get("ms"),
        text=entry.get("text"),
        cause=entry.get("cause"),
        detail=entry.get("detail"),
        trips=entry.get("trips"),
        system_prompt=entry.get("sys"),
        user_text=entry.get("user"),
        response=entry.get("resp"),
        tool_calls=entry.get("tool_calls"),
    )


class UnresolvedReference(Exception):
    """A record referenced a dictionary ID no earlier record defined.

    Raised internally and converted into a malformed count by the read loop.
    The producing spec forbids this ordering (INV-SNK-06), so it means the trace
    is damaged or the schema drifted — either way the honest response is to drop
    the record and say so, never to substitute a placeholder string that would
    flow into an analysis indistinguishable from a real activity name.
    """


class TraceReader:
    """Stream a stage-4 NDJSON trace, yielding one joined `StepRow` per step.

    Read-only and offline. Iteration is a single forward pass: the `ACT` and
    `STATE` tables are filled as their records are encountered, and every
    reference is resolved at the moment it is read. Reading twice re-opens the
    file and starts over.

    Preconditions: `trace_path` exists and is readable.
    Postconditions: rows come in file order; `diagnostics` is complete once
    iteration is exhausted; `run_start` is populated as soon as the `RUN_START`
    line has been consumed.
    Errors: `OSError` if the file cannot be opened. Nothing else propagates.
    """

    def __init__(self, trace_path: Path | str, *, strict: bool = False) -> None:
        """Bind the reader to a recorded trace without opening it.

        Construction touches no file, so a reader may be built for a path that
        is not yet readable; the `OSError` arrives at the first iteration.

        Args:
            trace_path: Path to a recorded `.trace` file. Opened read-only and
                never written to (INV-APV-48).
            strict: Whether a header declaring a foreign `RUN_START.v` aborts
                the read with `SchemaVersionMismatch` instead of being counted
                (INV-APV-62). The default is non-strict because a survey over a
                mixed tree should report its composition rather than stop at the
                first foreign trace; an analysis that compares fields across
                traces should ask for strict, since that comparison is exactly
                what a schema change invalidates.

        State:
            self._run_start: The `RUN_START` payload. None until that record is
                consumed, and reset to None at the start of every iteration.
            self._diagnostics: Counters filled as the file is read; complete
                only once iteration is exhausted. Replaced on each iteration.
            self._activities: `ACT` ID -> (activity name, has-MOP flag), the
                flag None when the entry carries no `mop`. Filled forward as
                entries are met, cleared on each iteration.
            self._states: `STATE` ID -> (state key, owning `ACT` ID). Same
                lifecycle as `_activities`.
            self._mop_data, self._pipeline, self._llm_ack, self._run_end: The
                run-level census records, verbatim. Same lifecycle as
                `_run_start`.
        """
        self._path = Path(trace_path)
        self._strict = strict
        self._run_start: Optional[RunStart] = None
        self._diagnostics = TraceDiagnostics()
        self._activities: Dict[int, Tuple[str, Optional[bool]]] = {}
        self._states: Dict[int, Tuple[str, int]] = {}
        self._mop_data: Optional[Dict[str, Any]] = None
        self._pipeline: Optional[Dict[str, Any]] = None
        self._llm_ack: Optional[Dict[str, Any]] = None
        self._run_end: Optional[Dict[str, Any]] = None

    @property
    def path(self) -> Path:
        """The trace file this reader is bound to."""
        return self._path

    @property
    def run_start(self) -> Optional[RunStart]:
        """The trace's header, or None until — or unless — it has been read.

        Populated as soon as the first sink record is consumed, so a caller that
        needs only the header can stop after the first row.
        """
        return self._run_start

    @property
    def diagnostics(self) -> TraceDiagnostics:
        """The counters of the current read, complete once iteration ends."""
        return self._diagnostics

    @property
    def mop_data(self) -> Optional[Dict[str, Any]]:
        """The `MOP_DATA` load census, verbatim, or None if the trace has none.

        Returned as the record wrote it — minus its `type` — rather than as a
        dataclass, for the reason `RunStart.params` gives: the sink owns these
        names, and mirroring the census here would create a second place that
        has to be kept in step with it.

        `wtgEdges` is the field to read for whether the frontier passes could
        run at all: it counts the click-only WTG view the three passes gate on,
        which is NOT the flat `transitions` list the retired `[APE-MOP-DATA]`
        line reported and which was read as the gate for months.
        """
        return self._mop_data

    @property
    def pipeline(self) -> Optional[Dict[str, Any]]:
        """The `PIPELINE` assembly provenance, verbatim, or None.

        `passes` lists what was constructed; `candidates` lists every candidate
        with whether it was. The second is what makes the first readable as a
        data-dependent outcome rather than a configuration echo — without it,
        "the arm turned this off" and "this application's data could not
        support it" are the same evidence, which they were across 25 of the
        decisive campaign's 40 applications.
        """
        return self._pipeline

    @property
    def run_end(self) -> Optional[Dict[str, Any]]:
        """The `RUN_END` record minus `type`, verbatim, or None.

        `counters` is the per-run census of the mechanisms the cell mounted: on the
        group-isolation jar `launches`, `gateMinActions`, `gateBreaker`, `guardBacks`,
        `bufAbandoned`, `restarts`, `coinLlm`, `coinMop` and `nullRelaunches` (the
        null-tree recoveries that relaunched the app, which are not steps and have no
        step record) beside `acts`, `states`, `stampNodes`, `stampHits`, `retired` and
        the LLM aggregates. The reader exposes the record without interpreting it and
        derives no completeness flag or status from it (INV-APV-53): a trace cut by a
        `SIGKILL` legitimately has none, and None here is that fact, reported, not
        repaired. The collection path never reads it.
        """
        return self._run_end

    @property
    def llm_ack(self) -> Optional[Dict[str, Any]]:
        """The `LLM_ACK` record, verbatim, or None when no call ever succeeded.

        `server_model` is what the server actually served, against the model
        `RUN_START.params` says the run asked for. Its absence is itself
        diagnostic: a run with zero successful responses emits none.
        """
        return self._llm_ack

    def __iter__(self) -> Iterator[StepRow]:
        """Stream the trace once, yielding one row per well-formed step record.

        The dictionaries and the diagnostics are reset first, so iterating a
        second time re-reads the file from scratch rather than resuming with
        stale ID tables. Because the counters are filled as the pass proceeds,
        `diagnostics` is only trustworthy once the iterator is exhausted.

        Yields:
            One `StepRow` per step record, in file order, with every dictionary
            reference already resolved.

        Raises:
            OSError: When the file cannot be opened.
            SchemaVersionMismatch: In strict mode only, when the header
                declares a foreign `RUN_START.v` — raised before the first row,
                so no caller receives a partial read of a schema it rejected.
                Nothing else escapes: a record that cannot be read increments
                `diagnostics.malformed` and is skipped (INV-APV-50).
        """
        self._run_start = None
        self._diagnostics = TraceDiagnostics()
        self._activities = {}
        self._states = {}
        self._mop_data = None
        self._pipeline = None
        self._llm_ack = None
        self._run_end = None

        # Records are one line each by construction (INV-SNK-01), so line
        # iteration is a safe record boundary: a raw newline can only appear as
        # an escape sequence inside a string value. `errors="replace"` is what
        # keeps a byte-level corruption — the tail of a trace cut mid-write —
        # from aborting the read of every step that precedes it.
        # The header is the trace's first sink record, not its first line: the
        # jar's own AOSP banners are printed to the same stdout and routinely
        # precede it. Only that first record is a candidate, which is what makes
        # a later `RUN_START` — the signature of two runs' output concatenated
        # into one file — visible as not-this-trace's-header instead of silently
        # overwriting the specification the steps were produced under.
        header_pending = True

        with self._path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line.startswith(RECORD_PREFIX):
                    # Free-text `[APE] ` diagnostics and blank lines: not sink
                    # records, so not malformed either.
                    continue

                self._diagnostics.records_read += 1
                try:
                    record = json.loads(line)
                except ValueError:
                    # An unparseable line, including the partial final line a
                    # SIGKILL leaves behind. It does not consume the header
                    # slot: a damaged first record says nothing about which
                    # record the header is.
                    self._diagnostics.malformed += 1
                    continue

                if not isinstance(record, dict):
                    self._diagnostics.malformed += 1
                    continue

                record_type = record.get("type")
                if record_type is not None:
                    self._absorb_typed_record(record_type, record, header_pending)
                    header_pending = False
                    continue

                header_pending = False
                try:
                    row = self._build_step_row(record)
                except (UnresolvedReference, KeyError, TypeError, ValueError):
                    self._diagnostics.malformed += 1
                    continue

                self._diagnostics.steps_yielded += 1
                yield row

    def _absorb_typed_record(
        self, record_type: str, record: Dict[str, Any], is_header_candidate: bool
    ) -> None:
        """Fill the ID tables, the run header and the run-level census.

        A dictionary entry that is itself unreadable counts as malformed,
        because losing it silently would turn every later reference to it into
        an unresolved one with no explanation.

        Args:
            record_type: The record's `type` member, already known non-None.
            record: The parsed record.
            is_header_candidate: Whether this is the trace's first sink record,
                the only position at which a `RUN_START` is this trace's header.

        Raises:
            SchemaVersionMismatch: In strict mode, when the header declares a
                `v` outside `SUPPORTED_VERSIONS`.
        """
        if record_type == _TYPE_ACT:
            # The group-isolation jar writes `mop` only when the MOP group is
            # mounted, so an entry without it is a fact not computed, kept None
            # rather than read as False (INV-APV-68).
            mop = record.get("mop")
            try:
                self._activities[record["id"]] = (
                    record["name"],
                    None if mop is None else bool(mop),
                )
                self._diagnostics.activities += 1
            except (KeyError, TypeError):
                self._diagnostics.malformed += 1
        elif record_type == _TYPE_STATE:
            try:
                self._states[record["id"]] = (record["key"], record["act"])
                self._diagnostics.states += 1
            except (KeyError, TypeError):
                self._diagnostics.malformed += 1
        elif record_type == _TYPE_RUN_START:
            if is_header_candidate:
                self._absorb_header(record)
        elif record_type == _TYPE_MOP_DATA:
            self._mop_data = _without_type(record)
        elif record_type == _TYPE_PIPELINE:
            self._pipeline = _without_type(record)
        elif record_type == _TYPE_LLM_ACK:
            self._llm_ack = _without_type(record)
        elif record_type == _TYPE_RUN_END:
            self._run_end = _without_type(record)
        # A RUN_START outside the header position, and any type added later:
        # well-formed and skipped without a malformed count.

    def _absorb_header(self, record: Dict[str, Any]) -> None:
        """Read the whole `RUN_START` record and check the schema it declares.

        Nothing here can fail on an absent member: all fourteen are optional by
        design, and reporting one absent is the honest answer to "what did this
        run say about itself" (INV-APV-61). What can fail is the schema check,
        and only in strict mode.

        Args:
            record: The parsed `RUN_START`, known to be the first sink record.

        Raises:
            SchemaVersionMismatch: In strict mode, when `v` is present and is
                not in `SUPPORTED_VERSIONS`.
        """
        build = record.get("build")
        self._run_start = RunStart(
            v=record.get("v"),
            run_id=record.get("run_id"),
            t0_ms=record.get("t0"),
            seed=record.get("seed"),
            agent=record.get("agent"),
            preset=record.get("preset"),
            features=_as_str_tuple(record.get("features")),
            params=record.get("params"),
            inert=_as_str_tuple(record.get("inert")),
            corpus_basis=record.get("corpus_basis"),
            digest=record.get("digest"),
            props_digest=record.get("props_digest"),
            build=(
                BuildStamp(sha=build.get("sha"), time=build.get("time"))
                if isinstance(build, dict)
                else None
            ),
            variant=record.get("variant"),
        )
        self._diagnostics.run_start_present = True

        # A header with no `v` reports the version unknown, and unknown is not
        # mismatched: the reader does not infer a version from the fields it
        # happens to recognise (INV-APV-51 applies to the schema too).
        version = self._run_start.v
        if version is not None and version not in SUPPORTED_VERSIONS:
            self._diagnostics.schema_version_mismatch += 1
            if self._strict:
                raise SchemaVersionMismatch(version, SUPPORTED_VERSIONS)

    def _activity(self, act_id: int) -> Tuple[str, Optional[bool]]:
        """Resolve an `ACT` ID to its (name, has-MOP) pair, the flag possibly None.

        Raises:
            UnresolvedReference: When no earlier `ACT` record defined the ID.
        """
        try:
            return self._activities[act_id]
        except KeyError:
            raise UnresolvedReference(f"no ACT record defines id {act_id}")

    def _state(self, state_id: int) -> Tuple[str, int]:
        """Resolve a `STATE` ID to its (state key, owning `ACT` ID) pair.

        Raises:
            UnresolvedReference: When no earlier `STATE` record defined the ID.
        """
        try:
            return self._states[state_id]
        except KeyError:
            raise UnresolvedReference(f"no STATE record defines id {state_id}")

    def _build_outcome(self, out: Dict[str, Any]) -> StepOutcome:
        """Resolve the outcome section, re-deriving its activity's MOP flag.

        The outcome-side flag is a two-hop lookup — `target -> STATE.act ->
        ACT.mop` — because the jar records it once per activity rather than on
        every record; it is None when that `ACT` entry carries no `mop`. A
        target naming an undefined state is an unresolved reference like any
        other, and takes the malformed branch.

        Args:
            out: The record's `out` member, already known to be an object.

        Returns:
            The outcome with its three target-derived fields resolved, or left
            None together when the record carried no `target`.

        Raises:
            UnresolvedReference: When `target`, or the activity it leads to,
                was never defined by an earlier record.
        """
        target_state = target_activity = None
        target_has_mop = None

        target_id = out.get("target")
        if target_id is not None:
            state_key, act_id = self._state(target_id)
            activity_name, activity_has_mop = self._activity(act_id)
            target_state = state_key
            target_activity = activity_name
            target_has_mop = activity_has_mop

        return StepOutcome(
            # `resolved` is emitted explicitly, and only as `false`, by the
            # teardown flush. Its absence on a normal record means resolved.
            resolved=bool(out.get("resolved", True)),
            new_state=bool(out.get("new_state", False)),
            target_state=target_state,
            target_activity=target_activity,
            target_activity_has_mop=target_has_mop,
            activity_changed=bool(out.get("act_changed", False)),
        )

    def _build_step_row(self, record: Dict[str, Any]) -> StepRow:
        """Assemble one `StepRow`, raising on anything that makes it malformed.

        Nothing here is defensive: the envelope, `dec.a`, `dec.src` and `dec.ch`
        are required by the schema, so their absence is subscripted directly and
        the `KeyError` becomes the caller's malformed count. Guarding them would
        only produce a row that is missing the fields an analysis reads.

        The optional `dec` members are read only when present, and a present
        one with the wrong shape — `cf`, `own`, `nav`, `trig` or `cfc` that is
        not an object, `draw` that is not a pair, `ret` that is not an array,
        or an object lacking a member its type requires — raises, so the record
        is malformed. The enumerated values inside them are carried as written
        and never checked against a list: a new owner or SATA path on the jar
        side is a well-formed record, and the malformed count exists for
        damaged lines (INV-APV-50).

        Args:
            record: A parsed step record — a sink record with no `type` member.

        Returns:
            The step with its dictionary references resolved, its omitted
            defaults materialized, and its `llm[]` and `out` sections attached.

        Raises:
            UnresolvedReference: When `act`, `st` or `out.target` names an
                undefined dictionary ID.
            KeyError: When a schema-required member is absent, at the top
                level or inside a present `comp`, `own`, `nav` or `trig`.
            TypeError: When `dec`, `llm`, `out` or a structured `dec` member is
                present with the wrong shape.
        """
        step = record["s"]
        t_rel_ms = record["t"]
        activity, activity_has_mop = self._activity(record["act"])
        state_key, _ = self._state(record["st"])

        dec = record["dec"]
        if not isinstance(dec, dict):
            raise TypeError("dec is not an object")

        # The epoch expansion exists only when the trace said where zero is —
        # which takes both a header and a `t0` on it. Without either, the
        # run-relative clock still stands and the absolute one is reported
        # unavailable rather than guessed (INV-APV-51).
        t_epoch_ms = None
        if self._run_start is not None and self._run_start.t0_ms is not None:
            t_epoch_ms = self._run_start.t0_ms + t_rel_ms

        boosts = {attr: dec.get(wire, 0) for wire, attr in _BOOST_FIELDS}

        counterfactual = None
        if "cf" in dec:
            cf = _require_object(dec, "cf")
            counterfactual = Counterfactual(
                changed=bool(cf.get("changed", 0)), action=cf.get("a")
            )

        owner = None
        if "own" in dec:
            owner = _parse_ownership(_require_object(dec, "own"))

        nav = None
        if "nav" in dec:
            nav = _parse_nav_tie(_require_object(dec, "nav"))

        component_trigger = None
        if "trig" in dec:
            trig = _require_object(dec, "trig")
            component_trigger = ComponentTrigger(
                kind=trig["k"], component_class=trig["c"]
            )

        # `cfc` values are `0`/`1` on the wire, read as booleans.
        scorer_cf = None
        if "cfc" in dec:
            scorer_cf = {
                scorer: bool(changed)
                for scorer, changed in _require_object(dec, "cfc").items()
            }

        draw = _parse_draw(dec["draw"]) if "draw" in dec else None
        retired = _parse_array(dec, "ret")
        fuzz_events = _parse_array(dec, "fz")

        component = None
        if "comp" in dec:
            comp = dec["comp"]
            component = ComponentDispatch(result=comp["r"], error=comp.get("e"))

        llm_entries = record.get("llm") or []
        if not isinstance(llm_entries, list):
            raise TypeError("llm is not an array")

        outcome = None
        if "out" in record:
            out = record["out"]
            if not isinstance(out, dict):
                raise TypeError("out is not an object")
            outcome = self._build_outcome(out)

        return StepRow(
            step=step,
            t_rel_ms=t_rel_ms,
            t_epoch_ms=t_epoch_ms,
            activity=activity,
            activity_has_mop=activity_has_mop,
            state_key=state_key,
            action=dec["a"],
            decision_source=dec["src"],
            pick_channel=dec["ch"],
            priority=dec.get("pri"),
            wtg_source=dec.get("wtgsrc"),
            mop_exposure=_as_int_pair(dec.get("mopx")),
            # Absent stays absent: `patched` is a tri-state, `cf` is present
            # only on the MOP-sensitive channels, and every member of the
            # group-isolation jar is absent on older traces (INV-APV-49).
            patched=dec.get("patched"),
            counterfactual=counterfactual,
            component=component,
            llm=tuple(_parse_llm_call(entry) for entry in llm_entries),
            outcome=outcome,
            owner=owner,
            scorer_cf=scorer_cf,
            draw=draw,
            nav=nav,
            input_source=dec.get("inp"),
            restart_kind=dec.get("restart"),
            back_menu_capped=dec.get("bmc"),
            sata_path=dec.get("strat"),
            rotation=dec.get("rot"),
            buffer_abandoned_by=dec.get("buf"),
            component_trigger=component_trigger,
            mop_distance=dec.get("mopd"),
            mop_stamp=dec.get("mops"),
            retired_targets=retired,
            mop_handler=dec.get("hnd"),
            fuzz_events=fuzz_events,
            **boosts,
        )


def read_steps(trace_path: Path | str) -> List[StepRow]:
    """Read a whole trace into a list. For callers that want the rows at once.

    Streaming is the default because the trace is large; this convenience exists
    for the consumers that genuinely need random access by step, and it is their
    choice to pay the memory.

    Note that the reader is discarded with the list, so a caller who also needs
    `diagnostics` or `run_start` must build a `TraceReader` itself.

    Args:
        trace_path: Path to a recorded `.trace` file. Opened read-only.

    Returns:
        Every well-formed step, in file order. Malformed records are absent
        with no trace of their number, which is the cost of dropping the
        reader.

    Raises:
        OSError: When the file cannot be opened.
    """
    return list(TraceReader(trace_path))
