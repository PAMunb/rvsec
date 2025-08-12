# RV-Platform Module

Independent executor for Android testing experiments with task management and component-based architecture.

## Overview

The RV-Platform module provides a standalone execution engine for Android testing experiments within the RV-Android ecosystem. It handles task execution, result collection, and tool coordination without dependencies on monitor generation or APK instrumentation.

### Key Features

- **Independent Task Execution**: Executes testing tasks independently with configurable tools (works with any APK)
- **Logcat Processing**: Parses logcat files for coverage data and monitored operations errors
- **Result Processing**: Processes completed experiment tasks to generate standardized CSV and JSON output files
- **Coverage Calculation**: Calculates coverage metrics via CoverageTracker integration
- **Component-Based Architecture**: Modular design with specialized components for emulator, logcat, coverage, and tool execution
- **Static Analysis Integration**: Loads pre-generated static analysis files for coverage calculation
- **Emulator Management**: Fresh emulator instances per task with lifecycle management
- **CLI Interface**: Standalone command-line interface for independent execution
- **Variant System**: Tool variant support with automatic resolution and configuration management

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
- **ResultProcessorComponent**: Result processing to generate CSV and JSON output files from completed tasks
- **PerformanceProcessorComponent**: Performance metrics processing to generate performance.csv files

#### Configuration Management
- **PlatformConfig**: Configuration class with validation, tool configuration, and execution parameters
- **ToolConfig**: Tool configuration with variants, parameters, and validation support
- **Variant Resolution**: Automatic resolution of tool variants with merged parameter configurations

### Integration Points

- **rv-android-core**: Uses ErrorHandler decorators, LoggingManager, EventBus, and domain models
- **rv-tools**: Integration with tool registry for tool discovery, creation, and execution coordination
- **rv-static-analysis**: Loads pre-generated static analysis files for coverage calculation
- **rv-coverage**: Integration for coverage tracking, metrics calculation, and result reporting

### Architectural Responsibilities

#### Task Execution Engine
- **Independent Execution**: Execute tasks provided by external orchestrators (like rv-experiment)
- **Tool Coordination**: Coordinate testing tool execution with configurable parameters
- **Emulator Management**: Manage fresh emulator instances per task for isolation
- **Environment Setup**: Set up testing environment with APK installation and static analysis

#### Data Processing and Analysis
- **Logcat Processing**: Parse logcat files for coverage data and monitored operations violations
- **Coverage Calculation**: Calculate progressive coverage metrics during task execution
- **Error Detection**: Detect and categorize monitored operations errors from logcat data
- **Metrics Aggregation**: Aggregate coverage and error metrics for analysis

#### Result Generation and Storage
- **Result Processing**: Process completed tasks to generate CSV and JSON output files
- **CSV Generation**: Generate detailed coverage.csv, errors.csv, summary.csv, and performance.csv files
- **JSON Generation**: Generate comprehensive results.json files with experiment data
- **Performance Metrics**: Generate performance.csv with detailed metrics when monitoring is enabled
- **Standalone Processing**: Reprocess existing experiment results without re-execution
- **Performance Data**: Collect and export performance metrics and execution data

#### CLI and Configuration
- **Standalone CLI**: Provide independent command-line interface for direct execution
- **Configuration Management**: Manage platform-specific configuration and validation
- **Template Generation**: Generate configuration templates for different scenarios

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

# Multi-tool experiment with variants
rv-platform run --tools "monkey:default,droidbot:dfs_greedy" --repetitions 3 --timeout 600

# Custom APK directory and results
rv-platform run --tools monkey --apks-dir ./my_apks --results-dir ./my_results

# Headless execution
rv-platform run --tools monkey --no-window

# Skip automatic result processing
rv-platform run --tools monkey --skip-result-processing

# Process existing results directory
rv-platform run --process-results ./results/experiment_20241201_143022
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

# Create tool configurations with variants
tools = [
    ToolConfig(name="monkey", variants=["default"], parameters={}),
    ToolConfig(name="droidbot", variants=["dfs_greedy"], parameters={"count": 1000})
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
      "variants": ["default"],
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
      "variants": ["default"],
      "parameters": {
        "event_count": 1000,
        "seed": 42
      }
    },
    {
      "name": "droidbot",
      "variants": ["dfs_greedy"],
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

RV-Platform functions as an independent execution engine that rv-experiment coordinates with:

```python
# rv-experiment orchestrates the complete workflow
from rv_platform.platform import Platform
from rv_experiment.config import ExperimentConfig

# rv-experiment handles pre-processing
experiment_config = ExperimentConfig.from_file("experiment.json")
experiment_config.instrument_apks()          # rv-experiment responsibility
experiment_config.generate_static_analysis() # rv-experiment responsibility
experiment_config.generate_monitors()        # rv-experiment responsibility

# rv-experiment creates platform configuration for task execution
platform_config = experiment_config.get_platform_config()

# rv-platform handles independent task execution and result processing
platform = Platform(platform_config)
results = platform.run()  # Includes task execution, logcat processing, CSV/JSON generation

# rv-experiment handles experiment-specific post-processing
experiment_config.process_experiment_diagnostics(results)
```

### Architectural Separation

- **rv-experiment**: Orchestrates experiment lifecycle, instruments APKs, generates static analysis
- **rv-platform**: Executes tasks, processes logcat, generates CSV/JSON result files
- **Clear boundaries**: rv-platform handles all data processing, rv-experiment focuses on orchestration
- **Independent operation**: rv-platform can function standalone or reprocess existing results

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