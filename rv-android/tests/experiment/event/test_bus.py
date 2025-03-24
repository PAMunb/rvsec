# tests/experiment/event/test_bus.py
"""
Unit tests for the EventBus class.

These tests verify the functionality of the event bus system, including
subscription management, event publishing, and event history tracking.
The EventBus is a critical component in the event-driven architecture
of the RV-Android framework, enabling decoupled communication across
system components.
"""

from unittest.mock import MagicMock

from rvandroid.experiment.event.bus import EventBus
from rvandroid.experiment.event.models import (
    Event, EventType
)


class TestEventBus:
    """Tests for the EventBus class."""

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
        """Test that EventBus implements the singleton pattern correctly."""
        # Act
        instance1 = EventBus.get_instance()
        instance2 = EventBus.get_instance()

        # Assert
        assert instance1 is instance2
        assert isinstance(instance1, EventBus)

    def test_initialization(self):
        """Test that EventBus initializes correctly."""
        # Assert
        assert hasattr(self.event_bus, 'subscribers')
        assert hasattr(self.event_bus, 'history')
        assert self.event_bus.max_history_size > 0

        # Verify subscribers map has entries for all event types
        for event_type in EventType:
            assert event_type in self.event_bus.subscribers
            assert isinstance(self.event_bus.subscribers[event_type], list)

    def test_subscribe(self):
        """Test that subscribing to an event works correctly."""
        # Arrange
        callback = MagicMock()
        event_type = EventType.EXPERIMENT_STARTED

        # Act
        handler_id = self.event_bus.subscribe(event_type, callback)

        # Assert
        assert len(self.event_bus.subscribers[event_type]) == 1
        assert isinstance(handler_id, int)
        assert self.event_bus.logger.debug.called

    def test_subscribe_with_filter(self):
        """Test subscribing with a filter function."""
        # Arrange
        callback = MagicMock()
        filter_fn = MagicMock()
        event_type = EventType.EXPERIMENT_STARTED

        # Act
        handler_id = self.event_bus.subscribe(event_type, callback, filter_fn)

        # Assert
        assert len(self.event_bus.subscribers[event_type]) == 1
        handler = self.event_bus.subscribers[event_type][0]
        assert handler.callback == callback
        assert handler.filter_fn == filter_fn

    def test_subscribe_many(self):
        """Test subscribing to multiple event types at once."""
        # Arrange
        callback = MagicMock()
        event_types = [EventType.EXPERIMENT_STARTED, EventType.EXPERIMENT_COMPLETED]

        # Act
        handler_ids = self.event_bus.subscribe_many(event_types, callback)

        # Assert
        assert len(handler_ids) == 2
        assert len(self.event_bus.subscribers[event_types[0]]) == 1
        assert len(self.event_bus.subscribers[event_types[1]]) == 1

    def test_unsubscribe_by_handler(self):
        """Test unsubscribing by handler ID."""
        # Arrange
        callback = MagicMock()
        event_type = EventType.EXPERIMENT_STARTED
        handler_id = self.event_bus.subscribe(event_type, callback)

        # Act
        result = self.event_bus.unsubscribe_by_handler(event_type, handler_id)

        # Assert
        assert result is True
        assert len(self.event_bus.subscribers[event_type]) == 0

    def test_unsubscribe_by_handler_nonexistent(self):
        """Test unsubscribing with a non-existent handler ID."""
        # Arrange
        event_type = EventType.EXPERIMENT_STARTED

        # Act
        result = self.event_bus.unsubscribe_by_handler(event_type, 12345)

        # Assert
        assert result is False

    def test_unsubscribe_all(self):
        """Test unsubscribing a callback from all event types."""
        # Arrange
        callback = MagicMock()
        # Subscribe to multiple event types
        self.event_bus.subscribe(EventType.EXPERIMENT_STARTED, callback)
        self.event_bus.subscribe(EventType.EXPERIMENT_COMPLETED, callback)
        self.event_bus.subscribe(EventType.TASK_STARTED, callback)

        # Act
        count = self.event_bus.unsubscribe_all(callback)

        # Assert
        assert count == 3
        assert len(self.event_bus.subscribers[EventType.EXPERIMENT_STARTED]) == 0
        assert len(self.event_bus.subscribers[EventType.EXPERIMENT_COMPLETED]) == 0
        assert len(self.event_bus.subscribers[EventType.TASK_STARTED]) == 0

    def test_publish_valid_event(self):
        """Test publishing a valid event."""
        # Arrange
        callback = MagicMock()
        event_type = EventType.EXPERIMENT_STARTED
        self.event_bus.subscribe(event_type, callback)

        event = Event(type=event_type, source="test")

        # Act
        count = self.event_bus.publish(event)

        # Assert
        assert count == 1
        callback.assert_called_once_with(event)
        assert len(self.event_bus.history) == 1
        assert self.event_bus.history[0] == event

    def test_publish_invalid_event(self):
        """Test publishing an invalid event object."""
        # Arrange
        callback = MagicMock()
        event_type = EventType.EXPERIMENT_STARTED
        self.event_bus.subscribe(event_type, callback)

        # Act
        count = self.event_bus.publish("not an event object")

        # Assert
        assert count == 0
        callback.assert_not_called()
        assert self.event_bus.logger.error.called

    def test_publish_no_subscribers(self):
        """Test publishing an event with no subscribers."""
        # Arrange
        event = Event(type=EventType.EXPERIMENT_STARTED, source="test")

        # Act
        count = self.event_bus.publish(event)

        # Assert
        assert count == 0
        assert len(self.event_bus.history) == 1

    def test_history_size_limit(self):
        """Test that the event history is limited to max_history_size."""
        # Arrange
        original_limit = self.event_bus.max_history_size
        self.event_bus.max_history_size = 5

        # Act
        for i in range(10):
            event = Event(type=EventType.EXPERIMENT_STARTED, source=f"test_{i}")
            self.event_bus.publish(event)

        # Assert
        assert len(self.event_bus.history) == 5
        assert self.event_bus.history[0].source == "test_5"
        assert self.event_bus.history[-1].source == "test_9"

        # Cleanup
        self.event_bus.max_history_size = original_limit
       