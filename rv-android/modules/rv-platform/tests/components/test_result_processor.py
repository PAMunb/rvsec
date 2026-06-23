"""
Tests for ResultProcessorComponent — CSV/JSON generation, task filtering,
coverage/error/summary data writing, and logcat reconstruction fallback.
"""

import csv
import json
import os
import shutil
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.task import Task, TaskConfiguration, TaskState, ToolConfig
from rv_coverage.parser.log.logcat_parser import parse_logcat_file
from rv_platform.components.result_processor import ResultProcessorComponent
from rv_static_analysis.parser.static import static_analysis_parser

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completed_task(
    apk="app.apk",
    tool="monkey",
    variant="default",
    rep=1,
    timeout=300,
    coverage_metrics=None,
    repository=None,
):
    """Create a completed task with optional coverage metrics and repository."""
    config = TaskConfiguration(
        apk_name=apk,
        repetition=rep,
        timeout=timeout,
        tool_config=ToolConfig(name=tool, variant=variant),
    )
    task = Task(config)
    task.update_state(TaskState.RUNNING)
    task.result.execution_time_seconds = 120
    task.update_state(TaskState.COMPLETED)

    if coverage_metrics:
        task.result.coverage_metrics = coverage_metrics

    if repository is not None:
        task.repository = repository
    else:
        # Simulate a task loaded from disk (repository=None)
        task.repository = None

    return task


def _make_error_task(apk="app.apk"):
    config = TaskConfiguration(
        apk_name=apk,
        repetition=1,
        timeout=300,
        tool_config=ToolConfig(name="monkey"),
    )
    task = Task(config)
    task.update_state(TaskState.ERROR, "something failed")
    return task


def _make_mock_repository(method_calls=None, errors=None, static_methods=None):
    """Create a mock LogcatRepository."""
    repo = MagicMock()
    repo.get_method_calls.return_value = method_calls or []
    repo.get_errors.return_value = errors or []
    repo.get_static_methods.return_value = static_methods or []
    repo.get_static_activities.return_value = []
    repo.get_target_methods.return_value = []

    metrics = MagicMock()
    metrics.called_activities = 2
    metrics.called_methods = 10
    metrics.called_target_methods = 3
    metrics.total_errors = len(errors) if errors else 0
    metrics.to_dict.return_value = {
        "activity_coverage": 50.0,
        "method_coverage": 25.0,
        "mop_method_coverage": 15.0,
        "unique_errors": len(errors) if errors else 0,
        "called_methods": 10,
    }
    repo.calculate_metrics.return_value = metrics

    return repo


# ===========================================================================
# Filter Completed Tasks
# ===========================================================================


class TestFilterCompletedTasks:
    def test_filters_only_completed_tasks(self, tmp_path):
        completed = _make_completed_task()
        error = _make_error_task()
        processor = ResultProcessorComponent(
            [completed, error], str(tmp_path / "results")
        )
        filtered = processor._filter_completed_tasks()
        assert len(filtered) == 1
        assert filtered[0].result.state == TaskState.COMPLETED

    def test_empty_when_no_completed(self, tmp_path):
        error = _make_error_task()
        processor = ResultProcessorComponent([error], str(tmp_path / "results"))
        filtered = processor._filter_completed_tasks()
        assert len(filtered) == 0


# ===========================================================================
# Coverage CSV Generation
# ===========================================================================


class TestCoverageCSV:
    def test_coverage_csv_with_repository(self, tmp_path):
        """Tasks with a repository produce per-method-call rows."""
        method_calls = [
            {
                "signature": "void foo()",
                "class_name": "Foo",
                "method_name": "foo",
                "time": 1,
                "activity": "MainActivity",
                "is_mop_method": True,
            },
            {
                "signature": "void bar()",
                "class_name": "Bar",
                "method_name": "bar",
                "time": 2,
                "activity": "MainActivity",
                "is_mop_method": False,
            },
        ]
        static_methods = [MagicMock() for _ in range(10)]
        repo = _make_mock_repository(
            method_calls=method_calls, static_methods=static_methods
        )

        task = _make_completed_task(repository=repo)
        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)

        processor._generate_coverage_csv([task])

        csv_path = os.path.join(results_dir, "coverage.csv")
        assert os.path.isfile(csv_path)
        with open(csv_path) as f:
            reader = list(csv.reader(f))
        # header + 2 data rows
        assert len(reader) == 3
        assert reader[0][0] == "apk"  # header
        assert reader[1][0] == "app.apk"

    def test_coverage_csv_no_rows_when_repository_and_logcat_both_missing(
        self, tmp_path
    ):
        """gh58/INV-PLT-16: when task.repository is None AND no logcat is on
        disk, _write_task_coverage_data must NOT emit a fallback row from
        task.result.coverage_metrics. The legacy Branch 2 (empty
        class/method/signature + stale percentages) is removed."""
        metrics = {"method_coverage": 25.0, "activities_coverage": 50.0}
        task = _make_completed_task(coverage_metrics=metrics)
        task.result.logcat_file = ""  # ensure reconstruct returns None

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_coverage_csv([task])

        with open(os.path.join(results_dir, "coverage.csv")) as f:
            reader = list(csv.reader(f))
        # Only the header — no data row from stale serialized metrics.
        assert len(reader) == 1


# ===========================================================================
# Errors CSV Generation
# ===========================================================================


