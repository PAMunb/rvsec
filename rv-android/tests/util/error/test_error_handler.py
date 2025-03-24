# tests/util/error/test_error_handler.py
"""
Unit tests for the error_handler module in rv-android.

This test suite covers the functionality of the ErrorHandler class,
which serves as the central error handling system in the rv-android framework.
"""

from unittest.mock import patch, MagicMock

import pytest

from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.error.handler_registry import HandlerRegistry
from rvandroid.util.exceptions import RVAndroidError


class TestErrorHandler:
    """
    Comprehensive test suite for the ErrorHandler class.

    ### Architectural Testing Considerations:
    - Verify central error handling functionality
    - Test error processing, tracking, and reporting
    - Ensure proper integration with recovery strategies
    - Validate event notification and error statistics
    """

    @pytest.fixture
    def mock_registry(self):
        """Fixture providing a mock HandlerRegistry."""
        mock = MagicMock(spec=HandlerRegistry)
        with patch('rvandroid.util.error.error_handler.HandlerRegistry') as mock_registry_class:
            mock_registry_class.return_value = mock
            yield mock

    @pytest.fixture
    def mock_event_bus(self):
        """Fixture providing a mock EventBus."""
        mock = MagicMock(spec=EventBus)
        with patch('rvandroid.util.error.error_handler.EventBus') as mock_event_bus_class:
            mock_event_bus_class.get_instance.return_value = mock
            yield mock

    @pytest.fixture
    def mock_logging(self):
        """Fixture providing a mock logging setup."""
        with patch('rvandroid.util.error.error_handler.LoggingManager') as mock_manager:
            mock_logger = MagicMock()
            manager_instance = MagicMock()
            mock_manager.get_instance.return_value = manager_instance
            manager_instance.get_logger.return_value = mock_logger
            yield mock_logger

    @pytest.fixture
    def error_handler(self, mock_registry, mock_event_bus, mock_logging):
        """Fixture providing an ErrorHandler with mocked dependencies."""
        # Reset singleton instance before test
        ErrorHandler._instance = None

        # Create a fresh instance with mocked dependencies
        handler = ErrorHandler.get_instance()
        yield handler

        # Reset singleton after test
        ErrorHandler._instance = None

    def test_singleton_pattern(self):
        """
        Test that ErrorHandler follows the singleton pattern.

        Validates:
        - Multiple calls to get_instance() return the same instance
        - Only one instance of ErrorHandler exists at any time
        """
        # Reset any existing instance
        ErrorHandler._instance = None

        # Get first instance
        handler1 = ErrorHandler.get_instance()

        # Get second instance
        handler2 = ErrorHandler.get_instance()

        # Verify both references point to the same object
        assert handler1 is handler2

        # Reset for other tests
        ErrorHandler._instance = None

    def test_thread_safety_of_singleton(self):
        """
        Test thread safety of the singleton implementation.

        Validates:
        - Concurrent calls to get_instance() safely return the same instance
        - Thread locking prevents race conditions
        """
        import threading

        # Reset any existing instance
        ErrorHandler._instance = None

        # Array to store instances from different threads
        instances = []
        threads = []

        # Function to get instance from a thread
        def get_instance():
            instances.append(ErrorHandler.get_instance())

        # Create and start multiple threads
        for _ in range(10):
            thread = threading.Thread(target=get_instance)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all threads got the same instance
        first_instance = instances[0]
        for instance in instances[1:]:
            assert instance is first_instance

        # Reset for other tests
        ErrorHandler._instance = None

    def test_initialization(self, error_handler, mock_registry, mock_event_bus, mock_logging):
        """
        Test proper initialization of the ErrorHandler.

        Validates:
        - Registry and event bus are correctly initialized
        - Error tracking structures are properly set up
        - Logger is configured correctly
        """
        # Verify registry was created
        assert hasattr(error_handler, '_registry')

        # Verify event bus was obtained
        assert hasattr(error_handler, '_event_bus')

        # Verify error tracking structures were initialized
        assert hasattr(error_handler, '_error_counts')
        assert hasattr(error_handler, '_error_history')
        assert hasattr(error_handler, '_recovery_attempts')

        # Verify default handlers were configured
        mock_registry.register.assert_called()

    def test_register_handler(self, error_handler, mock_registry):
        """
        Test handler registration functionality.

        Validates:
        - Handlers can be registered for specific exception types
        - Registration is delegated to the handler registry
        """
        # Define a mock handler
        mock_handler = MagicMock()

        # Reset mock to clear previous calls (from initialization)
        mock_registry.reset_mock()

        # Register the handler
        error_handler.register_handler(ValueError, mock_handler)

        # Verify registration was delegated to registry
        mock_registry.register.assert_called_once_with(ValueError, mock_handler)

    def test_handle_error_success(self, error_handler, mock_registry, mock_event_bus, mock_logging):
        """
        Test successful error handling with registered handlers.

        Validates:
        - Error is processed and handlers are found and executed
        - Error is logged appropriately
        - Event is published with correct information
        - Error statistics are updated
        """
        # Create a test error and context
        test_error = ValueError("Test error")
        test_context = {"task_id": 123, "phase": "testing"}

        # Set up mock handler that successfully handles the error
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]

        # Handle the error
        result = error_handler.handle_error(test_error, test_context)

        # Verify handlers were found via registry
        mock_registry.find_handlers.assert_called_once_with(ValueError)

        # Verify handler was called with correct arguments
        mock_handler.assert_called_once_with(test_error, test_context)

        # Verify error was logged
        mock_logging.error.assert_called()

        # Verify event was published
        mock_event_bus.publish_analysis_event.assert_called()

        # Verify successful handling
        assert result is True

        # Verify error statistics were updated
        assert error_handler._error_counts.get("ValueError") == 1
        assert len(error_handler._error_history) == 1

    def test_handle_error_with_multiple_handlers(self, error_handler, mock_registry):
        """
        Test error handling with multiple registered handlers.

        Validates:
        - Multiple handlers are called in sequence
        - Handling stops after first successful handler
        - Result indicates if any handler was successful
        """
        # Create a test error
        test_error = ValueError("Test error")

        # Create mock handlers with different behaviors
        failed_handler = MagicMock(return_value=False)
        successful_handler = MagicMock(return_value=True)
        uncalled_handler = MagicMock(return_value=True)

        # Set up mock registry to return the handlers
        mock_registry.find_handlers.return_value = [
            failed_handler, successful_handler, uncalled_handler
        ]

        # Handle the error
        result = error_handler.handle_error(test_error, None)

        # Verify both handlers were called in order
        failed_handler.assert_called_once_with(test_error, None)
        successful_handler.assert_called_once_with(test_error, None)

        # Verify third handler was not called since second was successful
        uncalled_handler.assert_not_called()

        # Verify successful handling
        assert result is True

    def test_handle_error_all_handlers_fail(self, error_handler, mock_registry):
        """
        Test error handling when all handlers fail.

        Validates:
        - All handlers are called when none succeed
        - Result indicates failure when no handler succeeds
        """
        # Create a test error
        test_error = ValueError("Test error")

        # Create mock handlers that all fail
        failed_handler1 = MagicMock(return_value=False)
        failed_handler2 = MagicMock(return_value=False)

        # Set up mock registry to return the handlers
        mock_registry.find_handlers.return_value = [
            failed_handler1, failed_handler2
        ]

        # Handle the error
        result = error_handler.handle_error(test_error, None)

        # Verify both handlers were called
        failed_handler1.assert_called_once_with(test_error, None)
        failed_handler2.assert_called_once_with(test_error, None)

        # Verify unsuccessful handling
        assert result is False

    def test_handle_error_with_rv_android_error(self, error_handler, mock_registry, mock_logging):
        """
        Test handling of RVAndroidError with nested cause.

        Validates:
        - RVAndroidError is properly logged with cause information
        - Error details are correctly captured in logging
        """
        # Create a test error with a cause
        cause = RuntimeError("Original cause")
        rv_error = RVAndroidError("High-level error message", cause)

        # Set up mock handler
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]

        # Handle the error
        error_handler.handle_error(rv_error, None)

        # Verify error was logged with cause information
        call_args = mock_logging.error.call_args_list[0]
        error_message = call_args[0][0]
        exc_info = call_args[1].get('exc_info')

        # Verify message contains the RVAndroidError message
        assert "High-level error message" in error_message

        # Verify cause was included
        assert "caused by" in error_message

        # Verify handler was called with the RVAndroidError
        mock_handler.assert_called_once_with(rv_error, None)

    def test_handle_error_no_handlers(self, error_handler, mock_registry):
        """
        Test handling of error with no registered handlers.

        Validates:
        - Errors without specific handlers are still logged and tracked
        - Result indicates unsuccessful handling when no handlers exist
        """
        # Create a test error
        test_error = KeyError("No handler for this")

        # Set up mock registry to return empty handler list
        mock_registry.find_handlers.return_value = []

        # Handle the error
        result = error_handler.handle_error(test_error, None)

        # Verify handlers were searched for
        mock_registry.find_handlers.assert_called_once_with(KeyError)

        # Verify unsuccessful handling
        assert result is False

        # Verify error was still tracked
        assert error_handler._error_counts.get("KeyError") == 1
        assert len(error_handler._error_history) == 1

    def test_handle_error_with_task_id(self, error_handler, mock_event_bus):
        """
        Test error handling with task ID in context.

        Validates:
        - Task ID is properly extracted from context
        - Task-specific event is published when task ID is available
        """
        # Create a test error with task context
        test_error = ValueError("Task-related error")
        task_context = {"task_id": 42, "phase": "testing"}

        # Handle the error
        error_handler.handle_error(test_error, task_context)

        # Verify task-specific event was published
        call_args = mock_event_bus.publish_analysis_event.call_args
        assert call_args[1]["related_task_id"] == 42

    def test_handle_error_handler_exception(self, error_handler, mock_registry, mock_logging):
        """
        Test error handling when a handler raises an exception.

        Validates:
        - Exceptions in handlers are caught and logged
        - Processing continues to next handler after exception
        """
        # Create a test error
        test_error = ValueError("Test error")

        # Create handlers, first one raises an exception
        def failing_handler(error, context):
            raise RuntimeError("Handler failed")

        successful_handler = MagicMock(return_value=True)

        # Set up mock registry to return both handlers
        mock_registry.find_handlers.return_value = [
            failing_handler, successful_handler
        ]

        # Handle the error
        result = error_handler.handle_error(test_error, None)

        # Verify an error was logged (without being strict about the format)
        assert mock_logging.error.called, "Error logger was not called"

        # Verify second handler was still called despite first handler's exception
        successful_handler.assert_called_once_with(test_error, None)

        # Verify overall handling was successful due to second handler
        assert result is True

    def test_error_history_limit(self, error_handler):
        """
        Test that error history is limited to a reasonable size.

        Validates:
        - Error history doesn't grow indefinitely
        - Oldest errors are removed when limit is reached
        """
        # The class uses a hard-coded maximum history size
        # Access it directly or use the constant value from the implementation
        max_history_size = 100  # Default value from the implementation

        # Generate errors beyond the limit
        for i in range(max_history_size + 10):
            error_handler.handle_error(ValueError(f"Error {i}"), None)

        # Verify history is limited to max size
        assert len(error_handler._error_history) <= max_history_size

        # Verify oldest errors were removed (should have the most recent errors)
        error_messages = [entry["error_message"] for entry in error_handler._error_history]

        # Check for the most recent error messages
        for i in range(max_history_size + 10 - 5, max_history_size + 10):
            assert f"Error {i}" in str(error_messages), f"Expected recent error 'Error {i}' in history"

    def test_get_error_statistics(self, error_handler):
        """
        Test retrieval of error statistics.

        Validates:
        - Error statistics are correctly tracked and returned
        - Statistics include counts, attempts, and recent errors
        """
        # Generate some errors of different types
        error_handler.handle_error(ValueError("Value error"), None)
        error_handler.handle_error(ValueError("Another value error"), None)
        error_handler.handle_error(KeyError("Key error"), None)

        # Get statistics
        stats = error_handler.get_error_statistics()

        # Verify statistics structure
        assert "error_counts" in stats
        assert "recovery_attempts" in stats
        assert "recent_errors" in stats

        # Verify error counts
        assert stats["error_counts"]["ValueError"] == 2
        assert stats["error_counts"]["KeyError"] == 1

        # Verify recent errors
        assert len(stats["recent_errors"]) == 3

    def test_clear_statistics(self, error_handler):
        """
        Test clearing of error statistics.

        Validates:
        - Error statistics can be reset
        - All tracking dictionaries are cleared
        """
        # Generate some errors
        error_handler.handle_error(ValueError("Test error"), None)
        error_handler.handle_error(KeyError("Another error"), None)

        # Verify errors were tracked
        assert len(error_handler._error_counts) > 0
        assert len(error_handler._error_history) > 0

        # Clear statistics
        error_handler.clear_statistics()

        # Verify all statistics were cleared
        assert error_handler._error_counts == {}
        assert error_handler._error_history == []
        assert error_handler._recovery_attempts == {}

    def test_log_error_with_context(self, error_handler, mock_logging):
        """
        Test that errors are logged with context information.

        Validates:
        - Error logging includes context information
        - Context is used to enrich the log message
        """
        # Create a test error with rich context
        test_error = ValueError("Context-rich error")
        test_context = {
            "task_id": 42,
            "phase": "testing",
            "app_name": "test_app",
            "tool_name": "test_tool"
        }

        # Handle the error
        error_handler.handle_error(test_error, test_context)

        # Verify context was used in logging
        with_context_call = mock_logging.with_context.call_args
        context_args = with_context_call[1]

        # Verify key context elements were included
        assert context_args["error_type"] == "ValueError"
        assert context_args["task_id"] == 42
        assert context_args["phase"] == "testing"
        assert context_args["app_name"] == "test_app"
        assert context_args["tool_name"] == "test_tool"

    def test_publish_error_event(self, error_handler, mock_event_bus):
        """
        Test publishing of error events to the event bus.

        Validates:
        - Error events are published to the event bus
        - Events contain appropriate error information
        """
        # Create a test error
        test_error = ValueError("Event publishing test")
        test_context = {"phase": "testing"}

        # Handle the error
        error_handler.handle_error(test_error, test_context)

        # Verify event was published
        publish_call = mock_event_bus.publish_analysis_event.call_args

        # Verify event type and source
        assert publish_call[0][0] == EventType.ERROR_DETECTED
        assert publish_call[1]["source"] == "ErrorHandler"

        # Verify event data
        event_data = publish_call[1]["data"]
        assert event_data["error_type"] == "ValueError"
        assert event_data["error_message"] == "Event publishing test"
        assert event_data["context"] == test_context

    def test_handle_error_with_custom_handler(self, error_handler):
        """
        Test error handling with a custom registered handler.

        Validates:
        - Custom handlers can be registered and called
        - Handler receives correct error and context information
        """
        # Reset the registry and its mock
        error_handler._registry = MagicMock()

        # Create a test error and context
        test_error = TypeError("Custom handler test")
        test_context = {"custom": "value"}

        # Create and track a custom handler
        handler_called = False
        handler_args = None

        def custom_handler(error, context):
            nonlocal handler_called, handler_args
            handler_called = True
            handler_args = (error, context)
            return True

        # Mock the find_handlers method to return our custom handler
        error_handler._registry.find_handlers.return_value = [custom_handler]

        # Handle the error
        result = error_handler.handle_error(test_error, test_context)

        # Verify handler was called
        assert handler_called is True

        # Verify handler received correct arguments
        assert handler_args[0] is test_error
        assert handler_args[1] is test_context

        # Verify successful handling
        assert result is True

    def test_handle_generic_error(self, error_handler):
        """
        Test the _handle_generic_error method.

        Validates:
        - Generic handler logs but doesn't claim to handle the error
        - Return value indicates error not fully handled
        """
        # Create a test RVAndroidError
        test_error = RVAndroidError("Generic error test", None)

        # Call the generic handler directly
        result = error_handler._handle_generic_error(test_error, None)

        # Verify handler doesn't claim to have handled the error
        assert result is False

    def test_add_to_history(self, error_handler):
        """
        Test the _add_to_history method.

        Validates:
        - Errors are properly added to history with metadata
        - History entries contain all required information
        """
        # Create a test error and context
        test_error = ValueError("History test")
        test_context = {"task_id": 123}

        # Add to history
        error_handler._add_to_history(test_error, test_context)

        # Verify entry was added
        assert len(error_handler._error_history) == 1

        # Verify entry structure
        entry = error_handler._error_history[0]
        assert "timestamp" in entry
        assert entry["error_type"] == "ValueError"
        assert entry["error_message"] == "History test"
        assert entry["context"] == test_context
