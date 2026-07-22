"""Tests for gh26 exploration strategy config fields and constants."""

import pytest
from pydantic import ValidationError
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.constants import RVAgentConstants


class TestNewConfigFields:
    """Verify 6 new config fields have correct defaults and constraints."""

    def _make_config(self, **overrides):
        defaults = {"package_name": "com.test.app"}
        defaults.update(overrides)
        return RVAgentConfig(**defaults)

    def test_backtrack_saturation_threshold_default(self):
        config = self._make_config()
        assert config.backtrack_saturation_threshold == 0.8

    def test_mop_nav_weight_default(self):
        config = self._make_config()
        assert config.mop_nav_weight == 2.0

    def test_mop_max_input_variations_default(self):
        config = self._make_config()
        assert config.mop_max_input_variations == 11

    def test_reward_gamma_default(self):
        config = self._make_config()
        assert config.reward_gamma == 0.8

    def test_reward_score_weight_default(self):
        config = self._make_config()
        assert config.reward_score_weight == 1.0

    def test_coverage_density_weight_default(self):
        config = self._make_config()
        assert config.coverage_density_weight == 200.0

    @pytest.mark.parametrize(
        "field,bad_value",
        [
            ("backtrack_saturation_threshold", 0.4),
            ("backtrack_saturation_threshold", 1.1),
            ("mop_nav_weight", 0.3),
            ("mop_nav_weight", 5.5),
            ("mop_max_input_variations", 4),
            ("mop_max_input_variations", 16),
            ("reward_gamma", 0.49),
            ("reward_gamma", 1.0),
            ("reward_score_weight", 0.05),
            ("reward_score_weight", 5.5),
            ("coverage_density_weight", 40.0),
            ("coverage_density_weight", 650.0),
        ],
    )
    def test_range_constraints_reject_out_of_bounds(self, field, bad_value):
        with pytest.raises(ValidationError):
            self._make_config(**{field: bad_value})


class TestUpdatedScorerDefaults:
    """Verify updated scorer weight defaults from task 1.2."""

    def _make_config(self):
        return RVAgentConfig(package_name="com.test.app")

    def test_mop_direct_score(self):
        assert self._make_config().mop_direct_score == 500.0

    def test_mop_transitive_score(self):
        assert self._make_config().mop_transitive_score == 300.0

    def test_wtg_guided_score(self):
        assert self._make_config().wtg_guided_score == 150.0

    def test_unsaturated_bonus(self):
        assert self._make_config().unsaturated_bonus == 100.0

    def test_visitation_penalty_factor(self):
        assert self._make_config().visitation_penalty_factor == -15.0

    def test_stochastic_probability(self):
        assert self._make_config().stochastic_probability == 0.15


class TestModuleConstants:
    """Verify 5 module-level constants from task 1.1."""

    def test_path_buffer_enabled(self):
        assert RVAgentConstants.PATH_BUFFER_ENABLED is True

    def test_max_backtrack_hops(self):
        assert RVAgentConstants.MAX_BACKTRACK_HOPS == 8

    def test_max_coverage_hops(self):
        assert RVAgentConstants.MAX_COVERAGE_HOPS == 5

    def test_reward_mop_weight(self):
        assert RVAgentConstants.REWARD_MOP_WEIGHT == 5.0

    def test_reward_propagation_n(self):
        assert RVAgentConstants.REWARD_PROPAGATION_N == 5
