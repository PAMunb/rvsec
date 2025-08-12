# RV-Android-Core Module

Foundation infrastructure module providing essential components, utilities, and abstractions for monitored operations testing in the RV-Android system.

## Overview

The RV-Android-Core module serves as the fundamental infrastructure layer for the entire RV-Android monitored operations ecosystem. It provides core abstractions, utilities, and components that enable consistent behavior across all specialized modules.

### Key Features

- **Infrastructure**: ErrorHandler with decorators, LoggingManager, EventBus for modular architecture
- **Domain Models**: Domain objects for Android applications, coverage, static analysis, and UI elements
- **Tool Abstractions**: Base classes for testing tool implementations with centralized error handling and circuit breaker protection
- **Resilience Patterns**: Circuit breaker implementation preventing cascading failures in command execution
- **Utility Libraries**: Configuration management, performance monitoring, diagnostics, and JAR resolution
- **Event System**: Event-driven architecture for component communication and system integration
- **Type Safety**: Type annotations and validation throughout with Pydantic v2
- **Data Validation**: Environment-controlled validation with strong typing and backward compatibility
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
- **AbstractTool**: Base abstraction for all testing tool implementations providing centralized error handling, unified command execution, and automatic circuit breaker protection. Includes variant system integration.
- **Command**: Command execution infrastructure with timeout handling, failure detection, and comprehensive logging support
- **CommandCircuitBreaker**: Resilience pattern implementation preventing cascading failures through command-specific failure tracking and automatic recovery testing
- **JarResolver**: Centralized JAR file resolution utility providing standardized search patterns and comprehensive error handling for JAR-dependent tools
- **ToolSpec**: Tool specification and metadata management system enabling tool discovery and configuration
- **Variant System**: Tool variant management with predefined configurations and automatic registry integration

#### Utility Components
- **Configuration Management**: Type-safe configuration with validation and environment-controlled settings
- **Performance Monitor**: Real-time performance tracking and metrics collection
- **Diagnostics**: System health monitoring and troubleshooting capabilities
- **Android Utilities**: Emulator management and Android SDK integration tools
- **JAR Resolution**: Centralized JAR file discovery with standardized search patterns and comprehensive error handling
- **Command Execution**: Command infrastructure with timeout handling, failure detection, and circuit breaker protection
- **Data Validation**: Pydantic v2 models with environment-controlled validation and backward compatibility support

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
- Pydantic v2.8.0+ for data validation
- Android SDK (for emulator management utilities)

### Setup

```bash
# Install dependencies
poetry install

# Enable validation in development (optional)
export RV_PYDANTIC=true

# Run tests
poetry run pytest

# Install in development mode
poetry install --extras dev
```

### Environment Configuration

The module supports environment-controlled data validation:

- **Development**: Set `RV_PYDANTIC=true` to enable full validation
- **Production**: Leave unset or set to `false` for performance optimization
- **Testing**: Validation automatically enabled during test execution

```bash
# Enable validation
export RV_PYDANTIC=true

# Disable validation (default)
export RV_PYDANTIC=false
```

## Usage

### Error Handling

```python
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import RVToolError

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
from rv_android_core.domain.app import App
from rv_android_core.domain.coverage import CoverageMetrics
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.commands.command_result import CommandResult

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

# Command execution with validation
result = CommandResult(
  exit_code=0,
  stdout=b"Command output",
  stderr=None,
  execution_time=1.5
)
print(f"Output: {result.get_stdout_text()}")
```

### Data Validation

```python
from rv_android_core.util.validation import BaseValidatedModel, validated_model
from rv_android_core.event.models import TaskEvent, EventType

# Using validated models with automatic validation
task_event = TaskEvent(
    type=EventType.TASK_STARTED,
    task_id="123",
    task_config={"timeout": 60}
)

# Using @validated_model decorator for backward compatibility
@validated_model
class CustomModel(BaseValidatedModel):
    name: str
    value: int

# Supports both named and positional arguments
model1 = CustomModel(name="test", value=42)
model2 = CustomModel("test", 42)  # Positional arguments work too
```

### Tool Implementation

