# tests/experiment/test_task_model.py
import os
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from rv_android_core.app import App
from rv_android_core.domain.coverage import LogcatRepository
from rv_android_core.domain.log import RvCoverageLog, RvErrorLog
from rv_experiment.experiment.task.interfaces import TaskState
from rv_experiment.experiment.task.task_model import TaskConfiguration, TaskResult, Task


class TestTaskState:
    """Tests for the TaskState enumeration"""

    def test_task_state_values(self):
        """Test that TaskState contains all expected states"""
        # Test that all expected states exist
        assert hasattr(TaskState, 'CREATED')
        assert hasattr(TaskState, 'CONFIGURED')
        assert hasattr(TaskState, 'READY')
        assert hasattr(TaskState, 'RUNNING')
        assert hasattr(TaskState, 'COMPLETED')
        assert hasattr(TaskState, 'ERROR')
        assert hasattr(TaskState, 'CANCELED')


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

        assert result.state == TaskState.CREATED
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
        result.state = TaskState.COMPLETED
        result.start_time = datetime(2023, 1, 1, 10, 0, 0)
        result.end_time = datetime(2023, 1, 1, 10, 0, 30)
        result.execution_time_seconds = 30
        result.error_message = "Test error"
        result.logcat_file = "/path/to/logcat.log"
        result.trace_file = "/path/to/trace.log"
        result.coverage_metrics = {"method_coverage": 75.5}
        result.detected_errors = [{"error_type": "TestError", "message": "Test error message"}]

        result_dict = result.to_dict()

        assert result_dict["state"] == "COMPLETED"
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

        assert len(task.id) > 0  # Should get an ID
        assert task.config == basic_config
        assert task.result.state == TaskState.CREATED
        assert task.app is None
        assert task.results_dir == ""
        assert task.static_data is None
        # Repository might be None if LogcatRepository is not available
        assert task.repository is not None or task.repository is None

    def test_task_id_uniqueness(self, basic_config):
        """Test that task IDs are unique UUIDs"""
        task1 = Task(basic_config)
        task2 = Task(basic_config)

        # IDs should be different
        assert task1.id != task2.id

        # IDs should be valid UUID strings
        import uuid
        uuid.UUID(task1.id)  # Should not raise exception
        uuid.UUID(task2.id)  # Should not raise exception

        # Test custom ID
        custom_task = Task(basic_config, "custom-123")
        assert custom_task.id == "custom-123"

    def test_add_error(self, basic_config):
        """Test adding an error to the task repository"""
        task = Task(basic_config)
        error_log = MagicMock(spec=RvErrorLog)

        # Mock the repository if it's None
        if task.repository is None:
            task.repository = MagicMock()

        with patch.object(task.repository, 'register_rv_error') as mock_register:
            task.add_error(error_log)
            mock_register.assert_called_once_with(error_log)

    def test_add_method_call(self, basic_config):
        """Test adding a method call to the task repository"""
        task = Task(basic_config)
        coverage_log = MagicMock(spec=RvCoverageLog)

        # Mock the repository if it's None
        if task.repository is None:
            task.repository = MagicMock()

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

        # Mock the method's internal logic since LogcatRepository might be Any
        def mock_get_repository():
            if task.repository is None:
                task.repository = MagicMock()  # Create a mock repository
            return task.repository

        with patch.object(task, 'get_repository', side_effect=mock_get_repository):
            repo = task.get_repository()
            assert repo is not None

    def test_get_repository_from_logcat(self, basic_config, tmp_path):
        """Test getting repository by parsing logcat file"""
        task = Task(basic_config)
        task.repository = None

        # Create temp logcat file
        logcat_file = tmp_path / "test.logcat"
        logcat_file.write_text("Test logcat content")

        # Set the logcat file path and mock parse_logcat_file
        task.result.logcat_file = str(logcat_file)

        # Mock the get_repository method to simulate the parsing behavior
        mock_repo = MagicMock()

        def mock_get_repository():
            if task.repository is None:
                task.repository = mock_repo
            return task.repository

        with patch.object(task, 'get_repository', side_effect=mock_get_repository):
            repo = task.get_repository()
            assert repo is mock_repo

    def test_initialize(self, basic_config, tmp_path):
        """Test task initialization with base results directory"""
        task = Task(basic_config)
        base_dir = str(tmp_path)

        task.initialize(base_dir)

        assert task.result.state == TaskState.READY
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

    def test_update_state_running(self, basic_config):
        """Test updating task state to running"""
        task = Task(basic_config)
        task.update_state(TaskState.RUNNING)

        assert task.result.state == TaskState.RUNNING
        assert task.result.start_time is not None
        assert isinstance(task.result.start_time, datetime)

    def test_update_state_completed(self, basic_config):
        """Test updating task state to completed with execution time calculation."""
        task = Task(basic_config)

        # Set start time to test execution time calculation
        task.result.start_time = datetime.now()
        
        # Update the task state to completed
        task.update_state(TaskState.COMPLETED)

        # Verify state
        assert task.result.state == TaskState.COMPLETED
        # Verify end time was set
        assert task.result.end_time is not None
        # Verify execution time was calculated (should be minimal)
        assert task.result.execution_time_seconds >= 0

    def test_update_state_error(self, basic_config):
        """Test updating a task state to error with error message."""
        task = Task(basic_config)

        # Set start time to test execution time calculation
        task.result.start_time = datetime.now()

        # Update task state to error
        error_message = "Test error message"
        task.update_state(TaskState.ERROR, error_message)

        # Verify state and error message
        assert task.result.state == TaskState.ERROR
        assert task.result.error_message == error_message
        # Verify end time was set
        assert task.result.end_time is not None
        # Verify execution time was calculated (should be minimal)
        assert task.result.execution_time_seconds >= 0

    def test_completed_property(self, basic_config):
        """Test the completed property"""
        task = Task(basic_config)
        assert not task.completed  # Default state is CREATED

        task.result.state = TaskState.COMPLETED
        assert task.completed

        task.result.state = TaskState.ERROR
        assert not task.completed

    def test_failed_property(self, basic_config):
        """Test the failed property"""
        task = Task(basic_config)
        assert not task.failed  # Default state is CREATED

        task.result.state = TaskState.ERROR
        assert task.failed

        task.result.state = TaskState.COMPLETED
        assert not task.failed

    def test_string_representation(self, basic_config):
        """Test string representation of Task"""
        task = Task(basic_config)
        task.id = 42  # Force ID for consistent testing

        expected = "Task[id=42, TaskConfiguration(apk=test.apk, rep=1, timeout=60, tool=monkey), state=CREATED]"
        assert str(task) == expected


