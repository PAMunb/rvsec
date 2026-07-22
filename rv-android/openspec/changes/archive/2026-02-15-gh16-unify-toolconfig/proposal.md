## Why

The tool configuration system carries accidental complexity from its evolution: two separate `ToolConfig` classes exist with different field names serving overlapping roles, variant expansion happens at the wrong architectural layer, and the JSON config save/load infrastructure — fully implemented — was never wired into the experiment workflow. Unifying the two classes into one cascades into simpler code paths across all modules and enables the calibration workflow needed for rv-agent parameter tuning.

GitHub Issue: #16

## What Changes

- **Unify ToolConfig**: Replace two `ToolConfig` classes (rv-android-core `tool_name/variant/additional_params` and rv-platform `name/variants/parameters`) with a single class in rv-android-core using fields `name`, `variant`, `parameters`
- **Delete duplicate**: Remove `ToolConfig` from `rv-platform/config/platform_config.py`; all modules import from rv-android-core
- **Move variant expansion**: Expand `droidbot:dfs_greedy:bfs_greedy` into separate ToolConfig instances at CLI parse time instead of inside `Platform._generate_tasks()`
- **Wire JSON config auto-save**: Call `save_experiment_config()` in `ExperimentController.run()` so every experiment produces `results/<name>/experiment_config.json`
- **Remove dead code**: Delete `rvandroid` special case in `ToolFactory.create_tool()`
- **Add JSON config tests**: New `test_config_json.py` for round-trip and type preservation
- **BREAKING**: JSON config format changes from `"variants": ["a", "b"]` to separate entries with `"variant": "a"`. Old format not supported per P3 — no migration code.

## Capabilities

### New Capabilities

_(none — this change simplifies existing behavior without introducing new capabilities)_

### Modified Capabilities

- `core`: ToolConfig field names change (`tool_name` -> `name`, `additional_params` -> `parameters`); `from_dict()` accepts current field names only (P3)
- `platform`: Removes local ToolConfig class; `_generate_tasks()` simplified (no variant loop, no class conversion); `total_tasks` calculation updated
- `tools`: ToolFactory field references updated; dead `rvandroid` code removed
- `experiment`: CLI parser expands variants at parse time; `ExperimentConfig.from_dict()` uses current format only (P3); `save_experiment_config()` wired into `run()`

## Impact

- **Modules affected**: rv-android-core, rv-platform, rv-tools, rv-experiment (4 modules)
- **Files**: 13 source, 8 test, 3 docs, 4 specs (28 total)
- **User-facing**: No CLI changes. JSON config format changes (old format not supported per P3). New `experiment_config.json` auto-saved in results dir.
- **Resume**: Old `tasks.json` with previous field names will NOT load — experiments must be re-run (P3). Config checksum changes trigger a warning but execution continues.
- **Risk**: Medium — field renames across ~20 files must be comprehensive. Mitigated by comprehensive grep verification + end-to-end validation with real experiment execution.
