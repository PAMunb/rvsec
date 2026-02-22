"""
Tests for Group 28 low-priority bug fixes (gh26).

Covers:
(a) L2: force_restart_app declared in AgentState TypedDict
(b) L3: Level 1 stuck detection does not trigger on consecutive None hashes
(c) L4: algorithm_node returns BACK action when strategy returns None
"""

from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# (a) L2: force_restart_app in AgentState
# ---------------------------------------------------------------------------


class TestForceRestartAppDeclared:
    """Verify force_restart_app is declared in the AgentState TypedDict."""

    def test_force_restart_app_in_annotations(self):
        """AgentState.__annotations__ includes 'force_restart_app' as bool."""
        from rv_agent.domain.state import AgentState

        annotations = AgentState.__annotations__
        assert "force_restart_app" in annotations
        assert annotations["force_restart_app"] is bool

    def test_force_restart_app_alongside_force_back_action(self):
        """Both force_back_action and force_restart_app are declared."""
        from rv_agent.domain.state import AgentState

        annotations = AgentState.__annotations__
        assert "force_back_action" in annotations
        assert "force_restart_app" in annotations


# ---------------------------------------------------------------------------
# (b) L3: Level 1 stuck detection guards against None hashes
# ---------------------------------------------------------------------------


class TestLevel1NoneHashGuard:
    """Verify that two consecutive None hashes do not trigger stuck detection."""

    def _make_agent(self):
        """Create minimal mock agent for learn_node testing."""
        agent = MagicMock()
        agent.last_screen_hash = None
        agent.stuck_screen_count = 0
        agent._last_action_was_stuck_back = False
        agent.error_recovery_count = 0
        agent.config.error_detection_enabled = False

        # Memory coordinator
        agent.memory_coordinator.update_memories.return_value = {
            "recent_action_window": [],
        }
        agent.memory_coordinator.generate_summaries.return_value = {
            "action_history_summary": "",
            "exploration_summary": "",
            "memory_insights": "",
            "navigation_path": "",
        }
        agent.memory_coordinator.track_state_discovery.return_value = {
            "visited_states": [],
            "state_transitions": [],
        }
        agent.memory_coordinator.check_continuation.return_value = {
            "should_continue": True,
        }

        # Strategy for _record_back_transition etc.
        agent.strategy.successor_tracker = MagicMock()
        agent.strategy.reward_propagator = MagicMock()
        agent.strategy.path_buffer = MagicMock()
        agent.strategy.path_buffer.is_active = False
        agent.strategy.graph = MagicMock()
        agent.strategy.graph.states = {}

        # Stuck recovery
        agent.stuck_recovery = None

        # BASE_STUCK_THRESHOLD for dynamic threshold
        agent.BASE_STUCK_THRESHOLD = 8
        agent.STUCK_THRESHOLD_FACTOR = 1.5

        return agent

    def test_none_hash_does_not_increment_stuck_count(self):
        """When both current and previous hashes are None, stuck_screen_count stays 0."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = self._make_agent()
        agent.last_screen_hash = None

        state = {
            "current_screen_hash": None,
            "current_activity": "TestActivity",
            "previous_screen_hash": None,
            "screen_description": None,
            "current_action": {"action_type": "CLICK", "x": 100, "y": 200},
            "current_item_action": None,
            "iteration": 1,
            "start_time": 0,
            "timeout": 300,
            "visited_states": [],
            "state_transitions": [],
            "recent_action_window": [],
            "llm_reasoning": "",
            "error_detection_screenshot": None,
            "previous_activity": None,
            "decision_maker": "algorithm",
        }

        result = learn_node(agent, state)

        # stuck_screen_count should NOT have incremented (guard prevents None == None match)
        assert agent.stuck_screen_count == 0
        # force_back_action should NOT be set
        assert result.get("force_back_action") is not True

    def test_real_hash_still_triggers_stuck(self):
        """When real hashes match, stuck detection still works normally."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = self._make_agent()
        agent.last_screen_hash = "abc123"
        agent.stuck_screen_count = 7  # One below threshold of 8
        agent.BASE_STUCK_THRESHOLD = 8

        # Mock screen_description with items so dynamic threshold is reasonable
        mock_screen_desc = MagicMock()
        mock_screen_desc.items = [MagicMock() for _ in range(3)]  # 3 elements

        state = {
            "current_screen_hash": "abc123",
            "current_activity": "TestActivity",
            "previous_screen_hash": "abc123",
            "screen_description": mock_screen_desc,
            "current_action": {"action_type": "CLICK", "x": 100, "y": 200},
            "current_item_action": None,
            "iteration": 10,
            "start_time": 0,
            "timeout": 300,
            "visited_states": [],
            "state_transitions": [],
            "recent_action_window": [],
            "llm_reasoning": "",
            "error_detection_screenshot": None,
            "previous_activity": None,
            "decision_maker": "algorithm",
        }

        result = learn_node(agent, state)

        # With 3 elements, dynamic threshold = max(8, 3*1.5) = 8
        # stuck_screen_count was 7, now incremented to 8 >= threshold 8
        assert result.get("force_back_action") is True


