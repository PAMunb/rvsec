# CLAUDE.md - rv-android-core

## Purpose

rv-android-core is the foundational infrastructure module for the RV-Android framework, providing shared domain models, event-driven communication system, error handling, logging, and utility components used across all other modules. It establishes the architectural patterns and core abstractions that enable modular design, type-safe validation through Pydantic, and consistent behavior across the runtime verification system for Android applications.

## Architecture

### Key Patterns and Design Decisions

- **Singleton Pattern**: Core services (EventBus, ErrorHandler, LoggingManager, PerformanceMonitor) use thread-safe singletons for global access
- **Event-Driven Communication**: Publish-subscribe EventBus enables decoupled component communication with typed events and channels
- **Pydantic Validation**: All domain models inherit from `BaseValidatedModel` for comprehensive validation and serialization
- **Decorator-Based Error Handling**: `@ErrorHandler.handle_errors()` provides Spring-like automatic error management
- **Template Method Pattern**: `AbstractTool` defines execution workflow for all testing tools
- **Circuit Breaker Pattern**: `CommandCircuitBreaker` provides resilience against repeatedly failing commands

### Key Components

| Component | Purpose |
|-----------|---------|
| `EventBus` | Central pub/sub system for decoupled event communication across modules |
| `ErrorHandler` | Unified error management with type-specific handlers and decorators |
| `LoggingManager` | Centralized logging with context injection and structured formatting |
| `BaseValidatedModel` | Pydantic base class for all validated domain models |
| `Command` | System command execution with timeout and process management |
| `AbstractTool` | Base class defining contract for all testing tools |
| `PerformanceMonitor` | Metrics collection and timing measurement system |

## Directory Structure

```
src/rv_android_core/
├── __init__.py
├── constants.py
├── analysis/
│   ├── __init__.py
│   └── base_analyzer.py          # Base class for analysis tools
├── commands/
│   ├── __init__.py
│   ├── circuit_breaker.py        # Circuit breaker for command resilience
│   ├── command.py                # Command execution with validation
│   ├── command_exception.py
│   ├── command_not_found_error.py
│   └── command_result.py         # Structured command results
├── domain/
│   ├── __init__.py
│   ├── app.py                    # Android application model (APK metadata)
│   ├── classes.py                # Java class/method models
│   ├── dynamic_wtg.py            # Dynamic Window Transition Graph
│   ├── log.py                    # Coverage and error log models
│   ├── static.py                 # Static analysis data models
│   ├── task.py                   # Task configuration and execution models
│   ├── widget.py                 # Android UI widget models
│   └── wtg.py                    # Window Transition Graph models
├── event/
│   ├── __init__.py
│   ├── bus.py                    # EventBus implementation
│   ├── decorators.py             # Event publishing decorators
│   ├── handler.py                # Event handler with priority support
│   ├── models.py                 # Event type definitions
│   └── utils.py                  # Event filtering utilities
├── tools/
│   ├── __init__.py
│   ├── abstract_tool.py          # Base class for testing tools
│   └── tool_spec.py              # Tool specification model
└── util/
    ├── __init__.py
    ├── decorators.py
    ├── diagnostics.py
    ├── jar_resolver.py           # JAR file resolution
    ├── json_helpers.py
    ├── utils.py
    ├── android/
    │   ├── __init__.py
    │   ├── emulator_manager.py   # Android emulator control
    │   ├── logcat_manager.py     # Logcat capture management
    │   └── repository_initializer.py
    ├── error/
    │   ├── __init__.py
    │   ├── error_handler.py      # Centralized error handling
    │   └── exceptions.py         # Exception hierarchy (~450 lines)
    ├── logging/
    │   ├── __init__.py
    │   ├── constants.py          # Logging constants
    │   ├── context_adapter.py    # Context-aware logging adapter
    │   ├── formatters.py         # JSON and structured formatters
    │   └── manager.py            # LoggingManager singleton
    ├── performance/
    │   ├── __init__.py
    │   ├── configuration.py      # Performance monitor config
    │   └── performance_monitor.py # Metrics collection
    └── validation/
        ├── __init__.py
        ├── base.py               # BaseValidatedModel
        ├── config.py             # Validation configuration
        └── decorators.py         # @validated_model decorator
```

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `domain/task.py` | Task, TaskConfiguration, TaskResult models | ~920 |
| `event/models.py` | Event types, channels, and event classes | ~725 |
| `util/error/error_handler.py` | ErrorHandler with 30+ type-specific handlers | ~990 |
| `event/bus.py` | EventBus with async processing and channels | ~530 |
| `util/error/exceptions.py` | Complete exception hierarchy | ~450 |
| `util/logging/manager.py` | LoggingManager with context support | ~415 |
| `tools/abstract_tool.py` | AbstractTool base class | ~410 |
| `domain/widget.py` | Widget and WidgetEvent models | ~365 |
| `util/performance/performance_monitor.py` | PerformanceMonitor with metrics | ~345 |
| `commands/command.py` | Command execution with validation | ~335 |

