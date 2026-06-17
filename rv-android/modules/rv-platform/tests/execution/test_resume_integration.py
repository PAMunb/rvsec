"""
Integration tests for experiment resume functionality.

These tests exercise the REAL save→load→resume path without mocking
the storage layer. They verify that:
- tasks.json survives a full round-trip (save → load)
- A new Platform instance correctly skips previously-completed tasks
- Expanding experiments (increasing repetitions) only runs new tasks
- Config checksum persists across save/load
- Coverage CSV uses summary rows (not per-method) for resumed tasks
"""

import csv
import json
import os
import shutil
from unittest.mock import MagicMock, patch

from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task, TaskConfiguration, TaskState, ToolConfig
from rv_platform.components.result_processor import ResultProcessorComponent
from rv_platform.config.platform_config import PlatformConfig
from rv_platform.platform import Platform
from rv_platform.storage.task_storage import ExperimentMetadata, TaskStorage

_GH58_FIX = os.path.join(
    os.path.dirname(__file__), "..", "components", "fixtures", "gh58"
)


def _seed_completed_task(results_dir, apk_name, copy_json=True):
    """Build a COMPLETED task with a real logcat + co-located SA JSON on disk,
    laid out exactly as Task.initialize() + a live run would (so
    dirname(logcat_file) == results_dir/apk_name holds the JSON). The gh58
    fixture logcat carries 5 RVSEC-COV lines and 2 RVSEC error lines."""
    config = TaskConfiguration(
        apk_name=apk_name,
        repetition=1,
        timeout=300,
        tool_config=ToolConfig(name="monkey"),
    )
    task = Task(config)
    task.initialize(results_dir)  # sets results_dir == dirname(logcat_file)
    shutil.copy(os.path.join(_GH58_FIX, "sample_task.logcat"), task.result.logcat_file)
    if copy_json:
        shutil.copy(
            os.path.join(_GH58_FIX, "sample_apk.apk.json"),
            os.path.join(task.results_dir, apk_name + ".json"),
        )
    task.update_state(TaskState.RUNNING)
    task.result.execution_time_seconds = 60
    task.update_state(TaskState.COMPLETED)
    return task


def _summary_rows(results_dir):
    """Return summary.csv as a list of dicts keyed by header."""
    with open(os.path.join(results_dir, "summary.csv")) as f:
        reader = list(csv.reader(f))
    header = reader[0]
    return [dict(zip(header, row)) for row in reader[1:]]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_apks_dir(tmp_path, names=("app.apk",)):
    """Create a directory with fake APK files."""
    apks_dir = tmp_path / "apks"
    apks_dir.mkdir(exist_ok=True)
    for name in names:
        (apks_dir / name).write_bytes(b"PK\x03\x04")
    return str(apks_dir)


def _make_platform_config(
    apks_dir, results_dir, tools=None, repetitions=1, timeouts=None
):
    return PlatformConfig(
        apks_dir=apks_dir,
        tools=tools or [ToolConfig(name="monkey")],
        repetitions=repetitions,
        timeouts=timeouts or [300],
        results_dir=results_dir,
        no_window=True,
        log_level="WARNING",
    )


def _create_platform(config):
    """Create a Platform, patching App validation (fake APKs)."""
    with patch.object(App, "model_post_init", lambda self, ctx: None):
        return Platform(config)


def _simulate_task_execution(task):
    """Simulate a task being executed to completion."""
    task.update_state(TaskState.RUNNING)
    task.result.execution_time_seconds = 60
    task.result.coverage_metrics = {
        "method_coverage": 25.0,
        "activities_coverage": 50.0,
        "methods_mop_reachable_coverage": 10.0,
        "total_errors": 2,
        "total_method_calls": 5,
        "called_activities": 1,
        "called_methods": 3,
        "called_target_methods": 1,
    }
    task.update_state(TaskState.COMPLETED)


# ===========================================================================
# Round-trip: save → load → skip
# ===========================================================================


