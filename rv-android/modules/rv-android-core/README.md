# RV-Android-Core Module

Foundation infrastructure module providing essential components, utilities, and abstractions for monitored operations testing in the RV-Android system.

## Overview

The RV-Android-Core module serves as the fundamental infrastructure layer for the entire RV-Android monitored operations ecosystem. It provides core abstractions, utilities, and components that enable consistent behavior across all specialized modules.

### Key Features

- **Infrastructure**: ErrorHandler with decorators, LoggingManager for modular architecture
- **Domain Models**: Domain objects for Android applications, coverage, static analysis, and UI elements
- **Tool Abstractions**: Base classes for testing tool implementations with centralized error handling and circuit breaker protection
- **Command Execution**: Robust command execution with timeout handling and failure detection
- **Utility Libraries**: Configuration management, performance monitoring, diagnostics, and JAR resolution
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

#### Domain Models
- **App**: Android application metadata and instrumentation tracking
- **Coverage**: Code coverage models with real-time tracking support
- **Static Analysis**: Unified static analysis data representation
- **UI Components**: Window, widget, and navigation graph models

#### Tool Infrastructure
- **AbstractTool**: Base abstraction for all testing tool implementations providing centralized error handling and unified command execution. Includes variant system integration.
- **Command**: Command execution infrastructure with timeout handling, failure detection, and comprehensive logging support
- **JarResolver**: Centralized JAR file resolution utility providing standardized search patterns and comprehensive error handling for JAR-dependent tools
- **ToolSpec**: Tool specification and metadata management system enabling tool discovery and configuration
- **Variant System**: Tool variant management with predefined configurations and automatic registry integration

#### Utility Components
- **Configuration Management**: Type-safe configuration with validation and environment-controlled settings
- **Performance Monitor**: Real-time performance tracking and metrics collection
- **Diagnostics**: System health monitoring and troubleshooting capabilities
- **Android Utilities**: Emulator management and Android SDK integration tools
- **JAR Resolution**: Centralized JAR file discovery with standardized search patterns and comprehensive error handling
- **Command Execution**: Command infrastructure with timeout handling and failure detection
- **Data Validation**: Pydantic v2 models with environment-controlled validation and backward compatibility support

### Integration Points

- **All RV-Android Modules**: Provides foundation infrastructure used by every module
- **External Tools**: Base classes for tool integration (Monkey, DroidBot, etc.)
- **Analysis Pipeline**: Domain models consumed by coverage and static analysis modules
- **Experiment Framework**: Configuration used by rv-experiment
- **LLM Testing**: Base infrastructure used by rv-agent for error handling and logging

## Installation

### Prerequisites

- Python 3.12+
- uv for dependency management
- Pydantic v2.8.0+ for data validation
- Android SDK (for emulator management utilities)

### Setup

```bash
# Install dependencies
uv sync

# Enable validation in development (optional)
export RV_PYDANTIC=true

# Run tests
uv run pytest

# Install in development mode
uv sync --extras dev
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
from rv_static_analysis.parser.static.static_analysis_parser import parse_file
static_data = parse_file("app.apk.json")

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
        
        # Execute with centralized error handling
        # The _execute_and_check_command method provides:
        # - Automatic timeout detection and conversion to tool timeouts
        # - Command failure detection and appropriate exception raising
        # - Logging for debugging and monitoring
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

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=rv_android_core

# Run specific test categories
uv run pytest tests/util/error/
uv run pytest tests/event/
uv run pytest tests/domain/
```

### Test Structure

- `tests/analysis/`: Base analyzer functionality testing
- `tests/commands/`: Command infrastructure and command execution testing
- `tests/domain/`: Domain model validation and data integrity testing
- `tests/tools/`: Tool infrastructure, AbstractTool base functionality, and tool integration testing
- `tests/unit/`: Unit tests (emulator boot retry, etc.)
- `tests/util/`: Utility component tests
  - `android/`: Android utility tests (package detector, signature normalizer, etc.)
  - `error/`: Error handling infrastructure and exception management testing
  - `logging/`: Logging manager functionality and contextual logging testing
  - `validation/`: Validation base and decorator tests

### Test Coverage

The module includes comprehensive tests covering:
- Error handling infrastructure with complete exception hierarchy testing
- Command execution infrastructure including timeout handling and failure detection
- Domain model validation and data integrity across all model types
- Tool infrastructure including AbstractTool base functionality and JAR resolution utilities
- Utility component behavior including logging, configuration management, and Android SDK integration

## Integration Examples

### Module Integration Pattern

```python
# Module initialization pattern
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager

class ModuleComponent:
    """Pattern for module components."""

    def __init__(self, config):
        # Infrastructure integration
        self.error_handler = ErrorHandler.get_instance()
        self.logging_manager = LoggingManager.get_instance()

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

            self.logger.info("Operation completed", extra={"result": result})

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

## License

This module is part of the RV-Android project and follows the same licensing terms.