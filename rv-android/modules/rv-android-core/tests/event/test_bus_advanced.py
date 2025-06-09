# tests/experiment/event/test_bus_advanced.py
"""
Advanced unit tests for the EventBus class.

These tests verify more complex scenarios including handler exceptions,
event filtering, and event history filtering. They ensure the EventBus
provides robust event handling even in edge cases.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

from rv_android_core.event.bus import EventBus
from rv_android_core.event.models import (
    Event, TaskEvent, ExperimentEvent, EventType
)


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
        self.event_bus.subscribe(EventType.EXPERIMENT_STARTED, callback)

        event = Event(type=EventType.EXPERIMENT_STARTED, source="test")

        # Act
        count = self.event_bus.publish(event)

        # Assert
        assert count == 0  # No successful handlers
        assert self.event_bus.logger.error.called
        assert len(self.event_bus.history) == 1

    def test_multiple_handlers_one_exception(self):
        """Test that one failing handler doesn't prevent others from executing."""
        # Arrange
        callback1 = MagicMock(side_effect=Exception("Test exception"))
        callback2 = MagicMock()

        self.event_bus.subscribe(EventType.EXPERIMENT_STARTED, callback1)
        self.event_bus.subscribe(EventType.EXPERIMENT_STARTED, callback2)

        event = Event(type=EventType.EXPERIMENT_STARTED, source="test")

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

        self.event_bus.subscribe(EventType.EXPERIMENT_STARTED, callback, filter_fn)

        # Create events with different sources
        event1 = Event(type=EventType.EXPERIMENT_STARTED, source="test_source")
        event2 = Event(type=EventType.EXPERIMENT_STARTED, source="other_source")

        # Act
        count1 = self.event_bus.publish(event1)
        count2 = self.event_bus.publish(event2)

        # Assert
        assert count1 == 1
        assert count2 == 0
        callback.assert_called_once_with(event1)

    def test_get_history_all(self):
        """Test retrieving the full event history."""
        # Arrange
        # Create and publish different events
        event1 = Event(type=EventType.EXPERIMENT_STARTED, source="test1")
        event2 = TaskEvent(type=EventType.TASK_STARTED, task_id=1, source="test2")
        event3 = ExperimentEvent(type=EventType.EXPERIMENT_COMPLETED, experiment_id="exp1", source="test3")

        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        self.event_bus.publish(event3)

        # Act
        history = self.event_bus.get_history()

        # Assert
        assert len(history) == 3
        assert history[0] == event3  # Most recent first
        assert history[1] == event2
        assert history[2] == event1

    def test_get_history_by_event_type(self):
        """Test filtering history by event type."""
        # Arrange
        event1 = Event(type=EventType.EXPERIMENT_STARTED, source="test1")
        event2 = TaskEvent(type=EventType.TASK_STARTED, task_id=1, source="test2")
        event3 = ExperimentEvent(type=EventType.EXPERIMENT_COMPLETED, experiment_id="exp1", source="test3")
        event4 = TaskEvent(type=EventType.TASK_COMPLETED, task_id=1, source="test4")

        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        self.event_bus.publish(event3)
        self.event_bus.publish(event4)

        # Act
        task_events = self.event_bus.get_history(event_type=EventType.TASK_STARTED)

        # Assert
        assert len(task_events) == 1
        assert task_events[0] == event2

    def test_get_history_by_source(self):
        """Test filtering history by source."""
        # Arrange
        event1 = Event(type=EventType.EXPERIMENT_STARTED, source="source_a")
        event2 = Event(type=EventType.TASK_STARTED, source="source_b")
        event3 = Event(type=EventType.EXPERIMENT_COMPLETED, source="source_a")

        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        self.event_bus.publish(event3)

        # Act
        source_a_events = self.event_bus.get_history(source="source_a")

        # Assert
        assert len(source_a_events) == 2
        assert source_a_events[0] == event3  # Most recent first
        assert source_a_events[1] == event1

    def test_get_history_by_task_id(self):
        """Test filtering history by task ID."""
        # Arrange
        event1 = TaskEvent(type=EventType.TASK_STARTED, task_id=1, source="test1")
        event2 = TaskEvent(type=EventType.TASK_STARTED, task_id=2, source="test2")
        event3 = TaskEvent(type=EventType.TASK_COMPLETED, task_id=1, source="test3")
        event4 = ExperimentEvent(type=EventType.EXPERIMENT_COMPLETED, experiment_id="exp1", source="test4")

        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        self.event_bus.publish(event3)
        self.event_bus.publish(event4)

        # Act
        task1_events = self.event_bus.get_history(task_id=1)

        # Assert
        assert len(task1_events) == 2
        assert task1_events[0] == event3  # Most recent first
        assert task1_events[1] == event1

    def test_get_history_with_time_filter(self):
        """Test filtering history by timestamp."""
        # Arrange
        now = datetime.now()

        # Create events with different timestamps
        event1 = Event(type=EventType.EXPERIMENT_STARTED, source="test1")
        event1.timestamp = now - timedelta(hours=2)

        event2 = Event(type=EventType.TASK_STARTED, source="test2")
        event2.timestamp = now - timedelta(hours=1)

        event3 = Event(type=EventType.EXPERIMENT_COMPLETED, source="test3")
        event3.timestamp = now

        # Manually add events to history with specific timestamps
        self.event_bus.history = [event1, event2, event3]

        # Act
        recent_events = self.event_bus.get_history(since=now - timedelta(hours=1, minutes=30))

        # Assert
        assert len(recent_events) == 2
        assert recent_events[0] == event3  # Most recent first
        assert recent_events[1] == event2
       