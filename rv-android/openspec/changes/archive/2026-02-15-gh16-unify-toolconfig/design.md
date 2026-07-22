# Design: Unify ToolConfig Classes

## Context

This design supports the gh16-unify-toolconfig change (GitHub Issue #16). The system has two `ToolConfig` classes with different field names serving overlapping roles — one in rv-android-core (task level) and one in rv-platform (config level). This dualism causes naming confusion, unnecessary conversion code, and a wrong dependency direction. Additionally, `save_experiment_config()` exists but is never called, blocking the calibration workflow needed for rv-agent parameter tuning.

Addresses: FR08 (Task Generation), FR15 (Experiment Configuration), FR18 (Tool Registration), FR20 (Variant System), FR33 (Domain Models).

## Architecture

```
CLI DSL ("droidbot:dfs_greedy:bfs_greedy")
    |
    v
parse_tool_specification()  ← expands variants here (rv-experiment CLI)
    |
    v
[ToolConfig(name="droidbot", variant="dfs_greedy"),
 ToolConfig(name="droidbot", variant="bfs_greedy")]   ← from rv_android_core.domain.task
    |
    v
ExperimentConfig.tool_configs  ← stored, passed through unchanged
    |
    v
ExecutionController._create_platform_config()  ← injects device_port, same ToolConfig class
    |
    v
Platform._generate_tasks()  ← iterates tool_configs × reps × timeouts (no variant loop)
    |
    v
ToolFactory.create_tool(tool_config)  ← resolves variant, merges params
    |
    v
tool.configure(final_dict)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `rv_android_core.domain.task.ToolConfig` | Single source of truth for tool config | name, variant, parameters | Validated config object |
| `parse_tool_specification()` | Parse CLI DSL + expand variants | `"droidbot:dfs_greedy:bfs_greedy"` | `List[ToolConfig]` |
| `ExperimentConfig.from_dict()` | Deserialize with legacy migration | JSON dict | `ExperimentConfig` |
| `Platform._generate_tasks()` | Generate Cartesian product | tool_configs × reps × timeouts | `List[Task]` |
| `ToolFactory.create_tool()` | Resolve variant + create tool | `ToolConfig` | Configured `AbstractTool` |
| `ExperimentController.run()` | Auto-save config on run | `ExperimentConfig` | `experiment_config.json` |

## Mapping: Spec → Implementation

| Requirement | Implementation | Test |
|-------------|---------------|------|
| FR33: ToolConfig unified fields | `rv_android_core/domain/task.py:ToolConfig` | `test_task.py::test_tool_config_*` |
| FR33: ToolConfig from_dict | `ToolConfig.from_dict()` deserialization | `test_task.py::test_tool_config_from_dict` |
| FR08: Task generation without variant loop | `Platform._generate_tasks()` simplified | `test_executor.py`, `test_resume.py` |
| FR15: CLI variant expansion | `parse_tool_specification()` in `__main__.py` | `test_config_json.py::test_variant_expansion` |
| FR15: JSON config auto-save | `ExperimentController.run()` calls `save_experiment_config()` | `test_config_json.py::test_auto_save` |
| FR15: from_dict current format only | `ExperimentConfig.from_dict()` uses `variant: str` | `test_config_json.py::test_from_dict_current_format` |
| FR18: Factory field names | `ToolFactory.create_tool()` uses `.name`, `.parameters` | `test_tool_execution.py` |
| FR20: DSL parsing fields | `parse_tool_specification()` returns unified ToolConfig | `test_config_json.py::test_dsl_parsing` |
| Dead code: rvandroid | Delete `if tool_name == "rvandroid"` block in `factory.py` | N/A (negative test removed) |

## API Design

### `ToolConfig(name: str, variant: str = "default", parameters: Dict = {})` → `ToolConfig`

Single unified tool configuration used by all modules.

- **Preconditions**: `name` must be non-empty string
- **Postconditions**: Instance with validated fields, `variant` defaults to `"default"`, `parameters` defaults to empty dict
- **Error behavior**: Validation error if `name` is empty (when `RV_PYDANTIC=true`)

### `ToolConfig.from_dict(data: Dict) -> ToolConfig`

Deserialize from dict using current field names only.

- **Preconditions**: `data` is a dict with keys `name`, `variant`, `parameters`
- **Postconditions**: ToolConfig with validated fields
- **Error behavior**: Missing `name` key results in empty string (validation catches it when `RV_PYDANTIC=true`)

### `ToolConfig.get_full_tool_name() -> str`

Returns `"tool:variant"` or `"tool"` if variant is `"default"`.

### `parse_tool_specification(spec: str, parameters: Dict) -> List[ToolConfig]`

Parse CLI DSL and expand multi-variant specs into separate ToolConfig instances.

- **Preconditions**: `spec` is comma-separated tool specifications in DSL format
- **Postconditions**: List of ToolConfig, one per (tool, variant) pair
- **Error behavior**: Empty tool name raises validation error

## Data Flow

```
CLI: --tools droidbot:dfs_greedy:bfs_greedy@count=5000 --timeout 60 300

    ↓ parse_tool_specification()

[ToolConfig(name="droidbot", variant="dfs_greedy", parameters={"count":"5000"}),
 ToolConfig(name="droidbot", variant="bfs_greedy", parameters={"count":"5000"})]

    ↓ ExperimentConfig(tool_configs=[...])

    ↓ save_experiment_config()  →  results/<name>/experiment_config.json

    ↓ ExecutionController._create_platform_config()

PlatformConfig(tools=[ToolConfig(...), ToolConfig(...)], ...)
                                                    ↓
                                      inject device_port into parameters copy

    ↓ Platform._generate_tasks()

[Task(tool_config=TC1, rep=1, timeout=60),
 Task(tool_config=TC1, rep=1, timeout=300),
 Task(tool_config=TC2, rep=1, timeout=60),
 Task(tool_config=TC2, rep=1, timeout=300)]

    ↓ ToolFactory.create_tool(task.tool_config)

Configured DroidBotTool instance → tool.execute(task, app)
```

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `AttributeError` on old field names | Missed field rename in some module | Runtime crash on affected code path | Comprehensive grep before declaring complete |
| Old `tasks.json` with previous field names | Experiment resume after upgrade | `from_dict()` fails — old fields not recognized | Per P3: re-run experiment from scratch |
| Old JSON config with `variants:[]` | User JSON file with old format | `from_dict()` fails — `variants` not recognized | Per P3: user edits JSON to use `variant: str` |
| Config checksum mismatch on resume | Field name change alters SHA-256 | WARNING log with first 8 hex chars | Execution continues normally |

## Acceptance Criteria

The change is complete when ALL of the following are satisfied:

### AC1: Zero orphaned field references
`grep -rn` for `tool_name` (as ToolConfig field), `additional_params`, and `variants` (as plural ToolConfig field) across all `modules/*/src/` returns zero hits. No exceptions — per P3, no legacy code exists.

### AC2: All existing tests pass
`uv run pytest modules/rv-android-core/tests/ modules/rv-platform/tests/ modules/rv-experiment/tests/ modules/rv-tools/tests/ -v` — all green.

### AC3: New unit tests pass
New `test_config_json.py` and legacy migration tests in `test_task.py` — all green.

### AC4: experiment_config.json auto-saved
After any `rv-experiment run`, the file `results/<name>/experiment_config.json` MUST exist, use unified field names (`name`, `variant`, `parameters`), and be loadable via `--config`.

### AC5: End-to-end rv-experiment with rvagent (full pipeline)
Run `rv-experiment run --tools rvagent:pure_algorithm --specification-set jca --apks-dir ./apks_examples --timeout 60 --name e2e_test`. This exercises the full pipeline: monitor generation, APK instrumentation, static analysis, and rvagent execution. Validate:
- Experiment completes without errors
- `results/e2e_test/experiment_config.json` exists with unified field names
- `results/e2e_test/tasks.json` exists with `"name"` and `"parameters"` fields (not `"tool_name"` / `"additional_params"`)
- Result CSVs exist (`coverage.csv`, `errors.csv`, `summary.csv`)

### AC6: End-to-end rv-platform with instrumented APKs
Using the instrumented APKs and static analysis files from AC5, run `rv-platform run --tools rvagent:pure_algorithm --apks-dir results/e2e_test/instrumented_apks --timeout 60 --skip-result-processing`. This validates the platform path independently (no experiment wrapper), using pre-processed artifacts. Validate:
- Platform completes without errors
- Tasks executed with correct ToolConfig field names in logs

### AC7: JSON config reload produces same task set
Take `results/e2e_test/experiment_config.json` from AC5, run `rv-experiment run --config results/e2e_test/experiment_config.json --name e2e_reload --skip-monitors --skip-instrument --skip-static --apks-dir results/e2e_test/instrumented_apks`. Validate that the loaded config produces the same number of tasks as the original run.

## Testing Strategy

### New Tests Inventory

| File | Test | What it validates |
|------|------|-------------------|
| `rv-android-core/tests/domain/test_task.py` | `test_tool_config_unified_fields` | ToolConfig creation with `name`, `variant`, `parameters` |
| `rv-android-core/tests/domain/test_task.py` | `test_tool_config_default_variant` | `variant` defaults to `"default"`, `parameters` defaults to `{}` |
| `rv-android-core/tests/domain/test_task.py` | `test_tool_config_from_dict` | `from_dict()` works with current field names |
| `rv-android-core/tests/domain/test_task.py` | `test_tool_config_to_dict` | `to_dict()` uses unified field names |
| `rv-android-core/tests/domain/test_task.py` | `test_tool_config_get_full_tool_name` | Returns `"tool:variant"` or `"tool"` for default |
| `rv-experiment/tests/test_config_json.py` | `test_json_round_trip` | Save ExperimentConfig → load → compare (same tool_configs, timeouts, etc.) |
| `rv-experiment/tests/test_config_json.py` | `test_from_dict_current_format` | `from_dict()` deserializes `{"name": ..., "variant": ..., "parameters": ...}` correctly |
| `rv-experiment/tests/test_config_json.py` | `test_type_preservation` | JSON types preserved (int stays int, not converted to string) |
| `rv-experiment/tests/test_config_json.py` | `test_variant_expansion_at_parse_time` | `parse_tool_specification("droidbot:a:b")` → 2 ToolConfig instances |

### Test Coverage by Layer

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | ToolConfig creation, from_dict, to_dict, get_full_tool_name | Direct assertions | ~5 tests |
| Unit | ExperimentConfig.from_dict current format | Mock JSON input | ~1 test |
| Unit | JSON config round-trip (save → load → compare) + type preservation | File I/O with temp dir | ~2 tests |
| Integration | CLI variant expansion → ToolConfig count | Parse spec, verify list | ~1 test |
| E2E | rv-experiment full pipeline (monitors + instrument + static + rvagent) | Real execution, validate result files | 1 manual test |
| E2E | rv-platform with pre-instrumented APKs | Real execution, validate task completion | 1 manual test |
| E2E | JSON config reload produces same task set | Real execution, compare task counts | 1 manual test |
| Negative | Orphaned field reference grep | `grep -rn` across all modules | 1 check |

## Decisions

### D1: Field names — use rv-platform naming (`name`, `variant`, `parameters`)

**Chosen**: rv-platform field names (`name`, `variant`, `parameters`)
**Alternative**: rv-android-core field names (`tool_name`, `variant`, `additional_params`)
**Rationale**: The rv-platform names are shorter, more generic, and align with standard naming conventions. `name` is simpler than `tool_name` (the context already implies it's a tool). `parameters` is clearer than `additional_params` (they're not always "additional"). The only field that stays the same is `variant`.

### D2: Variant expansion at CLI parser, not Platform

**Chosen**: Expand variants into separate ToolConfig instances at `parse_tool_specification()` time.
**Alternative**: Keep variant expansion inside `Platform._generate_tasks()`.
**Rationale**: Moving expansion to the parser eliminates one loop level in `_generate_tasks()`, removes the need for two ToolConfig classes, and makes JSON configs explicit (each entry = one tool+variant pair). The CLI syntax `droidbot:dfs_greedy:bfs_greedy` continues to work — the parser just expands earlier.

### D3: No legacy support — strict P3 compliance

**Chosen**: `ToolConfig.from_dict()` and `ExperimentConfig.from_dict()` accept only the current field names. Old `tasks.json` and old JSON configs fail to load.
**Alternative**: Add migration logic to map old field names to new ones.
**Rationale**: P3 (No Backward Compatibility) is non-negotiable. Migration code is backward compatibility code regardless of how it's labeled. Old experiments must be re-run. Old JSON configs must be edited. This produces simpler code (P1) and a cleaner codebase (P4).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Missed field reference causes runtime `AttributeError` | Comprehensive grep for `tool_name`, `additional_params`, `variants` (plural as field) before completion |
| Config checksum changes break resume matching | Already handled gracefully — WARNING log, execution continues |
| Old JSON configs / tasks.json fail to load | Per P3: no migration. Users re-run experiments or edit JSON manually. This is a deliberate trade-off for codebase simplicity. |
| Test files use old field names | Phase updates all test files mechanically |
