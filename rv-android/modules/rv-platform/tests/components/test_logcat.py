"""
Tests for LogcatComponent - rv_platform logcat capture and filtering.

Tests cover:
- Component initialization with device serial resolution
- execute() and cleanup() behavior
- start_capture() with clear_buffer option
- stop_capture() lifecycle management
- Error handling for all operations
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.task import Task
from rv_platform.components.logcat import LogcatComponent

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
    task.config.device_id = "emulator-5554"
    task.config.clean_logcat = True
    tool_config = MagicMock()
    tool_config.parameters = {"device_serial": "emulator-5556"}
    task.config.tool_config = tool_config
    task.result = MagicMock()
    task.result.logcat_file = "/tmp/test_logcat.txt"
    return task


@pytest.fixture
def logcat_component(mock_task):
    """Create LogcatComponent instance with mocked dependencies."""
    with patch("rv_platform.components.logcat.LogcatManager"):
        component = LogcatComponent(mock_task)
        yield component


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


class TestLogcatComponentInitialization:
    """Test LogcatComponent initialization."""

    def test_init_sets_name(self, logcat_component):
        """Test that component name is set correctly."""
        assert logcat_component.name == "LogcatComponent"

    def test_init_stores_task(self, logcat_component, mock_task):
        """Test that task is stored correctly."""
        assert logcat_component.task is mock_task

    def test_init_creates_logcat_manager(self, logcat_component):
        """Test that LogcatManager is instantiated."""
        assert logcat_component.logcat_manager is not None

    def test_init_creates_logger(self, logcat_component):
        """Test that logger is created."""
        assert logcat_component.logger is not None

    def test_init_uses_device_serial_from_params(self, mock_task):
        """Test that device serial is resolved from tool_config.parameters."""
        with patch("rv_platform.components.logcat.LogcatManager") as mock_logcat_mgr:
            LogcatComponent(mock_task)
            mock_logcat_mgr.assert_called_once_with(device_serial="emulator-5556")

    def test_init_derives_serial_from_device_port(self, mock_task):
        """Only device_port injected: capture follows the port that was booted.

        `task.config.device_id` is left at the stale "emulator-5554" on purpose —
        capturing from it instead of from the resolved serial is the defect this
        pins (INV-PLT-28), and it fails silently: an empty logcat, not an error.
        """
        mock_task.config.tool_config.parameters = {"device_port": 5558}

        with patch("rv_platform.components.logcat.LogcatManager") as mock_logcat_mgr:
            LogcatComponent(mock_task)
            mock_logcat_mgr.assert_called_once_with(device_serial="emulator-5558")

    def test_init_without_parameters_uses_the_default_serial(self, mock_task):
        """Neither key present: single-emulator mode."""
        mock_task.config.tool_config.parameters = {}

        with patch("rv_platform.components.logcat.LogcatManager") as mock_logcat_mgr:
            LogcatComponent(mock_task)
            mock_logcat_mgr.assert_called_once_with(device_serial="emulator-5554")


# ---------------------------------------------------------------------------
# Tests: execute() and cleanup()
# ---------------------------------------------------------------------------


class TestExecuteAndCleanup:
    """Test execute() and cleanup() behavior."""

    def test_execute_returns_true(self, logcat_component):
        """Test that execute() always returns True."""
        result = logcat_component.execute({})
        assert result is True

    def test_execute_does_nothing(self, logcat_component):
        """Test that execute() doesn't call logcat methods."""
        logcat_component.logcat_manager.start_capture = MagicMock()
        logcat_component.execute({})
        logcat_component.logcat_manager.start_capture.assert_not_called()

    def test_cleanup_calls_stop_capture(self, logcat_component):
        """Test that cleanup() stops logcat capture."""
        logcat_component.stop_capture = MagicMock()
        logcat_component.cleanup({})
        logcat_component.stop_capture.assert_called_once()

    def test_cleanup_handles_exception(self, logcat_component):
        """Test that cleanup() handles exceptions gracefully."""
        logcat_component.stop_capture = MagicMock(
            side_effect=Exception("Cleanup error")
        )
        logcat_component.logger.warning = MagicMock()

        # Should not raise
        logcat_component.cleanup({})
        logcat_component.logger.warning.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: start_capture()
# ---------------------------------------------------------------------------


