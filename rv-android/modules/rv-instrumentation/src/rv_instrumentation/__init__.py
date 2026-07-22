"""Parent canonical module for instrumentation.

Re-exports the abstractions from ``rv-instrumentation-core`` and exposes the
``get_instrumenter`` factory that dispatches to concrete variants
(``rv-instrumentation-ajc``, ``rv-instrumentation-dexlib2``). The shared
``assets/keystore.jks`` resource lives here.
"""

from rv_instrumentation_core import (
    Instrumenter,
    InstrumentationError,
    InstrumentationResults,
)

from rv_instrumentation.factory import get_instrumenter

__all__ = [
    "Instrumenter",
    "InstrumentationError",
    "InstrumentationResults",
    "get_instrumenter",
]
