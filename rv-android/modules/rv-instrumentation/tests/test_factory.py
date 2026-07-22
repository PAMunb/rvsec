"""Tests for the parent ``get_instrumenter`` factory.

Verifies dispatch correctness, lazy-import behaviour (selecting one variant
does not force importing the other), error path for unknown variants, and ABC
subclass relationship.
"""

import sys
from unittest.mock import MagicMock

import pytest

from rv_instrumentation import Instrumenter, get_instrumenter


def _drop(*module_prefixes):
    for name in list(sys.modules):
        if any(name == p or name.startswith(p + ".") for p in module_prefixes):
            del sys.modules[name]


def test_ajc_returns_subclass_and_does_not_import_dexlib2():
    _drop("rv_instrumentation_dexlib2")
    instrumenter = get_instrumenter("ajc", MagicMock())
    from rv_instrumentation_ajc.ajc_instrumentation import AjcInstrumentation

    assert isinstance(instrumenter, AjcInstrumentation)
    assert isinstance(instrumenter, Instrumenter)
    assert "rv_instrumentation_dexlib2" not in sys.modules


def test_dexlib2_returns_subclass_and_does_not_import_ajc():
    _drop("rv_instrumentation_ajc")
    config = MagicMock()
    instrumenter = get_instrumenter("dexlib2", config)
    from rv_instrumentation_dexlib2 import DexlibInstrumentation

    assert isinstance(instrumenter, DexlibInstrumentation)
    assert isinstance(instrumenter, Instrumenter)
    assert "rv_instrumentation_ajc" not in sys.modules


def test_unknown_variant_raises_valueerror_with_helpful_message():
    with pytest.raises(ValueError) as exc:
        get_instrumenter("lspatch", MagicMock())
    msg = str(exc.value)
    assert "lspatch" in msg
    assert "ajc" in msg
    assert "dexlib2" in msg
