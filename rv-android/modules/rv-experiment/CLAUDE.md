# CLAUDE.md - rv-experiment

Experiment orchestration + primary CLI (`rv-experiment`) for RV-Android. It owns the
three-phase workflow and delegates execution to rv-platform. Identity: **clean separation**
(orchestration only, execution lives in rv-platform), **no data transfer** (results stay in
rv-platform), **just-in-time configuration** (sub-module configs built only when accessed).

## Source layout
| Path | Role |
|---|---|
| `__main__.py` | Click CLI entry point |
| `config.py` | `ExperimentConfig` Pydantic model + JIT config methods |
| `constants.py` | Directory names / defaults |
| `experiment/experiment_controller.py` | Main orchestration |
| `experiment/workflow/{pre_processor,execution_controller,post_processor,result_manager,workflow_factory}.py` | Three-phase workflow |
| `factories/configuration_factory.py` | Config/template creation |

## Tool Specification DSL
Format: `tool_name[:variant1][:variant2][@param1=value1,param2=value2]`
Examples: `monkey`, `droidbot:dfs_greedy`, `rvagent:multimode@temperature=0.3`,
`monkey,droidbot:dfs_greedy,ape` (comma-separated = multiple tools).
Passed via `--tools` (see top `rv-android/CLAUDE.md` for `run` examples) or `--config <json>`.

## Three-Phase Workflow
1. **Pre-Processing** (`PreProcessor`): monitor generation, APK instrumentation via
   `rv_instrumentation.get_instrumenter(variant, config)` (INV-INS-36; `ajc`/`dexlib2`),
   static analysis (GATOR/GESDA/REACH).
2. **Execution** (`ExecutionController`): builds `PlatformConfig`, calls rv-platform; no
   results flow back.
3. **Post-Processing** (`PostProcessor`): instrumentation-errors JSON + completion
   diagnostics only. CSV/JSON results are owned by rv-platform.

## ExperimentConfig (`config.py`)
Fields: `name`, `description`, `tool_configs=[ToolConfig(...)]`, `repetitions`, `timeouts`,
`no_window`, pre-proc flags `generate_monitors`/`instrument_apks`/`run_static_analysis`,
`specification_set` (`jca`/`jca_android`/`generic`/`custom`) + `custom_specs_dir`, and
`apks_dir`/`output_dir`/`results_dir`.

JIT methods (config built lazily on access):
- `get_monitored_operations_config()` → rv-monitor-generator config
- `get_instrumentation_config()` → rv-instrumentation config
- `get_static_analysis_config()` → rv-static-analysis config
- `get_module_config(module_name)` → generic dispatch (empty dict for unknown module)

## Directory constants (`constants.py`)
`RESULTS_DIR="results"`, `INSTRUMENTED_DIR="out"`, `MONITORS_DIR="monitors"`,
`INSTRUMENTED_APKS_DIR="instrumented_apks"`, `STATIC_ANALYSIS_DIR="static_analysis"`
(legacy — output now goes to `instrumented_apks/`), plus `DEFAULT_*` defaults.

## rv-platform seam
External tools (e.g. rvagent) are registered by rv-platform on import; access via
`ToolRegistry.get_instance()` from rv-tools. `ExecutionController` creates a
`PlatformConfig(apks_dir, tools, repetitions, timeouts, results_dir, no_window)` then calls
`Platform(config).run()`.

To add a tool: create its class, add the module dep to `rv-platform/pyproject.toml`, and
register it in `rv-platform/src/rv_platform/__init__.py::_register_external_tools()`.

## Specification sets
- `jca`: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/`
- `jca_android`: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/` — the JCA
  set derived for a declared Android API level, and the one carrying the specification
  repairs; it is selectable by name so that a stale `custom` path cannot silently
  substitute the frozen `jca` set for it
- `generic`: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic/`
- `custom`: `--custom-specs-dir` pointing at a dir of `.mop` files

## Experiment Resume
Two entry points: `--name` (implicit — activates when `results/<name>/tasks.json` exists) and
`--resume-dir <dir>` (explicit; overrides `--name`). Orchestration invariants:
- **Auto-skip pre-processing**: on resume all pre-proc flags
  (`generate_monitors`/`instrument_apks`/`run_static_analysis`) are forced to `False`
  regardless of CLI values.
- **Flat results dir**: `ExperimentController` uses `config.results_dir` directly, no
  subdirectory nesting.
- Task-skip mechanics (loading completed tasks from `tasks.json`, MOP reconstruction from
  logcat) are rv-platform's responsibility — see its CLAUDE.md.

## Docker Execution Mode
Runs inside containers via `docker/rvandroid/docker-entrypoint.sh`. The entrypoint
validates `RV_*` names against the `ENV_*` registry (`rv-android-core/constants.py`; unknown
→ exit 64) and `exec rv-experiment run`. Most `RV_*` vars are resolved by Click's per-option
`envvar=`.

**Negation-flag gotcha (gh55 §9.6)**: 5 boolean-negation vars are translated to explicit
negative CLI flags *by the entrypoint only*, working around Click's `envvar=` inversion:

| Variable | CLI flag |
|---|---|
| `RV_SKIP_MONITORS` | `--skip-monitors` |
| `RV_SKIP_INSTRUMENT` | `--skip-instrument` |
| `RV_SKIP_STATIC_ANALYSIS` | `--skip-static` |
| `RV_SKIP_EXECUTION` | `--skip-execution` |
| `RV_NO_QUARANTINE` | `--no-quarantine` (ajc only) |

Standalone (`uv run rv-experiment ...`, no entrypoint): these 5 vars **silently do the
opposite of intent** (e.g. `RV_SKIP_MONITORS=true` → `generate_monitors=True`). Use the
explicit `--skip-*` CLI flags instead. Architectural fix tracked in
`openspec/changes/gh-tbd-env-vars-architecture/`.
