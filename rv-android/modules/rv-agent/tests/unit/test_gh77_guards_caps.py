"""
Unit tests for gh77 Group 4 — exploration guards and caps (INV-AGT-51).

Every guard/cap is off by default (byte-identical to the base policy) and each
rejection increments a per-guard telemetry counter. These tests exercise:

- foreign-activity guard: escape (BACK) on a foreign foreground + counter
- BACK/MENU consecutive-pick cap: lift after N picks (relaunch) + counter
- MOP-target revisit cap: MopScorer boost stops at the cap, base scorers intact

Node-level policies (idle-timeout, dynamic epsilon, per-activity budget) live in
`NodeExplorationPolicy` and are tested against their gated behavior.
"""

from unittest.mock import MagicMock

import pytest
from rv_agent import tracking as track
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.agent.nodes.exploration_policy import NodeExplorationPolicy
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.strategies.rvagent_strategy.ranking.scorers import MopScorer
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_android_core.domain.widget import WidgetEventType
from support_config import make_agent_config

TARGET_PACKAGE = "br.unb.cic.cryptoapp"


@pytest.fixture(autouse=True)
def reset_tracking_counters():
    """Reset aggregate guard counters around each test."""
    track.reset_counters()
    yield
    track.reset_counters()


def _make_strategy(**config_overrides):
    """Build an RVAgentStrategy with a real config and minimal dependencies."""
    config = make_agent_config(package_name=TARGET_PACKAGE, **config_overrides)
    graph = DynamicStateGraph(
        multi_value_saturation_threshold=config.multi_value_saturation_threshold
    )
    return RVAgentStrategy(
        graph=graph,
        ui_coverage=UICoverageTracker(),
        config=config,
        static_data=None,
        transition_manager=None,
    )


def _mock_item(package: str):
    """A screen item whose view reports the given package."""
    item = MagicMock()
    item.view = {"package": package}
    return item


def _mock_screen(activity: str, packages):
    """A ScreenDescription-like mock with items from the given packages."""
    screen = MagicMock()
    screen.activity = activity
    screen.items = [_mock_item(pkg) for pkg in packages]
    return screen


def _back_action():
    """A BACK ItemAction as the strategy emits it."""
    strategy = _make_strategy()
    return strategy._create_back_action()


# ---------------------------------------------------------------------------
# Foreign-activity guard
# ---------------------------------------------------------------------------


class TestForeignActivityGuard:
    def test_escapes_on_foreign_foreground(self):
        strategy = _make_strategy(foreign_activity_guard=True)
        screen = _mock_screen("SettingsActivity", ["com.android.settings"] * 3)

        action = strategy.select_next_action("hash_foreign", screen)

        assert action is not None
        assert action.event == WidgetEventType.BACK
        assert track.get_aggregate_counters()["foreign_activity_guard_escapes"] == 1

    def test_disabled_guard_does_not_escape(self):
        # With the guard off the foreign screen is handled by normal ranking,
        # not the escape path — the counter stays at 0.
        strategy = _make_strategy(foreign_activity_guard=False)
        screen = _mock_screen("SettingsActivity", ["com.android.settings"] * 3)

        strategy.select_next_action("hash_foreign", screen)

        assert track.get_aggregate_counters()["foreign_activity_guard_escapes"] == 0

    def test_native_screen_is_not_foreign(self):
        strategy = _make_strategy(foreign_activity_guard=True)
        assert strategy._is_foreign_foreground(
            _mock_screen("MainActivity", [TARGET_PACKAGE, TARGET_PACKAGE])
        ) is False

    def test_system_dialog_is_not_foreign(self):
        # Permission dialogs render under a system package but are part of the
        # app flow — they must NOT be treated as foreign.
        strategy = _make_strategy(foreign_activity_guard=True)
        assert strategy._is_foreign_foreground(
            _mock_screen("PermissionDialog", ["com.android.permissioncontroller"])
        ) is False

    def test_no_package_info_is_not_foreign(self):
        strategy = _make_strategy(foreign_activity_guard=True)
        assert strategy._is_foreign_foreground(_mock_screen("Unknown", ["", ""])) is False


