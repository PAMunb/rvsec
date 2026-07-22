## MODIFIED Requirements

### Requirement: Plugin System with Registry and Factory Patterns (FR18, NFR02)

The tool infrastructure MUST provide a centralized registry and factory system that enables dynamic tool registration, discovery, and instantiation. The registry follows a singleton pattern to ensure a single source of truth. Tools self-register at module import time, making them immediately available for experiment configuration and execution.

The registration flow has two phases: (1) built-in tools are registered automatically when the `rv_tools` package is imported -- `_register_builtin_tools()` iterates over the `BUILTIN_TOOLS` list and calls `registry.register_tool_class()` for each; (2) external tools (rvagent) are registered by `_register_external_tools()` in rv-platform's `__init__.py` when that module is imported. The function checks `is_tool_registered("rvagent")` before attempting registration to ensure idempotency.

`register_tool_class()` performs complete registration in a single call: it invokes `get_tool_spec()` to obtain the `ToolSpec`, registers the class and spec, then calls `get_variants()` and registers each variant individually. This means a tool author only needs to implement `get_tool_spec()` and `get_variants()` for their tool to be fully registered.

The `ToolFactory` creates configured instances by: (1) resolving the tool class from the registry, (2) getting variant configuration, (3) merging with additional parameters from the experiment config (overrides take precedence), and (4) calling `tool.configure()` on the instance. For standard tools, configuration is a flat dictionary.

#### Scenario: Built-in tools are registered at import time

- **WHEN** a Python module executes `import rv_tools`
- **THEN** the `ToolRegistry` singleton MUST contain all 8 built-in tools: monkey, droidbot, ape, fastbot, ares, droidmate, humanoid, qtesting
- **AND** each tool MUST have at least a `"default"` variant registered
- **AND** `registry.get_tool_names()` MUST return a list of length >= 8

#### Scenario: External tool registration via rv-platform import

- **WHEN** a Python module executes `import rv_platform`
- **THEN** `_register_external_tools()` in `rv_platform/__init__.py` MUST be called automatically
- **AND** if the `rvagent_tool` package is importable, the `"rvagent"` tool MUST be registered with variants `default`, `multimode`, `pure_algorithm`, `llm_only`, `thorough`
- **AND** if the `rvagent_tool` package is not importable, the failure MUST be logged as a warning
- **AND** if `is_tool_registered("rvagent")` returns `True`, the registration MUST be skipped (idempotency)

#### Scenario: Factory creates configured tool from ToolConfig

- **WHEN** `ToolFactory.create_tool(tool_config)` is called with `tool_config.tool_name="droidbot"`, `tool_config.variant="dfs_greedy"`, `tool_config.additional_params={"count": 5000}`
- **THEN** the factory MUST return a `DroidBotTool` instance
- **AND** the instance MUST have `config["policy"] == "dfs_greedy"` (from variant)
- **AND** the instance MUST have `config["count"] == 5000` (from additional_params override)
- **AND** the instance MUST have `config["ignore_ad"] == True` (from variant defaults)

#### Scenario: Factory rejects invalid tool or variant

- **WHEN** `ToolFactory.create_tool(tool_config)` is called with an unregistered tool name
- **THEN** the factory MUST raise `ToolNotFoundError`
- **AND** `ToolFactory.create_tool(tool_config)` called with an invalid variant MUST raise `ConfigurationError`

## MODIFIED Invariants

- **INV-TOOL-12**: External tool registration in rv-platform MUST be idempotent. The `_register_external_tools()` function MUST check `is_tool_registered("rvagent")` before calling `register_tool_class()`. Multiple imports of `rv_platform` MUST NOT produce duplicate registrations.

## REMOVED Requirements

### Requirement: ExperimentToolRegistry

**Reason**: The `ExperimentToolRegistry` class in `rv-experiment/tools/experiment_tools.py` was a wrapper around `ToolRegistry` that added no value beyond calling `register_tool_class()` for rvagent. External tool registration is now handled directly by rv-platform on import. The class, its `__init__.py`, and related constants (`EXTERNAL_TOOL_RVAGENT`, `TOOL_REGISTRATION_SUCCESS`, `TOOL_REGISTRATION_FAILED`, `TOOL_REGISTRATION_IMPORT_ERROR`) are deleted entirely (P3).

**Migration**: rv-experiment callers (`__main__.py`, `config.py`) use `ToolRegistry.get_instance()` from rv-tools directly. rv-experiment's dependency on `rvagent-tool` is removed — it comes transitively through rv-platform.
