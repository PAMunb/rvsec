"""
Unit tests for gh77 Group 6: launcher dose/denylist (INV-AGT-47 dose control).

Covers the two dose scenarios of the delta-spec Requirement "MOP-First Activity
Launch Ordering with Dose Control" plus the pure-arm no-op:

  - Failed Launch Enters Denylist: a launch that fails is denylisted and never
    re-selected in the same run.
  - Per-Run Launch Cap: once the per-run cap is spent, no further direct launches
    are dispatched and normal exploration (None return) continues.
  - Launch cadence: the launcher fires once every ``launch_cadence`` opportunities.
  - Pure-arm no-op: with ``trigger_mop_first`` off (as ``pure_mode`` forces it),
    the launcher never dispatches — a byte-identical no-op.

The MOP-first ordering itself (INV-AGT-47 ordering half) is covered in
``test_gh77_mop_reach.py``; here the ordering is exercised only through candidate
selection (MOP-reaching activities are preferred, visited/denylisted skipped).
"""

from unittest.mock import MagicMock

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from support_config import make_agent_config

TARGET_PACKAGE = "com.test.app"


def _make_strategy(mop_activities=frozenset(), **config_overrides):
    """Build a real RVAgentStrategy; optionally attach a MOP-aware TransitionManager.

    A real strategy is used (not ``__new__``) so the dose state is initialized by
    ``__init__`` exactly as in production and ``reset`` can be exercised. When
    ``mop_activities`` is non-empty a mock ``TransitionManager`` is attached whose
    ``activity_has_mop`` reports membership, so ``order_activity_launch_queue``
    partitions MOP-first; otherwise ``transition_manager`` is None and ordering is
    identity.
    """
    config = make_agent_config(package_name=TARGET_PACKAGE, **config_overrides)
    graph = DynamicStateGraph(
        multi_value_saturation_threshold=config.multi_value_saturation_threshold
    )
    transition_manager = None
    if mop_activities:
        transition_manager = MagicMock()
        transition_manager.activity_has_mop.side_effect = lambda a: a in mop_activities
        transition_manager._visited_activities = set()
    return RVAgentStrategy(
        graph=graph,
        ui_coverage=UICoverageTracker(),
        config=config,
        static_data=None,
        transition_manager=transition_manager,
    )


# ---------------------------------------------------------------------------
# Failed Launch Enters Denylist
# ---------------------------------------------------------------------------


class TestFailedLaunchDenylist:
    def test_failed_launch_is_denylisted(self):
        """record_launch_failure adds the activity to the per-run denylist."""
        strategy = _make_strategy(trigger_mop_first=True, launch_cadence=1)

        strategy.record_launch_failure("CryptoActivity")

        assert "CryptoActivity" in strategy._launch_denylist

    def test_denylisted_activity_not_reselected(self):
        """After a failure the denylisted activity is skipped; the next is chosen."""
        strategy = _make_strategy(trigger_mop_first=True, launch_cadence=1)

        first = strategy.maybe_launch_activity(["A", "B"], visited=set())
        assert first == "A"

        strategy.record_launch_failure("A")
        second = strategy.maybe_launch_activity(["A", "B"], visited=set())

        assert second == "B"

    def test_all_denylisted_returns_none_without_spending_budget(self):
        """A firing with no eligible activity dispatches nothing, spends no budget."""
        strategy = _make_strategy(trigger_mop_first=True, launch_cadence=1)
        strategy._launch_denylist = {"A", "B"}

        result = strategy.maybe_launch_activity(["A", "B"], visited=set())

        assert result is None
        assert strategy._launch_count == 0
        # The cadence counter still resets at the firing point.
        assert strategy._steps_since_launch == 0


# ---------------------------------------------------------------------------
# Per-Run Launch Cap
# ---------------------------------------------------------------------------


class TestPerRunLaunchCap:
    def test_cap_stops_further_launches(self):
        """With cap=5 and 5 launches dispatched, no further direct launch fires."""
        strategy = _make_strategy(
            trigger_mop_first=True, launch_cadence=1, launch_cap=5
        )
        queue = ["A", "B", "C"]

        launched = [
            strategy.maybe_launch_activity(queue, visited=set()) for _ in range(6)
        ]

        assert all(x is not None for x in launched[:5])
        assert launched[5] is None
        assert strategy._launch_count == 5

    def test_cap_zero_is_unlimited(self):
        """cap=0 means unlimited: launches keep firing past any fixed count."""
        strategy = _make_strategy(
            trigger_mop_first=True, launch_cadence=1, launch_cap=0
        )

        launched = [
            strategy.maybe_launch_activity(["A"], visited=set()) for _ in range(20)
        ]

        assert all(x == "A" for x in launched)
        assert strategy._launch_count == 20

    def test_capped_run_leaves_normal_exploration_unaffected(self):
        """Once capped, maybe_launch_activity simply returns None (no side effect)."""
        strategy = _make_strategy(
            trigger_mop_first=True, launch_cadence=1, launch_cap=1
        )

        assert strategy.maybe_launch_activity(["A"], visited=set()) == "A"
        # Cap spent: every subsequent opportunity yields None, count frozen at 1.
        assert strategy.maybe_launch_activity(["A"], visited=set()) is None
        assert strategy.maybe_launch_activity(["A"], visited=set()) is None
        assert strategy._launch_count == 1


