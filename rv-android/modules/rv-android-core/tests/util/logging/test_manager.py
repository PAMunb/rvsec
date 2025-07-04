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

    def test_context_display_default_configuration(self, cleanup_instance):
        """Test that context display is enabled by default with correct settings"""
        manager = LoggingManager.get_instance()

        # Check default context display configuration
        assert manager._output_config['console']['show_context'] is True
        assert manager._output_config['console']['max_context_length'] == 120
        assert manager._output_config['file']['show_context'] is True
        assert manager._output_config['file']['max_context_length'] == 200

    def test_toggle_context_display(self, cleanup_instance):
        """Test toggling context display for console and file"""
        manager = LoggingManager.get_instance()

        # Initial state
        assert manager._output_config['console']['show_context'] is True
        assert manager._output_config['file']['show_context'] is True

        # Toggle console context off
        manager.toggle_context_display(console=False)
        assert manager._output_config['console']['show_context'] is False
        assert manager._output_config['file']['show_context'] is True

        # Toggle file context off
        manager.toggle_context_display(file=False)
        assert manager._output_config['console']['show_context'] is False
        assert manager._output_config['file']['show_context'] is False

        # Toggle both back on
        manager.toggle_context_display(console=True, file=True)
        assert manager._output_config['console']['show_context'] is True
        assert manager._output_config['file']['show_context'] is True

    def test_toggle_context_display_none_values(self, cleanup_instance):
        """Test that None values in toggle_context_display don't change settings"""
        manager = LoggingManager.get_instance()

        # Set initial state
        manager._output_config['console']['show_context'] = False
        manager._output_config['file']['show_context'] = True

        # Toggle with None values
        manager.toggle_context_display(console=None, file=None)

        # Values should remain unchanged
        assert manager._output_config['console']['show_context'] is False
        assert manager._output_config['file']['show_context'] is True

    def test_toggle_context_display_validation(self, cleanup_instance):
        """Test that toggle_context_display validates input parameters"""
        manager = LoggingManager.get_instance()

        # Test invalid console parameter
        with pytest.raises(Exception) as exc_info:
            manager.toggle_context_display(console="invalid")
        assert "Console context display must be boolean" in str(exc_info.value)

        # Test invalid file parameter
        with pytest.raises(Exception) as exc_info:
            manager.toggle_context_display(file=123)
        assert "File context display must be boolean" in str(exc_info.value)

    def test_configure_context_display(self, cleanup_instance):
        """Test comprehensive context display configuration"""
        manager = LoggingManager.get_instance()

        # Configure all parameters
        manager.configure_context_display(
            console_context=False,
            file_context=True,
            console_max_length=50,
            file_max_length=300
        )

        # Check configuration was applied
        assert manager._output_config['console']['show_context'] is False
        assert manager._output_config['file']['show_context'] is True
        assert manager._output_config['console']['max_context_length'] == 50
        assert manager._output_config['file']['max_context_length'] == 300

    def test_configure_context_display_partial(self, cleanup_instance):
        """Test partial configuration of context display"""
        manager = LoggingManager.get_instance()

        # Store initial values
        initial_console_context = manager._output_config['console']['show_context']
        initial_file_length = manager._output_config['file']['max_context_length']

        # Configure only console max length
        manager.configure_context_display(console_max_length=80)

        # Check only specified value changed
        assert manager._output_config['console']['max_context_length'] == 80
        assert manager._output_config['console']['show_context'] == initial_console_context
        assert manager._output_config['file']['max_context_length'] == initial_file_length

    def test_configure_context_display_validation(self, cleanup_instance):
        """Test that configure_context_display validates input parameters"""
        manager = LoggingManager.get_instance()

        # Test invalid console context
        with pytest.raises(Exception) as exc_info:
            manager.configure_context_display(console_context="invalid")
        assert "Console context display must be boolean" in str(exc_info.value)

        # Test invalid file context
        with pytest.raises(Exception) as exc_info:
            manager.configure_context_display(file_context=123)
        assert "File context display must be boolean" in str(exc_info.value)

        # Test invalid console max length
        with pytest.raises(Exception) as exc_info:
            manager.configure_context_display(console_max_length=-1)
        assert "Console max context length must be positive integer" in str(exc_info.value)

        # Test invalid file max length
        with pytest.raises(Exception) as exc_info:
            manager.configure_context_display(file_max_length="invalid")
        assert "File max context length must be positive integer" in str(exc_info.value)

    def test_get_context_display_config(self, cleanup_instance):
        """Test getting current context display configuration"""
        manager = LoggingManager.get_instance()

        # Set specific configuration
        manager.configure_context_display(
            console_context=False,
            file_context=True,
            console_max_length=100,
            file_max_length=250
        )

        # Get configuration
        config = manager.get_context_display_config()

        # Check returned configuration
        expected_config = {
            'console': {
                'show_context': False,
                'max_context_length': 100
            },
            'file': {
                'show_context': True,
                'max_context_length': 250
            }
        }

        assert config == expected_config

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
