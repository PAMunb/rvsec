## MODIFIED Requirements

### Requirement: Tool Registration and Factory System (FR18, NFR02)

The tool system MUST provide a centralized registry and factory for all Android testing tools. `ToolRegistry` maintains a singleton registry of tool classes and their variant configurations. `ToolFactory` creates configured tool instances from `ToolConfig` objects.

The factory resolution flow in `ToolFactory.create_tool()` is:
1. Resolve `tool_class` from registry using `tool_config.name`.
2. Get `variant_config` from registry using `tool_config.name` and `tool_config.variant`.
3. Merge variant_config with `tool_config.parameters` (parameters override variant values).
4. Create `tool_class()` instance and call `tool.configure(merged_config)`.

#### Scenario: Factory creates configured tool from ToolConfig

- **WHEN** `ToolFactory.create_tool(tool_config)` is called with `tool_config.name="droidbot"`, `tool_config.variant="dfs_greedy"`, `tool_config.parameters={"count": 5000}`
- **THEN** the factory MUST return a `DroidBotTool` instance
- **AND** the instance MUST have `config["policy"] == "dfs_greedy"` (from variant)
- **AND** the instance MUST have `config["count"] == 5000` (from parameters override)
- **AND** the instance MUST have `config["ignore_ad"] == True` (from variant defaults)

#### Scenario: Factory rejects invalid tool or variant

- **WHEN** `ToolFactory.create_tool(tool_config)` is called with `tool_config.name="nonexistent_tool"`
- **THEN** the factory MUST raise `ConfigurationError` with a message indicating the tool is not found
- **AND** no tool instance MUST be created

- **WHEN** `ToolFactory.create_tool(tool_config)` is called with `tool_config.name="droidbot"`, `tool_config.variant="invalid_variant"`
- **THEN** the factory MUST raise `ConfigurationError` with a message indicating the variant is invalid

### Requirement: Per-Tool Variant System (FR20)

Each tool MUST support multiple named variants representing different operational modes and parameter sets. Variants provide a way to reference complete tool configurations by name in experiment specifications, CLI arguments, and configuration files. The variant system enables the tool specification DSL format: `tool_name:variant_name@param=value`.

Variants are defined by each tool's `get_variants()` classmethod, which returns a dictionary mapping variant names to configuration parameter dictionaries. Every tool MUST include a `"default"` variant. Variants are registered in the `ToolRegistry.variants` data structure as a three-level dictionary: `tool_name -> variant_name -> config_dict`.

The variant resolution flow in `ToolFactory.create_tool()` is:
1. If `variant_name` is provided and not `"default"`, validate it exists via `registry.validate_tool_variant()`.
2. Get the variant configuration via `registry.get_variant_config()` (returns a copy).
3. Merge with `tool_config.parameters` (parameters override variant values).
4. Call `tool.configure(merged_config)` on the new instance.

#### Scenario: Additional parameters override variant values

- **WHEN** `ToolFactory.create_tool()` is called with variant `"dfs_greedy"` (which has `count=10000000000`) and `parameters={"count": 500}`
- **THEN** the final configuration passed to `configure()` MUST have `count=500`
- **AND** all other variant parameters MUST be preserved (e.g., `policy="dfs_greedy"`, `interval=3`)

#### Scenario: Tool specification DSL parsing

- **WHEN** the CLI receives the tool specification string `"droidbot:dfs_greedy@count=5000"`
- **THEN** the parser MUST extract `name="droidbot"`, `variant="dfs_greedy"`, `parameters={"count": "5000"}`
- **AND** the resulting `ToolConfig` MUST be usable by `ToolFactory.create_tool()`

- **WHEN** the CLI receives `"monkey,droidbot:bfs_greedy,rvagent:pure_algorithm"`
- **THEN** the parser MUST produce 3 `ToolConfig` objects, one for each tool specification

## REMOVED Requirements

### Requirement: rvandroid special case in ToolFactory
**Reason**: The `rvandroid` tool was deleted (replaced by `rvagent`). The `if tool_name == "rvandroid"` special case in `ToolFactory.create_tool()` is dead code.
**Migration**: No migration needed. The code path was never executed because no tool named "rvandroid" exists in the registry.