class TestErrorsCSV:
    def test_errors_csv_with_repository(self, tmp_path):
        """Tasks with a repository produce error rows from repository.get_errors()."""
        errors = [
            {
                "class_full_name": "javax.crypto.Cipher",
                "method": "init",
                "spec": "Cipher_1",
                "error_type": "violation",
                "message": "bad init",
                "unique_msg": "Cipher:::init:::Cipher_1:::violation:::bad init",
                "time_since_task_start": 5,
            },
        ]
        repo = _make_mock_repository(errors=errors)
        task = _make_completed_task(repository=repo)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_errors_csv([task])

        csv_path = os.path.join(results_dir, "errors.csv")
        with open(csv_path) as f:
            reader = list(csv.reader(f))
        assert len(reader) == 2  # header + 1 error
        assert reader[1][5] == "Cipher_1"  # spec column

    def test_errors_csv_reconstructs_from_logcat(self, tmp_path):
        """Tasks without repository reconstruct MOP violations from logcat."""
        task = _make_completed_task()  # repository=None

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)

        # Mock reconstruction to return errors
        mock_repo = _make_mock_repository(
            errors=[
                {
                    "class_full_name": "c",
                    "method": "m",
                    "spec": "s",
                    "error_type": "t",
                    "message": "msg",
                    "unique_msg": "c:::m:::s:::t:::msg",
                    "time_since_task_start": 1,
                }
            ]
        )
        with patch.object(
            processor, "_reconstruct_repository_from_logcat", return_value=mock_repo
        ):
            processor._generate_errors_csv([task])

        csv_path = os.path.join(results_dir, "errors.csv")
        with open(csv_path) as f:
            reader = list(csv.reader(f))
        assert len(reader) == 2  # header + 1 reconstructed error

    def test_errors_csv_empty_when_no_repository_no_logcat(self, tmp_path):
        """No repository and no logcat → header-only errors.csv."""
        task = _make_completed_task()

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)

        with patch.object(
            processor, "_reconstruct_repository_from_logcat", return_value=None
        ):
            processor._generate_errors_csv([task])

        csv_path = os.path.join(results_dir, "errors.csv")
        with open(csv_path) as f:
            reader = list(csv.reader(f))
        assert len(reader) == 1  # header only


# ===========================================================================
# App Events CSV Generation (gh72)
# ===========================================================================


def _diagnostic_event_dict(category="crash", time=2):
    """A diagnostic-event dict as returned by LogcatRepository.get_diagnostic_events()."""
    return {
        "category": category,
        "class_full_name": "java.lang.NullPointerException",
        "method": "onMenuItemClick",
        "source": "MainActivity.java:50",
        "message": "FATAL EXCEPTION: main",
        "process": "br.unb.cic.cryptoapp",
        "pid": "7071",
        "tid": "7071",
        "fatal": True,
        "stack_head": "br.unb.cic.cryptoapp.MainActivity$1.onMenuItemClick(MainActivity.java:50)",
        "n_frames": 4,
        "original_msg": "FATAL EXCEPTION: main\n\tat ...",
        "time_since_task_start": time,
    }


class TestAppEventsCSV:
    # app_events.csv column order per the platform delta spec.
    HEADER = [
        "apk",
        "rep",
        "timeout",
        "tool",
        "time",
        "category",
        "exception_class",
        "method",
        "source",
        "message",
        "process",
        "pid",
        "fatal",
        "n_frames",
        "stack_head",
    ]

    def test_one_row_per_event_with_stack_head_only(self, tmp_path):
        """One row per diagnostic event; only stack_head (no multi-line trace)."""
        repo = _make_mock_repository()
        repo.get_diagnostic_events.return_value = [_diagnostic_event_dict()]
        task = _make_completed_task(repository=repo)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_app_events_csv([task])

        with open(os.path.join(results_dir, "app_events.csv")) as f:
            rows = list(csv.reader(f))

        assert rows[0] == self.HEADER
        assert len(rows) == 2  # header + 1 event
        row = rows[1]
        assert row[5] == "crash"  # category
        assert row[6] == "java.lang.NullPointerException"  # exception_class
        assert row[10] == "br.unb.cic.cryptoapp"  # process
        # stack_head present, but no multi-line trace leaked into the CSV
        assert "MainActivity.java:50" in row[14]
        assert "\n" not in "".join(row)

    def test_app_events_survives_resume_reconstruction(self, tmp_path):
        """INV-PLT-20: a task with no in-memory repository repopulates events from
        the reconstructed-from-logcat repository."""
        task = _make_completed_task()  # repository=None
        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)

        mock_repo = _make_mock_repository()
        mock_repo.get_diagnostic_events.return_value = [
            _diagnostic_event_dict(category="anr", time=3)
        ]
        with patch.object(
            processor, "_reconstruct_repository_from_logcat", return_value=mock_repo
        ):
            processor._generate_app_events_csv([task])

        with open(os.path.join(results_dir, "app_events.csv")) as f:
            rows = list(csv.reader(f))
        assert len(rows) == 2
        assert rows[1][5] == "anr"

    def test_empty_when_no_repository_no_logcat(self, tmp_path):
        """No repository and no logcat → header-only app_events.csv."""
        task = _make_completed_task()
        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)

        with patch.object(
            processor, "_reconstruct_repository_from_logcat", return_value=None
        ):
            processor._generate_app_events_csv([task])

        with open(os.path.join(results_dir, "app_events.csv")) as f:
            rows = list(csv.reader(f))
        assert len(rows) == 1  # header only

    def test_existing_csv_headers_unchanged(self, tmp_path):
        """INV-PLT-19: generating diagnostics does not alter the coverage/errors/
        summary headers (byte-identical to baseline)."""
        repo = _make_mock_repository(
            method_calls=[],
            errors=[],
            static_methods=[MagicMock() for _ in range(3)],
        )
        repo.get_diagnostic_events.return_value = [_diagnostic_event_dict()]
        task = _make_completed_task(repository=repo)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_coverage_csv([task])
        processor._generate_errors_csv([task])
        processor._generate_summary_csv([task])
        processor._generate_app_events_csv([task])

        def header(name):
            with open(os.path.join(results_dir, name)) as f:
                return next(csv.reader(f))

        assert header("errors.csv") == [
            "apk",
            "rep",
            "timeout",
            "tool",
            "time",
            "spec",
            "class",
            "method",
            "message",
            "unique_msg",
        ]
        # coverage/summary headers must still start with the baseline apk/rep/... keys
        assert header("coverage.csv")[:4] == ["apk", "rep", "timeout", "tool"]
        assert header("summary.csv")[:4] == ["apk", "rep", "timeout", "tool"]


