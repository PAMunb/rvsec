"""
Pure-arm parity test (INV-AGT-44).

With all RV steering flags off — equivalently, ``pure_mode=True`` — action
selection degenerates to the documented base policy: the MOP/WTG steering
scorers are excluded and only the always-active base-policy scorers score the
actions. This test asserts the three-way equivalence

    all flags off  ==  pure_mode=True  ==  base-policy ActionRanker

produces identical rankings on the same actions with a fixed seed, and that the
kill-switch is *meaningful*: the same MOP-reaching action that the default
(steering) arm boosts to the top receives no MOP boost under the pure arm.
"""

import random
from unittest.mock import MagicMock

import pytest
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.strategies.rvagent_strategy.ranking import RV_STEERING_FLAGS, ScoringPipeline
from rv_agent.strategies.rvagent_strategy.ranking.action_ranker import ActionRanker
from rv_agent.strategies.rvagent_strategy.ranking.scorers import (
    ComponentPriorityScorer,
    CoverageDensityScorer,
    GradualDecayScorer,
    SaturationScorer,
    StrengthScorer,
    SystemElementFilter,
    VisitationPenaltyScorer,
)

SEED = 42


def _make_action(cls, coords, directly=False, transitive=False):
    action = MagicMock()
    action.target_view = {"class": cls, "package": "test.app"}
    action.coordinates = coords
    action.coords_for_matching = coords
    action.directly_reaches_target = directly
    action.reaches_target = directly or transitive
    action.id = f"{cls}@{coords}"
    return action


@pytest.fixture
def actions():
    # A cross-section of widget types so the base policy produces a real
    # ordering; action "crypto_btn" is MOP-reaching (only steering boosts it).
    return [
        _make_action("Button", (100, 100), directly=True),  # crypto_btn
        _make_action("CheckBox", (200, 200)),
        _make_action("TextView", (300, 300)),
        _make_action("Button", (400, 400), transitive=True),
    ]


@pytest.fixture
def context():
    node = MagicMock()
    node.get_saturation_rate.return_value = 0.5
    node.visit_count = 2
    node.get_action_strength.return_value = 0.5
    node.action_cumulative_reward = {}

    ctx = MagicMock()
    ctx.current_state_hash = "state_hash"
    ctx.graph.states.get.return_value = node
    ctx.ui_coverage.get_element_test_count.return_value = 0
    ctx.ui_coverage.get_coverage_gap.return_value = 0.5
    ctx.successor_tracker.get_action_destination.return_value = None
    ctx.screen_desc.activity = "MainActivity"
    ctx.transition_manager = None
    return ctx


def _base_policy_ranker(config):
    """The documented base policy — the seven always-active scorers."""
    return ActionRanker(
        [
            SaturationScorer(config=config),
            ComponentPriorityScorer(config=config),
            StrengthScorer(config=config),
            GradualDecayScorer(config=config),
            CoverageDensityScorer(config=config),
            SystemElementFilter(),
            VisitationPenaltyScorer(config=config),
        ]
    )


def _ranked(ranker, actions, context):
    random.seed(SEED)
    return [(sa.action.id, sa.score) for sa in ranker.rank(actions, context)]


class TestPureArmParity:
    def test_pure_mode_equals_all_flags_off_equals_base_policy(self, actions, context):
        pure = ScoringPipeline.from_config(
            RVAgentConfig(package_name="test.app", pure_mode=True)
        )
        all_off = ScoringPipeline.from_config(
            RVAgentConfig(package_name="test.app", **dict(RV_STEERING_FLAGS))
        )
        base = _base_policy_ranker(RVAgentConfig(package_name="test.app"))

        pure_ranking = _ranked(pure, actions, context)
        all_off_ranking = _ranked(all_off, actions, context)
        base_ranking = _ranked(base, actions, context)

        assert pure_ranking == all_off_ranking
        assert pure_ranking == base_ranking

    def test_kill_switch_is_meaningful(self, actions, context):
        # Default arm: MOP steering boosts the directly-reaching crypto button
        # to the top with a score >= mop_direct_score (500).
        steering = ScoringPipeline.from_config(RVAgentConfig(package_name="test.app"))
        steering_ranking = _ranked(steering, actions, context)
        assert steering_ranking[0][0] == "Button@(100, 100)"
        assert steering_ranking[0][1] >= 500.0

        # Pure arm: the same action gets no MOP boost — its score drops well
        # below 500 (only base-policy scorers contribute).
        pure = ScoringPipeline.from_config(
            RVAgentConfig(package_name="test.app", pure_mode=True)
        )
        pure_scores = dict(_ranked(pure, actions, context))
        assert pure_scores["Button@(100, 100)"] < 500.0
