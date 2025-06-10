# RV-Experiment Module

Modern experiment orchestration and management system for monitored operations testing in Android applications with dependency injection architecture.

## Overview

The RV-Experiment module serves as the central orchestration hub for all monitored operations experiments in the RV-Android ecosystem. It provides comprehensive experiment management, execution coordination, and result analysis while supporting both JCA cryptography and generic programming pattern specifications through a modern, factory-based architecture.

### Key Features

- **Modern CLI**: Simplified 3-command interface with intelligent tool parsing and configuration
- **DI-Ready Architecture**: Full dependency injection support with lifecycle management
- **Experiment Orchestration**: Comprehensive experiment coordination with multi-tool support
- **Directory Management**: Standardized ./out/ directory structure for all operations
- **Configuration System**: Flexible configuration with templates and validation
- **Factory Pattern**: Modern LLM and strategy factories for component creation
- **Monitored Operations**: Support for both JCA crypto and generic specification monitoring
- **Tool Integration**: Seamless integration with all rv-tools module testing tools

## Architecture

### Core Components

#### Experiment Management
- **SimpleExperimentConfig**: Simplified configuration with DI-ready design and template support
- **SimplifiedOrchestrator**: Modern orchestrator using factory pattern and comprehensive error handling
- **ExperimentDirectoryManager**: Standardized ./out/ directory structure with specification separation

#### Dependency Injection System
- **ComponentLifecycleManager**: Complete lifecycle management with dependency graph resolution
- **ConfigurationProvider**: Multi-source configuration (files, environment, programmatic)
- **DependencyRegistry**: Full DI container with type-safe component registration

#### Tool Integration
- **Tool Specification DSL**: Advanced tool parsing with variants and parameters
- **Multi-Tool Coordination**: Seamless execution of multiple testing tools
- **Result Aggregation**: Comprehensive result collection and analysis

#### Directory Structure
```
./out/
├── experiments/{experiment_id}/     # Individual experiment results
│   ├── config.json                  # Experiment configuration
│   ├── logs/                        # Experiment-specific logs
│   ├── results/                     # Results and analysis data
│   └── traces/                      # Execution traces and coverage
├── instrumented/                    # Shared instrumented APKs  
│   ├── jca/                         # JCA crypto monitored APKs
│   ├── generic/                     # Generic pattern monitored APKs
│   └── cache/                       # Instrumentation cache
├── monitors/                        # Generated monitor files
│   ├── jca/                         # JCA crypto specifications
│   ├── generic/                     # Generic programming patterns  
│   └── custom/                      # Custom specification sets
├── static/                          # Static analysis results
│   ├── gator/                       # Gator analysis results
│   ├── gesda/                       # GESDA analysis results
│   └── reach/                       # Reachability analysis results
└── cache/                           # Component and tool cache
    ├── tools/                       # Tool-specific cache
    ├── models/                      # LLM model cache
    └── temp/                        # Temporary files
```

### Integration Points

- **rv-android-core**: Uses ErrorHandler decorators, LoggingManager, and EventBus
- **rv-llm**: Integrates LLMFactory and PromptStrategyFactory for AI-driven testing
- **rv-tools**: Coordinates with all testing tools through registry integration
- **rv-static-analysis**: Manages static analysis integration and result processing
- **rv-coverage**: Coordinates coverage tracking and analysis
- **rv-monitor-generator**: Integrates monitor generation for both JCA and generic specs

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

### Modern CLI Interface

#### Basic Experiment Execution

```bash
# Simple experiment with single tool
rv-experiment run --tools monkey

# Multi-tool experiment with configuration
rv-experiment run --tools monkey,droidbot:dfs_greedy,rvandroid:llama:batch@temperature=0.3

# JCA cryptography monitoring experiment
rv-experiment run --tools rvandroid:llama:standard@specification_set=jca,temperature=0.2

# Generic programming patterns experiment  
rv-experiment run --tools droidbot:dfs_greedy,ape@specification_set=generic
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
rvandroid:llama:batch
rvandroid:claude:standard

# Tools with parameters
rvandroid:llama@temperature=0.3,max_tokens=2048
droidbot:dfs_greedy@timeout=600,enable_accessibility=true

# Multiple tools combination
monkey,droidbot:dfs_greedy,rvandroid:llama:batch@temperature=0.2,specification_set=jca
```

#### Configuration Templates

```bash
# Generate basic configuration template
rv-experiment generate-config --template-type basic --output basic_config.json

# Generate advanced configuration with all options
rv-experiment generate-config --template-type advanced --format yaml --output advanced.yaml

# Generate LLM-focused configuration for AI-driven testing
rv-experiment generate-config --template-type llm_focused --output llm_experiment.json
```

#### Tool Management

```bash
# List all available tools
rv-experiment list-tools

# Show detailed tool information
rv-experiment list-tools --detailed

# Filter by tool category
rv-experiment list-tools --filter-by llm --detailed
```

