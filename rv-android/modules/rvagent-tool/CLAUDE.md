# rvagent-tool - CLAUDE.md

## Overview

rv-platform plugin that wraps rv-agent as an `AbstractTool`. Maps platform `Task`/`App` context to `RVAgentConfig` and delegates to `AgentFactory` for LLM-driven Android UI exploration. Registered via the `rv_tools.plugins` entry point so rv-platform discovers it at import time.

## Quick Start

```bash
# Install (from project root)
uv sync

# Run tests (from project root)
uv run pytest modules/rvagent-tool/tests/ -v

# Use via rv-experiment
uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --timeout 60
```

## Architecture

### Directory Structure

```
src/rvagent_tool/
    tools/
        rvagent/
            __init__.py
            tool.py       # RVAgentTool (AbstractTool implementation)
            config.py     # Configuration mapping: Task/App -> RVAgentConfig
```

### Key Components

| Component | Purpose |
|-----------|---------|
| `tools/rvagent/tool.py` | `RVAgentTool` class implementing `AbstractTool` for rv-platform registration |
| `tools/rvagent/config.py` | `build_agent_config_dict()` maps Task/App/variant config to RVAgentConfig params; `get_static_data()` extracts static analysis data from Task |

### Dependencies

- **Internal**: `rv-android-core` (AbstractTool, ToolSpec, ErrorHandler, domain models), `rv-agent` (AgentFactory, RVAgentConfig), `rv-tools` (plugin entry point)
- **External**: `pydantic>=2.9.0`

## Development

### Testing

| Category | Path | Purpose |
|----------|------|---------|
| unit | `tests/unit/test_tool.py` | Tool spec, variants, configure, config mapping, tool info |

### Variants

Five named variants, all using `strategy: rvagent`:

| Variant | Mode | LLM Probability | Notes |
|---------|------|-----------------|-------|
| `default` | multimode | 0.7 | Same as multimode |
| `multimode` | multimode | 0.7 | 70% LLM / 30% algorithm |
| `pure_algorithm` | pure_algorithm | - | DFS-only, no LLM |
| `llm_only` | llm_only | - | LLM decisions only |
| `thorough` | multimode | 0.8 | Higher LLM ratio, plateau_window=15 |

### Configuration Flow

1. rv-platform calls `configure(variant_config)` with resolved variant parameters
2. rv-platform calls `execute_tool_specific_logic(task, app)`
3. `build_agent_config_dict()` merges task config (device_id, timeout, repetition), app metadata (package_name), and variant config (agent_mode, llm_probability, strategy params, scorer weights)
4. `AgentFactory.create_agent()` creates the agent with optional static analysis data
5. `agent.run()` executes exploration

### Key Design Decisions

- **Lazy imports**: rv-agent modules imported inside `execute_tool_specific_logic()` to avoid circular dependencies at registration time
- **Timeout from Task only**: timeout always comes from `Task.config`, never from variant configuration -- the platform controls execution timeout uniformly
- **Static data passthrough**: static analysis data is injected from the platform's `StaticAnalysisComponent` via `task.static_data`, not loaded independently
- **Extensive parameter mapping**: `config.py` maps 40+ parameters across categories (LLM, strategy, scorer weights, error detection, fallback)

## Key Files

| File | Purpose |
|------|---------|
| `src/rvagent_tool/tools/rvagent/tool.py` | Main tool class with variants, configure, and execution |
| `src/rvagent_tool/tools/rvagent/config.py` | Configuration mapping from platform context to RVAgentConfig |
| `tests/unit/test_tool.py` | Unit tests covering spec, variants, configure, config mapping |
| `pyproject.toml` | Package metadata and workspace dependency declarations |

## Gotchas

- The entry point `rvagent = "rvagent_tool.tools.rvagent.tool:RVAgentTool"` in `pyproject.toml` is what makes rv-platform discover this tool. If the entry point name changes, experiment YAML tool references break.
- `process_pattern` is empty because rv-agent uses UIAutomator2 which manages its own cleanup (no persistent processes to kill on the device).
- Timeout in variant config is silently ignored -- only `task.config.timeout` is used. This is intentional but can be confusing when debugging.