# ---------------------------------------------------------------------------
# Launch cadence
# ---------------------------------------------------------------------------


class TestLaunchCadence:
    def test_fires_once_per_cadence_period(self):
        """With cadence=3 the launcher fires on the 3rd opportunity, then re-arms."""
        strategy = _make_strategy(trigger_mop_first=True, launch_cadence=3)
        queue = ["A"]

        assert strategy.maybe_launch_activity(queue, visited=set()) is None  # step 1
        assert strategy.maybe_launch_activity(queue, visited=set()) is None  # step 2
        assert strategy.maybe_launch_activity(queue, visited=set()) == "A"  # step 3
        assert strategy.maybe_launch_activity(queue, visited=set()) is None  # step 4
        assert strategy.maybe_launch_activity(queue, visited=set()) is None  # step 5
        assert strategy.maybe_launch_activity(queue, visited=set()) == "A"  # step 6

    def test_cadence_one_fires_every_step(self):
        """cadence=1 fires on every opportunity."""
        strategy = _make_strategy(trigger_mop_first=True, launch_cadence=1)

        assert strategy.maybe_launch_activity(["A"], visited=set()) == "A"
        assert strategy.maybe_launch_activity(["A"], visited=set()) == "A"


# ---------------------------------------------------------------------------
# MOP-first selection + visited skipping
# ---------------------------------------------------------------------------


class TestLaunchCandidateSelection:
    def test_mop_reaching_activity_selected_first(self):
        """The MOP-reaching activity leads the ordered queue and is launched first."""
        strategy = _make_strategy(
            mop_activities={"CryptoActivity"},
            trigger_mop_first=True,
            launch_cadence=1,
        )

        chosen = strategy.maybe_launch_activity(
            ["AboutActivity", "CryptoActivity", "HelpActivity"], visited=set()
        )

        assert chosen == "CryptoActivity"

    def test_visited_activities_are_skipped(self):
        """A visited activity is skipped even when it is the MOP-first choice."""
        strategy = _make_strategy(
            mop_activities={"CryptoActivity"},
            trigger_mop_first=True,
            launch_cadence=1,
        )

        chosen = strategy.maybe_launch_activity(
            ["AboutActivity", "CryptoActivity", "HelpActivity"],
            visited={"CryptoActivity"},
        )

        # MOP-first order is [Crypto, About, Help]; Crypto visited → About.
        assert chosen == "AboutActivity"

    def test_visited_defaults_to_strategy_visited_set(self):
        """When visited is None the strategy's own visited set drives skipping."""
        strategy = _make_strategy(
            mop_activities={"CryptoActivity"},
            trigger_mop_first=True,
            launch_cadence=1,
        )
        strategy.transition_manager._visited_activities = {"CryptoActivity"}

        chosen = strategy.maybe_launch_activity(
            ["AboutActivity", "CryptoActivity", "HelpActivity"]
        )

        assert chosen == "AboutActivity"


# ---------------------------------------------------------------------------
# Pure-arm no-op (dose off)
# ---------------------------------------------------------------------------


class TestDoseOffNoOp:
    def test_launcher_never_fires_with_trigger_mop_first_off(self):
        """trigger_mop_first off (as pure_mode forces) → the launcher is a no-op."""
        strategy = _make_strategy(
            trigger_mop_first=False, launch_cadence=1, launch_cap=0
        )

        results = [
            strategy.maybe_launch_activity(["A", "B"], visited=set()) for _ in range(10)
        ]

        assert all(r is None for r in results)
        assert strategy._launch_count == 0

    def test_pure_mode_forces_launcher_off(self):
        """pure_mode forces trigger_mop_first off, so the launcher cannot fire."""
        strategy = _make_strategy(
            pure_mode=True, trigger_mop_first=True, launch_cadence=1
        )

        # pure_mode is the kill-switch: it overrides trigger_mop_first to off.
        assert strategy.config.trigger_mop_first is False
        assert strategy.maybe_launch_activity(["A"], visited=set()) is None


# ---------------------------------------------------------------------------
# Reset (per-run scope)
# ---------------------------------------------------------------------------


class TestDoseReset:
    def test_reset_clears_dose_state(self):
        """reset() clears the denylist, launch budget, and cadence counter."""
        strategy = _make_strategy(
            trigger_mop_first=True, launch_cadence=1, launch_cap=5
        )
        strategy.maybe_launch_activity(["A"], visited=set())
        strategy.record_launch_failure("Z")
        assert strategy._launch_count == 1
        assert strategy._launch_denylist == {"Z"}

        strategy.reset()

        assert strategy._launch_denylist == set()
        assert strategy._launch_count == 0
        assert strategy._steps_since_launch == 0
