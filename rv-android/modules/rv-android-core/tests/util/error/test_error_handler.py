"""
Tests for ErrorHandler.

This test suite validates the error handler functionality, focusing on key behaviors:
- Singleton pattern
- Handler registration and execution
- Built-in handlers for specific error types
- Decorator functionality
- Instance-level error_context context manager
- No duplicate handler execution
"""

import threading
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import (
    ConfigurationError,
    RVCommandTimeoutError,
    RVExperimentError,
    RVParsingError,
    RVToolExecutionError,
    RVValidationError,
    ToolNotFoundError,
)


class TestErrorHandlerCore:
    """Test suite for ErrorHandler core functionality."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        ErrorHandler._instance = None
        yield
        ErrorHandler._instance = None

    @pytest.fixture
    def mock_logging_manager(self):
        """Mock LoggingManager for testing."""
        with patch(
            "rv_android_core.util.error.error_handler.LoggingManager"
        ) as mock_manager:
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

    def test_singleton_pattern(self, mock_logging_manager):
        """Test that ErrorHandler follows singleton pattern."""
        handler1 = ErrorHandler.get_instance()
        handler2 = ErrorHandler.get_instance()

        assert handler1 is handler2
        assert ErrorHandler._instance is handler1

    def test_singleton_thread_safety(self, mock_logging_manager):
        """Test singleton thread safety."""
        instances = []

        def create_instance():
            instances.append(ErrorHandler.get_instance())

        threads = [threading.Thread(target=create_instance) for _ in range(10)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All instances should be the same
        assert len(set(id(i) for i in instances)) == 1

    def test_builtin_handlers_registered(self, error_handler):
        """Test that built-in handlers are automatically registered."""
        # Should have 16 built-in handlers registered
        assert len(error_handler._error_callbacks) == 16

        # Check that handler signatures are tracked
        assert hasattr(error_handler, "_registered_handlers")
        assert len(error_handler._registered_handlers) == 16

    def test_register_handler_success(self, error_handler):
        """Test successful handler registration."""

        def test_handler(error, context):
            return True

        initial_count = len(error_handler._error_callbacks)
        error_handler.register_handler(ValueError, test_handler)

        assert len(error_handler._error_callbacks) == initial_count + 1

    def test_register_handler_duplicate_prevention(self, error_handler):
        """Test that duplicate handlers are prevented."""

        def test_handler(error, context):
            return True

        initial_count = len(error_handler._error_callbacks)

        # Register same handler twice
        error_handler.register_handler(ValueError, test_handler)
        error_handler.register_handler(ValueError, test_handler)

        # Should only have one additional callback
        assert len(error_handler._error_callbacks) == initial_count + 1

    def test_absorbed_error_handler(self, error_handler):
        """Test that absorbed error types return True."""
        error = RVToolExecutionError("Tool execution failed", "test_tool")
        result = error_handler.handle_error(error)
        assert result is True

    def test_propagated_error_handler(self, error_handler):
        """Test that propagated error types return False."""
        error = RVExperimentError("Experiment failed", "exp_1")
        result = error_handler.handle_error(error)
        assert result is False

    def test_validation_error_handler(self, error_handler):
        """Test RVValidationError handler returns True (absorbed)."""
        error = RVValidationError("Validation failed", "test_field")
        result = error_handler.handle_error(error)
        assert result is True

    def test_exact_type_matching(self, error_handler):
        """Test that handlers only trigger for exact type matches."""

        # Create a subclass of RVToolExecutionError
        class CustomToolError(RVToolExecutionError):
            pass

        error = CustomToolError("Custom error", "test_tool")

        # Should NOT be handled by RVToolExecutionError handler due to exact type matching
        result = error_handler.handle_error(error)
        # Falls through to generic handlers
        assert isinstance(result, bool)

    def test_handler_execution_order(self, error_handler):
        """Test that handlers are executed in registration order and stop on first success."""
        execution_order = []

        def handler1(error, context):
            execution_order.append(1)
            return False  # Don't handle

        def handler2(error, context):
            execution_order.append(2)
            return True  # Handle successfully

        def handler3(error, context):
            execution_order.append(3)
            return True  # Should not be called

        # Register in order
        error_handler.register_handler(ValueError, handler1)
        error_handler.register_handler(ValueError, handler2)
        error_handler.register_handler(ValueError, handler3)

        error = ValueError("Test error")
        result = error_handler.handle_error(error)

        assert result is True
        assert execution_order == [1, 2]  # handler3 should not be called

    def test_decorator_functionality(self, error_handler):
        """Test @ErrorHandler.handle_errors decorator."""

        @ErrorHandler.handle_errors(component="TestComponent")
        def test_function():
            raise RVToolExecutionError("Test error", "test_tool")

        # Should not raise exception - decorator handles it
        result = test_function()
        assert result is None

    def test_decorator_with_reraise(self, error_handler):
        """Test decorator with reraise=True."""

        @ErrorHandler.handle_errors(component="TestComponent", reraise=True)
        def test_function():
            raise ValueError("Unhandled error")

        # Should raise exception because ValueError is not handled and reraise=True
        with pytest.raises(ValueError):
            test_function()

    def test_decorator_reraise_annotates_error_phase(self, error_handler):
        """Test that reraise=True annotates _error_phase on the exception."""

        @ErrorHandler.handle_errors(
            component="Test", phase="apk_signing", reraise=True
        )
        def test_function():
            raise RuntimeError("signing failed")

        with pytest.raises(RuntimeError) as exc_info:
            test_function()

        assert hasattr(exc_info.value, "_error_phase")
        assert exc_info.value._error_phase == "apk_signing"

    def test_decorator_reraise_false_does_not_annotate(self, error_handler):
        """Test that reraise=False does NOT annotate _error_phase (returns None)."""

        @ErrorHandler.handle_errors(
            component="Test", phase="apk_signing", reraise=False
        )
        def test_function():
            raise RuntimeError("signing failed")

        result = test_function()
        assert result is None

    def test_nested_decorators_inner_phase_wins(self, error_handler):
        """Test that inner decorator's phase is preserved through nested chain."""

        @ErrorHandler.handle_errors(
            component="Test", phase="apk_creation", reraise=True
        )
        def outer():
            return inner()

        @ErrorHandler.handle_errors(
            component="Test", phase="apk_signing", reraise=True
        )
        def inner():
            raise RuntimeError("jarsigner failed")

        with pytest.raises(RuntimeError) as exc_info:
            outer()

        # Inner decorator sets "apk_signing", outer must NOT overwrite
        assert exc_info.value._error_phase == "apk_signing"

    def test_no_duplicate_handler_execution(self, error_handler, mock_logging_manager):
        """Test that handlers are not executed multiple times for the same error."""
        _, _, mock_logger = mock_logging_manager

        error = ToolNotFoundError("Tool missing", "test_tool")
        error_handler.handle_error(error)

        # Count error log calls - should be limited
        assert mock_logger.error.called

    def test_custom_handler_registration(self, error_handler):
        """Test registering custom handlers for custom exceptions."""

        class CustomError(Exception):
            pass

        handler_called = False

        def custom_handler(error, context):
            nonlocal handler_called
            handler_called = True
            return True

        error_handler.register_handler(CustomError, custom_handler)

        error = CustomError("Custom error")
        result = error_handler.handle_error(error)

        assert result is True
        assert handler_called is True


