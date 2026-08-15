"""The `ape` parser, against the pinned runs it was written for.

Each test here corresponds to a property of the stream that a plausible parser
gets wrong: a run with no step marker raising instead of returning, a final block
cut by the timeout being dropped, decision provenance being read as free text,
and a one-second clock being treated as if it supported per-step latency.
"""

from __future__ import annotations

from pathlib import Path

from baseline_runs import trace_of

from aperv_tool.analysis import baseline_ape

# The strategy names the tool prints. A run whose strategies fall outside this
# set is either a different build or a parse that captured the wrong token.
KNOWN_STRATEGIES = {
    "EARLY_STAGE",
    "EPSILON_GREEDY",
    "USE_BUFFER",
    "RANDOM",
    "TRIVIAL_ACTIVITY",
    "SATURATED_STATE",
    "BUFFER_LOSS",
    "FILL_BUFFER",
    "BAD_STATE",
    "NULL",
}


def _ordinary_run(directory: Path, manifest: dict) -> Path:
    """The densest pinned run: 50 steps in 60 seconds, no anomaly in it."""
    return trace_of(
        directory,
        manifest,
        apk="app.pwhs.universalinstaller_24.apk",
        repetition=1,
        timeout_s=60,
        arm="ape",
    )


def test_no_steps_outcome(baseline_sample_dir, baseline_sample_manifest) -> None:
    """A trace with no step marker is a run with zero steps, not an error.

    One of 80 sampled traces looks like this. A parser that raised would delete
    the run from every denominator it appears in, and the deletion would be
    invisible in the result.
    """
    path = trace_of(
        baseline_sample_dir,
        baseline_sample_manifest,
        apk="com.shub39.dharmik.online_2200.apk",
        repetition=1,
        timeout_s=60,
        arm="ape",
    )

    run = baseline_ape.parse(path)

    assert run.steps == ()
    assert run.activity_unknown_steps == 0
    assert run.lines_read > 0, "the file was read, it simply had no step in it"
    assert run.key is not None, "the run keeps its identity, so it keeps its place"
    assert run.key.apk == "com.shub39.dharmik.online_2200.apk"

    frame = run.step_frame()
    assert frame.empty
    assert list(frame.columns) == list(baseline_ape.STEP_FRAME_COLUMNS)


def test_unterminated_block(
    baseline_sample_dir, baseline_sample_manifest, tmp_path
) -> None:
    """A final block cut mid-stream is emitted with what it had printed.

    The cut is made by truncating a pinned trace at its last `SATA end step`,
    which is the shape a timeout produces: the run is killed inside a block. No
    trace in the sample is naturally unterminated, because all six were killed
    between blocks; the property still has to hold.
    """
    path = _ordinary_run(baseline_sample_dir, baseline_sample_manifest)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    cut = max(i for i, line in enumerate(lines) if "SATA end step" in line)
    truncated_trace = tmp_path / path.name
    truncated_trace.write_text("\n".join(lines[:cut]), encoding="utf-8")

    whole = baseline_ape.parse(path)
    cut_run = baseline_ape.parse(truncated_trace)

    assert whole.unterminated_blocks == 0
    assert cut_run.unterminated_blocks == 1
    assert len(cut_run.steps) == len(whole.steps), "the open block is still emitted"
    assert cut_run.steps[-1].step == whole.steps[-1].step
    assert cut_run.steps[-1].strategy == whole.steps[-1].strategy
    assert cut_run.truncated, "no ape trace carries the epilogue that would deny this"


def test_strategy_provenance(baseline_sample_dir, baseline_sample_manifest) -> None:
    """The named strategy reaches `decision_source`, the column `aperv` fills.

    Decision provenance is the signal an earlier draft of the plan assumed the
    baselines did not have. They do, on 99.6 % of `ape` steps, and it lands in
    the same column as `aperv`'s so a cross-tool question about *why* an action
    was chosen is answerable at a coarser grain rather than not at all.
    """
    run = baseline_ape.parse(
        _ordinary_run(baseline_sample_dir, baseline_sample_manifest)
    )

    strategies = [step.strategy for step in run.steps]
    assert len(strategies) == 50
    assert all(strategy in KNOWN_STRATEGIES for strategy in strategies)
    assert len(set(strategies)) > 1, "one value for every step would mean a stuck read"

    frame = run.step_frame()
    assert list(frame["decision_source"]) == strategies
    assert list(frame["action_type"]) == [step.action_type for step in run.steps]
    assert all(action_type.startswith("MODEL_") for action_type in frame["action_type"])


def test_elapsed_one_second_grain(
    baseline_sample_dir, baseline_sample_manifest
) -> None:
    """The clock is one-second granular, so per-step latency is not derivable.

    `[Elapsed: DDDD HH:MM:SS]` has no sub-second field. The consequence is not
    cosmetic: consecutive steps share a value, so a difference between two steps
    is frequently zero for reasons of resolution rather than speed, and this test
    records that the resolution is real rather than an artefact of the parse.
    """
    run = baseline_ape.parse(
        _ordinary_run(baseline_sample_dir, baseline_sample_manifest)
    )

    clocks = [step.elapsed_s for step in run.steps]
    assert all(clock is not None for clock in clocks)
    assert clocks == sorted(clocks), "the elapsed clock is monotonic"
    assert clocks[-1] > clocks[0], "a 60 s run advances its clock"
    assert len(set(clocks)) < len(clocks), "consecutive steps share a second"

    frame = run.step_frame()
    assert all(value % 1000 == 0 for value in frame["t_rel_ms"])
    assert frame["t_epoch_ms"].isna().all(), "no absolute origin is printed anywhere"


def test_not_responding_is_a_run_event(
    baseline_sample_dir, baseline_sample_manifest
) -> None:
    """An ANR is hoisted to the run, carrying the step it followed.

    It is printed between blocks, by the framework rather than by the tool, so
    parsing it as a step would insert a phantom into a count that is already a
    per-tool unit.
    """
    path = trace_of(
        baseline_sample_dir,
        baseline_sample_manifest,
        apk="com.serwylo.retrowars_70.apk",
        repetition=3,
        timeout_s=60,
        arm="ape",
    )

    run = baseline_ape.parse(path)

    assert len(run.steps) == 9
    assert [event.kind for event in run.events] == ["NOT_RESPONDING"]
    assert run.events[0].after_step == 8
    assert run.events[0].detail.startswith("// NOT RESPONDING")
    assert all(step.step != 0 for step in run.steps), "no phantom step was inserted"


def test_every_pinned_ape_run_parses(
    baseline_sample_dir, baseline_sample_manifest
) -> None:
    """All six, so a property proved on one is not proved on an outlier.

    The unparsed count is asserted at zero against a read of thousands of lines:
    the parser targets a handful of markers, and any of them failing to decompose
    would mean the log format moved.
    """
    pinned = [run for run in baseline_sample_manifest["runs"] if run["arm"] == "ape"]
    assert len(pinned) == 6

    for record in pinned:
        path = trace_of(
            baseline_sample_dir,
            baseline_sample_manifest,
            apk=record["apk"],
            repetition=record["repetition"],
            timeout_s=record["timeout_s"],
            arm=record["arm"],
        )
        run = baseline_ape.parse(path)

        assert run.unparsed_lines == 0, f"{path.name} carries a marker that moved"
        assert run.truncated, f"{path.name} is expected to lack the Monkey epilogue"
        assert run.activity_unknown_steps == 0, f"{path.name} lost an activity"
        assert all(step.model is not None for step in run.steps)