class TestSaveLoadResume:
    """Test the real save→load→skip cycle without mocking TaskStorage."""

    def test_completed_tasks_survive_save_load_and_are_skipped(self, tmp_path):
        """Full round-trip: generate tasks, complete some, save, create new
        Platform from same results_dir, verify completed tasks are skipped."""
        apks_dir = _create_apks_dir(tmp_path)
        results_dir = str(tmp_path / "results")

        # --- Session 1: run 2 repetitions, complete both ---
        config = _make_platform_config(apks_dir, results_dir, repetitions=2)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p1 = Platform(config)
            p1._generate_tasks()

        assert len(p1.tasks) == 2  # app.apk × monkey × 2 reps × 300s

        # Simulate completing both tasks
        for task in p1.tasks:
            _simulate_task_execution(task)
            p1.task_storage.update_task(task)

        # Store metadata (as Platform.run() would)
        config_dict = config.model_dump(mode="json")
        metadata = ExperimentMetadata.create_from_config(results_dir, config_dict)
        p1.task_storage.set_experiment_metadata(metadata)
        p1.task_storage.save()

        # Verify tasks.json exists
        tasks_file = os.path.join(results_dir, "tasks.json")
        assert os.path.isfile(tasks_file)

        # --- Session 2: same config, 2 reps — all should be skipped ---
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p2 = Platform(config)
            p2._generate_tasks()

        assert len(p2.tasks) == 2
        p2._skip_completed_tasks()

        assert len(p2.tasks) == 0, "All 2 tasks should be skipped on resume"
        assert p2._skipped_count == 2

    def test_only_completed_state_tasks_are_loaded_for_skipping(self, tmp_path):
        """ERROR tasks persisted in tasks.json do NOT cause skipping."""
        apks_dir = _create_apks_dir(tmp_path)
        results_dir = str(tmp_path / "results")

        config = _make_platform_config(apks_dir, results_dir, repetitions=2)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p1 = Platform(config)
            p1._generate_tasks()

        # Complete rep 1, fail rep 2
        _simulate_task_execution(p1.tasks[0])
        p1.task_storage.update_task(p1.tasks[0])

        p1.tasks[1].update_state(TaskState.RUNNING)
        p1.tasks[1].update_state(TaskState.ERROR, "emulator crash")
        p1.task_storage.update_task(p1.tasks[1])
        p1.task_storage.save()

        # Session 2: rep 1 skipped (COMPLETED), rep 2 remains (ERROR → re-execute)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p2 = Platform(config)
            p2._generate_tasks()

        p2._skip_completed_tasks()

        assert len(p2.tasks) == 1, "Only the ERROR task should remain"
        assert p2.tasks[0].config.repetition == 2
        assert p2._skipped_count == 1


# ===========================================================================
# Expand experiment
# ===========================================================================


class TestExpandExperiment:
    """Test expanding an experiment by increasing repetitions."""

    def test_expand_from_2_to_5_repetitions(self, tmp_path):
        """Run 2 reps first, then run with 5 reps — only reps 3-5 execute."""
        apks_dir = _create_apks_dir(tmp_path)
        results_dir = str(tmp_path / "results")

        # --- Session 1: 2 reps ---
        config1 = _make_platform_config(apks_dir, results_dir, repetitions=2)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p1 = Platform(config1)
            p1._generate_tasks()

        for task in p1.tasks:
            _simulate_task_execution(task)
            p1.task_storage.update_task(task)

        config_dict = config1.model_dump(mode="json")
        metadata = ExperimentMetadata.create_from_config(results_dir, config_dict)
        p1.task_storage.set_experiment_metadata(metadata)
        p1.task_storage.save()

        # --- Session 2: 5 reps (expand) ---
        config2 = _make_platform_config(apks_dir, results_dir, repetitions=5)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p2 = Platform(config2)
            p2._generate_tasks()

        assert len(p2.tasks) == 5  # all 5 generated
        p2._skip_completed_tasks()

        assert len(p2.tasks) == 3, "Only reps 3, 4, 5 should remain"
        remaining_reps = sorted(t.config.repetition for t in p2.tasks)
        assert remaining_reps == [3, 4, 5]
        assert p2._skipped_count == 2

    def test_expand_with_multiple_tools(self, tmp_path):
        """Expand with 2 tools × 2 APKs — identity matching is per-combination."""
        apks_dir = _create_apks_dir(tmp_path, names=("a.apk", "b.apk"))
        results_dir = str(tmp_path / "results")

        tools = [ToolConfig(name="monkey"), ToolConfig(name="droidbot")]

        # Session 1: 1 rep
        config1 = _make_platform_config(
            apks_dir, results_dir, tools=tools, repetitions=1
        )
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p1 = Platform(config1)
            p1._generate_tasks()

        # 2 APKs × 2 tools × 1 rep × 1 timeout = 4 tasks
        assert len(p1.tasks) == 4
        for task in p1.tasks:
            _simulate_task_execution(task)
            p1.task_storage.update_task(task)
        p1.task_storage.save()

        # Session 2: 3 reps — should generate 12, skip 4, run 8
        config2 = _make_platform_config(
            apks_dir, results_dir, tools=tools, repetitions=3
        )
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p2 = Platform(config2)
            p2._generate_tasks()

        assert len(p2.tasks) == 12
        p2._skip_completed_tasks()

        assert len(p2.tasks) == 8
        assert p2._skipped_count == 4
        # All remaining tasks should have rep > 1
        assert all(t.config.repetition > 1 for t in p2.tasks)


