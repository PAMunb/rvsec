# tests/experiment/event/test_bus_core.py
"""
Core unit tests for the EventBus class.

These tests verify the basic functionality of the EventBus including
initialization, subscription management, event publishing, and
singleton behavior.
"""

from unittest.mock import MagicMock

import pytest

from rv_android_core.event.bus import EventBus
from rv_android_core.event.models import Event, EventType, EventChannel


class TestEventBusCore:
    """Core tests for the EventBus class."""

    def setup_method(self):
        """Set up test environment before each test method."""
        # Clear the singleton instance to ensure test isolation
        EventBus._instance = None
        EventBus._lock = MagicMock()

        # Create a clean instance for testing
        self.event_bus = EventBus()

        # Mock the logger
        self.event_bus.logger = MagicMock()

    def test_singleton_pattern(self):
        """Test that get_instance returns the same instance each time."""
        # Arrange & Act
        instance1 = EventBus.get_instance()
        instance2 = EventBus.get_instance()

        # Assert
        assert instance1 is instance2

    def test_create_instance(self):
        """Test that create_instance creates a new independent instance."""
        # Arrange
        singleton = EventBus.get_instance()

        # Act
        new_instance = EventBus.create_instance()

        # Assert
        assert new_instance is not singleton
        assert isinstance(new_instance, EventBus)


    def test_subscribe(self):
        """Test subscribing to an event type."""
        # Arrange
        callback = MagicMock()

        # Act
        handler_id = self.event_bus.subscribe(
            EventType.TASK_STARTED,
            callback
        )

        # Assert
        assert handler_id is not None

        # Check that the handler was added
        handlers = self.event_bus.channel_subscribers[EventChannel.DEFAULT.value][EventType.TASK_STARTED]
        assert len(handlers) == 1
        assert handlers[0].callback == callback
        assert handlers[0].filter_fn is None

    def test_subscribe_with_filter(self):
        """Test subscribing with a filter function."""
        # Arrange
        callback = MagicMock()
        filter_fn = lambda event: event.source == "test"

        # Act
        handler_id = self.event_bus.subscribe(
            EventType.TASK_STARTED,
            callback,
            filter_fn=filter_fn,
            channel=EventChannel.LIFECYCLE
        )

        # Assert
        handlers = self.event_bus.channel_subscribers[EventChannel.LIFECYCLE.value][EventType.TASK_STARTED]
        assert len(handlers) == 1
        assert handlers[0].callback == callback
        assert handlers[0].filter_fn == filter_fn

    def test_subscribe_many(self):
        """Test subscribing to multiple event types at once."""
        # Arrange
        callback = MagicMock()
        event_types = [EventType.TASK_STARTED, EventType.EXPERIMENT_COMPLETED]

        # Act
        handler_ids = self.event_bus.subscribe_many(event_types, callback)

        # Assert
        assert len(handler_ids) == 2

        # Check that handlers were added for both event types
        handlers1 = self.event_bus.channel_subscribers[EventChannel.DEFAULT.value][EventType.TASK_STARTED]
        handlers2 = self.event_bus.channel_subscribers[EventChannel.DEFAULT.value][EventType.EXPERIMENT_COMPLETED]

        assert len(handlers1) == 1
        assert len(handlers2) == 1
        assert handlers1[0].callback == callback
        assert handlers2[0].callback == callback

    def test_unsubscribe_by_handler(self):
        """Test unsubscribing by handler ID."""
        # Arrange
        callback = MagicMock()
        handler_id = self.event_bus.subscribe(EventType.TASK_STARTED, callback)

        # Act
        result = self.event_bus.unsubscribe_by_handler(
            EventType.TASK_STARTED,
            handler_id
        )

        # Assert
        assert result is True
        handlers = self.event_bus.channel_subscribers[EventChannel.DEFAULT.value][EventType.TASK_STARTED]
        assert len(handlers) == 0

    def test_unsubscribe_by_handler_invalid_id(self):
        """Test unsubscribing with an invalid handler ID."""
        # Arrange
        callback = MagicMock()
        self.event_bus.subscribe(EventType.TASK_STARTED, callback)

        # Act
        result = self.event_bus.unsubscribe_by_handler(
            EventType.TASK_STARTED,
            9999  # Non-existent ID
        )

        # Assert
        assert result is False
        handlers = self.event_bus.channel_subscribers[EventChannel.DEFAULT.value][EventType.TASK_STARTED]
        assert len(handlers) == 1

    def test_unsubscribe_all(self):
        """Test unsubscribing all instances of a callback."""
        # Arrange
        callback = MagicMock()
        callback2 = MagicMock()

        # Subscribe callback to multiple event types and channels
        self.event_bus.subscribe(EventType.TASK_STARTED, callback)
        self.event_bus.subscribe(EventType.EXPERIMENT_COMPLETED, callback)
        self.event_bus.subscribe(
            EventType.TASK_COMPLETED,
            callback,
            channel=EventChannel.LIFECYCLE
        )
        self.event_bus.subscribe(EventType.TASK_FAILED, callback2)

        # Act
        count = self.event_bus.unsubscribe_all(callback)

        # Assert
        assert count == 3

        # Check that only callback2 remains
        handlers = self.event_bus.channel_subscribers[EventChannel.DEFAULT.value][EventType.TASK_FAILED]
        assert len(handlers) == 1
        assert handlers[0].callback == callback2

        # Check that all handlers for callback were removed
        assert len(self.event_bus.channel_subscribers[EventChannel.DEFAULT.value][EventType.TASK_STARTED]) == 0
        assert len(self.event_bus.channel_subscribers[EventChannel.DEFAULT.value][EventType.EXPERIMENT_COMPLETED]) == 0
        assert len(self.event_bus.channel_subscribers[EventChannel.LIFECYCLE.value][EventType.TASK_COMPLETED]) == 0

    def test_unsubscribe_all_specific_channels(self):
        """Test unsubscribing a callback from specific channels only."""
        # Arrange
        callback = MagicMock()

        # Subscribe callback to multiple channels
        self.event_bus.subscribe(
            EventType.TASK_STARTED,
            callback,
            channel=EventChannel.LIFECYCLE
        )
        self.event_bus.subscribe(
            EventType.TASK_COMPLETED,
            callback,
            channel=EventChannel.LIFECYCLE
        )
        self.event_bus.subscribe(
            EventType.COVERAGE_UPDATED,
            callback,
            channel=EventChannel.ANALYSIS
        )

        # Act
        count = self.event_bus.unsubscribe_all(
            callback,
            channels=[EventChannel.LIFECYCLE]
        )

        # Assert
        assert count == 2

        # Check that only the ANALYSIS_CHANNEL handler remains
        handlers = self.event_bus.channel_subscribers[EventChannel.ANALYSIS.value][EventType.COVERAGE_UPDATED]
        assert len(handlers) == 1

    def test_publish_basic(self):
        """Test basic event publishing."""
        # Arrange
        callback = MagicMock()
        self.event_bus.subscribe(EventType.TASK_STARTED, callback)

        event = Event(type=EventType.TASK_STARTED, source="test")

        # Act
        count = self.event_bus.publish(event)

        # Assert
        assert count == 1
        callback.assert_called_once_with(event)


if __name__ == "__main__":
    pytest.main(["-v"])
