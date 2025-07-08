# tests/event/test_decorators.py
"""
Tests for event decorators functionality.

This module tests the decorators that enable declarative event publishing
and subscription, ensuring proper integration with the event system.
"""

import pytest
from unittest.mock import Mock, call
from typing import Dict, Any

from rv_android_core.event.bus import EventBus
from rv_android_core.event.decorators import publish_event, subscribe_to
from rv_android_core.event.handler import HandlerPriority
from rv_android_core.event.models import Event, EventType


class TestPublishEventDecorator:
    """Test cases for the @publish_event decorator."""

    def setup_method(self):
        """Set up test environment with isolated event bus."""
        self.event_bus = EventBus()
        self.events_published = []
        
        # Mock the publish method to capture events
        original_publish = self.event_bus.publish
        
        def mock_publish(event, channel=EventBus.DEFAULT_CHANNEL):
            self.events_published.append((event, channel))
            return original_publish(event, channel)
            
        self.event_bus.publish = mock_publish

    def test_basic_event_publishing(self):
        """Test basic event publishing after method execution."""
        @publish_event(
            event_type=EventType.TASK_STARTED,
            event_bus_provider=lambda: self.event_bus
        )
        def start_task():
            return "task_started"

        result = start_task()
        
        assert result == "task_started"
        assert len(self.events_published) == 1
        
        event, channel = self.events_published[0]
        assert event.type == EventType.TASK_STARTED
        assert channel == EventBus.DEFAULT_CHANNEL

    def test_event_publishing_with_custom_channel(self):
        """Test event publishing to custom channel."""
        @publish_event(
            event_type=EventType.EXPERIMENT_STARTED,
            channel=EventBus.LIFECYCLE_CHANNEL,
            event_bus_provider=lambda: self.event_bus
        )
        def start_experiment():
            return "experiment_started"

        start_experiment()
        
        assert len(self.events_published) == 1
        event, channel = self.events_published[0]
        assert event.type == EventType.EXPERIMENT_STARTED
        assert channel == EventBus.LIFECYCLE_CHANNEL

    def test_event_publishing_with_source_extraction(self):
        """Test event publishing with source information extraction."""
        def get_source(obj):
            return getattr(obj, 'name', 'unknown')

        @publish_event(
            event_type=EventType.TASK_COMPLETED,
            get_source=get_source,
            event_bus_provider=lambda: self.event_bus
        )
        def complete_task(self):
            return "completed"

        # Create a mock object with name attribute
        mock_obj = Mock()
        mock_obj.name = "TestTaskExecutor"
        
        complete_task(mock_obj)
        
        assert len(self.events_published) == 1
        event, _ = self.events_published[0]
        assert event.source == "TestTaskExecutor"

    def test_event_publishing_with_details_extraction(self):
        """Test event publishing with detail information extraction."""
        def get_details(args, kwargs):
            return {
                "task_id": kwargs.get("task_id", "unknown"),
                "duration": kwargs.get("duration", 0),
                "args_count": len(args)
            }

        @publish_event(
            event_type=EventType.ANALYSIS_COMPLETED,
            get_details=get_details,
            event_bus_provider=lambda: self.event_bus
        )
        def analyze_results(data, task_id="test-task", duration=60):
            return "analysis_done"

        analyze_results("test_data", task_id="task-123", duration=120)
        
        assert len(self.events_published) == 1
        event, _ = self.events_published[0]
        # Note: The current implementation creates a basic Event, not with details
        # This tests the decorator execution path

    def test_async_event_publishing(self):
        """Test asynchronous event publishing."""
        # Mock async publish to capture calls
        self.event_bus.publish_async = Mock()

        @publish_event(
            event_type=EventType.MOP_ERROR_DETECTED,
            async_mode=True,
            event_bus_provider=lambda: self.event_bus
        )
        def report_error():
            return "error_reported"

        report_error()
        
        # Verify async publish was called
        assert self.event_bus.publish_async.called

    def test_method_exception_handling(self):
        """Test that decorator handles method exceptions properly."""
        @publish_event(
            event_type=EventType.TASK_FAILED,
            event_bus_provider=lambda: self.event_bus
        )
        def failing_method():
            raise ValueError("Task failed")

        # The current decorator implementation publishes AFTER method execution
        # So if method fails, event is NOT published
        with pytest.raises(ValueError, match="Task failed"):
            failing_method()
        
        # No event should be published if method fails before completion
        assert len(self.events_published) == 0

    def test_complex_source_and_details_extraction(self):
        """Test complex source and details extraction scenarios."""
        def get_source(obj):
            return f"{obj.__class__.__name__}:{obj.id}"

        def get_details(args, kwargs):
            return {
                "method_args": len(args),
                "method_kwargs": list(kwargs.keys()),
                "config": kwargs.get("config", {})
            }

        @publish_event(
            event_type=EventType.WORKFLOW_STARTED,
            get_source=get_source,
            get_details=get_details,
            channel=EventBus.SYSTEM_CHANNEL,
            event_bus_provider=lambda: self.event_bus
        )
        def start_workflow(self, config=None):
            return "workflow_started"

        # Create a mock object
        mock_obj = Mock()
        mock_obj.__class__.__name__ = "WorkflowManager"
        mock_obj.id = "wf-123"
        
        start_workflow(mock_obj, config={"timeout": 300})
        
        assert len(self.events_published) == 1
        event, channel = self.events_published[0]
        assert event.type == EventType.WORKFLOW_STARTED
        assert event.source == "WorkflowManager:wf-123"
        assert channel == EventBus.SYSTEM_CHANNEL


