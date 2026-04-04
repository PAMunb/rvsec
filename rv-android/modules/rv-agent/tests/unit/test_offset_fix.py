"""
Unit tests for Group 30: One-iteration offset fix.

The offset fix corrects the attribution of action success, reward, and
transition recording. learn_node runs AFTER execute_node, so the hash
comparison (previous_hash vs current_hash) measures the EFFECT of the
PREVIOUS iteration's action, not the current one. Success and reward must
be attributed to previous_action_signature, not whatever action runs in
the current iteration.

Tests:
(a) _record_action_success attributes success to previous_action_signature, not current
(b) First iteration (previous_action_signature=None) returns early (skips attribution)
(c) _propagate_reward uses previous_action_signature for reward propagation
(d) execute_node transition recording uses previous_action_signature
(e) RVTRACK:ATTRIBUTION is emitted with source="previous"
"""

from unittest.mock import MagicMock, patch


from rv_agent.agent.nodes.learn_node import _propagate_reward, _record_action_success
from rv_agent.agent.nodes.execute_node import execute_node

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent_with_graph(state_hash: str):
    """Build a minimal agent mock with a strategy graph containing one state."""
    agent = MagicMock()
    agent.error_recovery_count = 0
    agent.stuck_screen_count = 0
    agent.last_screen_hash = None
    agent.stuck_recovery = None
    agent._last_action_was_stuck_back = False

    mock_node = MagicMock()
    mock_node.action_success_counts = {}
    mock_node.get_action_execution_count.return_value = 1
    mock_node.get_action_strength.return_value = 0.5

    mock_graph = MagicMock()
    mock_graph.states = {state_hash: mock_node}

    agent.strategy.graph = mock_graph
    agent.strategy.reward_propagator = None  # disabled by default

    return agent, mock_node


def _base_state():
    """Return a minimal state dict with sensible defaults."""
    return {
        "iteration": 5,
        "current_screen_hash": "hash_B",
        "previous_screen_hash": "hash_A",
        "current_action": {"action_type": "CLICK", "x": 100, "y": 200},
        "current_item_action": None,
        "previous_action_signature": ((100, 200), "click"),
        "previous_activity": "ActivityA",
        "current_activity": "ActivityB",
        "screen_description": None,
        "error_detection_screenshot": None,
        "decision_maker": "algorithm",
        "llm_reasoning": "",
        "recent_action_window": [],
        "visited_states": [],
        "state_transitions": [],
        "start_time": 0.0,
        "timeout": 300,
    }


# ---------------------------------------------------------------------------
# (a) Success is attributed to previous_action_signature, not current action
# ---------------------------------------------------------------------------


class TestSuccessAttributedToPreviousAction:
    """(a) _record_action_success uses previous_action_signature, not current_action."""

    def test_record_success_calls_node_with_previous_signature(self):
        """record_action_success is called on the node for previous_action_signature."""
        prev_sig = ((100, 200), "click")
        agent, mock_node = _make_agent_with_graph("hash_A")

        state = _base_state()
        state["previous_action_signature"] = prev_sig
        # Hashes differ -> success=True
        state["previous_screen_hash"] = "hash_A"
        state["current_screen_hash"] = "hash_B"

        _record_action_success(agent, state)

        mock_node.record_action_success.assert_called_once_with(prev_sig, True)

    def test_record_success_detects_failure_when_hashes_equal(self):
        """When prev_hash == current_hash, action is marked as failure."""
        prev_sig = ((300, 400), "click")
        agent, mock_node = _make_agent_with_graph("hash_X")

        state = _base_state()
        state["previous_action_signature"] = prev_sig
        state["previous_screen_hash"] = "hash_X"
        state["current_screen_hash"] = "hash_X"  # No change

        _record_action_success(agent, state)

        mock_node.record_action_success.assert_called_once_with(prev_sig, False)

    def test_current_action_signature_not_used_for_attribution(self):
        """The current_action coordinates are NOT used to look up the node."""
        # previous action was at (100, 200); current action is at (999, 999)
        prev_sig = ((100, 200), "click")
        agent, mock_node = _make_agent_with_graph("hash_A")

        state = _base_state()
        state["previous_action_signature"] = prev_sig
        # current_action has completely different coords — should be ignored
        state["current_action"] = {"action_type": "CLICK", "x": 999, "y": 999}
        state["previous_screen_hash"] = "hash_A"
        state["current_screen_hash"] = "hash_B"

        _record_action_success(agent, state)

        # Node was looked up by previous_screen_hash ("hash_A"), not current_screen_hash
        assert "hash_A" in agent.strategy.graph.states
        # record_action_success was called with the PREVIOUS signature, not (999,999)
        call_args = mock_node.record_action_success.call_args[0]
        assert call_args[0] == prev_sig
        assert call_args[0] != ((999, 999), "click")