### Programmatic Usage

#### Modern Configuration

```python
from rv_experiment.config import SimpleExperimentConfig
from rv_experiment.orchestrator import SimplifiedOrchestrator

# Create experiment configuration
config = SimpleExperimentConfig(
    experiment_dir="./out/",
    experiment_id="crypto_analysis_001",
    tools=[
        {"name": "monkey", "variants": [], "parameters": {}},
        {"name": "rvandroid", "variants": ["llama", "batch"], 
         "parameters": {"temperature": 0.3, "specification_set": "jca"}}
    ],
    specification_set="jca",  # JCA cryptography monitoring
    timeout=300,
    repetitions=3,
    apk_patterns=["*.apk"]
)

# Validate configuration
config.validate()

# Execute experiment
orchestrator = SimplifiedOrchestrator(config)
success = orchestrator.execute()
```

#### DI-Ready Architecture

```python
from rv_experiment.di import ComponentLifecycleManager, ConfigurationProvider, DependencyRegistry
from rv_experiment.di.interfaces import IExperimentOrchestrator, IDirectoryManager

# Initialize DI system
lifecycle_manager = ComponentLifecycleManager()
config_provider = ConfigurationProvider(config_files=["experiment.yaml"])
registry = DependencyRegistry()

# Register components
registry.register(IExperimentOrchestrator, SimplifiedOrchestrator)
registry.register(IDirectoryManager, ExperimentDirectoryManager)

# Register component with lifecycle management
lifecycle_manager.register_component(
    "orchestrator", 
    registry.get(IExperimentOrchestrator),
    dependencies=["directory_manager", "llm_factory"],
    config=config_provider.get_config("orchestrator")
)

# Initialize all components
lifecycle_manager.initialize_all()
lifecycle_manager.start_all()

# Execute experiment
orchestrator = registry.get(IExperimentOrchestrator)
result = orchestrator.execute()

# Graceful shutdown
lifecycle_manager.stop_all()
```

#### Directory Management

```python
from rv_experiment.directory_manager import ExperimentDirectoryManager

# Initialize directory manager
dir_manager = ExperimentDirectoryManager("./out/")

# Create complete directory structure
dir_manager.create_full_structure()

# Create experiment-specific directory
experiment_dir = dir_manager.create_experiment_directory(
    experiment_id="jca_crypto_001",
    specification_set="jca"
)

# Get specification-specific directories
jca_instrumented = dir_manager.get_instrumented_dir("jca")
generic_instrumented = dir_manager.get_instrumented_dir("generic")
jca_monitors = dir_manager.get_monitors_dir("jca")

# Cache management
models_cache = dir_manager.get_cache_dir("models")
cleaned_files = dir_manager.cleanup_temp_files(max_age_hours=24)
```

#### Factory Integration

```python
from rv_llm.factories import LLMFactory, PromptStrategyFactory

# Create factories
llm_factory = LLMFactory()
strategy_factory = PromptStrategyFactory()

# Create LLM for JCA cryptography monitoring
jca_llm = llm_factory.create_ollama(
    model="llama3",
    temperature=0.2,
    specification_context="jca_crypto"
)

# Create strategy for batch action generation
batch_strategy = strategy_factory.create_batch_action(
    batch_size=3,
    use_action_coordination=True,
    specification_aware=True
)

# Configuration-driven creation
llm_config = {
    "provider": "ollama",
    "model": "llama3",
    "temperature": 0.3,
    "specification_set": "generic"
}
generic_llm = llm_factory.create_from_config(llm_config)
```

### Experiment Templates

#### Basic Experiment Template

```json
{
  "experiment_id": "basic_001",
  "specification_set": "generic",
  "tools": [
    {"name": "monkey", "variants": [], "parameters": {"timeout": 300}},
    {"name": "droidbot", "variants": ["dfs_greedy"], "parameters": {}}
  ],
  "timeout": 300,
  "repetitions": 1,
  "apk_patterns": ["*.apk"],
  "generate_monitors": true,
  "instrument_apks": true,
  "run_static_analysis": true
}
```

#### LLM-Focused Template

```json
{
  "experiment_id": "llm_jca_001", 
  "specification_set": "jca",
  "tools": [
    {
      "name": "rvandroid",
      "variants": ["llama", "batch"],
      "parameters": {
        "temperature": 0.2,
        "max_tokens": 2048,
        "specification_context": "jca_crypto",
        "monitored_operations_focus": true
      }
    },
    {
      "name": "rvandroid", 
      "variants": ["claude", "standard"],
      "parameters": {
        "temperature": 0.1,
        "specification_context": "jca_crypto"
      }
    }
  ],
  "timeout": 600,
  "repetitions": 3,
  "llm_config": {
    "providers": ["ollama", "anthropic"],
    "fallback_strategy": "graceful_degradation",
    "context_management": "specification_aware"
  }
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
poetry run pytest tests/experiment/
poetry run pytest tests/di/
poetry run pytest tests/config/
```

