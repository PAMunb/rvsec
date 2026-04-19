"""
Tests for EmulatorComponent - rv_platform emulator lifecycle management.

Tests cover:
- Component initialization
- execute() and cleanup() no-op behavior
- start_emulator() with dynamic port allocation
- install_app() with skip_installation logic
- clean_logcat() error handling
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.app import App
from rv_android_core.domain.task import Task
from rv_android_core.util.error.exceptions import EmulatorError
from rv_platform.components.emulator import EmulatorComponent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_task():
    """Create a mock task with minimal configuration."""
    task = MagicMock()
    task.id = "test_task_001"
    task.config = MagicMock()
    task.config.apk_name = "test_app.apk"
    task.config.no_window = False
    task.config.device_id = "emulator-5554"
    task.config.skip_installation = False
    tool_config = MagicMock()
    tool_config.parameters = {"device_port": 5556, "device_serial": "emulator-5556"}
    task.config.tool_config = tool_config
    return task


@pytest.fixture
def mock_app():
    """Create a mock App instance."""
    app = MagicMock()
    app.name = "test_app"
    app.path = "/path/to/test_app.apk"
    app.package_name = "com.test.app"
    return app


@pytest.fixture
def emulator_component(mock_task):
    """Create EmulatorComponent instance with mocked dependencies."""
    with patch("rv_platform.components.emulator.EmulatorManager"):
        component = EmulatorComponent(mock_task)
        yield component


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestEmulatorComponentInitialization:
    """Test EmulatorComponent initialization."""

    def test_init_sets_name(self, emulator_component):
        """Test that component name is set correctly."""
        assert emulator_component.name == "EmulatorComponent"

    def test_init_stores_task(self, emulator_component, mock_task):
        """Test that task is stored correctly."""
        assert emulator_component.task is mock_task

    def test_init_creates_emulator_manager(self, emulator_component):
        """Test that EmulatorManager is instantiated."""
        assert emulator_component.emulator_manager is not None

    def test_init_creates_logger(self, emulator_component):
        """Test that logger is created."""
        assert emulator_component.logger is not None


# ---------------------------------------------------------------------------
# Tests: execute() and cleanup() no-ops
# ---------------------------------------------------------------------------


class TestExecuteAndCleanup:
    """Test execute() and cleanup() no-op behavior."""

    def test_execute_returns_true(self, emulator_component):
        """Test that execute() always returns True."""
        result = emulator_component.execute({})
        assert result is True

    def test_execute_does_nothing(self, emulator_component):
        """Test that execute() doesn't call emulator methods."""
        emulator_component.emulator_manager.start_emulator = MagicMock()
        emulator_component.execute({})
        emulator_component.emulator_manager.start_emulator.assert_not_called()

    def test_cleanup_does_nothing(self, emulator_component):
        """Test that cleanup() is intentionally a no-op."""
        # Should not raise any errors
        emulator_component.cleanup({})

    def test_cleanup_logs_debug(self, emulator_component):
        """Test that cleanup() logs debug message."""
        emulator_component.logger.debug = MagicMock()
        emulator_component.cleanup({})
        emulator_component.logger.debug.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: start_emulator()
# ---------------------------------------------------------------------------


class TestStartEmulator:
    """Test start_emulator() with dynamic port allocation."""

    def test_start_emulator_default_port(self, emulator_component, mock_task):
        """Test start_emulator with default port (5554)."""
        mock_task.config.tool_config.parameters = {}
        mock_context = MagicMock()
        emulator_component.emulator_manager.start_emulator.return_value = mock_context

        result = emulator_component.start_emulator("RVSec")

        emulator_component.emulator_manager.start_emulator.assert_called_once_with(
            "RVSec", False, 5554
        )
        assert result is mock_context

    def test_start_emulator_custom_port_from_params(self, emulator_component):
        """Test start_emulator with custom port from parameters."""
        mock_context = MagicMock()
        emulator_component.emulator_manager.start_emulator.return_value = mock_context

        result = emulator_component.start_emulator("TestAVD")

        emulator_component.emulator_manager.start_emulator.assert_called_once_with(
            "TestAVD", False, 5556
        )
        assert result is mock_context

    def test_start_emulator_passes_no_window(self, emulator_component, mock_task):
        """Test that no_window flag is passed correctly."""
        mock_task.config.no_window = True
        mock_context = MagicMock()
        emulator_component.emulator_manager.start_emulator.return_value = mock_context

        emulator_component.start_emulator("RVSec")

        emulator_component.emulator_manager.start_emulator.assert_called_once()
        call_args = emulator_component.emulator_manager.start_emulator.call_args
        assert call_args[0][1] is True  # no_window parameter

    def test_start_emulator_handles_exception(self, emulator_component):
        """Test that start_emulator handles and re-raises exceptions."""
        emulator_component.emulator_manager.start_emulator.side_effect = Exception("AVD not found")
        emulator_component.error_handler.handle_error = MagicMock()

        # Exception is re-raised after error handling
        with pytest.raises(Exception, match="AVD not found"):
            emulator_component.start_emulator("InvalidAVD")
        
        # Error handler should have been called
        emulator_component.error_handler.handle_error.assert_called_once()

    def test_start_emulator_logs_start(self, emulator_component):
        """Test that start_emulator logs the start."""
        mock_context = MagicMock()
        emulator_component.emulator_manager.start_emulator.return_value = mock_context
        emulator_component.logger.info = MagicMock()

        emulator_component.start_emulator("RVSec")

        # Should log start message
        assert emulator_component.logger.info.called


