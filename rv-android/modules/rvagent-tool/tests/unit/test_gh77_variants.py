"""
Guard tests for the gh77 rvagent-tool experimental-arm policy (INV-RVA-01..06).

Mirrors the aperv-tool guard pattern (`modules/aperv-tool/tests/test_aperv_tool.py`):
introspect the frozen variants and the variant->RVAgentConfig mapping, never build a
strategy. The single source of truth for which config keys are *arm-defining* is the
agent-side kill-switch registry `RV_STEERING_FLAGS` (rv_agent
`strategies/rvagent_strategy/ranking/pipeline.py`), kept in sync with the config's
`arm_defining` fields by INV-AGT-43. The tool keeps a pinned local copy
(`RV_STEERING_OFF`) so registration stays free of the rv_agent import; the first test
below fails if the two ever drift.
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.util.error.exceptions import RVValidationError

# SoT: the agent kill-switch registry (every arm-defining flag -> off value).
from rv_agent.strategies.rvagent_strategy.ranking.pipeline import RV_STEERING_FLAGS
from rvagent_tool.tools.rvagent.config import (
    RV_STEERING_OFF,
    RV_TUNING_PARAMS,
    build_agent_config_dict,
)
from rvagent_tool.tools.rvagent.tool import RVAgentTool

# Set of arm-defining keys, derived from the registry (Decision A: never hardcoded).
ARM_DEFINING_KEYS = set(RV_STEERING_FLAGS)

# LLM arms whose isolation is asserted (INV-RVA-04). `default` is the multimode alias;
# `thorough` is a multimode tuning — both belong to the LLM family and set steering off.
LLM_ARMS = ("multimode", "llm_only", "default", "thorough")

# No arm may impose an artificial LLM call limit (project policy, INV-RVA-04).
_FORBIDDEN_LLM_LIMIT_KEYS = {
    "llm_max_calls",
    "max_llm_calls",
    "llm_call_limit",
    "llm_call_budget",
    "max_llm_requests",
    "llm_request_limit",
}


def _non_off(off_value):
    """Return a value distinct from the given off value (bool before int)."""
    if isinstance(off_value, bool):
        return not off_value
    if isinstance(off_value, (int, float)):
        return off_value + 1
    return "on"


class TestArmDefiningSoT:
    """The tool's pinned copy must equal the agent kill-switch registry (INV-RVA-01/02)."""

    def test_steering_off_equals_registry(self):
        # Dict equality pins BOTH the key set and each off value: any new steering
        # flag added to the agent registry (or a changed off value) fails here until
        # RV_STEERING_OFF is updated to match. This is the drift guard (Decision A/B).
        assert RV_STEERING_OFF == RV_STEERING_FLAGS

    def test_arm_defining_key_count(self):
        # Explicit count so an accidental add/remove gives a pointed failure.
        assert len(RV_STEERING_OFF) == 15
        assert len(ARM_DEFINING_KEYS) == 15

    def test_tuning_params_are_not_arm_defining(self):
        # pure_mode (kill-switch driver), seed, and gate-subordinate cadence/cap knobs
        # are mapped but MUST NOT be arm-defining (INV-RVA-02 / aperv precedent).
        assert set(RV_TUNING_PARAMS).isdisjoint(ARM_DEFINING_KEYS)


class TestArmVariants:
    """Every frozen variant sets every arm-defining key explicitly (INV-RVA-01/03/04)."""

    def test_every_variant_sets_every_arm_defining_key(self):
        # The executable explicitness guard: no exemptions (Decision C).
        variants = RVAgentTool.get_variants()
        for name, cfg in variants.items():
            missing = ARM_DEFINING_KEYS - set(cfg)
            assert not missing, f"variant {name!r} missing arm-defining keys: {sorted(missing)}"

    def test_expected_variants_present(self):
        variants = RVAgentTool.get_variants()
        for name in ("pure_algorithm", "multimode", "llm_only"):
            assert name in variants, f"missing frozen arm {name!r}"

    def test_pure_algorithm_sets_kill_switch_and_offs(self):
        # INV-RVA-03 + spec scenario "pure_algorithm Sets the Kill-Switch".
        cfg = RVAgentTool.get_variants()["pure_algorithm"]
        assert cfg["pure_mode"] is True
        assert cfg["agent_mode"] == "pure_algorithm"
        for key in ARM_DEFINING_KEYS:
            assert cfg[key] == RV_STEERING_FLAGS[key], f"{key} not at off value in pure arm"

    def test_llm_arms_disable_all_steering(self):
        # INV-RVA-04 + spec scenario "LLM and Steering Arms Are Isolated".
        variants = RVAgentTool.get_variants()
        for name in LLM_ARMS:
            cfg = variants[name]
            assert cfg["pure_mode"] is False
            for key in ARM_DEFINING_KEYS:
                assert cfg[key] == RV_STEERING_FLAGS[key], f"{name}:{key} steering not off"

    def test_mop_frontier_arm_calibrated_weights(self):
        # Frozen steering arm from the 7.7 calibration smoke: the two frontier
        # weights are on at their calibrated values, every other arm-defining key
        # is off, and no LLM (agent_mode pure_algorithm, pure_mode False).
        cfg = RVAgentTool.get_variants()["mop_frontier"]
        assert cfg["pure_mode"] is False
        assert cfg["agent_mode"] == "pure_algorithm"
        assert cfg["mop_frontier_weight"] == 200.0
        assert cfg["wtg_guided_score"] == 150.0
        for key in ARM_DEFINING_KEYS:
            if key in ("mop_frontier_weight", "wtg_guided_score"):
                continue
            assert cfg[key] == RV_STEERING_FLAGS[key], f"{key} not at off value in mop_frontier arm"

    def test_no_variant_imposes_llm_call_limit(self):
        # INV-RVA-04: no artificial LLM call-count limit key in any arm.
        for name, cfg in RVAgentTool.get_variants().items():
            offenders = _FORBIDDEN_LLM_LIMIT_KEYS & set(cfg)
            assert not offenders, f"variant {name!r} has forbidden LLM-limit key(s): {offenders}"


