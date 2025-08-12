# RV-Experiment Module

Experiment orchestration system for monitored operations testing in Android applications with comprehensive lifecycle management.

## Overview

The RV-Experiment module serves as the orchestrator for monitored operations experiments in the RV-Android ecosystem. It manages the complete experiment lifecycle including APK instrumentation, static analysis generation, experiment configuration, and coordination with rv-platform for task execution and result processing. The module provides factory components for tool configuration and supports multi-instance configurations for parallel testing.

### Key Features

- **Experiment Orchestration**: Complete lifecycle management from pre-processing to result analysis
- **APK Instrumentation**: Instruments APKs for runtime verification and monitoring
- **Static Analysis Generation**: Generates static analysis files for consumption by rv-platform
- **Configuration Management**: Comprehensive experiment configuration with validation and templates
- **RV-Platform Coordination**: Coordinates with rv-platform for task execution and result processing
- **Multi-Instance Support**: Factory components for independent tool configurations
- **Monitored Operations**: Support for JCA crypto and generic specification monitoring
- **CLI Interface**: Four core commands (run, config, list-tools, validate)
- **Variant System**: Tool variant support with predefined configurations and flexible parameter overrides

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
- **Variant Resolution**: Automatic resolution of tool variants with parameter merging

#### Factory System
- **RvAndroidConfigFactory**: Factory for creating RVAndroid tool configurations with multi-instance support
- **Hybrid Configuration**: Support for pre-configured variants and manual configuration
- **Tool-Specific Factories**: Factory components for different tool types

#### Execution System
- **execute_with_config()**: Direct execution function for experiment orchestration
- **Tool Registry Integration**: Direct access to rv-tools registry for tool creation
- **Error Handling**: Comprehensive error management using rv-android-core decorators

### Integration Points

- **rv-platform**: Task execution and result processing coordination
- **rv-tools**: Tool registry and factory system integration
- **rv-android-core**: Infrastructure services (logging, error handling, validation)
- **rv-instrumentation**: APK instrumentation for monitored operations
- **rv-static-analysis**: Static analysis generation and processing
- **rv-llm**: LLM configuration factory support for AI-driven tools
- **rvandroid-tool**: Tool-specific configuration factory integration

## Installation

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- All RV-Android core modules
- Android SDK for APK processing

### Setup

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Install CLI command
poetry install
```

## Usage

### Basic Experiment Execution

```bash
# Run experiment with default configuration
poetry run rv-experiment run --app /path/to/app.apk

# Run with specific tools and variants
poetry run rv-experiment run \
    --app /path/to/app.apk \
    --tools "droidbot:dfs_greedy,ape:sata,rvandroid:default" \
    --timeout 300

# Run with custom configuration
poetry run rv-experiment run \
    --config /path/to/config.json \
    --results-dir /path/to/results
```

### Configuration Management

```bash
# Generate configuration template with variants
poetry run rv-experiment config basic \
    --tools "droidbot:dfs_greedy,ape:sata,rvandroid:default" \
    --output config.json

# Validate configuration
poetry run rv-experiment validate config.json

# List available tools
poetry run rv-experiment list-tools
```

### Multi-Instance RVAndroid Configuration

```python
from rv_experiment.factories.rvandroid_config_factory import RvAndroidConfigFactory
from rv_experiment.config.tool_config import ToolConfig
from rv_experiment.config.experiment_config import ExperimentConfig

# Create experiment configuration
experiment_config = ExperimentConfig(
    app_path="/path/to/app.apk",
    timeout=300,
    spec_set="jca"
)

# Configuration 1: Pre-configured variant
tool_config_1 = ToolConfig(
    name="rvandroid",
    variants=["llama_batch_detailed"],
    parameters={"temperature": "0.2"}
)

rv_config_1 = RvAndroidConfigFactory.create_from_tool_config(
    tool_config=tool_config_1,
    experiment_config=experiment_config
)

# Configuration 2: Manual configuration
tool_config_2 = ToolConfig(
    name="rvandroid",
    variants=[],
    parameters={
        "llm_backend": "ollama",
        "llm_model": "qwen2.5:7b",
        "prompt_strategy": "standard_modular",
        "visitor_type": "basic",
        "temperature": "0.7"
    }
)

rv_config_2 = RvAndroidConfigFactory.create_from_tool_config(
    tool_config=tool_config_2,
    experiment_config=experiment_config
)

