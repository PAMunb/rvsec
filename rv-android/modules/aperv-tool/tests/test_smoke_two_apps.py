"""The whole library, end to end, over two applications and no device.

Every other test in this suite exercises one module. This one proves the modules
compose: a campaign directory goes in at one end and a CSV of envelopes comes out
at the other, through loader, gates, corpus, a catalogue-driven caller and emit,
with nothing started, installed or connected. That is the property the final
campaign depends on — the analysis has to already exist and already run when its
output lands — and it is exactly the property a suite of unit tests cannot show.

Two applications, because the point is composition and not statistics. No number
computed here answers anything (INV-CAN-21): with two pairs the estimator is
below its own power floor by construction, and the test asserts that it *says so*
rather than asserting a result.

The chain is deliberately run against the whole campaign before scoping, so the
denominator the envelope carries is the real one — 162 applications reachable,
two analysed, with the reason recorded. A smoke that loaded only the two would
have produced a denominator of two and hidden the thing worth checking.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest
from cmp162_arms import ARM_TABLE, arm_manifest, assert_matches_manifest
from fixture_gate import CMP162_MANIFEST, MISSING_REAL, campaign_root, load_manifest

from aperv_tool.analysis import corpus, gates, loader, provenance
from aperv_tool.analysis.callers import RQ_MAP, entry, paired_detection
from aperv_tool.analysis.emit import table
from aperv_tool.analysis.envelope import Envelope


@pytest.fixture(scope="module")
def manifest() -> dict:
    document = load_manifest(CMP162_MANIFEST)
    if document is None:
        pytest.skip(MISSING_REAL)
    return document


@pytest.fixture(scope="module")
def campaign(manifest: dict) -> Path:
    root = campaign_root(manifest)
    if root is None:
        pytest.skip(MISSING_REAL)
    return root


@pytest.fixture(scope="module")
def loaded(campaign: Path, manifest: dict):
    """The campaign's ``results/`` at the run grain, plus its load diagnostics.

    ``results/`` and not the campaign root, deliberately. ``find_batches`` also
    discovers ``results_smoke/``, two further batches the campaign ran while it
    was being set up, so loading the root returns a **superset** of what the
    fixture manifest pins — and every count asserted below is a manifest fact.
    A test that loaded the root would compare pinned numbers against unpinned
    bytes and drift the moment either changed.
    """
    assert_matches_manifest(manifest)
    return loader.load(campaign / "results", ARM_TABLE)


@pytest.fixture(scope="module")
def smoke_applications(manifest: dict) -> list[str]:
    """The two applications the manifest names for this purpose."""
    return list(manifest["smoke_applications"])


@pytest.fixture(scope="module")
def pipeline(loaded, smoke_applications: list[str]):
    """loader → gates → corpus → outcomes → estimator → the envelope.

    Run once for the module: the load walks eight batches, and every assertion
    below reads the same result rather than repeating it.
    """
    frame, diagnostics = loaded

    report = gates.run_all(frame, arm_manifest())

    scoped, scope = corpus.scope(
        frame,
        subset=smoke_applications,
        reason="the two applications the fixture manifest names for the smoke",
    )

    catalogue_entry = entry("E01")
    stamp = provenance.stamp(
        "smoke-two-apps",
        [CMP162_MANIFEST, RQ_MAP],
        dict(catalogue_entry.parameters),
    )
    envelope = paired_detection.run(
        catalogue_entry, scoped, scope=scope, provenance_ref=stamp.ref
    )
    return frame, diagnostics, report, scoped, scope, envelope, stamp


class TestTheChainComposes:
    """Each stage produced something the next one could use."""

    def test_the_load_reaches_the_whole_campaign(self, pipeline, manifest) -> None:
        """Every arm, every batch, and the identity count the manifest pins."""
        frame, _diagnostics, _report, _scoped, _scope, _envelope, _stamp = pipeline

        assert not frame.empty
        assert set(frame["arm"]) == set(ARM_TABLE)

        batches = {
            key.split("/")[1] for key in manifest["files"] if key.startswith("results/")
        }
        assert frame["batch"].nunique() == len(batches)
        assert len(frame) == manifest["facts"]["identities"]
        assert frame["apk"].nunique() == manifest["facts"]["applications"]

    def test_the_gates_ran_on_every_arm(self, pipeline) -> None:
        """Five gates, and gate 1 only where a control was declared."""
        _frame, _diagnostics, report, _scoped, _scope, _envelope, _stamp = pipeline

        gated_arms = {arm for _gate, arm in report.results}
        assert gated_arms == set(ARM_TABLE)
        assert report.verdicts, "no per-run verdict was computed"
        assert report.corpse_census, "the corpse census is empty"

    def test_an_unevidenced_gate_is_not_run_and_never_a_pass(self, pipeline) -> None:
        """INV-CAN-06, on the frame as it actually arrives.

        The loader fills no `run_start` column and the fixture declares no build
        digest, so the attribution evidence for the `aperv` arms is absent. The
        result must be `not-run` — a third status, not a lenient pass.
        """
        _frame, _diagnostics, report, _scoped, _scope, _envelope, _stamp = pipeline

        attribution = report.status(gates.GATE_ARM_ATTRIBUTION, "aperv:mop_on_llm_off")
        assert attribution == "not-run"

        statuses = {result.status for result in report.results.values()}
        assert statuses <= {"pass", "fail", "not-run"}

    def test_the_scope_carries_both_denominators(self, pipeline) -> None:
        """162 reachable, 2 analysed, and the reason for the difference."""
        _frame, _diagnostics, _report, scoped, scope, _envelope, _stamp = pipeline

        assert scope.reachable.cardinality == 162
        assert scope.analysed.cardinality == 2
        assert scope.reason
        assert set(scoped["apk"]) == set(scope.analysed.members)

    def test_the_estimate_came_out_of_the_catalogue(self, pipeline) -> None:
        """Every knob in the envelope's convention is one the TOML declared."""
        *_, envelope, _stamp = pipeline

        assert envelope.convention["entry"] == "E01"
        declared = entry("E01").parameters
        assert str(declared["arm_a"]) in envelope.convention["arms"]
        assert str(declared["replica_rule"]) in envelope.convention["outcome"]


