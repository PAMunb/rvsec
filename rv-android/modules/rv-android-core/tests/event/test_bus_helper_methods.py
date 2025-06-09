# tests/experiment/event/test_bus_helper_methods.py
"""
Unit tests for EventBus helper methods.

These tests verify the convenience methods for publishing specific types
of events, ensuring they correctly create and publish events with the
appropriate properties.
"""

from unittest.mock import MagicMock

from rv_android_core.event.bus import EventBus
from rv_android_core.event.models import (
    TaskEvent, ExperimentEvent, AnalysisEvent, EventType
)


class TestEventBusHelperMethods:
    """Tests for the EventBus helper methods for publishing different event types."""

    def setup_method(self):
        """Set up test environment before each test method."""
        # Clear the singleton instance to ensure test isolation
        EventBus._instance = None
        EventBus._lock = MagicMock()

        # Create a clean instance for testing
        self.event_bus = EventBus()

        # Mock the logger
        self.event_bus.logger = MagicMock()

        # Mock the publish method to intercept the events
        self.event_bus.publish = MagicMock(return_value=1)

    def test_publish_task_event(self):
        """Test publishing a task event using the helper method."""
        # Arrange
        task_id = 42
        task_config = {"timeout": 60, "tool": "monkey"}
        details = {"result": "success"}
        source = "test_source"

        # Act
        result = self.event_bus.publish_task_event(
            EventType.TASK_STARTED,
            task_id,
            task_config,
            details,
            source
        )

        # Assert
        assert result == 1
        self.event_bus.publish.assert_called_once()

        # Get the event that was published
        event = self.event_bus.publish.call_args[0][0]
        assert isinstance(event, TaskEvent)
        assert event.type == EventType.TASK_STARTED
        assert event.task_id == task_id
        assert event.task_config == task_config
        assert event.details == details
        assert event.source == source

    def test_publish_experiment_event(self):
        """Test publishing an experiment event using the helper method."""
        # Arrange
        experiment_id = "experiment_123"
        message = "Experiment started successfully"
        affected_tasks = [1, 2, 3]
        source = "test_source"

        # Act
        result = self.event_bus.publish_experiment_event(
            EventType.EXPERIMENT_STARTED,
            experiment_id,
            message,
            affected_tasks,
            source
        )

        # Assert
        assert result == 1
        self.event_bus.publish.assert_called_once()

        # Get the event that was published
        event = self.event_bus.publish.call_args[0][0]
        assert isinstance(event, ExperimentEvent)
        assert event.type == EventType.EXPERIMENT_STARTED
        assert event.experiment_id == experiment_id
        assert event.message == message
        assert event.affected_tasks == affected_tasks
        assert event.source == source

    def test_publish_analysis_event(self):
        """Test publishing an analysis event using the helper method."""
        # Arrange
        data = {"coverage": 85.5, "errors": 0}
        related_task_id = 42
        source = "test_source"

        # Act
        result = self.event_bus.publish_analysis_event(
            EventType.COVERAGE_UPDATED,
            data,
            related_task_id,
            source
        )

        # Assert
        assert result == 1
        self.event_bus.publish.assert_called_once()

        # Get the event that was published
        event = self.event_bus.publish.call_args[0][0]
        assert isinstance(event, AnalysisEvent)
        assert event.type == EventType.COVERAGE_UPDATED
        assert event.data == data
        assert event.related_task_id == related_task_id
        assert event.source == source

    def test_publish_error_event(self):
        """Test publishing an error event using the helper method."""
        # Arrange
        error = Exception("Test error")
        context = {"phase": "execution", "task_id": 42}

        # Act
        result = self.event_bus.publish_error_event(error, context)

        # Assert
        assert result == 1
        self.event_bus.publish.assert_called_once()

        # Get the event that was published
        event = self.event_bus.publish.call_args[0][0]
        assert isinstance(event, AnalysisEvent)
        assert event.type == EventType.ERROR_DETECTED
        assert event.data["error_type"] == "Exception"
        assert event.data["error_message"] == "Test error"
        assert event.data["context"] == context
        assert event.related_task_id == 42  # Should extract from context
        assert event.source == "ErrorHandler"

    def test_publish_error_event_without_task_id(self):
        """Test publishing an error event without a task ID in the context."""
        # Arrange
        error = Exception("Test error")
        context = {"phase": "execution"}  # No task_id

        # Act
        result = self.event_bus.publish_error_event(error, context)

        # Assert
        assert result == 1
        self.event_bus.publish.assert_called_once()

        # Get the event that was published
        event = self.event_bus.publish.call_args[0][0]
        assert isinstance(event, AnalysisEvent)
        assert event.type == EventType.ERROR_DETECTED
        assert event.related_task_id is None  # No task ID should be set

    def test_publish_rvandroid_error(self):
        """Test publishing a RVAndroidError with cause information."""
        # Arrange
        from rv_android_core.util.exceptions import RVAndroidError

        cause = ValueError("Original error")
        error = RVAndroidError("An error occurred", cause)
        context = {"phase": "execution"}

        # Act
        result = self.event_bus.publish_error_event(error, context)

        # Assert
        assert result == 1
        self.event_bus.publish.assert_called_once()

        # Get the event that was published
        event = self.event_bus.publish.call_args[0][0]
        error_data = event.data

        assert error_data["error_type"] == "RVAndroidError"
        assert error_data["message"] == "An error occurred"
        assert "cause" in error_data
        assert error_data["cause"]["type"] == "ValueError"
        assert error_data["cause"]["message"] == "Original error"
