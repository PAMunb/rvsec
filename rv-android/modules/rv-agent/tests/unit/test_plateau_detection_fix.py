"""
Tests for plateau detection fix (gh26 Group 24).

Verifies the H2 bug fix: record_transition() was checking
`to_hash not in self.graph.states` to determine new-state discovery,
but select_next_action() had already added the state via
get_or_create_state(). So PlateauDetector always received
discovered_new_state=False, triggering plateau mode (50% stochastic)
after 10 iterations even when new states were being discovered.

Fix: select_next_action() stores `is_new_state` in `_last_is_new_state`
BEFORE adding it to the graph. record_transition() reads this flag
instead of re-checking the graph.
"""

from unittest.mock import MagicMock

from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.strategies.rvagent_strategy.rvagent_strategy import RVAgentStrategy


def _make_config(**overrides):
    """Create a mock config with defaults."""
    config = MagicMock()
    config.seed = None
    config.plateau_window = 10
    config.max_input_variations = 3
    config.mop_max_input_variations = 11
    config.stochastic_probability = 0.15
    config.stochastic_temperature = 1.0
    config.package_name = "com.test.app"
    config.device_dimensions = (1080, 1920)
    config.scroll_probability = 0.15
    config.backtrack_saturation_threshold = 0.8
    config.max_re_enables = 6
    config.ui_coverage_threshold = 0.9
    config.mop_direct_score = 500.0
    config.mop_transitive_score = 300.0
    config.wtg_guided_score = 150.0
    config.unsaturated_bonus = 100.0
    config.visitation_penalty_factor = -15.0
    config.strength_weight = 50.0
    config.gradual_decay_base = 200.0
    config.gradual_decay_rate = 0.7
    config.gradual_decay_min_visits = 5
    config.component_high_priority = 50.0
    config.component_medium_priority = 40.0
    config.reward_gamma = 0.8
    config.reward_score_weight = 1.0
    config.coverage_density_weight = 200.0
    for k, v in overrides.items():
        setattr(config, k, v)
    return config


def _make_screen_desc(activity=".MainActivity"):
    """Create a mock ScreenDescription with 3 clickable actions."""
    desc = MagicMock()
    desc.activity = activity

    mock_actions = []
    for i in range(3):
        action = MagicMock()
        action.coordinates = (100 + i * 100, 500)
        action.coords_for_matching = ((100 + i * 100, 500), "CLICK")
        action.event = MagicMock()
        action.event.name = "CLICK"
        action.event.value = 1
        action.text = f"Button {i}"
        action.target_view = {
            "class": "android.widget.Button",
            "bounds": [[50 + i * 100, 450], [150 + i * 100, 550]],
        }
        action.widget_id = f"btn_{i}"
        action.reaches_target = False
        action.directly_reaches_target = False
        action.callback_signature = None
        action.text_input = None
        mock_actions.append(action)

    mock_item = MagicMock()
    mock_item.view = {"package": "com.test.app"}
    mock_item.actions = mock_actions
    desc.items = [mock_item]
    desc.get_all_actions.return_value = mock_actions
    return desc


def _make_action(coords=(300, 500)):
    """Create a mock ItemAction for record_transition calls."""
    action = MagicMock()
    action.coordinates = coords
    action.coords_for_matching = (coords, "CLICK")
    action.callback_signature = None
    return action


class TestLastIsNewStateFlag:
    """Verify _last_is_new_state is set correctly in select_next_action."""

    def test_new_state_sets_flag_true(self):
        """When visiting a state for the first time, _last_is_new_state is True."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        assert strategy._last_is_new_state is False  # initial value

        screen_desc = _make_screen_desc()
        strategy.select_next_action("brand_new_state", screen_desc)

        assert strategy._last_is_new_state is True

    def test_revisit_sets_flag_false(self):
        """When revisiting an existing state, _last_is_new_state is False."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        screen_desc = _make_screen_desc()

        # First visit — creates the state
        strategy.select_next_action("state_A", screen_desc)
        assert strategy._last_is_new_state is True

        # Second visit — state already in graph
        strategy.select_next_action("state_A", screen_desc)
        assert strategy._last_is_new_state is False

    def test_alternating_new_and_revisit(self):
        """Flag alternates correctly between new and revisited states."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        screen_desc = _make_screen_desc()

        # New state
        strategy.select_next_action("state_1", screen_desc)
        assert strategy._last_is_new_state is True

        # Revisit
        strategy.select_next_action("state_1", screen_desc)
        assert strategy._last_is_new_state is False

        # Another new state
        strategy.select_next_action("state_2", screen_desc)
        assert strategy._last_is_new_state is True


class TestPlateauDetectorReceivesCorrectFlag:
    """Verify PlateauDetector.record_iteration receives the correct discovered_new_state."""

    def test_new_state_passes_true_to_plateau_detector(self):
        """record_transition passes discovered_new_state=True for genuinely new states."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        screen_desc = _make_screen_desc()

        # Visit a new state (sets _last_is_new_state = True)
        strategy.select_next_action("state_A", screen_desc)
        assert strategy._last_is_new_state is True

        # Now record transition — plateau detector should get True
        action = _make_action()
        strategy.record_transition("state_prev", "state_A", action)

        # Verify via total_states_discovered counter
        assert strategy.plateau_detector.total_states_discovered == 1

    def test_revisit_passes_false_to_plateau_detector(self):
        """record_transition passes discovered_new_state=False for revisited states."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        screen_desc = _make_screen_desc()

        # First visit creates state
        strategy.select_next_action("state_A", screen_desc)

        # Revisit (sets _last_is_new_state = False)
        strategy.select_next_action("state_A", screen_desc)
        assert strategy._last_is_new_state is False

        action = _make_action()
        strategy.record_transition("state_A", "state_A", action)

        # No new state discovered in the revisit
        assert strategy.plateau_detector.total_states_discovered == 0

    def test_multiple_new_states_counted(self):
        """Each new state discovery increments total_states_discovered."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        action = _make_action()

        for i in range(5):
            screen_desc = _make_screen_desc(activity=f".Activity{i}")
            strategy.select_next_action(f"state_{i}", screen_desc)
            strategy.record_transition(
                f"state_{i - 1}" if i > 0 else "start", f"state_{i}", action
            )

        assert strategy.plateau_detector.total_states_discovered == 5


