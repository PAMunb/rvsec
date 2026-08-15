"""Three things go wrong at once, and every one of them leaves in the envelope.

The smoke proves the chain composes on good input. This proves the more important
half: that on bad input it *reports* rather than degrades. Three defects are
introduced into a throwaway copy of the two smoke applications —

  1. a trace truncated to 864 bytes, the size of the decisive campaign's own
     corpse, so the run is `COMPLETED` and carries nothing;
  2. a batch's `summary.csv` removed, so every run in it loses the payload the
     outcome is built from;
  3. a `tasks.json` record stripped of its `apk_name`, so it has no identity and
     the run it recorded cannot be named;

— and the test asserts each one arrives in the envelope by identity and reason,
and that no denominator quietly got smaller instead.

The failure being guarded against is specific and it is not a crash. Every one of
these three degrades *silently* by default: a corpse's zero counts as a genuine
zero, a missing payload becomes NaN and then False, and an unidentifiable record
simply is not there. All three make the analysis look complete and move the
answer, which is the one failure mode a green test suite cannot otherwise see.

**The campaign tree is never touched.** Everything is copied into ``tmp_path``
first, and the test asserts the originals are untouched afterwards.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest
from cmp162_arms import ARM_TABLE, arm_manifest
from fixture_gate import CMP162_MANIFEST, MISSING_REAL, campaign_root, load_manifest

from aperv_tool.analysis import corpus, gates, loader
from aperv_tool.analysis.callers import entry, paired_detection
from aperv_tool.analysis.envelope import Exclusion
from aperv_tool.analysis.liveness import SIGNAL_TRACE_BELOW_FLOOR
from aperv_tool.analysis.run_identity import IDENTITY_COLUMNS

#: The size of the decisive campaign's own corpse trace, reused here so the
#: fixture's defect is the one that actually occurred rather than an invented
#: small number.
CORPSE_BYTES = 864

#: Copied artefacts. `.trace.ndjson.gz` is excluded because it is a gzip of its
#: sibling `.trace` and not a second stream, and `.mop.json` because nothing in
#: this library may open one (INV-CAN-24) — leaving it out of the copy makes that
#: structural for this fixture instead of merely asserted.
_SKIPPED_SUFFIXES = (".trace.ndjson.gz", ".mop.json")


def _app_batch(campaign: Path, application: str) -> Path:
    """The batch directory holding one application's runs."""
    found = sorted((campaign / "results").glob(f"*/*/{application}"))
    assert found, f"{application} is not under {campaign / 'results'}"
    return found[0].parent


def _filter_tasks(source: Path, dest: Path, application: str) -> None:
    """Copy `tasks.json`, keeping only the records of one application."""
    document = json.loads(source.read_text(encoding="utf-8"))
    records = document["tasks"] if isinstance(document, dict) else document
    kept = [
        record
        for record in records
        if (record.get("config") or {}).get("apk_name") == application
    ]
    assert kept, f"no task record for {application} in {source}"
    if isinstance(document, dict):
        document["tasks"] = kept
        dest.write_text(json.dumps(document), encoding="utf-8")
    else:
        dest.write_text(json.dumps(kept), encoding="utf-8")


def _filter_csv(source: Path, dest: Path, application: str) -> None:
    """Copy an identity-grain CSV, keeping only one application's rows."""
    with source.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [row for row in reader if row.get("apk") == application]
    with dest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture(scope="module")
def corrupt_campaign(tmp_path_factory) -> dict:
    """A throwaway copy of the two smoke applications, with three defects in it.

    Module-scoped: the copy is about fifty megabytes and every assertion below
    reads the same tree.
    """
    document = load_manifest(CMP162_MANIFEST)
    if document is None:
        pytest.skip(MISSING_REAL)
    campaign = campaign_root(document)
    if campaign is None:
        pytest.skip(MISSING_REAL)

    applications = list(document["smoke_applications"])
    root = tmp_path_factory.mktemp("corrupt-campaign")
    batches: dict[str, Path] = {}

    for application in applications:
        source_batch = _app_batch(campaign, application)
        # The campaign nests each batch under a directory of its own name; the
        # loader tolerates that and the copy keeps it, so the fixture exercises
        # the real shape rather than a flattened convenience.
        dest_batch = root / "results" / source_batch.name / source_batch.name
        dest_batch.mkdir(parents=True, exist_ok=True)
        batches[application] = dest_batch

        dest_app = dest_batch / application
        dest_app.mkdir(exist_ok=True)
        for path in sorted((source_batch / application).iterdir()):
            if path.is_dir() or path.name.endswith(_SKIPPED_SUFFIXES):
                continue
            shutil.copy2(path, dest_app / path.name)

        _filter_tasks(
            source_batch / "tasks.json", dest_batch / "tasks.json", application
        )
        for name in ("summary.csv", "performance.csv"):
            _filter_csv(source_batch / name, dest_batch / name, application)

    truncated, dropped_payload = applications
    corruptions: dict[str, str] = {}

    # 1. A trace truncated to the corpse size. The run stays COMPLETED in the
    #    record; only the artefact says it died.
    arm = "aperv:mop_on_llm_off"
    trace = batches[truncated] / truncated / f"{truncated}__1__300__{arm}.trace"
    assert trace.is_file(), f"the copy is missing {trace.name}"
    with trace.open("r+b") as handle:
        handle.truncate(CORPSE_BYTES)
    corruptions["truncated_trace"] = f"{truncated}__1__300__{arm}"

    # 2. A whole batch's summary.csv removed. Nothing raises; every run in it
    #    simply has no outcome payload.
    (batches[dropped_payload] / "summary.csv").unlink()
    corruptions["missing_summary"] = dropped_payload

    # 3. One task record stripped of its application name, so it has no identity.
    tasks = batches[truncated] / "tasks.json"
    document = json.loads(tasks.read_text(encoding="utf-8"))
    records = document["tasks"]
    victim = next(
        record
        for record in records
        if (record.get("config") or {}).get("tool_config", {}).get("name") == "ape"
    )
    corruptions["malformed_record"] = victim["id"]
    del victim["config"]["apk_name"]
    tasks.write_text(json.dumps(document), encoding="utf-8")

    return {
        "root": root,
        "campaign": campaign,
        "applications": applications,
        "corruptions": corruptions,
        "batches": batches,
    }