# ===========================================================================
# Summary CSV Generation
# ===========================================================================


class TestSummaryCSV:
    def test_summary_csv_uses_repository_metrics_only(self, tmp_path):
        """gh58/INV-PLT-16: summary reads exclusively from
        repository.calculate_metrics().to_dict() after reconstruct. The legacy
        primary path that read task.result.coverage_metrics is removed —
        repository values take precedence even when coverage_metrics is set."""
        repo = _make_mock_repository()
        # _make_mock_repository to_dict: activity=50.0, method=25.0, mop=15.0.
        # Pass DIFFERENT coverage_metrics to prove the repository wins.
        ignored_metrics = {
            "activities_coverage": 99.0,
            "method_coverage": 99.0,
            "methods_mop_reachable_coverage": 99.0,
            "total_errors": 99,
        }
        task = _make_completed_task(repository=repo, coverage_metrics=ignored_metrics)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_summary_csv([task])

        with open(os.path.join(results_dir, "summary.csv")) as f:
            reader = list(csv.reader(f))
        header, row = reader[0], reader[1]
        # Values come from repository.to_dict(), NOT from the ignored_metrics dict.
        assert float(row[header.index("cov_act")]) == 50.0
        assert float(row[header.index("cov_method")]) == 25.0
        assert float(row[header.index("cov_reaches_target")]) == 15.0

    def test_summary_csv_fallback_to_repository(self, tmp_path):
        """Summary uses repository.calculate_metrics() when no coverage_metrics."""
        repo = _make_mock_repository()
        task = _make_completed_task(repository=repo, coverage_metrics={})

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_summary_csv([task])

        csv_path = os.path.join(results_dir, "summary.csv")
        with open(csv_path) as f:
            reader = list(csv.reader(f))
        assert len(reader) == 2

    def test_summary_csv_zeros_when_no_data(self, tmp_path):
        """No metrics and no repository → all zeros."""
        task = _make_completed_task(coverage_metrics={})

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_summary_csv([task])

        csv_path = os.path.join(results_dir, "summary.csv")
        with open(csv_path) as f:
            reader = list(csv.reader(f))
        row = reader[1]
        assert row[4] == "0"  # zeros


# ===========================================================================
# Results JSON Generation
# ===========================================================================


class TestResultsJSON:
    def test_json_hierarchical_structure(self, tmp_path):
        """JSON is structured: apk → repetition → timeout → tool."""
        tasks = [
            _make_completed_task(apk="a.apk", tool="monkey", rep=1, timeout=300),
            _make_completed_task(apk="a.apk", tool="droidbot", rep=1, timeout=300),
            _make_completed_task(apk="b.apk", tool="monkey", rep=2, timeout=600),
        ]
        for t in tasks:
            t.repository = None

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent(tasks, results_dir)
        processor._generate_results_json(tasks)

        json_path = os.path.join(results_dir, "results.json")
        with open(json_path) as f:
            data = json.load(f)

        assert "a.apk" in data
        assert "b.apk" in data
        assert "monkey" in data["a.apk"]["repetitions"]["1"]["timeouts"]["300"]["tools"]
        assert (
            "droidbot" in data["a.apk"]["repetitions"]["1"]["timeouts"]["300"]["tools"]
        )

    def test_json_task_data_with_repository(self, tmp_path):
        """Task data extracted from repository includes summary and MOP errors."""
        errors = [
            {
                "class_full_name": "Cipher",
                "method": "init",
                "spec": "Cipher_1",
                "error_type": "v",
                "message": "m",
                "unique_msg": "Cipher:::init:::Cipher_1:::v:::m",
            },
        ]
        repo = _make_mock_repository(errors=errors)
        task = _make_completed_task(repository=repo)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        task_data = processor._extract_task_data(task)

        assert task_data["summary"]["called_methods"] == 10
        assert task_data["monitored_operations_errors"]["total"] == 1
        assert len(task_data["monitored_operations_errors"]["messages"]) == 1

    def test_json_task_data_without_repository(self, tmp_path):
        """Without repository, uses coverage_metrics and reconstructs from logcat."""
        metrics = {
            "called_activities": 3,
            "called_methods": 8,
            "called_target_methods": 2,
            "activities_coverage": 60.0,
            "method_coverage": 20.0,
            "total_errors": 1,
        }
        task = _make_completed_task(coverage_metrics=metrics)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)

        with patch.object(
            processor, "_reconstruct_repository_from_logcat", return_value=None
        ):
            task_data = processor._extract_task_data(task)

        assert task_data["summary"]["called_methods"] == 8
        assert task_data["summary"]["method_coverage"] == 20.0


