# rvagent-tool - CLAUDE.md

## Overview

rv-platform plugin that wraps rv-agent as an `AbstractTool`. Maps platform `Task`/`App` context to `RVAgentConfig` and delegates to `AgentFactory` for LLM-driven Android UI exploration. Registered explicitly by `rv_platform/__init__.py` (`_register_external_tools()`), which imports `RVAgentTool` and calls `ToolRegistry.register_tool_class()` when `rv_platform` is imported; an `ImportError` is logged as a warning and the tool is simply unavailable.

## Quick Start

```bash
# Install (from project root)
uv sync

# Run tests (from project root)
uv run pytest modules/rvagent-tool/tests/ --import-mode=importlib -o "addopts=" -v

# Use via rv-experiment
uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --timeouts 60
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
| `tools/rvagent/config.py` | `RV_STEERING_OFF` (pinned copy of the agent kill-switch registry), `RV_TUNING_PARAMS`, `build_agent_config_dict()` (Task/App/variant config → RVAgentConfig params), `get_static_data()` (reads `task.static_data`) |

### Dependencies

- **Internal**: `rv-android-core` (AbstractTool, ToolSpec, ErrorHandler, domain models), `rv-agent` (`AgentFactory`, `RVAgentConfig`, `validate_static_data`, and — in tests — `RV_STEERING_FLAGS`), `rv-tools` (registry the tool is registered into)
- **Dependents**: `rv-platform` registers it on import
- **External**: `pydantic>=2.9.0`

## Development

### Testing

| Category | Path | Purpose |
|----------|------|---------|
| unit | `tests/unit/test_tool.py` | Tool spec, variants, configure, config mapping, tool info |
| guard | `tests/unit/test_gh77_variants.py` | Arm policy INV-RVA-01..06: `RV_STEERING_OFF` equals the agent's `RV_STEERING_FLAGS`, every variant sets every arm-defining key, every such key is mapped, pure arm forces steering off, static-data fail-fast, teardown |

### Variants

Six named variants, all using `strategy: rvagent`. A variant is a frozen experimental arm and must not inherit defaults (INV-RVA-01): each spreads `RV_STEERING_OFF` (every arm-defining key at its off/0 value) and then sets only what defines it.

| Variant | Mode | LLM Probability | Notes |
|---------|------|-----------------|-------|
| `default` | multimode | 0.7 | Same as multimode |
| `multimode` | multimode | 0.7 | 70% LLM / 30% algorithm; all steering off |
| `pure_algorithm` | pure_algorithm | - | `pure_mode=True`: the kill-switch that forces every steering flag off at assembly time (INV-RVA-03) |
| `mop_frontier` | pure_algorithm | - | Steering arm: `mop_frontier_weight=200` over `wtg_guided_score=150`, no LLM |
| `llm_only` | llm_only | - | LLM decisions only; all steering off |
| `thorough` | multimode | 0.8 | Higher LLM ratio, `plateau_window=15` |

LLM-family arms keep every steering flag off (INV-RVA-04), so LLM latency never contaminates a steering measurement.

### Configuration Flow

1. rv-platform calls `configure(variant_config)` with resolved variant parameters
2. rv-platform calls `execute_tool_specific_logic(task, app)`
3. `build_agent_config_dict()` merges task config (device_id, timeout, repetition), app metadata (package_name), and variant config (agent_mode, llm_probability, strategy params, scorer weights)
4. `RVAgentConfig(**config_dict).validate()`; an invalid config raises `ValueError`
5. `validate_static_data(task.static_data)` fails fast on present-but-invalid static data before any device time; absent static data passes (WTG guidance disabled)
6. `AgentFactory.create_agent()` creates the agent; `agent.run()` explores
7. `_teardown_agent()` always runs in `finally` (INV-RVA-05): stops the app on the device, never raises

### Key Design Decisions

- **Lazy imports**: rv-agent modules imported inside `execute_tool_specific_logic()` to avoid circular dependencies at registration time
- **Timeout from Task only**: timeout always comes from `Task.config`, never from variant configuration -- the platform controls execution timeout uniformly
- **Static data passthrough**: static analysis data is injected from the platform's `StaticAnalysisComponent` via `task.static_data`, not loaded independently
- **Extensive parameter mapping**: `config.py` passes through about 60 keys (LLM, strategy, scorer weights, error detection, fallback, steering flags, tuning knobs); every arm-defining key in `RV_STEERING_OFF` must be mapped (INV-RVA-02). `task.results_dir` becomes `metrics_output_dir`

## Key Files

| File | Purpose |
|------|---------|
| `src/rvagent_tool/tools/rvagent/tool.py` | Main tool class with variants, configure, and execution |
| `src/rvagent_tool/tools/rvagent/config.py` | Configuration mapping from platform context to RVAgentConfig |
| `tests/unit/test_tool.py` | Unit tests covering spec, variants, configure, config mapping |
| `tests/unit/test_gh77_variants.py` | Arm-policy guard tests (INV-RVA-01..06) |
| `pyproject.toml` | Package metadata and workspace dependency declarations |

## Gotchas

- The tool name `rvagent` (`RVAGENT_TOOL_NAME`) and the variant names are what experiment YAML and `--tools rvagent:<variant>` reference; renaming either breaks those references and the resume identity.
- `RV_STEERING_OFF` is a literal copy of `RV_STEERING_FLAGS` (`rv_agent/strategies/rvagent_strategy/ranking/pipeline.py`) so registration stays free of the `rv_agent` import. Adding a steering flag on the agent side means adding it here too; the guard test fails until both match.
- The INV-RVA-* identifiers are cited only in this module's code and tests; no spec under `openspec/specs/` defines them.
- `process_pattern` is empty because rv-agent uses UIAutomator2 which manages its own cleanup (no persistent processes to kill on the device).
- Timeout in variant config is silently ignored -- only `task.config.timeout` is used. This is intentional but can be confusing when debugging.
