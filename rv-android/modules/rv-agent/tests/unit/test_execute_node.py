"""
Unit tests for execute_node functionality.

Tests the execute_node function which handles action execution on the device.
"""

import pytest
from unittest.mock import MagicMock
from rv_agent.agent.nodes.execute_node import execute_node
from rv_agent.domain.state import AgentState


class TestExecuteNode:
    """Test execute_node function."""

    def test_execute_node_with_valid_action(self):
        """execute_node executes valid action and returns result."""
        # Create mock agent with tool executor
        mock_agent = MagicMock()
        mock_tool_executor = MagicMock()
        mock_agent.tool_executor = mock_tool_executor
        
        # Mock successful execution result
        execution_result = {
            "success": True,
            "action_executed": {"action_type": "CLICK", "x": 100, "y": 200}
        }
        mock_tool_executor.execute_action.return_value = execution_result
        
        # Create state with action
        state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="hash123",
            visited_states=set(),
            state_transitions=[],
            recent_action_window=[],
            current_action={
                "action_type": "CLICK",
                "x": 100,
                "y": 200,
                "source": "llm"
            },
            previous_screen_hash="prev_hash"
        )
        
        result = execute_node(mock_agent, state)
        
        # Verify tool executor was called with the action
        mock_tool_executor.execute_action.assert_called_once_with({
            "action_type": "CLICK",
            "x": 100,
            "y": 200,
            "source": "llm"
        })
        
        # Verify result structure
        assert "action_executed" in result
        assert "action_success" in result
        assert result["action_success"] is True
        assert result["action_executed"] == {"action_type": "CLICK", "x": 100, "y": 200}

    def test_execute_node_with_no_action(self):
        """execute_node handles case when no action is provided."""
        mock_agent = MagicMock()
        mock_tool_executor = MagicMock()
        mock_agent.tool_executor = mock_tool_executor
        
        # Create state without action
        state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="hash123",
            visited_states=set(),
            state_transitions=[],
            recent_action_window=[]
        )
        
        result = execute_node(mock_agent, state)
        
        # Verify tool executor was not called
        mock_tool_executor.execute_action.assert_not_called()
        
        # Verify result indicates no action executed
        assert result["action_executed"] is None

    def test_execute_node_with_failed_action(self):
        """execute_node handles failed action execution."""
        mock_agent = MagicMock()
        mock_tool_executor = MagicMock()
        mock_agent.tool_executor = mock_tool_executor
        
        # Mock failed execution result
        execution_result = {
            "success": False,
            "error": "Click failed",
            "action_executed": {"action_type": "CLICK", "x": 100, "y": 200}
        }
        mock_tool_executor.execute_action.return_value = execution_result
        
        # Create state with action
        state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="hash123",
            visited_states=set(),
            state_transitions=[],
            recent_action_window=[],
            current_action={
                "action_type": "CLICK",
                "x": 100,
                "y": 200,
                "source": "algorithm"
            }
        )
        
        result = execute_node(mock_agent, state)
        
        # Verify tool executor was called
        mock_tool_executor.execute_action.assert_called_once()
        
        # Verify result indicates failure
        assert "action_executed" in result
        assert "action_success" in result
        assert result["action_success"] is False

    def test_execute_node_records_transition_for_successful_action(self):
        """execute_node records transition when action succeeds."""
        mock_agent = MagicMock()
        mock_tool_executor = MagicMock()
        mock_agent.tool_executor = mock_tool_executor
        mock_strategy = MagicMock()
        mock_agent.strategy = mock_strategy
        mock_agent.ui_coverage = MagicMock()
        
        # Mock successful execution result
        execution_result = {
            "success": True,
            "action_executed": {"action_type": "CLICK", "x": 100, "y": 200, "source": "llm"}
        }
        mock_tool_executor.execute_action.return_value = execution_result
        
        # Create state with action and screen hashes
        state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="new_hash",
            visited_states=set(),
            state_transitions=[],
            recent_action_window=[],
            current_action={
                "action_type": "CLICK",
                "x": 100,
                "y": 200,
                "source": "llm"
            },
            current_item_action={
                "action_type": "CLICK",
                "x": 100,
                "y": 200,
                "source": "llm"
            },
            previous_screen_hash="prev_hash"
        )
        
        result = execute_node(mock_agent, state)
        
        # Verify strategy record_transition was called
        mock_agent.strategy.record_transition.assert_called_once_with(
            "prev_hash", "new_hash", {"action_type": "CLICK", "x": 100, "y": 200, "source": "llm"}
        )

    def test_execute_node_records_ui_coverage_for_llm_action(self):
        """execute_node records UI coverage for LLM actions."""
        mock_agent = MagicMock()
        mock_tool_executor = MagicMock()
        mock_agent.tool_executor = mock_tool_executor
        mock_agent.ui_coverage = MagicMock()
        mock_agent.ui_coverage.find_nearest_element.return_value = ("elem_100_200", "Button", 5.0)
        mock_agent.screen_processor = MagicMock()
        mock_agent.screen_processor.device_dimensions = (1080, 1920)
        mock_agent.dynamic_graph = MagicMock()
        mock_agent.strategy = MagicMock()

        # Mock successful execution result
        execution_result = {
            "success": True,
            "action_executed": {"action_type": "CLICK", "x": 100, "y": 200, "source": "llm"}
        }
        mock_tool_executor.execute_action.return_value = execution_result

        # Create state with action
        state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="current_hash",
            visited_states=set(),
            state_transitions=[],
            recent_action_window=[],
            current_action={
                "action_type": "CLICK",
                "x": 100,
                "y": 200,
                "source": "llm"
            },
            previous_screen_hash="prev_hash"
        )

        result = execute_node(mock_agent, state)

        # Verify UI coverage was recorded
        assert mock_agent.ui_coverage.record_interaction.called

    def test_execute_node_records_ui_coverage_for_algorithm_action(self):
        """execute_node records UI coverage for algorithm actions (unified tracking)."""
        mock_agent = MagicMock()
        mock_tool_executor = MagicMock()
        mock_agent.tool_executor = mock_tool_executor
        mock_agent.ui_coverage = MagicMock()
        mock_agent.screen_processor = MagicMock()
        mock_agent.screen_processor.device_dimensions = (1080, 1920)

        # Mock successful execution result
        execution_result = {
            "success": True,
            "action_executed": {"action_type": "CLICK", "x": 100, "y": 200, "source": "algorithm"}
        }
        mock_tool_executor.execute_action.return_value = execution_result

        # Create state with algorithm action
        state = AgentState(
            current_activity="MainActivity",
            current_screen_hash="current_hash",
            visited_states=set(),
            state_transitions=[],
            recent_action_window=[],
            current_action={
                "action_type": "CLICK",
                "x": 100,
                "y": 200,
                "source": "algorithm"
            },
            previous_screen_hash="prev_hash"
        )

        result = execute_node(mock_agent, state)

        # Verify UI coverage WAS recorded for algorithm action
        # execute_node now records for ALL sources (unified tracking point)
        assert mock_agent.ui_coverage.record_interaction.called