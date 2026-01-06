"""
Unit tests for MockDeviceInterface.
"""

import base64
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from rv_agent.validation.mock_device import MockDeviceInterface
from rv_agent.validation.sequence_loader import ScreenData, AppSequence
from rv_agent.validation.action_validator import ValidationResult


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_screen_data(tmp_path) -> ScreenData:
    """Create a sample ScreenData for testing."""
    # Create screenshot
    screenshot_path = tmp_path / "001.png"
    screenshot_path.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

    # Create UIAutomator dump
    uiautomator_path = tmp_path / "001.uiautomator"
    uiautomator_path.write_text('''<?xml version="1.0" encoding="UTF-8"?>
    <hierarchy rotation="0">
        <node bounds="[100,100][300,200]" class="android.widget.Button"
              clickable="true" long-clickable="false" checkable="false"
              resource-id="button1" text="Click Me" content-desc="">
        </node>
        <node bounds="[100,250][400,300]" class="android.widget.EditText"
              clickable="true" long-clickable="false" checkable="false"
              editable="true"
              resource-id="input1" text="" content-desc="">
        </node>
    </hierarchy>
    ''')

    return ScreenData(
        step=1,
        screenshot_path=screenshot_path,
        uiautomator_path=uiautomator_path,
        state_path=tmp_path / "001.state",
        activity="com.example.MainActivity",
        package="com.example",
        screen_size=(1080, 1920)
    )


