"""
Unit tests for force_fill_input error recovery block in algorithm_node.

Tests the integration of spatial association and sequential fallback
within the algorithm_node function. When force_fill_input=True, the node
should find the nearest input field to the error indicator and generate
an appropriate action (SET_TEXT for EditText, CLICK for Spinner).
"""

from unittest.mock import MagicMock

from rv_agent.agent.nodes.algorithm_node import algorithm_node


def _make_item_action(
    bounds=None,
    view_class="android.widget.EditText",
    action_type="set_text",
    action_id=1,
    text_input=None,
    widget_id="input_field_1",
    reaches_mop=False,
):
    """Create a mock ItemAction with specified properties."""
    action = MagicMock()
    action.target_view = {
        "bounds": bounds or [[100, 490], [300, 540]],
        "class": view_class,
        "resource_id": widget_id,
    }
    action.action_type = action_type
    action.id = action_id
    action.text = "Enter text"
    action.text_input = text_input
    action.widget_id = widget_id
    action.reaches_mop = reaches_mop
    action.directly_reaches_mop = False
    action.event = MagicMock()
    action.coordinates = None

    if bounds:
        center_x = (bounds[0][0] + bounds[1][0]) // 2
        center_y = (bounds[0][1] + bounds[1][1]) // 2
        action.get_execution_coordinates.return_value = (center_x, center_y)
    else:
        action.get_execution_coordinates.return_value = (200, 515)

    # model_copy support for text_input enrichment
    def mock_model_copy(update=None):
        copy = MagicMock()
        copy.target_view = action.target_view
        copy.action_type = action.action_type
        copy.id = action.id
        copy.text = action.text
        copy.text_input = update.get("text_input") if update else action.text_input
        copy.widget_id = action.widget_id
        copy.reaches_mop = action.reaches_mop
        copy.directly_reaches_mop = action.directly_reaches_mop
        copy.event = action.event
        copy.coordinates = action.coordinates
        copy.get_execution_coordinates.return_value = (
            action.get_execution_coordinates.return_value
        )
        return copy

    action.model_copy = mock_model_copy
    return action


def _make_screen_item(actions):
    """Create a mock ScreenItem with given actions."""
    item = MagicMock()
    item.actions = actions
    return item


def _make_screen_description(items):
    """Create a mock ScreenDescription with given items."""
    desc = MagicMock()
    desc.items = items
    return desc


def _make_agent():
    """Create a mock agent with config and strategy for error recovery tests."""
    agent = MagicMock()
    agent.config.spatial_edittext_boost = 1.2
    agent.config.spatial_spinner_boost = 1.1
    agent.config.spatial_min_match_threshold = 0.1
    agent.config.package_name = "com.example.app"
    agent.consecutive_no_action = 0
    agent.NO_ACTION_THRESHOLD = 5

    # Value generator for SET_TEXT actions
    agent.strategy.value_generator.get_next_value.return_value = "test_value_123"

    return agent


def _make_error_indicator(x=100, y=500, width=30, height=30):
    """Create a mock ErrorIndicator with bbox property."""
    from rv_screen_parser.screenshot.models import (
        DetectionMethod,
        ErrorIndicator,
        ErrorType,
    )

    return ErrorIndicator(
        x=x,
        y=y,
        width=width,
        height=height,
        detection_method=DetectionMethod.COLOR,
        confidence=0.9,
        error_type=ErrorType.VALIDATION_ERROR,
    )


