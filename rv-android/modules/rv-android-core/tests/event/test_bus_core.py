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
from rv_android_core.event.handler import HandlerPriority
from rv_android_core.event.models import Event, EventType


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

    def test_initialization(self):
        """Test that EventBus initializes with the expected state."""
        # Assert
        assert self.event_bus.channel_subscribers is not None
        assert EventBus.DEFAULT_CHANNEL in self.event_bus.channel_subscribers
        assert EventBus.SYSTEM_CHANNEL in self.event_bus.channel_subscribers
        assert EventBus.LIFECYCLE_CHANNEL in self.event_bus.channel_subscribers
        assert EventBus.ANALYSIS_CHANNEL in self.event_bus.channel_subscribers
        assert EventBus.ERROR_CHANNEL in self.event_bus.channel_subscribers
        assert EventBus.USER_CHANNEL in self.event_bus.channel_subscribers

        # Check that each channel has entries for all event types
        for channel in self.event_bus.channel_subscribers:
            assert len(self.event_bus.channel_subscribers[channel]) == len(EventType)

        # Check history initialization
        assert self.event_bus.history == []
        assert self.event_bus.max_history_size > 0

    def test_subscribe(self):
        """Test subscribing to an event type."""
        # Arrange
        callback = MagicMock()

        # Act
        handler_id = self.event_bus.subscribe(
            EventType.EXPERIMENT_STARTED,
            callback
        )

        # Assert
        assert handler_id is not None

        # Check that the handler was added
        handlers = self.event_bus.channel_subscribers[EventBus.DEFAULT_CHANNEL][EventType.EXPERIMENT_STARTED]
        assert len(handlers) == 1
        assert handlers[0].callback == callback
        assert handlers[0].filter_fn is None
        assert handlers[0].priority == HandlerPriority.NORMAL

    def test_subscribe_with_filter_and_priority(self):
        """Test subscribing with a filter function and priority."""
        # Arrange
        callback = MagicMock()
        filter_fn = lambda event: event.source == "test"

        # Act
        handler_id = self.event_bus.subscribe(
            EventType.EXPERIMENT_STARTED,
            callback,
            filter_fn=filter_fn,
            priority=HandlerPriority.HIGH,
            channel=EventBus.LIFECYCLE_CHANNEL
        )

        # Assert
        handlers = self.event_bus.channel_subscribers[EventBus.LIFECYCLE_CHANNEL][EventType.EXPERIMENT_STARTED]
        assert len(handlers) == 1
        assert handlers[0].callback == callback
        assert handlers[0].filter_fn == filter_fn
        assert handlers[0].priority == HandlerPriority.HIGH

    def test_subscribe_many(self):
        """Test subscribing to multiple event types at once."""
        # Arrange
        callback = MagicMock()
        event_types = [EventType.EXPERIMENT_STARTED, EventType.EXPERIMENT_COMPLETED]

        # Act
        handler_ids = self.event_bus.subscribe_many(event_types, callback)

        # Assert
        assert len(handler_ids) == 2

        # Check that handlers were added for both event types
        handlers1 = self.event_bus.channel_subscribers[EventBus.DEFAULT_CHANNEL][EventType.EXPERIMENT_STARTED]
        handlers2 = self.event_bus.channel_subscribers[EventBus.DEFAULT_CHANNEL][EventType.EXPERIMENT_COMPLETED]

        assert len(handlers1) == 1
        assert len(handlers2) == 1
        assert handlers1[0].callback == callback
        assert handlers2[0].callback == callback

    def test_unsubscribe_by_handler(self):
        """Test unsubscribing by handler ID."""
        # Arrange
        callback = MagicMock()
        handler_id = self.event_bus.subscribe(EventType.EXPERIMENT_STARTED, callback)

        # Act
        result = self.event_bus.unsubscribe_by_handler(
            EventType.EXPERIMENT_STARTED,
            handler_id
        )

        # Assert
        assert result is True
        handlers = self.event_bus.channel_subscribers[EventBus.DEFAULT_CHANNEL][EventType.EXPERIMENT_STARTED]
        assert len(handlers) == 0

    def test_unsubscribe_by_handler_invalid_id(self):
        """Test unsubscribing with an invalid handler ID."""
        # Arrange
        callback = MagicMock()
        self.event_bus.subscribe(EventType.EXPERIMENT_STARTED, callback)

        # Act
        result = self.event_bus.unsubscribe_by_handler(
            EventType.EXPERIMENT_STARTED,
            9999  # Non-existent ID
        )

        # Assert
        assert result is False
        handlers = self.event_bus.channel_subscribers[EventBus.DEFAULT_CHANNEL][EventType.EXPERIMENT_STARTED]
        assert len(handlers) == 1

    def test_unsubscribe_all(self):
        """Test unsubscribing all instances of a callback."""
        # Arrange
        callback = MagicMock()
        callback2 = MagicMock()

        # Subscribe callback to multiple event types and channels
        self.event_bus.subscribe(EventType.EXPERIMENT_STARTED, callback)
        self.event_bus.subscribe(EventType.EXPERIMENT_COMPLETED, callback)
        self.event_bus.subscribe(
            EventType.TASK_STARTED,
            callback,
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        self.event_bus.subscribe(EventType.TASK_COMPLETED, callback2)

        # Act
        count = self.event_bus.unsubscribe_all(callback)

        # Assert
        assert count == 3

        # Check that only callback2 remains
        handlers = self.event_bus.channel_subscribers[EventBus.DEFAULT_CHANNEL][EventType.TASK_COMPLETED]
        assert len(handlers) == 1
        assert handlers[0].callback == callback2

        # Check that all handlers for callback were removed
        assert len(self.event_bus.channel_subscribers[EventBus.DEFAULT_CHANNEL][EventType.EXPERIMENT_STARTED]) == 0
        assert len(self.event_bus.channel_subscribers[EventBus.DEFAULT_CHANNEL][EventType.EXPERIMENT_COMPLETED]) == 0
        assert len(self.event_bus.channel_subscribers[EventBus.LIFECYCLE_CHANNEL][EventType.TASK_STARTED]) == 0

    def test_unsubscribe_all_specific_channels(self):
        """Test unsubscribing a callback from specific channels only."""
        # Arrange
        callback = MagicMock()

        # Subscribe callback to multiple channels
        self.event_bus.subscribe(
            EventType.EXPERIMENT_STARTED,
            callback,
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        self.event_bus.subscribe(
            EventType.TASK_STARTED,
            callback,
            channel=EventBus.LIFECYCLE_CHANNEL
        )
        self.event_bus.subscribe(
            EventType.COVERAGE_UPDATED,
            callback,
            channel=EventBus.ANALYSIS_CHANNEL
        )

        # Act
        count = self.event_bus.unsubscribe_all(
            callback,
            channels=[EventBus.LIFECYCLE_CHANNEL]
        )

        # Assert
        assert count == 2

        # Check that only the ANALYSIS_CHANNEL handler remains
        handlers = self.event_bus.channel_subscribers[EventBus.ANALYSIS_CHANNEL][EventType.COVERAGE_UPDATED]
        assert len(handlers) == 1

    def test_publish_basic(self):
        """Test basic event publishing."""
        # Arrange
        callback = MagicMock()
        self.event_bus.subscribe(EventType.EXPERIMENT_STARTED, callback)

        event = Event(type=EventType.EXPERIMENT_STARTED, source="test")

        # Act
        count = self.event_bus.publish(event)

        # Assert
        assert count == 1
        callback.assert_called_once_with(event)

        # Check event was added to history
        assert len(self.event_bus.history) == 1
        assert self.event_bus.history[0] == event

    def test_publish_invalid_event(self):
        """Test publishing an invalid event."""
        # Arrange
        callback = MagicMock()
        self.event_bus.subscribe(EventType.EXPERIMENT_STARTED, callback)

        # Act
        count = self.event_bus.publish("not an event")

        # Assert
        assert count == 0
        callback.assert_not_called()
        assert len(self.event_bus.history) == 0
        assert self.event_bus.logger.error.called

    def test_publish_handlers_sorted_by_priority(self):
        """Test that handlers are called in priority order."""
        # Arrange
        call_order = []

        def callback1(event):
            call_order.append("low")

        def callback2(event):
            call_order.append("normal")

        def callback3(event):
            call_order.append("high")

        def callback4(event):
            call_order.append("critical")

        # Subscribe handlers with different priorities (in mixed order)
        self.event_bus.subscribe(
            EventType.EXPERIMENT_STARTED,
            callback1,
            priority=HandlerPriority.LOW
        )
        self.event_bus.subscribe(
            EventType.EXPERIMENT_STARTED,
            callback3,
            priority=HandlerPriority.HIGH
        )
        self.event_bus.subscribe(
            EventType.EXPERIMENT_STARTED,
            callback4,
            priority=HandlerPriority.CRITICAL
        )
        self.event_bus.subscribe(
            EventType.EXPERIMENT_STARTED,
            callback2,
            priority=HandlerPriority.NORMAL
        )

        event = Event(type=EventType.EXPERIMENT_STARTED, source="test")

        # Act
        count = self.event_bus.publish(event)

        # Assert
        assert count == 4
        # Highest priority should be called first
        assert call_order == ["critical", "high", "normal", "low"]

    def test_history_limit(self):
        """Test that history is limited to max_history_size."""
        # Arrange
        original_size = self.event_bus.max_history_size

        # Temporarily reduce max_history_size for testing
        self.event_bus.max_history_size = 3

        # Act
        # Publish more events than the history size limit
        for i in range(5):
            event = Event(
                type=EventType.EXPERIMENT_STARTED,
                source=f"test{i}"
            )
            self.event_bus.publish(event)

        # Assert
        assert len(self.event_bus.history) == 3

        # Check that the oldest events were removed
        sources = [e.source for e in self.event_bus.history]
        assert "test0" not in sources
        assert "test1" not in sources
        assert "test2" in sources
        assert "test3" in sources
        assert "test4" in sources

        # Restore original size
        self.event_bus.max_history_size = original_size

    def test_shutdown(self):
        """Test shutting down the EventBus."""
        # Arrange
        thread_pool_mock = MagicMock()
        self.event_bus._thread_pool = thread_pool_mock
        self.event_bus._processing_thread = MagicMock()
        self.event_bus._processing_thread.is_alive.return_value = True
        self.event_bus._processing_thread.join.return_value = None

        # Act
        self.event_bus.shutdown(wait_for_completion=True)

        # Assert
        assert self.event_bus._active is False
        thread_pool_mock.shutdown.assert_called_once_with(wait=True)
        self.event_bus._processing_thread.join.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-v"])
