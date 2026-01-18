"""
Comprehensive tests for ToolExecutor functionality.

Tests the ToolExecutor class which handles execution of various tools/actions on the device.
"""

import pytest
from unittest.mock import MagicMock
from rv_agent.execution.tool_executor import ToolExecutor


class TestToolExecutorInitialization:
    """Test ToolExecutor initialization and setup."""

    def test_initialization_with_device(self):
        """ToolExecutor initializes with device interface."""
        mock_device = MagicMock()
        mock_image_handler = MagicMock()
        
        tool_executor = ToolExecutor(device=mock_device, image_handler=mock_image_handler)
        
        assert tool_executor.device == mock_device
        assert tool_executor.image_handler == mock_image_handler

    def test_initialization_without_image_handler(self):
        """ToolExecutor initializes without image handler (optional)."""
        mock_device = MagicMock()
        
        tool_executor = ToolExecutor(device=mock_device)
        
        assert tool_executor.device == mock_device
        assert tool_executor.image_handler is None

    def test_initialization_with_none_device_raises_error(self):
        """ToolExecutor raises error when initialized with None device."""
        with pytest.raises(AttributeError):  # Will fail when trying to access device methods
            executor = ToolExecutor(device=None)
            # Try to use the executor to trigger the error
            executor.execute_action({"action_type": "CLICK", "x": 100, "y": 100})


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
            "element_description": "Test button"
        }

        result = tool_executor.execute_action(action)

        # Verify device click was called with correct coordinates
        mock_device.click.assert_called_once_with(100, 200)
        assert result["success"] is True
        assert result["action_executed"] == action

    def test_execute_click_failure(self):
        """ToolExecutor handles click failure."""
        mock_device = MagicMock()
        # Make the click method raise an exception to simulate failure
        mock_device.click.side_effect = Exception("Click failed")

        tool_executor = ToolExecutor(device=mock_device)

        action = {
            "action_type": "CLICK",
            "x": 100,
            "y": 200,
            "element_description": "Test button"
        }

        # Should raise DeviceError due to the exception
        with pytest.raises(Exception):
            tool_executor.execute_action(action)

    def test_execute_click_without_coordinates_fails(self):
        """ToolExecutor handles click without coordinates."""
        mock_device = MagicMock()
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "CLICK",
            # Missing x, y coordinates
        }
        
        result = tool_executor.execute_action(action)
        
        # Should fail gracefully without calling device
        mock_device.click.assert_not_called()
        assert result["success"] is False
        assert "missing coordinates" in result["message"]


class TestToolExecutorSetTextAction:
    """Test ToolExecutor set_text action execution."""

    def test_execute_set_text_success(self):
        """ToolExecutor successfully executes set_text action."""
        mock_device = MagicMock()
        mock_device.type_text.return_value = True
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "SET_TEXT",
            "text": "Hello World",
            "element_description": "Input field"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device type_text was called with correct text
        mock_device.type_text.assert_called_once_with("Hello World")
        assert result["success"] is True
        assert "message" in result

    def test_execute_set_text_failure(self):
        """ToolExecutor handles set_text failure."""
        mock_device = MagicMock()
        mock_device.type_text.return_value = False
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "SET_TEXT",
            "text": "Hello World",
            "element_description": "Input field"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device type_text was called
        mock_device.type_text.assert_called_once_with("Hello World")
        assert result["success"] is False
        assert "message" in result

    def test_execute_set_text_without_text_fails(self):
        """ToolExecutor handles set_text without text."""
        mock_device = MagicMock()
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "SET_TEXT",
            # Missing text field
        }
        
        result = tool_executor.execute_action(action)
        
        # Should fail gracefully without calling device
        mock_device.type_text.assert_not_called()
        assert result["success"] is False
        assert "missing text" in result["message"]


class TestToolExecutorSwipeAction:
    """Test ToolExecutor swipe action execution."""

    def test_execute_swipe_success(self):
        """ToolExecutor successfully executes swipe action."""
        mock_device = MagicMock()
        mock_device.swipe.return_value = True
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "SWIPE",
            "start_x": 100,
            "start_y": 200,
            "end_x": 300,
            "end_y": 400,
            "element_description": "Scrollable area"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device swipe was called with correct coordinates
        mock_device.swipe.assert_called_once_with(100, 200, 300, 400, duration=0.5)
        assert result["success"] is True
        assert "message" in result

    def test_execute_swipe_failure(self):
        """ToolExecutor handles swipe failure."""
        mock_device = MagicMock()
        mock_device.swipe.return_value = False
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "SWIPE",
            "start_x": 100,
            "start_y": 200,
            "end_x": 300,
            "end_y": 400,
            "element_description": "Scrollable area"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device swipe was called
        mock_device.swipe.assert_called_once_with(100, 200, 300, 400, duration=0.5)
        assert result["success"] is False
        assert "message" in result

    def test_execute_swipe_without_coordinates_fails(self):
        """ToolExecutor handles swipe without coordinates."""
        mock_device = MagicMock()
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "SWIPE",
            # Missing start_x, start_y, end_x, end_y coordinates
        }
        
        result = tool_executor.execute_action(action)
        
        # Should fail gracefully without calling device
        mock_device.swipe.assert_not_called()
        assert result["success"] is False
        assert "missing coordinates" in result["message"]


