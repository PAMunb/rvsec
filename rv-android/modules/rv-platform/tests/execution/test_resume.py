# tests/execution/test_resume.py
"""
Unit tests for Platform resume functionality.

Tests U1-U10 from the resume-docker change design.md Testing Strategy.
Tests U1-U6 and U10 verify already-implemented behavior and should pass.
Tests U7-U9 verify the result consolidation fix (task 7).
Tests U15-U17 verify MOP violation reconstruction from logcat (task 10).
"""

import csv
import json
import os
from unittest.mock import MagicMock, patch, call

import pytest

from rv_android_core.domain.app import App
from rv_android_core.domain.task import (
    Task,
    TaskConfiguration,
    TaskFactory,
    TaskState,
    ToolConfig,
)
from rv_platform.components.result_processor import ResultProcessorComponent
from rv_platform.config.platform_config import PlatformConfig
from rv_platform.platform import Platform
from rv_platform.storage.task_storage import ExperimentMetadata, TaskStorage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task_config(
    apk="test.apk", tool="monkey", variant="default", rep=1, timeout=60
):
    """Create a TaskConfiguration with the given identity fields."""
    tool_config = ToolConfig(name=tool, variant=variant, parameters={})
    return TaskConfiguration(
        apk_name=apk,
        repetition=rep,
        timeout=timeout,
        tool_config=tool_config,
    )


def _make_completed_task(
    apk="test.apk", tool="monkey", variant="default", rep=1, timeout=60
):
    """Create a Task in COMPLETED state with coverage_metrics populated."""
    config = _make_task_config(apk, tool, variant, rep, timeout)
    task = Task(config)
    app = MagicMock(spec=App)
    app.name = apk
    app.package_name = "com.test"
    task.set_app(app)
    task.initialize("/tmp/fake_results")
    # Simulate execution
    task.update_state(TaskState.RUNNING)
    task.update_state(TaskState.COMPLETED)
    task.result.coverage_metrics = {
        "method_coverage": 0.0,
        "activities_coverage": 0.0,
        "methods_jca_reachable_coverage": 0.0,
        "total_errors": 0,
        "total_method_calls": 0,
    }
    return task


def _make_error_task(
    apk="test.apk", tool="monkey", variant="default", rep=1, timeout=60
):
    """Create a Task in ERROR state."""
    config = _make_task_config(apk, tool, variant, rep, timeout)
    task = Task(config)
    app = MagicMock(spec=App)
    app.name = apk
    app.package_name = "com.test"
    task.set_app(app)
    task.initialize("/tmp/fake_results")
    task.update_state(TaskState.RUNNING)
    task.update_state(TaskState.ERROR, "some error")
    return task


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def apks_dir(tmp_path):
    """Create a temporary directory with a fake APK file."""
    apk_file = tmp_path / "test.apk"
    apk_file.write_bytes(b"fake apk")
    return str(tmp_path)


@pytest.fixture
def results_dir(tmp_path):
    """Create a temporary results directory."""
    results = tmp_path / "results"
    results.mkdir()
    return str(results)


@pytest.fixture
def platform_config(apks_dir, results_dir):
    """Create a minimal PlatformConfig for testing."""
    return PlatformConfig(
        apks_dir=apks_dir,
        tools=[ToolConfig(name="monkey")],
        repetitions=5,
        timeouts=[60],
        results_dir=results_dir,
        no_window=True,
        log_level="INFO",
    )


@pytest.fixture
def platform(platform_config):
    """Create a Platform instance with mocked external dependencies."""
    with patch.object(Platform, "_discover_apks") as mock_discover:
        # Return a fake APK path so _generate_tasks works
        mock_discover.return_value = []
        p = Platform(platform_config)
    return p


# ---------------------------------------------------------------------------
# U1: _skip_completed_tasks filters by identity
# ---------------------------------------------------------------------------


