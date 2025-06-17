# tests/experiment/event/test_models.py
"""
Unit tests for the event models module in rv-android.

This test suite covers the various event models used in the event-driven architecture
of the rv-android framework, ensuring they properly represent and carry event data.
"""

from datetime import datetime
from enum import Enum

from rv_android_core.event.models import (
    EventType, Event, TaskEvent, ExperimentEvent, AnalysisEvent
)


class TestEventType:
    """
    Tests for the EventType enumeration.

    ### Architectural Testing Considerations:
    - Verify all necessary event types are defined
    - Ensure enumeration values are properly defined
    - Validate that event types align with the system's behavioral needs
    """

    def test_event_type_existence(self):
        """Test that EventType contains all expected event types."""
        expected_types = [
            "TASK_CREATED", "TASK_CONFIGURED", "TASK_STARTED", "TASK_COMPLETED", "TASK_FAILED",
            "EXPERIMENT_STARTED", "EXPERIMENT_COMPLETED", "EXPERIMENT_FAILED",
            "EXPERIMENT_PAUSED", "EXPERIMENT_RESUMED",
            "COVERAGE_UPDATED", "COVERAGE_TRACKING_STARTED", "COVERAGE_TRACKING_STOPPED",
            "ERROR_DETECTED", "STATIC_ANALYSIS_COMPLETED", "NEW_METHOD_DISCOVERED",
            "EMULATOR_STARTED", "EMULATOR_STOPPED", "APP_INSTALLED",
            "TOOL_STARTED", "TOOL_STOPPED",
            "CONFIG_LOADED", "CONFIG_SAVED",
        ]

        # Verify all expected types exist
        for event_type in expected_types:
            assert hasattr(EventType, event_type)

    def test_event_type_is_enum(self):
        """Test that EventType is properly defined as an Enum."""
        assert issubclass(EventType, Enum)

    def test_event_type_values(self):
        """Test that event type values are properly defined and unique."""
        # Get all values
        values = [e.value for e in EventType]

        # Check that all values are unique
        assert len(values) == len(set(values)), "Event type values must be unique"


