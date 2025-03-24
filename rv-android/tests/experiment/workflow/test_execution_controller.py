# tests/experiment/workflow/test_execution_controller.py
import os
from unittest.mock import Mock, patch

import pytest

from rvandroid.app import App
from rvandroid.experiment.event.bus import EventBus
from rvandroid.experiment.task.task_storage import TaskStorage
from rvandroid.experiment.workflow.execution_controller import ExecutionController
from rvandroid.tools.tool_spec import AbstractTool


class TestExecutionController:
    """
    Test suite for the ExecutionController class that manages task execution during experiments.

    These tests verify:
    - Proper initialization of the controller
    - Update of task storage
    - Setup of experiment execution
    - Running of tasks
    - Copying of static analysis files
    - Retrieval of statistics and coverage reports
    """

    @pytest.fixture
    def mock_storage(self):
        """Fixture for a mock TaskStorage."""
        storage = Mock(spec=TaskStorage)
        storage.storage_file = "/tmp/tasks.json"
        return storage

    @pytest.fixture
    def mock_event_bus(self):
        """Fixture for a mock EventBus."""
        return Mock(spec=EventBus)

    @pytest.fixture
    def execution_controller(self, mock_storage, mock_event_bus):
        """Fixture for an ExecutionController instance with mocked dependencies."""
        with patch('rvandroid.experiment.workflow.execution_controller.ExecutionManager') as mock_exec_manager_cls:
            mock_exec_manager = Mock()
            mock_exec_manager_cls.return_value = mock_exec_manager

            # Set up the get_tasks method to return an empty list by default
            mock_exec_manager.get_tasks.return_value = []

            controller = ExecutionController(mock_storage, mock_event_bus)
            # Replace the auto-created execution manager with our mock
            controller.execution_manager = mock_exec_manager
            return controller

    def test_initialization(self, mock_storage, mock_event_bus):
        """Test that ExecutionController initializes correctly with provided dependencies."""
        with patch('rvandroid.experiment.workflow.execution_controller.ExecutionManager'):
            controller = ExecutionController(mock_storage, mock_event_bus)

            assert controller.task_storage == mock_storage
            assert controller.event_bus == mock_event_bus
            assert controller.base_results_dir == os.path.dirname(mock_storage.storage_file)
            assert controller.has_errors is False

    def test_update_storage(self, execution_controller, mock_storage):
        """Test updating the task storage used by the controller."""
        new_storage = Mock(spec=TaskStorage)
        new_storage.storage_file = "/tmp/new_tasks.json"

        execution_controller.update_storage(new_storage)

        assert execution_controller.task_storage == new_storage
        assert execution_controller.base_results_dir == os.path.dirname(new_storage.storage_file)

    def test_setup(self, execution_controller):
        """Test setting up experiment execution with specified parameters."""
        # Mock apps and tools
        mock_apps = [Mock(spec=App) for _ in range(2)]
        mock_tools = [Mock(spec=AbstractTool) for _ in range(2)]
        for i, tool in enumerate(mock_tools):
            tool.name = f"tool_{i}"

        # Mock the task_storage.get_tasks to return an empty list
        execution_controller.task_storage.get_tasks = Mock(return_value=[])

        # Execute setup
        execution_controller.setup(
            apks=mock_apps,
            repetitions=3,
            timeouts=[30, 60],
            tools=mock_tools,
            no_window=True
        )

        # Verify apps and tools were registered
        for app in mock_apps:
            execution_controller.execution_manager.register_app.assert_any_call(app)

        for tool in mock_tools:
            execution_controller.execution_manager.register_tool.assert_any_call(tool)

    def test_setup_with_existing_tasks(self, execution_controller):
        """Test setup when tasks already exist."""
        # Mock tasks and task_storage to simulate existing tasks
        mock_tasks = [Mock(), Mock()]
        execution_controller.task_storage.get_tasks = Mock(return_value=mock_tasks)

        # Mock apps and tools
        mock_apps = [Mock(spec=App)]
        mock_tools = [Mock(spec=AbstractTool)]
        mock_tools[0].name = "tool_0"

        # Execute setup
        execution_controller.setup(
            apks=mock_apps,
            repetitions=1,
            timeouts=[60],
            tools=mock_tools
        )

        # Verify apps and tools were registered
        execution_controller.execution_manager.register_app.assert_called_once_with(mock_apps[0])
        execution_controller.execution_manager.register_tool.assert_called_once_with(mock_tools[0])

        # Verify setup_execution was not called since tasks already exist
        execution_controller.execution_manager.setup_execution.assert_not_called()

    def test_run_success(self, execution_controller):
        """Test running tasks with success."""
        # Configure execution manager to return success
        execution_controller.execution_manager.run_all_tasks.return_value = True

        # Execute run
        result = execution_controller.run()

        # Verify execution manager was called
        execution_controller.execution_manager.run_all_tasks.assert_called_once()
        execution_controller.execution_manager.get_statistics.assert_called_once()

        # Verify result
        assert result is True
        assert execution_controller.has_errors is False

    def test_run_failure(self, execution_controller):
        """Test running tasks with failure."""
        # Configure execution manager to return failure
        execution_controller.execution_manager.run_all_tasks.return_value = False

        # Execute run
        result = execution_controller.run()

        # Verify execution manager was called
        execution_controller.execution_manager.run_all_tasks.assert_called_once()
        execution_controller.execution_manager.get_statistics.assert_called_once()

        # Verify result
        assert result is False
        assert execution_controller.has_errors is True

    @patch('rvandroid.experiment.workflow.execution_controller.os.makedirs')
    @patch('rvandroid.experiment.workflow.execution_controller.os.path.exists')
    @patch('rvandroid.experiment.workflow.execution_controller.shutil.copy')
    def test_copy_static_analysis_files_success(self, mock_copy, mock_exists, mock_makedirs, execution_controller):
        """Test copying static analysis files successfully."""
        # Configure mocks
        mock_exists.return_value = True

        # Execute copy
        result = execution_controller.copy_static_analysis_files("test_app.apk", "/tmp/results/test_app")

        # Verify directory was created
        mock_makedirs.assert_called_once_with("/tmp/results/test_app", exist_ok=True)

        # Verify files were checked and copied
        assert mock_exists.call_count == 4  # One for each extension
        assert mock_copy.call_count == 4  # One for each extension that exists

        # Verify result
        assert result is True

    @patch('rvandroid.experiment.workflow.execution_controller.os.makedirs')
    @patch('rvandroid.experiment.workflow.execution_controller.os.path.exists')
    @patch('rvandroid.experiment.workflow.execution_controller.shutil.copy')
    def test_copy_static_analysis_files_no_files(self, mock_copy, mock_exists, mock_makedirs, execution_controller):
        """Test copying static analysis files when no files exist."""
        # Configure mocks
        mock_exists.return_value = False

        # Execute copy
        result = execution_controller.copy_static_analysis_files("test_app.apk", "/tmp/results/test_app")

        # Verify directory was created
        mock_makedirs.assert_called_once_with("/tmp/results/test_app", exist_ok=True)

        # Verify files were checked but not copied
        assert mock_exists.call_count == 4  # One for each extension
        assert mock_copy.call_count == 0  # No files exist

        # Verify result
        assert result is False

    @patch('rvandroid.experiment.workflow.execution_controller.os.makedirs')
    def test_copy_static_analysis_files_exception(self, mock_makedirs, execution_controller):
        """Test handling exceptions when copying static analysis files."""
        # Configure mocks to raise an exception
        mock_makedirs.side_effect = Exception("Test exception")

        # Execute copy
        result = execution_controller.copy_static_analysis_files("test_app.apk", "/tmp/results/test_app")

        # Verify result
        assert result is False

    def test_get_statistics(self, execution_controller):
        """Test retrieving execution statistics."""
        # Configure execution manager to return statistics
        expected_stats = {"total": 10, "completed": 5, "running": True}
        execution_controller.execution_manager.get_statistics.return_value = expected_stats

        # Get statistics
        stats = execution_controller.get_statistics()

        # Verify execution manager was called
        execution_controller.execution_manager.get_statistics.assert_called_once()

        # Verify result
        assert stats == expected_stats

    def test_get_coverage_report(self, execution_controller):
        """Test retrieving coverage report."""
        # Configure execution manager to return coverage report
        expected_report = {
            "summary": {"avg_method_coverage": 75.5},
            "tasks": {"task1": {"method_coverage": 80.0}}
        }
        execution_controller.execution_manager.get_coverage_report.return_value = expected_report

        # Get coverage report
        report = execution_controller.get_coverage_report()

        # Verify execution manager was called
        execution_controller.execution_manager.get_coverage_report.assert_called_once()

        # Verify result
        assert report == expected_report
