"""rv-instrumentation-ajc — AspectJ-based APK instrumentation variant.

Implements the legacy dex2jar+ajc+d8 instrumentation pipeline. ``AjcInstrumentation``
inherits from ``Instrumenter`` (``rv_instrumentation_core``); shared result types
(``InstrumentationResults``, ``InstrumentationError``) live in ``-core``.
"""

from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation
from rv_instrumentation_ajc.config import (
    AjcInstrumentationConfig,
    ConfigurationError,
    ConfigurationSummary,
    Dex2jarTools,
)

__all__ = [
    "AjcInstrumentation",
    "AjcInstrumentationConfig",
    "ConfigurationError",
    "ConfigurationSummary",
    "Dex2jarTools",
]