# ---------------------------------------------------------------------------
# BACK/MENU consecutive-pick cap
# ---------------------------------------------------------------------------


class TestBackMenuCap:
    def test_disabled_cap_is_passthrough(self):
        strategy = _make_strategy(back_menu_pick_cap=0)
        back = _back_action()
        for _ in range(10):
            out = strategy._apply_back_menu_cap(back)
            assert out.event == WidgetEventType.BACK
        assert track.get_aggregate_counters()["back_menu_cap_filtered"] == 0

    def test_cap_filters_after_n_consecutive_backs(self):
        strategy = _make_strategy(back_menu_pick_cap=3)
        back = _back_action()

        # First 3 BACK picks pass through.
        for _ in range(3):
            assert strategy._apply_back_menu_cap(back).event == WidgetEventType.BACK

        # 4th consecutive BACK is filtered and replaced by a relaunch.
        escalated = strategy._apply_back_menu_cap(back)
        assert escalated.event == WidgetEventType.RESTART
        assert track.get_aggregate_counters()["back_menu_cap_filtered"] == 1

    def test_non_back_lifts_the_filter(self):
        strategy = _make_strategy(back_menu_pick_cap=2)
        back = _back_action()
        non_back = MagicMock()
        non_back.event = WidgetEventType.CLICK

        strategy._apply_back_menu_cap(back)
        strategy._apply_back_menu_cap(back)  # streak now at cap
        # A non-BACK decision resets the streak...
        assert strategy._apply_back_menu_cap(non_back) is non_back
        # ...so BACK is allowed again without being filtered.
        assert strategy._apply_back_menu_cap(back).event == WidgetEventType.BACK
        assert track.get_aggregate_counters()["back_menu_cap_filtered"] == 0


# ---------------------------------------------------------------------------
# MOP-target revisit cap (MopScorer)
# ---------------------------------------------------------------------------


def _mop_action(coords=(100, 100), directly=True):
    action = MagicMock()
    action.directly_reaches_target = directly
    action.reaches_target = directly
    action.coords_for_matching = coords
    action.coordinates = coords
    return action


def _mop_context(exec_count):
    node = MagicMock()
    node.get_action_execution_count.return_value = exec_count
    ctx = MagicMock()
    ctx.current_state_hash = "state"
    ctx.graph.states.get.return_value = node
    return ctx


class TestMopRevisitCap:
    def test_boost_applies_below_cap(self):
        scorer = MopScorer(config=make_agent_config(mop_target_pick_cap=4))
        # Picked 3 times (< cap 4): full direct boost still applies.
        assert scorer.score(_mop_action(), _mop_context(exec_count=3)) == 500.0
        assert track.get_aggregate_counters()["mop_target_cap_boost_stopped"] == 0

    def test_boost_stops_at_cap(self):
        scorer = MopScorer(config=make_agent_config(mop_target_pick_cap=4))
        # Picked 4 times (== cap): the MOP boost is suppressed.
        assert scorer.score(_mop_action(), _mop_context(exec_count=4)) == 0.0
        assert track.get_aggregate_counters()["mop_target_cap_boost_stopped"] == 1

    def test_disabled_cap_never_suppresses(self):
        scorer = MopScorer(config=make_agent_config(mop_target_pick_cap=0))
        # Even after many picks, cap=0 leaves the boost intact and never touches
        # the graph (base-identical).
        assert scorer.score(_mop_action(), _mop_context(exec_count=99)) == 500.0
        assert track.get_aggregate_counters()["mop_target_cap_boost_stopped"] == 0

    def test_non_mop_action_unaffected(self):
        scorer = MopScorer(config=make_agent_config(mop_target_pick_cap=4))
        non_mop = _mop_action(directly=False)
        non_mop.reaches_target = False
        assert scorer.score(non_mop, _mop_context(exec_count=99)) == 0.0


# ---------------------------------------------------------------------------
# Node-level policies (dynamic epsilon, idle-timeout cap, activity budget)
# ---------------------------------------------------------------------------


