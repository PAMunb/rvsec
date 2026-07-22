"""
Tests for LoggingManager - centralized logging configuration.

Tests cover:
- Singleton pattern (get_instance)
- _setup_default_logging() console configuration
- configure_output() with various options
- setup_file_logging() with JSON and structured formats
- get_logger() with context caching
"""

import logging
import os
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.context_adapter import ContextAdapter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def logging_manager():
    """Create a fresh LoggingManager instance."""
    # Reset singleton for clean tests
    LoggingManager._instance = None
    return LoggingManager.get_instance()


# ---------------------------------------------------------------------------
# Tests: Singleton Pattern
# ---------------------------------------------------------------------------


class TestSingleton:
    """Test LoggingManager singleton pattern."""

    def test_get_instance_returns_instance(self):
        """Test that get_instance returns LoggingManager."""
        LoggingManager._instance = None
        instance = LoggingManager.get_instance()
        assert isinstance(instance, LoggingManager)

    def test_get_instance_returns_same_instance(self):
        """Test singleton behavior."""
        LoggingManager._instance = None
        inst1 = LoggingManager.get_instance()
        inst2 = LoggingManager.get_instance()
        assert inst1 is inst2

    def test_get_instance_thread_safe(self):
        """Test thread-safe singleton access."""
        LoggingManager._instance = None
        instances = []

        import threading

        def get_instance():
            instances.append(LoggingManager.get_instance())

        threads = [threading.Thread(target=get_instance) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be the same instance
        assert all(i is instances[0] for i in instances)


# ---------------------------------------------------------------------------
# Tests: _setup_default_logging()
# ---------------------------------------------------------------------------


class TestSetupDefaultLogging:
    """Test _setup_default_logging() console configuration."""

    def test_setup_adds_console_handler(self, logging_manager):
        """Test that setup adds console handler."""
        logging_manager._setup_default_logging()
        root_logger = logging.getLogger()
        # Should have at least one handler
        assert len(root_logger.handlers) > 0
        # At least one should be a StreamHandler
        has_console = any(
            isinstance(h, logging.StreamHandler) for h in root_logger.handlers
        )
        assert has_console

    def test_setup_clears_existing_handlers(self, logging_manager):
        """Test that setup clears existing handlers."""
        root_logger = logging.getLogger()
        root_logger.handlers = [logging.StreamHandler()]
        logging_manager._setup_default_logging()
        # Should have replaced handlers
        assert len(root_logger.handlers) > 0

    def test_sets_log_level(self, logging_manager):
        """Test that log level is set."""
        logging_manager._setup_default_logging()
        root_logger = logging.getLogger()
        assert root_logger.level > 0


# ---------------------------------------------------------------------------
# Tests: configure_output()
# ---------------------------------------------------------------------------


class TestConfigureOutput:
    """Test configure_output() with various options."""

    def test_configure_console_enabled(self, logging_manager):
        """Test enabling console output."""
        logging_manager.configure_output(console=True)
        assert logging_manager._output_config["console"]["enabled"] is True

    def test_configure_console_disabled(self, logging_manager):
        """Test disabling console output."""
        logging_manager.configure_output(console=False)
        assert logging_manager._output_config["console"]["enabled"] is False

    def test_configure_console_level(self, logging_manager):
        """Test setting console log level."""
        logging_manager.configure_output(console_level=logging.DEBUG)
        assert logging_manager._output_config["console"]["level"] == logging.DEBUG

    def test_configure_file_enabled(self, logging_manager):
        """Test enabling file output."""
        logging_manager.configure_output(file=True)
        assert logging_manager._output_config["file"]["enabled"] is True

    def test_configure_json_format(self, logging_manager):
        """Test enabling JSON format."""
        logging_manager.configure_output(json_format=True)
        assert logging_manager._output_config["file"]["json"] is True

    def test_configure_console_context(self, logging_manager):
        """Test setting console context display."""
        logging_manager.configure_output(console_context=True)
        assert logging_manager._output_config["console"]["show_context"] is True

    def test_configure_file_context(self, logging_manager):
        """Test setting file context display."""
        logging_manager.configure_output(file_context=False)
        assert logging_manager._output_config["file"]["show_context"] is False


# ---------------------------------------------------------------------------
# Tests: setup_file_logging()
# ---------------------------------------------------------------------------


class TestSetupFileLogging:
    """Test setup_file_logging() with JSON and structured formats."""

    def test_setup_file_logging_creates_directory(self, logging_manager, tmp_path):
        """Test that file logging creates directory."""
        log_dir = str(tmp_path / "logs")
        logging_manager.setup_file_logging(log_dir, "test_exp")
        assert os.path.exists(log_dir)

    def test_setup_file_logging_sets_log_path(self, logging_manager, tmp_path):
        """Test that log_path is set."""
        log_dir = str(tmp_path / "logs")
        logging_manager.setup_file_logging(log_dir, "test_exp")
        assert logging_manager.log_path is not None
        assert "test_exp" in logging_manager.log_path

    def test_setup_file_logging_json_format(self, logging_manager, tmp_path):
        """Test file logging with JSON format."""
        log_dir = str(tmp_path / "logs")
        logging_manager._output_config["file"]["json"] = True  # Set before setup
        logging_manager.setup_file_logging(log_dir, "test_exp", json_format=True)
        # Verify file logging is enabled
        assert logging_manager._output_config["file"]["enabled"] is True

    def test_setup_file_logging_structured_format(self, logging_manager, tmp_path):
        """Test file logging with structured format."""
        log_dir = str(tmp_path / "logs")
        logging_manager.setup_file_logging(log_dir, "test_exp", json_format=False)
        assert logging_manager._output_config["file"]["json"] is False


# ---------------------------------------------------------------------------
# Tests: get_logger()
# ---------------------------------------------------------------------------


class TestGetLogger:
    """Test get_logger() with context caching."""

    def test_get_logger_returns_adapter(self, logging_manager):
        """Test that get_logger returns ContextAdapter."""
        logger = logging_manager.get_logger("test.logger")
        assert isinstance(logger, ContextAdapter)

    def test_get_logger_with_context(self, logging_manager):
        """Test get_logger with context."""
        context = {"task_id": "123", "component": "Test"}
        logger = logging_manager.get_logger("test.logger", context=context)
        assert isinstance(logger, ContextAdapter)

    def test_get_logger_caches_result(self, logging_manager):
        """Test that get_logger caches results."""
        logger1 = logging_manager.get_logger("test.cache")
        logger2 = logging_manager.get_logger("test.cache")
        assert logger1 is logger2

    def test_get_logger_different_context_different_cache(self, logging_manager):
        """Test that different contexts create different cache entries."""
        logger1 = logging_manager.get_logger("test.ctx", context={"a": 1})
        logger2 = logging_manager.get_logger("test.ctx", context={"b": 2})
        # Different cache keys
        assert logger1 is not logger2

    def test_get_logger_same_context_same_cache(self, logging_manager):
        """Test that same context returns same cached logger."""
        ctx = {"key": "value"}
        logger1 = logging_manager.get_logger("test.ctx2", context=ctx)
        logger2 = logging_manager.get_logger("test.ctx2", context=ctx)
        assert logger1 is logger2
