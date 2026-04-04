"""
Integration tests for text input improvements (gh26 Group 9, task 9.2).

Verifies clear-before-type in ToolExecutor and LLM text tracking
in InputValueGenerator via learn_node.
"""

from unittest.mock import MagicMock

from rv_agent.strategies.rvagent_strategy.input_value_generator import (
    InputValueGenerator,
)
from rv_agent.agent.nodes.learn_node import _track_llm_text_value


class TestClearBeforeType:
    """Verify ToolExecutor calls clear_text() before input_text() for SET_TEXT."""

    def test_clear_text_called_before_input(self):
        """click -> clear_text -> input_text sequence in _execute_type_text."""
        from rv_agent.execution.tool_executor import ToolExecutor

        mock_device = MagicMock()
        call_order = []
        mock_device.click.side_effect = lambda *a: call_order.append("click")
        mock_device.clear_text.side_effect = lambda: call_order.append("clear")
        mock_device.input_text.side_effect = lambda *a: call_order.append("input")

        executor = ToolExecutor(device=mock_device)

        result = executor._execute_type_text(
            {"x": 200, "y": 400, "text": "test@email.com"}
        )

        assert result["success"] is True
        assert call_order == ["click", "clear", "input"]
        mock_device.clear_text.assert_called_once()


class TestLlmTextTracking:
    """Verify LLM-generated text values are tracked in InputValueGenerator."""

    def test_llm_text_tracked_prevents_algorithm_repetition(self):
        """LLM SET_TEXT text is recorded in tested_values for the element."""
        vg = InputValueGenerator(max_variations=5)

        # Simulate LLM tracking via _track_llm_text_value
        mock_agent = MagicMock()
        mock_agent.strategy.value_generator = vg

        state = {
            "decision_maker": "llm",
            "current_action": {
                "action_type": "SET_TEXT",
                "text": "llm_generated_password",
                "x": 200,
                "y": 400,
            },
            "current_item_action": MagicMock(widget_id="input_password"),
        }

        _track_llm_text_value(mock_agent, state)

        # Verify the LLM text is now in tested_values
        assert "llm_generated_password" in vg.tested_values["input_password"]

    def test_non_llm_decision_not_tracked(self):
        """Algorithm-generated text should NOT be tracked via _track_llm_text_value."""
        vg = InputValueGenerator(max_variations=5)

        mock_agent = MagicMock()
        mock_agent.strategy.value_generator = vg

        state = {
            "decision_maker": "algorithm",
            "current_action": {
                "action_type": "SET_TEXT",
                "text": "algo_text",
                "x": 200,
                "y": 400,
            },
            "current_item_action": MagicMock(widget_id="input_field"),
        }

        _track_llm_text_value(mock_agent, state)

        # Algorithm decisions are NOT tracked via this function
        assert "input_field" not in vg.tested_values
