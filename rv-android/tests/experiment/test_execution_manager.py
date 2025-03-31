# tests/experiment/test_execution_manager.py
import os
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pytest

from rvandroid.app import App
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.execution_manager import ExecutionManager
from rvandroid.experiment.task.task_model import Task, TaskStatus
from rvandroid.experiment.task.task_storage import TaskStorage
from rvandroid.tools.tool_spec import AbstractTool


class TestExecutionManager:
    """Tests for the ExecutionManager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_storage(self, temp_dir):
        """Create a mock TaskStorage for testing."""
        mock = MagicMock(spec=TaskStorage)
        # Use temporary directory instead of /test
        mock.storage_file = os.path.join(temp_dir, "tasks.json")
        return mock

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock EventBus for testing."""
        return MagicMock(spec=EventBus)

    @pytest.fixture
    def mock_app(self):
        """Create a mock App for testing."""
        mock = MagicMock(spec=App)
        mock.name = "test_app"
        return mock

    @pytest.fixture
    def mock_tool(self):
        """Create a mock Tool for testing."""
        mock = MagicMock(spec=AbstractTool)
        mock.name = "test_tool"
        return mock

    @pytest.fixture
    def execution_manager(self, mock_storage, mock_event_bus):
        """Create an ExecutionManager instance for testing."""
        return ExecutionManager(mock_storage, mock_event_bus)

    def test_initialization(self, mock_storage, mock_event_bus):
        """Test ExecutionManager initialization."""
        manager = ExecutionManager(mock_storage, mock_event_bus)

        assert manager.storage == mock_storage
        assert manager.event_bus == mock_event_bus
        assert manager.base_results_dir == os.path.dirname(mock_storage.storage_file)
        assert not manager.is_running
        assert manager.current_task is None
        assert manager.running_timestamp is None
        assert isinstance(manager.tools, dict)
        assert isinstance(manager.apks, dict)

    def test_register_tool(self, execution_manager, mock_tool):
        """Test registering a tool with the manager."""
        execution_manager.register_tool(mock_tool)

        assert mock_tool.name in execution_manager.tools
        assert execution_manager.tools[mock_tool.name] == mock_tool

    def test_register_app(self, execution_manager, mock_app):
        """Test registering an app with the manager."""
        execution_manager.register_app(mock_app)

        assert mock_app.name in execution_manager.apks
        assert execution_manager.apks[mock_app.name] == mock_app

    def test_setup_execution(self, execution_manager, mock_app, mock_tool, temp_dir):
        """Test setting up tasks for execution."""
        # Prepare test data
        apks = [mock_app]
        repetitions = 2
        timeouts = [30, 60]
        tools = [mock_tool]

        # Create a proper Task mockup to be returned from Task constructor
        mock_task = MagicMock(spec=Task)
        mock_task.config = MagicMock()
        mock_task.config.apk_name = mock_app.name
        mock_task.config.tool_name = mock_tool.name

        # Patch the Task class to return our mock
        with patch('rvandroid.experiment.execution_manager.Task', return_value=mock_task):
            # Execute the method
            execution_manager.setup_execution(
                apks=apks,
                repetitions=repetitions,
                timeouts=timeouts,
                tools=tools
            )

            # Verify app and tool registration
            assert mock_app.name in execution_manager.apks
            assert mock_tool.name in execution_manager.tools

            # Verify task creation and save
            assert execution_manager.storage.add_task.called
            assert execution_manager.storage.save.called

    @patch('rvandroid.experiment.execution_manager.datetime')
    def test_run_all_tasks_success(self, mock_datetime, execution_manager, mock_event_bus):
        """Test running all tasks with success."""
        # Setup mock datetime
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        # Create proper mock tasks with required attributes
        mock_task1 = MagicMock(spec=Task)
        mock_task1.id = 1
        mock_task1.config = MagicMock()
        mock_task1.config.apk_name = "app1"
        mock_task1.config.tool_name = "tool1"

        mock_task2 = MagicMock(spec=Task)
        mock_task2.id = 2
        mock_task2.config = MagicMock()
        mock_task2.config.apk_name = "app2"
        mock_task2.config.tool_name = "tool2"

        execution_manager.storage.get_pending_tasks.return_value = [mock_task1, mock_task2]

        # Setup the run_task method to return True (success)
        execution_manager.run_task = MagicMock(return_value=True)

        # Execute the method
        result = execution_manager.run_all_tasks()

        # Verify results
        assert result is True
        assert execution_manager.run_task.call_count == 2
        execution_manager.run_task.assert_has_calls([call(mock_task1), call(mock_task2)])

        # Verify events
        assert mock_event_bus.publish_experiment_event.call_count == 2
        # First call should be EXPERIMENT_STARTED
        assert mock_event_bus.publish_experiment_event.call_args_list[0][0][0] == EventType.EXPERIMENT_STARTED
        # Last call should be EXPERIMENT_COMPLETED
        assert mock_event_bus.publish_experiment_event.call_args_list[1][0][0] == EventType.EXPERIMENT_COMPLETED

    @patch('rvandroid.experiment.execution_manager.datetime')
    def test_run_all_tasks_with_errors(self, mock_datetime, execution_manager, mock_event_bus):
        """Test running all tasks with some errors."""
        # Setup mock datetime
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        # Create proper mock tasks with required attributes
        mock_task1 = MagicMock(spec=Task)
        mock_task1.id = 1
        mock_task1.config = MagicMock()
        mock_task1.config.apk_name = "app1"
        mock_task1.config.tool_name = "tool1"

        mock_task2 = MagicMock(spec=Task)
        mock_task2.id = 2
        mock_task2.config = MagicMock()
        mock_task2.config.apk_name = "app2"
        mock_task2.config.tool_name = "tool2"

        execution_manager.storage.get_pending_tasks.return_value = [mock_task1, mock_task2]

        # Setup the run_task method to return False for the second task (error)
        execution_manager.run_task = MagicMock(side_effect=[True, False])

        # Execute the method
        result = execution_manager.run_all_tasks()

        # Verify results
        assert result is False  # Should return False if any task fails
        assert execution_manager.run_task.call_count == 2

        # Verify events
        assert mock_event_bus.publish_experiment_event.call_count == 2
        # Last call should be EXPERIMENT_FAILED because of the error
        assert mock_event_bus.publish_experiment_event.call_args_list[1][0][0] == EventType.EXPERIMENT_FAILED

    def test_run_all_tasks_already_running(self, execution_manager):
        """Test running all tasks when already running."""
        # Set the running flag
        execution_manager.is_running = True

        # Execute the method
        result = execution_manager.run_all_tasks()

        # Verify results
        assert result is False
        execution_manager.storage.get_pending_tasks.assert_not_called()

    def test_run_task_success(self, execution_manager, mock_app, mock_tool, temp_dir):
        """Test running a single task successfully."""
        # Setup mock task with necessary attributes
        mock_task = MagicMock(spec=Task)
        mock_task.id = 1
        mock_task.config = MagicMock()
        mock_task.config.apk_name = mock_app.name
        mock_task.config.tool_name = mock_tool.name
        mock_task.app = mock_app
        mock_task.results_dir = os.path.join(temp_dir, "app1")

        # Register app and tool
        execution_manager.register_app(mock_app)
        execution_manager.register_tool(mock_tool)

        # Mock the copy_static_analysis_files method
        execution_manager.copy_static_analysis_files = MagicMock(return_value=True)

        # Mock TaskExecutor
        mock_executor = MagicMock()
        mock_executor.execute.return_value = True

        with patch('rvandroid.experiment.execution_manager.TaskExecutor', return_value=mock_executor):
            # Execute the method
            result = execution_manager.run_task(mock_task)

            # Verify results
            assert result is True
            execution_manager.copy_static_analysis_files.assert_called_once_with(
                mock_app.name, mock_task.results_dir
            )
            mock_executor.execute.assert_called_once()
            execution_manager.storage.update_task.assert_called_once_with(mock_task)

    def test_run_task_missing_tool(self, execution_manager, mock_app):
        """Test running a task with a missing tool."""
        # Setup mock task with necessary attributes
        mock_task = MagicMock(spec=Task)
        mock_task.id = 1
        mock_task.config = MagicMock()
        mock_task.config.apk_name = mock_app.name
        mock_task.config.tool_name = "missing_tool"

        # Register app but not the tool
        execution_manager.register_app(mock_app)

        # Execute the method
        result = execution_manager.run_task(mock_task)

        # Verify results
        assert result is False
        mock_task.mark_error.assert_called_once()
        assert "Tool not found" in mock_task.mark_error.call_args[0][0]
        execution_manager.storage.update_task.assert_called_once_with(mock_task)

    def test_run_task_missing_app(self, execution_manager, mock_tool):
        """Test running a task with a missing app."""
        # Setup mock task with necessary attributes
        mock_task = MagicMock(spec=Task)
        mock_task.id = 1
        mock_task.config = MagicMock()
        mock_task.config.apk_name = "missing_app"
        mock_task.config.tool_name = mock_tool.name

        # Register tool but not the app
        execution_manager.register_tool(mock_tool)

        # Execute the method
        result = execution_manager.run_task(mock_task)

        # Verify results
        assert result is False
        mock_task.mark_error.assert_called_once()
        assert "App not found" in mock_task.mark_error.call_args[0][0]
        execution_manager.storage.update_task.assert_called_once_with(mock_task)

    def test_run_task_execution_error(self, execution_manager, mock_app, mock_tool, temp_dir):
        """Test running a task that encounters an execution error."""
        # Setup mock task with necessary attributes
        mock_task = MagicMock(spec=Task)
        mock_task.id = 1
        mock_task.config = MagicMock()
        mock_task.config.apk_name = mock_app.name
        mock_task.config.tool_name = mock_tool.name
        mock_task.app = mock_app
        mock_task.results_dir = os.path.join(temp_dir, "app1")

        # Register app and tool
        execution_manager.register_app(mock_app)
        execution_manager.register_tool(mock_tool)

        # Mock the copy_static_analysis_files method
        execution_manager.copy_static_analysis_files = MagicMock(return_value=True)

        # Mock TaskExecutor to raise an exception
        mock_executor = MagicMock()
        mock_executor.execute.side_effect = Exception("Execution error")

        with patch('rvandroid.experiment.execution_manager.TaskExecutor', return_value=mock_executor):
            # Execute the method
            result = execution_manager.run_task(mock_task)

            # Verify results
            assert result is False
            mock_task.mark_error.assert_called_once()
            assert "Execution error" in mock_task.mark_error.call_args[0][0]
            execution_manager.storage.update_task.assert_called_once_with(mock_task)

    def test_copy_static_analysis_files_success(self, execution_manager, temp_dir):
        """Test copying static analysis files successfully."""
        apk_name = "test_app.apk"
        app_results_dir = os.path.join(temp_dir, "app")

        # Mock os.path.exists to return True for all files
        with patch('os.path.exists', return_value=True), \
                patch('os.makedirs') as mock_makedirs, \
                patch('shutil.copy') as mock_copy:
            # Execute the method
            result = execution_manager.copy_static_analysis_files(apk_name, app_results_dir)

            # Verify results
            assert result is True
            mock_makedirs.assert_called_once_with(app_results_dir, exist_ok=True)
            assert mock_copy.call_count == 4  # One for each extension

    def test_copy_static_analysis_files_no_files(self, execution_manager, temp_dir):
        """Test copying static analysis files when no files exist."""
        apk_name = "test_app.apk"
        app_results_dir = os.path.join(temp_dir, "app")

        # Mock os.path.exists to return False for all files
        with patch('os.path.exists', return_value=False), \
                patch('os.makedirs') as mock_makedirs, \
                patch('shutil.copy') as mock_copy:
            # Execute the method
            result = execution_manager.copy_static_analysis_files(apk_name, app_results_dir)

            # Verify results
            assert result is False
            mock_makedirs.assert_called_once_with(app_results_dir, exist_ok=True)
            mock_copy.assert_not_called()

    def test_get_statistics(self, execution_manager):
        """Test getting execution statistics."""
        # Setup mock tasks with result attributes
        mock_task1 = MagicMock(spec=Task)
        mock_task1.result = MagicMock()
        mock_task1.result.status = TaskStatus.EXECUTED

        mock_task2 = MagicMock(spec=Task)
        mock_task2.result = MagicMock()
        mock_task2.result.status = TaskStatus.ERROR

        mock_task3 = MagicMock(spec=Task)
        mock_task3.result = MagicMock()
        mock_task3.result.status = TaskStatus.CREATED

        execution_manager.storage.get_tasks.return_value = [mock_task1, mock_task2, mock_task3]
        execution_manager.current_task = mock_task1

        # Mock datetime for elapsed time calculation
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        current_time = datetime(2023, 1, 1, 12, 1, 30)  # 1 minute 30 seconds later

        execution_manager.running_timestamp = start_time

        with patch('rvandroid.experiment.execution_manager.datetime') as mock_datetime:
            mock_datetime.now.return_value = current_time

            # Execute the method
            stats = execution_manager.get_statistics()

            # Verify results
            assert stats["total"] == 3
            assert stats["completed"] == 1
            assert stats["failed"] == 1
            assert stats["pending"] == 1
            assert stats["pct_complete"] == round((1 * 100 / 3), 2)  # 33.33%
            assert stats["current_task"] == str(mock_task1)
            assert stats["running"] == execution_manager.is_running

            # Don't check exact string format, just verify it contains minutes and seconds
            assert "m" in stats["elapsed"]
            assert "s" in stats["elapsed"]
            # Alternatively, check that it contains the expected values
            assert "1" in stats["elapsed"]  # 1 minute
            assert "30" in stats["elapsed"]  # 30 seconds

    def test_get_coverage_report(self, execution_manager):
        """Test getting a coverage report."""
        # Setup mock tasks with proper attributes
        mock_task1 = MagicMock(spec=Task)

        # Set up result attribute
        mock_task1.result = MagicMock()
        mock_task1.result.status = TaskStatus.EXECUTED
        mock_task1.result.coverage_metrics = {
            "method_coverage": 75.0,
            "activities_coverage": 80.0,
            "methods_jca_reachable_coverage": 60.0,
            "total_errors": 2,
            "total_method_calls": 150
        }
        mock_task1.result.execution_time_seconds = 120

        # Set up config attribute
        mock_task1.config = MagicMock()
        mock_task1.config.apk_name = "app1"
        mock_task1.config.tool_name = "tool1"
        mock_task1.config.repetition = 1
        mock_task1.config.timeout = 30

        # Create a mock repository for the task
        mock_repository = MagicMock()
        mock_metrics = MagicMock()
        mock_metrics.to_dict.return_value = {
            "method_coverage": 75.0,
            "activity_coverage": 80.0,
            "mop_method_coverage": 60.0,
            "unique_errors": 2,
            "called_methods": 150
        }
        mock_repository.calculate_metrics.return_value = mock_metrics

        # Assign the repository to the task
        mock_task1.repository = mock_repository

        # Set up the storage to return our task
        execution_manager.storage.get_tasks.return_value = [mock_task1]

        # Execute the method
        report = execution_manager.get_coverage_report()

        # Verify results
        assert report["summary"]["total_tasks"] == 1
        assert report["summary"]["completed_tasks"] == 1

        # Check that the task data is in the report
        task_key = f"{mock_task1.config.apk_name}_{mock_task1.config.tool_name}_{mock_task1.config.repetition}_{mock_task1.config.timeout}"
        assert task_key in report["tasks"]

        task_data = report["tasks"][task_key]
        assert task_data["method_coverage"] == 75.0
        assert task_data["activities_coverage"] == 80.0
        assert task_data["mop_coverage"] == 60.0
        assert task_data["errors"] == 2
        assert task_data["method_calls"] == 150
        assert task_data["execution_time"] == 120

    def test_format_time(self):
        """Test the _format_time utility method."""
        format_time = ExecutionManager._format_time

        assert format_time(30) == "30s"  # Seconds only
        assert format_time(90) == "1m 30s"  # Minutes and seconds
        assert format_time(3665) == "1h 1m 5s"  # Hours, minutes, seconds
