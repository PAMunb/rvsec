## Purpose

The `experiment` capability owns the orchestration layer: the CLI, `ExperimentConfig` and its validation, and the just-in-time methods that build each sub-module's configuration when Phase 1 reaches it. This change touches it for one reason — the successor specification set `jca_android` becomes a value of `specification_set` that the user selects by name. The set exists because the violation reports of the frozen `jca` cannot be read: 72.93 % of the 97,018 records of the published dataset carry the literal `unknown` as their message, and the identity under which records are deduplicated discards the one field that would tell which event fired. The repairs that fix this on the specification side cannot land in `jca` (frozen, `INV-INS-109`) nor in the derived Android set of gh101 (judged NOT READY by the 2026-08-08 audit), so they land in a new set. The name `jca_android` is rebound rather than added: the directory that held the derived set is renamed to `rvsec-mop/src/main/resources/jca_android_bug_predicate/` and stops being selectable, and `rvsec-mop/src/main/resources/jca_android/` is written fresh, seeded byte-identical from `jca`.

That is a small edit to the code and a consequential one to this capability's contract, because the accepted values are enumerated in several places that must agree: the input contract for `specification_set`, the validation invariant INV-EXP-03 clause (f), the directory mapping stated inside the just-in-time requirement, and the two enumeration sites in the code — the `click.Choice` of `--specification-set` in `modules/rv-experiment/src/rv_experiment/__main__.py` and `valid_spec_sets` plus the set → directory mapping in `modules/rv-experiment/src/rv_experiment/config.py` (`validate()` and `get_monitored_operations_config()`). The enumeration itself does not grow: it keeps the four values `jca`, `jca_android`, `generic`, `custom`, and what changes is the directory `jca_android` resolves to. An enumeration is a closed statement — a reader who finds one list in the invariant and another in the code has no way to tell which is authoritative — so every one of them is restated here together.

Nothing else about orchestration changes. The set is still selected once per experiment and never mixed; `custom` still requires its directory; the three-level `RVSEC_HOME` hierarchy is untouched. What matters is that the successor set is reachable without a hand-written path: pointing `custom_specs_dir` at a working copy of `jca_android` would let a stale path silently select the frozen `jca`, or the archived `jca_android_bug_predicate`, while the experiment records itself as having run the repaired set. The requirement that `jca_android` be a first-class set lives in the `instrumentation` capability, under `Specification Set Support (FR03)`; this delta makes the orchestration contract agree with it.

## Data Contracts

Only the entry this change alters is restated; every other input, output, side-effect and error of the capability is unchanged.

### Input

- `specification_set: str` -- One of "jca", "jca_android", "generic", "custom" (source: user input via `--specification-set` or `RV_SPEC_SET`, default: "jca"). The first four name a directory under `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/`; only "custom" reads a path from the user

### Output

- `RVGeneratorConfig.mop_specs_dir: str` -- For "jca_android", exactly `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android` (destination: `PreProcessor._generate_monitors()`)

### Side-Effects

- **[none added]**: selecting "jca_android" performs the same monitor generation as any predefined set; no file outside the experiment's `out/` and `results/` directories is written

### Error

- `click.BadParameter` -- raised by the CLI when `--specification-set` is not one of the four values; the message lists them
- `ValueError` -- raised by `ExperimentConfig.validate()` when `specification_set` is not one of the four values (INV-EXP-03 clause f); the message lists them

## Invariants

- **INV-EXP-03** (restated, replacing the entry of the same number): `ExperimentConfig.validate()` MUST be called before experiment execution. The validation MUST check: (a) name is non-empty, (b) at least one tool is configured, (c) repetitions > 0, (d) all timeouts > 0, (e) APK source directory exists and contains `.apk` files, (f) specification_set is one of "jca", "jca_android", "generic", "custom". Clause (f) is a closed enumeration and MUST reject anything outside it, including a near-miss spelling of a valid value and the name of a directory that exists but is not offered — `jca_android_bug_predicate`. Rebinding `jca_android` to the successor set does not widen the list and MUST NOT weaken the check into an allow-anything, since a value that passes validation but names no mapped directory would fail later, during monitor generation, with the experiment already under way. The `click.Choice` on `--specification-set` and `valid_spec_sets` in `config.py` MUST list the same four values, so the CLI and the model reject the same inputs.

## MODIFIED Requirements

### Requirement: Just-in-Time Sub-Module Configuration (FR17, NFR05)

The Experiment Orchestration domain MUST create sub-module configurations only when they are needed during experiment execution. This design exists because eager construction of all sub-module configurations during `ExperimentConfig.__init__()` would: (a) fail if optional sub-modules are not installed, (b) validate paths that may not be needed (e.g., RVSEC_HOME when pre-processing is skipped), and (c) couple configuration construction to the full module dependency tree.

`ExperimentConfig` MUST provide three JIT configuration methods:
- `get_monitored_operations_config()` -- creates `RVGeneratorConfig` for rv-monitor-generator
- `get_rv_instrumentation_config()` -- creates `RVInstrumentationConfig` for rv-instrumentation
- `get_static_analysis_config()` -- creates `RVStaticAnalysisConfig` for rv-static-analysis

Each method MUST resolve RVSEC_HOME using the three-level priority hierarchy (INV-EXP-05) and MUST construct the appropriate sub-module configuration with validated paths. These methods are called only by `PreProcessor` during Phase 1 when the corresponding operation is enabled.

