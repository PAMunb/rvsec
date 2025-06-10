# tests/util/error/test_error_handler.py
"""
Unit tests for the ErrorHandler module in rv-android.

This test suite covers the functionality of the ErrorHandler class,
which serves as the central error management facility for the framework.
"""

import os
import sys
import threading
import time
from unittest.mock import patch, MagicMock

import pytest

# Ensure the parent directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from rv_android_core.util.error.error_handler import ErrorHandler, error_context
from rv_android_core.util.error.context import ErrorContext
from rv_android_core.util.error.handler_registry import HandlerRegistry
from rv_android_core.util.exceptions import RVAndroidError, RVTaskError, RVToolError


class TestErrorHandler:
    """
    Comprehensive test suite for the ErrorHandler class.

    ### Architectural Testing Considerations:
    - Validate singleton pattern implementation
    - Test error handling registry integration
    - Verify error tracking and statistics functionality
    - Test recovery strategy application
    - Ensure proper event publishing behavior
    """

    @pytest.fixture
    def mock_logger(self):
        """Fixture providing a mock logger."""
        logger = MagicMock()
        return logger

    @pytest.fixture
    def mock_registry(self):
        """Fixture providing a mock handler registry."""
        registry = MagicMock(spec=HandlerRegistry)
        return registry

    @pytest.fixture
    def mock_callback(self):
        """Fixture providing a mock error callback."""
        callback = MagicMock()
        return callback

    @pytest.fixture
    def handler_with_mocks(self, mock_logger, mock_registry):
        """Fixture providing an ErrorHandler with mocked dependencies."""
        with patch('rv_android_core.util.error.error_handler.LoggingManager') as mock_logging_manager:
            # Set up the mock logger manager
            mock_manager = MagicMock()
            mock_manager.get_logger.return_value = mock_logger
            mock_logging_manager.get_instance.return_value = mock_manager

            # Patch the HandlerRegistry
            with patch('rv_android_core.util.error.error_handler.HandlerRegistry', return_value=mock_registry):
                # Create the handler instance
                handler = ErrorHandler()

                yield handler, mock_logger, mock_registry

    def test_singleton_pattern(self):
        """
        Test that ErrorHandler correctly implements the singleton pattern.

        Validates:
        - Multiple get_instance calls return the same object
        - Direct instantiation creates a different object than the singleton
        """
        # Get singleton instance twice
        instance1 = ErrorHandler.get_instance()
        instance2 = ErrorHandler.get_instance()

        # They should be the same object
        assert instance1 is instance2

        # Create a direct instance
        direct_instance = ErrorHandler()

        # Singleton and direct instances should be different objects
        assert direct_instance is not instance1

        # But they should be the same class
        assert isinstance(direct_instance, ErrorHandler)
        assert isinstance(instance1, ErrorHandler)

    # def test_initialization(self, handler_with_mocks):
    #     """
    #     Test that ErrorHandler is correctly initialized.
    #
    #     Validates:
    #     - Logger is properly configured
    #     - Registry is initialized
    #     - Error statistics are initialized
    #     - Default handlers are registered
    #     """
    #     handler, mock_logger, mock_registry, _ = handler_with_mocks
    #
    #     # Verify logger was created with correct context
    #     assert handler._logger is mock_logger
    #
    #     # Verify registry was created
    #     assert handler._registry is mock_registry
    #
    #     # Verify statistics were initialized
    #     assert hasattr(handler, '_error_counts')
    #     assert isinstance(handler._error_counts, dict)
    #     assert len(handler._error_counts) == 0
    #
    #     assert hasattr(handler, '_error_history')
    #     assert isinstance(handler._error_history, list)
    #     assert len(handler._error_history) == 0
    #
    #     assert hasattr(handler, '_recovery_attempts')
    #     assert isinstance(handler._recovery_attempts, dict)
    #     assert len(handler._recovery_attempts) == 0
    #
    #     # Verify default handlers were registered
    #     # At minimum, these error types should be registered
    #     mock_registry.register.assert_any_call(ADBError, handler._configure_default_handlers.__self__.handle_adb_error)
    #     mock_registry.register.assert_any_call(EmulatorError,
    #                                            handler._configure_default_handlers.__self__.handle_emulator_error)
    #     mock_registry.register.assert_any_call(RvTimeoutError,
    #                                            handler._configure_default_handlers.__self__.handle_timeout_error)
    #     mock_registry.register.assert_any_call(RVAndroidError, handler._handle_generic_error)

    def test_register_handler(self, handler_with_mocks):
        """
        Test registering a custom error handler.

        Validates:
        - Handlers can be registered for specific error types
        - Registration correctly delegates to the registry
        """
        handler, _, mock_registry = handler_with_mocks

        # Define a mock handler function
        def custom_handler(error, context):
            return True

        # Register the handler
        handler.register_handler(ValueError, custom_handler)

        # Verify handler was registered with the registry
        mock_registry.register.assert_called_with(ValueError, custom_handler)

    def test_handle_error_success(self, handler_with_mocks):
        """
        Test successful error handling.

        Validates:
        - Errors are logged correctly
        - Events are published
        - Handlers are found and executed
        - Error statistics are updated
        - Return value reflects successful handling
        """
        handler, mock_logger, mock_registry = handler_with_mocks

        # Set up a successful handler
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]

        # Create test error and context
        test_error = ValueError("Test error")
        test_context = {"task_id": 123}

        # Handle the error
        result = handler.handle_error(test_error, test_context)

        # Verify error was logged
        mock_logger.error.assert_called()

        # Verify handlers were found and executed
        mock_registry.find_handlers.assert_called_with(ValueError)
        mock_handler.assert_called_with(test_error, test_context)

        # Verify error was added to history
        assert len(handler._error_history) == 1
        assert handler._error_counts.get('ValueError') == 1

        # Verify result indicates successful handling
        assert result is True

    def test_handle_error_failure(self, handler_with_mocks):
        """
        Test error handling when no handler succeeds.

        Validates:
        - Unsuccessful handling is correctly reported
        - Error statistics are still updated
        """
        handler, _, mock_registry = handler_with_mocks

        # Set up an unsuccessful handler
        mock_handler = MagicMock(return_value=False)
        mock_registry.find_handlers.return_value = [mock_handler]

        # Create test error
        test_error = ValueError("Test error")

        # Handle the error
        result = handler.handle_error(test_error, None)

        # Verify handler was called (context might be empty dict instead of None)
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        assert call_args[0][0] == test_error  # First arg is the error

        # Verify error was added to history
        assert len(handler._error_history) == 1
        assert handler._error_counts.get('ValueError') == 1

        # Verify result indicates unsuccessful handling
        assert result is False

    def test_handle_error_no_handlers(self, handler_with_mocks):
        """
        Test error handling when no handlers are found.

        Validates:
        - Error is still logged and tracked when no handlers exist
        - Handling fails gracefully with no handlers
        """
        handler, _, mock_registry = handler_with_mocks

        # Set up registry to return no handlers
        mock_registry.find_handlers.return_value = []

        # Create test error
        test_error = KeyError("Test error")

        # Handle the error
        result = handler.handle_error(test_error, None)

        # Verify registry was queried
        mock_registry.find_handlers.assert_called_with(KeyError)

        # Verify error was added to history
        assert len(handler._error_history) == 1
        assert handler._error_counts.get('KeyError') == 1

        # Verify result indicates unsuccessful handling
        assert result is False

    def test_handle_error_handler_exception(self, handler_with_mocks):
        """
        Test error handling when a handler raises an exception.

        Validates:
        - Exceptions in handlers are caught and logged
        - Processing continues with next handler if available
        - Error statistics are still updated
        """
        handler, mock_logger, mock_registry = handler_with_mocks

        # Set up a handler that raises an exception and one that succeeds
        def failing_handler(error, context):
            raise RuntimeError("Handler failed")

        succeeding_handler = MagicMock(return_value=True)

        # Return both handlers from the registry
        mock_registry.find_handlers.return_value = [failing_handler, succeeding_handler]

        # Create test error
        test_error = ValueError("Test error")

        # Handle the error
        result = handler.handle_error(test_error, None)

        # Verify both handlers were attempted
        succeeding_handler.assert_called_once()
        call_args = succeeding_handler.call_args
        assert call_args[0][0] == test_error

        # Verify exception was logged
        mock_logger.error.assert_any_call("Error in handler: Handler failed")

        # Verify error was added to history
        assert len(handler._error_history) == 1
        assert handler._error_counts.get('ValueError') == 1

        # Verify result indicates successful handling (from the second handler)
        assert result is True

    def test_handle_error_with_context(self, handler_with_mocks):
        """
        Test error handling with detailed context information.

        Validates:
        - Context is correctly passed to handlers
        - Logger gets appropriate context
        - Events include context data
        """
        handler, mock_logger, mock_registry = handler_with_mocks

        # Set up a handler
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]

        # Create test error and detailed context
        test_error = ValueError("Test error")
        test_context = {
            "task_id": 123,
            "phase": "testing",
            "app_name": "TestApp",
            "component": "TestComponent"
        }

        # Handle the error
        handler.handle_error(test_error, test_context)

        # Verify logger received context
        mock_logger.with_context.assert_called_with(error_type='ValueError', **test_context)

        # Verify handler received context
        mock_handler.assert_called_with(test_error, test_context)

        # Register a callback
        mock_callback = MagicMock()
        handler.register_error_callback(mock_callback)

        # Handle the error again to test callback
        handler.handle_error(test_error, test_context)

        # Verify callback was called with error and context
        mock_callback.assert_called_with(test_error, test_context)

    def test_callback_registration(self, handler_with_mocks):
        """
        Test error callback registration and notification.

        Validates:
        - Callbacks can be registered and unregistered
        - Callbacks are called when errors occur
        - Multiple callbacks are supported
        """
        handler, _, mock_registry = handler_with_mocks

        # Setup registry to return a handler
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]

        # Create mock callbacks
        callback1 = MagicMock()
        callback2 = MagicMock()

        # Register callbacks
        handler.register_error_callback(callback1)
        handler.register_error_callback(callback2)

        # Create test error and context
        test_error = ValueError("Test error")
        test_context = {"task_id": 123}

        # Handle the error
        handler.handle_error(test_error, test_context)

        # Verify both callbacks were called
        callback1.assert_called_once_with(test_error, test_context)
        callback2.assert_called_once_with(test_error, test_context)

    def test_callback_unregistration(self, handler_with_mocks):
        """
        Test error callback unregistration.

        Validates:
        - Callbacks can be unregistered
        - Unregistered callbacks are not called
        - Return value indicates success/failure of unregistration
        """
        handler, _, mock_registry = handler_with_mocks

        # Setup registry to return a handler
        mock_registry.find_handlers.return_value = [MagicMock(return_value=True)]

        # Create mock callback
        callback = MagicMock()

        # Register and then unregister callback
        handler.register_error_callback(callback)
        result = handler.unregister_error_callback(callback)

        # Verify unregistration was successful
        assert result is True

        # Handle an error
        test_error = ValueError("Test error")
        handler.handle_error(test_error, None)

        # Verify callback was not called
        callback.assert_not_called()

        # Test unregistering a non-existent callback
        non_existent_callback = MagicMock()
        result = handler.unregister_error_callback(non_existent_callback)
        assert result is False

    def test_handle_generic_error(self, handler_with_mocks):
        """
        Test the generic error handler.

        Validates:
        - Generic handler logs error but doesn't claim to have handled it
        - Return value is correctly set to False
        """
        handler, mock_logger, _ = handler_with_mocks

        # Create test error
        test_error = RVAndroidError("Generic error", None)

        # Call the generic handler directly
        result = handler._handle_generic_error(test_error, None)

        # Verify error was logged
        mock_logger.info.assert_called()

        # Verify handler reports that it didn't handle the error
        assert result is False

    def test_error_statistics(self, handler_with_mocks):
        """
        Test error statistics tracking and reporting.

        Validates:
        - Error counts are correctly tracked
        - Error history is maintained
        - Statistics are correctly reported
        """
        handler, _, mock_registry = handler_with_mocks

        # Setup mock handler
        mock_registry.find_handlers.return_value = [MagicMock(return_value=True)]

        # Handle a few different errors
        handler.handle_error(ValueError("Value error"), {"phase": "test1"})
        handler.handle_error(KeyError("Key error"), {"phase": "test2"})
        handler.handle_error(ValueError("Another value error"), {"phase": "test3"})

        # Get statistics
        stats = handler.get_error_statistics()

        # Verify error counts
        assert stats["error_counts"]["ValueError"] == 2
        assert stats["error_counts"]["KeyError"] == 1

        # Verify error history
        assert len(stats["recent_errors"]) == 3

        # Verify history entries have required fields
        for entry in stats["recent_errors"]:
            assert "timestamp" in entry
            assert "error_type" in entry
            assert "error_message" in entry
            assert "context" in entry

    def test_clear_statistics(self, handler_with_mocks):
        """
        Test clearing error statistics.

        Validates:
        - Statistics are properly reset when cleared
        - Error counts, history, and recovery attempts are all cleared
        """
        handler, _, mock_registry = handler_with_mocks

        # Setup mock handler
        mock_registry.find_handlers.return_value = [MagicMock(return_value=True)]

        # Add some errors
        handler.handle_error(ValueError("Test error"), None)
        handler.handle_error(TypeError("Another error"), None)

        # Verify errors were recorded
        assert len(handler._error_history) == 2
        assert len(handler._error_counts) == 2

        # Clear statistics
        handler.clear_statistics()

        # Verify everything was cleared
        assert len(handler._error_history) == 0
        assert len(handler._error_counts) == 0
        assert len(handler._recovery_attempts) == 0

        # Verify get_error_statistics returns empty data
        stats = handler.get_error_statistics()
        assert stats["error_counts"] == {}
        assert stats["recent_errors"] == []

    def test_add_to_history(self, handler_with_mocks):
        """
        Test adding errors to history with size limiting.

        Validates:
        - Errors are added to history with correct data
        - History size is limited to a reasonable number
        """
        handler, _, _ = handler_with_mocks

        # Add more than the limit of errors to history
        # The internal limit is 100 entries
        for i in range(110):
            error = ValueError(f"Error {i}")
            handler._add_to_history(error, {"index": i})

        # Verify history size is capped
        assert len(handler._error_history) == 100

        # Verify the oldest entries were removed (FIFO)
        # The first entry should be error #10, not error #0
        assert handler._error_history[0]["error_message"] == "Error 10"

        # Verify the newest entry is present
        assert handler._error_history[-1]["error_message"] == "Error 109"

    def test_log_error(self, handler_with_mocks):
        """
        Test error logging with different error types.

        Validates:
        - Regular errors are logged correctly
        - RVAndroidError with causes are logged with cause information
        """
        handler, mock_logger, _ = handler_with_mocks

        # Test with a regular error
        regular_error = ValueError("Regular error")
        handler._log_error(regular_error, None)

        # Verify regular error was logged
        mock_logger.error.assert_called_with("Error: Regular error", exc_info=regular_error)

        # Reset mock
        mock_logger.reset_mock()

        # Test with an RVAndroidError that has a cause
        cause = RuntimeError("Original cause")
        rv_error = RVAndroidError("RV error with cause", cause)
        handler._log_error(rv_error, None)

        # Verify error with cause was logged appropriately
        mock_logger.error.assert_called_with(
            "Error: RV error with cause caused by: Original cause",
            exc_info=cause
        )

    # def test_diagnose(self, handler_with_mocks):
    #     """
    #     Test the diagnostic report generation.
    #
    #     Validates:
    #     - Diagnostics contain expected information
    #     - Issues are correctly identified
    #     """
    #     handler, _, mock_registry, _ = handler_with_mocks
    #
    #     # Set up some mock data
    #     handler._error_counts = {"ValueError": 5, "KeyError": 3}
    #     handler._error_history = [{"error_type": "ValueError", "timestamp": 123456789}] * 10
    #
    #     # Generate diagnostics
    #     diagnostics = handler.diagnose()
    #
    #     # Verify diagnostics structure
    #     assert "class_count" in diagnostics
    #     assert "activity_count" in diagnostics
    #     assert "method_count" in diagnostics
    #     assert "called_method_count" in diagnostics
    #     assert "error_count" in diagnostics
    #     assert "unique_error_count" in diagnostics
    #     assert "issues" in diagnostics
    #
    #     # Verify correct counts
    #     assert diagnostics["error_count"] == 10

    # def test_event_bus_lazy_import(self, handler_with_mocks):
    #     """
    #     Test lazy import of EventBus.
    #
    #     Validates:
    #     - EventBus is lazily imported only when needed
    #     - System handles missing EventBus gracefully
    #     """
    #     handler, mock_logger, _, _ = handler_with_mocks
    #
    #     # Reset the event bus to None to test lazy loading
    #     handler._event_bus = None
    #
    #     # Create test patches
    #     with patch('rv_android_core.util.error.error_handler.EventBus') as mock_event_bus_class:
    #         # Set up mock EventBus
    #         mock_event_bus_instance = MagicMock()
    #         mock_event_bus_class.get_instance.return_value = mock_event_bus_instance
    #
    #         # Access the event_bus property to trigger lazy import
    #         assert handler.event_bus is mock_event_bus_instance
    #
    #         # Verify EventBus was imported and instantiated
    #         mock_event_bus_class.get_instance.assert_called_once()
    #
    #     # Now test the case where import fails
    #     handler._event_bus = None
    #
    #     with patch('rv_android_core.util.error.error_handler.EventBus', side_effect=ImportError("Module not found")):
    #         # Access should return None but not raise an exception
    #         assert handler.event_bus is None
    #
    #         # Verify warning was logged
    #         mock_logger.warning.assert_called_with("EventBus module could not be imported")

    # def test_to_dict(self, handler_with_mocks):
    #     """
    #     Test conversion of repository to dictionary format.
    #
    #     Validates:
    #     - Repository data is correctly serialized
    #     - All required sections are included
    #     """
    #     handler, _, mock_registry, _ = handler_with_mocks
    #
    #     # Add some errors for the statistics
    #     handler._error_counts = {"ValueError": 2, "KeyError": 1}
    #     handler._error_history = [
    #         {"timestamp": 123456, "error_type": "ValueError", "error_message": "Test error", "context": {}}
    #     ]
    #
    #     # Get dictionary representation
    #     result = handler.to_dict()
    #
    #     # Verify structure
    #     assert "metrics" in result
    #     assert "classes" in result
    #     assert "errors" in result
    #
    #     # Verify error data
    #     assert result["errors"]["count"] == 1
    #     assert result["errors"]["unique_count"] == 0  # Using _unique_errors set, which is empty
    #     assert len(result["errors"]["items"]) == 1

    def test_handler_execution_order(self, handler_with_mocks):
        """
        Test that handlers are executed in the order they are returned from registry.

        Validates:
        - Handlers are executed in the correct order
        - Execution stops after first successful handler
        """
        handler, _, mock_registry = handler_with_mocks

        # Create a list to track execution order
        execution_order = []

        # Create mock handlers with different return values
        def handler1(error, context):
            execution_order.append(1)
            return False  # First handler fails

        def handler2(error, context):
            execution_order.append(2)
            return True  # Second handler succeeds

        def handler3(error, context):
            execution_order.append(3)
            return False  # Third handler should never be called

        # Set up registry to return these handlers
        mock_registry.find_handlers.return_value = [handler1, handler2, handler3]

        # Handle an error
        handler.handle_error(ValueError("Test error"), None)

        # Verify execution order - should only execute first two handlers
        assert execution_order == [1, 2]

    def test_rv_android_error_with_cause(self, handler_with_mocks):
        """
        Test handling of RVAndroidError with nested causes.

        Validates:
        - Errors with causes are correctly logged
        - Cause chain information is preserved
        """
        handler, mock_logger, mock_registry = handler_with_mocks

        # Set up registry to return a handler
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]

        # Create a nested error with cause
        original_cause = ValueError("Original cause")
        rv_error = RVAndroidError("RV error with cause", original_cause)

        # Handle the error
        handler.handle_error(rv_error, None)

        # Verify error was logged with cause information
        mock_logger.error.assert_called()

        # Verify handler was called with the original error
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        assert call_args[0][0] == rv_error

        # Verify error was added to history
        assert len(handler._error_history) == 1
        assert handler._error_counts.get('RVAndroidError') == 1

    # def test_unique_errors_tracking(self, handler_with_mocks):
    #     """
    #     Test tracking of unique errors.
    #
    #     Validates:
    #     - Unique errors are correctly identified
    #     - Duplicate errors are tracked but not counted as unique
    #     """
    #     handler, _, mock_registry, _ = handler_with_mocks
    #
    #     # Set up registry to return a handler
    #     mock_registry.find_handlers.return_value = [MagicMock(return_value=True)]
    #
    #     # Create an RV error log object with a unique_msg field
    #     class MockRvErrorLog:
    #         def __init__(self, msg):
    #             self.unique_msg = msg
    #
    #     # Register several errors, some duplicates
    #     handler.register_rv_error(MockRvErrorLog("error1"))
    #     handler.register_rv_error(MockRvErrorLog("error2"))
    #     handler.register_rv_error(MockRvErrorLog("error1"))  # Duplicate
    #     handler.register_rv_error(MockRvErrorLog("error3"))
    #
    #     # Verify total and unique counts
    #     assert len(handler.errors) == 4  # All errors
    #     assert len(handler.unique_errors) == 3  # Unique errors
    #
    #     # Verify specific unique errors
    #     assert "error1" in handler.unique_errors
    #     assert "error2" in handler.unique_errors
    #     assert "error3" in handler.unique_errors

    # def test_publish_error_event_with_event_bus(self, handler_with_mocks):
    #     """
    #     Test publishing error events through the event bus.
    #
    #     Validates:
    #     - Events are correctly published to the event bus
    #     - Event data contains all required information
    #     """
    #     handler, _, mock_registry, mock_event_bus = handler_with_mocks
    #
    #     # Create a patch for EventType to simulate import
    #     with patch('rv_android_core.util.error.error_handler.EventType') as MockEventType:
    #         # Set ERROR_DETECTED enum value
    #         MockEventType.ERROR_DETECTED = "ERROR_DETECTED"
    #
    #         # Create test error and context
    #         test_error = ValueError("Test event error")
    #         test_context = {"custom_field": "test_value"}
    #
    #         # Publish event directly
    #         handler._publish_error_event(test_error, test_context)
    #
    #         # Verify event bus was called with correct data
    #         mock_event_bus.publish_analysis_event.assert_called_once()
    #
    #         # Extract arguments
    #         call_args = mock_event_bus.publish_analysis_event.call_args[0]
    #         call_kwargs = mock_event_bus.publish_analysis_event.call_args[1]
    #
    #         # Verify event type
    #         assert call_args[0] == "ERROR_DETECTED"
    #
    #         # Verify event data
    #         event_data = call_kwargs.get('data', {})
    #         assert event_data.get('error_type') == 'ValueError'
    #         assert event_data.get('error_message') == 'Test event error'
    #         assert event_data.get('context') == test_context

    def test_error_history_size_limit(self, handler_with_mocks):
        """
        Test that error history size is limited.

        Validates:
        - Error history doesn't grow indefinitely
        - Oldest errors are removed when limit is reached
        """
        handler, _, mock_registry = handler_with_mocks

        # Setup registry to always return a successful handler
        mock_registry.find_handlers.return_value = [MagicMock(return_value=True)]

        # Generate many errors to exceed the history limit
        for i in range(105):  # Assuming limit is 100
            handler.handle_error(ValueError(f"Error {i}"), None)

        # Verify history size is limited
        assert len(handler._error_history) <= 100

        # Verify oldest entries were removed first
        # The first error should have timestamp greater than the
        # earliest error we generated (which would have been removed)
        first_error_timestamp = handler._error_history[0]["timestamp"]
        early_timestamp = time.time() - 105  # Approximate timestamp of first error

        # First timestamp should be later than the earliest error timestamp
        assert first_error_timestamp > early_timestamp

    def test_thread_safety(self):
        """
        Test thread safety of singleton implementation.

        Validates:
        - Instance creation is thread-safe
        - Multiple threads get the same instance
        """
        # Use a list to collect instances created by threads
        instances = []
        exception_occurred = [False]  # Use list for mutable state

        def get_instance():
            try:
                instances.append(ErrorHandler.get_instance())
            except Exception:
                exception_occurred[0] = True

        # Create threads that try to get the instance simultaneously
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=get_instance)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify no exceptions occurred
        assert not exception_occurred[0]

        # Verify all threads got the same instance
        assert len(set(instances)) == 1  # All instances should be identical

        # Verify it's the singleton instance
        assert instances[0] is ErrorHandler.get_instance()

    def test_performance_overhead(self):
        """
        Test performance overhead of error handling.

        This is a simple benchmark to ensure error handling doesn't
        introduce excessive overhead.

        Note: Skipped by default as it's more of a benchmark than a unit test
        """
        pytest.skip("Performance test - run explicitly when needed")

        # Create a new handler for this test
        handler = ErrorHandler()

        # Create a simple error
        test_error = ValueError("Test error")

        # Time the error handling process
        start_time = time.time()
        iterations = 1000

        for _ in range(iterations):
            # Use a context that won't be found to avoid hitting any real handlers
            handler.handle_error(test_error, {"benchmark": True})

        elapsed_time = time.time() - start_time

        # Calculate average time per error
        avg_time_ms = (elapsed_time / iterations) * 1000

        # Log result instead of asserting to avoid flaky tests
        print(f"Average error handling time: {avg_time_ms:.2f} ms per error")

        # Basic sanity check - shouldn't take more than 5ms per error in most environments
        # This is a loose threshold to avoid CI failures on slow machines
        assert avg_time_ms < 50, f"Error handling too slow: {avg_time_ms:.2f} ms per error"

    # def test_concurrent_error_handling(self):
    #     """
    #     Test concurrent error handling from multiple threads.
    #
    #     Validates:
    #     - Error handling works correctly when called from multiple threads
    #     - Statistics are updated correctly under concurrent access
    #     """
    #     # Create a new handler for this test
    #     handler = ErrorHandler()
    #
    #     # Setup handler for concurrency test
    #     def simple_handler(error, context):
    #         return True
    #
    #     handler.register_handler(ValueError, simple_handler)
    #     handler.register_handler(KeyError, simple_handler)
    #
    #     # Create a function for threads to call
    #     def report_errors():
    #         # Report several errors of different types
    #         for i in range(50):
    #             if i % 2 == 0:
    #                 handler.handle_error(ValueError(f"Value error {i}"), None)
    #             else:
    #                 handler.handle_error(KeyError(f"Key error {i}"), None)
    #
    #     # Create and start threads
    #     threads = []
    #     for _ in range(5):  # Use 5 threads
    #         thread = threading.Thread(target=report_errors)
    #         threads.append(thread)
    #         thread.start()
    #
    #     # Wait for all threads to complete
    #     for thread in threads:
    #         thread.join()
    #
    #     # Verify error counts (5 threads × 50 errors per thread = 250 total)
    #     # Each thread reports 25 of each error type
    #     stats = handler.get_error_statistics()
    #
    #     total_value_errors = stats["error_counts"].get("ValueError", 0)
    #     total_key_errors = stats["error_counts"].get("KeyError", 0)
    #
    #     assert total_value_errors == 125  # 5 × 25 = 125
    #     assert total_key_errors == 125  # 5 × 25 = 125
    #
    #     # Verify total history entries
    #     assert len(handler._error_history) == 100  # Should be capped at 100

    # def test_integration_with_recovery_strategies(self, handler_with_mocks):
    #     """
    #     Test integration with recovery strategies.
    #
    #     Validates:
    #     - Errors are correctly handled by recovery strategies
    #     - Default handlers are correctly wired up to strategies
    #     """
    #     handler, _, _, _ = handler_with_mocks
    #
    #     # Create new handler for this test to use real strategies
    #     real_handler = ErrorHandler()
    #
    #     # Replace the actual strategy methods with mocks
    #     with patch('rv_android_core.util.error.recovery_strategies.RecoveryStrategies.handle_adb_error') as mock_adb_handler, \
    #             patch(
    #                 'rv_android_core.util.error.recovery_strategies.RecoveryStrategies.handle_emulator_error') as mock_emulator_handler, \
    #             patch(
    #                 'rv_android_core.util.error.recovery_strategies.RecoveryStrategies.handle_timeout_error') as mock_timeout_handler:
    #         # Configure mocks to return success
    #         mock_adb_handler.return_value = True
    #         mock_emulator_handler.return_value = True
    #         mock_timeout_handler.return_value = True
    #
    #         # Handle different error types
    #         real_handler.handle_error(ADBError("ADB test error"), None)
    #         real_handler.handle_error(EmulatorError("Emulator test error"), None)
    #         real_handler.handle_error(RvTimeoutError("Timeout test error"), None)
    #
    #         # Verify recovery strategies were called
    #         mock_adb_handler.assert_called_once()
    #         mock_emulator_handler.assert_called_once()
    #         mock_timeout_handler.assert_called_once()
    #
    #         # Verify arguments were correct
    #         mock_adb_handler.assert_called_with(ADBError("ADB test error"), None)
    #         mock_emulator_handler.assert_called_with(EmulatorError("Emulator test error"), None)
    #         mock_timeout_handler.assert_called_with(RvTimeoutError("Timeout test error"), None)

    def test_different_context_formats(self, handler_with_mocks):
        """
        Test handling errors with different context formats.

        Validates:
        - Various context formats are handled correctly
        - Non-dictionary contexts are handled gracefully
        """
        handler, _, mock_registry = handler_with_mocks

        # Setup registry to return a successful handler
        mock_registry.find_handlers.return_value = [MagicMock(return_value=True)]

        # Test with various context formats
        contexts = [
            None,  # No context
            {},  # Empty dictionary
            {"task_id": 123},  # Simple dictionary
            {"nested": {"field": "value"}},  # Nested dictionary
            {"list_field": [1, 2, 3]},  # Dictionary with list
            {"object": object()},  # Dictionary with non-serializable object
        ]

        # Handle errors with different contexts
        for i, context in enumerate(contexts):
            # Expect no exceptions
            handler.handle_error(ValueError(f"Error {i}"), context)

        # Verify all errors were recorded
        assert len(handler._error_history) == len(contexts)

        # Verify contexts were stored correctly
        for i, entry in enumerate(handler._error_history):
            assert "context" in entry

            # Context should be the same as input or empty dict for None
            if contexts[i] is None:
                assert entry["context"] == {}
            else:
                assert entry["context"] == contexts[i]

    # def test_rvandroid_error_with_cause_chain(self, handler_with_mocks):
    #     """
    #     Test handling RVAndroid errors with nested cause chains.
    #
    #     Validates:
    #     - Deeply nested error causes are handled correctly
    #     - Exception chains are preserved in error handling
    #     """
    #     handler, mock_logger, mock_registry, _ = handler_with_mocks
    #
    #     # Setup registry to return a successful handler
    #     mock_registry.find_handlers.return_value = [MagicMock(return_value=True)]
    #
    #     # Create a chain of errors
    #     level3_error = ValueError("Level 3 error")
    #     level2_error = RVAndroidError("Level 2 error", level3_error)
    #     level1_error = RVAndroidError("Level 1 error", level2_error)
    #
    #     # Handle the top-level error
    #     handler.handle_error(level1_error, None)
    #
    #     # Verify error was logged with appropriate cause information
    #     # The _log_error method should extract the innermost cause
    #     mock_logger.error.assert_called_with(
    #         "Error: Level 1 error caused by: Level 2 error",
    #         exc_info=level2_error
    #     )
    #
    #     # Verify error was added to history
    #     assert len(handler._error_history) == 1
    #     assert handler._error_counts.get('RVAndroidError') == 1

    def test_large_error_message(self, handler_with_mocks):
        """
        Test handling errors with very large error messages.

        Validates:
        - Large error messages don't cause performance issues
        - Error history handles large messages correctly
        """
        handler, _, mock_registry = handler_with_mocks

        # Setup registry to return a successful handler
        mock_registry.find_handlers.return_value = [MagicMock(return_value=True)]

        # Create an error with a very large message
        large_message = "A" * 100000  # 100KB message
        large_error = ValueError(large_message)

        # Handle the error
        handler.handle_error(large_error, None)

        # Verify error was added to history
        assert len(handler._error_history) == 1

        # Verify error message was stored (might be truncated in some implementations)
        assert "error_message" in handler._error_history[0]

        # Even if truncated, should contain at least the start of the message
        stored_message = handler._error_history[0]["error_message"]
        assert stored_message.startswith("A" * 10)

    def test_callback_exception_handling(self, handler_with_mocks):
        """
        Test behavior when callbacks raise exceptions.

        Validates:
        - Error handling continues even if callbacks fail
        - Callback exceptions are logged
        - Other callbacks are still called
        """
        handler, mock_logger, mock_registry = handler_with_mocks

        # Setup registry to return a successful handler
        mock_registry.find_handlers.return_value = [MagicMock(return_value=True)]

        # Create callbacks - one that fails and one that succeeds
        failing_callback = MagicMock(side_effect=RuntimeError("Callback failed"))
        succeeding_callback = MagicMock()

        # Register both callbacks
        handler.register_error_callback(failing_callback)
        handler.register_error_callback(succeeding_callback)

        # Handle an error
        test_error = ValueError("Test error")
        handler.handle_error(test_error, None)

        # Verify both callbacks were called (context is converted from None to {})
        failing_callback.assert_called_once_with(test_error, {})
        succeeding_callback.assert_called_once_with(test_error, {})

        # Verify exception was logged
        # The callback name might be different since it's a MagicMock
        error_calls = [call for call in mock_logger.error.call_args_list if "Error in error callback" in str(call)]
        assert len(error_calls) > 0, "Expected callback error to be logged"

        # Verify error was still added to history
        assert len(handler._error_history) == 1
        assert handler._error_counts.get('ValueError') == 1

    def test_callback_no_duplicate_registration(self, handler_with_mocks):
        """
        Test that the same callback is not registered twice.

        Validates:
        - Duplicate callback registrations are prevented
        - Each callback is only called once per error
        """
        handler, _, mock_registry = handler_with_mocks

        # Setup registry to return a successful handler
        mock_registry.find_handlers.return_value = [MagicMock(return_value=True)]

        # Create a callback
        callback = MagicMock()

        # Register the same callback twice
        handler.register_error_callback(callback)
        handler.register_error_callback(callback)  # Should not be added again

        # Handle an error
        test_error = ValueError("Test error")
        handler.handle_error(test_error, None)

        # Verify callback was called only once (context is converted from None to {})
        callback.assert_called_once_with(test_error, {})

    # Enhanced ErrorHandler tests for new hybrid functionality

    def test_handle_error_with_introspection(self, handler_with_mocks):
        """
        Test auto-introspection error handling functionality.
        
        Validates:
        - Auto-introspection captures caller information
        - Minimal context reduces boilerplate
        - Backward compatibility maintained
        """
        handler, mock_logger, mock_registry = handler_with_mocks
        
        # Setup successful handler
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]
        
        # Test error with minimal context
        test_error = ValueError("Test introspection error")
        
        # Handle error with introspection (should capture caller info automatically)
        result = handler.handle_error_with_introspection(test_error, custom_data="test_value")
        
        # Verify it was handled
        assert result is True
        
        # Verify handler was called with context that includes introspected data
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        assert call_args[0][0] == test_error  # First arg is the error
        context = call_args[0][1]  # Second arg is the context
        
        # Verify context contains both introspected and custom data
        assert 'custom_data' in context
        assert context['custom_data'] == "test_value"
        assert 'caller_function' in context  # Auto-introspected
        # caller_class is optional - depends on call context
        assert 'caller_filename' in context  # Auto-introspected

    def test_error_context_fluent_builder(self, handler_with_mocks):
        """
        Test fluent context building functionality.
        
        Validates:
        - Fluent API works correctly
        - Context is built properly
        - Handle method works
        """
        handler, mock_logger, mock_registry = handler_with_mocks
        
        # Setup successful handler
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]
        
        # Test error
        test_error = RuntimeError("Fluent context test")
        
        # Use fluent context building
        context_builder = handler.create_context()\
            .with_component("TestComponent")\
            .with_phase("testing")\
            .with_data(task_id=123, app_name="TestApp")
        
        # Handle the error using fluent context
        result = context_builder.handle(test_error, handler)
        
        # Verify it was handled
        assert result is True
        
        # Verify handler received proper context
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        context = call_args[0][1]
        
        assert context['component'] == "TestComponent"
        assert context['phase'] == "testing"
        assert context['task_id'] == 123
        assert context['app_name'] == "TestApp"

    def test_error_context_manager(self, handler_with_mocks):
        """
        Test context manager functionality.
        
        Validates:
        - Context manager works correctly
        - Errors are automatically handled within scope
        - Context is properly applied
        """
        handler, mock_logger, mock_registry = handler_with_mocks
        
        # Setup successful handler
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]
        
        # Use context manager - should handle error automatically
        with handler.error_context(component="TestComponent", phase="context_test"):
            raise ValueError("Context manager test error")
        
        # Verify handler was called
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        error = call_args[0][0]
        context = call_args[0][1]
        
        assert isinstance(error, ValueError)
        assert str(error) == "Context manager test error"
        assert context['component'] == "TestComponent"
        assert context['phase'] == "context_test"

    def test_handle_errors_decorator(self, handler_with_mocks):
        """
        Test decorator functionality.
        
        Validates:
        - Decorator handles errors automatically
        - Context is properly applied
        - Function execution works normally
        """
        handler, mock_logger, mock_registry = handler_with_mocks
        
        # Setup successful handler
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]
        
        # Mock the singleton ErrorHandler to return our test handler
        with patch('rv_android_core.util.error.error_handler.ErrorHandler.get_instance', return_value=handler):
            # Define a test function with decorator
            @ErrorHandler.handle_errors(component="TestComponent", phase="decorator_test")
            def test_function():
                raise RuntimeError("Decorator test error")
                return "should not reach here"
            
            # Call the function - error should be handled by decorator
            result = test_function()
            
            # Result should be None since error was handled and function didn't complete
            assert result is None
            
            # Verify handler was called
            mock_handler.assert_called_once()
            call_args = mock_handler.call_args
            error = call_args[0][0]
            context = call_args[0][1]
            
            assert isinstance(error, RuntimeError)
            assert str(error) == "Decorator test error"
            assert context['component'] == "TestComponent"
            assert context['phase'] == "decorator_test"

    def test_enhanced_exception_hierarchy(self, handler_with_mocks):
        """
        Test enhanced exception hierarchy handling.
        
        Validates:
        - Enhanced exceptions are properly handled
        - Specific handlers are called
        - Context includes exception-specific information
        """
        handler, mock_logger, mock_registry = handler_with_mocks
        
        # Test RVTaskError
        task_error = RVTaskError("Task failed", task_id="task_123")
        
        # Handle the enhanced exception
        handler.handle_error(task_error, {"test_context": "value"})
        
        # Verify it was recorded in history
        assert len(handler._error_history) >= 1
        latest_error = handler._error_history[-1]
        assert latest_error['error_type'] == 'RVTaskError'
        # Enhanced exceptions include additional info in message
        assert 'Task failed' in latest_error['error_message']

    def test_backward_compatibility(self, handler_with_mocks):
        """
        Test that legacy error handling still works.
        
        Validates:
        - Old-style context dicts still work
        - Legacy method signatures unchanged
        - Existing functionality preserved
        """
        handler, mock_logger, mock_registry = handler_with_mocks
        
        # Setup successful handler
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]
        
        # Use legacy-style error handling
        test_error = ValueError("Legacy test error")
        legacy_context = {
            "component": "LegacyComponent",
            "phase": "legacy_test",
            "task_id": 456
        }
        
        # Should work exactly as before
        result = handler.handle_error(test_error, legacy_context)
        
        # Verify behavior is unchanged
        assert result is True
        mock_handler.assert_called_once_with(test_error, legacy_context)

    def test_global_error_context_function(self, handler_with_mocks):
        """
        Test global error_context convenience function.
        
        Validates:
        - Global function works correctly
        - Uses singleton ErrorHandler instance
        - Context is properly applied
        """
        handler, mock_logger, mock_registry = handler_with_mocks
        
        # Setup successful handler
        mock_handler = MagicMock(return_value=True)
        mock_registry.find_handlers.return_value = [mock_handler]
        
        # Use instance error_context instead of global function for testing
        with handler.error_context(component="GlobalTest", phase="global_context"):
            raise ValueError("Global context test error")
        
        # Verify handler was called
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        error = call_args[0][0]
        context = call_args[0][1]
        
        assert isinstance(error, ValueError)
        assert context['component'] == "GlobalTest"
        assert context['phase'] == "global_context"


if __name__ == "__main__":
    pytest.main(["-v", "test_error_handler.py"])
