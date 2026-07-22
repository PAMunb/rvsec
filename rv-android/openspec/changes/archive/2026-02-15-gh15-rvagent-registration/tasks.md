## 1. rv-platform: Add rvagent Registration

- [x] 1.1 Add `rvagent-tool` to `modules/rv-platform/pyproject.toml` dependencies and `[tool.uv.sources]`
- [x] 1.2 Create `_register_external_tools()` in `modules/rv-platform/src/rv_platform/__init__.py` that imports `RVAgentTool` with try/except and registers it via `ToolRegistry.register_tool_class()`, guarded by `is_tool_registered("rvagent")`

## 2. rv-experiment: Remove ExperimentToolRegistry

- [x] 2.1 Backup `modules/rv-experiment/src/rv_experiment/tools/experiment_tools.py` and `__init__.py` to `backup/experiment_tools/`
- [x] 2.2 Delete `modules/rv-experiment/src/rv_experiment/tools/` directory entirely
- [x] 2.3 Remove `rvagent-tool` from `modules/rv-experiment/pyproject.toml` dependencies and `[tool.uv.sources]`
- [x] 2.4 Remove constants `EXTERNAL_TOOL_RVAGENT`, `TOOL_REGISTRATION_SUCCESS`, `TOOL_REGISTRATION_FAILED`, `TOOL_REGISTRATION_IMPORT_ERROR` from `modules/rv-experiment/src/rv_experiment/constants.py` (lines 63-69)

## 3. rv-experiment: Update Callers

- [x] 3.1 In `modules/rv-experiment/src/rv_experiment/__main__.py`: replace `from rv_experiment.tools.experiment_tools import ExperimentToolRegistry` with `from rv_tools import ToolRegistry`
- [x] 3.2 In `CLIContext.__init__()`: replace `self.tool_registry = ExperimentToolRegistry.get_instance()` with `self.tool_registry = ToolRegistry.get_instance()`
- [x] 3.3 Delete method `CLIContext._register_available_tools()` entirely
- [x] 3.4 In `modules/rv-experiment/src/rv_experiment/config.py` `_validate_tool_variants()`: replace the `ExperimentToolRegistry` try/except block with `tool_registry = ToolRegistry.get_instance()` (import already exists at line 261)

## 4. Dependency Resolution

- [x] 4.1 Run `uv sync` from project root — must resolve without errors

## 5. Documentation Updates

- [x] 5.1 Update `modules/rvagent-tool/src/rvagent_tool/tools/rvagent/tool.py` line 41: change "Registered via rv-experiment ExperimentToolRegistry" to "Registered via rv-platform on import"
- [x] 5.2 Update `modules/rvagent-tool/README.md`: replace `ExperimentToolRegistry` example with `ToolRegistry` via rv-platform import
- [x] 5.3 Update `modules/rv-experiment/CLAUDE.md`: remove `tools/` from directory tree, update "External Tool Registration" section, remove "Tool Registration" from key responsibilities, update "Adding a New Tool" instructions
- [x] 5.4 Update `modules/rv-experiment/README.md`: remove `tools/` from directory tree
- [x] 5.5 Update `modules/rv-experiment/docs/architecture.md`: remove `tools/` from directory tree, remove Tools subgraph from mermaid, update Extension Points
- [x] 5.6 Update `modules/rv-platform/CLAUDE.md`: annotate `__init__.py` in directory tree, add `rvagent-tool` to dependencies section

## 6. Verification

- [x] 6.1 `uv run rv-platform list-tools` — output MUST include `rvagent` with 5 variants
- [x] 6.2 `uv run rv-experiment list-tools` — output MUST include `rvagent`
- [x] 6.3 `uv run pytest modules/rv-platform/tests/ -v` — all tests MUST pass (59 tests)
- [x] 6.4 `uv run pytest modules/rv-experiment/tests/ -v` — all tests MUST pass (11 tests)
- [x] 6.5 `uv run pytest modules/rv-tools/tests/ -v` — all tests MUST pass (3 tests)
- [x] 6.6 Idempotency check: `import rv_platform` twice, assert rvagent count == 1 in registry
- [x] 6.7 Config validation: `ExperimentConfig` with `ToolConfig(name='rvagent', variants=['pure_algorithm'])` MUST pass `_validate_tool_variants()`
- [x] 6.8 `grep -r "ExperimentToolRegistry\|experiment_tools\|_register_rvagent\|_register_available_tools\|EXTERNAL_TOOL_RVAGENT\|TOOL_REGISTRATION_SUCCESS\|TOOL_REGISTRATION_FAILED\|TOOL_REGISTRATION_IMPORT_ERROR" modules/ --include="*.py"` — MUST return zero hits
- [x] 6.9 `grep -r "ExperimentToolRegistry" modules/ --include="*.md"` — MUST return zero hits in CLAUDE.md, README.md, architecture.md files (openspec specs excluded — handled by `/opsx:sync`)
