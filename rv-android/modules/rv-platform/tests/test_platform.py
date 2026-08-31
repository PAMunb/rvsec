"""
Tests for Platform — task generation, APK discovery, resume (skip completed),
error message extraction, and summary generation.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

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


def _make_platform(
    tmp_path,
    tools=None,
    repetitions=1,
    timeouts=None,
    apk_names=None,
    package_detector=False,
):
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
        package_detector=package_detector,
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

    def test_device_id_follows_device_port(self, tmp_path):
        """device_id names the device that will actually be booted (INV-PLT-28).

        `--tools "monkey@device_port=5558"` produces parameters with no
        device_serial key; the generated config must not fall back to a literal
        "emulator-5554" that no component will address.
        """
        platform = _make_platform(
            tmp_path,
            tools=[ToolConfig(name="monkey", parameters={"device_port": 5558})],
        )
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            platform._generate_tasks()
        assert platform.tasks[0].config.device_id == "emulator-5558"

    def test_device_id_defaults_to_5554_without_parameters(self, tmp_path):
        """Single-emulator mode keeps the historical default."""
        platform = _make_platform(tmp_path)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            platform._generate_tasks()
        assert platform.tasks[0].config.device_id == "emulator-5554"

    def test_tasks_have_app_set(self, tmp_path):
        """Each generated task must have an App instance."""
        platform = _make_platform(tmp_path)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            platform._generate_tasks()
        for task in platform.tasks:
            assert task.app is not None

    @pytest.mark.parametrize("policy", [True, False])
    def test_generated_apps_carry_the_run_package_policy(self, tmp_path, policy):
        """Task generation builds every App under PlatformConfig's policy.

        The value arrives by value from the entry point that resolved it;
        rv-platform reads no environment variable to obtain it (INV-EXP-34).
        """
        platform = _make_platform(tmp_path, package_detector=policy)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            platform._generate_tasks()

        assert platform.tasks
        for task in platform.tasks:
            assert task.app.package_detector is policy
            # Three values now (INV-CORE-18 as modified). This platform builds
            # its apps without the neutralization policy, so the manifest branch
            # reports "manifest" — "manifest-neutralized" belongs to the runs
            # that turn the policy on AND have a suffix to remove.
            assert task.app.code_package_source == (
                "detector" if policy else "manifest"
            )
            assert task.app.strip_build_type_suffix is False

    def test_platform_reads_no_environment_for_the_policy(self):
        """The variable name appears nowhere in rv-platform's source."""
        import rv_platform

        sources = Path(rv_platform.__file__).parent.rglob("*.py")
        offenders = [
            path
            for path in sources
            if "RV_PACKAGE_DETECTOR" in path.read_text(encoding="utf-8")
        ]

        assert offenders == []


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


# ===========================================================================
# run() error handling (except branch)
# ===========================================================================


class TestRunErrorHandling:
    """Cover the run() except branch (lines 176-179).

    Basis Path Testing: run() has a happy path (already covered indirectly)
    and an error path where any phase raises. We force the first phase
    (_generate_tasks) to raise and assert the exception is re-raised after
    error_handler.handle_error is invoked.
    """

    def test_run_reraises_and_reports_on_failure(self, tmp_path):
        platform = _make_platform(tmp_path)
        boom = RuntimeError("gen fail")
        platform._generate_tasks = MagicMock(side_effect=boom)
        platform.error_handler.handle_error = MagicMock()

        with pytest.raises(RuntimeError, match="gen fail"):
            platform.run()

        # error_handler must receive the original exception with phase context
        platform.error_handler.handle_error.assert_called_once()
        called_exc = platform.error_handler.handle_error.call_args[0][0]
        assert called_exc is boom


# ===========================================================================
# run() happy-path orchestration (lines 146-174)
# ===========================================================================


