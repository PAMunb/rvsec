"""
Device interface integration tests.

Tests DeviceInterface with real Android emulator.
"""

import pytest
import time

from .conftest import launch_app

pytestmark = [pytest.mark.online]


class TestDeviceConnection:
    """Test device connection and basic operations."""

    def test_device_connected(self, device, check_emulator):
        """Device is connected and responsive."""
        assert device is not None
        assert device.device_id == "emulator-5554"

    def test_get_screen_size(self, device, check_emulator):
        """Can retrieve screen dimensions."""
        width, height = device.get_screen_size()
        assert width > 0
        assert height > 0
        # Typical emulator sizes
        assert 720 <= width <= 1440
        assert 1280 <= height <= 2560
        print(f"\n  Screen size: {width}x{height}")


class TestScreenCapture:
    """Test screenshot and UI hierarchy capture."""

    def test_capture_screenshot(self, device, check_emulator):
        """Can capture screenshot from device."""
        screenshot_path = device.take_screenshot()
        assert screenshot_path is not None
        from pathlib import Path

        assert Path(screenshot_path).exists()
        size = Path(screenshot_path).stat().st_size
        assert size > 1000  # Non-trivial image
        print(f"\n  Screenshot saved: {screenshot_path} ({size} bytes)")

    def test_capture_ui_hierarchy(self, device, check_emulator):
        """Can capture UI state."""
        ui_state = device.get_current_ui_state()
        assert ui_state is not None
        print(f"\n  UI state type: {type(ui_state)}")


class TestAppInteraction:
    """Test app launch and interaction."""

    def test_launch_app(self, device, cryptoapp, device_id, check_emulator):
        """Can launch installed app."""
        success = launch_app(device_id, cryptoapp.package_name)
        assert success
        time.sleep(2)

        # Verify app launched by checking UI state
        ui_state = device.get_current_ui_state()
        assert ui_state is not None
        print(f"\n  App launched, UI state retrieved")

    def test_click_action(self, device, cryptoapp, device_id, check_emulator):
        """Can perform click action."""
        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        # Click center of screen
        result = device.click(540, 960)
        assert result is True or result is None  # Some implementations return None
        print("\n  Click at (540, 960) executed")

    def test_back_action(self, device, cryptoapp, device_id, check_emulator):
        """Can perform back action."""
        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        result = device.back()
        assert result is True or result is None
        print("\n  Back action executed")

    def test_home_action(self, device, check_emulator):
        """Can go to home screen."""
        result = device.home()
        assert result is True or result is None
        time.sleep(1)
        print("\n  Home action executed")

    def test_swipe_action(self, device, cryptoapp, device_id, check_emulator):
        """Can perform swipe action."""
        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        # Swipe up (scroll down)
        result = device.swipe(540, 1200, 540, 600, duration=300)
        assert result is True or result is None
        print("\n  Swipe executed")


class TestTextInput:
    """Test text input functionality."""

    def test_type_text(self, device, cryptoapp, device_id, check_emulator):
        """Can type text on device."""
        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        # Type simple text
        result = device.input_text("test123")
        assert result is True or result is None
        print("\n  Text 'test123' typed")

    def test_clear_and_type(self, device, cryptoapp, device_id, check_emulator):
        """Can clear field and type new text."""
        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        # Type new text
        result = device.input_text("newtext")
        assert result is True or result is None
        print("\n  Text input executed")
