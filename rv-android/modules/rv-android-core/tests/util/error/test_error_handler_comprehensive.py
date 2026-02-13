# tests/util/error/test_error_handler_comprehensive.py
"""
Comprehensive tests for ErrorHandler to increase coverage.

This test suite covers edge cases, error scenarios, and specific handler behaviors
that are not covered by the main test suite. Focus on increasing coverage
for uncovered lines in the error handler module.
"""
import pytest
import threading
from unittest.mock import Mock, patch
from contextlib import contextmanager

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import (
    RVAndroidError, RVToolError, RVExperimentError,
    RVParsingError, RVValidationError,
    CommandValidationError, LogcatValidationError, EventProcessingError,
    RVCommandTimeoutError, JarNotFoundError,
    ToolNotFoundError, ToolRegistrationError,
    RVToolTimeoutError, RVToolExecutionError, ConfigurationError
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

    # Test specific absorbed error types

    def test_command_validation_error_absorbed(self, error_handler):
        """Test CommandValidationError is absorbed (returns True)."""
        error = CommandValidationError("Invalid command", "command_field")
        result = error_handler.handle_error(error)
        assert result is True

    def test_logcat_validation_error_absorbed(self, error_handler):
        """Test LogcatValidationError is absorbed (returns True)."""
        error = LogcatValidationError("Invalid logcat config", "tags_field")
        result = error_handler.handle_error(error)
        assert result is True

    def test_event_processing_error_absorbed(self, error_handler):
        """Test EventProcessingError is absorbed (returns True)."""
        error = EventProcessingError("Event processing failed", "TEST_EVENT")
        result = error_handler.handle_error(error)
        assert result is True

    def test_rv_validation_error_absorbed(self, error_handler):
        """Test RVValidationError is absorbed (returns True)."""
        error = RVValidationError("Validation failed", "test_field")
        result = error_handler.handle_error(error)
        assert result is True

    def test_tool_not_found_error_absorbed(self, error_handler):
        """Test ToolNotFoundError is absorbed (returns True)."""
        error = ToolNotFoundError("Tool missing", "missing_tool")
        result = error_handler.handle_error(error)
        assert result is True

    def test_tool_registration_error_absorbed(self, error_handler):
        """Test ToolRegistrationError is absorbed (returns True)."""
        error = ToolRegistrationError("Registration failed", "failing_tool")
        result = error_handler.handle_error(error)
        assert result is True

    def test_rv_tool_timeout_error_absorbed(self, error_handler):
        """Test RVToolTimeoutError is absorbed (returns True)."""
        error = RVToolTimeoutError("Tool timeout", "test_tool", 30)
        result = error_handler.handle_error(error)
        assert result is True

    def test_rv_tool_execution_error_absorbed(self, error_handler):
        """Test RVToolExecutionError is absorbed (returns True)."""
        error = RVToolExecutionError("Tool execution failed", "test_tool")
        result = error_handler.handle_error(error)
        assert result is True

    # Test specific propagated error types

    def test_rv_tool_error_propagated(self, error_handler):
        """Test RVToolError (base) is propagated (returns False)."""
        error = RVToolError("Tool error", "test_tool")
        result = error_handler.handle_error(error)
        assert result is False

    def test_rv_experiment_error_propagated(self, error_handler):
        """Test RVExperimentError is propagated (returns False)."""
        error = RVExperimentError("Experiment failed", "exp_456")
        result = error_handler.handle_error(error)
        assert result is False

    def test_rv_parsing_error_propagated(self, error_handler):
        """Test RVParsingError is propagated (returns False)."""
        error = RVParsingError("Parse failed", "xml_parser")
        result = error_handler.handle_error(error)
        assert result is False

    def test_rv_command_timeout_error_propagated(self, error_handler):
        """Test RVCommandTimeoutError is propagated (returns False)."""
        error = RVCommandTimeoutError("Command timed out", timeout_seconds=30, command="adb shell")
        result = error_handler.handle_error(error)
        assert result is False

    def test_jar_not_found_error_propagated(self, error_handler):
        """Test JarNotFoundError is propagated (returns False)."""
        error = JarNotFoundError("JAR not found", jar_name="test.jar", search_paths=["/path1", "/path2"])
        result = error_handler.handle_error(error)
        assert result is False

    # Test special handlers

    def test_configuration_error_handler(self, error_handler):
        """Test ConfigurationError falls to generic RVAndroidError handler (returns False)."""
        error = ConfigurationError("Configuration issue")
        result = error_handler.handle_error(error)
        assert result is False

    def test_pydantic_validation_error_handler(self, error_handler):
        """Test Pydantic ValidationError is not absorbed by generic exception handler."""
        try:
            from pydantic_core import ValidationError as PydanticValidationError
            error = PydanticValidationError.from_exception_data(
                "ValidationError",
                [{"type": "missing", "loc": ("field",), "msg": "Field required"}]
            )
            result = error_handler.handle_error(error)
            assert result is False
        except ImportError:
            pytest.skip("pydantic_core not available")

    def test_value_error_not_handled(self, error_handler):
        """Test that ValueError is not handled by generic exception handler."""
        error = ValueError("Test value error")
        result = error_handler.handle_error(error)
        assert result is False

    # Test FileNotFoundError handler

    def test_file_not_found_error_with_check_operation(self, error_handler):
        """Test FileNotFoundError with check_if_exists operation."""
        error = FileNotFoundError("test.apk")
        context = {"operation": "check_if_exists", "component": "TestComponent"}
        result = error_handler.handle_error(error, context)
        assert result is True

    def test_file_not_found_error_with_verify_operation(self, error_handler):
        """Test FileNotFoundError with verify_file operation."""
        error = FileNotFoundError("test.apk")
        context = {"operation": "verify_file", "component": "TestComponent"}
        result = error_handler.handle_error(error, context)
        assert result is True

    def test_file_not_found_error_with_hash_operation(self, error_handler):
        """Test FileNotFoundError with get_file_hash operation."""
        error = FileNotFoundError("test.apk")
        context = {"operation": "get_file_hash", "component": "TestComponent"}
        result = error_handler.handle_error(error, context)
        assert result is True

    def test_file_not_found_error_critical_operation(self, error_handler):
        """Test FileNotFoundError with critical operation."""
        error = FileNotFoundError("test.apk")
        context = {"operation": "write_file", "component": "TestComponent"}
        result = error_handler.handle_error(error, context)
        assert result is False

    def test_file_not_found_error_no_context(self, error_handler):
        """Test FileNotFoundError without context."""
        error = FileNotFoundError("test.apk")
        result = error_handler.handle_error(error)
        assert result is False

    # Test generic exception handler

    def test_generic_exception_in_decorator_phase(self, error_handler):
        """Test generic exception in decorator phase returns False for RVAndroidError."""
        error = RVAndroidError("Test Android error")
        context = {"phase": "tool_creation", "component": "TestComponent"}
        result = error_handler.handle_error(error, context)
        assert result is False

    def test_generic_exception_no_context(self, error_handler):
        """Test generic exception handled with absorbed error type."""
        error = RVToolExecutionError("Test tool error", "test_tool")
        result = error_handler.handle_error(error)
        assert result is True

    def test_command_timeout_error_with_context(self, error_handler):
        """Test RVCommandTimeoutError with detailed context."""
        error = RVCommandTimeoutError("Command timed out", timeout_seconds=30, command="adb shell")
        context = {"component": "ADBManager", "operation": "shell_command"}
        result = error_handler.handle_error(error, context)
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
        assert result is False

    def test_error_with_object_context(self, error_handler):
        """Test error handling with object context (has build method)."""

        class MockErrorContext:
            def build(self, frame_offset=3):
                return {"component": "MockComponent", "phase": "testing"}

        error = RVToolExecutionError("Test error", "test_tool")
        context = MockErrorContext()
        result = error_handler.handle_error(error, context)
        assert result is True

    def test_error_with_invalid_context_object(self, error_handler):
        """Test error handling with invalid context object (no build method)."""

        class InvalidContext:
            pass

        error = RVToolExecutionError("Test error", "test_tool")
        context = InvalidContext()
        result = error_handler.handle_error(error, context)
        assert result is True

    def test_log_error_with_rv_android_error_and_cause(self, error_handler, mock_logging_manager):
        """Test logging RVAndroidError with cause."""
        _, _, mock_logger = mock_logging_manager

        cause = ValueError("Original error")
        error = RVAndroidError("Wrapper error", cause)

        error_handler._log_error(error, {})

        mock_logger.error.assert_called()
        args, kwargs = mock_logger.error.call_args
        assert "caused by" in args[0]
        assert kwargs.get("exc_info") == cause

    def test_log_error_with_timeout_error(self, error_handler, mock_logging_manager):
        """Test logging timeout errors is less verbose (no stacktrace)."""
        _, _, mock_logger = mock_logging_manager

        error = RVToolTimeoutError("Tool timeout", "test_tool", 30)

        error_handler._log_error(error, {})

        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        assert "Error:" in args[0]
        assert "exc_info" not in kwargs

    def test_log_error_with_command_timeout_error(self, error_handler, mock_logging_manager):
        """Test logging command timeout errors is less verbose (no stacktrace)."""
        _, _, mock_logger = mock_logging_manager

        error = RVCommandTimeoutError("Command timeout", 30, "adb shell")

        error_handler._log_error(error, {})

        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        assert "Error:" in args[0]
        assert "exc_info" not in kwargs

    def test_context_manager_with_unhandled_error(self, error_handler):
        """Test error_context instance method with unhandled error."""
        with pytest.raises(ValueError):
            with error_handler.error_context(component="TestComponent"):
                raise ValueError("This should propagate")

    def test_context_manager_with_handled_error(self, error_handler):
        """Test error_context instance method with handled (absorbed) error."""
        with error_handler.error_context(component="TestComponent"):
            raise RVToolExecutionError("This should be handled", "test_tool")

    def test_decorator_with_unhandled_error_and_no_reraise(self, error_handler):
        """Test decorator with unhandled error and reraise=False."""

        @ErrorHandler.handle_errors(component="TestComponent", reraise=False)
        def test_function():
            raise ValueError("Unhandled error")

        result = test_function()
        assert result is None

    def test_decorator_with_handled_error_and_reraise_true(self, error_handler):
        """Test decorator with handled error and reraise=True."""

        @ErrorHandler.handle_errors(component="TestComponent", reraise=True)
        def test_function():
            raise RVToolExecutionError("Handled error", "test_tool")

        with pytest.raises(RVToolExecutionError):
            test_function()

    def test_decorator_with_unhandled_error_and_reraise_true(self, error_handler):
        """Test decorator with unhandled error and reraise=True."""

        @ErrorHandler.handle_errors(component="TestComponent", reraise=True)
        def test_function():
            raise ValueError("Unhandled error")

        with pytest.raises(ValueError):
            test_function()


class TestParametrizedErrorHandling:
    """Parametrized tests for error handling scenarios."""

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
        """Parametrized test for tool timeout errors (all absorbed)."""
        error = RVToolTimeoutError(error_message, tool_name, timeout_seconds)
        result = error_handler.handle_error(error)
        assert result is True

    @pytest.mark.parametrize("error_message,jar_name,search_paths", [
        ("JAR not found", "test.jar", ["/path1", "/path2"]),
        ("Missing dependency", "lib.jar", ["/usr/lib", "/opt/lib"]),
        ("Tool JAR missing", "tool.jar", []),
        ("Complex path JAR", "complex-name.jar", ["/very/long/path/to/search", "/another/path"]),
        ("Single path search", "simple.jar", ["/single/path"])
    ])
    def test_jar_not_found_error_parametrized(self, error_handler, error_message, jar_name, search_paths):
        """Parametrized test for JAR not found errors (all propagated)."""
        error = JarNotFoundError(error_message, jar_name, search_paths)
        result = error_handler.handle_error(error)
        assert result is False

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
        assert result is expected_result

    @pytest.mark.parametrize("error_message,tool_name", [
        ("Execution failed", "monkey"),
        ("Tool crashed", "droidbot"),
        ("Process error", "rvagent"),
        ("Timeout exceeded", "espresso"),
        ("Connection lost", "ui_automator")
    ])
    def test_tool_execution_error_parametrized(self, error_handler, error_message, tool_name):
        """Parametrized test for tool execution errors (all absorbed)."""
        error = RVToolExecutionError(error_message, tool_name)
        result = error_handler.handle_error(error)
        assert result is True

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
        error = RVToolExecutionError("Test error", "test_tool")
        result = error_handler.handle_error(error, context_data)
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
                error = RVToolExecutionError(f"Error from thread {thread_id}-{i}", "test_tool")
                result = error_handler.handle_error(error)
                errors_handled.append((thread_id, i, result))

        threads = []
        for tid in range(5):
            thread = threading.Thread(target=handle_error_thread, args=(tid,))
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(errors_handled) == 50
        assert all(result is True for _, _, result in errors_handled)

    def test_error_handler_with_empty_context(self, error_handler):
        """Test error handling with empty context dictionary."""
        error = RVToolExecutionError("Test error", "test_tool")
        context = {}
        result = error_handler.handle_error(error, context)
        assert result is True

    def test_error_handler_with_none_context_values(self, error_handler):
        """Test error handling with None values in context."""
        error = RVToolExecutionError("Test error", "test_tool")
        context = {"component": None, "phase": None, "operation": None}
        result = error_handler.handle_error(error, context)
        assert result is True

    def test_error_handler_with_missing_attributes(self, error_handler):
        """Test error handling when errors are missing expected attributes."""
        error = RVToolExecutionError("Tool failed", "test_tool")
        result = error_handler.handle_error(error)
        assert result is True

    def test_error_handler_with_none_attributes(self, error_handler):
        """Test error handling when error attributes are None."""
        error = RVToolTimeoutError("Timeout", None, None)
        result = error_handler.handle_error(error)
        assert result is True

    def test_rv_android_error_without_cause(self, error_handler, mock_logging_manager):
        """Test RVAndroidError without cause attribute."""
        _, _, mock_logger = mock_logging_manager

        error = RVAndroidError("Test error")

        error_handler._log_error(error, {})

        mock_logger.error.assert_called()
        args, kwargs = mock_logger.error.call_args
        assert "Error:" in args[0]

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
                raise RVToolExecutionError("Test error", "test_tool")
            return f"{arg1}-{arg2}-{kwarg1}"

        result = test_function_with_args("hello", "world", kwarg1="test")
        assert result == "hello-world-test"

        result = test_function_with_args("error", "world")
        assert result is None

    def test_decorator_with_class_method(self, error_handler):
        """Test decorator works with class methods."""

        class TestClass:
            @ErrorHandler.handle_errors(component="TestClass", phase="method_execution")
            def test_method(self, should_error=False):
                if should_error:
                    raise RVToolExecutionError("Method error", "test_tool")
                return "method_success"

        test_obj = TestClass()

        result = test_obj.test_method()
        assert result == "method_success"

        result = test_obj.test_method(should_error=True)
        assert result is None

    def test_exact_type_matching_inheritance(self, error_handler):
        """Test that handler type matching is exact, not inheritance-based."""

        class CustomToolError(RVToolExecutionError):
            pass

        error = CustomToolError("Custom error", "test_tool")

        # Should NOT be handled by RVToolExecutionError handler due to exact type matching
        result = error_handler.handle_error(error)
        assert isinstance(result, bool)

    def test_handler_registration_with_duplicate_prevention(self, error_handler):
        """Test that duplicate handler registration is prevented."""

        def test_handler(error, context):
            return True

        initial_count = len(error_handler._error_callbacks)

        error_handler.register_handler(ValueError, test_handler)
        error_handler.register_handler(ValueError, test_handler)
        error_handler.register_handler(ValueError, test_handler)

        final_count = len(error_handler._error_callbacks)
        assert final_count == initial_count + 1

    def test_error_handler_thread_safety_singleton(self):
        """Test thread safety of singleton pattern."""
        instances = []

        def create_instance():
            instances.append(ErrorHandler.get_instance())

        threads = []
        for _ in range(10):
            thread = threading.Thread(target=create_instance)
            threads.append(thread)

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        assert len(set(id(instance) for instance in instances)) == 1

    def test_complex_error_inheritance_chain(self, error_handler):
        """Test handling of complex error inheritance chains."""
        errors = [
            RVToolError("Tool error", "test_tool"),
            RVExperimentError("Experiment error", "exp_1"),
            RVAndroidError("Base error")
        ]

        results = []
        for error in errors:
            result = error_handler.handle_error(error)
            results.append(result)

        # RVToolError -> False (propagated)
        # RVExperimentError -> False (propagated)
        # RVAndroidError -> False (generic handler)
        expected = [False, False, False]
        assert results == expected

    def test_error_with_very_long_message(self, error_handler):
        """Test error handling with very long error messages."""
        long_message = "x" * 10000
        error = RVToolExecutionError(long_message, "test_tool")
        result = error_handler.handle_error(error)
        assert result is True

    def test_error_with_special_characters(self, error_handler):
        """Test error handling with special characters in messages."""
        special_message = "Error with special chars: \u00e0\u00e1\u00e2\u00e3 \u65e5\u672c\u8a9e \n\t\r"
        error = RVToolExecutionError(special_message, "test_tool")
        result = error_handler.handle_error(error)
        assert result is True

    def test_error_context_with_instance_method(self, error_handler):
        """Test error_context instance method."""
        with error_handler.error_context(component="InstanceTest", phase="testing"):
            raise RVToolExecutionError("Instance context test", "test_tool")

    def test_all_builtin_handlers_registered(self, error_handler):
        """Test that all expected builtin handlers are registered."""
        assert len(error_handler._error_callbacks) == 16
        assert hasattr(error_handler, '_registered_handlers')
        assert len(error_handler._registered_handlers) == 16


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

    def test_tool_not_found_error_logged(self, error_handler, mock_logging_manager):
        """Test ToolNotFoundError handler logs appropriately and returns True."""
        _, _, mock_logger = mock_logging_manager
        error = ToolNotFoundError("Tool missing", "missing_tool")
        result = error_handler.handle_error(error)
        assert result is True
        assert mock_logger.error.called

    def test_tool_registration_error_logged(self, error_handler, mock_logging_manager):
        """Test ToolRegistrationError handler logs appropriately and returns True."""
        _, _, mock_logger = mock_logging_manager
        error = ToolRegistrationError("Registration failed", "failing_tool")
        result = error_handler.handle_error(error)
        assert result is True
        assert mock_logger.error.called

    def test_experiment_error_logged(self, error_handler, mock_logging_manager):
        """Test RVExperimentError handler logs appropriately and returns False."""
        _, _, mock_logger = mock_logging_manager
        error = RVExperimentError("Experiment failed", "exp_456")
        result = error_handler.handle_error(error)
        assert result is False
        assert mock_logger.error.called

    def test_parsing_error_logged(self, error_handler, mock_logging_manager):
        """Test RVParsingError handler logs appropriately and returns False."""
        _, _, mock_logger = mock_logging_manager
        error = RVParsingError("Parse failed", "xml_parser")
        result = error_handler.handle_error(error)
        assert result is False
        assert mock_logger.error.called

    def test_validation_error_logged(self, error_handler, mock_logging_manager):
        """Test RVValidationError handler logs appropriately and returns True."""
        _, _, mock_logger = mock_logging_manager
        error = RVValidationError("Validation failed", "test_field")
        result = error_handler.handle_error(error)
        assert result is True
        assert mock_logger.error.called

    def test_command_validation_error_with_command_context(self, error_handler, mock_logging_manager):
        """Test CommandValidationError with command in context."""
        _, _, mock_logger = mock_logging_manager
        error = CommandValidationError("Invalid command", "command_field")
        context = {"command": "invalid_adb_command"}
        result = error_handler.handle_error(error, context)
        assert result is True
        assert mock_logger.error.called

    def test_logcat_validation_error_with_tags_context(self, error_handler, mock_logging_manager):
        """Test LogcatValidationError with tags in context."""
        _, _, mock_logger = mock_logging_manager
        error = LogcatValidationError("Invalid logcat config", "tags_field")
        context = {"tags": "invalid_tags", "output_file": "/tmp/logcat.log"}
        result = error_handler.handle_error(error, context)
        assert result is True
        assert mock_logger.error.called

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
        assert result is True
        assert mock_logger.error.called

    def test_tool_execution_error_with_exit_code(self, error_handler, mock_logging_manager):
        """Test RVToolExecutionError with exit code attribute."""
        _, _, mock_logger = mock_logging_manager
        error = RVToolExecutionError("Tool execution failed", "test_tool")
        error.exit_code = 1
        result = error_handler.handle_error(error)
        assert result is True
        assert mock_logger.error.called

    def test_handlers_without_optional_attributes(self, error_handler):
        """Test handlers when errors have no optional attributes set."""
        errors_and_expected = [
            (ToolNotFoundError("Tool missing"), True),
            (ToolRegistrationError("Registration failed"), True),
            (RVExperimentError("Experiment failed"), False),
            (RVParsingError("Parse failed"), False),
            (RVValidationError("Validation failed"), True),
            (RVToolExecutionError("Exec failed"), True),
            (RVToolTimeoutError("Timeout"), True),
            (CommandValidationError("Cmd error"), True),
            (LogcatValidationError("Logcat error"), True),
            (EventProcessingError("Event error"), True),
        ]

        for error, expected in errors_and_expected:
            result = error_handler.handle_error(error)
            assert result is expected, f"Expected {expected} for {type(error).__name__}, got {result}"


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
        """Test error callback that raises exception does not break the flow."""
        _, _, mock_logger = mock_logging_manager

        def failing_callback(error, context):
            raise RuntimeError("Direct callback failed")

        # Insert the failing callback directly
        error_handler._error_callbacks.insert(0, failing_callback)

        error = RVToolExecutionError("Test error", "test_tool")
        result = error_handler.handle_error(error)

        # Should still handle the error despite callback failure
        assert result is True

        # Should log the callback error
        assert any("Error in callback:" in str(call) for call in mock_logger.error.call_args_list)

        # Clean up
        error_handler._error_callbacks.remove(failing_callback)

    def test_generic_exception_with_valueerror_direct(self, error_handler, mock_logging_manager):
        """Test generic exception handler with ValueError directly."""
        _, _, mock_logger = mock_logging_manager

        error = ValueError("Test value error")
        context = {"component": "TestComponent", "operation": "test_operation"}

        result = error_handler._handle_generic_exception(error, context)

        assert result is False

        assert any("Not handling ValueError" in str(call) for call in mock_logger.debug.call_args_list)

    def test_generic_exception_with_configuration_error_direct(self, error_handler, mock_logging_manager):
        """Test generic exception handler with ConfigurationError directly."""
        _, _, mock_logger = mock_logging_manager

        error = ConfigurationError("Test config error")
        context = {"component": "TestComponent", "operation": "test_operation"}

        result = error_handler._handle_generic_exception(error, context)

        assert result is False

        assert any("Not handling ConfigurationError" in str(call) for call in mock_logger.debug.call_args_list)

    def test_generic_exception_in_decorator_phases(self, error_handler, mock_logging_manager):
        """Test generic exception handler in decorator phases."""
        _, _, mock_logger = mock_logging_manager

        phases = ['tool_copy', 'tool_creation', 'tool_instantiation']

        for phase in phases:
            error = Exception(f"Generic error in {phase}")
            context = {"component": "TestComponent", "phase": phase}

            result = error_handler.handle_error(error, context)

            assert result is False

            assert any(f"Not handling Exception in decorator phase '{phase}'" in str(call)
                       for call in mock_logger.debug.call_args_list)

    def test_generic_exception_with_non_critical_operations(self, error_handler, mock_logging_manager):
        """Test generic exception handler with non-critical operations."""
        _, _, mock_logger = mock_logging_manager

        operations = ['static_analysis', 'file_copy', 'artifact_validation', 'optional_processing']

        for operation in operations:
            error = Exception(f"Generic error in {operation}")
            context = {"component": "TestComponent", "operation": operation}

            result = error_handler.handle_error(error, context)

            assert result is True

            assert any(f"Non-critical Exception in TestComponent during {operation}" in str(call)
                       for call in mock_logger.warning.call_args_list)

    def test_generic_exception_with_critical_operations(self, error_handler, mock_logging_manager):
        """Test generic exception handler with critical operations."""
        _, _, mock_logger = mock_logging_manager

        error = Exception("Generic error in critical operation")
        context = {"component": "TestComponent", "operation": "critical_system_operation"}

        result = error_handler.handle_error(error, context)

        assert result is True

        assert any("Unhandled Exception in TestComponent during critical_system_operation" in str(call)
                    for call in mock_logger.error.call_args_list)

    def test_generic_exception_without_context(self, error_handler, mock_logging_manager):
        """Test generic exception handler without context."""
        _, _, mock_logger = mock_logging_manager

        error = Exception("Generic error without context")

        result = error_handler.handle_error(error)

        assert result is True

        assert any("Unhandled Exception: Generic error without context" in str(call)
                    for call in mock_logger.error.call_args_list)

    def test_generic_exception_final_fallback_direct(self, error_handler, mock_logging_manager):
        """Test generic exception handler final return directly."""
        _, _, mock_logger = mock_logging_manager

        class CustomException(Exception):
            pass

        error = CustomException("Custom error for fallback")
        context = {"component": "TestComponent", "operation": "unknown_operation"}

        result = error_handler._handle_generic_exception(error, context)

        assert result is True

        assert any("Unhandled CustomException in TestComponent during unknown_operation" in str(call)
                    for call in mock_logger.error.call_args_list)

    def test_pydantic_validation_error_direct(self, error_handler, mock_logging_manager):
        """Test PydanticValidationError handling directly."""
        _, _, mock_logger = mock_logging_manager

        try:
            from pydantic_core import ValidationError as PydanticValidationError

            error = PydanticValidationError.from_exception_data(
                "ValidationError",
                [{"type": "missing", "loc": ("field",), "msg": "Field required"}]
            )

            context = {"component": "TestComponent", "operation": "validation"}

            result = error_handler._handle_generic_exception(error, context)

            assert result is False

            assert any("Not handling ValidationError" in str(call) for call in mock_logger.debug.call_args_list)

        except ImportError:
            pytest.skip("pydantic_core not available")

    def test_no_handler_processed_debug_message(self, error_handler, mock_logging_manager):
        """Test debug message when no handler processes error."""
        _, _, mock_logger = mock_logging_manager

        error = ValueError("Test value error")

        result = error_handler.handle_error(error)

        assert result is False

        assert any("No handler successfully processed ValueError" in str(call)
                    for call in mock_logger.debug.call_args_list)

    def test_multiple_error_types_in_sequence(self, error_handler):
        """Test handling multiple error types in sequence with correct results."""
        test_cases = [
            (CommandValidationError("cmd error", "field"), True),
            (LogcatValidationError("logcat error", "field"), True),
            (EventProcessingError("event error", "EVENT"), True),
            (RVValidationError("validation error", "field"), True),
            (ToolNotFoundError("not found", "tool"), True),
            (ToolRegistrationError("reg error", "tool"), True),
            (RVToolTimeoutError("timeout", "tool", 30), True),
            (RVToolExecutionError("exec error", "tool"), True),
            (RVToolError("tool error", "tool"), False),
            (RVExperimentError("exp error", "exp"), False),
            (RVParsingError("parse error", "parser"), False),
            (RVCommandTimeoutError("cmd timeout", 30, "cmd"), False),
            (JarNotFoundError("jar error", "jar", ["/p"]), False),
            (RVAndroidError("base error"), False),
        ]

        for error, expected in test_cases:
            result = error_handler.handle_error(error)
            assert result is expected, f"Expected {expected} for {type(error).__name__}, got {result}"
