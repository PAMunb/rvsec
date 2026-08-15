"""`tasks.json` is read by identity, and every attempt is accounted for.

The unit tests here are written against the shapes that actually broke a reading
of this file: a retry appended with a fresh UUID, a failed attempt carrying more
coverage than the retry that succeeded, and a record whose own
`state_transitions[]` says `COMPLETED` five times over. The last of the tests is
gated on FIXTURE-REAL and asserts the campaign's arithmetic against the pinned
manifest rather than against a literal, so a number that changes has to change
in the manifest first.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pytest

from aperv_tool.analysis.tasks_record import (
    IdentityCollisionUnresolved,
    arm_label,
    classify_error,
    load,
)

# The two failure messages rv-platform writes, in the form the records carry
# them. Only the fragment that classifies matters; the tail is a Task ID or an
# adb transcript.
INSTALL_MESSAGE = (
    "TaskExecutionError: EmulatorError: Failed to install app com.jerboa_87.apk "
    "caused by RuntimeError: APK installation failed"
)
TOOL_EXECUTION_MESSAGE = (
    "TaskExecutionError: Component ToolExecutionComponent execution failed "
    "(Task ID: 47e61ae7-5393-4178-b844-ec7db6a0b0f1)"
)


def _record(
    task_id: str,
    *,
    apk: str = "app.demo_1.apk",
    tool: str = "aperv",
    variant: str | None = "mop_on_llm_off",
    rep: int = 1,
    timeout: int = 300,
    state: str = "COMPLETED",
    error: str | None = None,
    seconds: int = 361,
    method_coverage: float = 10.0,
    transitions: int = 0,
) -> Dict[str, Any]:
    """One task record in the shape rv-platform writes it."""
    return {
        "id": task_id,
        "config": {
            "apk_name": apk,
            "repetition": rep,
            "timeout": timeout,
            "tool_config": {"name": tool, "variant": variant, "parameters": {}},
            "device_id": "emulator-5554",
        },
        "result": {
            "state": state,
            "start_time": "2026-08-12T19:31:49.378028",
            "end_time": "2026-08-12T19:37:50.881878",
            "tool_execution_start": "2026-08-12T19:32:39.237156",
            "execution_time_seconds": seconds,
            "error_message": error,
            "logcat_file": f"{apk}__{rep}__{timeout}__{tool}.logcat",
            "trace_file": f"{apk}__{rep}__{timeout}__{tool}.trace",
            "coverage_metrics": {
                "method_coverage": method_coverage,
                "activities_coverage": 50.0,
                "methods_mop_reachable_coverage": 18.87,
                "total_errors": 4.0,
                "total_method_calls": 789.0,
            },
            "detected_errors_count": 0,
            "state_transitions": [
                {
                    "state": "COMPLETED",
                    "timestamp": "2026-08-12T19:37:50.881878",
                    "previous_state": "RUNNING",
                }
                for _ in range(transitions)
            ],
        },
    }


def _write(
    tmp_path: Path,
    records: List[Dict[str, Any]],
    *,
    status: str | None = "running",
    bare_list: bool = False,
    name: str = "tasks.json",
) -> Path:
    """A `tasks.json` holding `records`, in either of the two shapes."""
    path = tmp_path / name
    if bare_list:
        path.write_text(json.dumps(records))
        return path
    path.write_text(
        json.dumps(
            {
                "version": 3,
                "timestamp": "2026-08-13T15:07:32.127036",
                "tasks": records,
                "experiment": {"experiment_id": "batch", "current_status": status},
                "statistics": {"total_tasks": len(records)},
            }
        )
    )
    return path


def test_identity_not_task_id(tmp_path: Path) -> None:
    """A resume appends a record; it does not create a run (INV-CAN-03)."""
    path = _write(
        tmp_path,
        [
            _record(
                "aaaaaaaa-0000-0000-0000-000000000001",
                state="ERROR",
                error=TOOL_EXECUTION_MESSAGE,
                seconds=181,
                method_coverage=9.667,
            ),
            _record(
                "bbbbbbbb-0000-0000-0000-000000000002",
                seconds=360,
                method_coverage=9.483,
            ),
        ],
    )
    frame, diagnostics = load(path)

    assert diagnostics.lines == 2
    assert len(frame) == diagnostics.identities == 1
    assert diagnostics.superseded_records == 1
    assert diagnostics.collisions == 1
    assert diagnostics.recovered_retries == 1
    assert diagnostics.recovered_identities == 1
    assert frame.loc[0, "records"] == 2


def test_identity_fields_separate_runs(tmp_path: Path) -> None:
    """Each of the five identity fields distinguishes two runs, not one."""
    base = _record("aaaaaaaa-0000-0000-0000-000000000001")
    variations = [
        base,
        _record("bbbbbbbb-0000-0000-0000-000000000002", apk="other.app_9.apk"),
        _record("cccccccc-0000-0000-0000-000000000003", tool="ape", variant="default"),
        _record("dddddddd-0000-0000-0000-000000000004", variant="mop_off_llm_off"),
        _record("eeeeeeee-0000-0000-0000-000000000005", rep=2),
        _record("ffffffff-0000-0000-0000-000000000006", timeout=1800),
    ]
    frame, diagnostics = load(_write(tmp_path, variations))

    assert len(frame) == diagnostics.identities == len(variations)
    assert diagnostics.collisions == 0


def test_collision_keeps_larger_coverage(tmp_path: Path) -> None:
    """Among `COMPLETED` records the larger coverage wins; a failure never competes.

    The second half is the case that makes "keep the last" and "keep the best"
    disagree on real data: the failed attempt explored further before its
    component died, so it carries the larger number and is still the attempt
    that did not finish.
    """
    frame, _ = load(
        _write(
            tmp_path,
            [
                _record("aaaaaaaa-0000-0000-0000-000000000001", method_coverage=9.483),
                _record("bbbbbbbb-0000-0000-0000-000000000002", method_coverage=12.5),
            ],
        )
    )
    assert frame.loc[0, "method_coverage"] == 12.5
    assert frame.loc[0, "task_id"] == "bbbbbbbb-0000-0000-0000-000000000002"

    frame, _ = load(
        _write(
            tmp_path,
            [
                _record(
                    "cccccccc-0000-0000-0000-000000000003",
                    state="ERROR",
                    error=TOOL_EXECUTION_MESSAGE,
                    seconds=181,
                    method_coverage=9.667,
                ),
                _record(
                    "dddddddd-0000-0000-0000-000000000004",
                    seconds=360,
                    method_coverage=9.483,
                ),
            ],
            name="retry.json",
        )
    )
    assert frame.loc[0, "state"] == "COMPLETED"
    assert frame.loc[0, "method_coverage"] == 9.483


def test_tie_on_coverage_raises(tmp_path: Path) -> None:
    """Two `COMPLETED` records tied on coverage and differing: the author decides."""
    path = _write(
        tmp_path,
        [
            _record("aaaaaaaa-0000-0000-0000-000000000001", seconds=361),
            _record("bbbbbbbb-0000-0000-0000-000000000002", seconds=298),
        ],
    )
    with pytest.raises(IdentityCollisionUnresolved) as caught:
        load(path)

    message = str(caught.value)
    assert "aaaaaaaa-0000-0000-0000-000000000001" in message
    assert "bbbbbbbb-0000-0000-0000-000000000002" in message


def test_tie_with_identical_payload_is_not_a_conflict(tmp_path: Path) -> None:
    """Two identical attempts are one run; only the id and the transitions differ."""
    frame, diagnostics = load(
        _write(
            tmp_path,
            [
                _record("aaaaaaaa-0000-0000-0000-000000000001", transitions=3),
                _record("bbbbbbbb-0000-0000-0000-000000000002", transitions=7),
            ],
        )
    )
    assert len(frame) == 1
    assert diagnostics.collisions == 1


def test_state_transitions_not_counted(tmp_path: Path) -> None:
    """`state_transitions[]` are transitions, never records — parse, never grep.

    A grep for `COMPLETED` over cmp162's eight files returns 2910 against 1455
    real completions, because each record carries its own transition list. The
    same inflation is reproduced here in miniature and asserted against.
    """
    path = _write(
        tmp_path,
        [
            _record("aaaaaaaa-0000-0000-0000-000000000001", transitions=5),
            _record("bbbbbbbb-0000-0000-0000-000000000002", rep=2, transitions=4),
        ],
    )
    frame, diagnostics = load(path)

    assert diagnostics.lines == 2
    assert diagnostics.identities == len(frame) == 2
    assert diagnostics.state_transition_entries == 9

    grepped = path.read_text().count("COMPLETED")
    assert grepped == 11, "the fixture must reproduce the inflation, not avoid it"
    assert grepped > diagnostics.lines


def test_current_status_not_a_gate(tmp_path: Path) -> None:
    """`experiment.current_status` is reported and never acted on.

    It reads `running` in all eight cmp162 files, written when the batch started
    and never updated by whatever stopped it.
    """
    records = [_record("aaaaaaaa-0000-0000-0000-000000000001")]
    running, _ = load(_write(tmp_path, records, status="running", name="a.json"))
    finished, _ = load(_write(tmp_path, records, status="completed", name="b.json"))
    absent, diagnostics = load(_write(tmp_path, records, bare_list=True, name="c.json"))

    assert running.equals(finished)
    assert running.equals(absent)
    assert diagnostics.current_status is None
    assert load(_write(tmp_path, records, name="d.json"))[1].current_status == "running"


def test_error_classes_kept_apart(tmp_path: Path) -> None:
    """An install failure and a mid-exploration death are not the same event."""
    assert classify_error(INSTALL_MESSAGE) == "install_failure"
    assert classify_error(TOOL_EXECUTION_MESSAGE) == "tool_execution_failure"
    assert classify_error("TaskExecutionError: something else") == "other"
    assert classify_error(None) == ""

    frame, diagnostics = load(
        _write(
            tmp_path,
            [
                _record(
                    "aaaaaaaa-0000-0000-0000-000000000001",
                    state="ERROR",
                    error=INSTALL_MESSAGE,
                    seconds=61,
                    method_coverage=0.0,
                ),
                _record(
                    "bbbbbbbb-0000-0000-0000-000000000002",
                    rep=2,
                    state="ERROR",
                    error=TOOL_EXECUTION_MESSAGE,
                    seconds=181,
                    method_coverage=9.667,
                ),
            ],
        )
    )
    assert dict(diagnostics.error_records_by_class) == {
        "install_failure": 1,
        "tool_execution_failure": 1,
    }
    assert diagnostics.dead_identities == 2
    assert sorted(frame["error_class"]) == ["install_failure", "tool_execution_failure"]


def test_dead_identity_keeps_its_last_attempt(tmp_path: Path) -> None:
    """With no `COMPLETED` record, the last attempt is what decided the run."""
    frame, diagnostics = load(
        _write(
            tmp_path,
            [
                _record(
                    "aaaaaaaa-0000-0000-0000-000000000001",
                    state="ERROR",
                    error=TOOL_EXECUTION_MESSAGE,
                    seconds=200,
                ),
                _record(
                    "bbbbbbbb-0000-0000-0000-000000000002",
                    state="ERROR",
                    error=TOOL_EXECUTION_MESSAGE,
                    seconds=127,
                ),
            ],
        )
    )
    assert diagnostics.dead_identities == 1
    assert diagnostics.recovered_retries == 0
    assert frame.loc[0, "execution_time_s"] == 127
    assert diagnostics.dead_identity_keys == (
        ("app.demo_1.apk", "aperv:mop_on_llm_off", 1, 300),
    )


def test_ape_variant_collapses_to_a_bare_arm(tmp_path: Path) -> None:
    """`ape` writes `variant='default'`; the label the CSVs carry is `ape`.

    Without the collapse the arm becomes `ape:default`, joins to nothing, and
    every application leaves the analysis as an arm with no execution.
    """
    assert arm_label("ape", "default") == "ape"
    assert arm_label("aperv", "mop_on_llm_off") == "aperv:mop_on_llm_off"

    frame, _ = load(
        _write(
            tmp_path,
            [
                _record(
                    "aaaaaaaa-0000-0000-0000-000000000001",
                    tool="ape",
                    variant="default",
                )
            ],
        )
    )
    assert frame.loc[0, "arm"] == "ape"
    assert (frame.loc[0, "tool_name"], frame.loc[0, "tool_variant"]) == (
        "ape",
        "default",
    )


def test_unidentifiable_record_is_counted(tmp_path: Path) -> None:
    """A malformed record leaves as a count, never as a silent skip (INV-CAN-04)."""
    broken = _record("aaaaaaaa-0000-0000-0000-000000000001")
    del broken["config"]["apk_name"]
    frame, diagnostics = load(
        _write(tmp_path, [broken, _record("bbbbbbbb-0000-0000-0000-000000000002")])
    )
    assert len(frame) == 1
    assert diagnostics.lines == 2
    assert diagnostics.unidentifiable_records == 1


def test_cmp162_3_dead_22_recovered(cmp162_root: Path, cmp162_facts: dict) -> None:
    """The campaign's arithmetic, asserted against the pinned manifest.

    Identities do not span batches, so the per-file diagnostics sum. The three
    dead identities are the campaign's only runs with no successful attempt, and
    they are invisible in every consolidated CSV.
    """
    totals = {
        "lines": 0,
        "identities": 0,
        "completed": 0,
        "dead": 0,
        "error_records": 0,
        "recovered_retries": 0,
        "recovered_identities": 0,
        "superseded": 0,
    }
    dead_keys: List[tuple] = []
    by_class: Dict[str, int] = {}
    dead_rows = []

    files = sorted((cmp162_root / "results").glob("*/*/tasks.json"))
    assert files, "the campaign tree holds no tasks.json at the pinned depth"

    for path in files:
        frame, diagnostics = load(path)
        totals["lines"] += diagnostics.lines
        totals["identities"] += diagnostics.identities
        totals["completed"] += diagnostics.completed_identities
        totals["dead"] += diagnostics.dead_identities
        totals["error_records"] += diagnostics.error_records
        totals["recovered_retries"] += diagnostics.recovered_retries
        totals["recovered_identities"] += diagnostics.recovered_identities
        totals["superseded"] += diagnostics.superseded_records
        dead_keys.extend(diagnostics.dead_identity_keys)
        for label, count in diagnostics.error_records_by_class:
            by_class[label] = by_class.get(label, 0) + count
        dead_rows.append(frame[frame["state"] != "COMPLETED"])

    assert totals["lines"] == cmp162_facts["task_records"]
    assert totals["identities"] == cmp162_facts["identities"]
    assert totals["completed"] == cmp162_facts["completed_identities"]
    assert totals["dead"] == cmp162_facts["dead_identities"]
    assert totals["error_records"] == cmp162_facts["error_records"]
    assert totals["recovered_retries"] == cmp162_facts["recovered_retry_records"]
    assert totals["recovered_identities"] == cmp162_facts["recovered_retry_identities"]
    assert totals["superseded"] == totals["lines"] - totals["identities"]

    assert sorted(dead_keys) == sorted(
        tuple(entry) for entry in cmp162_facts["dead_identity_list"]
    )

    # The two failure classes partition the ERROR records, and they differ in
    # whether the application ran: an install failure leaves zero coverage, a
    # dead exploration component leaves whatever it had explored.
    assert set(by_class) == {"install_failure", "tool_execution_failure"}
    assert sum(by_class.values()) == cmp162_facts["error_records"]

    import pandas as pd

    dead = pd.concat(dead_rows, ignore_index=True)
    assert len(dead) == cmp162_facts["dead_identities"]
    assert set(dead["error_class"]) == {"tool_execution_failure"}
    assert (dead["method_coverage"] > 0).all(), (
        "a run whose component died mid-exploration carries a plausible coverage "
        "number; that is why the collision policy cannot simply keep the last record"
    )
