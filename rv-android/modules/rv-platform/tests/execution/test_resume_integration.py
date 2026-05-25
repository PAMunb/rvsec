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
from unittest.mock import MagicMock, patch

from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task, TaskConfiguration, TaskState, ToolConfig
from rv_platform.components.result_processor import ResultProcessorComponent
from rv_platform.config.platform_config import PlatformConfig
from rv_platform.platform import Platform
from rv_platform.storage.task_storage import ExperimentMetadata, TaskStorage

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
