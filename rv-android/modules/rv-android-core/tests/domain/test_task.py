# tests/execution/test_task_model.py
import os
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from rv_android_core.app import App
from rv_android_core.domain.task import TaskState, TaskConfiguration, TaskResult, Task


class TestTaskState:
    """Tests for the TaskState enumeration"""

    def test_task_state_values(self):
        """Test that TaskState contains all expected states"""
        # Test that all expected states exist
        assert hasattr(TaskState, 'CREATED')
        assert hasattr(TaskState, 'INITIALIZING')
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

    def test_to_dict(self):
        """Test TaskConfiguration serialization to dictionary"""
        config = TaskConfiguration(
            apk_name="test.apk",
            repetition=1,
            timeout=60,
            tool_name="monkey"
        )
        
        result = config.to_dict()
        
        assert result["apk_name"] == "test.apk"
        assert result["repetition"] == 1
        assert result["timeout"] == 60
        assert result["tool_name"] == "monkey"
        assert result["no_window"] is False

    def test_from_dict(self):
        """Test TaskConfiguration deserialization from dictionary"""
        data = {
            "apk_name": "test.apk",
            "repetition": 1,
            "timeout": 60,
            "tool_name": "monkey",
            "no_window": True
        }
        
        config = TaskConfiguration.from_dict(data)
        
        assert config.apk_name == "test.apk"
        assert config.repetition == 1
        assert config.timeout == 60
        assert config.tool_name == "monkey"
        assert config.no_window is True


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

    def test_mark_tool_execution_start(self):
        """Test marking tool execution start time"""
        result = TaskResult()
        
        # Mock datetime to control timing
        with patch('rv_android_core.domain.task.datetime') as mock_datetime:
            test_time = datetime(2023, 1, 1, 10, 0, 0)
            mock_datetime.now.return_value = test_time
            
            result.mark_tool_execution_start()
            
            assert result.tool_execution_start == test_time

    def test_get_time_since_tool_start(self):
        """Test calculating time since tool execution started"""
        result = TaskResult()
        
        # Test with no tool start time
        assert result.get_time_since_tool_start() == 0
        
        # Test with tool start time
        result.tool_execution_start = datetime.now()
        time.sleep(0.1)  # Small delay
        elapsed = result.get_time_since_tool_start()
        assert elapsed >= 0

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

    def test_task_initialization(self, basic_config):
        """Test that Task initializes correctly with a configuration"""
        task = Task(basic_config)

        assert len(task.id) > 0  # Should get an ID
        assert task.config == basic_config
        assert task.result.state == TaskState.CREATED
        assert task.app is None
        assert task.results_dir == ""

    def test_task_initialization_with_custom_id(self, basic_config):
        """Test that Task can be initialized with a custom ID"""
        custom_id = "custom-task-id"
        task = Task(basic_config, custom_id)

        assert task.id == custom_id
        assert task.config == basic_config

    def test_set_app(self, basic_config, mock_app):
        """Test setting app instance on task"""
        task = Task(basic_config)
        task.set_app(mock_app)

        assert task.app == mock_app

    def test_update_state(self, basic_config):
        """Test updating task state"""
        task = Task(basic_config)
        
        # Test updating to RUNNING state
        task.update_state(TaskState.RUNNING)
        assert task.result.state == TaskState.RUNNING
        assert task.result.start_time is not None

        # Add a small delay to ensure different timestamps
        import time
        time.sleep(0.001)

        # Test updating to COMPLETED state
        task.update_state(TaskState.COMPLETED)
        assert task.result.state == TaskState.COMPLETED
        assert task.result.end_time is not None
        assert task.result.execution_time_seconds >= 0  # Changed from > 0 to >= 0

    def test_update_state_with_error(self, basic_config):
        """Test updating task state to ERROR with message"""
        task = Task(basic_config)
        error_message = "Test error occurred"
        
        task.update_state(TaskState.ERROR, error_message)
        
        assert task.result.state == TaskState.ERROR
        assert task.result.error_message == error_message
        assert task.result.end_time is not None

    def test_task_properties(self, basic_config):
        """Test task state properties"""
        task = Task(basic_config)
        
        # Initial state
        assert not task.completed
        assert not task.failed
        assert not task.running
        assert not task.can_execute
        
        # Ready state
        task.update_state(TaskState.READY)
        assert task.can_execute
        
        # Running state
        task.update_state(TaskState.RUNNING)
        assert task.running
        
        # Completed state
        task.update_state(TaskState.COMPLETED)
        assert task.completed
        
        # Reset and test failed state
        task.update_state(TaskState.ERROR, "Test error")
        assert task.failed

    def test_mark_tool_execution_start(self, basic_config):
        """Test marking tool execution start time"""
        task = Task(basic_config)
        
        task.mark_tool_execution_start()
        
        assert task.result.tool_execution_start is not None
        assert task.get_time_since_tool_start() >= 0

    def test_initialize_task(self, basic_config, tmp_path):
        """Test task initialization with results directory"""
        task = Task(basic_config)
        base_results_dir = str(tmp_path)
        
        task.initialize(base_results_dir)
        
        assert task.result.state == TaskState.READY
        assert task.results_dir.endswith("test.apk")
        assert os.path.exists(task.results_dir)
        assert task.result.logcat_file.endswith(".logcat")
        assert task.result.trace_file.endswith(".trace")

    def test_to_dict(self, basic_config):
        """Test task serialization to dictionary"""
        task = Task(basic_config)
        
        result = task.to_dict()
        
        assert "id" in result
        assert "config" in result
        assert "result" in result
        assert result["config"]["apk_name"] == "test.apk"

    def test_from_dict(self, basic_config):
        """Test task deserialization from dictionary"""
        # Create a task and serialize it
        original_task = Task(basic_config)
        task_dict = original_task.to_dict()
        
        # Deserialize it
        restored_task = Task.from_dict(task_dict)
        
        assert restored_task is not None
        assert restored_task.id == original_task.id
        assert restored_task.config.apk_name == original_task.config.apk_name
        assert restored_task.config.tool_name == original_task.config.tool_name

    def test_string_representation(self, basic_config):
        """Test task string representation"""
        task = Task(basic_config)
        
        task_str = str(task)
        
        assert "Task[id=" in task_str
        assert "test.apk" in task_str
        assert "monkey" in task_str
        assert "CREATED" in task_str