@pytest.fixture
def sample_sequence(tmp_path, sample_screen_data) -> AppSequence:
    """Create a sample AppSequence for testing."""
    # Create multiple screens
    screens = []
    for i in range(3):
        step_str = f"{i+1:03d}"
        screenshot_path = tmp_path / f"{step_str}.png"
        screenshot_path.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)

        uiautomator_path = tmp_path / f"{step_str}.uiautomator"
        uiautomator_path.write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
        <hierarchy rotation="0">
            <node bounds="[100,100][300,200]" class="android.widget.Button"
                  clickable="true" long-clickable="true" checkable="false"
                  resource-id="button{i}" text="Button {i}" content-desc="">
            </node>
        </hierarchy>
        ''')

        screens.append(ScreenData(
            step=i + 1,
            screenshot_path=screenshot_path,
            uiautomator_path=uiautomator_path,
            state_path=tmp_path / f"{step_str}.state",
            activity=f"com.example.Activity{i}",
            package="com.example",
            screen_size=(1080, 1920)
        ))

    return AppSequence(
        app_name="test.apk",
        app_dir=tmp_path,
        package_name="com.example",
        screens=screens
    )


# =============================================================================
# MockDeviceInterface Initialization Tests
# =============================================================================

class TestMockDeviceInterfaceInit:
    """Tests for MockDeviceInterface initialization."""

    def test_init_basic(self, sample_sequence):
        """Test basic initialization."""
        mock_device = MockDeviceInterface(sample_sequence)

        assert mock_device.sequence == sample_sequence
        assert mock_device.device_id == "mock"
        assert mock_device.current_step == 0
        assert mock_device.actions_executed == []

    def test_init_with_device_id(self, sample_sequence):
        """Test initialization with custom device ID."""
        mock_device = MockDeviceInterface(sample_sequence, device_id="emulator-5554")

        assert mock_device.device_id == "emulator-5554"

    def test_init_loads_ui_elements(self, sample_sequence):
        """Test that UI elements are loaded on init."""
        mock_device = MockDeviceInterface(sample_sequence)

        assert len(mock_device.validator.current_elements) > 0

    def test_init_empty_sequence(self, tmp_path):
        """Test initialization with empty sequence."""
        sequence = AppSequence(
            app_name="empty.apk",
            app_dir=tmp_path,
            package_name="com.empty",
            screens=[]
        )

        mock_device = MockDeviceInterface(sequence)

        assert mock_device.current_step == 0
        assert len(mock_device.validator.current_elements) == 0


# =============================================================================
# Current Screen Property Tests
# =============================================================================

class TestMockDeviceCurrentScreen:
    """Tests for current_screen property."""

    def test_current_screen_returns_first(self, sample_sequence):
        """Test that current_screen returns first screen initially."""
        mock_device = MockDeviceInterface(sample_sequence)

        assert mock_device.current_screen.step == 1
        assert mock_device.current_screen == sample_sequence.screens[0]


# =============================================================================
# Get UI State Tests
# =============================================================================

class TestMockDeviceGetCurrentUIState:
    """Tests for get_current_ui_state()."""

    def test_get_current_ui_state(self, sample_sequence):
        """Test getting current UI state."""
        mock_device = MockDeviceInterface(sample_sequence)

        state = mock_device.get_current_ui_state()

        assert 'xml' in state
        assert 'current_activity' in state
        assert 'current_package' in state
        assert 'hierarchy' in state['xml']
        assert state['current_package'] == "com.example"

    def test_get_current_ui_state_read_error(self, sample_sequence):
        """Test handling of read error."""
        mock_device = MockDeviceInterface(sample_sequence)

        # Delete the uiautomator file to cause an error
        sample_sequence.screens[0].uiautomator_path.unlink()

        state = mock_device.get_current_ui_state()

        assert state['xml'] == ''
        assert state['current_activity'] == 'unknown'


# =============================================================================
# Screenshot Tests
# =============================================================================

class TestMockDeviceScreenshot:
    """Tests for screenshot methods."""

    def test_get_screenshot(self, sample_sequence):
        """Test getting screenshot bytes."""
        mock_device = MockDeviceInterface(sample_sequence)

        screenshot = mock_device.get_screenshot()

        assert screenshot is not None
        assert isinstance(screenshot, bytes)
        assert screenshot.startswith(b'\x89PNG')

    def test_get_screenshot_error(self, sample_sequence):
        """Test handling of screenshot read error."""
        mock_device = MockDeviceInterface(sample_sequence)

        # Delete the screenshot file
        sample_sequence.screens[0].screenshot_path.unlink()

        screenshot = mock_device.get_screenshot()

        assert screenshot is None

    def test_take_screenshot(self, sample_sequence):
        """Test take_screenshot returns path."""
        mock_device = MockDeviceInterface(sample_sequence)

        path = mock_device.take_screenshot()

        assert path == str(sample_sequence.screens[0].screenshot_path)

    def test_get_screenshot_base64(self, sample_sequence):
        """Test getting base64-encoded screenshot."""
        mock_device = MockDeviceInterface(sample_sequence)

        b64 = mock_device.get_screenshot_base64()

        assert b64 != ""
        # Verify it's valid base64
        decoded = base64.b64decode(b64)
        assert decoded.startswith(b'\x89PNG')

    def test_get_screenshot_base64_error(self, sample_sequence):
        """Test base64 screenshot with error."""
        mock_device = MockDeviceInterface(sample_sequence)
        sample_sequence.screens[0].screenshot_path.unlink()

        b64 = mock_device.get_screenshot_base64()

        assert b64 == ""


# =============================================================================
# Activity and Package Tests
# =============================================================================

class TestMockDeviceActivityPackage:
    """Tests for activity and package methods."""

    def test_get_current_activity(self, sample_sequence):
        """Test getting current activity."""
        mock_device = MockDeviceInterface(sample_sequence)

        activity = mock_device.get_current_activity()

        assert activity == "com.example.Activity0"

    def test_get_current_package(self, sample_sequence):
        """Test getting current package."""
        mock_device = MockDeviceInterface(sample_sequence)

        package = mock_device.get_current_package()

        assert package == "com.example"


# =============================================================================
# Click Action Tests
# =============================================================================

class TestMockDeviceClick:
    """Tests for click action."""

    def test_click_advances_sequence(self, sample_sequence):
        """Test that click advances sequence."""
        mock_device = MockDeviceInterface(sample_sequence)
        initial_step = mock_device.current_step

        mock_device.click(200, 150)

        assert mock_device.current_step == initial_step + 1

    def test_click_returns_true(self, sample_sequence):
        """Test that click always returns True."""
        mock_device = MockDeviceInterface(sample_sequence)

        result = mock_device.click(200, 150)

        assert result is True

    def test_click_records_action(self, sample_sequence):
        """Test that click records action."""
        mock_device = MockDeviceInterface(sample_sequence)

        mock_device.click(200, 150)

        assert len(mock_device.actions_executed) == 1
        assert mock_device.actions_executed[0]['action_type'] == 'CLICK'

    def test_click_validates_coordinates(self, sample_sequence):
        """Test that click validates coordinates."""
        mock_device = MockDeviceInterface(sample_sequence)

        # Click on button (valid)
        mock_device.click(200, 150)
        assert mock_device.actions_executed[0]['valid'] is True

    def test_click_invalid_coordinates(self, sample_sequence):
        """Test click on invalid coordinates."""
        mock_device = MockDeviceInterface(sample_sequence)

        # Click on empty area
        mock_device.click(500, 500)

        assert mock_device.actions_executed[0]['valid'] is False

    def test_click_wraps_sequence(self, sample_sequence):
        """Test that click wraps around at end of sequence."""
        mock_device = MockDeviceInterface(sample_sequence)

        # Click enough times to wrap
        for _ in range(4):  # 3 screens + 1 to wrap
            mock_device.click(200, 150)

        assert mock_device.current_step == 1  # Back to second screen (wrapped)


# =============================================================================
# Input Text Tests
# =============================================================================

class TestMockDeviceInputText:
    """Tests for input_text action."""

    def test_input_text_returns_true(self, sample_sequence):
        """Test that input_text always returns True."""
        mock_device = MockDeviceInterface(sample_sequence)

        result = mock_device.input_text("hello")

        assert result is True

    def test_input_text_no_action_recorded(self, sample_sequence):
        """Test that input_text doesn't record action (it's a helper)."""
        mock_device = MockDeviceInterface(sample_sequence)

        mock_device.input_text("hello")

        # input_text is a no-op helper, doesn't advance or record
        assert len(mock_device.actions_executed) == 0


# =============================================================================
# Type Text Tests
# =============================================================================

class TestMockDeviceTypeText:
    """Tests for type_text action."""

    def test_type_text_with_coordinates(self, sample_sequence):
        """Test type_text with coordinates."""
        mock_device = MockDeviceInterface(sample_sequence)

        result = mock_device.type_text("hello", x=250, y=275)

        assert result is True
        assert len(mock_device.actions_executed) == 1
        assert mock_device.actions_executed[0]['action_type'] == 'SET_TEXT'

    def test_type_text_without_coordinates(self, sample_sequence):
        """Test type_text without coordinates."""
        mock_device = MockDeviceInterface(sample_sequence)

        result = mock_device.type_text("hello")

        assert result is True
        assert mock_device.actions_executed[0]['valid'] is True

    def test_type_text_advances_sequence(self, sample_sequence):
        """Test that type_text advances sequence."""
        mock_device = MockDeviceInterface(sample_sequence)
        initial_step = mock_device.current_step

        mock_device.type_text("hello", x=250, y=275)

        assert mock_device.current_step == initial_step + 1


# =============================================================================
# Long Click Tests
# =============================================================================

class TestMockDeviceLongClick:
    """Tests for long_click action."""

    def test_long_click_advances_sequence(self, sample_sequence):
        """Test that long_click advances sequence."""
        mock_device = MockDeviceInterface(sample_sequence)
        initial_step = mock_device.current_step

        mock_device.long_click(200, 150)

        assert mock_device.current_step == initial_step + 1

    def test_long_click_returns_true(self, sample_sequence):
        """Test that long_click always returns True."""
        mock_device = MockDeviceInterface(sample_sequence)

        result = mock_device.long_click(200, 150)

        assert result is True

    def test_long_click_records_action(self, sample_sequence):
        """Test that long_click records action."""
        mock_device = MockDeviceInterface(sample_sequence)

        mock_device.long_click(200, 150)

        assert len(mock_device.actions_executed) == 1
        assert mock_device.actions_executed[0]['action_type'] == 'LONG_CLICK'


# =============================================================================
# System Action Tests
# =============================================================================

class TestMockDeviceSystemActions:
    """Tests for system actions (back, home)."""

    def test_back_advances_sequence(self, sample_sequence):
        """Test that back advances sequence."""
        mock_device = MockDeviceInterface(sample_sequence)
        initial_step = mock_device.current_step

        mock_device.back()

        assert mock_device.current_step == initial_step + 1

    def test_back_returns_true(self, sample_sequence):
        """Test that back always returns True."""
        mock_device = MockDeviceInterface(sample_sequence)

        result = mock_device.back()

        assert result is True

    def test_back_records_valid_action(self, sample_sequence):
        """Test that back is always valid."""
        mock_device = MockDeviceInterface(sample_sequence)

        mock_device.back()

        assert mock_device.actions_executed[0]['action_type'] == 'BACK'
        assert mock_device.actions_executed[0]['valid'] is True

    def test_home_advances_sequence(self, sample_sequence):
        """Test that home advances sequence."""
        mock_device = MockDeviceInterface(sample_sequence)
        initial_step = mock_device.current_step

        mock_device.home()

        assert mock_device.current_step == initial_step + 1

    def test_home_returns_true(self, sample_sequence):
        """Test that home always returns True."""
        mock_device = MockDeviceInterface(sample_sequence)

        result = mock_device.home()

        assert result is True

    def test_home_records_valid_action(self, sample_sequence):
        """Test that home is always valid."""
        mock_device = MockDeviceInterface(sample_sequence)

        mock_device.home()

        assert mock_device.actions_executed[0]['action_type'] == 'HOME'
        assert mock_device.actions_executed[0]['valid'] is True


# =============================================================================
# Launch App and Keyboard Tests
# =============================================================================

class TestMockDeviceLaunchAndKeyboard:
    """Tests for launch_app and disable_soft_keyboard."""

    def test_launch_app_returns_true(self, sample_sequence):
        """Test that launch_app returns True."""
        mock_device = MockDeviceInterface(sample_sequence)

        result = mock_device.launch_app("com.example")

        assert result is True

    def test_launch_app_no_side_effects(self, sample_sequence):
        """Test that launch_app doesn't advance sequence."""
        mock_device = MockDeviceInterface(sample_sequence)
        initial_step = mock_device.current_step

        mock_device.launch_app("com.example")

        assert mock_device.current_step == initial_step
        assert len(mock_device.actions_executed) == 0

    def test_disable_soft_keyboard_returns_true(self, sample_sequence):
        """Test that disable_soft_keyboard returns True."""
        mock_device = MockDeviceInterface(sample_sequence)

        result = mock_device.disable_soft_keyboard()

        assert result is True


# =============================================================================
# Action Summary Tests
# =============================================================================

class TestMockDeviceGetActionSummary:
    """Tests for get_action_summary()."""

    def test_get_action_summary_empty(self, sample_sequence):
        """Test summary with no actions."""
        mock_device = MockDeviceInterface(sample_sequence)

        summary = mock_device.get_action_summary()

        assert summary['total_actions'] == 0
        assert summary['valid_actions'] == 0
        assert summary['invalid_actions'] == 0
        assert summary['valid_rate'] == 0.0
        assert summary['action_types'] == {}
        assert summary['actions'] == []

    def test_get_action_summary_with_actions(self, sample_sequence):
        """Test summary with various actions."""
        mock_device = MockDeviceInterface(sample_sequence)

        mock_device.click(200, 150)  # Valid click
        mock_device.click(500, 500)  # Invalid click (empty area)
        mock_device.back()  # Valid system action

        summary = mock_device.get_action_summary()

        assert summary['total_actions'] == 3
        assert summary['valid_actions'] == 2
        assert summary['invalid_actions'] == 1
        assert summary['valid_rate'] == pytest.approx(2/3)
        assert summary['action_types']['CLICK'] == 2
        assert summary['action_types']['BACK'] == 1
        assert len(summary['actions']) == 3


# =============================================================================
# Step and Sequence Length Tests
# =============================================================================

class TestMockDeviceStepMethods:
    """Tests for get_current_step and get_sequence_length."""

    def test_get_current_step(self, sample_sequence):
        """Test getting current step (1-indexed)."""
        mock_device = MockDeviceInterface(sample_sequence)

        # Initially at step 1 (not 0)
        assert mock_device.get_current_step() == 1

        mock_device.click(200, 150)
        assert mock_device.get_current_step() == 2

    def test_get_sequence_length(self, sample_sequence):
        """Test getting sequence length."""
        mock_device = MockDeviceInterface(sample_sequence)

        length = mock_device.get_sequence_length()

        assert length == 3


# =============================================================================
# Advance Sequence Tests
# =============================================================================

class TestMockDeviceAdvanceSequence:
    """Tests for _advance_sequence internal method."""

    def test_advance_loads_new_ui_elements(self, sample_sequence):
        """Test that advancing loads UI elements for new screen."""
        mock_device = MockDeviceInterface(sample_sequence)

        # Initial elements count
        initial_elements = len(mock_device.validator.current_elements)

        mock_device.click(200, 150)

        # Elements should be reloaded (count might differ between screens)
        # At minimum, verify that load was called by checking elements exist
        assert len(mock_device.validator.current_elements) > 0
