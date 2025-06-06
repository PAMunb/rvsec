# tests/util/logging/test_manager.py
import logging

import pytest

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.context_adapter import ContextAdapter
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
        # Restore original instance
        LoggingManager._instance = original_instance

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
        assert manager.root_logger.name == 'rvandroid'
        assert manager.log_path is None
        assert manager.logger_cache == {}
        assert manager.context_registry == {}

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

        # Check that context was registered
        assert manager.context_registry.get("test.logger") == context

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

    def test_register_context(self, cleanup_instance):
        """Test registering a context for a logger name"""
        manager = LoggingManager.get_instance()

        # Register context
        context = {"app": "test_app", "component": "test_component"}
        manager.register_context("test.logger", context)

        # Check that context was registered
        assert manager.context_registry.get("test.logger") == context

        # Context should be a copy
        context["new_key"] = "new_value"
        assert "new_key" not in manager.context_registry.get("test.logger")

    def test_get_context(self, cleanup_instance):
        """Test getting a registered context"""
        manager = LoggingManager.get_instance()

        # Register context
        context = {"app": "test_app", "component": "test_component"}
        manager.register_context("test.logger", context)

        # Get context
        retrieved_context = manager.get_context("test.logger")

        # Should be same content
        assert retrieved_context == context

        # Get non-existent context
        empty_context = manager.get_context("non.existent")

        # Should return empty dict
        assert empty_context == {}

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

    def test_complex_context_registration(self, cleanup_instance):
        """Test registering and retrieving complex contexts"""
        manager = LoggingManager.get_instance()

        # Create complex context
        complex_context = {
            "app": "test_app",
            "component": "test_component",
            "nested": {
                "key1": "value1",
                "key2": 123
            },
            "list": [1, 2, 3]
        }

        # Register context
        manager.register_context("complex.logger", complex_context)

        # Retrieve context
        retrieved_context = manager.get_context("complex.logger")

        # Should be same content
        assert retrieved_context == complex_context

        # But should be a copy
        assert retrieved_context is not complex_context