# ===========================================================================
# Logcat Reconstruction
# ===========================================================================


class TestLogcatReconstruction:
    def test_no_logcat_file_returns_none(self, tmp_path):
        """If logcat_file is missing, reconstruction returns None with warning."""
        task = _make_completed_task()
        task.result.logcat_file = ""  # no file

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        result = processor._reconstruct_repository_from_logcat(task)
        assert result is None

    def test_nonexistent_logcat_file_returns_none(self, tmp_path):
        task = _make_completed_task()
        task.result.logcat_file = str(tmp_path / "nonexistent.logcat")

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        result = processor._reconstruct_repository_from_logcat(task)
        assert result is None

    def test_successful_reconstruction(self, tmp_path):
        """parse_logcat_file is called and repository is returned."""
        logcat_file = tmp_path / "task.logcat"
        logcat_file.write_text("some logcat content")

        task = _make_completed_task()
        task.result.logcat_file = str(logcat_file)

        mock_repo = MagicMock()
        mock_repo.errors = [1, 2]

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)

        with patch(
            "rv_platform.components.result_processor.parse_logcat_file",
            return_value=mock_repo,
        ):
            result = processor._reconstruct_repository_from_logcat(task)

        assert result is mock_repo

    def test_parse_failure_returns_none(self, tmp_path):
        """If parse_logcat_file raises, reconstruction returns None gracefully."""
        logcat_file = tmp_path / "task.logcat"
        logcat_file.write_text("corrupt data")

        task = _make_completed_task()
        task.result.logcat_file = str(logcat_file)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)

        with patch(
            "rv_platform.components.result_processor.parse_logcat_file",
            side_effect=Exception("parse error"),
        ):
            result = processor._reconstruct_repository_from_logcat(task)

        assert result is None


# ===========================================================================
# Full Execute Pipeline
# ===========================================================================


class TestExecutePipeline:
    def test_execute_generates_all_output_files(self, tmp_path):
        """execute() produces coverage.csv, errors.csv, summary.csv, results.json, performance.csv."""
        metrics = {
            "activities_coverage": 50.0,
            "method_coverage": 25.0,
            "methods_mop_reachable_coverage": 10.0,
            "total_errors": 0,
        }
        task = _make_completed_task(coverage_metrics=metrics)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)

        with patch.object(
            processor, "_reconstruct_repository_from_logcat", return_value=None
        ):
            processor.initialize({})
            processor.execute({})
            processor.cleanup()

        expected_files = ["coverage.csv", "errors.csv", "summary.csv", "results.json"]
        for fname in expected_files:
            assert os.path.isfile(os.path.join(results_dir, fname)), f"Missing {fname}"

    def test_execute_skips_when_no_completed_tasks(self, tmp_path):
        """execute() with only error tasks produces no output files."""
        error_task = _make_error_task()
        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([error_task], results_dir)
        processor.execute({})

        # No CSV files should be generated
        assert not os.path.isfile(os.path.join(results_dir, "coverage.csv"))


# ===========================================================================
# Performance CSV Fallback
# ===========================================================================


class TestPerformanceCSVFallback:
    def test_fallback_creates_empty_performance_csv(self, tmp_path):
        """When PerformanceProcessorComponent fails, a fallback CSV is created."""
        task = _make_completed_task()
        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._create_empty_performance_csv()

        csv_path = os.path.join(results_dir, "performance.csv")
        assert os.path.isfile(csv_path)
        with open(csv_path) as f:
            reader = list(csv.reader(f))
        # header + 1 data row
        assert len(reader) == 2
        assert reader[0][0] == "apk"


# ===========================================================================
# gh58: Resume-path static_data re-parse + ASE-Journal CSV schema
# ===========================================================================


_GH58_FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "gh58")


def _make_gh58_task(tmp_path, copy_json=True, app_code_package="com.example.gh58"):
    """Create a task whose results_dir is a fresh tmp dir seeded with the gh58
    static-analysis JSON (when copy_json) and a real logcat fixture."""
    import shutil

    task = _make_completed_task(apk="sample_apk.apk")

    results_dir = tmp_path / "sample_apk.apk"
    results_dir.mkdir(parents=True, exist_ok=True)
    task.results_dir = str(results_dir)

    fixture_logcat = os.path.join(_GH58_FIXTURE_DIR, "sample_task.logcat")
    task_logcat = results_dir / "sample_apk.logcat"
    shutil.copy(fixture_logcat, task_logcat)
    task.result.logcat_file = str(task_logcat)

    if copy_json:
        shutil.copy(
            os.path.join(_GH58_FIXTURE_DIR, "sample_apk.apk.json"),
            results_dir / "sample_apk.apk.json",
        )

    # Attach a minimal mock App that exposes code_package as the test expects.
    mock_app = MagicMock()
    mock_app.code_package = app_code_package
    mock_app.name = "sample_apk"
    task.app = mock_app
    task.static_data = None  # simulate resume — must be re-parsed on demand

    return task


