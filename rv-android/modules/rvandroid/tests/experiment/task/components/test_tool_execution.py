import pytest
from unittest.mock import Mock, patch

from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.task.components.tool_execution import ToolExecutionComponent
from rvandroid.experiment.task.task_model import Task
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.manager import LoggingManager


@pytest.fixture
def mock_task():
    task = Mock(spec=Task)
    task.id = "test_task_1"
    # Create a Mock for config with apk_name attribute
    config_mock = Mock()
    config_mock.apk_name = "test_app"
    task.config = config_mock
    task.app = Mock()
    return task


@pytest.fixture
def mock_tool():
    tool = Mock(spec=AbstractTool)
    tool.name = "test_tool"
    tool.process_pattern = "test_pattern"
    return tool


@pytest.fixture
def mock_event_bus():
    return Mock(spec=EventBus)


@pytest.fixture
def mock_error_handler():
    return Mock(spec=ErrorHandler)


@pytest.fixture
def mock_logger():
    logger_mock = Mock()
    logger_mock.with_context.return_value.__enter__ = Mock()
    logger_mock.with_context.return_value.__exit__ = Mock()
    return logger_mock


@pytest.fixture
def tool_execution_component(mock_task, mock_tool, mock_event_bus, mock_error_handler, mock_logger):
    with patch('rvandroid.util.error.error_handler.ErrorHandler.get_instance', return_value=mock_error_handler), \
            patch('rvandroid.util.logging.manager.LoggingManager.get_instance') as mock_logging_manager:
        mock_logging_manager.return_value.get_logger.return_value = mock_logger
        return ToolExecutionComponent(mock_task, mock_tool, mock_event_bus)


def test_execute_tool_success(tool_execution_component, mock_task, mock_tool, mock_event_bus):
    result = tool_execution_component.run_tool()

    assert result is True
    mock_tool.execute.assert_called_once_with(mock_task, mock_task.app)
    mock_event_bus.publish_task_event.assert_any_call(
        EventType.TOOL_STARTED,
        task_id=mock_task.id,
        details={"tool_name": mock_tool.name},
        source="ToolExecutionComponent"
    )
    mock_event_bus.publish_task_event.assert_any_call(
        EventType.TOOL_STOPPED,
        task_id=mock_task.id,
        details={"tool_name": mock_tool.name},
        source="ToolExecutionComponent"
    )


def test_execute_tool_failure(tool_execution_component, mock_task, mock_tool, mock_event_bus, mock_error_handler):
    mock_tool.execute.side_effect = Exception("Tool execution failed")
    
    # Mock the _get_error_handler method to return our mock
    tool_execution_component._get_error_handler = Mock(return_value=mock_error_handler)

    result = tool_execution_component.run_tool()

    assert result is False
    mock_error_handler.handle_error.assert_called_once()
    mock_event_bus.publish_task_event.assert_any_call(
        EventType.TASK_FAILED,
        task_id=mock_task.id,
        details={
            "tool_name": mock_tool.name,
            "error": "Tool execution failed"
        },
        source="ToolExecutionComponent"
    )


def test_execute_tool_without_event_bus(mock_task, mock_tool, mock_logger):
    with patch('rvandroid.util.error.error_handler.ErrorHandler.get_instance'), \
            patch('rvandroid.util.logging.manager.LoggingManager.get_instance') as mock_logging_manager:
        mock_logging_manager.return_value.get_logger.return_value = mock_logger
        component = ToolExecutionComponent(mock_task, mock_tool, event_bus=None)

        result = component.run_tool()
        assert result is True
        mock_tool.execute.assert_called_once_with(mock_task, mock_task.app)


def test_cleanup_processes_success(tool_execution_component, mock_tool):
    tool_execution_component.cleanup_processes()
    mock_tool.kill_related_processes.assert_called_once_with(mock_tool.process_pattern)


def test_cleanup_processes_with_error(tool_execution_component, mock_tool):
    mock_tool.kill_related_processes.side_effect = Exception("Cleanup failed")
    tool_execution_component.cleanup_processes()
    mock_tool.kill_related_processes.assert_called_once_with(mock_tool.process_pattern)


def test_cleanup_processes_no_pattern(mock_task, mock_tool, mock_event_bus):
    mock_tool.process_pattern = None
    component = ToolExecutionComponent(mock_task, mock_tool, mock_event_bus)
    component.cleanup_processes()
    mock_tool.kill_related_processes.assert_not_called()
