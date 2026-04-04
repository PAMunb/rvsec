"""
Comprehensive tests for DeviceInterface functionality.

Tests the DeviceInterface class which handles all device interactions.
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_agent.agent.device_interface import DeviceInterface


class TestDeviceInterfaceInitialization:
    """Test DeviceInterface initialization and setup."""

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_initialization_with_valid_emulator_device(self, mock_ui_adapter_class):
        """DeviceInterface initializes with valid emulator device ID."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        # Verify initialization
        assert device_interface.device_id == "emulator-5554"
        mock_ui_adapter_class.assert_called_once_with(device_id="emulator-5554")
        mock_adapter_instance.connect.assert_called_once_with("emulator-5554")

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_initialization_with_localhost_device(self, mock_ui_adapter_class):
        """DeviceInterface initializes with localhost device ID."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True

        device_interface = DeviceInterface(device_id="localhost:5554")

        # Verify initialization
        assert device_interface.device_id == "localhost:5554"
        mock_ui_adapter_class.assert_called_once_with(device_id="localhost:5554")
        mock_adapter_instance.connect.assert_called_once_with("localhost:5554")

    def test_initialization_with_invalid_device_id_raises_error(self):
        """DeviceInterface raises error with invalid device ID."""
        with pytest.raises(ValueError, match="Only emulator devices supported"):
            DeviceInterface(device_id="invalid-device-id")

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_initialization_connection_failure_raises_error(
        self, mock_ui_adapter_class
    ):
        """DeviceInterface raises error when connection fails."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = False

        with pytest.raises(Exception, match="Failed to connect to device"):
            DeviceInterface(device_id="emulator-5554")


class TestDeviceInterfaceClickMethod:
    """Test DeviceInterface click method."""

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_click_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully performs click."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.click.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.click(100, 200)

        # Verify device click was called with correct coordinates
        mock_adapter_instance.click.assert_called_once_with(100, 200)
        assert result is True

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_click_failure(self, mock_ui_adapter_class):
        """DeviceInterface handles click failure."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.click.return_value = False

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.click(100, 200)

        # Verify device click was called
        mock_adapter_instance.click.assert_called_once_with(100, 200)
        assert result is False


class TestDeviceInterfaceInputTextMethod:
    """Test DeviceInterface input_text method."""

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_input_text_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully inputs text."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.input_text.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.input_text("Hello World")

        # Verify device input_text was called with correct text
        mock_adapter_instance.input_text.assert_called_once_with("Hello World")
        assert result is True

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_input_text_failure(self, mock_ui_adapter_class):
        """DeviceInterface handles input_text failure."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.input_text.return_value = False

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.input_text("Hello World")

        # Verify device input_text was called
        mock_adapter_instance.input_text.assert_called_once_with("Hello World")
        assert result is False


class TestDeviceInterfaceSwipeMethod:
    """Test DeviceInterface swipe method."""

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_swipe_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully performs swipe."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.swipe.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.swipe(100, 200, 300, 400)

        # Verify device swipe was called with correct coordinates
        mock_adapter_instance.swipe.assert_called_once_with(
            100, 200, 300, 400, duration=0.5
        )
        assert result is True

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_swipe_failure(self, mock_ui_adapter_class):
        """DeviceInterface handles swipe failure."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.swipe.return_value = False

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.swipe(100, 200, 300, 400)

        # Verify device swipe was called
        mock_adapter_instance.swipe.assert_called_once_with(
            100, 200, 300, 400, duration=0.5
        )
        assert result is False


class TestDeviceInterfaceSystemActions:
    """Test DeviceInterface system action methods."""

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_back_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully performs back action."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.press_back.return_value = True  # Correct method name

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.back()

        # Verify device press_back was called
        mock_adapter_instance.press_back.assert_called_once()
        assert result is True

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_back_failure(self, mock_ui_adapter_class):
        """DeviceInterface handles back action failure."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.press_back.return_value = False  # Correct method name

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.back()

        # Verify device press_back was called
        mock_adapter_instance.press_back.assert_called_once()
        assert result is False

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_home_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully performs home action."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.press_home.return_value = True  # Correct method name

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.home()

        # Verify device press_home was called
        mock_adapter_instance.press_home.assert_called_once()
        assert result is True

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_home_failure(self, mock_ui_adapter_class):
        """DeviceInterface handles home action failure."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.press_home.return_value = False  # Correct method name

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.home()

        # Verify device press_home was called
        mock_adapter_instance.press_home.assert_called_once()
        assert result is False


class TestDeviceInterfaceScrollMethod:
    """Test DeviceInterface scroll method."""

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_scroll_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully performs scroll."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.swipe.return_value = True  # scroll calls swipe internally

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.scroll("down", "medium")

        # Verify device swipe was called with calculated coordinates for scroll
        mock_adapter_instance.swipe.assert_called_once()
        assert result is True

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_scroll_failure(self, mock_ui_adapter_class):
        """DeviceInterface handles scroll failure."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.swipe.return_value = (
            False  # scroll calls swipe internally
        )

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.scroll("up", "short")

        # Verify device swipe was called for scroll
        mock_adapter_instance.swipe.assert_called_once()
        assert result is False


