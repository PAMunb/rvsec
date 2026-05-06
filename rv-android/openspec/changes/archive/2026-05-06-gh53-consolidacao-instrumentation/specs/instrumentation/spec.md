# Spec Delta — instrumentation

GitHub Issue: #53

## Purpose

This delta consolidates the post-merge state of `gh50-improve-instrumentation`, `gh51-gator-soot-upgrade`, and `gh52-instr-dexlib2` into a canonical Docker image rebuild path while restructuring the instrumentation domain into a four-module layout that resolves a circular dependency that would arise if a single parent module owned both the abstractions and the factory dispatching to variant implementations. After Phase 4 (Implement) of this change:

1. A new minimal module `rv-instrumentation-core` owns pure abstractions: types `InstrumentationResults` and `InstrumentationError`, and the abstract base class `Instrumenter`. It declares only `pydantic` and `rv-android-core` as runtime dependencies — it MUST NOT depend on any concrete variant implementation.
2. The module `rv-instrumentation` becomes the **canonical parent** holding the public factory `get_instrumenter(variant, config) -> Instrumenter` and the shared signing keystore `assets/keystore.jks`. It re-exports the public surface from `rv-instrumentation-core` so that consumers continue to use `from rv_instrumentation import Instrumenter, InstrumentationResults, get_instrumenter` exactly as they would for any single-module domain. It declares dependencies on `rv-instrumentation-core` and on both variant implementations (`rv-instrumentation-ajc`, `rv-instrumentation-dexlib2`).
3. The AspectJ implementation is renamed atomically to `rv-instrumentation-ajc` (Python package `rv_instrumentation_ajc`, class `AjcInstrumentation(Instrumenter)`, config class `AjcInstrumentationConfig`). The AspectJ-specific asset `weaving_excludes.yaml` moves to this module's `assets/`. It depends on `rv-instrumentation-core` (for the ABC and types) and MUST NOT depend on the parent `rv-instrumentation` (this would create a cycle).
4. `rv-instrumentation-dexlib2` keeps its name and class name; `DexlibInstrumentation` MUST inherit from `Instrumenter`. Type imports come from `rv_instrumentation_core` (not from `rv_instrumentation.config`, which no longer hosts these types). It depends on `rv-instrumentation-core` and MUST NOT depend on the parent `rv-instrumentation`.
5. `rv-experiment` selects between variants exclusively via `get_instrumenter(variant, config)` imported from `rv_instrumentation` (parent). The inline `if/else` in `PreProcessor._instrument_apks()` is replaced.
6. The Docker image `phtcosta/rvandroid:0.8.0` rebuilt from `modules` carries both variants behind the variant flag — the temporary `phtcosta/rvandroid:0.8.0-dexlib2` tag and the layered `docker/rvandroid_dexlib2/Dockerfile` are removed.

The four-module split is required to keep dependency declarations honest: each module's `pyproject.toml` lists exactly what it imports, with no implicit lazy-import-without-declared-dep tricks. The parent `rv-instrumentation` declares deps on the implementations because its factory imports them; the implementations do NOT declare deps back on the parent, breaking the cycle. The dependency graph is acyclic with arrows pointing only toward `rv-android-core` at the base. ADR `ADR-INSTRUMENTER-ABC.md` (in this change directory) records the architectural choice and the alternatives considered.

