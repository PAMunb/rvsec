# Delta Spec: experiment — gh98-manifest-package-default

## Purpose

`rv-experiment` is the layer where a run's configuration is decided. It is the only Python module that reads user-facing `RV_*` environment variables, it owns the CLI surface, and it hands every lower layer a resolved configuration object rather than a place to look one up. That arrangement is what keeps Layer Purity checkable by a single grep, and it is the reason a new user-facing switch belongs here even when the behaviour it controls lives three layers down.

The switch this delta adds is the choice between reporting the package an APK declares and electing one heuristically. The decision is per-run and per-corpus: the same jar, run over a set of single-module apps and over a set of Godot games, wants different answers. `rv-experiment` resolves it once — from the CLI flag, else the environment, else the default — and passes the resolved boolean into every `App` it constructs. Nothing below reads the environment to find out.

`rv-static-analysis` can be invoked standalone, outside any experiment, and constructs `App` itself. It is an entry point in its own right, not an intermediate layer, so it carries the same flag *and* resolves the same environment variable under the same precedence. The rule this preserves is not "only `rv-experiment` may call `os.environ`" but "no layer between an entry point and `App` may": an operator who exports `RV_PACKAGE_DETECTOR` in a shell or a container gets the same behaviour from either command, without having to remember which one honours it. A standalone invocation with neither flag nor variable uses the default, exactly as an experiment does.

What stays closed is everything below. `rv-platform`, `rv-instrumentation-*` and `rv-android-core`'s domain layer receive the resolved boolean by value and read nothing — `rv-experiment` copies it into `PlatformConfig` alongside the configuration it already builds there, and `App` receives it as a constructor argument.

## Data Contracts

### Input
- `package_detector: bool` — user input via the `--package-detector` / `--no-package-detector` CLI flag or the `RV_PACKAGE_DETECTOR` environment variable, on either entry point. Default `False`.

### Output
- `ExperimentConfig.package_detector: bool` — the resolved value, forwarded to every `App` construction performed by the experiment workflow and by the sub-module configurations it builds.
- `PlatformConfig.package_detector: bool` — the same value, carried into the execution layer so that the `App` objects built during task generation are built under the run's policy.

### Side-Effects
- None beyond configuration propagation.

### Error
- The command MUST abort before any experiment setup or APK analysis if the environment variable holds a value that is neither truthy nor falsy under the project's parsing convention, rather than silently choosing a mode. This applies to both entry points.

## Invariants

- **INV-EXP-34**: `RV_PACKAGE_DETECTOR` MUST be read only at an entry point — `modules/rv-experiment/` and the `rv-static-analysis` command's own `__main__` — and only through the `ENV_PACKAGE_DETECTOR` constant of the core registry; no string literal `"RV_PACKAGE_DETECTOR"` MUST appear at a read site. No module between an entry point and `App` MUST read it: `rv-platform`, `rv-instrumentation-*` and `rv-android-core` MUST receive the resolved boolean by value, and `App` MUST receive it as a constructor argument. Precedence MUST be CLI flag > environment variable > default (INV-EXP-32) at each entry point independently, and the default MUST be `False` — the package declared in the manifest.

## MODIFIED Requirements

### Requirement: Layer-Purity Audit for Environment Reads (NFR01, NFR03)

An **entry point** is the command the user actually invoked: `modules/rv-experiment/`, and a module's own standalone `__main__` when that module can be run on its own and builds its own configuration. Entry points are the only places under `modules/` that read user-facing `RV_*` environment variables, and they read them through `ENV_*` constants. Everything between an entry point and the domain model receives configuration by value: L2 plugins (`rv-tools/builtin/`, `aperv-tool`, `rvagent-tool`), L3 modules (`rv-instrumentation*`), L4 (`rv-platform`) and the domain layer of `rv-android-core` read nothing.

The rule is stated this way because the property being protected is that no *intermediate* layer can acquire a second, invisible source for a decision, and a standalone command is not an intermediate layer — a `rv-static-analysis` invocation is a run, so an operator who exported a variable in a shell or a container must get the same behaviour whichever command they invoke.

Any file inside `modules/rv-experiment/` qualifies as an entry point, and today two of them read: `config.py` (`RV_SA_TIMEOUT`, `RV_JVM_MEMORY`, `RV_PACKAGE_DETECTOR`, `RVSEC_HOME`) and `__main__.py` (`RV_HUMANOID_URL`). Outside `rv-experiment`, the only permitted reader is a standalone command's own `__main__`, and the only one that exercises this today is `modules/rv-static-analysis/src/rv_static_analysis/__main__.py` for `RV_PACKAGE_DETECTOR`. A per-variable reader set MAY be narrower than this rule allows — `RV_PACKAGE_DETECTOR` pins its own to exactly those two files (INV-EXP-34) — but MUST NOT be wider.