# ---------------------------------------------------------------------------
# (b) First iteration (previous_action_signature=None) skips attribution
# ---------------------------------------------------------------------------


class TestFirstIterationSkipsAttribution:
    """(b) When previous_action_signature is None, _record_action_success returns early."""

    def test_first_iteration_does_not_call_record_action_success(self):
        """No node lookup or record_action_success call when previous_action_signature is None."""
        agent, mock_node = _make_agent_with_graph("hash_A")

        state = _base_state()
        state["previous_action_signature"] = None
        state["iteration"] = 0

        _record_action_success(agent, state)

        mock_node.record_action_success.assert_not_called()

    def test_first_iteration_propagate_reward_skips_recording(self):
        """_propagate_reward also returns early on first iteration (None signature)."""
        agent = MagicMock()
        mock_propagator = MagicMock()
        agent.strategy.reward_propagator = mock_propagator

        state = _base_state()
        state["previous_action_signature"] = None
        state["iteration"] = 0

        _propagate_reward(agent, state)

        mock_propagator.record_action.assert_not_called()

    def test_attribution_track_called_with_skipped_on_first_iteration(self):
        """RVTRACK:ATTRIBUTION is emitted with source='skipped' for first iteration."""
        from rv_agent import tracking as track

        agent, _ = _make_agent_with_graph("hash_A")

        state = _base_state()
        state["previous_action_signature"] = None
        state["iteration"] = 1

        logged_calls = []

        def capture_attribution(**kwargs):
            logged_calls.append(kwargs)

        with patch.object(track, "attribution", side_effect=capture_attribution):
            _record_action_success(agent, state)

        assert len(logged_calls) == 1
        assert logged_calls[0]["source"] == "skipped"
        assert logged_calls[0]["reward_type"] == "skipped"


# ---------------------------------------------------------------------------
# (c) Reward propagation uses previous_action_signature
# ---------------------------------------------------------------------------


class TestRewardPropagationUsesPreviousAction:
    """(c) _propagate_reward records and propagates using previous_action_signature."""

    def test_reward_recorded_with_previous_signature(self):
        """record_action is called with (previous_hash, previous_action_signature)."""
        prev_sig = ((100, 200), "click")
        agent = MagicMock()
        mock_propagator = MagicMock()
        agent.strategy.reward_propagator = mock_propagator
        agent.strategy.graph = MagicMock()
        agent.strategy._get_visited_activities = MagicMock(return_value=set())

        state = _base_state()
        state["previous_action_signature"] = prev_sig
        state["previous_screen_hash"] = "hash_A"
        state["current_screen_hash"] = "hash_B"

        _propagate_reward(agent, state)

        mock_propagator.record_action.assert_called_once_with("hash_A", prev_sig)

    def test_reward_not_recorded_with_current_action(self):
        """The current_action coordinates are NOT passed to record_action."""
        prev_sig = ((100, 200), "click")
        agent = MagicMock()
        mock_propagator = MagicMock()
        agent.strategy.reward_propagator = mock_propagator
        agent.strategy.graph = MagicMock()
        agent.strategy._get_visited_activities = MagicMock(return_value=set())

        state = _base_state()
        state["previous_action_signature"] = prev_sig
        state["current_action"] = {"action_type": "CLICK", "x": 555, "y": 666}
        state["previous_screen_hash"] = "hash_A"
        state["current_screen_hash"] = "hash_B"

        _propagate_reward(agent, state)

        call_args = mock_propagator.record_action.call_args[0]
        # Second argument must be the previous signature, not derived from current_action
        assert call_args[1] == prev_sig
        assert call_args[1] != ((555, 666), "click")

    def test_reward_type_new_state_when_hash_changes(self):
        """When hashes differ and activity was already visited, reward_type='new_state'."""
        prev_sig = ((100, 200), "click")
        agent = MagicMock()
        mock_propagator = MagicMock()
        agent.strategy.reward_propagator = mock_propagator
        agent.strategy.graph = MagicMock()
        # Activity already in visited set
        agent.strategy._get_visited_activities = MagicMock(return_value={"ActivityB"})

        state = _base_state()
        state["previous_action_signature"] = prev_sig
        state["previous_screen_hash"] = "hash_A"
        state["current_screen_hash"] = "hash_B"
        state["current_activity"] = "ActivityB"
        state["current_item_action"] = None

        _propagate_reward(agent, state)

        mock_propagator.propagate.assert_called_once()
        call_kwargs = mock_propagator.propagate.call_args
        assert call_kwargs[0][0] == "new_state"

    def test_reward_type_same_state_when_hash_unchanged(self):
        """When hashes are equal and action is not SET_TEXT, reward_type='same_state'."""
        prev_sig = ((100, 200), "click")
        agent = MagicMock()
        mock_propagator = MagicMock()
        agent.strategy.reward_propagator = mock_propagator
        agent.strategy.graph = MagicMock()
        agent.strategy._get_visited_activities = MagicMock(return_value=set())

        state = _base_state()
        state["previous_action_signature"] = prev_sig
        state["previous_screen_hash"] = "hash_A"
        state["current_screen_hash"] = "hash_A"  # No change
        state["current_action"] = {"action_type": "CLICK", "x": 100, "y": 200}
        state["current_item_action"] = None

        _propagate_reward(agent, state)

        call_kwargs = mock_propagator.propagate.call_args
        assert call_kwargs[0][0] == "same_state"