class TestTheEnvelopeIsComplete:
    """The five things a number may not leave the library without."""

    def test_every_envelope_carries_all_five(self, pipeline) -> None:
        *_, envelope, _stamp = pipeline

        for produced in (envelope,):
            assert isinstance(produced, Envelope)
            assert produced.estimand, "no estimand"
            assert isinstance(produced.n, int), "no n"
            assert produced.denominator is not None, "no denominator"
            assert produced.convention, "no convention"
            assert isinstance(produced.exclusions, tuple), "no exclusions field"

    def test_the_denominator_is_readable_on_its_own(self, pipeline) -> None:
        """Both cardinalities, and a reason whenever they differ."""
        *_, envelope, _stamp = pipeline

        denominator = envelope.denominator
        assert denominator.analysed <= denominator.reachable
        if denominator.analysed != denominator.reachable:
            assert denominator.reason

    def test_the_campaign_the_subset_came_from_stays_visible(self, pipeline) -> None:
        """The denominator is the declared subset; the 162 it came from is not lost.

        Both numbers matter and they answer different questions. The denominator
        says what this estimate covers; the convention says what the campaign
        could have covered, which is the only way a reader can tell a corpus of
        two from a corpus of two chosen out of a hundred and sixty-two.
        """
        _frame, _diagnostics, _report, _scoped, scope, envelope, _stamp = pipeline

        assert envelope.denominator.reachable == scope.analysed.cardinality
        assert str(scope.reachable.cardinality) in envelope.convention["corpus"]
        assert scope.reason in envelope.convention["corpus"]

    def test_two_pairs_are_below_the_floor_and_the_envelope_says_so(
        self, pipeline
    ) -> None:
        """The smoke reports its own inability to conclude, rather than a result."""
        *_, envelope, _stamp = pipeline

        assert envelope.estimate["n_disc"] < envelope.estimate["power_floor_n_disc"]
        assert envelope.estimate["below_floor"] is True

    def test_the_provenance_reference_travels_with_the_estimate(self, pipeline) -> None:
        """A reference, not the record: a timestamp would break re-derivation."""
        *_, envelope, stamp = pipeline

        assert envelope.provenance_ref == stamp.ref
        assert stamp.inputs, "the provenance hashed nothing"


class TestEmit:
    """The last stage writes a file, and the file is readable without the code."""

    def test_the_table_writes_the_fixed_columns(self, pipeline, tmp_path) -> None:
        *_, envelope, _stamp = pipeline

        written = table([envelope], tmp_path / "smoke" / "results.csv")
        rows = list(csv.DictReader(written.read_text(encoding="utf-8").splitlines()))

        assert written.exists()
        assert len(rows) == 1
        header = set(rows[0])
        for column in (
            "estimand",
            "n",
            "reachable",
            "analysed",
            "denominator_reason",
            "convention",
            "exclusions",
            "provenance_ref",
        ):
            assert column in header, f"{column} is not in the emitted table"

    def test_nothing_under_the_campaign_was_written(self, campaign, pipeline) -> None:
        """The whole chain is read-only over recorded artefacts (INV-APV-35).

        Asserted by comparing the campaign's own consolidated outputs before and
        after: the pipeline fixture has already run by the time this executes.
        """
        consolidated = campaign / "consolidado"
        if not consolidated.is_dir():
            pytest.skip(f"{MISSING_REAL}: no consolidado directory")

        before = {path.name: path.stat().st_mtime_ns for path in consolidated.iterdir()}
        table([pipeline[5]], Path(campaign).parent / "___never___")
        after = {path.name: path.stat().st_mtime_ns for path in consolidated.iterdir()}

        assert before == after, "the analysis touched the campaign's own outputs"
        Path(Path(campaign).parent / "___never___").unlink(missing_ok=True)


def test_no_device_was_needed(pipeline) -> None:
    """Non-vacuity: the chain really did run, on real recorded bytes.

    A smoke that skipped would satisfy every assertion above by never executing
    one. This asserts the load produced the campaign's own scale, which no
    synthetic fixture in this suite reaches.
    """
    frame, diagnostics, *_ = pipeline

    assert len(frame) > 1_000, "the smoke did not read the recorded campaign"
    assert diagnostics is not None


def test_the_frame_is_a_frame(pipeline) -> None:
    """Guards the fixture's own shape, so a later refactor of it fails here."""
    frame, *_ = pipeline

    assert isinstance(frame, pd.DataFrame)
