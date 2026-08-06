"""Unit tests for Gate 6 — the admissibility predicate in `verify.py`.

The gate exists because `COMPLETED` turned out to be a claim nothing checked: two runs of
the leg B campaign returned at 1284 s and 1012 s of an 1800 s budget and were stored
`COMPLETED` with `error_message` null, and every gate that existed passed on them. So each
test here builds an identity that is admissible in every respect but one, and asserts that
the gate names exactly that criterion. A criterion that cannot fail alone is a criterion
whose contribution is untestable.

Run from the campaign directory:
    uv run pytest scripts/test_verify_admissibility.py --import-mode=importlib -o "addopts=" -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import verify  # noqa: E402

APK = "org.example.app_1.apk"
ARM = "mop_on_llm_off"
TIMEOUT = 1800

# The minimum a trace needs to satisfy C3: RUN_START, the ACT/STATE dictionary entries the
# step refers to, then one step. A step record keys its timestamp on `t` and carries no
# `type` — that absence is what marks it as a step — and a step whose `act`/`st` references
# are unresolvable is counted malformed and skipped, so the dictionary lines are not
# decoration.
TRACE_WITHOUT_STEPS = (
    '{"type":"RUN_START","run_id":"r","t0":1750000000000,"preset":"mop","params":{}}\n'
    '{"type":"ACT","id":17,"name":"org.example/.MainActivity","mop":1}\n'
    '{"type":"STATE","id":231,"key":"S17a4f","act":17}\n'
)
TRACE_WITH_STEP = TRACE_WITHOUT_STEPS + (
    '{"s":1,"t":8123,"act":17,"st":231,'
    '"dec":{"a":"model=CLICK@[0,0][100,50]","src":"SATA","ch":"roulette_greedy"}}\n'
)


def build_tree(
    tmp_path: Path,
    *,
    state: str = "COMPLETED",
    error_message=None,
    execution_time_seconds: float = 1872.0,
    trace: str = TRACE_WITH_STEP,
    cov_signatures: int = 12,
    cov_method: float = 41.5,
    cov_act: float = 60.0,
    predicted_identities: int = 1,
    rep: int = 1,
    arm: str = ARM,
    campaign: str = "campaign",
) -> Path:
    """A one-identity campaign tree that is admissible unless a keyword says otherwise.

    Everything is written to disk rather than mocked: the predicate reads a real logcat and
    a real trace through the same paths it uses on the campaign, so a test that stubbed
    those would prove nothing about the file layout the gate actually walks.
    """
    iter_dir = tmp_path / campaign
    base = iter_dir / "results" / "container_00" / "run_00"
    apk_dir = base / APK
    apk_dir.mkdir(parents=True, exist_ok=True)

    stem = f"{APK}__{rep}__{TIMEOUT}__aperv:{arm}"
    logcat_lines = [
        f"01-01 00:00:0{i % 10}.000  1000  1000 I RVSEC-COV: <org.example.C: void m{i}()>"
        for i in range(cov_signatures)
    ]
    (apk_dir / f"{stem}.logcat").write_text("\n".join(logcat_lines) + "\n")
    (apk_dir / f"{stem}.trace").write_text(trace)

    task = {
        "config": {
            "apk_name": APK,
            "repetition": rep,
            "timeout": TIMEOUT,
            "tool_config": {"name": "aperv", "variant": arm},
        },
        "result": {
            "state": state,
            "error_message": error_message,
            "execution_time_seconds": execution_time_seconds,
            "detected_errors_count": 0,
            "coverage_metrics": {
                "method_coverage": cov_method,
                "activities_coverage": cov_act,
                "methods_mop_reachable_coverage": 30.0,
                "total_errors": 0,
            },
        },
    }
    (base / "tasks.json").write_text(json.dumps({"tasks": [task]}))
    (iter_dir / "manifest.json").write_text(
        json.dumps(
            {
                "timeout": TIMEOUT,
                "predicted_identities": predicted_identities,
                "arms": [{"rv_tools_token": f"aperv:{arm}", "preset": "mop"}],
            }
        )
    )
    return iter_dir


def failures_for(iter_dir: Path):
    """The criteria the tree's single identity fails, as bare codes."""
    scanned = verify.admissibility_by_identity(iter_dir)
    assert len(scanned) == 1, scanned
    (entry,) = scanned.values()
    return [f["criterion"] for f in entry["failures"]]


