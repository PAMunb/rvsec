# Design: Move rvagent Registration to rv-platform

## Context

GitHub Issue: #15. This change moves the rvagent tool registration from rv-experiment (`ExperimentToolRegistry`) to rv-platform (`_register_external_tools()`). The motivation is that rv-platform is the central execution engine (FR07-FR11) and should be the single registration point for all tools, enabling `rv-platform run --tools rvagent` to work standalone without rv-experiment.

Constraints: INV-TOOL-12 requires idempotent registration. P3 requires complete deletion of `ExperimentToolRegistry` with no backward-compatibility shims.

## Architecture

```
import rv_tools        →  ToolRegistry singleton created
                           8 builtin tools registered (_register_builtin_tools)

import rv_platform     →  _register_external_tools() called
                           rvagent registered via ToolRegistry.register_tool_class()
                           (guarded by is_tool_registered check)

import rv_experiment   →  imports rv_platform (triggers above)
                           CLIContext uses ToolRegistry.get_instance() directly
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `rv_platform.__init__._register_external_tools()` | Register rvagent on import | None | rvagent in ToolRegistry |
| `rv_tools.ToolRegistry` | Singleton tool storage | Tool classes | Registered tools |
| `rv_experiment.__main__.CLIContext` | CLI context with tool access | None | ToolRegistry instance |
| `rv_experiment.config._validate_tool_variants()` | Validate tool/variant combos | tool_configs | ConfigurationError or None |

## Mapping: Spec → Implementation

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-TOOL-12 (idempotent registration) | `is_tool_registered("rvagent")` guard in `_register_external_tools()` | Idempotency check: double import rv_platform, assert count==1 |
| FR18 (plugin system) | `_register_external_tools()` in `rv_platform/__init__.py` | `rv-platform list-tools` shows rvagent |
| ExperimentToolRegistry REMOVED | `tools/` dir deleted, constants removed | `grep -r ExperimentToolRegistry modules/ --include="*.py"` → 0 hits |

## Data Flow

```
Module import → rv_platform.__init__.py
    → _register_external_tools()
        → ToolRegistry.is_tool_registered("rvagent") → False?
            → import RVAgentTool from rvagent_tool
            → ToolRegistry.register_tool_class(RVAgentTool)
        → True? → skip (idempotent)
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `ImportError` | rvagent_tool not installed | Log warning, skip registration | rvagent unavailable but system functional |
| `Exception` | Registration failure | Log error, skip registration | Same as above |

## Decisions

**D1: Register in `__init__.py` vs dedicated module**

Register directly in `rv_platform/__init__.py` rather than creating a separate `registration.py` module. The function is 10 lines of code — a separate file would be over-engineering (P1).

Alternative considered: `rv_platform/tools/registration.py` — rejected because it recreates the same unnecessary indirection that `ExperimentToolRegistry` had.

**D2: Guard mechanism for idempotency**

Use `ToolRegistry.is_tool_registered("rvagent")` check instead of a module-level `_registered` flag. The registry itself is the source of truth — no need for a parallel tracking mechanism.

Alternative considered: Module-level `_external_tools_registered` boolean (same as `ExperimentToolRegistry` had) — rejected because the registry already provides `is_tool_registered()`.

**D3: Dependency direction**

rv-platform depends on rvagent-tool (not the reverse). rv-experiment loses its direct rvagent-tool dependency — it comes transitively through rv-platform.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| rv-platform import becomes slower due to rvagent_tool import chain | Acceptable — rvagent_tool is lightweight (no heavy deps at import time). The try/except ensures failure is graceful. |
| Circular dependency if rvagent-tool imports rv-platform | Not possible — rvagent-tool depends on rv-android-core and rv-agent, not rv-platform. Dependency is unidirectional. |

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | rv-platform tests pass | `uv run pytest modules/rv-platform/tests/ -v` | 59 existing |
| Unit | rv-experiment tests pass | `uv run pytest modules/rv-experiment/tests/ -v` | 11 existing |
| Integration | `rv-platform list-tools` shows rvagent | CLI execution | 1 manual |
| Integration | `rv-experiment list-tools` shows rvagent | CLI execution | 1 manual |
| Integration | Idempotency: double import, count==1 | Python script | 1 manual |
| Integration | Config validation works with rvagent | Python script | 1 manual |
| Cleanup | Zero dangling references | `grep -r "ExperimentToolRegistry" modules/ --include="*.py"` | 1 check |
