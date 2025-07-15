# Event System Documentation

This document describes the event system in the RVAndroid framework, which follows a publish-subscribe pattern for loose coupling between components.

## Core Concepts

### Event Types

Events are categorized by `EventType` enum values that represent different system actions and state transitions:

- **Task Lifecycle Events**: `TASK_CREATED`, `TASK_CONFIGURED`, `TASK_STARTED`, `TASK_COMPLETED`, `TASK_FAILED`
- **Experiment Lifecycle Events**: `EXPERIMENT_STARTED`, `EXPERIMENT_COMPLETED`, `EXPERIMENT_FAILED`, `EXPERIMENT_PAUSED`, `EXPERIMENT_RESUMED`
- **Orchestration Events**: `ORCHESTRATION_EVENT`
- **Analysis Events**: `COVERAGE_UPDATED`, `COVERAGE_TRACKING_STARTED`, `COVERAGE_TRACKING_STOPPED`, `ERROR_DETECTED`, `STATIC_ANALYSIS_COMPLETED`, `NEW_METHOD_DISCOVERED`
- **Environment Lifecycle Events**: `EMULATOR_STARTED`, `EMULATOR_STOPPED`, `APP_INSTALLED`, `TOOL_STARTED`, `TOOL_STOPPED`
- **Configuration Events**: `CONFIG_LOADED`, `CONFIG_SAVED`

### Event Channels

Events can be published to specific channels that separate concerns:

- `SYSTEM_CHANNEL`: System-level events for core framework operations
- `LIFECYCLE_CHANNEL`: Events related to task and experiment lifecycles
- `ANALYSIS_CHANNEL`: Events for analysis operations and results
- `ERROR_CHANNEL`: Error-related events
- `USER_CHANNEL`: User-triggered events and interactions
- `DEFAULT_CHANNEL`: Default channel for events without a specified channel

### Event Models

Different event types carry different payload structures:

- `Event`: Base class for all events with type, timestamp, and source
- `TaskEvent`: Events specific to a task, with task ID, config, and details
- `ExperimentEvent`: Events for experiment-level operations
- `AnalysisEvent`: Events containing analysis results

### Event Handlers

Handlers process events when they're published:

- Handlers can have different priority levels (`LOW`, `NORMAL`, `HIGH`, `CRITICAL`)
- Handlers can include filter functions to selectively process events
- Handlers may include metadata for additional context

## Using the Event System

### Publishing Events

```python
# Get the shared event bus instance
event_bus = EventBus.get_instance()

# Publish a task event
event_bus.publish_task_event(
    event_type=EventType.TASK_STARTED,
    task_id="123e4567-e89b-12d3-a456-426614174000",  # UUID as string
    task_config={"tool": "monkey", "duration": 60},
    details={"device_id": "emulator-5554"},
    source="TaskExecutor"
)

# Publish an experiment event
event_bus.publish_experiment_event(
    event_type=EventType.EXPERIMENT_STARTED,
    experiment_id="exp-001",
    message="Started experiment with Monkey tool",
    affected_tasks=["123e4567-e89b-12d3-a456-426614174000"],
    source="ExperimentController"
)

# Publish an analysis event
event_bus.publish_analysis_event(
    event_type=EventType.COVERAGE_UPDATED,
    data={"method_count": 120, "coverage_percentage": 45.5},
    related_task_id="123e4567-e89b-12d3-a456-426614174000",
    source="CoverageTracker"
)

# Publish an error event
try:
    # Some operation that might fail
    pass
except Exception as e:
    event_bus.publish_error_event(
        error=e,
        context={"task_id": "123e4567-e89b-12d3-a456-426614174000", "operation": "TaskExecution"}
    )
```

### Asynchronous Publishing

```python
# Publish event asynchronously 
event_bus.publish_task_event(
    event_type=EventType.TASK_STARTED,
    task_id="123e4567-e89b-12d3-a456-426614174000",
    source="TaskExecutor",
    async_mode=True  # This makes the event publish asynchronously
)

# Publish with a callback
def on_event_processed(event, handler_count):
    print(f"Event {event} was processed by {handler_count} handlers")

event_bus.publish_with_callback(
    event=task_event,
    callback=on_event_processed
)
```

### Subscribing to Events

