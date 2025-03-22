# tests/experiment/test_event_system.py
import threading
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from model.test_framework import ModelTestBase

from rvandroid.experiment.event_system import (
    EventType,
    Event,
    TaskEvent,
    ExperimentEvent,
    AnalysisEvent,
    EventHandler,
    EventBus
)


class TestEventType(ModelTestBase):
    """
    Unit tests for the EventType enum.

    Tests cover enum consistency and completeness.
    """

    def test_event_type_values(self):
        """Test that EventType enum contains expected event types."""
        # Check task lifecycle events
        assert hasattr(EventType, "TASK_CREATED")
        assert hasattr(EventType, "TASK_CONFIGURED")
        assert hasattr(EventType, "TASK_STARTED")
        assert hasattr(EventType, "TASK_COMPLETED")
        assert hasattr(EventType, "TASK_FAILED")

        # Check experiment lifecycle events
        assert hasattr(EventType, "EXPERIMENT_STARTED")
        assert hasattr(EventType, "EXPERIMENT_COMPLETED")
        assert hasattr(EventType, "EXPERIMENT_FAILED")
        assert hasattr(EventType, "EXPERIMENT_PAUSED")
        assert hasattr(EventType, "EXPERIMENT_RESUMED")

        # Check analysis events
        assert hasattr(EventType, "COVERAGE_UPDATED")
        assert hasattr(EventType, "ERROR_DETECTED")
        assert hasattr(EventType, "STATIC_ANALYSIS_COMPLETED")

        # Check environment events
        assert hasattr(EventType, "EMULATOR_STARTED")
        assert hasattr(EventType, "EMULATOR_STOPPED")
        assert hasattr(EventType, "APP_INSTALLED")
        assert hasattr(EventType, "TOOL_STARTED")
        assert hasattr(EventType, "TOOL_STOPPED")

    def test_event_type_uniqueness(self):
        """Test that each EventType has a unique value."""
        values = set()
        for event_type in EventType:
            assert event_type.value not in values, f"Duplicate value {event_type.value} for {event_type.name}"
            values.add(event_type.value)


class TestEvent(ModelTestBase):
    """
    Unit tests for the base Event class.

    Tests cover initialization and string representation.
    """

    def test_initialization(self):
        """Test that Event initializes with correct attributes."""
        event_type = EventType.TASK_STARTED
        event = Event(type=event_type)

        assert event.type == event_type
        assert isinstance(event.timestamp, datetime)
        assert event.source is None

    def test_initialization_with_source(self):
        """Test initialization with a source."""
        event = Event(
            type=EventType.TASK_STARTED,
            source="TestSource"
        )
        assert event.source == "TestSource"

    def test_str_representation(self):
        """Test string representation."""
        event = Event(
            type=EventType.TASK_STARTED,
            source="TestSource"
        )
        str_rep = str(event)

        assert "TASK_STARTED" in str_rep
        assert "TestSource" in str_rep
        assert event.timestamp.isoformat() in str_rep


class TestTaskEvent(ModelTestBase):
    """
    Unit tests for the TaskEvent class.

    Tests cover initialization, string representation, and attribute access.
    """

    def test_initialization(self):
        """Test that TaskEvent initializes with correct attributes."""
        event = TaskEvent(
            type=EventType.TASK_STARTED,
            task_id=123,
            task_config={"timeout": 60, "tool": "monkey"},
            details={"status": "running"},
            source="TestSource"
        )

        assert event.type == EventType.TASK_STARTED
        assert event.task_id == 123
        assert event.task_config == {"timeout": 60, "tool": "monkey"}
        assert event.details == {"status": "running"}
        assert event.source == "TestSource"

    def test_default_values(self):
        """Test default values for optional parameters."""
        event = TaskEvent(
            type=EventType.TASK_STARTED,
            task_id=123
        )

        assert event.task_config == {}
        assert event.details == {}
        assert event.source is None

    def test_str_representation(self):
        """Test string representation."""
        event = TaskEvent(
            type=EventType.TASK_STARTED,
            task_id=123
        )
        str_rep = str(event)

        assert "TASK_STARTED" in str_rep
        assert "Task 123" in str_rep
        assert event.timestamp.isoformat() in str_rep


