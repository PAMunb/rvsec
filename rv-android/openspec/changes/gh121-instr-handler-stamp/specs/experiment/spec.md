## Purpose

The handler stamp exists only in an APK instrumented with it, and the corpus of a campaign is instrumented by `rv-experiment`'s pre-processing. `rv-experiment` builds the `dexlib2` configuration itself (`ExperimentConfig.get_dexlib_instrumentation_config`), so without a switch of its own a campaign could not ask for the stamp, and the stamp would have to be produced outside the pipeline that records the run's provenance. This delta gives `rv-experiment run` that switch, as the project's other per-run policies are given: a negatable command-line flag, an `RV_*` environment variable for the containers that set their policy through the environment, and a default that leaves the instrumentation as it is today.

The value travels by value from the entry point to the instrumenter configuration. No module below `rv-experiment` reads the variable: the `dexlib2` wrapper turns the configuration field into the `instr-cli` argument `--stamp-handlers` (instrumentation INV-INS-180).

## Data Contracts

### Input
- `stamp_handlers: bool` -- Handler-stamp policy (source: `--stamp-handlers/--no-stamp-handlers` > `RV_STAMP_HANDLERS` > default `False`, INV-EXP-40); forwarded to `DexlibInstrumentationConfig.stamp_handlers` by `get_dexlib_instrumentation_config`, and recorded in `experiment_config.json`.
- `ENV_STAMP_HANDLERS: str = "RV_STAMP_HANDLERS"` -- constant of the core environment registry (`rv_android_core/constants.py`).

### Output
- `experiment_config.json` -- carries `stamp_handlers`.

### Side-Effects
- None beyond the instrumentation the flag selects.

### Error
- Pre-processing abort -- when the flag resolves to `True` and the instrumentation variant is not `dexlib2` (INV-EXP-37).

## Invariants

- **INV-EXP-40**: `RV_STAMP_HANDLERS` MUST be read only at the `rv-experiment` entry point, through the `ENV_STAMP_HANDLERS` constant of the core registry, with no string literal at any read site, and parsed with the project's truthiness convention through the shared `resolve_bool_setting` helper, not by Click's own boolean vocabulary (no `envvar=` on the option); a value the convention cannot parse MUST be a usage error naming the variable. Precedence MUST be CLI flag > environment variable > default `False`; an explicit `--no-stamp-handlers` MUST win over a truthy variable. No module between the entry point and `DexlibInstrumentationConfig` MUST read it: `get_dexlib_instrumentation_config` MUST set `stamp_handlers` from `ExperimentConfig.stamp_handlers`. When the resolved value is `True` and `--instrumentation-variant` is not `dexlib2`, the run MUST abort before pre-processing with a message naming the flag and the variant, because the `ajc` variant has no stamp and the flag would otherwise do nothing silently.

## ADDED Requirements

### Requirement: Handler Stamp CLI Flag (FR02, NFR05)

The `rv-experiment run` command SHALL expose the negatable boolean pair `--stamp-handlers` / `--no-stamp-handlers`. The resolved value SHALL set `ExperimentConfig.stamp_handlers`, and `get_dexlib_instrumentation_config` SHALL forward it to `DexlibInstrumentationConfig.stamp_handlers`, so the instrumentation of the run's APKs carries the handler stamp (instrumentation "Handler Stamp on the Accessibility Node").

An absent flag SHALL fall through to `RV_STAMP_HANDLERS`, parsed with the project's truthiness convention; an explicit negative SHALL win over a truthy variable. The default SHALL be `False`, so a run that sets neither instruments exactly as before this requirement. The option is declared as `--strip-build-type-suffix` is: `default=None`, so that "flag absent" stays distinguishable from `--no-stamp-handlers`, and a callback that resolves the variable through `resolve_bool_setting`, so this command and every other entry point read a boolean variable with one vocabulary. Under `--config` the JSON file is the authority for every setting, as for the sibling flags: the policy is the file's `stamp_handlers`.

`RV_STAMP_HANDLERS` SHALL be registered as `ENV_STAMP_HANDLERS` in `rv_android_core/constants.py`, documented in `README.md` or `.env.example`, and admitted by `docker/rvandroid/scripts/validate_env_vars.sh` (which builds its allow-list from the `ENV_*` constants of that file, so the registration admits it), so that `scripts/check_env_vars_drift.py` passes and a container that sets it is not rejected as using an unknown `RV_*` name.

The resolved policy SHALL be recorded in `experiment_config.json`, which is the run's provenance record: whether an APK of the run carries the stamp is then readable from the run itself, and from the `stamp*` counters the instrumenter writes into `instrument_results.json` only when the stamp is on.

The flag acts on instrumentation only. A run with `--skip-instrument` consumes APKs instrumented earlier, and whether those carry the stamp was decided when they were instrumented.

#### Scenario: Default leaves the instrumentation unchanged
- **WHEN** the user runs `uv run rv-experiment run --instrumentation-variant dexlib2 ...` with neither the flag nor the variable set
- **THEN** `ExperimentConfig.stamp_handlers` MUST be `False`
- **AND** the `instr-cli` argument list MUST contain neither `--stamp-handlers` nor `--no-stamp-handlers`
- **AND** `experiment_config.json` MUST record `stamp_handlers: false`

#### Scenario: The flag reaches the instrumenter
- **WHEN** the user runs `uv run rv-experiment run --instrumentation-variant dexlib2 --stamp-handlers ...`
- **THEN** `get_dexlib_instrumentation_config()` MUST return a configuration with `stamp_handlers == True`
- **AND** the `instr-cli` argument list MUST contain `--stamp-handlers` exactly once

#### Scenario: The variable turns it on and the negative flag wins
- **WHEN** `RV_STAMP_HANDLERS=true` is set and the user runs `rv-experiment run --instrumentation-variant dexlib2` without the flag
- **THEN** `ExperimentConfig.stamp_handlers` MUST be `True`
- **AND** when the same run is given `--no-stamp-handlers`, `ExperimentConfig.stamp_handlers` MUST be `False`

#### Scenario: An unparseable variable is a usage error
- **WHEN** `RV_STAMP_HANDLERS=maybe` is set and the user runs `rv-experiment run --instrumentation-variant dexlib2` without the flag
- **THEN** the command MUST exit with a usage error naming `RV_STAMP_HANDLERS` before any pre-processing

#### Scenario: The flag with the ajc variant aborts
- **WHEN** the user runs `rv-experiment run --instrumentation-variant ajc --stamp-handlers ...`
- **THEN** the command MUST abort before pre-processing
- **AND** the message MUST name `--stamp-handlers` and the `ajc` variant

#### Scenario: The read stays at the entry point
- **WHEN** the source tree is searched for reads of `RV_STAMP_HANDLERS`
- **THEN** the only read MUST be in `modules/rv-experiment/`, through `ENV_STAMP_HANDLERS`
- **AND** no module under `rv-instrumentation-*`, `rv-platform` or `rv-android-core` MUST read it