class TestRunHappyPath:
    """Cover the run() success body (lines 146-174).

    Basis Path Testing: the five-phase orchestration between task generation
    and summary. All phase methods are stubbed so only the orchestration glue
    (metadata build, set_experiment_metadata, result-processing gate, summary)
    executes.
    """

    def test_run_executes_all_phases_and_returns_summary(self, tmp_path):
        platform = _make_platform(tmp_path)
        platform._generate_tasks = MagicMock()
        platform._skip_completed_tasks = MagicMock()
        platform._execute_tasks = MagicMock(return_value=[])
        platform._process_results = MagicMock()
        platform.task_storage.set_experiment_metadata = MagicMock()
        platform._skipped_count = 3

        summary = platform.run()

        # Orchestration wired the phases together
        platform._generate_tasks.assert_called_once()
        platform._skip_completed_tasks.assert_called_once()
        platform._execute_tasks.assert_called_once()
        platform._process_results.assert_called_once()
        platform.task_storage.set_experiment_metadata.assert_called_once()
        # Summary reflects the (empty) results plus the skipped count
        assert summary["total_tasks"] == 0
        assert summary["skipped_tasks"] == 3

    def test_run_skips_result_processing_when_configured(self, tmp_path):
        platform = _make_platform(tmp_path)
        platform._generate_tasks = MagicMock()
        platform._skip_completed_tasks = MagicMock()
        platform._execute_tasks = MagicMock(return_value=[])
        platform._process_results = MagicMock()
        platform.config.skip_result_processing = True

        platform.run()

        platform._process_results.assert_not_called()


# ===========================================================================
# _process_results() (lines 554-571)
# ===========================================================================


class TestProcessResults:
    """Cover _process_results() (lines 554-571).

    ResultProcessorComponent is patched at the module path so its
    initialize/execute/cleanup lifecycle is invoked without real file I/O.
    """

    def test_process_results_runs_component_lifecycle(self, tmp_path):
        platform = _make_platform(tmp_path)
        platform.task_storage.get_completed_tasks = MagicMock(return_value=[])

        with patch("rv_platform.platform.ResultProcessorComponent") as MockProc:
            platform._process_results()

        instance = MockProc.return_value
        instance.initialize.assert_called_once()
        instance.execute.assert_called_once()
        instance.cleanup.assert_called_once()


# ===========================================================================
# _discover_apks() empty-directory direct branch (line 298)
# ===========================================================================


class TestDiscoverApksEmptyDirect:
    """Cover the raise at line 298 directly.

    Error guessing: existing test_raises_on_empty_directory trips
    validate_dependencies in __init__, never reaching _discover_apks. Here we
    build a valid platform, then repoint apks_dir at an empty dir and call
    _discover_apks() directly so the glob returns no files.
    """

    def test_discover_apks_raises_when_dir_empty(self, tmp_path):
        platform = _make_platform(tmp_path)
        empty = tmp_path / "empty"
        empty.mkdir()
        platform.config.apks_dir = str(empty)
        with pytest.raises(ValueError, match="No APK files found"):
            platform._discover_apks()


# ===========================================================================
# _execute_tasks() full method (success + except paths)
# ===========================================================================


