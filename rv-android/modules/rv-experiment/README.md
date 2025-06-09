# RV-Experiment Module

## Overview

The `rv-experiment` module provides modern experiment orchestration and coordination capabilities for the RV-Android platform. It implements a comprehensive CLI and configuration system that coordinates execution across multiple specialized modules while maintaining module independence.

## Key Features

- **Modern CLI Interface**: Comprehensive Click-based command-line interface
- **Tool Variant Support**: Full support for tool specifications with variants and parameters
- **Type-Safe Configuration**: Dataclass-based configuration with validation
- **Multiple Experiment Types**: Single-tool, comparative, batch, and local experiments
- **Bridge Pattern**: Seamless integration with legacy main.py workflows
- **Module Coordination**: Orchestrates rv-monitor-generator, rv-instrumentation, rv-static-analysis, and other modules

## Installation

```bash
cd modules/rv-experiment
pip install -e .
```

## CLI Usage

### Tool Specification Format

Tools support variants and parameters using the following format:
```
tool_name[:variant1][:variant2][@param1=value1,param2=value2]
```

### Examples

#### Basic Tool Usage
```bash
# Simple tool
rv-experiment run-single --tool monkey

# Tool with variants
rv-experiment run-single --tool droidbot:dfs_greedy

# Tool with variants and parameters
rv-experiment run-single --tool rvandroid:llama:batch@temperature=0.3,model=llama3
```

#### Available Tool Variants

**DroidBot**:
- `dfs_naive`, `dfs_greedy`, `bfs_naive`, `bfs_greedy`
- Example: `droidbot:dfs_greedy@count=1000`

**RVAndroid**:
- LLM variants: `llama`, `gpt4`, `claude`
- Strategy variants: `single_action`, `composable`, `batch`
- Combined: `llama_batch`, `gpt4_batch`
- Example: `rvandroid:llama:batch@temperature=0.3`

**Monkey**:
- `fixed_seed`, `low_throttle`
- Example: `monkey:fixed_seed@seed=42`

**FastBot**:
- `fast`, `slow`
- Example: `fastbot:fast@throttle=50`

### Command Reference

#### Single-Tool Experiments
```bash
# Basic single-tool experiment
rv-experiment run-single --tool monkey --timeout 300 --repetitions 3

# With variants and parameters
rv-experiment run-single --tool rvandroid:llama:batch@temperature=0.3 --no-window

# Skip specific phases
rv-experiment run-single --tool droidbot:dfs_greedy --skip-monitors --skip-static
```

#### Comparative Experiments
```bash
# Compare multiple tools
rv-experiment run-comparative --tools monkey,droidbot:dfs_greedy --repetitions 3

# Complex comparison with variants
rv-experiment run-comparative \
  --tools monkey:fixed_seed,droidbot:dfs_greedy@count=1000,rvandroid:llama:batch@temperature=0.3 \
  --timeouts 300,600,900 \
  --repetitions 2
```

#### Batch Experiments
```bash
# Run from configuration file
rv-experiment run-batch --config-file experiment.json

# Validate configuration without running
rv-experiment run-batch --config-file experiment.json --dry-run
```

#### Local Development
```bash
# Quick local testing
rv-experiment run-local

# Custom local setup
rv-experiment run-local --tools monkey:fixed_seed,ape --timeout 60 --repetitions 2
```

#### Configuration Management
```bash
# Generate configuration template
rv-experiment generate-config --format json --output experiment.json

# Generate YAML template
rv-experiment generate-config --format yaml > config.yaml

# List available tools
rv-experiment list-tools
```

## Configuration Files

### JSON Configuration Example
```json
{
  "name": "comparative_study",
  "description": "Comparative analysis of testing tools",
  "tools": ["monkey", "droidbot", "rvandroid"],
  "tool_configs": [
    {
      "name": "monkey",
      "variants": ["fixed_seed"],
      "parameters": {"seed": 42, "throttle": 100},
      "enabled": true
    },
    {
      "name": "droidbot",
      "variants": ["dfs_greedy"],
      "parameters": {"count": 1000},
      "enabled": true
    },
    {
      "name": "rvandroid",
      "variants": ["llama", "batch"],
      "parameters": {"temperature": 0.3, "model": "llama3"},
      "enabled": true
    }
  ],
  "applications": {
    "directory": "./apks",
    "patterns": ["*.apk"],
    "exclude_patterns": ["*test*.apk", "*debug*.apk"]
  },
  "execution": {
    "repetitions": 3,
    "timeouts": [300, 600, 900],
    "no_window": true,
    "parallel_execution": false,
    "max_parallel_tasks": 2
  },
  "processing": {
    "generate_monitors": true,
    "instrument": true,
    "static_analysis": true,
    "skip_experiment": false,
    "process_results": true,
    "generate_reports": true
  }
}
```

### Tool Specification in Config
```json
{
  "tools": [
    "monkey:fixed_seed@seed=42,throttle=100",
    "droidbot:dfs_greedy@count=1000",
    "rvandroid:llama:batch@temperature=0.3,model=llama3"
  ]
}
```

## Programmatic Usage

### Basic Configuration
```python
from rv_experiment.config import ExperimentConfiguration, ToolConfiguration

# Create tool configurations
tool_configs = [
    ToolConfiguration(
        name="monkey",
        variants=["fixed_seed"],
        parameters={"seed": 42}
    ),
    ToolConfiguration(
        name="droidbot",
        variants=["dfs_greedy"],
        parameters={"count": 1000}
    )
]

# Create experiment configuration
config = ExperimentConfiguration(
    name="my_experiment",
    tool_configs=tool_configs,
    execution={"repetitions": 3, "timeouts": [300]}
)
```

