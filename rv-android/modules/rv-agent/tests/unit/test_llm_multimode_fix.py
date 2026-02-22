"""
Unit tests for Group 35: LLM multimode fixes.

Tests:
(a) execute_node LLM pre-marking uses lowercase action_type in signature
(b) llm_node return dict includes current_item_action=None
(c) RVTRACK:EXEC log shows the action_type as received (uppercase from state)
"""

import logging
import pytest
from unittest.mock import MagicMock

from rv_agent.agent.nodes.execute_node import execute_node
from rv_agent.agent.nodes.llm_node import llm_generate_node
from rv_agent.domain.state import AgentState


class TestExecuteNodeLLMPreMarkingLowercase:
    """(a) execute_node pre-marking uses lowercase action_type in the action signature."""

    def _make_agent(self, record_action_calls):
        """Build a minimal mock agent that captures record_action calls."""
        agent = MagicMock()
        agent.tool_executor.execute_action.return_value = {
            "success": True,
            "action_executed": {"action_type": "CLICK", "x": 540, "y": 960, "source": "llm"},
        }
        agent.dynamic_graph.record_action.side_effect = (
            lambda screen_hash, sig, widget_class="": record_action_calls.append(sig)
        )
        agent.ui_coverage = None  # disable coverage branch
        return agent

    def test_llm_action_signature_uses_lowercase_action_type(self):
        """Pre-mark signature for LLM CLICK action must use 'click', not 'CLICK'."""
        calls = []
        agent = self._make_agent(calls)

        state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="abc123",
            visited_states=[],
            state_transitions=[],
            recent_action_window=[],
            current_action={
                "action_type": "CLICK",
                "x": 540,
                "y": 960,
                "source": "llm",
            },
            decision_maker="llm",
        )

        execute_node(agent, state)

        assert len(calls) == 1, "record_action should be called exactly once"
        sig = calls[0]
        # sig is ((x, y), action_type_str)
        coords, action_type_str = sig
        assert action_type_str == "click", (
            f"Pre-mark signature must use lowercase action_type; got '{action_type_str}'"
        )
        assert coords == (540, 960)

    def test_llm_action_set_text_signature_uses_lowercase(self):
        """Pre-mark signature for LLM SET_TEXT action must use 'set_text'."""
        calls = []
        agent = self._make_agent(calls)
        agent.tool_executor.execute_action.return_value = {
            "success": True,
            "action_executed": {"action_type": "SET_TEXT", "x": 200, "y": 400, "source": "llm"},
        }

        state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="def456",
            visited_states=[],
            state_transitions=[],
            recent_action_window=[],
            current_action={
                "action_type": "SET_TEXT",
                "x": 200,
                "y": 400,
                "source": "llm",
            },
            decision_maker="llm",
        )

        execute_node(agent, state)

        assert len(calls) == 1
        _, action_type_str = calls[0]
        assert action_type_str == "set_text", (
            f"Pre-mark must lowercase SET_TEXT; got '{action_type_str}'"
        )

    def test_algorithm_action_does_not_call_record_action(self):
        """Algorithm actions must NOT trigger LLM pre-marking (record_action)."""
        calls = []
        agent = self._make_agent(calls)
        agent.tool_executor.execute_action.return_value = {
            "success": True,
            "action_executed": {"action_type": "CLICK", "x": 100, "y": 200, "source": "algorithm"},
        }

        state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="ghi789",
            visited_states=[],
            state_transitions=[],
            recent_action_window=[],
            current_action={
                "action_type": "CLICK",
                "x": 100,
                "y": 200,
                "source": "algorithm",
            },
            decision_maker="algorithm",
        )

        execute_node(agent, state)

        assert len(calls) == 0, (
            "record_action must not be called for algorithm actions"
        )

    def test_llm_action_without_screen_hash_skips_premark(self):
        """LLM pre-marking must be skipped when screen_hash is empty."""
        calls = []
        agent = self._make_agent(calls)

        state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="",  # empty hash
            visited_states=[],
            state_transitions=[],
            recent_action_window=[],
            current_action={
                "action_type": "CLICK",
                "x": 540,
                "y": 960,
                "source": "llm",
            },
            decision_maker="llm",
        )

        execute_node(agent, state)

        assert len(calls) == 0, (
            "Pre-marking must be skipped when screen_hash is empty"
        )


