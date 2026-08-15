"""The `droidbot` parser, against the pinned runs it was written for.

The tests are organised around the three absences the parser must declare rather
than repair — no clock, no step index, no activity on most events — plus the one
run in the sample that ended in an orderly way, without which `truncated` would
be true of every input and the flag would be untested.
"""

from __future__ import annotations

from pathlib import Path

from baseline_runs import trace_of

from aperv_tool.analysis import baseline_droidbot

# The event classes measured in the corpus, by share of 5,141 actions:
# TouchEvent 60.8 %, KeyEvent 19.0 %, IntentEvent 13.1 %, ScrollEvent 3.5 %,
# SetTextEvent 1.4 %, KillAppEvent 1.2 %, LongTouchEvent 0.9 %.
KNOWN_EVENT_TYPES = {
    "TouchEvent",
    "KeyEvent",
    "IntentEvent",
    "ScrollEvent",
    "SetTextEvent",
    "KillAppEvent",
    "LongTouchEvent",
}

# The events that carry no widget identity, and therefore no activity.
WIDGETLESS = {"KeyEvent", "IntentEvent", "KillAppEvent"}


def _longest_run(directory: Path, manifest: dict) -> Path:
    """The densest pinned run: 109 events at 300 s, cut by the timeout."""
    return trace_of(
        directory,
        manifest,
        apk="app.maskan.chat_90.apk",
        repetition=3,
        timeout_s=300,
        arm="droidbot:bfs_naive",
    )


def _orderly_run(directory: Path, manifest: dict) -> Path:
    """The one pinned run that reached `Finish sending events`."""
    return trace_of(
        directory,
        manifest,
        apk="app.maskan.chat_90.apk",
        repetition=3,
        timeout_s=300,
        arm="droidbot:dfs_naive",
    )


def test_clock_null(baseline_sample_dir, baseline_sample_manifest) -> None:
    """Every record carries an explicit null clock, on every pinned run.

    The stream prints no timestamp after exploration begins. The sibling
    `.logcat` does carry absolute milliseconds, but it times RVSEC events rather
    than tool actions, so anchoring an action to it would be an inference the
    data does not support.
    """
    for record in baseline_sample_manifest["runs"]:
        if not record["arm"].startswith("droidbot"):
            continue
        path = trace_of(
            baseline_sample_dir,
            baseline_sample_manifest,
            apk=record["apk"],
            repetition=record["repetition"],
            timeout_s=record["timeout_s"],
            arm=record["arm"],
        )
        frame = baseline_droidbot.parse(path).step_frame()

        assert not frame.empty, f"{path.name} produced no event"
        assert frame["t_rel_ms"].isna().all(), f"{path.name} invented a relative clock"
        assert frame["t_epoch_ms"].isna().all(), f"{path.name} invented an origin"


def test_synth_ordinal_flag(baseline_sample_dir, baseline_sample_manifest) -> None:
    """The index is ours, counted over the dispatched events, and says so.

    The tool prints no index. Counting is sound because the stream is sequential,
    but a reader must be able to tell this ordinal from `ape`'s native one, which
    is what the flag is for (INV-CAN-19).
    """
    run = baseline_droidbot.parse(
        _longest_run(baseline_sample_dir, baseline_sample_manifest)
    )

    assert [step.step for step in run.steps] == list(range(1, len(run.steps) + 1))
    assert len(run.steps) == 109

    frame = run.step_frame()
    assert frame["step_index_synthesized"].all()
    assert run.policy == "bfs_naive"
    assert (frame["policy"] == "bfs_naive").all()
    assert set(frame["action_type"]) <= KNOWN_EVENT_TYPES


