"""Verify CLI > env > default precedence for analysis_timeout / jvm_memory.

gh55 INV-EXP-32: every CLI flag for tunable values has a corresponding `ENV_*`
env var of equivalent semantics. Resolution order is **CLI flag > env var >
Pydantic default**. This test exercises three modes for each of two flags
(6 cases total).

The CLI value lives on `ExperimentConfig.analysis_timeout` /
`ExperimentConfig.jvm_memory` (set by `_create_experiment_config_from_cli`).
The env var read happens inside `get_static_analysis_config()`. The Pydantic
default comes from `RVStaticAnalysisConfig` itself.
"""

from __future__ import annotations

import pytest

from rv_android_core.constants import ENV_JVM_MEMORY, ENV_SA_TIMEOUT
from rv_experiment.config import ExperimentConfig


@pytest.fixture
def rvsec_home(tmp_path, monkeypatch):
    """RVSEC_HOME pointing at a real (empty) directory. The static-analysis
    config we build does not actually need the GATOR jars to exist — it only
    validates the path on construction."""
    rvsec_dir = tmp_path / "rvsec_home"
    rvsec_dir.mkdir()
    (rvsec_dir / "rv-android" / "lib" / "gator").mkdir(parents=True)
    monkeypatch.setenv("RVSEC_HOME", str(rvsec_dir))
    return rvsec_dir


def _make_config(*, analysis_timeout=None, jvm_memory=None) -> ExperimentConfig:
    """Build a minimal valid ExperimentConfig with optional CLI overrides."""
    return ExperimentConfig(
        name="precedence_test",
        analysis_timeout=analysis_timeout,
        jvm_memory=jvm_memory,
    )


# ----------------------------- analysis_timeout -----------------------------


def test_analysis_timeout_env_only(rvsec_home, monkeypatch):
    """Mode 2: only env var set → that wins over the Pydantic default."""
    monkeypatch.setenv(ENV_SA_TIMEOUT, "900")
    cfg = _make_config()
    sa_cfg = cfg.get_static_analysis_config()
    assert sa_cfg.analysis_timeout == 900


def test_analysis_timeout_cli_only(rvsec_home, monkeypatch):
    """Mode 3: only CLI flag set (env unset) → CLI value wins."""
    monkeypatch.delenv(ENV_SA_TIMEOUT, raising=False)
    cfg = _make_config(analysis_timeout=600)
    sa_cfg = cfg.get_static_analysis_config()
    assert sa_cfg.analysis_timeout == 600


def test_analysis_timeout_cli_wins_over_env(rvsec_home, monkeypatch):
    """Mode 1: both set → CLI takes precedence."""
    monkeypatch.setenv(ENV_SA_TIMEOUT, "900")
    cfg = _make_config(analysis_timeout=600)
    sa_cfg = cfg.get_static_analysis_config()
    assert sa_cfg.analysis_timeout == 600


# ------------------------------- jvm_memory ---------------------------------


def test_jvm_memory_env_only(rvsec_home, monkeypatch):
    """Mode 2 for jvm_memory."""
    monkeypatch.setenv(ENV_JVM_MEMORY, "8g")
    cfg = _make_config()
    sa_cfg = cfg.get_static_analysis_config()
    assert sa_cfg.jvm_memory == "8g"


def test_jvm_memory_cli_only(rvsec_home, monkeypatch):
    """Mode 3 for jvm_memory."""
    monkeypatch.delenv(ENV_JVM_MEMORY, raising=False)
    cfg = _make_config(jvm_memory="6g")
    sa_cfg = cfg.get_static_analysis_config()
    assert sa_cfg.jvm_memory == "6g"


def test_jvm_memory_cli_wins_over_env(rvsec_home, monkeypatch):
    """Mode 1 for jvm_memory."""
    monkeypatch.setenv(ENV_JVM_MEMORY, "8g")
    cfg = _make_config(jvm_memory="6g")
    sa_cfg = cfg.get_static_analysis_config()
    assert sa_cfg.jvm_memory == "6g"