Reads of the legacy non-`RV_*` workspace paths (`RVSEC_HOME`, `ANDROID_HOME`, `TOOLS_DIR`) through their `ENV_*` constants are outside this rule and occur in several modules, because they locate the installation rather than parameterize the experiment. They are governed by the literal-vs-constant rule below, not by the entry-point rule.

The CI lint MUST verify the mechanical half of this by running a combined grep covering all read forms (`os\.environ\.get`, `os\.environ\[`, `os\.getenv`, `dict\(os\.environ`, `os\.environ\.copy`) over `modules/`. String-literal reads MUST occur nowhere; the wholesale forms `dict(os.environ)` and `os.environ.copy()` MUST occur only inside `modules/rv-experiment/`; and the L1 cross-layer infrastructure family keeps its literal exception in `modules/rv-android-core/util/validation/config.py` (the three `RV_PYDANTIC*` toggles), `util/jar_resolver.py` and `util/android/android.py` (the legacy SDK paths `RVSEC_HOME` / `ANDROID_HOME` / `TOOLS_DIR` and the three device timeout budgets). That allow-list MUST NOT grow.

#### Scenario: Lint rejects new env read in lower layer

- **WHEN** a developer adds `os.environ.get(ENV_TOOLS)` in `modules/rv-platform/src/rv_platform/...`
- **THEN** the CI lint MUST fail naming the offending file and line
- **AND** the message MUST point the developer at the experiment delta spec for the Layer Purity rule

#### Scenario: Cross-layer infra family is permitted

- **WHEN** `modules/rv-android-core/src/rv_android_core/util/validation/config.py` reads `RV_PYDANTIC`, `RV_PYDANTIC_STRICT`, or `RV_PYDANTIC_LOG`
- **THEN** the CI lint MUST recognize all three as authorized L1 cross-layer infra reads (they control validation behavior across every module)
- **AND** MUST NOT flag any of them
- **AND** the lint MUST also accept `RVSEC_HOME` and `ANDROID_HOME` reads in `rv-android-core` (legacy SDK paths)

#### Scenario: A standalone command resolves its own variable

- **WHEN** `modules/rv-static-analysis/src/rv_static_analysis/__main__.py` reads `RV_PACKAGE_DETECTOR` through the `ENV_PACKAGE_DETECTOR` constant, before constructing any `App`
- **THEN** the read MUST be authorized, because the file is the entry point of a command a user can invoke on its own
- **AND** no file in `rv-platform`, `rv-instrumentation-*`, or the domain layer of `rv-android-core` MUST perform an equivalent read
- **AND** the set of files reading `RV_PACKAGE_DETECTOR` MUST remain exactly `rv_experiment/config.py` and `rv_static_analysis/__main__.py`

## ADDED Requirements

### Requirement: Package Detector Opt-In CLI Flag (FR15, NFR05)

The `rv-experiment run` command MUST expose the negatable boolean pair `--package-detector` / `--no-package-detector`. The resolved value MUST set `ExperimentConfig.package_detector`, which the experiment workflow MUST forward to every `App` it constructs, to the sub-module configurations that construct their own, and to `PlatformConfig` so that task generation constructs its `App` objects under the same policy.

An absent flag MUST be distinguishable from an explicitly negative one: with the flag absent the value falls through to `RV_PACKAGE_DETECTOR`, and with `--no-package-detector` given the resolved value MUST be `False` even when the variable is truthy. When neither the flag nor the variable is provided, the resolved value MUST be `False`, meaning `App.code_package` reports the package declared in the APK manifest. The environment variable MUST be parsed with the project's existing truthiness convention — `"true"`, `"1"`, `"yes"`, `"on"`, case-insensitive — matching INV-CORE-12.

The flag controls provenance, not normalization: enabling it runs `PackageDetector` as specified in INV-ANA-14, and disabling it reports the declared applicationId verbatim. Neither mode applies any rewriting of the identifier, because rules such as build-type suffix stripping are properties of a particular corpus and belong to whoever curates it.

`rv-static-analysis` MUST expose the same negatable pair on its own command line and MUST resolve `RV_PACKAGE_DETECTOR` itself under the same precedence, because it constructs `App` when invoked standalone and is therefore an entry point rather than an intermediate layer. Both entry points MUST parse the environment value through one shared helper, so that the two commands cannot diverge on what a given string means.