# ---------------------------------------------------------------------------
# (d) execute_node transition recording uses previous_action_signature
# ---------------------------------------------------------------------------


class TestExecuteNodeTransitionUsesPreviousSignature:
    """(d) execute_node records transition using state['previous_action_signature']."""

    def _make_execute_agent(self):
        agent = MagicMock()
        agent.tool_executor.execute_action.return_value = {
            "success": True,
            "action_executed": {"action_type": "CLICK", "x": 50, "y": 60},
        }
        agent.dynamic_graph = None
        agent.ui_coverage = None
        return agent

    def test_transition_recorded_with_previous_action_signature(self):
        """record_transition is called with the previous_action_signature tuple."""
        prev_sig = ((50, 60), "click")
        agent = self._make_execute_agent()

        state = {
            "current_action": {
                "action_type": "CLICK",
                "x": 50,
                "y": 60,
                "source": "algorithm",
            },
            "current_screen_hash": "hash_B",
            "previous_screen_hash": "hash_A",
            "previous_action_signature": prev_sig,
            "current_item_action": None,
            "iteration": 3,
        }

        execute_node(agent, state)

        agent.strategy.record_transition.assert_called_once_with(
            "hash_A", "hash_B", prev_sig
        )

    def test_transition_not_recorded_when_no_previous_signature(self):
        """No transition is recorded if previous_action_signature is None."""
        agent = self._make_execute_agent()

        state = {
            "current_action": {
                "action_type": "CLICK",
                "x": 50,
                "y": 60,
                "source": "algorithm",
            },
            "current_screen_hash": "hash_B",
            "previous_screen_hash": "hash_A",
            "previous_action_signature": None,  # First iteration
            "current_item_action": None,
            "iteration": 1,
        }

        execute_node(agent, state)

        agent.strategy.record_transition.assert_not_called()

    def test_self_loop_guard_fires_when_hashes_equal(self):
        """When prev_hash == current_hash, record_transition is skipped (self-loop guard)."""
        from rv_agent import tracking as track

        prev_sig = ((50, 60), "click")
        agent = self._make_execute_agent()

        state = {
            "current_action": {
                "action_type": "CLICK",
                "x": 50,
                "y": 60,
                "source": "algorithm",
            },
            "current_screen_hash": "hash_A",  # Same hash
            "previous_screen_hash": "hash_A",  # Same hash
            "previous_action_signature": prev_sig,
            "current_item_action": None,
            "iteration": 4,
        }

        self_loop_calls = []

        def capture_self_loop(**kwargs):
            self_loop_calls.append(kwargs)

        with patch.object(track, "self_loop_guard", side_effect=capture_self_loop):
            execute_node(agent, state)

        agent.strategy.record_transition.assert_not_called()
        assert len(self_loop_calls) == 1

    def test_transition_uses_tuple_not_item_action_object(self):
        """record_transition receives the raw tuple, not an ItemAction object."""
        prev_sig = ((200, 300), "set_text")
        agent = self._make_execute_agent()

        state = {
            "current_action": {
                "action_type": "SET_TEXT",
                "x": 200,
                "y": 300,
                "source": "llm",
            },
            "current_screen_hash": "hash_C",
            "previous_screen_hash": "hash_B",
            "previous_action_signature": prev_sig,
            "current_item_action": MagicMock(),  # Present but should NOT be used
            "iteration": 7,
        }

        execute_node(agent, state)

        call_args = agent.strategy.record_transition.call_args[0]
        # Third argument must be the tuple, not the ItemAction mock
        assert call_args[2] == prev_sig
        assert isinstance(call_args[2], tuple)


# ---------------------------------------------------------------------------
# (e) RVTRACK:ATTRIBUTION is emitted with source="previous"
# ---------------------------------------------------------------------------


