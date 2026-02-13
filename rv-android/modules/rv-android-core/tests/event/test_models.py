# tests/experiment/event/test_models.py
"""
Unit tests for the event models module in rv-android.

This test suite covers the various event models used in the event-driven architecture
of the rv-android framework, ensuring they properly represent and carry event data.
"""

from datetime import datetime
from enum import Enum

import pytest

from rv_android_core.event.models import (
    EventType, Event, TaskEvent, ExperimentEvent,
    TaskToolExecutionEvent, PhaseExecutionModeEvent
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
            "TASK_STARTED", "TASK_COMPLETED", "TASK_FAILED",
            "EXPERIMENT_COMPLETED", "EXPERIMENT_FAILED",
            "WORKFLOW_COMPLETED",
            "EMULATOR_STARTED", "APP_INSTALLED",
            "TOOL_STARTED", "TOOL_STOPPED",
            "MONITOR_GENERATED", "INSTRUMENTATION_COMPLETED",
            "STATIC_ANALYSIS_COMPLETED",
            "COVERAGE_TRACKING_STARTED", "COVERAGE_TRACKING_STOPPED",
            "COVERAGE_UPDATED", "MOP_ERROR_DETECTED",
        ]

        # Verify all expected types exist
        for event_type in expected_types:
            assert hasattr(EventType, event_type)

        # Verify the total count is exactly 17
        all_members = [e for e in EventType]
        assert len(all_members) == 17

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

    def test_event_name_property(self):
        """Test the name property returns event type name."""
        event = Event(EventType.TASK_STARTED)
        assert event.name == "TASK_STARTED"

    def test_is_lifecycle_event(self):
        """Test the is_lifecycle_event method."""
        # Test lifecycle events
        lifecycle_events = [
            EventType.TASK_STARTED, EventType.TASK_COMPLETED, EventType.TASK_FAILED,
            EventType.EXPERIMENT_COMPLETED, EventType.EXPERIMENT_FAILED,
            EventType.WORKFLOW_COMPLETED,
            EventType.EMULATOR_STARTED, EventType.TOOL_STARTED, EventType.TOOL_STOPPED,
        ]

        for event_type in lifecycle_events:
            event = Event(event_type)
            assert event.is_lifecycle_event() == True

        # Test non-lifecycle events
        non_lifecycle_events = [
            EventType.COVERAGE_UPDATED,
            EventType.MONITOR_GENERATED, EventType.INSTRUMENTATION_COMPLETED,
            EventType.STATIC_ANALYSIS_COMPLETED, EventType.APP_INSTALLED,
            EventType.COVERAGE_TRACKING_STARTED, EventType.COVERAGE_TRACKING_STOPPED,
            EventType.MOP_ERROR_DETECTED,
        ]

        for event_type in non_lifecycle_events:
            event = Event(event_type)
            assert event.is_lifecycle_event() == False

    def test_is_analysis_event(self):
        """Test the is_analysis_event method."""
        # Test analysis events
        analysis_events = [
            EventType.COVERAGE_UPDATED, EventType.COVERAGE_TRACKING_STARTED,
            EventType.COVERAGE_TRACKING_STOPPED,
            EventType.MOP_ERROR_DETECTED, EventType.STATIC_ANALYSIS_COMPLETED,
        ]

        for event_type in analysis_events:
            event = Event(event_type)
            assert event.is_analysis_event() == True

        # Test non-analysis events
        non_analysis_events = [
            EventType.TASK_STARTED, EventType.TASK_COMPLETED,
            EventType.EXPERIMENT_COMPLETED, EventType.EMULATOR_STARTED,
            EventType.TOOL_STARTED,
        ]

        for event_type in non_analysis_events:
            event = Event(event_type)
            assert event.is_analysis_event() == False


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

    def test_get_task_summary(self):
        """Test the get_task_summary method."""
        task_config = {"tool": "monkey", "timeout": 60}
        details = {"device": "emulator-5554", "status": "running"}

        event = TaskEvent(
            type=EventType.TASK_STARTED,
            task_id="test-task-123",
            task_config=task_config,
            details=details,
            source="TaskExecutor"
        )

        summary = event.get_task_summary()

        assert summary['task_id'] == "test-task-123"
        assert summary['event_type'] == "TASK_STARTED"
        assert summary['source'] == "TaskExecutor"
        assert summary['config_keys'] == ['tool', 'timeout']
        assert summary['detail_keys'] == ['device', 'status']
        assert 'timestamp' in summary

    def test_has_error_details(self):
        """Test the has_error_details method."""
        # Event with error details
        event_with_error = TaskEvent(
            type=EventType.TASK_FAILED,
            task_id="42",
            details={"error": "Connection timeout"}
        )
        assert event_with_error.has_error_details() == True

        # Event with exception details
        event_with_exception = TaskEvent(
            type=EventType.TASK_FAILED,
            task_id="42",
            details={"exception": "ValueError: Invalid input"}
        )
        assert event_with_exception.has_error_details() == True

        # Event without error details
        event_without_error = TaskEvent(
            type=EventType.TASK_COMPLETED,
            task_id="42",
            details={"status": "success"}
        )
        assert event_without_error.has_error_details() == False


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
        message = "Experiment completed successfully"
        source = "test_source"

        event = ExperimentEvent(
            type=EventType.EXPERIMENT_COMPLETED,
            experiment_id=experiment_id,
            affected_tasks=affected_tasks,
            message=message,
            source=source
        )

        # Check all attributes are properly set
        assert event.type == EventType.EXPERIMENT_COMPLETED
        assert event.experiment_id == experiment_id
        assert event.affected_tasks == affected_tasks
        assert event.message == message
        assert event.source == source
        assert isinstance(event.timestamp, datetime)

    def test_experiment_event_default_values(self):
        """Test that ExperimentEvent uses correct default values."""
        event = ExperimentEvent(type=EventType.EXPERIMENT_COMPLETED, experiment_id="exp_1")

        assert event.experiment_id == "exp_1"
        assert event.affected_tasks == []
        assert event.message == ""

    def test_experiment_event_inheritance(self):
        """Test that ExperimentEvent properly inherits from Event."""
        event = ExperimentEvent(type=EventType.EXPERIMENT_COMPLETED, experiment_id="exp_1")

        assert isinstance(event, Event)

    def test_experiment_event_string_representation(self):
        """Test the string representation of ExperimentEvent objects."""
        event = ExperimentEvent(
            type=EventType.EXPERIMENT_COMPLETED,
            experiment_id="exp_1",
            message="Test message"
        )

        # Check string representation contains experiment-specific information
        string_repr = str(event)
        assert "EXPERIMENT_COMPLETED" in string_repr
        assert "exp_1" in string_repr
        assert "Test message" in string_repr

    def test_get_experiment_summary(self):
        """Test the get_experiment_summary method."""
        affected_tasks = ["task1", "task2", "task3"]
        message = "Experiment completed successfully"

        event = ExperimentEvent(
            type=EventType.EXPERIMENT_COMPLETED,
            experiment_id="exp-test-123",
            affected_tasks=affected_tasks,
            message=message,
            source="ExperimentRunner"
        )

        summary = event.get_experiment_summary()

        assert summary['experiment_id'] == "exp-test-123"
        assert summary['event_type'] == "EXPERIMENT_COMPLETED"
        assert summary['source'] == "ExperimentRunner"
        assert summary['affected_tasks_count'] == 3
        assert summary['has_message'] == True
        assert 'timestamp' in summary

    def test_affects_task(self):
        """Test the affects_task method."""
        affected_tasks = ["task1", "task2", "task3"]

        event = ExperimentEvent(
            type=EventType.EXPERIMENT_COMPLETED,
            experiment_id="exp_1",
            affected_tasks=affected_tasks
        )

        # Test task that is affected
        assert event.affects_task("task1") == True
        assert event.affects_task("task2") == True
        assert event.affects_task("task3") == True

        # Test task that is not affected
        assert event.affects_task("task4") == False

    def test_is_failure_event(self):
        """Test the is_failure_event method."""
        # Test failure event
        failure_event = ExperimentEvent(type=EventType.EXPERIMENT_FAILED, experiment_id="exp_1")
        assert failure_event.is_failure_event() == True

        # Test non-failure events
        success_event = ExperimentEvent(type=EventType.EXPERIMENT_COMPLETED, experiment_id="exp_1")
        assert success_event.is_failure_event() == False


