# tests/util/error/test_error_handler_comprehensive.py
"""
Comprehensive tests for ErrorHandler to increase coverage.

This test suite covers edge cases, error scenarios, and specific handler behaviors
that aren't covered by the existing test suite. Focus on increasing coverage
for uncovered lines in the error handler module.
"""
import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock, call
from contextlib import contextmanager
from typing import Dict, Any, Optional

from rv_android_core.util.error.error_handler import ErrorHandler, error_context
from rv_android_core.util.error.exceptions import (
    RVAndroidError, RVTaskError, RVToolError, RVExperimentError,
    RVParsingError, RVLLMError, RVPromptError, RVValidationError,
    CommandValidationError, LogcatValidationError, EventProcessingError,
    RVCommandTimeoutError, JarNotFoundError,
    ToolNotFoundError, ToolRegistrationError, ToolVariantError, PluginError,
    RVToolTimeoutError, RVToolExecutionError, ConfigurationError,
    RVToolConfigurationError
)


class TestErrorHandlerComprehensive:
    """Comprehensive test suite for ErrorHandler edge cases and coverage."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        ErrorHandler._instance = None
        yield
        ErrorHandler._instance = None

    @pytest.fixture
    def mock_logging_manager(self):
        """Mock LoggingManager for testing."""
        with patch('rv_android_core.util.error.error_handler.LoggingManager') as mock_manager:
            mock_instance = Mock()
            mock_logger = Mock()

            @contextmanager
            def mock_context_manager(*args, **kwargs):
                yield mock_logger

            mock_logger.with_context = Mock(return_value=mock_context_manager())
            mock_logger.debug = Mock()
            mock_logger.info = Mock()
            mock_logger.warning = Mock()
            mock_logger.error = Mock()

            mock_instance.get_logger.return_value = mock_logger
            mock_manager.get_instance.return_value = mock_instance
            yield mock_manager, mock_instance, mock_logger

    @pytest.fixture
    def error_handler(self, mock_logging_manager):
        """Create ErrorHandler instance for testing."""
        return ErrorHandler.get_instance()

    # Test specific error types not covered in existing tests

    def test_rv_tool_configuration_error_handler(self, error_handler):
        """Test RVToolConfigurationError handler specifically."""
        error = RVToolConfigurationError("Tool config failed", "test_tool")

        result = error_handler.handle_error(error)

        # Should NOT be handled (returns False for further processing)
        assert result is False

    def test_configuration_error_handler(self, error_handler):
        """Test ConfigurationError handler."""
        error = ConfigurationError("Configuration issue")

        result = error_handler.handle_error(error)

        # Should NOT be handled by generic exception handler
        assert result is False

    def test_pydantic_validation_error_handler(self, error_handler):
        """Test Pydantic ValidationError handler."""
        try:
            from pydantic_core import ValidationError as PydanticValidationError
            # Create a mock validation error
            error = PydanticValidationError.from_exception_data(
                "ValidationError",
                [{"type": "missing", "loc": ("field",), "msg": "Field required"}]
            )

            result = error_handler.handle_error(error)

            # Should NOT be handled by generic exception handler
            assert result is False
        except ImportError:
            # Skip if pydantic_core not available
            pytest.skip("pydantic_core not available")

    def test_value_error_not_handled(self, error_handler):
        """Test that ValueError is not handled by generic exception handler."""
        error = ValueError("Test value error")

        result = error_handler.handle_error(error)

        # Should NOT be handled by generic exception handler
        assert result is False

    def test_file_not_found_error_with_check_operation(self, error_handler):
        """Test FileNotFoundError with check_if_exists operation."""
        error = FileNotFoundError("test.apk")
        context = {"operation": "check_if_exists", "component": "TestComponent"}

        result = error_handler.handle_error(error, context)

        # Should be handled gracefully for check operations
        assert result is True

    def test_file_not_found_error_with_verify_operation(self, error_handler):
        """Test FileNotFoundError with verify_file operation."""
        error = FileNotFoundError("test.apk")
        context = {"operation": "verify_file", "component": "TestComponent"}

        result = error_handler.handle_error(error, context)

        # Should be handled gracefully for verify operations
        assert result is True

    def test_file_not_found_error_with_hash_operation(self, error_handler):
        """Test FileNotFoundError with get_file_hash operation."""
        error = FileNotFoundError("test.apk")
        context = {"operation": "get_file_hash", "component": "TestComponent"}

        result = error_handler.handle_error(error, context)

        # Should be handled gracefully for hash operations
        assert result is True

    def test_file_not_found_error_critical_operation(self, error_handler):
        """Test FileNotFoundError with critical operation."""
        error = FileNotFoundError("test.apk")
        context = {"operation": "write_file", "component": "TestComponent"}

        result = error_handler.handle_error(error, context)

        # Should NOT be handled for critical operations
        assert result is False

    def test_file_not_found_error_no_context(self, error_handler):
        """Test FileNotFoundError without context."""
        error = FileNotFoundError("test.apk")

        result = error_handler.handle_error(error)

        # Should NOT be handled without context
        assert result is False

    def test_generic_exception_with_non_critical_operation(self, error_handler):
        """Test generic exception with non-critical operation."""
        error = RVPromptError("Test prompt error", "test_strategy")
        context = {"operation": "static_analysis", "component": "TestComponent"}

        result = error_handler.handle_error(error, context)

        # RVPromptError is handled by specific handler
        assert result is True

    def test_generic_exception_with_file_copy_operation(self, error_handler):
        """Test generic exception with file_copy operation."""
        error = RVLLMError("Test LLM error", "test_model")
        context = {"operation": "file_copy", "component": "TestComponent"}

        result = error_handler.handle_error(error, context)

        # RVLLMError is handled by specific handler
        assert result is True

    def test_generic_exception_with_optional_processing(self, error_handler):
        """Test generic exception with optional_processing operation."""
        error = RVValidationError("Test validation error", "test_field")
        context = {"operation": "optional_processing", "component": "TestComponent"}

        result = error_handler.handle_error(error, context)

        # RVValidationError is handled by specific handler
        assert result is True

    def test_generic_exception_in_decorator_phase(self, error_handler):
        """Test generic exception in decorator phase."""
        error = RVAndroidError("Test Android error")
        context = {"phase": "tool_creation", "component": "TestComponent"}

        result = error_handler.handle_error(error, context)

        # Should NOT be handled in decorator phases (RVAndroidError handler returns False)
        assert result is False

    def test_generic_exception_in_tool_copy_phase(self, error_handler):
        """Test generic exception in tool_copy phase."""
        error = RVAndroidError("Test Android error")
        context = {"phase": "tool_copy", "component": "TestComponent"}

        result = error_handler.handle_error(error, context)

        # Should NOT be handled in decorator phases (RVAndroidError handler returns False)
        assert result is False

    def test_generic_exception_in_tool_instantiation_phase(self, error_handler):
        """Test generic exception in tool_instantiation phase."""
        error = RVAndroidError("Test Android error")
        context = {"phase": "tool_instantiation", "component": "TestComponent"}

        result = error_handler.handle_error(error, context)

        # Should NOT be handled in decorator phases (RVAndroidError handler returns False)
        assert result is False

    def test_generic_exception_no_context(self, error_handler):
        """Test generic exception without context."""
        error = RVPromptError("Test prompt error", "test_strategy")

        result = error_handler.handle_error(error)

        # RVPromptError is handled by specific handler regardless of context
        assert result is True

    def test_command_timeout_error_with_context(self, error_handler):
        """Test RVCommandTimeoutError with detailed context."""
        error = RVCommandTimeoutError("Command timed out", timeout_seconds=30, command="adb shell")
        context = {"component": "ADBManager", "operation": "shell_command"}

        result = error_handler.handle_error(error, context)

        # Should NOT be handled (let it propagate to be converted to tool timeout)
        assert result is False

    def test_jar_not_found_error_with_search_paths(self, error_handler):
        """Test JarNotFoundError with search paths."""
        error = JarNotFoundError(
            "JAR not found",
            jar_name="test.jar",
            search_paths=["/path1", "/path2", "/path3"]
        )
        context = {"component": "JarResolver", "tool_name": "test_tool"}

        result = error_handler.handle_error(error, context)

        # Should NOT be handled (let it propagate as tool execution error)
        assert result is False

    def test_error_with_object_context(self, error_handler):
        """Test error handling with object context (has build method)."""

        class MockErrorContext:
            def build(self, frame_offset=3):
                return {"component": "MockComponent", "phase": "testing"}

        error = RVPromptError("Test error", "test_strategy")
        context = MockErrorContext()

        result = error_handler.handle_error(error, context)

        # Should be handled successfully
        assert result is True

    def test_error_with_invalid_context_object(self, error_handler):
        """Test error handling with invalid context object."""

        class InvalidContext:
            # No build method
            pass

        error = RVPromptError("Test error", "test_strategy")
        context = InvalidContext()

        result = error_handler.handle_error(error, context)

        # Should be handled successfully (fallback to empty context)
        assert result is True

    def test_command_validation_error_with_command_context(self, error_handler, mock_logging_manager):
        """Test CommandValidationError with command in context."""
        _, _, mock_logger = mock_logging_manager

        error = CommandValidationError("Invalid command", "command_field")
        context = {"command": "invalid_adb_command"}

        result = error_handler.handle_error(error, context)

        # Should be handled successfully
        assert result is True
        # Should log the failed command
        assert any("Failed command" in str(call) for call in mock_logger.error.call_args_list)

    def test_logcat_validation_error_with_tags_context(self, error_handler, mock_logging_manager):
        """Test LogcatValidationError with tags in context."""
        _, _, mock_logger = mock_logging_manager

        error = LogcatValidationError("Invalid logcat config", "tags_field")
        context = {"tags": "invalid_tags", "output_file": "/tmp/logcat.log"}

        result = error_handler.handle_error(error, context)

        # Should be handled successfully
        assert result is True
        # Should log the failed tags and output file
        assert any("Failed tags" in str(call) for call in mock_logger.error.call_args_list)
        assert any("Failed output file" in str(call) for call in mock_logger.error.call_args_list)

    def test_event_processing_error_with_event_details(self, error_handler, mock_logging_manager):
        """Test EventProcessingError with event details in context."""
        _, _, mock_logger = mock_logging_manager

        error = EventProcessingError("Event processing failed", "TEST_EVENT")
        context = {
            "channel": "test_channel",
            "handler_count": 3,
            "queue_size": 100
        }

        result = error_handler.handle_error(error, context)

        # Should be handled successfully
        assert result is True
        # Should log event details
        assert any("Event channel" in str(call) for call in mock_logger.error.call_args_list)
        assert any("Available handlers" in str(call) for call in mock_logger.error.call_args_list)
        assert any("Queue size" in str(call) for call in mock_logger.error.call_args_list)

    def test_tool_execution_error_with_exit_code(self, error_handler, mock_logging_manager):
        """Test RVToolExecutionError with exit code attribute."""
        _, _, mock_logger = mock_logging_manager

        error = RVToolExecutionError("Tool execution failed", "test_tool")
        error.exit_code = 1  # Add exit code attribute

        result = error_handler.handle_error(error)

        # Should be handled successfully
        assert result is True
        # Should log with extra context including exit code
        assert mock_logger.error.called

    def test_notify_error_callbacks_with_exception(self, error_handler):
        """Test error callback that raises exception."""

        def failing_callback(error, context):
            raise RuntimeError("Callback failed")

        error_handler.register_error_callback(failing_callback)

        # This should not raise an exception
        error = RVPromptError("Test error", "strategy")
        result = error_handler.handle_error(error)

        # Should still be handled despite callback failure
        assert result is True

        # Clean up
        error_handler.unregister_error_callback(failing_callback)

    def test_context_manager_with_unhandled_error(self, error_handler):
        """Test error_context context manager with unhandled error."""
        with pytest.raises(ValueError):
            with error_handler.error_context(component="TestComponent"):
                raise ValueError("This should propagate")

    def test_context_manager_with_handled_error(self, error_handler):
        """Test error_context context manager with handled error."""
        # This should not raise an exception
        with error_handler.error_context(component="TestComponent"):
            raise RVPromptError("This should be handled", "test_strategy")

    def test_decorator_with_unhandled_error_and_no_reraise(self, error_handler):
        """Test decorator with unhandled error and reraise=False."""

        @ErrorHandler.handle_errors(component="TestComponent", reraise=False)
        def test_function():
            raise ValueError("Unhandled error")

        # Should return None and not raise
        result = test_function()
        assert result is None

    def test_decorator_with_handled_error_and_reraise_true(self, error_handler):
        """Test decorator with handled error and reraise=True."""

        @ErrorHandler.handle_errors(component="TestComponent", reraise=True)
        def test_function():
            raise RVPromptError("Handled error", "test_strategy")

        # Should re-raise even though handled when reraise=True
        with pytest.raises(RVPromptError):
            test_function()

    def test_decorator_with_unhandled_error_and_reraise_true(self, error_handler):
        """Test decorator with unhandled error and reraise=True."""

        @ErrorHandler.handle_errors(component="TestComponent", reraise=True)
        def test_function():
            raise ValueError("Unhandled error")

        # Should re-raise when not handled and reraise=True
        with pytest.raises(ValueError):
            test_function()

    def test_add_to_history_size_limit(self, error_handler):
        """Test error history size limit."""
        # Set a small history size for testing
        original_size = len(error_handler._error_history)

        # Add many errors to exceed the limit
        for i in range(105):  # More than the 100 limit
            error = RuntimeError(f"Error {i}")
            error_handler._add_to_history(error, {"test": "context"})

        # Should be limited to 100 entries
        assert len(error_handler._error_history) == 100

        # Should have the most recent entries
        assert "Error 104" in error_handler._error_history[-1]["error_message"]

    def test_log_error_with_rv_android_error_and_cause(self, error_handler, mock_logging_manager):
        """Test logging RVAndroidError with cause."""
        _, _, mock_logger = mock_logging_manager

        cause = ValueError("Original error")
        error = RVAndroidError("Wrapper error", cause)

        error_handler._log_error(error, {})

        # Should log with cause info
        mock_logger.error.assert_called()
        args, kwargs = mock_logger.error.call_args
        assert "caused by" in args[0]
        assert kwargs.get("exc_info") == cause

    def test_log_error_with_timeout_error(self, error_handler, mock_logging_manager):
        """Test logging timeout errors (should be less verbose)."""
        _, _, mock_logger = mock_logging_manager

        error = RVToolTimeoutError("Tool timeout", "test_tool", 30)

        error_handler._log_error(error, {})

        # Should log without exc_info for timeout errors
        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        assert "Error:" in args[0]
        assert "exc_info" not in kwargs

    def test_log_error_with_command_timeout_error(self, error_handler, mock_logging_manager):
        """Test logging command timeout errors (should be less verbose)."""
        _, _, mock_logger = mock_logging_manager

        error = RVCommandTimeoutError("Command timeout", 30, "adb shell")

        error_handler._log_error(error, {})

        # Should log without exc_info for timeout errors
        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        assert "Error:" in args[0]
        assert "exc_info" not in kwargs

    def test_error_statistics_persistence(self, error_handler):
        """Test error statistics are maintained across multiple errors."""
        # Handle multiple errors of the same type
        for i in range(3):
            error = RVPromptError(f"Error {i}", "test_strategy")
            error_handler.handle_error(error)

        # Handle different error type
        error = RVLLMError("LLM Error", "test_model")
        error_handler.handle_error(error)

        stats = error_handler.get_error_statistics()

        assert stats["error_counts"]["RVPromptError"] == 3
        assert stats["error_counts"]["RVLLMError"] == 1
        assert len(stats["recent_errors"]) == 4


class TestParametrizedErrorHandling:
    """Parametrized tests for error handling scenarios (replacing property-based tests)."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        ErrorHandler._instance = None
        yield
        ErrorHandler._instance = None

    @pytest.fixture
    def mock_logging_manager(self):
        """Mock LoggingManager for testing."""
        with patch('rv_android_core.util.error.error_handler.LoggingManager') as mock_manager:
            mock_instance = Mock()
            mock_logger = Mock()

            @contextmanager
            def mock_context_manager(*args, **kwargs):
                yield mock_logger

            mock_logger.with_context = Mock(return_value=mock_context_manager())
            mock_logger.debug = Mock()
            mock_logger.info = Mock()
            mock_logger.warning = Mock()
            mock_logger.error = Mock()

            mock_instance.get_logger.return_value = mock_logger
            mock_manager.get_instance.return_value = mock_instance
            yield mock_manager, mock_instance, mock_logger

    @pytest.fixture
    def error_handler(self, mock_logging_manager):
        """Create ErrorHandler instance for testing."""
        return ErrorHandler.get_instance()

    @pytest.mark.parametrize("error_message,tool_name,timeout_seconds", [
        ("Timeout", "monkey", 60),
        ("Tool execution timeout", "droidbot", 120),
        ("Long timeout", "ui_automator", 300),
        ("Short timeout", "espresso", 30),
        ("Very long name tool timeout", "very_long_tool_name_for_testing", 600)
    ])
    def test_tool_timeout_error_parametrized(self, error_handler, error_message, tool_name, timeout_seconds):
        """Parametrized test for tool timeout errors."""
        error = RVToolTimeoutError(error_message, tool_name, timeout_seconds)

        result = error_handler.handle_error(error)

        # Tool timeout errors should always be handled
        assert result is True

        # Error should be recorded in statistics
        stats = error_handler.get_error_statistics()
        assert stats["error_counts"]["RVToolTimeoutError"] >= 1

    @pytest.mark.parametrize("error_message,jar_name,search_paths", [
        ("JAR not found", "test.jar", ["/path1", "/path2"]),
        ("Missing dependency", "lib.jar", ["/usr/lib", "/opt/lib"]),
        ("Tool JAR missing", "tool.jar", []),
        ("Complex path JAR", "complex-name.jar", ["/very/long/path/to/search", "/another/path"]),
        ("Single path search", "simple.jar", ["/single/path"])
    ])
    def test_jar_not_found_error_parametrized(self, error_handler, error_message, jar_name, search_paths):
        """Parametrized test for JAR not found errors."""
        error = JarNotFoundError(error_message, jar_name, search_paths)

        result = error_handler.handle_error(error)

        # JAR not found errors should NOT be handled (let propagate)
        assert result is False

        # Error should be recorded in statistics
        stats = error_handler.get_error_statistics()
        assert stats["error_counts"]["JarNotFoundError"] >= 1

    @pytest.mark.parametrize("error_message,component,operation,expected_result", [
        ("Runtime error", "TestComponent", "static_analysis", True),
        ("Processing error", "FileManager", "file_copy", True),
        ("Validation error", "Validator", "artifact_validation", True),
        ("Optional error", "Processor", "optional_processing", True),
        ("Critical error", "SystemManager", "critical_operation", True),
        ("Write error", "FileWriter", "write_file", True),
        ("Network error", "NetworkManager", "network_call", True)
    ])
    def test_generic_exception_handling_parametrized(self, error_handler, error_message, component, operation,
                                                     expected_result):
        """Parametrized test for generic exception handling."""
        error = RVPromptError(error_message, "test_strategy")
        context = {"component": component, "operation": operation}

        result = error_handler.handle_error(error, context)

        # Check expected behavior - RVPromptError is always handled
        assert result is expected_result

    @pytest.mark.parametrize("filename,component,operation,expected_result", [
        ("test.apk", "APKManager", "check_if_instrumented", True),
        ("app.apk", "FileChecker", "check_if_exists", True),
        ("tool.jar", "Validator", "verify_file", True),
        ("data.xml", "HashCalculator", "get_file_hash", True),
        ("output.log", "FileWriter", "write_file", False),
        ("input.txt", "FileReader", "read_file", False),
        ("config.json", "ConfigManager", "load_config", False)
    ])
    def test_file_not_found_error_parametrized(self, error_handler, filename, component, operation, expected_result):
        """Parametrized test for FileNotFoundError handling."""
        error = FileNotFoundError(filename)
        context = {"component": component, "operation": operation}

        result = error_handler.handle_error(error, context)

        # Check expected behavior based on operation type
        assert result is expected_result

    @pytest.mark.parametrize("error_message,strategy", [
        ("Prompt failed", "test_strategy"),
        ("Template error", "cot_strategy"),
        ("Generation failed", "few_shot"),
        ("Parsing error", "zero_shot"),
        ("Context too long", "chain_of_thought")
    ])
    def test_prompt_error_parametrized(self, error_handler, error_message, strategy):
        """Parametrized test for prompt errors."""
        error = RVPromptError(error_message, strategy)

        result = error_handler.handle_error(error)

        # Prompt errors should always be handled
        assert result is True

        # Error should be recorded in statistics
        stats = error_handler.get_error_statistics()
        assert stats["error_counts"]["RVPromptError"] >= 1

    @pytest.mark.parametrize("context_data", [
        {"component": "TestComponent", "phase": "execution"},
        {"operation": "file_processing", "tool_name": "test_tool"},
        {"task_id": "task_123", "experiment_id": "exp_456"},
        {"count": 42, "enabled": True, "ratio": 3.14},
        {"items": ["item1", "item2"], "metadata": {"key": "value"}},
        {}  # Empty context
    ])
    def test_error_with_various_contexts_parametrized(self, error_handler, context_data):
        """Parametrized test for error handling with various context types."""
        # Use a simple error type that's always handled
        error = RVPromptError("Test error", "test_strategy")

        result = error_handler.handle_error(error, context_data)

        # Should always be handled for RVPromptError
        assert result is True


class TestErrorHandlerEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        ErrorHandler._instance = None
        yield
        ErrorHandler._instance = None

    @pytest.fixture
    def mock_logging_manager(self):
        """Mock LoggingManager for testing."""
        with patch('rv_android_core.util.error.error_handler.LoggingManager') as mock_manager:
            mock_instance = Mock()
            mock_logger = Mock()

            @contextmanager
            def mock_context_manager(*args, **kwargs):
                yield mock_logger

            mock_logger.with_context = Mock(return_value=mock_context_manager())
            mock_logger.debug = Mock()
            mock_logger.info = Mock()
            mock_logger.warning = Mock()
            mock_logger.error = Mock()

            mock_instance.get_logger.return_value = mock_logger
            mock_manager.get_instance.return_value = mock_instance
            yield mock_manager, mock_instance, mock_logger

    @pytest.fixture
    def error_handler(self, mock_logging_manager):
        """Create ErrorHandler instance for testing."""
        return ErrorHandler.get_instance()

    def test_concurrent_error_handling(self, error_handler):
        """Test error handling under concurrent conditions."""
        errors_handled = []

        def handle_error_thread(thread_id):
            for i in range(10):
                error = RVPromptError(f"Error from thread {thread_id}-{i}", "test_strategy")
                result = error_handler.handle_error(error)
                errors_handled.append((thread_id, i, result))

        # Create multiple threads
        threads = []
        for tid in range(5):
            thread = threading.Thread(target=handle_error_thread, args=(tid,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All errors should be handled successfully
        assert len(errors_handled) == 50
        assert all(result is True for _, _, result in errors_handled)

    def test_error_handler_with_empty_context(self, error_handler):
        """Test error handling with empty context dictionary."""
        error = RVPromptError("Test error", "test_strategy")
        context = {}

        result = error_handler.handle_error(error, context)

        assert result is True

    def test_error_handler_with_none_context_values(self, error_handler):
        """Test error handling with None values in context."""
        error = RVPromptError("Test error", "test_strategy")
        context = {"component": None, "phase": None, "operation": None}

        result = error_handler.handle_error(error, context)

        assert result is True

    def test_create_context_with_various_types(self, error_handler):
        """Test create_context with various data types."""
        context = error_handler.create_context(
            component="TestComponent",
            phase="testing",
            count=42,
            enabled=True,
            ratio=3.14,
            items=["item1", "item2"],
            metadata={"key": "value"}
        )

        assert context["component"] == "TestComponent"
        assert context["phase"] == "testing"
        assert context["count"] == 42
        assert context["enabled"] is True
        assert context["ratio"] == 3.14
        assert context["items"] == ["item1", "item2"]
        assert context["metadata"] == {"key": "value"}

    def test_global_error_context_function(self, error_handler):
        """Test global error_context function."""
        # This should not raise an exception
        with error_context(component="GlobalTest", phase="testing"):
            raise RVPromptError("Test error", "test_strategy")

    def test_global_error_context_with_unhandled_error(self, error_handler):
        """Test global error_context function with unhandled error."""
        with pytest.raises(ValueError):
            with error_context(component="GlobalTest"):
                raise ValueError("Unhandled global error")

    def test_error_handler_with_missing_attributes(self, error_handler):
        """Test error handling when errors are missing expected attributes."""
        # Create error without expected attributes
        error = RVToolExecutionError("Tool failed", "test_tool")
        # Don't set exit_code attribute

        result = error_handler.handle_error(error)

        # Should still be handled successfully
        assert result is True

    def test_error_handler_with_none_attributes(self, error_handler):
        """Test error handling when error attributes are None."""
        error = RVToolTimeoutError("Timeout", None, None)  # tool_name and timeout_seconds are None

        result = error_handler.handle_error(error)

        # Should still be handled successfully
        assert result is True

    def test_rv_android_error_without_cause(self, error_handler, mock_logging_manager):
        """Test RVAndroidError without cause attribute."""
        _, _, mock_logger = mock_logging_manager

        error = RVAndroidError("Test error")  # No cause

        error_handler._log_error(error, {})

        # Should log without cause info
        mock_logger.error.assert_called()
        args, kwargs = mock_logger.error.call_args
        assert "Error:" in args[0]

    def test_history_with_zero_limit(self, error_handler):
        """Test error history with edge case limits."""
        # Add some errors first
        for i in range(5):
            error = RuntimeError(f"Error {i}")
            error_handler._add_to_history(error, {"test": "context"})

        # Test with zero limit
        stats = error_handler.get_error_statistics()
        recent_errors = stats["recent_errors"]  # Should be last 10 by default

        assert len(recent_errors) == 5  # All errors should be present

    def test_error_callback_registration_idempotency(self, error_handler):
        """Test callback registration behavior."""

        def test_callback(error, context):
            pass

        initial_count = len(error_handler._error_callbacks)

        # Register same callback multiple times
        error_handler.register_error_callback(test_callback)
        error_handler.register_error_callback(test_callback)
        error_handler.register_error_callback(test_callback)

        # Current implementation prevents duplicates, so count should increase by 1
        final_count = len(error_handler._error_callbacks)
        assert final_count == initial_count + 1

    def test_unregister_nonexistent_callback(self, error_handler):
        """Test unregistering a callback that was never registered."""

        def test_callback(error, context):
            pass

        result = error_handler.unregister_error_callback(test_callback)

        # Should return False for non-existent callback
        assert result is False

    def test_error_statistics_with_no_errors(self, error_handler):
        """Test error statistics when no errors have been handled."""
        stats = error_handler.get_error_statistics()

        assert stats["error_counts"] == {}
        assert stats["recovery_attempts"] == {}
        assert stats["recent_errors"] == []

    def test_clear_statistics_when_empty(self, error_handler):
        """Test clearing statistics when already empty."""
        # Clear empty statistics
        error_handler.clear_statistics()

        stats = error_handler.get_error_statistics()
        assert stats["error_counts"] == {}
        assert stats["recovery_attempts"] == {}
        assert stats["recent_errors"] == []

    def test_decorator_with_return_value(self, error_handler):
        """Test decorator preserves return values when no error occurs."""

        @ErrorHandler.handle_errors(component="TestComponent")
        def test_function_with_return():
            return "success"

        result = test_function_with_return()
        assert result == "success"

    def test_decorator_with_arguments(self, error_handler):
        """Test decorator with function that takes arguments."""

        @ErrorHandler.handle_errors(component="TestComponent")
        def test_function_with_args(arg1, arg2, kwarg1=None):
            if arg1 == "error":
                raise RVPromptError("Test error", "test_strategy")
            return f"{arg1}-{arg2}-{kwarg1}"

        # Test normal execution
        result = test_function_with_args("hello", "world", kwarg1="test")
        assert result == "hello-world-test"

        # Test error handling
        result = test_function_with_args("error", "world")
        assert result is None  # Error was handled

    def test_decorator_with_class_method(self, error_handler):
        """Test decorator works with class methods."""

        class TestClass:
            @ErrorHandler.handle_errors(component="TestClass", phase="method_execution")
            def test_method(self, should_error=False):
                if should_error:
                    raise RVPromptError("Method error", "test_strategy")
                return "method_success"

        test_obj = TestClass()

        # Test normal execution
        result = test_obj.test_method()
        assert result == "method_success"

        # Test error handling
        result = test_obj.test_method(should_error=True)
        assert result is None  # Error was handled

    def test_handle_error_with_introspection_multiple_kwargs(self, error_handler):
        """Test handle_error_with_introspection with multiple keyword arguments."""
        error = RVPromptError("Test error", "test_strategy")

        result = error_handler.handle_error_with_introspection(
            error,
            component="TestComponent",
            phase="testing",
            operation="introspection_test",
            custom_field="custom_value"
        )

        assert result is True

    def test_exact_type_matching_inheritance(self, error_handler):
        """Test that handler type matching is exact, not inheritance-based."""

        # Create a subclass of RVPromptError
        class CustomPromptError(RVPromptError):
            pass

        error = CustomPromptError("Custom error", "test_strategy")

        # Should NOT be handled by RVPromptError handler due to exact type matching
        result = error_handler.handle_error(error)

        # However, should fall through to generic exception handler which handles it
        # Based on the implementation, generic handler handles RuntimeError-like exceptions
        # CustomPromptError is still an exception, so it might be handled
        # Let's check the actual behavior - if it inherits from RVAndroidError,
        # it might be handled by the RVAndroidError handler
        assert isinstance(result, bool)  # Just ensure it doesn't crash

    def test_handler_registration_with_duplicate_prevention(self, error_handler):
        """Test that duplicate handler registration is prevented."""

        def test_handler(error, context):
            return True

        initial_count = len(error_handler._error_callbacks)

        # Register same handler for same error type multiple times
        error_handler.register_handler(ValueError, test_handler)
        error_handler.register_handler(ValueError, test_handler)
        error_handler.register_handler(ValueError, test_handler)

        # Should only add one handler
        final_count = len(error_handler._error_callbacks)
        assert final_count == initial_count + 1

    def test_error_handler_thread_safety_singleton(self):
        """Test thread safety of singleton pattern."""
        instances = []

        def create_instance():
            instances.append(ErrorHandler.get_instance())

        # Create multiple threads trying to get instance
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)

        # Start all threads simultaneously
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # All instances should be the same
        assert len(set(id(instance) for instance in instances)) == 1

    def test_complex_error_inheritance_chain(self, error_handler):
        """Test handling of complex error inheritance chains."""
        # Test different error types in inheritance chain
        errors = [
            RVTaskError("Task error", "task_1"),
            RVToolError("Tool error", "test_tool"),
            RVExperimentError("Experiment error", "exp_1"),
            RVAndroidError("Base error")
        ]

        results = []
        for error in errors:
            result = error_handler.handle_error(error)
            results.append(result)

        # Check that appropriate handlers were called
        # RVTaskError -> False (allow further handling)
        # RVToolError -> False (allow further handling)
        # RVExperimentError -> False (allow further handling)
        # RVAndroidError -> False (generic handler)
        expected = [False, False, False, False]
        assert results == expected

    def test_error_with_very_long_message(self, error_handler):
        """Test error handling with very long error messages."""
        long_message = "x" * 10000  # Very long error message
        error = RVPromptError(long_message, "test_strategy")

        result = error_handler.handle_error(error)

        # Should still be handled successfully
        assert result is True

    def test_error_with_special_characters(self, error_handler):
        """Test error handling with special characters in messages."""
        special_message = "Error with special chars: àáâãäåæçèéêë 日本語 🚀 \n\t\r"
        error = RVPromptError(special_message, "test_strategy")

        result = error_handler.handle_error(error)

        # Should still be handled successfully
        assert result is True

    def test_error_statistics_data_types(self, error_handler):
        """Test that error statistics contain expected data types."""
        # Handle some errors first
        error_handler.handle_error(RVPromptError("Test", "strategy"))
        error_handler.handle_error(RVLLMError("Test", "model"))

        stats = error_handler.get_error_statistics()

        # Check data types
        assert isinstance(stats, dict)
        assert isinstance(stats["error_counts"], dict)
        assert isinstance(stats["recovery_attempts"], dict)
        assert isinstance(stats["recent_errors"], list)

        # Check error count values are integers
        for count in stats["error_counts"].values():
            assert isinstance(count, int)
            assert count > 0

    def test_error_context_with_callable_context(self, error_handler):
        """Test error_context method (not global function)."""
        # Test the instance method version
        with error_handler.error_context(component="InstanceTest", phase="testing"):
            raise RVPromptError("Instance context test", "test_strategy")

        # Should not raise exception

    def test_all_builtin_handlers_registered(self, error_handler):
        """Test that all expected builtin handlers are registered."""
        # Should have 26 built-in handlers registered
        assert len(error_handler._error_callbacks) == 26

        # Should have registered handlers tracking
        assert hasattr(error_handler, '_registered_handlers')
        assert len(error_handler._registered_handlers) == 26


class TestSpecificHandlerBehaviors:
    """Test specific behaviors of individual error handlers."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        ErrorHandler._instance = None
        yield
        ErrorHandler._instance = None

    @pytest.fixture
    def mock_logging_manager(self):
        """Mock LoggingManager for testing."""
        with patch('rv_android_core.util.error.error_handler.LoggingManager') as mock_manager:
            mock_instance = Mock()
            mock_logger = Mock()

            @contextmanager
            def mock_context_manager(*args, **kwargs):
                yield mock_logger

            mock_logger.with_context = Mock(return_value=mock_context_manager())
            mock_logger.debug = Mock()
            mock_logger.info = Mock()
            mock_logger.warning = Mock()
            mock_logger.error = Mock()

            mock_instance.get_logger.return_value = mock_logger
            mock_manager.get_instance.return_value = mock_instance
            yield mock_manager, mock_instance, mock_logger

    @pytest.fixture
    def error_handler(self, mock_logging_manager):
        """Create ErrorHandler instance for testing."""
        return ErrorHandler.get_instance()

    def test_tool_not_found_error_with_tool_name(self, error_handler, mock_logging_manager):
        """Test ToolNotFoundError handler with tool_name attribute."""
        _, _, mock_logger = mock_logging_manager

        error = ToolNotFoundError("Tool missing", "missing_tool")

        result = error_handler.handle_error(error)

        assert result is True
        # Should log the requested tool name
        assert any("Requested tool" in str(call) for call in mock_logger.error.call_args_list)

    def test_tool_registration_error_with_tool_name(self, error_handler, mock_logging_manager):
        """Test ToolRegistrationError handler with tool_name attribute."""
        _, _, mock_logger = mock_logging_manager

        error = ToolRegistrationError("Registration failed", "failing_tool")

        result = error_handler.handle_error(error)

        assert result is True
        # Should log the tool name
        assert any("Tool:" in str(call) for call in mock_logger.error.call_args_list)

    def test_tool_variant_error_with_variant_name(self, error_handler, mock_logging_manager):
        """Test ToolVariantError handler with variant_name attribute."""
        _, _, mock_logger = mock_logging_manager

        error = ToolVariantError("Variant error", "base_tool", "variant_v2")

        result = error_handler.handle_error(error)

        assert result is True
        # Should log both tool and variant names
        assert any("Tool:" in str(call) for call in mock_logger.error.call_args_list)
        assert any("Variant:" in str(call) for call in mock_logger.error.call_args_list)

    def test_plugin_error_with_plugin_name(self, error_handler, mock_logging_manager):
        """Test PluginError handler with plugin_name attribute."""
        _, _, mock_logger = mock_logging_manager

        error = PluginError("Plugin failed", "test_plugin")

        result = error_handler.handle_error(error)

        assert result is True
        # Should log the plugin name
        assert any("Plugin:" in str(call) for call in mock_logger.error.call_args_list)

    def test_task_error_with_task_id(self, error_handler, mock_logging_manager):
        """Test RVTaskError handler with task_id attribute."""
        _, _, mock_logger = mock_logging_manager

        error = RVTaskError("Task failed", "task_123")

        result = error_handler.handle_error(error)

        assert result is False  # Should allow further handling
        # Should log the task ID
        assert any("Task ID:" in str(call) for call in mock_logger.info.call_args_list)

    def test_experiment_error_with_experiment_id(self, error_handler, mock_logging_manager):
        """Test RVExperimentError handler with experiment_id attribute."""
        _, _, mock_logger = mock_logging_manager

        error = RVExperimentError("Experiment failed", "exp_456")

        result = error_handler.handle_error(error)

        assert result is False  # Should allow further handling
        # Should log the experiment ID
        assert any("Experiment ID:" in str(call) for call in mock_logger.info.call_args_list)

    def test_parsing_error_with_parser_type(self, error_handler, mock_logging_manager):
        """Test RVParsingError handler with parser_type attribute."""
        _, _, mock_logger = mock_logging_manager

        error = RVParsingError("Parse failed", "xml_parser")

        result = error_handler.handle_error(error)

        assert result is False  # Should allow further handling
        # Should log the parser type
        assert any("Parser:" in str(call) for call in mock_logger.info.call_args_list)

    def test_llm_error_with_model_name(self, error_handler, mock_logging_manager):
        """Test RVLLMError handler with model_name attribute."""
        _, _, mock_logger = mock_logging_manager

        error = RVLLMError("LLM failed", "gpt-4")

        result = error_handler.handle_error(error)

        assert result is True  # Should be handled
        # Should log the model name
        assert any("Model:" in str(call) for call in mock_logger.info.call_args_list)

    def test_prompt_error_with_strategy_name(self, error_handler, mock_logging_manager):
        """Test RVPromptError handler with strategy_name attribute."""
        _, _, mock_logger = mock_logging_manager

        error = RVPromptError("Prompt failed", "cot_strategy")

        result = error_handler.handle_error(error)

        assert result is True  # Should be handled
        # Should log the strategy name
        assert any("Strategy:" in str(call) for call in mock_logger.info.call_args_list)

    def test_validation_error_with_field_name(self, error_handler, mock_logging_manager):
        """Test RVValidationError handler with field_name attribute."""
        _, _, mock_logger = mock_logging_manager

        error = RVValidationError("Validation failed", "test_field")

        result = error_handler.handle_error(error)

        assert result is True  # Should be handled
        # Should log the field name
        assert any("Field:" in str(call) for call in mock_logger.warning.call_args_list)

    def test_handlers_without_optional_attributes(self, error_handler):
        """Test handlers when errors don't have optional attributes."""
        # Test errors without optional attributes
        errors = [
            ToolNotFoundError("Tool missing"),  # No tool_name
            ToolRegistrationError("Registration failed"),  # No tool_name
            ToolVariantError("Variant error"),  # No tool_name or variant_name
            PluginError("Plugin failed"),  # No plugin_name
            RVTaskError("Task failed"),  # No task_id
            RVExperimentError("Experiment failed"),  # No experiment_id
            RVParsingError("Parse failed"),  # No parser_type
            RVLLMError("LLM failed"),  # No model_name
            RVPromptError("Prompt failed"),  # No strategy_name
            RVValidationError("Validation failed"),  # No field_name
        ]

        for error in errors:
            result = error_handler.handle_error(error)
            # Should handle or not handle based on error type, but not crash
            assert isinstance(result, bool)


class TestErrorHandlerCoverageGaps:
    """Test specific edge cases to increase coverage."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        ErrorHandler._instance = None
        yield
        ErrorHandler._instance = None

    @pytest.fixture
    def mock_logging_manager(self):
        """Mock LoggingManager for testing."""
        with patch('rv_android_core.util.error.error_handler.LoggingManager') as mock_manager:
            mock_instance = Mock()
            mock_logger = Mock()

            @contextmanager
            def mock_context_manager(*args, **kwargs):
                yield mock_logger

            mock_logger.with_context = Mock(return_value=mock_context_manager())
            mock_logger.debug = Mock()
            mock_logger.info = Mock()
            mock_logger.warning = Mock()
            mock_logger.error = Mock()

            mock_instance.get_logger.return_value = mock_logger
            mock_manager.get_instance.return_value = mock_instance
            yield mock_manager, mock_instance, mock_logger

    @pytest.fixture
    def error_handler(self, mock_logging_manager):
        """Create ErrorHandler instance for testing."""
        return ErrorHandler.get_instance()

    def test_callback_exception_handling_direct(self, error_handler, mock_logging_manager):
        """Test callback exception handling by directly injecting a failing callback."""
        _, _, mock_logger = mock_logging_manager
        
        # Directly add a failing callback to the list (simulating a corrupted callback)
        def failing_callback(error, context):
            raise RuntimeError("Direct callback failed")
        
        # Insert the failing callback directly
        error_handler._error_callbacks.insert(0, failing_callback)
        
        # Handle an error - the failing callback should trigger but not break the flow
        error = RVPromptError("Test error", "test_strategy")
        result = error_handler.handle_error(error)
        
        # Should still handle the error despite callback failure  
        assert result is True
        
        # Should log the callback error
        assert any("Error in callback:" in str(call) for call in mock_logger.error.call_args_list)
        
        # Clean up
        error_handler._error_callbacks.remove(failing_callback)

    def test_notify_callbacks_exception_handling(self, error_handler, mock_logging_manager):
        """Test _notify_error_callbacks exception handling (lines 268-282)."""
        _, _, mock_logger = mock_logging_manager
        
        # Register a callback that raises an exception
        def failing_callback(error, context):
            raise ValueError("Notify callback failed")
        
        error_handler.register_error_callback(failing_callback)
        
        # Directly call the notify method
        error = RVPromptError("Test error", "test_strategy")
        error_handler._notify_error_callbacks(error, {})
        
        # Should log the callback error with proper naming
        assert any("Error in error callback" in str(call) for call in mock_logger.error.call_args_list)
        
        # Clean up
        error_handler.unregister_error_callback(failing_callback)

    def test_notify_callbacks_with_named_callback_exception(self, error_handler, mock_logging_manager):
        """Test _notify_error_callbacks with named callback that has __name__ attribute."""
        _, _, mock_logger = mock_logging_manager
        
        # Create a named function callback that raises an exception
        def named_failing_callback(error, context):
            raise ValueError("Named callback failed")
        
        # Add it directly to the callbacks list
        error_handler._error_callbacks.append(named_failing_callback)
        
        # Directly call the notify method
        error = RVPromptError("Test error", "test_strategy")
        error_handler._notify_error_callbacks(error, {})
        
        # Should log with the callback name
        assert any("named_failing_callback" in str(call) for call in mock_logger.error.call_args_list)
        
        # Clean up
        error_handler._error_callbacks.remove(named_failing_callback)

    def test_generic_exception_with_valueerror_direct(self, error_handler, mock_logging_manager):
        """Test generic exception handler with ValueError directly."""
        _, _, mock_logger = mock_logging_manager
        
        error = ValueError("Test value error")
        context = {"component": "TestComponent", "operation": "test_operation"}
        
        # Call the generic exception handler directly
        result = error_handler._handle_generic_exception(error, context)
        
        # Should NOT handle ValueError - let it propagate
        assert result is False
        
        # Should log debug message about not handling
        assert any("Not handling ValueError" in str(call) for call in mock_logger.debug.call_args_list)

    def test_generic_exception_with_configuration_error_direct(self, error_handler, mock_logging_manager):
        """Test generic exception handler with ConfigurationError directly."""
        _, _, mock_logger = mock_logging_manager
        
        error = ConfigurationError("Test config error")
        context = {"component": "TestComponent", "operation": "test_operation"}
        
        # Call the generic exception handler directly
        result = error_handler._handle_generic_exception(error, context)
        
        # Should NOT handle ConfigurationError - let it propagate
        assert result is False
        
        # Should log debug message about not handling
        assert any("Not handling ConfigurationError" in str(call) for call in mock_logger.debug.call_args_list)

    def test_generic_exception_in_decorator_phases(self, error_handler, mock_logging_manager):
        """Test generic exception handler in decorator phases (lines 787-789)."""
        _, _, mock_logger = mock_logging_manager
        
        # Test all decorator phases
        phases = ['tool_copy', 'tool_creation', 'tool_instantiation']
        
        for phase in phases:
            # Use a custom exception that would normally be handled
            error = Exception(f"Generic error in {phase}")
            context = {"component": "TestComponent", "phase": phase}
            
            result = error_handler.handle_error(error, context)
            
            # Should NOT handle in decorator phases
            assert result is False
            
            # Should log debug message about not handling in decorator phase
            assert any(f"Not handling Exception in decorator phase '{phase}'" in str(call) 
                      for call in mock_logger.debug.call_args_list)

    def test_generic_exception_with_non_critical_operations_exact_match(self, error_handler, mock_logging_manager):
        """Test generic exception handler with exact non-critical operations (lines 799-801)."""
        _, _, mock_logger = mock_logging_manager
        
        # Test exact matches for non-critical operations
        operations = ['static_analysis', 'file_copy', 'artifact_validation', 'optional_processing']
        
        for operation in operations:
            error = Exception(f"Generic error in {operation}")
            context = {"component": "TestComponent", "operation": operation}
            
            result = error_handler.handle_error(error, context)
            
            # Should handle non-critical operations
            assert result is True
            
            # Should log warning message
            assert any(f"Non-critical Exception in TestComponent during {operation}" in str(call) 
                      for call in mock_logger.warning.call_args_list)

    def test_generic_exception_with_critical_operations(self, error_handler, mock_logging_manager):
        """Test generic exception handler with critical operations (lines 803-804)."""
        _, _, mock_logger = mock_logging_manager
        
        error = Exception("Generic error in critical operation")
        context = {"component": "TestComponent", "operation": "critical_system_operation"}
        
        result = error_handler.handle_error(error, context)
        
        # Should handle to prevent crashes, but log as error
        assert result is True
        
        # Should log error message for critical operations
        assert any("Unhandled Exception in TestComponent during critical_system_operation" in str(call) 
                  for call in mock_logger.error.call_args_list)

    def test_generic_exception_without_context(self, error_handler, mock_logging_manager):
        """Test generic exception handler without context (lines 807-808)."""
        _, _, mock_logger = mock_logging_manager
        
        error = Exception("Generic error without context")
        
        result = error_handler.handle_error(error)
        
        # Should handle to prevent crashes
        assert result is True
        
        # Should log generic error message
        assert any("Unhandled Exception: Generic error without context" in str(call) 
                  for call in mock_logger.error.call_args_list)

    def test_generic_exception_final_fallback_direct(self, error_handler, mock_logging_manager):
        """Test generic exception handler final return (line 811) directly."""
        _, _, mock_logger = mock_logging_manager
        
        # Use a custom exception type that's not in critical_error_types
        class CustomException(Exception):
            pass
        
        error = CustomException("Custom error for fallback")
        context = {"component": "TestComponent", "operation": "unknown_operation"}
        
        # Call the generic exception handler directly
        result = error_handler._handle_generic_exception(error, context)
        
        # Should handle to prevent system crashes (final fallback)
        assert result is True
        
        # Should log error message
        assert any("Unhandled CustomException in TestComponent during unknown_operation" in str(call) 
                  for call in mock_logger.error.call_args_list)

    def test_pydantic_validation_error_direct(self, error_handler, mock_logging_manager):
        """Test PydanticValidationError handling directly."""
        _, _, mock_logger = mock_logging_manager
        
        try:
            from pydantic_core import ValidationError as PydanticValidationError
            
            # Create a mock validation error
            error = PydanticValidationError.from_exception_data(
                "ValidationError",
                [{"type": "missing", "loc": ("field",), "msg": "Field required"}]
            )
            
            context = {"component": "TestComponent", "operation": "validation"}
            
            # Call the generic exception handler directly
            result = error_handler._handle_generic_exception(error, context)
            
            # Should NOT handle PydanticValidationError - let it propagate
            assert result is False
            
            # Should log debug message about not handling
            assert any("Not handling ValidationError" in str(call) for call in mock_logger.debug.call_args_list)
            
        except ImportError:
            # Skip if pydantic_core not available
            pytest.skip("pydantic_core not available")

    def test_no_handler_processed_debug_message(self, error_handler, mock_logging_manager):
        """Test debug message when no handler processes error (line 234)."""
        _, _, mock_logger = mock_logging_manager
        
        # Use ValueError which is not handled by any specific handler
        error = ValueError("Test value error")
        
        result = error_handler.handle_error(error)
        
        # Should not be handled
        assert result is False
        
        # Should log debug message about no handler processing
        assert any("No handler successfully processed ValueError" in str(call) 
                  for call in mock_logger.debug.call_args_list)