class TestAdmissiblePassesCleanly:
    def test_a_complete_run_fails_no_criterion(self, tmp_path):
        assert failures_for(build_tree(tmp_path)) == []


class TestEachCriterionFailsAlone:
    def test_c1_non_completed_state(self, tmp_path):
        assert failures_for(build_tree(tmp_path, state="ERROR")) == ["C1"]

    def test_c1_completed_but_carrying_an_error_message(self, tmp_path):
        # A COMPLETED record with a message is a contradiction, and the criterion is
        # written as a conjunction so it surfaces rather than passing on the state alone.
        assert failures_for(build_tree(tmp_path, error_message="adb: device offline")) == [
            "C1"
        ]

    def test_c2_the_truncated_run(self, tmp_path):
        # net.pfiers.osmfocus rep 1 as it happened: COMPLETED, no message, back at 1012 s
        # of 1800. Only C2 sees it — which is the whole reason C2 exists.
        assert failures_for(
            build_tree(tmp_path, execution_time_seconds=1012.0)
        ) == ["C2"]

    def test_c2_missing_execution_time(self, tmp_path):
        assert failures_for(build_tree(tmp_path, execution_time_seconds=None)) == ["C2"]

    def test_c3_trace_with_no_step_beyond_run_start(self, tmp_path):
        assert failures_for(build_tree(tmp_path, trace=TRACE_WITHOUT_STEPS)) == ["C3"]

    def test_c4_no_rvsec_cov_signature(self, tmp_path):
        # An application that never launched. The logcat is present and well-formed; it
        # simply carries no evidence that any instrumented method ran.
        assert failures_for(build_tree(tmp_path, cov_signatures=0)) == ["C4"]

    def test_c5_the_deliberately_zeroed_coverage_row(self, tmp_path):
        # INV-PLT-16: rv-platform emits a zeroed row when a logcat is present but its
        # static-analysis JSON cannot be resolved. Designed behaviour, and indistinguishable
        # from a valid task without this criterion.
        assert failures_for(build_tree(tmp_path, cov_method=0.0, cov_act=0.0)) == ["C5"]

    def test_c5_fires_when_only_one_of_the_two_is_zero(self, tmp_path):
        assert failures_for(build_tree(tmp_path, cov_act=0.0)) == ["C5"]


class TestC4FloorIsOne:
    def test_a_single_signature_is_enough(self, tmp_path):
        # The floor is structural — did the application execute any instrumented method at
        # all — and must not drift upward toward a number fitted to a campaign's own
        # distribution.
        assert verify._COV_SIGNATURE_FLOOR == 1
        assert failures_for(build_tree(tmp_path, cov_signatures=1)) == []


class TestGateSixOverTheWholeSet:
    def _gate(self, iter_dir: Path):
        result = verify.verify(iter_dir, sample_size=0, seed=42)
        return result, result["integrity"]

    def test_clean_tree_is_admissible(self, tmp_path):
        result, integrity = self._gate(build_tree(tmp_path))
        assert integrity["inadmissible"] == []
        assert integrity["n_admissible"] == 1
        assert integrity["count_matches"] is True
        assert result["verdict"] == "admissible"

    def test_one_truncated_identity_quarantines_the_run(self, tmp_path):
        result, integrity = self._gate(
            build_tree(tmp_path, execution_time_seconds=1012.0)
        )
        assert result["verdict"] == "quarantine"
        assert integrity["criterion_counts"]["C2"] == 1
        # The identity is named, not merely counted: a lost run is reported, never silenced.
        (row,) = integrity["inadmissible"]
        assert row["identity"][0] == APK
        assert row["container"] == "container_00"
        assert "1012" in row["failures"][0]["detail"]

    def test_c6_fires_when_the_count_misses_the_manifest(self, tmp_path):
        # Every identity present is admissible, but the campaign is short of what it
        # declared — the completeness half of the gate, which no per-identity check sees.
        result, integrity = self._gate(build_tree(tmp_path, predicted_identities=360))
        assert result["verdict"] == "quarantine"
        assert integrity["inadmissible"] == []
        assert integrity["count_matches"] is False
        assert integrity["criterion_counts"]["C6"] == 1

    def test_signature_distribution_is_reported_on_a_passing_run(self, tmp_path):
        _result, integrity = self._gate(build_tree(tmp_path, cov_signatures=7))
        dist = integrity["cov_signature_distribution"]
        assert dist == {
            "n": 1,
            "min": 7,
            "median": 7,
            "max": 7,
            "at_floor_or_below": 0,
        }


