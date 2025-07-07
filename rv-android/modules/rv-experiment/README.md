# RV-Experiment Module

Experiment orchestration system for monitored operations testing in Android applications with comprehensive lifecycle management.

## Overview

The RV-Experiment module serves as the orchestrator for monitored operations experiments in the RV-Android ecosystem. It manages the complete experiment lifecycle including APK instrumentation, static analysis generation, experiment configuration, and coordination with rv-platform for task execution and result processing. The module focuses on high-level experiment management while delegating task execution and data processing to rv-platform.

### Key Features

- **Experiment Orchestration**: Complete lifecycle management from pre-processing to result analysis
- **APK Instrumentation**: Instruments APKs for runtime verification and monitoring
- **Static Analysis Generation**: Generates static analysis files for consumption by rv-platform
- **Configuration Management**: Comprehensive experiment configuration with validation and templates
- **RV-Platform Coordination**: Coordinates with rv-platform for task execution and result processing
- **Experiment Diagnostics**: Provides experiment-level diagnostics and instrumentation error tracking
- **Monitored Operations**: Support for JCA crypto and generic specification monitoring
- **CLI Interface**: Four core commands (run, config, list-tools, validate)

## Architecture

### Core Components

#### CLI Interface
- **CLIContext**: CLI state management with logging and tool registry integration
- **Command Structure**: Four focused commands (run, config, list-tools, validate)
- **Tool Specification Parsing**: DSL parser for tool:variant@parameter format
- **Configuration Templates**: Factory methods for different experiment scenarios

#### Configuration Management
- **ExperimentConfig**: Primary configuration class with validation and sub-module config
- **ToolConfiguration**: Individual tool configuration with variant and parameter support
- **Template Generation**: Pre-built configurations for basic, advanced, and research scenarios

#### Execution System
- **execute_with_config()**: Direct execution function for experiment orchestration
- **Tool Registry Integration**: Direct access to rv-tools registry for tool creation
- **Error Handling**: Comprehensive error management using rv-android-core decorators

#### Directory Structure
```
./results/{experiment_id}/           # Individual experiment results
├── config.json                     # Experiment configuration
├── logs/                           # Experiment-specific logs
├── results/                        # Results and analysis data
└── traces/                         # Execution traces and coverage

./out/                              # Shared processing artifacts
├── instrumented/                   # Instrumented APKs
├── monitors/                       # Generated monitor files
└── static/                         # Static analysis results
```

### Integration Points

- **rv-android-core**: Uses ErrorHandler decorators, LoggingManager for consistent error handling and logging
- **rv-platform**: Coordinates task execution by calling rv-platform with configured tasks
- **rv-static-analysis**: Generates static analysis files for rv-platform consumption
- **rv-instrumentation**: Instruments APKs and generates monitored operations artifacts
- **rv-monitor-generator**: Generates monitoring specifications for runtime verification
- **rv-coverage**: Provides coverage configuration for rv-platform components

### Architectural Responsibilities

#### Pre-processing Phase
- **APK Instrumentation**: Instrument APKs using rv-instrumentation with monitored operations
- **Static Analysis**: Generate static analysis files (GATOR, GESDA, REACH) for coverage calculation
- **Monitor Generation**: Create monitor specifications using rv-monitor-generator
- **Configuration Validation**: Validate experiment configuration and prepare execution parameters

#### Execution Coordination Phase
- **Task Generation**: Create task configurations for rv-platform execution
- **RV-Platform Coordination**: Coordinate with rv-platform for independent task execution
- **Progress Monitoring**: Monitor experiment progress through event bus integration
- **Error Management**: Handle experiment-level errors and orchestration issues

#### Post-processing Phase
- **Experiment Diagnostics**: Generate experiment-level diagnostics and completion tracking
- **Instrumentation Error Reporting**: Track and report APK instrumentation errors
- **Basic Metadata**: Provide basic experiment metadata for logging and coordination
- **Result Interface**: Coordinate with rv-platform for comprehensive result processing

## Installation

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- Access to other RV-Android modules

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
python -m rv_experiment run --tools monkey

# Multi-tool experiment with configuration
python -m rv_experiment run --tools monkey,droidbot:dfs_greedy --repetitions 3

# JCA cryptography monitoring experiment
python -m rv_experiment run --tools monkey --specification-set jca

# Generic programming patterns experiment  
python -m rv_experiment run --tools droidbot:dfs_greedy --specification-set generic
```

#### Tool Specification DSL

```bash
# Tool variants and parameters
# Format: tool[:variant1][:variant2][@param1=value1,param2=value2]

# Basic tools
monkey
droidbot
ape

# Tools with variants
droidbot:dfs_greedy
droidbot:bfs_greedy

# Tools with parameters
monkey@seed=42,throttle=100
droidbot:dfs_greedy@count=1000,timeout=600

# Multiple tools combination
monkey,droidbot:dfs_greedy,ape@running_minutes=10
```

#### Configuration Templates

```bash
# Generate basic configuration template
python -m rv_experiment config --template-type basic --output basic_config.json

# Generate advanced configuration template
python -m rv_experiment config --template-type advanced --output advanced_config.json

# Generate research template
python -m rv_experiment config --template-type research --output research_config.json
```

#### Tool Management

```bash
# List all available tools
python -m rv_experiment list-tools

# Show detailed tool information
python -m rv_experiment list-tools --detailed

# Filter by tool category
python -m rv_experiment list-tools --filter-by basic --detailed
```

#### Configuration Validation

```bash
# Validate configuration file
python -m rv_experiment validate experiment_config.json
```

### Programmatic Usage

#### Configuration and Execution

```python
from rv_experiment.config import ExperimentConfig, ToolConfiguration
from rv_experiment.experiment.experiment_controller import execute_with_config

