# RVAgent Tool

Tool wrapper for rv-agent integration with rv-platform.

## Overview

This module provides an `AbstractTool` implementation that wraps rv-agent for execution within the rv-platform task execution framework. It enables rv-agent to be used as a testing tool alongside other tools (Monkey, DroidBot, etc.) through the rv-tools plugin system. The module handles configuration mapping from platform Task/ToolConfig to RVAgentConfig and passes static analysis data to the agent.

## Installation

```bash
# Install all rv-android modules (from project root)
poetry install
```

This module is part of the RV-Android Poetry workspace. All modules are installed in editable mode --- source changes are reflected immediately.

## Quick Start

### Via rv-experiment (recommended)

```bash
# Run with default multimode variant
poetry run rv-experiment run --tools rvagent --apks-dir ./apks_examples

# Run with a specific variant
poetry run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples

# Combine with other tools
poetry run rv-experiment run --tools monkey,rvagent:multimode,droidbot:dfs_greedy --apks-dir ./apks_examples
```

### Programmatic Usage

```python
from rv_tools import ToolFactory
from rv_android_core.domain.task import ToolConfig

# Get registry with rvagent registered
from rv_experiment.tools import ExperimentToolRegistry
registry = ExperimentToolRegistry.get_instance()

# Create tool configuration
tool_config = ToolConfig(
    tool_name="rvagent",
    variant="multimode",
    additional_params={"timeout": 900}
)

# Create and use tool instance
factory = ToolFactory()
tool = factory.create_tool(tool_config)

# Execute within platform context
# tool.execute(task, app)
```

## Features

- **Platform Integration**: Implements `AbstractTool` interface for use within rv-platform's task execution framework
- **Plugin Registration**: Automatically registered via the `rv_tools.plugins` entry point
- **Multiple Variants**: Supports different execution modes (multimode, pure_algorithm, llm_only, thorough)
- **Static Analysis Support**: Receives and forwards static analysis data from the platform to rv-agent
- **Configuration Mapping**: Maps platform Task/ToolConfig to RVAgentConfig, including LLM, strategy, and scorer parameters

## Variants

| Variant | Mode | Description |
|---------|------|-------------|
| `default` | multimode | 70% LLM, 30% algorithm decisions |
| `multimode` | multimode | Same as default |
| `pure_algorithm` | pure_algorithm | Algorithmic DFS exploration only (no LLM) |
| `llm_only` | llm_only | LLM-driven exploration only |
| `thorough` | multimode | 80% LLM, larger plateau window for deeper exploration |

Timeout is always controlled by the platform Task configuration, not by variants.

## Configuration

### Variant Parameters

Each variant sets a combination of these parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_mode` | str | Exploration mode: `multimode`, `pure_algorithm`, `llm_only` |
| `llm_probability` | float | Probability of using LLM for decisions (multimode only) |
| `strategy` | str | Exploration strategy name |
| `plateau_window` | int | Steps before declaring exploration plateau |

### Additional Parameters

These can be passed via `ToolConfig.additional_params` for fine-tuning:

| Category | Parameters |
|----------|-----------|
| LLM | `llm_model`, `llm_base_url`, `llm_temperature`, `llm_top_p`, `llm_top_k`, `llm_max_tokens`, `llm_timeout`, `prompt_version` |
| Strategy | `plateau_window`, `max_input_variations`, `stochastic_probability`, `stochastic_temperature` |
| Scorers | `mop_direct_score`, `mop_transitive_score`, `wtg_guided_score`, `unsaturated_bonus`, `visitation_penalty_factor`, `strength_weight`, and others |

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANDROID_HOME` | Android SDK path for emulator management | Yes |
| `RVSEC_HOME` | Path to RVSEC installation (enables instrumentation and static analysis) | No |
| `RVAGENT_MODE` | Override rv-agent execution mode | No |

## Execution Flow

```
rv-experiment / rv-platform
        |
        v
ToolFactory.create_tool(tool_config)
        |
        v
RVAgentTool.configure(variant_params)
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
RVAgent.run() -> results
```

## Dependencies

### Internal (rv-android)

| Module | Purpose |
|--------|---------|
| `rv-android-core` | Foundation infrastructure (AbstractTool, domain models, error handling) |
| `rv-agent` | LLM-driven testing agent (AgentFactory, RVAgent, RVAgentConfig) |
| `rv-tools` | Tool registry and plugin system |

### External

| Package | Purpose |
|---------|---------|
| `pydantic` | Configuration validation |

## Testing

```bash
# From project root
poetry run pytest modules/rvagent-tool/tests/ -v

# With coverage
poetry run pytest modules/rvagent-tool/tests/ --cov=modules/rvagent-tool/src --cov-report=html
```

## License

Part of the rv-android project.
