"""What a `droidbot` run says about itself, which is much less than `ape`.

`droidbot`'s structured output was never retained. There is no `droidbot_output/`
directory, no `utg.js`, no `states/`, no per-event JSON and no screenshot in any
of the four archives of the raw corpus of the Android test-generation study —
verified negatively across all of them. The stdout stream is the whole record,
and this parser reads it under the same rule as its `ape` sibling: extract what
is present, cheap and unambiguous, and stop (INV-CAN-19).

Three measured properties of that stream decide the design:

- **There is no clock.** Zero timestamps appear after exploration begins. So
  `clock` is an explicit `None` on every record and nothing is inferred from the
  surrounding logcat, whose absolute millisecond stamps time RVSEC events rather
  than tool actions. Anything of the form *time to reach a screen*, *events per
  second*, or *when did a violation occur relative to this action* is
  unanswerable for this tool and is not attempted.
- **There is no step index.** The ordinal on each record is counted by this
  parser over the `Action:` lines. The stream is sequential so the count is
  sound, but it is **our construct, not the tool's**, and every row is flagged
  `step_index_synthesized=True` so a reader cannot mistake it for a native one.
  A `droidbot` step is one dispatched event, which is not the unit `ape` or
  `aperv` count in (INV-CAN-20).
- **The activity is partial and degraded.** It appears only inside a touched
  view's parenthetical, as a **simple** class name, on roughly 58 % of events;
  `KeyEvent`, `IntentEvent` and `KillAppEvent` carry no widget identity at all
  and therefore no activity. The simple name is emitted **unresolved** — the
  package prefix is not reattached from the application id, because a nested or
  library activity would be reconstructed wrongly and silently. Events with no
  activity are counted in `activity_unknown_steps`.

Two further facts shape the reading. A trace opens with roughly 3,500 lines of
androguard `DEBUG` output, which is why the parser **skips to**
`start sending events, policy is …` instead of parsing from the top: before that
line there is no exploration to read. And a run rarely ends in an orderly way —
5 of 150 sampled runs reach `Finish sending events` / `DroidBot Stopped`, the
rest are cut mid-stream at the timeout — so `truncated` is normally `True`, and
step totals, coverage and termination reason come from `tasks.json` and the
consolidated CSVs, never from this stream.

What `droidbot` has and the others do not is a **content-derived** state key: the
same screen hashes to the same value in any run. That makes it the only arm able
to supply a cross-run screen-level denominator. The parser emits the key and
draws no conclusion from it; adopting one tool's screen abstraction as the
measuring instrument for every arm is a decision for a caller to declare.

Offline and read-only over a recorded trace; no device, no `adb` (INV-APV-35).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

from aperv_tool.analysis.baseline_ape import STEP_FRAME_COLUMNS
from aperv_tool.analysis.run_identity import RunKey, try_parse_run_filename

# The shared per-step column contract is defined once, in the sibling parser, and
# imported here rather than restated. Two copies of a frame's column list is the
# same defect as two copies of the run-identity regex (INV-CAN-01): they drift,
# they disagree about what a frame contains, and nothing reports it.

#: How this tool counts a step, carried on every row (INV-CAN-20). One dispatched
#: event — not an `ape` `SATA begin/end` cycle and not an `aperv` `StepRecord`.
STEP_UNIT = "droidbot dispatched event"

# Where exploration starts. Everything above it is androguard's static-analysis
# narration, some 3,500 lines of it, with no event in it.
_POLICY = re.compile(r"start sending events, policy is (?P<policy>\S+)")

# One dispatched event. The argument list holds nested parentheses — a touched
# view's parenthetical — so the closing bracket is matched greedily.
_ACTION = re.compile(r"^Action: (?P<type>\w+)\((?P<args>.*)\)\s*$")
_ACTION_PREFIX = "Action: "

# The event's own state, printed on the record itself. Preferred over the
# policy's `Current state:` line because it is on the record rather than near it.
_ACTION_STATE = re.compile(r"\bstate=(?P<state>[0-9a-f]+)")

# The touched view: a content hash, then the simple activity name and the widget
# class. `KeyEvent`, `IntentEvent` and `KillAppEvent` have none of this.
_ACTION_VIEW = re.compile(r"\bview=(?P<view>[0-9a-f]+)\((?P<activity>[^/)]+)/")

# A line the exploration policy printed. The logger name distinguishes the
# policies (`UtgGreedySearchPolicy`, `UtgNaiveSearchPolicy`) and is dropped.
_POLICY_LINE = re.compile(r"^(?:INFO|WARNING|DEBUG|ERROR):Utg\w*:(?P<message>.*)$")

# The greedy policies announce the screen before choosing on it. The naive ones
# never print this line at all, which is why the action's own `state=` is the
# primary source.
_CURRENT_STATE = re.compile(r"^Current state: (?P<state>[0-9a-f]+)\s*$")

# An orderly end. Measured in 5 of 150 sampled runs; either marker is accepted
# because the second follows the first only when teardown also completes.
_ORDERLY_END = ("Finish sending events", "DroidBot Stopped")

# Redaction of a policy message's variable payload, so the decision source is a
# small stable vocabulary rather than one category per screen. Content hashes go
# first, then any remaining digit run; nothing is renamed, only blanked.
_HEX_PAYLOAD = re.compile(r"\b[0-9a-f]{16,}\b")
_DIGITS = re.compile(r"\d+")


@dataclass(frozen=True, slots=True)
class DroidbotStep:
    """One dispatched event.

    Attributes:
        step: The synthesized ordinal, from 1, counted over the `Action:` lines
            of this run. Not printed by the tool (INV-CAN-19).
        event_type: The event class — `TouchEvent`, `KeyEvent`, `IntentEvent`,
            `ScrollEvent`, `SetTextEvent`, `KillAppEvent`, `LongTouchEvent`.
        action: The record exactly as printed, argument list included.
        state_key: The content hash of the screen. Cross-run comparable, unlike
            every other arm's key.
        activity: The **simple** activity name from the touched view, unresolved.
            `None` on every event carrying no widget identity.
        view: The touched view's content hash, `None` when there is no view.
        decision_source: The policy message that preceded this event, with its
            variable payload redacted. `None` when the event was dispatched with
            no policy line of its own — a restart intent, typically — because
            reusing the previous event's reason would attribute a decision the
            tool did not print.
    """

    step: int
    event_type: str
    action: str
    state_key: Optional[str]
    activity: Optional[str]
    view: Optional[str]
    decision_source: Optional[str]


@dataclass(frozen=True, slots=True)
class DroidbotRun:
    """Everything one `droidbot` trace supports saying about its run.

    Attributes:
        key: The run identity from the filename, or `None` for a foreign name.
            A trace with no identity is still parsed and still returned, because
            dropping it would remove a run from a denominator (INV-APV-37).
        policy: The exploration policy the run announced, `None` when it never
            reached the announcement.
        steps: The dispatched events, in file order.
        exploration_started: Whether the policy line was found. False means the
            run produced no events at all — an outcome that keeps its place in
            every denominator, not a parse failure.
        truncated: No orderly terminator was found. Expected to be `True`: only
            5 of 150 sampled runs stop in an orderly way.
        lines_read: Every line the file held.
        preamble_lines: Lines before the policy announcement, skipped by design.
            Roughly 3,500 in a typical trace, which is why `lines_read` is a poor
            denominator on its own.
        unparsed_lines: Lines carrying a marker this parser recognises and could
            not decompose. Narration it does not target is not counted here.
        activity_unknown_steps: Events with no activity, because they carried no
            widget identity. Roughly 42 % of events in the surveyed corpus.
        step_unit: What one row of this run counts (INV-CAN-20).
    """

    key: Optional[RunKey]
    policy: Optional[str]
    steps: Tuple[DroidbotStep, ...]
    exploration_started: bool
    truncated: bool
    lines_read: int
    preamble_lines: int
    unparsed_lines: int
    activity_unknown_steps: int
    step_unit: str = STEP_UNIT

    def step_frame(self) -> pd.DataFrame:
        """The run's events in the shared per-step frame.

        Returns:
            A frame with exactly `STEP_FRAME_COLUMNS` — the same columns the
            `aperv` per-step frame carries, plus the baseline block — one row per
            dispatched event, in file order. An empty frame keeps the columns, so
            a run that never started exploring concatenates with the others.
        """
        return pd.DataFrame(
            [_row(self.key, self.policy, step) for step in self.steps],
            columns=list(STEP_FRAME_COLUMNS),
        )


def _row(key: Optional[RunKey], policy: Optional[str], step: DroidbotStep) -> dict:
    """One event as a row of the shared frame.

    Every column the tool has no signal for is an explicit `None`. `t_rel_ms` is
    the load-bearing one: the stream carries no timestamp after exploration
    begins, and a zero or an interpolated value would be a measurement this run
    never made. The `ape`-only columns — the transition and the model statistics
    — are `None` here for the same reason, as are the `aperv` scorer's six boost
    columns, whose zero would assert a mechanism ran.
    """
    return {
        "apk": key.apk if key else None,
        "arm": key.arm if key else None,
        "rep": key.repetition if key else None,
        "timeout_s": key.timeout_s if key else None,
        "step": step.step,
        "t_rel_ms": None,
        "t_epoch_ms": None,
        "activity": step.activity,
        "activity_has_mop": None,
        "state_key": step.state_key,
        "action": step.action,
        "decision_source": step.decision_source,
        "pick_channel": None,
        "priority": None,
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
        "step_index_synthesized": True,
        "step_unit": STEP_UNIT,
        "action_type": step.event_type,
        "policy": policy,
        "source_state_key": None,
        "target_state_key": None,
        "model_activities": None,
        "model_states": None,
        "model_edges": None,
        "model_unvisited_actions": None,
        "model_visited_actions": None,
    }


def _decision_source(message: str) -> str:
    """A policy message reduced to its stable part.

    The payload after a colon is the varying half — `selected an un-clicked
    view: 025f704d…` names one widget, and keeping it would produce one category
    per widget instead of one per kind of decision. What remains is redacted for
    content hashes and digit runs, so `Navigating to 8a3f…, 2 steps left.`
    becomes one category rather than one per target. Nothing is renamed: the
    surviving text is the tool's own.
    """
    head = message.split(": ", 1)[0]
    return _DIGITS.sub("<n>", _HEX_PAYLOAD.sub("<id>", head)).strip()


def parse(trace_path: Path | str) -> DroidbotRun:
    """Read one recorded `droidbot` trace into its run record.

    A single forward pass; the parser holds only the pending state and decision,
    each of which is consumed by the next event and then cleared. The file is
    opened read-only and never written to (INV-APV-35).

    Args:
        trace_path: Path to a recorded `.trace`. Its basename supplies the run
            identity when it follows the campaign convention.

    Returns:
        The `DroidbotRun`. A trace that never announces its policy returns zero
        steps with `exploration_started=False` and no exception.

    Raises:
        OSError: The file cannot be opened. Nothing else propagates: a line this
            parser cannot decompose is counted, never raised (INV-CAN-04).
    """
    path = Path(trace_path)
    key = try_parse_run_filename(path)

    steps: list[DroidbotStep] = []
    policy: Optional[str] = None
    pending_state: Optional[str] = None
    pending_decision: Optional[str] = None
    lines_read = 0
    preamble_lines = 0
    unparsed = 0
    orderly_end = False

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            lines_read += 1
            line = raw.rstrip("\n")

            announcement = _POLICY.search(line)
            if announcement is not None:
                policy = announcement.group("policy")
                continue
            if policy is None:
                preamble_lines += 1
                continue

            if any(marker in line for marker in _ORDERLY_END):
                orderly_end = True

            if line.startswith(_ACTION_PREFIX):
                match = _ACTION.match(line)
                if match is None:
                    unparsed += 1
                    continue
                steps.append(
                    _step(
                        ordinal=len(steps) + 1,
                        line=line,
                        event_type=match.group("type"),
                        args=match.group("args"),
                        pending_state=pending_state,
                        pending_decision=pending_decision,
                    )
                )
                pending_state = None
                pending_decision = None
                continue

            policy_line = _POLICY_LINE.match(line)
            if policy_line is not None:
                message = policy_line.group("message")
                current = _CURRENT_STATE.match(message)
                if current is not None:
                    pending_state = current.group("state")
                else:
                    pending_decision = _decision_source(message)

    return DroidbotRun(
        key=key,
        policy=policy,
        steps=tuple(steps),
        exploration_started=policy is not None,
        truncated=not orderly_end,
        lines_read=lines_read,
        preamble_lines=preamble_lines,
        unparsed_lines=unparsed,
        activity_unknown_steps=sum(1 for step in steps if step.activity is None),
    )


def _step(
    *,
    ordinal: int,
    line: str,
    event_type: str,
    args: str,
    pending_state: Optional[str],
    pending_decision: Optional[str],
) -> DroidbotStep:
    """Assemble one event from its own line plus what the policy printed above it.

    The state is taken from the event's own `state=` when it has one and from the
    policy's `Current state:` otherwise. The two agree wherever both appear; the
    preference is for the value on the record rather than the one near it, and it
    is what lets the naive policies — which never print `Current state:` — carry
    a state at all.
    """
    state = _ACTION_STATE.search(args)
    view = _ACTION_VIEW.search(args)
    return DroidbotStep(
        step=ordinal,
        event_type=event_type,
        action=line,
        state_key=state.group("state") if state else pending_state,
        activity=view.group("activity") if view else None,
        view=view.group("view") if view else None,
        decision_source=pending_decision,
    )
