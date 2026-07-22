# Architecture — rv-instrumentation-core

Pure abstractions module for instrumentation. Holds the `Instrumenter` ABC and
the shared Pydantic result types (`InstrumentationResults`, `InstrumentationError`).
No logic, no factory, no assets, no CLI.

## Why a separate module

If the parent `rv-instrumentation` declared the ABC + shared types AND the
factory that imports concrete impls, dependency direction would form a cycle:

- `rv-instrumentation-ajc` needs the ABC → depends on parent.
- Parent's factory imports `AjcInstrumentation` → depends on `-ajc`.

Separating the abstractions into `-core` breaks that cycle: variants depend on
`-core` (only); the parent re-exports from `-core` and depends on the variants.
Setas só vão para baixo no grafo.

## Public API

```python
from rv_instrumentation_core import (
    Instrumenter,           # ABC — sole abstractmethod: instrument_apks
    InstrumentationResults, # Pydantic — success/total counts + variant tag
    InstrumentationError,   # Pydantic — code/tool/message/phase
)
```

Re-exported by `rv-instrumentation` so consumers can import either symbol from
the parent.

## Dependencies

```toml
dependencies = ["pydantic>=2.9.0", "rv-android-core"]
```

`rv-android-core` provides `BaseValidatedModel`. No dependency on impls
(`rv-instrumentation-ajc`, `rv-instrumentation-dexlib2`) — INV-INS-41.

## Variant pattern

Each concrete variant lives in its own module and depends on `-core`:

```
rv-instrumentation-core      ← rv-instrumentation-ajc
                             ← rv-instrumentation-dexlib2
                             ← rv-instrumentation (parent — re-exports + factory)
```

A new variant (e.g. LSPatch) creates `rv-instrumentation-lspatch` declaring
`-core` as its only `rv-instrumentation*` dependency, implements
`Instrumenter`, and is wired into the parent's factory.