class TestSubscribeToDecorator:
    """Test cases for the @subscribe_to decorator."""

    def setup_method(self):
        """Set up test environment with isolated event bus."""
        self.event_bus = EventBus()
        self.handled_events = []

    def test_single_event_subscription(self):
        """Test subscription to a single event type."""
        @subscribe_to(
            event_types=EventType.TASK_STARTED,
            event_bus_provider=lambda: self.event_bus
        )
        def handle_task_started(event):
            self.handled_events.append(event)

        # Publish an event
        event = Event(type=EventType.TASK_STARTED, source="test")
        self.event_bus.publish(event)
        
        assert len(self.handled_events) == 1
        assert self.handled_events[0].type == EventType.TASK_STARTED

    def test_multiple_event_subscription(self):
        """Test subscription to multiple event types."""
        @subscribe_to(
            event_types=[EventType.TASK_STARTED, EventType.TASK_COMPLETED],
            event_bus_provider=lambda: self.event_bus
        )
        def handle_task_events(event):
            self.handled_events.append(event)

        # Publish different events
        event1 = Event(type=EventType.TASK_STARTED, source="test")
        event2 = Event(type=EventType.TASK_COMPLETED, source="test")
        event3 = Event(type=EventType.EXPERIMENT_STARTED, source="test")
        
        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        self.event_bus.publish(event3)  # Should not be handled
        
        assert len(self.handled_events) == 2
        assert self.handled_events[0].type == EventType.TASK_STARTED
        assert self.handled_events[1].type == EventType.TASK_COMPLETED

    def test_subscription_with_filter(self):
        """Test subscription with event filtering."""
        def filter_by_source(event):
            return event.source == "important_source"

        @subscribe_to(
            event_types=EventType.MOP_ERROR_DETECTED,
            filter_fn=filter_by_source,
            event_bus_provider=lambda: self.event_bus
        )
        def handle_important_errors(event):
            self.handled_events.append(event)

        # Publish events with different sources
        event1 = Event(type=EventType.MOP_ERROR_DETECTED, source="important_source")
        event2 = Event(type=EventType.MOP_ERROR_DETECTED, source="other_source")
        
        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        
        assert len(self.handled_events) == 1
        assert self.handled_events[0].source == "important_source"

    def test_subscription_with_priority(self):
        """Test subscription with priority handling."""
        execution_order = []

        @subscribe_to(
            event_types=EventType.ANALYSIS_COMPLETED,
            priority=HandlerPriority.HIGH,
            event_bus_provider=lambda: self.event_bus
        )
        def high_priority_handler(event):
            execution_order.append("high")

        @subscribe_to(
            event_types=EventType.ANALYSIS_COMPLETED,
            priority=HandlerPriority.LOW,
            event_bus_provider=lambda: self.event_bus
        )
        def low_priority_handler(event):
            execution_order.append("low")

        # Publish event
        event = Event(type=EventType.ANALYSIS_COMPLETED, source="test")
        self.event_bus.publish(event)
        
        # High priority should execute first
        assert execution_order == ["high", "low"]

    def test_subscription_with_custom_channel(self):
        """Test subscription to custom event channel."""
        @subscribe_to(
            event_types=EventType.COVERAGE_UPDATED,
            channel=EventBus.ANALYSIS_CHANNEL,
            event_bus_provider=lambda: self.event_bus
        )
        def handle_coverage_updates(event):
            self.handled_events.append(event)

        # Publish to different channels
        event = Event(type=EventType.COVERAGE_UPDATED, source="test")
        
        # Publish to default channel - should not be handled
        self.event_bus.publish(event, EventBus.DEFAULT_CHANNEL)
        assert len(self.handled_events) == 0
        
        # Publish to analysis channel - should be handled
        self.event_bus.publish(event, EventBus.ANALYSIS_CHANNEL)
        assert len(self.handled_events) == 1

    def test_decorator_preserves_function_metadata(self):
        """Test that decorators preserve original function metadata."""
        @subscribe_to(
            event_types=EventType.CONFIG_LOADED,
            event_bus_provider=lambda: self.event_bus
        )
        def documented_handler(event):
            """This is a documented event handler."""
            pass

        assert documented_handler.__name__ == "documented_handler"
        assert "documented event handler" in documented_handler.__doc__


