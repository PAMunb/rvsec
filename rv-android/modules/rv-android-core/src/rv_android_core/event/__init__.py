# rv_android_core/event/__init__.py
"""
Event system for decoupled communication across the rv-android framework.

This module provides a comprehensive event system that enables components
to communicate without direct dependencies through a publish-subscribe pattern.
The system supports type-safe event handling, event filtering, event history
tracking, and asynchronous event processing.

### Architectural Design:
- Implements centralized event bus with singleton pattern
- Provides type-safe event models with hierarchical structure
- Supports channel-based event organization for different system aspects
- Enables priority-based event handling with flexible filtering
- Maintains event history for debugging and analysis purposes

### Core Components:
1. EventBus: Central communication hub for publishing and subscribing to events
2. Event Models: Hierarchical event types (Event, TaskEvent, ExperimentEvent, CoverageEvent, MOPErrorEvent)
3. EventHandler: Configurable event processors with priority and filtering support
4. EventType: Enumeration of all supported event types across the system
5. Decorators: Declarative event integration for methods and functions

### Event Channels:
- EventChannel.DEFAULT: General system events without specific category
- EventChannel.LIFECYCLE: Task and experiment lifecycle events (including coverage and MOP events)
- EventChannel.ANALYSIS: General analysis results and static analysis events
- EventChannel.ERROR: Error events and exception handling notifications

### Usage Examples:

Publishing Events:
```python
from rv_android_core.event import EventBus, EventType

# Get the singleton event bus
event_bus = EventBus.get_instance()

# Publish a task event
event_bus.publish_task_event(
    event_type=EventType.TASK_STARTED,
    task_id="task-uuid-string",
    task_config={"tool": "monkey", "duration": 60},
    details={"device_id": "emulator-5554"},
    source="TaskExecutor"
)
```

Subscribing to Events:
```python
from rv_android_core.event import EventBus, EventType, HandlerPriority

event_bus = EventBus.get_instance()

def handle_task_completion(event):
    print(f"Task {event.task_id} completed")

event_bus.subscribe(
    event_type=EventType.TASK_COMPLETED,
    callback=handle_task_completion,
    priority=HandlerPriority.HIGH,
    channel=EventChannel.LIFECYCLE
)
```
"""

# Export event models
from rv_android_core.event.models import Event, EventType, TaskEvent, ExperimentEvent, CoverageEvent, MOPErrorEvent, EventChannel, EventPriority

# Export event bus
from rv_android_core.event.bus import EventBus

# Export decorators
from rv_android_core.event.decorators import publish_event, subscribe_to

# Export handler and priority
from rv_android_core.event.handler import EventHandler, HandlerPriority

# Export utility functions
from rv_android_core.event.utils import (
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

# Define the exported API
__all__ = [
    # Event models
    'Event', 'EventType', 'TaskEvent', 'ExperimentEvent', 'CoverageEvent', 'MOPErrorEvent', 'EventChannel', 'EventPriority',
    
    # EventBus
    'EventBus',
    
    # Handler and priority
    'EventHandler', 'HandlerPriority',
    
    # Utility functions
    'filter_events_by_task', 'filter_events_by_experiment', 
    'filter_events_by_type', 'filter_events_by_source',
    'filter_events_by_time_range', 'group_events_by_type',
    'find_related_task_events', 'extract_task_timeline',
    'find_unique_task_ids', 'find_unique_experiment_ids',
    
    # Decorators
    'publish_event', 'subscribe_to'
]