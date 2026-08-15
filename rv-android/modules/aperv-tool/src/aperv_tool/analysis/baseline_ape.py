"""What an `ape` run says about itself, and nothing more.

`ape` writes no NDJSON. Its only record is the free-text stdout stream the jar
prints, and the temptation this module exists to refuse is to reconstruct an
`aperv` step record out of it — to infer a per-step latency from a one-second
clock, to correlate a run-local state key across replicas, to recompute the GUI
tree abstraction. A survey of the raw corpus of the Android test-generation
study (21,681 runs, 39.8 GB, read-only) measured what is actually there, and
the decision taken on that measurement is that the parser **extracts the fields
that are present, cheap and unambiguous, and stops** (INV-CAN-19).

What the measurement found, and what each fact costs the parser:

- The step envelope is native and complete. `>>>>>>>> SATA begin step [N]` …
  `>>>>>>>> SATA end step [N]` brackets every step, the index is monotonic, and
  it is present on 100 % of steps. Nothing has to be synthesized here, which is
  the single largest difference from the sibling `droidbot` parser.
- The clock is `[Elapsed: DDDD HH:MM:SS]` on the begin marker, at **one-second
  resolution**. Many consecutive steps therefore share one value — in the
  fixture's densest run, 50 steps span 58 seconds — so a per-step latency is
  not computable from this stream and is not attempted. The offset between this
  clock's origin and the logcat's absolute clock is not printed anywhere, so
  `t_epoch_ms` stays `None` rather than being anchored to a guess.
- The state key embeds a JVM identity hash
  (`…MainActivity@-1093388650@Naming[0]@[W=3][A=6]`), which changes on every
  process start. Measured across three replicas of the same application and
  arm: **zero** states in common, **100 %** of activities in common. So the key
  is emitted for intra-run use, and the cross-run join is the activity name
  (INV-APV-36, INV-CAN-13).
- Decision provenance is explicit and dense — `… by strategy EARLY_STAGE`,
  `EPSILON_GREEDY`, `USE_BUFFER` on 99.6 % of steps — and lands on
  `decision_source`, the same column the `aperv` reader fills.
- `ape_output/` is empty in all 220 archived instances: the per-step
  `step-N.xml` GUI tree and `step-N.png` the log names were never pulled off the
  device. APE's own state abstraction cannot be recomputed, and this module does
  not pretend otherwise.
- No `ape` trace carries an end-of-run summary. The Monkey epilogue appears in
  **0 of 150** sampled traces, so `truncated` is expected to be `True` for every
  real run and step totals, coverage and termination reason come from
  `tasks.json` and the consolidated CSVs, never from here.

**"No steps" is an outcome, not a failure.** One of 80 sampled traces carried no
step marker at all; the run still occupies its place in every denominator, so
`parse` returns a run with zero steps and raises nothing.

**`New`, never `Curr`.** APE's block epilogue prints `Last`, `Curr` and `New`
as a three-deep history: `New   state:` / `New  action:` are the state this step
observed and the action it selected — `New  action:` is always the action the
same block's `Select action …` line chose — while `Curr` is the step before.
Reading `Curr  state:` would look reasonable and be wrong: on the fixture it is
`null` on 8 of 50 blocks in the densest run and on 8 of 9 in another, which puts
activity coverage at 84 % and 11 % against the ~99.8 % the survey measured, where
`New   state:` is non-null on 106 of 106 blocks. `Curr` is kept nowhere.

Offline and read-only over a recorded trace; no device, no `adb` (INV-APV-35).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from aperv_tool.analysis import tasks_record
from aperv_tool.analysis.run_identity import RunKey, try_parse_run_filename
from aperv_tool.analysis.trace_ndjson import StepRow

#: How this tool counts a step, carried on every row so a count cannot be added
#: to another tool's count without the difference being visible (INV-CAN-20). A
#: `droidbot` step is one dispatched event and an `aperv` step is a `StepRecord`;
#: these are three units, comparable only as per-tool rates with the unit named.
STEP_UNIT = "ape SATA begin/end cycle"

#: The columns the `aperv` per-step frame carries, derived from the reader's own
#: record rather than copied, so the two cannot drift. A baseline frame carries
#: every one of them and writes an explicit `None` wherever the tool emits no
#: such signal — the absence is the fact, and a zero would assert the mechanism
#: ran and produced nothing (INV-CAN-19).
APERV_STEP_COLUMNS = tasks_record.IDENTITY_COLUMNS + tuple(
    field.name for field in fields(StepRow)
)

#: What a baseline knows that the `aperv` record has no column for. Both
#: baseline parsers emit this block identically, each filling only what its own
#: stream prints, so the two frames concatenate without an alignment step: the
#: model statistics and the transition are `ape`-only, `policy` is
#: `droidbot`-only, and the first two are mandatory everywhere.
BASELINE_STEP_COLUMNS = (
    "step_index_synthesized",
    "step_unit",
    "action_type",
    "policy",
    "source_state_key",
    "target_state_key",
    "model_activities",
    "model_states",
    "model_edges",
    "model_unvisited_actions",
    "model_visited_actions",
)

#: The frame both baseline parsers return. Its first block is byte-for-byte the
#: `aperv` per-step frame's column list, so a consumer written against that frame
#: reads a baseline without knowing it is one.
STEP_FRAME_COLUMNS = APERV_STEP_COLUMNS + BASELINE_STEP_COLUMNS

# The step envelope. The index is bracketed and the elapsed clock rides the
# opening marker only; a closing marker carries the index alone.
_BEGIN = re.compile(
    r"SATA begin step \[(?P<step>\d+)\]\[Elapsed: (?P<elapsed>[^\]]*)\]"
)
_BEGIN_PREFIX = "SATA begin step"
_END = re.compile(r"SATA end step \[(?P<step>\d+)\]")
_END_PREFIX = "SATA end step"

# `DDDD HH:MM:SS` — days, then a wall-clock triple. One second is the finest
# grain the stream has.
_ELAPSED = re.compile(r"^(?P<days>\d+) (?P<h>\d+):(?P<m>\d+):(?P<s>\d+)$")

# The action and the strategy that chose it, on one line. The action descriptor
# is greedy up to the literal separator because it contains brackets, equals
# signs and semicolons of its own.
_SELECT = re.compile(r"Select action (?P<action>.+) by strategy (?P<strategy>\S+)\s*$")
_SELECT_PREFIX = "Select action "

# The state the block observed, third of APE's `Last`/`Curr`/`New` history. The
# whitespace run varies with the label's width, so it is matched loosely.
_NEW_STATE = re.compile(r"^\[APE\] New\s+state:\s*(?P<state>.+?)\s*$")

# The transition APE recorded for the *previous* action, printed as a three-line
# block. Absent on the 8 of 50 fixture blocks where no edge was added.
_SOURCE = re.compile(r"^\[APE\]\s+Source:\s*(?P<state>.+?)\s*$")
_TARGET = re.compile(r"^\[APE\]\s+Target:\s*(?P<state>.+?)\s*$")

# The model's size at this step. One line per block on every fixture run.
_GSTG = re.compile(
    r"GSTG\([^)]*\): activities \((?P<activities>\d+)\), "
    r"states \((?P<states>\d+)\), edges \((?P<edges>\d+)\), "
    r"unvisited actions \((?P<unvisited>\d+)\), visited actions \((?P<visited>\d+)\)"
)
_GSTG_PREFIX = "GSTG("

# A state key's anatomy: a graph/state index, two bracketed counters, then the
# fully-qualified activity, then the JVM identity hash that makes the whole key
# run-local.
_STATE_ACTIVITY = re.compile(r"^g\d+s\d+\[[^\]]*\]\[[^\]]*\](?P<activity>[^@]+)@")

# The action's own descriptor: the model action type, and the priority the
# scheduler assigned it.
_ACTION_TYPE = re.compile(r"@(?P<type>MODEL_[A-Z_]+)")
_PRIORITY = re.compile(r"\[P=(?P<priority>-?\d+)\]")

# Run-level interruptions, printed by the framework outside the `[APE] ` stream
# and outside any step envelope. The marker line is kept; the dump that follows
# it is unstructured and is not parsed.
_RUN_EVENTS = (("// NOT RESPONDING", "NOT_RESPONDING"), ("// CRASH", "CRASH"))

# The orderly end of a Monkey-derived run. Measured absent in 150 of 150 sampled
# traces, so its absence is the normal case and `truncated` is normally True.
_EPILOGUE = ("// Monkey finished", "Events injected:")


@dataclass(frozen=True, slots=True)
class ModelStats:
    """The exploration model's size at one step, from the block's `GSTG(…)` line.

    Attributes:
        activities: Activities in the model.
        states: Abstract states in the model.
        edges: Transitions between them.
        unvisited_actions: Actions the model holds and has never fired.
        visited_actions: Actions it has fired at least once.
    """

    activities: int
    states: int
    edges: int
    unvisited_actions: int
    visited_actions: int


@dataclass(frozen=True, slots=True)
class ApeStep:
    """One `SATA begin/end` cycle, with every field the block actually printed.

    A `None` here is never a default. It means the block did not print that line
    — an edge that was not added, a strategy line that did not appear — and a
    consumer must be able to tell that apart from a value of zero.

    Attributes:
        step: The index APE printed, native and monotonic.
        elapsed_s: Seconds since the tool's own clock started, at one-second
            resolution. Consecutive steps routinely share a value.
        activity: Fully-qualified activity, read off the state key.
        state_key: The run-local key of the state this step observed. Joins
            within the run and carries no meaning outside it (INV-CAN-13).
        action: The action descriptor exactly as the `Select action …` line
            printed it.
        action_type: The `MODEL_*` type inside that descriptor.
        strategy: The named strategy that chose the action.
        priority: The `[P=…]` priority on the chosen action.
        source_state_key: Origin of the transition the block recorded, when it
            recorded one.
        target_state_key: Its destination.
        model: The `GSTG(…)` statistics of the block.
    """

    step: int
    elapsed_s: Optional[int]
    activity: Optional[str]
    state_key: Optional[str]
    action: Optional[str]
    action_type: Optional[str]
    strategy: Optional[str]
    priority: Optional[int]
    source_state_key: Optional[str]
    target_state_key: Optional[str]
    model: Optional[ModelStats]


@dataclass(frozen=True, slots=True)
class RunEvent:
    """An interruption hoisted out of the step stream to the run.

    An ANR or a crash is not a step: it is printed between blocks, by a different
    producer, and parsing it as one would insert a phantom step into a count that
    is already a per-tool unit. It is carried instead with the index of the step
    it followed, which is what a reader needs in order to place it.

    Attributes:
        kind: `NOT_RESPONDING` or `CRASH`.
        detail: The marker line, stripped. The dump beneath it is unstructured
            and is deliberately not parsed.
        after_step: Index of the step in progress or last closed, `None` when the
            interruption preceded every step.
    """

    kind: str
    detail: str
    after_step: Optional[int]


@dataclass(frozen=True, slots=True)
class ApeRun:
    """Everything one `ape` trace supports saying about its run.

    Attributes:
        key: The run identity from the filename, or `None` for a foreign name.
            A trace with no identity is still parsed and still returned, because
            dropping it would remove a run from a denominator (INV-APV-37).
        steps: The blocks, in file order.
        events: Interruptions hoisted to the run.
        truncated: No orderly terminator was found. Expected to be `True`: the
            Monkey epilogue appears in 0 of 150 sampled traces.
        unterminated_blocks: Blocks opened and never closed. One at the end of
            the stream is the ordinary shape of a run cut at its timeout; the
            block is still emitted with whatever it had printed.
        lines_read: Every line the file held, so the unparsed count has a
            denominator.
        unparsed_lines: Lines carrying a marker this parser recognises and could
            not decompose. Everything the parser does not target — the `*** INFO
            ***` narration, the ANR dump body — is not counted here; it is the
            difference between this and `lines_read`.
        activity_unknown_steps: Steps whose activity could not be read.
        step_unit: What one row of this run counts (INV-CAN-20).
    """

    key: Optional[RunKey]
    steps: Tuple[ApeStep, ...]
    events: Tuple[RunEvent, ...]
    truncated: bool
    unterminated_blocks: int
    lines_read: int
    unparsed_lines: int
    activity_unknown_steps: int
    step_unit: str = STEP_UNIT

    def step_frame(self) -> pd.DataFrame:
        """The run's steps in the shared per-step frame.

        Returns:
            A frame with exactly `STEP_FRAME_COLUMNS`, one row per step, in file
            order. An empty frame keeps the columns, so a "no steps" run
            concatenates with the others instead of collapsing the shape.
        """
        return pd.DataFrame(
            [_row(self.key, step) for step in self.steps],
            columns=list(STEP_FRAME_COLUMNS),
        )


def _row(key: Optional[RunKey], step: ApeStep) -> dict:
    """One step as a row of the shared frame.

    The `aperv`-only columns are `None` rather than absent or zero. The six boost
    columns are the clearest case: in an `aperv` row a zero means the scorer ran
    and added nothing, and `ape` has no scorer at all, so a zero here would be a
    claim about a mechanism that does not exist.
    """
    model = step.model
    return {
        "apk": key.apk if key else None,
        "arm": key.arm if key else None,
        "rep": key.repetition if key else None,
        "timeout_s": key.timeout_s if key else None,
        "step": step.step,
        "t_rel_ms": None if step.elapsed_s is None else step.elapsed_s * 1000,
        "t_epoch_ms": None,
        "activity": step.activity,
        "activity_has_mop": None,
        "state_key": step.state_key,
        "action": step.action,
        "decision_source": step.strategy,
        "pick_channel": None,
        "priority": step.priority,
        "mop": None,
        "mop_frontier": None,
        "wtg": None,
        "coverage": None,
        "menu": None,
        "form": None,
        "wtg_source": None,
        "mop_exposure": None,
        "patched": None,
        "counterfactual": None,
        "component": None,
        "llm": None,
        "outcome": None,
        "step_index_synthesized": False,
        "step_unit": STEP_UNIT,
        "action_type": step.action_type,
        "policy": None,
        "source_state_key": step.source_state_key,
        "target_state_key": step.target_state_key,
        "model_activities": model.activities if model else None,
        "model_states": model.states if model else None,
        "model_edges": model.edges if model else None,
        "model_unvisited_actions": model.unvisited_actions if model else None,
        "model_visited_actions": model.visited_actions if model else None,
    }


def _elapsed_seconds(text: str) -> Optional[int]:
    """`DDDD HH:MM:SS` as whole seconds, or `None` when it does not parse."""
    match = _ELAPSED.match(text.strip())
    if match is None:
        return None
    return (
        int(match.group("days")) * 86400
        + int(match.group("h")) * 3600
        + int(match.group("m")) * 60
        + int(match.group("s"))
    )


def _activity_of(state_key: Optional[str]) -> Optional[str]:
    """The fully-qualified activity carried inside a state key.

    The key is `g<graph>s<state>[…][…]<activity>@<identity hash>@…`; only the
    activity survives a process restart, which is why it and not the key is the
    cross-run join.
    """
    if state_key is None or state_key == "null":
        return None
    match = _STATE_ACTIVITY.match(state_key)
    return match.group("activity") if match else None


class _Block:
    """The fields of one open step block, filled as its lines go past.

    A mutable accumulator rather than a growing tuple of arguments: the block's
    lines arrive in an order the format does not guarantee, and every field is
    optional.
    """

    def __init__(self, step: int, elapsed_s: Optional[int]) -> None:
        """Open a block on its `SATA begin step` marker.

        Args:
            step: The index the marker carried.
            elapsed_s: The marker's clock in whole seconds, `None` when it did
                not parse.

        State:
            Every remaining attribute starts `None` and is filled at most once,
            by the line that carries it, before `finish` freezes the block. A
            `None` that survives means the block never printed that line.
        """
        self.step = step
        self.elapsed_s = elapsed_s
        self.state_key: Optional[str] = None
        self.action: Optional[str] = None
        self.strategy: Optional[str] = None
        self.source_state_key: Optional[str] = None
        self.target_state_key: Optional[str] = None
        self.model: Optional[ModelStats] = None

    def finish(self) -> ApeStep:
        """Freeze the accumulator into the record the caller sees."""
        action_type = None
        priority = None
        if self.action is not None:
            type_match = _ACTION_TYPE.search(self.action)
            action_type = type_match.group("type") if type_match else None
            priority_match = _PRIORITY.search(self.action)
            priority = int(priority_match.group("priority")) if priority_match else None
        state_key = None if self.state_key == "null" else self.state_key
        return ApeStep(
            step=self.step,
            elapsed_s=self.elapsed_s,
            activity=_activity_of(state_key),
            state_key=state_key,
            action=self.action,
            action_type=action_type,
            strategy=self.strategy,
            priority=priority,
            source_state_key=self.source_state_key,
            target_state_key=self.target_state_key,
            model=self.model,
        )


def parse(trace_path: Path | str) -> ApeRun:
    """Read one recorded `ape` trace into its run record.

    A single forward pass over the file; nothing is held but the open block. The
    file is opened read-only and never written to (INV-APV-35).

    Args:
        trace_path: Path to a recorded `.trace`. Its basename supplies the run
            identity when it follows the campaign convention.

    Returns:
        The `ApeRun`. A trace with no step marker returns zero steps and no
        exception — that is an outcome the denominators must keep, not an error.

    Raises:
        OSError: The file cannot be opened. Nothing else propagates: a line this
            parser cannot decompose is counted, never raised (INV-CAN-04).
    """
    path = Path(trace_path)
    key = try_parse_run_filename(path)

    steps: list[ApeStep] = []
    events: list[RunEvent] = []
    block: Optional[_Block] = None
    last_closed: Optional[int] = None
    lines_read = 0
    unparsed = 0
    unterminated = 0
    epilogue_seen = False

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            lines_read += 1
            line = raw.rstrip("\n")

            if any(marker in line for marker in _EPILOGUE):
                epilogue_seen = True

            hoisted = _run_event(line, block, last_closed)
            if hoisted is not None:
                events.append(hoisted)
                continue

            if _BEGIN_PREFIX in line:
                match = _BEGIN.search(line)
                if match is None:
                    unparsed += 1
                    continue
                if block is not None:
                    unterminated += 1
                    steps.append(block.finish())
                block = _Block(
                    step=int(match.group("step")),
                    elapsed_s=_elapsed_seconds(match.group("elapsed")),
                )
                continue

            if _END_PREFIX in line:
                match = _END.search(line)
                if match is None:
                    unparsed += 1
                    continue
                last_closed = int(match.group("step"))
                if block is not None:
                    steps.append(block.finish())
                    block = None
                continue

            if block is not None:
                unparsed += _fill(block, line)

    if block is not None:
        unterminated += 1
        steps.append(block.finish())

    return ApeRun(
        key=key,
        steps=tuple(steps),
        events=tuple(events),
        truncated=not epilogue_seen,
        unterminated_blocks=unterminated,
        lines_read=lines_read,
        unparsed_lines=unparsed,
        activity_unknown_steps=sum(1 for step in steps if step.activity is None),
    )


def _run_event(
    line: str, block: Optional[_Block], last_closed: Optional[int]
) -> Optional[RunEvent]:
    """An interruption marker as a run-level event, or `None`.

    Placed on the step in progress when one is open and on the last closed step
    otherwise — an ANR is printed between blocks in the fixture, after the
    framework has already closed the step it interrupted.
    """
    stripped = line.strip()
    for marker, kind in _RUN_EVENTS:
        if stripped.startswith(marker):
            return RunEvent(
                kind=kind,
                detail=stripped,
                after_step=block.step if block is not None else last_closed,
            )
    return None


def _fill(block: _Block, line: str) -> int:
    """Absorb one line of an open block.

    Returns:
        `1` when the line carried a marker this parser targets and could not be
        decomposed, `0` otherwise. Narration the parser does not target returns
        `0` and is accounted for by `lines_read`.
    """
    state = _NEW_STATE.match(line)
    if state is not None:
        block.state_key = state.group("state")
        return 0

    if _SELECT_PREFIX in line:
        match = _SELECT.search(line)
        if match is None:
            return 1
        block.action = match.group("action")
        block.strategy = match.group("strategy")
        return 0

    source = _SOURCE.match(line)
    if source is not None:
        block.source_state_key = source.group("state")
        return 0

    target = _TARGET.match(line)
    if target is not None:
        block.target_state_key = target.group("state")
        return 0

    if _GSTG_PREFIX in line:
        match = _GSTG.search(line)
        if match is None:
            return 1
        block.model = ModelStats(
            activities=int(match.group("activities")),
            states=int(match.group("states")),
            edges=int(match.group("edges")),
            unvisited_actions=int(match.group("unvisited")),
            visited_actions=int(match.group("visited")),
        )
        return 0

    return 0