class TestSkipCompletedTasks:

    def test_skip_completed_tasks_filters_by_identity(self, platform):
        """U1: Tasks whose identity matches a completed task are removed."""
        # Populate platform.tasks with 5 tasks (reps 1-5)
        platform.tasks = []
        for rep in range(1, 6):
            config = _make_task_config(rep=rep)
            task = Task(config)
            platform.tasks.append(task)

        # Mock TaskStorage to return 2 completed tasks (reps 1 and 2)
        completed = [
            _make_completed_task(rep=1),
            _make_completed_task(rep=2),
        ]
        platform.task_storage.get_completed_tasks = MagicMock(return_value=completed)
        platform.task_storage.check_continuation_compatibility = MagicMock(
            return_value=True
        )

        platform._skip_completed_tasks()

        # 3 tasks should remain (reps 3, 4, 5)
        assert len(platform.tasks) == 3
        remaining_reps = {t.config.repetition for t in platform.tasks}
        assert remaining_reps == {3, 4, 5}

    def test_skip_completed_tasks_stores_skipped_count(self, platform):
        """U2: _skipped_count stores the number of skipped tasks."""
        platform.tasks = []
        for rep in range(1, 6):
            config = _make_task_config(rep=rep)
            task = Task(config)
            platform.tasks.append(task)

        completed = [
            _make_completed_task(rep=1),
            _make_completed_task(rep=2),
            _make_completed_task(rep=3),
        ]
        platform.task_storage.get_completed_tasks = MagicMock(return_value=completed)
        platform.task_storage.check_continuation_compatibility = MagicMock(
            return_value=True
        )

        platform._skip_completed_tasks()

        # _skipped_count should exist and be 3
        assert hasattr(
            platform, "_skipped_count"
        ), "Platform must have _skipped_count attribute after _skip_completed_tasks()"
        assert platform._skipped_count == 3

    def test_skip_completed_tasks_does_not_skip_error_tasks(self, platform):
        """U3: Tasks with ERROR state are NOT skipped — they re-execute."""
        platform.tasks = []
        for rep in range(1, 4):
            config = _make_task_config(rep=rep)
            task = Task(config)
            platform.tasks.append(task)

        # TaskStorage returns ERROR tasks (not COMPLETED)
        # get_completed_tasks only returns COMPLETED, so ERROR tasks won't appear
        platform.task_storage.get_completed_tasks = MagicMock(return_value=[])

        platform._skip_completed_tasks()

        # All 3 tasks remain (nothing was skipped)
        assert len(platform.tasks) == 3

    def test_skip_completed_tasks_checksum_mismatch_warns(self, platform):
        """U4: Config checksum mismatch logs a warning but still skips."""
        platform.tasks = []
        for rep in range(1, 3):
            config = _make_task_config(rep=rep)
            task = Task(config)
            platform.tasks.append(task)

        completed = [_make_completed_task(rep=1)]
        platform.task_storage.get_completed_tasks = MagicMock(return_value=completed)
        platform.task_storage.check_continuation_compatibility = MagicMock(
            return_value=False
        )

        with patch.object(platform.logger, "warning") as mock_warn:
            platform._skip_completed_tasks()

        # Task was still skipped despite mismatch
        assert len(platform.tasks) == 1
        assert platform.tasks[0].config.repetition == 2

        # Warning was logged
        mock_warn.assert_called()
        warning_msg = mock_warn.call_args[0][0]
        assert "Config changed" in warning_msg or "config" in warning_msg.lower()

    def test_skip_completed_tasks_checksum_match_no_warning(self, platform):
        """U5: Config checksum match does not log a warning."""
        platform.tasks = []
        for rep in range(1, 3):
            config = _make_task_config(rep=rep)
            task = Task(config)
            platform.tasks.append(task)

        completed = [_make_completed_task(rep=1)]
        platform.task_storage.get_completed_tasks = MagicMock(return_value=completed)
        platform.task_storage.check_continuation_compatibility = MagicMock(
            return_value=True
        )

        with patch.object(platform.logger, "warning") as mock_warn:
            platform._skip_completed_tasks()

        # No config mismatch warning (resume info log is fine, but not a warning)
        for c in mock_warn.call_args_list:
            msg = c[0][0]
            assert "Config changed" not in msg