class TestCountingIsPerIdentity:
    def test_a_resume_record_does_not_double_count(self, tmp_path):
        """A resume APPENDS; the identity is judged on its best record, not on both.

        Counting records instead of identities is the error that turned 3 outstanding
        tasks into an apparent 8 during this campaign, so the gate is tested against the
        exact shape a recovery leaves behind: a failed record followed by a good one.
        """
        iter_dir = build_tree(tmp_path)
        tasks_json = iter_dir / "results" / "container_00" / "run_00" / "tasks.json"
        payload = json.loads(tasks_json.read_text())
        good = payload["tasks"][0]
        failed = json.loads(json.dumps(good))
        failed["result"]["state"] = "ERROR"
        failed["result"]["error_message"] = "adb: device offline"
        failed["result"]["execution_time_seconds"] = 61.0
        payload["tasks"] = [failed, good]
        tasks_json.write_text(json.dumps(payload))

        result = verify.verify(iter_dir, sample_size=0, seed=42)
        assert result["n_tasks"] == 2
        assert result["n_identities"] == 1
        assert result["integrity"]["n_admissible"] == 1
        assert result["verdict"] == "admissible"


class TestGateSevenControlArm:
    """Gate 7: MOP guidance must not reach `mop_off_llm_off`.

    A leak here means G1 is comparing the reference against something that is not a control,
    so the test builds the leak rather than trusting that the arm's weights were zeroed.
    """

    def _control_tree(self, tmp_path, trace):
        return build_tree(
            tmp_path, arm=verify.CONTROL_ARM_VARIANT, trace=trace, campaign="control"
        )

    def test_a_clean_control_arm_passes(self, tmp_path):
        result = verify.verify(self._control_tree(tmp_path, TRACE_WITH_STEP), 0, 42)
        assert result["control"]["violations"] == []
        assert result["control"]["n_control_runs"] == 1
        assert result["verdict"] == "admissible"

    def test_a_mop_sourced_step_quarantines(self, tmp_path):
        leaked = TRACE_WITHOUT_STEPS + (
            '{"s":1,"t":8123,"act":17,"st":231,'
            '"dec":{"a":"model=CLICK@[0,0][100,50]","src":"MOP_WIDGET","ch":"roulette"}}\n'
        )
        result = verify.verify(self._control_tree(tmp_path, leaked), 0, 42)

        assert result["verdict"] == "quarantine"
        (violation,) = result["control"]["violations"]
        assert violation["mop_sourced_steps"] == 1
        assert violation["first_offending_step"] == 1

    def test_a_mop_boosted_step_quarantines(self, tmp_path):
        # The source is innocent; the boost is not. Both halves of the criterion matter.
        # `dec.mop` is the MOP-widget boost — distinct from `dec.mopx`, which is MOP
        # exposure and says nothing about whether a boost was applied.
        boosted = TRACE_WITHOUT_STEPS + (
            '{"s":4,"t":8123,"act":17,"st":231,'
            '"dec":{"a":"model=CLICK@[0,0][100,50]","src":"SATA","ch":"roulette",'
            '"mop":500}}\n'
        )
        result = verify.verify(self._control_tree(tmp_path, boosted), 0, 42)

        assert result["verdict"] == "quarantine"
        (violation,) = result["control"]["violations"]
        assert violation["mop_boosted_steps"] == 1

    def test_the_reference_arm_is_not_audited_by_this_gate(self, tmp_path):
        # Gate 7 is about the control arm only. MOP guidance in the reference is the point
        # of the reference, not a violation.
        leaked = TRACE_WITHOUT_STEPS + (
            '{"s":1,"t":8123,"act":17,"st":231,'
            '"dec":{"a":"model=CLICK@[0,0][100,50]","src":"MOP_WIDGET","ch":"roulette"}}\n'
        )
        result = verify.verify(build_tree(tmp_path, trace=leaked), 0, 42)

        assert result["control"]["n_control_runs"] == 0
        assert result["control"]["violations"] == []


