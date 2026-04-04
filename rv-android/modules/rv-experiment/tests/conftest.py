"""
Shared fixtures for rv-experiment tests.
"""

import pytest

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