### Test Structure

- `tests/experiment/`: Experiment management and orchestration tests
- `tests/di/`: Dependency injection system tests
- `tests/config/`: Configuration management tests
- `tests/directory/`: Directory management tests
- `tests/integration/`: Cross-component integration tests

## Performance Characteristics

### Experiment Execution
- **Small Experiments** (1-3 tools): 2-5 minutes typical execution
- **Large Experiments** (5+ tools): 10-30 minutes depending on tool configuration
- **LLM Integration**: Additional 1-3 minutes for model initialization

### DI System
- **Component Resolution**: < 1ms for singleton resolution
- **Lifecycle Management**: < 100ms for complete system startup
- **Configuration Loading**: < 50ms for typical configuration files

### Directory Management
- **Structure Creation**: < 10ms for complete directory structure
- **Experiment Setup**: < 5ms per experiment directory
- **Cache Cleanup**: < 100ms for typical cache sizes

## Monitored Operations Support

### JCA Cryptography Specifications

```bash
# JCA-focused experiment
rv-experiment run --tools rvandroid:llama:batch@specification_set=jca,crypto_context=true

# JCA specification monitoring with multiple tools
rv-experiment run --tools monkey,rvandroid:llama:standard@specification_set=jca
```

### Generic Programming Pattern Specifications

```bash
# Generic patterns experiment
rv-experiment run --tools droidbot:dfs_greedy,rvandroid:claude:batch@specification_set=generic

# Iterator pattern monitoring
rv-experiment run --tools rvandroid:llama@specification_set=generic,pattern_focus=iterator
```

### Custom Specification Sets

```bash
# Custom specification experiment
rv-experiment run --tools rvandroid:llama@specification_set=custom,spec_file=/path/to/custom.specs
```

## Integration Examples

### Cross-Module Integration

```python
# Complete experiment with all modules
from rv_experiment.config import SimpleExperimentConfig
from rv_experiment.orchestrator import SimplifiedOrchestrator
from rv_llm.factories import LLMFactory
from rv_tools.registry import ToolRegistry
from rv_static_analysis.analysis import StaticAnalysisManager

# Setup experiment for JCA cryptography monitoring
config = SimpleExperimentConfig(
    specification_set="jca",
    tools=[
        {"name": "rvandroid", "variants": ["llama", "batch"], 
         "parameters": {"specification_context": "jca_crypto"}}
    ]
)

# Execute with full integration
orchestrator = SimplifiedOrchestrator(config)
orchestrator.execute()
```

### Tool Integration Pattern

```python
# Standard tool integration with experiment framework
from rv_experiment.interfaces import IToolExecutor
from rv_android_core.util.error.decorators import handle_errors

class CustomToolExecutor(IToolExecutor):
    @handle_errors(component="CustomTool", operation="execute")
    def execute(self, task, config):
        """Execute tool with experiment framework integration."""
        with self.logger.with_context(tool=self.name, specification=config.specification_set):
            # Tool execution with monitored operations support
            result = self._run_tool_with_monitoring(task, config)
            
            # Publish results to experiment framework
            self.event_bus.publish_tool_event(
                EventType.TOOL_COMPLETED,
                tool_name=self.name,
                specification_set=config.specification_set,
                results=result
            )
            
            return result
```

## Architecture Guidelines

### Configuration Best Practices

- Use SimpleExperimentConfig for all experiment definitions
- Leverage configuration templates for common scenarios
- Validate configurations before experiment execution
- Use specification_set parameter to separate JCA and generic monitoring

### DI System Usage

- Register components with clear interface contracts
- Use lifecycle management for complex component hierarchies
- Implement proper dependency ordering
- Use configuration providers for flexible component setup

### Tool Integration Standards

- Follow tool specification DSL for consistent parameter passing
- Implement proper error handling with rv-android-core decorators
- Use event system for loose coupling between components
- Support both JCA and generic specification monitoring

### Directory Management

- Always use ExperimentDirectoryManager for path management
- Maintain separation between JCA and generic specification directories
- Use caching strategies for improved performance
- Implement proper cleanup for temporary files

## Contributing

### Code Standards

- Follow modern architecture patterns with DI-ready design
- Use comprehensive type hints for all public interfaces
- Include detailed docstrings following Google style
- Maintain separation between JCA crypto and generic specification logic

### Testing Requirements

- Achieve 100% test coverage for all public interfaces
- Include integration tests for cross-module functionality
- Test both JCA and generic specification scenarios
- Implement performance benchmarks for critical paths

### Architecture Principles

- Maintain factory-based component creation
- Use dependency injection for all component relationships
- Implement comprehensive error handling with context
- Follow event-driven architecture for component communication

## License

This module is part of the RV-Android project and follows the same licensing terms.