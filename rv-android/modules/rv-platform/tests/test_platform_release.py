"""
Tests for the release of a finished task's parsed state by Platform (INV-PLT-38).

Requirement "A Finished Task Releases Its Parsed State", Scenario "A finished
task holds no parsed state".
"""

import os
import shutil
from datetime import datetime
from functools import partial
from unittest.mock import MagicMock, patch

from rv_android_core.domain.app import App
from rv_android_core.domain.task import TaskState, ToolConfig
from rv_coverage.parser.log.logcat_parser import parse_logcat_file
from rv_platform.__main__ import _process_results_standalone
from rv_platform.config.platform_config import PlatformConfig
from rv_platform.platform import Platform
from rv_static_analysis.parser.static import static_analysis_parser

_FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "components", "fixtures", "gh58")
_APK = "sample_apk.apk"
_OUTPUT_FILES = (
    "coverage.csv",
    "errors.csv",
    "app_events.csv",
    "summary.csv",
    "results.json",
)


def _epoch():
    """Tool execution start aligned with the 05-14 10:00:00 fixture timeline."""
    return datetime(datetime.now().year, 5, 14, 10, 0, 0)


class _LiveExecutor:
    """Stands in for TaskExecutor: leaves the task as a live run does, with the
    logcat and static JSON on disk and both parsed objects on the task."""

    def __init__(self, results_dir, task, tool, task_storage=None):
        self.results_dir = results_dir
        self.task = task

    def register_component(self, component):
        pass

    def execute(self):
        task = self.task
        task.initialize(self.results_dir)
        shutil.copy(
            os.path.join(_FIXTURE_DIR, "sample_task.logcat"), task.result.logcat_file
        )
        shutil.copy(
            os.path.join(_FIXTURE_DIR, f"{_APK}.json"),
            os.path.join(task.results_dir, f"{_APK}.json"),
        )
        task.update_state(TaskState.RUNNING)
        task.result.tool_execution_start = _epoch()
        task.static_data = static_analysis_parser.read_static_analysis_files(
            task.results_dir, _APK
        )
        task.repository = parse_logcat_file(
            task.result.logcat_file,
            task.static_data,
            tool_execution_start=_epoch(),
        )
        task.result.coverage_metrics = {
            "method_coverage": 16.67,
            "activities_coverage": 50.0,
            "total_errors": 2.0,
        }
        task.update_state(TaskState.COMPLETED)
        return True


def _make_platform(tmp_path):
    apks_dir = tmp_path / "apks"
    apks_dir.mkdir()
    (apks_dir / _APK).write_bytes(b"PK\x03\x04")
    config = PlatformConfig(
        apks_dir=str(apks_dir),
        tools=[ToolConfig(name="monkey")],
        repetitions=1,
        timeouts=[300],
        results_dir=str(tmp_path / "results"),
        no_window=True,
        log_level="WARNING",
    )
    with patch.object(App, "model_post_init", lambda self, ctx: None):
        platform = Platform(config)
        platform._generate_tasks()
    return platform


def _read(directory, name):
    with open(os.path.join(directory, name), "rb") as f:
        return f.read()


class TestFinishedTaskReleasesParsedState:
    def test_finished_task_releases_parsed_state(self, tmp_path):
        platform = _make_platform(tmp_path)
        assert len(platform.tasks) == 1
        task = platform.tasks[0]

        # What the store received, observed at the moment it received it: the
        # release must come after storage, not instead of it.
        state_at_storage = []
        update_task = platform.task_storage.update_task

        def observing_update_task(stored):
            state_at_storage.append(
                (stored.repository is not None, stored.static_data is not None)
            )
            update_task(stored)

        platform._load_tool = MagicMock(return_value=MagicMock())
        with (
            patch(
                "rv_platform.platform.TaskExecutor",
                partial(_LiveExecutor, platform.config.results_dir),
            ),
            patch("rv_platform.platform.StaticAnalysisComponent"),
            patch("rv_platform.platform.EmulatorComponent"),
            patch("rv_platform.platform.LogcatComponent"),
            patch("rv_platform.platform.CoverageComponent"),
            patch("rv_platform.platform.ToolExecutionComponent"),
            patch.object(
                platform.task_storage,
                "update_task",
                side_effect=observing_update_task,
            ),
        ):
            results = platform._execute_tasks()

        assert results[0]["success"] is True
        assert state_at_storage == [(True, True)]
        # THEN immediately afterwards neither field is populated.
        assert task.repository is None
        assert task.static_data is None
        # AND the metrics the run needs after completion are untouched.
        assert task.result.coverage_metrics == {
            "method_coverage": 16.67,
            "activities_coverage": 50.0,
            "total_errors": 2.0,
        }

        # AND the rows written at the end of the run equal those of a standalone
        # --process-results over the same results directory.
        results_dir = platform.config.results_dir
        platform._process_results()
        live = {name: _read(results_dir, name) for name in _OUTPUT_FILES}
        for name in _OUTPUT_FILES:
            os.remove(os.path.join(results_dir, name))

        assert _process_results_standalone(results_dir) == 0
        standalone = {name: _read(results_dir, name) for name in _OUTPUT_FILES}

        assert live == standalone
        # The comparison is not vacuous: the task wrote coverage and violations.
        assert live["coverage.csv"].count(b"\n") > 1
        assert live["errors.csv"].count(b"\n") == 3