# ---------------------------------------------------------------------------
# U6: ExperimentMetadata creation
# ---------------------------------------------------------------------------


class TestMetadataCreation:

    def test_metadata_created_after_task_generation(self, platform):
        """U6: Platform.run() creates ExperimentMetadata with correct checksum."""
        # We mock everything except metadata creation
        platform.tasks = []
        platform._generate_tasks = MagicMock()
        platform._skip_completed_tasks = MagicMock()
        platform._execute_tasks = MagicMock(return_value=[])
        platform._process_results = MagicMock()
        platform.task_storage.set_experiment_metadata = MagicMock()

        platform.run()

        # Verify set_experiment_metadata was called
        platform.task_storage.set_experiment_metadata.assert_called_once()

        # Verify the metadata has a valid checksum
        metadata = platform.task_storage.set_experiment_metadata.call_args[0][0]
        assert isinstance(metadata, ExperimentMetadata)
        assert len(metadata.config_checksum) == 64  # SHA-256 hex digest
        assert metadata.experiment_id == platform.config.results_dir


# ---------------------------------------------------------------------------
# U7-U9: Result consolidation (EXPECTED TO FAIL before fix)
# ---------------------------------------------------------------------------


class TestResultConsolidation:

    def test_process_results_uses_all_completed_tasks(self, platform):
        """U7: _process_results() passes all completed tasks from TaskStorage,
        not just the filtered self.tasks.

        EXPECTED TO FAIL before the result consolidation fix (task 7.3).
        """
        # Simulate resume: self.tasks only has 1 task (the one executed this session)
        session_task = _make_completed_task(rep=2)
        platform.tasks = [session_task]

        # TaskStorage has 3 completed tasks (2 from previous + 1 from this session)
        all_completed = [
            _make_completed_task(rep=1),
            session_task,
            _make_completed_task(rep=3),
        ]
        platform.task_storage.get_completed_tasks = MagicMock(
            return_value=all_completed
        )

        with patch("rv_platform.platform.ResultProcessorComponent") as MockProcessor:
            mock_instance = MagicMock()
            MockProcessor.return_value = mock_instance

            platform._process_results()

            # ResultProcessorComponent should receive ALL 3 completed tasks
            MockProcessor.assert_called_once()
            tasks_passed = MockProcessor.call_args[0][0]
            assert (
                len(tasks_passed) == 3
            ), f"Expected 3 tasks passed to ResultProcessorComponent, got {len(tasks_passed)}"

    def test_generate_summary_includes_skipped_count(self, platform):
        """U8: _generate_summary() includes skipped_tasks in the summary dict.

        EXPECTED TO FAIL before the result consolidation fix (task 7.4).
        """
        results = [
            {
                "task_id": "1",
                "success": True,
                "execution_time": 60,
                "error_message": None,
            },
            {
                "task_id": "2",
                "success": True,
                "execution_time": 55,
                "error_message": None,
            },
        ]

        # After fix, _generate_summary accepts skipped_count parameter
        summary = platform._generate_summary(results, skipped_count=3)

        assert "skipped_tasks" in summary, "Summary must include 'skipped_tasks' field"
        assert summary["skipped_tasks"] == 3

    def test_generate_summary_total_includes_skipped(self, platform):
        """U9: Summary correctly reflects total experiment scope.

        EXPECTED TO FAIL before the result consolidation fix (task 7.4).
        """
        results = [
            {
                "task_id": "1",
                "success": True,
                "execution_time": 60,
                "error_message": None,
            },
        ]

        summary = platform._generate_summary(results, skipped_count=2)

        # total_tasks should reflect executed tasks (1) — the skipped count
        # is reported separately for backward compatibility
        assert summary["total_tasks"] == 1
        assert summary["skipped_tasks"] == 2


# ---------------------------------------------------------------------------
# U10: No resume scenario
# ---------------------------------------------------------------------------


