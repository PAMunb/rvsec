import pytest
from unittest.mock import Mock, patch

from rvandroid.experiment.event.bus import EventBus
from rvandroid.experiment.task.components.logcat import LogcatComponent
from rvandroid.experiment.task.task_model import Task
from rvandroid.util.logcat_manager import LogcatManager
from rvandroid.util.exceptions import AnalysisError
from rvandroid.util.error.error_handler import ErrorHandler


@pytest.fixture
def mock_task():
    task = Mock(spec=Task)
    config_mock = Mock()
    config_mock.apk_name = "test_app"
    config_mock.clean_logcat = True

    result_mock = Mock()
    result_mock.logcat_file = "test_logcat.log"

    task.id = "test_task_id"
    task.config = config_mock
    task.result = result_mock
    return task


@pytest.fixture
def mock_event_bus():
    return Mock(spec=EventBus)


@pytest.fixture
def mock_error_handler():
    with patch.object(ErrorHandler, '_instance', None):
        error_handler = Mock()
        ErrorHandler._instance = error_handler
        yield error_handler
        ErrorHandler._instance = None


@pytest.fixture
def logcat_component(mock_task, mock_event_bus, mock_error_handler):
    with patch('rvandroid.util.logging.manager.LoggingManager'):
        component = LogcatComponent(mock_task, mock_event_bus)
        component.logcat_manager = Mock(spec=LogcatManager)
        component.error_handler = mock_error_handler
        return component


def test_start_capture_success(logcat_component):
    logcat_component.logcat_manager.start_capture.return_value = True

    result = logcat_component.start_capture()

    assert result is True
    logcat_component.logcat_manager.start_capture.assert_called_once_with(
        "test_logcat.log",
        clear_buffer=True
    )


def test_start_capture_failure(logcat_component):
    logcat_component.logcat_manager.start_capture.return_value = False

    result = logcat_component.start_capture()

    assert result is False
    logcat_component.logcat_manager.start_capture.assert_called_once()


def test_start_capture_exception(logcat_component):
    logcat_component.logcat_manager.start_capture.side_effect = Exception("Test error")

    result = logcat_component.start_capture()

    assert result is False
    logcat_component.error_handler.handle_error.assert_called_once()


def test_stop_capture_success(logcat_component):
    logcat_component.logcat_manager.stop_capture.return_value = True

    result = logcat_component.stop_capture()

    assert result is True
    logcat_component.logcat_manager.stop_capture.assert_called_once()


def test_stop_capture_failure(logcat_component):
    logcat_component.logcat_manager.stop_capture.return_value = False

    result = logcat_component.stop_capture()

    assert result is False
    logcat_component.logcat_manager.stop_capture.assert_called_once()


def test_stop_capture_exception(logcat_component):
    logcat_component.logcat_manager.stop_capture.side_effect = Exception("Test error")

    result = logcat_component.stop_capture()

    assert result is False