# Access configuration components
llm_config_1 = experiment_config.get_llm_config("rvandroid")
prompt_config_1 = experiment_config.get_prompt_config("rvandroid")

# Each configuration creates independent tool instances
print(f"Config 1 LLM: {rv_config_1.llm_config.model}")
print(f"Config 2 LLM: {rv_config_2.llm_config.model}")
print(f"Config 1 Strategy: {rv_config_1.prompt_config.strategy_type}")
```

### Programmatic Interface

```python
from rv_experiment.config.experiment_config import ExperimentConfig
from rv_experiment.execution.execute_with_config import execute_with_config

# Create experiment configuration
config = ExperimentConfig(
    app_path="/path/to/app.apk",
    tools=[
        {
            "name": "droidbot",
            "variants": ["dfs_greedy"],
            "parameters": {"timeout": "300"}
        },
        {
            "name": "rvandroid",
            "variants": ["llama_batch_detailed"],
            "parameters": {"temperature": "0.2"}
        }
    ],
    timeout=600,
    spec_set="jca"
)

# Execute experiment
results = execute_with_config(config)
```

### Factory Configuration Examples

```python
from rv_experiment.factories.rvandroid_config_factory import RvAndroidConfigFactory, RVANDROID_VARIANTS

# List available pre-configured variants
print("Available variants:")
for variant_name, variant_config in RVANDROID_VARIANTS.items():
    print(f"  {variant_name}: {variant_config}")

# Create from variant name
tool_config = ToolConfig(
    name="rvandroid",
    variants=["gpt4_standard_basic"],
    parameters={"api_key": "sk-..."}
)

rv_config = RvAndroidConfigFactory.create_from_tool_config(
    tool_config=tool_config,
    experiment_config=experiment_config
)

# Hybrid configuration (variant + overrides)
tool_config_hybrid = ToolConfig(
    name="rvandroid",
    variants=["llama_batch_detailed"],  # Base configuration
    parameters={
        "temperature": "0.5",           # Override temperature
        "max_tokens": "1000",          # Override max_tokens
        "timeout": "1200"              # Add custom parameter
    }
)

rv_config_hybrid = RvAndroidConfigFactory.create_from_tool_config(
    tool_config=tool_config_hybrid,
    experiment_config=experiment_config
)
```

## Configuration

### Experiment Configuration

```python
from rv_experiment.config.experiment_config import ExperimentConfig
from rv_experiment.constants import SPEC_SET_JCA, SPEC_SET_GENERIC

config = ExperimentConfig(
    app_path="/path/to/app.apk",
    tools=[
        {
            "name": "droidbot",
            "variants": ["dfs_greedy"],
            "parameters": {"timeout": "300"}
        }
    ],
    timeout=600,
    spec_set=SPEC_SET_JCA,          # JCA crypto monitoring
    results_dir="/path/to/results",
    instrumentation_enabled=True,
    static_analysis_enabled=True
)
```

### Tool Configuration

```python
from rv_experiment.config.tool_config import ToolConfig

# Simple tool configuration
tool_config = ToolConfig(
    name="droidbot",
    variants=["dfs_greedy"],
    parameters={"timeout": "300"}
)

# Complex RVAndroid configuration
rvandroid_config = ToolConfig(
    name="rvandroid",
    variants=["llama_batch_detailed"],
    parameters={
        "temperature": "0.2",
        "max_tokens": "800",
        "timeout": "600"
    }
)
```

### RVAndroid Variants

Pre-configured variants available in RvAndroidConfigFactory:

```python
RVANDROID_VARIANTS = {
    "llama_batch_detailed": {
        "llm_backend": "ollama",
        "llm_model": "llama3.2:3b",
        "prompt_strategy": "batch_action_modular",
        "visitor_type": "detailed",
        "screen_parser": "droidbot"
    },
    "gpt4_standard_basic": {
        "llm_backend": "openai",
        "llm_model": "gpt-4",
        "prompt_strategy": "standard_modular",
        "visitor_type": "basic",
        "screen_parser": "droidbot"
    },
    "claude_context_enhanced": {
        "llm_backend": "anthropic",
        "llm_model": "claude-3-5-sonnet-20241022",
        "prompt_strategy": "standard_modular",
        "visitor_type": "enhanced",
        "screen_parser": "droidbot"
    }
}
```

## CLI Commands

### run

Execute experiments with comprehensive configuration.

```bash
poetry run rv-experiment run [OPTIONS]

