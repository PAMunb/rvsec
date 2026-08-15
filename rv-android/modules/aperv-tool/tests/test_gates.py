"""The five gates: the anchored pattern, the per-arm evidence form, and delegation.

Two of these tests are structural rather than behavioural. ``test_anchored_mop_pattern``
carries the unanchored form beside the anchored one, because the defect it encodes —
``activity_has_mop=1`` counted as a violation — is invisible unless the line that
caused it is in the test. ``test_gates_delegate_to_liveness`` reads this module's own
source: an excluded run must be excluded once, and nothing but a source check stops a
later author from adding a second, slightly different corpse predicate here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from aperv_tool.analysis import gates
from aperv_tool.analysis.gates import (
    _EVIDENCE_COLUMNS,
    GATE_ARM_ATTRIBUTION,
    GATE_CLEAN_CONTROL,
    GATE_CORPSE_DETECTION,
    GATE_CORRECT_BINARY,
    GATE_TASK_INTEGRITY,
    ArmManifest,
    ArmSpec,
    count_forbidden_signal,
    run_all,
)
from aperv_tool.analysis.runspec import ManifestArm

DECLARED_DIGEST = "0f1e2d3c4b5a69788796a5b4c3d2e1f00f1e2d3c"


def declaration(arm: str, *, digest: str | None = DECLARED_DIGEST) -> ManifestArm:
    """What a campaign declares for one arm, as data (INV-APV-59)."""
    return ManifestArm(arm=arm, digest=digest, preset=None, features=None, params={})


def manifest() -> ArmManifest:
    """cmp162's roster plus a droidbot arm, with the control arm declared."""
    return ArmManifest(
        arms={
            "ape": ArmSpec(
                tool="ape", variant="", declaration=declaration("ape"), control=True
            ),
            "aperv:mop_off_llm_off": ArmSpec(
                tool="aperv",
                variant="mop_off_llm_off",
                declaration=declaration("aperv:mop_off_llm_off"),
                control=True,
            ),
            "aperv:mop_on_llm_off": ArmSpec(
                tool="aperv",
                variant="mop_on_llm_off",
                declaration=declaration("aperv:mop_on_llm_off"),
            ),
            "droidbot:bfs_greedy": ArmSpec(
                tool="droidbot",
                variant="bfs_greedy",
                declaration=declaration("droidbot:bfs_greedy", digest=None),
                policy="bfs_greedy",
            ),
        }
    )


def row(arm: str, **overrides) -> dict:
    """A healthy cmp162-shaped identity, with the facts under test overridden."""
    record = {
        "apk": "com.example_1.apk",
        "rep": 1,
        "timeout_s": 300,
        "arm": arm,
        "state": "COMPLETED",
        "error_message": "",
        "execution_time_s": 366.0,
        "method_coverage": 12.5,
        "activities_coverage": 3.0,
        "trace_bytes": 2_318_297,
        "fatal_exception": None,
        "last_trace_line": "## Network stats: elapsed time=300193ms",
    }
    record.update(overrides)
    return record


def test_anchored_mop_pattern() -> None:
    """``activity_has_mop=1`` is not a violation; the unanchored form said it was."""
    contaminated_looking = "step=7 activity_has_mop=1 dec=EARLY_STAGE"
    assert count_forbidden_signal([contaminated_looking]) == 0
    assert len(re.compile(r"mop=").findall(contaminated_looking)) == 1

    assert count_forbidden_signal(["boost mop=on", "mop=off"]) == 2

    report = run_all(
        pd.DataFrame(
            [
                row("aperv:mop_off_llm_off", forbidden_signal_count=0),
                row(
                    "aperv:mop_off_llm_off",
                    rep=2,
                    forbidden_signal_count=count_forbidden_signal(
                        [contaminated_looking]
                    ),
                ),
                # The treated arm is in the frame and fires the signal by design.
                row("aperv:mop_on_llm_off", forbidden_signal_count=17),
            ]
        ),
        manifest(),
    )
    assert report.status(GATE_CLEAN_CONTROL, "aperv:mop_off_llm_off") == "pass"

    # And a real signal fails the control arm, naming the run.
    contaminated = run_all(
        pd.DataFrame([row("aperv:mop_off_llm_off", forbidden_signal_count=3)]),
        manifest(),
    )
    result = contaminated.results[(GATE_CLEAN_CONTROL, "aperv:mop_off_llm_off")]
    assert result.status == "fail"
    assert "com.example_1.apk__1__300__aperv:mop_off_llm_off" in result.detail

    # Gate 1 makes no claim about an arm that is not a control.
    assert report.status(GATE_CLEAN_CONTROL, "aperv:mop_on_llm_off") is None


def test_ape_negative_evidence() -> None:
    """Zero NDJSON lines proves the upstream jar ran; the digest stays ``not-run``."""
    report = run_all(
        pd.DataFrame([row("ape", forbidden_signal_count=0, ndjson_line_count=0)]),
        manifest(),
    )

    attribution = report.results[(GATE_ARM_ATTRIBUTION, "ape")]
    assert attribution.status == "pass"
    assert attribution.evidence_form == "negative: 0 NDJSON lines"

    binary = report.results[(GATE_CORRECT_BINARY, "ape")]
    assert binary.status == "not-run"
    assert "no digest emitted, no sidecar" in binary.detail