The `get_monitored_operations_config()` method MUST select the specification directory based on the `specification_set` field: "jca" maps to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca`, "jca_android" maps to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android`, "generic" maps to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic`, and "custom" uses the `custom_specs_dir` field directly. The four predefined values MUST derive their directory from the set name, so that selecting a predefined set never depends on a path the caller supplies and cannot be pointed at a set other than the one the experiment records. `jca_android` is the successor of the frozen `jca`: it is seeded byte-identical from it and carries the specification-side repairs of this change, while `jca` and its freeze gate stay untouched. The derived set that carried this name before is archived as `jca_android_bug_predicate` and has no mapping entry at all, so it cannot be selected; reproducing the 2026-08-08 audit means pointing `RVSEC_HOME` at the commit that audit was run against, not naming a set here. Selecting `jca_android` by name is what keeps a run of the repaired set distinguishable from a run of the frozen one in the experiment record.

The enumeration of accepted values lives in exactly two places in the code — the `click.Choice` of `--specification-set` in `rv_experiment/__main__.py` and `valid_spec_sets` together with the set → directory mapping in `rv_experiment/config.py` — and both MUST list the same four values as INV-EXP-03 clause (f).

The `get_module_config()` method MUST serve as a generic dispatcher that routes module names to the appropriate JIT method. It MUST support the module names "rv-monitor-generator", "rv-instrumentation", and "rv-static-analysis".

#### Scenario: JIT Configuration for Monitor Generation With JCA Specs

- **WHEN** `PreProcessor._generate_monitors()` calls `config.get_monitored_operations_config()` with `specification_set="jca"` and `RVSEC_HOME="/path/to/rvsec"`
- **THEN** the method MUST return an `RVGeneratorConfig` instance with:
  - `rvsec_root="/path/to/rvsec"`
  - `javamop_bin="/path/to/rvsec/javamop/bin/javamop"`
  - `rvmonitor_bin="/path/to/rvsec/rv-monitor/bin/rv-monitor"`
  - `mop_specs_dir="/path/to/rvsec/rvsec/rvsec-mop/src/main/resources/jca"`
  - `aspects_dir="/path/to/rvsec/rvsec/rvsec-mop/src/main/resources/aspect"`
- **AND** `mop_specs_dir` MUST be the frozen set's directory exactly, not a directory whose name merely begins with it — `jca_android` and `jca_android_bug_predicate` are sibling directories, not sub-paths of `jca`

#### Scenario: JIT Configuration for Monitor Generation With the Successor Set

- **WHEN** `PreProcessor._generate_monitors()` calls `config.get_monitored_operations_config()` with `specification_set="jca_android"`, `custom_specs_dir=None` and `RVSEC_HOME="/path/to/rvsec"`
- **THEN** the method MUST return an `RVGeneratorConfig` with `mop_specs_dir="/path/to/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android"`
- **AND** MUST NOT raise for the absent `custom_specs_dir`, which is required by "custom" alone
- **AND** `mop_specs_dir` MUST NOT be `/path/to/rvsec/rvsec/rvsec-mop/src/main/resources/jca`, so a run of the successor set can never be recorded as a run of the frozen one
- **AND** `mop_specs_dir` MUST NOT be `/path/to/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android_bug_predicate` either — the archived directory's name has the successor's name as a prefix, so a mapping built by string matching rather than by explicit lookup would silently run the set the 2026-08-08 audit judged NOT READY

#### Scenario: Unknown Specification Set Is Rejected With the Full List

- **WHEN** `rv-experiment run --tools monkey --specification-set jca_android_bug_predicate` is invoked
- **THEN** the CLI MUST reject the value before any experiment state is created
- **AND** the error message MUST list the four accepted values `jca`, `jca_android`, `generic`, `custom`
- **AND** the rejection MUST hold even though `jca_android_bug_predicate` names a directory that exists, because the archived derived set is preserved for the record and is deliberately unreachable by name
- **AND** `ExperimentConfig(name="x", specification_set="jca_android_bug_predicate", ...).validate()` MUST raise `ValueError` whose message contains the same four values, so a configuration built without the CLI is rejected identically

#### Scenario: JIT Configuration for Custom Specification Set

- **WHEN** `config.get_monitored_operations_config()` is called with `specification_set="custom"` and `custom_specs_dir="/my/specs"`
- **THEN** the method MUST validate that `/my/specs` is a directory containing at least one `.mop` file
- **AND** MUST return an `RVGeneratorConfig` with `mop_specs_dir="/my/specs"`
- **AND** if the directory does not contain `.mop` files, MUST raise `ConfigurationError` with message: "Invalid specs dir: /my/specs"

#### Scenario: JIT Configuration for Custom Aspects Directory

- **WHEN** `config.get_monitored_operations_config()` is called with `custom_aspects_dir="/my/aspects"`
- **THEN** the method MUST use `/my/aspects` as the `aspects_dir` in the returned `RVGeneratorConfig`
- **AND** MUST NOT use the default RVSEC aspects directory

#### Scenario: RVSEC_HOME Not Available

- **WHEN** a JIT configuration method is called but neither `rvsec_root` is set in configuration nor `RVSEC_HOME` environment variable is defined
- **THEN** the method MUST raise `ConfigurationError` with message: "RVSEC_HOME not found in configuration or environment. Set rvsec_root field in configuration or RVSEC_HOME environment variable"

#### Scenario: RVSEC_HOME Path Does Not Exist

- **WHEN** `rvsec_root` is set to "/nonexistent/path" in configuration
- **THEN** `get_effective_rvsec_root()` MUST raise `ConfigurationError` with message: "Configured rvsec_root path does not exist: /nonexistent/path"

#### Scenario: JIT Configuration Not Called When Phase Is Skipped

- **WHEN** `generate_monitors=False` is set in ExperimentConfig
- **THEN** `PreProcessor.process()` MUST NOT call `config.get_monitored_operations_config()`
- **AND** missing or invalid RVSEC_HOME MUST NOT cause an error if all three pre-processing phases are skipped
