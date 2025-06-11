# RV-Android-Core Module

Foundation infrastructure module providing essential components, utilities, and abstractions for monitored operations testing in the RV-Android system.

## Overview

The RV-Android-Core module serves as the fundamental infrastructure layer for the entire RV-Android monitored operations ecosystem. It provides core abstractions, utilities, and components that enable consistent behavior across all specialized modules.

### Key Features

- **Infrastructure**: ErrorHandler with decorators, LoggingManager, EventBus for modular architecture
- **Domain Models**: Domain objects for Android applications, coverage, static analysis, and UI elements
- **Tool Abstractions**: Base classes for testing tool implementations with error handling
- **Utility Libraries**: Configuration management, performance monitoring, diagnostics
- **Event System**: Event-driven architecture for component communication
- **Type Safety**: Type annotations and validation throughout
- **Monitored Operations**: Support for both JCA cryptography and generic programming pattern specifications

## Architecture

### Core Components

#### Error Handling Infrastructure
- **ErrorHandler**: Centralized error management with context tracking and recovery strategies
- **Exception Hierarchy**: Specialized exceptions for different system components
- **Decorator Support**: `@ErrorHandler.handle_errors()` for automatic error handling
- **Context Management**: Rich error context for debugging and analysis

#### Logging Infrastructure
- **LoggingManager**: Standardized logging across all modules
- **ContextAdapter**: Contextual logging with automatic metadata injection
- **Formatters**: Consistent log formatting with structured output
- **Performance Integration**: Built-in performance monitoring and metrics

#### Event System
- **EventBus**: High-performance event distribution with channel management
- **EventProcessor**: Asynchronous event processing with guaranteed delivery
- **Event Models**: Type-safe event definitions for all system operations
- **Decorators**: Declarative event handling patterns

#### Domain Models
- **App**: Android application metadata and instrumentation tracking
- **Coverage**: Code coverage models with real-time tracking support
- **Static Analysis**: Unified static analysis data representation
- **UI Components**: Window, widget, and navigation graph models

#### Tool Infrastructure
- **AbstractTool**: Base abstraction for all testing tool implementations
- **ConfigurableTool**: Enhanced tool base with rich configuration support
- **ToolSpec**: Tool specification and metadata management

#### Utility Components
- **Configuration Management**: Type-safe configuration with validation
- **Performance Monitor**: Real-time performance tracking and metrics
- **Diagnostics**: System health monitoring and troubleshooting
- **Android Utilities**: Emulator management and Android SDK integration

### Integration Points

- **All RV-Android Modules**: Provides foundation infrastructure used by every module
- **External Tools**: Base classes for tool integration (Monkey, DroidBot, etc.)
- **Analysis Pipeline**: Domain models consumed by coverage and static analysis modules
- **Experiment Framework**: Event system and configuration used by rv-experiment
- **LLM Integration**: Base infrastructure used by rv-llm for error handling and logging

## Installation

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- Android SDK (for emulator management utilities)

### Setup

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Install in development mode
poetry install --extras dev
```

## Usage

### Error Handling

```python
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.exceptions import RVToolError

# Get singleton instance
error_handler = ErrorHandler.get_instance()

# Using context manager
with error_handler.error_context(component="MyComponent", operation="test_operation"):
    # Code that might fail
    if something_wrong:
        raise RVToolError("Tool execution failed", tool_name="droidbot")

# Using decorator
@ErrorHandler.handle_errors(component="Parser", phase="parsing")
def parse_data(data):
    # Errors automatically handled with context
    pass

# Manual error handling with context
try:
    risky_operation()
except Exception as e:
    context = error_handler.create_context(
        component="TestRunner",
        phase="execution", 
        task_id="123"
    )
    error_handler.handle_error(e, context)
```

### Logging

```python
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT

# Get logging manager
logging_manager = LoggingManager.get_instance()

# Create contextual logger
logger = logging_manager.get_logger(
    'tool.execution',
    {
        CONTEXT_COMPONENT: 'DroidBot',
        'tool_variant': 'dfs_greedy'
    }
)

# Use with context management
with logger.with_context(task_id="task_123", app_name="test.apk"):
    logger.info("Starting tool execution")
    # Context automatically included in all log messages
    logger.error("Tool execution failed")
```

### Event System

```python
from rv_android_core.event import EventBus, EventType, get_event_bus
from rv_android_core.event.models import TaskEvent

# Get event bus instance
event_bus = get_event_bus()

# Subscribe to events
def on_task_started(event: TaskEvent):
    print(f"Task {event.task_id} started")

event_bus.subscribe(EventType.TASK_STARTED, on_task_started)

# Publish events
event_bus.publish_task_event(
    EventType.TASK_STARTED,
    task_id="task_123",
    details={"tool": "monkey", "app": "test.apk"},
    source="TaskExecutor"
)

