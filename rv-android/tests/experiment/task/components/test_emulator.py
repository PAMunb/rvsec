import pytest
from unittest.mock import Mock, patch

from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.task.components.emulator import EmulatorComponent
from rvandroid.experiment.task.task_model import Task
from rvandroid.app import App
from rvandroid.util.exceptions import EmulatorError


@pytest.fixture
def mock_task():
    task = Mock(spec=Task)
    task.id = "test_task_id"
    task.config = Mock()
    task.config.apk_name = "test_app"
    task.config.device_id = "test_device"
    task.config.no_window = True
    task.config.skip_installation = False
    return task


@pytest.fixture
def mock_event_bus():
    return Mock(spec=EventBus)


@pytest.fixture
def mock_app():
    app = Mock(spec=App)
    app.name = "test_app"
    return app


@pytest.fixture
def emulator_component(mock_task, mock_event_bus):
    with patch('rvandroid.util.emulator_manager.EmulatorManager') as manager_class, \
            patch('rvandroid.util.logging.manager.LoggingManager') as logging_manager, \
            patch('rvandroid.util.error.error_handler.ErrorHandler.get_instance') as error_handler:
        logging_manager.get_instance.return_value.get_logger.return_value = Mock()
        error_handler.return_value = Mock()
        component = EmulatorComponent(mock_task, mock_event_bus)
        component.emulator_manager = manager_class.return_value
        return component


def test_start_emulator_success(emulator_component, mock_task):
    context_manager = Mock()
    context_manager.__enter__ = Mock(return_value="emulator_context")
    context_manager.__exit__ = Mock(return_value=None)
    emulator_component.emulator_manager.start_emulator.return_value = context_manager

    with emulator_component.start_emulator("RVSec") as context:
        assert context == "emulator_context"

    emulator_component.event_bus.publish_task_event.assert_called_once_with(
        EventType.EMULATOR_STARTED,
        task_id=mock_task.id,
        details={"device_id": mock_task.config.device_id},
        source="EmulatorComponent"
    )


# def test_start_emulator_failure(emulator_component):
#     # Arrange
#     emulator_component.emulator_manager.start_emulator.side_effect = Exception("Failed to start")
#
#     # Act & Assert
#     with pytest.raises(EmulatorError) as exc_info:
#         emulator_component.start_emulator("RVSec")
#
#     # Verify error message matches expected format
#     assert "Failed to start emulator RVSec" in str(exc_info.value)


def test_install_app_success(emulator_component, mock_task, mock_app):
    mock_android = Mock()
    result = emulator_component.install_app(mock_android, mock_app)

    assert result is True
    emulator_component.event_bus.publish_task_event.assert_called_once_with(
        EventType.APP_INSTALLED,
        task_id=mock_task.id,
        details={"app_name": mock_app.name},
        source="EmulatorComponent"
    )


def test_install_app_failure(emulator_component, mock_app):
    emulator_component.emulator_manager.install_app.side_effect = Exception("Install failed")
    mock_android = Mock()
    result = emulator_component.install_app(mock_android, mock_app)
    assert result is False


def test_clean_logcat_success(emulator_component):
    emulator_component.emulator_manager.clear_logcat.return_value = True
    result = emulator_component.clean_logcat()
    assert result is True


def test_clean_logcat_failure(emulator_component):
    emulator_component.emulator_manager.clear_logcat.side_effect = Exception("Clear failed")
    result = emulator_component.clean_logcat()
    assert result is False
