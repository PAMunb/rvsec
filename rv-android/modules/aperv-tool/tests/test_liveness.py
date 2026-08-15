"""The admissibility rule, and the promotion that must not have changed it.

The last test is the point of the module. ``liveness`` is a promotion of a rule the
campaigns already run, and the only thing that makes the promotion safe is that both
answers agree run by run — so the campaign copy is loaded from disk, read-only, and
its verdicts are compared against the package's over the same records. An import
assertion would prove the file says ``import``; this proves the rule is the same one.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
from fixture_gate import REPO_ROOT

from aperv_tool.analysis import liveness
from aperv_tool.analysis.liveness import (
    SIGNAL_COVERAGE_ALL_ZERO,
    SIGNAL_FATAL_EXCEPTION,
    SIGNAL_TRACE_BELOW_FLOOR,
    RunFacts,
    arm_label,
    classify_last_line,
    floor_for,
    full_budget,
    judge_identities,
    select,
    verdict,
)
from aperv_tool.analysis.run_identity import RunKey

CAMPAIGN_RULE = REPO_ROOT / "experimento-comp162" / "scripts" / "admissibility.py"

# cmp162's roster, as data. The bare `ape` is the collapsed label, not a tool with an
# empty variant.
ARMS = ["ape", "aperv:mop_off_llm_off", "aperv:mop_on_llm_off"]


def facts(
    *,
    apk: str = "com.example_1.apk",
    replica: int = 1,
    timeout_s: int = 300,
    arm: str = "aperv:mop_on_llm_off",
    state: str = "COMPLETED",
    error_message: str | None = "",
    execution_time_s: float = 366.0,
    method_coverage: float | None = 12.5,
    activities_coverage: float | None = 3.0,
    trace_bytes: int | None = 2_318_297,
    fatal_exception: str | None = None,
    last_trace_line: str | None = "## Network stats: elapsed time=300193ms",
) -> RunFacts:
    """A healthy cmp162-shaped run, with the one fact under test overridden.

    The defaults are measured: the median cmp162 run lasts 366 s of a 300 s budget
    (install and teardown are inside the number) and writes a 2.3 MB trace.
    """
    return RunFacts(
        identity=RunKey(apk=apk, repetition=replica, timeout_s=timeout_s, arm=arm),
        task_state=state,
        error_message=error_message,
        execution_time_s=execution_time_s,
        declared_timeout_s=timeout_s,
        method_coverage=method_coverage,
        activities_coverage=activities_coverage,
        trace_bytes=trace_bytes,
        fatal_exception=fatal_exception,
        last_trace_line=last_trace_line,
    )


def test_decisive_corpse_pattern() -> None:
    """The run that made corpse detection a channel is caught, once, with a class.

    Completed at 65 s of an 1800 s budget, an 864-byte trace, zero step lines and
    all coverage at zero, because the explorer died in ``setActivityController``
    with the binder already gone.
    """
    corpse = facts(
        timeout_s=1800,
        execution_time_s=65.0,
        method_coverage=0.0,
        activities_coverage=0.0,
        trace_bytes=864,
        fatal_exception="android.os.DeadObjectException",
        last_trace_line="[APE] *** FATAL *** android.os.DeadObjectException",
    )
    answer = verdict(corpse)

    assert answer.admissible is False
    assert answer.failed_criteria == ("C2", "C5")
    assert set(answer.corpse_signals) == {
        SIGNAL_TRACE_BELOW_FLOOR,
        SIGNAL_COVERAGE_ALL_ZERO,
        SIGNAL_FATAL_EXCEPTION,
    }
    assert answer.is_corpse is True
    assert answer.corpse_class == "crash"

    # The classification is emitted beside the boolean, and reads the last line for
    # what it says rather than assuming the exploration died mid-step.
    assert classify_last_line("## Network stats: elapsed time=300193ms") == "normal_end"
    assert (
        classify_last_line('{"type":"RUN_END","reason":"timeout"}')
        == "cut_during_teardown"
    )
    assert classify_last_line("[APE]      0  BAD_STATE") == "cut_during_teardown"
    assert classify_last_line("[APE] >>>>>>>> SATA end step [80]") == "cut_elsewhere"
    assert classify_last_line(None) == "n/a"
    assert classify_last_line("   ") == "n/a"


def test_full_budget_required() -> None:
    """A run that ended early is an execution failure, not a low outcome."""
    assert full_budget(facts(timeout_s=1800, execution_time_s=65.0)) is False
    assert full_budget(facts(execution_time_s=366.0)) is True

    short = verdict(facts(execution_time_s=61.0))
    assert short.admissible is False
    assert "C2" in short.failed_criteria

    # An unmeasured duration has not been shown to have reached the budget.
    assert full_budget(facts(execution_time_s=None)) is False


def test_teardown_grace_is_the_floor() -> None:
    """C2's floor is the budget minus the grace the tool itself takes."""
    assert liveness.TEARDOWN_GRACE_S == 45
    assert floor_for(300) == 255
    assert floor_for(1800) == 1755

    assert verdict(facts(execution_time_s=255.0)).admissible is True
    assert "C2" in verdict(facts(execution_time_s=254.0)).failed_criteria


