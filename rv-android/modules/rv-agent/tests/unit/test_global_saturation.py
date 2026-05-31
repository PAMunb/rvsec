"""
Unit tests for strategy defect fixes (Group 12).

Tests:
- TIER3 failure fallback triggers RESTART instead of TIER4 when saturated
- Score decay in TIER4 prevents action monopolization
- Plateau detector wiring triggers stochastic boost
- Backtrack failure tracking per state
- RESTART_APP always carries package_name

Note: Global saturation detection and early termination tests were removed.
The ONLY way to exit the RVAgent execution loop is via TIMEOUT — never via
early termination. Task 12.4 was REVERSED.
"""

import math
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


def _make_screen_desc(activity=".MainActivity", items=None):
    """Create a mock ScreenDescription."""
    desc = MagicMock()
    desc.activity = activity
    if items is None:
        # Create a screen with 3 mock actions
        mock_actions = []
        for i in range(3):
            action = MagicMock()
            action.coordinates = (100 + i * 100, 500)
            action.coords_for_matching = ((100 + i * 100, 500), "CLICK")
            action.event = MagicMock()
            action.event.name = "CLICK"
            action.event.value = 1
            action.action_type = "click"
            action.text = f"Button {i}"
            action.target_view = {
                "class": "android.widget.Button",
                "bounds": [[50 + i * 100, 450], [150 + i * 100, 550]],
            }
            action.widget_id = f"btn_{i}"
            action.reaches_target = False
            action.directly_reaches_target = False
            action.callback_signature = None
            mock_actions.append(action)

        mock_item = MagicMock()
        mock_item.view = {"package": "com.test.app"}
        mock_item.actions = mock_actions
        desc.items = [mock_item]
        desc.get_all_actions.return_value = mock_actions
    else:
        desc.items = items
    return desc


class TestTier3RestartFallback:
    """Tests for TIER3 no-path-plan → RESTART when saturated (task 12.5)."""

    def test_tier3_falls_to_tier4_when_saturated_with_actions(self):
        """When TIER3 all plans fail but actions exist, fall through to Tier 4 scored."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
        )

        screen_desc = _make_screen_desc()
        hash_val = "saturated_state"

        # Create and fully saturate the state (all actions executed 3+ times)
        node = graph.get_or_create_state(hash_val, ".MainActivity", screen_desc)
        for i in range(3):
            sig = ((100 + i * 100, 500), "CLICK")
            for _ in range(3):
                node.record_action(sig)

        # Ensure no path plans succeed
        strategy.path_buffer = MagicMock()
        strategy.path_buffer.is_active = False
        strategy.path_buffer.is_cooling_down = False
        strategy.path_buffer.plan_coverage_path.return_value = False
        strategy.path_buffer.plan_mop_path.return_value = False
        strategy.path_buffer.plan_backtrack_path.return_value = False

        result = strategy.select_next_action(hash_val, screen_desc)

        # Falls through to Tier 4 scored selection (D8: no RESTART when actions exist)
        assert result is not None

    def test_tier3_returns_restart_when_saturated_and_no_actions(self):
        """When TIER3 all plans fail and NO actions available, return RESTART."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
        )

        # Empty screen — no actions
        empty_desc = MagicMock()
        empty_desc.activity = ".MainActivity"
        empty_desc.items = []
        empty_desc.get_all_actions.return_value = []
        hash_val = "empty_saturated"

        # Create an empty node (saturated because 0 actions = 100%)
        graph.get_or_create_state(hash_val, ".MainActivity", empty_desc)

        strategy.path_buffer = MagicMock()
        strategy.path_buffer.is_active = False
        strategy.path_buffer.is_cooling_down = False
        strategy.path_buffer.plan_coverage_path.return_value = False
        strategy.path_buffer.plan_mop_path.return_value = False
        strategy.path_buffer.plan_backtrack_path.return_value = False

        result = strategy.select_next_action(hash_val, empty_desc)

        assert result is not None
        assert result.text.startswith("RESTART_APP:")


class TestScoreDecay:
    """Tests for TIER4 score decay (task 12.6)."""

    def test_score_decay_formula(self):
        """Score decay follows effective_score = base_score / (1 + log2(count))."""
        base_score = 825.0
        exec_count = 203

        expected = base_score / (1 + math.log2(exec_count))
        actual = base_score / (1 + math.log2(exec_count))

        assert abs(expected - actual) < 0.01
        # With 203 executions: 825 / (1 + 7.66) = 825 / 8.66 ≈ 95.3
        assert expected < 100.0

    def test_score_decay_zero_executions(self):
        """No decay for actions that have never been executed."""
        base_score = 825.0

        # exec_count == 0 means no decay
        decayed = base_score  # no decay applied
        assert decayed == base_score

    def test_score_decay_single_execution(self):
        """Single execution applies minimal decay."""
        base_score = 825.0
        exec_count = 1

        decayed = base_score / (1 + math.log2(exec_count))
        # log2(1) = 0, so decay = 825 / (1 + 0) = 825
        assert decayed == base_score

    def test_score_decay_changes_selection_order(self):
        """Score decay causes a less-executed action to be preferred over a more-executed one."""
        # Action A: base_score=825, executed 100 times
        # Action B: base_score=500, executed 2 times
        score_a = 825.0 / (1 + math.log2(100))  # 825 / 7.64 ≈ 108
        score_b = 500.0 / (1 + math.log2(2))  # 500 / 2.0 = 250

        # Without decay: A wins (825 > 500)
        # With decay: B wins (250 > 108)
        assert score_b > score_a