class TestGh58ReconstructWithStaticData:
    """RED before fix; GREEN after _reconstruct_repository_from_logcat re-parses
    static_data on demand (INV-PLT-15)."""

    def test_reconstruct_repository_from_logcat_populates_coverage_with_static_data(
        self, tmp_path
    ):
        task = _make_gh58_task(tmp_path)
        processor = ResultProcessorComponent([task], str(tmp_path / "results"))

        repo = processor._reconstruct_repository_from_logcat(task)

        assert repo is not None
        assert len(repo.get_method_calls()) >= 1
        metrics = repo.calculate_metrics().to_dict()
        assert metrics["method_coverage"] > 0
        # Expected from fixture: 5/30 methods hit ~= 16.67%
        assert metrics["method_coverage"] > 10.0

    def test_reconstruct_warns_and_zeroes_coverage_when_json_missing(
        self, tmp_path, caplog
    ):
        """FR10-ext scenario: logcat present, JSON absent → errors captured,
        coverage = 0, warning emitted. Resume path must NOT fall back silently."""
        task = _make_gh58_task(tmp_path, copy_json=False)
        processor = ResultProcessorComponent([task], str(tmp_path / "results"))

        repo = processor._reconstruct_repository_from_logcat(task)

        assert repo is not None
        # Errors still reliable (do not need static_data)
        assert len(repo.get_errors()) == 2
        # Coverage degraded to zero
        metrics = repo.calculate_metrics().to_dict()
        assert metrics["method_coverage"] == 0
        assert metrics["class_coverage"] == 0


class TestGh58ResolveStaticData:
    """Helper-level tests added after `_resolve_static_data` exists (task 2.3).
    Located here to avoid wrong-reason AttributeError during RED phase."""

    def test_resolve_static_data_reuses_task_attribute(self, tmp_path):
        """When task.static_data is already set, no re-parse occurs."""
        task = _make_completed_task()
        sentinel = MagicMock(name="cached_static_data")
        task.static_data = sentinel

        processor = ResultProcessorComponent([task], str(tmp_path / "results"))
        with patch(
            "rv_platform.components.result_processor."
            "static_analysis_parser.read_static_analysis_files"
        ) as mock_read:
            result = processor._resolve_static_data(task)
            mock_read.assert_not_called()
        assert result is sentinel

    def test_resolve_static_data_returns_none_when_json_missing(self, tmp_path):
        """Re-parse exception → warning + None; does NOT raise."""
        task = _make_gh58_task(tmp_path, copy_json=False)
        processor = ResultProcessorComponent([task], str(tmp_path / "results"))

        with patch(
            "rv_platform.components.result_processor."
            "static_analysis_parser.read_static_analysis_files",
            side_effect=FileNotFoundError("no json"),
        ):
            result = processor._resolve_static_data(task)
        assert result is None

    def test_resolve_static_data_tolerates_task_app_none(self, tmp_path):
        """task.app=None → code_package=None; parser tolerates it (no TypeError)."""
        task = _make_gh58_task(tmp_path)
        task.app = None
        task.static_data = None

        processor = ResultProcessorComponent([task], str(tmp_path / "results"))
        result = processor._resolve_static_data(task)
        assert result is not None


class TestGh58CovClassSlotFix:
    """INV-PLT-17: cov_class column must hold class_coverage, not method_coverage.
    RED before fix because line 322 of result_processor.py writes method_coverage
    into the cov_class slot."""

    def _build_repo_with_distinct_class_and_method_coverage(self):
        """Build a mock repo where calculate_metrics().to_dict() returns
        class_coverage=40.0 and method_coverage=16.67 — distinct values so the
        slot identity is auditable."""
        method_calls = [
            {
                "time": i,
                "class_name": "com.example.gh58.A",
                "method_name": f"m{i}",
                "signature": f"<com.example.gh58.A: void m{i}()>",
                "is_mop_method": True,
                "activity": None,
            }
            for i in range(5)
        ]
        repo = _make_mock_repository(method_calls=method_calls)
        # Override the metrics dict with distinct class_coverage vs method_coverage
        repo.calculate_metrics.return_value.to_dict.return_value = {
            "class_coverage": 40.0,
            "activity_coverage": 0.0,
            "method_coverage": 16.67,
            "reachable_method_coverage": 41.67,
            "mop_method_coverage": 83.33,
            "direct_mop_method_coverage": 100.0,
            "total_errors": 0,
            "unique_errors": 0,
        }
        # Static-side denominators for progressive coverage calc inside writer
        repo.get_static_methods.return_value = [f"sig{i}" for i in range(30)]
        repo.get_static_activities.return_value = []
        repo.get_target_methods.return_value = [f"sig{i}" for i in range(6)]
        return repo

    def test_coverage_csv_cov_class_uses_class_coverage_not_method_coverage(
        self, tmp_path
    ):
        repo = self._build_repo_with_distinct_class_and_method_coverage()
        task = _make_completed_task(repository=repo)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_coverage_csv([task])

        with open(os.path.join(results_dir, "coverage.csv")) as f:
            reader = list(csv.reader(f))
        header = reader[0]
        first_row = reader[1]
        cov_class_idx = header.index("cov_class")
        # cov_class MUST equal class_coverage (40.0), NOT method_coverage (16.67)
        assert float(first_row[cov_class_idx]) == 40.0, (
            f"cov_class={first_row[cov_class_idx]} but class_coverage=40.0; "
            "pre-fix code wrote method_coverage (16.67) into this slot"
        )

    def test_summary_csv_cov_class_uses_class_coverage_not_method_coverage(
        self, tmp_path
    ):
        repo = self._build_repo_with_distinct_class_and_method_coverage()
        task = _make_completed_task(repository=repo)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_summary_csv([task])

        with open(os.path.join(results_dir, "summary.csv")) as f:
            reader = list(csv.reader(f))
        header = reader[0]
        row = reader[1]
        assert "cov_class" in header, "summary.csv must include cov_class column"
        cov_class_idx = header.index("cov_class")
        assert float(row[cov_class_idx]) == 40.0


