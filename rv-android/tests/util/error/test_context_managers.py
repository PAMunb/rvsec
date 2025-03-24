# tests/util/error/test_context_managers.py

"""
Unit tests for the context_managers module in rv-android.

This test suite covers various scenarios for the context management utilities
that facilitate error handling in the rv-android framework.
"""

import pytest
from unittest.mock import patch, MagicMock

from rvandroid.util.exceptions import EmulatorError, RVAndroidError
from rvandroid.util.error.context_managers import handle_errors
from rvandroid.util.error.error_handler import ErrorHandler


class TestHandleErrors:
    """
    Tests for the handle_errors context manager.

    ### Architectural Testing Considerations:
    - Verify correct integration with the ErrorHandler
    - Test behavior with different exception types
    - Ensure proper context propagation
    - Validate re-raising of exceptions after handling
    """

    @pytest.fixture
    def mock_error_handler(self):
        """Fixture providing a mock error handler"""
        handler = MagicMock()
        with patch.object(ErrorHandler, 'get_instance', return_value=handler):
            yield handler

    def test_no_exception(self, mock_error_handler):
        """
        Test behavior when no exception occurs in the context.

        Validates:
        - The context manager executes without issues when no exceptions occur
        - No errors are reported to the error handler
        """
        # Use the context manager without raising an exception
        with handle_errors({"key": "value"}):
            pass  # No exception

        # Verify the handler's handle_error method was not called
        mock_error_handler.handle_error.assert_not_called()

    def test_with_exception(self, mock_error_handler):
        """
        Test behavior when an exception occurs in the context.

        Validates:
        - Exceptions are properly passed to the error handler
        - Context information is passed along with the exception
        - The original exception is re-raised after handling
        """
        # Create context dictionary
        context = {"task_id": 123, "phase": "testing"}

        # Test exception
        test_exception = ValueError("Test error")

        # Use the context manager with an exception
        with pytest.raises(ValueError) as exc_info:
            with handle_errors(context):
                raise test_exception

        # Verify the exception was re-raised properly
        assert str(exc_info.value) == "Test error"

        # Verify the handler's handle_error method was called with the correct arguments
        mock_error_handler.handle_error.assert_called_once()
        args, kwargs = mock_error_handler.handle_error.call_args
        assert isinstance(args[0], ValueError)
        assert args[1] == context

    def test_with_none_context(self, mock_error_handler):
        """
        Test behavior when context is None.

        Validates:
        - The context manager works correctly with None as context
        - ErrorHandler receives None as the context
        """
        # Test exception
        test_exception = RuntimeError("No context error")

        # Use the context manager with None context
        with pytest.raises(RuntimeError):
            with handle_errors(None):
                raise test_exception

        # Verify the handler's handle_error method was called with None context
        mock_error_handler.handle_error.assert_called_once()
        args, kwargs = mock_error_handler.handle_error.call_args
        assert isinstance(args[0], RuntimeError)
        assert args[1] is None

    def test_with_nested_contexts(self, mock_error_handler):
        """
        Test behavior with nested context managers.

        Validates:
        - Nested contexts work correctly
        - Each context's information is properly passed to the handler
        - Inner exceptions don't affect outer contexts
        """
        # Create context dictionaries
        outer_context = {"scope": "outer", "id": 1}
        inner_context = {"scope": "inner", "id": 2}

        # Test with nested contexts and exceptions in both
        try:
            with handle_errors(outer_context):
                # Some code in outer context
                try:
                    with handle_errors(inner_context):
                        # Inner context raises an exception
                        raise ValueError("Inner error")
                except ValueError:
                    # After inner exception is handled and re-raised
                    # Outer context raises its own exception
                    raise KeyError("Outer error")
        except KeyError:
            pass  # Expected to catch the re-raised outer exception

        # Verify both exceptions were handled with their respective contexts
        assert mock_error_handler.handle_error.call_count == 2

        # Check that both calls were made with appropriate contexts
        call_contexts = [call[0][1] for call in mock_error_handler.handle_error.call_args_list]
        assert inner_context in call_contexts
        assert outer_context in call_contexts

    def test_with_various_exception_types(self, mock_error_handler):
        """
        Test handling of various exception types.

        Validates:
        - Different exception types are all handled correctly
        - System, standard library, and custom exceptions all work
        """
        # Create context dictionary
        context = {"phase": "testing_exceptions"}

        # Define a list of different exception types to test
        exceptions = [
            ValueError("Value error"),
            KeyError("Key error"),
            TypeError("Type error"),
            OSError("OS error"),
            EmulatorError("Emulator error", None),
            RVAndroidError("RV-Android error", None),
            Exception("Generic exception"),
            ZeroDivisionError("Division by zero"),
            IndexError("Index out of range"),
        ]

        # Test each exception type
        for exception in exceptions:
            mock_error_handler.reset_mock()  # Reset call history

            # Use the context manager with the current exception
            with pytest.raises(type(exception)):
                with handle_errors(context):
                    raise exception

            # Verify the handler's handle_error method was called with the correct arguments
            mock_error_handler.handle_error.assert_called_once_with(exception, context)
