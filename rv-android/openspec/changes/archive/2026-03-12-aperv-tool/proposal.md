## Why

Phase 4 of the APE-RV research project introduces `aperv-tool`, a Python rv-tools plugin that wraps the enhanced `ape-rv.jar` (built in Phase 1–2 of the ape repo) for controlled integration into the rv-android experiment framework. Without this module, the enhanced APE binary cannot participate in rv-experiment runs, making comparative experiments between the original `ape` builtin and the enhanced `aperv` variant impossible. GitHub Issue: phtcosta/ape#3 (ape repo); linked rv-android change.

## What Changes

- **New module** `modules/aperv-tool/` added to the uv workspace (auto-discovered via `members = ["modules/*"]`).
- **New class** `ApeRVTool(AbstractTool)` in `aperv_tool/tools/aperv/tool.py` that locates `ape-rv.jar`, pushes it to the Android device via ADB, and executes the enhanced APE via `app_process`.
- **New variants** registered: `default`, `sata`, `sata_mop`, `bfs`, `random` — each mapping to an APE exploration strategy.
- **rv-platform registration**: `_register_external_tools()` in `rv_platform/__init__.py` gains an idempotent import block for `ApeRVTool` (same pattern as `RVSmartTool`).
- **JAR delivery**: `ape-rv.jar` is placed in `src/aperv_tool/tools/aperv/` by `mvn install` in the ape repo; the file is gitignored.

## Capabilities

### New Capabilities
- `aperv`: New external tool registered in the tools subsystem. `ApeRVTool` locates and pushes `ape-rv.jar`, writes an `ape.properties` file with throttle configuration, and launches the enhanced APE via `app_process` using the `com.android.commands.monkey.Monkey` main class with `--ape <strategy>` and `--running-minutes <N>` flags. Variants `sata`, `bfs`, `random` run without MOP data; `sata_mop` is a placeholder variant for Phase 3 MOP-guided scoring (currently behaves identically to `sata`).

### Modified Capabilities
- `tools`: `_register_external_tools()` in rv-platform gains one additional idempotent registration block for `ApeRVTool`. No existing behavior changes.

## Impact

**Modules affected**:
- `aperv-tool` (new): depends on `rv-android-core`, `rv-tools`
- `rv-platform`: `__init__.py` modified to register `ApeRVTool`

**FRs**: FR18 (tool registration and factory system), FR19 (external tool support), FR20 (per-tool variant system)

**NFRs**: NFR02 (modularity — optional module; graceful ImportError if not installed)

**Dependencies**: `ape-rv.jar` produced by `mvn install` in `workspace-rv/ape`; must exist before running `aperv` tool. No runtime Python dependencies beyond `rv-android-core` and `rv-tools`.

**Cross-module interfaces**: `ApeRVTool` implements `AbstractTool` from `rv-android-core`; registered via `ToolRegistry` from `rv-tools`; invoked by `ToolExecutionComponent` in `rv-platform`. No changes to these interfaces.