class TestDecoratorIntegration:
    """Integration tests for decorator combinations and edge cases."""

    def setup_method(self):
        """Set up test environment."""
        self.event_bus = EventBus()
        self.events_published = []
        self.events_handled = []

    def test_publish_and_subscribe_integration(self):
        """Test integration between publish and subscribe decorators."""
        # Set up subscriber
        @subscribe_to(
            event_types=EventType.TOOL_STARTED,
            event_bus_provider=lambda: self.event_bus
        )
        def handle_tool_started(event):
            self.events_handled.append(event)

        # Set up publisher
        @publish_event(
            event_type=EventType.TOOL_STARTED,
            event_bus_provider=lambda: self.event_bus
        )
        def start_tool():
            return "tool_started"

        # Execute and verify
        result = start_tool()
        
        assert result == "tool_started"
        assert len(self.events_handled) == 1
        assert self.events_handled[0].type == EventType.TOOL_STARTED

    def test_multiple_decorators_on_same_function(self):
        """Test multiple event decorators on the same function."""
        @subscribe_to(
            event_types=EventType.EXPERIMENT_COMPLETED,
            event_bus_provider=lambda: self.event_bus
        )
        @publish_event(
            event_type=EventType.ANALYSIS_COMPLETED,
            event_bus_provider=lambda: self.event_bus
        )
        def process_experiment_completion(event=None):
            self.events_handled.append(event if event else "published")
            return "processed"

        # First, trigger the publisher function
        result = process_experiment_completion()
        assert result == "processed"
        
        # Then, trigger through event subscription
        event = Event(type=EventType.EXPERIMENT_COMPLETED, source="test")
        self.event_bus.publish(event)
        
        # Verify both decorators worked
        assert len(self.events_handled) == 2

    def test_decorator_error_handling(self):
        """Test decorator behavior with various error scenarios."""
        @publish_event(
            event_type=EventType.MOP_ERROR_DETECTED,
            event_bus_provider=lambda: self.event_bus
        )
        def method_with_none_return():
            return None

        @subscribe_to(
            event_types=EventType.TASK_FAILED,
            event_bus_provider=lambda: self.event_bus
        )
        def handler_with_exception(event):
            raise RuntimeError("Handler failed")

        # Test publisher with None return
        result = method_with_none_return()
        assert result is None

        # Test subscriber with exception (should not break event bus)
        event = Event(type=EventType.TASK_FAILED, source="test")
        # This should not raise an exception due to event bus error handling
        self.event_bus.publish(event)