def test_activity_unknown_counted(
    baseline_sample_dir, baseline_sample_manifest
) -> None:
    """The activity is a simple name where it exists and a counted null elsewhere.

    It appears only inside a touched view's parenthetical. The name is left
    unresolved: reattaching a package prefix would reconstruct a nested or
    library activity wrongly, and silently. Over the six pinned runs the share of
    events carrying an activity is 60.4 %, against the roughly 58 % the corpus
    survey measured over 5,141 actions.
    """
    events = 0
    with_activity = 0

    for record in baseline_sample_manifest["runs"]:
        if not record["arm"].startswith("droidbot"):
            continue
        path = trace_of(
            baseline_sample_dir,
            baseline_sample_manifest,
            apk=record["apk"],
            repetition=record["repetition"],
            timeout_s=record["timeout_s"],
            arm=record["arm"],
        )
        run = baseline_droidbot.parse(path)
        named = [step for step in run.steps if step.activity is not None]

        assert run.activity_unknown_steps == len(run.steps) - len(named)
        assert all("." not in step.activity for step in named), "left unresolved"

        events += len(run.steps)
        with_activity += len(named)

    assert events == 227
    assert 0.55 <= with_activity / events <= 0.65


def test_orderly_stop_not_truncated(
    baseline_sample_dir, baseline_sample_manifest
) -> None:
    """The rare orderly stop clears `truncated`; the timeout cut does not.

    Five of 150 sampled runs stop this way. Both runs here are 300 s replicas of
    the same application, so the flag is separating the terminator from the
    budget rather than from the workload.
    """
    orderly = baseline_droidbot.parse(
        _orderly_run(baseline_sample_dir, baseline_sample_manifest)
    )
    cut = baseline_droidbot.parse(
        _longest_run(baseline_sample_dir, baseline_sample_manifest)
    )

    assert orderly.truncated is False
    assert cut.truncated is True
    assert orderly.exploration_started and cut.exploration_started
    assert orderly.unparsed_lines == 0 and cut.unparsed_lines == 0


def test_intent_killapp_no_widget(
    baseline_sample_dir, baseline_sample_manifest
) -> None:
    """The widgetless event classes carry no view, no activity and no invention.

    `KeyEvent`, `IntentEvent` and `KillAppEvent` are 33 % of the events in the
    corpus; a parser that filled their activity from the previous event would
    look far better on paper and would be reporting a screen the tool never
    attributed to the action.
    """
    run = baseline_droidbot.parse(
        _longest_run(baseline_sample_dir, baseline_sample_manifest)
    )

    widgetless = [step for step in run.steps if step.event_type in WIDGETLESS]
    touched = [step for step in run.steps if step.event_type == "TouchEvent"]

    assert widgetless, "the pinned run is expected to hold widgetless events"
    assert touched, "and touch events, or the contrast proves nothing"
    assert all(step.view is None for step in widgetless)
    assert all(step.activity is None for step in widgetless)
    assert all(step.view is not None for step in touched)
    assert all(step.activity is not None for step in touched)

    # The preamble is skipped rather than parsed: androguard's static-analysis
    # narration holds no event and is thousands of lines long.
    assert run.preamble_lines > 1000
    assert run.preamble_lines < run.lines_read


def test_decision_source_is_a_small_vocabulary(
    baseline_sample_dir, baseline_sample_manifest
) -> None:
    """Provenance is categorical, and an event with none is left null.

    The payload after a colon names one widget or one target screen; keeping it
    would give one category per widget. What survives is the tool's own text with
    its variable half redacted. An event dispatched with no policy line of its
    own — a restart intent — carries `None` rather than the previous event's
    reason.
    """
    naive = baseline_droidbot.parse(
        _longest_run(baseline_sample_dir, baseline_sample_manifest)
    )
    greedy = baseline_droidbot.parse(
        trace_of(
            baseline_sample_dir,
            baseline_sample_manifest,
            apk="app.maskan.chat_90.apk",
            repetition=1,
            timeout_s=60,
            arm="droidbot:bfs_greedy",
        )
    )

    naive_sources = {step.decision_source for step in naive.steps} - {None}
    greedy_sources = {step.decision_source for step in greedy.steps} - {None}

    assert naive_sources == {
        "selected an un-clicked view",
        "selected a transition view",
    }
    assert greedy_sources == {
        "Trying an unexplored event.",
        "Trying to start the app...",
    }
    assert any(step.decision_source is None for step in naive.steps)
    assert naive_sources.isdisjoint(greedy_sources), "the policies differ, visibly"