class TestPlateauNotTriggeredWithRegularDiscovery:
    """Verify plateau is NOT triggered when new states are discovered regularly."""

    def test_no_plateau_with_new_state_every_iteration(self):
        """Discovering a new state every iteration prevents plateau detection."""
        config = _make_config(plateau_window=10)
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        action = _make_action()

        # Simulate 15 iterations, each with a new state
        for i in range(15):
            screen_desc = _make_screen_desc(activity=f".Activity{i}")
            strategy.select_next_action(f"state_{i}", screen_desc)
            strategy.record_transition(
                f"state_{i - 1}" if i > 0 else "start", f"state_{i}", action
            )

        # Plateau should NOT be reached — every iteration discovered a new state
        assert not strategy.plateau_detector.is_plateau_reached()
        assert strategy.plateau_detector.total_states_discovered == 15

    def test_no_plateau_within_first_10_iterations_with_discoveries(self):
        """Plateau requires a full window (10 iterations) to activate."""
        config = _make_config(plateau_window=10)
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        action = _make_action()

        # 5 iterations with new states — window not full yet
        for i in range(5):
            screen_desc = _make_screen_desc(activity=f".Activity{i}")
            strategy.select_next_action(f"state_{i}", screen_desc)
            strategy.record_transition(
                f"state_{i - 1}" if i > 0 else "start", f"state_{i}", action
            )

        assert not strategy.plateau_detector.is_plateau_reached()

    def test_plateau_triggered_after_10_revisits(self):
        """Plateau IS triggered after 10 consecutive iterations without new states."""
        config = _make_config(plateau_window=10)
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        action = _make_action()

        # Create one state first
        screen_desc = _make_screen_desc()
        strategy.select_next_action("only_state", screen_desc)
        strategy.record_transition("start", "only_state", action)

        # Then revisit it 10 times (no new states)
        for _ in range(10):
            strategy.select_next_action("only_state", screen_desc)
            strategy.record_transition("only_state", "only_state", action)

        # Now plateau should be triggered (10 consecutive no-discovery iterations)
        assert strategy.plateau_detector.is_plateau_reached()

    def test_stochastic_probability_not_boosted_when_discovering_states(self):
        """With regular discoveries, stochastic probability stays at config default."""
        config = _make_config(plateau_window=10)
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        # Simulate 15 iterations with new states each time
        for i in range(15):
            screen_desc = _make_screen_desc(activity=f".Activity{i}")
            strategy.select_next_action(f"state_{i}", screen_desc)

        # Stochastic probability should remain at default (not boosted)
        assert strategy.stochastic_probability == config.stochastic_probability


class TestBugReproduction:
    """Reproduce the original H2 bug and verify the fix."""

    def test_old_behavior_would_miss_new_states(self):
        """Demonstrates the fix: after select_next_action creates the state,
        record_transition correctly reports it as new via _last_is_new_state.

        Before the fix, record_transition() checked `to_hash not in self.graph.states`,
        which was always False because select_next_action() had already added the state.
        """
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()
        strategy = RVAgentStrategy(graph=graph, ui_coverage=ui_coverage, config=config)

        screen_desc = _make_screen_desc()
        action = _make_action()

        # Step 1: select_next_action adds "new_hash" to graph
        strategy.select_next_action("new_hash", screen_desc)

        # At this point, "new_hash" IS in self.graph.states
        assert "new_hash" in graph.states

        # Step 2: record_transition is called
        strategy.record_transition("prev_hash", "new_hash", action)

        # With the fix, PlateauDetector correctly gets discovered_new_state=True
        # (Before the fix, it would always get False here)
        assert strategy.plateau_detector.total_states_discovered == 1
        assert strategy.plateau_detector.state_discovery[-1] is True
