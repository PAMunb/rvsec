"""Factory for instrumentation variants — single dispatch site (INV-INS-36)."""

from __future__ import annotations

from rv_instrumentation_core import Instrumenter


def get_instrumenter(variant: str, config) -> Instrumenter:
    """Return the configured instrumenter for the given variant.

    Lazy imports keep variant modules optional at import time. Selecting "ajc"
    does NOT force importing ``rv_instrumentation_dexlib2``, and vice versa —
    consumers in environments where one variant's runtime is absent (e.g. a
    Docker layer that only built ajc deps) can still call this factory for
    the available variant.
    """
    if variant == "ajc":
        from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation

        return AjcInstrumentation(config)
    if variant == "dexlib2":
        from rv_instrumentation_dexlib2 import DexlibInstrumentation

        return DexlibInstrumentation(config)
    raise ValueError(
        f"unknown instrumentation_variant {variant!r}; valid: 'ajc', 'dexlib2'"
    )
