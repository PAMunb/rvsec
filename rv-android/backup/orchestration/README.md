# Advanced Experiment Orchestration System

This directory contains the implementation of an advanced experiment orchestration system for RV-Android, designed to improve experiment execution performance, reliability, and flexibility.

## Key Features

- Multiple execution strategies (Sequential, Parallel, Adaptive, Priority-based)
- Comprehensive tracking and statistics
- Advanced error handling and recovery
- Checkpointing for experiment resilience
- Event-driven architecture for better coordination
- Integration with existing experiment workflow

## Architecture

The orchestration system is designed with a modular, component-based architecture:

- `interfaces.py`: Core interfaces and enums
- `tracker.py`: Execution tracking and statistics
- `execution.py`: Execution strategy implementations
- `orchestrator.py`: Main orchestrator implementation
- `integration.py`: Integration with existing experiment workflow

## Execution Strategies

The system supports multiple execution strategies:

- **Sequential**: Execute tasks one after another
- **Parallel**: Execute tasks concurrently with configurable concurrency
- **Adaptive**: Adjust concurrency based on resource availability
- **Priority**: Execute tasks based on priority levels

## Integration with Existing Workflow

The `integration.py` module provides adapters and integration points to connect the new orchestration system with the existing experiment workflow:

- `OrchestratorAdapter`: Adapter for the new orchestration system
- `LegacyExecutionStrategyAdapter`: Adapter for using legacy execution manager

## Usage

### Command-Line Interface

Use the enhanced experiment controller through the CLI:

```bash
python -m rvandroid.experiment.cli --enhanced --orchestration-mode parallel
```

CLI options:
- `--enhanced`: Use the enhanced experiment controller
- `--orchestration-mode`: Specify the orchestration mode (sequential, parallel, adaptive, priority)
- `--repetitions`: Number of repetitions
- `--timeouts`: Timeout durations
- `--tools`: Testing tools to use
- `--memory-file`: Memory file for resumption
- `--no-generate-monitors`: Skip monitor generation
- `--no-instrument`: Skip instrumentation
- `--no-static-analysis`: Skip static analysis
- `--skip-experiment`: Skip experiment execution
- `--no-window`: Run emulator in headless mode
- `--log-level`: Logging level

### Programmatic Usage

```python
from rvandroid.experiment.enhanced_experiment_controller import execute_enhanced
from rvandroid.tools.registry import ToolRegistry

# Get tools from registry
registry = ToolRegistry.get_instance()
tools = registry.get_tools(['monkey', 'droidbot'])

# Execute enhanced experiment
result = execute_enhanced(tools)
```

### Using the Integration Factory

```python
from rvandroid.experiment.integration_factory import IntegrationFactory
from rvandroid.experiment.orchestration.interfaces import OrchestrationMode

# Create integration factory
factory = IntegrationFactory()

# Create orchestrator adapter
orchestrator = factory.create_orchestrator_adapter(
    results_dir='/path/to/results',
    task_storage=task_storage,
    execution_mode=OrchestrationMode.PARALLEL
)

# Set up experiment
orchestrator.setup(
    apks=apps,
    repetitions=3,
    timeouts=[60, 120],
    tools=tools
)

# Run experiment
orchestrator.run()
```

## Extending the System

The system is designed to be extensible. To add a new execution strategy:

1. Implement the `ExecutionStrategy` interface in `interfaces.py`
2. Register the strategy with the orchestrator

Example:

```python
from rvandroid.experiment.orchestration.interfaces import ExecutionStrategy

class MyCustomStrategy(ExecutionStrategy):
    def execute(self, tasks, **kwargs):
        # Custom execution logic
        pass
```

## Integration with Results Analysis

The orchestration system integrates with the advanced results analysis system:

```python
from rvandroid.analysis.results.integration import AnalysisAdapter

# Create analysis adapter
adapter = AnalysisAdapter(results_dir='/path/to/results')

# Process results with advanced analysis
results = adapter.process_results()
```