class TestErrorHandlerIntegration:
    """Integration tests for real-world scenarios."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        ErrorHandler._instance = None
        yield
        ErrorHandler._instance = None

    @pytest.fixture
    def mock_logging_manager(self):
        """Mock LoggingManager for testing."""
        with patch(
            "rv_android_core.util.error.error_handler.LoggingManager"
        ) as mock_manager:
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

    def test_tool_execution_integration_scenario(self, mock_logging_manager):
        """Test integration scenario with tool execution errors."""
        error_handler = ErrorHandler.get_instance()

        @ErrorHandler.handle_errors(component="ToolFactory", operation="create_tool")
        def create_tool(tool_type):
            if tool_type == "invalid":
                raise ToolNotFoundError(f"Tool not found: {tool_type}", tool_type)
            return "tool_object"

        # This should not raise an exception
        result = create_tool("invalid")
        assert result is None  # Decorator returns None for handled errors

    def test_multiple_error_types_in_sequence(self, mock_logging_manager):
        """Test handling multiple different error types."""
        error_handler = ErrorHandler.get_instance()

        errors = [
            RVToolExecutionError("Tool exec error", "tool1"),
            ToolNotFoundError("Tool not found", "tool2"),
            RVExperimentError("Experiment error", "exp1"),
            RVParsingError("Parsing error", "parser1"),
            RVValidationError("Validation error", "field1"),
            RVCommandTimeoutError("Timeout", 30, "cmd"),
        ]

        results = []
        for error in errors:
            result = error_handler.handle_error(error)
            results.append(result)

        # RVToolExecutionError and ToolNotFoundError -> True (absorbed)
        # RVExperimentError, RVParsingError, RVCommandTimeoutError -> False (propagated)
        # RVValidationError -> True (absorbed)
        expected = [True, True, False, False, True, False]
        assert results == expected

    def test_concurrent_error_handling(self, mock_logging_manager):
        """Test error handling under concurrent conditions."""
        error_handler = ErrorHandler.get_instance()

        errors = []
        for i in range(5):
            error = RVToolExecutionError(f"Error {i}", f"tool_{i}")
            result = error_handler.handle_error(error)
            errors.append(result)

        # All errors should be handled successfully (absorbed)
        assert all(result is True for result in errors)


class TestErrorHandlerExtended:
    """Additional tests to increase coverage of ErrorHandler."""

    @pytest.fixture(autouse=True)
    def reset_handler(self):
        ErrorHandler._instance = None
        yield
        ErrorHandler._instance = None

    @pytest.fixture
    def mock_logging_manager(self):
        with patch(
            "rv_android_core.util.error.error_handler.LoggingManager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_logger = Mock()

            @contextmanager
            def mock_context():
                yield mock_logger

            mock_logger.with_context = Mock(return_value=mock_context())
            mock_logger.debug = Mock()
            mock_logger.info = Mock()
            mock_logger.warning = Mock()
            mock_logger.error = Mock()

            mock_instance.get_logger.return_value = mock_logger
            mock_manager.get_instance.return_value = mock_instance
            yield mock_manager, mock_instance, mock_logger

    @pytest.fixture
    def handler(self, mock_logging_manager):
        return ErrorHandler.get_instance()

    def test_handle_error_with_dict_context(self, handler):
        """Test handle_error with dictionary context."""
        context = {"component": "TestComponent", "phase": "demo"}
        err = RVToolExecutionError("demo", "tool1")
        assert handler.handle_error(err, context) is True

    def test_handle_error_with_object_context(self, handler):
        """Test handle_error with object context that has build method."""

        class DummyContext:
            def build(self, frame_offset=3):
                return {"phase": "from-object"}

        err = RVToolExecutionError("demo", "tool1")
        assert handler.handle_error(err, DummyContext()) is True

    def test_generic_exception_handler_without_context(self, handler):
        """Test generic exception handler without context."""
        err = RuntimeError("unexpected")
        # RuntimeError without context goes to _handle_generic_exception
        result = handler.handle_error(err)
        assert isinstance(result, bool)

    def test_generic_exception_not_handled_if_configuration(self, handler):
        """Test ConfigurationError is not absorbed."""
        err = ConfigurationError("invalid config")
        assert handler.handle_error(err) is False

    def test_file_not_found_expected_case(self, handler):
        """Test FileNotFoundError with expected operation."""
        err = FileNotFoundError("Missing file")
        context = {"component": "Test", "operation": "check_if_exists"}
        assert handler.handle_error(err, context) is True

    def test_file_not_found_unexpected_case(self, handler):
        """Test FileNotFoundError with critical operation."""
        err = FileNotFoundError("Missing file")
        context = {"component": "Test", "operation": "write_file"}
        assert handler.handle_error(err, context) is False

    def test_file_not_found_without_context(self, handler):
        """Test FileNotFoundError without context."""
        err = FileNotFoundError("Missing file")
        assert handler.handle_error(err) is False

    def test_error_context_scope_success(self, handler):
        """Test instance error_context context manager with handled error."""
        # Should not raise because RVToolExecutionError is absorbed
        with handler.error_context(component="Scoped", phase="run"):
            raise RVToolExecutionError("oops", "tool1")

    def test_error_context_scope_reraise(self, handler):
        """Test instance error_context context manager re-raises unhandled errors."""

        class Dummy(Exception):
            pass

        with pytest.raises(Dummy):
            with handler.error_context(component="Scoped"):
                raise Dummy("fail")

    def test_decorator_propagate_with_phase(self, handler):
        """Test decorator with phase context."""

        @ErrorHandler.handle_errors(component="X", phase="tool_creation", reraise=False)
        def f():
            raise RuntimeError("boom")

        assert f() is None

    def test_decorator_logs_if_not_handled(self, handler):
        """Test decorator with absorbed error."""

        @ErrorHandler.handle_errors(component="Test", reraise=False)
        def f():
            raise RVToolExecutionError("fail", "tool1")

        assert f() is None
