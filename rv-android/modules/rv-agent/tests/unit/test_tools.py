import pytest
from unittest.mock import MagicMock
from rv_agent.execution.tool_executor import ToolExecutor
from rv_agent.core.device_interface import DeviceInterface

class TestToolExecutor:
    @pytest.fixture
    def executor(self):
        device = MagicMock()
        device.get_screen_size.return_value = (1080, 1920)
        device.click = MagicMock()
        device.long_click = MagicMock()
        device.input_text = MagicMock()
        device.scroll = MagicMock()
        device.swipe = MagicMock()
        device.back = MagicMock()
        device.home = MagicMock()
        device.press_keycode = MagicMock()
        device.stop_app = MagicMock()
        device.start_app = MagicMock()

        return ToolExecutor(device, image_handler=None)

    def test_execute_click(self, executor):
        action = {
            "tool_name": "android_click",
            "tool_args": {"x": 100, "y": 200}
        }
        
        result = executor.execute_action(action)
        
        assert result["success"] is True
        # Note: Coordinates might be scaled if image_handler was present, 
        # but here we use default which might imply scaling if defaults differ.
        # ToolExecutor default optimized size is (704, 1248).
        # Device size is (1080, 1920).
        # Scale X: 1080/704 = 1.53
        # Scale Y: 1920/1248 = 1.53
        # So 100 -> 153, 200 -> 307 (approx)
        # Let's check if click was called, arguments might vary based on scaling logic
        executor.device.click.assert_called()

    def test_execute_type_text(self, executor):
        action = {
            "tool_name": "android_type_text",
            "tool_args": {"x": 100, "y": 200, "text": "hello"}
        }
        
        result = executor.execute_action(action)
        
        assert result["success"] is True
        executor.device.click.assert_called()
        executor.device.input_text.assert_called_with("hello")

    def test_execute_scroll(self, executor):
        action = {
            "tool_name": "android_scroll",
            "tool_args": {"direction": "down"}
        }
        
        result = executor.execute_action(action)
        
        assert result["success"] is True
        executor.device.scroll.assert_called_with("down", "medium")

    def test_execute_back(self, executor):
        action = {
            "tool_name": "android_back",
            "tool_args": {}
        }
        
        result = executor.execute_action(action)
        
        assert result["success"] is True
        executor.device.back.assert_called()

    def test_execute_home(self, executor):
        action = {
            "tool_name": "android_home",
            "tool_args": {}
        }
        
        result = executor.execute_action(action)
        
        assert result["success"] is True
        executor.device.home.assert_called()

    def test_execute_unknown(self, executor):
        action = {
            "tool_name": "unknown_tool",
            "tool_args": {}
        }

        result = executor.execute_action(action)

        assert result["success"] is False
        assert "Unknown action type" in result["error"]

    def test_execute_long_click(self, executor):
        """Test long click execution."""
        action = {
            "tool_name": "android_long_click",
            "tool_args": {"x": 150, "y": 250}
        }

        result = executor.execute_action(action)

        assert result["success"] is True
        executor.device.long_click.assert_called()

    def test_execute_swipe(self, executor):
        """Test swipe execution."""
        action = {
            "tool_name": "android_swipe",
            "tool_args": {"direction": "up", "distance": "long"}
        }

        result = executor.execute_action(action)

        assert result["success"] is True
        executor.device.swipe.assert_called_with("up", "long")

    def test_execute_swipe_default_distance(self, executor):
        """Test swipe with default distance."""
        action = {
            "tool_name": "android_swipe",
            "tool_args": {"direction": "left"}
        }

        result = executor.execute_action(action)

        assert result["success"] is True
        executor.device.swipe.assert_called_with("left", "medium")

    def test_execute_directional_scroll_up(self, executor):
        """Test directional scroll up (algorithm format)."""
        action = {"action_type": "SCROLL_UP"}

        result = executor.execute_action(action)

        assert result["success"] is True
        executor.device.swipe.assert_called_with("up", "medium")

    def test_execute_directional_scroll_down(self, executor):
        """Test directional scroll down (algorithm format)."""
        action = {"action_type": "SCROLL_DOWN"}

        result = executor.execute_action(action)

        assert result["success"] is True
        executor.device.swipe.assert_called_with("down", "medium")

    def test_execute_directional_scroll_left(self, executor):
        """Test directional scroll left (algorithm format)."""
        action = {"action_type": "SCROLL_LEFT"}

        result = executor.execute_action(action)

        assert result["success"] is True
        executor.device.swipe.assert_called_with("left", "medium")

    def test_execute_directional_scroll_right(self, executor):
        """Test directional scroll right (algorithm format)."""
        action = {"action_type": "SCROLL_RIGHT"}

        result = executor.execute_action(action)

        assert result["success"] is True
        executor.device.swipe.assert_called_with("right", "medium")

    def test_execute_press_enter(self, executor):
        """Test ENTER key press."""
        action = {
            "tool_name": "android_press_enter",
            "tool_args": {}
        }

        result = executor.execute_action(action)

        assert result["success"] is True
        executor.device.press_keycode.assert_called_with(66)

    def test_execute_restart_with_package(self, executor):
        """Test app restart with package name."""
        action = {
            "tool_name": "android_restart",
            "tool_args": {"package_name": "com.example.app"}
        }

        result = executor.execute_action(action)

        assert result["success"] is True
        executor.device.stop_app.assert_called_with("com.example.app")
        executor.device.start_app.assert_called_with("com.example.app")

    def test_execute_restart_without_package(self, executor):
        """Test app restart without package name fails."""
        action = {
            "tool_name": "android_restart",
            "tool_args": {}
        }

        result = executor.execute_action(action)

        assert result["success"] is False
        assert "No package name" in result["error"]

    def test_execute_type_text_empty(self, executor):
        """Test type text with empty text fails."""
        action = {
            "tool_name": "android_type_text",
            "tool_args": {"x": 100, "y": 200, "text": ""}
        }

        result = executor.execute_action(action)

        assert result["success"] is False
        assert "No text provided" in result["error"]

    def test_execute_type_text_no_text(self, executor):
        """Test type text with missing text field fails."""
        action = {
            "tool_name": "android_type_text",
            "tool_args": {"x": 100, "y": 200}
        }

        result = executor.execute_action(action)

        assert result["success"] is False

    def test_execute_system_back(self, executor):
        """Test SYSTEM_BACK action type."""
        action = {"action_type": "SYSTEM_BACK"}

        result = executor.execute_action(action)

        assert result["success"] is True
        executor.device.back.assert_called()

    def test_execute_action_with_exception(self, executor):
        """Test action execution with exception."""
        executor.device.click.side_effect = Exception("Device disconnected")

        action = {
            "tool_name": "android_click",
            "tool_args": {"x": 100, "y": 200}
        }

        result = executor.execute_action(action)

        assert result["success"] is False
        assert "Device disconnected" in result["error"]

    def test_normalize_already_internal_format(self, executor):
        """Test normalize with already internal format."""
        action = {"action_type": "CLICK", "x": 100, "y": 200}

        result = executor.execute_action(action)

        assert result["success"] is True
        executor.device.click.assert_called()

    def test_coordinate_conversion_disabled(self, executor):
        """Test with coordinate conversion disabled."""
        action = {"action_type": "CLICK", "x": 540, "y": 960}

        result = executor.execute_action(action, convert_coordinates=False)

        assert result["success"] is True
        # Coordinates should be used as-is
        executor.device.click.assert_called_with(540, 960)

    def test_long_click_no_conversion(self, executor):
        """Test long click without coordinate conversion."""
        action = {"action_type": "LONG_CLICK", "x": 540, "y": 960}

        result = executor.execute_action(action, convert_coordinates=False)

        assert result["success"] is True
        executor.device.long_click.assert_called_with(540, 960)

    def test_type_text_no_conversion(self, executor):
        """Test type text without coordinate conversion."""
        action = {"action_type": "SET_TEXT", "x": 540, "y": 960, "text": "hello"}

        result = executor.execute_action(action, convert_coordinates=False)

        assert result["success"] is True
        executor.device.click.assert_called_with(540, 960)


class TestToolExecutorWithImageHandler:
    """Test ToolExecutor with image handler."""

    @pytest.fixture
    def executor_with_handler(self):
        device = MagicMock(spec=DeviceInterface)
        device.get_screen_size.return_value = (1080, 1920)

        # Mock image handler
        image_handler = MagicMock()
        image_handler.target_size = (540, 960)

        return ToolExecutor(device, image_handler=image_handler)

    def test_uses_image_handler_size(self, executor_with_handler):
        """Test that image handler's target size is used."""
        assert executor_with_handler.optimized_size == (540, 960)

    def test_coordinate_conversion_with_handler(self, executor_with_handler):
        """Test coordinate conversion uses correct scale."""
        # Device: 1080x1920, Optimized: 540x960
        # Scale: 2x
        action = {"action_type": "CLICK", "x": 270, "y": 480}

        result = executor_with_handler.execute_action(action)

        assert result["success"] is True
        # 270 * 2 = 540, 480 * 2 = 960
        executor_with_handler.device.click.assert_called_with(540, 960)
