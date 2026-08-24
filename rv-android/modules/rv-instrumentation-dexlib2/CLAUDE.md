# CLAUDE.md - rv-instrumentation-dexlib2

DEX-native APK instrumentation variant. Python wrapper around the Java CLI
(`rvsec-instrumentation-dexlib2/cli`) whose fat jar is auto-copied to
`lib/instr-cli.jar` by the Maven build (design D9). Implements the
`Instrumenter` ABC defined in `rv-instrumentation-core`; the parent
`rv-instrumentation` dispatches here via `get_instrumenter("dexlib2", config)`.

## Module Overview

**Purpose**: Spec-set-agnostic DEX-native instrumentation backend (gh52). Avoids
the dex2jar→ajc→d8 chain — the Java CLI rewrites DEX bytecode in place using
the dexlib2 library.

**Package**: `rv_instrumentation_dexlib2`

**Entry Point**: Programmatic only — construct `DexlibInstrumentation` directly,
or let `rv-experiment` select the variant via `RV_INSTRUMENTATION_VARIANT=dexlib2`
(or `--instrumentation-variant dexlib2`). There is no module CLI: `pyproject.toml`
still declares a `rv-instrumentation-dexlib2` console script pointing at
`rv_instrumentation_dexlib2.__main__:main`, but no `__main__.py` exists — the
script is dangling and fails on invocation.

## Public API

```python
from rv_instrumentation_dexlib2 import DexlibInstrumentation
from rv_instrumentation_dexlib2.config import DexlibInstrumentationConfig
from rv_instrumentation_core import Instrumenter

assert issubclass(DexlibInstrumentation, Instrumenter)

config = DexlibInstrumentationConfig(
    monitor_output_dir="/path/to/monitors",
    instrumented_dir="/output",
    working_dir="/scratch",
    cli_jar_path="/path/to/instr-cli.jar",
)
results = DexlibInstrumentation(config).instrument_apks(apks_dir, results_dir)
results.weave_counts["cryptoapp.apk"]["matchesApplied"]  # weaver counters
```

`instrument_apks` is the only abstract method on the ABC. `prepare_instrumentation()`
and `instrument(app, result_dir) -> Path` are variant-specific and reached through
the concrete class.

## File Structure

```
modules/rv-instrumentation-dexlib2/
├── src/rv_instrumentation_dexlib2/
│   ├── __init__.py                # Public API re-exports
│   ├── config.py                  # DexlibInstrumentationConfig
│   ├── dexlib_instrumentation.py  # DexlibInstrumentation(Instrumenter)
│   └── errors.py                  # MissingDescriptorError, DescriptorParseError,
│                                  # UnsupportedAspectConstructError
├── lib/                           # gitignored — instr-cli.jar lands here at build time
├── docs/architecture.md
├── tests/test_dexlib_instrumentation.py
└── pyproject.toml
```

## Dependencies

```toml
dependencies = [
    "rv-android-core",
    "rv-instrumentation-core",
    "pydantic>=2.9.0",
]
```

Depends only on `rv-instrumentation-core` (for the ABC + shared types) — NOT
on the parent `rv-instrumentation` and NOT on the sibling
`rv-instrumentation-ajc`. INV-INS-41 keeps the dependency graph acyclic.

## External tool dependency: instr-cli.jar

The Python wrapper shells out to a Java fat jar produced by Maven from
`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/cli/`. Maven's
copy-resources step (design D9) auto-copies the jar to
`modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` at every
`mvn install` of the rvsec tree. The Docker build (`docker/rvandroid/Dockerfile`)
gates the image build on the jar being present — if it isn't, the build fails
loudly so we never ship a runtime where `RV_INSTRUMENTATION_VARIANT=dexlib2`
crashes with `FileNotFoundError` partway through an experiment.

## Artefacts written under `results_dir`

Both execution paths leave the same document shape, so a results tree can be
inspected without knowing which path produced it (INV-INS-105).

