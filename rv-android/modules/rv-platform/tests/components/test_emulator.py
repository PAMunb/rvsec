import pytest
from unittest.mock import Mock, patch

from rv_platform.components.emulator import EmulatorComponent
from rv_android_core.domain.task import Task
from rv_android_core.domain.app import App
from rv_android_core.event import EventType
from rv_android_core.util.error.exceptions import EmulatorError
from rv_android_core.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, LOG_START, LOG_ERROR, LOG_SKIPPED, LOG_COMPLETE

# Fixtures for mocks
@pytest.fixture
def mock_task():
    task = Mock(spec=Task)
    task.id = "test_task_id"
    task.config = Mock()
    task.config.apk_name = "test_app"
    task.config.no_window = False
    task.config.skip_installation = False
    task.config.device_id = "emulator-5554"
    return task

@pytest.fixture
def mock_event_bus():
    return Mock()

@pytest.fixture
def mock_emulator_manager():
    return Mock()

@pytest.fixture
def mock_error_handler():
    return Mock()

@pytest.fixture
def mock_logging_manager():
    with patch('rv_android_core.util.logging.manager.LoggingManager.get_instance') as mock_get_instance:
        mock_logger = Mock()

        # Create a dedicated mock for the context manager
        class MockContextManager:
            def __enter__(self):
                return mock_logger # Return the logger mock itself
            def __exit__(self, exc_type, exc_val, exc_tb):
                return False # Indicate no exception handling

        mock_logger.with_context.return_value = MockContextManager()
        mock_get_instance.return_value.get_logger.return_value = mock_logger
        yield mock_logger

@pytest.fixture
def mock_app():
    app = Mock(spec=App)
    app.name = "TestApp"
    app.package_name = "com.test.app"
    return app

@pytest.fixture
def emulator_component(mock_task, mock_event_bus, mock_error_handler, mock_emulator_manager, mock_logging_manager):
    with patch('rv_android_core.util.error.error_handler.ErrorHandler.get_instance', return_value=mock_error_handler):
        with patch('rv_android_core.util.android.emulator_manager.EmulatorManager', return_value=mock_emulator_manager):
            component = EmulatorComponent(mock_task, mock_event_bus)
            yield component

# Tests for EmulatorComponent

def test_emulator_component_init(emulator_component, mock_task, mock_logging_manager):
    assert emulator_component.name == "EmulatorComponent"
    assert emulator_component.task == mock_task
    # event_bus, error_handler, emulator_manager are assigned in __init__ and mocked by fixtures
    mock_logging_manager.get_logger.assert_called_once_with(
        'rv_platform.components.emulator',
        {
            CONTEXT_TASK_ID: mock_task.id,
            CONTEXT_APP_NAME: mock_task.config.apk_name
        }
    )

def test_emulator_component_initialize(emulator_component, mock_logging_manager):
    emulator_component.initialize({})
    mock_logging_manager.debug.assert_called_with("Initializing EmulatorComponent")

def test_emulator_component_execute(emulator_component, mock_logging_manager):
    result = emulator_component.execute({})
    assert result is True
    mock_logging_manager.info.assert_called_with("EmulatorComponent prepared for execution")

def test_emulator_component_cleanup(emulator_component, mock_logging_manager):
    emulator_component.cleanup({})
    mock_logging_manager.debug.assert_called_with("Cleaning up EmulatorComponent")

# --- start_emulator tests ---

def test_start_emulator_success(emulator_component, mock_task, mock_event_bus, mock_emulator_manager, mock_logging_manager):
    mock_emulator_manager.start_emulator.return_value = Mock() # Mock the context manager

    with emulator_component.start_emulator("test_avd"):
        mock_emulator_manager.start_emulator.assert_called_once_with(
            "test_avd", mock_task.config.no_window
        )
        mock_logging_manager.info.assert_any_call(
            LOG_START.format(phase=f"emulator test_avd")
        )
        mock_event_bus.publish_task_event.assert_called_once_with(
            EventType.EMULATOR_STARTED,
            task_id=mock_task.id,
            details={"device_id": mock_task.config.device_id},
            source="EmulatorComponent"
        )