class TestAttributionTrackingEmittedWithSourcePrevious:
    """(e) RVTRACK:ATTRIBUTION log is emitted with source='previous' for normal iterations."""

    def test_record_action_success_emits_attribution_with_source_previous(self):
        """_record_action_success emits RVTRACK:ATTRIBUTION with source='previous'."""
        from rv_agent import tracking as track

        prev_sig = ((100, 200), "click")
        agent, _ = _make_agent_with_graph("hash_A")

        state = _base_state()
        state["previous_action_signature"] = prev_sig
        state["previous_screen_hash"] = "hash_A"
        state["current_screen_hash"] = "hash_B"
        state["iteration"] = 5

        logged_calls = []

        def capture_attribution(**kwargs):
            logged_calls.append(kwargs)

        with patch.object(track, "attribution", side_effect=capture_attribution):
            _record_action_success(agent, state)

        assert len(logged_calls) == 1
        assert logged_calls[0]["source"] == "previous"

    def test_propagate_reward_emits_attribution_with_source_previous(self):
        """_propagate_reward also emits RVTRACK:ATTRIBUTION with source='previous'."""
        from rv_agent import tracking as track

        prev_sig = ((100, 200), "click")
        agent = MagicMock()
        mock_propagator = MagicMock()
        agent.strategy.reward_propagator = mock_propagator
        agent.strategy.graph = MagicMock()
        agent.strategy._get_visited_activities = MagicMock(return_value=set())

        state = _base_state()
        state["previous_action_signature"] = prev_sig
        state["previous_screen_hash"] = "hash_A"
        state["current_screen_hash"] = "hash_B"
        state["iteration"] = 5
        state["current_item_action"] = None

        logged_calls = []

        def capture_attribution(**kwargs):
            logged_calls.append(kwargs)

        with patch.object(track, "attribution", side_effect=capture_attribution):
            _propagate_reward(agent, state)

        assert len(logged_calls) == 1
        assert logged_calls[0]["source"] == "previous"

    def test_attribution_log_contains_action_sig_string(self):
        """RVTRACK:ATTRIBUTION includes the action signature as a string."""
        from rv_agent import tracking as track

        prev_sig = ((123, 456), "click")
        agent, _ = _make_agent_with_graph("hash_A")

        state = _base_state()
        state["previous_action_signature"] = prev_sig
        state["previous_screen_hash"] = "hash_A"
        state["current_screen_hash"] = "hash_B"

        logged_calls = []

        def capture_attribution(**kwargs):
            logged_calls.append(kwargs)

        with patch.object(track, "attribution", side_effect=capture_attribution):
            _record_action_success(agent, state)

        assert str(prev_sig) in logged_calls[0]["action_sig"]

    def test_attribution_log_reflects_actual_success_value(self):
        """RVTRACK:ATTRIBUTION success field matches whether hash changed."""
        from rv_agent import tracking as track

        prev_sig = ((100, 200), "click")
        agent, _ = _make_agent_with_graph("hash_A")

        # Scenario 1: Hash changed -> success=True
        state = _base_state()
        state["previous_action_signature"] = prev_sig
        state["previous_screen_hash"] = "hash_A"
        state["current_screen_hash"] = "hash_B"

        calls_changed = []
        with patch.object(
            track, "attribution", side_effect=lambda **kw: calls_changed.append(kw)
        ):
            _record_action_success(agent, state)
        assert calls_changed[0]["success"] is True

        # Scenario 2: Hash unchanged -> success=False
        agent2, _ = _make_agent_with_graph("hash_A")
        state2 = _base_state()
        state2["previous_action_signature"] = prev_sig
        state2["previous_screen_hash"] = "hash_A"
        state2["current_screen_hash"] = "hash_A"

        calls_same = []
        with patch.object(
            track, "attribution", side_effect=lambda **kw: calls_same.append(kw)
        ):
            _record_action_success(agent2, state2)
        assert calls_same[0]["success"] is False

    def test_attribution_counter_increments(self):
        """Each attribution call increments the aggregate attribution_count counter."""
        from rv_agent import tracking as track

        track.reset_counters()
        initial_count = track.get_aggregate_counters()["attribution_count"]

        prev_sig = ((100, 200), "click")
        agent, _ = _make_agent_with_graph("hash_A")

        state = _base_state()
        state["previous_action_signature"] = prev_sig
        state["previous_screen_hash"] = "hash_A"
        state["current_screen_hash"] = "hash_B"

        _record_action_success(agent, state)

        final_count = track.get_aggregate_counters()["attribution_count"]
        assert final_count == initial_count + 1
