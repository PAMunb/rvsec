"""The teardown coverage dump joins the step timeline, inside one run only.

Two things are being kept true here. The first is that the join is **total**: the
`UICOV state=` key and the NDJSON `STATE.key` are the same string, and on the
recorded campaign every dump row finds its key and every key finds its row. The
manifest carries that measurement (`uicov_join`), and the test asserts against the
manifest rather than against a literal, so a regenerated pin moves the expectation
and a changed reader does not.

The second is that the key **never leaves its run**. It embeds a JVM identity
hash, so a cross-run join on it matches nothing truthfully and plenty plausibly —
which is the failure mode that makes an exception the right answer rather than a
warning in a docstring.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fixture_gate import MISSING_REAL

from aperv_tool.analysis import coverage_dump, state_coverage_join, trace_ndjson
from aperv_tool.analysis.coverage_dump import DumpStatus, RunCoverage, StateCoverage
from aperv_tool.analysis.state_coverage_join import CrossRunStateKey

# The ordering the campaign measurement used, and the only one under which "the
# first N runs" is reproducible from the tree alone. It mirrors the manifest's own
# `measured_figures.ordering`, widened from one arm to both instrumented arms.
UICOV_GLOB = "results/*/*/*/*__aperv:*.trace"


def _state(key: str, discovered: int = 4, interacted: int = 2) -> StateCoverage:
    return StateCoverage(
        state_key=key,
        discovered=discovered,
        interacted=interacted,
        mop_reach=0,
        by_type={"MODEL_CLICK": (interacted, discovered)},
    )


def _coverage(*states: StateCoverage) -> RunCoverage:
    return RunCoverage(
        trace_path=Path("run.trace"),
        apk="app.apk",
        repetition=1,
        timeout_seconds=300,
        arm="aperv:mop_on_llm_off",
        status=DumpStatus.COMPLETE,
        states=tuple(states),
    )


def _row(
    step: int, state_key: str, activity: str = "com.example.Main"
) -> trace_ndjson.StepRow:
    return trace_ndjson.StepRow(
        step=step,
        t_rel_ms=step * 1000,
        t_epoch_ms=None,
        activity=activity,
        activity_has_mop=False,
        state_key=state_key,
        action="g0a0@MODEL_CLICK",
        decision_source="Coverage",
        pick_channel="roulette_greedy",
    )


def test_payload_rides_the_step_and_says_it_is_cumulative() -> None:
    """A step gets its state's dump row, labelled for what the row measures."""
    rows = [_row(1, "S1"), _row(2, "S2"), _row(3, "S1")]
    frame, totals = state_coverage_join.join(
        rows, _coverage(_state("S1"), _state("S2"))
    )

    assert list(frame["step"]) == [1, 2, 3]
    assert list(frame["uicov_present"]) == [True, True, True]
    # The dump is written once, at teardown, with counters accumulated over the
    # whole run: the two rows of S1 carry the same value because it is the same
    # measurement, not because the state was seen twice.
    assert list(frame["uicov_discovered"]) == [4, 4, 4]
    assert set(frame["uicov_scope"]) == {state_coverage_join.CUMULATIVE_SCOPE}
    assert totals.total


def test_a_step_without_a_dump_row_is_reported_not_invented() -> None:
    """A truncated teardown leaves steps unjoined, and says how many."""
    rows = [_row(1, "S1"), _row(2, "S2")]
    frame, totals = state_coverage_join.join(rows, _coverage(_state("S1")))

    assert list(frame["uicov_present"]) == [True, False]
    assert pd.isna(frame.loc[1, "uicov_discovered"])
    assert totals.orphan_step_keys == 1
    assert not totals.total


def test_no_cross_run_key() -> None:
    """A state key is refused at the run boundary, by exception."""
    rows = [_row(1, "S1")]
    frame, _ = state_coverage_join.join(rows, _coverage(_state("S1")))

    with pytest.raises(CrossRunStateKey) as raised:
        state_coverage_join.combine_runs([("run-a", frame)], grain="state")
    assert "state" in str(raised.value)

    # The frame itself carries no run identity, so there is nothing on it that
    # would make a concatenation across runs look keyed.
    assert "run_id" not in frame.columns
    assert "apk" not in frame.columns

    combined = state_coverage_join.combine_runs(
        [("run-a", frame), ("run-b", frame)], grain="activity"
    )
    assert list(combined["run_id"]) == ["run-a", "run-b"]
    assert "state_key" not in combined.columns


def test_activity_grain_sums_states_once_not_once_per_step() -> None:
    """Cumulative counters must not be multiplied by how often a state was visited."""
    rows = [_row(1, "S1"), _row(2, "S1"), _row(3, "S2")]
    frame, _ = state_coverage_join.join(
        rows, _coverage(_state("S1", 4, 2), _state("S2", 6, 1))
    )

    combined = state_coverage_join.combine_runs([("run-a", frame)])

    assert list(combined["uicov_discovered"]) == [10]
    assert list(combined["uicov_interacted"]) == [3]


def test_uicov_total_join(cmp162_root: Path, cmp162_manifest: dict) -> None:
    """The join is a total bijection on the campaign (FIXTURE-REAL).

    The basis is the first `runs` instrumented traces in sorted path order — the
    ordering the manifest declares for its measured figures — and the expected
    counts come from `manifest["uicov_join"]`, never from a literal here.
    """
    expected = cmp162_manifest["uicov_join"]
    traces = sorted(cmp162_root.glob(UICOV_GLOB))[: expected["runs"]]
    if len(traces) < expected["runs"]:
        pytest.skip(f"{MISSING_REAL}: {len(traces)} instrumented traces under the tree")

    dump_states = 0
    matched = 0
    orphan_dump = 0
    orphan_steps = 0
    for trace in traces:
        coverage = coverage_dump.parse_run(trace)
        keys = [row.state_key for row in trace_ndjson.TraceReader(trace)]
        totals = state_coverage_join.totals(keys, coverage)
        dump_states += totals.dump_states
        matched += totals.matched
        orphan_dump += totals.orphan_dump_states
        orphan_steps += totals.orphan_step_keys

    assert len(traces) == expected["runs"]
    assert dump_states == expected["uicov_states"]
    assert matched == expected["state_keys_matched"]
    # Zero on both sides: the dump set is an exact subset of the step set and the
    # step set an exact subset of the dump set, which is what makes it a bijection
    # rather than a containment.
    assert orphan_dump == expected["orphans"]
    assert orphan_steps == expected["orphans"]