# ===========================================================================
# Config checksum persistence
# ===========================================================================


class TestChecksumPersistence:
    """Test that config checksum survives save→load."""

    def test_checksum_persists_across_save_load(self, tmp_path):
        """Checksum written by save() is recovered by load() in a new instance."""
        storage_file = str(tmp_path / "tasks.json")
        config_dict = {"tools": ["monkey"], "timeout": 300, "reps": 2}

        # Session 1: create metadata and save
        metadata = ExperimentMetadata.create_from_config("exp-1", config_dict)
        original_checksum = metadata.config_checksum

        s1 = TaskStorage(storage_file, experiment_metadata=metadata)
        s1.load()
        s1.add_task(_make_dummy_task())
        s1.save()

        # Session 2: load from file
        s2 = TaskStorage(storage_file)
        s2.load()

        assert s2.experiment_metadata is not None
        assert s2.experiment_metadata.config_checksum == original_checksum

    def test_continuation_compatibility_after_round_trip(self, tmp_path):
        """check_continuation_compatibility works with loaded checksum."""
        storage_file = str(tmp_path / "tasks.json")
        config_dict = {"tools": ["monkey"], "timeout": 300}

        metadata = ExperimentMetadata.create_from_config("exp-1", config_dict)
        s1 = TaskStorage(storage_file, experiment_metadata=metadata)
        s1.load()
        s1.add_task(_make_dummy_task())
        s1.save()

        # New instance loads and checks compatibility
        s2 = TaskStorage(storage_file)
        s2.load()
        assert s2.check_continuation_compatibility(config_dict) is True
        assert s2.check_continuation_compatibility({"tools": ["droidbot"]}) is False

    def test_config_change_warning_on_platform_resume(self, tmp_path):
        """Platform logs warning when config changes between sessions."""
        apks_dir = _create_apks_dir(tmp_path)
        results_dir = str(tmp_path / "results")

        # Session 1: monkey, 1 rep
        config1 = _make_platform_config(apks_dir, results_dir)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p1 = Platform(config1)
            p1._generate_tasks()

        _simulate_task_execution(p1.tasks[0])
        p1.task_storage.update_task(p1.tasks[0])
        config_dict = config1.model_dump(mode="json")
        metadata = ExperimentMetadata.create_from_config(results_dir, config_dict)
        p1.task_storage.set_experiment_metadata(metadata)
        p1.task_storage.save()

        # Session 2: different timeout (config changed)
        config2 = _make_platform_config(apks_dir, results_dir, timeouts=[600])
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p2 = Platform(config2)
            p2._generate_tasks()

        with patch.object(p2.logger, "warning") as mock_warn:
            p2._skip_completed_tasks()

        # Warning about config change must be logged
        warning_msgs = [c[0][0] for c in mock_warn.call_args_list]
        assert any(
            "Config changed" in msg for msg in warning_msgs
        ), f"Expected 'Config changed' warning. Got: {warning_msgs}"


def _make_dummy_task():
    """Create a minimal task for storage tests."""
    config = TaskConfiguration(
        apk_name="dummy.apk",
        repetition=1,
        timeout=60,
        tool_config=ToolConfig(name="monkey"),
    )
    return Task(config)


# ===========================================================================
# Coverage CSV for resumed tasks
# ===========================================================================


