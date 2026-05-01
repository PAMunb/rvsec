# CLAUDE.md - rv-instrumentation

Parent canonical module for APK instrumentation. **No business logic lives
here** — the parent re-exports the public API from `rv-instrumentation-core`
and exposes the `get_instrumenter` factory that dispatches between two
concrete variants (`rv-instrumentation-ajc`, `rv-instrumentation-dexlib2`).
The shared `assets/keystore.jks` asset (used by both `apksigner` and
`jarsigner`) lives here.

## Module Overview

**Purpose**: Stable public entry point for instrumentation. Consumers import
all instrumentation symbols from `rv_instrumentation` regardless of which
concrete variant is in use.

**Package**: `rv_instrumentation`

**Entry Point**: Importable library only. The CLI moved to
`rv-instrumentation-ajc`; invoke it as `rv-instrumentation-ajc` (or use the
factory programmatically).

## Public API

```python
from rv_instrumentation import (
    Instrumenter,           # ABC — re-exported from -core
    InstrumentationResults, # Pydantic — re-exported from -core
    InstrumentationError,   # Pydantic — re-exported from -core
    get_instrumenter,       # factory — defined here
)

instrumenter = get_instrumenter("ajc", config)   # → AjcInstrumentation
# or
instrumenter = get_instrumenter("dexlib2", config) # → DexlibInstrumentation
results = instrumenter.instrument_apks(apks_dir, results_dir)
```

Both variants implement `Instrumenter`; consumers code against the ABC and
let the factory pick.

## File Structure

```
modules/rv-instrumentation/
├── src/rv_instrumentation/
│   ├── __init__.py    # re-exports + factory
│   └── factory.py     # get_instrumenter
├── tests/
│   └── test_factory.py
├── assets/
│   └── keystore.jks   # shared (apksigner + jarsigner)
├── docs/architecture.md
└── pyproject.toml
```

## Dependencies

```toml
dependencies = [
    "rv-instrumentation-core",
    "rv-instrumentation-ajc",
    "rv-instrumentation-dexlib2",
]
```

The parent declares all three workspace siblings, but `factory.py` lazy-imports
the impl modules inside the selected branch — selecting `"ajc"` does not load
`rv_instrumentation_dexlib2`, and vice versa.

## Variant module quick reference

| Variant | Module | Class | CLI |
|---------|--------|-------|-----|
| AspectJ-based | `rv-instrumentation-ajc` | `AjcInstrumentation` | `rv-instrumentation-ajc` |
| DEX-native (gh52) | `rv-instrumentation-dexlib2` | `DexlibInstrumentation` | `rv-instrumentation-dexlib2` |

## Tests

```bash
uv run pytest modules/rv-instrumentation/tests/ \
    --import-mode=importlib -o "addopts=" -v
```

`test_factory.py` covers the three dispatch paths and verifies lazy-import
behaviour.

## Adding a new variant

See `docs/architecture.md` § "Adding a third variant".