Options:
  --app PATH               APK file path (required)
  --tools TEXT            Tool specifications with variants (e.g., "droidbot:dfs_greedy,ape:sata,rvandroid:default")
  --config PATH           Configuration file path
  --results-dir PATH      Results directory
  --timeout INTEGER       Experiment timeout in seconds
  --spec-set TEXT         Specification set (jca, generic)
```

### config

Generate configuration templates.

```bash
poetry run rv-experiment config [template_type] [OPTIONS]

Templates:
  basic                   Basic experiment configuration
  advanced               Advanced multi-tool configuration
  research               Research-oriented configuration with multiple variants

Options:
  --tools TEXT           Tool specifications
  --output PATH          Output file path
  --timeout INTEGER      Default timeout
```

### list-tools

List available tools and variants.

```bash
poetry run rv-experiment list-tools [OPTIONS]

Options:
  --detailed             Show detailed tool information
  --tool TEXT           Show specific tool information
```

### validate

Validate experiment configurations.

```bash
poetry run rv-experiment validate [config_file] [OPTIONS]

Options:
  --strict              Enable strict validation
  --fix                 Attempt to fix common issues
```

## Factory System

### RvAndroidConfigFactory

```python
from rv_experiment.factories.rvandroid_config_factory import RvAndroidConfigFactory

class RvAndroidConfigFactory:
    @classmethod
    def create_from_tool_config(cls, tool_config: ToolConfig, experiment_config: ExperimentConfig) -> RvAndroidToolConfig:
        """Create RvAndroidToolConfig from ToolConfig with hybrid support."""
        
    @classmethod
    def resolve_configuration(cls, tool_config: ToolConfig) -> Dict[str, Any]:
        """Resolve configuration from variants and parameters."""
        
    @classmethod
    def get_supported_variants(cls) -> List[str]:
        """Get list of supported pre-configured variants."""
```

### Multi-Instance Support

```python
# Create multiple independent configurations
configs = []
for i in range(3):
    tool_config = ToolConfig(
        name="rvandroid",
        variants=["llama_batch_detailed"],
        parameters={"temperature": str(0.2 + i * 0.1)}
    )
    
    rv_config = RvAndroidConfigFactory.create_from_tool_config(
        tool_config=tool_config,
        experiment_config=experiment_config
    )
    
    configs.append(rv_config)

# Each configuration is independent
for i, config in enumerate(configs):
    print(f"Config {i+1}: {config.llm_config.temperature}")
```

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=rv_experiment

# Run specific test categories
poetry run pytest tests/factories/
poetry run pytest tests/config/
```

### Test Structure

- `tests/factories/`: Factory system tests
- `tests/config/`: Configuration management tests
- `tests/execution/`: Execution system tests
- `tests/cli/`: CLI interface tests

## Performance Characteristics

### Factory Operations
- **Configuration Creation**: < 10ms per instance
- **Variant Resolution**: < 5ms per variant lookup
- **Multi-Instance Setup**: < 50ms for 10 instances

### Configuration Management
- **Validation**: 10-50ms per configuration
- **Template Generation**: 5-20ms per template
- **Serialization**: < 10ms per configuration

## Error Handling

The module provides comprehensive error handling:

- **Configuration Errors**: Validation failures, missing parameters, invalid tool specifications
- **Factory Errors**: Variant resolution failures, parameter validation errors
- **Execution Errors**: Tool creation failures, experiment orchestration issues
- **CLI Errors**: Command parsing failures, file access issues

## Dependencies

- `rv-android-core`: Core infrastructure and utilities
- `rv-platform`: Task execution and result processing
- `rv-tools`: Tool registry and factory system
- `rv-llm`: LLM configuration support
- `rvandroid-tool`: Tool-specific configuration classes
- `click`: CLI framework
- `pydantic`: Configuration validation

## Contributing

### Development Guidelines

1. Follow existing architectural patterns for factory components
2. Use comprehensive error handling with rv-android-core infrastructure
3. Implement proper logging for debugging and monitoring
4. Add tests for new factory methods and configuration options
5. Document configuration templates and usage patterns

### Factory Design Principles

1. Support hybrid configuration (variants + parameters)
2. Provide clear error messages for configuration issues
3. Maintain backward compatibility with existing configurations
4. Use type-safe configuration with validation
5. Support multi-instance scenarios with independent configurations

## License

This module is part of the RV-Android project and follows the same licensing terms.