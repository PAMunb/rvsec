"""
Tests for Platform — task generation, APK discovery, resume (skip completed),
error message extraction, and summary generation.
"""

from unittest.mock import patch

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task, TaskConfiguration, TaskState, ToolConfig
from rv_android_core.util.error.exceptions import (
    RVToolExecutionError,
    RVToolTimeoutError,
)
from rv_platform.config.platform_config import PlatformConfig
from rv_platform.platform import Platform

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_apks(tmp_path, names=("app1.apk", "app2.apk")):
    """Create fake APK files and return the directory path."""
    apks_dir = tmp_path / "apks"
    apks_dir.mkdir(exist_ok=True)
    for name in names:
        (apks_dir / name).write_bytes(b"PK\x03\x04")  # minimal ZIP header
    return str(apks_dir)


def _make_platform(tmp_path, tools=None, repetitions=1, timeouts=None, apk_names=None):
    """Create a Platform with test config, patching App to skip APK validation."""
    apk_names = apk_names or ("app.apk",)
    apks_dir = _create_apks(tmp_path, apk_names)
    results_dir = str(tmp_path / "results")

    config = PlatformConfig(
        apks_dir=apks_dir,
        tools=tools or [ToolConfig(name="monkey")],
        repetitions=repetitions,
        timeouts=timeouts or [300],
        results_dir=results_dir,
        no_window=True,
        log_level="WARNING",
    )
    # Patch App to skip APK validation (fake files are not real APKs)
    with patch.object(App, "model_post_init", lambda self, ctx: None):
        platform = Platform(config)
    return platform


# ===========================================================================
# Task Generation
# ===========================================================================


class TestGenerateTasks:
    def test_generates_tasks_for_all_combinations(self, tmp_path):
        """Tasks = APKs × tools × repetitions × timeouts."""
        platform = _make_platform(
            tmp_path,
            tools=[ToolConfig(name="monkey"), ToolConfig(name="droidbot")],
            repetitions=2,
            timeouts=[300, 600],
            apk_names=("a.apk", "b.apk"),
        )
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            platform._generate_tasks()
        # 2 APKs × 2 tools × 2 reps × 2 timeouts = 16
        assert len(platform.tasks) == 16

    def test_task_config_fields_are_correct(self, tmp_path):
        """Verify that generated task configs carry the right values."""
        platform = _make_platform(
            tmp_path,
            tools=[ToolConfig(name="ape", variant="sata_mop")],
            repetitions=1,
            timeouts=[120],
        )
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            platform._generate_tasks()
        assert len(platform.tasks) == 1
        task = platform.tasks[0]
        assert task.config.apk_name == "app.apk"
        assert task.config.tool_config.name == "ape"
        assert task.config.tool_config.variant == "sata_mop"
        assert task.config.repetition == 1
        assert task.config.timeout == 120

    def test_tasks_have_app_set(self, tmp_path):
        """Each generated task must have an App instance."""
        platform = _make_platform(tmp_path)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            platform._generate_tasks()
        for task in platform.tasks:
            assert task.app is not None


# ===========================================================================
# APK Discovery
# ===========================================================================


