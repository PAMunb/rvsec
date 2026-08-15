"""The segmenter, on the shapes that decided its design.

Each synthetic case is one of the traps the measurement found: a screen returned
to, a combobox opening and closing inside one screen, a form whose every field
changes the abstract state, a step counter that skips. The gated case is the
whole of it — the same 60 campaign traces the unit was chosen on, asserted
against the pinned manifest rather than against a literal, so a figure that
moves is reported as a difference from what was measured instead of from what
someone typed here.
"""

from __future__ import annotations

import statistics as st
from collections import Counter
from pathlib import Path
from typing import Optional, Sequence

from aperv_tool.analysis.screen_visits import (
    CLICK,
    action_type,
    form_episodes,
    is_text_entry,
    segment,
)
from aperv_tool.analysis.trace_ndjson import StepOutcome, StepRow, TraceReader

MAIN = "com.example.MainActivity"
SETTINGS = "com.example.SettingsActivity"

#: An action string in the shape the agent prints: graph element, `@`, type, and
#: the descriptor's `key=value;` pairs with no separator after the type.
BUTTON = "g0a0[]@MODEL_CLICKclass=android.widget.Button;resource-id=app:id/submit;"
BACK = "g0a1[]@MODEL_BACK"


def edit_action(field: str) -> str:
    """A click on a named text field."""
    return (
        f"g0a2[]@MODEL_CLICKclass=androidx.appcompat.widget.AppCompatEditText;"
        f"resource-id=app:id/{field};"
    )


def step(
    number: int,
    activity: str,
    state_key: str,
    *,
    action: str = BUTTON,
    target_state: Optional[str] = None,
    activity_changed: bool = False,
    resolved: bool = True,
    outcome: bool = True,
    form: int = 0,
) -> StepRow:
    """One step, with the outcome that keeps a visit open unless asked otherwise.

    `target_state` defaults to the step's own key, which is the self-loop that
    closes neither the visit nor the state span.
    """
    landed = StepOutcome(
        resolved=resolved,
        target_state=state_key if target_state is None else target_state,
        target_activity=activity,
        target_activity_has_mop=False,
        activity_changed=activity_changed,
    )
    return StepRow(
        step=number,
        t_rel_ms=number * 1_000,
        t_epoch_ms=None,
        activity=activity,
        activity_has_mop=activity == MAIN,
        state_key=state_key,
        action=action,
        decision_source="model",
        pick_channel="roulette",
        form=form,
        outcome=landed if outcome else None,
    )


def key(activity: str, ordinal: int) -> str:
    """A state key in the agent's shape: activity, identity hash, naming, width."""
    return f"{activity}@{100 + ordinal}@Naming[1]@[W=7]"


def test_revisits_separate() -> None:
    """`A → B → A` is three visits, and the second `A` knows it is the second."""
    rows: Sequence[StepRow] = [
        step(1, MAIN, key(MAIN, 0)),
        step(2, MAIN, key(MAIN, 0)),
        step(3, MAIN, key(MAIN, 0)),
        step(
            4, MAIN, key(MAIN, 0), target_state=key(SETTINGS, 0), activity_changed=True
        ),
        step(5, SETTINGS, key(SETTINGS, 0)),
        step(
            6,
            SETTINGS,
            key(SETTINGS, 0),
            target_state=key(MAIN, 0),
            activity_changed=True,
        ),
        step(7, MAIN, key(MAIN, 0)),
        step(8, MAIN, key(MAIN, 0)),
        step(9, MAIN, key(MAIN, 0)),
    ]

    visits = segment(rows)

    assert [visit.activity for visit in visits] == [MAIN, SETTINGS, MAIN]
    assert [visit.revisit_index for visit in visits] == [1, 1, 2]
    assert [visit.visits_of_activity for visit in visits] == [2, 1, 2]
    assert [(visit.first_step, visit.last_step) for visit in visits] == [
        (1, 4),
        (5, 6),
        (7, 9),
    ]
    assert [visit.n_steps for visit in visits] == [4, 2, 3]
    assert [visit.exit_kind for visit in visits] == [
        "activity_transition",
        "activity_transition",
        "run_end",
    ]
    assert visits[0].activity_has_mop is True
    assert visits[0].target_activity == MAIN