## Dependencies

### Internal (rv-android modules)
- None (this is the core foundation module)

### External
- `pydantic` ^2.9.0 - Data validation and settings management
- `androguard` 3.4.0a1 - Android APK metadata extraction
- `psutil` ^7.0.0 - Process management utilities
- `networkx` ^3.5 - Graph data structures for WTG

## Testing

```bash
cd modules/rv-android-core

# Run all tests
poetry run pytest tests/ -v

# Run with coverage
poetry run pytest tests/ --cov=src --cov-report=html

# Run specific test categories
poetry run pytest tests/domain/ -v      # Domain model tests
poetry run pytest tests/event/ -v       # Event system tests
poetry run pytest tests/util/ -v        # Utility tests
poetry run pytest tests/commands/ -v    # Command execution tests
```

## Common Tasks

### Using the Event System
```python
from rv_android_core.event import EventBus, EventType, EventChannel

# Get singleton instance
event_bus = EventBus.get_instance()

# Subscribe to events
event_bus.subscribe(
    event_type=EventType.TASK_COMPLETED,
    callback=lambda e: print(f"Task {e.task_id} completed"),
    channel=EventChannel.LIFECYCLE
)

# Publish task events
event_bus.publish_task_event(
    event_type=EventType.TASK_STARTED,
    task_id="uuid-string",
    task_config={"tool": "rvagent"},
    source="TaskExecutor"
)
```

### Using the Error Handler
```python
from rv_android_core.util.error.error_handler import ErrorHandler

# Decorator-based error handling
@ErrorHandler.handle_errors(component="MyComponent", phase="execution")
def risky_operation():
    # Errors automatically logged and handled
    pass

# Context manager for scoped error handling
with ErrorHandler.get_instance().error_context(component="MyComponent"):
    risky_operation()
```

### Creating Validated Domain Models
```python
from rv_android_core.util.validation import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model
from pydantic import Field

@validated_model(['name', 'value'])
class MyModel(BaseValidatedModel):
    name: str = Field(..., description="Model name")
    value: int = Field(default=0, description="Model value")
```

### Using the Logging System
```python
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT

logging_manager = LoggingManager.get_instance()
logger = logging_manager.get_logger(
    "my_module.my_class",
    {CONTEXT_COMPONENT: "MyComponent"}
)

# Context-aware logging
with logger.with_context(task_id="123"):
    logger.info("Processing task")
```

### Executing System Commands
```python
from rv_android_core.commands import Command, CommandResult

# Create and execute command with timeout
cmd = Command(command="adb", args=["devices"], timeout=30.0)
result: CommandResult = cmd.invoke()

if result.is_success():
    print(result.get_stdout_text())
```

### Creating Testing Tools
```python
from rv_android_core.tools import AbstractTool, ToolSpec
from rv_android_core.domain.task import Task
from rv_android_core.domain.app import App

class MyTool(AbstractTool):
    def __init__(self):
        super().__init__(
            name="mytool",
            description="My custom testing tool",
            process_pattern="mytool"
        )

    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        return {"default": {"timeout": 300}}

    @classmethod
    def get_tool_spec(cls) -> ToolSpec:
        return ToolSpec(name="mytool", tool_class=cls)

    def configure(self, config: Dict[str, Any]) -> None:
        self.timeout = config.get("timeout", 300)

    def execute_tool_specific_logic(self, task: Task, app: App) -> None:
        # Tool implementation here
        pass
```


## Development Notes

This module is part of the RV-Android Poetry workspace. All modules are installed in **editable mode** via the root `pyproject.toml`.

**Key points:**
- Run `poetry install` from the project root to install all modules
- Source code changes are reflected immediately (no reinstall needed)
- Only reinstall if `pyproject.toml` dependencies change

```bash
# From project root
poetry install          # Install/update all modules
poetry install --sync   # Also remove unused packages
```