class TestDynamicEpsilon:
    def test_disabled_returns_base(self):
        policy = NodeExplorationPolicy(make_agent_config(dynamic_epsilon=False))
        assert policy.effective_epsilon(0.15, coverage_gap=0.5) == 0.15

    def test_enabled_scales_with_coverage_gap(self):
        policy = NodeExplorationPolicy(make_agent_config(dynamic_epsilon=True))
        # 0.02 + (0.15 - 0.02) * gap  (ported APE-RV bounds)
        assert policy.effective_epsilon(0.05, coverage_gap=0.0) == pytest.approx(0.02)
        assert policy.effective_epsilon(0.05, coverage_gap=1.0) == pytest.approx(0.15)
        assert policy.effective_epsilon(0.05, coverage_gap=0.5) == pytest.approx(0.085)

    def test_clamps_out_of_range_gap(self):
        policy = NodeExplorationPolicy(make_agent_config(dynamic_epsilon=True))
        assert policy.effective_epsilon(0.05, coverage_gap=-1.0) == pytest.approx(0.02)
        assert policy.effective_epsilon(0.05, coverage_gap=2.0) == pytest.approx(0.15)


class TestIdleTimeoutCap:
    def test_disabled_never_fires(self):
        policy = NodeExplorationPolicy(make_agent_config(idle_timeout_cap=0))
        # Even a long idle interval does not fire when the cap is disabled.
        assert policy.check_idle(now=0.0, screen_changed=False, iteration=1) is False
        assert policy.check_idle(now=999.0, screen_changed=False, iteration=2) is False
        assert track.get_aggregate_counters()["idle_timeout_waits"] == 0

    def test_fires_after_cap_seconds_idle(self):
        policy = NodeExplorationPolicy(make_agent_config(idle_timeout_cap=10))
        # t=0 starts the idle interval; still under the cap at t=5.
        assert policy.check_idle(now=0.0, screen_changed=False, iteration=1) is False
        assert policy.check_idle(now=5.0, screen_changed=False, iteration=2) is False
        # t=10 reaches the cap -> escape fires and is counted.
        assert policy.check_idle(now=10.0, screen_changed=False, iteration=3) is True
        assert track.get_aggregate_counters()["idle_timeout_waits"] == 1

    def test_screen_change_resets_the_clock(self):
        policy = NodeExplorationPolicy(make_agent_config(idle_timeout_cap=10))
        policy.check_idle(now=0.0, screen_changed=False, iteration=1)
        # A screen change resets the idle interval start to t=8...
        assert policy.check_idle(now=8.0, screen_changed=True, iteration=2) is False
        # ...so at t=15 only 7 s have elapsed since the reset — no fire.
        assert policy.check_idle(now=15.0, screen_changed=False, iteration=3) is False
        assert track.get_aggregate_counters()["idle_timeout_waits"] == 0


class TestActivityBudget:
    def test_disabled_never_deprioritizes(self):
        policy = NodeExplorationPolicy(make_agent_config(activity_budget_enabled=False))
        policy.register_activity("A", widget_count=0)
        for i in range(200):
            assert policy.record_and_check_budget("A", iteration=i) is False
        assert track.get_aggregate_counters()["activity_budget_deprioritized"] == 0

    def test_deprioritizes_when_budget_exhausted(self):
        policy = NodeExplorationPolicy(make_agent_config(activity_budget_enabled=True))
        # budget = base(50) + per_widget(5) * 0 widgets = 50
        policy.register_activity("A", widget_count=0)
        for i in range(49):
            assert policy.record_and_check_budget("A", iteration=i) is False
        # 50th action reaches the budget -> deprioritized and counted.
        assert policy.record_and_check_budget("A", iteration=49) is True
        assert track.get_aggregate_counters()["activity_budget_deprioritized"] == 1

    def test_budget_scales_with_widget_count(self):
        policy = NodeExplorationPolicy(make_agent_config(activity_budget_enabled=True))
        # budget = 50 + 5 * 10 = 100; frozen on first registration.
        policy.register_activity("Rich", widget_count=10)
        policy.register_activity("Rich", widget_count=999)  # idempotent, ignored
        fired = [policy.record_and_check_budget("Rich", iteration=i) for i in range(100)]
        assert fired[:99] == [False] * 99
        assert fired[99] is True