class TestTaskToolExecutionEvent:
    """Tests for the TaskToolExecutionEvent class."""

    def test_task_tool_execution_event_initialization(self):
        """Test that TaskToolExecutionEvent initializes with correct values."""
        task_id = "task-123"
        tool_execution_start = datetime(2023, 1, 1, 12, 5, 0)
        task_config = {"tool": "monkey", "timeout": 300}
        details = {"device": "emulator-5554"}
        source = "ToolExecutor"

        event = TaskToolExecutionEvent(
            type=EventType.TOOL_STARTED,
            task_id=task_id,
            tool_execution_start=tool_execution_start,
            task_config=task_config,
            details=details,
            source=source
        )

        assert event.type == EventType.TOOL_STARTED
        assert event.task_id == task_id
        assert event.tool_execution_start == tool_execution_start
        assert event.task_config == task_config
        assert event.details == details
        assert event.source == source
        assert isinstance(event.timestamp, datetime)

    def test_task_tool_execution_event_inheritance(self):
        """Test that TaskToolExecutionEvent properly inherits from TaskEvent."""
        tool_execution_start = datetime(2023, 1, 1, 12, 5, 0)
        event = TaskToolExecutionEvent(
            type=EventType.TOOL_STARTED,
            task_id="task-123",
            tool_execution_start=tool_execution_start
        )

        assert isinstance(event, TaskEvent)
        assert isinstance(event, Event)

    def test_get_tool_execution_summary(self):
        """Test the get_tool_execution_summary method."""
        task_id = "task-456"
        tool_execution_start = datetime(2023, 1, 1, 12, 5, 30)
        event_timestamp = datetime(2023, 1, 1, 12, 5, 0)

        event = TaskToolExecutionEvent(
            type=EventType.TOOL_STARTED,
            timestamp=event_timestamp,
            task_id=task_id,
            tool_execution_start=tool_execution_start,
            source="ToolManager"
        )

        summary = event.get_tool_execution_summary()

        assert summary['task_id'] == task_id
        assert summary['tool_execution_start'] == tool_execution_start.isoformat()
        assert summary['event_timestamp'] == event_timestamp.isoformat()
        assert summary['source'] == "ToolManager"
        assert summary['execution_delay'] == 30.0  # 30 second delay

    def test_task_tool_execution_event_string_representation(self):
        """Test the string representation of TaskToolExecutionEvent objects."""
        tool_execution_start = datetime(2023, 1, 1, 12, 5, 0)
        event = TaskToolExecutionEvent(
            type=EventType.TOOL_STARTED,
            task_id="task-789",
            tool_execution_start=tool_execution_start
        )

        string_repr = str(event)
        assert "TOOL_STARTED" in string_repr
        assert "task-789" in string_repr
        assert tool_execution_start.isoformat() in string_repr


