"""Pure abstractions module for instrumentation.

Provides the ``Instrumenter`` ABC and shared Pydantic result types used by all
variant impls (``rv-instrumentation-ajc``, ``rv-instrumentation-dexlib2``) and
re-exported by the parent ``rv-instrumentation``. No logic, no factory, no
assets — only contract.
"""

from rv_instrumentation_core.instrumenter import Instrumenter
from rv_instrumentation_core.results import InstrumentationError, InstrumentationResults

__all__ = ["Instrumenter", "InstrumentationError", "InstrumentationResults"]