| Artefact | Written by | Content |
|---|---|---|
| `instrument_results.json` | `batch`: the Java CLI directly. `apk_paths`: `_merge_per_apk_results` concatenates the per-APK files. | `{"variant": "dexlib2", "results": [...]}` — one entry per APK with `apkName`, `success`, `phase`, `weaveCounts`. |
| `instrument_results.d/<apk>.json` | `apk_paths` path only | One results JSON per JVM run; a single-APK run only knows its own APK, so a shared path would overwrite. |
| `instrument_results.d/<apk>.log`, `instr-cli.log` | `_run_cli(log_path=...)` | Full argv, exit code, elapsed time, CLI stdout and stderr. `capture_output=True` takes the weaver's output off the terminal; without this file a platform-jar mismatch or a javac diagnostic is not diagnosable after the fact. |
| `instrument_errors.json` | `_persist_errors_json` | `{<apk_name>: {code, tool, message, phase}}`; `{}` when clean, so consumers can rely on the file existing. Mirrors the AJC schema. |

## Weaver counters (`InstrumentationResults.weave_counts`)

Keyed by APK name, populated from each entry's `weaveCounts`. The Java
`BatchRunner` publishes them; notable keys:

- `classesSeen`, `methodsSeen`, `matchesApplied` — weave reach.
- `plansSkipped`, `plansSkippedAliasing`, `plansSkippedUnresolvedBinding` (INV-INS-71),
  `plansSkippedHighRegister` — what the weaver declined to apply. `plansSkippedHighRegister`
  is where extra invokes pushing a method over its register budget shows up.
- `wrappersGenerated`, `wrappersSubstituted`, `wrappersAliasedToSubtype`,
  `constructorInlineApplied`, `constructorInlineSkippedAliasing` — wrapper emission.
- `advicesExcludedByArity` (INV-INS-122) — a measurement, not a filter: advice/overload
  pairs whose positional `args()` arity does not fit the overload they are grouped onto.
  Every one of them still fires. Always written, so `0` means "measured none", not
  "not measured". Counted over wrapper-path after-advices only.
- `coverageInstrumented`, `coverageSpillFailed` — present only when the coverage
  weaver ran.

A demoted APK keeps its counters: `_demote_silent_failures` changes the verdict
on an APK, not what the weaver did to it, and a demoted APK's counters are the
most interesting ones in the batch.

## Tests

```bash
uv run pytest modules/rv-instrumentation-dexlib2/tests/ \
    --import-mode=importlib -o "addopts=" -v
```

26 unit tests, Java CLI mocked throughout.

## Development Notes

- The Java CLI is the source of truth for instrumentation behaviour; the
  Python wrapper only orchestrates subprocess invocation, parses the
  `instrument_results.json` output, and tags it with `variant="dexlib2"`.
- Spec-set agnostic — JCA and Generic specifications are handled identically
  by the underlying weaver.
- `instrument_apks(apk_paths=...)` honours strict subsets via per-APK
  invocation (one JVM per APK). Each item is a **complete path**; do not
  re-join with `apks_dir`. When `apk_paths=None`, the batch subcommand
  processes the whole directory in one JVM (fast path).
- Exit code 0 is not proof of success. The CLI can print javac/d8 errors and
  still exit 0, or record `success: true` in the JSON for an APK it never
  wrote. Both paths cross-check the output APK on disk — the `apk_paths` loop
  inline, the batch path via `_demote_silent_failures`.
- No wallclock timeout on the subprocess. Weave time scales with method count;
  JCA-400 APKs legitimately take 10-30+ minutes. If a hung CLI ever needs
  detection, add an inactivity watchdog — not a wallclock cap.
- `_build_subprocess_env` forwards only `PATH`, `HOME`, `JAVA_HOME`,
  `ANDROID_HOME`, `RVSEC_HOME`, plus `RVSEC_KEYSTORE` / `RVSEC_KEYSTORE_PASS`
  when configured. Wholesale `os.environ` propagation is forbidden by INV-EXP-30.