class TestExperimentEvent(ModelTestBase):
    """
    Unit tests for the ExperimentEvent class.

    Tests cover initialization, string representation, and attribute access.
    """

    def test_initialization(self):
        """Test that ExperimentEvent initializes with correct attributes."""
        event = ExperimentEvent(
            type=EventType.EXPERIMENT_STARTED,
            experiment_id="exp-123",
            affected_tasks=[1, 2, 3],
            message="Experiment started successfully",
            source="TestSource"
        )

        assert event.type == EventType.EXPERIMENT_STARTED
        assert event.experiment_id == "exp-123"
        assert event.affected_tasks == [1, 2, 3]
        assert event.message == "Experiment started successfully"
        assert event.source == "TestSource"

    def test_default_values(self):
        """Test default values for optional parameters."""
        event = ExperimentEvent(
            type=EventType.EXPERIMENT_STARTED,
            experiment_id="exp-123"
        )

        assert event.affected_tasks == []
        assert event.message == ""
        assert event.source is None

    def test_str_representation(self):
        """Test string representation."""
        event = ExperimentEvent(
            type=EventType.EXPERIMENT_STARTED,
            experiment_id="exp-123",
            message="Test message"
        )
        str_rep = str(event)

        assert "EXPERIMENT_STARTED" in str_rep
        assert "Experiment exp-123" in str_rep
        assert "Test message" in str_rep


class TestAnalysisEvent(ModelTestBase):
    """
    Unit tests for the AnalysisEvent class.

    Tests cover initialization, string representation, and attribute access.
    """

    def test_initialization(self):
        """Test that AnalysisEvent initializes with correct attributes."""
        event = AnalysisEvent(
            type=EventType.COVERAGE_UPDATED,
            data={"method_coverage": 75.5, "activity_coverage": 80.0},
            related_task_id=123,
            source="TestSource"
        )

        assert event.type == EventType.COVERAGE_UPDATED
        assert event.data == {"method_coverage": 75.5, "activity_coverage": 80.0}
        assert event.related_task_id == 123
        assert event.source == "TestSource"

    def test_default_values(self):
        """Test default values for optional parameters."""
        event = AnalysisEvent(
            type=EventType.COVERAGE_UPDATED
        )

        assert event.data == {}
        assert event.related_task_id is None
        assert event.source is None

    def test_str_representation(self):
        """Test string representation."""
        event = AnalysisEvent(
            type=EventType.COVERAGE_UPDATED,
            related_task_id=123
        )
        str_rep = str(event)

        assert "COVERAGE_UPDATED" in str_rep
        assert "Task 123" in str_rep
        assert event.timestamp.isoformat() in str_rep

        # Event without task ID should have different representation
        event_no_task = AnalysisEvent(
            type=EventType.COVERAGE_UPDATED
        )
        str_rep_no_task = str(event_no_task)
        assert "Task" not in str_rep_no_task


class TestEventHandler(ModelTestBase):
    """
    Unit tests for the EventHandler class.

    Tests cover event filtering and handling.
    """

    def test_initialization(self):
        """Test that EventHandler initializes with correct attributes."""
        callback = MagicMock()
        filter_fn = MagicMock(return_value=True)
        handler = EventHandler(callback, filter_fn)

        assert handler.callback == callback
        assert handler.filter_fn == filter_fn

    def test_handler_without_filter(self):
        """Test handler without a filter function."""
        callback = MagicMock()
        handler = EventHandler(callback)
        event = Event(type=EventType.TASK_STARTED)

        result = handler.handle(event)

        assert result is True
        callback.assert_called_once_with(event)

    def test_handler_with_filter_passing(self):
        """Test handler with a filter function that passes the event."""
        callback = MagicMock()
        filter_fn = MagicMock(return_value=True)
        handler = EventHandler(callback, filter_fn)
        event = Event(type=EventType.TASK_STARTED)

        result = handler.handle(event)

        assert result is True
        filter_fn.assert_called_once_with(event)
        callback.assert_called_once_with(event)

    def test_handler_with_filter_blocking(self):
        """Test handler with a filter function that blocks the event."""
        callback = MagicMock()
        filter_fn = MagicMock(return_value=False)
        handler = EventHandler(callback, filter_fn)
        event = Event(type=EventType.TASK_STARTED)

        result = handler.handle(event)

        assert result is False
        filter_fn.assert_called_once_with(event)
        callback.assert_not_called()


