
import pytest
from unittest.mock import MagicMock, patch
from rv_android_core.event.decorators import publish_event, subscribe_to
from rv_android_core.event.models import Event, EventType, EventChannel, EventPriority
from rv_android_core.event.bus import EventBus
from rv_android_core.event.handler import HandlerPriority

# Fixture for a mock EventBus
@pytest.fixture
def mock_event_bus():
    return MagicMock(spec=EventBus)

# Tests for publish_event decorator
class TestPublishEventDecorator:

    def test_publish_event_sync(self, mock_event_bus):
        @publish_event(event_type=EventType.CUSTOM, async_mode=False, event_bus_provider=lambda: mock_event_bus)
        def my_function():
            return "result"

        result = my_function()
        assert result == "result"
        mock_event_bus.publish.assert_called_once()
        args, kwargs = mock_event_bus.publish.call_args
        published_event = args[0]
        assert isinstance(published_event, Event)
        assert published_event.type == EventType.CUSTOM
        assert published_event.source is None
        assert kwargs['channel'] == EventChannel.DEFAULT

    def test_publish_event_async(self, mock_event_bus):
        @publish_event(event_type=EventType.CUSTOM, async_mode=True, channel=EventChannel.LIFECYCLE, priority=EventPriority.HIGH, event_bus_provider=lambda: mock_event_bus)
        def my_function():
            pass

        my_function()
        mock_event_bus.publish_async.assert_called_once()
        args, kwargs = mock_event_bus.publish_async.call_args
        published_event = args[0]
        assert isinstance(published_event, Event)
        assert published_event.type == EventType.CUSTOM
        assert kwargs['channel'] == EventChannel.LIFECYCLE
        assert kwargs['priority'] == EventPriority.HIGH

    def test_publish_event_with_source_and_details(self, mock_event_bus):
        def get_source_fn(instance):
            return instance.name

        def get_details_fn(args, kwargs):
            return {"arg1": args[1], "kwarg1": kwargs.get("kwarg1")}

        class MyClass:
            def __init__(self, name):
                self.name = name

            @publish_event(event_type=EventType.CUSTOM, get_source=get_source_fn, get_details=get_details_fn, event_bus_provider=lambda: mock_event_bus)
            def my_method(self, arg1, kwarg1=None):
                return True

        instance = MyClass("test_instance")
        instance.my_method("value1", kwarg1="value2")

        mock_event_bus.publish.assert_called_once()
        args, _ = mock_event_bus.publish.call_args
        published_event = args[0]
        assert published_event.source == "test_instance"
        # Note: Event details are not directly stored in the base Event object,
        # but would be in a custom Event subclass. Here we just check the source.

# Tests for subscribe_to decorator
class TestSubscribeToDecorator:

    def test_subscribe_to_single_event_type(self, mock_event_bus):
        @subscribe_to(event_types=EventType.CUSTOM, event_bus_provider=lambda: mock_event_bus)
        def my_handler(event):
            pass

        # The decorator is applied at definition time, so subscribe should be called
        mock_event_bus.subscribe.assert_called_once()
        args, kwargs = mock_event_bus.subscribe.call_args
        assert kwargs['event_type'] == EventType.CUSTOM
        assert kwargs['callback'] == my_handler
        assert kwargs['channel'] == EventChannel.DEFAULT

    def test_subscribe_to_multiple_event_types(self, mock_event_bus):
        @subscribe_to(event_types=[EventType.CUSTOM, EventType.TASK_STARTED], channel=EventChannel.ANALYSIS, priority=HandlerPriority.HIGH, event_bus_provider=lambda: mock_event_bus)
        def my_handler(event):
            pass

        assert mock_event_bus.subscribe.call_count == 2
        # Check calls for each event type
        calls = mock_event_bus.subscribe.call_args_list
        assert any(call.kwargs['event_type'] == EventType.CUSTOM for call in calls)
        assert any(call.kwargs['event_type'] == EventType.TASK_STARTED for call in calls)
        assert all(call.kwargs['channel'] == EventChannel.ANALYSIS for call in calls)
        assert all(call.kwargs['priority'] == HandlerPriority.HIGH for call in calls)

    def test_subscribe_to_with_filter(self, mock_event_bus):
        def my_filter(event):
            return event.source == "filtered_source"

        @subscribe_to(event_types=EventType.CUSTOM, filter_fn=my_filter, event_bus_provider=lambda: mock_event_bus)
        def my_handler(event):
            pass

        mock_event_bus.subscribe.assert_called_once()
        args, kwargs = mock_event_bus.subscribe.call_args
        assert kwargs['filter_fn'] == my_filter