def test_combobox_in_trail() -> None:
    """A dropdown opened and closed is a trail of three, not three visits."""
    inside, dropdown = key(MAIN, 0), key(MAIN, 1)
    rows = [
        step(1, MAIN, inside),
        step(2, MAIN, inside),
        step(3, MAIN, inside, target_state=dropdown),
        step(4, MAIN, dropdown, target_state=inside),
        step(5, MAIN, inside),
    ]

    visits = segment(rows)

    assert len(visits) == 1
    visit = visits[0]
    assert visit.n_steps == 5
    assert visit.state_visits == len(visit.state_trail) == 3
    assert visit.distinct_states == 2
    assert [span.state_key for span in visit.state_trail] == [inside, dropdown, inside]
    assert [span.n_steps for span in visit.state_trail] == [3, 1, 1]
    assert [span.exit_kind for span in visit.state_trail] == [
        "state_transition",
        "state_transition",
        "run_end",
    ]
    assert [(span.enter_step, span.exit_step) for span in visit.state_trail] == [
        (1, 3),
        (4, 4),
        (5, 5),
    ]


def test_no_outcome_closes_visit() -> None:
    """A restart or a component launch ends the visit: the destination is unknown."""
    rows = [
        step(1, MAIN, key(MAIN, 0)),
        step(2, MAIN, key(MAIN, 0), outcome=False),
        step(3, MAIN, key(MAIN, 0)),
    ]

    visits = segment(rows)

    assert [visit.exit_kind for visit in visits] == ["no_outcome", "run_end"]
    assert [visit.n_steps for visit in visits] == [2, 1]
    assert visits[0].target_activity is None
    assert visits[0].target_activity_has_mop is None
    assert [visit.revisit_index for visit in visits] == [1, 2]


def test_teardown_closes_visit() -> None:
    """The in-flight record the teardown flush wrote closes the visit as teardown."""
    rows = [
        step(1, MAIN, key(MAIN, 0)),
        step(2, MAIN, key(MAIN, 0), resolved=False),
    ]

    visits = segment(rows)

    assert len(visits) == 1
    assert visits[0].exit_kind == "teardown"
    assert visits[0].state_trail[-1].exit_kind == "teardown"


def test_next_activity_differs_closes_visit() -> None:
    """The stream may move without the outcome saying so; the visit still ends."""
    rows = [
        step(1, MAIN, key(MAIN, 0)),
        step(2, SETTINGS, key(SETTINGS, 0)),
    ]

    visits = segment(rows)

    assert [visit.exit_kind for visit in visits] == ["next_activity_differs", "run_end"]
    assert visits[0].state_trail[0].exit_kind == "key_change_without_outcome"


def test_form_episode_across_states() -> None:
    """Three fills that each change the state key are one episode, not three."""
    first, second, third, fourth = (key(MAIN, index) for index in range(4))
    rows = [
        step(1, MAIN, first, action=edit_action("user"), target_state=second, form=200),
        step(2, MAIN, second, action=edit_action("mail"), target_state=third, form=200),
        step(3, MAIN, third, action=edit_action("pass"), target_state=fourth, form=200),
        step(
            4,
            MAIN,
            fourth,
            action=BUTTON,
            target_state=key(SETTINGS, 0),
            activity_changed=True,
        ),
    ]

    visits = segment(rows)

    assert len(visits) == 1
    visit = visits[0]
    assert visit.exit_kind == "activity_transition"
    assert visit.last_step == 4
    assert visit.n_edittext_clicks == 3
    assert visit.n_form_boosted_steps == 3
    assert visit.distinct_states == 4

    episodes = form_episodes(visit)

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.n_fills == 3
    assert episode.distinct_edit_targets == 3
    assert episode.submit_action == BUTTON
    assert episode.submit_exit_kind == "activity_transition"
    assert (episode.first_step, episode.last_step) == (1, 4)


def test_form_episode_no_submit_ends_with_visit() -> None:
    """Fields filled and never submitted is an episode with no submit at all."""
    first, second = key(MAIN, 0), key(MAIN, 1)
    rows = [
        step(1, MAIN, first, action=edit_action("user"), target_state=second),
        step(2, MAIN, second, action=edit_action("user")),
        step(3, MAIN, second, action=BACK),
    ]

    visits = segment(rows)
    episodes = form_episodes(visits[0])

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.n_fills == 2
    assert episode.distinct_edit_targets == 1
    assert episode.submit_action is None
    assert episode.submit_exit_kind is None
    assert (episode.first_step, episode.last_step) == (1, 2)


def test_step_numbers_may_skip() -> None:
    """A selection retry reuses the open record, so 44 is followed by 46."""
    rows = [
        step(44, MAIN, key(MAIN, 0)),
        step(46, MAIN, key(MAIN, 0)),
    ]

    visits = segment(rows)

    assert len(visits) == 1
    visit = visits[0]
    assert (visit.first_step, visit.last_step, visit.n_steps) == (44, 46, 2)
    assert visit.duration_ms == 2_000
    span = visit.state_trail[0]
    assert (span.enter_step, span.exit_step, span.n_steps) == (44, 46, 2)


def test_empty_stream_is_no_visits() -> None:
    """A run that produced no step still occupies its denominator."""
    assert segment([]) == []


