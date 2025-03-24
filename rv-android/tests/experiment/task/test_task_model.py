# tests/experiment/test_task_model.py
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from rvandroid.app import App
from rvandroid.domain.coverage import LogcatRepository
from rvandroid.domain.log import RvCoverageLog, RvErrorLog
# Import the classes we want to test
from rvandroid.experiment.task.task_model import TaskStatus, TaskConfiguration, TaskResult, Task


class TestTaskStatus:
    """Tests for the TaskStatus enumeration"""

    def test_task_status_values(self):
        """Test that TaskStatus contains all expected states with correct values"""
        assert TaskStatus.CREATED.value == 1
        assert TaskStatus.CONFIGURED.value == 2
        assert TaskStatus.RUNNING.value == 3
        assert TaskStatus.EXECUTED.value == 4
        assert TaskStatus.ERROR.value == 5
        assert TaskStatus.CANCELED.value == 6


class TestTaskConfiguration:
    """Tests for TaskConfiguration data class"""

    def test_basic_configuration(self):
        """Test creating a basic configuration with mandatory fields"""
        config = TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=60,
            tool_name="monkey"
        )

        assert config.apk_name == "test.apk"
        assert config.repetition == 1
        assert config.timeout == 60
        assert config.tool_name == "monkey"
        # Check default values
        assert config.no_window is False
        assert config.clean_logcat is True
        assert config.skip_installation is False
        assert config.device_id == "emulator-5554"
        assert config.export_to_csv is True

    def test_full_configuration(self):
        """Test creating a configuration with all options specified"""
        config = TaskConfiguration(
            apk_name="test.apk",
            repetition=2,
            timeout=120,
            tool_name="droidbot",
            no_window=True,
            clean_logcat=False,
            skip_installation=True,
            device_id="custom-device-id",
            export_to_csv=False
        )

        assert config.apk_name == "test.apk"
        assert config.repetition == 2
        assert config.timeout == 120
        assert config.tool_name == "droidbot"
        assert config.no_window is True
        assert config.clean_logcat is False
        assert config.skip_installation is True
        assert config.device_id == "custom-device-id"
        assert config.export_to_csv is False

    def test_string_representation(self):
        """Test string representation of TaskConfiguration"""
        config = TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=60,
            tool_name="monkey"
        )

        expected = "TaskConfiguration(apk=test.apk, rep=1, timeout=60, tool=monkey)"
        assert str(config) == expected


class TestTaskResult:
    """Tests for TaskResult data class"""

    def test_default_values(self):
        """Test that TaskResult initializes with correct default values"""
        result = TaskResult()

        assert result.status == TaskStatus.CREATED
        assert result.start_time is None
        assert result.end_time is None
        assert result.execution_time_seconds == 0
        assert result.error_message is None
        assert result.logcat_file == ""
        assert result.trace_file == ""
        assert isinstance(result.coverage_metrics, dict)
        assert len(result.coverage_metrics) == 0
        assert isinstance(result.detected_errors, list)
        assert len(result.detected_errors) == 0

    def test_update_execution_time(self):
        """Test that execution time is correctly calculated"""
        result = TaskResult()
        result.start_time = datetime(2023, 1, 1, 10, 0, 0)
        result.end_time = datetime(2023, 1, 1, 10, 0, 30)

        result.update_execution_time()
        assert result.execution_time_seconds == 30

    def test_update_execution_time_missing_times(self):
        """Test that execution time is not updated when times are missing"""
        result = TaskResult()
        # No start time
        result.end_time = datetime(2023, 1, 1, 10, 0, 30)
        result.update_execution_time()
        assert result.execution_time_seconds == 0

        # No end time
        result.start_time = datetime(2023, 1, 1, 10, 0, 0)
        result.end_time = None
        result.update_execution_time()
        assert result.execution_time_seconds == 0

    def test_to_dict(self):
        """Test that TaskResult converts to dictionary correctly"""
        result = TaskResult()
        result.status = TaskStatus.EXECUTED
        result.start_time = datetime(2023, 1, 1, 10, 0, 0)
        result.end_time = datetime(2023, 1, 1, 10, 0, 30)
        result.execution_time_seconds = 30
        result.error_message = "Test error"
        result.logcat_file = "/path/to/logcat.log"
        result.trace_file = "/path/to/trace.log"
        result.coverage_metrics = {"method_coverage": 75.5}
        result.detected_errors = [{"error_type": "TestError", "message": "Test error message"}]

        result_dict = result.to_dict()

        assert result_dict["status"] == "EXECUTED"
        assert result_dict["start_time"] == result.start_time.isoformat()
        assert result_dict["end_time"] == result.end_time.isoformat()
        assert result_dict["execution_time_seconds"] == 30
        assert result_dict["error_message"] == "Test error"
        assert result_dict["logcat_file"] == "/path/to/logcat.log"
        assert result_dict["trace_file"] == "/path/to/trace.log"
        assert result_dict["coverage_metrics"] == {"method_coverage": 75.5}
        assert result_dict["detected_errors_count"] == 1