# ===========================================================================
# gh65: Resume results_dir derivation + once-per-task unresolved counter
# ===========================================================================


def _make_resume_task(tmp_path, copy_json=True):
    """Resume-shaped task obtained via a REAL Task.from_dict(Task.to_dict())
    round-trip (task 3.7), so results_dir="" and app=None exactly as on resume
    — the precondition the gh58 fixture masked by setting results_dir manually
    (D-1). The logcat + co-located SA JSON remain on disk in their per-APK dir;
    logcat_file survives serialization, so dirname(logcat_file) resolves both."""
    live = _make_gh58_task(tmp_path, copy_json=copy_json)
    revived = Task.from_dict(live.to_dict())
    assert revived.results_dir == ""
    assert revived.app is None
    return revived


class TestGh65ResumeResolution:
    """D-1 / D-3 / D-3a: derive results_dir from the logcat path, count
    unresolved static data once per task, no serialized fallback."""

    def test_resolve_static_data_derives_dir_from_logcat(self, tmp_path):
        """results_dir="" → dir derived from os.path.dirname(logcat_file); the
        co-located JSON resolves to non-empty static data (D-1, INV-PLT-15)."""
        task = _make_resume_task(tmp_path, copy_json=True)
        processor = ResultProcessorComponent([task], str(tmp_path / "results"))

        result = processor._resolve_static_data(task)

        assert result is not None
        assert result.classes.classes  # non-empty → coverage reconstructible
        assert task.id not in processor._unresolved_task_ids

    def test_missing_json_counts_and_errors_survive(self, tmp_path):
        """Logcat present, JSON absent → coverage zeroed, MOP errors preserved,
        task counted once as unresolved (D-3, D-3a)."""
        task = _make_resume_task(tmp_path, copy_json=False)
        processor = ResultProcessorComponent([task], str(tmp_path / "results"))

        result = processor._resolve_static_data(task)

        assert result is None
        assert processor._unresolved_task_ids == {task.id}

        # Errors survive the missing JSON (reconstructed from the logcat alone).
        repo = processor._reconstruct_repository_from_logcat(task)
        assert len(repo.get_errors()) == 2
        metrics = repo.calculate_metrics().to_dict()
        assert metrics["method_coverage"] == 0
        assert metrics["total_errors"] == 2  # D-2: survives empty classes

    def test_unresolved_counter_increments_once_per_task(self, tmp_path):
        """All three reconstruction call sites for one JSON-absent task →
        counter == 1 AND the parser is invoked at most once (memo holds)."""
        from rv_static_analysis.parser.static import (
            static_analysis_parser as _real_parser,
        )

        task = _make_resume_task(tmp_path, copy_json=False)
        processor = ResultProcessorComponent([task], str(tmp_path / "results"))

        cov_writer = csv.writer(open(tmp_path / "c.csv", "w", newline=""))
        err_writer = csv.writer(open(tmp_path / "e.csv", "w", newline=""))

        with patch(
            "rv_platform.components.result_processor."
            "static_analysis_parser.read_static_analysis_files",
            wraps=_real_parser.read_static_analysis_files,
        ) as spy:
            processor._write_task_coverage_data(cov_writer, task)
            processor._write_task_error_data(err_writer, task)
            processor._extract_task_data(task)

        assert len(processor._unresolved_task_ids) == 1
        assert spy.call_count <= 1  # memo short-circuits re-parse across writers

    def test_missing_json_summary_row_zeroed_no_fallback(self, tmp_path):
        """Serialized coverage_metrics present but JSON absent → summary.csv
        cov_* stay 0.00 (NO fallback), mop_errors accurate (D-3, INV-PLT-16)."""
        task = _make_resume_task(tmp_path, copy_json=False)
        # Stale serialized metrics that MUST NOT leak into the CSV.
        task.result.coverage_metrics = {
            "method_coverage": 88.0,
            "class_coverage": 77.0,
            "activity_coverage": 66.0,
            "total_errors": 99,
        }
        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_summary_csv([task])

        with open(os.path.join(results_dir, "summary.csv")) as f:
            reader = list(csv.reader(f))
        header, row = reader[0], reader[1]

        def col(name):
            return row[header.index(name)]

        assert float(col("cov_method")) == 0.00
        assert float(col("cov_class")) == 0.00
        assert float(col("cov_act")) == 0.00
        # MOP errors come from the logcat reconstruction (D-2), not the stale 99.
        assert int(col("mop_errors_total")) == 2


