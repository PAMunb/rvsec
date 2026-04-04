"""
Tests for proactive backtracking in select_next_action() (gh26 Group 5, task 5.2).

Verifies FR26 Proactive Backtracking scenarios and INV-AGT-38:
- Tier 3 triggers when saturation >= threshold
- All path plans fail -> fall through to Tier 4 (scored), NOT plain BACK
- Below threshold -> Tier 4 scored selection
- Full tier ordering: buffer -> untested -> backtrack+planning -> scored -> BACK
"""

from unittest.mock import MagicMock

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.domain.screen_node import ScreenNode
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_screen_parser.parser.screen.visitor.model import (
    ItemAction,
    ScreenDescription,
    ScreenItem,
    WidgetEventType,
)

# Safe Y coordinate — between statusbar (5%) and navbar (94%) for 1920px screen
SAFE_Y = 500


def _make_action(
    action_id,
    x=None,
    event=WidgetEventType.CLICK,
    reaches_mop=False,
    directly_reaches_mop=False,
):
    """Create ItemAction with coords in safe zone."""
    if x is None:
        x = 100 + action_id * 80
    return ItemAction(
        id=action_id,
        text=f"Action {action_id}",
        event=event,
        coordinates=(x, SAFE_Y),
        reaches_mop=reaches_mop,
        directly_reaches_mop=directly_reaches_mop,
        target_view={"class": "android.widget.Button", "package": "test.app"},
    )


def _make_screen_desc(actions, activity="com.test.MainActivity"):
    """Create ScreenDescription with given actions."""
    items = []
    for action in actions:
        item = ScreenItem(
            view={
                "resource_id": f"test:id/btn_{action.id}",
                "class": "android.widget.Button",
                "package": "test.app",
            },
            base_description=f"Button {action.id}",
            actions=[action],
        )
        items.append(item)
    return ScreenDescription(activity=activity, items=items)


def _make_strategy():
    """Create RVAgentStrategy with real graph."""
    config = RVAgentConfig(
        package_name="test.app",
        backtrack_saturation_threshold=0.8,
        stochastic_probability=0.0,
    )
    graph = DynamicStateGraph()
    ui_coverage = MagicMock()
    # Scorers call get_element_test_count — return 0 (no visits) by default
    ui_coverage.get_element_test_count = MagicMock(return_value=0)
    strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)
    strategy.successor_tracker.has_incomplete_successors = MagicMock(return_value=False)
    return strategy


def _populate_node(
    strategy, state_hash, actions, saturated_count, activity="com.test.MainActivity"
):
    """Create a screen_desc, call select_next_action to build the node, then
    manually set execution counts for desired saturation level.

    All signatures use device-space coordinates (INV-AGT-40).
    """
    screen_desc = _make_screen_desc(actions, activity)

    # First call to register the state in the graph
    strategy.select_next_action(state_hash, screen_desc)
    node = strategy.graph.states[state_hash]

    # Populate executed_actions using device-space signatures directly
    for i, action in enumerate(actions):
        sig = action.coords_for_matching
        node.executed_actions.add(sig)
        count = 2 if i < saturated_count else 1
        node.action_execution_counts[sig] = count

    return node, screen_desc


class TestProactiveBacktracking:
    """Verify proactive backtracking behavior in select_next_action()."""

    def test_backtrack_triggers_path_planning(self):
        """Saturation 0.9 -> should_backtrack() True, path planning attempted C > B > A."""
        strategy = _make_strategy()
        actions = [_make_action(i + 1) for i in range(10)]
        node, screen_desc = _populate_node(
            strategy, "state_A", actions, saturated_count=9
        )

        # Mock path_buffer that tracks planning call order
        mock_buffer = MagicMock()
        mock_buffer.is_active = False
        mock_buffer.is_cooling_down = False
        call_order = []
        mock_buffer.plan_coverage_path = MagicMock(
            side_effect=lambda *a: (call_order.append("C"), False)[1]
        )
        mock_buffer.plan_mop_path = MagicMock(
            side_effect=lambda *a, **kw: (call_order.append("B"), False)[1]
        )
        mock_buffer.plan_backtrack_path = MagicMock(
            side_effect=lambda *a: (call_order.append("A"), True)[1]
        )
        mock_buffer.get_next_action = MagicMock(return_value=_make_action(99, x=500))
        strategy.path_buffer = mock_buffer

        result = strategy.select_next_action("state_A", screen_desc)

        assert call_order == ["C", "B", "A"]
        assert result is not None
        assert result.id == 99

    def test_backtrack_all_plans_fail_falls_to_scored_continuous(self):
        """Saturation 0.9, all plans fail -> Tier 4 scored selection, NOT plain BACK."""
        strategy = _make_strategy()
        actions = [_make_action(i + 1) for i in range(10)]
        node, screen_desc = _populate_node(
            strategy, "state_A", actions, saturated_count=9
        )

        # PathBuffer with all plans failing
        mock_buffer = MagicMock()
        mock_buffer.is_active = False
        mock_buffer.is_cooling_down = False
        mock_buffer.plan_coverage_path = MagicMock(return_value=False)
        mock_buffer.plan_mop_path = MagicMock(return_value=False)
        mock_buffer.plan_backtrack_path = MagicMock(return_value=False)
        strategy.path_buffer = mock_buffer

        result = strategy.select_next_action("state_A", screen_desc)

        # Falls through to Tier 4: scored selection, NOT Tier 5 BACK
        assert result is not None
        assert result.event != WidgetEventType.BACK

    def test_below_threshold_falls_to_scored_continuous(self):
        """Saturation 0.7 < threshold 0.8 -> scored selection via ActionRanker."""
        strategy = _make_strategy()
        actions = [_make_action(i + 1) for i in range(10)]
        node, screen_desc = _populate_node(
            strategy, "state_A", actions, saturated_count=7
        )

        result = strategy.select_next_action("state_A", screen_desc)

        # Below threshold: should_backtrack() is False, all tested -> Tier 4
        assert result is not None
        assert result.event != WidgetEventType.BACK

    def test_action_selection_order(self):
        """Verify tier ordering: untested -> backtrack+planning -> scored -> BACK."""
        strategy = _make_strategy()

        # TIER 2: 3 actions, only 1 executed -> 2 untested -> picks untested
        actions_t2 = [
            _make_action(1, x=200),
            _make_action(2, x=400),
            _make_action(3, x=600),
        ]
        screen_desc_t2 = _make_screen_desc(actions_t2)

        # First call creates the node, action 1 gets pre-marked
        result_t2 = strategy.select_next_action("s1", screen_desc_t2)
        assert result_t2 is not None
        # Should be one of the untested or first selected
        assert result_t2.event == WidgetEventType.CLICK

        # TIER 3/5: empty screen, fully saturated -> RESTART (Group 12: TIER3 forces
        # RESTART when saturated with no path plan) or BACK as fallback
        empty_screen = _make_screen_desc([])
        node_empty = ScreenNode(
            screen_hash="s2", activity="com.test.Main", total_actions=0
        )
        strategy.graph.states["s2"] = node_empty

        result_back = strategy.select_next_action("s2", empty_screen)
        assert result_back is not None
        # TIER3 now forces RESTART when saturated (100% with 0 actions) and
        # no path plan available, instead of falling through to TIER5 BACK
        assert result_back.event in (WidgetEventType.BACK, WidgetEventType.RESTART)