This delta does NOT redefine requirements introduced by gh50, gh51, or gh52. It adds requirements about the new four-module canonical layout and amends the wording of the variant-selection requirement (originally INV-INS-55 in gh52's delta) to point at the new locations. Reconciliation with `openspec/specs/instrumentation/spec.md` is deferred to the synchronization step performed when gh50, gh51, gh52, and gh53 are all archived together.

## Data Contracts

### Canonical import paths

- `from rv_instrumentation import Instrumenter` — abstract base class. Re-exported by parent from `rv_instrumentation_core`.
- `from rv_instrumentation import InstrumentationResults` — Pydantic model. Re-exported from `rv_instrumentation_core`.
- `from rv_instrumentation import InstrumentationError` — Pydantic model. Re-exported from `rv_instrumentation_core`.
- `from rv_instrumentation import get_instrumenter` — public factory. Lives in `rv_instrumentation.factory`.
- `from rv_instrumentation_core import Instrumenter, InstrumentationResults, InstrumentationError` — direct import from the abstractions module. Equivalent to importing from the parent re-exports; consumers can use either path.
- `from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation` — concrete ajc implementation (renamed from `RVInstrumentation`).
- `from rv_instrumentation_ajc.config import AjcInstrumentationConfig` — ajc-specific config (renamed from `RVInstrumentationConfig`).
- `from rv_instrumentation_dexlib2 import DexlibInstrumentation` — concrete dexlib2 implementation (existing).

### Removed import paths

- `from rv_instrumentation.config import InstrumentationResults` — REMOVED (P3).
- `from rv_instrumentation.config import InstrumentationError` — REMOVED (P3).
- `from rv_instrumentation.config import RVInstrumentationConfig` — REMOVED (renamed; migrate to `from rv_instrumentation_ajc.config import AjcInstrumentationConfig`).
- `from rv_instrumentation import RVInstrumentation` — REMOVED (renamed; migrate to `get_instrumenter("ajc", config)` or import `AjcInstrumentation` directly from `rv_instrumentation_ajc.ajc_instrumentation`).

### Side-Effects

None at the abstractions module level. Tests in `rv-instrumentation-core/tests/` MUST cover Pydantic round-trip serialization and ABC contract enforcement. Tests in `rv-instrumentation/tests/` MUST cover factory dispatch (valid variants return the right concrete class with `isinstance(returned, Instrumenter)`; invalid variant raises `ValueError`; selecting one variant does NOT import the other module per `sys.modules` snapshot). No filesystem writes, no subprocess invocations.

### Error

- `InstrumentationError` — preserved exactly as it exists today, just relocated to `rv_instrumentation_core/results.py`.
- `ValueError` raised by `get_instrumenter(variant, config)` when `variant` is unknown. Message MUST list the valid variants.
- `TypeError` raised by Python when a subclass of `Instrumenter` lacking `instrument_apks` is instantiated (standard ABC enforcement).

## Invariants

- **INV-INS-33**: The Pydantic models `InstrumentationResults` and `InstrumentationError` MUST live in `rv_instrumentation_core` (specifically in `rv_instrumentation_core/results.py`) and MUST NOT be redefined or aliased in `rv_instrumentation` (parent), `rv_instrumentation_ajc`, or `rv_instrumentation_dexlib2`. The parent `rv_instrumentation` MAY re-export the symbols from `rv_instrumentation_core` via `__init__.py` for API convenience. Validation: `grep -rnE '^class (InstrumentationResults|InstrumentationError)\b' modules/rv-instrumentation*/src/` returns hits ONLY under `modules/rv-instrumentation-core/src/`.
- **INV-INS-34**: `rv-instrumentation-ajc` and `rv-instrumentation-dexlib2` MUST depend ONLY on `rv-instrumentation-core` for shared abstractions and types. Neither MUST depend on the parent `rv-instrumentation` (such a dependency would form a cycle since the parent declares deps on the variant implementations to enable factory dispatch). Validation: `grep -rnE 'from rv_instrumentation[^_]|^import rv_instrumentation[^_]' modules/rv-instrumentation-dexlib2/src/ modules/rv-instrumentation-ajc/src/` returns 0 hits — neither implementation imports from the parent module path; they import from `rv_instrumentation_core` exclusively.
- **INV-INS-35**: The `Instrumenter` abstract base class in `rv_instrumentation_core/instrumenter.py` MUST declare `instrument_apks(apks_dir, results_dir, force_instrumentation: bool = False, apk_paths: Optional[List[str]] = None) -> InstrumentationResults` as the SOLE `@abstractmethod`. Variant-specific helpers (`prepare_instrumentation`, `instrument`, `check_if_instrumented`, `clear`, `create_temp_directories`) MUST NOT appear in the ABC. Both `AjcInstrumentation` and `DexlibInstrumentation` MUST inherit from `Instrumenter`. Validation: `tests/test_instrumenter.py` in `rv-instrumentation-core` asserts that a synthetic subclass missing `instrument_apks` raises `TypeError` on instantiation.
- **INV-INS-36**: Variant dispatch across `rv-android` MUST go through the public factory `rv_instrumentation.factory.get_instrumenter(variant, config) -> Instrumenter`. No private dispatch helper, parallel factory, or inlined `if/else` over variants MUST exist in any module other than `rv_instrumentation.factory`. Validation: `grep -rnE 'def get_instrumenter|def make_instrumenter|def _select_instrumenter' modules/ scripts/` returns hits ONLY under `modules/rv-instrumentation/src/rv_instrumentation/factory.py`.
- **INV-INS-37**: The Docker image `phtcosta/rvandroid:0.8.0` rebuilt from branch `modules` after this change is applied MUST carry `rv-instrumentation-core`, `rv-instrumentation` (parent), `rv-instrumentation-ajc`, and `rv-instrumentation-dexlib2` modules and the `instr-cli.jar` (auto-copied by Maven per gh52 Design D9). The image MUST resolve `RV_INSTRUMENTATION_VARIANT=ajc` and `RV_INSTRUMENTATION_VARIANT=dexlib2` at runtime without rebuild. Validation: AC-IMG-01 (rebuild from clean clone exits 0; `instr-cli.jar` build-time gate passes) AND AC-IMG-02 (smoke 1-APK por variant — `RV_INSTRUMENTATION_VARIANT=ajc` produz `instrument_errors.json` com `variant: "ajc"`; `=dexlib2` produz `variant: "dexlib2"`); both ACs defined in `design.md` §D7.
- **INV-INS-38**: The temporary Docker artifact `docker/rvandroid_dexlib2/Dockerfile` and the parent directory MUST be removed. Tags `phtcosta/rvandroid:0.8.0-dexlib2` and `phtcosta/rvandroid:0.8.0-dexlib2-base` MUST NOT be referenced by any compose template or build script after this change. Validation: `find docker -name 'rvandroid_dexlib2*'` returns empty; `grep -rn '0\.8\.0-dexlib2' docker/ scripts/ docs/` returns 0 hits in functional code.
- **INV-INS-39**: The signing keystore `keystore.jks` is a SHARED asset (used by `apksigner` in dexlib2 and `jarsigner` in ajc). It MUST live in `modules/rv-instrumentation/assets/` (parent canonical), NOT in `rv-instrumentation-core` (which holds no assets), NOT in either variant module. The path that `rv-experiment/config.py:669` resolves at runtime — `Path(rvsec_root) / "rv-android" / "modules" / "rv-instrumentation" / "assets" / "keystore.jks"` — MUST remain unchanged after this change. Validation: `[ -f modules/rv-instrumentation/assets/keystore.jks ]`; AC-AST-06 (`grep -n 'rv-instrumentation/assets/keystore' modules/rv-experiment/src/rv_experiment/config.py` returns 1+ hit).
- **INV-INS-40**: The AspectJ weaving exclusion file `weaving_excludes.yaml` MUST live in `modules/rv-instrumentation-ajc/assets/` (ajc-specific asset). Consumers (specifically `scripts/jca557_quarantine_impact.py`) MUST reference the new path. The old path `modules/rv-instrumentation/assets/weaving_excludes.yaml` MUST NOT exist after this change. Validation: `[ -f modules/rv-instrumentation-ajc/assets/weaving_excludes.yaml ] && [ ! -f modules/rv-instrumentation/assets/weaving_excludes.yaml ]`.
- **INV-INS-41**: The dependency graph across the four `rv-instrumentation*` modules MUST be acyclic with arrows pointing only toward `rv-instrumentation-core` at the base. Specifically: `rv-instrumentation-core` MUST NOT declare any dep on `rv-instrumentation`, `rv-instrumentation-ajc`, or `rv-instrumentation-dexlib2` in its `pyproject.toml`. `rv-instrumentation-ajc` MUST declare dep on `rv-instrumentation-core` and MUST NOT declare dep on `rv-instrumentation` (parent), `rv-instrumentation-dexlib2`. `rv-instrumentation-dexlib2` MUST declare dep on `rv-instrumentation-core` and MUST NOT declare dep on `rv-instrumentation` (parent), `rv-instrumentation-ajc`. The parent `rv-instrumentation` MUST declare deps on `rv-instrumentation-core`, `rv-instrumentation-ajc`, `rv-instrumentation-dexlib2`. Validation: `python -c "import tomllib; ..."` enforces each module's deps post-implementation per AC-WSP-05/06.

## ADDED Requirements

### Requirement: Pure Abstractions Module `rv-instrumentation-core`

The system MUST provide a Python module `rv-instrumentation-core` (under `modules/rv-instrumentation-core/`, package name `rv_instrumentation_core`) that holds the pure abstractions of the instrumentation domain. The module MUST contain ONLY:

- `results.py`: `InstrumentationResults` Pydantic model + `InstrumentationError` Pydantic model (relocated from `rv_instrumentation.config`).
- `instrumenter.py`: abstract base class `Instrumenter` with `instrument_apks` as its sole `@abstractmethod`.
- `__init__.py`: re-exports `InstrumentationResults`, `InstrumentationError`, `Instrumenter`.

The module MUST NOT contain any concrete instrumentation logic, factory function, asset, or shared mutable state. It MUST be a uv workspace member declared in the root `pyproject.toml`. Its only declared runtime dependencies are `pydantic` and `rv-android-core`. It MUST NOT declare a dependency on `rv-instrumentation`, `rv-instrumentation-ajc`, or `rv-instrumentation-dexlib2` (this would be a cycle).

#### Scenario: Direct imports from -core work after migration

- **WHEN** the change is applied and `python -c "from rv_instrumentation_core import Instrumenter, InstrumentationResults, InstrumentationError"` is run
- **THEN** the command MUST exit 0
- **AND** `Instrumenter` MUST be a class with `abc.ABCMeta` as its metaclass
- **AND** `InstrumentationResults` and `InstrumentationError` MUST be `BaseValidatedModel` subclasses

#### Scenario: -core has no dependency on impl modules

- **WHEN** `python -c "import tomllib; deps = tomllib.loads(open('modules/rv-instrumentation-core/pyproject.toml','rb').read().decode())['project']['dependencies']; ..."` is evaluated
- **THEN** the dependency list MUST contain ONLY `pydantic` and `rv-android-core` (allowing `>=` version pins)
- **AND** none of `rv-instrumentation`, `rv-instrumentation-ajc`, `rv-instrumentation-dexlib2` MUST appear

### Requirement: Canonical Parent Module `rv-instrumentation` with Public Factory

The module `rv-instrumentation` MUST serve as the canonical parent for the instrumentation domain. After this change, its `src/rv_instrumentation/` directory MUST contain ONLY:

- `factory.py`: public function `get_instrumenter(variant, config) -> Instrumenter` that dispatches to concrete variant implementations via lazy imports inside each branch (selecting "ajc" does NOT import `rv_instrumentation_dexlib2`; selecting "dexlib2" does NOT import `rv_instrumentation_ajc`). Raises `ValueError` for unknown variants.
- `__init__.py`: re-exports `Instrumenter`, `InstrumentationResults`, `InstrumentationError` from `rv_instrumentation_core`, AND exposes `get_instrumenter`.

The parent's `assets/` directory MUST contain `keystore.jks` (shared by both variants for APK signing). The parent's `pyproject.toml` MUST declare runtime dependencies on `rv-instrumentation-core`, `rv-instrumentation-ajc`, AND `rv-instrumentation-dexlib2` (the factory imports both implementations at runtime, even if lazily).

The parent MUST NOT contain any concrete instrumentation logic, ABC definition, or Pydantic type definition (those live in `-core`).

#### Scenario: Canonical imports via parent re-exports work

- **WHEN** the change is applied and `python -c "from rv_instrumentation import Instrumenter, InstrumentationResults, InstrumentationError, get_instrumenter"` is run
- **THEN** the command MUST exit 0
- **AND** the `Instrumenter` symbol MUST be the same object as imported via `rv_instrumentation_core.Instrumenter` (verifiable via `from rv_instrumentation import Instrumenter as A; from rv_instrumentation_core import Instrumenter as B; assert A is B`)

#### Scenario: Both implementations inherit from Instrumenter

- **WHEN** `AjcInstrumentation` is instantiated with a valid `AjcInstrumentationConfig` and `DexlibInstrumentation` is instantiated with a valid `DexlibInstrumentationConfig`
- **THEN** `isinstance(ajc_instance, Instrumenter)` MUST return `True` (where `Instrumenter` is imported from `rv_instrumentation` OR `rv_instrumentation_core` — same class)
- **AND** `isinstance(dexlib_instance, Instrumenter)` MUST return `True`

### Requirement: Atomic Rename of AspectJ Implementation Module

The system MUST atomically rename the current AspectJ implementation:
- Module directory: `modules/rv-instrumentation/` (impl portion) → `modules/rv-instrumentation-ajc/`
- Python package: `rv_instrumentation` (impl portion) → `rv_instrumentation_ajc`
- Class: `RVInstrumentation` → `AjcInstrumentation`
- Config class: `RVInstrumentationConfig` → `AjcInstrumentationConfig`
- Asset: `assets/weaving_excludes.yaml` (AspectJ-specific) moves with the module to `modules/rv-instrumentation-ajc/assets/`

The rename MUST be atomic per principle P3 — no aliases, no shims, no `# removed` comments, no backward-compatible re-exports. Every consumer MUST be updated in the same change.

The new `rv-instrumentation-ajc` module MUST depend on `rv-instrumentation-core` (for the ABC and types) and on `rv-android-core` (for `BaseValidatedModel`, `ConfigurationError`, etc.). It MUST NOT depend on `rv-instrumentation` (parent) — this would form a cycle. The class `AjcInstrumentation` MUST inherit from `Instrumenter` (imported from `rv_instrumentation_core`) and override `instrument_apks` with behavior unchanged from the legacy `RVInstrumentation.instrument_apks`.

#### Scenario: Renamed module is importable after migration

- **WHEN** the change is applied and `python -c "from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation; from rv_instrumentation_ajc.config import AjcInstrumentationConfig"` is run
- **THEN** the command MUST exit 0

#### Scenario: No legacy class names remain

- **WHEN** `grep -rnE 'from rv_instrumentation import RVInstrumentation|RVInstrumentation\(' modules/ scripts/ tests/` is run after the change
- **THEN** the command MUST return 0 hits

#### Scenario: -ajc does not depend on parent or sibling

- **WHEN** `tomllib`-parsed dependencies of `modules/rv-instrumentation-ajc/pyproject.toml` are inspected
- **THEN** the dependency list MUST NOT contain `rv-instrumentation` (parent)
- **AND** MUST NOT contain `rv-instrumentation-dexlib2` (sibling)
- **AND** MUST contain `rv-instrumentation-core` and `rv-android-core`

### Requirement: dexlib2 Module Updated to Use -core for Abstractions

`rv-instrumentation-dexlib2` MUST be updated such that:
- All imports of `InstrumentationResults` and `InstrumentationError` come from `rv_instrumentation_core` (not from `rv_instrumentation.config`).
- `class DexlibInstrumentation` MUST inherit from `Instrumenter` (imported from `rv_instrumentation_core`).
- `pyproject.toml` MUST replace its current dep on `rv-instrumentation` (which the impl was using as a workaround for shared types) with a dep on `rv-instrumentation-core`. The dep on `rv-instrumentation` (parent) MUST NOT be added — that would form a cycle.

#### Scenario: dexlib2 imports come from -core

- **WHEN** `grep -rnE 'from rv_instrumentation\.config|^import rv_instrumentation\.config' modules/rv-instrumentation-dexlib2/src/` is run
- **THEN** the command MUST return 0 hits
- **AND** `grep -rnE 'from rv_instrumentation_core' modules/rv-instrumentation-dexlib2/src/` MUST return 1+ hits

#### Scenario: dexlib2 does not depend on parent or sibling

- **WHEN** `tomllib`-parsed dependencies of `modules/rv-instrumentation-dexlib2/pyproject.toml` are inspected
- **THEN** the dependency list MUST NOT contain `rv-instrumentation` (parent)
- **AND** MUST NOT contain `rv-instrumentation-ajc` (sibling)
- **AND** MUST contain `rv-instrumentation-core`

### Requirement: Public Factory Dispatch

`rv-experiment` MUST replace the inline `if/else` dispatch in `PreProcessor._instrument_apks()` (currently at `pre_processor.py:188-207`) with a call to `rv_instrumentation.get_instrumenter(variant, config)`. The factory call MUST be the unique site of variant selection across the entire `rv-android` codebase. No parallel dispatch helper, no private `_select_instrumenter` (or similar), no inlined `if/else` over variants MUST appear in any module other than `rv_instrumentation.factory`.

The factory MUST use lazy imports: importing the dexlib2 concrete class MUST happen only when `variant == "dexlib2"`, and the ajc concrete class MUST be imported only when `variant == "ajc"`. This prevents environments where one variant's transitive dependencies are unavailable from breaking the other variant.

#### Scenario: Factory dispatches to dexlib2 when variant is "dexlib2"

- **WHEN** `get_instrumenter("dexlib2", dexlib_config)` is called with a valid `DexlibInstrumentationConfig`
- **THEN** the returned instance MUST be a `DexlibInstrumentation`
- **AND** `isinstance(returned, Instrumenter)` MUST hold
- **AND** `rv_instrumentation_ajc` MUST NOT have been imported by this call (verifiable via `sys.modules` snapshot before/after)

#### Scenario: Factory dispatches to ajc when variant is "ajc"

- **WHEN** `get_instrumenter("ajc", ajc_config)` is called with a valid `AjcInstrumentationConfig`
- **THEN** the returned instance MUST be an `AjcInstrumentation`
- **AND** `isinstance(returned, Instrumenter)` MUST hold
- **AND** `rv_instrumentation_dexlib2` MUST NOT have been imported by this call

#### Scenario: Factory rejects unknown variant

- **WHEN** `get_instrumenter("lspatch", config)` is called and `lspatch` is not a registered variant
- **THEN** the factory MUST raise `ValueError`
- **AND** the exception message MUST list the valid variants (`ajc`, `dexlib2`)

### Requirement: Canonical Docker Image Rebuild

The Docker image `phtcosta/rvandroid:0.8.0` MUST be rebuildable from branch `modules` (after this change is applied) and the resulting image MUST carry `rv-instrumentation-core`, `rv-instrumentation` (parent), `rv-instrumentation-ajc`, and `rv-instrumentation-dexlib2`. The image MUST resolve `RV_INSTRUMENTATION_VARIANT` at container runtime without rebuild. The temporary build path `docker/rvandroid_dexlib2/Dockerfile` and the tag `phtcosta/rvandroid:0.8.0-dexlib2` MUST be removed.

`docker/rvandroid/Dockerfile` MUST include a build-time gate verifying that the `instr-cli.jar` was auto-copied by Maven (Design D9 from gh52); the gate MUST fail the build with a clear message if the jar is missing. The expected path inside the image is `/opt/rvsec/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` (matching the existing layout: base image uses `WORKDIR /opt/rvsec` with `git clone ... .`). The `ARG RVSEC_BRANCH=modules` MUST be preserved per Phase 0 §4.3.

#### Scenario: Image rebuild succeeds and supports both variants

- **WHEN** `docker build -t phtcosta/rvandroid:0.8.0 docker/rvandroid/` is run from a clean clone of branch `modules` after this change is applied
- **THEN** the build MUST exit 0
- **AND** the resulting image MUST contain `/opt/rvsec/rv-android/modules/rv-instrumentation-dexlib2/lib/instr-cli.jar`
- **AND** running `docker run --rm phtcosta/rvandroid:0.8.0 -e RV_INSTRUMENTATION_VARIANT=ajc rv-experiment run --tools monkey --apks-dir /apks --skip-monitors --skip-static` over a 1-APK fixture MUST exit 0 with `instrument_errors.json` showing `variant: "ajc"`
- **AND** the same invocation with `RV_INSTRUMENTATION_VARIANT=dexlib2` MUST exit 0 with `instrument_errors.json` showing `variant: "dexlib2"`

#### Scenario: Build fails when instr-cli.jar is missing

- **WHEN** `docker build` is run on a workspace where `mvn clean install` was not executed
- **THEN** the build MUST fail at the gate step
- **AND** the error message MUST identify the missing jar path and recommend running `mvn clean install` from `rvsec/`

### Requirement: Removal of Temporary Docker Artifacts

The change MUST remove the following artifacts that became redundant once gh52 was merged into `modules`:
- `docker/rvandroid_dexlib2/Dockerfile` (53 lines)
- `docker/rvandroid_dexlib2/` (directory; verified to contain only `Dockerfile`)
- References to `phtcosta/rvandroid:0.8.0-dexlib2` and `phtcosta/rvandroid:0.8.0-dexlib2-base` in any compose template, build script, or active documentation

`docker/docker-compose.dexlib2-validation.template.yml` MUST be rewritten to use `phtcosta/rvandroid:0.8.0` for both services, distinguishing the variants via `RV_INSTRUMENTATION_VARIANT=ajc` and `RV_INSTRUMENTATION_VARIANT=dexlib2`. The two-service paired-comparison structure required by gh52 Phase 5 (Layer-4 validation) MUST be preserved.

The dead-code example comment in `docker/rvandroid/Dockerfile:8-9` referencing `--build-arg RVSEC_BRANCH=gh52-instr-dexlib2` and the `0.8.0-dexlib2-base` tag MUST be removed or replaced with a current-state example (P4).

#### Scenario: Compose template parses and uses unified image

- **WHEN** `docker compose -f docker/docker-compose.dexlib2-validation.template.yml config` is run after the rewrite
- **THEN** the command MUST exit 0
- **AND** the resolved configuration MUST show both services using image `phtcosta/rvandroid:0.8.0`
- **AND** the two services MUST differ on `RV_INSTRUMENTATION_VARIANT` only (`ajc` vs `dexlib2`)

### Requirement: Asset Migration — Shared Keystore in Parent, AspectJ Excludes in -ajc

The signing keystore `keystore.jks` is a SHARED asset (used by `apksigner` in dexlib2 and `jarsigner` in ajc, both pointing at the same path via `rv-experiment/config.py`'s keystore_file setter). It MUST live in `modules/rv-instrumentation/assets/` (parent canonical), NOT in `rv-instrumentation-core` (which holds no assets). The path that `rv-experiment/config.py:669` resolves at runtime — `Path(rvsec_root) / "rv-android" / "modules" / "rv-instrumentation" / "assets" / "keystore.jks"` — MUST remain unchanged after this change.

The AspectJ weaving exclusion file `weaving_excludes.yaml` is AJC-SPECIFIC. It MUST move from `modules/rv-instrumentation/assets/` to `modules/rv-instrumentation-ajc/assets/`. The script `scripts/jca557_quarantine_impact.py` (lines 14 docstring, 44 code) MUST be updated to reference the new path.

#### Scenario: Keystore stays at parent canonical path

- **WHEN** the change is applied and `[ -f modules/rv-instrumentation/assets/keystore.jks ]` is checked
- **THEN** the file MUST exist
- **AND** `grep -n 'rv-instrumentation/assets/keystore.jks' modules/rv-experiment/src/rv_experiment/config.py` MUST return 1+ hit

#### Scenario: weaving_excludes.yaml moves to -ajc module

- **WHEN** the change is applied
- **THEN** `[ -f modules/rv-instrumentation-ajc/assets/weaving_excludes.yaml ]` MUST be true
- **AND** `[ ! -f modules/rv-instrumentation/assets/weaving_excludes.yaml ]` MUST be true
- **AND** `grep -n 'rv-instrumentation/assets/weaving_excludes' scripts/jca557_quarantine_impact.py` MUST return 0 hits
- **AND** `grep -n 'rv-instrumentation-ajc/assets/weaving_excludes' scripts/jca557_quarantine_impact.py` MUST return 1+ hits

### Requirement: AspectJ Crash-Dump Cleanup

The 22 `ajcore.20260421.*.txt` files at the repository root (residue of gh50's JCA-557 validation) MUST be removed and `.gitignore` MUST be updated to ignore the pattern `ajcore.*.txt` going forward.

#### Scenario: Crash dumps removed and pattern ignored

- **WHEN** the change has been applied and `git status` is run from the repo root
- **THEN** no `ajcore.*.txt` file MUST appear as tracked or untracked
- **AND** `.gitignore` MUST contain a line matching `ajcore.*.txt`

## MODIFIED Requirements

### Requirement: Instrumentation Variant Selection (amended from gh52 INV-INS-55)

This delta amends gh52's "Instrumentation Variant Selection" requirement only with respect to the location of the shared types and the dispatch shape. The functional behavior MUST remain identical: default `ajc`, env `RV_INSTRUMENTATION_VARIANT`, CLI flag `--instrumentation-variant`, and the `InstrumentationResults.variant` field MUST all be preserved exactly as defined by gh52.

The amendments below MUST be applied:
- The `InstrumentationResults` and `InstrumentationError` Pydantic models referenced by INV-INS-55 MUST be imported from `rv_instrumentation_core` (or equivalently from `rv_instrumentation` parent re-exports), NOT from `rv_instrumentation.config` (which no longer hosts these types).
- `PreProcessor._instrument_apks()` MUST delegate selection to `rv_instrumentation.get_instrumenter(variant, config)` (public factory imported from the parent) rather than inlining the `if/else`.
- The factory MUST type its return value as `Instrumenter` (ABC from `rv_instrumentation_core`), not as a concrete class union or `Any`.
- Legacy JSONs without the `variant` field MUST deserialize with `variant == "ajc"` via the existing `Field(default="ajc")` mechanism on `InstrumentationResults.variant`. NOTE: gh52 INV-INS-55 textually mandates a `model_validator(mode="before")` for this retrocompat path, but the actual code uses `Field(default="ajc")` instead. This delta carries the existing `Field` mechanism forward unchanged; closing the gh52 spec-vs-code divergence is dívida da gh52 (out of scope here — see design.md §"Dívida herdada gh52 INV-INS-55").

The variant flag, the env variable mapping in `docker/rvandroid/docker-entrypoint.sh:97-103`, the Pydantic field `instrumentation_variant: str = Field(default="ajc", ...)` in `rv-experiment/config.py:137`, and the click option `--instrumentation-variant` in `rv-experiment/__main__.py:340` MUST remain unchanged.

#### Scenario: Variant tag propagates through the new -core types

- **WHEN** `_instrument_apks()` runs with `instrumentation_variant == "dexlib2"`
- **THEN** the resulting `InstrumentationResults` MUST be an instance of `rv_instrumentation_core.InstrumentationResults` (equivalent to `rv_instrumentation.InstrumentationResults` via re-export)
- **AND** `result.variant` MUST equal `"dexlib2"`
- **AND** `instrument_errors.json` written by `ResultManager` MUST round-trip via `model_validate_json` without error

#### Scenario: Legacy JSON without variant field deserializes as ajc

- **WHEN** an `instrument_errors.json` written before gh52 (lacking the `variant` field) is loaded via `rv_instrumentation_core.InstrumentationResults.model_validate_json(legacy_payload)`
- **THEN** the deserialization MUST succeed
- **AND** the resulting object MUST have `variant == "ajc"` (via the `Field(default="ajc")` mechanism — see design.md §"Dívida herdada gh52 INV-INS-55")
