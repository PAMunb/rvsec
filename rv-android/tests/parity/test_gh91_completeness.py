"""The gh91 campaign must not mistake a killed WTG for a finished analysis.

`RvsecAnalysisClient` writes the report once at `:169-170`, before `WTGBuilder.build()` at
`:189`, and `JsonReportWriter.java:111` appends `"complete": true` at the end of every
successful write. A run killed inside the WTG builder therefore leaves on disk a JSON that
parses, ends in the sentinel, and holds `"transitions": []`.

While the campaign passed `skipWtg=true` this could not happen: the client returned right
after the pre-WTG write (`:180-184`), so nothing ran after the sentinel that a kill could land
in. Dropping `skipWtg` — which is the whole point of this round — is exactly what creates the
gap, and the consequence is not cosmetic: an APK judged finished is never promoted to round 2,
so the escalation ladder silently refuses to climb for the very APKs it exists for. Nine of
the thirty timed out in Phase 7.

These tests reproduce that file on disk and pin the two halves of the fix: the predicate says
"not finished", and the round scheduler acts on it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import gh91_campaign as campaign  # noqa: E402
import gh91_sa_rerun as drv  # noqa: E402

APK = "de.markusfisch.android.binaryeye_174.apk"


def _write_run(out_dir: Path, *, transitions: list, timed_out: bool,
               sentinel: bool = True) -> None:
    """Put one APK's artefacts on disk exactly as a round leaves them.

    The JSON is written by hand rather than through the writer because what is under test is
    how the campaign *reads* the two files, and the shape that matters — sentinel last, empty
    transitions — is the one the Java writer is separately pinned to emit.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    body = {"package": "de.markusfisch.android.binaryeye", "transitions": transitions}
    text = json.dumps(body)[:-1] + (',"complete":true}' if sentinel else "}")
    (out_dir / f"{APK}.json").write_text(text, encoding="utf-8")

    progress = out_dir / "_progress"
    progress.mkdir(exist_ok=True)
    (progress / f"{APK}.json").write_text(json.dumps({
        "apk": APK,
        "sa_status": "complete",
        "returncode": -1 if timed_out else 0,
        "seconds": 3600.0 if timed_out else 812.3,
        "timed_out": timed_out,
    }), encoding="utf-8")


def _job(out_dir: Path) -> drv.Job:
    return drv.Job(
        apk=APK,
        code_package="de.markusfisch.android.binaryeye",
        manifest_package="de.markusfisch.android.binaryeye",
        jvm_memory="32g",
        timeout=3600,
        apk_path=Path("/nonexistent") / APK,
        out_dir=out_dir,
    )


def test_killed_wtg_carries_the_sentinel(tmp_path: Path) -> None:
    """The premise: the file a WTG timeout leaves behind is sentinel-carrying and empty.

    If this ever stops holding, the rest of these tests are guarding nothing.
    """
    _write_run(tmp_path, transitions=[], timed_out=True)
    assert campaign.has_sentinel(tmp_path / f"{APK}.json") is True


def test_killed_wtg_is_not_complete(tmp_path: Path) -> None:
    _write_run(tmp_path, transitions=[], timed_out=True)
    assert campaign.is_complete(tmp_path, APK) is False


def test_killed_wtg_is_promoted_to_the_next_round(tmp_path: Path) -> None:
    """The consequence that matters: the ladder climbs.

    After round 1 the APK has `rounds_done == 1`, so `pending_for_round` admits it into
    round 2 only if it is judged unfinished. Judged by the sentinel alone it would be
    dropped here, and 120 g / 7200 s would never be tried.
    """
    _write_run(tmp_path, transitions=[], timed_out=True)
    jobs = [_job(tmp_path)]
    state = {APK: {"rounds_done": 1, "verdict": campaign.CLASS_TRANSIENT}}
    home = {APK: 1}

    assert campaign.pending_for_round(jobs, state, 2, home) == jobs
    assert campaign.retryable(jobs, state) == jobs


def test_finished_run_with_an_empty_graph_is_complete(tmp_path: Path) -> None:
    """An empty WTG that nobody killed is a fact about the app, not a failure.

    `eu.faircode.email_2322` is the corpus's example: it ran to the end and produced no
    transitions. Retrying it would spend the largest budget reproducing the same emptiness,
    so the predicate must accept it — which is why the discriminator is the timeout flag and
    not the transition count.
    """
    _write_run(tmp_path, transitions=[], timed_out=False)
    assert campaign.is_complete(tmp_path, APK) is True
    assert campaign.pending_for_round([_job(tmp_path)], {}, 1, {APK: 1}) == []


def test_finished_run_with_a_graph_is_complete(tmp_path: Path) -> None:
    _write_run(tmp_path, transitions=[{"event": "click"}], timed_out=False)
    assert campaign.is_complete(tmp_path, APK) is True


def test_truncated_json_is_not_complete(tmp_path: Path) -> None:
    """The sentinel keeps its original job: a file cut mid-write is still rejected."""
    _write_run(tmp_path, transitions=[{"event": "click"}], timed_out=False, sentinel=False)
    assert campaign.is_complete(tmp_path, APK) is False


def test_json_without_its_outcome_record_is_not_complete(tmp_path: Path) -> None:
    """A JSON this campaign did not write cannot be confirmed, so it is re-run.

    The alternative — trusting the sentinel when the record is missing — reopens the exact
    hole these tests close, for a file whose origin is unknown.
    """
    _write_run(tmp_path, transitions=[{"event": "click"}], timed_out=False)
    (tmp_path / "_progress" / f"{APK}.json").unlink()
    assert campaign.is_complete(tmp_path, APK) is False


@pytest.mark.parametrize("timed_out,expected", [(True, False), (False, True)])
def test_completeness_turns_on_the_timeout_flag_alone(tmp_path: Path, timed_out: bool,
                                                      expected: bool) -> None:
    """Same bytes in the JSON, opposite verdicts — the flag is doing the work."""
    _write_run(tmp_path, transitions=[], timed_out=timed_out)
    assert campaign.is_complete(tmp_path, APK) is expected