class TestExecuteTasks:
    """Cover _execute_tasks() (lines 327-412).

    Basis Path Testing: two paths through the per-task loop — the success
    path (executor.execute returns) and the except path (executor.execute
    raises). All heavy collaborators (TaskExecutor + the five components) are
    patched at the module path rv_platform.platform.* so construction is
    side-effect-free.
    """

    def _one_task_platform(self, tmp_path):
        platform = _make_platform(tmp_path)
        with patch.object(App, "model_post_init", lambda self, ctx: None):
            platform._generate_tasks()
        assert len(platform.tasks) == 1
        return platform

    def test_success_path_collects_result_and_persists(self, tmp_path):
        platform = self._one_task_platform(tmp_path)

        with patch("rv_platform.platform.TaskExecutor") as MockExec, patch(
            "rv_platform.platform.StaticAnalysisComponent"
        ), patch("rv_platform.platform.EmulatorComponent"), patch(
            "rv_platform.platform.LogcatComponent"
        ), patch(
            "rv_platform.platform.CoverageComponent"
        ), patch(
            "rv_platform.platform.ToolExecutionComponent"
        ):
            MockExec.return_value.execute.return_value = True
            platform._load_tool = MagicMock(return_value=MagicMock())
            platform.task_storage.update_task = MagicMock()

            results = platform._execute_tasks()

        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["apk_name"] == "app.apk"
        assert results[0]["tool_name"] == "monkey"
        assert platform.task_storage.update_task.called

    def test_except_path_marks_error_and_persists(self, tmp_path):
        platform = self._one_task_platform(tmp_path)

        with patch("rv_platform.platform.TaskExecutor") as MockExec, patch(
            "rv_platform.platform.StaticAnalysisComponent"
        ), patch("rv_platform.platform.EmulatorComponent"), patch(
            "rv_platform.platform.LogcatComponent"
        ), patch(
            "rv_platform.platform.CoverageComponent"
        ), patch(
            "rv_platform.platform.ToolExecutionComponent"
        ):
            MockExec.return_value.execute.side_effect = RuntimeError("exec boom")
            platform._load_tool = MagicMock(return_value=MagicMock())
            platform.task_storage.update_task = MagicMock()

            results = platform._execute_tasks()

        assert len(results) == 1
        assert results[0]["success"] is False
        assert "exec boom" in results[0]["error_message"]
        # Task marked ERROR and persisted (crash-recovery invariant)
        assert platform.tasks[0].result.state == TaskState.ERROR
        assert platform.task_storage.update_task.called


# ===========================================================================
# _extract_meaningful_error_message() .message branch (line 448)
# ===========================================================================


class TestExtractMessageAttr:
    """Cover the generic `.message` branch (line 448).

    Equivalence Partitioning: distinct from the RVToolTimeoutError /
    RVToolExecutionError partitions already covered — a non-RV exception that
    nonetheless carries a truthy `.message` attribute must short-circuit to it
    before the fallback str(exception).
    """

    def test_non_rv_exception_with_message_attr(self, tmp_path):
        platform = _make_platform(tmp_path)

        class CustomErr(Exception):
            def __init__(self):
                super().__init__("x")
                self.message = "custom detail"
                self.cause = None

        msg = platform._extract_meaningful_error_message(CustomErr())
        assert msg == "custom detail"


# ===========================================================================
# _load_tool() three sub-branches (lines 475-488)
# ===========================================================================


class TestLoadTool:
    """Cover _load_tool() success and both failure branches.

    Decision table:
      - valid ToolConfig + factory ok         -> returns tool instance
      - non-ToolConfig input                   -> inner ValueError re-wrapped
      - valid ToolConfig + factory raises      -> RuntimeError re-wrapped
    """

    def test_success_returns_factory_instance(self, tmp_path):
        platform = _make_platform(tmp_path)
        sentinel = MagicMock()
        platform.tool_factory.create_tool = MagicMock(return_value=sentinel)
        tc = ToolConfig(name="monkey")
        assert platform._load_tool(tc) is sentinel

    def test_non_toolconfig_raises_wrapped(self, tmp_path):
        platform = _make_platform(tmp_path)
        with pytest.raises(ValueError, match="Failed to load tool"):
            platform._load_tool("not-a-toolconfig")

    def test_factory_error_raises_wrapped(self, tmp_path):
        platform = _make_platform(tmp_path)
        platform.tool_factory.create_tool = MagicMock(
            side_effect=RuntimeError("boom")
        )
        tc = ToolConfig(name="monkey")
        with pytest.raises(ValueError, match="Failed to load tool"):
            platform._load_tool(tc)


# ===========================================================================
# Task accessors (lines 535, 544)
# ===========================================================================


class TestTaskAccessors:
    """Cover get_tasks() and get_tasks_summary()."""

    def test_get_tasks_returns_task_list(self, tmp_path):
        platform = _make_platform(tmp_path)
        sentinel = ["t1", "t2"]
        platform.tasks = sentinel
        assert platform.get_tasks() is sentinel

    def test_get_tasks_summary_serializes_each_task(self, tmp_path):
        platform = _make_platform(tmp_path)
        fake = MagicMock()
        fake.to_dict.return_value = {"id": "x"}
        platform.tasks = [fake]
        assert platform.get_tasks_summary() == [{"id": "x"}]
        assert fake.to_dict.called