```python
# Simple subscription
def on_task_started(event):
    print(f"Task {event.task_id} started")

event_bus.subscribe(
    event_type=EventType.TASK_STARTED,
    callback=on_task_started
)

# Subscription with filter
def on_coverage_updated(event):
    print(f"Coverage updated: {event.data.get('coverage_percentage')}%")

def filter_high_coverage(event):
    return event.data.get('coverage_percentage', 0) > 50

event_bus.subscribe(
    event_type=EventType.COVERAGE_UPDATED,
    callback=on_coverage_updated,
    filter_fn=filter_high_coverage,
    priority=HandlerPriority.HIGH,
    channel=EventBus.ANALYSIS_CHANNEL
)

# Subscribe to multiple event types
event_bus.subscribe_many(
    event_types=[EventType.TASK_STARTED, EventType.TASK_COMPLETED, EventType.TASK_FAILED],
    callback=task_state_changed_handler
)
```

### Unsubscribing

```python
# Unsubscribe by handler ID
handler_id = event_bus.subscribe(EventType.TASK_STARTED, callback)
event_bus.unsubscribe_by_handler(EventType.TASK_STARTED, handler_id)

# Unsubscribe all instances of a callback
event_bus.unsubscribe_all(callback)

# Unsubscribe from specific channels
event_bus.unsubscribe_all(callback, channels=[EventBus.ANALYSIS_CHANNEL, EventBus.ERROR_CHANNEL])
```

### Using Event Channels

```python
# Subscribe to a specific channel
event_bus.subscribe(
    event_type=EventType.COVERAGE_UPDATED,
    callback=on_coverage_updated,
    channel=EventBus.ANALYSIS_CHANNEL
)

# Publish to a specific channel
event_bus.publish(event, channel=EventBus.ANALYSIS_CHANNEL)

# Helper methods automatically use appropriate channels
event_bus.publish_task_event(...)  # Uses LIFECYCLE_CHANNEL by default
event_bus.publish_analysis_event(...)  # Uses ANALYSIS_CHANNEL by default
event_bus.publish_error_event(...)  # Uses ERROR_CHANNEL by default
```

## Best Practices

1. **Use Event Channels**: Organize events by channel to maintain separation of concerns

2. **Consider Priority Levels**: Set appropriate priorities for handlers:
   - `CRITICAL`: Essential system operations that must run first
   - `HIGH`: Important handlers that should run before most others
   - `NORMAL`: Default handlers with standard priority
   - `LOW`: Background handlers that can run after others

3. **Use Asynchronous Events** for non-blocking operations:
   - `publish_async()` for fire-and-forget events
   - `publish_with_callback()` when you need completion notification

4. **Prefer Helper Methods** over direct event creation:
   - `publish_task_event()`
   - `publish_experiment_event()`
   - `publish_analysis_event()`
   - `publish_error_event()`

5. **Use Dependency Injection** with `EventBus.create_instance()` for components that need their own event bus

6. **Clean Up Subscriptions** when components are destroyed to prevent memory leaks:
   - Call `unsubscribe_all()` in component cleanup methods

7. **Use UUIDs for Task IDs** rather than integers for distributed safety

## Advanced Usage

### Creating a Service with its Own Event Bus

```python
class AnalysisService:
    def __init__(self):
        # Create a dedicated event bus for this service
        self.event_bus = EventBus.create_instance()
        
        # Set up internal event handling
        self.event_bus.subscribe(EventType.COVERAGE_UPDATED, self._on_coverage_updated)
    
    def _on_coverage_updated(self, event):
        # Internal handler
        pass
    
    def publish_result(self, result_data):
        # Publish to the service's internal event bus
        self.event_bus.publish_analysis_event(
            event_type=EventType.COVERAGE_UPDATED,
            data=result_data
        )
        
        # Also publish to the global event bus
        global_bus = EventBus.get_instance()
        global_bus.publish_analysis_event(
            event_type=EventType.COVERAGE_UPDATED,
            data=result_data
        )
```

### Using Event History for Diagnostics

```python
# Get recent error events
error_events = event_bus.get_history(
    event_type=EventType.ERROR_DETECTED,
    since=datetime.now() - timedelta(hours=1),
    limit=10
)

# Print details of recent errors
for event in error_events:
    print(f"Error at {event.timestamp}: {event.data.get('error_message')}")
    
# Get task history for a specific task
task_events = event_bus.get_history(
    task_id="123e4567-e89b-12d3-a456-426614174000"
)

# Reconstruct task timeline
for event in sorted(task_events, key=lambda e: e.timestamp):
    print(f"{event.timestamp}: {event.type.name}")
```

### Proper Shutdown

```python
# Clean shutdown at application exit
def shutdown_application():
    event_bus = EventBus.get_instance()
    event_bus.shutdown(wait_for_completion=True)
    
# Register shutdown handler
atexit.register(shutdown_application)
```