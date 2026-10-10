## Purpose

`aperv-tool` is registered by rv-platform's `_register_external_tools()` in `rv_platform/__init__.py`, the same way as `rvagent-tool`. Until this delta, rv-platform imported `aperv_tool` without declaring it. The spec therefore described the module as an optional workspace member whose absence rv-platform tolerates. Meanwhile `aperv-tool` declared `rv-tools`, which none of its code imports: `ApeRVTool` subclasses `AbstractTool` and uses `ToolSpec` from `rv-android-core` (`rv_android_core.tools.abstract_tool`).

This delta aligns the declared graph with the imports. rv-platform declares `aperv-tool`, and `aperv-tool` declares `rv-android-core` as its only workspace dependency. Runtime behaviour does not change. The root `uv sync` installs every workspace member before and after, and the guarded import in `_register_external_tools()` is kept exactly as it is. What the guard now covers is a module that is present but fails to import, not an install that left the module out.

The lazy import of `rv_coverage.parser.log.diagnostic_parser` in `aperv_tool/analysis/step_bundle.py` stays undeclared on purpose. The diagnostic stream is opt-in on the capture side (`RV_LOGCAT_DIAGNOSTICS`), and a missing parser degrades to "not read" instead of breaking every bundle.

The narrative parts of `openspec/specs/aperv/spec.md` that repeat the old graph are corrected by hand when this change is archived. In the Purpose section, the paragraph that calls the module "an optional uv workspace member" and says a missing install only logs a warning. In "Relationship with Other Domains", the `rv-tools` entry, which says rv-tools provides `AbstractTool`, `ToolSpec`, `ToolRegistry` and `ToolFactory` to this module. The module receives `ToolRegistry`/`ToolFactory` behaviour through rv-platform and imports nothing from rv-tools.

## MODIFIED Requirements

### Requirement: ApeRVTool Registration (FR18, FR19)

`ApeRVTool` SHALL be registered as an external tool via rv-platform's `_register_external_tools()` function in `rv_platform/__init__.py`. `modules/rv-platform/pyproject.toml` SHALL declare `aperv-tool` in `dependencies` and as a workspace source in `[tool.uv.sources]`, as it declares `rvagent-tool` (`tools` INV-TOOL-26). Registration SHALL be idempotent: the function MUST check `registry.is_tool_registered("aperv")` before calling `registry.register_tool_class(ApeRVTool)`. If importing `aperv_tool.tools.aperv.tool` raises `ImportError`, the error SHALL be caught and logged as a warning, and the platform SHALL continue operating normally. An unexpected exception during registration SHALL be logged as an error and SHALL NOT propagate.

With the dependency declared, an `ImportError` no longer means the module was left out of the install. It means the module is present and its import failed, for example because one of its own imports broke. The guard keeps rv-platform importable in that case. The `aperv` arm is then absent from the registry. `rv-experiment` rejects it in `ExperimentConfig.validate()` before pre-processing, with `ConfigurationError("Tool 'aperv' not found in registry...")`. `rv-platform run` fails each `aperv` task in `ToolFactory.create_tool`.

#### Scenario: ApeRVTool registers on rv-platform import
- **WHEN** `import rv_platform` is executed in the workspace `.venv`
- **THEN** `ToolRegistry.get_instance().is_tool_registered("aperv")` SHALL return True
- **AND** `ToolRegistry.get_instance().get_tool_spec("aperv").name` SHALL be `"aperv"`

#### Scenario: Missing aperv-tool does not break rv-platform
- **WHEN** `import rv_platform` is executed and importing `aperv_tool.tools.aperv.tool` raises `ImportError` (the module is declared, so this is a broken import rather than a missing install)
- **THEN** rv-platform SHALL import successfully
- **AND** a warning log line SHALL be written containing `"aperv tool not available"`
- **AND** `ToolRegistry.get_instance().is_tool_registered("aperv")` SHALL return False

#### Scenario: Re-importing rv-platform does not double-register
- **WHEN** `import rv_platform` is executed twice
- **THEN** `ToolRegistry.get_instance()` SHALL contain exactly one registration for `"aperv"`

#### Scenario: rv-platform declares aperv-tool
- **WHEN** `.claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py` is run from the rv-android root
- **THEN** the `rv-platform` entry SHALL list `aperv-tool` under `declared`
- **AND** its `undeclared` line SHALL be `-`

---

### Requirement: uv Workspace Declaration

`aperv-tool/pyproject.toml` SHALL declare the package as a uv workspace member compatible with rv-android's `members = ["modules/*"]` discovery. Its only workspace dependency SHALL be `rv-android-core`, declared as a workspace source. That is where `AbstractTool`, `ToolSpec`, `Command`, `JarResolver`, the domain models and `util.analysis_document` come from. The module SHALL NOT declare `rv-tools`, which its code does not import. The undeclared lazy import of `rv_coverage` in `analysis/step_bundle.py` is deliberate and is not declared (see Purpose).

The `[project.entry-points."rv_tools.plugins"]` table SHALL NOT be used for `aperv-tool` -- registration is done explicitly in `rv-platform/__init__.py`, not via entry-point auto-discovery.

#### Scenario: Module added to workspace
- **WHEN** `aperv-tool/` exists under `modules/` in the rv-android root
- **THEN** `uv sync` SHALL include `aperv-tool` in the workspace without any change to the root `pyproject.toml`

#### Scenario: Declared and imported workspace dependencies agree
- **WHEN** `.claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py` is run from the rv-android root
- **THEN** the `aperv-tool` entry SHALL show `declared: rv-android-core`
- **AND** its `unused` line SHALL be `-`
- **AND** its `undeclared` line SHALL list only `rv-coverage`
