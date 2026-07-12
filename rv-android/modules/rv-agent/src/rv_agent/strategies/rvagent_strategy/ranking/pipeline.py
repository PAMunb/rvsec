"""
Single assembly point for the composite action-scoring pipeline.

`ScoringPipeline.from_config` is the ONLY place scorers are instantiated into
an `ActionRanker` (INV-AGT-42). Assembling in one place makes the active
experimental arm auditable: the pipeline logs its composition once at startup
as a single `[RV-ARCH]` line, and enforces the `pure_mode` kill-switch before
any scorer is built.

Arm auditability rests on two independent sources of truth that MUST agree:

1. Config fields carry ``json_schema_extra={"arm_defining": True}`` (declared in
   `config/agent_config.py`) to mark themselves as arm-defining — a flag whose
   value distinguishes one experimental arm from the base policy.
2. `RV_STEERING_FLAGS` below maps each such flag to its off/0 value — the value
   `pure_mode` forces it to.

`from_config` cross-checks the two: if a field is marked arm-defining but is
missing from `RV_STEERING_FLAGS`, assembly fails fast with `ConfigurationError`
(INV-AGT-43). This catches the contamination failure mode where a new steering
flag is added to the config but silently inherits a non-off default in some arm
because nobody wired it into the kill-switch. The mirror check — every registry
key is also a marked field — is covered by the registry-completeness unit test.

When `pure_mode` is True, every registered flag is forced to its off value
before assembly and each forced key is logged; the pipeline then degenerates to
the documented base policy (INV-AGT-44): the MOP/WTG steering scorers exclude
themselves (their weights are now 0) and only the always-active base-policy
scorers remain.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List

from pydantic import BaseModel
from rv_android_core.util.error.exceptions import ConfigurationError

from rv_agent.strategies.rvagent_strategy.ranking.action_ranker import ActionRanker
from rv_agent.strategies.rvagent_strategy.ranking.scorers import (
    ComponentPriorityScorer,
    CoverageDensityScorer,
    GradualDecayScorer,
    MopScorer,
    SaturationScorer,
    Scorer,
    StrengthScorer,
    SystemElementFilter,
    VisitationPenaltyScorer,
    WtgScorer,
)

if TYPE_CHECKING:
    from rv_agent.config.agent_config import RVAgentConfig


logger = logging.getLogger(__name__)


# Kill-switch registry: every RV steering flag mapped to the off/0 value that
# `pure_mode` forces. The key set MUST equal the set of config fields marked
# `arm_defining` (cross-checked at assembly and by the completeness test). To
# add a new steering flag: mark the config field `arm_defining` AND add it here.
RV_STEERING_FLAGS: Dict[str, Any] = {
    # MOP/WTG scorer weights — gate whether MOP/WTG steering is active at all.
    "mop_direct_score": 0.0,
    "mop_transitive_score": 0.0,
    "wtg_guided_score": 0.0,
    # Ported steering scorers / launch / trigger flags.
    "mop_frontier_weight": 0.0,
    "mop_activity_source_components": False,
    "trigger_mop_first": False,
    "component_trigger_enabled": False,
    "state_mop_density_enabled": False,
    "form_completion_enabled": False,
    # Exploration guards and caps.
    "foreign_activity_guard": False,
    "back_menu_pick_cap": 0,
    "mop_target_pick_cap": 0,
    "idle_timeout_cap": 0,
    "dynamic_epsilon": False,
    "activity_budget_enabled": False,
}


class ScoringPipeline:
    """Assemble the config-selected scorers into an `ActionRanker`.

    Single assembly point for the scoring pipeline (INV-AGT-42): the only
    place scorers are instantiated. Stateless — exposes one static factory,
    `from_config`, which validates the kill-switch registry, applies the
    `pure_mode` kill-switch, and logs the assembled arm once at startup. See
    the module docstring for the arm-auditability contract this enforces.
    """

    @staticmethod
    def from_config(config: "RVAgentConfig") -> ActionRanker:
        """
        Build the `ActionRanker` for the arm described by `config`.

        This is the single assembly point (INV-AGT-42). It validates the
        kill-switch registry, applies `pure_mode`, instantiates the enabled
        scorers, logs the composition, and returns the ranker.

        Args:
            config: Agent configuration. Mutated in place when `pure_mode` is
                True (registered flags forced off) so the whole run observes the
                pure arm from one source of truth.

        Returns:
            An `ActionRanker` holding exactly the scorers enabled for this arm.

        Raises:
            ConfigurationError: An arm-defining config field is not registered
                in `RV_STEERING_FLAGS` (fail-fast, no silent default).
        """
        # Registry validation and the pure_mode kill-switch introspect the
        # config's Pydantic fields. Unit tests may pass a lightweight test
        # double (MagicMock) instead of RVAgentConfig; those bypass the
        # introspection — a real run always passes a validated RVAgentConfig,
        # and registry completeness is enforced by the pipeline unit tests.
        if isinstance(config, BaseModel):
            _validate_registry(config)
            _apply_kill_switch(config)

        # Candidate scorers, in reading order. `is_enabled` gates each one:
        # base-policy scorers are always active; MOP/WTG scorers exclude
        # themselves once their weights are 0 (which pure_mode guarantees).
        candidates: List[Scorer] = [
            MopScorer(config=config),
            WtgScorer(config=config),
            SaturationScorer(config=config),
            ComponentPriorityScorer(config=config),
            StrengthScorer(config=config),
            GradualDecayScorer(config=config),
            CoverageDensityScorer(config=config),
            SystemElementFilter(),
            VisitationPenaltyScorer(config=config),
        ]
        enabled = [scorer for scorer in candidates if scorer.is_enabled(config)]

        _log_composition(enabled, config)
        return ActionRanker(enabled)


def _validate_registry(config: "RVAgentConfig") -> None:
    """Fail fast when an arm-defining config field is not registered.

    Args:
        config: Agent configuration whose Pydantic fields are introspected
            for the `arm_defining` marker.

    Raises:
        ConfigurationError: A field marked `arm_defining` is missing from
            `RV_STEERING_FLAGS` (INV-AGT-43).
    """
    arm_fields = {
        name
        for name, field in type(config).model_fields.items()
        if (field.json_schema_extra or {}).get("arm_defining")
    }
    unregistered = arm_fields - set(RV_STEERING_FLAGS)
    if unregistered:
        raise ConfigurationError(
            "Arm-defining config field(s) not registered with the pure_mode "
            f"kill-switch registry: {sorted(unregistered)}. Add them to "
            "RV_STEERING_FLAGS in ranking/pipeline.py."
        )


def _apply_kill_switch(config: "RVAgentConfig") -> None:
    """Force every registered steering flag off/0 when `pure_mode` is True."""
    if not config.pure_mode:
        return
    for name, off_value in RV_STEERING_FLAGS.items():
        current = getattr(config, name)
        if current != off_value:
            setattr(config, name, off_value)
            logger.info(
                "[RV-ARCH] pure_mode forced %s: %r -> %r", name, current, off_value
            )


def _log_composition(scorers: List[Scorer], config: "RVAgentConfig") -> None:
    """Emit the single `[RV-ARCH]` audit line describing the assembled arm."""
    scorer_names = [type(scorer).__name__ for scorer in scorers]
    flags = {name: getattr(config, name) for name in RV_STEERING_FLAGS}
    logger.info("[RV-ARCH] scorers=%s flags=%s", scorer_names, flags)
