"""A campaign becomes one frame, and everything left out leaves as a number.

The synthetic batches below are the smallest trees that reproduce the three
shapes a real campaign has taught this loader to survive: the bind-mount double
nesting, a consolidated CSV that is simply not there, and the compressed trace
sibling that doubles a run's stream count if it is mistaken for one. The gated
tests assert cmp162's arithmetic against the pinned manifest, never against a
literal.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Sequence, Tuple

import pytest

from aperv_tool.analysis.loader import find_batches, load
from aperv_tool.analysis.run_identity import UnknownArm

#: cmp162's roster, supplied as data exactly as a caller must supply it.
CMP162_ARMS = {
    "ape": ("ape", ""),
    "aperv:mop_off_llm_off": ("aperv", "mop_off_llm_off"),
    "aperv:mop_on_llm_off": ("aperv", "mop_on_llm_off"),
}

#: One synthetic run: `(apk, arm, rep, timeout, state)`.
Run = Tuple[str, str, int, int, str]

_SUMMARY_HEADER = [
    "apk",
    "rep",
    "timeout",
    "tool",
    "cov_act",
    "cov_class",
    "cov_method",
    "cov_reachable",
    "cov_reaches_target",
    "cov_directly_reaches_target",
    "mop_errors_total",
    "mop_errors_unique",
]
_PERFORMANCE_HEADER = [
    "apk",
    "rep",
    "timeout",
    "tool",
    "execution_time_seconds",
    "task_state",
    "timestamp",
]


def _tool_config(arm: str) -> dict:
    """The `tool_config` an arm label was written from.

    `ape` is the collapsed form of `ape`/`default`; everything else is
    `tool:variant` as the orchestrator wrote it.
    """
    if ":" not in arm:
        return {"name": arm, "variant": "default", "parameters": {}}
    tool, variant = arm.split(":", 1)
    return {"name": tool, "variant": variant, "parameters": {}}


def _make_batch(
    batch: Path,
    runs: Sequence[Run],
    *,
    files: Iterable[str] = ("summary.csv", "performance.csv"),
    artefacts: Iterable[str] = (".trace", ".logcat"),
    compressed_sibling: bool = False,
) -> Path:
    """A batch directory holding `runs`: the record, the CSVs and the streams."""
    batch.mkdir(parents=True, exist_ok=True)
    records = []
    for index, (apk, arm, rep, timeout, state) in enumerate(runs):
        records.append(
            {
                "id": f"{index:08d}-0000-0000-0000-000000000000",
                "config": {
                    "apk_name": apk,
                    "repetition": rep,
                    "timeout": timeout,
                    "tool_config": _tool_config(arm),
                },
                "result": {
                    "state": state,
                    "execution_time_seconds": 361 if state == "COMPLETED" else 61,
                    "error_message": (
                        None
                        if state == "COMPLETED"
                        else (
                            "TaskExecutionError: EmulatorError: Failed to install app "
                            + apk
                        )
                    ),
                    "coverage_metrics": {
                        "method_coverage": 22.3 if state == "COMPLETED" else 0.0,
                        "activities_coverage": 50.0 if state == "COMPLETED" else 0.0,
                        "methods_mop_reachable_coverage": 18.8,
                        "total_errors": 4.0,
                        "total_method_calls": 789.0,
                    },
                    "detected_errors_count": 0,
                    "state_transitions": [],
                },
            }
        )
    (batch / "tasks.json").write_text(
        json.dumps(
            {
                "version": 3,
                "tasks": records,
                "experiment": {"current_status": "running"},
            }
        )
    )

    completed = [run for run in runs if run[4] == "COMPLETED"]
    if "summary.csv" in files:
        with (batch / "summary.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(_SUMMARY_HEADER)
            for apk, arm, rep, timeout, _ in completed:
                writer.writerow(
                    [apk, rep, timeout, arm, 50.0, 38.05, 22.34, 26.63, 18.87, 0, 20, 4]
                )
    if "performance.csv" in files:
        with (batch / "performance.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(_PERFORMANCE_HEADER)
            for apk, arm, rep, timeout, _ in completed:
                writer.writerow(
                    [apk, rep, timeout, arm, 361, "TaskState.COMPLETED", 1786644596.9]
                )

    for apk, arm, rep, timeout, _ in runs:
        app_dir = batch / apk
        app_dir.mkdir(exist_ok=True)
        stem = f"{apk}__{rep}__{timeout}__{arm}"
        for suffix in artefacts:
            (app_dir / f"{stem}{suffix}").write_text("")
        if compressed_sibling:
            (app_dir / f"{stem}.trace.ndjson.gz").write_bytes(b"")
    return batch


def test_double_nesting_tolerated(tmp_path: Path) -> None:
    """`results/<batch>/<batch>/` is read from any of the four levels above it.

    The nesting is a bind-mount artefact of the container that wrote cmp162.
    Tolerating it means no campaign has to be renamed on disk to be readable.
    """
    batch = _make_batch(
        tmp_path / "results" / "cmp_00" / "cmp_00",
        [("io.keepalive.android_133.apk", "ape", 1, 300, "COMPLETED")],
    )
    for root in (tmp_path, tmp_path / "results", batch.parent, batch):
        assert find_batches(root) == [batch.resolve()], f"not found from {root}"
        frame, diagnostics = load(root, CMP162_ARMS)
        assert len(frame) == diagnostics.identities == 1
        assert diagnostics.batches == ("cmp_00",)


def test_missing_csv_counted_not_dropped(tmp_path: Path) -> None:
    """An absent CSV costs the payload, never the run (INV-CAN-04)."""
    runs = [
        ("io.keepalive.android_133.apk", "ape", 1, 300, "COMPLETED"),
        ("io.keepalive.android_133.apk", "aperv:mop_on_llm_off", 1, 300, "COMPLETED"),
    ]
    _make_batch(tmp_path / "cmp_00", runs, files=("performance.csv",))
    frame, diagnostics = load(tmp_path, CMP162_ARMS)

    assert len(frame) == 2, "a missing CSV must not remove a run"
    assert diagnostics.missing_files == ("cmp_00/summary.csv",)
    assert dict(diagnostics.payload_missing)["summary.csv"] == 2
    assert frame["cov_method"].isna().all(), (
        "the payload columns must exist and be NaN, so a consumer indexing them "
        "fails on the value rather than on a column that stopped existing"
    )
    assert frame["perf_execution_time_s"].notna().all()


def test_identity_without_a_csv_row_keeps_nan_payload(tmp_path: Path) -> None:
    """A failed run is in the record and in no CSV; the join keeps it."""
    runs = [
        ("io.keepalive.android_133.apk", "ape", 1, 300, "COMPLETED"),
        ("com.ds.avare_404.apk", "aperv:mop_on_llm_off", 1, 300, "ERROR"),
    ]
    _make_batch(tmp_path / "cmp_00", runs)
    frame, diagnostics = load(tmp_path, CMP162_ARMS)

    assert len(frame) == 2
    assert diagnostics.dead_identities == 1
    assert dict(diagnostics.payload_missing) == {"summary.csv": 1, "performance.csv": 1}
    assert dict(diagnostics.unmatched_csv_rows) == {
        "summary.csv": 0,
        "performance.csv": 0,
    }
    dead = frame[frame["state"] == "ERROR"].iloc[0]
    assert pd_isna(dead["cov_method"])
    assert dead["method_coverage"] == 0.0


def pd_isna(value) -> bool:
    """`NaN` from a left join, without importing pandas into every assertion."""
    return value != value


def test_unmatched_csv_row_is_counted(tmp_path: Path) -> None:
    """A CSV row no record claims means the two artefacts disagree; say so."""
    batch = _make_batch(
        tmp_path / "cmp_00",
        [("io.keepalive.android_133.apk", "ape", 1, 300, "COMPLETED")],
    )
    with (batch / "summary.csv").open("a", newline="") as handle:
        csv.writer(handle).writerow(
            [
                "ghost.app_1.apk",
                1,
                300,
                "ape",
                50.0,
                38.05,
                22.34,
                26.63,
                18.87,
                0,
                20,
                4,
            ]
        )
    _, diagnostics = load(tmp_path, CMP162_ARMS)

    assert dict(diagnostics.unmatched_csv_rows)["summary.csv"] == 1


def test_ndjson_gz_not_a_second_stream(tmp_path: Path) -> None:
    """The gzip sibling is counted as one, and is never a run's trace.

    Treating it as a stream doubles the trace count and about 1.5 GB of a
    campaign; the run's `trace_path` must stay the uncompressed file.
    """
    _make_batch(
        tmp_path / "cmp_00",
        [("io.keepalive.android_133.apk", "aperv:mop_on_llm_off", 1, 300, "COMPLETED")],
        compressed_sibling=True,
    )
    frame, diagnostics = load(tmp_path, CMP162_ARMS)

    assert diagnostics.trace_files == 1
    assert diagnostics.logcat_files == 1
    assert diagnostics.compressed_trace_siblings == 1
    assert diagnostics.identities_without_trace == 0
    assert frame.loc[0, "trace_path"].endswith("__aperv:mop_on_llm_off.trace")


def test_missing_stream_is_counted(tmp_path: Path) -> None:
    """A run with no trace keeps its row and its reason."""
    _make_batch(
        tmp_path / "cmp_00",
        [("io.keepalive.android_133.apk", "ape", 1, 300, "COMPLETED")],
        artefacts=(".logcat",),
    )
    frame, diagnostics = load(tmp_path, CMP162_ARMS)

    assert len(frame) == 1
    assert diagnostics.identities_without_trace == 1
    assert diagnostics.identities_without_logcat == 0
    assert frame.loc[0, "trace_path"] is None


def test_unknown_arm_raises_rather_than_guessing(tmp_path: Path) -> None:
    """An arm the caller did not declare stops the load (INV-CAN-02)."""
    _make_batch(
        tmp_path / "cmp_00",
        [("io.keepalive.android_133.apk", "droidbot:bfs_greedy", 1, 300, "COMPLETED")],
    )
    with pytest.raises(UnknownArm, match="droidbot:bfs_greedy"):
        load(tmp_path, CMP162_ARMS)


def test_arm_table_supplies_the_decomposition(tmp_path: Path) -> None:
    """`tool`/`variant` come from the table; the record's own pair stays beside them."""
    _make_batch(
        tmp_path / "cmp_00",
        [("io.keepalive.android_133.apk", "ape", 1, 300, "COMPLETED")],
    )
    frame, _ = load(tmp_path, CMP162_ARMS)
    row = frame.iloc[0]

    assert (row["tool"], row["variant"]) == ("ape", "")
    assert (row["tool_name"], row["tool_variant"]) == ("ape", "default")