class TestNoResume:

    def test_no_resume_skipped_count_zero(self, platform):
        """U10: When no tasks are skipped, _skipped_count is 0."""
        platform.tasks = []
        for rep in range(1, 4):
            config = _make_task_config(rep=rep)
            task = Task(config)
            platform.tasks.append(task)

        # No completed tasks in storage
        platform.task_storage.get_completed_tasks = MagicMock(return_value=[])

        platform._skip_completed_tasks()

        # All tasks remain
        assert len(platform.tasks) == 3

        # skipped_count should be 0 (or not set, depending on implementation)
        skipped = getattr(platform, "_skipped_count", 0)
        assert skipped == 0


# ---------------------------------------------------------------------------
# Sample logcat data for U15-U17
# ---------------------------------------------------------------------------

# Realistic logcat lines with RVSEC entries (MOP violations).
# Format: MM-DD HH:MM:SS.mmm  PID  TID LEVEL TAG: message
SAMPLE_LOGCAT_WITH_RVSEC = """\
02-12 10:00:01.000  1234  5678 V RVSEC  : MessageDigest_1,java.security.MessageDigest,init,update,MessageDigest_1.java:10,MessageDigest_1,Missing update call before digest
02-12 10:00:02.000  1234  5678 V RVSEC-COV: <java.security.MessageDigest: java.security.MessageDigest getInstance(java.lang.String)>
02-12 10:00:03.500  1234  5678 V RVSEC  : Cipher_1,javax.crypto.Cipher,init,doFinal,Cipher_1.java:15,Cipher_1,Cipher not initialized before doFinal
02-12 10:00:04.000  1234  5678 I ActivityManager: Displayed com.test/.MainActivity
02-12 10:00:05.000  1234  5678 V RVSEC-COV: <javax.crypto.Cipher: javax.crypto.Cipher getInstance(java.lang.String)>
"""

SAMPLE_LOGCAT_NO_RVSEC = """\
02-12 10:00:01.000  1234  5678 I ActivityManager: Displayed com.test/.MainActivity
02-12 10:00:02.000  1234  5678 D dalvikvm: GC_CONCURRENT freed 1024K
"""


def _make_loaded_task_with_logcat(
    logcat_path, apk="test.apk", tool="monkey", variant="default", rep=1, timeout=60
):
    """Create a task that simulates being loaded from tasks.json on resume.

    Key characteristics:
    - repository is None (runtime-only, not serialized)
    - result.logcat_file points to a real file on disk
    - result.coverage_metrics has summary-level data
    - state is COMPLETED
    """
    config = _make_task_config(apk, tool, variant, rep, timeout)
    task = Task(config)
    app = MagicMock(spec=App)
    app.name = apk
    app.package_name = "com.test"
    task.set_app(app)
    task.initialize("/tmp/fake_results")
    task.update_state(TaskState.RUNNING)
    task.update_state(TaskState.COMPLETED)
    task.result.logcat_file = logcat_path
    task.result.coverage_metrics = {
        "method_coverage": 25.0,
        "activities_coverage": 50.0,
        "methods_jca_reachable_coverage": 10.0,
        "total_errors": 2,
        "total_method_calls": 5,
        "called_activities": 1,
        "called_methods": 2,
        "called_mop_methods": 1,
        "mop_coverage": 10.0,
    }
    # Simulate loaded from tasks.json: repository is None
    task.repository = None
    return task


# ---------------------------------------------------------------------------
# U15-U17: MOP violation reconstruction from logcat
# ---------------------------------------------------------------------------


