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
  every consumer ceases to exist.

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
# Every other `type` (MOP_DATA, PIPELINE, LLM_ACK, RUN_END) is well-formed
# output that this module has no business reading: it is skipped silently and
# is NOT counted as malformed. RUN_END in particular is write-only by owner
# decision D5 — no code path here reads, validates or acts on it (INV-APV-53).
_TYPE_RUN_START = "RUN_START"
_TYPE_ACT = "ACT"
_TYPE_STATE = "STATE"

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
    """The trace's first record: run identity and the epoch base for every step."""

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


@dataclass(frozen=True)
class StepOutcome:
    """What the step's action produced, attached when it resolved at step N+1.

    `resolved` is `False` only for the record the teardown flush wrote while the
    step was still in flight. That is a different fact from a record closed with
    no `out` member at all (a restart, a non-model action, a refinement
    discard), which this reader reports as `StepRow.outcome is None`.
    """

    resolved: bool = True
    new_state: bool = False
    target_state: Optional[str] = None
    target_activity: Optional[str] = None
    target_activity_has_mop: Optional[bool] = None
    activity_changed: bool = False


@dataclass(frozen=True)
class Counterfactual:
    """The counterfactual pick, present exactly on the MOP-sensitive channels."""

    changed: bool
    action: Optional[str] = None


@dataclass(frozen=True)
class ComponentDispatch:
    """The result the platform returned for a component launch.

    A refused intent and an accepted one were the same trace evidence in the
    retired line family; `result` is what distinguishes them.
    """

    result: int
    error: Optional[str] = None


@dataclass(frozen=True)
class StepRow:
    """One fully-joined exploration step, dictionary references resolved."""

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
    """

    records_read: int = 0
    steps_yielded: int = 0
    malformed: int = 0
    run_start_present: bool = False
    activities: int = 0
    states: int = 0


def _as_int_pair(value: Any) -> Optional[Tuple[int, int]]:
    """Coerce a two-element wire array (`qwen`, `px`, `tok`, `mopx`) to a tuple."""
    if isinstance(value, list) and len(value) == 2:
        return (value[0], value[1])
    return None


def _parse_llm_call(entry: Dict[str, Any]) -> LlmCall:
    """Build one `LlmCall` from an `llm[]` entry, keeping absent fields absent."""
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
        self._path = Path(trace_path)
        self._run_start: Optional[RunStart] = None
        self._diagnostics = TraceDiagnostics()
        self._activities: Dict[int, Tuple[str, bool]] = {}
        self._states: Dict[int, Tuple[str, int]] = {}

    @property
    def path(self) -> Path:
        return self._path

    @property
    def run_start(self) -> Optional[RunStart]:
        return self._run_start

    @property
    def diagnostics(self) -> TraceDiagnostics:
        return self._diagnostics

    def __iter__(self) -> Iterator[StepRow]:
        self._run_start = None
        self._diagnostics = TraceDiagnostics()
        self._activities = {}
        self._states = {}

        # newline="" keeps the file's own line discipline out of the way; the
        # records are one line each by construction (INV-SNK-01), so a raw
        # newline can only appear as an escape sequence inside a string value.
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
        """Fill the ID tables and the run header; ignore every other record type."""
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
        # MOP_DATA, PIPELINE, LLM_ACK, RUN_END: well-formed, and none of this
        # module's business. Skipped without a malformed count.

    def _activity(self, act_id: int) -> Tuple[str, bool]:
        try:
            return self._activities[act_id]
        except KeyError:
            raise UnresolvedReference(f"no ACT record defines id {act_id}")

    def _state(self, state_id: int) -> Tuple[str, int]:
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
        """Assemble one `StepRow`, raising on anything that makes it malformed."""
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
    """
    return list(TraceReader(trace_path))
