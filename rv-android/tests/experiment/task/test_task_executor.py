# tests/experiment/task/test_task_executor.py
import logging
from unittest.mock import MagicMock, patch

import pytest

from rvandroid.app import App
from rvandroid.domain.coverage import LogcatRepository
from rvandroid.experiment.event.bus import EventBus
from rvandroid.experiment.task.task_executor import TaskExecutor
from rvandroid.experiment.task.task_model import Task, TaskConfiguration, TaskStatus
from rvandroid.tools.tool_spec import AbstractTool

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.fixture
def mock_app():
    """Create a mock App instance for testing."""
    app = MagicMock(spec=App)
    app.name = "test_app"
    app.path = "/path/to/test_app.apk"
    app.package_name = "com.test.app"
    return app


@pytest.fixture
def mock_task(mock_app, tmp_path):
    """Create a mock Task instance for testing."""
    config = TaskConfiguration(
        apk_name="test_app.apk",
        repetition=1,
        timeout=60,
        tool_name="mock_tool"
    )
    task = Task(config)
    task.app = mock_app
    task.results_dir = str(tmp_path)
    task.result.logcat_file = str(tmp_path / "logcat.log")
    return task


@pytest.fixture
def mock_tool():
    """Create a mock AbstractTool for testing."""
    tool = MagicMock(spec=AbstractTool)
    tool.name = "mock_tool"
    tool.process_pattern = "test_process"

    def mock_execute(task, app):
        logger.debug(f"Mock tool executing task {task.id} for app {app.name}")

    tool.execute = mock_execute
    return tool


def create_mocked_task_executor(mock_task, mock_tool):
    """Create a TaskExecutor with comprehensive mocking."""
    event_bus = MagicMock(spec=EventBus)
    executor = TaskExecutor(mock_task, mock_tool, event_bus)

    # Mock all components comprehensively
    executor.static_analysis = MagicMock()
    executor.static_analysis.load_static_data.return_value = True

    executor.coverage = MagicMock()
    executor.coverage.initialize_tracker.return_value = True
    executor.coverage.start_tracking.return_value = True
    executor.coverage.stop_tracking.return_value = True
    executor.coverage.process_results.return_value = True
    executor.coverage.get_repository.return_value = MagicMock(spec=LogcatRepository)

    executor.emulator = MagicMock()
    emulator_context = MagicMock()
    emulator_context.__enter__.return_value = emulator_context
    executor.emulator.start_emulator.return_value = emulator_context
    executor.emulator.install_app.return_value = True

    executor.logcat = MagicMock()
    executor.logcat.start_capture.return_value = True
    executor.logcat.stop_capture.return_value = True

    executor.tool_executor = MagicMock()
    executor.tool_executor.execute_tool.return_value = True
    executor.tool_executor.cleanup_processes.return_value = None

    return executor


def test_task_executor_export_repository_data(mock_task, mock_tool):
    """Specific test for repository data export."""
    # Create a mocked task executor
    executor = create_mocked_task_executor(mock_task, mock_tool)

    # Patch SpreadsheetExporter to prevent actual file operations
    with patch('rvandroid.experiment.task.task_executor.SpreadsheetExporter') as mock_exporter_class:
        mock_exporter = MagicMock()
        mock_exporter_class.return_value = mock_exporter

        mock_repository = MagicMock(spec=LogcatRepository)

        # Call the method directly
        executor._export_repository_data(mock_repository)

        # Verify export methods were called
        mock_exporter.export_coverage_data.assert_called_once()
        mock_exporter.export_error_data.assert_called_once()


@patch('rvandroid.experiment.task.task_executor.SpreadsheetExporter')
def test_task_executor_execute_success(mock_spreadsheet_exporter, mock_task, mock_tool):
    """Detailed test for task execution."""
    # Create a mocked task executor
    executor = create_mocked_task_executor(mock_task, mock_tool)

    # Ensure SpreadsheetExporter is mocked
    mock_exporter = MagicMock()
    mock_spreadsheet_exporter.return_value = mock_exporter

    try:
        result = executor.execute()

        # Log detailed diagnostics
        logger.debug(f"Execution result: {result}")
        logger.debug(f"Task status: {mock_task.result.status}")

        # Comprehensive assertions
        assert result is True, "Task execution should return True"
        assert mock_task.result.status == TaskStatus.EXECUTED, "Task status should be EXECUTED"

        # Verify method calls
        executor.static_analysis.load_static_data.assert_called_once()
        executor.coverage.initialize_tracker.assert_called_once()
        executor.emulator.start_emulator.assert_called_once()
        executor.emulator.install_app.assert_called_once()
        executor.logcat.start_capture.assert_called_once()
        executor.coverage.start_tracking.assert_called_once()
        executor.tool_executor.execute_tool.assert_called_once()
        executor.coverage.stop_tracking.assert_called_once()
        executor.logcat.stop_capture.assert_called_once()
        executor.coverage.process_results.assert_called_once()

    except Exception as e:
        logger.error(f"Unexpected error during test: {e}")
        import traceback
        traceback.print_exc()
        raise