def _judged(cells: dict[tuple[str, str, int], list[str]]) -> dict:
    """A verdict mapping written as literals, in the shape ``select`` consumes."""
    return dict(cells)


def test_inadmissible_replica_does_not_drop_the_application() -> None:
    """A transient failure costs its replica, never the application."""
    judged = _judged(
        {
            (apk, arm, replica): (["C2"] if (arm, replica) == (ARMS[1], 2) else [])
            for apk in ["com.example_1.apk"]
            for arm in ARMS
            for replica in (1, 2, 3)
        }
    )
    selection = select(judged, ARMS)

    assert selection["kept"] == ["com.example_1.apk"]
    assert selection["excluded"] == {}
    assert selection["good_reps"][("com.example_1.apk", ARMS[1])] == [1, 3]
    assert selection["dropped_reps"][("com.example_1.apk", ARMS[1])] == [(2, ["C2"])]


def test_arm_with_no_admissible_replica_drops_the_application_whole() -> None:
    """The pair breaks, so the application leaves — not the arm.

    Keeping the surviving arms would unbalance the pair exactly where the data is
    worst, and the bias would enter in the direction of whichever arms survived.
    """
    # The first application's third arm is dead in all three replicas. The second
    # keeps one admissible replica there and survives with a partial cell.
    judged: dict[tuple[str, str, int], list[str]] = {}
    for arm in ARMS:
        for replica in (1, 2, 3):
            dead = arm == ARMS[2]
            judged[("com.ds.avare_404.apk", arm, replica)] = (
                ["C1", "C2", "C5"] if dead else []
            )
            judged[("com.example_1.apk", arm, replica)] = (
                ["C1"] if dead and replica != 1 else []
            )
    selection = select(judged, ARMS)

    assert selection["kept"] == ["com.example_1.apk"]
    assert list(selection["excluded"]) == ["com.ds.avare_404.apk"]
    assert list(selection["excluded"]["com.ds.avare_404.apk"]) == [ARMS[2]]

    # The application left whole: none of its surviving arms is carried forward.
    assert not [
        cell for cell in selection["good_reps"] if cell[0] == "com.ds.avare_404.apk"
    ]


def test_partial_cells_reported() -> None:
    """A cell left with fewer replicas is reported, never absorbed."""
    judged = _judged(
        {
            (apk, arm, replica): (["C5"] if (arm, replica) == (ARMS[0], 3) else [])
            for apk in ["com.example_1.apk"]
            for arm in ARMS
            for replica in (1, 2, 3)
        }
    )
    selection = select(judged, ARMS)

    assert selection["max_reps"] == 3
    assert selection["partial_cells"] == {("com.example_1.apk", ARMS[0]): 2}