def pipeline_over(root: Path, applications: list[str]):
    """loader → gates → exclusions → corpus → estimator, reporting every drop.

    This is the shape a real caller's pipeline has, written out here rather than
    hidden in a helper because the point of the test is *which* stage notices
    *which* defect.
    """
    frame, diagnostics = loader.load(root, ARM_TABLE)
    report = gates.run_all(frame, arm_manifest())

    exclusions: list[Exclusion] = []

    # The record that lost its identity. It is counted, never listed by name —
    # there is no name left to list — so the reason carries the count.
    if diagnostics.unidentifiable_records:
        exclusions.append(
            Exclusion(
                identity=f"{diagnostics.unidentifiable_records} task record(s)",
                reason="no usable identity in the task record",
            )
        )

    # The runs the admissibility rule refused, and the runs it admitted while a
    # corpse signal fired.
    #
    # The second half is this pipeline's own declared policy, not the library's.
    # `liveness` calls a run a corpse only when ALL THREE signals fire, because
    # each one alone has a benign reading, and it deliberately admits a run that
    # fired one. A caller may still decline to use such a run — that is a policy
    # decision, so it is made here, in the open, and the reason names the signal
    # rather than hiding behind the word "corpse".
    for identity, verdict in sorted(
        report.verdicts.items(), key=lambda item: str(item[0])
    ):
        if not verdict.admissible:
            exclusions.append(
                Exclusion(
                    identity=str(identity),
                    reason="failed " + ", ".join(verdict.failed_criteria),
                )
            )
        elif verdict.corpse_signals:
            exclusions.append(
                Exclusion(
                    identity=str(identity),
                    reason="corpse signal: " + ", ".join(verdict.corpse_signals),
                )
            )

    # The runs whose outcome payload never arrived. NaN would become False one
    # step later and count as a genuine non-detection.
    outcome = entry("E01").parameter("count_column")
    missing = frame[frame[outcome].isna()]
    for row in missing[list(IDENTITY_COLUMNS)].to_dict(orient="records"):
        identity = "__".join(str(row[column]) for column in IDENTITY_COLUMNS)
        exclusions.append(
            Exclusion(identity=identity, reason=f"no {outcome}: payload not loaded")
        )

    excluded_apks = {
        apk
        for apk in applications
        if frame.loc[frame["apk"] == apk, outcome].isna().all()
    }
    usable = frame[~frame["apk"].isin(excluded_apks) & frame[outcome].notna()]

    scoped, scope = corpus.scope(
        frame,
        subset=applications,
        reason="the two applications the fixture manifest names for the smoke",
    )
    usable = usable[usable["apk"].isin(scope.analysed.members)]

    envelope = paired_detection.run(
        entry("E01"),
        usable,
        scope=scope,
        exclusions=exclusions,
        provenance_ref="corrupted-fixture",
    )
    return frame, diagnostics, report, scope, exclusions, envelope


@pytest.fixture(scope="module")
def result(corrupt_campaign):
    return pipeline_over(corrupt_campaign["root"], corrupt_campaign["applications"])