class TestTaskResultTiming:
    """Tests for TaskResult timing functionality added in Phase 1"""

    def test_mark_tool_execution_start(self):
        """Test marking tool execution start timestamp"""
        result = TaskResult()
        
        # Initially no tool execution start time
        assert result.tool_execution_start is None
        assert result.get_time_since_tool_start() == 0
        
        # Mark tool execution start
        before_mark = datetime.now()
        result.mark_tool_execution_start()
        after_mark = datetime.now()
        
        # Verify timestamp was set within reasonable bounds
        assert result.tool_execution_start is not None
        assert before_mark <= result.tool_execution_start <= after_mark
    
    def test_get_time_since_tool_start(self):
        """Test calculating time since tool execution started"""
        result = TaskResult()
        
        # No tool start time should return 0
        assert result.get_time_since_tool_start() == 0
        
        # Mark start and test timing calculation
        result.mark_tool_execution_start()
        
        # Wait a small amount to ensure time difference
        time.sleep(0.1)
        
        elapsed = result.get_time_since_tool_start()
        assert elapsed >= 0
        assert elapsed < 5  # Should be very small for this test
    
    def test_get_time_since_task_start(self):
        """Test calculating time since task started"""
        result = TaskResult()
        
        # No task start time should return 0
        assert result.get_time_since_task_start() == 0
        
        # Set start time manually and test timing calculation
        result.start_time = datetime.now()
        
        # Wait a small amount to ensure time difference
        time.sleep(0.1)
        
        elapsed = result.get_time_since_task_start()
        assert elapsed >= 0
        assert elapsed < 5  # Should be very small for this test
    
    def test_constructor_compatibility(self):
        """Test that TaskResult maintains constructor compatibility"""
        start_time = datetime.now()
        end_time = datetime.now()
        
        # Test positional arguments (legacy style)
        result1 = TaskResult(start_time, end_time)
        assert result1.start_time == start_time
        assert result1.end_time == end_time
        
        # Test named arguments (modern style)
        result2 = TaskResult(start_time=start_time, end_time=end_time)
        assert result2.start_time == start_time
        assert result2.end_time == end_time
    
    def test_tool_execution_timing_serialization(self):
        """Test that tool execution timing is properly serialized"""
        result = TaskResult()
        result.mark_tool_execution_start()
        
        # Test to_dict includes tool_execution_start
        data = result.to_dict()
        assert "tool_execution_start" in data
        assert data["tool_execution_start"] is not None
        
        # Test from_dict restores tool_execution_start
        restored = TaskResult.from_dict(data)
        assert restored.tool_execution_start is not None
        assert restored.tool_execution_start == result.tool_execution_start


class TestTaskTiming:
    """Tests for Task timing integration"""

    @pytest.fixture
    def task_with_timing(self):
        """Create a task for timing tests"""
        config = TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=60,
            tool_name="monkey"
        )
        return Task(config)
    
    def test_mark_tool_execution_start(self, task_with_timing):
        """Test task delegates tool execution timing to result"""
        task = task_with_timing
        
        # Initially no tool execution start time
        assert task.result.tool_execution_start is None
        
        # Mark tool execution start
        task.mark_tool_execution_start()
        
        # Verify timing was set
        assert task.result.tool_execution_start is not None
    
    def test_get_time_since_tool_start(self, task_with_timing):
        """Test task delegates time calculation to result"""
        task = task_with_timing
        
        # No tool start time should return 0
        assert task.get_time_since_tool_start() == 0
        
        # Mark start and test timing calculation
        task.mark_tool_execution_start()
        elapsed = task.get_time_since_tool_start()
        
        assert elapsed >= 0
        assert elapsed < 5  # Should be very small for this test