def test_arm_label_collapses_ape_default() -> None:
    """``ape:default`` matches nothing, and every application would drop out.

    The builtin writes ``variant='default'`` into its ``tool_config`` while the
    consolidator collapses it to a bare ``ape``. Without the same collapse here the
    labels stop matching the ``tool`` column, every ``ape`` cell looks empty, and the
    exclusion rule drops every application for an arm with no execution.
    """
    assert arm_label("ape", "default") == "ape"
    assert arm_label("ape", None) == "ape"
    assert arm_label("aperv", "mop_on_llm_off") == "aperv:mop_on_llm_off"

    uncollapsed = {
        ("com.example_1.apk", "ape:default" if arm == "ape" else arm, replica): []
        for arm in ARMS
        for replica in (1, 2, 3)
    }
    selection = select(uncollapsed, ARMS)
    assert selection["kept"] == []
    assert selection["excluded"]["com.example_1.apk"]["ape"] == ["no execution"]


def _task(
    apk: str,
    tool: str,
    variant: str | None,
    replica: int,
    *,
    state: str = "COMPLETED",
    error_message: str = "",
    execution_time_seconds: float | None = 366.0,
    coverage: dict | None = None,
) -> dict:
    """One rv-platform task record, in the shape ``tasks.json`` writes it."""
    return {
        "config": {
            "apk_name": apk,
            "repetition": replica,
            "tool_config": {"name": tool, "variant": variant},
        },
        "result": {
            "state": state,
            "error_message": error_message,
            "execution_time_seconds": execution_time_seconds,
            "coverage_metrics": (
                coverage
                if coverage is not None
                else {"method_coverage": 12.5, "activities_coverage": 3.0}
            ),
        },
    }


def test_promoted_rule_matches_the_campaign_copy(tmp_path: Path) -> None:
    """The package and the campaign judge the same records identically.

    The campaign file is loaded from its own path and read only. It is the rule the
    two campaigns already ran; if the promotion changed any verdict, the promotion
    is a different rule wearing the same name.
    """
    if not CAMPAIGN_RULE.exists():
        pytest.skip(f"campaign rule not present: {CAMPAIGN_RULE}")

    records = [
        # Healthy runs of all three arms, the ape one carrying `variant='default'`.
        _task("com.example_1.apk", "ape", "default", 1),
        _task("com.example_1.apk", "aperv", "mop_off_llm_off", 1),
        _task("com.example_1.apk", "aperv", "mop_on_llm_off", 1),
        # A resume: the ERROR record stays in the file beside the COMPLETED one.
        _task(
            "com.example_2.apk",
            "aperv",
            "mop_on_llm_off",
            1,
            state="ERROR",
            error_message="device offline",
            execution_time_seconds=12.0,
            coverage={},
        ),
        _task("com.example_2.apk", "aperv", "mop_on_llm_off", 1),
        # Short of the budget, zero coverage, no coverage block at all, and an
        # unrecoverable failure.
        _task("com.example_2.apk", "ape", "default", 1, execution_time_seconds=61.0),
        _task(
            "com.example_2.apk",
            "aperv",
            "mop_off_llm_off",
            1,
            coverage={"method_coverage": 0, "activities_coverage": 0},
        ),
        _task("com.example_3.apk", "ape", "default", 2, coverage={}),
        _task(
            "com.example_3.apk",
            "aperv",
            "mop_on_llm_off",
            3,
            state="ERROR",
            error_message="emulator died",
            execution_time_seconds=None,
            coverage={},
        ),
    ]
    tasks_json = tmp_path / "tasks.json"
    tasks_json.write_text(json.dumps({"tasks": records}))

    spec = importlib.util.spec_from_file_location("campaign_rule", CAMPAIGN_RULE)
    campaign = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(campaign)

    glob_pattern = str(tmp_path / "tasks.json")
    assert campaign.TEARDOWN_GRACE_S == liveness.TEARDOWN_GRACE_S
    assert campaign.judge_identities(glob_pattern, 300) == judge_identities(
        glob_pattern, 300
    )

    # And the exclusion rule agrees on what the verdicts mean.
    ours = judge_identities(glob_pattern, 300)
    assert (
        campaign.select(campaign.judge_identities(glob_pattern, 300), ARMS)["kept"]
        == select(ours, ARMS)["kept"]
    )
