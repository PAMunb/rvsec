"""
Unit tests for stuck detection fixes (gh26 Group 26).

Tests 4 bug fixes that improve stuck detection accuracy:
(a) H3: StuckRecovery.check() does not increment counter for form actions
(b) M2: Dynamic stuck threshold is capped below max_blocks
(c) M3: BFS result queues multiple BACK actions via PathBuffer
(d) M4: Error detection is skipped after stuck recovery BACK
"""

from unittest.mock import MagicMock, patch

from rv_agent.routing.stuck_recovery import StuckRecovery
from rv_agent.strategies.rvagent_strategy.path_buffer import (
    PathBuffer,
    _create_back_action,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_mock_agent(
    stuck_threshold_base=8,
    stuck_threshold_factor=1.5,
    max_blocks=10,
    screen_items_count=0,
    error_detection_enabled=True,
):
    """Create a mock RVAgent with stuck detection attributes.

    Args:
        stuck_threshold_base: BASE_STUCK_THRESHOLD value.
        stuck_threshold_factor: STUCK_THRESHOLD_FACTOR value.
        max_blocks: StuckRecovery max_blocks threshold.
        screen_items_count: Number of items in screen_description.
        error_detection_enabled: Whether error detection is enabled in config.
    """
    agent = MagicMock()
    agent.BASE_STUCK_THRESHOLD = stuck_threshold_base
    agent.STUCK_THRESHOLD_FACTOR = stuck_threshold_factor
    agent.stuck_screen_count = 0
    agent.last_screen_hash = None
    agent.error_recovery_count = 0
    agent._last_action_was_stuck_back = False
    agent._cached_screen_desc = None

    # StuckRecovery
    stuck_recovery = StuckRecovery(max_blocks=max_blocks)
    agent.stuck_recovery = stuck_recovery

    # Config
    agent.config = MagicMock()
    agent.config.error_detection_enabled = error_detection_enabled
    agent.config.error_detection_confidence = 0.5
    agent.config.error_max_indicator_size = 100
    agent.config.error_max_indicator_count = 20

    # Strategy with path_buffer
    successor_tracker = MagicMock()
    successor_tracker.graph = MagicMock()
    successor_tracker.graph.states = {"s1": MagicMock(), "s2": MagicMock()}
    successor_tracker.back_successors = {}

    ui_coverage = MagicMock()
    ui_coverage.get_coverage_gap.return_value = 0.0
    ui_coverage.get_element_count.return_value = 0

    config_mock = MagicMock()
    config_mock.backtrack_saturation_threshold = 0.8

    path_buffer = PathBuffer(
        transition_manager=None,
        successor_tracker=successor_tracker,
        ui_coverage_tracker=ui_coverage,
        config=config_mock,
    )
    agent.strategy = MagicMock()
    agent.strategy.path_buffer = path_buffer
    agent.strategy.successor_tracker = successor_tracker
    agent.strategy.reward_propagator = None

    # MemoryCoordinator
    agent.memory_coordinator = MagicMock()
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

    return agent


def _make_state(
    current_hash="hash_a",
    previous_hash=None,
    current_action=None,
    current_item_action=None,
    screenshot_path=None,
    iteration=1,
):
    """Create a minimal AgentState dict for learn_node."""
    return {
        "current_screen_hash": current_hash,
        "previous_screen_hash": previous_hash,
        "current_action": current_action or {},
        "current_item_action": current_item_action,
        "current_activity": "com.example.TestActivity",
        "previous_activity": None,
        "screen_description": MagicMock(items=[]),
        "error_detection_screenshot": screenshot_path,
        "iteration": iteration,
        "start_time": 0,
        "timeout": 300,
        "recent_action_window": [],
        "visited_states": [],
        "state_transitions": [],
        "llm_reasoning": "",
        "decision_maker": "algorithm",
    }


# =============================================================================
# (a) H3: StuckRecovery.check() skips counter increment for form actions
# =============================================================================


class TestStuckRecoveryFormAction:
    """H3: StuckRecovery.check() should not increment counter for form actions."""

    def test_counter_increments_for_normal_action(self):
        """Normal action on the same state increments block counter."""
        sr = StuckRecovery(max_blocks=10)
        sr.check("hash_a")  # First call sets last_state_hash
        sr.check("hash_a")  # Same hash, should increment
        assert sr.state_block_counter == 1

    def test_counter_does_not_increment_for_form_action(self):
        """Form action (is_form_action=True) on the same state does NOT increment."""
        sr = StuckRecovery(max_blocks=10)
        sr.check("hash_a")  # First call sets last_state_hash
        sr.check("hash_a", is_form_action=True)  # Same hash but form action
        assert sr.state_block_counter == 0

    def test_form_action_prevents_recovery_trigger(self):
        """Even after max_blocks-1 normal iterations, a form action does not trigger."""
        sr = StuckRecovery(max_blocks=5)
        sr.check("hash_a")  # Sets last_state_hash

        # Bring counter to max_blocks - 1
        for _ in range(4):
            sr.check("hash_a")
        assert sr.state_block_counter == 4

        # Form action should not push it over
        result = sr.check("hash_a", is_form_action=True)
        assert result is None
        assert sr.state_block_counter == 4

    def test_normal_action_after_form_action_increments(self):
        """Normal action after a form action still increments normally."""
        sr = StuckRecovery(max_blocks=10)
        sr.check("hash_a")  # Sets last_state_hash
        sr.check("hash_a", is_form_action=True)  # No increment
        assert sr.state_block_counter == 0

        sr.check("hash_a")  # Normal action should increment
        assert sr.state_block_counter == 1

    def test_form_action_default_parameter_is_false(self):
        """Default is_form_action=False preserves backward compatibility."""
        sr = StuckRecovery(max_blocks=10)
        sr.check("hash_a")
        sr.check("hash_a")  # No is_form_action kwarg
        assert sr.state_block_counter == 1


# =============================================================================
# (b) M2: Dynamic stuck threshold is capped below max_blocks
# =============================================================================


class TestDynamicThresholdCap:
    """M2: _get_dynamic_stuck_threshold() caps result below stuck_recovery.max_blocks."""

    def test_threshold_capped_when_exceeds_max_blocks(self):
        """With many elements, threshold should be capped at max_blocks - 1."""
        from rv_agent.agent.nodes.learn_node import _get_dynamic_stuck_threshold

        agent = _make_mock_agent(
            stuck_threshold_base=8,
            stuck_threshold_factor=1.5,
            max_blocks=10,
        )
        # Create screen with 20 elements: uncapped = max(8, 20*1.5) = 30
        state = _make_state()
        state["screen_description"] = MagicMock(items=[MagicMock()] * 20)

        threshold = _get_dynamic_stuck_threshold(agent, state)

        # Should be capped to max_blocks - 1 = 9
        assert threshold == 9

    def test_threshold_not_capped_when_below_max_blocks(self):
        """With few elements, threshold remains at base (below cap)."""
        from rv_agent.agent.nodes.learn_node import _get_dynamic_stuck_threshold

        agent = _make_mock_agent(
            stuck_threshold_base=5,
            stuck_threshold_factor=1.5,
            max_blocks=10,
        )
        # Create screen with 2 elements: uncapped = max(5, 2*1.5) = 5
        state = _make_state()
        state["screen_description"] = MagicMock(items=[MagicMock()] * 2)

        threshold = _get_dynamic_stuck_threshold(agent, state)

        # base=5 < max_blocks-1=9, so not capped
        assert threshold == 5

    def test_threshold_cap_without_stuck_recovery(self):
        """Without stuck_recovery, no cap is applied."""
        from rv_agent.agent.nodes.learn_node import _get_dynamic_stuck_threshold

        agent = _make_mock_agent(
            stuck_threshold_base=8,
            stuck_threshold_factor=1.5,
            max_blocks=10,
        )
        # Remove stuck_recovery
        del agent.stuck_recovery

        state = _make_state()
        state["screen_description"] = MagicMock(items=[MagicMock()] * 20)

        threshold = _get_dynamic_stuck_threshold(agent, state)

        # Uncapped: max(8, 20*1.5) = 30
        assert threshold == 30

    def test_level1_always_fires_before_level2(self):
        """Level 1 threshold is strictly less than Level 2 (max_blocks)."""
        from rv_agent.agent.nodes.learn_node import _get_dynamic_stuck_threshold

        for max_blocks in [5, 10, 15, 20]:
            for n_elements in [0, 3, 5, 10, 50, 100]:
                agent = _make_mock_agent(
                    stuck_threshold_base=8,
                    stuck_threshold_factor=1.5,
                    max_blocks=max_blocks,
                )
                state = _make_state()
                state["screen_description"] = MagicMock(
                    items=[MagicMock()] * n_elements
                )

                threshold = _get_dynamic_stuck_threshold(agent, state)
                assert threshold < max_blocks, (
                    f"Threshold {threshold} >= max_blocks {max_blocks} "
                    f"with {n_elements} elements"
                )


# =============================================================================
# (c) M3: BFS result queues multiple BACK actions via PathBuffer
# =============================================================================


class TestBfsMultiHopPathBuffer:
    """M3: Level 2 BFS queues multi-hop BACK actions in PathBuffer."""

    def test_load_back_actions_fills_buffer(self):
        """load_back_actions() fills buffer with N BACK actions."""
        successor_tracker = MagicMock()
        successor_tracker.graph = MagicMock()
        successor_tracker.graph.states = {"s1": MagicMock()}
        successor_tracker.back_successors = {}

        pb = PathBuffer(
            transition_manager=None,
            successor_tracker=successor_tracker,
            ui_coverage_tracker=MagicMock(),
            config=MagicMock(),
        )

        pb.load_back_actions(5)

        assert pb.is_active
        assert pb.remaining_steps == 5

    def test_load_back_actions_creates_back_events(self):
        """All loaded actions are BACK actions with correct event type."""
        from rv_android_core.domain.widget import WidgetEventType

        successor_tracker = MagicMock()
        successor_tracker.graph = MagicMock()
        successor_tracker.graph.states = {"s1": MagicMock()}
        successor_tracker.back_successors = {}

        pb = PathBuffer(
            transition_manager=None,
            successor_tracker=successor_tracker,
            ui_coverage_tracker=MagicMock(),
            config=MagicMock(),
        )

        pb.load_back_actions(3)

        for _ in range(3):
            action = pb.get_next_action()
            assert action is not None
            assert action.text == "BACK"
            assert action.event == WidgetEventType.BACK

        # Buffer exhausted
        assert pb.get_next_action() is None

    def test_load_back_actions_replaces_existing_buffer(self):
        """load_back_actions() replaces any existing buffer content."""
        successor_tracker = MagicMock()
        successor_tracker.graph = MagicMock()
        successor_tracker.graph.states = {"s1": MagicMock()}
        successor_tracker.back_successors = {}

        pb = PathBuffer(
            transition_manager=None,
            successor_tracker=successor_tracker,
            ui_coverage_tracker=MagicMock(),
            config=MagicMock(),
        )

        # Pre-fill with 2 actions
        pb._buffer = [_create_back_action() for _ in range(2)]
        assert pb.remaining_steps == 2

        # Load 4 new actions — replaces existing
        pb.load_back_actions(4)
        assert pb.remaining_steps == 4

    def test_learn_node_uses_pathbuffer_for_multi_hop_bfs(self):
        """learn_node queues BFS result in PathBuffer when hop_count > 1."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = _make_mock_agent(max_blocks=3)

        # Set up stuck recovery to trigger on this call
        sr = agent.stuck_recovery
        sr.last_state_hash = "stuck_hash"
        sr.state_block_counter = sr.max_blocks  # Will trigger recovery

        # BFS finds unsaturated ancestor 3 hops away
        agent.strategy.successor_tracker.find_nearest_unsaturated.return_value = (
            "target_hash_abc",
            3,
        )

        state = _make_state(
            current_hash="stuck_hash",
            previous_hash="stuck_hash",
        )
        agent.last_screen_hash = "stuck_hash"

        result = learn_node(agent, state)

        # PathBuffer should have 3 BACK actions loaded
        pb = agent.strategy.path_buffer
        assert pb.remaining_steps == 3

        # force_back_action should NOT be in result (PathBuffer handles it)
        assert "force_back_action" not in result or not result.get("force_back_action")

    def test_learn_node_falls_back_to_force_back_for_single_hop(self):
        """learn_node uses force_back when hop_count == 1 (no PathBuffer needed)."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = _make_mock_agent(max_blocks=3)

        sr = agent.stuck_recovery
        sr.last_state_hash = "stuck_hash"
        sr.state_block_counter = sr.max_blocks

        # BFS finds unsaturated ancestor 1 hop away
        agent.strategy.successor_tracker.find_nearest_unsaturated.return_value = (
            "target_hash_abc",
            1,
        )

        state = _make_state(
            current_hash="stuck_hash",
            previous_hash="stuck_hash",
        )
        agent.last_screen_hash = "stuck_hash"

        result = learn_node(agent, state)

        # force_back_action should be set
        assert result.get("force_back_action") is True

        # PathBuffer should be empty (single hop, no buffering)
        pb = agent.strategy.path_buffer
        assert pb.remaining_steps == 0


# =============================================================================
# (d) M4: Error detection skipped after stuck recovery BACK
# =============================================================================


class TestSkipErrorDetectionAfterStuckBack:
    """M4: Error detection is skipped when last action was stuck recovery BACK."""

    def test_error_detection_skipped_when_flag_set(self):
        """When _last_action_was_stuck_back=True, error detection is bypassed."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = _make_mock_agent(error_detection_enabled=True)
        agent._last_action_was_stuck_back = True

        # Provide a screenshot (which would normally trigger error detection)
        state = _make_state(
            current_hash="hash_a",
            previous_hash="hash_b",
            screenshot_path="/tmp/screenshot.png",
        )
        agent.last_screen_hash = "hash_b"

        with patch(
            "rv_agent.agent.nodes.learn_node._detect_validation_error"
        ) as mock_detect:
            _ = learn_node(agent, state)

            # _detect_validation_error should NOT have been called
            mock_detect.assert_not_called()

        # Flag should be cleared after use
        assert agent._last_action_was_stuck_back is False

    def test_error_detection_runs_when_flag_not_set(self):
        """When _last_action_was_stuck_back=False, error detection runs normally."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = _make_mock_agent(error_detection_enabled=True)
        agent._last_action_was_stuck_back = False

        state = _make_state(
            current_hash="hash_a",
            previous_hash="hash_a",
            screenshot_path="/tmp/screenshot.png",
        )
        agent.last_screen_hash = "hash_a"

        with patch(
            "rv_agent.agent.nodes.learn_node._detect_validation_error"
        ) as mock_detect:
            mock_detect.return_value = None  # No error detected
            _ = learn_node(agent, state)

            # Detection should have been called
            mock_detect.assert_called_once()

    def test_level1_stuck_sets_flag(self):
        """Level 1 stuck recovery sets _last_action_was_stuck_back flag."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = _make_mock_agent(
            stuck_threshold_base=2,
            stuck_threshold_factor=0.5,
            max_blocks=10,
        )
        agent.last_screen_hash = "hash_stuck"
        agent.stuck_screen_count = 1  # One more will hit threshold of 2

        state = _make_state(
            current_hash="hash_stuck",
            previous_hash="hash_stuck",
            current_action={"action_type": "CLICK"},
        )

        result = learn_node(agent, state)

        # force_back should have triggered
        assert result.get("force_back_action") is True
        # Flag should be set for next iteration
        assert agent._last_action_was_stuck_back is True

    def test_level2_restart_sets_flag(self):
        """Level 2 restart recovery sets _last_action_was_stuck_back flag."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = _make_mock_agent(max_blocks=3)

        sr = agent.stuck_recovery
        sr.last_state_hash = "stuck_hash"
        sr.state_block_counter = sr.max_blocks

        # BFS finds no ancestor -> restart
        agent.strategy.successor_tracker.find_nearest_unsaturated.return_value = None

        state = _make_state(
            current_hash="stuck_hash",
            previous_hash="stuck_hash",
        )
        agent.last_screen_hash = "stuck_hash"

        result = learn_node(agent, state)

        assert result.get("force_restart_app") is True
        assert agent._last_action_was_stuck_back is True

    def test_flag_cleared_on_normal_iteration(self):
        """Flag is cleared even when screenshot_path is None (screen changed)."""
        from rv_agent.agent.nodes.learn_node import learn_node

        agent = _make_mock_agent()
        agent._last_action_was_stuck_back = True

        # No screenshot = screen changed (Branch a)
        state = _make_state(
            current_hash="hash_new",
            previous_hash="hash_old",
            screenshot_path=None,
        )
        agent.last_screen_hash = "hash_old"

        _ = learn_node(agent, state)

        # Flag should be cleared
        assert agent._last_action_was_stuck_back is False
        # Error recovery counter should be reset (Branch a behavior)
        assert agent.error_recovery_count == 0