def test_ape_one_ndjson_line_fails() -> None:
    """One ``{``-leading record in an ape-labelled trace fails, naming the line."""
    report = run_all(
        pd.DataFrame(
            [
                row(
                    "ape",
                    forbidden_signal_count=0,
                    ndjson_line_count=1,
                    first_ndjson_line_no=42,
                )
            ]
        ),
        manifest(),
    )
    result = report.results[(GATE_ARM_ATTRIBUTION, "ape")]
    assert result.status == "fail"
    assert "line 42" in result.detail


def test_droidbot_policy_line() -> None:
    """The announced policy is the evidence; the filename's label is the claim."""
    announced = "start sending events, policy is bfs_greedy"
    passing = run_all(
        pd.DataFrame([row("droidbot:bfs_greedy", policy_line=announced)]), manifest()
    )
    result = passing.results[(GATE_ARM_ATTRIBUTION, "droidbot:bfs_greedy")]
    assert result.status == "pass"
    assert result.evidence_form.startswith("start sending events, policy is")

    mismatched = run_all(
        pd.DataFrame(
            [
                row(
                    "droidbot:bfs_greedy",
                    policy_line="start sending events, policy is dfs_naive",
                )
            ]
        ),
        manifest(),
    )
    assert mismatched.status(GATE_ARM_ATTRIBUTION, "droidbot:bfs_greedy") == "fail"

    silent = run_all(pd.DataFrame([row("droidbot:bfs_greedy")]), manifest())
    assert silent.status(GATE_ARM_ATTRIBUTION, "droidbot:bfs_greedy") == "not-run"


def test_not_run_never_pass() -> None:
    """With no evidence at all, no evidence-bearing gate passes (INV-CAN-06)."""
    frame = pd.DataFrame([row(arm) for arm in manifest().arms])
    assert not [column for column in _EVIDENCE_COLUMNS if column in frame.columns]

    report = run_all(frame, manifest())
    for arm in manifest().arms:
        assert report.status(GATE_CORRECT_BINARY, arm) == "not-run"
        assert report.status(GATE_ARM_ATTRIBUTION, arm) == "not-run"
    for arm in manifest().control_arms:
        assert report.status(GATE_CLEAN_CONTROL, arm) == "not-run"

    # The gates that read only the task record still answer: the runs are healthy.
    for arm in manifest().arms:
        assert report.status(GATE_TASK_INTEGRITY, arm) == "pass"
        assert report.status(GATE_CORPSE_DETECTION, arm) == "pass"

    # An arm passes only when every one of its runs was evidenced.
    partial = run_all(
        pd.DataFrame(
            [
                row("ape", ndjson_line_count=0),
                row("ape", rep=2),
            ]
        ),
        manifest(),
    )
    assert partial.status(GATE_ARM_ATTRIBUTION, "ape") == "not-run"


def test_gates_delegate_to_liveness() -> None:
    """No predicate of its own over trace size, coverage or a fatal exception."""
    source = Path(gates.__file__).read_text()

    assert "from aperv_tool.analysis import liveness" in source
    assert "liveness.verdict(" in source

    owned_by_liveness = (
        "trace_bytes",
        "method_coverage",
        "activities_coverage",
        "fatal_exception",
        "execution_time_s",
    )
    comparison = re.compile(
        r"\b(" + "|".join(owned_by_liveness) + r")\s*(?:[<>]|==|!=)"
    )
    assert comparison.search(source) is None

    # Nor a second copy of the completion criterion or the budget floor.
    for token in ("COMPLETED", "TEARDOWN_GRACE_S", "floor_for", "TRACE_FLOOR_BYTES ="):
        assert token not in source


def test_full_budget_required() -> None:
    """Gate 4 fails on a run that ended before its budget did."""
    report = run_all(
        pd.DataFrame(
            [
                row("aperv:mop_on_llm_off"),
                row("aperv:mop_on_llm_off", rep=2, execution_time_s=61.0),
            ]
        ),
        manifest(),
    )
    result = report.results[(GATE_TASK_INTEGRITY, "aperv:mop_on_llm_off")]
    assert result.status == "fail"
    assert "short of the declared budget" in result.detail
    assert "com.example_1.apk__2__300__aperv:mop_on_llm_off" in result.detail


def test_decisive_corpse() -> None:
    """The corpse fails gate 4 on duration and gate 5 as a crash, once."""
    corpse = row(
        "aperv:mop_on_llm_off",
        timeout_s=1800,
        execution_time_s=65.0,
        method_coverage=0.0,
        activities_coverage=0.0,
        trace_bytes=864,
        fatal_exception="android.os.DeadObjectException",
        last_trace_line="[APE] *** FATAL *** android.os.DeadObjectException",
    )
    report = run_all(pd.DataFrame([corpse]), manifest())

    assert report.status(GATE_TASK_INTEGRITY, "aperv:mop_on_llm_off") == "fail"
    assert (
        "short of the declared budget"
        in report.results[(GATE_TASK_INTEGRITY, "aperv:mop_on_llm_off")].detail
    )

    detection = report.results[(GATE_CORPSE_DETECTION, "aperv:mop_on_llm_off")]
    assert detection.status == "fail"
    assert "[crash]" in detection.detail

    # Excluded once, by liveness, and reported with its reason.
    assert len(report.verdicts) == 1
    (admissibility,) = report.verdicts.values()
    assert admissibility.admissible is False
    assert admissibility.is_corpse is True
    assert report.corpse_census == {"crash": 1}
