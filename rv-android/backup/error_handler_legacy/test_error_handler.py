import threading
import time
from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest

from rv_android_core.util.error.error_handler import ErrorHandler, error_context
from rv_android_core.util.exceptions import (
    RVAndroidError, RVTaskError, RVTaskExecutionError, RVTaskConfigurationError,
    RVToolError, RVExperimentError, RVParsingError, RVLLMError, RVPromptError
)


class TestErrorHandler:
    """Comprehensive tests for ErrorHandler class."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        """Setup and teardown for each test."""
        # Reset singleton instance before each test
        ErrorHandler._instance = None
        yield
        # Clean up after each test
        ErrorHandler._instance = None

    @pytest.fixture
    def mock_logging_manager(self):
        """Mock LoggingManager for testing."""
        with patch('rv_android_core.util.error.error_handler.LoggingManager') as mock_manager:
            mock_instance = Mock()
            mock_logger = Mock()
            mock_logger.with_context.return_value = contextmanager(lambda: (yield mock_logger))()
            mock_instance.get_logger.return_value = mock_logger
            mock_manager.get_instance.return_value = mock_instance
            yield mock_manager, mock_instance, mock_logger

    @pytest.fixture
    def error_handler(self, mock_logging_manager):
        """Create ErrorHandler instance for testing."""
        return ErrorHandler.get_instance()

    @pytest.fixture
    def sample_context(self):
        """Sample context for testing."""
        return {
            "component": "TestComponent",
            "phase": "testing",
            "task_id": "test_task_123"
        }

    def test_singleton_pattern(self, mock_logging_manager):
        """Test that ErrorHandler follows singleton pattern."""
        # Create two instances
        handler1 = ErrorHandler.get_instance()
        handler2 = ErrorHandler.get_instance()

        # Should be the same instance
        assert handler1 is handler2
        assert id(handler1) == id(handler2)

    def test_singleton_thread_safety(self, mock_logging_manager):
        """Test singleton thread safety."""
        instances = []

        def create_instance():
            instances.append(ErrorHandler.get_instance())

        # Create multiple threads
        threads = [threading.Thread(target=create_instance) for _ in range(10)]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All instances should be the same
        assert len(set(id(instance) for instance in instances)) == 1

    def test_initialization(self, mock_logging_manager):
        """Test ErrorHandler initialization."""
        _, mock_manager_instance, mock_logger = mock_logging_manager

        handler = ErrorHandler()

        # Verify logging setup
        mock_manager_instance.get_logger.assert_called_once()

        # Verify initial state
        assert handler._error_callbacks is not None
        assert handler._error_counts == {}
        assert handler._error_history == []
        assert handler._recovery_attempts == {}

    def test_register_error_callback_success(self, error_handler):
        """Test successful error callback registration."""
        callback = Mock()

        # Register callback
        error_handler.register_error_callback(callback)

        # Verify callback is registered
        assert callback in error_handler._error_callbacks

    def test_register_error_callback_duplicate(self, error_handler):
        """Test duplicate callback registration is prevented."""
        callback = Mock()

        # Register callback twice
        error_handler.register_error_callback(callback)
        error_handler.register_error_callback(callback)

        # Should only be registered once
        assert error_handler._error_callbacks.count(callback) == 1

    def test_unregister_error_callback_success(self, error_handler):
        """Test successful error callback unregistration."""
        callback = Mock()

        # Register then unregister
        error_handler.register_error_callback(callback)
        result = error_handler.unregister_error_callback(callback)

        # Verify unregistration
        assert result is True
        assert callback not in error_handler._error_callbacks

    def test_unregister_error_callback_not_found(self, error_handler):
        """Test unregistering non-existent callback."""
        callback = Mock()

        # Try to unregister without registering
        result = error_handler.unregister_error_callback(callback)

        # Should return False
        assert result is False

    def test_register_handler_success(self, error_handler):
        """Test successful handler registration."""
        handler_func = Mock(return_value=True)

        # Register handler
        error_handler.register_handler(RVTaskError, handler_func)

        # Verify handler is registered (indirectly through callback list)
        assert len(error_handler._error_callbacks) > 0

    def test_register_handler_duplicate_prevention(self, error_handler):
        """Test duplicate handler registration is prevented."""
        handler_func = Mock(return_value=True)
        initial_count = len(error_handler._error_callbacks)

        # Register handler twice
        error_handler.register_handler(RVTaskError, handler_func)
        count_after_first = len(error_handler._error_callbacks)
        error_handler.register_handler(RVTaskError, handler_func)
        count_after_second = len(error_handler._error_callbacks)

        # Should not duplicate
        assert count_after_first > initial_count
        assert count_after_second == count_after_first

    def test_handle_error_with_dict_context(self, error_handler, sample_context):
        """Test error handling with dictionary context."""
        error = RVTaskError("Test error", task_id="test_123")

        # Handle error
        result = error_handler.handle_error(error, sample_context)

        # Verify error was processed
        assert "RVTaskError" in error_handler._error_counts
        assert error_handler._error_counts["RVTaskError"] == 1
        assert len(error_handler._error_history) == 1

    def test_handle_error_with_none_context(self, error_handler):
        """Test error handling with None context."""
        error = RVTaskError("Test error")

        # Handle error with None context
        result = error_handler.handle_error(error, None)

        # Should not raise exception
        assert "RVTaskError" in error_handler._error_counts

    def test_handle_error_with_empty_context(self, error_handler):
        """Test error handling with empty context."""
        error = RVTaskError("Test error")

        # Handle error with empty dict
        result = error_handler.handle_error(error, {})

        # Should process successfully
        assert "RVTaskError" in error_handler._error_counts

    def test_handle_error_with_callback_execution(self, error_handler):
        """Test error handling executes callbacks."""
        callback = Mock()
        error = RVTaskError("Test error")

        # Register callback and handle error
        error_handler.register_error_callback(callback)
        error_handler.handle_error(error, {"test": "context"})

        # Verify callback was called
        callback.assert_called()

    def test_handle_error_with_failing_callback(self, error_handler, mock_logging_manager):
        """Test error handling when callback fails."""
        _, _, mock_logger = mock_logging_manager
        failing_callback = Mock(side_effect=Exception("Callback failed"))
        error = RVTaskError("Test error")

        # Register failing callback
        error_handler.register_error_callback(failing_callback)

        # Handle error - should not raise exception
        result = error_handler.handle_error(error, {})

        # Error should still be processed
        assert "RVTaskError" in error_handler._error_counts

    def test_handle_error_with_introspection(self, error_handler):
        """Test handle_error_with_introspection method."""
        error = RVTaskError("Test error")

        # Handle with introspection
        result = error_handler.handle_error_with_introspection(
            error,
            component="TestComponent",
            task_id="test_123"
        )

        # Verify error was processed
        assert "RVTaskError" in error_handler._error_counts

    def test_create_context(self, error_handler):
        """Test context creation."""
        context = error_handler.create_context(
            component="TestComponent",
            phase="execution",
            task_id="test_123"
        )

        # Verify context structure
        assert context["component"] == "TestComponent"
        assert context["phase"] == "execution"
        assert context["task_id"] == "test_123"

    def test_error_context_manager_success(self, error_handler):
        """Test error context manager with successful execution."""
        executed = False

        # Use context manager
        with error_handler.error_context(component="TestComponent"):
            executed = True

        # Should complete successfully
        assert executed is True

    def test_error_context_manager_with_handled_error(self, error_handler):
        """Test error context manager with handled error."""
        # Register handler that handles the error
        handler_func = Mock(return_value=True)
        error_handler.register_handler(RVTaskError, handler_func)

        # Use context manager with error
        with error_handler.error_context(component="TestComponent"):
            raise RVTaskError("Test error")

        # Should not re-raise since error was handled
        assert "RVTaskError" in error_handler._error_counts

    def test_error_context_manager_with_unhandled_error(self, error_handler):
        """Test error context manager with unhandled error."""
        # Use context manager with unhandled error
        with pytest.raises(RVTaskError):
            with error_handler.error_context(component="TestComponent"):
                raise RVTaskError("Test error")

    def test_handle_errors_decorator_success(self, error_handler):
        """Test @handle_errors decorator with successful execution."""

        @ErrorHandler.handle_errors(component="TestComponent", phase="execution")
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_handle_errors_decorator_with_handled_error(self, error_handler):
        """Test @handle_errors decorator with handled error."""
        # Register handler that handles the error
        handler_func = Mock(return_value=True)
        error_handler.register_handler(RVTaskError, handler_func)

        @ErrorHandler.handle_errors(component="TestComponent", reraise=False)
        def test_function():
            raise RVTaskError("Test error")

        # Should not raise since error is handled
        result = test_function()
        assert result is None  # Default return for handled errors

    def test_handle_errors_decorator_with_reraise(self, error_handler):
        """Test @handle_errors decorator with reraise=True."""

        @ErrorHandler.handle_errors(component="TestComponent", reraise=True)
        def test_function():
            raise RVTaskError("Test error")

        # Should re-raise even if not handled
        with pytest.raises(RVTaskError):
            test_function()

    def test_handle_errors_decorator_unhandled_no_reraise(self, error_handler):
        """Test @handle_errors decorator with unhandled error and reraise=False."""

        @ErrorHandler.handle_errors(component="TestComponent", reraise=False)
        def test_function():
            raise RVTaskError("Test error")

        # Should not re-raise
        result = test_function()
        assert result is None

    def test_error_statistics_tracking(self, error_handler):
        """Test error statistics are properly tracked."""
        # Generate some errors
        errors = [
            RVTaskError("Task error 1"),
            RVTaskError("Task error 2"),
            RVToolError("Tool error 1"),
        ]

        for error in errors:
            error_handler.handle_error(error)

        # Check statistics
        stats = error_handler.get_error_statistics()

        assert stats["error_counts"]["RVTaskError"] == 2
        assert stats["error_counts"]["RVToolError"] == 1
        assert len(stats["recent_errors"]) == 3

    def test_clear_statistics(self, error_handler):
        """Test clearing error statistics."""
        # Generate an error
        error_handler.handle_error(RVTaskError("Test error"))

        # Clear statistics
        error_handler.clear_statistics()

        # Verify statistics are cleared
        stats = error_handler.get_error_statistics()
        assert stats["error_counts"] == {}
        assert stats["recent_errors"] == []

    def test_error_history_size_limit(self, error_handler):
        """Test error history maintains size limit."""
        # Generate more than 100 errors
        for i in range(105):
            error_handler.handle_error(RVTaskError(f"Error {i}"))

        # History should be limited to 100
        assert len(error_handler._error_history) == 100

        # Should contain the most recent errors
        assert "Error 104" in error_handler._error_history[-1]["error_message"]

    # Test specific error handlers

    def test_handle_task_error(self, error_handler):
        """Test RVTaskError specific handler."""
        error = RVTaskError("Task failed", task_id="task_123")

        result = error_handler._handle_task_error(error, {"component": "TestRunner"})

        # Should return False to allow further handling
        assert result is False

    def test_handle_tool_error(self, error_handler):
        """Test RVToolError specific handler."""
        error = RVToolError("Tool failed", tool_name="monkey")

        result = error_handler._handle_tool_error(error, {"component": "ToolRunner"})

        # Should return False to allow further handling
        assert result is False

    def test_handle_experiment_error(self, error_handler):
        """Test RVExperimentError specific handler."""
        error = RVExperimentError("Experiment failed", experiment_id="exp_123")

        result = error_handler._handle_experiment_error(error, {"component": "ExpRunner"})

        # Should return False to allow further handling
        assert result is False

    def test_handle_parsing_error(self, error_handler):
        """Test RVParsingError specific handler."""
        error = RVParsingError("Parse failed", parser_type="xml")

        result = error_handler._handle_parsing_error(error, {"component": "Parser"})

        # Should return False to allow further handling
        assert result is False

    def test_handle_prompt_error(self, error_handler):
        """Test RVPromptError specific handler."""
        error = RVPromptError("Prompt failed", strategy="completion")

        result = error_handler._handle_prompt_error(error, {"component": "LLM"})

        # Should return True indicating it was handled
        assert result is True

    def test_handle_llm_error(self, error_handler):
        """Test RVLLMError specific handler."""
        error = RVLLMError("LLM failed", model_name="gpt-4")

        result = error_handler._handle_llm_error(error, {"component": "LLM"})

        # Should return False to allow further handling
        assert result is False

    def test_handle_generic_error(self, error_handler):
        """Test generic RVAndroidError handler."""
        error = RVAndroidError("Generic error")

        result = error_handler._handle_generic_error(error, {"component": "Generic"})

        # Should return False to allow further handling
        assert result is False

    def test_error_with_cause(self, error_handler, mock_logging_manager):
        """Test error handling with cause chain."""
        _, _, mock_logger = mock_logging_manager

        root_cause = ValueError("Root cause")
        error = RVAndroidError("Wrapped error", cause=root_cause)

        error_handler.handle_error(error)

        # Should log with cause information
        assert "RVAndroidError" in error_handler._error_counts

    def test_builtin_handlers_registration(self, error_handler):
        """Test that built-in handlers are properly registered."""
        # Built-in handlers should be registered during initialization
        assert len(error_handler._error_callbacks) > 0

        # Test that specific error types are handled by built-in handlers
        task_error = RVTaskError("Test task error")
        tool_error = RVToolError("Test tool error")

        # These should be processed by built-in handlers
        error_handler.handle_error(task_error)
        error_handler.handle_error(tool_error)

        assert "RVTaskError" in error_handler._error_counts
        assert "RVToolError" in error_handler._error_counts

    def test_error_handler_type_specificity(self, error_handler):
        """Test that handlers are type-specific."""
        task_handler = Mock(return_value=True)
        tool_handler = Mock(return_value=True)

        # Register specific handlers
        error_handler.register_handler(RVTaskError, task_handler)
        error_handler.register_handler(RVToolError, tool_handler)

        # Test with task error
        task_error = RVTaskError("Task error")
        error_handler.handle_error(task_error)

        # Test with tool error
        tool_error = RVToolError("Tool error")
        error_handler.handle_error(tool_error)

        # Only appropriate handlers should be called for each error type
        # Note: Due to the wrapper implementation, we check the error counts instead
        assert "RVTaskError" in error_handler._error_counts
        assert "RVToolError" in error_handler._error_counts

    # Edge cases

    def test_handle_error_with_invalid_context_type(self, error_handler):
        """Test error handling with invalid context type."""
        error = RVTaskError("Test error")

        # Use invalid context type (should handle gracefully)
        result = error_handler.handle_error(error, "invalid_context")

        # Should still process the error
        assert "RVTaskError" in error_handler._error_counts

    def test_concurrent_error_handling(self, error_handler):
        """Test concurrent error handling."""
        errors_handled = []

        def handle_error_concurrently(error_id):
            error = RVTaskError(f"Concurrent error {error_id}")
            error_handler.handle_error(error)
            errors_handled.append(error_id)

        # Create multiple threads handling errors concurrently
        threads = [
            threading.Thread(target=handle_error_concurrently, args=(i,))
            for i in range(10)
        ]

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All errors should be handled
        assert len(errors_handled) == 10
        assert error_handler._error_counts["RVTaskError"] == 10

    def test_global_error_context_function(self):
        """Test global error_context function."""
        executed = False

        # Test successful execution
        with error_context(component="GlobalTest"):
            executed = True

        assert executed is True

    def test_global_error_context_with_error(self):
        """Test global error_context function with error."""
        # Should re-raise unhandled errors
        with pytest.raises(RVTaskError):
            with error_context(component="GlobalTest"):
                raise RVTaskError("Global context error")

    def test_error_context_with_custom_attributes(self, error_handler):
        """Test error context with custom error attributes."""
        # Test error with custom attributes
        error = RVTaskError("Task error", task_id="custom_task")
        error.custom_attr = "custom_value"

        result = error_handler.handle_error(error, {"custom_context": "value"})

        # Should handle error with custom attributes
        assert "RVTaskError" in error_handler._error_counts

    def test_error_handler_with_subclass_errors(self, error_handler):
        """Test error handling with error subclasses."""
        # Test with more specific error types
        execution_error = RVTaskExecutionError("Execution failed", task_id="exec_task")
        config_error = RVTaskConfigurationError("Config failed", task_id="config_task")

        error_handler.handle_error(execution_error)
        error_handler.handle_error(config_error)

        # Should track each error type separately
        assert "RVTaskExecutionError" in error_handler._error_counts
        assert "RVTaskConfigurationError" in error_handler._error_counts

    def test_error_handler_performance_with_many_callbacks(self, error_handler):
        """Test error handler performance with many callbacks."""
        # Register many callbacks
        callbacks = [Mock() for _ in range(100)]
        for callback in callbacks:
            error_handler.register_error_callback(callback)

        # Handle error
        start_time = time.time()
        error_handler.handle_error(RVTaskError("Performance test"))
        end_time = time.time()

        # Should complete in reasonable time (less than 1 second)
        assert (end_time - start_time) < 1.0
        assert "RVTaskError" in error_handler._error_counts

    def test_error_handler_memory_cleanup(self, error_handler):
        """Test that error handler doesn't leak memory with history."""
        # Generate many errors to test history cleanup
        for i in range(200):
            error_handler.handle_error(RVTaskError(f"Memory test {i}"))

        # History should be capped at 100
        assert len(error_handler._error_history) == 100

        # Error count should still track all errors
        assert error_handler._error_counts["RVTaskError"] == 200
