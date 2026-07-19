# tests/components/test_coverage.py
"""
Tests for CoverageComponent, specifically verifying that coverage timing
uses tool_execution_start (not task creation time) for accurate relative timestamps.
"""

from unittest.mock import MagicMock

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task, TaskConfiguration, TaskState, ToolConfig
from rv_platform.components.coverage import CoverageComponent


class TestCoverageComponentTiming:
    """Tests for coverage timing accuracy — tool_execution_start vs task creation time."""

    @pytest.fixture
    def basic_config(self):
        tool_config = ToolConfig(name="monkey", variant="default", parameters={})
        return TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )

    @pytest.fixture
    def mock_app(self):
        app = MagicMock(spec=App)
        app.name = "test.apk"
        app.package_name = "com.test.app"
        return app

    @pytest.fixture
    def task_with_app(self, basic_config, mock_app, tmp_path):
        task = Task(basic_config)
        task.set_app(mock_app)
        task.initialize(str(tmp_path))
        task.update_state(TaskState.RUNNING)  # Sets start_time
        return task

    def test_start_tracking_updates_timing_reference(self, task_with_app):
        """
        Verify that start_tracking() updates the tracker's tool_execution_start_time
        when the task has a valid tool_execution_start timestamp.

        This is the core of the timing fix: the tracker is initialized in Phase 2
        (before emulator starts), but tool_execution_start is only set in Phase 3.
        start_tracking() must update the tracker's time reference before starting.
        """
        component = CoverageComponent(task_with_app)

        # Phase 2: initialize tracker (tool_execution_start is None at this point)
        assert task_with_app.result.tool_execution_start is None
        component.execute({})  # calls initialize_tracker()

        # Simulate what executor does: mark tool execution start BEFORE start_tracking
        task_with_app.mark_tool_execution_start()
        tool_start = task_with_app.result.tool_execution_start
        assert tool_start is not None

        # Phase 3: start_tracking should update the tracker's time reference
        component.start_tracking()

        assert component.coverage_tracker is not None
        assert component.coverage_tracker.tool_execution_start_time == tool_start

    def test_start_tracking_without_tool_execution_start(self, task_with_app):
        """
        Verify that start_tracking() preserves the original timing reference
        when tool_execution_start is not available (defensive case).
        """
        component = CoverageComponent(task_with_app)

        # Initialize tracker (tool_execution_start is None)
        component.execute({})

        original_time = component.coverage_tracker.tool_execution_start_time

        # start_tracking without calling mark_tool_execution_start first
        component.start_tracking()

        # Should keep original reference (start_time from initialization)
        assert component.coverage_tracker.tool_execution_start_time == original_time

    def test_timing_difference_between_start_time_and_tool_execution_start(
        self, task_with_app
    ):
        """
        Verify that tool_execution_start differs from start_time by the expected
        pre-processing overhead. This is the symptom the fix addresses: without it,
        coverage times would be offset by the pre-processing duration.
        """
        component = CoverageComponent(task_with_app)

        task_start = task_with_app.result.start_time

        # Initialize tracker (uses start_time as initial reference)
        component.execute({})
        initial_ref = component.coverage_tracker.tool_execution_start_time
        assert initial_ref == task_start

        # Simulate pre-processing overhead
        task_with_app.mark_tool_execution_start()
        tool_start = task_with_app.result.tool_execution_start

        # tool_execution_start must be >= start_time
        assert tool_start >= task_start

        # After start_tracking, the tracker should use the later timestamp
        component.start_tracking()
        assert component.coverage_tracker.tool_execution_start_time == tool_start
        assert component.coverage_tracker.tool_execution_start_time >= task_start


