# CLAUDE.md - rv-experiment

Experiment orchestration + primary CLI (`rv-experiment`) for RV-Android. It owns the
three-phase workflow and delegates execution to rv-platform. Identity: **clean separation**
(orchestration only, execution lives in rv-platform), **no data transfer** (results stay in
rv-platform; only a success/failure status crosses back), **just-in-time configuration**
(sub-module configs built only when accessed).

## Source layout
Paths relative to `src/rv_experiment/`.

| Path | Role |
|---|---|
| `__main__.py` | Click CLI: group `cli` (`--debug`, `--log-level`, `--show-context`) with `run`, `config`, `list-tools`, `validate`; builds `ExperimentConfig` from flags (`_create_experiment_config_from_cli`) |
| `config.py` | `ExperimentConfig` Pydantic model, JIT sub-module config methods, `resolve_package_detector` / `resolve_strip_build_type_suffix` / `resolve_stamp_handlers` |
| `constants.py` | Directory names, `SPEC_SET_*`, `DEFAULT_*` |
| `experiment/experiment_controller.py` | `ExperimentController.run()` (pre → exec → post), `execute_with_config(config) -> bool` |
| `experiment/workflow/pre_processor.py` | `PreProcessor`: monitors, instrumentation, static analysis, flag-combination guards |
| `experiment/workflow/execution_controller.py` | `ExecutionController`: builds `PlatformConfig`, calls `Platform(config).run()` |
| `experiment/workflow/post_processor.py`, `result_manager.py` | `instrument_errors.json` + `experiment_completion.json` |
| `experiment/workflow/workflow_factory.py` | `WorkflowFactory`: builds the three phase objects |
| `factories/configuration_factory.py` | `ConfigurationFactory` — no production caller (tests only); the CLI does not use it |

## Tool Specification DSL
Format: `tool_name[:variant1][:variant2][@param1=value1,param2=value2]`
Examples: `monkey`, `droidbot:dfs_greedy`, `rvagent:multimode@temperature=0.3`,
`monkey,droidbot:dfs_greedy,ape` (comma-separated = multiple tools; `_split_tool_specifications`
splits on commas outside the `@...` section).
Passed via `--tools` (see top `rv-android/CLAUDE.md` for `run` examples) or `--config <json>`.
Under `--config` the JSON file is the authority: `--tools` is not parsed, and the file's
`package_detector`, `strip_build_type_suffix` and `stamp_handlers` win over the flags.

### Server URLs injected into tool parameters
After the tool specifications are parsed into `ToolConfig`s, `__main__.py` reads two server
addresses from the environment, through their `ENV_*` constants, and passes them on by value in
`ToolConfig.parameters`; the plugins below it read no environment (INV-TOOL-20):
- `RV_HUMANOID_URL` — the shared inference server the Humanoid wrapper talks to.
- `APERV_LLM_BASE_URL` (INV-EXP-41) — the LLM endpoint of the `aperv` cells that mount the LLM
  group. When it is non-empty, every `aperv` `ToolConfig` whose variant definition in
  `ToolRegistry` carries `overrides.llm_url` (today `as_llm` and `as_mop_llm`) and whose
  parameters carry no `llm_url` receives `parameters["llm_url"]`; `ApeRVTool.configure()`'s DSL
  fold then moves it into `overrides`. The LLM cells are found through the registry, not a list of
  names here. Precedence is DSL `@llm_url` > variable > the cell's default
  (`http://10.0.2.2:30000/v1`). Cells without the LLM group never receive it, because it would
  write an `ape.llmUrl` line for a group they do not mount. It is the one user-facing name outside
  `RV_*` that the entry-point rule admits, because the `aperv-tool` docs advertise that name.
  `rv-platform run` does not read it.

