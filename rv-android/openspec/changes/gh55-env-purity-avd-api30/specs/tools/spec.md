## Purpose

The Tools domain (`rv-tools`) provides the registry, factory, and base-class infrastructure that all testing tool plugins (Monkey, DroidBot, APE, FastBot, ARES, DroidMate, Humanoid, QTesting, rvagent, aperv) inherit from. Tool plugins live at Layer 2 in the layered architecture (`docs/rv_android_architecture.md`). Per the Layer Purity rule formalized in this change, Layer 2 modules MUST NOT read environment variables directly: any value previously sourced from `os.environ` at L2 MUST be received via `PlatformConfig.tools[*].parameters` (the `tools: List[ToolConfig]` field on `PlatformConfig`, populated at L5 by `rv-experiment` and translated by `ConfigurationFactory` from `ExperimentConfig.tool_configs`).

The currently identified violation is `rv-tools/src/rv_tools/builtin/humanoid/tool.py:89`, which reads `RV_HUMANOID_URL` directly. This change migrates the resolution to L5 and routes the value through the existing `tool_configs` channel without introducing a new abstraction. The same audit MUST be applied to all other built-in tools — any environment-variable read found in `rv-tools/src/rv_tools/builtin/*/` MUST be migrated.

This is a contract-level change for the tool plugin ecosystem: external plugins (e.g., `aperv-tool`, `rvagent-tool`, future plugins) MUST also follow Layer Purity. The `AbstractTool.configure()` method becomes the canonical channel for receiving tool-specific configuration; no plugin may bypass it for environment-derived values.

## Data Contracts

### Input
- `config: Dict[str, Any]` (parameter to `AbstractTool.configure()`) — contains all tool-specific config values (URLs, credentials, paths, flags) resolved at L5

### Output
- Tool instance attributes (e.g., `self.url`, `self.timeout`) — populated from `config` keys

### Side-Effects
- None at the tool-base level; concrete tools may have their own side-effects (e.g., HTTP connections), but configuration acquisition is pure

### Error
- `KeyError` or `ValidationError` if a required config key is missing — raised by the concrete tool's `configure()` (callers in `rv-platform` know to surface these as task setup failures)

## Invariants

- **INV-TOOL-20**: No file under `modules/rv-tools/src/rv_tools/builtin/**/`, `modules/aperv-tool/src/**/`, or `modules/rvagent-tool/src/**/` (the three L2 plugin trees) MAY contain `os.environ.get`, `os.environ[`, `os.getenv`, `dict(os.environ)`, `os.environ.copy()`, or any direct `os.environ` access. Verified by lint: `grep -rnE 'os\.(environ|getenv)' modules/rv-tools/src/rv_tools/builtin/ modules/aperv-tool/src/ modules/rvagent-tool/src/` returns 0 hits. (Empirical baseline today: rv-tools/builtin/{ape,droidmate,fastbot}/tool.py and aperv-tool/tools/aperv/tool.py:329,352,355 violate this; the change migrates them.)
- **INV-TOOL-21**: All built-in tools MUST receive their configuration exclusively through `AbstractTool.configure(config)`. Tool source files MUST NOT import `rv_android_core.constants.ENV_*` symbols (the constants are L5/L1 territory).

## ADDED Requirements

### Requirement: Layer Purity for Tool Configuration (NFR01, NFR02)

Tool plugins (Layer 2) MUST receive all configuration values via the `AbstractTool.configure(config: Dict[str, Any])` contract established by `rv-android-core`. They MUST NOT read environment variables, configuration files, or any other external state during initialization or execution. The `config` dictionary is assembled at Layer 5 (by `rv-experiment`) and forwarded through the entries of `rv-platform.PlatformConfig.tools` (each a `ToolConfig` carrying a `parameters: Dict[str, Any]`) to `ToolFactory.create_tool` (in `rv_tools.registry.factory`, L2), which merges variant defaults with `tool_config.parameters` and calls `configure()`.

This rule has three concrete consequences:

1. **No `os.environ` reads in `rv-tools/src/rv_tools/builtin/`**. The `RV_HUMANOID_URL` read at `rv-tools/.../humanoid/tool.py:89` is the canonical example of a violation removed by this change. Any equivalent read in other tool plugins MUST also be removed.
2. **Tool configuration keys are documented**. Each tool's `configure()` MUST declare which keys it expects (via Pydantic model or explicit `config["..."]` access). The set of declared keys forms part of the tool's public contract.
3. **Tools cannot probe the environment as a fallback**. Even if `config` lacks a value, the tool MUST raise rather than silently fall back to `os.environ`. The L5 resolver is responsible for providing defaults.

#### Scenario: Humanoid tool uses variant default when L5 does not override

- **WHEN** `rv-experiment` does NOT set `RV_HUMANOID_URL` and does NOT pass `--humanoid-url`
- **AND** the factory builds `tool_config = ToolConfig(name="humanoid", variant="default", parameters={})`
- **AND** `ToolFactory.create_tool(tool_config)` merges `{**variant_defaults, **{}}` and calls `tool.configure({"policy": "dfs_greedy", "count": 10_000_000_000, "ignore_ad": True, "humanoid_url": "127.0.0.1:50405"})`
- **THEN** `self.url` MUST equal `"127.0.0.1:50405"` (the variant default carried in `get_variants()["default"]["humanoid_url"]`)
- **AND** the tool source file MUST contain no `os.environ` reads or `ENV_*` imports
- **AND** running `grep -rn 'ENV_HUMANOID_URL\|os\.environ' modules/rv-tools/src/rv_tools/builtin/humanoid/` MUST return 0 hits

#### Scenario: L5-resolved URL overrides variant default

- **WHEN** `rv-experiment` resolves `RV_HUMANOID_URL=http://humanoid:50405` from the environment (or from `--humanoid-url`)
- **AND** the factory builds `tool_config = ToolConfig(name="humanoid", variant="default", parameters={"humanoid_url": "http://humanoid:50405"})`
- **AND** `ToolFactory.create_tool(tool_config)` merges `{**variant_defaults, "humanoid_url": "http://humanoid:50405"}` (parameters wins because it merges last)
- **THEN** `self.url` MUST equal `"http://humanoid:50405"`
- **AND** at no point does the platform or the tool read `RV_HUMANOID_URL` directly from `os.environ`

#### Scenario: Tool fails fast for keys without variant default and without L5 injection

- **WHEN** a hypothetical tool plugin declares no variant default for required key `K` and L5 also injects no `K`
- **AND** `tool.configure(merged_dict)` accesses `merged_dict["K"]`
- **THEN** the tool MUST raise `KeyError` naming `K` (no `os.environ` fallback at L2)
- **AND** the fix is to add `K` to `get_variants()` defaults or have L5 inject it, never to read env at L2

#### Scenario: Lint enforces no env reads in tool plugins (all three plugin trees)

- **WHEN** a developer reintroduces `os.environ.get(ENV_X)`, `os.getenv(ENV_X)`, or `os.environ["RV_X"]` anywhere under `modules/rv-tools/src/rv_tools/builtin/`, `modules/aperv-tool/src/`, or `modules/rvagent-tool/src/`
- **THEN** the CI lint MUST fail naming the offending file, line, and plugin tree
- **AND** the message MUST cite `INV-TOOL-20` and `docs/rv_android_architecture.md` (Layer Purity rule)
- **AND** the lint MUST equally flag `dict(os.environ)` and `os.environ.copy()` in the same scope (environment leak via shallow copy)
