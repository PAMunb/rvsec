"""
Tests for ScoringPipeline assembly and the pure_mode kill-switch.

Covers INV-AGT-42 (single assembly point + one [RV-ARCH] audit line),
INV-AGT-43 (pure_mode forces every registered steering flag off/0, logs each
forced key; every arm-defining field must be registered — completeness and
fail-fast).
"""

import logging

import pytest
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.strategies.rvagent_strategy.ranking import pipeline as pipeline_mod
from rv_agent.strategies.rvagent_strategy.ranking.pipeline import (
    RV_STEERING_FLAGS,
    ScoringPipeline,
)
from rv_android_core.util.error.exceptions import ConfigurationError

BASE_POLICY_SCORERS = {
    "SaturationScorer",
    "ComponentPriorityScorer",
    "StrengthScorer",
    "GradualDecayScorer",
    "CoverageDensityScorer",
    "SystemElementFilter",
    "VisitationPenaltyScorer",
}


def _config(**overrides):
    return RVAgentConfig(package_name="test.app", **overrides)


def _arch_lines(caplog):
    """Return the [RV-ARCH] composition lines (excludes forced-key lines)."""
    return [
        r.message
        for r in caplog.records
        if r.name == pipeline_mod.__name__ and "[RV-ARCH] scorers=" in r.getMessage()
    ]


class TestAssemblyAuditLog:
    """INV-AGT-42: exactly one [RV-ARCH] line describing the assembled arm."""

    def test_single_audit_line_emitted(self, caplog):
        with caplog.at_level(logging.INFO, logger=pipeline_mod.__name__):
            ScoringPipeline.from_config(_config())
        lines = _arch_lines(caplog)
        assert len(lines) == 1

    def test_audit_line_lists_scorers_and_flags(self, caplog):
        with caplog.at_level(logging.INFO, logger=pipeline_mod.__name__):
            ScoringPipeline.from_config(_config(mop_frontier_weight=250.0))
        line = _arch_lines(caplog)[0]
        # Default config keeps MOP/WTG steering active.
        assert "MopScorer" in line
        assert "WtgScorer" in line
        # Effective flag values are reported for auditability.
        assert "'mop_frontier_weight': 250.0" in line

    def test_default_config_assembles_all_nine_scorers(self):
        ranker = ScoringPipeline.from_config(_config())
        names = [type(s).__name__ for s in ranker.scorers]
        assert names == [
            "MopScorer",
            "WtgScorer",
            "SaturationScorer",
            "ComponentPriorityScorer",
            "StrengthScorer",
            "GradualDecayScorer",
            "CoverageDensityScorer",
            "SystemElementFilter",
            "VisitationPenaltyScorer",
        ]


class TestPureModeKillSwitch:
    """INV-AGT-43: pure_mode forces every registered flag off/0 and logs it."""

    def test_pure_mode_forces_all_registered_flags(self):
        # Set several steering flags on, then let pure_mode override them.
        config = _config(
            pure_mode=True,
            mop_frontier_weight=250.0,
            trigger_mop_first=True,
            component_trigger_enabled=True,
            back_menu_pick_cap=3,
            foreign_activity_guard=True,
        )
        ScoringPipeline.from_config(config)
        for name, off_value in RV_STEERING_FLAGS.items():
            assert getattr(config, name) == off_value, name

    def test_pure_mode_excludes_mop_and_wtg_scorers(self):
        ranker = ScoringPipeline.from_config(_config(pure_mode=True))
        names = {type(s).__name__ for s in ranker.scorers}
        assert names == BASE_POLICY_SCORERS
        assert "MopScorer" not in names
        assert "WtgScorer" not in names

    def test_pure_mode_logs_each_forced_key(self, caplog):
        with caplog.at_level(logging.INFO, logger=pipeline_mod.__name__):
            ScoringPipeline.from_config(
                _config(pure_mode=True, mop_frontier_weight=250.0, trigger_mop_first=True)
            )
        forced = [
            r.getMessage() for r in caplog.records if "pure_mode forced" in r.getMessage()
        ]
        # The three non-default steering flags (plus the non-zero MOP/WTG
        # weight defaults) are each logged as forced.
        forced_keys = {msg.split("forced ")[1].split(":")[0] for msg in forced}
        assert {"mop_frontier_weight", "trigger_mop_first"} <= forced_keys
        assert {"mop_direct_score", "mop_transitive_score", "wtg_guided_score"} <= forced_keys

    def test_pure_mode_does_not_force_seed(self):
        # seed is determinism, not steering — pure_mode must leave it alone.
        config = _config(pure_mode=True, seed=42)
        ScoringPipeline.from_config(config)
        assert config.seed == 42


class TestRegistryCompleteness:
    """INV-AGT-43: every arm-defining field is registered; fail-fast otherwise."""

    def test_registry_matches_arm_defining_fields(self):
        arm_fields = {
            name
            for name, field in RVAgentConfig.model_fields.items()
            if (field.json_schema_extra or {}).get("arm_defining")
        }
        assert arm_fields == set(RV_STEERING_FLAGS), (
            "Every arm_defining config field must be registered in "
            "RV_STEERING_FLAGS, and vice versa"
        )

    def test_unregistered_arm_defining_flag_fails_fast(self, monkeypatch):
        # Simulate a new arm-defining field that nobody added to the registry
        # by removing one existing entry from the registry the pipeline reads.
        reduced = dict(RV_STEERING_FLAGS)
        reduced.pop("mop_frontier_weight")
        monkeypatch.setattr(pipeline_mod, "RV_STEERING_FLAGS", reduced)

        with pytest.raises(ConfigurationError, match="mop_frontier_weight"):
            ScoringPipeline.from_config(_config())