class TestEventBus(ModelTestBase):
    """
    Unit tests for the EventBus class.

    Tests cover subscription management, event publishing, and event filtering.
    """

    @pytest.fixture
    def event_bus(self):
        """Create a fresh EventBus for testing."""
        # Clear the singleton before each test
        EventBus._instance = None
        EventBus._lock = threading.Lock()
        return EventBus.get_instance()

    def test_singleton_pattern(self):
        """Test that EventBus follows the singleton pattern."""
        bus1 = EventBus.get_instance()
        bus2 = EventBus.get_instance()

        assert bus1 is bus2

    def test_subscribe(self, event_bus):
        """Test subscribing to an event type."""
        callback = MagicMock()
        handler_id = event_bus.subscribe(EventType.TASK_STARTED, callback)

        assert isinstance(handler_id, int)
        assert len(event_bus.subscribers[EventType.TASK_STARTED]) == 1

        # The subscriber should be an EventHandler
        handler = event_bus.subscribers[EventType.TASK_STARTED][0]
        assert isinstance(handler, EventHandler)
        assert handler.callback == callback

    def test_subscribe_many(self, event_bus):
        """Test subscribing to multiple event types."""
        callback = MagicMock()
        event_types = [EventType.TASK_STARTED, EventType.TASK_COMPLETED, EventType.TASK_FAILED]

        handler_ids = event_bus.subscribe_many(event_types, callback)

        assert len(handler_ids) == 3
        for event_type in event_types:
            assert len(event_bus.subscribers[event_type]) == 1

    def test_unsubscribe_by_handler(self, event_bus):
        """Test unsubscribing by handler ID."""
        callback = MagicMock()
        handler_id = event_bus.subscribe(EventType.TASK_STARTED, callback)

        # Unsubscribe
        result = event_bus.unsubscribe_by_handler(EventType.TASK_STARTED, handler_id)

        assert result is True
        assert len(event_bus.subscribers[EventType.TASK_STARTED]) == 0

        # Try to unsubscribe with an invalid ID
        result = event_bus.unsubscribe_by_handler(EventType.TASK_STARTED, 999999)
        assert result is False

    def test_unsubscribe_all(self, event_bus):
        """Test unsubscribing a callback from all event types."""
        callback1 = MagicMock()
        callback2 = MagicMock()

        # Subscribe callbacks to multiple events
        event_bus.subscribe(EventType.TASK_STARTED, callback1)
        event_bus.subscribe(EventType.TASK_COMPLETED, callback1)
        event_bus.subscribe(EventType.TASK_STARTED, callback2)

        # Unsubscribe callback1
        count = event_bus.unsubscribe_all(callback1)

        assert count == 2
        assert len(event_bus.subscribers[EventType.TASK_STARTED]) == 1
        assert len(event_bus.subscribers[EventType.TASK_COMPLETED]) == 0

        # The remaining handler should be for callback2
        assert event_bus.subscribers[EventType.TASK_STARTED][0].callback == callback2

    def test_publish(self, event_bus):
        """Test publishing an event."""
        callback = MagicMock()
        event_bus.subscribe(EventType.TASK_STARTED, callback)

        event = Event(type=EventType.TASK_STARTED)
        count = event_bus.publish(event)

        assert count == 1
        callback.assert_called_once_with(event)

        # The event should be in the history
        assert len(event_bus.history) == 1
        assert event_bus.history[0] == event

    def test_publish_with_no_subscribers(self, event_bus):
        """Test publishing an event with no subscribers."""
        event = Event(type=EventType.TASK_STARTED)
        count = event_bus.publish(event)

        assert count == 0
        assert len(event_bus.history) == 1  # Still added to history

    def test_publish_with_multiple_subscribers(self, event_bus):
        """Test publishing an event to multiple subscribers."""
        callback1 = MagicMock()
        callback2 = MagicMock()

        event_bus.subscribe(EventType.TASK_STARTED, callback1)
        event_bus.subscribe(EventType.TASK_STARTED, callback2)

        event = Event(type=EventType.TASK_STARTED)
        count = event_bus.publish(event)

        assert count == 2
        callback1.assert_called_once_with(event)
        callback2.assert_called_once_with(event)

    def test_publish_with_filter(self, event_bus):
        """Test publishing an event with a filter function."""
        callback = MagicMock()
        filter_fn = lambda e: e.source == "TestSource"

        event_bus.subscribe(EventType.TASK_STARTED, callback, filter_fn)

        # Event that passes the filter
        event1 = Event(type=EventType.TASK_STARTED, source="TestSource")
        count1 = event_bus.publish(event1)

        assert count1 == 1
        callback.assert_called_once_with(event1)
        callback.reset_mock()

        # Event that doesn't pass the filter
        event2 = Event(type=EventType.TASK_STARTED, source="OtherSource")
        count2 = event_bus.publish(event2)

        assert count2 == 0
        callback.assert_not_called()

    def test_publish_with_error_in_handler(self, event_bus):
        """Test that errors in event handlers are caught."""

        def error_callback(event):
            raise ValueError("Test error")

        event_bus.subscribe(EventType.TASK_STARTED, error_callback)

        # This should not raise an exception
        event = Event(type=EventType.TASK_STARTED)
        count = event_bus.publish(event)

        # The handler was called but returned an error
        assert count == 0
        assert len(event_bus.history) == 1

    def test_publish_invalid_event(self, event_bus):
        """Test publishing an invalid event object."""
        count = event_bus.publish("not an event object")

        assert count == 0
        assert len(event_bus.history) == 0

    def test_history_management(self, event_bus):
        """Test that history is properly maintained."""
        # Set a small history size for testing
        event_bus.max_history_size = 3

        # Publish multiple events
        for i in range(5):
            event = Event(type=EventType.TASK_STARTED)
            event_bus.publish(event)

        # Should only keep the most recent 3 events
        assert len(event_bus.history) == 3

    def test_publish_task_event(self, event_bus):
        """Test the publish_task_event convenience method."""
        callback = MagicMock()
        event_bus.subscribe(EventType.TASK_STARTED, callback)

        count = event_bus.publish_task_event(
            event_type=EventType.TASK_STARTED,
            task_id=123,
            task_config={"timeout": 60},
            details={"status": "running"},
            source="TestSource"
        )

        assert count == 1
        callback.assert_called_once()

        # Verify the created event
        event = callback.call_args[0][0]
        assert isinstance(event, TaskEvent)
        assert event.type == EventType.TASK_STARTED
        assert event.task_id == 123
        assert event.task_config == {"timeout": 60}
        assert event.details == {"status": "running"}
        assert event.source == "TestSource"

    def test_publish_experiment_event(self, event_bus):
        """Test the publish_experiment_event convenience method."""
        callback = MagicMock()
        event_bus.subscribe(EventType.EXPERIMENT_STARTED, callback)

        count = event_bus.publish_experiment_event(
            event_type=EventType.EXPERIMENT_STARTED,
            experiment_id="exp-123",
            message="Experiment started",
            affected_tasks=[1, 2, 3],
            source="TestSource"
        )

        assert count == 1
        callback.assert_called_once()

        # Verify the created event
        event = callback.call_args[0][0]
        assert isinstance(event, ExperimentEvent)
        assert event.type == EventType.EXPERIMENT_STARTED
        assert event.experiment_id == "exp-123"
        assert event.message == "Experiment started"
        assert event.affected_tasks == [1, 2, 3]
        assert event.source == "TestSource"

    def test_publish_analysis_event(self, event_bus):
        """Test the publish_analysis_event convenience method."""
        callback = MagicMock()
        event_bus.subscribe(EventType.COVERAGE_UPDATED, callback)

        count = event_bus.publish_analysis_event(
            event_type=EventType.COVERAGE_UPDATED,
            data={"method_coverage": 75.5},
            related_task_id=123,
            source="TestSource"
        )

        assert count == 1
        callback.assert_called_once()

        # Verify the created event
        event = callback.call_args[0][0]
        assert isinstance(event, AnalysisEvent)
        assert event.type == EventType.COVERAGE_UPDATED
        assert event.data == {"method_coverage": 75.5}
        assert event.related_task_id == 123
        assert event.source == "TestSource"

    def test_get_task_events(self, event_bus):
        """Test filtering events by task ID."""
        # Create and publish task events
        event_bus.publish_task_event(EventType.TASK_STARTED, task_id=1)
        event_bus.publish_task_event(EventType.TASK_COMPLETED, task_id=1)
        event_bus.publish_task_event(EventType.TASK_STARTED, task_id=2)

        # Get events for task 1
        events = event_bus.get_task_events(1)

        assert len(events) == 2
        assert all(event.task_id == 1 for event in events)

        # Filter by event type
        events_by_type = event_bus.get_task_events(1, [EventType.TASK_STARTED])
        assert len(events_by_type) == 1
        assert events_by_type[0].type == EventType.TASK_STARTED

    def test_get_experiment_events(self, event_bus):
        """Test filtering events by experiment ID."""
        # Create and publish experiment events
        event_bus.publish_experiment_event(EventType.EXPERIMENT_STARTED, experiment_id="exp1")
        event_bus.publish_experiment_event(EventType.EXPERIMENT_COMPLETED, experiment_id="exp1")
        event_bus.publish_experiment_event(EventType.EXPERIMENT_STARTED, experiment_id="exp2")

        # Get events for experiment 1
        events = event_bus.get_experiment_events("exp1")

        assert len(events) == 2
        assert all(event.experiment_id == "exp1" for event in events)

        # Filter by event type
        events_by_type = event_bus.get_experiment_events("exp1", [EventType.EXPERIMENT_STARTED])
        assert len(events_by_type) == 1
        assert events_by_type[0].type == EventType.EXPERIMENT_STARTED

    def test_get_event_counts(self, event_bus):
        """Test getting counts of events by type."""
        # Publish different event types
        event_bus.publish(Event(type=EventType.TASK_STARTED))
        event_bus.publish(Event(type=EventType.TASK_STARTED))
        event_bus.publish(Event(type=EventType.TASK_COMPLETED))

        # Get counts
        counts = event_bus.get_event_counts()

        assert counts[EventType.TASK_STARTED] == 2
        assert counts[EventType.TASK_COMPLETED] == 1
        assert counts[EventType.TASK_FAILED] == 0  # Not published

        # Test with time filter
        past_time = datetime.now() - timedelta(hours=1)
        counts_since = event_bus.get_event_counts(since=past_time)
        assert counts_since[EventType.TASK_STARTED] == 2

        future_time = datetime.now() + timedelta(hours=1)
        counts_future = event_bus.get_event_counts(since=future_time)
        assert counts_future[EventType.TASK_STARTED] == 0

    def test_get_recent_activity(self, event_bus):
        """Test getting a summary of recent events."""
        # Publish different event types
        event_bus.publish_task_event(EventType.TASK_STARTED, task_id=1)
        event_bus.publish_experiment_event(EventType.EXPERIMENT_STARTED, experiment_id="exp1")
        event_bus.publish_analysis_event(EventType.COVERAGE_UPDATED, data={"coverage": 75})

        # Get recent activity
        activity = event_bus.get_recent_activity()

        assert len(activity) == 3

        # Verify the summaries include the right information
        task_event = next(a for a in activity if a["type"] == "TASK_STARTED")
        assert "task_id" in task_event
        assert task_event["task_id"] == 1

        exp_event = next(a for a in activity if a["type"] == "EXPERIMENT_STARTED")
        assert "experiment_id" in exp_event
        assert exp_event["experiment_id"] == "exp1"

        analysis_event = next(a for a in activity if a["type"] == "COVERAGE_UPDATED")
        assert "data_keys" in analysis_event
        assert analysis_event["data_keys"] == ["coverage"]

    def test_error_events_filtering(self, event_bus):
        """Test basic filtering of error events."""
        # Publish an error event
        event_bus.publish(Event(type=EventType.ERROR_DETECTED))

        # Publish a non-error event
        event_bus.publish(Event(type=EventType.COVERAGE_UPDATED))

        # Get all events
        all_events = event_bus.get_history()
        assert len(all_events) == 2

        # Filter events by type
        error_events = event_bus.get_history(event_type=EventType.ERROR_DETECTED)
        assert len(error_events) == 1
        assert error_events[0].type == EventType.ERROR_DETECTED

        # Clear history for other tests
        event_bus.clear_history()

    def test_get_history(self, event_bus):
        """Test getting event history with various filters."""
        # Publish events
        event_bus.publish_task_event(EventType.TASK_STARTED, task_id=1, source="Source1")
        event_bus.publish_task_event(EventType.TASK_COMPLETED, task_id=1, source="Source2")
        event_bus.publish_task_event(EventType.TASK_STARTED, task_id=2, source="Source1")

        # Get all events
        all_events = event_bus.get_history()
        assert len(all_events) == 3

        # Filter by event type
        type_events = event_bus.get_history(event_type=EventType.TASK_STARTED)
        assert len(type_events) == 2
        assert all(e.type == EventType.TASK_STARTED for e in type_events)

        # Filter by source
        source_events = event_bus.get_history(source="Source1")
        assert len(source_events) == 2
        assert all(e.source == "Source1" for e in source_events)

        # Filter by task ID
        task_events = event_bus.get_history(task_id=1)
        assert len(task_events) == 2
        assert all(e.task_id == 1 for e in task_events)

        # Combined filters
        combined_events = event_bus.get_history(
            event_type=EventType.TASK_STARTED,
            source="Source1",
            task_id=1
        )
        assert len(combined_events) == 1
        assert combined_events[0].type == EventType.TASK_STARTED
        assert combined_events[0].source == "Source1"
        assert combined_events[0].task_id == 1

    def test_clear_history(self, event_bus):
        """Test clearing event history."""
        # Add some events
        for _ in range(5):
            event_bus.publish(Event(type=EventType.TASK_STARTED))

        assert len(event_bus.history) == 5

        # Clear history
        count = event_bus.clear_history()

        assert count == 5
        assert len(event_bus.history) == 0

    def test_get_subscriber_count(self, event_bus):
        """Test getting the number of subscribers for an event type."""
        # Initially no subscribers
        assert event_bus.get_subscriber_count(EventType.TASK_STARTED) == 0

        # Add subscribers
        event_bus.subscribe(EventType.TASK_STARTED, MagicMock())
        event_bus.subscribe(EventType.TASK_STARTED, MagicMock())

        assert event_bus.get_subscriber_count(EventType.TASK_STARTED) == 2
        assert event_bus.get_subscriber_count(EventType.TASK_COMPLETED) == 0

    def test_publish_event(self, event_bus):
        """Test the generic publish_event method."""
        # Set up subscribers
        task_callback = MagicMock()
        exp_callback = MagicMock()
        analysis_callback = MagicMock()

        event_bus.subscribe(EventType.TASK_STARTED, task_callback)
        event_bus.subscribe(EventType.EXPERIMENT_STARTED, exp_callback)
        event_bus.subscribe(EventType.COVERAGE_UPDATED, analysis_callback)

        # Test task event
        event_bus.publish_event(
            event_type=EventType.TASK_STARTED,
            details={"task_id": 1, "status": "running"},
            source="TestSource"
        )
        task_callback.assert_called_once()
        task_event = task_callback.call_args[0][0]
        assert isinstance(task_event, TaskEvent)

        # Test experiment event
        event_bus.publish_event(
            event_type=EventType.EXPERIMENT_STARTED,
            details={"experiment_id": "exp1", "message": "Starting"},
            source="TestSource"
        )
        exp_callback.assert_called_once()
        exp_event = exp_callback.call_args[0][0]
        assert isinstance(exp_event, ExperimentEvent)

        # Test analysis event
        event_bus.publish_event(
            event_type=EventType.COVERAGE_UPDATED,
            details={"method_coverage": 75},
            source="TestSource"
        )
        analysis_callback.assert_called_once()
        analysis_event = analysis_callback.call_args[0][0]
        assert isinstance(analysis_event, AnalysisEvent)

    def test_publish_error_event(self, event_bus):
        """Test publishing an error event."""
        callback = MagicMock()
        event_bus.subscribe(EventType.ERROR_DETECTED, callback)

        # Create a standard exception
        error = ValueError("Test error")

        # Publish error event with context
        count = event_bus.publish_event(
            event_type=EventType.ERROR_DETECTED,
            details={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "task_id": 123,
                "context": {"operation": "test"}
            },
            source="ErrorHandler"
        )

        assert count == 1
        callback.assert_called_once()

        # Verify the created event
        event = callback.call_args[0][0]
        assert isinstance(event, Event)
        assert event.type == EventType.ERROR_DETECTED
        assert event.source == "ErrorHandler"

        # For a more comprehensive test, we can use the publish_analysis_event directly
        event_bus.publish_analysis_event(
            event_type=EventType.ERROR_DETECTED,
            data={
                "error_type": "CustomError",
                "error_message": "Custom error message",
                "timestamp": datetime.now().isoformat(),
                "context": {"task_id": 456}
            },
            related_task_id=456,
            source="TestSource"
        )

        assert callback.call_count == 2
        second_event = callback.call_args[0][0]
        assert second_event.type == EventType.ERROR_DETECTED
        assert second_event.related_task_id == 456
        assert second_event.data["error_type"] == "CustomError"
        assert second_event.data["error_message"] == "Custom error message"

    def test_event_handler_decorator(self):
        """Test the event_handler decorator."""
        # Clear singleton for this test
        EventBus._instance = None

        # Define a function with the decorator
        callback = MagicMock()

        # Use the event_handler decorator from the EventBus class
        @EventBus.event_handler(EventType.TASK_STARTED)
        def handle_task_started(event):
            callback(event)

        # Get the EventBus instance
        event_bus = EventBus.get_instance()

        # Verify the decorator registered the handler
        assert event_bus.get_subscriber_count(EventType.TASK_STARTED) == 1

        # Publish an event and verify it's handled
        event = Event(type=EventType.TASK_STARTED)
        event_bus.publish(event)

        callback.assert_called_once_with(event)

        # Test decorator with filter
        filter_mock = MagicMock(return_value=True)

        @EventBus.event_handler(EventType.TASK_COMPLETED, filter_fn=filter_mock)
        def handle_task_completed(event):
            pass

        # Verify the filter is used
        assert event_bus.get_subscriber_count(EventType.TASK_COMPLETED) == 1

        # Create a completed event
        completed_event = Event(type=EventType.TASK_COMPLETED)
        event_bus.publish(completed_event)

        # Filter should have been called
        filter_mock.assert_called_once_with(completed_event)