class TestToolExecutorSystemActions:
    """Test ToolExecutor system actions execution."""

    def test_execute_back_success(self):
        """ToolExecutor successfully executes back action."""
        mock_device = MagicMock()
        mock_device.back.return_value = True
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "BACK"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device back was called
        mock_device.back.assert_called_once()
        assert result["success"] is True
        assert "message" in result

    def test_execute_back_failure(self):
        """ToolExecutor handles back action failure."""
        mock_device = MagicMock()
        mock_device.back.return_value = False
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "BACK"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device back was called
        mock_device.back.assert_called_once()
        assert result["success"] is False
        assert "message" in result

    def test_execute_home_success(self):
        """ToolExecutor successfully executes home action."""
        mock_device = MagicMock()
        mock_device.home.return_value = True
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "HOME"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device home was called
        mock_device.home.assert_called_once()
        assert result["success"] is True
        assert "message" in result

    def test_execute_home_failure(self):
        """ToolExecutor handles home action failure."""
        mock_device = MagicMock()
        mock_device.home.return_value = False
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "HOME"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device home was called
        mock_device.home.assert_called_once()
        assert result["success"] is False
        assert "message" in result

    def test_execute_restart_success(self):
        """ToolExecutor successfully executes restart action."""
        mock_device = MagicMock()
        mock_device.force_stop.return_value = True
        mock_device.launch_app.return_value = True
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "RESTART_APP",
            "package_name": "com.example.test"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device force_stop and launch_app were called
        mock_device.force_stop.assert_called_once()
        mock_device.launch_app.assert_called_once_with("com.example.test")
        assert result["success"] is True
        assert "message" in result

    def test_execute_restart_failure(self):
        """ToolExecutor handles restart action failure."""
        mock_device = MagicMock()
        mock_device.force_stop.return_value = False  # Force stop fails
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "RESTART_APP",
            "package_name": "com.example.test"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device force_stop was called but launch_app was not
        mock_device.force_stop.assert_called_once()
        mock_device.launch_app.assert_not_called()
        assert result["success"] is False
        assert "message" in result


class TestToolExecutorScrollAction:
    """Test ToolExecutor scroll action execution."""

    def test_execute_scroll_success(self):
        """ToolExecutor successfully executes scroll action."""
        mock_device = MagicMock()
        mock_device.scroll.return_value = True
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "SCROLL",
            "direction": "down",
            "distance": "medium"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device scroll was called with correct parameters
        mock_device.scroll.assert_called_once_with("down", "medium")
        assert result["success"] is True
        assert "message" in result

    def test_execute_scroll_failure(self):
        """ToolExecutor handles scroll failure."""
        mock_device = MagicMock()
        mock_device.scroll.return_value = False
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "SCROLL",
            "direction": "up",
            "distance": "short"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device scroll was called
        mock_device.scroll.assert_called_once_with("up", "short")
        assert result["success"] is False
        assert "message" in result

    def test_execute_scroll_without_direction_fails(self):
        """ToolExecutor handles scroll without direction."""
        mock_device = MagicMock()
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "SCROLL",
            # Missing direction
        }
        
        result = tool_executor.execute_action(action)
        
        # Should fail gracefully without calling device
        mock_device.scroll.assert_not_called()
        assert result["success"] is False
        assert "missing direction" in result["message"]


class TestToolExecutorLongClickAction:
    """Test ToolExecutor long click action execution."""

    def test_execute_long_click_success(self):
        """ToolExecutor successfully executes long click action."""
        mock_device = MagicMock()
        mock_device.long_click.return_value = True
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "LONG_CLICK",
            "x": 150,
            "y": 250,
            "duration": 1.5,
            "element_description": "Menu item"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device long_click was called with correct parameters
        mock_device.long_click.assert_called_once_with(150, 250, duration=1.5)
        assert result["success"] is True
        assert "message" in result

    def test_execute_long_click_failure(self):
        """ToolExecutor handles long click failure."""
        mock_device = MagicMock()
        mock_device.long_click.return_value = False
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "LONG_CLICK",
            "x": 150,
            "y": 250,
            "duration": 1.0,
            "element_description": "Menu item"
        }
        
        result = tool_executor.execute_action(action)
        
        # Verify device long_click was called
        mock_device.long_click.assert_called_once_with(150, 250, duration=1.0)
        assert result["success"] is False
        assert "message" in result


class TestToolExecutorUnknownAction:
    """Test ToolExecutor handling of unknown actions."""

    def test_execute_unknown_action_type(self):
        """ToolExecutor handles unknown action type."""
        mock_device = MagicMock()
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": "UNKNOWN_ACTION_TYPE",
            "x": 100,
            "y": 200
        }
        
        result = tool_executor.execute_action(action)
        
        # Should fail gracefully without calling device
        assert result["success"] is False
        assert "Unknown action type" in result["message"]
        assert result["message"] == "Unknown action type: UNKNOWN_ACTION_TYPE"


class TestToolExecutorActionValidation:
    """Test ToolExecutor action validation."""

    def test_execute_action_with_none_action(self):
        """ToolExecutor handles None action."""
        mock_device = MagicMock()
        
        tool_executor = ToolExecutor(device=mock_device)
        
        result = tool_executor.execute_action(None)
        
        # Should fail gracefully
        assert result["success"] is False
        assert "Action cannot be None" in result["message"]

    def test_execute_action_with_empty_action(self):
        """ToolExecutor handles empty action."""
        mock_device = MagicMock()
        
        tool_executor = ToolExecutor(device=mock_device)
        
        result = tool_executor.execute_action({})
        
        # Should fail gracefully
        assert result["success"] is False
        assert "missing action_type" in result["message"]

    def test_execute_action_with_invalid_action_type(self):
        """ToolExecutor handles invalid action type."""
        mock_device = MagicMock()
        
        tool_executor = ToolExecutor(device=mock_device)
        
        action = {
            "action_type": 123  # Invalid type
        }
        
        result = tool_executor.execute_action(action)
        
        # Should fail gracefully
        assert result["success"] is False
        assert "Unknown action type" in result["message"]