def test_action_helpers() -> None:
    """The action string's type and its text-entry test, used by the counts."""
    assert action_type(BUTTON) == CLICK
    assert action_type(BACK) == "MODEL_BACK"
    assert action_type("no type here") == "unknown"
    assert is_text_entry(edit_action("user")) is True
    assert is_text_entry(BUTTON) is False


def quantile_at(values: list[int], fraction: float) -> int:
    """The nearest-rank quantile the measurement used.

    Stated here because the figure is an integer and every quantile convention
    returns a different one: this is `sorted(values)[int(fraction * (n - 1))]`.
    """
    ordered = sorted(values)
    return ordered[int(fraction * (len(ordered) - 1))]


def test_cmp162_measured_figures(cmp162_root: Path, cmp162_manifest: dict) -> None:
    """The distributions the Activity grain was chosen on, from the pinned traces.

    Every figure is asserted against `measured_figures` in the manifest, in the
    order the manifest lists the traces. A figure that no longer reproduces is a
    change in the segmenter, and the manifest is what says so.
    """
    figures = cmp162_manifest["measured_figures"]
    traces = [cmp162_root / relative for relative in figures["traces"]]
    missing = [str(path) for path in traces if not path.exists()]
    assert not missing, f"pinned traces absent: {missing[:3]}"

    steps = 0
    visits_per_run: list[int] = []
    visit_lengths: list[int] = []
    distinct_states: list[int] = []
    spans_per_run: list[int] = []
    span_lengths: list[int] = []
    span_kinds: Counter[str] = Counter()
    edit_clicks = 0
    edit_clicks_changing_state = 0

    for path in traces:
        rows = list(TraceReader(path))
        steps += len(rows)
        visits = segment(rows)
        visits_per_run.append(len(visits))
        spans = [span for visit in visits for span in visit.state_trail]
        spans_per_run.append(len(spans))
        for visit in visits:
            visit_lengths.append(visit.n_steps)
            distinct_states.append(visit.distinct_states)
        for span in spans:
            span_lengths.append(span.n_steps)
            span_kinds[span.exit_kind] += 1
        for row in rows:
            if action_type(row.action) != CLICK or not is_text_entry(row.action):
                continue
            edit_clicks += 1
            outcome = row.outcome
            if (
                outcome is not None
                and outcome.resolved
                and not outcome.activity_changed
                and outcome.target_state != row.state_key
            ):
                edit_clicks_changing_state += 1

    assert len(traces) == figures["runs"]
    assert steps == figures["steps"]

    assert st.median(visits_per_run) == figures["activity_visits_per_run_median"]
    assert round(st.mean(visit_lengths), 2) == figures["activity_visit_len_mean"]
    assert st.median(visit_lengths) == figures["activity_visit_len_median"]
    assert quantile_at(visit_lengths, 0.9) == figures["activity_visit_len_p90"]
    assert max(visit_lengths) == figures["activity_visit_len_max"]
    share_one = sum(1 for length in visit_lengths if length == 1) / len(visit_lengths)
    assert round(share_one, 3) == figures["activity_visit_share_len1"]
    assert (
        round(st.mean(distinct_states), 2)
        == figures["distinct_states_per_activity_visit_mean"]
    )

    assert st.median(spans_per_run) == figures["state_visits_per_run_median"]
    assert round(st.mean(span_lengths), 2) == figures["state_visit_len_mean"]
    assert st.median(span_lengths) == figures["state_visit_len_median"]
    span_share_one = sum(1 for length in span_lengths if length == 1) / len(
        span_lengths
    )
    assert round(span_share_one, 3) == figures["state_visit_share_len1"]
    assert {
        kind: round(count / len(span_lengths), 3) for kind, count in span_kinds.items()
    } == figures["state_exit_kind_share"]

    assert edit_clicks == figures["edittext_clicks_total"]
    assert (
        edit_clicks_changing_state
        == figures["edittext_clicks_changing_state_same_activity"]
    )


def test_cmp162_spans_nest_inside_visits(
    cmp162_root: Path, cmp162_manifest: dict
) -> None:
    """Every activity boundary is also a state boundary, on real traces.

    The property is what makes the state trail a partition of the run rather
    than a second, differently-cut segmentation: an Activity change implies a
    key change, so no span ever straddles two visits and the trails add up to
    the run's steps.
    """
    for relative in cmp162_manifest["measured_figures"]["traces"][:5]:
        rows = list(TraceReader(cmp162_root / relative))
        visits = segment(rows)

        assert sum(visit.n_steps for visit in visits) == len(rows)
        for visit in visits:
            assert sum(span.n_steps for span in visit.state_trail) == visit.n_steps