class TestCoverageCSVResumedTasks:
    """gh58/INV-PLT-15+16: resumed tasks reconstruct a populated repository from
    logcat + on-demand static-data re-parse. No "single summary row" fallback;
    per-method rows are emitted when logcat exists, zero rows when it does not."""

    def test_resumed_task_with_no_logcat_emits_no_rows(self, tmp_path):
        """When repository=None AND logcat is missing, the writer emits zero
        rows for the task (no fallback to stale serialized metrics)."""
        config = TaskConfiguration(
            apk_name="app.apk",
            repetition=1,
            timeout=300,
            tool_config=ToolConfig(name="monkey"),
        )
        task = Task(config)
        task.update_state(TaskState.RUNNING)
        task.result.execution_time_seconds = 60
        task.result.coverage_metrics = {
            "method_coverage": 25.0,
            "activities_coverage": 50.0,
            "methods_mop_reachable_coverage": 10.0,
        }
        task.update_state(TaskState.COMPLETED)
        task.repository = None
        task.result.logcat_file = ""  # missing → reconstruct returns None

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_coverage_csv([task])

        with open(os.path.join(results_dir, "coverage.csv")) as f:
            reader = list(csv.reader(f))
        # Header only — no data row from stale serialized metrics.
        assert len(reader) == 1

    def test_mixed_live_and_resumed_tasks(self, tmp_path):
        """Live task (with repository) gets per-method rows; resumed task
        without logcat gets zero rows. Total = header + per-method rows only."""
        live_repo = MagicMock()
        live_repo.get_method_calls.return_value = [
            {
                "signature": "void a()",
                "class_name": "A",
                "method_name": "a",
                "time": 1,
                "activity": "Main",
                "is_mop_method": False,
            },
            {
                "signature": "void b()",
                "class_name": "B",
                "method_name": "b",
                "time": 2,
                "activity": "Main",
                "is_mop_method": True,
            },
        ]
        live_repo.get_static_methods.return_value = [MagicMock()] * 10
        live_repo.get_static_activities.return_value = [MagicMock()] * 2
        live_repo.get_target_methods.return_value = [MagicMock()] * 5
        live_repo.calculate_metrics.return_value.to_dict.return_value = {
            "class_coverage": 20.0,
            "activity_coverage": 50.0,
            "method_coverage": 20.0,
            "reachable_method_coverage": 25.0,
            "mop_method_coverage": 20.0,
            "direct_mop_method_coverage": 0.0,
            "total_errors": 0,
            "unique_errors": 0,
        }

        live_config = TaskConfiguration(
            apk_name="live.apk",
            repetition=1,
            timeout=300,
            tool_config=ToolConfig(name="monkey"),
        )
        live_task = Task(live_config)
        live_task.update_state(TaskState.RUNNING)
        live_task.update_state(TaskState.COMPLETED)
        live_task.repository = live_repo

        resumed_config = TaskConfiguration(
            apk_name="resumed.apk",
            repetition=1,
            timeout=300,
            tool_config=ToolConfig(name="monkey"),
        )
        resumed_task = Task(resumed_config)
        resumed_task.update_state(TaskState.RUNNING)
        resumed_task.update_state(TaskState.COMPLETED)
        resumed_task.repository = None
        resumed_task.result.logcat_file = ""  # missing → no rows

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([live_task, resumed_task], results_dir)
        processor._generate_coverage_csv([live_task, resumed_task])

        with open(os.path.join(results_dir, "coverage.csv")) as f:
            reader = list(csv.reader(f))

        # header + 2 per-method rows (live only) — resumed contributes nothing
        # because its logcat is missing.
        assert len(reader) == 3
        live_rows = [r for r in reader[1:] if r[0] == "live.apk"]
        resumed_rows = [r for r in reader[1:] if r[0] == "resumed.apk"]
        assert len(live_rows) == 2
        assert len(resumed_rows) == 0


# ===========================================================================
# Result consolidation across sessions
# ===========================================================================


