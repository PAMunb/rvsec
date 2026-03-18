"""
Shared fixtures for rv-experiment tests.
"""

import pytest
from pathlib import Path

from rv_android_core.domain.task import ToolConfig


@pytest.fixture
def tmp_apk_dir(tmp_path):
    """Create a temporary directory with dummy APK files for config validation."""
    apk_dir = tmp_path / "apks"
    apk_dir.mkdir()
    (apk_dir / "app1.apk").write_bytes(b"fake-apk-1")
    (apk_dir / "app2.apk").write_bytes(b"fake-apk-2")
    return str(apk_dir)


@pytest.fixture
def tmp_results_dir(tmp_path):
    """Create a temporary results directory."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    return str(results_dir)


@pytest.fixture
def minimal_tool_configs():
    """Minimal valid tool configs for ExperimentConfig."""
    return [ToolConfig(name="monkey")]


def create_fake_rvsec_tree(tmp_path, spec_set="jca"):
    """Create a minimal fake RVSEC directory tree for JIT config tests.

    Returns the rvsec_dir path. Creates javamop/rv-monitor binaries with +x,
    and the spec set directory.
    """
    import os

    rvsec_dir = tmp_path / "rvsec"
    mop_dir = rvsec_dir / "rvsec" / "rvsec-mop" / "src" / "main" / "resources"
    (mop_dir / spec_set).mkdir(parents=True)
    (mop_dir / "aspect").mkdir(parents=True)

    javamop = rvsec_dir / "javamop" / "bin" / "javamop"
    javamop.parent.mkdir(parents=True)
    javamop.write_text("#!/bin/sh")
    os.chmod(javamop, 0o755)

    rvmonitor = rvsec_dir / "rv-monitor" / "bin" / "rv-monitor"
    rvmonitor.parent.mkdir(parents=True)
    rvmonitor.write_text("#!/bin/sh")
    os.chmod(rvmonitor, 0o755)

    return str(rvsec_dir)


def make_valid_config(tmp_apk_dir, tool_configs=None, **overrides):
    """Helper to create a valid ExperimentConfig with required fields.

    ExperimentConfig.validate() requires apks_dir to exist and contain .apk files.
    This helper provides sensible defaults that pass validation.
    """
    from rv_experiment.config import ExperimentConfig

    kwargs = {
        "name": "test_experiment",
        "tool_configs": tool_configs if tool_configs is not None else [ToolConfig(name="monkey")],
        "apks_dir": tmp_apk_dir,
        "specification_set": "jca",
        # Skip pre-processing to avoid RVSEC_HOME dependency
        "generate_monitors": False,
        "instrument_apks": False,
        "run_static_analysis": False,
    }
    kwargs.update(overrides)
    return ExperimentConfig(**kwargs)