class TestTheDefectsAreNoticed:
    """Each of the three is detected by the stage that should detect it."""

    def test_the_malformed_record_is_counted_not_dropped(self, result) -> None:
        """INV-CAN-04: a record with no identity leaves in the diagnostics."""
        _frame, diagnostics, *_ = result

        assert diagnostics.unidentifiable_records >= 1

    def test_the_truncated_trace_fires_the_floor_signal(
        self, result, corrupt_campaign
    ) -> None:
        """864 bytes is below the trace floor, whatever the record says.

        And only that signal fires, which is the interesting half. The record
        still says `COMPLETED` with real coverage, so the C-criteria all pass and
        `liveness` admits the run — a corpse needs all three signals, because
        each alone has a benign reading. The signal is what the run leaves
        behind, and a pipeline that wants it excluded has to say so itself.
        """
        _frame, _diagnostics, report, *_ = result

        expected = corrupt_campaign["corruptions"]["truncated_trace"]
        signalled = {
            str(identity): verdict
            for identity, verdict in report.verdicts.items()
            if verdict.corpse_signals
        }
        assert expected in signalled, (
            f"{expected} fired no corpse signal; runs that did: " f"{sorted(signalled)}"
        )

        verdict = signalled[expected]
        assert verdict.corpse_signals == (SIGNAL_TRACE_BELOW_FLOOR,)
        assert verdict.admissible is True
        assert verdict.is_corpse is False

    def test_no_healthy_run_fired_the_floor_signal(self, result) -> None:
        """Non-vacuity: the signal came from the corruption, not from everything."""
        _frame, _diagnostics, report, *_ = result

        signalled = [
            identity
            for identity, verdict in report.verdicts.items()
            if verdict.corpse_signals
        ]
        assert len(signalled) == 1, (
            "more than the truncated run fired a corpse signal: "
            f"{[str(identity) for identity in signalled]}"
        )

    def test_the_missing_summary_leaves_the_runs_without_an_outcome(
        self, result, corrupt_campaign
    ) -> None:
        """The rows survive with a null payload rather than vanishing."""
        frame, _diagnostics, *_ = result

        application = corrupt_campaign["corruptions"]["missing_summary"]
        rows = frame[frame["apk"] == application]
        assert not rows.empty, "the runs disappeared with their summary.csv"
        assert rows["mop_errors_unique"].isna().all()


class TestEveryExclusionReachesTheEnvelope:
    """The point of the test: attrition travels with the number."""

    def test_all_three_defects_are_listed(self, result) -> None:
        _frame, _diagnostics, _report, _scope, _exclusions, envelope = result

        reasons = " | ".join(exclusion.reason for exclusion in envelope.exclusions)
        assert "no usable identity" in reasons
        assert "payload not loaded" in reasons
        assert any(
            SIGNAL_TRACE_BELOW_FLOOR in exclusion.reason
            for exclusion in envelope.exclusions
        ), f"the truncated trace is not among the envelope's reasons: {reasons}"

    def test_every_exclusion_names_a_unit_and_a_reason(self, result) -> None:
        """A count with no identities cannot separate incidental from systematic."""
        *_, envelope = result

        assert envelope.exclusions
        for exclusion in envelope.exclusions:
            assert exclusion.identity, "an exclusion with no unit"
            assert exclusion.reason, f"{exclusion.identity} excluded for no reason"

    def test_the_denominator_did_not_shrink_silently(self, result) -> None:
        """Two applications reachable; whatever was analysed says why it was fewer."""
        _frame, _diagnostics, _report, scope, _exclusions, envelope = result

        denominator = envelope.denominator
        assert denominator.reachable == scope.analysed.cardinality == 2
        assert denominator.analysed < denominator.reachable, (
            "the corrupted fixture analysed everything, so this test proves "
            "nothing about attrition"
        )
        assert denominator.reason, "a shrunken denominator with no recorded reason"

    def test_the_convention_summarises_the_attrition(self, result) -> None:
        """A reader of the emitted table sees the losses without opening a log."""
        *_, envelope = result

        # `attrition`, not `exclusions`: the envelope already has a field of
        # that name carrying the full list, and both become columns of an
        # emitted table.
        assert "exclusions" not in envelope.convention
        assert envelope.convention["attrition"]
        assert "corpse signal" in envelope.convention["attrition"]

    def test_the_estimate_is_still_a_complete_envelope(self, result) -> None:
        """Degraded input produces a smaller estimate, not a less-documented one."""
        *_, envelope = result

        assert envelope.estimand
        assert envelope.denominator is not None
        assert envelope.convention
        assert isinstance(envelope.exclusions, tuple)


def test_the_campaign_tree_was_not_touched(corrupt_campaign) -> None:
    """The corruptions live in the copy; the originals are byte-identical.

    Checked against the fixture manifest's own digests, which is the only
    statement of what those files are supposed to be.
    """
    document = load_manifest(CMP162_MANIFEST)
    campaign = corrupt_campaign["campaign"]

    from fixture_gate import sha256_of

    checked = 0
    for relative, digest in document["files"].items():
        if not relative.startswith("results/"):
            continue
        path = campaign / relative
        if not path.is_file():
            continue
        assert sha256_of(path) == digest, f"{relative} was modified by the tests"
        checked += 1

    assert checked, "no pinned campaign file was checked — the guard is vacuous"