class TestGateOneAbsenceIsCompliance:
    """Gate 1: a declared key absent from `params` is at the jar's own value, not wrong.

    Both halves are tested together on purpose. Reading absence as compliance is only sound
    while the gate still asserts that it compared something — otherwise the rule becomes a
    way to pass without checking anything, which is a worse gate than the one it replaced.
    """

    def _tree_with_expectations(self, tmp_path, expected_params, params):
        iter_dir = build_tree(
            tmp_path,
            trace=(
                '{"type":"RUN_START","run_id":"r","t0":1750000000000,"preset":"mop",'
                f'"params":{json.dumps(params)}}}\n'
                '{"type":"ACT","id":17,"name":"org.example/.MainActivity","mop":1}\n'
                '{"type":"STATE","id":231,"key":"S17a4f","act":17}\n'
                '{"s":1,"t":8123,"act":17,"st":231,'
                '"dec":{"a":"model=CLICK@[0,0][100,50]","src":"SATA","ch":"roulette"}}\n'
            ),
        )
        manifest = json.loads((iter_dir / "manifest.json").read_text())
        manifest["arms"][0]["expected_params"] = expected_params
        (iter_dir / "manifest.json").write_text(json.dumps(manifest))
        return iter_dir

    def test_a_key_at_the_preset_value_is_not_a_mismatch(self, tmp_path):
        # The real case: the control arm declares mopWeightWtg=0, which IS the mop preset's
        # value, so the jar omits it. 120 healthy runs were failed for complying.
        iter_dir = self._tree_with_expectations(
            tmp_path,
            {"ape.mopWeightDirect": 0, "ape.mopWeightWtg": 0},
            {"ape.mopWeightDirect": 0},
        )
        result = verify.verify(iter_dir, 0, 42)

        assert result["config_findings"] == []
        assert result["config_at_default"] == {"aperv:mop_on_llm_off": ["ape.mopWeightWtg"]}
        assert result["verdict"] == "admissible"

    def test_a_wrong_value_is_still_a_mismatch(self, tmp_path):
        iter_dir = self._tree_with_expectations(
            tmp_path,
            {"ape.mopWeightDirect": 0},
            {"ape.mopWeightDirect": 500},
        )
        result = verify.verify(iter_dir, 0, 42)

        assert result["verdict"] == "quarantine"
        (finding,) = result["config_findings"]
        assert finding["field"] == "ape.mopWeightDirect"
        assert finding["observed"] == 500

    def test_an_arm_that_compared_nothing_fails(self, tmp_path):
        # The guard that keeps the rule above from being a free pass: every declared key
        # absent means the gate checked nothing, which must not read as a pass.
        iter_dir = self._tree_with_expectations(
            tmp_path,
            {"ape.mopWeightDirect": 0, "ape.mopWeightWtg": 0},
            {},
        )
        result = verify.verify(iter_dir, 0, 42)

        assert result["verdict"] == "quarantine"
        (finding,) = result["config_findings"]
        assert finding["field"] == "<declared keys>"
        assert "compared nothing" in finding["observed"]


class TestDivergenceWithoutTheCsv:
    def test_an_absent_csv_is_reported_skipped_not_passed(self, tmp_path):
        """A gate that never ran must not print PASS.

        The validity gates have to be decidable before consolidation, since no outcome may
        be read until they pass — so verify runs with no CSV, and Gate 5 has to say that
        it had nothing to compare against rather than silently reading as clean.
        """
        iter_dir = build_tree(tmp_path)
        assert not (iter_dir / "per_apk_paired.csv").exists()

        result = verify.verify(iter_dir, 0, 42)
        report = verify.render_report(iter_dir, result)

        assert result["csv_present"] is False
        assert "SKIPPED" in report
        assert "it is not a pass" in report


class TestBlindToArm:
    """An admissibility rule that could see the arm could prune one side of the comparison
    — the failure this whole change is built to prevent at the jar level."""

    @pytest.mark.parametrize(
        "arm", ["mop_on_llm_off", "mop_off_llm_off", "mop_on_llm_70"]
    )
    def test_the_same_run_is_judged_the_same_in_every_arm(self, tmp_path, arm):
        intact = build_tree(tmp_path, arm=arm, campaign="intact")
        truncated = build_tree(
            tmp_path, arm=arm, campaign="truncated", execution_time_seconds=1012.0
        )
        assert failures_for(intact) == []
        assert failures_for(truncated) == ["C2"]