class TestEventBusConcurrency(ModelTestBase):
    """
    Unit tests for concurrent event handling in the EventBus.

    Tests cover thread safety and concurrent event publishing.
    """

    @pytest.fixture
    def event_bus(self):
        """Create a fresh EventBus for testing."""
        # Clear the singleton before each test
        EventBus._instance = None
        EventBus._lock = threading.Lock()
        return EventBus.get_instance()

    def test_concurrent_publishing(self, event_bus):
        """Test publishing events from multiple threads."""
        # Set up a subscriber that counts calls
        call_count = {'value': 0}
        call_lock = threading.Lock()

        def counter(event):
            with call_lock:
                call_count['value'] += 1

        event_bus.subscribe(EventType.TASK_STARTED, counter)

        # Set up threads to publish events
        thread_count = 10
        events_per_thread = 20
        threads = []

        def publish_events():
            for _ in range(events_per_thread):
                event_bus.publish(Event(type=EventType.TASK_STARTED))

        # Create and start threads
        for _ in range(thread_count):
            thread = threading.Thread(target=publish_events)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify all events were processed
        expected_count = thread_count * events_per_thread
        assert call_count['value'] == expected_count
        assert len(event_bus.history) == expected_count

    def test_concurrent_subscription(self, event_bus):
        """Test subscribing from multiple threads."""
        # Set up threads to subscribe
        thread_count = 10
        threads = []
        subscription_lock = threading.Lock()
        subscription_ids = []

        def subscribe():
            callback = lambda e: None
            handler_id = event_bus.subscribe(EventType.TASK_STARTED, callback)
            with subscription_lock:
                subscription_ids.append(handler_id)

        # Create and start threads
        for _ in range(thread_count):
            thread = threading.Thread(target=subscribe)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify all subscriptions were added
        assert len(subscription_ids) == thread_count
        assert event_bus.get_subscriber_count(EventType.TASK_STARTED) == thread_count

    def test_concurrent_history_access(self, event_bus):
        """Test concurrent publishing and history access."""
        # Set up threads to publish events and access history
        publish_thread_count = 5
        history_thread_count = 5
        events_per_thread = 10
        threads = []

        # Add some initial events
        for _ in range(10):
            event_bus.publish(Event(type=EventType.TASK_STARTED))

        def publish_events():
            for _ in range(events_per_thread):
                event_bus.publish(Event(type=EventType.TASK_STARTED))

        def access_history():
            for _ in range(events_per_thread):
                # Access history through different methods
                event_bus.get_history()
                event_bus.get_history(event_type=EventType.TASK_STARTED)
                event_bus.get_event_counts()
                event_bus.get_recent_activity()

        # Create and start publish threads
        for _ in range(publish_thread_count):
            thread = threading.Thread(target=publish_events)
            threads.append(thread)
            thread.start()

        # Create and start history access threads
        for _ in range(history_thread_count):
            thread = threading.Thread(target=access_history)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=5.0)

        # Verify events were published correctly
        assert len(event_bus.history) == 10 + (publish_thread_count * events_per_thread)
