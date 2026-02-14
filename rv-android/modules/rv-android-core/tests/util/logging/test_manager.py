# tests/util/logging/test_manager.py
import io
import logging

import pytest

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.context_adapter import ContextAdapter
from rv_android_core.util.logging.formatters import StructuredFormatter
from rv_android_core.util.logging.manager import LoggingManager


class TestLoggingManager:
    """Tests for LoggingManager class"""

    @pytest.fixture
    def cleanup_instance(self):
        """Fixture to reset the singleton instance between tests"""
        # Store original instance
        original_instance = LoggingManager._instance
        # Reset instance for test
        LoggingManager._instance = None
        # Run test
        yield
        # Restore original instance and clean root logger handlers
        LoggingManager._instance = original_instance
        logging.getLogger().handlers = []

    def test_singleton_pattern(self, cleanup_instance):
        """Test that LoggingManager implements the singleton pattern correctly"""
        # Get two instances
        instance1 = LoggingManager.get_instance()
        instance2 = LoggingManager.get_instance()

        # Both should be the same object
        assert instance1 is instance2
        assert isinstance(instance1, LoggingManager)

    def test_initialization(self, cleanup_instance):
        """Test that LoggingManager initializes with correct defaults"""
        manager = LoggingManager.get_instance()

        # Check default attributes
        assert manager.root_logger.name == 'root'
        assert manager.log_path is None
        assert manager.logger_cache == {}

        # Check default output config
        assert manager._output_config['console']['enabled'] is True
        assert manager._output_config['console']['level'] == logging.INFO
        assert manager._output_config['file']['enabled'] is False

    def test_get_instance_initialization(self, cleanup_instance):
        """Test that get_instance initializes properly"""
        # Get instance once
        instance = LoggingManager.get_instance()

        # Check basic initialization
        assert instance is not None
        assert instance.root_logger is not None

    def test_get_logger(self, cleanup_instance):
        """Test getting a logger with context"""
        manager = LoggingManager.get_instance()

        # Get a logger with context
        context = {"app": "test_app", CONTEXT_COMPONENT: "test_component"}
        logger = manager.get_logger("test.logger", context)

        # Check logger properties
        assert isinstance(logger, ContextAdapter)
        assert logger.context == context

        # Check that logger was cached
        assert len(manager.logger_cache) > 0

    def test_get_logger_cache(self, cleanup_instance):
        """Test that loggers are cached and reused"""
        manager = LoggingManager.get_instance()

        # Get logger twice with same name and context
        logger1 = manager.get_logger("test.logger", {"app": "test_app"})
        logger2 = manager.get_logger("test.logger", {"app": "test_app"})

        # Should be same object
        assert logger1 is logger2

        # Get logger with different context
        logger3 = manager.get_logger("test.logger", {"app": "different_app"})

        # Should be different object
        assert logger1 is not logger3

    def test_configure_output_basic(self, cleanup_instance):
        """Test that configure_output updates the config values"""
        manager = LoggingManager.get_instance()

        # Initial values
        assert manager._output_config['console']['level'] == logging.INFO

        # Configure output
        manager.configure_output(console_level=logging.DEBUG)

        # Check that config was updated
        assert manager._output_config['console']['level'] == logging.DEBUG

    def test_get_logger_with_different_contexts(self, cleanup_instance):
        """Test getting loggers with different contexts"""
        manager = LoggingManager.get_instance()

        # Get loggers with different contexts
        logger1 = manager.get_logger("test.logger", {"app": "app1"})
        logger2 = manager.get_logger("test.logger", {"app": "app2"})

        # Should be different loggers
        assert logger1 is not logger2
        assert logger1.context != logger2.context

        # Check cache keys are different
        assert len(manager.logger_cache) == 2

    def test_context_display_default_configuration(self, cleanup_instance):
        """Test that context display is enabled by default with correct settings"""
        manager = LoggingManager.get_instance()

        # Check default context display configuration
        assert manager._output_config['console']['show_context'] is True
        assert manager._output_config['console']['max_context_length'] == 120
        assert manager._output_config['file']['show_context'] is True
        assert manager._output_config['file']['max_context_length'] == 200

    def test_configure_output_with_context_parameters(self, cleanup_instance):
        """Test that configure_output handles context parameters correctly"""
        manager = LoggingManager.get_instance()

        # Configure output with context parameters
        manager.configure_output(
            console=True,
            file=True,
            console_context=False,
            file_context=True
        )

        # Check context configuration was applied
        assert manager._output_config['console']['show_context'] is False
        assert manager._output_config['file']['show_context'] is True

        # Configure output with None context parameters
        manager.configure_output(
            console_level=logging.DEBUG,
            console_context=None,
            file_context=None
        )

        # Context settings should remain unchanged
        assert manager._output_config['console']['show_context'] is False
        assert manager._output_config['file']['show_context'] is True

    def test_root_logger_receives_handlers(self, cleanup_instance):
        """Test that any logger propagates through root logger's StructuredFormatter.

        This validates the core fix: LoggingManager attaches handlers to the root
        logger, so all loggers (regardless of name) receive StructuredFormatter.
        """
        manager = LoggingManager.get_instance()

        # Create a logger with an unrelated name (not a child of 'rvandroid')
        test_logger = logging.getLogger("some.unrelated.module")

        # Capture output from root logger's handler
        stream = io.StringIO()
        # Replace the handler's stream temporarily
        root_handler = manager.root_logger.handlers[0]
        original_stream = root_handler.stream
        root_handler.stream = stream

        try:
            test_logger.info("Test message from unrelated module")
            output = stream.getvalue()
        finally:
            root_handler.stream = original_stream

        # The message should have been formatted by StructuredFormatter
        assert "Test message from unrelated module" in output

    def test_logging_manager_overrides_basic_config(self, cleanup_instance):
        """Test that LoggingManager replaces any existing basicConfig handlers.

        This validates that the guard checking 'root already has handlers' was
        removed. LoggingManager is authoritative and replaces previous handlers.
        """
        # Set up basicConfig first (simulates CLI calling basicConfig before LoggingManager)
        logging.basicConfig(level=logging.WARNING)
        assert len(logging.getLogger().handlers) > 0

        # Initialize LoggingManager — should replace basicConfig handlers
        manager = LoggingManager.get_instance()

        # Root logger should have LoggingManager's handlers, not basicConfig's
        root = logging.getLogger()
        assert root.level == logging.INFO  # LoggingManager's default, not WARNING
        assert len(root.handlers) == 1  # Only LoggingManager's console handler
        assert isinstance(root.handlers[0].formatter, StructuredFormatter)

    def test_get_logger_receives_structured_formatter(self, cleanup_instance):
        """Test that loggers from get_logger() receive StructuredFormatter via root."""
        manager = LoggingManager.get_instance()

        # Get a logger via get_logger
        logger = manager.get_logger("some.module")

        # The underlying logger should propagate to root which has StructuredFormatter
        root = logging.getLogger()
        assert len(root.handlers) > 0
        assert isinstance(root.handlers[0].formatter, StructuredFormatter)

        # The logger itself should not have its own handlers (propagates to root)
        assert len(logging.getLogger("some.module").handlers) == 0
