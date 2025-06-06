# rvandroid/experiment/event/__init__.py
"""
Event system for decoupled communication across the rv-android framework.

This module provides a comprehensive event system that enables components
to communicate without direct dependencies. It supports type-safe event
handling, event filtering, comprehensive event tracking, and asynchronous processing.

Overview
--------
The event system consists of several key components:

1. Events: Data objects that carry information about things that have happened
   - Event: Base class for all events
   - TaskEvent: Event related to a specific task
   - ExperimentEvent: Event related to the overall experiment
   - AnalysisEvent: Event related to analysis results

2. EventBus: Communication channel for publishing and subscribing to events
   - Publishes events to all subscribers
   - Maintains event history for later retrieval
   - Supports filtering events based on various criteria
   - Provides async event processing with priorities
   - Supports specialized event channels for different aspects of the system

3. EventProcessor: Handles event processing details
   - Processes events based on priority
   - Manages concurrency for asynchronous events
   - Provides result tracking and error handling

4. EventHandler: Processes events from the event bus
   - Supports priority levels for controlling order of execution
   - Provides optional filtering for selective processing
   - Can include additional metadata for context

5. EventType: Enumeration of supported event types
   - Task lifecycle events (TASK_CREATED, TASK_STARTED, etc.)
   - Experiment lifecycle events (EXPERIMENT_STARTED, etc.)
   - Analysis events (COVERAGE_UPDATED, etc.)
   - Environment and configuration events

Example Usage
------------

Publishing Events:
```python
from rv_android_core.experiment.event import EventBus, EventType

# Get the singleton event bus
event_bus = EventBus.get_instance()

# Publish a task event
event_bus.publish_task_event(
    event_type=EventType.TASK_STARTED,
    task_id="123e4567-e89b-12d3-a456-426614174000",  # UUID as string
    task_config={"tool": "monkey", "duration": 60},
    details={"device_id": "emulator-5554"},
    source="TaskExecutor"
)

# Publish asynchronously
event_bus.publish_task_event(
    event_type=EventType.TASK_COMPLETED,
    task_id="123e4567-e89b-12d3-a456-426614174000",
    async_mode=True
)
```

Subscribing to Events:
```python
from rv_android_core.experiment.event import EventBus, EventType, HandlerPriority

# Simple subscription
def on_task_started(event):
    print(f"Task {event.task_id} started")

event_bus.subscribe(
    event_type=EventType.TASK_STARTED,
    callback=on_task_started
)

# Subscribe with priority and filter
def on_critical_error(event):
    print(f"Critical error: {event.data.get('error_message')}")

def is_critical_error(event):
    return event.data.get('error_type') in ['CriticalError', 'SystemCrash']

event_bus.subscribe(
    event_type=EventType.ERROR_DETECTED,
    callback=on_critical_error,
    filter_fn=is_critical_error,
    priority=HandlerPriority.CRITICAL,
    channel=EventBus.ERROR_CHANNEL
)
```

Using Event Channels:
```python
from rv_android_core.experiment.event import EventBus, EventType

# Subscribe to analysis channel
event_bus.subscribe(
    event_type=EventType.COVERAGE_UPDATED,
    callback=on_coverage_updated,
    channel=EventBus.ANALYSIS_CHANNEL
)

# Publish to analysis channel
event_bus.publish(event, channel=EventBus.ANALYSIS_CHANNEL)
```

For more detailed usage examples, see the README.md file in this directory.
"""

# Export event models
from rv_android_core.experiment.event.models import Event, EventType, TaskEvent, ExperimentEvent, AnalysisEvent

# Export event bus and processor
from rv_android_core.experiment.event.bus import EventBus
from rv_android_core.experiment.event.processor import EventProcessor, ProcessingMode, ProcessingResult

# Export provider
from rv_android_core.experiment.event.provider import EventBusProvider

# Export decorators
from rv_android_core.experiment.event.decorators import publish_event, subscribe_to

# Export handler and priority
from rv_android_core.experiment.event.handler import EventHandler, HandlerPriority

# Export utility functions
from rv_android_core.experiment.event.utils import (
    filter_events_by_task,
    filter_events_by_experiment,
    filter_events_by_type,
    filter_events_by_source,
    filter_events_by_time_range,
    group_events_by_type,
    find_related_task_events,
    extract_task_timeline,
    find_unique_task_ids,
    find_unique_experiment_ids
)

# Convenience functions
def get_event_bus() -> EventBus:
    """
    Get the singleton event bus instance.
    
    Returns:
        EventBus instance
    """
    return EventBus.get_instance()
    
def create_event_bus(worker_threads=4, max_queue_size=1000) -> EventBus:
    """
    Create a new independent event bus instance.
    
    Args:
        worker_threads: Number of worker threads for async processing
        max_queue_size: Maximum size of the event queue
    
    Returns:
        New EventBus instance
    """
    return EventBus(is_singleton=False, worker_threads=worker_threads, max_queue_size=max_queue_size)

# Define the exported API
__all__ = [
    # Event models
    'Event', 'EventType', 'TaskEvent', 'ExperimentEvent', 'AnalysisEvent',
    
    # EventBus and processor
    'EventBus', 'EventProcessor', 'ProcessingMode', 'ProcessingResult',
    
    # Handler and priority
    'EventHandler', 'HandlerPriority',
    
    # Utility functions
    'filter_events_by_task', 'filter_events_by_experiment', 
    'filter_events_by_type', 'filter_events_by_source',
    'filter_events_by_time_range', 'group_events_by_type',
    'find_related_task_events', 'extract_task_timeline',
    'find_unique_task_ids', 'find_unique_experiment_ids',
    
    # Convenience functions
    'get_event_bus', 'create_event_bus',
    
    # Provider
    'EventBusProvider',
    
    # Decorators
    'publish_event', 'subscribe_to'
]