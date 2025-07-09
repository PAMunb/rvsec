# tests/experiment/event/test_handler.py
"""
Unit tests for the EventHandler class.

These tests verify the behavior of the event handler including filtering capabilities,
callback execution, and error handling. The EventHandler is a critical component
in the event-driven architecture of the RV-Android framework.
"""

import pytest
from unittest.mock import MagicMock, call

from rv_android_core.event.handler import EventHandler
from rv_android_core.event.models import Event, EventType


class TestEventHandler:
    """Tests for the EventHandler class."""

    def test_initialization(self):
        """Test that the EventHandler is initialized correctly."""
        # Arrange
        callback = MagicMock()
        filter_fn = MagicMock()

        # Act
        handler = EventHandler(callback, filter_fn)

        # Assert
        assert handler.callback == callback
        assert handler.filter_fn == filter_fn

    def test_initialization_without_filter(self):
        """Test that the EventHandler can be initialized without a filter function."""
        # Arrange
        callback = MagicMock()

        # Act
        handler = EventHandler(callback)

        # Assert
        assert handler.callback == callback
        assert handler.filter_fn is None

    def test_handle_with_matching_filter(self):
        """Test handling an event that matches the filter."""
        # Arrange
        callback = MagicMock()
        filter_fn = MagicMock(return_value=True)
        handler = EventHandler(callback, filter_fn)

        mock_event = MagicMock(spec=Event)
        mock_event.type = EventType.EXPERIMENT_STARTED

        # Act
        result = handler.handle(mock_event)

        # Assert
        assert result is True
        filter_fn.assert_called_once_with(mock_event)
        callback.assert_called_once_with(mock_event)

    def test_handle_with_non_matching_filter(self):
        """Test handling an event that doesn't match the filter."""
        # Arrange
        callback = MagicMock()
        filter_fn = MagicMock(return_value=False)
        handler = EventHandler(callback, filter_fn)

        mock_event = MagicMock(spec=Event)
        mock_event.type = EventType.EXPERIMENT_STARTED

        # Act
        result = handler.handle(mock_event)

        # Assert
        assert result is False
        filter_fn.assert_called_once_with(mock_event)
        callback.assert_not_called()

    def test_handle_without_filter(self):
        """Test handling an event without a filter function."""
        # Arrange
        callback = MagicMock()
        handler = EventHandler(callback)

        mock_event = MagicMock(spec=Event)
        mock_event.type = EventType.EXPERIMENT_STARTED

        # Act
        result = handler.handle(mock_event)

        # Assert
        assert result is True
        callback.assert_called_once_with(mock_event)

    def test_handle_with_exception_in_callback(self):
        """Test behavior when the callback raises an exception."""
        # Arrange
        callback = MagicMock(side_effect=Exception("Test exception"))
        handler = EventHandler(callback)

        mock_event = MagicMock(spec=Event)
        mock_event.type = EventType.EXPERIMENT_STARTED

        # Act & Assert
        with pytest.raises(Exception, match="Test exception"):
            handler.handle(mock_event)

        callback.assert_called_once_with(mock_event)

    def test_handle_with_multiple_events(self):
        """Test handling multiple events with the same handler."""
        # Arrange
        callback = MagicMock()
        handler = EventHandler(callback)

        mock_event1 = MagicMock(spec=Event)
        mock_event1.type = EventType.EXPERIMENT_STARTED

        mock_event2 = MagicMock(spec=Event)
        mock_event2.type = EventType.EXPERIMENT_COMPLETED

        # Act
        result1 = handler.handle(mock_event1)
        result2 = handler.handle(mock_event2)

        # Assert
        assert result1 is True
        assert result2 is True

        callback.assert_has_calls([
            call(mock_event1),
            call(mock_event2)
        ])

    def test_handle_with_complex_filter(self):
        """Test handling an event with a complex filter function."""
        # Arrange
        callback = MagicMock()

        # Filter that only accepts events with a specific source
        def complex_filter(event):
            return hasattr(event, 'source') and event.source == 'test_source'

        handler = EventHandler(callback, complex_filter)

        # Create events with different sources
        matching_event = MagicMock(spec=Event)
        matching_event.type = EventType.EXPERIMENT_STARTED
        matching_event.source = 'test_source'

        non_matching_event = MagicMock(spec=Event)
        non_matching_event.type = EventType.EXPERIMENT_STARTED
        non_matching_event.source = 'other_source'

        # Act
        result1 = handler.handle(matching_event)
        result2 = handler.handle(non_matching_event)

        # Assert
        assert result1 is True
        assert result2 is False

        callback.assert_called_once_with(matching_event)

    def test_handle_with_type_specific_events(self):
        """Test handling events with different concrete event types."""
        # Arrange
        callback = MagicMock()
        handler = EventHandler(callback)

        # Create different types of events from the event hierarchy
        from rv_android_core.event.models import TaskEvent, ExperimentEvent

        task_event = TaskEvent(
            type=EventType.TASK_STARTED,
            task_id="1",
            task_config={"timeout": 60}
        )

        experiment_event = ExperimentEvent(
            type=EventType.EXPERIMENT_STARTED,
            experiment_id="test-exp-1",
            message="Experiment started"
        )


        # Act
        handler.handle(task_event)
        handler.handle(experiment_event)

        # Assert
        assert callback.call_count == 2
        callback.assert_has_calls([
            call(task_event),
            call(experiment_event)
        ])

    def test_handle_with_filter_exception(self):
        """Test behavior when the filter function raises an exception."""
        # Arrange
        callback = MagicMock()
        filter_fn = MagicMock(side_effect=Exception("Filter exception"))
        handler = EventHandler(callback, filter_fn)

        mock_event = MagicMock(spec=Event)
        mock_event.type = EventType.EXPERIMENT_STARTED

        # Act & Assert
        with pytest.raises(Exception, match="Filter exception"):
            handler.handle(mock_event)

        filter_fn.assert_called_once_with(mock_event)
        callback.assert_not_called()


if __name__ == "__main__":
    pytest.main(["-v", "test_handler.py"])
    