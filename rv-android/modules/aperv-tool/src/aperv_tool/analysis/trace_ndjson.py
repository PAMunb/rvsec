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

The wire format's authority is the other repository — the `event-sink` spec of
`ape`'s `rearch-04-step-ndjson-telemetry`, which owns the `StepRecord` schema,
the dictionary encoding and the omitted-default rules. This reader conforms to
it rather than restating it.

What the reader does for its callers, so that no consumer does it again:

- **Resolves the dictionaries.** `act`, `st` and `out.target` are run-local
  integer IDs defined by earlier `ACT` / `STATE` lines. One forward pass is
  enough because the producing spec (INV-SNK-06) requires definition before
  reference; a reference that is nevertheless unresolved makes the record
  malformed rather than yielding a placeholder string (INV-APV-50).
- **Materializes omitted defaults, but only where absence means a default.**
  The six boosts come back as explicit zeros and the two outcome booleans as
  `False`. `patched` and `cf` are left absent when absent: `patched` is a
  tri-state the jar emits explicitly for both `0` and `1`, so defaulting it
  would erase the difference between "no resolved target" and "natively
  clickable node" (INV-APV-49).
- **Re-derives `activity_has_mop` on both sides.** The jar records that static
  per-activity fact once, on the `ACT` entry, instead of on every step: the
  step side reads `ACT[act].mop`, the outcome side follows
  `out.target -> STATE.act -> ACT.mop`.
- **Expands the run-relative clock.** `t` is milliseconds since `RUN_START`,
  whose record carries the epoch base `t0`. Without a `RUN_START` — a capture
  that began late, or a truncated file — the epoch expansion is reported as
  unavailable and **no base is inferred** from mtime, from the logcat, or from
  anything else (INV-APV-51).
- **Joins the step's own sections.** `dec`, `llm[]` and `out` arrive on one
  record, so the three-way join by `step=` that the retired format forced on
  every consumer ceases to exist. The sub-event keeps every field it was
  written with, prompt and response dumps included.
- **Surfaces the run-level census.** `MOP_DATA`, `PIPELINE` and `LLM_ACK` are
  reader attributes beside `run_start`, because a step-row iterator has no
  natural place for them and this module is the only sanctioned reader — a
  record it skipped would be a record no analysis could reach. `RUN_END` is
  the deliberate exception and has no accessor (D5, INV-APV-53).

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
run's analysis over its last line would be the worse failure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

# Record types carried in the same NDJSON stream that this reader resolves.
# The record types this module reads. `RUN_END` is deliberately absent and has
# no constant: it is write-only by owner decision D5, so no code path here
# reads, validates or acts on it (INV-APV-53), and an accessor would be the
# first step toward the exit contract that decision refuses. It is skipped
# without being counted as malformed, as any unknown future type is.
_TYPE_RUN_START = "RUN_START"
_TYPE_ACT = "ACT"
_TYPE_STATE = "STATE"
_TYPE_MOP_DATA = "MOP_DATA"
_TYPE_PIPELINE = "PIPELINE"
_TYPE_LLM_ACK = "LLM_ACK"

# INV-SNK-11: a trace line is a sink record if and only if it begins with `{`.
# The jar interleaves free-text `[APE] ` diagnostics into the same stdout, so
# those lines are mechanically separable and are skipped without being counted
# as malformed — counting them would report a healthy run as damaged.
_RECORD_PREFIX = "{"

# The six per-mechanism boost fields, in the wire names the sink emits, mapped
# to their row attribute. Absent means zero (INV-SNK-05), and the reader
# materializes that zero so no consumer has to remember the rule.
_BOOST_FIELDS = (
    ("mop", "mop"),
    ("mopf", "mop_frontier"),
    ("wtg", "wtg"),
    ("cov", "coverage"),
    ("menu", "menu"),
    ("form", "form"),
)


