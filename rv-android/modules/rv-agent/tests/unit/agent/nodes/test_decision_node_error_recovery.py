"""
Unit tests for force_fill_input routing in decision_node.

When force_fill_input=True, the decision router should bypass normal
routing and send directly to algorithm_node for error recovery.
"""

import pytest
from unittest.mock import MagicMock, patch

from rv_agent.agent.nodes.decision_node import decision_router_node


def _make_agent():
    """Create a mock agent with routing_manager."""
    agent = MagicMock()
    agent.routing_manager.mode = "multimode"
    agent.routing_manager.forced_back_count = 0
    agent.routing_manager.route_decision.return_value = "llm"
    return agent


class TestDecisionNodeErrorRecovery:
    """Tests for force_fill_input routing in decision_router_node."""

    @patch("rv_agent.agent.nodes.decision_node.track")
    def test_force_fill_input_routes_to_algorithm(self, mock_track):
        """force_fill_input=True -> routes to algorithm for error recovery."""
        agent = _make_agent()
        state = {
            "force_fill_input": True,
            "iteration": 5,
        }

        result = decision_router_node(agent, state)

        assert result["decision_path"] == "algorithm"
        assert result["decision_maker"] == "error_recovery"
        # Normal routing should NOT have been called
        agent.routing_manager.route_decision.assert_not_called()

    @patch("rv_agent.agent.nodes.decision_node.track")
    def test_force_fill_input_false_normal_routing(self, mock_track):
        """force_fill_input=False -> normal routing via routing_manager."""
        agent = _make_agent()
        agent.routing_manager.route_decision.return_value = "llm"

        state = {
            "force_fill_input": False,
            "iteration": 5,
        }

        result = decision_router_node(agent, state)

        # Normal routing was used
        agent.routing_manager.route_decision.assert_called_once()
        assert result["decision_path"] == "llm"

    @patch("rv_agent.agent.nodes.decision_node.track")
    def test_force_fill_input_bypasses_llm_only_mode(self, mock_track):
        """Even in llm_only mode, force_fill_input routes to algorithm."""
        agent = _make_agent()
        agent.routing_manager.mode = "llm_only"

        state = {
            "force_fill_input": True,
            "iteration": 3,
        }

        result = decision_router_node(agent, state)

        assert result["decision_path"] == "algorithm"
        assert result["decision_maker"] == "error_recovery"

    @patch("rv_agent.agent.nodes.decision_node.track")
    def test_force_back_has_priority_over_force_fill(self, mock_track):
        """force_back_action=True takes priority over force_fill_input=True."""
        agent = _make_agent()

        state = {
            "force_back_action": True,
            "force_fill_input": True,
            "force_restart_app": False,
            "iteration": 5,
        }

        result = decision_router_node(agent, state)

        # force_back_action is checked before force_fill_input
        assert result["decision_maker"] == "stuck_recovery"

    @patch("rv_agent.agent.nodes.decision_node.track")
    def test_force_restart_has_priority_over_force_fill(self, mock_track):
        """force_restart_app=True takes priority over force_fill_input=True."""
        agent = _make_agent()

        state = {
            "force_restart_app": True,
            "force_fill_input": True,
            "iteration": 5,
        }

        result = decision_router_node(agent, state)

        # force_restart_app is checked before force_fill_input
        assert result["decision_maker"] == "stuck_recovery"

    @patch("rv_agent.agent.nodes.decision_node.track")
    def test_track_route_called_with_error_recovery(self, mock_track):
        """track.route is called with error_recovery path."""
        agent = _make_agent()
        state = {
            "force_fill_input": True,
            "iteration": 7,
        }

        result = decision_router_node(agent, state)

        mock_track.route.assert_called_once_with(
            iter=7, mode="multimode", path="algorithm(error_recovery)"
        )
