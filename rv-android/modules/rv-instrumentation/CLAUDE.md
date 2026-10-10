# CLAUDE.md - rv-instrumentation

Parent canonical module for APK instrumentation. **No business logic lives
here** — the parent re-exports the public API from `rv-instrumentation-core`
and exposes the `get_instrumenter` factory that dispatches between two
concrete variants (`rv-instrumentation-ajc`, `rv-instrumentation-dexlib2`).
The shared signing keystore `assets/keystore.jks` (alias `server`, password
`password`) lives here; both variants sign with `apksigner`.

## Module Overview

**Purpose**: Stable public entry point for instrumentation. Consumers import
all instrumentation symbols from `rv_instrumentation` regardless of which
concrete variant is in use.

**Package**: `rv_instrumentation`

**Entry Point**: Importable library only. The only command line in the family
is `rv-instrumentation-ajc` (see that module).

## Public API

```python
from rv_instrumentation import (
    Instrumenter,           # ABC — re-exported from -core
    InstrumentationResults, # Pydantic — re-exported from -core
    InstrumentationError,   # Pydantic — re-exported from -core
    get_instrumenter,       # factory — defined in factory.py
)

instrumenter = get_instrumenter("ajc", config)     # → AjcInstrumentation(config)
# or
instrumenter = get_instrumenter("dexlib2", config) # → DexlibInstrumentation(config)
results = instrumenter.instrument_apks(apks_dir, results_dir, apk_paths=apk_list)
```

`get_instrumenter(variant: str, config) -> Instrumenter` is the single dispatch
site (INV-INS-36); any other `variant` raises `ValueError` naming the valid
values. `config` is untyped: it must be the variant's own config
(`AjcInstrumentationConfig` / `DexlibInstrumentationConfig`). Both variants
implement `Instrumenter`; consumers code against the ABC and let the factory
pick.

## File Structure

```
modules/rv-instrumentation/
├── src/rv_instrumentation/
│   ├── __init__.py    # re-exports + factory
│   └── factory.py     # get_instrumenter
├── tests/
│   └── test_factory.py
├── assets/
│   └── keystore.jks   # shared signing keystore
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

**Depended on by**: `rv-experiment` — `PreProcessor._instrument_apks`
(`modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py`)
builds the variant config (`get_rv_instrumentation_config` or
`get_dexlib_instrumentation_config`), calls `get_instrumenter`, and passes an
explicit `apk_paths` list.

## Keystore

`assets/keystore.jks` reaches the variants by source-tree path, not by package
resources: `AjcInstrumentationConfig._apply_default_paths` resolves
`modules/rv-instrumentation/assets/keystore.jks` relative to its own file, and
rv-experiment's `get_dexlib_instrumentation_config` resolves
`$RVSEC_HOME/rv-android/modules/rv-instrumentation/assets/keystore.jks` and
passes it as `keystore_file`. Moving the file breaks both.

## Variant module quick reference

| Variant | Module | Class | CLI |
|---------|--------|-------|-----|
| AspectJ-based | `rv-instrumentation-ajc` | `AjcInstrumentation` | `rv-instrumentation-ajc` |
| DEX-native | `rv-instrumentation-dexlib2` | `DexlibInstrumentation` | none (wraps the Java `instr-cli.jar`) |

## Tests

```bash
uv run pytest modules/rv-instrumentation/tests/ \
    --import-mode=importlib -o "addopts=" -v
```

`test_factory.py` covers the three dispatch paths (ajc, dexlib2, unknown) and
verifies lazy-import behaviour.

## Adding a new variant

See `docs/architecture.md` § "Adding a third variant".
