# CLAUDE.md - rv-instrumentation-core

Pure abstractions module for APK instrumentation. Holds the `Instrumenter` ABC
(with one shared Template Method, `_resolve_runtime_libs`) and the shared
Pydantic result types (`InstrumentationResults`, `InstrumentationError`). No
factory, no assets, no CLI.

## Module Overview

**Purpose**: Provide the contract every instrumentation variant satisfies and
the result models they all return, while keeping the dependency graph
acyclic (variants → `-core`; parent → `-core` + variants).

**Package**: `rv_instrumentation_core`

**Entry Point**: Importable library only — no executable.

## Public API

```python
from rv_instrumentation_core import (
    Instrumenter,           # ABC — single @abstractmethod: instrument_apks
    InstrumentationResults, # Pydantic — counts, errors, weave_counts, variant + computed success_rate
    InstrumentationError,   # Pydantic — code, tool, message, phase
)
```

Symbols are re-exported by the parent `rv-instrumentation`, so consumers can
import them from either location.

### `Instrumenter` (`src/rv_instrumentation_core/instrumenter.py`)

- `instrument_apks(apks_dir, results_dir, force_instrumentation=False, apk_paths=None) -> InstrumentationResults`
  — the only abstract method. When `apk_paths` is set, each item is a
  **complete path** to an APK and `apks_dir` is ignored for input lookup;
  variants must not re-join items with `apks_dir`. rv-experiment always passes
  `apk_paths`.
- `_resolve_runtime_libs(rvsec_root, lib_tmp_dir, timeout_seconds=600) -> List[Path]`
  — runs `mvn -f <rvsec_root>/rv-android/pom.xml -q dependency:copy-dependencies
  -DincludeScope=runtime -Dmdep.stripVersion=true` into `lib_tmp_dir` and
  returns the sorted jar paths. Raises `FileNotFoundError` when
  `rv-android/pom.xml` is missing and `RuntimeError` when Maven fails or copies
  no jar. `-Dmdep.stripVersion=true` matters: both variants look jars up by
  bare artifactId (`rv-monitor-rt.jar`). Each variant passes its own
  `lib_tmp_dir` and keeps the jars it needs (ajc keeps `aspectjrt`; dexlib2
  keeps only `rv-monitor-rt`, `rvsec-core`, `rvsec-logger-logcat`).

### `InstrumentationResults` (`src/rv_instrumentation_core/results.py`)

Fields: `errors: Dict[str, InstrumentationError]` (keyed by APK name),
`success_count`, `total_count`, `weave_counts: Dict[str, Dict[str, int]]`
(per-APK weaver counters; filled by dexlib2 only, empty for ajc), `variant: str`,
and the computed `success_rate` (percent, `0.0` when `total_count == 0`).

`variant` is declared required, but the `mode="before"` validator
`_inject_legacy_variant_default` adds `"variant": "ajc"` to **any** input that
lacks the key — legacy JSON and also keyword constructor calls, because Pydantic
passes constructor kwargs to a before-validator as a dict. So
`InstrumentationResults()` is valid and has `variant == "ajc"`; the ajc variant
relies on this (`ajc_instrumentation.py:149`). The inline comment in
`results.py` saying the validator never fires for constructor calls is wrong.
`variant` is a plain `str`: no value check.

## File Structure

```
modules/rv-instrumentation-core/
├── src/rv_instrumentation_core/
│   ├── __init__.py          # re-exports Instrumenter + types
│   ├── instrumenter.py      # ABC Instrumenter + _resolve_runtime_libs
│   └── results.py           # InstrumentationResults + InstrumentationError
├── tests/
│   ├── test_instrumenter.py # ABC contract + _resolve_runtime_libs (mvn mocked)
│   └── test_results.py      # round-trip, legacy JSON without variant, success_rate
├── docs/architecture.md
└── pyproject.toml
```

## Dependencies

| Dep | Why |
|-----|-----|
| `pydantic>=2.9.0` | `InstrumentationResults` / `InstrumentationError` are validated models |
| `rv-android-core` | `BaseValidatedModel` base class (`rv_android_core.util.validation.base`) |

No dep on `rv-instrumentation`, `-ajc`, or `-dexlib2` — INV-INS-41 keeps the
graph acyclic. External tool: `mvn` on `PATH` (only when a variant calls
`_resolve_runtime_libs`).

## Tests

```bash
uv run pytest modules/rv-instrumentation-core/tests/ \
    --import-mode=importlib -o "addopts=" -v
```

`test_instrumenter.py` confirms a synthetic subclass missing `instrument_apks`
raises `TypeError` on instantiation, that concrete subclasses instantiate and
keep the signature, and covers `_resolve_runtime_libs` (argv, missing pom,
Maven failure, no jars) with `subprocess.run` mocked. `test_results.py` covers
round-trip serialization for both `"ajc"` and `"dexlib2"` variants, legacy
JSON without `variant` deserializing as `"ajc"`, and `success_rate` with zero
total.

## Adding a new variant

1. Create `modules/rv-instrumentation-<variant>/` declaring `rv-instrumentation-core`
   as its only `rv-instrumentation*` dep.
2. Subclass `Instrumenter`, override `instrument_apks`; construct
   `InstrumentationResults` with an explicit `variant=` (omitting it yields `"ajc"`).
3. Add a branch to `rv_instrumentation.factory.get_instrumenter` (lazy-import
   the new module so unrelated variants are not loaded).

The threshold for migrating from explicit branches to a registry is the third
concrete variant materialising; the fourth is a definitive signal.
