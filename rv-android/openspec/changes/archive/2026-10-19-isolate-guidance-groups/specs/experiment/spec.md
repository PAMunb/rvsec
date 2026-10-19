## Purpose

This delta makes `APERV_LLM_BASE_URL` work. The `aperv-tool` docs and spec promise that the variable redirects the
LLM cells to another endpoint, and no code reads it: gh55 removed the read from `ApeRVTool.configure()` for layer
purity (INV-TOOL-20) and announced an entry-point read that was never written. The read lands where
`RV_HUMANOID_URL` is already read, in `rv-experiment/__main__.py`, and the value reaches the tool through
`ToolConfig.parameters`, the only sanctioned channel (platform "Tool-Configuration Channel via
ToolConfig.parameters"). No compose file, script or recorded campaign sets the variable, so no recorded run
changes.

## Invariants

These add to `openspec/specs/experiment/spec.md` § Invariants; the invariant section is synchronized by hand at
archive.

- **INV-EXP-41** (new): `APERV_LLM_BASE_URL` MUST be read only in `modules/rv-experiment/src/rv_experiment/__main__.py`,
  through the `ENV_APERV_LLM_BASE_URL` constant of the core registry, with no string literal at the read site. When
  it is set to a non-empty value, every parsed `ToolConfig` named `aperv` whose variant definition in `ToolRegistry`
  carries `overrides.llm_url`, and whose `parameters` carry no `llm_url`, MUST receive `parameters["llm_url"]` equal
  to the value. A `ToolConfig` whose `parameters` already carry `llm_url` (a DSL `@llm_url`) MUST keep it: DSL >
  variable > the cell's default. A `ToolConfig` whose variant carries no `llm_url` MUST NOT receive one. When the
  variable is unset or empty, nothing MUST be injected. No module between the entry point and `ApeRVTool.configure()`
  MUST read it. The core registry's `ENV_*` name rule (INV-CORE-30, `rv-android-core/tests/test_constants_registry.py`)
  MUST admit `APERV_LLM_BASE_URL` as its one user-facing name outside `RV_*`, beside the three installation paths,
  and no other.

## MODIFIED Requirements

### Requirement: Layer-Purity Audit for Environment Reads (NFR01, NFR03)

An **entry point** is the command the user actually invoked: `modules/rv-experiment/`, and a module's own standalone `__main__` when that module can be run on its own and builds its own configuration. Entry points are the only places under `modules/` that read user-facing `RV_*` environment variables, and they read them through `ENV_*` constants. Everything between an entry point and the domain model receives configuration by value: L2 plugins (`rv-tools/builtin/`, `aperv-tool`, `rvagent-tool`), L3 modules (`rv-instrumentation*`), L4 (`rv-platform`) and the domain layer of `rv-android-core` read nothing.

The rule is stated this way because the property being protected is that no *intermediate* layer can acquire a second, invisible source for a decision, and a standalone command is not an intermediate layer — a `rv-static-analysis` invocation is a run, so an operator who exported a variable in a shell or a container must get the same behaviour whichever command they invoke.

Any file inside `modules/rv-experiment/` qualifies as an entry point, and today two of them read: `config.py` (`RV_SA_TIMEOUT`, `RV_JVM_MEMORY`, `RV_PACKAGE_DETECTOR`, `RVSEC_HOME`) and `__main__.py` (`RV_HUMANOID_URL`, `APERV_LLM_BASE_URL`). `APERV_LLM_BASE_URL` is the one user-facing variable outside the `RV_*` prefix that this rule admits: the `aperv-tool` documentation has advertised that name, and the author kept it (INV-EXP-41). It is read only in `__main__.py`, through its `ENV_*` constant. Outside `rv-experiment`, the only permitted reader is a standalone command's own `__main__`, and the only one that exercises this today is `modules/rv-static-analysis/src/rv_static_analysis/__main__.py` for `RV_PACKAGE_DETECTOR`. A per-variable reader set MAY be narrower than this rule allows — `RV_PACKAGE_DETECTOR` pins its own to exactly those two files (INV-EXP-34) — but MUST NOT be wider.

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

### Requirement: aperv LLM URL Resolved at the Entry Point (FR19, NFR05)

`rv-experiment` SHALL resolve `APERV_LLM_BASE_URL` once, after the tool specifications are parsed into
`ToolConfig`s and beside the `RV_HUMANOID_URL` resolution, and SHALL inject it into the `aperv` cells that mount
the LLM group (INV-EXP-41). Which cells those are is read from the variant definitions in `ToolRegistry`, not from
a list of names in `rv-experiment`: a cell is an LLM cell when its definition carries `overrides.llm_url`
(`aperv` INV-APV-38). The tool's own DSL fold moves the injected top-level `llm_url` into `overrides`, so the
tool reads nothing new.

The order of precedence follows INV-EXP-32 with the tool DSL in the CLI flag's place, because `@llm_url` is the
operator's explicit word for one tool entry, while the variable is a deployment default for all of them. The cells
without the LLM group never receive the URL: it would write an `ape.llmUrl` line for a group the cell does not
mount.

#### Scenario: The variable reaches the LLM cells
- **WHEN** `APERV_LLM_BASE_URL=http://192.168.1.100:30000/v1` is set and `rv-experiment run --tools aperv:as_llm,aperv:as_mop_llm` parses its tools
- **THEN** both `ToolConfig`s SHALL carry `parameters["llm_url"] == "http://192.168.1.100:30000/v1"`
- **AND** the `ape.properties` of each run SHALL carry `ape.llmUrl=http://192.168.1.100:30000/v1`

#### Scenario: Cells without the LLM group are left alone
- **WHEN** the same variable is set and `--tools aperv:base,aperv:as_mop` is parsed
- **THEN** neither `ToolConfig` SHALL carry `llm_url` in its `parameters`

#### Scenario: The DSL value wins over the variable
- **WHEN** the variable is set to `http://192.168.1.100:30000/v1` and `--tools aperv:as_llm@llm_url=http://sglang:30000/v1` is parsed
- **THEN** the `ToolConfig` SHALL keep `parameters["llm_url"] == "http://sglang:30000/v1"`

#### Scenario: Unset variable keeps the cell default
- **WHEN** `APERV_LLM_BASE_URL` is unset or empty and `--tools aperv:as_llm` is parsed
- **THEN** the `ToolConfig`'s `parameters` SHALL carry no `llm_url`
- **AND** the run SHALL use the cell's default `http://10.0.2.2:30000/v1`

#### Scenario: The reader set is pinned
- **WHEN** `modules/` is searched for reads of `ENV_APERV_LLM_BASE_URL` or the literal `"APERV_LLM_BASE_URL"`
- **THEN** the only read SHALL be in `modules/rv-experiment/src/rv_experiment/__main__.py`, through the constant
- **AND** `modules/aperv-tool/src/` SHALL contain no read of it