#### Scenario: Default reports the declared package

- **WHEN** the user runs `uv run rv-experiment run ...` with neither `--package-detector` nor `RV_PACKAGE_DETECTOR` set
- **THEN** `ExperimentConfig.package_detector` MUST be `False`
- **AND** every `App` constructed by the run MUST report `code_package == package_name`
- **AND** `PackageDetector` MUST NOT be invoked at any point in the run

#### Scenario: Environment variable enables the detector

- **WHEN** the shell has `RV_PACKAGE_DETECTOR=true` exported
- **AND** the user runs `uv run rv-experiment run ...` without the flag
- **THEN** `ExperimentConfig.package_detector` MUST be `True`
- **AND** each `App` MUST report `code_package_source == "detector"`

#### Scenario: CLI flag overrides the environment variable

- **WHEN** the shell has `RV_PACKAGE_DETECTOR=true` exported
- **AND** the user runs `uv run rv-experiment run --package-detector ...`
- **THEN** the resolved value MUST be `True` — the flag and the variable agree, and the flag is the authority
- **AND** when the shell has `RV_PACKAGE_DETECTOR=true` and the user runs `uv run rv-experiment run --no-package-detector ...`, the resolved value MUST be `False`

#### Scenario: The resolved value reaches task generation

- **WHEN** an experiment resolves `package_detector` to `True`
- **THEN** the `PlatformConfig` built by `ExecutionController` MUST carry `package_detector == True`
- **AND** every `App` constructed during task generation MUST report `code_package_source == "detector"`
- **AND** `rv-platform` MUST NOT read `RV_PACKAGE_DETECTOR` to obtain it

#### Scenario: Standalone static analysis honours both the flag and the variable

- **WHEN** the user runs `uv run rv-static-analysis --apk <path> --package-detector`
- **THEN** the `App` it constructs MUST report `code_package_source == "detector"`

- **WHEN** the shell has `RV_PACKAGE_DETECTOR=true` exported and the user runs `uv run rv-static-analysis --apk <path>` with no flag
- **THEN** the resolved value MUST be `True`, because a standalone invocation is a run and resolves the variable itself

- **WHEN** the shell has `RV_PACKAGE_DETECTOR=true` exported and the user runs `uv run rv-static-analysis --apk <path> --no-package-detector`
- **THEN** the resolved value MUST be `False`

- **WHEN** the shell has `RV_PACKAGE_DETECTOR=maybe` exported and the user runs `uv run rv-static-analysis --apk <path>` with no flag
- **THEN** the command MUST exit nonzero with a message naming the variable, before constructing any `App`

#### Scenario: The read stays at the entry points and goes through the registry

- **WHEN** `scripts/check_env_vars_drift.py` runs over the implemented change
- **THEN** it MUST report zero violations
- **AND** every read of `RV_PACKAGE_DETECTOR` MUST go through the `ENV_PACKAGE_DETECTOR` constant, with no string literal at any read site
- **AND** no read MUST exist in `rv-platform`, in `rv-instrumentation-*`, or anywhere in `rv-android-core` — `domain/app.py` included (INV-CORE-55)

### Requirement: Package Detector Variable in the Environment Registry (NFR01, NFR05)

`ENV_PACKAGE_DETECTOR = "RV_PACKAGE_DETECTOR"` MUST exist in `modules/rv-android-core/src/rv_android_core/constants.py`, MUST be documented in `.env.example` and in the README's environment-variable table, and MUST be referenced through the constant at its single read site in `rv-experiment`. No string literal `"RV_PACKAGE_DETECTOR"` MUST appear at a read site.

The Docker entry point requires no edit: `validate_env_vars.sh` reconciles the container environment against the registry at runtime, so a variable present in the registry is accepted by construction.

#### Scenario: Registry, documentation and lint agree

- **WHEN** `uv run python scripts/check_env_vars_drift.py` runs after the constant, the `.env.example` entry and the README row are in place
- **THEN** it MUST report zero violations across all three of its cross-checks
- **AND** `uv run pytest modules/rv-android-core/tests/test_constants_registry.py tests/lint/test_env_vars_drift.py` MUST pass

#### Scenario: Container accepts the variable without an entry-point change

- **WHEN** a container is started with `RV_PACKAGE_DETECTOR=true` in its environment
- **THEN** `validate_env_vars.sh` MUST accept the name because it is in the registry
- **AND** the entry point MUST NOT exit 64
