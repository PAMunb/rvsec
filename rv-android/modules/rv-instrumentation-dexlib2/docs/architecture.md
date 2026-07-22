# rv-instrumentation-dexlib2 Architecture

## Overview

`rv-instrumentation-dexlib2` is the DEX-native instrumentation backend for rv-android. It is a thin Python wrapper around a Java CLI fat jar (`instr-cli.jar`, produced by the Maven aggregator `rvsec-instrumentation-dexlib2`) that rewrites Android DEX bytecode in place using the dexlib2 library, weaving runtime-verification monitors and the Coverage hook directly into the application's `classes*.dex`. The module implements the `Instrumenter` ABC defined in `rv-instrumentation-core`; the parent `rv-instrumentation` dispatches to it through `get_instrumenter("dexlib2", config)`. It is spec-set agnostic — the Java CLI handles both JCA and Generic specifications uniformly via the JSON descriptor contract emitted by `rv-monitor-generator`.

## Specification Alignment

This module implements requirements from `openspec/specs/instrumentation/spec.md`.

### Functional Requirements

| FR | Description | Architectural Support |
|----|-------------|-----------------------|
| FR01 | Monitor generation produces artifacts consumed downstream | This module consumes the JSON descriptors emitted by `rv-monitor-generator` (`--emit-descriptor`) — `prepare_instrumentation()` validates their presence before any APK is processed. |
| FR02 | APK instrumentation weaves monitors into bytecode | `DexlibInstrumentation.instrument_apks()` shells out to `instr-cli.jar`, which rewrites DEX in place — bypassing the legacy `dex2jar -> ajc -> d8` chain and its JVMS §4.10.1.9 type-consistency conflict on R8-optimized APKs. |
| FR03 | Specification set support (JCA, Generic) | Spec-set agnostic by construction — the Java weaver consumes whichever descriptor JSONs are present in `monitor_output_dir`, with no Python-side branching on spec set. |

### Key Invariants

| Invariant | Description | Enforcement Mechanism |
|-----------|-------------|----------------------|
| INV-INS-06 | Instrumented APK hash differs from original | The Java CLI rewrites and re-signs every APK; the wrapper cross-checks output existence in `_demote_silent_failures`. |
| INV-INS-41 | Variant impls depend only on `-core`, not on parent or sibling | `pyproject.toml` declares dependencies on `rv-android-core` and `rv-instrumentation-core` only. No import of `rv_instrumentation` or `rv_instrumentation_ajc`. |
| INV-INS-50 | Missing descriptor halts the dexlib2 variant | `prepare_instrumentation()` raises `MissingDescriptorError` when no `MultiSpec_*MonitorAspect.json` is found. |
| INV-INS-52 | Multidex preservation | Delegated to the Java weaver, which rewrites each `classes*.dex` independently rather than collapsing into a single DEX. |
| INV-INS-53 | Canonical Coverage exclusion filter honored | Java weaver re-implements the `Coverage.aj` exclusion rules natively in the `coverage-weaver` submodule. |
| INV-INS-55 | `instrument_apks(apks_dir, results_dir) -> InstrumentationResults` contract uniform across variants | `DexlibInstrumentation` extends the `Instrumenter` ABC; results are tagged `variant="dexlib2"` and persisted to `instrument_errors.json`. |

### Specification Scenarios

Scenarios from `openspec/specs/instrumentation/spec.md` that validate this architecture:

- **DEX-native instrumentation of an R8-optimized APK previously failing under ajc** — exercises `instrument_apks` against APKs in the JCA-400 corpus that emit `VerifyError` under the AJC variant (e.g., `hateitorrateit`); the dexlib2 variant must produce a hash-distinct, boot-successful APK.
- **Missing descriptor when dexlib2 variant is selected** — `prepare_instrumentation()` MUST raise `MissingDescriptorError` when the `.aj` is present but the `.json` is not.
- **Multidex preservation under DEX-native weaving** — input APK with `classes.dex` + `classes2.dex` retains both DEX entries after weaving.
- **Variant tag propagates through the new -core types** — `InstrumentationResults.variant == "dexlib2"` after a run, and the value is persisted to `instrument_errors.json`.