class TestBaseEvent:
    """
    Tests for the base Event class.

    ### Architectural Testing Considerations:
    - Verify the base event structure is properly defined
    - Ensure timestamp and source tracking work correctly
    - Validate string representation for logging and debugging
    """

    def test_event_initialization(self):
        """Test that Event initializes with correct values."""
        # Test with only required parameters
        event = Event(EventType.TASK_STARTED)
        assert event.type == EventType.TASK_STARTED
        assert isinstance(event.timestamp, datetime)
        assert event.source is None

        # Test with all parameters
        source = "test_source"
        event = Event(EventType.TASK_STARTED, source=source)
        assert event.type == EventType.TASK_STARTED
        assert isinstance(event.timestamp, datetime)
        assert event.source == source

    def test_event_initialization_with_timestamp(self):
        """Test that Event can be initialized with a specific timestamp."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        event = Event(EventType.TASK_STARTED, timestamp=timestamp)
        assert event.timestamp == timestamp

    def test_event_string_representation(self):
        """Test the string representation of Event objects."""
        source = "test_source"
        event = Event(EventType.TASK_STARTED, source=source)

        # Check string representation contains key information
        string_repr = str(event)
        assert "TASK_STARTED" in string_repr
        assert source in string_repr
        assert event.timestamp.isoformat() in string_repr


class TestTaskEvent:
    """
    Tests for the TaskEvent class.

    ### Architectural Testing Considerations:
    - Verify task events properly track task metadata
    - Ensure proper inheritance from base Event class
    - Validate task details are properly captured and accessible
    """

    def test_task_event_initialization(self):
        """Test that TaskEvent initializes with correct values."""
        task_id = "42"  # Using string for UUID compatibility
        task_config = {"apk_name": "test.apk", "timeout": 60}
        details = {"status": "running", "progress": 50}
        source = "test_source"

        event = TaskEvent(
            type=EventType.TASK_STARTED,
            task_id=task_id,
            task_config=task_config,
            details=details,
            source=source
        )

        # Check all attributes are properly set
        assert event.type == EventType.TASK_STARTED
        assert event.task_id == task_id
        assert event.task_config == task_config
        assert event.details == details
        assert event.source == source
        assert isinstance(event.timestamp, datetime)

    def test_task_event_default_values(self):
        """Test that TaskEvent uses correct default values."""
        event = TaskEvent(type=EventType.TASK_STARTED, task_id="42")

        assert event.task_id == "42"
        assert event.task_config == {}
        assert event.details == {}

    def test_task_event_inheritance(self):
        """Test that TaskEvent properly inherits from Event."""
        event = TaskEvent(type=EventType.TASK_STARTED, task_id="42")

        assert isinstance(event, Event)

    def test_task_event_string_representation(self):
        """Test the string representation of TaskEvent objects."""
        event = TaskEvent(type=EventType.TASK_STARTED, task_id="42")

        # Check string representation contains task-specific information
        string_repr = str(event)
        assert "TASK_STARTED" in string_repr
        assert "Task 42" in string_repr
        assert event.timestamp.isoformat() in string_repr


class TestExperimentEvent:
    """
    Tests for the ExperimentEvent class.

    ### Architectural Testing Considerations:
    - Verify experiment events properly track experiment metadata
    - Ensure proper inheritance from base Event class
    - Validate experiment details are properly captured and accessible
    """

    def test_experiment_event_initialization(self):
        """Test that ExperimentEvent initializes with correct values."""
        experiment_id = "exp_2023_01_01"
        affected_tasks = ["1", "2", "3"]
        message = "Experiment started successfully"
        source = "test_source"

        event = ExperimentEvent(
            type=EventType.EXPERIMENT_STARTED,
            experiment_id=experiment_id,
            affected_tasks=affected_tasks,
            message=message,
            source=source
        )

        # Check all attributes are properly set
        assert event.type == EventType.EXPERIMENT_STARTED
        assert event.experiment_id == experiment_id
        assert event.affected_tasks == affected_tasks
        assert event.message == message
        assert event.source == source
        assert isinstance(event.timestamp, datetime)

    def test_experiment_event_default_values(self):
        """Test that ExperimentEvent uses correct default values."""
        event = ExperimentEvent(type=EventType.EXPERIMENT_STARTED, experiment_id="exp_1")

        assert event.experiment_id == "exp_1"
        assert event.affected_tasks == []
        assert event.message == ""

    def test_experiment_event_inheritance(self):
        """Test that ExperimentEvent properly inherits from Event."""
        event = ExperimentEvent(type=EventType.EXPERIMENT_STARTED, experiment_id="exp_1")

        assert isinstance(event, Event)

    def test_experiment_event_string_representation(self):
        """Test the string representation of ExperimentEvent objects."""
        event = ExperimentEvent(
            type=EventType.EXPERIMENT_STARTED,
            experiment_id="exp_1",
            message="Test message"
        )

        # Check string representation contains experiment-specific information
        string_repr = str(event)
        assert "EXPERIMENT_STARTED" in string_repr
        assert "exp_1" in string_repr
        assert "Test message" in string_repr


class TestAnalysisEvent:
    """
    Tests for the AnalysisEvent class.

    ### Architectural Testing Considerations:
    - Verify analysis events properly track analytical data
    - Ensure proper inheritance from base Event class
    - Validate analysis details are properly captured and accessible
    """

    def test_analysis_event_initialization(self):
        """Test that AnalysisEvent initializes with correct values."""
        data = {"coverage": 75.5, "errors": 2}
        related_task_id = "42"
        source = "test_source"

        event = AnalysisEvent(
            type=EventType.COVERAGE_UPDATED,
            data=data,
            related_task_id=related_task_id,
            source=source
        )

        # Check all attributes are properly set
        assert event.type == EventType.COVERAGE_UPDATED
        assert event.data == data
        assert event.related_task_id == related_task_id
        assert event.source == source
        assert isinstance(event.timestamp, datetime)

    def test_analysis_event_default_values(self):
        """Test that AnalysisEvent uses correct default values."""
        event = AnalysisEvent(type=EventType.COVERAGE_UPDATED)

        assert event.data == {}
        assert event.related_task_id is None

    def test_analysis_event_inheritance(self):
        """Test that AnalysisEvent properly inherits from Event."""
        event = AnalysisEvent(type=EventType.COVERAGE_UPDATED)

        assert isinstance(event, Event)

    def test_analysis_event_string_representation(self):
        """Test the string representation of AnalysisEvent objects."""
        # With related task ID
        event1 = AnalysisEvent(
            type=EventType.COVERAGE_UPDATED,
            related_task_id="42"
        )

        string_repr1 = str(event1)
        assert "COVERAGE_UPDATED" in string_repr1
        assert "Task 42" in string_repr1

        # Without related task ID
        event2 = AnalysisEvent(type=EventType.COVERAGE_UPDATED)

        string_repr2 = str(event2)
        assert "COVERAGE_UPDATED" in string_repr2
        assert "Task" not in string_repr2


class TestEventIntegration:
    """
    Integration tests for event model interactions.

    ### Architectural Testing Considerations:
    - Verify event models work together as expected
    - Test the event creation with current timestamps
    - Validate integration with datetime functionality
    """

    def test_event_timestamp_consistency(self):
        """Test that events created close together have close timestamps."""
        event1 = Event(EventType.TASK_STARTED)
        event2 = TaskEvent(EventType.TASK_STARTED, task_id="1")
        event3 = ExperimentEvent(EventType.EXPERIMENT_STARTED, experiment_id="exp_1")

        # All events should have timestamps within a small window
        # Default is 1 second, but can be adjusted based on system performance
        max_time_diff = 1.0  # seconds

        assert abs((event1.timestamp - event2.timestamp).total_seconds()) < max_time_diff
        assert abs((event2.timestamp - event3.timestamp).total_seconds()) < max_time_diff

    def test_events_use_current_time(self):
        """Test that events use the current time by default."""
        # Create events
        event1 = Event(EventType.TASK_STARTED)
        event2 = TaskEvent(EventType.TASK_STARTED, task_id="1")
        event3 = ExperimentEvent(EventType.EXPERIMENT_STARTED, experiment_id="exp_1")

        # Calculate the maximum time difference between any two events
        time_diffs = [
            abs((event1.timestamp - event2.timestamp).total_seconds()),
            abs((event1.timestamp - event3.timestamp).total_seconds()),
            abs((event2.timestamp - event3.timestamp).total_seconds())
        ]

        max_diff = max(time_diffs)

        # All events should be created within a very small window (e.g., 0.1 seconds)
        # This verifies they all use "now" without having to mock datetime.now()
        assert max_diff < 0.1, f"Events should have very close timestamps, but max difference was {max_diff} seconds"
