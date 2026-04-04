import pytest
from unittest.mock import MagicMock
from rv_agent.execution.tool_executor import ToolExecutor
from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.domain.exceptions import DeviceError
from rv_agent.services.vision_service import ImageHandler


class TestToolExecutor:
    @pytest.fixture
    def mock_device(self):
        """Provides a mocked DeviceInterface."""
        device = MagicMock(spec=DeviceInterface)
        device.get_screen_size.return_value = (1080, 1920)
        return device

    @pytest.fixture
    def executor(self, mock_device):
        """Provides a ToolExecutor instance with a mocked device and no image handler."""
        return ToolExecutor(mock_device, image_handler=None)

    @pytest.fixture
    def executor_with_handler(self, mock_device):
        """Provides a ToolExecutor instance with a mocked device and image handler."""
        image_handler = MagicMock(spec=ImageHandler)
        image_handler.target_size = (540, 960)
        return ToolExecutor(mock_device, image_handler=image_handler)

    def test_execute_click(self, executor):
        action = {"action_type": "CLICK", "x": 100, "y": 200}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.click.assert_called_with(100, 200)

    def test_execute_type_text(self, executor):
        action = {"action_type": "SET_TEXT", "x": 100, "y": 200, "text": "hello"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.click.assert_called_with(100, 200)
        executor.device.clear_text.assert_called_once()
        executor.device.input_text.assert_called_with("hello")

    def test_execute_scroll(self, executor):
        action = {"action_type": "SCROLL", "direction": "down"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.scroll.assert_called_with("down", "medium")

    def test_execute_back(self, executor):
        action = {"action_type": "BACK"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.back.assert_called_once()

    def test_execute_home(self, executor):
        action = {"action_type": "HOME"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.home.assert_called_once()

    def test_execute_unknown(self, executor):
        action = {"action_type": "UNKNOWN_TOOL"}
        result = executor.execute_action(action)
        assert result["success"] is False
        assert "Unknown action type" in result["error"]

    def test_execute_long_click(self, executor):
        action = {"action_type": "LONG_CLICK", "x": 150, "y": 250}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.long_click.assert_called_with(150, 250)

    def test_execute_swipe(self, executor):
        action = {"action_type": "SWIPE", "direction": "up", "distance": "long"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.scroll.assert_called_with("up", "long")

    def test_execute_swipe_default_distance(self, executor):
        action = {"action_type": "SWIPE", "direction": "left"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.scroll.assert_called_with("left", "medium")

    def test_execute_directional_scroll_up(self, executor):
        action = {"action_type": "SCROLL_UP"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.scroll.assert_called_with("up", "medium")

    def test_execute_directional_scroll_down(self, executor):
        action = {"action_type": "SCROLL_DOWN"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.scroll.assert_called_with("down", "medium")

    def test_execute_directional_scroll_left(self, executor):
        action = {"action_type": "SCROLL_LEFT"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.scroll.assert_called_with("left", "medium")

    def test_execute_directional_scroll_right(self, executor):
        action = {"action_type": "SCROLL_RIGHT"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.scroll.assert_called_with("right", "medium")

    def test_execute_press_enter(self, executor):
        action = {"action_type": "PRESS_ENTER"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.press_keycode.assert_called_with(66)

    def test_execute_restart_with_package(self, executor):
        action = {"action_type": "RESTART_APP", "package_name": "com.example.app"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.stop_app.assert_called_with("com.example.app")
        executor.device.start_app.assert_called_with("com.example.app")

    def test_execute_restart_without_package(self, executor):
        action = {"action_type": "RESTART_APP"}
        result = executor.execute_action(action)
        assert result["success"] is False
        assert "No package name" in result["error"]

    def test_execute_type_text_empty(self, executor):
        action = {"action_type": "SET_TEXT", "x": 100, "y": 200, "text": ""}
        result = executor.execute_action(action)
        assert result["success"] is False
        assert "No text provided" in result["error"]

    def test_execute_type_text_no_text(self, executor):
        action = {"action_type": "SET_TEXT", "x": 100, "y": 200}
        result = executor.execute_action(action)
        assert result["success"] is False
        assert "No text provided" in result["error"]

    def test_execute_system_back(self, executor):
        action = {"action_type": "SYSTEM_BACK"}
        result = executor.execute_action(action)
        assert result["success"] is True
        executor.device.back.assert_called_once()

    def test_execute_action_with_exception(self, executor):
        executor.device.click.side_effect = Exception("Device disconnected")
        action = {"action_type": "CLICK", "x": 100, "y": 200}
        with pytest.raises(
            DeviceError, match="Action execution failed: Device disconnected"
        ):
            executor.execute_action(action)

    def test_no_coordinate_conversion_with_handler(self, executor_with_handler):
        # Even with an image handler, the executor should not perform conversion
        action = {"action_type": "CLICK", "x": 270, "y": 480}
        result = executor_with_handler.execute_action(action)
        assert result["success"] is True
        # Assert that coordinates are passed through as-is
        executor_with_handler.device.click.assert_called_with(270, 480)

    def test_coordinate_conversion_no_handler(self, executor):
        """Test coordinate conversion without handler (no scaling)."""
        action = {"action_type": "CLICK", "x": 500, "y": 1000}
        result = executor.execute_action(action)
        assert result["success"] is True
        # No scaling should occur
        executor.device.click.assert_called_with(500, 1000)
