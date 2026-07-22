# rv-instrumentation

Parent canonical module for APK instrumentation. Re-exports the public API
from `rv-instrumentation-core` and exposes the `get_instrumenter` factory
that dispatches between two concrete variants:

- `rv-instrumentation-ajc` — AspectJ-based pipeline (legacy dex2jar+ajc+d8).
- `rv-instrumentation-dexlib2` — DEX-native pipeline (gh52).

The shared `assets/keystore.jks` (used by both `apksigner` and `jarsigner`)
lives here. AspectJ-specific assets live in `rv-instrumentation-ajc/assets/`.

```python
from rv_instrumentation import (
    Instrumenter,
    InstrumentationResults,
    InstrumentationError,
    get_instrumenter,
)

instrumenter = get_instrumenter("ajc", config)
results = instrumenter.instrument_apks(apks_dir, results_dir)
```

See `CLAUDE.md` for module-level guidance and `docs/architecture.md` for the
dependency-graph rationale.