def test_start_emulator_failure(emulator_component, mock_task, mock_event_bus, mock_emulator_manager, mock_error_handler, mock_logging_manager):
    mock_emulator_manager.start_emulator.side_effect = Exception("Emulator failed to start")

    with pytest.raises(Exception, match="Emulator failed to start"):
        with emulator_component.start_emulator("test_avd"):
            pass

    mock_logging_manager.error.assert_called_once_with(
        LOG_ERROR.format(phase=f"starting emulator test_avd", error="Emulator failed to start")
    )
    mock_error_handler.handle_error.assert_called_once()
    assert isinstance(mock_error_handler.handle_error.call_args[0][0], EmulatorError)

# --- install_app tests ---

def test_install_app_success(emulator_component, mock_task, mock_event_bus, mock_emulator_manager, mock_app, mock_logging_manager):
    result = emulator_component.install_app(Mock(), mock_app)
    assert result is True
    mock_emulator_manager.install_app.assert_called_once_with(mock_app)
    mock_logging_manager.info.assert_any_call(
        LOG_START.format(phase=f"installing app {mock_app.name}")
    )
    mock_logging_manager.info.assert_any_call(
        LOG_COMPLETE.format(phase=f"installing app {mock_app.name}")
    )
    mock_event_bus.publish_task_event.assert_called_once_with(
        EventType.APP_INSTALLED,
        task_id=mock_task.id,
        details={"app_name": mock_app.name},
        source="EmulatorComponent"
    )

def test_install_app_skip_installation(emulator_component, mock_task, mock_event_bus, mock_emulator_manager, mock_app, mock_logging_manager):
    emulator_component.task.config.skip_installation = True

    result = emulator_component.install_app(Mock(), mock_app)
    assert result is True
    mock_emulator_manager.install_app.assert_not_called()
    mock_logging_manager.info.assert_called_with(
        LOG_SKIPPED.format(phase="app installation", reason="skipped as requested in configuration")
    )

def test_install_app_failure(emulator_component, mock_task, mock_event_bus, mock_emulator_manager, mock_app, mock_error_handler, mock_logging_manager):
    mock_emulator_manager.install_app.side_effect = Exception("Installation failed")

    result = emulator_component.install_app(Mock(), mock_app)
    assert result is False
    mock_logging_manager.error.assert_called_once_with(
        LOG_ERROR.format(phase=f"installing app {mock_app.name}", error="Installation failed")
    )
    mock_error_handler.handle_error.assert_called_once()
    assert isinstance(mock_error_handler.handle_error.call_args[0][0], EmulatorError)

# --- clean_logcat tests ---

def test_clean_logcat_success(emulator_component, mock_task, mock_event_bus, mock_emulator_manager, mock_logging_manager):
    mock_emulator_manager.clear_logcat.return_value = True

    result = emulator_component.clean_logcat()
    assert result is True
    mock_emulator_manager.clear_logcat.assert_called_once()
    mock_logging_manager.debug.assert_any_call(
        LOG_START.format(phase="cleaning logcat buffer")
    )
    mock_logging_manager.debug.assert_any_call(
        LOG_COMPLETE.format(phase="cleaning logcat buffer")
    )

def test_clean_logcat_failure(emulator_component, mock_task, mock_event_bus, mock_emulator_manager, mock_logging_manager):
    mock_emulator_manager.clear_logcat.side_effect = Exception("Logcat clear failed")

    result = emulator_component.clean_logcat()
    assert result is False
    mock_logging_manager.warning.assert_called_once_with(
        LOG_ERROR.format(phase="clearing logcat", error="Logcat clear failed")
    )