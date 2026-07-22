"""
Test helpers for rv-experiment tests.

These are plain functions (not fixtures) that can be imported directly.
"""

from rv_android_core.domain.task import ToolConfig


def make_config(tmp_apk_dir, tool_configs=None, **overrides):
    """Create a valid ExperimentConfig with required fields.

    ExperimentConfig.validate() requires apks_dir to exist and contain .apk files.
    This helper provides sensible defaults that pass validation.
    """
    from rv_experiment.config import ExperimentConfig

    kwargs = {
        "name": "test_experiment",
        "tool_configs": (
            tool_configs if tool_configs is not None else [ToolConfig(name="monkey")]
        ),
        "apks_dir": tmp_apk_dir,
        "specification_set": "jca",
        "generate_monitors": False,
        "instrument_apks": False,
        "run_static_analysis": False,
    }
    kwargs.update(overrides)
    return ExperimentConfig(**kwargs)