class TestResultConsolidationIntegration:
    """Verify that _process_results() uses ALL completed tasks from
    TaskStorage (previous + current session) for unified CSV/JSON generation."""

    def test_process_results_consolidates_all_sessions(self, tmp_path):
        """Session 1 completes rep 1, Session 2 completes rep 2 — both
        appear in the final summary.csv."""
        apks_dir = _create_apks_dir(tmp_path)
        results_dir = str(tmp_path / "results")

        # Session 1: complete rep 1
        config = _make_platform_config(apks_dir, results_dir, repetitions=2)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p1 = Platform(config)
            p1._generate_tasks()

        _simulate_task_execution(p1.tasks[0])
        p1.task_storage.update_task(p1.tasks[0])
        p1.task_storage.save()

        # Session 2: complete rep 2
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            p2 = Platform(config)
            p2._generate_tasks()

        p2._skip_completed_tasks()
        assert len(p2.tasks) == 1  # only rep 2 remains
        assert p2.tasks[0].config.repetition == 2

        # Simulate completing rep 2
        _simulate_task_execution(p2.tasks[0])
        p2.task_storage.update_task(p2.tasks[0])

        # Process results — should include both reps
        p2._process_results()

        # Verify summary.csv has 2 rows (one per rep)
        summary_path = os.path.join(results_dir, "summary.csv")
        assert os.path.isfile(summary_path)
        with open(summary_path) as f:
            reader = list(csv.reader(f))
        # header + 2 data rows
        assert len(reader) == 3, f"Expected 3 rows (header + 2 reps), got {len(reader)}"

        # Verify results.json has both reps
        results_path = os.path.join(results_dir, "results.json")
        with open(results_path) as f:
            data = json.load(f)
        reps = data["app.apk"]["repetitions"]
        assert "1" in reps, "Rep 1 from session 1 must be in results.json"
        assert "2" in reps, "Rep 2 from session 2 must be in results.json"


# ===========================================================================
# gh65: resume static-data resolution gates (G2/G3/G4/G6)
# ===========================================================================


class TestGh65TwoSessionResume:
    """G2/G6: a task completed in session 1 and reloaded via real
    Task.from_dict (results_dir="") MUST reconstruct non-zero coverage and
    correct MOP errors when consolidated alongside a session-2 task."""

    def test_e2e_two_session_resume(self, tmp_path):
        results_dir = str(tmp_path / "results")
        os.makedirs(results_dir, exist_ok=True)
        storage_file = os.path.join(results_dir, "tasks.json")

        # --- Session 1: complete task A, persist to tasks.json ---
        task_a = _seed_completed_task(results_dir, "appA.apk", copy_json=True)
        s1 = TaskStorage(storage_file)
        s1.load()
        s1.add_task(task_a)
        s1.update_task(task_a)
        s1.save()

        # --- Session 2: reload A from disk (real from_dict), add task B ---
        s2 = TaskStorage(storage_file)
        s2.load()
        completed = s2.get_completed_tasks()
        assert len(completed) == 1
        revived_a = completed[0]
        # The genuine resume precondition this gate defends.
        assert revived_a.results_dir == ""
        assert revived_a.app is None

        task_b = _seed_completed_task(results_dir, "appB.apk", copy_json=True)
        s2.add_task(task_b)
        s2.update_task(task_b)
        s2.save()

        all_completed = s2.get_completed_tasks()
        assert len(all_completed) == 2

        processor = ResultProcessorComponent(all_completed, results_dir)
        processor.execute({})

        rows = {r["apk"]: r for r in _summary_rows(results_dir)}
        assert set(rows) == {"appA.apk", "appB.apk"}

        # G2: specifically the RESUMED row A must be non-zeroed.
        assert float(rows["appA.apk"]["cov_method"]) > 0
        assert int(rows["appA.apk"]["mop_errors_total"]) == 2
        assert float(rows["appB.apk"]["cov_method"]) > 0
        assert int(rows["appB.apk"]["mop_errors_total"]) == 2

        # G6 canary: 100% of RVSEC-COV tasks have cov_method > 0.
        with_cov = [r for r in rows.values()]
        assert all(float(r["cov_method"]) > 0 for r in with_cov)


class TestGh65ConsolidationOnly:
    """G3/G6: a pure consolidation pass where ALL tasks are loaded from disk
    (the path that zeroed T=300) MUST produce correct CSVs for 100% of rows."""

    def test_consolidation_only_all_tasks_from_disk(self, tmp_path):
        results_dir = str(tmp_path / "results")
        os.makedirs(results_dir, exist_ok=True)
        storage_file = os.path.join(results_dir, "tasks.json")

        s1 = TaskStorage(storage_file)
        s1.load()
        for name in ("a.apk", "b.apk", "c.apk"):
            t = _seed_completed_task(results_dir, name, copy_json=True)
            s1.add_task(t)
            s1.update_task(t)
        s1.save()

        # Fresh storage: every task arrives via from_dict (results_dir="").
        s2 = TaskStorage(storage_file)
        s2.load()
        completed = s2.get_completed_tasks()
        assert len(completed) == 3
        assert all(t.results_dir == "" for t in completed)

        processor = ResultProcessorComponent(completed, results_dir)
        processor.execute({})

        rows = _summary_rows(results_dir)
        assert len(rows) == 3
        # G6: 100% of rows non-zeroed.
        assert all(float(r["cov_method"]) > 0 for r in rows)
        assert all(int(r["mop_errors_total"]) == 2 for r in rows)


