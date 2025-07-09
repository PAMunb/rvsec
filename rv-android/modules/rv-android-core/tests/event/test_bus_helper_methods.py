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
    TaskEvent, ExperimentEvent, EventType
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
        task_id = "42"
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
        affected_tasks = ["1", "2", "3"]
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