### From Specification Strings
```python
from rv_experiment.config import ToolConfiguration

# Parse tool specification
tool_config = ToolConfiguration.from_spec_string("rvandroid:llama:batch@temperature=0.3")
print(f"Tool: {tool_config.name}")
print(f"Variants: {tool_config.variants}")
print(f"Parameters: {tool_config.parameters}")
```

### Experiment Execution
```python
from rv_experiment.orchestrator import ExperimentOrchestrator

# Create and execute experiment
orchestrator = ExperimentOrchestrator(config)
success = orchestrator.execute_single_tool_experiment()
```

## Legacy Integration

The module provides seamless integration with legacy main.py through a bridge pattern:

```python
# Legacy main.py usage continues to work
python main.py --no_window -tools monkey:fixed_seed droidbot:dfs_greedy -r 3

# Modern usage provides enhanced capabilities
rv-experiment run-comparative --tools monkey:fixed_seed,droidbot:dfs_greedy --repetitions 3
```

## Module Coordination

The rv-experiment module coordinates with other specialized modules:

- **rv-monitor-generator**: Generates runtime verification monitors
- **rv-instrumentation**: Instruments APKs with monitoring code
- **rv-static-analysis**: Performs static analysis with GATOR, GESDA, REACH
- **rv-screen-parser**: Parses UI screenshots and layouts
- **rv-coverage**: Tracks and analyzes code coverage
- **rv-llm**: Provides LLM integration for intelligent testing

## Configuration Examples

### Tool Variant Examples

```bash
# DroidBot with different exploration strategies
rv-experiment run-single --tool droidbot:dfs_greedy
rv-experiment run-single --tool droidbot:bfs_naive

# RVAndroid with different LLM models
rv-experiment run-single --tool rvandroid:llama
rv-experiment run-single --tool rvandroid:gpt4:batch
rv-experiment run-single --tool rvandroid:claude:single_action

# Monkey with specific configurations
rv-experiment run-single --tool monkey:fixed_seed@seed=123
rv-experiment run-single --tool monkey:low_throttle@throttle=25

# FastBot speed variants
rv-experiment run-single --tool fastbot:fast
rv-experiment run-single --tool fastbot:slow
```

### Comparative Studies

```bash
# Compare exploration strategies
rv-experiment run-comparative \
  --tools droidbot:dfs_greedy,droidbot:bfs_greedy,droidbot:dfs_naive,droidbot:bfs_naive \
  --repetitions 5

# Compare LLM approaches
rv-experiment run-comparative \
  --tools rvandroid:llama:batch,rvandroid:gpt4:batch,rvandroid:claude:single_action \
  --timeouts 600,1200

# Traditional vs AI-guided testing
rv-experiment run-comparative \
  --tools monkey:fixed_seed,droidbot:dfs_greedy,rvandroid:llama:batch \
  --repetitions 10
```

## Output and Results

Experiments generate comprehensive outputs:

- **Logs**: Detailed execution logs with contextual information
- **Results**: Coverage metrics, error reports, performance data
- **Reports**: Comparative analysis and visualizations
- **Artifacts**: Generated monitors, instrumented APKs, analysis results

## Development and Testing

### Local Development
```bash
# Quick local test with default tools
rv-experiment run-local

# Custom local development setup
rv-experiment run-local --tools monkey:fixed_seed,ape --timeout 60

# Development with specific variants
rv-experiment run-local --tools droidbot:dfs_greedy@count=100 --repetitions 1
```

### Configuration Validation
```bash
# Validate configuration without execution
rv-experiment run-batch --config-file config.json --dry-run

# Generate and validate template
rv-experiment generate-config --format json --output test-config.json
rv-experiment run-batch --config-file test-config.json --dry-run
```

## Architecture

The module implements a modern, modular architecture:

- **CLI Layer**: Click-based command interface with comprehensive options
- **Configuration Layer**: Type-safe dataclass-based configuration
- **Orchestration Layer**: Coordinates execution across modules
- **Bridge Layer**: Maintains compatibility with legacy systems
- **Integration Layer**: Interfaces with specialized modules

## Migration Guide

### From Legacy main.py

**Old**:
```bash
python main.py --no_window -tools rvandroid:llama_batch -r 3 -t 300 600
```

**New**:
```bash
rv-experiment run-single --tool rvandroid:llama:batch --repetitions 3 --timeouts 300,600 --no-window
```

### Configuration Migration

**Old settings.py usage**: Automatically handled by bridge pattern

**New configuration**: Use modern ExperimentConfiguration with type safety and validation

## Contributing

When adding new tool variants or parameters:

1. Update tool registry with new variants
2. Add examples to this README
3. Update configuration templates
4. Add tests for new variants

## Troubleshooting

### Common Issues

**Tool not found**: Ensure tool is registered in the tool registry
```bash
rv-experiment list-tools
```

**Variant not recognized**: Check available variants for the tool
```bash
# Check main.py for registered variants
python main.py --list-tools
```

**Configuration errors**: Validate configuration before execution
```bash
rv-experiment run-batch --config-file config.json --dry-run
```

### Debug Mode
```bash
# Enable debug logging
rv-experiment --debug run-single --tool monkey
```

## License

Part of the RV-Android platform. See main repository for license information.