## Three-Phase Workflow
1. **Pre-Processing** (`PreProcessor.process`), in this order:
   - monitor generation via `rv-monitor-generator` into `<output_dir>/monitors/`; on success writes
     the provenance marker `monitors/specification_set.txt` (the set name). A generation failure
     logs `"Monitor generation failed"`, writes no marker, and pre-processing continues;
   - APK instrumentation via `rv_instrumentation.get_instrumenter(variant, config)` (`ajc` or
     `dexlib2`) into `<output_dir>/instrumented_apks/`; when the instrumenter raises (or the module
     is missing) the original APKs are copied there unmonitored, while a `False` return only logs;
   - GATOR static analysis (`rv-static-analysis`) on the **original** APKs that have an
     instrumented counterpart; the artefact `<apk>.apk.json` lands beside the instrumented APK.
2. **Execution** (`ExecutionController`): builds `PlatformConfig`, calls rv-platform; no
   results flow back.
3. **Post-Processing** (`PostProcessor`): `instrument_errors.json` + `experiment_completion.json`
   only. CSV/JSON results are owned by rv-platform.

### Flag-combination guards (abort before execution)
`PreProcessingConfigurationError` aborts the run; `ExperimentController.run()` returns `False`, so
the CLI exits 1.
- **INV-EXP-37** — `--skip-instrument` with `--static-analysis` when
  `<output_dir>/instrumented_apks/` holds no `.apk`: static analysis would analyse nothing and
  publish empty denominators for the whole run.
- **INV-EXP-38** — `--skip-monitors` when `monitors/specification_set.txt` names a different set
  than `--specification-set`. An absent marker only warns (resumed runs force `--skip-monitors`).
- **INV-EXP-40** — `stamp_handlers` true with a variant other than `dexlib2` (`click.ClickException`
  raised in `run`, see below).

### Every instrumented APK runs
`PreProcessor.get_instrumented_apks()` returns every `.apk` in `instrumented_apks/`, with or
without `<apk>.apk.json`. An APK without the artefact runs with empty coverage cells and
`measured=false` (INV-PLT-35); its violation columns are written as usual. Only when there is no
instrumented APK at all does it fall back to the originals in `apks_dir`.
`_report_missing_static_analysis` logs one consolidated warning naming the APKs without an
artefact, or naming `--skip-static` when the step was skipped. The set that actually executes is
the directory rv-platform globs (`instrumented_apks/` when non-empty, else `apks_dir`); the list is
used for the emptiness check and logging.

### Exit code
`run` exits 1 when `execute_with_config()` returns `False` — any failed task
(`failed_tasks > 0` in the rv-platform summary), no APKs or tools available, an exception in
execution, or a pre-processing guard — and when any exception reaches the command body.
Docker entrypoints `exec` this CLI, so the container exit code is the run's.

## ExperimentConfig (`config.py`)
Fields: `name`, `description`, `tool_configs=[ToolConfig(...)]`, `repetitions`, `timeouts`,
`no_window`, `device_port`, pre-proc flags `generate_monitors`/`instrument_apks`/`run_static_analysis`,
`run_execution`, `instrumentation_variant` (`ajc`/`dexlib2`), `enable_quarantine` (ajc only),
`logcat_diagnostics`, `package_detector`, `strip_build_type_suffix`, `stamp_handlers`,
`specification_set` (`jca`/`jca_android`/`generic`/`custom`) + `custom_specs_dir` +
`custom_aspects_dir`, `apks_dir`, `apks_filter`, `analysis_timeout`, `jvm_memory`, `rvsec_root`,
`output_dir`/`results_dir`, `resume_mode`.

**`output_dir` == `results_dir` under the CLI.** `_create_experiment_config_from_cli` sets both to
the same flat directory: `--resume-dir` > `--output-dir` > `results/<name>` >
`results/cli_experiment_<timestamp>_<hex>`. So monitors, instrumented APKs, static-analysis
artefacts, `tasks.json` and the CSVs all live in `results/<id>/`. The model's own defaults
(`output_dir="out"`, `results_dir` derived) apply only to programmatic / `--config` construction.