## Key Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Application Type | Library + thin subprocess wrapper | Heavy lifting (DEX rewriting, javac, d8, jarsigner) lives in the Java CLI; Python orchestrates and observes. |
| Structuring | Flat single-package layout | The module is small (4 files, ~480 SLOC); a layered split would add ceremony without abstraction value (P1). |
| Primary Pattern | Adapter (subprocess wrapper) | Translates Pydantic config and Python call into Java CLI argv + env. |
| Dispatch Strategy | Lazy factory in parent module | `rv_instrumentation.get_instrumenter("dexlib2", config)` imports `DexlibInstrumentation` only when the variant is selected — selecting `"ajc"` never imports this module. |
| Process Isolation | One JVM invocation per batch (or per APK) | Avoids state leakage between APKs; per-APK mode (one JVM per APK) is the only way to honor strict subsets without a symlink farm. |
| Failure Detection | Cross-check post-condition (file existence) | The CLI may exit 0 with `success` recorded in JSON yet drop the output APK silently (gh53 root cause); `_demote_silent_failures` rebuilds the results map by checking the filesystem. |

## Architectural Patterns

### Pattern: Adapter / Subprocess Wrapper

**Description**: `DexlibInstrumentation` adapts the Python-side `Instrumenter` ABC contract onto a Java fat-jar CLI invoked via `subprocess.run`. The wrapper translates `DexlibInstrumentationConfig` fields and the `instrument_apks(apks_dir, results_dir)` call into argv (`java -jar instr-cli.jar [batch|instrument] ...`) and environment variables (`RVSEC_KEYSTORE`, `RVSEC_KEYSTORE_PASS`, classpath hints). Results are read back from `instrument_results.json`, parsed into `InstrumentationResults`, and tagged `variant="dexlib2"`.

**When Used**: Whenever `instrumentation_variant == "dexlib2"` is selected in `ExperimentConfig` or via `--instrumentation-variant dexlib2`.

**Advantages**:

- Decouples Python orchestration from Java weaving — the Java CLI can evolve (new dexlib2 versions, new aspect constructs) without changing the Python contract.
- Subprocess isolation prevents JVM state from leaking into rv-experiment's Python runtime.
- The same Python wrapper runs against any rebuild of `instr-cli.jar` (development builds, Docker-mounted overrides).

**Disadvantages**:

- Two-language toolchain — debugging requires reading both Python and Java traces.
- Subprocess startup cost paid per JVM invocation; mitigated by a batch subcommand that processes a whole directory in one JVM.

### Pattern: Template Method (inherited)

**Description**: `prepare_instrumentation()` calls the inherited `_resolve_runtime_libs()` method from the `Instrumenter` ABC, then applies a variant-specific allowlist (rv-monitor-rt, rvsec-core, rvsec-logger-logcat — `aspectjrt` is filtered out because the rv-monitor-emitted `MultiSpec_*RuntimeMonitor.java` does not import any AspectJ types).

**When Used**: Once per instrumentation run, before any APK is processed.

**Advantages**: Maven dependency resolution logic lives in `-core` and is shared with the AJC variant.

**Disadvantages**: Allowlist drift — adding a new runtime jar requires updating both variants explicitly.

### Pattern: Pydantic Configuration Object