class TestMappingCompleteness:
    """Every arm-defining key reaches RVAgentConfig via build_agent_config_dict (INV-RVA-02)."""

    def _make_task_app(self):
        task = MagicMock()
        task.config = None
        task.static_data = None
        task.results_dir = None
        app = MagicMock()
        app.package_name = "br.unb.cic.cryptoapp"
        return task, app

    def test_every_arm_defining_key_flows_through(self):
        task, app = self._make_task_app()
        tool_config = {key: _non_off(off) for key, off in RV_STEERING_FLAGS.items()}
        config_dict = build_agent_config_dict(task, app, tool_config)
        for key in ARM_DEFINING_KEYS:
            assert key in config_dict, f"arm-defining key {key!r} dropped by the mapping"
            assert config_dict[key] == tool_config[key]

    def test_pure_mode_flows_through(self):
        # pure_mode is not arm-defining but must reach the config (drives kill-switch).
        task, app = self._make_task_app()
        config_dict = build_agent_config_dict(task, app, {"pure_mode": True})
        assert config_dict["pure_mode"] is True

    def test_tuning_knobs_flow_through(self):
        # launch cadence/cap + component cadence: mapped for calibration/@overrides,
        # not required in every variant (mapped-but-not-arm-defining, aperv precedent).
        task, app = self._make_task_app()
        knobs = {"launch_cadence": 25, "launch_cap": 3, "component_percentage": 0.2}
        config_dict = build_agent_config_dict(task, app, knobs)
        for key, value in knobs.items():
            assert key not in ARM_DEFINING_KEYS
            assert config_dict[key] == value


class TestSeedPropagation:
    """Seed passes through variant/@override unchanged to RVAgentConfig (FR19)."""

    def _make_task_app(self):
        task = MagicMock()
        task.config = None
        task.static_data = None
        task.results_dir = None
        app = MagicMock()
        app.package_name = "br.unb.cic.cryptoapp"
        return task, app

    def test_seed_flows_to_config(self):
        # Spec scenario "Seed Pass-Through": rvagent:pure_algorithm@seed=42.
        task, app = self._make_task_app()
        config_dict = build_agent_config_dict(task, app, {"seed": 42})
        assert config_dict["seed"] == 42

    def test_no_seed_omits_seed(self):
        task, app = self._make_task_app()
        config_dict = build_agent_config_dict(task, app, {})
        assert "seed" not in config_dict


def _configured_tool(variant_config=None):
    tool = RVAgentTool()
    tool.configure(variant_config or {"agent_mode": "pure_algorithm", "strategy": "rvagent"})
    return tool


def _make_task_app(static_data=None):
    task = MagicMock()
    task.config = None
    task.static_data = static_data
    task.results_dir = None
    app = MagicMock()
    app.package_name = "br.unb.cic.cryptoapp"
    return task, app


class TestTeardownLifecycle:
    """Teardown runs in a finally on success and on exception (INV-RVA-05)."""

    def test_teardown_on_success(self):
        tool = _configured_tool()
        task, app = _make_task_app()
        fake_agent = MagicMock()
        fake_agent.run.return_value = {"iterations": 3, "unique_states": 2}
        with patch(
            "rv_agent.agent.agent_factory.AgentFactory.create_agent",
            return_value=fake_agent,
        ):
            tool.execute_tool_specific_logic(task, app)
        fake_agent.device.stop_app.assert_called_once_with(app.package_name)

    def test_teardown_on_exception(self):
        # Spec scenario "Teardown Runs on Exception": the session is still stopped.
        tool = _configured_tool()
        task, app = _make_task_app()
        fake_agent = MagicMock()
        fake_agent.run.side_effect = RuntimeError("exploration blew up")
        with patch(
            "rv_agent.agent.agent_factory.AgentFactory.create_agent",
            return_value=fake_agent,
        ):
            with pytest.raises(RuntimeError):
                tool.execute_tool_specific_logic(task, app)
        fake_agent.device.stop_app.assert_called_once_with(app.package_name)


class TestStaticDataFailFast:
    """Present-but-invalid static data aborts before any device time (INV-RVA)."""

    def test_invalid_static_data_aborts_before_device(self):
        # Spec scenario "Invalid Static Data Aborts Before Session": wtg missing ->
        # error names wtg, and AgentFactory (which creates the device) is never called.
        invalid = MagicMock()
        invalid.wtg = None  # required field missing -> RVValidationError naming 'wtg'
        tool = _configured_tool()
        task, app = _make_task_app(static_data=invalid)
        with patch(
            "rv_agent.agent.agent_factory.AgentFactory.create_agent"
        ) as create_agent:
            with pytest.raises(RVValidationError) as exc:
                tool.execute_tool_specific_logic(task, app)
        assert "wtg" in str(exc.value)
        create_agent.assert_not_called()

    def test_absent_static_data_proceeds_degraded(self):
        # Spec scenario "Absent Static Data Proceeds Degraded": None is allowed.
        tool = _configured_tool()
        task, app = _make_task_app(static_data=None)
        fake_agent = MagicMock()
        fake_agent.run.return_value = {"iterations": 1, "unique_states": 1}
        with patch(
            "rv_agent.agent.agent_factory.AgentFactory.create_agent",
            return_value=fake_agent,
        ) as create_agent:
            tool.execute_tool_specific_logic(task, app)
        create_agent.assert_called_once()
        fake_agent.device.stop_app.assert_called_once_with(app.package_name)