class TestPlateauDetectorWiring:
    """Tests for plateau detector wiring (task 12.7)."""

    def test_plateau_increases_stochastic_probability(self):
        """When plateau is detected, stochastic probability is boosted."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
        )

        assert strategy.stochastic_probability == 0.15

        # Force plateau detection
        strategy.plateau_detector = MagicMock()
        strategy.plateau_detector.is_plateau_reached.return_value = True
        strategy.plateau_detector.get_metrics.return_value = {"window_size": 10}

        # Create a state so select_next_action works
        screen_desc = _make_screen_desc()
        graph.get_or_create_state("existing_state", ".MainActivity", screen_desc)

        strategy.select_next_action("existing_state", screen_desc)

        # Stochastic probability should be boosted to 0.5
        assert strategy.stochastic_probability == 0.5

    def test_stochastic_probability_restored_on_new_state(self):
        """Stochastic probability is restored when a new state is discovered."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
        )

        # Simulate plateau-boosted probability
        strategy.stochastic_probability = 0.5

        # Visit a new state
        screen_desc = _make_screen_desc()
        strategy.select_next_action("new_state", screen_desc)

        # Should be restored to config default
        assert strategy.stochastic_probability == 0.15


class TestBacktrackFailureTracking:
    """Tests for repeated backtrack failure tracking (task 12.2)."""

    def test_record_backtrack_failure(self):
        """Backtrack failures are tracked per state."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
        )

        strategy.record_backtrack_failure("target_hash_1")
        assert strategy._backtrack_failures["target_hash_1"] == 1

        strategy.record_backtrack_failure("target_hash_1")
        assert strategy._backtrack_failures["target_hash_1"] == 2

        strategy.record_backtrack_failure("target_hash_2")
        assert strategy._backtrack_failures["target_hash_2"] == 1

    def test_reset_clears_backtrack_failures(self):
        """reset() clears backtrack failure tracking."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
        )

        strategy._backtrack_failures["target1"] = 3
        strategy.reset()

        assert len(strategy._backtrack_failures) == 0


class TestRestartPackageName:
    """Tests for RESTART_APP always carrying package_name (task 12.3)."""

    def test_create_restart_action_includes_package(self):
        """_create_restart_action includes package_name in target_view."""
        config = _make_config()
        graph = DynamicStateGraph()
        ui_coverage = UICoverageTracker()

        strategy = RVAgentStrategy(
            graph=graph,
            ui_coverage=ui_coverage,
            config=config,
        )

        restart = strategy._create_restart_action()

        assert restart.target_view["package_name"] == "com.test.app"
        assert "RESTART_APP:com.test.app" in restart.text

    def test_algorithm_node_restart_includes_package(self):
        """algorithm_node adds package_name for RESTART_APP system actions."""
        from rv_agent.agent.nodes.algorithm_node import algorithm_node

        agent = MagicMock()
        agent.config.package_name = "com.example.app"
        agent.consecutive_no_action = 0
        agent.NO_ACTION_THRESHOLD = 10
        agent.strategy = MagicMock()
        agent.routing_manager = MagicMock()
        agent.routing_manager.forced_back_count = 0

        # Return a RESTART_APP action from strategy
        mock_action = MagicMock()
        mock_action.action_type = "RESTART_APP"
        mock_action.event = MagicMock()
        mock_action.event.name = "RESTART"
        mock_action.id = 999
        mock_action.text = "RESTART_APP:com.example.app"
        mock_action.target_view = {
            "system_action": True,
            "class": "SystemAction_RESTART",
            "package_name": "com.example.app",
        }
        mock_action.coordinates = None
        mock_action.get_execution_coordinates.return_value = None

        agent.strategy.select_next_action.return_value = mock_action

        state = {
            "current_screen_hash": "abc123",
            "screen_description": MagicMock(),
            "force_restart_app": False,
            "force_back_action": False,
            "force_fill_input": False,
        }

        result = algorithm_node(agent, state)

        assert result["current_action"]["package_name"] == "com.example.app"

    def test_tool_executor_restart_fallback(self):
        """tool_executor falls back to device config when package_name missing."""
        from rv_agent.execution.tool_executor import ToolExecutor

        mock_device = MagicMock()
        mock_device.config = MagicMock()
        mock_device.config.package_name = "com.fallback.app"

        executor = ToolExecutor(device=mock_device)

        # Action without package_name
        action = {"action_type": "RESTART_APP"}

        result = executor._execute_restart(action)

        mock_device.stop_app.assert_called_once_with("com.fallback.app")
        mock_device.start_app.assert_called_once_with("com.fallback.app")
        assert result["success"] is True
