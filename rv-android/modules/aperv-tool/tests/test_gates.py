"""The five gates: the anchored pattern, the per-arm evidence form, and delegation.

Two of these tests are structural rather than behavioural. ``test_anchored_mop_pattern``
carries the unanchored form beside the anchored one, because the defect it encodes —
``activity_has_mop=1`` counted as a violation — is invisible unless the line that
caused it is in the test. ``test_gates_delegate_to_liveness`` reads this module's own
source: an excluded run must be excluded once, and nothing but a source check stops a
later author from adding a second, slightly different corpse predicate here.

The MOP-group tests build their version-2 rows directly from the reader's
dataclasses and hand them to the counter through a stub reader, so the counter's
member list is tested apart from the reader's parsing of the group-isolation jar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterator, Optional

import pandas as pd
import pytest

from aperv_tool.analysis import gates
from aperv_tool.analysis.coverage_dump import DumpStatus, RunCoverage, StateCoverage
from aperv_tool.analysis.gates import (
    _EVIDENCE_COLUMNS,
    FORM_MOP_GROUP,
    GATE_ARM_ATTRIBUTION,
    GATE_CLEAN_CONTROL,
    GATE_CORPSE_DETECTION,
    GATE_CORRECT_BINARY,
    GATE_TASK_INTEGRITY,
    ArmManifest,
    ArmSpec,
    clean_control_signal,
    count_forbidden_signal,
    count_mop_group_signal,
    run_all,
)
from aperv_tool.analysis.runspec import ManifestArm
from aperv_tool.analysis.trace_ndjson import (
    NavTie,
    Ownership,
    RunStart,
    StepOutcome,
    StepRow,
)

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
    for token in (
        "COMPLETED",
        "TOOL_TEARDOWN_GRACE_S",
        "floor_for",
        "TRACE_FLOOR_BYTES =",
    ):
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


# ---------------------------------------------------------------------------
# The MOP-group form of gate 1, over NDJSON traces.
# ---------------------------------------------------------------------------

STATIC_ACTIVITY = "com.example.FormActivity"
SATA_ACTION = "g0a0[]@MODEL_CLICKclass=android.widget.Button;"


@dataclass
class StubReader:
    """The three things ``count_mop_group_signal`` reads off a ``TraceReader``."""

    rows: list[StepRow]
    run_start: Optional[RunStart]
    run_end: Optional[dict[str, Any]] = None
    mop_data: Optional[dict[str, Any]] = field(
        default_factory=lambda: {"activities": 4, "wtgEdges": 12}
    )

    def __iter__(self) -> Iterator[StepRow]:
        return iter(self.rows)


def clean_step(number: int, source: str = "sata", **overrides: Any) -> StepRow:
    """A step of an ``aperv:as`` run: STATIC boosts, no MOP member at all."""
    fields: dict[str, Any] = {
        "step": number,
        "t_rel_ms": number * 1_000,
        "t_epoch_ms": None,
        "activity": STATIC_ACTIVITY,
        "activity_has_mop": None,
        "state_key": f"{STATIC_ACTIVITY}@1@Naming[0]@[W=3]",
        "action": SATA_ACTION,
        "decision_source": source,
        "pick_channel": "roulette",
        "priority": 40,
        "coverage": 120,
        "nav_frontier": 200,
        "form": 80,
        "owner": Ownership(intended=source, u_llm=0.42),
        "scorer_cf": {"cov": True, "navf": False, "form": True},
        "nav": NavTie(point="X3", component="ape", alternative=False, drew=True),
        "outcome": StepOutcome(
            target_state=f"{STATIC_ACTIVITY}@1@Naming[0]@[W=3]",
            target_activity=STATIC_ACTIVITY,
            target_activity_has_mop=None,
        ),
    }
    fields.update(overrides)
    return StepRow(**fields)


def coverage(*mop_reach: Optional[int]) -> RunCoverage:
    """A complete dump with one ``UICOV`` state per given ``mopReach``."""
    return RunCoverage(
        trace_path=Path("run.trace"),
        apk="app.apk",
        repetition=1,
        timeout_seconds=300,
        arm="aperv:as",
        status=DumpStatus.COMPLETE,
        states=tuple(
            StateCoverage(
                state_key=f"S{index}", discovered=4, interacted=2, mop_reach=reach
            )
            for index, reach in enumerate(mop_reach)
        ),
    )


def static_control(rows: list[StepRow], **run_end_counters: int) -> StubReader:
    """An ``aperv:as`` trace (``v == 2``) with the given steps and counters."""
    counters = {"coinMop": 0, "launches": 0, "stampHits": 0, "retired": 0}
    counters.update(run_end_counters)
    return StubReader(
        rows=rows,
        run_start=RunStart(v=2, preset="as", variant="as"),
        run_end={"reason": "budget", "counters": counters},
    )


def group_manifest() -> ArmManifest:
    """A group-isolation roster: ``as`` is a control, ``as_mop`` is not."""
    features = ("ADDONS", "MOP", "STATIC")
    return ArmManifest(
        arms={
            "aperv:as": ArmSpec(
                tool="aperv",
                variant="as",
                declaration=ManifestArm(
                    arm="aperv:as",
                    digest=None,
                    preset="as",
                    features=None,
                    params={},
                    variant="as",
                ),
                control=True,
            ),
            "aperv:as_mop": ArmSpec(
                tool="aperv",
                variant="as_mop",
                declaration=ManifestArm(
                    arm="aperv:as_mop",
                    digest=None,
                    preset="as_mop",
                    features=features,
                    params={"ape.mopCoinPercentage": 1.0},
                    variant="as_mop",
                ),
            ),
        }
    )


def test_static_control_with_the_artifact_loaded_is_clean() -> None:
    """``MOP_DATA``, ``ACT`` without ``mop`` and STATIC boosts are not MOP signals."""
    reader = static_control([clean_step(1), clean_step(2, source="llm"), clean_step(3)])
    assert reader.mop_data is not None

    count = count_mop_group_signal(reader, coverage(None, None))
    assert count == 0

    report = run_all(
        pd.DataFrame(
            [
                row(
                    "aperv:as",
                    forbidden_signal_count=count,
                    forbidden_signal_form=FORM_MOP_GROUP,
                )
            ]
        ),
        group_manifest(),
    )
    result = report.results[(GATE_CLEAN_CONTROL, "aperv:as")]
    assert result.status == "pass"
    assert result.evidence_form == FORM_MOP_GROUP


def test_mop_members_in_a_control_are_counted() -> None:
    """A MOP owner, a MOP distance and a ``mopReach`` line are three signals."""
    reader = static_control(
        [
            clean_step(1),
            clean_step(2, source="mop"),
            clean_step(3, mop_distance=2),
            clean_step(4),
        ]
    )
    count = count_mop_group_signal(reader, coverage(None, 3))
    assert count == 3

    report = run_all(
        pd.DataFrame(
            [
                row(
                    "aperv:as",
                    forbidden_signal_count=count,
                    forbidden_signal_form=FORM_MOP_GROUP,
                )
            ]
        ),
        group_manifest(),
    )
    result = report.results[(GATE_CLEAN_CONTROL, "aperv:as")]
    assert result.status == "fail"
    assert "com.example_1.apk__1__300__aperv:as" in result.detail
    assert result.evidence_form == FORM_MOP_GROUP


@pytest.mark.parametrize(
    "member",
    [
        {"mop": 500},
        {"mop_frontier": 200},
        {"wtg": 200},
        {"menu": 50},
        {"mop_distance": 0},
        {"mop_stamp": "cache"},
        {"mop_handler": "com.example.MainActivity$1"},
        {"retired_targets": (7,)},
        {"mop_exposure": (0, 5)},
        {"owner": Ownership(intended="sata", u_llm=0.4, u_mop=0.9)},
        {"scorer_cf": {"cov": True, "mopf": False}},
        {"nav": NavTie(point="X3", component="mop", alternative=True, drew=False)},
        {"pick_channel": "mop_coin"},
        {"pick_channel": "launcher"},
        {"decision_source": "launcher"},
        {"owner": Ownership(intended="mop", fallback="no_match")},
        {"owner": Ownership(intended="launcher", fallback="ineligible")},
    ],
    ids=lambda member: "-".join(f"{key}={value}" for key, value in member.items()),
)
def test_each_step_member_counts(member: dict[str, Any]) -> None:
    """Every step-row member of the list is a signal on its own."""
    reader = static_control([clean_step(1, **member)])
    assert count_mop_group_signal(reader) == 1


def test_a_row_counts_once_whatever_it_carries() -> None:
    """Several members on one step are one signal, not several."""
    loaded = clean_step(
        1,
        source="mop",
        mop=500,
        mop_distance=1,
        mop_stamp="cache",
        pick_channel="mop_coin",
        activity_has_mop=True,
    )
    assert count_mop_group_signal(static_control([loaded])) == 1


def test_act_mop_fact_and_mop_counter_count_on_v2() -> None:
    """``ACT.mop:0`` on two steps and ``coinMop:1`` are three signals."""
    rows = [
        clean_step(1, activity_has_mop=False),
        clean_step(
            2,
            activity_has_mop=False,
            outcome=StepOutcome(
                target_activity=STATIC_ACTIVITY, target_activity_has_mop=False
            ),
        ),
    ]
    assert count_mop_group_signal(static_control(rows, coinMop=1)) == 3

    # The outcome side alone is enough for a row.
    target_only = clean_step(
        3,
        outcome=StepOutcome(
            target_activity=STATIC_ACTIVITY, target_activity_has_mop=False
        ),
    )
    assert count_mop_group_signal(static_control([target_only])) == 1

    # Each counter is a signal, and a RUN_END counts once however many it holds.
    for counter in ("coinMop", "launches", "stampHits", "retired"):
        assert count_mop_group_signal(static_control([], **{counter: 4})) == 1
    assert count_mop_group_signal(static_control([], launches=2, retired=3)) == 1

    # nullRelaunches is written in every cell and is not on the clean-control list.
    assert count_mop_group_signal(static_control([], nullRelaunches=3)) == 0


def test_v1_act_fact_and_run_end_counters_are_not_a_signal() -> None:
    """The v1 jar writes ``ACT.mop`` everywhere and stamps in a clean control."""
    rows = [
        replace(
            clean_step(number),
            owner=None,
            scorer_cf=None,
            nav=None,
            nav_frontier=0,
            activity_has_mop=True,
            outcome=StepOutcome(
                target_activity=STATIC_ACTIVITY, target_activity_has_mop=True
            ),
        )
        for number in (1, 2, 3)
    ]
    reader = StubReader(
        rows=rows,
        run_start=RunStart(v=1, preset="mop"),
        run_end={"counters": {"stampHits": 5, "retired": 2}},
    )
    assert count_mop_group_signal(reader) == 0

    # The step-row members that version carries still count on it.
    reader.rows.append(replace(rows[0], step=4, mop=500))
    assert count_mop_group_signal(reader) == 1


def v1_control_step(number: int, **overrides: Any) -> StepRow:
    """A step of a cmp162 ``mop_off_llm_off`` run: the zero-weight MOP pass ran."""
    fields: dict[str, Any] = {
        "step": number,
        "t_rel_ms": number * 1_000,
        "t_epoch_ms": None,
        "activity": STATIC_ACTIVITY,
        "activity_has_mop": True,
        "state_key": f"{STATIC_ACTIVITY}@1@Naming[0]@[W=3]",
        "action": SATA_ACTION,
        "decision_source": "Coverage",
        "pick_channel": "roulette_early",
        "priority": 152,
        "coverage": 100,
        "mop_exposure": (0, 5),
        "outcome": StepOutcome(
            target_activity=STATIC_ACTIVITY, target_activity_has_mop=True
        ),
    }
    fields.update(overrides)
    return StepRow(**fields)


def test_v1_control_counts_only_fired_mop_boosts() -> None:
    """By-products of the zero-weight MOP pass are not a v1 signal; a boost is."""
    rows = [v1_control_step(number) for number in range(1, 74)]
    rows[10] = v1_control_step(11, wtg=200)
    reader = StubReader(
        rows=rows,
        run_start=RunStart(v=1, preset="mop"),
        run_end={"counters": {"stampHits": 5, "retired": 2, "coinMop": 1}},
    )
    dump = coverage(1, 0, 3, 1, 0, 2, 1)

    assert count_mop_group_signal(reader, dump) == 0

    reader.rows[20] = v1_control_step(21, mop=500)
    assert count_mop_group_signal(reader, dump) == 1

    reader.rows[30] = v1_control_step(31, mop=500, mop_frontier=200)
    assert count_mop_group_signal(reader, dump) == 2


@pytest.mark.parametrize(
    "header", [None, RunStart(preset="mop")], ids=["no-header", "no-version"]
)
def test_unknown_version_reads_as_legacy(header: Optional[RunStart]) -> None:
    """A trace that does not say its version gets the narrower, v1 reading."""
    rows = [v1_control_step(1, activity_has_mop=False), v1_control_step(2)]
    reader = StubReader(
        rows=rows, run_start=header, run_end={"counters": {"coinMop": 1}}
    )
    assert count_mop_group_signal(reader, coverage(1)) == 0

    reader.rows.append(v1_control_step(3, mop_frontier=200))
    assert count_mop_group_signal(reader, coverage(1)) == 1


def _write(path: Path, *lines: str) -> Path:
    path.write_text("\n".join(lines) + "\n")
    return path


def test_legacy_pattern_is_blind_on_ndjson_and_the_gate_does_not_use_it(
    tmp_path: Path,
) -> None:
    """``"mop":500`` is not ``mop=``; the NDJSON trace is counted by its own form."""
    step_line = (
        '{"s":1,"t":10,"act":0,"st":0,'
        '"dec":{"a":"g0a0[]@MODEL_CLICK","src":"sata","ch":"roulette","mop":500}}'
    )
    trace = _write(
        tmp_path / "app.apk__1__300__aperv:mop_off_llm_off.trace",
        "[APE] *** INFO *** banner before the header",
        '{"type":"RUN_START","v":1,"preset":"mop"}',
        '{"type":"ACT","id":0,"name":"com.example.Main","mop":1}',
        '{"type":"STATE","id":0,"key":"com.example.Main@1@Naming[0]@[W=3]","act":0}',
        step_line,
    )

    assert count_forbidden_signal(trace.read_text().splitlines()) == 0

    signal = clean_control_signal(trace)
    assert signal.form == FORM_MOP_GROUP
    assert signal.count == 1

    legacy = _write(
        tmp_path / "app.apk__1__300__aperv:legacy.trace",
        "[APE-STEP] step=1 activity_has_mop=1 mop=0",
        "[APE-STEP] step=2 activity_has_mop=1 mop=500",
    )
    legacy_signal = clean_control_signal(legacy)
    assert legacy_signal.count == 2
    assert legacy_signal.form.startswith("anchored field pattern")


def test_variant_is_gate_3_evidence_on_the_new_jar() -> None:
    """An ``as_mop`` run passes on its variant and fails on another cell's."""
    header = RunStart(
        v=2,
        preset="as_mop",
        variant="as_mop",
        features=("ADDONS", "MOP", "STATIC"),
        params={"ape.mopCoinPercentage": 1.0},
    )
    passing = run_all(
        pd.DataFrame([row("aperv:as_mop", run_start=header)]), group_manifest()
    )
    result = passing.results[(GATE_ARM_ATTRIBUTION, "aperv:as_mop")]
    assert result.status == "pass"
    assert "variant" in result.evidence_form.split(", ")

    mislabelled = run_all(
        pd.DataFrame([row("aperv:as_mop", run_start=replace(header, variant="as"))]),
        group_manifest(),
    )
    assert mislabelled.status(GATE_ARM_ATTRIBUTION, "aperv:as_mop") == "fail"
