# RV-Platform Module

Independent executor for Android testing experiments with task management and component-based architecture.

## Overview

The RV-Platform module provides a standalone execution engine for Android testing experiments within the RV-Android ecosystem. It handles task execution, result collection, and tool coordination without dependencies on monitor generation or APK instrumentation.

### Key Features

- **Component-Based Architecture**: Modular design with specialized components for emulator management, logcat capture, coverage tracking, and tool execution
- **Task Management**: Task lifecycle management with state tracking, persistence, and error recovery
- **Tool Integration**: Integration with rv-tools registry supporting multiple testing frameworks
- **Static Analysis Integration**: Copying and loading of static analysis files for coverage calculation
- **Emulator Management**: Fresh emulator instances per task with lifecycle management
- **Result Collection**: Collection of logcat, tool outputs, coverage metrics, and error data
- **CLI Interface**: Command-line interface with configuration templates and validation

## Architecture

### Core Components

#### Task Execution System
- **TaskExecutor**: Task execution orchestrator with component coordination and state management
- **Task**: Task model with configuration, state tracking, and result collection
- **TaskConfiguration**: Task-specific configuration with tool selection, timeouts, and execution parameters
- **TaskResult**: Result model with execution metrics, state tracking, and error reporting

#### Execution Components
- **EmulatorComponent**: Emulator lifecycle management with context managers and device coordination
- **LogcatComponent**: Logcat capture during emulator sessions with processing and file management
- **CoverageComponent**: Coverage tracking initialization and execution with static analysis integration
- **StaticAnalysisComponent**: Static analysis file copying from instrumented directory and data loading
- **ToolExecutionComponent**: Tool execution coordination with configuration and error handling

#### Configuration Management
- **PlatformConfig**: Configuration class with validation, tool configuration, and execution parameters
- **ToolConfig**: Tool configuration with variants, parameters, and validation support

### Integration Points

- **rv-android-core**: Uses ErrorHandler decorators, LoggingManager, EventBus, and domain models
- **rv-tools**: Integration with tool registry for tool discovery, creation, and execution coordination
- **rv-static-analysis**: Integration for static analysis file processing and coverage calculation
- **rv-coverage**: Integration for coverage tracking, metrics calculation, and result reporting

## Installation

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- Access to other RV-Android modules
- Android SDK (for emulator management)

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

### CLI Interface

#### Basic Experiment Execution

```bash
# Simple experiment with single tool
rv-platform run --tools monkey

# Multi-tool experiment with configuration
rv-platform run --tools monkey,droidbot --repetitions 3 --timeout 600

# Custom APK directory and results
rv-platform run --tools monkey --apks-dir ./my_apks --results-dir ./my_results

# Headless execution
rv-platform run --tools monkey --no-window
```

#### Configuration File Usage

```bash
# Execute with configuration file
rv-platform run --config platform_config.json

# Generate configuration templates
rv-platform config --template-type basic --output basic_config.json
rv-platform config --template-type advanced --output advanced_config.json

# Validate configuration
rv-platform validate-config platform_config.json
```

#### Tool Management

```bash
# List available tools
rv-platform list-tools

# Show detailed tool information
rv-platform list-tools --detailed
```

### Programmatic Usage

#### Configuration and Execution

```python
from rv_platform.config.platform_config import PlatformConfig, ToolConfig
from rv_platform.platform import Platform

# Create tool configurations
tools = [
    ToolConfig(name="monkey", variants=[], parameters={}),
    ToolConfig(name="droidbot", variants=[], parameters={"count": 1000})
]

# Create platform configuration
config = PlatformConfig(
    apks_dir="./apks_examples",
    tools=tools,
    repetitions=2,
    timeouts=[300, 600],
    results_dir="./results/my_experiment",
    no_window=True,
    log_level="INFO"
)

# Execute platform
platform = Platform(config)
results = platform.run()

# Access results
print(f"Total tasks: {results['total_tasks']}")
print(f"Successful: {results['successful_tasks']}")
print(f"Success rate: {results['success_rate']:.2%}")
```

#### Configuration File Usage

```python
from rv_platform.config.platform_config import PlatformConfig
from rv_platform.platform import Platform

# Load configuration from file
config = PlatformConfig.from_file("platform_config.json")

# Validate and execute
config.validate_dependencies()
platform = Platform(config)
results = platform.run()
```

#### EventBus Integration