# ---------------------------------------------------------------------------
# (c) L4: algorithm_node returns BACK when strategy returns None
# ---------------------------------------------------------------------------


class TestAlgorithmNodeBackFallback:
    """Verify algorithm_node returns BACK action when strategy returns None."""

    def _make_agent(self):
        """Create minimal mock agent for algorithm_node testing."""
        agent = MagicMock()
        agent.consecutive_no_action = 0
        agent.NO_ACTION_THRESHOLD = 5
        agent.strategy.select_next_action.return_value = None
        agent.strategy._current_iteration = 0
        agent.config.package_name = "com.example.test"
        return agent

    def test_returns_back_action_when_strategy_returns_none(self):
        """When strategy returns None, algorithm_node returns BACK, not decision_path=end."""
        from rv_agent.agent.nodes.algorithm_node import algorithm_node

        agent = self._make_agent()
        state = {
            "current_screen_hash": "hash_abc",
            "screen_description": MagicMock(),
            "force_back_action": False,
            "force_restart_app": False,
            "force_fill_input": False,
            "iteration": 5,
        }

        result = algorithm_node(agent, state)

        # Should return an action, not None
        assert result["current_action"] is not None
        assert result["current_action"]["action_type"] == "BACK"
        assert result["current_action"]["reason"] == "strategy_no_action_fallback"
        assert result["current_action"]["source"] == "algorithm"

        # Should NOT have decision_path=end
        assert "decision_path" not in result or result.get("decision_path") != "end"

        # decision_maker should be "algorithm"
        assert result["decision_maker"] == "algorithm"

    def test_increments_consecutive_no_action(self):
        """consecutive_no_action counter still increments on strategy None."""
        from rv_agent.agent.nodes.algorithm_node import algorithm_node

        agent = self._make_agent()
        agent.consecutive_no_action = 2

        state = {
            "current_screen_hash": "hash_abc",
            "screen_description": MagicMock(),
            "force_back_action": False,
            "force_restart_app": False,
            "force_fill_input": False,
            "iteration": 5,
        }

        algorithm_node(agent, state)
        assert agent.consecutive_no_action == 3

    def test_back_action_has_zero_coordinates(self):
        """BACK fallback uses (0, 0) coordinates like other BACK actions."""
        from rv_agent.agent.nodes.algorithm_node import algorithm_node

        agent = self._make_agent()
        state = {
            "current_screen_hash": "hash_abc",
            "screen_description": MagicMock(),
            "force_back_action": False,
            "force_restart_app": False,
            "force_fill_input": False,
            "iteration": 5,
        }

        result = algorithm_node(agent, state)

        assert result["current_action"]["x"] == 0
        assert result["current_action"]["y"] == 0