class TestCoverageComponentBranchCoverage:
    """
    Branch/edge coverage for CoverageComponent.

    These tests exercise the error and edge branches of every method
    (initialize/execute/cleanup/_parse_existing_logcat/initialize_tracker/
    start_tracking/stop_tracking/process_results/get_repository). The tracker
    is mocked so that failures can be forced deterministically without a real
    emulator/logcat — the happy path with a REAL tracker is covered by
    TestCoverageComponentTiming.

    Design rationale:
    - Basis Path Testing: each conditional and try/except is driven at least
      once so all structural branches execute.
    - Error Guessing / Robustness: dependencies are made to raise so the
      explicit `return False`/swallow-and-warn branches are validated.
    - Equivalence Partitioning: tracker present vs. tracker None is the key
      partition for start/stop/process/get_repository.
    """

    @pytest.fixture
    def basic_config(self):
        tool_config = ToolConfig(name="monkey", variant="default", parameters={})
        return TaskConfiguration(
            apk_name="test.apk", repetition=1, timeout=60, tool_config=tool_config
        )

    @pytest.fixture
    def mock_app(self):
        app = MagicMock(spec=App)
        app.name = "test.apk"
        app.package_name = "com.test.app"
        return app

    @pytest.fixture
    def task_with_app(self, basic_config, mock_app, tmp_path):
        task = Task(basic_config)
        task.set_app(mock_app)
        task.initialize(str(tmp_path))
        task.update_state(TaskState.RUNNING)  # Sets start_time
        return task

    # ------------------------------------------------------------------ #
    # initialize()                                                        #
    # ------------------------------------------------------------------ #

    def test_initialize_returns_none(self, task_with_app):
        """initialize() only logs a debug line and returns None (line 81)."""
        component = CoverageComponent(task_with_app)
        assert component.initialize({}) is None

    # ------------------------------------------------------------------ #
    # execute()                                                          #
    # ------------------------------------------------------------------ #

    def test_execute_returns_false_when_tracker_init_fails(self, task_with_app):
        """execute() returns False and skips context population when
        initialize_tracker() returns False (line 102)."""
        component = CoverageComponent(task_with_app)
        component.initialize_tracker = MagicMock(return_value=False)

        context: dict = {}
        assert component.execute(context) is False
        assert "coverage_tracker" not in context

    def test_execute_returns_false_when_tracker_init_raises(self, task_with_app):
        """execute() except branch: initialize_tracker() raising is caught and
        returns False (lines 110-113)."""
        component = CoverageComponent(task_with_app)
        component.initialize_tracker = MagicMock(side_effect=RuntimeError("boom"))

        assert component.execute({}) is False

    # ------------------------------------------------------------------ #
    # cleanup()                                                          #
    # ------------------------------------------------------------------ #

    def test_cleanup_calls_stop_and_process(self, task_with_app):
        """cleanup() success path invokes stop_tracking() then process_results()
        exactly once each (lines 122,124,125)."""
        component = CoverageComponent(task_with_app)
        component.stop_tracking = MagicMock()
        component.process_results = MagicMock()

        component.cleanup({})

        component.stop_tracking.assert_called_once()
        component.process_results.assert_called_once()

    def test_cleanup_swallows_exception(self, task_with_app):
        """cleanup() except branch: a failure in stop_tracking() is logged as a
        warning and does NOT propagate (lines 126-127)."""
        component = CoverageComponent(task_with_app)
        component.stop_tracking = MagicMock(side_effect=Exception("x"))
        component.process_results = MagicMock()

        # Must not raise.
        assert component.cleanup({}) is None

    # ------------------------------------------------------------------ #
    # _parse_existing_logcat()                                           #
    # ------------------------------------------------------------------ #

    def test_parse_existing_logcat_success(self, task_with_app, tmp_path, monkeypatch):
        """_parse_existing_logcat() success path: an existing file is parsed and
        the returned repository is attached to component and task (lines 136-141)."""
        import rv_platform.components.coverage as cov_mod

        logcat = tmp_path / "existing.logcat"
        logcat.write_text("some logcat content\n")

        component = CoverageComponent(task_with_app)
        component.task.result.logcat_file = str(logcat)

        fake_repo = MagicMock()
        monkeypatch.setattr(
            cov_mod, "parse_logcat_file", MagicMock(return_value=fake_repo)
        )

        component._parse_existing_logcat()

        assert component.repository is fake_repo
        assert component.task.repository is fake_repo

    def test_parse_existing_logcat_forwards_tool_execution_start(
        self, task_with_app, tmp_path, monkeypatch
    ):
        """gh83 (design Decision 5): _parse_existing_logcat() forwards the task's
        tool_execution_start epoch so parsed entries carry real timing."""
        from datetime import datetime

        import rv_platform.components.coverage as cov_mod

        logcat = tmp_path / "existing.logcat"
        logcat.write_text("some logcat content\n")

        component = CoverageComponent(task_with_app)
        component.task.result.logcat_file = str(logcat)
        epoch = datetime(2026, 3, 24, 19, 37, 0)
        component.task.result.tool_execution_start = epoch

        spy = MagicMock(return_value=MagicMock())
        monkeypatch.setattr(cov_mod, "parse_logcat_file", spy)

        component._parse_existing_logcat()

        spy.assert_called_once()
        assert spy.call_args.kwargs["tool_execution_start"] == epoch

    def test_parse_existing_logcat_swallows_exception(
        self, task_with_app, tmp_path, monkeypatch
    ):
        """_parse_existing_logcat() except branch: a parse failure is logged and
        handled, not propagated (lines 142-146)."""
        import rv_platform.components.coverage as cov_mod

        logcat = tmp_path / "existing.logcat"
        logcat.write_text("some logcat content\n")

        component = CoverageComponent(task_with_app)
        component.task.result.logcat_file = str(logcat)

        monkeypatch.setattr(
            cov_mod,
            "parse_logcat_file",
            MagicMock(side_effect=Exception("parse fail")),
        )

        # Must not raise.
        assert component._parse_existing_logcat() is None

    def test_parse_existing_logcat_noop_when_missing_file(self, task_with_app):
        """_parse_existing_logcat() no-ops when logcat_file points to a
        nonexistent path (guard at lines 133-135)."""
        component = CoverageComponent(task_with_app)
        component.task.result.logcat_file = "/nonexistent/path/does_not_exist.logcat"
        # The repository attached by the constructor must be preserved.
        original_repo = component.repository

        assert component._parse_existing_logcat() is None
        assert component.repository is original_repo

    # ------------------------------------------------------------------ #
    # initialize_tracker()                                               #
    # ------------------------------------------------------------------ #

    def test_initialize_tracker_returns_false_on_ctor_failure(
        self, task_with_app, monkeypatch
    ):
        """initialize_tracker() except branch: CoverageTracker construction
        raising is caught, returns False, tracker stays None (lines 176-186)."""
        import rv_platform.components.coverage as cov_mod

        monkeypatch.setattr(
            cov_mod, "CoverageTracker", MagicMock(side_effect=Exception("ctor fail"))
        )

        component = CoverageComponent(task_with_app)
        assert component.initialize_tracker() is False
        assert component.coverage_tracker is None

    # ------------------------------------------------------------------ #
    # start_tracking()                                                   #
    # ------------------------------------------------------------------ #

    def test_start_tracking_returns_false_when_not_initialized(self, task_with_app):
        """start_tracking() returns False when no tracker was initialized
        (lines 198-199)."""
        component = CoverageComponent(task_with_app)
        component.coverage_tracker = None
        assert component.start_tracking() is False

    def test_start_tracking_returns_false_on_start_failure(self, task_with_app):
        """start_tracking() except branch: tracker.start() raising is caught and
        returns False (lines 215-223)."""
        component = CoverageComponent(task_with_app)
        component.coverage_tracker = MagicMock()
        component.coverage_tracker.start.side_effect = Exception("start fail")

        assert component.start_tracking() is False

    # ------------------------------------------------------------------ #
    # stop_tracking()                                                    #
    # ------------------------------------------------------------------ #

    def test_stop_tracking_returns_true_when_no_tracker(self, task_with_app):
        """stop_tracking() short-circuits to True when there is no tracker
        (lines 233-235)."""
        component = CoverageComponent(task_with_app)
        component.coverage_tracker = None
        assert component.stop_tracking() is True

    def test_stop_tracking_success(self, task_with_app):
        """stop_tracking() success path stops the tracker and returns True
        (lines 237-241)."""
        component = CoverageComponent(task_with_app)
        component.coverage_tracker = MagicMock()

        assert component.stop_tracking() is True
        assert component.coverage_tracker.stop.called

    def test_stop_tracking_returns_false_on_failure(self, task_with_app):
        """stop_tracking() except branch: tracker.stop() raising returns False
        (lines 242-250)."""
        component = CoverageComponent(task_with_app)
        component.coverage_tracker = MagicMock()
        component.coverage_tracker.stop.side_effect = Exception("stop fail")

        assert component.stop_tracking() is False

    # ------------------------------------------------------------------ #
    # process_results()                                                  #
    # ------------------------------------------------------------------ #

    def test_process_results_returns_false_when_no_tracker(self, task_with_app):
        """process_results() returns False when no tracker is available
        (lines 261-269)."""
        component = CoverageComponent(task_with_app)
        component.coverage_tracker = None
        assert component.process_results() is False

    def test_process_results_success_updates_metrics(self, task_with_app):
        """process_results() success path calculates metrics, maps them into the
        task result, attaches the repository, and returns True (lines 271-313)."""
        component = CoverageComponent(task_with_app)
        component.coverage_tracker = MagicMock()

        metrics = MagicMock()
        metrics.called_methods = 5
        metrics.to_dict.return_value = {
            "method_coverage": 50.0,
            "activity_coverage": 40.0,
            "mop_method_coverage": 30.0,
            "unique_errors": 2,
        }
        repo = component.coverage_tracker.repository
        repo.calculate_metrics.return_value = metrics

        assert component.process_results() is True

        cov = component.task.result.coverage_metrics
        assert cov["method_coverage"] == 50.0
        assert cov["activities_coverage"] == 40.0
        assert cov["methods_mop_reachable_coverage"] == 30.0
        assert cov["total_errors"] == 2
        assert cov["total_method_calls"] == 5
        assert component.task.repository is repo

    def test_process_results_returns_false_on_calc_failure(self, task_with_app):
        """process_results() except branch: calculate_metrics() raising is caught
        and returns False (lines 315-323)."""
        component = CoverageComponent(task_with_app)
        component.coverage_tracker = MagicMock()
        component.coverage_tracker.repository.calculate_metrics.side_effect = Exception(
            "calc fail"
        )

        assert component.process_results() is False

    # ------------------------------------------------------------------ #
    # get_repository()                                                   #
    # ------------------------------------------------------------------ #

    def test_get_repository_returns_tracker_repository(self, task_with_app):
        """get_repository() returns the tracker's repository when present
        (lines 332-333)."""
        component = CoverageComponent(task_with_app)
        component.coverage_tracker = MagicMock()
        assert component.get_repository() is component.coverage_tracker.repository

    def test_get_repository_returns_none_without_tracker(self, task_with_app):
        """get_repository() returns None when there is no tracker (line 334)."""
        component = CoverageComponent(task_with_app)
        component.coverage_tracker = None
        assert component.get_repository() is None
