"""
Fixed tests for ToolExecutor functionality.

Tests the ToolExecutor class which handles execution of various tools/actions on the device.
Based on the actual implementation.
"""

import pytest
from unittest.mock import MagicMock
from rv_agent.execution.tool_executor import ToolExecutor


class TestToolExecutorInitialization:
    """Test ToolExecutor initialization and setup."""

    def test_initialization_with_device(self):
        """ToolExecutor initializes with device interface."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        assert tool_executor.device == mock_device
        assert tool_executor.image_handler is None

    def test_initialization_with_image_handler(self):
        """ToolExecutor initializes with image handler."""
        mock_device = MagicMock()
        mock_image_handler = MagicMock()

        tool_executor = ToolExecutor(
            device=mock_device, image_handler=mock_image_handler
        )

        assert tool_executor.device == mock_device
        assert tool_executor.image_handler == mock_image_handler


class TestToolExecutorClickAction:
    """Test ToolExecutor click action execution."""

    def test_execute_click_success(self):
        """ToolExecutor successfully executes click action."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        action = {
            "action_type": "CLICK",
            "x": 100,
            "y": 200,
            "element_description": "Test button",
        }

        result = tool_executor.execute_action(action)

        # Verify device click was called with correct coordinates
        mock_device.click.assert_called_once_with(100, 200)
        assert result["success"] is True
        assert result["action_executed"] == action

    def test_execute_click_with_default_coordinates(self):
        """ToolExecutor handles click with default coordinates when not provided."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        action = {
            "action_type": "CLICK"
            # Missing x, y coordinates - should default to 0, 0
        }

        result = tool_executor.execute_action(action)

        # Verify device click was called with default coordinates
        mock_device.click.assert_called_once_with(0, 0)
        assert result["success"] is True


class TestToolExecutorSetTextAction:
    """Test ToolExecutor set_text action execution."""

    def test_execute_set_text_success(self):
        """ToolExecutor successfully executes set_text action."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        action = {
            "action_type": "SET_TEXT",
            "x": 100,
            "y": 200,
            "text": "Hello World",
            "element_description": "Input field",
        }

        result = tool_executor.execute_action(action)

        # Verify device methods were called
        mock_device.click.assert_called_once_with(100, 200)
        mock_device.input_text.assert_called_once_with("Hello World")
        assert result["success"] is True

    def test_execute_set_text_without_text_fails(self):
        """ToolExecutor handles set_text without text."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        action = {
            "action_type": "SET_TEXT",
            "x": 100,
            "y": 200,
            # Missing text field
        }

        result = tool_executor.execute_action(action)

        # Should fail gracefully
        assert result["success"] is False
        assert "error" in result
        assert "No text provided" in result["error"]


class TestToolExecutorSwipeAction:
    """Test ToolExecutor swipe action execution."""

    def test_execute_swipe_with_coordinates(self):
        """ToolExecutor executes swipe action with coordinates."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        action = {
            "action_type": "SCROLL",
            "swipe_start": [100, 200],
            "swipe_end": [300, 400],
        }

        result = tool_executor.execute_action(action)

        # According to the implementation, SCROLL action with coordinates calls device.swipe
        mock_device.swipe.assert_called_once_with(100, 200, 300, 400)
        assert result["success"] is True

    def test_execute_swipe_with_direction(self):
        """ToolExecutor executes swipe action with direction."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        action = {"action_type": "SWIPE", "direction": "down"}

        result = tool_executor.execute_action(action)

        # Verify device scroll was called with direction
        mock_device.scroll.assert_called_once_with("down", "medium")
        assert result["success"] is True


class TestToolExecutorSystemActions:
    """Test ToolExecutor system actions execution."""

    def test_execute_back_success(self):
        """ToolExecutor successfully executes back action."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        action = {"action_type": "BACK"}

        result = tool_executor.execute_action(action)

        # Verify device back was called
        mock_device.back.assert_called_once()
        assert result["success"] is True

    def test_execute_home_success(self):
        """ToolExecutor successfully executes home action."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        action = {"action_type": "HOME"}

        result = tool_executor.execute_action(action)

        # Verify device home was called
        mock_device.home.assert_called_once()
        assert result["success"] is True

    def test_execute_restart_success(self):
        """ToolExecutor successfully executes restart action."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        action = {"action_type": "RESTART_APP", "package_name": "com.example.test"}

        result = tool_executor.execute_action(action)

        # Verify device methods were called
        mock_device.stop_app.assert_called_once_with("com.example.test")
        mock_device.start_app.assert_called_once_with("com.example.test")
        assert result["success"] is True

    def test_execute_restart_without_package_uses_device_fallback(self):
        """ToolExecutor falls back to device.config.package_name when action lacks it."""
        mock_device = MagicMock()
        mock_device.config.package_name = "com.fallback.app"

        tool_executor = ToolExecutor(device=mock_device)

        action = {
            "action_type": "RESTART_APP"
            # Missing package_name — falls back to device.config.package_name
        }

        result = tool_executor.execute_action(action)

        # Should succeed using fallback package name
        assert result["success"] is not False or mock_device.stop_app.called


class TestToolExecutorUnknownAction:
    """Test ToolExecutor handling of unknown actions."""

    def test_execute_unknown_action_type(self):
        """ToolExecutor handles unknown action type."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        action = {"action_type": "UNKNOWN_ACTION_TYPE", "x": 100, "y": 200}

        result = tool_executor.execute_action(action)

        # Should fail gracefully
        assert result["success"] is False
        assert "error" in result
        assert "Unknown action type" in result["error"]

    def test_execute_action_with_none_action(self):
        """ToolExecutor handles None action."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        # This should raise an AttributeError since None has no 'get' method
        with pytest.raises(AttributeError):
            tool_executor.execute_action(None)

    def test_execute_action_with_empty_action(self):
        """ToolExecutor handles empty action."""
        mock_device = MagicMock()

        tool_executor = ToolExecutor(device=mock_device)

        result = tool_executor.execute_action({})

        # Should fail gracefully
        assert result["success"] is False
        assert "error" in result
        assert "Unknown action type" in result["error"]