# ---------------------------------------------------------------------------
# Tests: install_app()
# ---------------------------------------------------------------------------


class TestInstallApp:
    """Test install_app() with skip_installation logic."""

    def test_install_app_success(self, emulator_component, mock_app):
        """Test successful app installation."""
        emulator_component.emulator_manager.install_app.return_value = True

        result = emulator_component.install_app(None, mock_app)

        assert result is True
        emulator_component.emulator_manager.install_app.assert_called_once()

    def test_install_app_with_custom_serial(self, emulator_component, mock_app):
        """Test app installation with custom device serial."""
        emulator_component.emulator_manager.install_app.return_value = True

        emulator_component.install_app(None, mock_app)

        call_kwargs = emulator_component.emulator_manager.install_app.call_args
        assert call_kwargs[1]["device_serial"] == "emulator-5556"

    def test_install_app_skipped(self, emulator_component, mock_app, mock_task):
        """Test that installation is skipped when configured."""
        mock_task.config.skip_installation = True

        result = emulator_component.install_app(None, mock_app)

        assert result is True
        emulator_component.emulator_manager.install_app.assert_not_called()

    def test_install_app_failure(self, emulator_component, mock_app):
        """Test that app installation failure returns False."""
        emulator_component.emulator_manager.install_app.return_value = False

        result = emulator_component.install_app(None, mock_app)

        assert result is False

    def test_install_app_raises_error_on_failure(self, emulator_component, mock_app):
        """Test that failed installation raises EmulatorError via error handler."""
        emulator_component.emulator_manager.install_app.return_value = False
        emulator_component.error_handler.handle_error = MagicMock()

        # Should return False, not raise (error is handled internally)
        result = emulator_component.install_app(None, mock_app)
        assert result is False

    def test_install_app_logs_success(self, emulator_component, mock_app):
        """Test that successful installation logs completion."""
        emulator_component.emulator_manager.install_app.return_value = True
        emulator_component.logger.info = MagicMock()

        emulator_component.install_app(None, mock_app)

        # Should log completion
        assert emulator_component.logger.info.called


# ---------------------------------------------------------------------------
# Tests: clean_logcat()
# ---------------------------------------------------------------------------


class TestCleanLogcat:
    """Test clean_logcat() error handling."""

    def test_clean_logcat_success(self, emulator_component):
        """Test successful logcat cleaning."""
        emulator_component.emulator_manager.clear_logcat.return_value = True

        result = emulator_component.clean_logcat()

        assert result is True
        emulator_component.emulator_manager.clear_logcat.assert_called_once()

    def test_clean_logcat_failure_returns_false(self, emulator_component):
        """Test that logcat cleaning failure returns False."""
        emulator_component.emulator_manager.clear_logcat.return_value = False

        result = emulator_component.clean_logcat()

        assert result is False

    def test_clean_logcat_exception_returns_false(self, emulator_component):
        """Test that exception during logcat cleaning returns False."""
        emulator_component.emulator_manager.clear_logcat.side_effect = Exception("ADB error")

        result = emulator_component.clean_logcat()

        assert result is False

    def test_clean_logcat_logs_warning_on_error(self, emulator_component):
        """Test that logcat error logs warning."""
        emulator_component.emulator_manager.clear_logcat.side_effect = Exception("ADB error")
        emulator_component.logger.warning = MagicMock()

        emulator_component.clean_logcat()

        emulator_component.logger.warning.assert_called_once()
