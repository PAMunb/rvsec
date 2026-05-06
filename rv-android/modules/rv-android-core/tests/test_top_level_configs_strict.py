"""Verify ExperimentConfig and PlatformConfig declare extra='forbid' explicitly.

gh55 INV-CORE-32 requires that the top-level Pydantic configuration models
exposed at the user-input boundary state `model_config = ConfigDict(extra="forbid")`
at the class body level — not only via `BaseValidatedModel` inheritance. The
explicit declaration is what makes the entrypoint allow-list + ENV_* registry
contract auditable from the boundary class itself.

This test verifies:
1. The class body source contains the literal `model_config = ConfigDict(extra="forbid")`.
2. Instantiating the model with an extra field raises `ValidationError` naming the field.
"""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from rv_experiment.config import ExperimentConfig
from rv_platform.config.platform_config import PlatformConfig


def _source_contains_extra_forbid(cls) -> bool:
    src = inspect.getsource(cls)
    return 'model_config = ConfigDict(extra="forbid")' in src


def test_experiment_config_declares_extra_forbid():
    assert _source_contains_extra_forbid(ExperimentConfig), (
        "ExperimentConfig MUST declare `model_config = ConfigDict(extra=\"forbid\")` "
        "at the class body (gh55 INV-CORE-32). Inheriting from BaseValidatedModel "
        "is not enough — the contract must be visible at the boundary."
    )


def test_platform_config_declares_extra_forbid():
    assert _source_contains_extra_forbid(PlatformConfig), (
        "PlatformConfig MUST declare `model_config = ConfigDict(extra=\"forbid\")` "
        "at the class body (gh55 INV-CORE-32)."
    )


def test_experiment_config_rejects_unknown_field():
    with pytest.raises(ValidationError) as exc_info:
        ExperimentConfig(unknown_field="value")
    assert "unknown_field" in str(exc_info.value)


def test_platform_config_rejects_unknown_field():
    with pytest.raises(ValidationError) as exc_info:
        PlatformConfig(
            apks_dir="./apks",
            tools=[],
            unknown_field="value",
        )
    assert "unknown_field" in str(exc_info.value)