class TestDeviceInterfaceScreenshotMethod:
    """Test DeviceInterface screenshot method."""

    def test_take_screenshot_success(self):
        """DeviceInterface successfully takes screenshot."""
        with patch(
            "rv_agent.agent.device_interface.UIAutomator2Adapter"
        ) as mock_ui_adapter_class:
            mock_adapter_instance = MagicMock()
            mock_ui_adapter_class.return_value = mock_adapter_instance
            mock_adapter_instance.connect.return_value = True

            device_interface = DeviceInterface(device_id="emulator-5554")

            # Mock take_screenshot to return a temp file path
            mock_adapter_instance.take_screenshot.return_value = (
                "/tmp/test_screenshot.png"
            )

            with patch("rv_agent.agent.device_interface.Path") as mock_path_cls, patch(
                "shutil.move"
            ):
                # Path(screenshot_path) for .exists() check
                mock_src_path = MagicMock()
                mock_src_path.exists.return_value = True
                mock_src_path.name = "test_screenshot.png"

                # Path(output_dir) for / operator and .mkdir()
                mock_out_path = MagicMock()
                mock_target = MagicMock()
                mock_target.__str__ = lambda self: "/output/test_screenshot.png"
                mock_out_path.__truediv__ = lambda self, other: mock_target

                # Path() calls: Path(screenshot_path).exists(), Path(output_dir) / Path(screenshot_path).name, Path(output_dir).mkdir()
                mock_path_cls.side_effect = [
                    mock_src_path,
                    mock_out_path,
                    mock_src_path,
                    mock_out_path,
                ]

                result = device_interface.take_screenshot("/output")

            # Verify device take_screenshot was called
            mock_adapter_instance.take_screenshot.assert_called_once()
            assert result is not None

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_take_screenshot_failure(self, mock_ui_adapter_class):
        """DeviceInterface handles screenshot failure."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.take_screenshot.return_value = None

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.take_screenshot("/tmp")

        # Verify device take_screenshot was called (without parameters, it saves to current dir then moves)
        mock_adapter_instance.take_screenshot.assert_called_once()
        assert result is None


class TestDeviceInterfaceAppStateMethods:
    """Test DeviceInterface app state methods."""

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_get_current_ui_state_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully gets current UI state."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        expected_state = {"activity": "MainActivity", "elements": []}
        mock_adapter_instance.get_ui_state.return_value = (
            expected_state  # Correct method name
        )

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.get_current_ui_state()

        # Verify device get_ui_state was called
        mock_adapter_instance.get_ui_state.assert_called_once()
        assert result == expected_state

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_launch_app_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully launches app."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.launch_app.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.launch_app("com.example.app")

        # Verify device launch_app was called with correct package
        mock_adapter_instance.launch_app.assert_called_once_with("com.example.app")
        assert result is True

    @patch("rv_agent.agent.device_interface.UIAutomator2Adapter")
    def test_stop_app_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully stops app."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.stop_app.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.stop_app("com.example.app")

        # Verify device stop_app was called with correct package
        mock_adapter_instance.stop_app.assert_called_once_with("com.example.app")
        assert result is True


class TestDeviceInterfaceKeyboardHandling:
    """Test DeviceInterface keyboard handling methods."""

    def test_disable_soft_keyboard_success(self):
        """DeviceInterface successfully disables soft keyboard via ADB."""
        with patch(
            "rv_agent.agent.device_interface.UIAutomator2Adapter"
        ) as mock_ui_adapter_class, patch("subprocess.run") as mock_subprocess_run:
            mock_adapter_instance = MagicMock()
            mock_ui_adapter_class.return_value = mock_adapter_instance
            mock_adapter_instance.connect.return_value = True

            # Mock subprocess.run for the ADB command used by disable_soft_keyboard
            mock_subprocess_run.return_value = MagicMock(returncode=0, stderr="")

            device_interface = DeviceInterface(device_id="emulator-5554")

            result = device_interface.disable_soft_keyboard()

            # disable_soft_keyboard uses subprocess.run with ADB commands
            # Called once during __init__ and once explicitly here
            assert mock_subprocess_run.call_count == 2
            assert result is True