class TestTask:
    """Tests for Task class"""

    @pytest.fixture
    def basic_config(self):
        """Fixture providing a basic task configuration"""
        return TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=60,
            tool_name="monkey"
        )

    @pytest.fixture
    def mock_app(self):
        """Fixture providing a mock App object"""
        app = MagicMock(spec=App)
        app.name = "test.apk"
        app.package_name = "com.test.app"
        return app

    @pytest.fixture
    def mock_repository(self):
        """Fixture providing a mock LogcatRepository"""
        repo = MagicMock(spec=LogcatRepository)
        metrics = MagicMock()
        metrics.to_dict.return_value = {
            "method_coverage": 75.0,
            "activity_coverage": 80.0,
            "mop_method_coverage": 60.0,
            "unique_errors": 2,
            "called_methods": 100
        }
        repo.calculate_metrics.return_value = metrics
        return repo

    def test_task_initialization(self, basic_config):
        """Test that Task initializes correctly with a configuration"""
        task = Task(basic_config)

        assert task.id > 0  # Should get an ID
        assert task.config == basic_config
        assert task.result.status == TaskStatus.CREATED
        assert task.app is None
        assert task.results_dir == ""
        assert task.static_data is None
        assert isinstance(task.repository, LogcatRepository)

    def test_task_id_increment(self, basic_config):
        """Test that task IDs are incremented"""
        # Save the current counter
        original_next_id = Task._next_id

        try:
            # Reset counter for test
            Task._next_id = 1

            task1 = Task(basic_config)
            task2 = Task(basic_config)

            assert task1.id == 1
            assert task2.id == 2
        finally:
            # Restore counter
            Task._next_id = original_next_id

    def test_add_error(self, basic_config):
        """Test adding an error to the task repository"""
        task = Task(basic_config)
        error_log = MagicMock(spec=RvErrorLog)

        with patch.object(task.repository, 'register_rv_error') as mock_register:
            task.add_error(error_log)
            mock_register.assert_called_once_with(error_log)

    def test_add_method_call(self, basic_config):
        """Test adding a method call to the task repository"""
        task = Task(basic_config)
        coverage_log = MagicMock(spec=RvCoverageLog)

        with patch.object(task.repository, 'register_method_call') as mock_register:
            task.add_method_call(coverage_log)
            mock_register.assert_called_once_with(coverage_log)

    def test_update_coverage(self, basic_config, mock_repository):
        """Test updating coverage metrics from repository"""
        task = Task(basic_config)
        task.repository = mock_repository
        task.static_data = MagicMock()  # Just need this to exist

        task.update_coverage()

        assert task.result.coverage_metrics["method_coverage"] == 75.0
        assert task.result.coverage_metrics["activities_coverage"] == 80.0
        assert task.result.coverage_metrics["methods_jca_reachable_coverage"] == 60.0
        assert task.result.coverage_metrics["total_errors"] == 2
        assert task.result.coverage_metrics["total_method_calls"] == 100

    def test_update_coverage_no_data(self, basic_config, caplog):
        """Test update coverage with missing repository or static_data"""
        task = Task(basic_config)
        task.repository = None
        task.static_data = None

        task.update_coverage()

        # Should log a warning
        assert "Cannot update coverage: No repository or static data available" in caplog.text

    def test_get_repository(self, basic_config):
        """Test getting the task's repository"""
        task = Task(basic_config)
        original_repo = task.repository

        # Test with existing repository
        repo = task.get_repository()
        assert repo is original_repo

        # Test creating new repository
        task.repository = None
        repo = task.get_repository()
        assert isinstance(repo, LogcatRepository)

    def test_get_repository_from_logcat(self, basic_config, tmp_path):
        """Test getting repository by parsing logcat file"""
        task = Task(basic_config)
        task.repository = None

        # Create temp logcat file
        logcat_file = tmp_path / "test.logcat"
        logcat_file.write_text("Test logcat content")

        # Set the logcat file path and mock parse_logcat_file
        task.result.logcat_file = str(logcat_file)

        mock_repo = MagicMock(spec=LogcatRepository)
        with patch('rvandroid.parser.log.logcat_parser.parse_logcat_file', return_value=mock_repo) as mock_parse:
            repo = task.get_repository()

            mock_parse.assert_called_once_with(str(logcat_file))
            assert repo is mock_repo

    def test_initialize(self, basic_config, tmp_path):
        """Test task initialization with base results directory"""
        task = Task(basic_config)
        base_dir = str(tmp_path)

        task.initialize(base_dir)

        assert task.result.status == TaskStatus.CONFIGURED
        assert task.results_dir == os.path.join(base_dir, "test.apk")
        assert os.path.exists(task.results_dir)

        # Check that output file paths are correctly set
        expected_base = "test.apk__1__60__monkey"
        assert task.result.logcat_file.endswith(f"{expected_base}.logcat")
        assert task.result.trace_file.endswith(f"{expected_base}.trace")

    def test_set_app(self, basic_config, mock_app):
        """Test setting the app instance"""
        task = Task(basic_config)
        task.set_app(mock_app)

        assert task.app is mock_app

    def test_mark_started(self, basic_config):
        """Test marking a task as started"""
        task = Task(basic_config)
        task.mark_started()

        assert task.result.status == TaskStatus.RUNNING
        assert task.result.start_time is not None
        assert isinstance(task.result.start_time, datetime)

    def test_mark_completed(self, basic_config):
        """Test marking a task as completed with deterministic execution time."""
        task = Task(basic_config)

        # Directly patch the update_execution_time method to ensure deterministic behavior
        with patch.object(task.result, 'update_execution_time') as mock_update:
            # Set up the method to update execution_time_seconds to a known value
            def set_execution_time(*args, **kwargs):
                task.result.execution_time_seconds = 30

            mock_update.side_effect = set_execution_time

            # Mark the task as completed
            task.mark_completed()

            # Verify status
            assert task.result.status == TaskStatus.EXECUTED
            # Verify execution time was set to our mocked value
            assert task.result.execution_time_seconds == 30
            # Verify update_execution_time was called
            mock_update.assert_called_once()

    def test_mark_error(self, basic_config):
        """Test marking a task as failed with error, using deterministic execution time."""
        task = Task(basic_config)

        # Directly patch the update_execution_time method to ensure deterministic behavior
        with patch.object(task.result, 'update_execution_time') as mock_update:
            # Set up the method to update execution_time_seconds to a known value
            def set_execution_time(*args, **kwargs):
                task.result.execution_time_seconds = 45

            mock_update.side_effect = set_execution_time

            # Mark task with error
            error_message = "Test error message"
            task.mark_error(error_message)

            # Verify status and error message
            assert task.result.status == TaskStatus.ERROR
            assert task.result.error_message == error_message
            # Verify execution time was set to our mocked value
            assert task.result.execution_time_seconds == 45
            # Verify update_execution_time was called
            mock_update.assert_called_once()

    def test_executed_property(self, basic_config):
        """Test the executed property"""
        task = Task(basic_config)
        assert not task.executed  # Default status is CREATED

        task.result.status = TaskStatus.EXECUTED
        assert task.executed

        task.result.status = TaskStatus.ERROR
        assert not task.executed

    def test_failed_property(self, basic_config):
        """Test the failed property"""
        task = Task(basic_config)
        assert not task.failed  # Default status is CREATED

        task.result.status = TaskStatus.ERROR
        assert task.failed

        task.result.status = TaskStatus.EXECUTED
        assert not task.failed

    def test_string_representation(self, basic_config):
        """Test string representation of Task"""
        task = Task(basic_config)
        task.id = 42  # Force ID for consistent testing

        expected = "Task[id=42, TaskConfiguration(apk=test.apk, rep=1, timeout=60, tool=monkey), status=CREATED]"
        assert str(task) == expected
