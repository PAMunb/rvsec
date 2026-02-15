## 1. Core — Unified ToolConfig (rv-android-core)

- [x] 1.1 Rename ToolConfig fields in `rv-android-core/src/rv_android_core/domain/task.py`: `tool_name` → `name`, `additional_params` → `parameters`. Update all methods (`get_full_tool_name`, `to_dict`, `from_tool_specification`, `TaskConfiguration` references). Add `from_dict()` classmethod accepting current field names only (no legacy support per P3).
- [x] 1.2 Update `rv-android-core/tests/domain/test_task.py`: rename all ToolConfig field usages (`tool_name=` → `name=`, `additional_params=` → `parameters=`). Add test for `ToolConfig.from_dict()` with current field names.
- [x] 1.3 Update `rv-android-core/tests/tools/test_abstract_tool.py`: rename `tool_name=` → `name=` in all 7 ToolConfig constructors.

## 2. Platform — Delete Duplicate, Simplify (rv-platform)

- [x] 2.1 In `rv-platform/src/rv_platform/config/platform_config.py`: DELETE the local ToolConfig class (lines 17-29), import ToolConfig from `rv_android_core.domain.task`. Update `total_tasks` property to use `len(self.tools)` instead of iterating variants.
- [x] 2.2 In `rv-platform/src/rv_platform/platform.py`: remove variant loop and `TaskToolConfig` alias in `_generate_tasks()` (lines 145-163). Simplify to 3-level loop: tool_configs × reps × timeouts. Use `tool_config` directly (no conversion). Update `tool_config.name` references (was `tool_config.name` already, but remove `tool_name` local var).
- [x] 2.3 In `rv-platform/src/rv_platform/storage/task_storage.py`: update `.tool_config.tool_name` → `.tool_config.name`.
- [x] 2.4 In `rv-platform/src/rv_platform/components/emulator.py`: update `additional_params` → `parameters`.
- [x] 2.5 In `rv-platform/src/rv_platform/components/logcat.py`: update `additional_params` → `parameters`.
- [x] 2.6 In `rv-platform/src/rv_platform/__main__.py`: import ToolConfig from `rv_android_core.domain.task` instead of local config. Update CLI parsing to create unified ToolConfig.
- [x] 2.7 Update platform tests: `test_platform_config.py` (delete/rewrite tests for deleted class), `test_executor.py` (field renames), `test_resume.py` (field renames), `test_tool_execution.py` (field renames + imports).

## 3. Tools — Update Factory (rv-tools)

- [x] 3.1 In `rv-tools/src/rv_tools/registry/factory.py`: update `tool_config.tool_name` → `tool_config.name`, `tool_config.additional_params` → `tool_config.parameters`. Delete dead `if tool_name == "rvandroid"` block (lines 141-143).

## 4. Experiment — CLI Parser, Config, Auto-Save (rv-experiment)

- [x] 4.1 In `rv-experiment/src/rv_experiment/__main__.py`: import ToolConfig from `rv_android_core.domain.task`. Update `parse_tool_specification()` to expand multi-variant specs into separate ToolConfig instances at parse time (e.g., `droidbot:dfs_greedy:bfs_greedy` → 2 ToolConfig objects).
- [x] 4.2 In `rv-experiment/src/rv_experiment/config.py`: import ToolConfig from `rv_android_core.domain.task`. Update `from_dict()` to use `ToolConfig.from_dict()` with current field names only (no legacy `"variants": [...]` support per P3). Update `_validate_tool_variants()` for singular variant field.
- [x] 4.3 In `rv-experiment/src/rv_experiment/experiment/experiment_controller.py`: add `self.save_experiment_config()` call at the start of `run()`. Remove any `TaskToolConfig` alias if present.
- [x] 4.4 In `rv-experiment/src/rv_experiment/experiment/workflow/execution_controller.py`: import ToolConfig from `rv_android_core.domain.task`. Simplify `_create_platform_config()` to use same ToolConfig class (no conversion needed, just inject device_port into parameters copy).
- [x] 4.5 In `rv-experiment/src/rv_experiment/factories/configuration_factory.py`: import ToolConfig from `rv_android_core.domain.task`. Update `variant=` instead of `variants=` in template methods.
- [x] 4.6 Update experiment tests: `test_experiment_controller.py` (update variant handling). Create NEW `test_config_json.py` with tests for: JSON round-trip, `from_dict()` with current format, type preservation, CLI variant expansion.

## 5. Automated Verification

- [x] 5.1 Run all module tests: `uv run pytest modules/rv-android-core/tests/ modules/rv-platform/tests/ modules/rv-experiment/tests/ modules/rv-tools/tests/ -v` — all green (AC2). 824 passed, 11 pre-existing failures (confirmed on original code).
- [x] 5.2 Grep for orphaned field references: `tool_name` (as ToolConfig field), `additional_params`, `variants` (as plural field in ToolConfig) — must return zero hits in source files. No exceptions per P3 (AC1). Verified: zero ToolConfig field references found.

## 6. End-to-End Validation

- [x] 6.1 **rv-experiment full pipeline with rvagent** (AC5): Run `uv run rv-experiment run --tools rvagent:pure_algorithm --specification-set jca --apks-dir ./apks_examples --timeout 60 --name e2e_unified`. Validated: (a) experiment completed without errors, (b) experiment_config.json has `name/variant/parameters` only, (c) tasks.json tool_config has `name/variant/parameters`, (d) all CSVs exist (coverage, errors, summary, performance).
- [x] 6.2 **rv-platform with instrumented APKs** (AC6): Platform completed independently — 1/1 tasks successful, 100% success rate. Correct ToolConfig field names in logs.
- [x] 6.3 **JSON config reload** (AC7): Config reload recognized 1 previous task, skipped it (0 new tasks), consolidated results correctly. Loaded config produced same task set.

## 7. Documentation

- [x] 7.1 Update `modules/rv-platform/CLAUDE.md`, `modules/rv-tools/CLAUDE.md`, and `modules/rv-android-core/CLAUDE.md` with new ToolConfig field names in code examples.
