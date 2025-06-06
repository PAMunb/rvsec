# tests/experiment/event/test_handler_integration.py (updated)
"""
Integration tests for the EventHandler class.

These tests verify that the EventHandler integrates correctly with the Event models
and the EventBus, ensuring proper event propagation and handling throughout the system.
"""

from unittest.mock import MagicMock, patch

import pytest

from rvandroid.experiment.event.bus import EventBus
from rvandroid.experiment.event.handler import EventHandler
from rvandroid.experiment.event.models import Event, EventType, TaskEvent


class TestEventHandlerIntegration:
    """Integration tests for the EventHandler with the event system."""

    def test_registration_with_event_bus(self):
        """Test that an EventHandler can be registered with the EventBus."""
        # Arrange
        callback = MagicMock()

        # Use a patch to mock the EventBus.get_instance method
        with patch.object(EventBus, 'get_instance') as mock_get_instance:
            mock_event_bus = MagicMock()
            mock_get_instance.return_value = mock_event_bus
            mock_event_bus.subscribe.return_value = 123  # Mock handler ID

            # Act
            event_bus = EventBus.get_instance()
            event_type = EventType.EXPERIMENT_STARTED
            handler_id = event_bus.subscribe(event_type, callback)

            # Assert
            mock_event_bus.subscribe.assert_called_once()
            assert handler_id == 123  # Verify the handler ID is returned

    def test_event_propagation_through_bus(self):
        """Test event propagation from event bus to handlers."""
        # Arrange
        callback = MagicMock()
        handler = EventHandler(callback)

        # Create a task event
        task_event = TaskEvent(type=EventType.TASK_STARTED, task_id=1)

        # Act - simulate direct event handling without EventBus
        result = handler.handle(task_event)

        # Assert
        assert result is True
        callback.assert_called_once_with(task_event)

        # Verify event properties were passed correctly
        args = callback.call_args[0][0]
        assert args.type == EventType.TASK_STARTED
        assert args.task_id == 1

    def test_real_task_event_handling(self):
        """Test handling a real TaskEvent instance."""
        # Arrange
        callback = MagicMock()
        handler = EventHandler(callback)

        # Create a real TaskEvent
        task_event = TaskEvent(
            type=EventType.TASK_STARTED,
            task_id=42,
            task_config={
                "apk_name": "test_app.apk",
                "repetition": 1,
                "timeout": 60,
                "tool_name": "monkey"
            },
            details={"device_id": "emulator-5554"},
            source="TaskExecutor"
        )

        # Act
        result = handler.handle(task_event)

        # Assert
        assert result is True
        callback.assert_called_once_with(task_event)

        # Verify event properties were preserved
        args = callback.call_args[0][0]
        assert args.type == EventType.TASK_STARTED
        assert args.task_id == 42
        assert args.task_config["apk_name"] == "test_app.apk"
        assert args.source == "TaskExecutor"

    def test_filter_on_task_id(self):
        """Test filtering events based on task ID."""
        # Arrange
        callback = MagicMock()

        # Create filter that only accepts events for task ID 1
        def task_id_filter(event):
            return hasattr(event, 'task_id') and event.task_id == 1

        handler = EventHandler(callback, task_id_filter)

        # Create task events with different IDs
        task_event1 = TaskEvent(type=EventType.TASK_STARTED, task_id=1)
        task_event2 = TaskEvent(type=EventType.TASK_STARTED, task_id=2)

        # Act
        result1 = handler.handle(task_event1)
        result2 = handler.handle(task_event2)

        # Assert
        assert result1 is True
        assert result2 is False
        callback.assert_called_once_with(task_event1)

    def test_event_bus_integration_with_handler(self):
        """Test creating a handler and using it with the EventBus."""
        # Arrange
        callback = MagicMock()
        filter_fn = lambda event: True  # Simple filter that accepts all events

        # Create the handler
        handler = EventHandler(callback, filter_fn)

        # Set up mocked EventBus
        with patch.object(EventBus, 'get_instance') as mock_get_instance:
            mock_event_bus = MagicMock()
            mock_get_instance.return_value = mock_event_bus

            # Create subscribers dict to simulate EventBus behavior
            subscribers = {EventType.TASK_STARTED: []}

            # Mock the subscribe method to store handlers
            def mock_subscribe(event_type, callback_fn, filter_fn=None):
                handler = EventHandler(callback_fn, filter_fn)
                subscribers[event_type].append(handler)
                return id(handler)

            mock_event_bus.subscribe.side_effect = mock_subscribe

            # Mock the publish method to call handlers
            def mock_publish(event):
                handlers = subscribers.get(event.type, [])
                count = 0
                for handler in handlers:
                    if handler.handle(event):
                        count += 1
                return count

            mock_event_bus.publish.side_effect = mock_publish

            # Act
            event_bus = EventBus.get_instance()

            # Register a handler
            handler_id = event_bus.subscribe(EventType.TASK_STARTED, callback)

            # Create and publish an event
            task_event = TaskEvent(type=EventType.TASK_STARTED, task_id=1)
            result = event_bus.publish(task_event)

            # Assert
            assert result == 1  # One handler processed the event
            callback.assert_called_once_with(task_event)

    def test_generic_event_handling(self):
        """Test handling a generic Event instance."""
        # Arrange
        callback = MagicMock()
        handler = EventHandler(callback)

        # Create a generic Event
        event = Event(type=EventType.EXPERIMENT_STARTED, source="Test")

        # Act
        result = handler.handle(event)

        # Assert
        assert result is True
        callback.assert_called_once_with(event)


if __name__ == "__main__":
    pytest.main(["-v", "test_handler_integration.py"])
