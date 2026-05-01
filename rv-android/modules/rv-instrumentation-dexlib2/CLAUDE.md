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

**Entry Point**: `rv-instrumentation-dexlib2` CLI or programmatic via
`DexlibInstrumentation` class. Selected at runtime via
`RV_INSTRUMENTATION_VARIANT=dexlib2` (or `--instrumentation-variant dexlib2`)
in `rv-experiment`.

## Public API

```python
from rv_instrumentation_dexlib2 import DexlibInstrumentation
from rv_instrumentation_dexlib2.config import DexlibInstrumentationConfig
from rv_instrumentation_core import Instrumenter

assert issubclass(DexlibInstrumentation, Instrumenter)

config = DexlibInstrumentationConfig(
    monitor_output_dir="/path/to/monitors",
    instrumented_dir="/output",
    cli_jar_path="/path/to/instr-cli.jar",
)
results = DexlibInstrumentation(config).instrument_apks(apks_dir, results_dir)
```

## File Structure

```
modules/rv-instrumentation-dexlib2/
├── src/rv_instrumentation_dexlib2/
│   ├── __init__.py
│   ├── __main__.py              # CLI entry point
│   ├── config.py                # DexlibInstrumentationConfig
│   ├── dexlib_instrumentation.py # DexlibInstrumentation(Instrumenter)
│   ├── errors.py                # MissingDescriptorError
│   └── ...
├── lib/                          # gitignored — instr-cli.jar lands here at build time
├── tests/
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

## Tests

```bash
uv run pytest modules/rv-instrumentation-dexlib2/tests/ \
    --import-mode=importlib -o "addopts=" -v
```

## Development Notes

- The Java CLI is the source of truth for instrumentation behaviour; the
  Python wrapper only orchestrates subprocess invocation, parses the
  `instrument_results.json` output, and tags it with `variant="dexlib2"`.
- Spec-set agnostic — JCA and Generic specifications are handled identically
  by the underlying weaver.
- `instrument_apks(apk_paths=...)` honours strict subsets via per-APK
  invocation (one JVM per APK). When `apk_paths=None`, the batch subcommand
  processes the whole directory in one JVM (fast path).