```python
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.commands.command import Command
from rv_android_core.util.jar_resolver import JarResolver
from typing import Dict, Any

class MyTool(AbstractTool):
    """Custom testing tool implementation with variant support."""
    
    def __init__(self, tool_spec=None):
        super().__init__(tool_spec or {
            "name": "mytool",
            "description": "Custom monitored operations testing tool",
            "process_pattern": "com.mytool"
        })
        self.jar_resolver = JarResolver()
    
    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """Define tool variants with different configurations."""
        return {
            "default": {
                "timeout_multiplier": 1.0,
                "verbose": False,
                "additional_args": []
            },
            "debug": {
                "timeout_multiplier": 2.0,
                "verbose": True,
                "additional_args": ["--debug", "--trace"]
            },
            "fast": {
                "timeout_multiplier": 0.5,
                "verbose": False,
                "additional_args": ["--fast-mode"]
            }
        }
    
    def configure(self, variant_config: Dict[str, Any]) -> None:
        """Configure tool with variant-specific parameters."""
        self.timeout_multiplier = variant_config.get("timeout_multiplier", 1.0)
        self.verbose = variant_config.get("verbose", False)
        self.additional_args = variant_config.get("additional_args", [])
        
        if self.verbose:
            self.logger.info(f"Tool configured with variant parameters: {variant_config}")
    
    def get_tool_spec(self) -> Dict[str, Any]:
        """Return tool specification for registry."""
        return {
            "name": self.name,
            "description": self.description,
            "process_pattern": self.process_pattern,
            "supported_platforms": ["android"],
            "requires_emulator": True
        }
    
    def execute_tool_specific_logic(self, task, app):
        """Implement tool-specific execution logic."""
        self.logger.info(f"Starting {self.name} execution for {app.package_name}")
        
        # Build tool command with variant-specific configuration
        command = self._build_tool_command(task, app)
        
        # Execute with centralized error handling and automatic circuit breaker protection
        # The _execute_and_check_command method provides:
        # - Automatic timeout detection and conversion to tool timeouts
        # - Command failure detection and appropriate exception raising
        # - Circuit breaker protection preventing repeated execution of failing commands
        # - Comprehensive logging for debugging and monitoring
        with open(task.result.trace_file, 'wb') as trace_file:
            result = self._execute_and_check_command(command, stdout=trace_file)
        
        self.logger.info(f"{self.name} execution completed successfully")
    
    def _build_tool_command(self, task, app):
        """Build tool-specific command with variant configuration."""
        # Adjust timeout based on variant configuration
        adjusted_timeout = int(task.config.timeout * self.timeout_multiplier)
        
        # Build command with additional arguments from variant
        args = [app.apk_path] + self.additional_args
        
        return Command("mytool", args, timeout=adjusted_timeout)
```

### Variant System Usage

```python
from rv_tools.registry import ToolRegistry

# Register tool with automatic variant registration
registry = ToolRegistry.get_instance()
registry.register_tool_class(MyTool)

# Query available variants
variants = registry.get_tool_variants("mytool")
print(f"Available variants: {list(variants.keys())}")

# Get specific variant configuration
debug_config = registry.get_variant_config("mytool", "debug")
print(f"Debug variant config: {debug_config}")

# Create tool with variant
from rv_tools.registry import ToolFactory
factory = ToolFactory()
tool = factory.create_tool({
    "name": "mytool",
    "variant": "debug",
    "additional_params": {"custom_setting": "value"}
})
```

## Circuit Breaker Protection

### Understanding the Circuit Breaker Pattern

The RV-Android framework incorporates a circuit breaker pattern specifically designed to enhance system resilience during command execution. This pattern acts as a protective mechanism that prevents cascading failures when testing tools encounter persistent issues, ensuring the overall system remains stable even when individual components fail repeatedly.

### Why Circuit Breakers Are Essential

Testing frameworks often execute commands that interact with external systems, emulators, or third-party tools. These interactions can fail for various reasons: network connectivity issues, resource exhaustion, corrupted tool installations, or environmental problems. Without protection, a single failing command could consume system resources indefinitely, attempting the same operation repeatedly without success.

Consider a scenario where a testing tool's JAR file becomes corrupted or a required dependency is missing. In a traditional system, each test execution would attempt to run the same failing command, consuming CPU cycles, memory, and potentially blocking other operations. The circuit breaker pattern recognizes these failure patterns and temporarily suspends execution attempts, allowing the system to continue functioning while providing clear feedback about the problematic command.

### How Circuit Breakers Work

The circuit breaker monitors command execution patterns and maintains three distinct states. Initially, the circuit operates in a closed state, allowing all commands to execute normally. When a command fails, the circuit breaker records this failure against the specific command signature. If failures accumulate beyond a configured threshold, the circuit breaker transitions to an open state, blocking further execution attempts for that particular command.