@dataclass(frozen=True)
class RunStart:
    """The trace's first record: run identity and the epoch base for every step.

    Attributes:
        run_id: The run's identifier, carried only by the border records
            `RUN_START` and `RUN_END` and never repeated on a step (INV-SNK-04).
        t0_ms: Epoch milliseconds at which the run's clock started. Every step's
            `t` is an offset from this, and it is the only source of an absolute
            timestamp the trace offers.
        params: The run parameters the jar recorded for itself, verbatim. Read
            as provenance, not as a contract: the sink owns their names.
    """

    run_id: str
    t0_ms: int
    params: Dict[str, Any] = field(default_factory=dict)


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
            None when there is no target to look it up from.
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
    """The counterfactual pick, present exactly on the MOP-sensitive channels.

    It answers, per step, what the agent would have chosen with the MOP boosts
    removed — the per-decision evidence that the guidance changed anything.

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
    """The result the platform returned for a component launch.

    A refused intent and an accepted one were the same trace evidence in the
    retired line family; `result` is what distinguishes them.

    Attributes:
        result: The platform's own result code for the launch, passed through
            unaltered — `0` is the accepted case.
        error: The platform's message when it refused. None on acceptance.
    """

    result: int
    error: Optional[str] = None


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
            run's precomputed MOP set. Uniformly False in a MOP-off arm, which
            reports no MOP data at all.
        state_key: Abstract state key, resolved from the `STATE` dictionary.
            Run-local: the key embeds a JVM identity hash and carries no
            meaning outside the process that produced it (INV-APV-36), so it
            joins within a run and never across runs.
        action: The full action string exactly as the agent printed it.
        decision_source: The pipeline stage that selected the action (`src`).
        pick_channel: Label of the channel the pick came through (`ch`).
        priority: Model-action priority. None for non-model actions, which
            carry neither a priority nor any boost.
        mop: MOP-widget boost applied to the pick. Zero when not applied.
        mop_frontier: MOP activity-frontier boost. Zero when not applied.
        wtg: Window-transition-graph boost. Zero when not applied.
        coverage: Coverage boost. Zero when not applied.
        menu: Menu boost. Zero when not applied.
        form: Form boost. Zero when not applied.
        wtg_source: Which pass produced the `wtg` boost — `wtg`, `frontier` or
            `both` — present exactly when `wtg` is non-zero. The boost is a sum
            of two producers (the WTG pass writes it, the frontier pass
            read-modify-writes on top), so the value alone cannot be attributed:
            with both weights at 200 the decisive campaign realises {0,200,400},
            leaving 10,231 steps at 200 ambiguous and only 91 at 400 proving
            both fired. This field de-aliases them; the decision still sums the
            same number into the same field.
        mop_exposure: `(boosted, total)` — how many of the screen's actions the
            MOP widget pass boosted, against how many were eligible at all.
            Present when that pass is constructed. It is the denominator without
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
        counterfactual: The MOP-off counterfactual pick, present exactly on the
            MOP-sensitive pick channels and None everywhere else.
        component: Result of a component launch, present only on the steps that
            dispatched one.
        llm: LLM routing attempts made during this step's selection, in
            occurrence order. Empty when the step made none.
        outcome: What the action produced. None when the record legitimately
            closed with no outcome — which is a different fact from an outcome
            that exists but is unresolved (`StepOutcome.resolved is False`).
    """

    step: int
    t_rel_ms: int
    t_epoch_ms: Optional[int]
    activity: str
    activity_has_mop: bool
    state_key: str
    action: str
    decision_source: str
    pick_channel: str
    priority: Optional[int] = None
    mop: int = 0
    mop_frontier: int = 0
    wtg: int = 0
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
        activities: `ACT` dictionary entries absorbed.
        states: `STATE` dictionary entries absorbed.
    """

    records_read: int = 0
    steps_yielded: int = 0
    malformed: int = 0
    run_start_present: bool = False
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

    def __init__(self, trace_path: Path | str) -> None:
        """Bind the reader to a recorded trace without opening it.

        Construction touches no file, so a reader may be built for a path that
        is not yet readable; the `OSError` arrives at the first iteration.

        Args:
            trace_path: Path to a recorded `.trace` file. Opened read-only and
                never written to (INV-APV-48).

        State:
            self._run_start: The `RUN_START` payload. None until that record is
                consumed, and reset to None at the start of every iteration.
            self._diagnostics: Counters filled as the file is read; complete
                only once iteration is exhausted. Replaced on each iteration.
            self._activities: `ACT` ID -> (activity name, has-MOP flag). Filled
                forward as entries are met, cleared on each iteration.
            self._states: `STATE` ID -> (state key, owning `ACT` ID). Same
                lifecycle as `_activities`.
            self._mop_data, self._pipeline, self._llm_ack: The run-level census
                records, verbatim. Same lifecycle as `_run_start`.
        """
        self._path = Path(trace_path)
        self._run_start: Optional[RunStart] = None
        self._diagnostics = TraceDiagnostics()
        self._activities: Dict[int, Tuple[str, bool]] = {}
        self._states: Dict[int, Tuple[str, int]] = {}
        self._mop_data: Optional[Dict[str, Any]] = None
        self._pipeline: Optional[Dict[str, Any]] = None
        self._llm_ack: Optional[Dict[str, Any]] = None

    @property
    def path(self) -> Path:
        return self._path

    @property
    def run_start(self) -> Optional[RunStart]:
        return self._run_start

    @property
    def diagnostics(self) -> TraceDiagnostics:
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
            OSError: When the file cannot be opened. Nothing else escapes — a
                record that cannot be read increments `diagnostics.malformed`
                and is skipped (INV-APV-50).
        """
        self._run_start = None
        self._diagnostics = TraceDiagnostics()
        self._activities = {}
        self._states = {}
        self._mop_data = None
        self._pipeline = None
        self._llm_ack = None

        # Records are one line each by construction (INV-SNK-01), so line
        # iteration is a safe record boundary: a raw newline can only appear as
        # an escape sequence inside a string value. `errors="replace"` is what
        # keeps a byte-level corruption — the tail of a trace cut mid-write —
        # from aborting the read of every step that precedes it.
        with self._path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line.startswith(_RECORD_PREFIX):
                    # Free-text `[APE] ` diagnostics and blank lines: not sink
                    # records, so not malformed either.
                    continue

                self._diagnostics.records_read += 1
                try:
                    record = json.loads(line)
                except ValueError:
                    # An unparseable line, including the partial final line a
                    # SIGKILL leaves behind.
                    self._diagnostics.malformed += 1
                    continue

                if not isinstance(record, dict):
                    self._diagnostics.malformed += 1
                    continue

                record_type = record.get("type")
                if record_type is not None:
                    self._absorb_typed_record(record_type, record)
                    continue

                try:
                    row = self._build_step_row(record)
                except (UnresolvedReference, KeyError, TypeError, ValueError):
                    self._diagnostics.malformed += 1
                    continue

                self._diagnostics.steps_yielded += 1
                yield row

    def _absorb_typed_record(self, record_type: str, record: Dict[str, Any]) -> None:
        """Fill the ID tables, the run header and the run-level census.

        A dictionary or header entry that is itself unreadable counts as
        malformed, because losing it silently would turn every later reference
        to it into an unresolved one with no explanation.

        Args:
            record_type: The record's `type` member, already known non-None.
            record: The parsed record.
        """
        if record_type == _TYPE_ACT:
            try:
                self._activities[record["id"]] = (
                    record["name"],
                    bool(record.get("mop", 0)),
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
            try:
                self._run_start = RunStart(
                    run_id=record["run_id"],
                    t0_ms=record["t0"],
                    params=record.get("params", {}),
                )
                self._diagnostics.run_start_present = True
            except (KeyError, TypeError):
                self._diagnostics.malformed += 1
        elif record_type == _TYPE_MOP_DATA:
            self._mop_data = _without_type(record)
        elif record_type == _TYPE_PIPELINE:
            self._pipeline = _without_type(record)
        elif record_type == _TYPE_LLM_ACK:
            self._llm_ack = _without_type(record)
        # RUN_END, and any type added later: well-formed and skipped without a
        # malformed count. RUN_END is skipped by decision rather than by
        # omission — D5 makes it write-only, and exposing it would invite the
        # `if not run_end: ...` that is the exit contract that decision refuses
        # (INV-APV-53). The three census records above are not termination
        # signals, so surfacing them creates no such gradient.

    def _activity(self, act_id: int) -> Tuple[str, bool]:
        """Resolve an `ACT` ID to its (name, has-MOP) pair.

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
        every record. A target naming an undefined state is an unresolved
        reference like any other, and takes the malformed branch.

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

        Args:
            record: A parsed step record — a sink record with no `type` member.

        Returns:
            The step with its dictionary references resolved, its omitted
            defaults materialized, and its `llm[]` and `out` sections attached.

        Raises:
            UnresolvedReference: When `act`, `st` or `out.target` names an
                undefined dictionary ID.
            KeyError: When a schema-required member is absent.
            TypeError: When `dec`, `llm` or `out` is present with the wrong
                shape.
        """
        step = record["s"]
        t_rel_ms = record["t"]
        activity, activity_has_mop = self._activity(record["act"])
        state_key, _ = self._state(record["st"])

        dec = record["dec"]
        if not isinstance(dec, dict):
            raise TypeError("dec is not an object")

        # The epoch expansion exists only when the trace said where zero is.
        # Absent RUN_START, the run-relative clock still stands and the absolute
        # one is reported unavailable rather than guessed (INV-APV-51).
        t_epoch_ms = None
        if self._run_start is not None:
            t_epoch_ms = self._run_start.t0_ms + t_rel_ms

        boosts = {attr: dec.get(wire, 0) for wire, attr in _BOOST_FIELDS}

        counterfactual = None
        if "cf" in dec:
            cf = dec["cf"]
            if not isinstance(cf, dict):
                raise TypeError("cf is not an object")
            counterfactual = Counterfactual(
                changed=bool(cf.get("changed", 0)), action=cf.get("a")
            )

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
            # Absent stays absent: `patched` is a tri-state and `cf` is present
            # only on the MOP-sensitive channels (INV-APV-49).
            patched=dec.get("patched"),
            counterfactual=counterfactual,
            component=component,
            llm=tuple(_parse_llm_call(entry) for entry in llm_entries),
            outcome=outcome,
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
