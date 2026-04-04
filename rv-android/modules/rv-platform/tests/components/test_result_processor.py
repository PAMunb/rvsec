"""
Tests for ResultProcessorComponent — CSV/JSON generation, task filtering,
coverage/error/summary data writing, and logcat reconstruction fallback.
"""

import csv
import json
import os
from unittest.mock import MagicMock, patch

from rv_android_core.domain.task import Task, TaskConfiguration, TaskState, ToolConfig
from rv_platform.components.result_processor import ResultProcessorComponent

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
    repo.get_mop_methods.return_value = []

    metrics = MagicMock()
    metrics.called_activities = 2
    metrics.called_methods = 10
    metrics.called_mop_methods = 3
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

    def test_coverage_csv_fallback_without_repository(self, tmp_path):
        """Tasks without repository use coverage_metrics fallback (single row)."""
        metrics = {
            "method_coverage": 25.0,
            "activities_coverage": 50.0,
            "mop_coverage": 10.0,
        }
        task = _make_completed_task(coverage_metrics=metrics)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_coverage_csv([task])

        csv_path = os.path.join(results_dir, "coverage.csv")
        with open(csv_path) as f:
            reader = list(csv.reader(f))
        # header + 1 fallback row
        assert len(reader) == 2
        assert reader[1][8] == "25.0"  # cov_class = method_coverage


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
# Summary CSV Generation
# ===========================================================================


class TestSummaryCSV:
    def test_summary_csv_from_coverage_metrics(self, tmp_path):
        """Summary uses task.result.coverage_metrics when available."""
        metrics = {
            "activities_coverage": 75.0,
            "method_coverage": 30.0,
            "methods_jca_reachable_coverage": 20.0,
            "total_errors": 5,
        }
        task = _make_completed_task(coverage_metrics=metrics)

        results_dir = str(tmp_path / "results")
        processor = ResultProcessorComponent([task], results_dir)
        processor._generate_summary_csv([task])

        csv_path = os.path.join(results_dir, "summary.csv")
        with open(csv_path) as f:
            reader = list(csv.reader(f))
        assert len(reader) == 2
        row = reader[1]
        assert row[4] == "75.0"  # cov_act
        assert row[5] == "30.0"  # cov_method
        assert row[6] == "20.0"  # cov_rv_method
        assert float(row[7]) == 5  # errors (may be int or float in CSV)

    def test_summary_csv_fallback_to_repository(self, tmp_path):
        """Summary falls back to repository.calculate_metrics() when no coverage_metrics."""
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
            "called_mop_methods": 2,
            "activities_coverage": 60.0,
            "method_coverage": 20.0,
            "mop_coverage": 10.0,
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
            "methods_jca_reachable_coverage": 10.0,
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