After remaining open for a period, the circuit breaker enters a half-open state to test whether the underlying issue has been resolved. During this testing phase, it allows limited command execution. If the command succeeds, the circuit breaker returns to the closed state, resuming normal operation. If the command fails again, the circuit breaker immediately returns to the open state, indicating the issue persists.

### Benefits of Circuit Breaker Protection

The circuit breaker pattern provides several key advantages for testing framework stability. Resource protection prevents failing commands from consuming excessive system resources, ensuring other operations can continue uninterrupted. Fast failure detection means the system quickly identifies problematic commands and stops attempting futile operations, improving overall response time.

System stability is enhanced because isolated command failures cannot cascade into broader system failures. The framework continues operating even when specific tools encounter issues. Additionally, the circuit breaker provides clear failure feedback, helping developers quickly identify and diagnose problematic commands or environmental issues.

### Circuit Breaker Behavior in Practice

When a testing tool executes a command, the circuit breaker first checks whether execution is permitted based on the command's failure history. For commands that have been executing successfully, the circuit breaker remains transparent, adding minimal overhead to the execution process.

If a command begins failing consistently, the circuit breaker starts tracking these failures. Once the failure threshold is exceeded, the circuit breaker blocks further execution attempts, immediately raising an exception that clearly indicates the protection mechanism has activated. This immediate feedback prevents resource waste and provides clear diagnostic information.

The circuit breaker operates at the command level, meaning that failure of one specific command does not affect other commands or tools. This granular approach ensures that system protection is applied precisely where needed without impacting unrelated operations.

### System Operation Without Circuit Breakers

Without circuit breaker protection, a testing framework would be vulnerable to several problematic scenarios. Failing commands would continue executing indefinitely, consuming system resources and potentially causing memory exhaustion or CPU overload. Multiple test runs would repeat the same failing operations, wasting time and resources without providing additional diagnostic value.

System failures could cascade as resource exhaustion from one failing command impacts other system components. Debugging would be more difficult because repeated failures would generate excessive log output without clear indication of the underlying problem. The framework would lack graceful degradation capabilities, potentially requiring manual intervention to stop problematic operations.

### Integration with Testing Tools

The circuit breaker pattern integrates seamlessly with the existing tool infrastructure. Testing tools automatically benefit from circuit breaker protection without requiring modifications to their core logic. The pattern operates at the command execution level, providing protection regardless of which tool initiates the command.

When a circuit breaker activates, the testing framework can implement fallback strategies or provide clear failure reporting. This integration ensures that research and development activities can continue even when specific tools encounter issues, maintaining productivity and system reliability.

### Circuit Breaker Usage

```python
from rv_android_core.commands.circuit_breaker import CommandCircuitBreaker, CircuitBreakerState
from rv_android_core.util.error.exceptions import CircuitBreakerOpenError


# Circuit breaker is automatically integrated in AbstractTool
# Custom configuration (optional)
class CustomTool(AbstractTool):
    def __init__(self):
        super().__init__(name="custom", description="Custom tool", process_pattern="custom")
        # Override default circuit breaker settings
        self.circuit_breaker = CommandCircuitBreaker(failure_threshold=5, retry_count=2)

    def execute_tool_specific_logic(self, task, app):
        try:
            # Commands automatically protected by circuit breaker
            result = self._execute_and_check_command(command)
        except CircuitBreakerOpenError as e:
            self.logger.warning(f"Circuit breaker protection activated: {e}")
            # Handle blocked execution or implement fallback
            raise
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

- `tests/analysis/`: Base analyzer functionality testing
- `tests/commands/`: Command infrastructure, circuit breaker resilience patterns, and command execution testing
- `tests/domain/`: Domain model validation and data integrity testing
- `tests/event/`: Event system comprehensive testing including publishing, subscription, and event processing
- `tests/tools/`: Tool infrastructure, AbstractTool base functionality, and tool integration testing
- `tests/util/`: Utility component tests
  - `error/`: Error handling infrastructure and exception management testing
  - `logging/`: Logging manager functionality and contextual logging testing

### Test Coverage

The module includes comprehensive tests covering:
- Error handling infrastructure with complete exception hierarchy testing
- Command execution infrastructure including timeout handling and failure detection
- Circuit breaker resilience patterns with state transitions, failure tracking, and recovery testing
- Event system functionality including publishing, subscription, and asynchronous processing
- Domain model validation and data integrity across all model types
- Tool infrastructure including AbstractTool base functionality and JAR resolution utilities
- Utility component behavior including logging, configuration management, and Android SDK integration

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