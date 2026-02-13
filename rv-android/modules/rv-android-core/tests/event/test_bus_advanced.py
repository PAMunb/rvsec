# tests/experiment/event/test_bus_advanced.py
"""
Advanced unit tests for the EventBus class.

These tests verify more complex scenarios including handler exceptions
and event filtering. They ensure the EventBus provides robust event
handling even in edge cases.
"""

from unittest.mock import MagicMock

from rv_android_core.event.bus import EventBus
from rv_android_core.event.models import Event, EventType


class TestEventBusAdvanced:
    """Advanced tests for the EventBus class."""

    def setup_method(self):
        """Set up test environment before each test method."""
        # Clear the singleton instance to ensure test isolation
        EventBus._instance = None
        EventBus._lock = MagicMock()

        # Create a clean instance for testing
        self.event_bus = EventBus()

        # Mock the logger
        self.event_bus.logger = MagicMock()

    def test_handler_exception(self):
        """Test behavior when a handler raises an exception."""
        # Arrange
        callback = MagicMock(side_effect=Exception("Test exception"))
        self.event_bus.subscribe(EventType.TASK_STARTED, callback)

        event = Event(type=EventType.TASK_STARTED, source="test")

        # Act
        count = self.event_bus.publish(event)

        # Assert
        assert count == 0  # No successful handlers
        assert self.event_bus.logger.error.called

    def test_multiple_handlers_one_exception(self):
        """Test that one failing handler doesn't prevent others from executing."""
        # Arrange
        callback1 = MagicMock(side_effect=Exception("Test exception"))
        callback2 = MagicMock()

        self.event_bus.subscribe(EventType.TASK_STARTED, callback1)
        self.event_bus.subscribe(EventType.TASK_STARTED, callback2)

        event = Event(type=EventType.TASK_STARTED, source="test")

        # Act
        count = self.event_bus.publish(event)

        # Assert
        assert count == 1  # One successful handler
        callback1.assert_called_once_with(event)
        callback2.assert_called_once_with(event)
        assert self.event_bus.logger.error.called

    def test_filter_matching(self):
        """Test that a filter function can select specific events."""
        # Arrange
        callback = MagicMock()

        # Filter that accepts only events with source="test_source"
        def filter_fn(event):
            return event.source == "test_source"

        self.event_bus.subscribe(EventType.TASK_STARTED, callback, filter_fn)

        # Create events with different sources
        event1 = Event(type=EventType.TASK_STARTED, source="test_source")
        event2 = Event(type=EventType.TASK_STARTED, source="other_source")

        # Act
        count1 = self.event_bus.publish(event1)
        count2 = self.event_bus.publish(event2)

        # Assert
        assert count1 == 1
        assert count2 == 0
        callback.assert_called_once_with(event1)
