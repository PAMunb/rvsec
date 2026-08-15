"""Provenance makes a re-derivation checkable, and checks it before computing.

The estimator standing in for a real one here is deliberately trivial and
deterministic — the sum of a file's numbers, trimmed by a parameter — because
what is under test is not the arithmetic but the discipline around it: same
inputs and same parameters must give the identical value, and a changed input
must be reported by ``differences`` before that value is ever produced.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aperv_tool.analysis.provenance import (
    InputRef,
    Provenance,
    differences,
    stamp,
)

NOON = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
PARAMETERS = {"trim": 0.10, "seed": 42, "replica_rule": "majority"}


def a_data_file(tmp_path: Path, text: str = "1\n2\n3\n") -> Path:
    """An input on disk, so the stamp has real bytes to hash."""
    path = tmp_path / "coverage.csv"
    path.write_text(text)
    return path


def estimate_over(path: Path, parameters: dict) -> float:
    """The stand-in estimator: deterministic in its inputs and its parameters."""
    values = [float(line) for line in path.read_text().split()]
    return sum(values) * (1.0 - parameters["trim"])


def test_rederive_bitwise(tmp_path: Path) -> None:
    """Matching hashes and the same parameter set give the identical estimate."""
    data = a_data_file(tmp_path)

    first = stamp("run-a", [data], PARAMETERS, now=NOON)
    first_estimate = estimate_over(data, PARAMETERS)

    second = stamp("run-b", [data], dict(PARAMETERS), now=NOON + timedelta(hours=3))
    assert differences(first, second) == ()
    second_estimate = estimate_over(data, PARAMETERS)

    assert second_estimate == first_estimate
    assert repr(second_estimate) == repr(first_estimate)


def test_changed_input_is_reported_before_any_estimate(tmp_path: Path) -> None:
    """The report comes first; nothing is computed over the moved inputs."""
    data = a_data_file(tmp_path)
    first = stamp("run-a", [data], PARAMETERS, now=NOON)

    data.write_text("1\n2\n4\n")
    second = stamp("run-b", [data], PARAMETERS, now=NOON)

    computed: list[float] = []
    report = differences(first, second)
    if not report:
        computed.append(estimate_over(data, PARAMETERS))

    assert computed == [], "an estimate was produced over changed inputs"
    assert len(report) == 1
    assert report[0].startswith(f"input changed: {data}")
    assert first.inputs[0].sha256 in report[0]
    assert second.inputs[0].sha256 in report[0]


def test_timestamp_does_not_make_a_rerun_incomparable(tmp_path: Path) -> None:
    """The stamping instant lives here precisely so it changes nothing."""
    data = a_data_file(tmp_path)
    first = stamp("run-a", [data], PARAMETERS, now=NOON)
    later = stamp("run-a", [data], PARAMETERS, now=NOON + timedelta(days=90))

    assert first.stamped_at != later.stamped_at
    assert differences(first, later) == ()


def test_changed_parameter_is_reported(tmp_path: Path) -> None:
    """A parameter that moved is as disqualifying as an input that moved."""
    data = a_data_file(tmp_path)
    first = stamp("run-a", [data], PARAMETERS, now=NOON)
    second = stamp("run-b", [data], {**PARAMETERS, "trim": 0.20}, now=NOON)

    assert differences(first, second) == ("parameter changed: trim 0.1 -> 0.2",)


def test_added_and_removed_inputs_are_reported(tmp_path: Path) -> None:
    """A rerun that read a different set of files is not a re-derivation."""
    data = a_data_file(tmp_path)
    extra = tmp_path / "performance.csv"
    extra.write_text("5\n")

    first = stamp("run-a", [data], PARAMETERS, now=NOON)
    second = stamp("run-b", [data, extra], PARAMETERS, now=NOON)

    assert differences(first, second) == (f"input added: {extra}",)
    assert differences(second, first) == (f"input removed: {extra}",)


def test_path_only_input_is_reported_as_uncomparable(tmp_path: Path) -> None:
    """A record with no digest cannot say the input is unchanged, and says so."""
    tree = tmp_path / "results"
    tree.mkdir()

    first = stamp("run-a", [tree], PARAMETERS, now=NOON)
    second = stamp("run-b", [tree], PARAMETERS, now=NOON)

    assert first.inputs == (InputRef(path=str(tree), sha256=None),)
    report = differences(first, second)
    assert len(report) == 1
    assert "recorded by path alone" in report[0]
    assert str(tree) in report[0]


def test_inputs_are_sorted_so_two_records_compare_directly(tmp_path: Path) -> None:
    """Read order is not part of what a run is."""
    first_file = a_data_file(tmp_path)
    second_file = tmp_path / "app_events.csv"
    second_file.write_text("7\n")

    forwards = stamp("run-a", [first_file, second_file], PARAMETERS, now=NOON)
    backwards = stamp("run-b", [second_file, first_file], PARAMETERS, now=NOON)

    assert forwards.inputs == backwards.inputs
    assert differences(forwards, backwards) == ()


def test_provenance_is_frozen(tmp_path: Path) -> None:
    """The record of what produced a number is not editable afterwards."""
    record = stamp("run-a", [a_data_file(tmp_path)], PARAMETERS, now=NOON)
    assert isinstance(record, Provenance)
    with pytest.raises(FrozenInstanceError):
        record.ref = "run-b"  # type: ignore[misc]
