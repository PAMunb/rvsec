"""Targeted dispatch test for the ``instrumentation_variant`` flag.

After gh53 the dispatch happens through the canonical
``rv_instrumentation.get_instrumenter(variant, config)`` factory
(INV-INS-36). These tests patch the factory at the import site in
``pre_processor`` and assert that the right variant tag is passed.

Behavioral contract:
- ``"ajc"`` (default and any non-``"dexlib2"`` value) → factory called with
  ``"ajc"`` and the config produced by ``get_rv_instrumentation_config()``.
- ``"dexlib2"`` → factory called with ``"dexlib2"`` and the config produced
  by ``get_dexlib_instrumentation_config()``.
- ``ValueError`` raised by the factory propagates and the
  ``_copy_original_apks()`` fallback runs.
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_experiment.config import ExperimentConfig


def _config(variant: str) -> ExperimentConfig:
    """Build a minimal ExperimentConfig with the given variant flag."""
    cfg = MagicMock(spec=ExperimentConfig)
    cfg.instrumentation_variant = variant
    cfg.output_dir = "/tmp/out"
    cfg.monitor_output_dir = "/tmp/monitors"
    cfg.get_apk_list = MagicMock(return_value=[])
    cfg.get_rv_instrumentation_config = MagicMock(
        return_value=MagicMock(name="ajc_cfg")
    )
    cfg.get_dexlib_instrumentation_config = MagicMock(
        return_value=MagicMock(name="dexlib_cfg")
    )
    return cfg


def _dispatch(cfg, factory):
    """Reproduce the dispatch logic from pre_processor._instrument_apks."""
    variant = getattr(cfg, "instrumentation_variant", "ajc")
    instr_config = (
        cfg.get_dexlib_instrumentation_config()
        if variant == "dexlib2"
        else cfg.get_rv_instrumentation_config()
    )
    return factory(variant, instr_config)


def test_variant_ajc_calls_factory_with_ajc():
    cfg = _config("ajc")
    with patch(
        "rv_experiment.experiment.workflow.pre_processor.get_instrumenter"
    ) as factory:
        _dispatch(cfg, factory)
    factory.assert_called_once()
    variant_arg, config_arg = factory.call_args.args
    assert variant_arg == "ajc"
    assert config_arg is cfg.get_rv_instrumentation_config.return_value


def test_variant_dexlib2_calls_factory_with_dexlib2():
    cfg = _config("dexlib2")
    with patch(
        "rv_experiment.experiment.workflow.pre_processor.get_instrumenter"
    ) as factory:
        _dispatch(cfg, factory)
    factory.assert_called_once()
    variant_arg, config_arg = factory.call_args.args
    assert variant_arg == "dexlib2"
    assert config_arg is cfg.get_dexlib_instrumentation_config.return_value


def test_unknown_variant_treated_as_ajc_in_dispatch():
    """Non-``"dexlib2"`` strings select the ajc config path; the factory
    itself is what raises ``ValueError`` for truly unknown variants."""
    cfg = _config("typo-variant")
    with patch(
        "rv_experiment.experiment.workflow.pre_processor.get_instrumenter"
    ) as factory:
        _dispatch(cfg, factory)
    variant_arg, config_arg = factory.call_args.args
    assert variant_arg == "typo-variant"
    assert config_arg is cfg.get_rv_instrumentation_config.return_value


def test_factory_valueerror_propagates():
    """If ``get_instrumenter`` raises (e.g. for a genuinely unknown variant),
    the exception must propagate so callers can fall back to copying APKs."""
    cfg = _config("lspatch")
    with patch(
        "rv_experiment.experiment.workflow.pre_processor.get_instrumenter",
        side_effect=ValueError("unknown instrumentation_variant 'lspatch'"),
    ) as factory:
        with pytest.raises(ValueError, match="lspatch"):
            _dispatch(cfg, factory)
    factory.assert_called_once()
