## Purpose

The `experiment` capability owns the orchestration layer: the CLI, `ExperimentConfig` and its validation, and the just-in-time methods that build each sub-module's configuration when Phase 1 reaches it. This change touches it for one reason — the derived `jca_android` specification set becomes a value of `specification_set` that the user selects by name (D-S8).

That is a small edit to the code and a consequential one to this capability's contract, because three separate places here enumerate the accepted values: the input contract for `specification_set`, the validation invariant INV-EXP-03, and the directory mapping stated inside the just-in-time requirement. An enumeration is a closed statement — a reader who finds three values in the invariant and four in the code has no way to tell which is authoritative, and the code's own docstring cites the invariant by clause letter. All three are restated here together.

Nothing else about orchestration changes. The set is still selected once per experiment and never mixed; `custom` still requires its directory; the three-level `RVSEC_HOME` hierarchy is untouched. What changes is that the corrected instrument is reachable without a hand-written path, which is what removes the hazard the change exists to remove: a stale `custom_specs_dir` silently selects the uncorrected `jca` set while the experiment records itself as having run the corrected one. The requirement that the derived set be selectable by name lives in the `instrumentation` capability, under `Specification Set Support (FR03)`; this delta is what makes the orchestration contract agree with it.

## Data Contracts

Only the entry this change alters is restated; every other input, output, side-effect and error of the capability is unchanged.

### Input

- `specification_set: str` -- One of "jca", "jca_android", "generic", "custom" (source: user input, default: "jca"). The first three name a directory under `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/`; only "custom" reads a path from the user

## Invariants

- **INV-EXP-03** (restated, replacing the entry of the same number): `ExperimentConfig.validate()` MUST be called before experiment execution. The validation MUST check: (a) name is non-empty, (b) at least one tool is configured, (c) repetitions > 0, (d) all timeouts > 0, (e) APK source directory exists and contains `.apk` files, (f) specification_set is one of "jca", "jca_android", "generic", "custom". Clause (f) is a closed enumeration and MUST reject anything outside it, including a near-miss spelling of a valid value: widening the list for the derived set MUST NOT weaken the check into an allow-anything, since a value that passes validation but names no directory would fail later, during monitor generation, with the experiment already under way.

## MODIFIED Requirements

### Requirement: Just-in-Time Sub-Module Configuration (FR17, NFR05)

The Experiment Orchestration domain MUST create sub-module configurations only when they are needed during experiment execution. This design exists because eager construction of all sub-module configurations during `ExperimentConfig.__init__()` would: (a) fail if optional sub-modules are not installed, (b) validate paths that may not be needed (e.g., RVSEC_HOME when pre-processing is skipped), and (c) couple configuration construction to the full module dependency tree.

`ExperimentConfig` MUST provide three JIT configuration methods:
- `get_monitored_operations_config()` -- creates `RVGeneratorConfig` for rv-monitor-generator
- `get_rv_instrumentation_config()` -- creates `RVInstrumentationConfig` for rv-instrumentation
- `get_static_analysis_config()` -- creates `RVStaticAnalysisConfig` for rv-static-analysis

Each method MUST resolve RVSEC_HOME using the three-level priority hierarchy (INV-EXP-05) and MUST construct the appropriate sub-module configuration with validated paths. These methods are called only by `PreProcessor` during Phase 1 when the corresponding operation is enabled.

The `get_monitored_operations_config()` method MUST select the specification directory based on the `specification_set` field: "jca" maps to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca`, "jca_android" maps to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca_android`, "generic" maps to `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic`, and "custom" uses the `custom_specs_dir` field directly. The three predefined values MUST derive their directory from the set name, so that selecting a predefined set never depends on a path the caller supplies and cannot be pointed at a set other than the one the experiment records.

The `get_module_config()` method MUST serve as a generic dispatcher that routes module names to the appropriate JIT method. It MUST support the module names "rv-monitor-generator", "rv-instrumentation", and "rv-static-analysis".

#### Scenario: JIT Configuration for Monitor Generation With JCA Specs

- **WHEN** `PreProcessor._generate_monitors()` calls `config.get_monitored_operations_config()` with `specification_set="jca"` and `RVSEC_HOME="/path/to/rvsec"`
- **THEN** the method MUST return an `RVGeneratorConfig` instance with:
  - `rvsec_root="/path/to/rvsec"`
  - `javamop_bin="/path/to/rvsec/javamop/bin/javamop"`
  - `rvmonitor_bin="/path/to/rvsec/rv-monitor/bin/rv-monitor"`
  - `mop_specs_dir="/path/to/rvsec/rvsec/rvsec-mop/src/main/resources/jca"`
  - `aspects_dir="/path/to/rvsec/rvsec/rvsec-mop/src/main/resources/aspect"`
- **AND** `mop_specs_dir` MUST be the frozen set's directory exactly, not a directory whose name merely begins with it

#### Scenario: JIT Configuration for Monitor Generation With the Derived Android Specs

- **WHEN** `PreProcessor._generate_monitors()` calls `config.get_monitored_operations_config()` with `specification_set="jca_android"`, `custom_specs_dir=None` and `RVSEC_HOME="/path/to/rvsec"`
- **THEN** the method MUST return an `RVGeneratorConfig` with `mop_specs_dir="/path/to/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android"`
- **AND** MUST NOT raise for the absent `custom_specs_dir`, which is required by "custom" alone

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