def test_many_roots_and_a_repeated_identity(tmp_path: Path) -> None:
    """Batches concatenate; an identity in two of them is named, not averaged."""
    run = ("io.keepalive.android_133.apk", "ape", 1, 300, "COMPLETED")
    other = ("de.markusfisch.android.binaryeye_174.apk", "ape", 1, 300, "COMPLETED")
    _make_batch(tmp_path / "one" / "cmp_00", [run, other])
    _make_batch(tmp_path / "two" / "cmp_01", [run])

    frame, diagnostics = load([tmp_path / "one", tmp_path / "two"], CMP162_ARMS)

    assert diagnostics.task_records == 3
    assert len(frame) == diagnostics.identities == 2
    assert diagnostics.duplicate_identities == (
        "io.keepalive.android_133.apk__ape__1__300",
    )
    assert sorted(diagnostics.batches) == ["cmp_00", "cmp_01"]


def test_root_without_a_batch_is_reported(tmp_path: Path) -> None:
    """A mistyped root leaves as a named root, not as an empty campaign."""
    frame, diagnostics = load(tmp_path / "nowhere", CMP162_ARMS)

    assert frame.empty
    assert diagnostics.roots_without_batches == (str(tmp_path / "nowhere"),)


def test_cmp162_1458_identities(cmp162_root: Path, cmp162_manifest: dict) -> None:
    """The whole campaign in one frame, checked against the pinned manifest."""
    facts = cmp162_manifest["facts"]
    frame, diagnostics = load(cmp162_root / "results", CMP162_ARMS)

    assert diagnostics.task_records == facts["task_records"]
    assert len(frame) == diagnostics.identities == facts["identities"]
    assert diagnostics.completed_identities == facts["completed_identities"]
    assert diagnostics.dead_identities == facts["dead_identities"]
    assert diagnostics.error_records == facts["error_records"]
    assert diagnostics.recovered_retries == facts["recovered_retry_records"]
    assert diagnostics.recovered_identities == facts["recovered_retry_identities"]
    assert diagnostics.duplicate_identities == ()
    assert diagnostics.missing_files == ()

    assert sorted(set(frame["arm"])) == sorted(facts["arms"])
    assert sorted(set(frame["rep"])) == sorted(facts["repetitions"])
    assert sorted(set(frame["timeout_s"])) == sorted(facts["timeouts_s"])
    assert frame["apk"].nunique() == facts["applications"]
    assert len(frame) == (
        facts["applications"]
        * len(facts["arms"])
        * len(facts["repetitions"])
        * len(facts["timeouts_s"])
    )

    counts = cmp162_manifest["artefact_counts"]
    assert diagnostics.trace_files == counts["traces"]
    assert diagnostics.logcat_files == counts["logcats"]
    assert diagnostics.compressed_trace_siblings == counts["trace_ndjson_gz"]
    assert diagnostics.artefacts_without_identity == ()


def test_cmp162_failures_are_visible_only_in_tasks_json(
    cmp162_root: Path, cmp162_facts: dict
) -> None:
    """`performance.csv` holds successes alone; the record holds the campaign.

    A loader built on the consolidated CSVs would report 1455 runs, all of them
    successful, and no denominator anywhere would show the three that died.
    """
    frame, diagnostics = load(cmp162_root / "results", CMP162_ARMS)

    completed = frame[frame["state"] == "COMPLETED"]
    assert len(completed) == cmp162_facts["completed_identities"]
    assert set(completed["perf_task_state"]) == {"TaskState.COMPLETED"}

    dead = frame[frame["state"] != "COMPLETED"]
    assert len(dead) == cmp162_facts["dead_identities"]
    assert (
        dead["perf_task_state"].isna().all()
    ), "the dead runs must reach the frame from tasks.json alone"
    assert dead["cov_method"].isna().all()
    assert dict(diagnostics.payload_missing) == {
        "summary.csv": cmp162_facts["dead_identities"],
        "performance.csv": cmp162_facts["dead_identities"],
    }
    assert dict(diagnostics.unmatched_csv_rows) == {
        "summary.csv": 0,
        "performance.csv": 0,
    }