`validate()` is wrapped by `@ErrorHandler.handle_errors` without `reraise`, so a failing check is
logged and absorbed. Checks that must stop a run live in Click (`click.Choice`, `BadParameter`
callbacks) or in `run` itself.

JIT methods (config built lazily on access; all resolve the RVSEC root through
`get_effective_rvsec_root()`: `rvsec_root` field > `RVSEC_HOME` > `ConfigurationError`):
- `get_monitored_operations_config()` → `RVGeneratorConfig` with all four paths explicit
- `get_instrumentation_config()` / `get_rv_instrumentation_config()` → `AjcInstrumentationConfig`
- `get_dexlib_instrumentation_config()` → `DexlibInstrumentationConfig`
- `get_static_analysis_config()` → `RVStaticAnalysisConfig` (`mop_dir` = the run's set;
  `analysis_timeout`/`jvm_memory` from flag > `RV_SA_TIMEOUT`/`RV_JVM_MEMORY` > module default)
- `get_module_config(module_name)` → generic dispatch (empty dict for unknown module)

`resolve_spec_set_dir(rvsec_root)` is the single set → directory mapping, shared by monitor
generation and static analysis so the APK is instrumented and measured against the same set.

## Handler stamp (`--stamp-handlers`, INV-EXP-40)
`run --stamp-handlers/--no-stamp-handlers` asks the `dexlib2` instrumenter to record the
click/long-click handler of each clickable node, View and Compose, on that accessibility node. Declared like
`--strip-build-type-suffix`: `default=None`, no `envvar=`; `_stamp_handlers_callback` calls
`config.resolve_stamp_handlers`, the only read of `RV_STAMP_HANDLERS`
(`ENV_STAMP_HANDLERS`), through `resolve_bool_setting` — flag > variable > default `False`,
and an unparseable value is a usage error naming the variable. The value lands in
`ExperimentConfig.stamp_handlers`, and
`get_dexlib_instrumentation_config()` forwards it to `DexlibInstrumentationConfig.stamp_handlers`.
Under `--config` the file's `stamp_handlers` is the authority. `run` aborts before
pre-processing when the resolved config has `stamp_handlers` true and a variant other than
`dexlib2`, with a message that names all three sources (`--stamp-handlers`,
`RV_STAMP_HANDLERS`, `stamp_handlers` in `--config`) because the value may have come from
any of them; the check sits in `run`, not in `validate()`, whose `@handle_errors` wrapper
absorbs exceptions.

`experiment_config.json` records the stamp policy *this invocation* asked for, not what the
APKs carry. Under `--skip-instrument` or a resume, the flag has no effect: the APKs were
instrumented by an earlier invocation, and only that invocation's record says whether they
carry the stamp. Under `--skip-instrument` that record is the `experiment_config.json` of the
run that produced the APKs. A resume writes into the same results directory, and
`ExperimentController.save_experiment_config()` runs at the start of every `run`, so the
resuming invocation overwrites the earlier record; the `stamp*` counters in the
instrumentation results (present only when the stamp was on, see
`rv-instrumentation-dexlib2/CLAUDE.md`) still tell a stamped instrumentation from an
unstamped one.

## Package policy flags
`--package-detector/--no-package-detector` and `--strip-build-type-suffix/--no-strip-build-type-suffix`
follow the same pattern (`default=None`, no `envvar=`, callback → `resolve_*` → `resolve_bool_setting`,
flag > `RV_PACKAGE_DETECTOR` / `RV_STRIP_BUILD_TYPE_SUFFIX` > `False`). `PreProcessor._build_app`
builds every `App` under the resolved policy; the values are also forwarded to `PlatformConfig`.
What the policies mean is documented in `rv-static-analysis/CLAUDE.md`.

