"""Unit tests for `repair_tasks.py` over a synthetic campaign tree.

The script's whole value is that it preserves evidence *before* it mutates anything — the
re-execution writes to the same filenames, so a repair that skipped the copy would destroy
the record of the defect in the act of fixing it. So the tests assert the preservation, not
just the mutation, and they assert that a healthy identity is left alone: a repair tool that
condemns a good run costs more than the defect it was written for.

Run from the campaign directory:
    uv run pytest scripts/test_repair_tasks.py --import-mode=importlib -o "addopts=" -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import repair_tasks  # noqa: E402
import verify  # noqa: E402
from test_verify_admissibility import APK, TIMEOUT, build_tree  # noqa: E402


def read_records(iter_dir: Path):
    tasks_json = iter_dir / "results" / "container_00" / "run_00" / "tasks.json"
    return json.loads(tasks_json.read_text())["tasks"]


def add_second_identity(iter_dir: Path, *, rep: int, execution_time_seconds: float):
    """Append a second repetition of the same APK, sharing the container's tasks.json.

    Built by copying the existing record so the two differ only in the fields under test —
    otherwise a test that passes could be passing on an unrelated difference.
    """
    base = iter_dir / "results" / "container_00" / "run_00"
    tasks_json = base / "tasks.json"
    payload = json.loads(tasks_json.read_text())
    extra = json.loads(json.dumps(payload["tasks"][0]))
    extra["config"]["repetition"] = rep
    extra["result"]["execution_time_seconds"] = execution_time_seconds
    payload["tasks"].append(extra)
    tasks_json.write_text(json.dumps(payload))

    # The second identity needs its own artifacts, or C3/C4 would condemn it for reasons
    # the test did not ask about.
    source_stem = f"{APK}__1__{TIMEOUT}__aperv:mop_on_llm_off"
    target_stem = f"{APK}__{rep}__{TIMEOUT}__aperv:mop_on_llm_off"
    apk_dir = base / APK
    for suffix in repair_tasks.ARTIFACT_SUFFIXES:
        source = apk_dir / f"{source_stem}.{suffix}"
        if source.exists():
            (apk_dir / f"{target_stem}.{suffix}").write_bytes(source.read_bytes())


class TestDryRunIsTheDefault:
    def test_findings_are_reported_and_nothing_is_written(self, tmp_path, capsys):
        iter_dir = build_tree(tmp_path, execution_time_seconds=1012.0)
        before = read_records(iter_dir)

        exit_code = repair_tasks.main(["--iter-dir", str(iter_dir)])

        assert exit_code == 1  # usable as a gate: findings exist and were not repaired
        assert read_records(iter_dir) == before
        assert not (tmp_path / "backup").exists()
        assert "C2" in capsys.readouterr().out

    def test_a_clean_tree_reports_nothing_and_exits_zero(self, tmp_path, capsys):
        # The regression test the script is run against the real tree for: once INV-APV-60
        # is in the tool, finding nothing is the expected outcome.
        exit_code = repair_tasks.main(["--iter-dir", str(build_tree(tmp_path))])

        assert exit_code == 0
        assert "nothing to repair" in capsys.readouterr().out


class TestApplyPreservesThenRewrites:
    def test_the_record_is_set_to_error_naming_the_criterion(self, tmp_path):
        iter_dir = build_tree(tmp_path, execution_time_seconds=1012.0)

        assert repair_tasks.main(["--iter-dir", str(iter_dir), "--apply"]) == 0

        (record,) = read_records(iter_dir)
        # The enum NAME, which is what TaskState[...] reads back.
        assert record["result"]["state"] == "ERROR"
        assert "C2" in record["result"]["error_message"]
        assert "1012" in record["result"]["error_message"]

    def test_artifacts_and_the_original_tasks_json_are_preserved_with_digests(
        self, tmp_path
    ):
        iter_dir = build_tree(tmp_path, execution_time_seconds=1012.0)
        original = (iter_dir / "results" / "container_00" / "run_00" / "tasks.json").read_bytes()

        repair_tasks.main(["--iter-dir", str(iter_dir), "--apply"])

        preserved = tmp_path / repair_tasks.DEFAULT_BACKUP_DIR / "container_00"
        names = {p.name for p in preserved.iterdir()}
        stem = f"{APK}__1__{TIMEOUT}__aperv:mop_on_llm_off"
        assert f"{stem}.logcat" in names
        assert f"{stem}.trace" in names
        assert "tasks.json.before-repair" in names
        assert "SHA256SUMS" in names

        # The copy is the record as it stood BEFORE the rewrite — that is the whole point.
        assert (preserved / "tasks.json.before-repair").read_bytes() == original

        # Every digest in SHA256SUMS re-computes against the file beside it.
        for line in (preserved / "SHA256SUMS").read_text().splitlines():
            digest, name = line.split("  ", 1)
            assert verify_sha(preserved / name) == digest

    def test_the_repaired_identity_re_scans_as_inadmissible_on_c1_not_c2(self, tmp_path):
        """After the repair the record declares its own failure, which is what a resume reads.

        The identity stays inadmissible — it has not been re-executed — but it now fails on
        C1 rather than only C2, which is the difference between a run that claims success
        and one that admits it did not happen.
        """
        iter_dir = build_tree(tmp_path, execution_time_seconds=1012.0)
        repair_tasks.main(["--iter-dir", str(iter_dir), "--apply"])

        (entry,) = verify.admissibility_by_identity(iter_dir).values()
        assert "C1" in [f["criterion"] for f in entry["failures"]]


class TestOnlyTheInadmissibleRecordIsTouched:
    def test_a_healthy_identity_in_the_same_file_is_left_alone(self, tmp_path):
        iter_dir = build_tree(tmp_path, execution_time_seconds=1012.0)
        add_second_identity(iter_dir, rep=2, execution_time_seconds=1872.0)

        repair_tasks.main(["--iter-dir", str(iter_dir), "--apply"])

        truncated, intact = read_records(iter_dir)
        assert truncated["result"]["state"] == "ERROR"
        assert intact["result"]["state"] == "COMPLETED"
        assert intact["result"]["error_message"] is None


def verify_sha(path: Path) -> str:
    return repair_tasks._sha256(path)
