"""
Fixed tests for DeviceInterface functionality.

Tests the DeviceInterface class which handles all device interactions.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from rv_agent.agent.device_interface import DeviceInterface


class TestDeviceInterfaceInitialization:
    """Test DeviceInterface initialization and setup."""

    def test_initialization_with_valid_emulator_device(self):
        """DeviceInterface initializes with valid emulator device ID."""
        with patch('rv_agent.agent.device_interface.UIAutomator2Adapter') as mock_ui_adapter_class:
            mock_adapter_instance = MagicMock()
            mock_ui_adapter_class.return_value = mock_adapter_instance
            mock_adapter_instance.connect.return_value = True
            mock_adapter_instance.disable_soft_keyboard.return_value = True
            
            device_interface = DeviceInterface(device_id="emulator-5554")
            
            # Verify initialization
            assert device_interface.device_id == "emulator-5554"
            mock_ui_adapter_class.assert_called_once_with(device_id="emulator-5554")
            mock_adapter_instance.connect.assert_called_once_with("emulator-5554")
            # Verify disable_soft_keyboard was called during initialization
            mock_adapter_instance.disable_soft_keyboard.assert_called_once()


class TestDeviceInterfaceMethods:
    """Test DeviceInterface core methods."""

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_click_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully performs click."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.disable_soft_keyboard.return_value = True
        mock_adapter_instance.click.return_value = True
        
        device_interface = DeviceInterface(device_id="emulator-5554")
        
        result = device_interface.click(100, 200)
        
        # Verify device click was called with correct coordinates
        mock_adapter_instance.click.assert_called_once_with(100, 200)
        assert result is True

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_input_text_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully inputs text."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.disable_soft_keyboard.return_value = True
        mock_adapter_instance.input_text.return_value = True
        
        device_interface = DeviceInterface(device_id="emulator-5554")
        
        result = device_interface.input_text("Hello World")
        
        # Verify device input_text was called with correct text
        mock_adapter_instance.input_text.assert_called_once_with("Hello World")
        assert result is True

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_swipe_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully performs swipe."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.disable_soft_keyboard.return_value = True
        mock_adapter_instance.swipe.return_value = True
        
        device_interface = DeviceInterface(device_id="emulator-5554")
        
        result = device_interface.swipe(100, 200, 300, 400)
        
        # Verify device swipe was called with correct coordinates
        mock_adapter_instance.swipe.assert_called_once_with(100, 200, 300, 400, duration=0.5)
        assert result is True

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_back_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully performs back action."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.disable_soft_keyboard.return_value = True
        mock_adapter_instance.press_back.return_value = True
        
        device_interface = DeviceInterface(device_id="emulator-5554")
        
        result = device_interface.back()
        
        # Verify device press_back was called
        mock_adapter_instance.press_back.assert_called_once()
        assert result is True

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_home_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully performs home action."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.disable_soft_keyboard.return_value = True
        mock_adapter_instance.press_home.return_value = True
        
        device_interface = DeviceInterface(device_id="emulator-5554")
        
        result = device_interface.home()
        
        # Verify device press_home was called
        mock_adapter_instance.press_home.assert_called_once()
        assert result is True

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_scroll_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully performs scroll."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.disable_soft_keyboard.return_value = True
        mock_adapter_instance.swipe.return_value = True  # scroll calls swipe internally
        
        device_interface = DeviceInterface(device_id="emulator-5554")
        
        result = device_interface.scroll("down", "medium")
        
        # Verify device swipe was called for scroll
        mock_adapter_instance.swipe.assert_called_once()
        assert result is True

    def test_take_screenshot_success(self):
        """DeviceInterface successfully takes screenshot."""
        with patch('rv_agent.agent.device_interface.UIAutomator2Adapter') as mock_ui_adapter_class, \
             patch('pathlib.Path') as mock_path_class, \
             patch('shutil.move') as mock_shutil_move:
            mock_adapter_instance = MagicMock()
            mock_ui_adapter_class.return_value = mock_adapter_instance
            mock_adapter_instance.connect.return_value = True
            mock_adapter_instance.disable_soft_keyboard.return_value = True
            mock_adapter_instance.take_screenshot.return_value = "screenshot.png"  # Returns just filename

            # Mock Path operations
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_class.return_value = mock_path_instance
            mock_path_class.return_value.exists.return_value = True  # For the screenshot path existence check

            # Mock shutil.move to avoid actual file operations
            mock_shutil_move.return_value = None

            device_interface = DeviceInterface(device_id="emulator-5554")

            result = device_interface.take_screenshot("/tmp")

            # Verify device take_screenshot was called
            mock_adapter_instance.take_screenshot.assert_called_once()
            # Verify shutil.move was called to move the file
            mock_shutil_move.assert_called_once()
            # The result should be the constructed path
            assert result is not None

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_get_current_ui_state_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully gets current UI state."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.disable_soft_keyboard.return_value = True
        expected_state = {"activity": "MainActivity", "elements": []}
        mock_adapter_instance.get_ui_state.return_value = expected_state
        
        device_interface = DeviceInterface(device_id="emulator-5554")
        
        result = device_interface.get_current_ui_state()
        
        # Verify device get_ui_state was called
        mock_adapter_instance.get_ui_state.assert_called_once()
        assert result == expected_state

    @patch('rv_agent.agent.device_interface.UIAutomator2Adapter')
    def test_launch_app_success(self, mock_ui_adapter_class):
        """DeviceInterface successfully launches app."""
        mock_adapter_instance = MagicMock()
        mock_ui_adapter_class.return_value = mock_adapter_instance
        mock_adapter_instance.connect.return_value = True
        mock_adapter_instance.disable_soft_keyboard.return_value = True
        mock_adapter_instance.launch_app.return_value = True
        
        device_interface = DeviceInterface(device_id="emulator-5554")
        
        result = device_interface.launch_app("com.example.app")
        
        # Verify device launch_app was called with correct package
        mock_adapter_instance.launch_app.assert_called_once_with("com.example.app")
        assert result is True

    def test_disable_soft_keyboard_success(self):
        """DeviceInterface successfully disables soft keyboard."""
        with patch('rv_agent.agent.device_interface.UIAutomator2Adapter') as mock_ui_adapter_class:
            mock_adapter_instance = MagicMock()
            mock_ui_adapter_class.return_value = mock_adapter_instance
            mock_adapter_instance.connect.return_value = True
            mock_adapter_instance.disable_soft_keyboard.return_value = True
            
            device_interface = DeviceInterface(device_id="emulator-5554")
            
            result = device_interface.disable_soft_keyboard()
            
            # Verify device disable_soft_keyboard was called (first during init, then during test)
            # So we expect it to be called twice
            assert mock_adapter_instance.disable_soft_keyboard.call_count == 2
            assert result is True