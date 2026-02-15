## Why

GitHub Issue: #15

The `rvagent` tool is registered only in `rv-experiment` via `ExperimentToolRegistry`. This means `rv-platform run --tools rvagent` does not work standalone — the tool is not in the registry when rv-platform runs without rv-experiment. Since rv-platform is the central execution engine for all tools (FR07-FR11), it should be the single registration point. This eliminates the `ExperimentToolRegistry` wrapper class, simplifies the dependency chain, and ensures rvagent is available in both standalone (`rv-platform`) and orchestrated (`rv-experiment`) usage.

## What Changes

- **Move rvagent registration from rv-experiment to rv-platform**: rv-platform's `__init__.py` registers `RVAgentTool` on import via a `_register_external_tools()` function, using `is_tool_registered()` guard for idempotency.
- **Add rvagent-tool dependency to rv-platform**: `pyproject.toml` gains `rvagent-tool` in dependencies and uv sources.
- **Remove rvagent-tool dependency from rv-experiment**: No longer needed — rv-experiment already depends on rv-platform, which now brings rvagent transitively.
- **Delete ExperimentToolRegistry**: The `tools/` package in rv-experiment (`experiment_tools.py`, `__init__.py`) is deleted entirely (backed up to `backup/`). The wrapper class added no value beyond calling `ToolRegistry.register_tool_class()`.
- **Simplify rv-experiment callers**: `__main__.py` and `config.py` switch from `ExperimentToolRegistry` to `ToolRegistry` directly.
- **Remove registration constants from rv-experiment**: `EXTERNAL_TOOL_RVAGENT`, `TOOL_REGISTRATION_SUCCESS`, `TOOL_REGISTRATION_FAILED`, `TOOL_REGISTRATION_IMPORT_ERROR` are deleted from `constants.py`.

## Capabilities

### New Capabilities

None — this change reorganizes existing behavior, it does not introduce new capabilities.

### Modified Capabilities

- `tools`: The external tool registration mechanism changes from rv-experiment `ExperimentToolRegistry` to rv-platform `_register_external_tools()`. INV-TOOL-12 (idempotent registration) is preserved but implemented differently. The registration flow narrative in the spec needs updating.
- `platform`: rv-platform gains the responsibility of registering external tools on import. Its dependency list grows to include rvagent-tool.
- `experiment`: rv-experiment no longer owns tool registration. The `tools/` package is removed. Callers use `ToolRegistry` from rv-tools directly.

## Impact

- **rv-platform**: `pyproject.toml` (new dep), `__init__.py` (new registration function), CLAUDE.md (doc update)
- **rv-experiment**: `pyproject.toml` (remove dep), `__main__.py` (switch to ToolRegistry), `config.py` (simplify validation), `constants.py` (remove 6 lines), `tools/` directory (delete), CLAUDE.md + README.md + architecture.md (doc updates)
- **rvagent-tool**: `tool.py` docstring (update registration reference), `README.md` (update example)
- **openspec/specs/tools/spec.md**: Delta spec needed for registration flow changes
- **Dependencies**: rv-platform now depends on rvagent-tool (workspace = true). rv-experiment loses direct rvagent-tool dependency (transitive via rv-platform).
