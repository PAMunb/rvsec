"""Python wrapper for the DEX-native weaver (rvsec-instrumentation-dexlib2 Java CLI).

Spec-set agnostic: the underlying weaver handles JCA and Generic
specification sets identically; this module is a thin subprocess shim.
"""

from rv_instrumentation_dexlib2.config import DexlibInstrumentationConfig
from rv_instrumentation_dexlib2.dexlib_instrumentation import DexlibInstrumentation
from rv_instrumentation_dexlib2.errors import (
    DescriptorParseError,
    MissingDescriptorError,
    UnsupportedAspectConstructError,
)

__all__ = [
    "DexlibInstrumentation",
    "DexlibInstrumentationConfig",
    "DescriptorParseError",
    "MissingDescriptorError",
    "UnsupportedAspectConstructError",
]
