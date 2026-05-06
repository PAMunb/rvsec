## Purpose

The Platform domain (`rv-platform`) is the central execution engine sitting at Layer 4. It receives a `PlatformConfig` from Layer 5 (`rv-experiment`) and translates it into task generation, emulator management, component-based execution, and result consolidation. This change formalizes `ToolConfig.parameters` (already present on the existing `ToolConfig` Pydantic model in `rv-android-core/domain/task.py`) as the canonical channel for forwarding tool-specific configuration values from L5 to L2 — values that previously some tool plugins read directly from environment variables in violation of the Layer Purity rule.

`PlatformConfig` carries `tools: List[ToolConfig]` (the existing required field at `modules/rv-platform/src/rv_platform/config/platform_config.py:50`); each `ToolConfig` already has a `parameters: Dict[str, Any]` field that holds per-tool config (URLs, credentials, timeouts, custom paths). The `ToolFactory` (`rv_tools.registry.factory.ToolFactory.create_tool`, L2) MUST read `tool_config.parameters` and pass it to `AbstractTool.configure()`. Combined with INV-TOOL-20 (no env reads at L2), this gives a single inspectable path for every tool config value: env var (or CLI flag) → `ExperimentConfig` (L5, Pydantic) → `ToolConfig.parameters` (entries of `PlatformConfig.tools`) → `AbstractTool.configure()` (L2). No surprises, no parallel paths.

(Note: the L5 input field is `ExperimentConfig.tool_configs`; `ConfigurationFactory` translates that into `PlatformConfig.tools` when assembling the platform config. Both refer to a `List[ToolConfig]`; this change does not rename either field.)

This change does not introduce a new field; it formalizes `ToolConfig.parameters` as the only sanctioned channel and removes the historical fallback paths that bypassed it.

## Data Contracts

### Input
- `PlatformConfig.tools: List[ToolConfig]` (required field at `modules/rv-platform/src/rv_platform/config/platform_config.py:50`) — each entry holds `name`, `variant`, and `parameters: Dict[str, Any]`. The L5 counterpart is `ExperimentConfig.tool_configs` (also `List[ToolConfig]`); both names refer to the same shape.

### Output
- Pass-through of `tool_config.parameters` to `AbstractTool.configure()` via `ToolFactory`

### Side-Effects
- None at the platform level; concrete tools may produce side-effects from the config they receive

### Error
- `ValidationError` raised by Pydantic on `PlatformConfig` instantiation if `tools` is malformed (e.g., wrong type or items not matching `ToolConfig` schema)

## Invariants

- **INV-TOOL-25** (cross-references the tools domain because `ToolFactory` lives at L2 in `rv_tools.registry.factory`; declared here too because the contract is normative for `rv-platform` consumers): the `ToolFactory.create_tool(tool_config)` call MUST forward `tool_config.parameters` (the existing `Dict[str, Any]` field on `ToolConfig`) to `AbstractTool.configure()` when instantiating a tool. There is no other path by which tool-specific configuration values reach a tool plugin. The test that verifies this lives in `modules/rv-tools/tests/registry/`.

## ADDED Requirements

### Requirement: Tool-Configuration Channel via ToolConfig.parameters (NFR01, NFR02)

`PlatformConfig.tools` is a `List[ToolConfig]` (required field at `modules/rv-platform/src/rv_platform/config/platform_config.py:50`), where each `ToolConfig` (defined in `rv_android_core.domain.task.ToolConfig`) carries `name: str`, `variant: str`, and `parameters: Dict[str, Any]`. The `ToolFactory` (in `rv_tools.registry.factory`, L2; the rv-platform module imports it via `from rv_tools import ToolFactory`) MUST consult the matching `ToolConfig.parameters` when instantiating a tool plugin: it merges variant defaults from the registry with the entry's `parameters` dictionary and forwards the result as the `config` argument of `AbstractTool.configure()`. The `parameters` dictionary defaults to `{}` (empty) — the concrete tool decides whether to raise on missing required keys (per INV-TOOL-21).

The dictionary contents are decided at Layer 5 (`rv-experiment`): values may originate from environment variables (resolved via the `ENV_*` registry), CLI flags, or hard-coded defaults. The Platform layer treats `parameters` as opaque pass-through data — it does not interpret keys or apply per-tool logic.

This is the sole sanctioned channel for delivering per-tool configuration values that come from outside the Tools domain. Tool plugins MUST NOT read environment variables (INV-TOOL-20), configuration files, or any other external state during their lifecycle.

#### Scenario: Humanoid URL flows from CLI through ToolConfig.parameters to HumanoidTool

- **WHEN** `rv-experiment` resolves `RV_HUMANOID_URL=http://humanoid:50405` from the environment
- **AND** instantiates `PlatformConfig` with `tools=[ToolConfig(name="humanoid", variant="default", parameters={"humanoid_url": "http://humanoid:50405"})]`
- **AND** the platform schedules a task using the `humanoid` tool
- **THEN** the `ToolFactory.create_tool` MUST instantiate `HumanoidTool` and call `tool.configure({"humanoid_url": "http://humanoid:50405", ...variant_defaults})`
- **AND** at no point does the platform or the tool read `RV_HUMANOID_URL` from `os.environ`

#### Scenario: ToolConfig with empty parameters defaults gracefully

- **WHEN** `PlatformConfig.tools` contains `ToolConfig(name="monkey", variant="default", parameters={})`
- **AND** the platform schedules a task using the `monkey` tool
- **THEN** the `ToolFactory.create_tool` MUST instantiate `MonkeyTool` and call `tool.configure({...variant_defaults})` (empty `parameters` merged with variant defaults)
- **AND** the tool SHALL succeed if it has no required config keys, or raise per INV-TOOL-21 if it does

#### Scenario: PlatformConfig rejects malformed tools field

- **WHEN** code instantiates `PlatformConfig(tools="not a list", ...)`
- **THEN** Pydantic MUST raise `ValidationError` naming `tools` and the expected type (`List[ToolConfig]`)

#### Scenario: ToolFactory does not bypass parameters dict

- **WHEN** `ToolFactory.create_tool(tool_config)` (in `rv_tools.registry.factory`) is invoked
- **THEN** the only L2 input that influences `AbstractTool.configure()` MUST be the merge of variant defaults and `tool_config.parameters`
- **AND** the factory MUST NOT read any environment variable, configuration file, or other source to populate the `config` argument
