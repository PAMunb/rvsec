# rv-instrumentation Architecture

Parent canonical module for APK instrumentation. Holds the public API
(re-exported from `rv-instrumentation-core`), the `get_instrumenter` factory
that dispatches between concrete variants, and the shared `assets/keystore.jks`
asset used by both `apksigner` (dexlib2) and `jarsigner` (ajc).

## Role in the dependency graph

```
rv-instrumentation-core      ← rv-instrumentation-ajc       (variant impl)
                             ← rv-instrumentation-dexlib2   (variant impl)
                             ← rv-instrumentation           (parent — this module)
                                                            ↘ (dispatches to ajc, dexlib2)
                                                            ↘ rv-experiment (consumer)
```

Setas só vão para baixo no grafo. The parent does not import variant impls
at module-load time — `factory.get_instrumenter` does so lazily inside the
selected branch. Both impl modules and `-core` are declared as dependencies
in `pyproject.toml`, so the workspace installs them, but neither is loaded
until needed.

## Public API

```python
from rv_instrumentation import (
    Instrumenter,           # ABC — re-exported from -core
    InstrumentationResults, # Pydantic — re-exported from -core
    InstrumentationError,   # Pydantic — re-exported from -core
    get_instrumenter,       # factory — defined here
)
```

`get_instrumenter(variant: str, config) -> Instrumenter` accepts either
`"ajc"` or `"dexlib2"` and returns the configured implementation. Unknown
variants raise `ValueError` listing the valid options.

## Assets

| Path | Purpose | Consumers |
|------|---------|-----------|
| `assets/keystore.jks` | Bundled development keystore | `apksigner` (dexlib2) and `jarsigner` (ajc) — INV-INS-39 keeps it in the parent |

The `weaving_excludes.yaml` asset (AspectJ-specific) lives in
`rv-instrumentation-ajc/assets/` — INV-INS-40.

## Tests

`tests/test_factory.py` covers the three dispatch paths (ajc, dexlib2, error)
and verifies lazy-import behaviour: requesting `"ajc"` does not load
`rv_instrumentation_dexlib2`, and vice versa.

## Adding a third variant

1. Create `modules/rv-instrumentation-<name>/` declaring `rv-instrumentation-core`
   as its only `rv-instrumentation*` dependency. Subclass `Instrumenter`.
2. Add a branch to `factory.get_instrumenter` (lazy-import the new module).
3. Declare the new module as a dependency of this parent in `pyproject.toml`.
4. Extend the `Literal[...]` for `instrumentation_variant` in
   `rv-experiment/config.py`.

The threshold for migrating from explicit `if/elif` branches to a registry
pattern is the third concrete variant materialising; the fourth is a
definitive signal.
