# RVAgent Tool

Tool wrapper for rv-agent integration with rv-platform.

## Overview

This module provides an `AbstractTool` implementation that wraps rv-agent for execution within the rv-platform task execution framework. It enables rv-agent to be used as a testing tool alongside other tools like Monkey, DroidBot, etc.

## Features

- **Platform Integration**: Implements `AbstractTool` interface for seamless rv-platform integration
- **Static Analysis Support**: Receives and uses static analysis data from platform context
- **Multiple Variants**: Supports different execution modes (multimode, pure_algorithm, llm_only)
- **Configuration Mapping**: Maps platform Task/ToolConfig to RVAgentConfig

## Installation

```bash
cd modules/rvagent-tool
poetry install
```

Or install all modules:

```bash
cd modules
./install.sh rvagent-tool
```

## Usage

### Via rv-experiment CLI

```bash
# Run with default multimode variant
rv-experiment run --tools rvagent --apks-dir ./apks_examples

# Run with specific variant
rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples

# Run with multiple tools
rv-experiment run --tools monkey,rvagent:multimode,droidbot:dfs_greedy --apks-dir ./apks_examples
```

### Available Variants

| Variant | Description |
|---------|-------------|
| `default` | Multimode (70% LLM, 30% algorithm) |
| `multimode` | Same as default |
| `pure_algorithm` | Algorithmic exploration only (no LLM) |
| `llm_only` | LLM-driven exploration only |
| `thorough` | Multimode with 80% LLM, larger plateau window |

**Note**: Timeout is always controlled by the platform Task configuration, not by variants.

### Programmatic Usage

```python
from rv_tools import ToolRegistry, ToolFactory
from rv_android_core.domain.task import ToolConfig

# Get registry (auto-registers rvagent via rv-experiment)
from rv_experiment.tools import ExperimentToolRegistry
registry = ExperimentToolRegistry.get_instance()

# Create tool configuration
tool_config = ToolConfig(
    tool_name="rvagent",
    variant="multimode",
    additional_params={"timeout": 900}
)

# Create tool instance
factory = ToolFactory()
tool = factory.create_tool(tool_config)

# Execute (within platform context)
# tool.execute(task, app)
```

## Architecture

### Tool Registration Flow

```
rv-experiment imports ExperimentToolRegistry
    |
    v
ExperimentToolRegistry.register_external_tools()
    |
    v
_register_rvagent_tool()
    |
    v
rvagent_tool.tools.rvagent.tool.RVAgentTool registered
```

### Execution Flow

```
Platform.TaskExecutor.execute()
    |
    v
ToolExecutionComponent.execute()
    |
    v
RVAgentTool.execute_tool_specific_logic(task, app)
    |
    +-> build_agent_config_dict(task, app, tool_config)
    +-> get_static_data(task)
    |
    v
AgentFactory.create_agent(config, static_data)
    |
    v
RVAgent.run()
```

## Dependencies

- `rv-android-core`: Core infrastructure (AbstractTool, domain models)
- `rv-agent`: LLM-driven testing agent
- `rv-tools`: Tool registry and factory

## Testing

```bash
cd modules/rvagent-tool

# Run unit tests
poetry run pytest tests/unit/ -v

# Run with coverage
poetry run pytest --cov=src --cov-report=html
```