class TestLogcatReconstruction:

    def test_result_processor_reconstructs_violations_from_logcat(self, tmp_path):
        """U15: ResultProcessorComponent reconstructs MOP violations from logcat
        file when task.repository is None.

        Creates a mock task loaded from tasks.json (repository=None) with a
        logcat file containing RVSEC entries. After execute(), errors.csv must
        have MOP violation rows.
        """
        # Create a logcat file with RVSEC entries
        logcat_file = tmp_path / "test__1__60__monkey.logcat"
        logcat_file.write_text(SAMPLE_LOGCAT_WITH_RVSEC)

        # Create a task simulating resume (loaded from tasks.json)
        task = _make_loaded_task_with_logcat(str(logcat_file))

        # Create ResultProcessorComponent and execute
        results_dir = str(tmp_path / "output")
        os.makedirs(results_dir, exist_ok=True)
        processor = ResultProcessorComponent([task], results_dir)
        processor.execute({})

        # Read errors.csv and verify MOP violation rows
        errors_file = os.path.join(results_dir, "errors.csv")
        assert os.path.exists(errors_file), "errors.csv must be generated"

        with open(errors_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert (
            len(rows) >= 2
        ), f"errors.csv must have at least 2 MOP violation rows (from RVSEC entries), got {len(rows)}"

        # Verify the violations have expected fields
        first_row = rows[0]
        assert first_row["apk"] == "test.apk"
        assert first_row["spec"] != "", "spec field must not be empty"
        assert first_row["message"] != "", "message field must not be empty"

    def test_result_processor_handles_missing_logcat(self, tmp_path):
        """U16: Graceful handling when logcat file does not exist.

        Creates a mock task with repository=None and logcat_file pointing to
        a non-existent path. errors.csv must have no rows for that task,
        and a warning must be logged.
        """
        # Point to a non-existent logcat file
        missing_logcat = str(tmp_path / "nonexistent.logcat")

        task = _make_loaded_task_with_logcat(missing_logcat)

        results_dir = str(tmp_path / "output")
        os.makedirs(results_dir, exist_ok=True)
        processor = ResultProcessorComponent([task], results_dir)

        with patch.object(processor.logger, "warning") as mock_warn:
            processor.execute({})

        # Read errors.csv — should have header only (no data rows)
        errors_file = os.path.join(results_dir, "errors.csv")
        assert os.path.exists(errors_file), "errors.csv must be generated"

        with open(errors_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert (
            len(rows) == 0
        ), f"errors.csv must have no rows for task with missing logcat, got {len(rows)}"

        # Verify warning was logged about missing logcat
        warning_messages = [c[0][0] for c in mock_warn.call_args_list]
        logcat_warning = any(
            "logcat" in msg.lower() or "No logcat" in msg for msg in warning_messages
        )
        assert (
            logcat_warning
        ), f"Warning about missing logcat must be logged. Warnings: {warning_messages}"

    def test_result_processor_json_includes_violation_details_from_logcat(
        self, tmp_path
    ):
        """U17: results.json contains MOP violation details reconstructed
        from logcat when task.repository is None.

        Verifies that monitored_operations_errors has correct total, messages,
        and details fields.
        """
        logcat_file = tmp_path / "test__1__60__monkey.logcat"
        logcat_file.write_text(SAMPLE_LOGCAT_WITH_RVSEC)

        task = _make_loaded_task_with_logcat(str(logcat_file))

        results_dir = str(tmp_path / "output")
        os.makedirs(results_dir, exist_ok=True)
        processor = ResultProcessorComponent([task], results_dir)
        processor.execute({})

        # Read results.json and verify violation details
        results_file = os.path.join(results_dir, "results.json")
        assert os.path.exists(results_file), "results.json must be generated"

        with open(results_file, "r") as f:
            results_data = json.load(f)

        # Navigate the hierarchical structure to find the task data
        assert (
            "test.apk" in results_data
        ), f"results.json must have test.apk entry. Keys: {list(results_data.keys())}"

        tool_data = results_data["test.apk"]["repetitions"]["1"]["timeouts"]["60"][
            "tools"
        ]["monkey"]

        mop_errors = tool_data["monitored_operations_errors"]
        assert (
            mop_errors["total"] >= 2
        ), f"monitored_operations_errors.total must be >= 2, got {mop_errors['total']}"
        assert (
            len(mop_errors["messages"]) >= 2
        ), f"monitored_operations_errors.messages must have >= 2 entries"
        assert (
            len(mop_errors["details"]) >= 2
        ), f"monitored_operations_errors.details must have >= 2 entries"