```python
from rv_platform.platform import Platform
from rv_android_core.event import EventBus

# Create platform with custom event bus
event_bus = EventBus.get_instance()
platform = Platform(config, event_bus)

# Subscribe to events for real-time monitoring
def on_task_started(event):
    print(f"Task started: {event.task_id}")

event_bus.subscribe('TASK_STARTED', on_task_started)

# Execute with event monitoring
results = platform.run()
```

### Configuration Templates

#### Basic Configuration Template

```json
{
  "apks_dir": "apks_examples",
  "tools": [
    {
      "name": "monkey",
      "variants": [],
      "parameters": {}
    }
  ],
  "repetitions": 1,
  "timeouts": [300],
  "results_dir": "./results/basic_experiment",
  "no_window": true,
  "log_level": "INFO"
}
```

#### Advanced Configuration Template

```json
{
  "apks_dir": "apks_examples",
  "tools": [
    {
      "name": "monkey",
      "variants": [],
      "parameters": {
        "event_count": 1000,
        "seed": 42
      }
    },
    {
      "name": "droidbot",
      "variants": [],
      "parameters": {
        "count": 500
      }
    }
  ],
  "repetitions": 3,
  "timeouts": [300, 600],
  "results_dir": "./results/advanced_experiment",
  "no_window": true,
  "log_level": "DEBUG"
}
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=rv_platform

# Run specific test categories
poetry run pytest tests/execution/
poetry run pytest tests/components/
```

### Test Structure

- `tests/execution/`: Task execution and lifecycle management tests
- `tests/components/`: Individual component functionality tests
- `tests/config/`: Configuration management and validation tests

## Performance Characteristics

### Execution Performance
- **Small Experiments** (1-2 tools, 1 APK): 3-8 minutes typical execution
- **Large Experiments** (3+ tools, multiple APKs): 15-45 minutes depending on configuration
- **Configuration Loading**: < 100ms for typical configuration files
- **Static Analysis Integration**: < 5 seconds for file copying and loading

### Resource Management
- **Memory Usage**: 200-500MB baseline, scales with concurrent emulator instances
- **Disk Usage**: Results scale with experiment size, temporary files cleaned automatically
- **Emulator Instances**: Fresh instance per task prevents interference and ensures consistency

## Integration Examples

### Standalone Platform Usage

```python
# Complete experiment execution
from rv_platform.config.platform_config import PlatformConfig, ToolConfig
from rv_platform.platform import Platform

# Setup for comprehensive testing
tools = [
    ToolConfig(name="monkey", parameters={"seed": 42}),
    ToolConfig(name="droidbot", parameters={"count": 1000})
]

config = PlatformConfig(
    apks_dir="./apks_examples",
    tools=tools,
    repetitions=3,
    timeouts=[300, 600]
)

# Execute with full component integration
platform = Platform(config)
results = platform.run()
```

### Integration with rv-experiment

```python
# rv-platform as execution engine for rv-experiment
from rv_platform.platform import Platform
from rv_experiment.config import ExperimentConfig

# rv-experiment creates platform configuration
experiment_config = ExperimentConfig.from_file("experiment.json")
platform_config = experiment_config.get_platform_config()

# rv-platform handles execution
platform = Platform(platform_config)
results = platform.run()
```

## Architecture Guidelines

### Component Design Principles

- Use TaskExecutor for centralized execution coordination
- Implement components with clear initialize/execute/cleanup lifecycle
- Support EventBus integration for real-time progress reporting
- Follow error handling patterns with rv-android-core infrastructure

### Configuration Best Practices

- Use PlatformConfig for all platform-specific settings
- Leverage ToolConfig for individual tool configuration
- Validate configurations before execution
- Support both programmatic and file-based configuration

### Tool Integration Standards

- Integrate with rv-tools registry for tool discovery and creation
- Support tool defaults with parameter override capabilities
- Implement proper error handling and recovery mechanisms

## Contributing

### Code Standards

- Use comprehensive type hints for all public interfaces
- Include detailed docstrings with architectural context
- Maintain separation between execution logic and component implementation
- Follow rv-android-core patterns for error handling and logging

### Testing Requirements

- Include tests for task execution and component functionality
- Test configuration management and validation scenarios
- Include integration tests for complete platform execution workflows
- Test error handling and recovery mechanisms

## License

This module is part of the RV-Android project and follows the same licensing terms.