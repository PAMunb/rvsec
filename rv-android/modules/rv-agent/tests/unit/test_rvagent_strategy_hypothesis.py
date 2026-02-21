"""
Property-based tests for the RVAgentStrategy using Hypothesis.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import MagicMock, patch

from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy
from rv_agent.config.agent_config import RVAgentConfig
from rv_screen_parser.parser.screen.visitor.model import (
    ScreenDescription,
    ItemAction,
    WidgetEventType,
)

# --- Strategies for generating strategy components ---

# A simplified strategy for ItemAction
# We focus on the attributes that are important for the strategy's logic
item_action_strategy = st.builds(
    ItemAction,
    id=st.integers(min_value=0),
    text=st.text(max_size=20),
    event=st.sampled_from(list(WidgetEventType)),
    reaches_mop=st.booleans(),
    directly_reaches_mop=st.booleans(),
    target_view=st.fixed_dictionaries({}),
    coordinates=st.tuples(
        st.integers(min_value=0, max_value=1080),
        st.integers(min_value=0, max_value=1920),
    ),
    text_input=st.none(),
).map(lambda action: action.model_copy(update={"action_type": action.event.name}))


@pytest.mark.hypothesis
class TestRVAgentStrategyHypothesis:
    """Property-based tests for the RVAgentStrategy helper methods."""

    def _create_strategy(self):
        """Helper method to create a fresh RVAgentStrategy instance."""
        from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
        from rv_agent.memory.ui_coverage import UICoverageTracker

        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        config = RVAgentConfig.create_default(package_name="com.example.app")
        return RVAgentStrategy(graph, ui_coverage, config=config)

    @given(actions=st.lists(item_action_strategy, min_size=1, max_size=10))
    @settings(deadline=500, max_examples=20)
    def test_select_priority_action_prioritizes_mop(self, actions):
        """Ensures that direct MOPs are always chosen if available."""
        strategy = self._create_strategy()

        # Ensure at least one action is a direct MOP
        if len(actions) > 0:
            actions[0].directly_reaches_mop = True
            actions[0].reaches_mop = True

        # Ensure other actions are not direct MOPs
        for i in range(1, len(actions)):
            actions[i].directly_reaches_mop = False

        selected = strategy._select_priority_action(actions, MagicMock())

        assert selected.directly_reaches_mop is True

    @given(actions=st.lists(item_action_strategy, min_size=1, max_size=10))
    @settings(deadline=500, max_examples=20)
    def test_select_priority_action_prioritizes_transitive_mop(self, actions):
        """Ensures that transitive MOPs are chosen over regular actions."""
        strategy = self._create_strategy()

        # Ensure no direct MOPs
        for action in actions:
            action.directly_reaches_mop = False

        # Ensure at least one is a transitive MOP
        if len(actions) > 0:
            actions[0].reaches_mop = True

        # Ensure others are not transitive MOPs
        for i in range(1, len(actions)):
            actions[i].reaches_mop = False

        selected = strategy._select_priority_action(actions, MagicMock())

        assert selected.reaches_mop is True
        assert selected.directly_reaches_mop is False

    @given(
        x=st.integers(min_value=0, max_value=1080),
        y=st.integers(min_value=0, max_value=2000),
    )
    @settings(deadline=500, max_examples=20)
    def test_is_system_action(self, x, y):
        """Tests the logic for identifying system actions based on coordinates."""
        strategy = self._create_strategy()

        action = MagicMock(spec=ItemAction)
        action.coordinates = (x, y)
        action.target_view = {}

        is_system = strategy._is_system_action(action)

        # Thresholds: NAVBAR_Y_PERCENT=0.94 (1920*0.94=1804.8), STATUSBAR_Y_PERCENT=0.05 (1920*0.05=96)
        navbar_threshold = 1920 * RVAgentStrategy.NAVBAR_Y_PERCENT
        statusbar_threshold = 1920 * RVAgentStrategy.STATUSBAR_Y_PERCENT

        if y > navbar_threshold or y < statusbar_threshold:
            assert is_system is True
        else:
            assert is_system is False

    @given(action=item_action_strategy)
    @settings(deadline=500, max_examples=20)
    def test_is_system_action_no_coords(self, action):
        """Tests that an action with no coordinates is considered a system action."""
        strategy = self._create_strategy()

        action.coordinates = None
        assert strategy._is_system_action(action) is True
