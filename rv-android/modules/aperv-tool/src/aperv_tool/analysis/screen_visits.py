"""A run's steps, segmented into the screens they happened on.

A person using an application works in screens: arrive somewhere, do a few
things there, leave. A step stream carries none of that structure — it is a flat
sequence of picks — and every question about guidance follow-through ("did
arriving at a monitored screen make a monitor fire?"), about form completion
("were the fields filled, and did the submit leave the screen?") or about what an
LLM decision led to is a question about a screen, not about a step. This module
rebuilds the screens.

## Why the Activity is the unit, and the state key is not

The trace offers two candidate grains. ``StepRow.state_key`` is the agent's own
abstract state — ``<activity>@<identity-hash>@Naming[k]@[W=n]`` — and
``StepRow.activity`` is the Android Activity the step started on. The state key
looks like the finer, better answer. It was measured on 60 campaign runs
(15,702 steps) and it is not a screen at all:

- median state-visit length **1** step, mean 1.66, **75.5 % of them one step**;
- **84.6 %** of state-visit closings are transitions to another state *of the
  same Activity*;
- median **156.5** state-visits per run.

A combobox opening, a dialog, a menu, the soft keyboard appearing — each is
another state of the same Activity, and the naming refinement of the agent's
abstraction produces still more. The state grain is therefore a step-level unit
wearing a screen's name. The Activity grain, on the same runs, gives a median of
**14.5** visits per run, visit length mean 11.0 and median 2, with 2.68 distinct
state keys inside the average visit — right-sized in the middle of its
distribution.

The Activity grain has a second property the state grain cannot have: it is the
only one comparable **across** runs. A state key embeds a JVM identity hash and
is run-local (INV-APV-36) — three replicas of one application share **zero**
state keys and **100 %** of their activities.

So the activity-visit is the unit and the state sequence is kept inside it as a
descriptive ``state_trail`` (INV-CAN-12, INV-CAN-13). Nothing is discarded; the
combobox sub-trajectory stays legible as three spans of one visit rather than
becoming three visits.

**Recorded limitation.** Navigation between Fragments inside one Activity is
invisible here: such a run is one visit, and the longest measured is 294 steps.
Splitting a visit on ``MODEL_BACK`` / ``MODEL_MENU`` would address it and is
deliberately not built — the split would be decided against a concrete question,
and no question has asked for it.

## Closing rules, in a total order

A visit is a maximal run of consecutive rows with equal ``activity``, closed by
the **first** of:

1. ``outcome is None`` — a restart, a component launch or a non-model action.
   The destination is unknown, so the visit ends rather than being extended
   across an unobserved move.
2. ``outcome.resolved is False`` — the teardown flush wrote this record while
   the step was still in flight. Its other fields were never set by the graph
   update, which is why this is tested before any of them is read.
3. ``outcome.activity_changed`` — the step left the Activity.
4. The next row's ``activity`` differs — the stream moved without the outcome
   saying so.
5. End of trace.

The order is not the order of the sentence that describes them: an outcome must
exist before its members can be read, and an unresolved outcome's members were
never written. Rules 1 and 2 therefore come first, and the last row of a run
always matches at least rule 5, so no open visit is ever left behind.

**Non-adjacent runs never merge.** ``A → B → A`` is three visits, and the second
``A`` carries ``revisit_index`` 2. Merging them would answer "what happened on
this screen" with the union of two separate occasions.

## The form episode

There is no ``SET_TEXT`` record in the trace: typing is a side effect of a
``MODEL_CLICK`` on an ``EditText``, and the corroborating signal is the form
boost (``form > 0``) the completion pass applied to unfilled fields. So a form
episode is derived, inside one visit, as a maximal run of clicks on text-entry
widgets — the state key free to change between them, since 382 of 954 measured
``EditText`` clicks change the key within the same Activity — closed by the
first click on anything else, which is the submit candidate.

Pure functions, no I/O, one call per run.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping, Optional, Sequence, Tuple

from aperv_tool.analysis.trace_ndjson import StepRow

#: How an activity-visit ended.
ExitKind = Literal[
    "activity_transition",
    "next_activity_differs",
    "no_outcome",
    "teardown",
    "run_end",
]

#: How a state span inside a visit ended. Wider than ``ExitKind`` because the
#: state grain sees the movement the Activity grain is deliberately blind to:
#: ``state_transition`` is a move to another state of the same Activity, and it
#: is 84.6 % of all state-span closings.
StateExitKind = Literal[
    "state_transition",
    "activity_transition",
    "key_change_without_outcome",
    "no_outcome",
    "teardown",
    "run_end",
]

# The action string is `<graph-element>@<TYPE><descriptor>` — the `@` separates
# the model's element id from the type, and the descriptor's `key=value;` pairs
# follow the type with no separator (`MODEL_CLICKclass=...`). The type is
# upper-case and the descriptor's keys are not, which is what ends the match.
_ACTION_TYPE = re.compile(r"@(MODEL_[A-Z_]+|EVENT_[A-Z_]+)")

# The three widget classes that accept typed text. Matched inside the `class=`
# field so a vendor subclass (`…AppCompatEditText`) counts.
_TEXT_ENTRY_CLASS = re.compile(
    r"class=[^;\]]*(?:EditText|AutoCompleteTextView|SearchView)"
)

_CLASS_FIELD = re.compile(r"class=([^;\]]*)")
_RESOURCE_ID_FIELD = re.compile(r"resource-id=([^;\]]*)")

#: What an action whose string carries no recognisable type is counted as. A
#: label rather than a discard: an uncounted step would leave the visit's action
#: census failing to add up to ``n_steps``.
UNKNOWN_ACTION_TYPE = "unknown"

#: The action type a click is. Both the form episode's fills and its submit
#: candidate are this type; only the widget class tells them apart.
CLICK = "MODEL_CLICK"


def action_type(action: str) -> str:
    """The action's type, e.g. ``MODEL_CLICK``, or ``unknown``.

    Args:
        action: The action string exactly as the agent printed it.

    Returns:
        The type name, or ``UNKNOWN_ACTION_TYPE`` when the string carries none.
    """
    match = _ACTION_TYPE.search(action)
    return match.group(1) if match else UNKNOWN_ACTION_TYPE


def is_text_entry(action: str) -> bool:
    """Whether the action's target is a widget that accepts typed text.

    Args:
        action: The action string.

    Returns:
        True for ``EditText``, ``AutoCompleteTextView`` and ``SearchView``
        targets, including vendor subclasses of them.
    """
    return _TEXT_ENTRY_CLASS.search(action) is not None


def _edit_target(action: str) -> str:
    """The identity of a text field, for counting distinct ones in an episode.

    The resource id is the stable name when the layout gives one; the class is
    the fallback, which means two unnamed fields of the same class count as one
    target. That under-count is preferred to the alternative — the bounds, which
    move when the screen scrolls and would over-count one field as several.
    """
    resource = _RESOURCE_ID_FIELD.search(action)
    if resource and resource.group(1):
        return resource.group(1)
    widget = _CLASS_FIELD.search(action)
    return widget.group(1) if widget else action


@dataclass(frozen=True, slots=True)
class StateSpan:
    """One run of consecutive steps on a single abstract state, inside a visit.

    Attributes:
        state_key: The agent's abstract state key. Run-local: it embeds a JVM
            identity hash and joins within a run only (INV-APV-36).
        enter_step: Step number of the first step on this state.
        exit_step: Step number of the last one. Step numbers can skip — a
            selection retry reuses the open record — so this is not
            ``enter_step + n_steps - 1``.
        n_steps: Steps in the span.
        exit_kind: How the span ended. This is the field the Activity-grain
            decision was measured with, and it is the only way a reader can
            re-derive that measurement from the library.
    """

    state_key: str
    enter_step: int
    exit_step: int
    n_steps: int
    exit_kind: StateExitKind


@dataclass(frozen=True)
class ActivityVisit:
    """One occasion on one screen: everything the run did between arriving and
    leaving.

    Every count carries its denominator, ``n_steps``, on the same record.

    Attributes:
        visit_ordinal: Position of this visit in the run, from 1.
        activity: The Activity class name the visit happened on.
        activity_has_mop: Whether that Activity is in the run's precomputed
            monitored set. Uniformly False in an arm that reports no such data.
        revisit_index: Which occasion this is of that Activity, from 1.
        visits_of_activity: How many occasions of that Activity the whole run
            had. Together with ``revisit_index`` it says "the 2nd of 5", which
            is what makes a single visit interpretable in isolation.
        first_step: Step number of the first step of the visit.
        last_step: Step number of the last.
        n_steps: Steps in the visit.
        t_start_ms: Run-relative clock of the first step.
        t_end_ms: Run-relative clock of the last step.
        duration_ms: ``t_end_ms - t_start_ms``. The last action's own execution
            is not included — the trace does not record when it finished.
        steps: The rows themselves, in order.
        state_trail: The state spans inside the visit, in order. Descriptive
            (INV-CAN-13): never a unit of an outcome, never joined across runs.
        distinct_states: Distinct state keys the visit touched.
        state_visits: Spans in the trail — larger than ``distinct_states``
            whenever a state was returned to, as a combobox does.
        action_type_counts: Steps by action type.
        decision_source_counts: Steps by the pipeline stage that picked them.
        n_edittext_clicks: Clicks on text-entry widgets — the fill proxy, since
            the trace has no typing record of its own.
        n_form_boosted_steps: Steps whose pick carried a non-zero form boost.
        n_llm_calls: LLM routing attempts made across the visit's steps.
        closing_action: The action string of the last step.
        closing_type: That action's type.
        exit_kind: Which closing rule ended the visit.
        target_activity: The Activity the closing step led to, when its outcome
            named one. None when it did not.
        target_activity_has_mop: Whether that landing Activity is monitored.
            None under the same condition.
        violations: Monitor violations placed inside the visit's window, when
            the visit was built from bundles. Empty otherwise.
        monitored_ops: Monitored operations, same condition.
        diagnostics: Diagnostic lines, same condition.
        uicov: ``(state_key, payload)`` for the trail's keys, when the bundles
            carried per-state coverage. **The payload is cumulative over the
            whole run** — the dump is written once at teardown — so it describes
            the state, never this visit, and must never be summed across visits.
    """

    visit_ordinal: int
    activity: str
    activity_has_mop: bool
    revisit_index: int
    visits_of_activity: int
    first_step: int
    last_step: int
    n_steps: int
    t_start_ms: int
    t_end_ms: int
    duration_ms: int
    steps: Tuple[StepRow, ...]
    state_trail: Tuple[StateSpan, ...]
    distinct_states: int
    state_visits: int
    action_type_counts: Mapping[str, int]
    decision_source_counts: Mapping[str, int]
    n_edittext_clicks: int
    n_form_boosted_steps: int
    n_llm_calls: int
    closing_action: str
    closing_type: str
    exit_kind: ExitKind
    target_activity: Optional[str]
    target_activity_has_mop: Optional[bool]
    violations: Tuple[Any, ...] = ()
    monitored_ops: Tuple[Any, ...] = ()
    diagnostics: Tuple[Any, ...] = ()
    uicov: Tuple[Tuple[str, Any], ...] = ()


@dataclass(frozen=True, slots=True)
class FormEpisode:
    """A run of fills inside one visit, and what the submit candidate did.

    Attributes:
        first_step: Step number of the first fill.
        last_step: Step number of the submit, or of the last fill when the
            episode ran to the visit's end with none.
        n_fills: Clicks on text-entry widgets in the episode.
        distinct_edit_targets: How many different fields those clicks landed on.
            Below ``n_fills`` whenever a field was returned to.
        submit_action: The action string of the first click on anything that is
            not a text-entry widget. None when the visit ended first, which is
            the episode that filled fields and never submitted.
        submit_exit_kind: The visit's ``exit_kind`` when the submit closed the
            visit. None when the submit stayed on the screen — a different
            outcome from having no submit at all, which ``submit_action`` says.
    """

    first_step: int
    last_step: int
    n_fills: int
    distinct_edit_targets: int
    submit_action: Optional[str]
    submit_exit_kind: Optional[ExitKind]


def _step_of(item: Any) -> StepRow:
    """The ``StepRow`` inside a bundle, or the row itself.

    The bundle type is Layer 3 and is deliberately not imported here: a bundle
    is recognised by carrying a ``row``, which keeps this module usable directly
    over a ``TraceReader`` and leaves the placement of logcat streams entirely to
    the layer that reads them.
    """
    row = getattr(item, "row", None)
    return item if row is None else row


def _visit_exit_kind(row: StepRow, following: Optional[StepRow]) -> Optional[ExitKind]:
    """Which closing rule the row matches, or None when the visit stays open."""
    outcome = row.outcome
    if outcome is None:
        return "no_outcome"
    if not outcome.resolved:
        return "teardown"
    if outcome.activity_changed:
        return "activity_transition"
    if following is not None:
        return "next_activity_differs" if following.activity != row.activity else None
    return "run_end"


def _state_exit_kind(
    row: StepRow, following: Optional[StepRow]
) -> Optional[StateExitKind]:
    """The state grain's closing rule for the row, or None to stay open.

    The two grains agree on every boundary the Activity grain sees: an Activity
    change implies a state change, so every activity-visit boundary is also a
    state-span boundary and the spans nest inside the visits.
    """
    outcome = row.outcome
    if outcome is None:
        return "no_outcome"
    if not outcome.resolved:
        return "teardown"
    if outcome.target_state != row.state_key:
        return "activity_transition" if outcome.activity_changed else "state_transition"
    if following is not None:
        return (
            "key_change_without_outcome"
            if following.state_key != row.state_key
            else None
        )
    return "run_end"


def _state_spans(steps: Sequence[StepRow]) -> list[tuple[int, int, StateSpan]]:
    """The run's state spans with the row indices they cover.

    Computed over the whole run rather than per visit, so the last row of a
    visit is classified against the row that actually follows it instead of
    against the end of a slice.
    """
    spans: list[tuple[int, int, StateSpan]] = []
    start = 0
    for index, row in enumerate(steps):
        following = steps[index + 1] if index + 1 < len(steps) else None
        kind = _state_exit_kind(row, following)
        if kind is None:
            continue
        spans.append(
            (
                start,
                index,
                StateSpan(
                    state_key=steps[start].state_key,
                    enter_step=steps[start].step,
                    exit_step=row.step,
                    n_steps=index - start + 1,
                    exit_kind=kind,
                ),
            )
        )
        start = index + 1
    return spans


def segment(rows: Iterable[Any]) -> list[ActivityVisit]:
    """Segment one run's step stream into activity-visits.

    Args:
        rows: The run's steps in order, as ``StepRow`` from a ``TraceReader`` or
            as bundles carrying one. One call per run: the segmenter has no
            notion of a run boundary and would merge two runs' first and last
            visits if handed both.

    Returns:
        The visits in order. Empty for an empty stream, which is a first-class
        outcome — a run that produced no step still occupies its denominator.
    """
    items = list(rows)
    if not items:
        return []

    steps = [_step_of(item) for item in items]
    spans = _state_spans(steps)

    # Every run's last row matches at least the end-of-trace rule, so the loop
    # never leaves an open segment behind.
    segments: list[tuple[int, int, ExitKind]] = []
    start = 0
    for index, row in enumerate(steps):
        following = steps[index + 1] if index + 1 < len(steps) else None
        kind = _visit_exit_kind(row, following)
        if kind is not None:
            segments.append((start, index, kind))
            start = index + 1

    totals = Counter(steps[first].activity for first, _, _ in segments)
    seen: Counter[str] = Counter()

    visits: list[ActivityVisit] = []
    for ordinal, (first, last, exit_kind) in enumerate(segments, start=1):
        opening = steps[first]
        closing = steps[last]
        seen[opening.activity] += 1
        trail = tuple(
            span
            for span_first, span_last, span in spans
            if first <= span_first and span_last <= last
        )
        window = steps[first : last + 1]
        outcome = closing.outcome
        visits.append(
            ActivityVisit(
                visit_ordinal=ordinal,
                activity=opening.activity,
                activity_has_mop=opening.activity_has_mop,
                revisit_index=seen[opening.activity],
                visits_of_activity=totals[opening.activity],
                first_step=opening.step,
                last_step=closing.step,
                n_steps=len(window),
                t_start_ms=opening.t_rel_ms,
                t_end_ms=closing.t_rel_ms,
                duration_ms=closing.t_rel_ms - opening.t_rel_ms,
                steps=tuple(window),
                state_trail=trail,
                distinct_states=len({row.state_key for row in window}),
                state_visits=len(trail),
                action_type_counts=dict(
                    Counter(action_type(row.action) for row in window)
                ),
                decision_source_counts=dict(
                    Counter(row.decision_source for row in window)
                ),
                n_edittext_clicks=sum(
                    1
                    for row in window
                    if action_type(row.action) == CLICK and is_text_entry(row.action)
                ),
                n_form_boosted_steps=sum(1 for row in window if row.form > 0),
                n_llm_calls=sum(len(row.llm) for row in window),
                closing_action=closing.action,
                closing_type=action_type(closing.action),
                exit_kind=exit_kind,
                target_activity=None if outcome is None else outcome.target_activity,
                target_activity_has_mop=(
                    None if outcome is None else outcome.target_activity_has_mop
                ),
                violations=_streams_of(items[first : last + 1], "violations"),
                monitored_ops=_streams_of(items[first : last + 1], "monitored_ops"),
                diagnostics=_streams_of(items[first : last + 1], "diagnostics"),
                uicov=_coverage_of(items[first : last + 1], trail),
            )
        )
    return visits


def _streams_of(items: Sequence[Any], name: str) -> Tuple[Any, ...]:
    """One placed logcat stream, concatenated in step order across the visit."""
    placed: list[Any] = []
    for item in items:
        placed.extend(getattr(item, name, ()) or ())
    return tuple(placed)


def _coverage_of(
    items: Sequence[Any], trail: Sequence[StateSpan]
) -> Tuple[Tuple[str, Any], ...]:
    """Per-state coverage for the trail's keys, in the order the visit met them.

    One payload per key, not one per span: the dump is per state and cumulative
    over the run, so a state returned to does not have a second payload.
    """
    payloads: dict[str, Any] = {}
    for item in items:
        payload = getattr(item, "uicov", None)
        if payload is None:
            continue
        payloads.setdefault(_step_of(item).state_key, payload)
    ordered: list[Tuple[str, Any]] = []
    taken: set[str] = set()
    for span in trail:
        if span.state_key in payloads and span.state_key not in taken:
            taken.add(span.state_key)
            ordered.append((span.state_key, payloads[span.state_key]))
    return tuple(ordered)


def form_episodes(visit: ActivityVisit) -> list[FormEpisode]:
    """The form-filling episodes inside one visit.

    An episode accumulates clicks on text-entry widgets and is closed by the
    first click on anything else — the submit candidate — or by the visit's end.
    A step that is not a click at all (a scroll, a back, a menu) neither fills
    nor submits and leaves the episode open: scrolling between two fields is
    form-filling behaviour, and only a click can be a submit.

    Args:
        visit: The visit to look inside.

    Returns:
        The episodes in order. Empty when the visit clicked no text field.
    """
    episodes: list[FormEpisode] = []
    fills: list[StepRow] = []

    for row in visit.steps:
        if action_type(row.action) != CLICK:
            continue
        if is_text_entry(row.action):
            fills.append(row)
            continue
        if fills:
            episodes.append(_episode(visit, fills, submit=row))
            fills = []

    if fills:
        episodes.append(_episode(visit, fills, submit=None))
    return episodes


def _episode(
    visit: ActivityVisit, fills: Sequence[StepRow], *, submit: Optional[StepRow]
) -> FormEpisode:
    """Assemble one episode, resolving what its submit candidate achieved."""
    closed_the_visit = submit is not None and submit is visit.steps[-1]
    return FormEpisode(
        first_step=fills[0].step,
        last_step=fills[-1].step if submit is None else submit.step,
        n_fills=len(fills),
        distinct_edit_targets=len({_edit_target(row.action) for row in fills}),
        submit_action=None if submit is None else submit.action,
        submit_exit_kind=visit.exit_kind if closed_the_visit else None,
    )