class TestAlgorithmNodeErrorRecovery:
    """Tests for force_fill_input block in algorithm_node."""

    def test_flag_set_edittext_available_set_text(self):
        """force_fill_input=True, EditText with set_text action -> returns SET_TEXT action."""
        indicator = _make_error_indicator(x=100, y=500, width=30, height=30)

        action = _make_item_action(
            bounds=[[90, 490], [200, 540]],
            view_class="android.widget.EditText",
            action_type="set_text",
        )
        item = _make_screen_item([action])
        screen_desc = _make_screen_description([item])

        agent = _make_agent()

        state = {
            "force_fill_input": True,
            "error_indicators": [indicator],
            "screen_description": screen_desc,
            "current_screen_hash": "hash_abc",
        }

        result = algorithm_node(agent, state)

        assert result["decision_maker"] == "error_recovery"
        assert result["force_fill_input"] is False
        assert result["error_indicators"] is None
        assert result["current_action"] is not None
        assert result["current_action"]["action_type"] == "SET_TEXT"
        assert result["current_action"]["source"] == "algorithm"
        assert result["current_action"]["reason"] == "error_recovery"

    def test_flag_set_spinner_match_click(self):
        """force_fill_input=True, Spinner near error indicator -> returns CLICK action."""
        indicator = _make_error_indicator(x=100, y=500, width=30, height=30)

        action = _make_item_action(
            bounds=[[90, 490], [200, 540]],
            view_class="android.widget.Spinner",
            action_type="click",
        )
        item = _make_screen_item([action])
        screen_desc = _make_screen_description([item])

        agent = _make_agent()

        state = {
            "force_fill_input": True,
            "error_indicators": [indicator],
            "screen_description": screen_desc,
            "current_screen_hash": "hash_abc",
        }

        result = algorithm_node(agent, state)

        assert result["decision_maker"] == "error_recovery"
        assert result["current_action"]["action_type"] == "CLICK"
        assert result["force_fill_input"] is False
        assert result["error_indicators"] is None

    def test_flag_set_no_inputs_clears_flags(self):
        """force_fill_input=True but no inputs -> flags cleared, falls through to normal flow."""
        indicator = _make_error_indicator(x=100, y=500, width=30, height=30)

        # Only a BACK action available (no inputs, no spatial match)
        action = _make_item_action(
            bounds=[[800, 1800], [900, 1850]],
            view_class="android.widget.Button",
            action_type="click",
        )
        item = _make_screen_item([action])
        screen_desc = _make_screen_description([item])

        agent = _make_agent()

        # Set up normal strategy return for the fallthrough path
        mock_strategy_action = MagicMock()
        mock_strategy_action.action_type.upper.return_value = "CLICK"
        mock_strategy_action.text = "Click button"
        mock_strategy_action.text_input = None
        mock_strategy_action.id = 99
        mock_strategy_action.get_execution_coordinates.return_value = (850, 1825)
        mock_strategy_action.target_view = {}
        agent.strategy.select_next_action.return_value = mock_strategy_action

        state = {
            "force_fill_input": True,
            "error_indicators": [indicator],
            "screen_description": screen_desc,
            "current_screen_hash": "hash_abc",
        }

        result = algorithm_node(agent, state)

        # Flags should be cleared in the result
        assert result.get("force_fill_input") is False
        assert result.get("error_indicators") is None
        # The normal algorithm flow should have been executed (strategy.select_next_action called)
        agent.strategy.select_next_action.assert_called_once()

    def test_flag_not_set_unchanged(self):
        """force_fill_input=False -> normal behavior, spatial association NOT called."""
        agent = _make_agent()

        # Set up normal strategy return
        mock_item_action = MagicMock()
        mock_item_action.action_type.upper.return_value = "CLICK"
        mock_item_action.text = "Click button"
        mock_item_action.id = 5
        mock_item_action.get_execution_coordinates.return_value = (200, 400)
        mock_item_action.target_view = {}
        agent.strategy.select_next_action.return_value = mock_item_action

        state = {
            "force_fill_input": False,
            "error_indicators": None,
            "screen_description": MagicMock(),
            "current_screen_hash": "hash_abc",
        }

        result = algorithm_node(agent, state)

        # Normal flow: strategy was called
        agent.strategy.select_next_action.assert_called_once()
        assert result["decision_maker"] == "algorithm"

    def test_set_text_action_uses_value_generator(self):
        """SET_TEXT action should use the value generator for text input."""
        indicator = _make_error_indicator(x=100, y=500, width=30, height=30)

        action = _make_item_action(
            bounds=[[90, 490], [200, 540]],
            view_class="android.widget.EditText",
            action_type="set_text",
        )
        item = _make_screen_item([action])
        screen_desc = _make_screen_description([item])

        agent = _make_agent()
        agent.strategy.value_generator.get_next_value.return_value = "my_test_input"

        state = {
            "force_fill_input": True,
            "error_indicators": [indicator],
            "screen_description": screen_desc,
            "current_screen_hash": "hash_abc",
        }

        result = algorithm_node(agent, state)

        assert result["current_action"]["text"] == "my_test_input"
        agent.strategy.value_generator.get_next_value.assert_called_once()

    def test_sequential_fallback_when_no_spatial_match(self):
        """When spatial association finds no match, falls back to sequential search."""
        # Indicator far from EditText (no spatial match)
        indicator = _make_error_indicator(x=800, y=100, width=20, height=20)

        # EditText far from indicator (no overlap, no below-field)
        action = _make_item_action(
            bounds=[[100, 1700], [300, 1750]],
            view_class="android.widget.EditText",
            action_type="set_text",
        )
        item = _make_screen_item([action])
        screen_desc = _make_screen_description([item])

        agent = _make_agent()

        state = {
            "force_fill_input": True,
            "error_indicators": [indicator],
            "screen_description": screen_desc,
            "current_screen_hash": "hash_abc",
        }

        result = algorithm_node(agent, state)

        # Should still find the EditText via sequential fallback
        assert result["decision_maker"] == "error_recovery"
        assert result["current_action"]["action_type"] == "SET_TEXT"
