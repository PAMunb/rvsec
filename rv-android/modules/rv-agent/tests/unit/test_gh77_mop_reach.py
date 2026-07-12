"""
Unit tests for gh77 Group 3: MOP-reach strategies + component triggering.

Covers INV-AGT-45..50:
  - A′ component-sourced MOP activities (INV-AGT-45)
  - DIALOG→host-activity re-key (INV-AGT-50)
  - MopFrontierScorer conditions (INV-AGT-46)
  - MOP-first launch-queue ordering (INV-AGT-47)
  - Component triggering: plateau gate, activities excluded, dispatch-failure
    containment (INV-AGT-48)
  - Static-data fail-fast at load (INV-AGT-49)
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.services.component_trigger import ComponentTriggerService
from rv_agent.services.transition_manager import (
    TransitionManager,
    validate_static_data,
)
from rv_agent.strategies.rvagent_strategy.ranking.scorers import MopFrontierScorer
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_android_core.domain.classes import Classes, Method
from rv_android_core.domain.components import ComponentInfo, Components
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.window import Window, Windows, WindowType
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_android_core.util.error.exceptions import RVValidationError
from rv_static_analysis.parser.static.static_analysis_parser import parse_file


# =============================================================================
# Fixtures / helpers
# =============================================================================


@pytest.fixture
def cryptoapp_static_data() -> StaticAnalysisData:
    """Load the real cryptoapp static analysis (no components section)."""
    fixture = (
        Path(__file__).parent.parent
        / "fixtures"
        / "static_analysis"
        / "cryptoapp"
        / "cryptoapp.apk.json"
    )
    return parse_file(str(fixture), "br.unb.cic.cryptoapp")


def _mop_method(class_name: str, signature: str) -> Method:
    """Build a Method flagged as MOP-reaching for the given class."""
    return Method(
        class_name=class_name,
        name="onCreate",
        params=[],
        signature=signature,
        reachable=True,
        reaches_target=True,
        directly_reaches_target=False,
    )


# =============================================================================
# INV-AGT-45: A′ — component-sourced MOP activities
# =============================================================================


class TestActivityHasMopFromComponents:
    """A′: activity_has_mop sources from components[].reaches_target when flag on."""

    def _static_with_component(
        self, cryptoapp_static_data: StaticAnalysisData
    ) -> StaticAnalysisData:
        cryptoapp_static_data.components = Components(
            activities=[
                ComponentInfo(
                    class_name="com.app.CryptoActivity",
                    component_type="activity",
                    reaches_target=True,
                )
            ]
        )
        return cryptoapp_static_data

    def test_component_source_on(self, cryptoapp_static_data):
        """With the flag on, a component-only MOP activity is MOP-reaching."""
        static_data = self._static_with_component(cryptoapp_static_data)
        tm = TransitionManager(
            static_data,
            DynamicStateGraph(),
            mop_activity_source_components=True,
        )

        assert tm.activity_has_mop("com.app.CryptoActivity") is True

    def test_component_source_off(self, cryptoapp_static_data):
        """With the flag off, the pre-existing source alone does not flag it."""
        static_data = self._static_with_component(cryptoapp_static_data)
        tm = TransitionManager(
            static_data,
            DynamicStateGraph(),
            mop_activity_source_components=False,
        )

        assert tm.activity_has_mop("com.app.CryptoActivity") is False

    def test_empty_activity_is_not_mop(self, cryptoapp_static_data):
        """An empty activity name is never MOP-reaching."""
        tm = TransitionManager(cryptoapp_static_data, DynamicStateGraph())
        assert tm.activity_has_mop("") is False


# =============================================================================
# INV-AGT-50: DIALOG → host-activity re-key
# =============================================================================


class TestDialogRekey:
    """A MOP-flagged DIALOG window transfers its MOP-ness to the host activity."""

    def _static_with_dialog(self) -> StaticAnalysisData:
        main = Window(name="MainActivity", id="w1", type=WindowType.ACTIVITY,
                      activity="MainActivity")
        dialog = Window(name="ConfirmDialog", id="w2", type=WindowType.DIALOG,
                        activity="")
        windows = Windows(windows={main, dialog})
        # Flag the dialog class as MOP-reaching via the method source.
        classes = Classes(
            methods={"sig1": _mop_method("ConfirmDialog", "sig1")}
        )
        wtg = WindowTransitionGraph(
            transitions=[
                {
                    "source": "w1",
                    "target": "w2",
                    "widget_id": "x",
                    "event_type": "CLICK",
                }
            ],
            window_ids={"w1", "w2"},
        )
        return StaticAnalysisData(classes=classes, windows=windows, wtg=wtg)

    def test_dialog_flag_transfers_to_host(self):
        """activity_has_mop(host) is True after re-keying the MOP dialog."""
        tm = TransitionManager(self._static_with_dialog(), DynamicStateGraph())

        # The dialog itself is MOP-reaching (method source) ...
        assert tm.activity_has_mop("ConfirmDialog") is True
        # ... and the re-key propagates it to the host activity (INV-AGT-50).
        assert tm.activity_has_mop("MainActivity") is True


# =============================================================================
# INV-AGT-46: MopFrontierScorer conditions
# =============================================================================


class TestMopFrontierScorer:
    """Frontier boost only when target is MOP-reaching AND unvisited."""

    def _context(self, visited):
        return SimpleNamespace(
            screen_desc=SimpleNamespace(activity="MainActivity"),
            visited_activities=set(visited),
            transition_manager=self._tm,
        )

    def _make_tm(self, action_targets, mop_activities):
        """Mock TransitionManager resolving action_id → target and MOP membership."""
        tm = MagicMock()
        tm.wtg = object()  # truthy: WTG data present
        tm.get_navigation_guidance.return_value = {
            "suggested_actions": [
                {"action_id": aid, "target_activity": target}
                for aid, target in action_targets.items()
            ]
        }
        tm.activity_has_mop.side_effect = lambda a: a in mop_activities
        self._tm = tm
        return tm

    def test_boost_when_mop_and_unvisited(self):
        """Action A → MOP-reaching unvisited activity gets +weight."""
        self._make_tm({1: "SettingsActivity"}, {"SettingsActivity"})
        scorer = MopFrontierScorer(RVAgentConfig(package_name="p", mop_frontier_weight=250.0))
        action = SimpleNamespace(id=1)

        assert scorer.score(action, self._context(visited=[])) == 250.0

    def test_no_boost_when_not_mop(self):
        """Action B → non-MOP activity gets 0."""
        self._make_tm({2: "AboutActivity"}, {"SettingsActivity"})
        scorer = MopFrontierScorer(RVAgentConfig(package_name="p", mop_frontier_weight=250.0))
        action = SimpleNamespace(id=2)

        assert scorer.score(action, self._context(visited=[])) == 0.0

    def test_no_boost_when_visited(self):
        """Action C → MOP activity already visited gets 0."""
        self._make_tm({3: "SettingsActivity"}, {"SettingsActivity"})
        scorer = MopFrontierScorer(RVAgentConfig(package_name="p", mop_frontier_weight=250.0))
        action = SimpleNamespace(id=3)

        assert scorer.score(action, self._context(visited=["SettingsActivity"])) == 0.0

    def test_is_enabled_follows_weight(self):
        """The scorer excludes itself when the weight is 0 (pure_mode parity)."""
        assert MopFrontierScorer().is_enabled(
            RVAgentConfig(package_name="p", mop_frontier_weight=250.0)
        )
        assert not MopFrontierScorer().is_enabled(
            RVAgentConfig(package_name="p", mop_frontier_weight=0.0)
        )

    def test_no_transition_manager_scores_zero(self):
        """Without a TransitionManager the scorer contributes nothing."""
        scorer = MopFrontierScorer(RVAgentConfig(package_name="p", mop_frontier_weight=250.0))
        ctx = SimpleNamespace(
            screen_desc=SimpleNamespace(activity="MainActivity"),
            visited_activities=set(),
            transition_manager=None,
        )
        assert scorer.score(SimpleNamespace(id=1), ctx) == 0.0


# =============================================================================
# INV-AGT-47: MOP-first launch-queue ordering (E-mín)
# =============================================================================


class TestLaunchQueueMopFirst:
    """trigger_mop_first stable-partitions the launch queue MOP-first."""

    def _strategy(self, trigger_mop_first, mop_activities):
        # Build the pure method under test without full strategy construction.
        strategy = RVAgentStrategy.__new__(RVAgentStrategy)
        strategy.config = RVAgentConfig(
            package_name="p", trigger_mop_first=trigger_mop_first
        )
        tm = MagicMock()
        tm.activity_has_mop.side_effect = lambda a: a in mop_activities
        strategy.transition_manager = tm
        return strategy

    def test_mop_activities_first(self):
        """Only CryptoActivity is MOP-reaching → it leads, order otherwise stable."""
        strategy = self._strategy(True, {"CryptoActivity"})
        queue = ["AboutActivity", "CryptoActivity", "HelpActivity"]

        assert strategy.order_activity_launch_queue(queue) == [
            "CryptoActivity",
            "AboutActivity",
            "HelpActivity",
        ]

    def test_flag_off_preserves_order(self):
        """With the flag off the original order is preserved."""
        strategy = self._strategy(False, {"CryptoActivity"})
        queue = ["AboutActivity", "CryptoActivity", "HelpActivity"]

        assert strategy.order_activity_launch_queue(queue) == queue


# =============================================================================
# INV-AGT-48: Component triggering
# =============================================================================


def _catalog() -> Components:
    return Components(
        activities=[
            ComponentInfo(class_name="A", component_type="activity", reaches_target=True)
        ],
        services=[
            ComponentInfo(class_name="S", component_type="service", reaches_target=True)
        ],
        receivers=[
            ComponentInfo(class_name="R", component_type="receiver", reaches_target=True)
        ],
    )


def _trigger_config(**over) -> RVAgentConfig:
    base = dict(package_name="com.app", component_trigger_enabled=True)
    base.update(over)
    return RVAgentConfig(**base)


class TestComponentTrigger:
    """Plateau-gated dispatch of MOP-reaching services/receivers."""

    def test_activities_excluded_from_catalog(self):
        """Only the service and receiver are triggerable; the activity is excluded."""
        device = MagicMock()
        svc = ComponentTriggerService("com.app", _catalog(), device, _trigger_config())

        class_names = {c.class_name for c in svc._candidates}
        assert class_names == {"S", "R"}

    def test_no_fire_without_plateau(self):
        """No plateau → no dispatch."""
        device = MagicMock()
        svc = ComponentTriggerService(
            "com.app", _catalog(), device, _trigger_config(component_percentage=1.0)
        )

        assert svc.maybe_trigger(plateau=False) is None
        device.start_service.assert_not_called()
        device.send_broadcast.assert_not_called()

    def test_fires_on_plateau(self):
        """Plateau + cadence period 1 → dispatches one component."""
        device = MagicMock()
        device.start_service.return_value = True
        svc = ComponentTriggerService(
            "com.app", _catalog(), device, _trigger_config(component_percentage=1.0)
        )

        dispatched = svc.maybe_trigger(plateau=True)
        assert dispatched == "S"
        device.start_service.assert_called_once_with("com.app/S")

    def test_dispatch_failure_denylists_and_continues(self):
        """A failed dispatch denylists the component and does not abort."""
        device = MagicMock()
        device.start_service.return_value = False
        device.send_broadcast.return_value = True
        svc = ComponentTriggerService(
            "com.app", _catalog(), device, _trigger_config(component_percentage=1.0)
        )

        # First opportunity picks the service, which fails → None, denylisted.
        assert svc.maybe_trigger(plateau=True) is None
        assert "S" in svc._denylist
        # Next opportunity skips the denylisted service and reaches the receiver.
        assert svc.maybe_trigger(plateau=True) == "R"
        device.send_broadcast.assert_called_once_with("com.app/R")

    def test_cadence_period_gates_dispatch(self):
        """component_percentage=0.5 fires on every second plateau opportunity."""
        device = MagicMock()
        device.start_service.return_value = True
        svc = ComponentTriggerService(
            "com.app", _catalog(), device, _trigger_config(component_percentage=0.5)
        )

        assert svc.maybe_trigger(plateau=True) is None  # opportunity 1 (period 2)
        assert svc.maybe_trigger(plateau=True) == "S"  # opportunity 2 fires

    def test_zero_cadence_never_fires(self):
        """component_percentage=0 disables triggering entirely."""
        device = MagicMock()
        svc = ComponentTriggerService(
            "com.app", _catalog(), device, _trigger_config(component_percentage=0.0)
        )

        assert svc.maybe_trigger(plateau=True) is None
        device.start_service.assert_not_called()

    def test_disabled_never_fires(self):
        """component_trigger_enabled=False → never dispatches."""
        device = MagicMock()
        svc = ComponentTriggerService(
            "com.app",
            _catalog(),
            device,
            _trigger_config(component_trigger_enabled=False, component_percentage=1.0),
        )

        assert svc.maybe_trigger(plateau=True) is None

    def test_no_static_components_empty_catalog(self):
        """None components → empty catalog, never fires."""
        device = MagicMock()
        svc = ComponentTriggerService(
            "com.app", None, device, _trigger_config(component_percentage=1.0)
        )

        assert svc._candidates == []
        assert svc.maybe_trigger(plateau=True) is None


# =============================================================================
# INV-AGT-49: Static-data fail-fast
# =============================================================================


class TestStaticDataFailFast:
    """Present-but-invalid static data aborts; absence degrades gracefully."""

    def _valid_static_data(self) -> StaticAnalysisData:
        main = Window(name="MainActivity", id="w1", activity="MainActivity")
        return StaticAnalysisData(
            classes=Classes(),
            windows=Windows(windows={main}),
            wtg=WindowTransitionGraph(),
        )

    def test_absent_data_ok(self):
        """None static data is a supported degraded mode."""
        validate_static_data(None)  # must not raise

    def test_valid_data_ok(self):
        """Structurally valid data passes."""
        validate_static_data(self._valid_static_data())  # must not raise

    def test_invalid_components_aborts_naming_field(self):
        """A component with an empty class_name aborts, naming 'components'."""
        static_data = self._valid_static_data()
        # Bypass model validation to simulate malformed producer output reaching
        # the boundary (Pydantic would otherwise reject an empty class_name).
        bad = ComponentInfo.model_construct(
            class_name="", component_type="activity", reaches_target=True
        )
        static_data.components = Components.model_construct(activities=[bad])

        with pytest.raises(RVValidationError, match="components"):
            validate_static_data(static_data)
