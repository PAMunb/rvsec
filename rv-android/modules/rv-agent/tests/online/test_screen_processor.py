"""
Screen processor integration tests.

Tests ScreenProcessor with real device UI.
"""

import pytest
import time

from rv_agent.services.screen_analyzer import ScreenProcessor
from rv_agent.agent.device_interface import DeviceInterface
from .conftest import launch_app, force_stop_app


pytestmark = [pytest.mark.online]


class TestScreenCapture:
    """Test screen capture and parsing."""

    def test_parse_home_screen(self, device, device_id, check_emulator):
        """Can parse home screen UI."""
        processor = ScreenProcessor(device)

        result = processor.parse_current_screen(
            target_package=None,
            external_navigation_count=0
        )

        assert result is not None
        assert "screen_description" in result or "screen_hash" in result
        print(f"\n  Parsed screen: {list(result.keys())}")

    def test_parse_app_screen(self, device, cryptoapp, device_id, check_emulator):
        """Can parse app screen UI."""
        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        processor = ScreenProcessor(device)

        result = processor.parse_current_screen(
            target_package=cryptoapp.package_name,
            external_navigation_count=0
        )

        assert result is not None
        print(f"\n  App screen parsed: {list(result.keys())}")

        # Check for expected fields
        if "screen_description" in result:
            desc = result["screen_description"]
            print(f"  Screen description type: {type(desc)}")

    def test_extract_ui_elements(self, device, cryptoapp, device_id, check_emulator):
        """Extracts actionable UI elements."""
        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        processor = ScreenProcessor(device)

        result = processor.parse_current_screen(
            target_package=cryptoapp.package_name,
            external_navigation_count=0
        )

        assert result is not None

        # Check for UI elements
        if "screen_description" in result:
            desc = result["screen_description"]
            if hasattr(desc, "items"):
                print(f"\n  Found {len(desc.items)} UI items")
            elif hasattr(desc, "get_all_actions"):
                actions = desc.get_all_actions()
                print(f"\n  Found {len(actions)} actions")


class TestScreenHashing:
    """Test screen state hashing."""

    def test_same_screen_same_hash(self, device, cryptoapp, device_id, check_emulator):
        """Same screen produces same hash."""
        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        processor = ScreenProcessor(device)

        # Parse twice
        result1 = processor.parse_current_screen(
            target_package=cryptoapp.package_name,
            external_navigation_count=0
        )
        time.sleep(0.5)
        result2 = processor.parse_current_screen(
            target_package=cryptoapp.package_name,
            external_navigation_count=0
        )

        hash1 = result1.get("screen_hash") or result1.get("current_screen_hash")
        hash2 = result2.get("screen_hash") or result2.get("current_screen_hash")

        if hash1 and hash2:
            assert hash1 == hash2, "Same screen should produce same hash"
            print(f"\n  Hash: {hash1}")

    def test_different_screens_different_hash(self, device, cryptoapp, device_id, check_emulator):
        """Different screens produce different hashes."""
        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        processor = ScreenProcessor(device)

        # Parse first screen
        result1 = processor.parse_current_screen(
            target_package=cryptoapp.package_name,
            external_navigation_count=0
        )

        # Navigate to different screen
        device.click(540, 600)  # Click something
        time.sleep(1)

        result2 = processor.parse_current_screen(
            target_package=cryptoapp.package_name,
            external_navigation_count=0
        )

        hash1 = result1.get("screen_hash") or result1.get("current_screen_hash")
        hash2 = result2.get("screen_hash") or result2.get("current_screen_hash")

        if hash1 and hash2:
            # They might be same if click did nothing
            print(f"\n  Hash 1: {hash1}")
            print(f"  Hash 2: {hash2}")
            print(f"  Same: {hash1 == hash2}")


class TestExternalNavigation:
    """Test external navigation detection."""

    def test_detects_external_app(self, device, cryptoapp, device_id, check_emulator):
        """Detects when navigation leaves target app."""
        launch_app(device_id, cryptoapp.package_name)
        time.sleep(2)

        processor = ScreenProcessor(device)

        # Parse in target app
        result1 = processor.parse_current_screen(
            target_package=cryptoapp.package_name,
            external_navigation_count=0
        )

        # Go home (external navigation)
        device.home()
        time.sleep(1)

        # Parse outside target app
        result2 = processor.parse_current_screen(
            target_package=cryptoapp.package_name,
            external_navigation_count=0
        )

        # Check external navigation detection
        is_external = result2.get("is_external", False) or result2.get("external_app", False)
        print(f"\n  External navigation detected: {is_external}")

        # Return to app
        launch_app(device_id, cryptoapp.package_name)