class TestPhaseExecutionModeEvent:
    """Tests for the PhaseExecutionModeEvent class."""

    def test_phase_execution_mode_event_initialization(self):
        """Test that PhaseExecutionModeEvent initializes with correct values."""
        phase_name = "static_analysis"
        execution_mode = "full"
        fallback_reason = None
        artifacts_available = {"apk": True, "libs": True}
        source = "WorkflowManager"

        event = PhaseExecutionModeEvent(
            type=EventType.WORKFLOW_COMPLETED,
            phase_name=phase_name,
            execution_mode=execution_mode,
            fallback_reason=fallback_reason,
            artifacts_available=artifacts_available,
            source=source
        )

        assert event.type == EventType.WORKFLOW_COMPLETED
        assert event.phase_name == phase_name
        assert event.execution_mode == execution_mode
        assert event.fallback_reason == fallback_reason
        assert event.artifacts_available == artifacts_available
        assert event.source == source
        assert isinstance(event.timestamp, datetime)

    def test_phase_execution_mode_event_inheritance(self):
        """Test that PhaseExecutionModeEvent properly inherits from Event."""
        event = PhaseExecutionModeEvent(
            type=EventType.WORKFLOW_COMPLETED,
            phase_name="instrumentation",
            execution_mode="fallback"
        )

        assert isinstance(event, Event)

    def test_get_phase_summary(self):
        """Test the get_phase_summary method."""
        phase_name = "coverage_analysis"
        execution_mode = "fallback"
        fallback_reason = "Missing static analysis data"
        artifacts_available = {"logcat": True, "trace": False}

        event = PhaseExecutionModeEvent(
            type=EventType.WORKFLOW_COMPLETED,
            phase_name=phase_name,
            execution_mode=execution_mode,
            fallback_reason=fallback_reason,
            artifacts_available=artifacts_available,
            source="PhaseManager"
        )

        summary = event.get_phase_summary()

        assert summary['phase_name'] == phase_name
        assert summary['execution_mode'] == execution_mode
        assert summary['fallback_reason'] == fallback_reason
        assert summary['source'] == "PhaseManager"
        assert summary['artifacts_available'] == artifacts_available
        assert summary['is_degraded'] == True  # fallback mode is degraded
        assert 'timestamp' in summary

    def test_is_fallback_execution(self):
        """Test the is_fallback_execution method."""
        # Test fallback execution
        fallback_event = PhaseExecutionModeEvent(
            type=EventType.WORKFLOW_COMPLETED,
            phase_name="instrumentation",
            execution_mode="fallback"
        )
        assert fallback_event.is_fallback_execution() == True

        # Test non-fallback execution
        full_event = PhaseExecutionModeEvent(
            type=EventType.WORKFLOW_COMPLETED,
            phase_name="instrumentation",
            execution_mode="full"
        )
        assert full_event.is_fallback_execution() == False

        skipped_event = PhaseExecutionModeEvent(
            type=EventType.WORKFLOW_COMPLETED,
            phase_name="instrumentation",
            execution_mode="skipped"
        )
        assert skipped_event.is_fallback_execution() == False

    def test_phase_execution_mode_event_string_representation(self):
        """Test the string representation of PhaseExecutionModeEvent objects."""
        # Event with fallback reason
        event_with_reason = PhaseExecutionModeEvent(
            type=EventType.EXPERIMENT_FAILED,
            phase_name="tool_execution",
            execution_mode="failed",
            fallback_reason="Tool timeout"
        )

        string_repr_with_reason = str(event_with_reason)
        assert "tool_execution" in string_repr_with_reason
        assert "failed" in string_repr_with_reason
        assert "Tool timeout" in string_repr_with_reason

        # Event without fallback reason
        event_without_reason = PhaseExecutionModeEvent(
            type=EventType.WORKFLOW_COMPLETED,
            phase_name="results_collection",
            execution_mode="full"
        )

        string_repr_without_reason = str(event_without_reason)
        assert "results_collection" in string_repr_without_reason
        assert "full" in string_repr_without_reason
        assert "(" not in string_repr_without_reason  # No reason in parentheses


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
        event3 = ExperimentEvent(EventType.EXPERIMENT_COMPLETED, experiment_id="exp_1")

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
        event3 = ExperimentEvent(EventType.EXPERIMENT_COMPLETED, experiment_id="exp_1")

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
