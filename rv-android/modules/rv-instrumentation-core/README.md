# rv-instrumentation-core

Pure abstractions for APK instrumentation: the `Instrumenter` ABC and the
shared Pydantic result types (`InstrumentationResults`, `InstrumentationError`).

This module has no business logic, factory, assets, or CLI. Concrete variants
(`rv-instrumentation-ajc`, `rv-instrumentation-dexlib2`) depend on it; the
parent `rv-instrumentation` re-exports from it and dispatches between variants
through its factory.

```python
from rv_instrumentation_core import (
    Instrumenter,
    InstrumentationResults,
    InstrumentationError,
)
```

See `docs/architecture.md` for the dependency graph rationale and `CLAUDE.md`
for module-level guidance.
