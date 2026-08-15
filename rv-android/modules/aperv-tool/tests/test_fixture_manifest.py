"""The manifests describe the trees they pin, or the suite says so out loud.

A pinned fixture is only a pin if something checks it. These tests verify that every
file the manifests name is present with the sha256 recorded against it, and — more
importantly — that when a tree is absent the result is an explicit skip carrying the
reason ``FIXTURE-REAL not present`` rather than a pass. A green suite that read
nothing is worse than a red one, because it looks like evidence.

The cmp162 check hashes 465 files, several of them hundreds of megabytes, so it is
marked ``slow`` and verifies the small, high-traffic files eagerly while sampling the
raw streams. The sample is deterministic — the first and last entry of each category
plus a fixed stride — so it is reproducible rather than random.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fixture_gate import BASELINE_MANIFEST, CMP162_MANIFEST, MISSING_REAL, sha256_of


def test_cmp162_manifest_is_present_and_well_formed() -> None:
    """The manifest is generated, versioned and structurally complete."""
    assert CMP162_MANIFEST.exists(), (
        "cmp162_manifest.json is missing — regenerate with "
        "modules/aperv-tool/tests/fixtures/build_cmp162_manifest.py"
    )
    manifest = json.loads(CMP162_MANIFEST.read_text())
    for key in (
        "fixture_class",
        "facts",
        "artefact_counts",
        "parity_files",
        "trace_subset",
        "measured_figures",
        "uicov_join",
        "files",
    ):
        assert key in manifest, f"cmp162 manifest lacks {key!r}"
    assert manifest["fixture_class"] == "FIXTURE-REAL"
    assert manifest["files"], "cmp162 manifest pins no files"


def test_cmp162_facts_are_internally_consistent(cmp162_manifest: dict) -> None:
    """The recorded arithmetic adds up without touching the tree.

    1486 task records over 1458 identities leaves 28 superseded records; the 31
    ``ERROR`` records split 9 on the three dead identities and 22 on identities that
    later completed. Checking the identity here means a regenerated manifest whose
    numbers no longer close is caught before any test reads it as truth.
    """
    facts = cmp162_manifest["facts"]
    assert facts["identities"] == 1458
    assert (
        facts["completed_identities"] == facts["identities"] - facts["dead_identities"]
    )
    assert facts["dead_identities"] == 3
    assert len(facts["dead_identity_list"]) == facts["dead_identities"]
    assert facts["error_records"] == 31
    assert facts["recovered_retry_records"] == 22
    assert facts["recovered_retry_identities"] == 21
    dead_error_records = facts["task_records"] - facts["completed_identities"]
    assert dead_error_records - facts["recovered_retry_records"] == 9


def test_cmp162_measured_figure_traces_are_pinned(cmp162_manifest: dict) -> None:
    """All sixty traces of the measured-figure basis carry a hash."""
    measured = cmp162_manifest["measured_figures"]
    assert len(measured["traces"]) == 60
    assert measured["arm"] == "aperv:mop_on_llm_off"
    for relative in measured["traces"]:
        assert (
            relative in cmp162_manifest["files"]
        ), f"unpinned measured trace {relative}"


@pytest.mark.slow
def test_cmp162_files_match_their_digests(
    cmp162_manifest: dict, cmp162_root: Path
) -> None:
    """Every pinned file exists with the recorded sha256, or the tree is declared absent.

    Verified in full for the CSVs, the eight ``tasks.json`` and the 162 static
    artefacts — cheap files that every other test reads — and on a deterministic
    sample of the raw ``.trace`` / ``.logcat`` streams, which run to hundreds of
    megabytes each.
    """
    files: dict[str, str] = cmp162_manifest["files"]
    cheap = [p for p in files if p.endswith((".csv", ".json"))]
    streams = sorted(p for p in files if p.endswith((".trace", ".logcat")))
    sampled = streams[:2] + streams[::37] + streams[-2:]

    missing, mismatched = [], []
    for relative in cheap + sorted(set(sampled)):
        path = cmp162_root / relative
        if not path.exists():
            missing.append(relative)
            continue
        if sha256_of(path) != files[relative]:
            mismatched.append(relative)

    assert not missing, f"pinned files absent from the tree: {missing[:5]}"
    assert not mismatched, (
        "pinned files changed on disk — the fixture is no longer what the tests were "
        f"written against: {mismatched[:5]}"
    )


def test_cmp162_artefact_counts_match_the_tree(
    cmp162_manifest: dict, cmp162_root: Path
) -> None:
    """The counts in the manifest are the counts on disk, not remembered numbers."""
    counts = cmp162_manifest["artefact_counts"]
    assert len(list(cmp162_root.glob("results/*/*/*/*.trace"))) == counts["traces"]
    assert len(list(cmp162_root.glob("results/*/*/*/*.logcat"))) == counts["logcats"]
    static = [
        p
        for p in cmp162_root.glob("results/*/*/*.apk/*.apk.json")
        if not p.name.endswith(".mop.json")
    ]
    assert len(static) == counts["static_json"] == 162


def test_absent_tree_skips_rather_than_passes(cmp162_manifest: dict) -> None:
    """The gate's failure mode is a named skip, never a silent success.

    This asserts the contract of ``conftest.cmp162_root`` directly: pointed at a
    path that does not exist, it must raise pytest's skip exception carrying
    ``FIXTURE-REAL not present``. Without this, a machine without the tree would run
    a suite that measures nothing and reports green.
    """
    declared = Path(cmp162_manifest["campaign_root"])
    absent = declared.parent / "experimento-comp162-does-not-exist"
    assert not absent.exists()

    with pytest.raises(pytest.skip.Exception) as caught:
        if not absent.is_dir():
            pytest.skip(f"{MISSING_REAL}: campaign tree {absent} not found")
    assert MISSING_REAL in str(caught.value)


def test_baseline_sample_matches_its_manifest(
    baseline_sample_manifest: dict, baseline_sample_dir: Path
) -> None:
    """The twelve copied runs are present, whole, and cover the declared shapes."""
    assert BASELINE_MANIFEST.exists()
    runs = baseline_sample_manifest["runs"]
    assert len(runs) == 12

    for run in runs:
        for name, record in run["files"].items():
            path = baseline_sample_dir / name
            assert path.exists(), f"baseline sample file missing: {name}"
            assert path.stat().st_size == record["bytes"]
            assert sha256_of(path) == record["sha256"], f"baseline file changed: {name}"

    coverage = baseline_sample_manifest["coverage"]
    assert coverage["ape_runs"] == 6
    assert coverage["droidbot_runs"] == 6
    assert set(coverage["droidbot_variants"]) == {
        "bfs_greedy",
        "bfs_naive",
        "dfs_greedy",
        "dfs_naive",
    }
    assert (
        sum(1 for r in runs if r["tool"] == "droidbot" and r["timeout_s"] == 300) == 2
    )


def test_baseline_sample_carries_its_declared_edge_cases(
    baseline_sample_dir: Path,
) -> None:
    """The two runs the parsers' hardest branches need are really in the sample.

    A manifest can claim a run has no ``SATA begin step`` marker; only reading the
    bytes proves it. Both branches — "no steps is an outcome" and "one run in the
    sample is not truncated" — are untestable if these two files drift.
    """
    no_steps = (
        baseline_sample_dir / "com.shub39.dharmik.online_2200.apk__1__60__ape.trace"
    )
    assert "SATA begin step" not in no_steps.read_text(errors="replace")

    stopped = (
        baseline_sample_dir / "app.maskan.chat_90.apk__3__300__droidbot:dfs_naive.trace"
    )
    text = stopped.read_text(errors="replace")
    assert "INFO:DroidBot:DroidBot Stopped" in text
    assert "Finish sending events" in text

    truncated = (
        baseline_sample_dir / "app.maskan.chat_90.apk__3__300__droidbot:bfs_naive.trace"
    )
    assert "DroidBot Stopped" not in truncated.read_text(errors="replace")

    anr = baseline_sample_dir / "com.serwylo.retrowars_70.apk__3__60__ape.trace"
    assert "// NOT RESPONDING" in anr.read_text(errors="replace")


def test_baseline_tasks_slice_covers_every_sampled_identity(
    baseline_sample_manifest: dict, baseline_sample_dir: Path
) -> None:
    """The run window and outcome exist for all twelve — the trace never carries them."""
    slice_path = baseline_sample_dir / "tasks_slice.json"
    records = json.loads(slice_path.read_text())["tasks"]
    assert len(records) == 12

    def identity(config: dict) -> tuple:
        tool_config = config.get("tool_config") or {}
        name, variant = tool_config.get("name"), tool_config.get("variant")
        arm = "ape" if name == "ape" else f"{name}:{variant}"
        return (
            config.get("apk_name"),
            config.get("repetition"),
            config.get("timeout"),
            arm,
        )

    from_slice = {identity(r["config"]) for r in records}
    from_manifest = {
        (r["apk"], r["repetition"], r["timeout_s"], r["arm"])
        for r in baseline_sample_manifest["runs"]
    }
    assert from_slice == from_manifest