class TestDiscoverApks:
    def test_discovers_apk_files(self, tmp_path):
        platform = _make_platform(tmp_path, apk_names=("a.apk", "b.apk", "c.apk"))
        apks = platform._discover_apks()
        assert len(apks) == 3

    def test_raises_on_empty_directory(self, tmp_path):
        """No APK files → ValueError during Platform initialization."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        config = PlatformConfig(
            apks_dir=str(empty_dir),
            tools=[ToolConfig(name="monkey")],
            results_dir=str(tmp_path / "results"),
        )
        with pytest.raises(ValueError, match="No APK files found"):
            Platform(config)

    def test_filter_file_restricts_apks(self, tmp_path):
        """Only APKs listed in filter file are returned."""
        platform = _make_platform(tmp_path, apk_names=("a.apk", "b.apk", "c.apk"))
        filter_file = tmp_path / "filter.txt"
        filter_file.write_text("a.apk\nc.apk\n")
        platform.config.apks_filter_file = str(filter_file)
        apks = platform._discover_apks()
        assert len(apks) == 2
        names = {a.name for a in apks}
        assert names == {"a.apk", "c.apk"}

    def test_filter_file_no_matches_raises(self, tmp_path):
        """Filter file with no matching APKs → ValueError."""
        platform = _make_platform(tmp_path, apk_names=("a.apk",))
        filter_file = tmp_path / "filter.txt"
        filter_file.write_text("nonexistent.apk\n")
        platform.config.apks_filter_file = str(filter_file)
        with pytest.raises(ValueError, match="No APKs match filter"):
            platform._discover_apks()

    def test_results_are_sorted(self, tmp_path):
        platform = _make_platform(tmp_path, apk_names=("c.apk", "a.apk", "b.apk"))
        apks = platform._discover_apks()
        names = [a.name for a in apks]
        assert names == ["a.apk", "b.apk", "c.apk"]


# ===========================================================================
# Skip Completed Tasks (Resume)
# ===========================================================================


class TestSkipCompletedTasks:
    def _add_completed_to_storage(self, platform, apk, tool, rep, timeout):
        """Simulate a task completed in a previous run (in TaskStorage)."""
        config = TaskConfiguration(
            apk_name=apk,
            repetition=rep,
            timeout=timeout,
            tool_config=ToolConfig(name=tool),
        )
        task = Task(config)
        task.update_state(TaskState.RUNNING)
        task.update_state(TaskState.COMPLETED)
        platform.task_storage.add_task(task)

    def test_skips_matching_completed_tasks(self, tmp_path):
        """Tasks with identical identity tuple are removed from execution list."""
        platform = _make_platform(tmp_path, repetitions=2)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            platform._generate_tasks()
        assert len(platform.tasks) == 2  # app.apk × monkey × 2 reps × 300s

        # Simulate rep 1 completed in previous run
        self._add_completed_to_storage(platform, "app.apk", "monkey", 1, 300)
        platform._skip_completed_tasks()

        assert len(platform.tasks) == 1
        assert platform.tasks[0].config.repetition == 2
        assert platform._skipped_count == 1

    def test_error_tasks_not_skipped(self, tmp_path):
        """Only COMPLETED tasks are skipped; ERROR tasks remain."""
        platform = _make_platform(tmp_path)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            platform._generate_tasks()

        # Add an ERROR task — it should NOT cause skipping
        config = TaskConfiguration(
            apk_name="app.apk",
            repetition=1,
            timeout=300,
            tool_config=ToolConfig(name="monkey"),
        )
        error_task = Task(config)
        error_task.update_state(TaskState.ERROR, "failed")
        platform.task_storage.add_task(error_task)

        platform._skip_completed_tasks()
        assert len(platform.tasks) == 1  # not skipped
        assert platform._skipped_count == 0

    def test_no_completed_tasks_skipped_count_zero(self, tmp_path):
        platform = _make_platform(tmp_path)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            platform._generate_tasks()
        platform._skip_completed_tasks()
        assert platform._skipped_count == 0


# ===========================================================================
# Error Message Extraction
# ===========================================================================


class TestExtractMeaningfulErrorMessage:
    @pytest.fixture
    def platform(self, tmp_path):
        return _make_platform(tmp_path)

    def test_timeout_error_with_seconds(self, platform):
        exc = RVToolTimeoutError("monkey", timeout_seconds=300)
        msg = platform._extract_meaningful_error_message(exc)
        assert "timed out" in msg
        assert "300" in msg
        assert "expected behavior" in msg

    def test_timeout_error_without_seconds(self, platform):
        exc = RVToolTimeoutError("monkey")
        msg = platform._extract_meaningful_error_message(exc)
        assert "timed out" in msg

    def test_tool_execution_error(self, platform):
        exc = RVToolExecutionError("droidbot", "connection refused")
        msg = platform._extract_meaningful_error_message(exc)
        assert "droidbot" in msg

    def test_chained_exception(self, platform):
        """Walks __cause__ chain to find the root RVToolTimeoutError."""
        root = RVToolTimeoutError("ape", timeout_seconds=60)
        wrapper = RuntimeError("task failed")
        wrapper.__cause__ = root
        msg = platform._extract_meaningful_error_message(wrapper)
        assert "timed out" in msg
        assert "60" in msg

    def test_generic_exception_fallback(self, platform):
        """Falls back to str(exception) for unknown exception types."""
        exc = ValueError("something unexpected")
        msg = platform._extract_meaningful_error_message(exc)
        assert msg == "something unexpected"


# ===========================================================================
# Summary Generation
# ===========================================================================


class TestGenerateSummary:
    @pytest.fixture
    def platform(self, tmp_path):
        return _make_platform(tmp_path)

    def test_summary_counts(self, platform):
        results = [
            {"success": True, "execution_time": 100},
            {"success": True, "execution_time": 200},
            {"success": False, "execution_time": 50},
        ]
        summary = platform._generate_summary(results, skipped_count=5)

        assert summary["total_tasks"] == 3
        assert summary["successful_tasks"] == 2
        assert summary["failed_tasks"] == 1
        assert summary["skipped_tasks"] == 5
        assert summary["success_rate"] == pytest.approx(2 / 3)
        assert summary["total_execution_time"] == 350
        assert summary["average_execution_time"] == pytest.approx(350 / 3)

    def test_empty_results(self, platform):
        summary = platform._generate_summary([], skipped_count=0)
        assert summary["total_tasks"] == 0
        assert summary["success_rate"] == 0
        assert summary["average_execution_time"] == 0