## Directory constants (`constants.py`)
`RESULTS_DIR="results"`, `INSTRUMENTED_DIR="out"` (`ExperimentConfig.output_dir` default),
`MONITORS_DIR="monitors"`, `MONITORS_PROVENANCE_FILE="specification_set.txt"`,
`INSTRUMENTED_APKS_DIR="instrumented_apks"`, `DEFAULT_SPEC_SET="jca"`, `DEFAULT_TIMEOUT=300`,
`DEFAULT_REPETITIONS=1`, `DEFAULT_APKS_DIR="apks_examples"`.

## rv-platform seam
External tools (e.g. rvagent) are registered by rv-platform on import; access via
`ToolRegistry.get_instance()` from rv-tools. `ExecutionController` creates a
`PlatformConfig(apks_dir, tools, repetitions, timeouts, results_dir, no_window, log_level,
apks_filter_file, logcat_diagnostics, package_detector, strip_build_type_suffix)` then calls
`Platform(config).run()`. `device_port` is injected into each tool's parameters
(`device_port`, `device_serial`, `device_id`).

To add a tool: create its class, add the module dep to `rv-platform/pyproject.toml`, and
register it in `rv-platform/src/rv_platform/__init__.py::_register_external_tools()`.

## Specification sets
Selected by `--specification-set` (`click.Choice`, env `RV_SPEC_SET`, default `jca`):
- `jca`: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/`
- `jca_android`: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android/` — the JCA
  set derived for a declared Android API level, and the one carrying the specification
  repairs; it is selectable by name so that a stale `custom` path cannot silently
  substitute the frozen `jca` set for it
- `generic`: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic/`
- `custom`: `--custom-specs-dir` pointing at a dir of `.mop` files (required; `run` raises a
  `ClickException` without it)

Other directories under `resources/` (`generic_new`, `jca_android_bug_predicate`) have no set
name and are reachable only as a `custom` path. `--custom-aspects-dir` replaces the default
`resources/aspect/` passed to the monitor generator.

## Experiment Resume
Two entry points: `--name` (implicit — activates when `results/<name>/tasks.json` exists) and
`--resume-dir <dir>` (explicit; overrides `--name`). Orchestration invariants:
- **Auto-skip pre-processing** (INV-EXP-13): on resume all pre-proc flags
  (`generate_monitors`/`instrument_apks`/`run_static_analysis`) are forced to `False`
  regardless of CLI values.
- **Flat results dir** (INV-EXP-14): `ExperimentController` uses `config.results_dir` directly, no
  subdirectory nesting.
- Task-skip mechanics (loading completed tasks from `tasks.json`, MOP reconstruction from
  logcat) are rv-platform's responsibility — see its CLAUDE.md.

## Docker Execution Mode
Runs inside containers via `docker/rvandroid/docker-entrypoint.sh`. The entrypoint
validates `RV_*` names against the `ENV_*` registry (`rv-android-core/constants.py`, through
`docker/rvandroid/scripts/validate_env_vars.sh`; unknown → exit 64) and
`exec uv run --no-sync rv-experiment run` (the image also sets `UV_NO_SYNC=1`: a sync would
rebuild the editable workspace members, whose ctime changes when the layers are unpacked, and
fetch the build backend from PyPI). Most `RV_*` vars are resolved by Click's
per-option `envvar=`.

**Negation-flag gotcha**: 5 boolean-negation vars are translated to explicit
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

## Gotchas
- `python -m rv_experiment` runs `run_local()`, a development helper with a hardcoded path, not
  `main()`. Use the `rv-experiment` console script.
- With `--skip-monitors`/`--skip-instrument`/`--skip-static`, `--apks-dir` must point at the
  instrumented APKs of a previous run (`results/<id>/instrumented_apks/`), see root `CLAUDE.md`.

## Tests
```bash
# From rv-android root
uv run pytest modules/rv-experiment/tests/ --import-mode=importlib -o "addopts=" -v
```
`tests/test_cli_*.py` cover the CLI (exit code, env-var precedence, package detector, spec set,
stamp handlers); `tests/test_config_*.py` the model and JIT methods; `tests/test_resume_cli.py`
resume detection; `tests/experiment/` the controller and the three workflow phases.