# ===========================================================================
# gh65 G1: Round-trip metric equivalence (live task == from_dict(to_dict))
# ===========================================================================

_GH58_CODE_PACKAGE = "com.example.gh58"


def _seed_apk_dir(tmp_path, apk_name, copy_json=True, errors=True, coverage=True):
    """Create a per-APK dir seeded with a real logcat + co-located SA JSON,
    mirroring what Task.initialize() + a live run produce on disk.

    The gh58 fixture logcat carries 5 RVSEC-COV lines and 2 RVSEC error lines;
    `coverage`/`errors` select which subset is written so G1 can parametrize
    over normal / skip-static / cov-only / errors-only shapes.
    """
    apk_dir = tmp_path / apk_name
    apk_dir.mkdir(parents=True, exist_ok=True)

    src_logcat = os.path.join(_GH58_FIXTURE_DIR, "sample_task.logcat")
    with open(src_logcat) as f:
        lines = f.readlines()
    kept = [
        ln
        for ln in lines
        if (coverage and "RVSEC-COV:" in ln) or (errors and " E RVSEC:" in ln)
    ]
    logcat_path = apk_dir / f"{apk_name}.logcat"
    logcat_path.write_text("".join(kept))

    if copy_json:
        shutil.copy(
            os.path.join(_GH58_FIXTURE_DIR, "sample_apk.apk.json"),
            apk_dir / f"{apk_name}.json",
        )
    return apk_dir, logcat_path


def _make_live_task_with_coverage(
    tmp_path, apk_name="sample_apk.apk", copy_json=True, errors=True, coverage=True
):
    """A completed task whose repository is populated exactly as a live run:
    initialize() sets results_dir + logcat_file, static_data is parsed from the
    co-located JSON, and the repository is built from the logcat."""
    config = TaskConfiguration(
        apk_name=apk_name,
        repetition=1,
        timeout=300,
        tool_config=ToolConfig(name="monkey"),
    )
    task = Task(config)
    task.initialize(str(tmp_path))  # results_dir == dirname(logcat_file)

    _, _ = _seed_apk_dir(
        tmp_path, apk_name, copy_json=copy_json, errors=errors, coverage=coverage
    )
    # initialize() named the logcat with the experiment-dimension scheme; point
    # the result at the seeded file (same per-APK dir, so dirname is identical).
    task.result.logcat_file = str(tmp_path / apk_name / f"{apk_name}.logcat")

    app = MagicMock()
    app.code_package = _GH58_CODE_PACKAGE
    app.name = apk_name
    task.set_app(app)

    task.static_data = static_analysis_parser.read_static_analysis_files(
        task.results_dir, apk_name, _GH58_CODE_PACKAGE
    )
    task.repository = parse_logcat_file(task.result.logcat_file, task.static_data)

    task.update_state(TaskState.RUNNING)
    task.update_state(TaskState.COMPLETED)
    return task


_G1_METRIC_KEYS = [
    "class_coverage",
    "activity_coverage",
    "method_coverage",
    "reachable_method_coverage",
    "mop_method_coverage",
    "direct_mop_method_coverage",
    "total_errors",
    "unique_errors",
]


class TestGh65RoundTripEquivalence:
    """G1 / INV-PLT-18: a task's metrics MUST be identical whether computed from
    the live in-memory repository or reconstructed after a real
    Task.from_dict(Task.to_dict()) round-trip (which drops results_dir/app)."""

    @pytest.mark.parametrize(
        "label,copy_json,errors,coverage",
        [
            ("mop_violations", True, True, True),
            ("skip_static", False, True, True),
            ("normal_cov_only", True, False, True),
        ],
    )
    def test_roundtrip_metric_equivalence(
        self, tmp_path, label, copy_json, errors, coverage
    ):
        live = _make_live_task_with_coverage(
            tmp_path, copy_json=copy_json, errors=errors, coverage=coverage
        )
        live_metrics = live.repository.calculate_metrics().to_dict()

        # Real serialization round-trip → results_dir="", app=None.
        revived = Task.from_dict(live.to_dict())
        assert revived.results_dir == ""
        assert revived.app is None

        processor = ResultProcessorComponent([revived], str(tmp_path / "out"))
        revived.repository = processor._reconstruct_repository_from_logcat(revived)
        assert revived.repository is not None
        revived_metrics = revived.repository.calculate_metrics().to_dict()

        for key in _G1_METRIC_KEYS:
            assert abs(live_metrics[key] - revived_metrics[key]) <= 0.01, (
                f"[{label}] {key}: live={live_metrics[key]} "
                f"revived={revived_metrics[key]}"
            )

        # Sanity: the populated cases actually exercise non-zero coverage/errors.
        if copy_json and coverage:
            assert revived_metrics["method_coverage"] > 0
        if errors:
            assert revived_metrics["total_errors"] == 2


# ===========================================================================
# gh65 G9: D-3a unresolved-accounting integrity matrix
# ===========================================================================


