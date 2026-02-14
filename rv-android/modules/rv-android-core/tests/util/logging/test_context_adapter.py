# tests/util/logging/test_context_adapter.py
import logging
import threading
from datetime import datetime
from unittest.mock import MagicMock, patch, ANY

import pytest

from rv_android_core.util.logging.context_adapter import ContextAdapter


class TestContextAdapter:
    """Tests for ContextAdapter class"""

    @pytest.fixture
    def mock_logger(self):
        """Fixture that provides a mock logger for testing"""
        return MagicMock(spec=logging.Logger)

    @pytest.fixture
    def context_adapter(self, mock_logger):
        """Fixture that provides a context adapter with a mock logger"""
        return ContextAdapter(mock_logger, {"test_key": "test_value"})

    def test_initialization(self, mock_logger):
        """Test that ContextAdapter is initialized correctly"""
        # Test with empty context
        adapter = ContextAdapter(mock_logger)
        assert adapter.logger == mock_logger
        assert adapter.context == {}
        assert adapter._context_stack == []

        # Test with provided context
        adapter = ContextAdapter(mock_logger, {"app": "test_app"})
        assert adapter.logger == mock_logger
        assert adapter.context == {"app": "test_app"}
        assert adapter._context_stack == []

    def test_process_adds_context(self, context_adapter):
        """Test process method adds context to kwargs"""
        msg = "Test message"
        kwargs = {}

        processed_msg, processed_kwargs = context_adapter.process(msg, kwargs)

        assert processed_msg == msg
        assert "extra" in processed_kwargs
        assert processed_kwargs["extra"]["test_key"] == "test_value"
        assert "thread_id" in processed_kwargs["extra"]
        assert "timestamp" in processed_kwargs["extra"]

    def test_process_merges_with_existing_extra(self, context_adapter):
        """Test process method merges with existing 'extra' in kwargs"""
        msg = "Test message"
        kwargs = {"extra": {"existing_key": "existing_value"}}

        processed_msg, processed_kwargs = context_adapter.process(msg, kwargs)

        assert processed_msg == msg
        assert processed_kwargs["extra"]["existing_key"] == "existing_value"
        assert processed_kwargs["extra"]["test_key"] == "test_value"

    def test_push_context(self, context_adapter):
        """Test push_context method adds a new context"""
        # Initial context
        assert context_adapter.context == {"test_key": "test_value"}

        # Push new context
        context_adapter.push_context(new_key="new_value")

        # Check that context is updated
        assert context_adapter.context == {"test_key": "test_value", "new_key": "new_value"}
        assert context_adapter._context_stack == [{"test_key": "test_value"}]

        # Push another context
        context_adapter.push_context(another_key="another_value")

        # Check that context is updated again
        assert context_adapter.context == {
            "test_key": "test_value",
            "new_key": "new_value",
            "another_key": "another_value"
        }
        assert len(context_adapter._context_stack) == 2

    def test_pop_context(self, context_adapter):
        """Test pop_context method restores previous context"""
        # Push contexts
        context_adapter.push_context(new_key="new_value")
        context_adapter.push_context(another_key="another_value")

        # Pop context
        old_context = context_adapter.pop_context()

        # Check that context is restored to previous state
        assert old_context == {
            "test_key": "test_value",
            "new_key": "new_value",
            "another_key": "another_value"
        }
        assert context_adapter.context == {"test_key": "test_value", "new_key": "new_value"}
        assert len(context_adapter._context_stack) == 1

        # Pop again
        old_context = context_adapter.pop_context()
        assert old_context == {"test_key": "test_value", "new_key": "new_value"}
        assert context_adapter.context == {"test_key": "test_value"}
        assert len(context_adapter._context_stack) == 0

    def test_pop_context_with_empty_stack(self, context_adapter):
        """Test pop_context method with empty stack"""
        # Pop from empty stack
        old_context = context_adapter.pop_context()

        # Should return empty dict and leave context unchanged
        assert old_context == {}
        assert context_adapter.context == {"test_key": "test_value"}

    def test_with_context_as_context_manager(self, context_adapter):
        """Test using with_context as a context manager"""
        # Initial context
        assert context_adapter.context == {"test_key": "test_value"}

        # Use as context manager
        with context_adapter.with_context(temp_key="temp_value"):
            # Inside context: context should be updated
            assert context_adapter.context == {"test_key": "test_value", "temp_key": "temp_value"}
            assert context_adapter._context_stack == [{"test_key": "test_value"}]

        # After context: context should be restored
        assert context_adapter.context == {"test_key": "test_value"}
        assert context_adapter._context_stack == []

    def test_nested_with_context(self, context_adapter):
        """Test nested context managers"""
        # Initial context
        assert context_adapter.context == {"test_key": "test_value"}

        # Nested context managers
        with context_adapter.with_context(level1="value1"):
            assert context_adapter.context == {"test_key": "test_value", "level1": "value1"}

            with context_adapter.with_context(level2="value2"):
                assert context_adapter.context == {
                    "test_key": "test_value",
                    "level1": "value1",
                    "level2": "value2"
                }

            # After inner context
            assert context_adapter.context == {"test_key": "test_value", "level1": "value1"}

        # After outer context
        assert context_adapter.context == {"test_key": "test_value"}

    def test_thread_id_added_to_extra(self, context_adapter):
        """Test that thread ID is added to extra"""
        msg = "Test message"
        kwargs = {}

        with patch.object(threading, 'current_thread') as mock_current_thread:
            mock_thread = MagicMock()
            mock_thread.ident = 12345
            mock_current_thread.return_value = mock_thread

            _, processed_kwargs = context_adapter.process(msg, kwargs)

            assert processed_kwargs["extra"]["thread_id"] == 12345

    def test_timestamp_added_to_extra(self, context_adapter):
        """Test that timestamp is added to extra"""
        msg = "Test message"
        kwargs = {}

        _, processed_kwargs = context_adapter.process(msg, kwargs)

        # Verify timestamp exists and has ISO format
        timestamp = processed_kwargs["extra"]["timestamp"]
        assert isinstance(timestamp, str)

        # Try parsing to verify it's a valid ISO timestamp
        try:
            datetime.fromisoformat(timestamp)
            is_valid_timestamp = True
        except ValueError:
            is_valid_timestamp = False

        assert is_valid_timestamp

    def test_enter_exit_methods(self, context_adapter):
        """Test __enter__ and __exit__ methods"""
        # Setup test context
        context_adapter.push_context(test_enter="value")

        # Test __enter__
        result = context_adapter.__enter__()
        assert result is context_adapter

        # Test __exit__
        context_adapter.__exit__(None, None, None)
        assert context_adapter.context == {"test_key": "test_value"}

    def test_exception_handling_in_context_manager(self, context_adapter):
        """Test that context is properly restored even when exception occurs"""
        try:
            with context_adapter.with_context(exception_test="value"):
                assert context_adapter.context == {"test_key": "test_value", "exception_test": "value"}
                raise ValueError("Test exception")
        except ValueError:
            # Context should be restored after exception
            assert context_adapter.context == {"test_key": "test_value"}


if __name__ == "__main__":
    pytest.main()