# Create tool configurations
tools = [
    ToolConfiguration(name="monkey"),
    ToolConfiguration(name="droidbot", variants=["dfs_greedy"], parameters={"count": 1000})
]

# Create experiment configuration
config = ExperimentConfig(
    name="basic_experiment",
    description="Basic monitored operations experiment",
    tool_configs=tools,
    repetitions=3,
    timeouts=[300],
    specification_set="jca",  # JCA cryptography monitoring
    apk_dir="./apks_examples/",
    apk_patterns=["*.apk"]
)

# Validate configuration
config.validate()

# Execute experiment
execute_with_config(config)
```

#### Configuration File Usage

```python
from rv_experiment.config import ExperimentConfig

# Load configuration from file
config = ExperimentConfig.from_file("experiment_config.json")

# Validate and execute
config.validate()
execute_with_config(config)
```

#### Just-in-Time Configuration

```python
from rv_experiment.config import ExperimentConfig

# Configuration with just-in-time sub-module configuration
config = ExperimentConfig(
    name="jca_crypto_experiment",
    specification_set="jca"
)

# Get just-in-time configurations for sub-modules
monitor_config = config.get_monitored_operations_config()  # For rv-monitor-generator
instrumentation_config = config.get_instrumentation_config()  # For rv-instrumentation
static_analysis_config = config.get_static_analysis_config()  # For rv-static-analysis

# These configs are generated only when needed, eliminating complex upfront coordination
```

### Configuration Templates

#### Basic Experiment Template

```json
{
  "name": "basic_experiment",
  "description": "Basic experiment with standard tools",
  "tool_configs": [
    {"name": "monkey", "variants": [], "parameters": {}},
    {"name": "droidbot", "variants": ["dfs_greedy"], "parameters": {"count": 1000}}
  ],
  "repetitions": 1,
  "timeouts": [300],
  "specification_set": "jca",
  "generate_monitors": true,
  "instrument_apks": true,
  "run_static_analysis": true,
  "apk_dir": "./apks_examples/",
  "apk_patterns": ["*.apk"]
}
```

#### Advanced Template

```json
{
  "name": "advanced_experiment", 
  "description": "Advanced experiment with multiple tools",
  "tool_configs": [
    {"name": "monkey", "variants": ["fixed_seed"], "parameters": {"seed": 42, "throttle": 100}},
    {"name": "droidbot", "variants": ["dfs_greedy"], "parameters": {"count": 2000, "timeout": 600}},
    {"name": "ape", "variants": [], "parameters": {"running_minutes": 10}}
  ],
  "repetitions": 3,
  "timeouts": [300, 600, 900],
  "specification_set": "generic",
  "generate_monitors": true,
  "instrument_apks": true,
  "run_static_analysis": true,
  "apk_patterns": ["*.apk", "!*test*.apk", "!*debug*.apk"]
}
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=rv_experiment

# Run specific test categories
poetry run pytest tests/config/
poetry run pytest tests/experiment/
```

### Test Structure

- `tests/config/`: Configuration management and validation tests
- `tests/experiment/`: Experiment execution and workflow tests

## Performance Characteristics

### Experiment Execution
- **Small Experiments** (1-3 tools): 2-5 minutes typical execution
- **Large Experiments** (5+ tools): 10-30 minutes depending on tool configuration
- **Configuration Loading**: < 50ms for typical configuration files

## Monitored Operations Support

### JCA Cryptography Specifications

```bash
# JCA-focused experiment
python -m rv_experiment run --tools monkey --specification-set jca

# JCA specification monitoring with multiple tools
python -m rv_experiment run --tools monkey,droidbot:dfs_greedy --specification-set jca
```

### Generic Programming Pattern Specifications

```bash
# Generic patterns experiment
python -m rv_experiment run --tools droidbot:dfs_greedy --specification-set generic

# Generic pattern monitoring with multiple tools
python -m rv_experiment run --tools monkey,ape --specification-set generic
```

### Custom Specification Sets

```bash
# Custom specification experiment
python -m rv_experiment run --tools monkey --specification-set custom
```

## Integration Examples

```python
# Complete experiment execution
from rv_experiment.config import ExperimentConfig, ToolConfiguration
from rv_experiment.experiment.experiment_controller import execute_with_config

# Setup experiment for JCA cryptography monitoring
tools = [ToolConfiguration(name="monkey"), ToolConfiguration(name="droidbot", variants=["dfs_greedy"])]
config = ExperimentConfig(
    name="jca_crypto_test",
    tool_configs=tools,
    specification_set="jca"
)

# Execute with full integration
execute_with_config(config)
```

## Architecture Guidelines

### Configuration Best Practices

- Use ExperimentConfig for all experiment definitions
- Leverage configuration templates for common scenarios
- Validate configurations before experiment execution
- Use specification_set parameter to separate JCA and generic monitoring

### Tool Integration Standards

- Follow tool specification DSL for consistent parameter passing
- Implement proper error handling with rv-android-core decorators
- Support both JCA and generic specification monitoring

## Contributing

### Code Standards

- Use comprehensive type hints for all public interfaces
- Include detailed docstrings with architectural context
- Maintain separation between JCA crypto and generic specification logic

### Testing Requirements

- Include tests for configuration management and validation
- Test both JCA and generic specification scenarios
- Include integration tests for tool execution workflows

## License

This module is part of the RV-Android project and follows the same licensing terms.