class TestGh65ResumeHealthCheck:
    """G4/INV-PLT-18: when ≥1 resumed task has a logcat but no resolvable SA
    JSON, exactly one aggregate WARNING fires with the exact N/M count; silent
    when N == 0."""

    def test_warning_fires_with_exact_count(self, tmp_path, caplog):
        import logging

        results_dir = str(tmp_path / "results")
        os.makedirs(results_dir, exist_ok=True)
        storage_file = os.path.join(results_dir, "tasks.json")

        s1 = TaskStorage(storage_file)
        s1.load()
        # 2 resolvable + 1 with JSON absent → N/M = 1/3.
        seeded = [
            _seed_completed_task(results_dir, "ok1.apk", copy_json=True),
            _seed_completed_task(results_dir, "ok2.apk", copy_json=True),
            _seed_completed_task(results_dir, "bad.apk", copy_json=False),
        ]
        for t in seeded:
            s1.add_task(t)
            s1.update_task(t)
        s1.save()

        s2 = TaskStorage(storage_file)
        s2.load()
        completed = s2.get_completed_tasks()
        processor = ResultProcessorComponent(completed, results_dir)

        with caplog.at_level(logging.WARNING):
            processor.execute({})

        health = [
            r.getMessage()
            for r in caplog.records
            if "Resume coverage health" in r.getMessage()
        ]
        assert len(health) == 1
        assert "1/3" in health[0]
        assert len(processor._unresolved_task_ids) == 1

        # The unresolved task still has accurate MOP errors; coverage zeroed.
        rows = {r["apk"]: r for r in _summary_rows(results_dir)}
        assert float(rows["bad.apk"]["cov_method"]) == 0
        assert int(rows["bad.apk"]["mop_errors_total"]) == 2
        assert float(rows["ok1.apk"]["cov_method"]) > 0

    def test_no_warning_when_all_resolved(self, tmp_path, caplog):
        import logging

        results_dir = str(tmp_path / "results")
        os.makedirs(results_dir, exist_ok=True)
        storage_file = os.path.join(results_dir, "tasks.json")

        s1 = TaskStorage(storage_file)
        s1.load()
        for t in (
            _seed_completed_task(results_dir, "ok1.apk", copy_json=True),
            _seed_completed_task(results_dir, "ok2.apk", copy_json=True),
        ):
            s1.add_task(t)
            s1.update_task(t)
        s1.save()

        s2 = TaskStorage(storage_file)
        s2.load()
        processor = ResultProcessorComponent(s2.get_completed_tasks(), results_dir)

        with caplog.at_level(logging.WARNING):
            processor.execute({})

        health = [
            r.getMessage()
            for r in caplog.records
            if "Resume coverage health" in r.getMessage()
        ]
        assert health == []
        assert len(processor._unresolved_task_ids) == 0


class TestGh65StandaloneProcessResults:
    """G8 case 5 (consolidation-only) at the CLI layer: `rv-platform run
    --process-results <dir>` loads ALL tasks from tasks.json (via from_dict,
    results_dir="") and regenerates correct CSVs. Locks the fix to
    `_process_results_standalone` (it passed the directory to TaskStorage and
    never called load(), so it always found zero tasks)."""

    def test_process_results_standalone_consolidates_from_disk(self, tmp_path):
        from rv_platform.__main__ import _process_results_standalone

        results_dir = str(tmp_path / "results")
        os.makedirs(results_dir, exist_ok=True)
        storage_file = os.path.join(results_dir, "tasks.json")

        s = TaskStorage(storage_file)
        s.load()
        for name in ("a.apk", "b.apk"):
            t = _seed_completed_task(results_dir, name, copy_json=True)
            s.add_task(t)
            s.update_task(t)
        s.save()

        rc = _process_results_standalone(results_dir)
        assert rc == 0

        rows = _summary_rows(results_dir)
        assert len(rows) == 2
        assert all(float(r["cov_method"]) > 0 for r in rows)
        assert all(int(r["mop_errors_total"]) == 2 for r in rows)
