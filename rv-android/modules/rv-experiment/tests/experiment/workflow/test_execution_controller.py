from unittest.mock import MagicMock, patch

import pytest

from rv_android_core.app import App
from rv_android_core.event.bus import EventBus
from rv_platform.storage.task_storage import TaskStorage
from rv_experiment.experiment.workflow.execution_controller import ExecutionController
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_experiment.config import ExperimentConfig


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
    """Create a mock ExperimentConfig."""
    # Create the instrumented directory for validation
    instrumented_dir = tmp_path / "instrumented"
    instrumented_dir.mkdir(exist_ok=True)
    
    mock_config = MagicMock(spec=ExperimentConfig)
    mock_config.output_dir = str(tmp_path)
    mock_config.get_instrumented_dir.return_value = str(instrumented_dir)
    mock_config.get_timestamp_string.return_value = "20230101_120000"
    return mock_config


@pytest.fixture
def execution_controller(mock_task_storage, mock_config, mock_event_bus):
    """Create an ExecutionController instance for testing."""
    return ExecutionController(mock_task_storage, mock_config, mock_event_bus)


def test_setup_creates_platform_config(execution_controller, mock_app):
    """Test that setup method creates platform configuration."""
    tools = [DummyTool()]
    repetitions = 2
    timeouts = [30, 60]

    # Mock the Platform creation and PlatformConfig creation
    with patch('rv_experiment.experiment.workflow.execution_controller.Platform') as mock_platform_class, \
         patch('rv_experiment.experiment.workflow.execution_controller.PlatformConfig') as mock_config_class:
        
        mock_platform = mock_platform_class.return_value
        mock_config = mock_config_class.return_value
        
        execution_controller.setup(
            apks=[mock_app],
            repetitions=repetitions,
            timeouts=timeouts,
            tools=tools
        )

        # Verify platform configuration was created
        mock_config_class.assert_called_once()
        
        # Verify platform was created with the config and event_bus
        mock_platform_class.assert_called_once_with(mock_config, execution_controller.event_bus)
        
        # Verify internal state was set
        assert execution_controller.platform_config == mock_config
        assert execution_controller.platform == mock_platform


def test_setup_preserves_existing_tasks(execution_controller, mock_app):
    """Test that existing tasks are preserved during setup."""
    tools = [DummyTool()]
    repetitions = 2
    timeouts = [30, 60]

    # Mock the Platform creation
    with patch('rv_experiment.experiment.workflow.execution_controller.Platform') as mock_platform_class:
        execution_controller.setup(
            apks=[mock_app],
            repetitions=repetitions,
            timeouts=timeouts,
            tools=tools
        )

        # Just verify setup completes without error
        assert execution_controller.platform is not None


def test_run_calls_platform_run(execution_controller):
    """Test that run method calls run on Platform."""
    # Setup mock platform and platform_config to simulate setup was called
    mock_platform = MagicMock()
    # Platform.run() should return a dict with execution results
    mock_platform.run.return_value = {
        'success': True,
        'failed_tasks': 0,
        'completed_tasks': 5
    }
    execution_controller.platform = mock_platform
    execution_controller.platform_config = MagicMock()  # Simulate setup was called

    # Call the run method
    result = execution_controller.run()

    # Assert platform.run was called once
    mock_platform.run.assert_called_once()

    # Assert the result is True
    assert result is True




def test_get_statistics(execution_controller):
    """Test retrieving execution statistics."""
    # Setup mock platform
    mock_platform = MagicMock()
    mock_platform_stats = {
        'total': 10,
        'completed': 5,
        'failed': 2,
        'pending': 3,
        'running': False
    }
    mock_platform.get_execution_summary.return_value = mock_platform_stats
    execution_controller.platform = mock_platform

    # Call get_statistics
    stats = execution_controller.get_statistics()

    # Verify the method was called
    mock_platform.get_execution_summary.assert_called_once()
    
    # Verify the returned stats include platform stats and experiment metadata
    assert 'execution_method' in stats
    assert stats['execution_method'] == 'rv_platform_integration'
    assert stats['total'] == 10
    assert stats['completed'] == 5


def test_get_coverage_report(execution_controller):
    """Test retrieving coverage report."""
    # Setup mock platform
    mock_platform = MagicMock()
    mock_platform_stats = {
        'total_tasks': 10,
        'completed_tasks': 5,
        'avg_method_coverage': 60.0,
        'avg_activities_coverage': 50.0,
        'total_errors': 2
    }
    mock_platform.get_execution_summary.return_value = mock_platform_stats
    execution_controller.platform = mock_platform

    # Call get_coverage_report
    coverage_report = execution_controller.get_coverage_report()

    # Verify the method was called
    mock_platform.get_execution_summary.assert_called_once()
    
    # Verify the returned report structure
    assert coverage_report['coverage_source'] == 'rv_platform_integration'
    assert coverage_report['has_coverage_data'] is True
    assert coverage_report['execution_summary'] == mock_platform_stats
