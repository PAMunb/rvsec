# tests/experiment/test_execution_manager.py
import os
from datetime import datetime
from unittest.mock import MagicMock, patch, Mock

import pytest

from rv_android_core.app import App
from rv_android_core.event.bus import EventBus, EventType
from rv_experiment.experiment.execution_manager import ExecutionManager
from rv_experiment.experiment.task.task_model import Task
from rv_experiment.experiment.task.interfaces import TaskState
from rv_experiment.experiment.task.storage import TaskStorage
from rv_experiment.config import ExperimentConfiguration
from rv_android_core.tools.abstract_tool import AbstractTool


class TestExecutionManager:
    """Test cases for ExecutionManager class."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for test files."""
        return str(tmp_path)

    @pytest.fixture
    def mock_storage(self, temp_dir):
        """Create a mock TaskStorage."""
        mock_storage = MagicMock(spec=TaskStorage)
        mock_storage.storage_file = os.path.join(temp_dir, "tasks.json")
        mock_storage.get_pending_tasks.return_value = []
        mock_storage.get_tasks.return_value = []
        mock_storage.add_task = MagicMock()
        mock_storage.save = MagicMock()
        mock_storage.update_task = MagicMock()
        return mock_storage

    @pytest.fixture
    def mock_event_bus(self):
        """Create a mock EventBus."""
        mock_bus = MagicMock(spec=EventBus)
        mock_bus.publish_experiment_event = MagicMock()
        return mock_bus

    @pytest.fixture
    def mock_config(self, temp_dir):
        """Create a mock ExperimentConfiguration."""
        mock_config = MagicMock(spec=ExperimentConfiguration)
        mock_config.output_dir = temp_dir
        mock_config.get_instrumented_dir.return_value = os.path.join(temp_dir, "instrumented")
        mock_config.get_timestamp_string.return_value = "20230101_120000"
        return mock_config

    @pytest.fixture
    def execution_manager(self, mock_storage, mock_config, mock_event_bus, temp_dir):
        """Create an ExecutionManager for testing."""
        manager = ExecutionManager(mock_storage, mock_config, mock_event_bus)
        manager.base_results_dir = temp_dir
        return manager

    @pytest.fixture
    def mock_app(self):
        """Create a mock App."""
        mock_app = MagicMock(spec=App)
        mock_app.name = "test.apk"
        mock_app.apk_path = "/path/to/test.apk"
        return mock_app

    @pytest.fixture
    def mock_tool(self):
        """Create a mock Tool."""
        mock_tool = MagicMock(spec=AbstractTool)
        mock_tool.name = "test_tool"
        return mock_tool

    def test_initialization(self, mock_storage, mock_config, mock_event_bus):
        """Test ExecutionManager initialization."""
        execution_manager = ExecutionManager(mock_storage, mock_config, mock_event_bus)
        
        assert execution_manager.storage == mock_storage
        assert execution_manager.config == mock_config
        assert execution_manager.event_bus == mock_event_bus
        assert len(execution_manager.tools) == 0
        assert len(execution_manager.apks) == 0
        assert execution_manager.is_running is False

    def test_register_tool(self, execution_manager, mock_tool):
        """Test tool registration."""
        execution_manager.register_tool(mock_tool)
        
        assert mock_tool.name in execution_manager.tools
        assert execution_manager.tools[mock_tool.name] == mock_tool

    def test_register_app(self, execution_manager, mock_app):
        """Test app registration."""
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
        mock_task.initialize = MagicMock()
        mock_task.set_app = MagicMock()

        # Patch the Task class to return our mock
        with patch('rv_experiment.experiment.execution_manager.Task', return_value=mock_task):
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

    @patch('rv_experiment.experiment.execution_manager.datetime')
    def test_run_all_tasks_success(self, mock_datetime, execution_manager, mock_event_bus):
        """Test running all tasks with success."""
        # Setup mock datetime
        mock_now = datetime(2023, 1, 1, 12, 0, 0)
        mock_datetime.now.return_value = mock_now

        # Create proper mock tasks with required attributes
        mock_task1 = MagicMock(spec=Task)
        mock_task1.id = "task-1"
        mock_task1.config = MagicMock()
        mock_task1.config.apk_name = "app1"
        mock_task1.config.tool_name = "tool1"

        # Setup storage to return pending tasks
        execution_manager.storage.get_pending_tasks.return_value = [mock_task1]

        # Mock the run_task method to return success
        execution_manager.run_task = MagicMock(return_value=True)

        # Execute the method
        result = execution_manager.run_all_tasks()

        # Verify success
        assert result is True
        assert execution_manager.is_running is False
        
        # Verify event publishing
        mock_event_bus.publish_experiment_event.assert_any_call(
            EventType.EXPERIMENT_STARTED,
            experiment_id="experiment-20230101120000",
            message="Starting execution of tasks",
            source="ExecutionManager"
        )
        mock_event_bus.publish_experiment_event.assert_any_call(
            EventType.EXPERIMENT_COMPLETED,
            experiment_id="experiment-20230101120000",
            message="Execution completed successfully",
            source="ExecutionManager"
        )

    def test_run_task_success(self, execution_manager, mock_app, mock_tool, temp_dir):
        """Test running a single task successfully."""
        # Setup mock task with necessary attributes
        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-1"
        mock_task.config = MagicMock()
        mock_task.config.apk_name = mock_app.name
        mock_task.config.tool_name = mock_tool.name
        mock_task.app = mock_app
        mock_task.results_dir = os.path.join(temp_dir, "app1")
        mock_task.result = MagicMock()
        mock_task.result.state = TaskState.READY
        
        # Configure coverage_metrics properly to avoid format string errors
        mock_task.result.coverage_metrics = {
            'method_coverage': 75.5,
            'activities_coverage': 80.2,
            'total_errors': 2
        }

        # Register app and tool
        execution_manager.register_app(mock_app)
        execution_manager.register_tool(mock_tool)

        # Mock the copy_static_analysis_files method
        execution_manager.copy_static_analysis_files = MagicMock(return_value=True)

        # Mock TaskExecutor and components
        mock_executor = MagicMock()
        mock_executor.execute.return_value = True

        # Mock component classes
        with patch('rv_experiment.experiment.execution_manager.TaskExecutor', return_value=mock_executor), \
             patch('rv_experiment.experiment.execution_manager.StaticAnalysisComponent') as mock_static, \
             patch('rv_experiment.experiment.execution_manager.CoverageComponent') as mock_coverage, \
             patch('rv_experiment.experiment.execution_manager.EmulatorComponent') as mock_emulator, \
             patch('rv_experiment.experiment.execution_manager.LogcatComponent') as mock_logcat, \
             patch('rv_experiment.experiment.execution_manager.ToolExecutionComponent') as mock_tool_exec:
            
            # Configure component mocks
            mock_static_instance = MagicMock()
            mock_static.return_value = mock_static_instance
            mock_coverage_instance = MagicMock()
            mock_coverage.return_value = mock_coverage_instance
            mock_emulator_instance = MagicMock()
            mock_emulator.return_value = mock_emulator_instance
            mock_logcat_instance = MagicMock()
            mock_logcat.return_value = mock_logcat_instance
            mock_tool_exec_instance = MagicMock()
            mock_tool_exec.return_value = mock_tool_exec_instance
            
            # Execute the method
            result = execution_manager.run_task(mock_task)

        # Verify success
        assert result is True
        
        # Verify TaskExecutor was created and components registered
        mock_executor.register_component.assert_any_call(mock_static_instance)
        mock_executor.register_component.assert_any_call(mock_coverage_instance)
        mock_executor.register_component.assert_any_call(mock_emulator_instance)
        mock_executor.register_component.assert_any_call(mock_logcat_instance)
        mock_executor.register_component.assert_any_call(mock_tool_exec_instance)
        mock_executor.execute.assert_called_once()
        
        # Verify storage update
        execution_manager.storage.update_task.assert_called_with(mock_task)

    def test_run_task_missing_tool(self, execution_manager, mock_app):
        """Test running a task when tool is not found."""
        # Setup mock task
        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-1"
        mock_task.config = MagicMock()
        mock_task.config.apk_name = mock_app.name
        mock_task.config.tool_name = "missing_tool"
        mock_task.update_state = MagicMock()
        mock_task.result = MagicMock()
        mock_task.result.state = TaskState.READY
        mock_task.results_dir = "/tmp/test_results"
        mock_task.result.coverage_metrics = {}

        # Register only app (not tool)
        execution_manager.register_app(mock_app)

        # Execute the method
        result = execution_manager.run_task(mock_task)

        # Verify failure
        assert result is False
        mock_task.update_state.assert_called_with(TaskState.ERROR, "Tool not found: missing_tool")
        execution_manager.storage.update_task.assert_called_with(mock_task)

    def test_run_task_missing_app(self, execution_manager, mock_tool):
        """Test running a task when app is not found."""
        # Setup mock task
        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-1"
        mock_task.config = MagicMock()
        mock_task.config.apk_name = "missing_app"
        mock_task.config.tool_name = mock_tool.name
        mock_task.update_state = MagicMock()
        mock_task.result = MagicMock()
        mock_task.result.state = TaskState.READY
        mock_task.results_dir = "/tmp/test_results"
        mock_task.result.coverage_metrics = {}

        # Register only tool (not app)
        execution_manager.register_tool(mock_tool)

        # Execute the method
        result = execution_manager.run_task(mock_task)

        # Verify failure
        assert result is False
        mock_task.update_state.assert_called_with(TaskState.ERROR, "App not found: missing_app")
        execution_manager.storage.update_task.assert_called_with(mock_task)

    def test_run_task_execution_error(self, execution_manager, mock_app, mock_tool, temp_dir):
        """Test running a task when execution fails."""
        # Setup mock task
        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-1"
        mock_task.config = MagicMock()
        mock_task.config.apk_name = mock_app.name
        mock_task.config.tool_name = mock_tool.name
        mock_task.app = mock_app
        mock_task.results_dir = os.path.join(temp_dir, "app1")
        mock_task.update_state = MagicMock()
        mock_task.result = MagicMock()
        mock_task.result.state = TaskState.READY
        mock_task.result.coverage_metrics = {}

        # Register app and tool
        execution_manager.register_app(mock_app)
        execution_manager.register_tool(mock_tool)

        # Mock copy_static_analysis_files
        execution_manager.copy_static_analysis_files = MagicMock(return_value=True)

        # Mock TaskExecutor to raise exception
        mock_executor = MagicMock()
        mock_executor.execute.side_effect = Exception("Execution error")

        with patch('rv_experiment.experiment.execution_manager.TaskExecutor', return_value=mock_executor), \
             patch('rv_experiment.experiment.execution_manager.StaticAnalysisComponent'), \
             patch('rv_experiment.experiment.execution_manager.CoverageComponent'), \
             patch('rv_experiment.experiment.execution_manager.EmulatorComponent'), \
             patch('rv_experiment.experiment.execution_manager.LogcatComponent'), \
             patch('rv_experiment.experiment.execution_manager.ToolExecutionComponent'):
            
            # Execute the method
            result = execution_manager.run_task(mock_task)

        # Verify failure
        assert result is False
        mock_task.update_state.assert_called_with(TaskState.ERROR, "Execution error")
        execution_manager.storage.update_task.assert_called_with(mock_task)

    @patch('rv_experiment.experiment.execution_manager.os')
    @patch('rv_experiment.experiment.execution_manager.shutil')
    def test_copy_static_analysis_files(self, mock_shutil, mock_os, execution_manager):
        """Test copying static analysis files."""
        # Setup mocks
        mock_os.path.exists.return_value = True
        mock_os.makedirs = MagicMock()
        
        # Execute the method
        result = execution_manager.copy_static_analysis_files("test.apk", "/results/dir")
        
        # Verify success
        assert result is True
        mock_os.makedirs.assert_called_with("/results/dir", exist_ok=True)

    def test_get_statistics(self, execution_manager):
        """Test getting execution statistics."""
        # Setup mock tasks with different statuses
        mock_task1 = MagicMock()
        mock_task1.result.state = TaskState.COMPLETED
        mock_task2 = MagicMock()
        mock_task2.result.state = TaskState.ERROR
        mock_task3 = MagicMock()
        mock_task3.result.state = TaskState.CREATED

        execution_manager.storage.get_tasks.return_value = [mock_task1, mock_task2, mock_task3]

        # Execute the method
        stats = execution_manager.get_statistics()

        # Verify statistics
        assert stats["total"] == 3
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["pending"] == 1
        assert stats["running"] is False