class TestGh65AccountingIntegrity:
    """G9 / D-3a: cartesian product of {writer permutations} × {JSON state}.
    For each cell: counter == (1 if unresolved else 0); parser invoked at most
    once (memo holds, incl. exception path); re-entry never raises; a second
    execute()-style pass re-initializes the counter."""

    # The three reconstruction call sites, as callables over (processor, task).
    @staticmethod
    def _writers(tmp_path):
        cov = csv.writer(open(tmp_path / "cov.csv", "w", newline=""))
        err = csv.writer(open(tmp_path / "err.csv", "w", newline=""))
        return {
            "coverage": lambda p, t: p._write_task_coverage_data(cov, t),
            "error": lambda p, t: p._write_task_error_data(err, t),
            "extract": lambda p, t: p._extract_task_data(t),
        }

    @pytest.mark.parametrize(
        "order",
        [
            ("coverage", "error", "extract"),
            ("error", "extract", "coverage"),
            ("extract", "coverage", "error"),
            ("error", "coverage", "extract"),
        ],
    )
    @pytest.mark.parametrize(
        "json_state",
        ["populated", "absent", "empty", "parser_raises"],
    )
    def test_d3a_accounting_matrix(self, tmp_path, order, json_state):
        copy_json = json_state == "populated"
        task = _make_resume_task(tmp_path, copy_json=copy_json)

        if json_state == "empty":
            # JSON present but with no reachability → parser yields empty classes.
            apk_dir = os.path.dirname(task.result.logcat_file)
            with open(os.path.join(apk_dir, "sample_apk.apk.json"), "w") as f:
                json.dump({"package": _GH58_CODE_PACKAGE, "reachability": []}, f)

        processor = ResultProcessorComponent([task], str(tmp_path / "out"))
        writers = self._writers(tmp_path)

        unresolved_expected = json_state != "populated"

        spy_ctx = patch(
            "rv_platform.components.result_processor."
            "static_analysis_parser.read_static_analysis_files",
            wraps=static_analysis_parser.read_static_analysis_files,
        )
        if json_state == "parser_raises":
            spy_ctx = patch(
                "rv_platform.components.result_processor."
                "static_analysis_parser.read_static_analysis_files",
                side_effect=RuntimeError("boom"),
            )

        with spy_ctx as spy:
            for name in order:
                # (c) re-entry must never raise, regardless of writer/state.
                writers[name](processor, task)
            # (b) parser invoked at most once across all writers (memo holds).
            assert spy.call_count <= 1

        # (a) counter is exactly 1 when unresolved, 0 when populated.
        assert len(processor._unresolved_task_ids) == (1 if unresolved_expected else 0)

        # (d) a fresh pass (new component, set re-initialized in execute()) starts at 0.
        processor2 = ResultProcessorComponent([task], str(tmp_path / "out2"))
        assert len(processor2._unresolved_task_ids) == 0


# ===========================================================================
# gh65 G5: golden regression vs the offline regen reference
# ===========================================================================

_GH65_GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "gh65_golden")


def _load_golden_manifest():
    with open(os.path.join(_GH65_GOLDEN_DIR, "expected.csv")) as f:
        return list(csv.DictReader(f))


class TestGh65GoldenRegression:
    """G5: ≥10 real experimento-20260604 tasks (logcat truncated to the
    exercised RVSEC/RVSEC-COV lines + SA JSON subset to reachability) reconstruct
    via the resume path to the SAME cov_method/cov_class/mop_errors the validated
    offline `scripts/regenerate_results/` pipeline produced (within 0.01). This
    locks the in-container reconstruction to the audited reference."""

    def test_golden_vs_offline_regen(self, tmp_path):
        manifest = _load_golden_manifest()
        assert len(manifest) >= 10, "G5 requires ≥10 golden samples"

        mismatches = []
        for m in manifest:
            # Resume-shaped task: results_dir="" and app=None; logcat_file points
            # at the committed fixture, with the SA JSON co-located in the same dir.
            config = TaskConfiguration(
                apk_name=m["apk"],
                repetition=int(m["rep"]),
                timeout=int(m["timeout"]),
                tool_config=ToolConfig(name="monkey"),
            )
            task = Task(config)
            assert task.results_dir == "" and task.app is None
            task.result.logcat_file = os.path.join(
                _GH65_GOLDEN_DIR, f"{m['idx']}.logcat"
            )
            task.update_state(TaskState.RUNNING)
            task.update_state(TaskState.COMPLETED)

            processor = ResultProcessorComponent([task], str(tmp_path / m["idx"]))
            repo = processor._reconstruct_repository_from_logcat(task)
            assert repo is not None, f"{m['apk']}: reconstruction returned None"
            d = repo.calculate_metrics().to_dict()

            checks = {
                "cov_method": (d["method_coverage"], float(m["cov_method"])),
                "cov_class": (d["class_coverage"], float(m["cov_class"])),
            }
            for name, (got, exp) in checks.items():
                if abs(got - exp) > 0.01:
                    mismatches.append(f"{m['apk']} {name}: got={got:.2f} exp={exp:.2f}")
            if d["total_errors"] != int(m["mop_errors_total"]):
                mismatches.append(
                    f"{m['apk']} mop_errors_total: got={d['total_errors']} "
                    f"exp={m['mop_errors_total']}"
                )
            if d["unique_errors"] != int(m["mop_errors_unique"]):
                mismatches.append(
                    f"{m['apk']} mop_errors_unique: got={d['unique_errors']} "
                    f"exp={m['mop_errors_unique']}"
                )

        assert not mismatches, "Golden mismatches vs offline regen:\n" + "\n".join(
            mismatches
        )
