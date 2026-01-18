"""
Unit tests for DeviceInterface.

Tests the DeviceInterface class which handles all device interactions.
"""

import pytest
from unittest.mock import MagicMock, patch
from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.constants import RVAgentConstants


class TestDeviceInterfaceInitialization:
    """Test DeviceInterface initialization and setup."""

    def test_initialization_with_default_device_id(self):
        """DeviceInterface initializes with default device ID."""
        device_interface = DeviceInterface()
        
        assert device_interface.device_id == RVAgentConstants.DEFAULT_DEVICE_ID

    @patch('rv_agent.agent.device_interface.DeviceInterface._is_emulator_device')
    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_initialization_with_custom_device_id(self, mock_ui_adapter_class, mock_is_emulator_device):
        """DeviceInterface initializes with custom device ID."""
        mock_is_emulator_device.return_value = True
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5556")

        assert device_interface.device_id == "emulator-5556"

    def test_initialization_with_invalid_device_id_raises_error(self):
        """DeviceInterface raises error with invalid device ID."""
        with pytest.raises(ValueError, match="Only emulator devices supported"):
            DeviceInterface(device_id="invalid-device-id")


class TestDeviceInterfaceMethods:
    """Test DeviceInterface core methods."""

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    @patch('rv_agent.agent.device_interface.DeviceInterface._is_emulator_device')
    def test_initialization_creates_ui_adapter(self, mock_is_emulator_device, mock_ui_adapter_class):
        """DeviceInterface creates UIAutomator2Adapter during initialization."""
        mock_is_emulator_device.return_value = True
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        # Verify UIAutomator2Adapter was created with correct device ID
        mock_ui_adapter_class.assert_called_once_with(device_id="emulator-5554")
        # Verify connect was called
        mock_adapter_instance.connect.assert_called_once_with("emulator-5554")
        # Verify the adapter instance is stored
        assert device_interface.ui_adapter == mock_adapter_instance

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    @patch('rv_agent.agent.device_interface.DeviceInterface._is_emulator_device')
    def test_click_method_calls_ui_adapter(self, mock_is_emulator_device, mock_ui_adapter_class):
        """DeviceInterface click method calls UI adapter."""
        mock_is_emulator_device.return_value = True
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.click.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.click(100, 200)

        # Verify UI adapter click was called with correct coordinates
        mock_adapter_instance.click.assert_called_once_with(100, 200)
        assert result is True

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    @patch('rv_agent.agent.device_interface.DeviceInterface._is_emulator_device')
    def test_input_text_method_calls_ui_adapter(self, mock_is_emulator_device, mock_ui_adapter_class):
        """DeviceInterface input_text method calls UI adapter."""
        mock_is_emulator_device.return_value = True
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.input_text.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.input_text("Hello World")

        # Verify UI adapter input_text was called with correct text
        mock_adapter_instance.input_text.assert_called_once_with("Hello World")
        assert result is True

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    @patch('rv_agent.agent.device_interface.DeviceInterface._is_emulator_device')
    def test_swipe_method_calls_ui_adapter(self, mock_is_emulator_device, mock_ui_adapter_class):
        """DeviceInterface swipe method calls UI adapter."""
        mock_is_emulator_device.return_value = True
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.swipe.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.swipe(100, 200, 300, 400)

        # Verify UI adapter swipe was called with correct coordinates
        # Note: swipe method has a default duration parameter
        mock_adapter_instance.swipe.assert_called_once_with(100, 200, 300, 400, duration=0.5)
        assert result is True

    @patch('rv_agent.agent.device_interface.DeviceInterface._is_emulator_device')
    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_back_method_calls_ui_adapter(self, mock_ui_adapter_class, mock_is_emulator_device):
        """DeviceInterface back method calls UI adapter."""
        mock_is_emulator_device.return_value = True
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.press_back.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.back()

        # Verify UI adapter press_back was called
        mock_adapter_instance.press_back.assert_called_once()
        assert result is True

    @patch('rv_agent.agent.device_interface.DeviceInterface._is_emulator_device')
    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_home_method_calls_ui_adapter(self, mock_ui_adapter_class, mock_is_emulator_device):
        """DeviceInterface home method calls UI adapter."""
        mock_is_emulator_device.return_value = True
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.press_home.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.home()

        # Verify UI adapter press_home was called
        mock_adapter_instance.press_home.assert_called_once()
        assert result is True

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    @patch('rv_agent.agent.device_interface.DeviceInterface._is_emulator_device')
    def test_take_screenshot_method_calls_ui_adapter(self, mock_is_emulator_device, mock_ui_adapter_class):
        """DeviceInterface take_screenshot method calls UI adapter."""
        mock_is_emulator_device.return_value = True
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.take_screenshot.return_value = "/tmp/test.png"

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.take_screenshot("/tmp")

        # Verify UI adapter take_screenshot was called
        # Note: take_screenshot method doesn't take parameters, it generates its own filename
        mock_adapter_instance.take_screenshot.assert_called_once()
        assert result == "/tmp/test.png"

    @patch('rv_agent.agent.device_interface.DeviceInterface._is_emulator_device')
    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_get_current_ui_state_method_calls_ui_adapter(self, mock_ui_adapter_class, mock_is_emulator_device):
        """DeviceInterface get_current_ui_state method calls UI adapter."""
        mock_is_emulator_device.return_value = True
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        expected_state = {"activity": "MainActivity", "elements": []}
        mock_adapter_instance.get_ui_state.return_value = expected_state

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.get_current_ui_state()

        # Verify UI adapter get_ui_state was called
        mock_adapter_instance.get_ui_state.assert_called_once()
        assert result == expected_state

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_launch_app_method_calls_ui_adapter(self, mock_ui_adapter_class):
        """DeviceInterface launch_app method calls UI adapter."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.launch_app.return_value = True
        
        device_interface = DeviceInterface(device_id="emulator-5554")
        
        result = device_interface.launch_app("com.example.app")
        
        # Verify UI adapter launch_app was called with correct package name
        mock_adapter_instance.launch_app.assert_called_once_with("com.example.app")
        assert result is True

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_stop_app_method_calls_ui_adapter(self, mock_ui_adapter_class):
        """DeviceInterface stop_app method calls UI adapter."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.stop_app.return_value = True
        
        device_interface = DeviceInterface(device_id="emulator-5554")
        
        result = device_interface.stop_app("com.example.app")
        
        # Verify UI adapter stop_app was called with correct package name
        mock_adapter_instance.stop_app.assert_called_once_with("com.example.app")
        assert result is True

    @patch('rv_agent.agent.device_interface.DeviceInterface._is_emulator_device')
    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_scroll_method_calls_ui_adapter(self, mock_ui_adapter_class, mock_is_emulator_device):
        """DeviceInterface scroll method calls UI adapter."""
        mock_is_emulator_device.return_value = True
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.swipe.return_value = True

        device_interface = DeviceInterface(device_id="emulator-5554")

        result = device_interface.scroll("down", "medium")

        # Verify UI adapter swipe was called with calculated coordinates and duration
        # Note: scroll internally calls swipe with calculated coordinates
        mock_adapter_instance.swipe.assert_called_once()
        assert result is True