**Description**: `DexlibInstrumentationConfig` mirrors the public field names of `RVInstrumentationConfig` (the AJC variant's config) so callers in `rv-experiment` can swap variants without renaming arguments.

**When Used**: Construction of `DexlibInstrumentation`.

**Advantages**: Variant swap is a one-line change in `ExperimentConfig` plumbing; no caller rewrite.

**Disadvantages**: Field parity must be maintained manually — no compile-time check forces the two configs to stay aligned.

---

## Logical View

Reference: `checklists/architectural-views.md`.

Shows the domain entities and their relationships within the dexlib2 instrumentation pipeline.

### Domain Entities

| Entity | Responsibility |
|--------|----------------|
| `DexlibInstrumentation` | Concrete `Instrumenter` for the `dexlib2` variant — orchestrates subprocess invocation, descriptor validation, runtime classpath assembly, results parsing. |
| `DexlibInstrumentationConfig` | Validated configuration: CLI jar path, monitor descriptor directory, instrumented-APK output directory, signing material, extra Java args/classpath. |
| `MissingDescriptorError` | Raised at preparation time when no `MultiSpec_*MonitorAspect.json` is found. |
| `DescriptorParseError` | Raised when Jackson (Java side) rejects a descriptor JSON; surfaced through subprocess error parsing. |
| `UnsupportedAspectConstructError` | Raised when a descriptor references an out-of-scope construct (`around`, `cflow`, etc. — see `docs/LIMITATIONS.md`). |
| `InstrumentationResults` (from `-core`) | Aggregated per-batch result with `variant="dexlib2"` tag; persisted to `instrument_errors.json`. |
| `InstrumentationError` (from `-core`) | Per-APK error record: phase, tool, code, message. |
| `instr-cli.jar` (external) | Java fat jar that performs DEX rewriting; produced by Maven module `rvsec-instrumentation-dexlib2/cli`. |

### Component Architecture

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart TB
    subgraph Module["rv-instrumentation-dexlib2"]
        direction TB
        subgraph PyApi["Python API surface"]
            direction LR
            DInstr["DexlibInstrumentation"]
            DCfg["DexlibInstrumentationConfig"]
            DErr["errors.py<br/>MissingDescriptorError<br/>DescriptorParseError<br/>UnsupportedAspectConstructError"]
        end
        subgraph PyInternal["Internal helpers"]
            direction LR
            BuildEnv["_build_subprocess_env"]
            DemoteSF["_demote_silent_failures"]
            ResolveRoot["_resolve_rvsec_root_or_raise"]
            CommonCli["_common_cli_args"]
        end
    end

    subgraph Core["rv-instrumentation-core"]
        ABC["Instrumenter (ABC)"]
        Results["InstrumentationResults"]
        ErrModel["InstrumentationError"]
    end

    subgraph External["External Java toolchain"]
        Jar["instr-cli.jar<br/>(fat jar)"]
        JavaTools["javac / d8 / jarsigner / dexlib2"]
    end

    DInstr -->|extends| ABC
    DInstr -->|reads config| DCfg
    DInstr -->|raises| DErr
    DInstr -->|builds| BuildEnv
    DInstr -->|cross-checks| DemoteSF
    DInstr -->|calls| CommonCli
    DInstr -->|resolves| ResolveRoot
    DInstr -->|emits| Results
    Results -->|aggregates| ErrModel
    DInstr -.->|subprocess| Jar
    Jar --> JavaTools
```

---

## Development View

Shows code organization for developers maintaining the module.

### Module Structure

```
modules/rv-instrumentation-dexlib2/
├── src/rv_instrumentation_dexlib2/
│   ├── __init__.py                  # Public API re-exports
│   ├── config.py                    # DexlibInstrumentationConfig (Pydantic)
│   ├── dexlib_instrumentation.py    # DexlibInstrumentation(Instrumenter)
│   └── errors.py                    # 3 module-specific exceptions
├── lib/                             # gitignored — Maven copies instr-cli.jar here
├── tests/
│   └── test_dexlib_instrumentation.py
├── CLAUDE.md
├── README.md
└── pyproject.toml
```

The flat single-package layout is intentional: the module is a thin subprocess wrapper, so a `domain/`/`services/` split would introduce indirection without abstraction value (P1 — Simplicity).

### Package Dependencies

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart TB
    subgraph DexLib2["rv-instrumentation-dexlib2"]
        Pkg["rv_instrumentation_dexlib2"]
    end
    subgraph CoreAbstr["rv-instrumentation-core"]
        AbcPkg["rv_instrumentation_core<br/>(ABC + result types)"]
    end
    subgraph Foundation["rv-android-core"]
        FoundPkg["rv_android_core<br/>(App, ENV_RVSEC_HOME, LoggingManager)"]
    end
    subgraph Parent["rv-instrumentation (parent facade)"]
        Factory["factory.get_instrumenter()"]
    end

    Pkg --> AbcPkg
    Pkg --> FoundPkg
    Factory -.->|lazy import| Pkg
    Factory --> AbcPkg
```

This module has fan-in 2 (parent factory + `rv-experiment` configuration glue, both via lazy imports) and fan-out 2 (`-core`, `rv-android-core`). Instability `I = 0.5`. No dependency on the parent `rv-instrumentation` module nor on the sibling `rv-instrumentation-ajc` — INV-INS-41 keeps the dependency graph acyclic.

---

## Process View

Shows run-time behavior of a single instrumentation invocation.

### Execution Flow: Batch Path (apk_paths=None)

```mermaid
%%{init: {'theme': 'neutral'}}%%
sequenceDiagram
    participant Caller as rv-experiment<br/>PreProcessor
    participant Wrapper as DexlibInstrumentation
    participant ABC as Instrumenter ABC<br/>(rv-instrumentation-core)
    participant Java as instr-cli.jar<br/>(subprocess)
    participant FS as Filesystem

    Caller->>Wrapper: instrument_apks(apks_dir, results_dir)
    Wrapper->>Wrapper: prepare_instrumentation()
    Wrapper->>FS: glob MultiSpec_*MonitorAspect.json
    alt no descriptor present
        Wrapper-->>Caller: MissingDescriptorError (INV-INS-50)
    end
    Wrapper->>ABC: _resolve_runtime_libs()
    ABC->>FS: mvn dependency:copy-dependencies
    ABC-->>Wrapper: runtime jars list
    Wrapper->>Wrapper: filter to allowlist<br/>(rv-monitor-rt, rvsec-core, rvsec-logger-logcat)
    Wrapper->>Java: java -jar instr-cli.jar batch <apks_dir> ...
    Java->>FS: rewrite each APK's DEX in place
    Java->>FS: re-sign each APK
    Java->>FS: write instrument_results.json
    Java-->>Wrapper: exit code + stderr
    Wrapper->>FS: read instrument_results.json
    Wrapper->>Wrapper: _demote_silent_failures()<br/>cross-check output existence
    Wrapper->>FS: write instrument_errors.json (variant="dexlib2")
    Wrapper-->>Caller: InstrumentationResults
```

### Execution Flow: Per-APK Path (apk_paths=[...])

When `apk_paths` is a strict subset, the wrapper invokes the CLI once per APK (one JVM per APK). This is the only way to honor strict subsets without staging a symlink farm. Errors are demoted per-APK rather than aborting the batch.

---

## Core Components

### DexlibInstrumentation

**Purpose**: Concrete `Instrumenter` for the `dexlib2` variant — orchestrates subprocess invocation, descriptor validation, runtime classpath assembly, and results parsing.

**Location**: `src/rv_instrumentation_dexlib2/dexlib_instrumentation.py`

**Key Class**:

- `DexlibInstrumentation(Instrumenter)` — public methods `prepare_instrumentation()`, `instrument(app, result_dir)`, `instrument_apks(apks_dir, results_dir, apk_paths=None, force_instrumentation=False)`. Holds `config: DexlibInstrumentationConfig` and a structured `_logger`.

**Dependencies**:

- Internal: `DexlibInstrumentationConfig`, `MissingDescriptorError`.
- External: `rv_instrumentation_core` (`Instrumenter`, `InstrumentationResults`, `InstrumentationError`), `rv_android_core` (`App`, `ENV_RVSEC_HOME`, `LoggingManager`), `subprocess`, `pathlib`.

### DexlibInstrumentationConfig

**Purpose**: Validated configuration. Mirrors `RVInstrumentationConfig` field names so callers can swap variants without renaming.

**Location**: `src/rv_instrumentation_dexlib2/config.py`

**Key Fields**:

- `cli_jar_path: Path` — defaults to `../../lib/instr-cli.jar` (auto-copied by Maven).
- `monitor_output_dir: Path` — directory containing the descriptor JSONs and supporting Java sources.
- `descriptor_glob: str` — defaults to `MultiSpec_*MonitorAspect.json`.
- `instrumented_dir: Path` — output directory.
- `working_dir: Path` — scratch.
- `keystore_file`, `keystore_password`, `keystore_alias`, `key_password` — signing material (all optional, fall back to env vars on the Java side).
- `extra_java_args: List[str]`, `extra_classpath: List[Path]`.

**Notable absence**: no wallclock timeout. Weave time scales with method count; APKs in the JCA-400 corpus legitimately take 10-30+ minutes (e.g. `io.github.eucsoh.android_9.apk`: 14m14s, 249k methods). If hung-CLI detection is ever needed, an inactivity-based watchdog is the right tool — not a wallclock cap that aborts legitimate slow runs.

### errors.py

**Purpose**: Module-specific exceptions raised at preparation or surfaced from the Java CLI.

**Location**: `src/rv_instrumentation_dexlib2/errors.py`

**Classes**:

- `MissingDescriptorError` — INV-INS-50.
- `DescriptorParseError` — Java-side Jackson failure surfaced through subprocess parsing.
- `UnsupportedAspectConstructError` — descriptor references an out-of-scope construct (`around`, `cflow`, `cflowbelow`, `handler`, `get`, `set`, `initialization`, `preinitialization`).

---

## NFR Support

Reference: `docs/PRD.md` Section 7.

| NFR | PRD ID | Priority | Architectural Support |
|-----|--------|----------|-----------------------|
| Performance | NFR01 | P0 | Single-JVM batch path (one `instr-cli.jar` invocation for the whole `apks_dir`) eliminates per-APK JVM startup cost, which dominates throughput when processing hundreds of APKs. |
| Maintainability | NFR02 | P0 | Flat package structure; one public class; descriptor JSON is the single contract surface with `rv-monitor-generator`. |
| Extensibility | NFR03 | P1 | Variant selection lives in the parent factory — adding a future `dexlib3` variant requires only a new `Instrumenter` impl and a factory branch, no changes here. |
| Reliability | NFR04 | P1 | Silent-failure cross-check (`_demote_silent_failures`) catches CLI bugs where exit code 0 ships a missing output APK; per-APK demotion prevents one APK from poisoning the batch. |
| Testability | NFR07 | P1 | Subprocess invocation is the only side-effect, making mock-based unit tests straightforward; `DexlibInstrumentationConfig` is fully constructible from in-memory paths. |

---

## Key Interfaces

### Instrumenter (from `rv-instrumentation-core`)

```python
class Instrumenter(ABC):
    """Abstract instrumentation backend. Variants implement this."""

    @abstractmethod
    def prepare_instrumentation(self) -> None:
        """Validate config, populate runtime classpath. Raises on misconfig."""
        ...

    @abstractmethod
    def instrument(self, app: App, result_dir: Path) -> InstrumentationResults:
        """Instrument a single App; emit results into result_dir."""
        ...

    @abstractmethod
    def instrument_apks(
        self,
        apks_dir: Path,
        results_dir: Path,
        apk_paths: Optional[List[Path]] = None,
        force_instrumentation: bool = False,
    ) -> InstrumentationResults:
        """Instrument every APK in apks_dir (or the strict subset apk_paths)."""
        ...
```

```mermaid
%%{init: {'theme': 'neutral'}}%%
classDiagram
    class Instrumenter {
        <<interface>>
        +prepare_instrumentation()*
        +instrument(app, result_dir)*
        +instrument_apks(apks_dir, results_dir, apk_paths, force)*
    }

    class DexlibInstrumentation {
        +config: DexlibInstrumentationConfig
        +prepare_instrumentation()
        +instrument(app, result_dir)
        +instrument_apks(apks_dir, results_dir, apk_paths, force)
        -_build_subprocess_env()
        -_demote_silent_failures()
        -_common_cli_args()
        -_resolve_rvsec_root_or_raise()
    }

    class AjcInstrumentation {
        +config: AjcInstrumentationConfig
        +prepare_instrumentation()
        +instrument(app, result_dir)
        +instrument_apks(apks_dir, results_dir, apk_paths, force)
    }

    Instrumenter <|-- DexlibInstrumentation
    Instrumenter <|-- AjcInstrumentation
```

### Variant selection contract

```python
from rv_instrumentation import get_instrumenter

instr = get_instrumenter("dexlib2", config)  # lazy imports DexlibInstrumentation
results = instr.instrument_apks(apks_dir, results_dir)
assert results.variant == "dexlib2"
```

---

## Scenarios

### Scenario 1: Batch instrumentation of an experiment's APK directory

**Description**: `rv-experiment` runs Phase 1 pre-processing with `instrumentation_variant="dexlib2"`.

**Flow**:

1. `PreProcessor._instrument_apks()` calls `get_instrumenter("dexlib2", config)`.
2. Parent factory lazy-imports `DexlibInstrumentation` and constructs an instance with the JIT-built `DexlibInstrumentationConfig`.
3. `instrument_apks(apks_dir, results_dir)` is called with `apk_paths=None`.
4. `prepare_instrumentation()` validates descriptor presence and resolves the runtime classpath.
5. The wrapper invokes `instr-cli.jar batch <apks_dir>` in one subprocess.
6. The Java CLI rewrites each APK's DEX, re-signs, writes `instrument_results.json`.
7. The wrapper parses the JSON, runs `_demote_silent_failures` to catch missing outputs, persists `instrument_errors.json` with `variant="dexlib2"`.
8. `InstrumentationResults` returned to the caller.

### Scenario 2: Strict-subset reinstrumentation

**Description**: A re-run targets only APKs that failed in a previous batch.

**Flow**:

1. Caller passes `apk_paths=[apk1, apk2, apk3]`.
2. The wrapper switches to per-APK mode: one `instr-cli.jar instrument <apk>` invocation per APK.
3. Per-APK errors are demoted to entries in `InstrumentationResults.errors` rather than aborting the batch.
4. Aggregated results returned with `variant="dexlib2"`.

### Scenario 3: Silent-failure detection (gh53 root cause)

**Description**: The Java CLI exits 0 and records `success` for an APK in `instrument_results.json`, but a downstream javac/d8/jarsigner step silently dropped the output file.

**Flow**:

1. Wrapper parses `instrument_results.json` — the entry shows success.
2. `_demote_silent_failures` walks the results and checks `Path(result.instrumented_path).exists()`.
3. The missing entry is rebuilt as an `InstrumentationError(phase="dexlib2_pipeline", ...)`.
4. The corrected `InstrumentationResults` is returned to the caller and persisted, preventing phantom successes from poisoning downstream coverage analysis.

---

## Extension Points

- **New aspect construct support**: extend the descriptor schema in `rv-monitor-generator` and the corresponding weaver in the Java CLI. The Python wrapper requires no changes — descriptor parsing happens entirely on the Java side.
- **Alternative CLI override**: set `cli_jar_path` to a development build or a Docker-mounted jar to test weaver changes without reinstalling.
- **Extra classpath entries**: append to `extra_classpath` to pull additional libraries into the Java CLI's javac classpath when the rv-monitor-emitted Java sources reference them.
- **Subprocess environment**: `_build_subprocess_env` injects `RVSEC_KEYSTORE`, `RVSEC_KEYSTORE_PASS`, `RVSEC_KEYSTORE_ALIAS`, `RVSEC_KEY_PASS` only when the corresponding config fields are set, allowing the Java CLI to fall back to its own defaults otherwise.

## Dependencies

### Internal (rv-android modules)

| Module | Purpose |
|--------|---------|
| `rv-android-core` | `App` domain model, `ENV_RVSEC_HOME` constant, `LoggingManager` for structured per-APK logs. |
| `rv-instrumentation-core` | `Instrumenter` ABC, `InstrumentationResults` and `InstrumentationError` Pydantic types, `_resolve_runtime_libs` Template Method. |

### External

| Package | Version | Purpose |
|---------|---------|---------|
| `pydantic` | `>=2.9.0` | `DexlibInstrumentationConfig` validation. |
| `instr-cli.jar` | Built from `rvsec/rvsec-android/rvsec-instrumentation-dexlib2` | Java fat jar performing DEX rewriting; auto-copied to `lib/instr-cli.jar` by the Maven build (design D9). The Docker image build gates on its presence. |
| Android SDK / JDK | `ANDROID_HOME` / `JAVA_HOME` | Resolved by the Java CLI's `ConfigResolver`; the Python wrapper does not look at these. |

## Testing Strategy

| Type | Location | Purpose |
|------|----------|---------|
| Unit | `tests/test_dexlib_instrumentation.py` | Argv assembly, env injection, descriptor presence checks, results parsing, `_demote_silent_failures` cross-check logic — all with the Java CLI mocked. |
| End-to-end (validator) | `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/validator/` | `BaksmaliDiffer`, `BootValidator`, `TraceComparator`, `BatchValidator`, `CoverageValidator`, `FeatureMappingChecker` exercise the full pipeline against real APKs from the JCA-400 dataset (Java side; not part of this Python module's tests). |

## Related Documentation

- [Domain Spec](../../../openspec/specs/instrumentation/spec.md) — Instrumentation requirements and invariants.
- [PRD](../../../docs/PRD.md) — Product Requirements Document (FR01-37, NFR01-08).
- [CLAUDE.md](../CLAUDE.md) — Quick reference for Claude Code.
- [rv-instrumentation-core README](../../rv-instrumentation-core/README.md) — Pure abstractions module.
- [rv-instrumentation parent](../../rv-instrumentation/) — Parent facade with `get_instrumenter()` factory.
- [rv-instrumentation-ajc architecture](../../rv-instrumentation-ajc/docs/architecture.md) — Sibling AJC variant (for comparison).
- `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` — Java aggregator implementing the weaver.
- `docs/LIMITATIONS.md` — Out-of-scope AspectJ constructs.
- `docs/AJ_TO_DEXLIB2_MAPPING.md` — Construct-to-component mapping.