class TestRvtrackExecLog:
    """(c) RVTRACK:EXEC log is emitted for LLM actions."""

    def test_exec_log_emitted_for_llm_action(self, caplog):
        """execute_node emits [RVTRACK:EXEC] log line when executing an LLM action."""
        agent = MagicMock()
        agent.tool_executor.execute_action.return_value = {
            "success": True,
            "action_executed": {"action_type": "CLICK", "x": 540, "y": 960, "source": "llm"},
        }
        agent.dynamic_graph = MagicMock()
        agent.ui_coverage = None

        state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="abc123",
            visited_states=[],
            state_transitions=[],
            recent_action_window=[],
            current_action={
                "action_type": "CLICK",
                "x": 540,
                "y": 960,
                "source": "llm",
            },
            iteration=5,
            decision_maker="llm",
        )

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            execute_node(agent, state)

        exec_logs = [r for r in caplog.records if "[RVTRACK:EXEC]" in r.message]
        assert len(exec_logs) == 1, (
            f"Expected exactly one RVTRACK:EXEC log; got {len(exec_logs)}"
        )
        msg = exec_logs[0].message
        # action_type as stored in the action dict (uppercase) is what tracking logs
        assert "CLICK" in msg
        assert "source=llm" in msg


class TestLlmNodeCurrentItemActionCleared:
    """(b) llm_node return dict includes current_item_action=None."""

    def _make_agent_with_llm(self, llm_response):
        """Build a minimal mock agent with a functioning llm_client."""
        agent = MagicMock()
        agent.llm_client.generate_action.return_value = llm_response
        agent.navigation_guidance.is_enabled = False
        agent.dynamic_graph = None
        agent.action_normalizer = None
        return agent

    def _minimal_state(self, current_item_action=None):
        """Return a minimal AgentState for llm_generate_node invocation."""
        return AgentState(
            current_activity="MainActivity",
            current_screen_hash="abc123",
            visited_states=[],
            state_transitions=[],
            recent_action_window=[],
            iteration=1,
            screen_description=None,
            ui_elements_text="",
            screenshot_b64="",
            action_history_summary="",
            llm_tokens_input=0,
            llm_tokens_output=0,
            llm_time_ms=0,
            current_item_action=current_item_action,
        )

    def test_return_dict_contains_current_item_action_none(self):
        """llm_node always returns current_item_action=None to clear stale values."""
        llm_response = {
            "success": False,
            "response": None,
            "tokens_input": 0,
            "tokens_output": 0,
            "time_ms": 0,
        }
        agent = self._make_agent_with_llm(llm_response)
        state = self._minimal_state(current_item_action=None)

        result = llm_generate_node(agent, state)

        assert "current_item_action" in result, (
            "Return dict must contain 'current_item_action' key"
        )
        assert result["current_item_action"] is None

    def test_stale_item_action_is_cleared_in_return(self):
        """llm_node clears a non-None current_item_action from a previous algorithm iteration."""
        llm_response = {
            "success": False,
            "response": None,
            "tokens_input": 10,
            "tokens_output": 5,
            "time_ms": 100,
        }
        agent = self._make_agent_with_llm(llm_response)

        stale_item = MagicMock()  # Simulates an ItemAction set by a prior algorithm step
        state = self._minimal_state(current_item_action=stale_item)

        result = llm_generate_node(agent, state)

        assert result["current_item_action"] is None, (
            "Stale current_item_action from algorithm iterations must be cleared to None"
        )

    def test_decision_maker_is_llm_in_return(self):
        """llm_node sets decision_maker='llm' in the return dict."""
        llm_response = {
            "success": False,
            "response": None,
            "tokens_input": 0,
            "tokens_output": 0,
            "time_ms": 0,
        }
        agent = self._make_agent_with_llm(llm_response)
        state = self._minimal_state()

        result = llm_generate_node(agent, state)

        assert result.get("decision_maker") == "llm"

    def test_return_dict_with_successful_llm_response_still_clears_item_action(self):
        """current_item_action=None even when LLM returns a valid action."""
        # Simulate a successful LLM response with a tool call
        mock_response = MagicMock()
        mock_response.tool_calls = [{"name": "click", "args": {"x": 500, "y": 800}}]
        mock_response.content = "Reasoning text"

        llm_response = {
            "success": True,
            "response": mock_response,
            "tokens_input": 120,
            "tokens_output": 30,
            "time_ms": 450,
        }
        agent = self._make_agent_with_llm(llm_response)
        # action_normalizer returns None when None (branch that sets llm_action = raw_action)
        agent.action_normalizer = None

        stale_item = MagicMock()
        state = self._minimal_state(current_item_action=stale_item)

        result = llm_generate_node(agent, state)

        assert result["current_item_action"] is None, (
            "current_item_action must be None even when LLM succeeds"
        )
        # llm_action should be set from the tool call
        assert result.get("llm_action") is not None
