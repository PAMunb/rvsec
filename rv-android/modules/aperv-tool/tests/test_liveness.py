"""The admissibility rule, and the promotion that must not have changed it.

The last test is the point of the module. ``liveness`` is a promotion of a rule the
campaigns already run, and the only thing that makes the promotion safe is that both
answers agree run by run — so the campaign copy is loaded from disk, read-only, and
its verdicts are compared against the package's over the same records. An import
assertion would prove the file says ``import``; this proves the rule is the same one.
"""

from __future__ import annotations

import glob
import importlib.util
import json
from pathlib import Path

import pytest
from fixture_gate import (
    CMP162_MANIFEST,
    MISSING_REAL,
    REPO_ROOT,
    campaign_root,
    load_manifest,
)

from aperv_tool.analysis import liveness
from aperv_tool.analysis.liveness import (
    SIGNAL_COVERAGE_ALL_ZERO,
    SIGNAL_FATAL_EXCEPTION,
    SIGNAL_TRACE_BELOW_FLOOR,
    RunFacts,
    _decide_application,
    _split_cell,
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

# The tree the parity runs over. `results/` and not the campaign root: the root also
# holds `results_smoke/`, two further batches the manifest does not pin, so grounding
# a count on the root would compare a superset against the pinned figures. The depth
# is explicit because the campaign's own `glob.glob` call is not recursive.
PINNED_TASKS_GLOB = ("results", "*", "*", "tasks.json")

# Measured on the pinned tree, so the parity cannot pass over an empty glob.
CMP162_IDENTITIES = 1458

#: The one string the promotion translated. Every other reason either side produces is
#: a language-neutral criterion code (`C1`/`C2`/`C5`), so this pair is the whole prose
#: surface between the two implementations. The parity assertion below NAMES it rather
#: than normalizing both sides, because a blanket normalization would also absorb the
#: next divergence — and the next one would not be a translation.
NO_EXECUTION_PTBR = "sem execução"
NO_EXECUTION_EN = "no execution"


def pinned_batches(manifest: dict) -> set[str]:
    """The batch directories the manifest pins under `results/`.

    The manifest keys its files by repository-relative path, so the batch name is
    the second segment. Deriving the set here means the test tracks the pin instead
    of a literal that a regenerated manifest would silently outdate.
    """
    return {
        key.split("/")[1] for key in manifest["files"] if key.startswith("results/")
    }


def _load_campaign_rule():
    """The campaign's own `admissibility.py`, loaded from disk and read only.

    It is the pre-promotion reference and the only evidence the promotion preserved
    the rule. It must never become an import of `aperv_tool`: the comparison would
    then be `liveness` against itself, which is green and proves nothing.
    """
    spec = importlib.util.spec_from_file_location("campaign_rule", CAMPAIGN_RULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _assert_selection_parity(theirs: dict, ours: dict) -> None:
    """Every key of the selection agrees, with the one translated string named.

    `select` returns six keys and only `kept` was compared originally, which left the
    four that the reading actually reports — the exclusions, the discarded replicas,
    the partial cells — outside the differential oracle. Five of the six carry no
    prose at all (apk names, replica numbers, criterion codes) and are compared as
    they stand; `excluded` carries the sentinel, mapped one way, so anything else
    that differs still fails.
    """
    assert set(theirs) == set(ours)

    for key in ("kept", "good_reps", "dropped_reps", "partial_cells", "max_reps"):
        assert theirs[key] == ours[key], key

    assert set(theirs["excluded"]) == set(ours["excluded"])
    for apk, their_arms in theirs["excluded"].items():
        our_arms = ours["excluded"][apk]
        assert set(their_arms) == set(our_arms), apk
        for arm, their_reasons in their_arms.items():
            translated = [
                NO_EXECUTION_EN if reason == NO_EXECUTION_PTBR else reason
                for reason in their_reasons
            ]
            assert translated == our_arms[arm], (apk, arm)


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


def test_a_cell_splits_into_admissible_and_failed_in_replica_order() -> None:
    """`_split_cell` is the one place a cell is read, and order is part of it.

    The failed half is reported to a human as the cause of a cell's death, so it is
    ordered by replica rather than by whatever order the verdicts arrived in.
    """
    good, bad = _split_cell({3: ["C1"], 1: [], 2: ["C2", "C5"]})

    assert good == [1]
    assert bad == [(2, ["C2", "C5"]), (3, ["C1"])]


def test_an_application_survives_when_every_arm_has_one_admissible_replica() -> None:
    """Surviving is per application, but the bookkeeping stays per arm.

    A replica discarded inside a cell that lived is not an exclusion — it is
    attrition, and it has to reach the reader as such or the denominator moves
    without a reason.
    """
    decided = _decide_application(
        {
            ARMS[0]: {1: []},
            ARMS[1]: {1: [], 2: ["C2"]},
            ARMS[2]: {1: []},
        },
        ARMS,
    )

    assert decided.excluded is None
    assert decided.good_reps == {ARMS[0]: [1], ARMS[1]: [1], ARMS[2]: [1]}
    assert decided.dropped_reps == {ARMS[1]: [(2, ["C2"])]}


def test_an_arm_that_failed_and_an_arm_that_never_ran_read_differently() -> None:
    """Both break the pair; they do not say the same thing about why.

    An arm whose replicas all failed names them and the criteria they failed. An arm
    with no execution has nothing to name, and reports that rather than an empty list
    of causes — an empty list reads as "it ran and nothing went wrong".
    """
    decided = _decide_application(
        {ARMS[0]: {1: []}, ARMS[1]: {1: ["C1"], 2: ["C1", "C5"]}, ARMS[2]: {}},
        ARMS,
    )

    assert decided.excluded == {
        ARMS[1]: ["rep1:C1", "rep2:C1+C5"],
        ARMS[2]: [NO_EXECUTION_EN],
    }
    # The application leaves whole: no arm keeps its bookkeeping, not even the one
    # that was healthy.
    assert decided.good_reps == {}
    assert decided.dropped_reps == {}


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
        # An application that SURVIVES while losing a replica, and whose cells do not
        # all carry the same number. Without it `dropped_reps` and `partial_cells`
        # are empty on both sides and their parity compares `{}` against `{}` — the
        # pinned tree does not supply the case either, because only 3 of its 1458
        # identities fail and all three sit in the one application it excludes.
        _task("com.example_4.apk", "ape", "default", 1),
        _task("com.example_4.apk", "ape", "default", 2),
        _task("com.example_4.apk", "aperv", "mop_off_llm_off", 1),
        _task(
            "com.example_4.apk",
            "aperv",
            "mop_off_llm_off",
            2,
            coverage={"method_coverage": 0, "activities_coverage": 0},
        ),
        _task("com.example_4.apk", "aperv", "mop_on_llm_off", 1),
    ]
    tasks_json = tmp_path / "tasks.json"
    tasks_json.write_text(json.dumps({"tasks": records}))

    campaign = _load_campaign_rule()

    glob_pattern = str(tmp_path / "tasks.json")
    assert campaign.TEARDOWN_GRACE_S == liveness.TEARDOWN_GRACE_S
    theirs = campaign.judge_identities(glob_pattern, 300)
    ours = judge_identities(glob_pattern, 300)
    assert theirs == ours

    # And the exclusion rule agrees on what the verdicts mean — on every key, not
    # only on who was kept. These records are what reaches the sentinel: example_3
    # never ran `aperv:mop_off_llm_off` at all, so the arm has no failed replica to
    # name and both sides fall back to their own "no execution" string. The pinned
    # tree below does not exercise that branch, which is why both tests exist.
    ours_selection = select(ours, ARMS)
    _assert_selection_parity(campaign.select(theirs, ARMS), ours_selection)

    # Non-vacuity, per key. A parity assertion over an empty container passes while
    # measuring nothing, and four of these six were empty before the records above
    # were added.
    for key in ("kept", "excluded", "good_reps", "dropped_reps", "partial_cells"):
        assert ours_selection[key], key
    assert ours_selection["max_reps"] == 2

    # And the two shapes an exclusion can take are both present, distinguishable.
    assert ours_selection["excluded"]["com.example_3.apk"]["aperv:mop_off_llm_off"] == [
        NO_EXECUTION_EN
    ]
    assert ours_selection["dropped_reps"][("com.example_4.apk", ARMS[1])] == [
        (2, ["C5"])
    ]


def test_promoted_rule_matches_the_campaign_copy_on_the_pinned_tree() -> None:
    """The same comparison, over cmp162's 1458 identities instead of nine records.

    The synthetic case pins the rule's shape at the edges it was written to hit. This
    one pins it against every record the campaign actually produced, where a
    disagreement only a real distribution can trigger would surface — and it is the
    net that makes `select` safe to decompose, since the decomposition must leave all
    six keys byte-equal to an implementation it does not share a line with.
    """
    manifest = load_manifest(CMP162_MANIFEST)
    if manifest is None:
        pytest.skip(MISSING_REAL)
    root = campaign_root(manifest)
    if root is None:
        pytest.skip(MISSING_REAL)
    if not CAMPAIGN_RULE.exists():
        pytest.skip(f"campaign rule not present: {CAMPAIGN_RULE}")

    campaign = _load_campaign_rule()
    glob_pattern = str(root.joinpath(*PINNED_TASKS_GLOB))

    # Non-vacuity first, and against the manifest rather than a count. A glob that
    # matched nothing makes every assertion below true over two empty dicts, which
    # is the failure mode this test exists to rule out — but the identity count
    # alone does not rule out the *opposite* one: globbing the campaign root instead
    # of `results/` also yields 1458, because `results_smoke/`'s two extra batches
    # carry identities that collide with the pinned ones and collapse on the key.
    # Pinning the batch set catches both directions.
    matched = {Path(path).parent.name for path in sorted(glob.glob(glob_pattern))}
    assert matched == pinned_batches(manifest)

    theirs = campaign.judge_identities(glob_pattern, 300)
    ours = judge_identities(glob_pattern, 300)

    assert len(ours) == CMP162_IDENTITIES
    assert theirs == ours

    _assert_selection_parity(campaign.select(theirs, ARMS), select(ours, ARMS))
