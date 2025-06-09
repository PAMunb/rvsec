from unittest.mock import MagicMock, patch

import pytest

from rv_android_core.app import App
from rv_android_core.event.bus import EventBus
from rv_experiment.experiment.task.storage import TaskStorage
from rv_experiment.experiment.workflow.execution_controller import ExecutionController
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_experiment.config import ExperimentConfiguration


class DummyTool(AbstractTool):
    """Dummy tool for testing purposes."""

    def __init__(self):
        super().__init__("DummyTool", "A tool for testing", "dummy_pattern")

    def execute_tool_specific_logic(self, task, app):
        pass


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    return MagicMock(spec=EventBus)


@pytest.fixture
def mock_task_storage(tmp_path):
    """Create a mock task storage with a temporary file."""
    storage_file = tmp_path / "tasks.json"
    return TaskStorage(str(storage_file))


@pytest.fixture
def mock_app():
    """Create a mock App instance for testing."""
    mock_app = MagicMock(spec=App)
    mock_app.name = "test_app"
    mock_app.path = "/path/to/test_app.apk"
    return mock_app


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock ExperimentConfiguration."""
    mock_config = MagicMock(spec=ExperimentConfiguration)
    mock_config.output_dir = str(tmp_path)
    mock_config.get_instrumented_dir.return_value = str(tmp_path / "instrumented")
    mock_config.get_timestamp_string.return_value = "20230101_120000"
    return mock_config


@pytest.fixture
def execution_controller(mock_task_storage, mock_config, mock_event_bus):
    """Create an ExecutionController instance for testing."""
    return ExecutionController(mock_task_storage, mock_config, mock_event_bus)


def test_setup_adds_tasks_to_storage(execution_controller, mock_app):
    """Test that setup method adds tasks to storage."""
    tools = [DummyTool()]
    repetitions = 2
    timeouts = [30, 60]

    # Mock the setup_execution method to add tasks
    with patch.object(execution_controller, 'execution_manager') as mock_manager:
        execution_controller.setup(
            apks=[mock_app],
            repetitions=repetitions,
            timeouts=timeouts,
            tools=tools
        )

        mock_manager.setup_execution.assert_called_once()
        call_args = mock_manager.setup_execution.call_args[1]

        assert call_args['apks'] == [mock_app]
        assert call_args['repetitions'] == repetitions
        assert call_args['timeouts'] == timeouts
        assert call_args['tools'] == tools


def test_setup_preserves_existing_tasks(execution_controller, mock_app):
    """Test that existing tasks are preserved during setup."""
    tools = [DummyTool()]
    repetitions = 2
    timeouts = [30, 60]

    # Mock the setup_execution method
    with patch.object(execution_controller, 'execution_manager') as mock_manager:
        execution_controller.setup(
            apks=[mock_app],
            repetitions=repetitions,
            timeouts=timeouts,
            tools=tools
        )

        mock_manager.setup_execution.assert_called_once()


def test_run_calls_run_all_tasks(execution_controller):
    """Test that run method calls run_all_tasks on ExecutionManager."""
    # Use patch to mock the execution_manager
    with patch.object(execution_controller, 'execution_manager') as mock_manager:
        # Configure the mock to return a specific value
        mock_manager.run_all_tasks.return_value = True

        # Call the run method
        result = execution_controller.run()

        # Assert run_all_tasks was called once
        mock_manager.run_all_tasks.assert_called_once()

        # Assert the result is True
        assert result is True


def test_copy_static_analysis_files(execution_controller, tmp_path, mock_app):
    """Test copying static analysis files."""
    # Create a directory for results
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True)

    # Simulate files in the instrumented directory
    from rv_android_core.constants import (
        EXTENSION_METHODS, EXTENSION_GESDA,
        EXTENSION_GATOR, EXTENSION_REACH
    )

    # Mock the config to return temp path as instrumented directory
    execution_controller.config.get_instrumented_dir.return_value = str(tmp_path)
    
    with patch.object(execution_controller.config, 'get_instrumented_dir', return_value=str(tmp_path)):
        # Create mock files
        extensions = [
            EXTENSION_METHODS,
            EXTENSION_GESDA,
            EXTENSION_GATOR,
            EXTENSION_REACH
        ]

        for ext in extensions:
            file_path = tmp_path / f"{mock_app.name}{ext}"
            file_path.write_text("test content")

        # Call the method
        result = execution_controller.copy_static_analysis_files(
            mock_app.name,
            str(results_dir)
        )

        # Verify files were copied
        assert result is True
        for ext in extensions:
            copied_file = results_dir / f"{mock_app.name}{ext}"
            assert copied_file.exists()
            assert copied_file.read_text() == "test content"


def test_get_statistics(execution_controller):
    """Test retrieving execution statistics."""
    # Mock the execution_manager's get_statistics method
    with patch.object(execution_controller, 'execution_manager') as mock_manager:
        # Create a mock return value with expected keys
        mock_stats = {
            'total': 10,
            'completed': 5,
            'failed': 2,
            'pending': 3,
            'pct_complete': 50.0,
            'current_task': None,
            'running': False,
            'elapsed': '0s'
        }
        mock_manager.get_statistics.return_value = mock_stats

        # Call get_statistics
        stats = execution_controller.get_statistics()

        # Verify the returned stats match the mock
        assert stats == mock_stats
        mock_manager.get_statistics.assert_called_once()


def test_get_coverage_report(execution_controller):
    """Test retrieving coverage report."""
    # Mock the execution_manager's get_coverage_report method
    with patch.object(execution_controller, 'execution_manager') as mock_manager:
        # Create a mock return value with expected structure
        mock_coverage_report = {
            'tasks': {},
            'summary': {
                'total_tasks': 10,
                'completed_tasks': 5,
                'avg_method_coverage': 60.0,
                'avg_activities_coverage': 50.0,
                'avg_mop_coverage': 40.0,
                'total_errors': 2
            }
        }
        mock_manager.get_coverage_report.return_value = mock_coverage_report

        # Call get_coverage_report
        coverage_report = execution_controller.get_coverage_report()

        # Verify the returned report matches the mock
        assert coverage_report == mock_coverage_report
        mock_manager.get_coverage_report.assert_called_once()