# Using event decorators
from rv_android_core.event.decorators import publish_event

@publish_event(EventType.TOOL_COMPLETED)
def execute_tool(self, task):
    # Tool execution logic
    return {"result": "success"}
```

### Domain Models

```python
from rv_android_core.app import App
from rv_android_core.domain.coverage import CoverageMetrics
from rv_android_core.domain.static import StaticAnalysisData

# Android application model
app = App("/path/to/app.apk")
print(f"Package: {app.package}")
print(f"Activities: {app.activities}")
print(f"Size: {app.size_mb} MB")

# Coverage tracking
coverage = CoverageMetrics(
    total_methods=1000,
    called_methods=750,
    total_activities=25,
    visited_activities=20
)
print(f"Method coverage: {coverage.method_coverage}%")

# Static analysis integration
static_data = StaticAnalysisData.from_files(
    gesda_file="app.gesda",
    gator_file="app.wtg",
    reach_file="app.reach"
)
```

### Tool Implementation

```python
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.configurable_tool import ConfigurableTool

class MyTool(ConfigurableTool):
    """Custom testing tool implementation."""
    
    def __init__(self):
        super().__init__(
            name="mytool",
            description="Custom monitored operations testing tool",
            process_pattern="com.mytool"
        )
    
    @ErrorHandler.handle_errors(component="MyTool", phase="execution")
    def execute_tool_specific_logic(self, task, app):
        """Implement tool-specific execution logic."""
        with self.logger.with_context(app_name=app.name):
            self.logger.info("Starting custom tool execution")
            
            # Tool execution logic
            result = self._run_tool(app.apk_path)
            
            # Publish completion event
            self.event_bus.publish_tool_event(
                EventType.TOOL_COMPLETED,
                tool_name=self.name,
                details={"result": result}
            )
            
            return result
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=rv_android_core

# Run specific test categories
poetry run pytest tests/util/error/
poetry run pytest tests/event/
poetry run pytest tests/domain/
```

### Test Structure

- `tests/analysis/`: Base analyzer functionality
- `tests/commands/`: Command infrastructure tests
- `tests/domain/`: Domain model validation
- `tests/event/`: Event system comprehensive testing
- `tests/util/`: Utility component tests
  - `error/`: Error handling infrastructure
  - `logging/`: Logging manager functionality

### Test Coverage

The module includes comprehensive tests covering:
- Error handling infrastructure
- Event system functionality  
- Domain model validation
- Utility component behavior

## Integration Examples

### Module Integration Pattern

```python
# Module initialization pattern
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.event import get_event_bus

class ModuleComponent:
    """Pattern for module components."""
    
    def __init__(self, config):
        # Infrastructure integration
        self.error_handler = ErrorHandler.get_instance()
        self.logging_manager = LoggingManager.get_instance()
        self.event_bus = get_event_bus()
        
        # Component-specific logging
        self.logger = self.logging_manager.get_logger(
            'module.component',
            {'component': self.__class__.__name__}
        )
        
        self.config = config
    
    @ErrorHandler.handle_errors(component="ModuleComponent", phase="execute")
    def execute_operation(self):
        """Operation pattern with infrastructure support."""
        with self.logger.with_context(operation="execute"):
            self.logger.info("Starting operation")
            
            # Operation logic
            result = self._perform_operation()
            
            # Publish success event
            self.event_bus.publish_event(
                EventType.OPERATION_COMPLETED,
                details={"result": result}
            )
            
            return result
```

## Architecture Guidelines

### Error Handling Best Practices

- Always use ErrorHandler singleton for consistency
- Use `@ErrorHandler.handle_errors()` decorator for automatic handling
- Provide rich context information for debugging
- Use typed exceptions for different error categories

### Logging Standards

- Use LoggingManager for all logging operations
- Include relevant context in all log messages
- Follow structured logging patterns for tool integration
- Implement performance logging for critical operations

### Event System Usage

- Use EventBus for loose coupling between components
- Define clear event schemas with typed models
- Implement idempotent event handlers
- Use appropriate channels for event categorization

### Domain Model Guidelines

- Extend base domain models for consistency
- Implement proper validation and type checking
- Use immutable patterns where appropriate
- Provide rich metadata for analysis components

## Contributing

### Code Standards

- Follow PEP 8 guidelines with 100-character line limit
- Use comprehensive type hints for all public interfaces
- Include detailed docstrings following Google style
- Maintain architectural comment patterns for critical components

### Testing Requirements

- Achieve 100% test coverage for all public interfaces
- Include integration tests for cross-component functionality
- Implement performance benchmarks for critical paths
- Use consistent testing patterns across modules

### Architecture Principles

- Maintain separation of concerns between components
- Use composition over inheritance where appropriate
- Implement consistent error handling patterns
- Follow event-driven architecture for component communication

## License

This module is part of the RV-Android project and follows the same licensing terms.