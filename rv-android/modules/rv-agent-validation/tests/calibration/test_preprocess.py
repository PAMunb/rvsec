"""
Tests for preprocessing artifact collection and SA filtering (T23-T30).

Uses tmp_path fixture to create realistic container output directories
and validate the pure functions in preprocess_docker.py.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "scripts"))

from preprocess_docker import (
    collect_preprocessed_artifacts,
    filter_by_sa_completeness,
    split_apks_round_robin,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_container_output(output_dir: Path, container_idx: int, apk_names: list[str]):
    """Create a realistic container output directory structure.

    Mimics what rv-experiment produces in out/instrumented_apks/:
    - {apk_name} (instrumented APK)
    - {apk_name}.json (unified static analysis)
    """
    instrumented = output_dir / f"preprocess_{container_idx}" / "instrumented_apks"
    instrumented.mkdir(parents=True, exist_ok=True)
    for apk_name in apk_names:
        (instrumented / apk_name).write_text("fake apk data")
        (instrumented / f"{apk_name}.json").write_text("{}")


# ---------------------------------------------------------------------------
# Artifact collection (T23-T26)
# ---------------------------------------------------------------------------


def test_collect_merges_all_containers(tmp_path):
    """T23: Artifacts from all containers are merged into dataset/."""
    _create_container_output(tmp_path, 0, ["app_a.apk", "app_b.apk"])
    _create_container_output(tmp_path, 1, ["app_c.apk"])

    dataset_dir = collect_preprocessed_artifacts(tmp_path, n_containers=2)

    assert dataset_dir == tmp_path / "dataset"
    assert (dataset_dir / "app_a.apk").exists()
    assert (dataset_dir / "app_b.apk").exists()
    assert (dataset_dir / "app_c.apk").exists()
    assert (dataset_dir / "app_a.apk.json").exists()
    assert (dataset_dir / "app_c.apk.json").exists()


def test_collect_no_duplicates(tmp_path):
    """T24: If same file exists in multiple containers, first copy wins."""
    _create_container_output(tmp_path, 0, ["app_a.apk"])
    _create_container_output(tmp_path, 1, ["app_a.apk"])

    # Modify container 1's file to verify container 0's version is kept
    c1_apk = tmp_path / "preprocess_1" / "instrumented_apks" / "app_a.apk"
    c1_apk.write_text("different data")

    dataset_dir = collect_preprocessed_artifacts(tmp_path, n_containers=2)

    content = (dataset_dir / "app_a.apk").read_text()
    assert content == "fake apk data", "first container's version should be kept"


def test_collect_handles_missing_container(tmp_path):
    """T25: Missing container output is skipped with a warning."""
    _create_container_output(tmp_path, 0, ["app_a.apk"])
    # Container 1 output does not exist

    dataset_dir = collect_preprocessed_artifacts(tmp_path, n_containers=2)

    assert (dataset_dir / "app_a.apk").exists()
    # Should not crash, just skip missing container


def test_collect_file_count(tmp_path):
    """T26: Each APK produces 2 files (apk + .json), all collected."""
    apks = ["app_a.apk", "app_b.apk", "app_c.apk"]
    _create_container_output(tmp_path, 0, apks)

    dataset_dir = collect_preprocessed_artifacts(tmp_path, n_containers=1)

    # 3 APKs x 2 files each = 6 files
    files = list(dataset_dir.iterdir())
    assert len(files) == 6


# ---------------------------------------------------------------------------
# SA completeness filtering (T27-T30)
# ---------------------------------------------------------------------------


def test_filter_all_complete(tmp_path):
    """T27: APKs with analysis JSON pass."""
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    for name in ["app_a.apk", "app_b.apk"]:
        (dataset / name).write_text("")
        (dataset / f"{name}.json").write_text("{}")

    passed, failed = filter_by_sa_completeness(dataset)

    assert passed == ["app_a.apk", "app_b.apk"]
    assert failed == []


def test_filter_missing_sa_file(tmp_path):
    """T28: APK missing analysis JSON fails with correct missing extension."""
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "app.apk").write_text("")
    # Missing: app.apk.json

    passed, failed = filter_by_sa_completeness(dataset)

    assert passed == []
    assert len(failed) == 1
    assert failed[0][0] == "app.apk"
    assert ".json" in failed[0][1]


def test_filter_mixed_pass_fail(tmp_path):
    """T29: Mix of complete and incomplete APKs."""
    dataset = tmp_path / "dataset"
    dataset.mkdir()

    # app_a: complete
    (dataset / "app_a.apk").write_text("")
    (dataset / "app_a.apk.json").write_text("{}")

    # app_b: missing analysis JSON
    (dataset / "app_b.apk").write_text("")

    # app_c: complete
    (dataset / "app_c.apk").write_text("")
    (dataset / "app_c.apk.json").write_text("{}")

    passed, failed = filter_by_sa_completeness(dataset)

    assert passed == ["app_a.apk", "app_c.apk"]
    assert len(failed) == 1
    assert failed[0][0] == "app_b.apk"
    assert len(failed[0][1]) == 1  # 1 extension missing (.json)


def test_filter_empty_dataset(tmp_path):
    """T30: Empty dataset returns empty lists."""
    dataset = tmp_path / "dataset"
    dataset.mkdir()

    passed, failed = filter_by_sa_completeness(dataset)

    assert passed == []
    assert failed == []