class TestStartCapture:
    """Test start_capture() with various configurations."""

    def test_start_capture_success(self, logcat_component):
        """Test successful logcat capture start."""
        logcat_component.logcat_manager.start_capture.return_value = True

        result = logcat_component.start_capture()

        assert result is True
        # Diagnostics off (default): tags=None → LogcatManager emits the baseline.
        logcat_component.logcat_manager.start_capture.assert_called_once_with(
            "/tmp/test_logcat.txt", tags=None, clear_buffer=True
        )

    def test_start_capture_without_clear_buffer(self, logcat_component, mock_task):
        """Test logcat capture start without clearing buffer."""
        mock_task.config.clean_logcat = False
        logcat_component.logcat_manager.start_capture.return_value = True

        result = logcat_component.start_capture()

        assert result is True
        logcat_component.logcat_manager.start_capture.assert_called_once_with(
            "/tmp/test_logcat.txt", tags=None, clear_buffer=False
        )

    def test_start_capture_failure_returns_false(self, logcat_component):
        """Test that start capture failure returns False."""
        logcat_component.logcat_manager.start_capture.return_value = False

        result = logcat_component.start_capture()

        assert result is False

    def test_start_capture_logs_success(self, logcat_component):
        """Test that successful start logs completion."""
        logcat_component.logcat_manager.start_capture.return_value = True
        logcat_component.logger.info = MagicMock()

        logcat_component.start_capture()

        assert logcat_component.logger.info.called

    def test_start_capture_logs_failure(self, logcat_component):
        """Test that start capture failure logs warning."""
        logcat_component.logcat_manager.start_capture.return_value = False
        logcat_component.logger.warning = MagicMock()

        logcat_component.start_capture()

        logcat_component.logger.warning.assert_called_once()

    def test_start_capture_handles_exception(self, logcat_component):
        """Test that exception during start capture returns False."""
        logcat_component.logcat_manager.start_capture.side_effect = Exception(
            "ADB error"
        )
        logcat_component.error_handler.handle_error = MagicMock()

        result = logcat_component.start_capture()

        assert result is False
        logcat_component.error_handler.handle_error.assert_called_once()


class TestDiagnosticsFlagThreading:
    """INV-PLT-21 / gh72: the logcat_diagnostics flag controls the capture tags."""

    def test_flag_off_passes_no_diagnostic_tags(self, mock_task):
        """Default (flag off): start_capture is called with tags=None (baseline)."""
        with patch("rv_platform.components.logcat.LogcatManager"):
            component = LogcatComponent(mock_task)  # default logcat_diagnostics=False
            component.logcat_manager.start_capture.return_value = True

            component.start_capture()

            _, kwargs = component.logcat_manager.start_capture.call_args
            assert kwargs["tags"] is None

    def test_flag_on_appends_diagnostic_tags(self, mock_task):
        """Flag on: start_capture receives default_tags + DIAGNOSTIC_TAGS."""
        from rv_android_core.util.android.logcat_manager import DIAGNOSTIC_TAGS

        with patch("rv_platform.components.logcat.LogcatManager") as mock_mgr_cls:
            mock_mgr = mock_mgr_cls.return_value
            mock_mgr.default_tags = ["RVSEC", "RVSEC-COV"]
            mock_mgr.start_capture.return_value = True

            component = LogcatComponent(mock_task, logcat_diagnostics=True)
            component.start_capture()

            _, kwargs = mock_mgr.start_capture.call_args
            assert kwargs["tags"] == ["RVSEC", "RVSEC-COV"] + DIAGNOSTIC_TAGS


# ---------------------------------------------------------------------------
# Tests: stop_capture()
# ---------------------------------------------------------------------------


class TestStopCapture:
    """Test stop_capture() lifecycle management."""

    def test_stop_capture_success(self, logcat_component):
        """Test successful logcat capture stop."""
        logcat_component.logcat_manager.stop_capture.return_value = True

        result = logcat_component.stop_capture()

        assert result is True
        logcat_component.logcat_manager.stop_capture.assert_called_once()

    def test_stop_capture_failure_returns_false(self, logcat_component):
        """Test that stop capture failure returns False."""
        logcat_component.logcat_manager.stop_capture.return_value = False

        result = logcat_component.stop_capture()

        assert result is False

    def test_stop_capture_logs_success(self, logcat_component):
        """Test that successful stop logs completion."""
        logcat_component.logcat_manager.stop_capture.return_value = True
        logcat_component.logger.info = MagicMock()

        logcat_component.stop_capture()

        assert logcat_component.logger.info.called

    def test_stop_capture_logs_warning_on_failure(self, logcat_component):
        """Test that stop capture failure logs warning."""
        logcat_component.logcat_manager.stop_capture.return_value = False
        logcat_component.logger.warning = MagicMock()

        logcat_component.stop_capture()

        logcat_component.logger.warning.assert_called_once()

    def test_stop_capture_handles_exception(self, logcat_component):
        """Test that exception during stop capture returns False."""
        logcat_component.logcat_manager.stop_capture.side_effect = Exception(
            "ADB error"
        )
        logcat_component.logger.warning = MagicMock()

        result = logcat_component.stop_capture()

        assert result is False
        logcat_component.logger.warning.assert_called_once()
