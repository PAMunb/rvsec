"""Unit tests for `compare.py` and `preflight_runstart.py`, over synthetic inputs.

Both files are checks, and a check is only worth what it catches, so each test here breaks
the thing the check protects and asserts that the check notices. The decision rule is
exercised at each of its corners: a real regression blocks, a regression inside the margin
does not, an improvement never blocks, and a wide CI never blocks whatever the point
estimate says.

Run from the campaign directory:
    uv run pytest scripts/test_compare.py --import-mode=importlib -o "addopts=" -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compare  # noqa: E402
import preflight_runstart as preflight  # noqa: E402

CONTROL = compare.CONTROL_ARM
REFERENCE = compare.REFERENCE_ARM


def write_paired(path: Path, values):
    """A `per_apk_paired.csv` from `{apk: {column: value}}`, header ordered like the real one."""
    columns = sorted({column for cells in values.values() for column in cells})
    lines = ["apk," + ",".join(columns)]
    for apk in sorted(values):
        lines.append(
            apk + "," + ",".join(str(values[apk].get(column, "")) for column in columns)
        )
    path.write_text("\n".join(lines) + "\n")
    return path


def legs(tmp_path, a_values, b_values, metric="cov_method", arm=CONTROL):
    """Two legs differing only in the named metric of the named arm."""
    column = f"{arm}__{metric}"
    leg_a = write_paired(
        tmp_path / "a.csv",
        {f"app_{i:02d}.apk": {column: v} for i, v in enumerate(a_values)},
    )
    leg_b = write_paired(
        tmp_path / "b.csv",
        {f"app_{i:02d}.apk": {column: v} for i, v in enumerate(b_values)},
    )
    return leg_a, leg_b


class TestPairing:
    def test_only_applications_present_on_both_legs_are_paired(self, tmp_path):
        # Listwise, not imputed: an application measured on one leg only carries no paired
        # difference, and filling it with a zero would enter the trimmed mean as data.
        column = f"{CONTROL}__cov_method"
        leg_a = write_paired(
            tmp_path / "a.csv",
            {"shared.apk": {column: 50.0}, "only_a.apk": {column: 10.0}},
        )
        leg_b = write_paired(
            tmp_path / "b.csv",
            {"shared.apk": {column: 50.0}, "only_b.apk": {column: 90.0}},
        )
        report = compare.build_report(leg_a, leg_b)
        assert report["g1"]["outcomes"]["cov_method"]["n"] == 1

    def test_an_empty_cell_is_dropped_rather_than_read_as_zero(self, tmp_path):
        column = f"{CONTROL}__cov_method"
        path = write_paired(
            tmp_path / "a.csv", {"with.apk": {column: 42.0}, "without.apk": {}}
        )
        table = compare.read_paired(path)
        assert table["with.apk"][column] == 42.0
        assert column not in table["without.apk"]


class TestG1DecisionRule:
    """The four corners of "CI excludes zero harmfully AND |delta| > margin"."""

    def test_a_real_regression_blocks(self, tmp_path):
        # Every application drops by 5 pp, far beyond the 1.92 pp margin, with no overlap.
        base = [40.0 + i for i in range(20)]
        leg_a, leg_b = legs(tmp_path, base, [v - 5.0 for v in base])
        result = compare.build_report(leg_a, leg_b)["g1"]["outcomes"]["cov_method"]
        assert result["point"] == pytest.approx(-5.0, abs=1e-6)
        assert result["harmful_ci"] and result["beyond_margin"] and result["blocking"]

    def test_a_regression_inside_the_margin_does_not_block(self, tmp_path):
        # A consistent -1.0 pp: the CI excludes zero, but the drop is below the 1.92 pp
        # margin. This is the case the margin exists for — the documented between-campaign
        # drift is -0.743 pp with no code change at all.
        base = [40.0 + i for i in range(20)]
        leg_a, leg_b = legs(tmp_path, base, [v - 1.0 for v in base])
        result = compare.build_report(leg_a, leg_b)["g1"]["outcomes"]["cov_method"]
        assert result["harmful_ci"] is True
        assert result["beyond_margin"] is False
        assert result["blocking"] is False

    def test_an_improvement_never_blocks(self, tmp_path):
        base = [40.0 + i for i in range(20)]
        leg_a, leg_b = legs(tmp_path, base, [v + 5.0 for v in base])
        result = compare.build_report(leg_a, leg_b)["g1"]["outcomes"]["cov_method"]
        assert result["point"] > 0
        assert result["harmful_ci"] is False and result["blocking"] is False

    def test_a_large_drop_with_a_ci_that_straddles_zero_does_not_block(self, tmp_path):
        # Half the applications collapse and half improve by the same amount. The trimmed
        # mean moves little and the CI covers zero: noisy, not a finding.
        leg_a = [50.0] * 20
        leg_b = [10.0 if i % 2 else 90.0 for i in range(20)]
        paths = legs(tmp_path, leg_a, leg_b)
        result = compare.build_report(*paths)["g1"]["outcomes"]["cov_method"]
        assert result["excludes_zero"] is False
        assert result["blocking"] is False

    def test_a_tie_is_a_clean_no_finding(self, tmp_path):
        base = [40.0 + i for i in range(20)]
        leg_a, leg_b = legs(tmp_path, base, list(base))
        report = compare.build_report(leg_a, leg_b)
        result = report["g1"]["outcomes"]["cov_method"]
        assert result["point"] == pytest.approx(0.0, abs=1e-9)
        assert result["blocking"] is False
        assert report["g1"]["blocking"] == []


class TestDescriptiveOutcomes:
    def test_mop_total_never_blocks_however_far_it_moves(self, tmp_path):
        # The owner's 2026-08-04 decision, asserted rather than documented: mop_total
        # counts violation lines and its replica noise is ~15% of its level, so a large
        # move is not evidence about detection.
        base = [100.0] * 20
        leg_a, leg_b = legs(tmp_path, base, [1.0] * 20, metric="mop_total")
        result = compare.build_report(leg_a, leg_b)["g1"]["outcomes"]["mop_total"]
        assert result["point"] < -50
        assert result["gates"] is False and result["blocking"] is False

    @pytest.mark.parametrize("metric", compare.DESCRIPTIVE_OUTCOMES)
    def test_every_descriptive_outcome_is_still_reported(self, tmp_path, metric):
        base = [5.0] * 20
        leg_a, leg_b = legs(tmp_path, base, [3.0] * 20, metric=metric)
        result = compare.build_report(leg_a, leg_b)["g1"]["outcomes"][metric]
        assert "ci_lo" in result and "ci_hi" in result and result["n"] == 20

    def test_the_margin_table_and_the_descriptive_set_partition_the_outcomes(self):
        # Non-vacuity: an outcome in neither set would be silently unreported, and one in
        # both would be gated and excused at the same time.
        gated = set(compare.G1_MARGINS)
        descriptive = set(compare.DESCRIPTIVE_OUTCOMES)
        assert gated | descriptive == set(compare.OUTCOMES)
        assert gated & descriptive == set()


class TestG2:
    def test_guidance_that_still_guides_passes(self, tmp_path):
        # Reference above control on every application: the E3 shape, one-sided.
        values = {
            f"app_{i:02d}.apk": {
                f"{REFERENCE}__cov_act": 90.0 + i * 0.1,
                f"{CONTROL}__cov_act": 75.0 + i * 0.1,
            }
            for i in range(20)
        }
        leg_b = write_paired(tmp_path / "b.csv", values)
        leg_a = write_paired(tmp_path / "a.csv", values)
        g2 = compare.build_report(leg_a, leg_b)["g2"]
        assert g2["point"] > 0 and g2["passes"] is True and g2["blocking"] is False

    def test_guidance_that_collapsed_blocks(self, tmp_path):
        # The rewrite broke the MOP-weighted path: the contrast goes to zero. This is what
        # G2 exists to catch, and G1 by construction cannot see it — the control arm never
        # exercises the scoring the rewrite touched.
        values = {
            f"app_{i:02d}.apk": {
                f"{REFERENCE}__cov_act": 75.0 + i * 0.1,
                f"{CONTROL}__cov_act": 75.0 + i * 0.1,
            }
            for i in range(20)
        }
        leg_b = write_paired(tmp_path / "b.csv", values)
        g2 = compare.evaluate_g2(compare.read_paired(leg_b))
        assert g2["passes"] is False and g2["blocking"] is True

    def test_a_sign_reversal_blocks(self, tmp_path):
        values = {
            f"app_{i:02d}.apk": {
                f"{REFERENCE}__cov_act": 60.0 + i * 0.1,
                f"{CONTROL}__cov_act": 80.0 + i * 0.1,
            }
            for i in range(20)
        }
        leg_b = write_paired(tmp_path / "b.csv", values)
        g2 = compare.evaluate_g2(compare.read_paired(leg_b))
        assert g2["point"] < 0 and g2["blocking"] is True


class TestEstimandMatchesLegA:
    """The chain is worth nothing if it does not reproduce the number it is paired against."""

    LEG_A = (
        Path(__file__).resolve().parents[2]
        / "experimento-e3-decisiva/per_apk_paired.csv"
    )

    @pytest.mark.skipif(not LEG_A.is_file(), reason="leg A's frozen CSV is not present")
    def test_g2_reproduces_the_published_e3_contrast(self):
        # The E3 report published +14.916 with CI95 [7.754, 22.039] for exactly this
        # contrast. Recomputing it here proves that this script reads the columns the E3
        # analysis read and estimates what it estimated — the difference of trimmed means,
        # not the mean of the differences, which would give 14.006 instead.
        g2 = compare.evaluate_g2(compare.read_paired(self.LEG_A))
        assert g2["n"] == 40
        assert g2["point"] == pytest.approx(14.916, abs=0.001)
        assert g2["ci_lo"] == pytest.approx(7.754, abs=0.001)
        assert g2["ci_hi"] == pytest.approx(22.039, abs=0.001)


def run_start(**overrides):
    """A well-formed RUN_START record, before a test breaks one field of it."""
    record = {
        "type": "RUN_START",
        "v": 1,
        "run_id": "r1",
        "t0": 1_700_000_000_000,
        "preset": "mop",
        "params": {"ape.mopWeightDirect": 0, "ape.mopActivitySourceComponents": True},
        "props_digest": "d" * 64,
        "corpus_basis": "subset40:" + "b" * 64,
        "build": {"sha": "cafe1234", "time": "2026-08-04T00:00:00Z"},
    }
    record.update(overrides)
    return record


def manifest_with(arm_overrides=None, **top):
    manifest = {
        "corpus": {
            "subset_file": "calibracao/subset40.txt",
            "corpus_basis": "subset40:" + "b" * 64,
        },
        "build": {"expected_sha": "cafe1234"},
        "arms": [
            {
                "rv_tools_token": "aperv:mop_off_llm_off",
                "preset": "mop",
                "expected_params": (
                    arm_overrides
                    if arm_overrides is not None
                    else {"ape.mopWeightDirect": 0, "ape.frontierBoostWeight": 200}
                ),
            }
        ],
    }
    manifest.update(top)
    return manifest


def smoke_tree(tmp_path, record, token="aperv:mop_off_llm_off"):
    results = tmp_path / "results" / "c0" / "c0" / "app.apk"
    results.mkdir(parents=True)
    trace = results / f"app.apk__1__1800__{token}.trace"
    trace.write_text(json.dumps(record) + "\n" + json.dumps({"type": "STEP"}) + "\n")
    return tmp_path / "results"


class TestPreflight:
    def test_a_healthy_run_passes_every_check(self, tmp_path):
        results = smoke_tree(tmp_path, run_start())
        report, ok = preflight.run(results, manifest_with(), tmp_path, None)
        assert ok is True
        statuses = {row["check"]: row["status"] for row in report}
        assert statuses["preset+params"] == preflight.PASS
        assert statuses["build.sha"] == preflight.PASS
        assert statuses["corpus_basis"] == preflight.PASS
        # No pushed file supplied, so check 1 abstains rather than inventing a verdict.
        assert statuses["props_digest"] == preflight.SKIP

    def test_the_wrong_jar_fails_the_gate(self, tmp_path):
        # The gh71 failure mode: the image's own default-branch jar won the bind mount.
        results = smoke_tree(tmp_path, run_start(build={"sha": "0ldc0de"}))
        report, ok = preflight.run(results, manifest_with(), tmp_path, None)
        assert ok is False
        row = next(r for r in report if r["check"] == "build.sha")
        assert row["status"] == preflight.FAIL and "gh71" in row["detail"]

    def test_a_pre_stage_2_jar_collapsing_to_defaults_fails(self, tmp_path):
        # A jar that ignores ape.preset reports its own default preset and an empty plan.
        results = smoke_tree(tmp_path, run_start(preset="aperv", params={}))
        report, ok = preflight.run(results, manifest_with(), tmp_path, None)
        assert ok is False
        detail = next(r for r in report if r["check"] == "preset+params")["detail"]
        assert "preset" in detail

    def test_an_absent_corpus_basis_is_named_as_a_broken_parameter_path(self, tmp_path):
        record = run_start()
        del record["corpus_basis"]
        results = smoke_tree(tmp_path, record)
        report, ok = preflight.run(results, manifest_with(), tmp_path, None)
        assert ok is False
        row = next(r for r in report if r["check"] == "corpus_basis")
        assert row["status"] == preflight.FAIL and "ABSENT" in row["detail"]

    def test_a_mismatched_corpus_basis_is_named_as_the_wrong_list(self, tmp_path):
        results = smoke_tree(tmp_path, run_start(corpus_basis="subset40:" + "a" * 64))
        report, ok = preflight.run(results, manifest_with(), tmp_path, None)
        assert ok is False
        row = next(r for r in report if r["check"] == "corpus_basis")
        assert "MISMATCHED" in row["detail"]

    def test_a_key_at_the_jars_default_is_absent_and_that_is_not_a_failure(
        self, tmp_path
    ):
        # frontierBoostWeight=200 IS the jar's default, so RunSpecEcho omits it. Treating
        # that as a mismatch would fail every healthy run of this campaign.
        results = smoke_tree(tmp_path, run_start())
        report, ok = preflight.run(results, manifest_with(), tmp_path, None)
        row = next(r for r in report if r["check"] == "preset+params")
        assert row["status"] == preflight.PASS
        assert "1 at jar default" in row["detail"]

    def test_a_check_that_compared_nothing_fails(self, tmp_path):
        # Non-vacuity. If every declared key were absent, the plan check would be green
        # while verifying nothing at all — which is the shape of guard this project has
        # already been bitten by.
        results = smoke_tree(tmp_path, run_start(params={}))
        report, ok = preflight.run(
            results,
            manifest_with(arm_overrides={"ape.frontierBoostWeight": 200}),
            tmp_path,
            None,
        )
        assert ok is False
        detail = next(r for r in report if r["check"] == "preset+params")["detail"]
        assert "compared nothing" in detail

    def test_a_missing_trace_fails_rather_than_being_skipped(self, tmp_path):
        (tmp_path / "results").mkdir()
        report, ok = preflight.run(
            tmp_path / "results", manifest_with(), tmp_path, None
        )
        assert ok is False
        assert report[0]["check"] == "trace"

    def test_a_wrong_props_digest_fails(self, tmp_path):
        pushed = tmp_path / "pushed"
        pushed.mkdir()
        (pushed / "aperv:mop_off_llm_off.properties").write_text("ape.preset=mop\n")
        results = smoke_tree(tmp_path, run_start())
        report, ok = preflight.run(results, manifest_with(), tmp_path, pushed)
        assert ok is False
        row = next(r for r in report if r["check"] == "props_digest")
        assert row["status"] == preflight.FAIL

    def test_a_matching_props_digest_passes(self, tmp_path):
        import hashlib

        pushed = tmp_path / "pushed"
        pushed.mkdir()
        content = b"ape.preset=mop\n"
        (pushed / "aperv:mop_off_llm_off.properties").write_bytes(content)
        record = run_start(props_digest=hashlib.sha256(content).hexdigest())
        results = smoke_tree(tmp_path, record)
        report, ok = preflight.run(results, manifest_with(), tmp_path, pushed)
        row = next(r for r in report if r["check"] == "props_digest")
        assert row["status"] == preflight.PASS

    def test_an_unfilled_expected_sha_fails_loudly(self, tmp_path):
        # The manifest ships with build.expected_sha null, filled after the jar is built.
        # Running the gate before that must not pass by default.
        results = smoke_tree(tmp_path, run_start())
        report, ok = preflight.run(
            results, manifest_with(build={"expected_sha": None}), tmp_path, None
        )
        assert ok is False
        detail = next(r for r in report if r["check"] == "build.sha")["detail"]
        assert "6.2" in detail


class TestValuesEqual:
    @pytest.mark.parametrize(
        "observed,expected,equal",
        [
            (200, 200, True),
            (0.7, 0.7, True),
            (0.7, "0.7", True),
            (True, True, True),
            (False, False, True),
            (0, False, False),  # a zeroed weight is not a disabled gate
            (1, True, False),
            (200, 300, False),
            ("v13", "v13", True),
            ("v13", "v12", False),
        ],
    )
    def test_typed_echo_against_declared_value(self, observed, expected, equal):
        assert preflight.values_equal(observed, expected) is equal
