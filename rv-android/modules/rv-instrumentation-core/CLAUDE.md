# CLAUDE.md - rv-instrumentation-core

Pure abstractions module for APK instrumentation. Holds the `Instrumenter` ABC
and the shared Pydantic result types (`InstrumentationResults`,
`InstrumentationError`). No business logic, no factory, no assets, no CLI.

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
    InstrumentationResults, # Pydantic — counts + variant tag + computed success_rate
    InstrumentationError,   # Pydantic — code, tool, message, phase
)
```

Symbols are re-exported by the parent `rv-instrumentation`, so consumers can
import them from either location.

## File Structure

```
modules/rv-instrumentation-core/
├── src/rv_instrumentation_core/
│   ├── __init__.py          # re-exports Instrumenter + types
│   ├── instrumenter.py      # ABC Instrumenter
│   └── results.py           # InstrumentationResults + InstrumentationError
├── tests/
│   ├── test_instrumenter.py # ABC contract: missing impl fails fast
│   └── test_results.py      # round-trip + retrocompat for legacy JSON
├── docs/architecture.md
└── pyproject.toml
```

## Dependencies

| Dep | Why |
|-----|-----|
| `pydantic>=2.9.0` | `InstrumentationResults` / `InstrumentationError` are validated models |
| `rv-android-core` | `BaseValidatedModel` base class |

No dep on `rv-instrumentation`, `-ajc`, or `-dexlib2` — INV-INS-41 keeps the
graph acyclic.

## Tests

```bash
uv run pytest modules/rv-instrumentation-core/tests/ \
    --import-mode=importlib -o "addopts=" -v
```

`test_instrumenter.py` confirms a synthetic subclass missing `instrument_apks`
raises `TypeError` on instantiation; concrete subclasses instantiate fine and
return `InstrumentationResults`. `test_results.py` covers round-trip
serialization for both `"ajc"` and `"dexlib2"` variants and confirms legacy
JSON without `variant` deserializes with the default `"ajc"` (retrocompat).

## Adding a new variant

1. Create `modules/rv-instrumentation-<variant>/` declaring `rv-instrumentation-core`
   as its only `rv-instrumentation*` dep.
2. Subclass `Instrumenter`, override `instrument_apks`.
3. Add a branch to `rv_instrumentation.factory.get_instrumenter` (lazy-import
   the new module so unrelated variants are not loaded).

The threshold for migrating from explicit branches to a registry is the third
concrete variant materialising; the fourth is a definitive signal.
