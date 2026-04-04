"""
Unit tests for rv-uiautomator module.

Tests cover UIAutomator2Adapter, UIAutomatorActionExecutor, StateConverter,
and constants. All device interactions are mocked.
"""

import hashlib
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rv_android_core.domain.widget import WidgetEventType

from rv_uiautomator import (
    StateConverter,
    UIAutomator2Adapter,
    UIAutomatorActionExecutor,
)
from rv_uiautomator.constants import (
    ACTION_EXECUTION_DELAY,
    DEFAULT_CONNECTION_TIMEOUT,
    DEFAULT_DEVICE_ID,
    DEFAULT_SWIPE_DURATION,
    MAX_CONSECUTIVE_ERRORS,
    MAX_RETRY_ATTEMPTS,
    MAX_SWIPE_DURATION,
    MIN_SWIPE_DURATION,
    SCREEN_HASH_LENGTH,
    SCREENSHOT_QUALITY,
    STATE_STABILIZATION_DELAY,
    TEXT_INPUT_DELAY,
    WAIT_FOR_IDLE_TIMEOUT,
    WAIT_FOR_SELECTOR_TIMEOUT,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter():
    """UIAutomator2Adapter instance (not connected)."""
    return UIAutomator2Adapter("test-device")


@pytest.fixture
def connected_adapter():
    """UIAutomator2Adapter with a mocked connected device."""
    a = UIAutomator2Adapter("emulator-5554")
    a.device = MagicMock()
    a.connected = True
    return a


@pytest.fixture
def executor():
    return UIAutomatorActionExecutor()


@pytest.fixture
def converter():
    return StateConverter()


@pytest.fixture
def sample_ui_state():
    """UIAutomator-format state dictionary."""
    return {
        "xml": "<hierarchy><node text='Hello'/></hierarchy>",
        "current_activity": "com.example/.MainActivity",
        "current_package": "com.example",
        "screenshot_path": "/tmp/screen.png",
        "device_info": {"productName": "sdk_phone"},
        "timestamp": 1700000000.0,
    }


def _make_action(action_type, coordinates=None, params=None, text_value=None,
                 is_custom=False, text="test action"):
    """Helper to build a simple action namespace."""
    ns = SimpleNamespace(
        action_type=action_type,
        text=text,
    )
    if coordinates is not None:
        ns.coordinates = coordinates
    if params is not None:
        ns.params = params
    if text_value is not None:
        ns.text_value = text_value
    if is_custom:
        ns.is_custom = True
        if coordinates is not None:
            ns.coordinates = coordinates
    return ns


# ===================================================================
# UIAutomator2Adapter tests
# ===================================================================


class TestUIAutomator2AdapterInit:
    def test_default_device_id(self):
        a = UIAutomator2Adapter()
        assert a.device_id == "emulator-5554"

    def test_custom_device_id(self, adapter):
        assert adapter.device_id == "test-device"

    def test_initially_not_connected(self, adapter):
        assert adapter.connected is False

    def test_device_is_none_before_connect(self, adapter):
        assert adapter.device is None


class TestUIAutomator2AdapterConnectionGuard:
    """Operations on a disconnected adapter must return False / empty."""

    def test_click_when_not_connected(self, adapter):
        assert adapter.click(100, 200) is False

    def test_input_text_when_not_connected(self, adapter):
        assert adapter.input_text("hello") is False

    def test_long_click_when_not_connected(self, adapter):
        assert adapter.long_click(10, 20) is False

    def test_swipe_when_not_connected(self, adapter):
        assert adapter.swipe(0, 0, 100, 100) is False

    def test_press_back_when_not_connected(self, adapter):
        assert adapter.press_back() is False

    def test_press_home_when_not_connected(self, adapter):
        assert adapter.press_home() is False

    def test_take_screenshot_when_not_connected(self, adapter):
        assert adapter.take_screenshot() is None

    def test_get_ui_state_when_not_connected(self, adapter):
        assert adapter.get_ui_state() == {}

    def test_launch_app_when_not_connected(self, adapter):
        assert adapter.launch_app("com.example") is False

    def test_stop_app_when_not_connected(self, adapter):
        assert adapter.stop_app("com.example") is False


class TestUIAutomator2AdapterConnectedActions:
    """Actions on a connected adapter delegate to the mock device."""

    @patch("time.sleep")
    def test_click_success(self, mock_sleep, connected_adapter):
        result = connected_adapter.click(100, 200)
        connected_adapter.device.click.assert_called_once_with(100, 200)
        assert result is True

    @patch("time.sleep")
    def test_click_device_exception_returns_false(self, mock_sleep, connected_adapter):
        connected_adapter.device.click.side_effect = RuntimeError("device error")
        assert connected_adapter.click(50, 50) is False

    @patch("time.sleep")
    def test_input_text_clears_then_types(self, mock_sleep, connected_adapter):
        result = connected_adapter.input_text("hello")
        connected_adapter.device.send_keys.assert_any_call("", clear=True)
        connected_adapter.device.send_keys.assert_any_call("hello")
        assert result is True

    @patch("time.sleep")
    def test_long_click_with_duration(self, mock_sleep, connected_adapter):
        result = connected_adapter.long_click(10, 20, duration=2.5)
        connected_adapter.device.long_click.assert_called_once_with(10, 20, 2.5)
        assert result is True

    @patch("time.sleep")
    def test_swipe_delegates_correctly(self, mock_sleep, connected_adapter):
        result = connected_adapter.swipe(0, 100, 0, 500, 0.3)
        connected_adapter.device.swipe.assert_called_once_with(0, 100, 0, 500, 0.3)
        assert result is True

    @patch("time.sleep")
    def test_press_back(self, mock_sleep, connected_adapter):
        result = connected_adapter.press_back()
        connected_adapter.device.press.assert_called_once_with("back")
        assert result is True

    @patch("time.sleep")
    def test_press_home(self, mock_sleep, connected_adapter):
        result = connected_adapter.press_home()
        connected_adapter.device.press.assert_called_once_with("home")
        assert result is True

    @patch("time.sleep")
    def test_get_ui_state_returns_expected_keys(self, mock_sleep, connected_adapter):
        connected_adapter.device.info = {"productName": "test"}
        connected_adapter.device.app_current.return_value = {
            "package": "com.pkg",
            "activity": ".Act",
        }
        connected_adapter.device.dump_hierarchy.return_value = "<hierarchy/>"

        state = connected_adapter.get_ui_state()

        assert state["current_package"] == "com.pkg"
        assert state["current_activity"] == ".Act"
        assert state["xml"] == "<hierarchy/>"
        assert "timestamp" in state

    @patch("time.sleep")
    def test_launch_app_success(self, mock_sleep, connected_adapter):
        connected_adapter.device.app_current.return_value = {"package": "com.app"}
        result = connected_adapter.launch_app("com.app")
        connected_adapter.device.app_start.assert_called_once_with("com.app")
        assert result is True

    @patch("time.sleep")
    def test_launch_app_verification_fails(self, mock_sleep, connected_adapter):
        connected_adapter.device.app_current.return_value = {"package": "com.other"}
        result = connected_adapter.launch_app("com.app")
        assert result is False

    @patch("time.sleep")
    def test_stop_app_success(self, mock_sleep, connected_adapter):
        result = connected_adapter.stop_app("com.app")
        connected_adapter.device.app_stop.assert_called_once_with("com.app")
        assert result is True


# ===================================================================
# UIAutomatorActionExecutor tests
# ===================================================================


class TestActionExecutorDispatch:
    """Test action dispatch by WidgetEventType."""

    def test_none_action_returns_false(self, executor):
        mock_adapter = MagicMock()
        assert executor.execute(None, mock_adapter) is False

    def test_none_adapter_returns_false(self, executor):
        action = _make_action("click", coordinates=[100, 200])
        assert executor.execute(action, None) is False

    @patch("time.sleep")
    def test_click_action(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        mock_adapter.click.return_value = True
        action = _make_action("click", coordinates=[100, 200])
        assert executor.execute(action, mock_adapter) is True
        mock_adapter.click.assert_called_once_with(100, 200)

    @patch("time.sleep")
    def test_click_missing_coordinates(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        action = SimpleNamespace(action_type="click", text="click btn")
        assert executor.execute(action, mock_adapter) is False

    @patch("time.sleep")
    def test_long_click_action(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        mock_adapter.long_click.return_value = True
        action = _make_action("long_click", coordinates=[50, 60])
        assert executor.execute(action, mock_adapter) is True
        mock_adapter.long_click.assert_called_once_with(50, 60, 1.0)

    @patch("time.sleep")
    def test_long_click_custom_duration(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        mock_adapter.long_click.return_value = True
        action = _make_action("long_click", coordinates=[50, 60],
                              params={"duration": 3.0})
        assert executor.execute(action, mock_adapter) is True
        mock_adapter.long_click.assert_called_once_with(50, 60, 3.0)

    @patch("time.sleep")
    def test_text_change_with_params_text(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        mock_adapter.click.return_value = True
        mock_adapter.input_text.return_value = True
        action = _make_action("text_change", coordinates=[100, 200],
                              params={"text": "hello"})
        assert executor.execute(action, mock_adapter) is True
        mock_adapter.input_text.assert_called_once_with("hello")

    @patch("time.sleep")
    def test_text_change_with_text_value(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        mock_adapter.input_text.return_value = True
        action = _make_action("text_change", text_value="world")
        assert executor.execute(action, mock_adapter) is True
        mock_adapter.input_text.assert_called_once_with("world")

    @patch("time.sleep")
    def test_text_change_missing_text_returns_false(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        action = _make_action("text_change")
        assert executor.execute(action, mock_adapter) is False

    @patch("time.sleep")
    def test_scroll_down(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        mock_adapter.swipe.return_value = True
        action = _make_action("scroll", coordinates=[200, 300],
                              params={"direction": "down", "distance": 400})
        assert executor.execute(action, mock_adapter) is True
        mock_adapter.swipe.assert_called_once_with(200, 300, 200, 700, 0.5)

    @patch("time.sleep")
    def test_scroll_up(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        mock_adapter.swipe.return_value = True
        action = _make_action("scroll", coordinates=[200, 600],
                              params={"direction": "up", "distance": 200})
        assert executor.execute(action, mock_adapter) is True
        mock_adapter.swipe.assert_called_once_with(200, 600, 200, 400, 0.5)

    @patch("time.sleep")
    def test_scroll_left(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        mock_adapter.swipe.return_value = True
        action = _make_action("scroll", coordinates=[500, 300],
                              params={"direction": "left", "distance": 100})
        assert executor.execute(action, mock_adapter) is True
        mock_adapter.swipe.assert_called_once_with(500, 300, 400, 300, 0.5)

    @patch("time.sleep")
    def test_scroll_right(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        mock_adapter.swipe.return_value = True
        action = _make_action("scroll", coordinates=[100, 300],
                              params={"direction": "right", "distance": 150})
        assert executor.execute(action, mock_adapter) is True
        mock_adapter.swipe.assert_called_once_with(100, 300, 250, 300, 0.5)

    @patch("time.sleep")
    def test_scroll_unknown_direction_returns_false(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        action = _make_action("scroll", coordinates=[100, 100],
                              params={"direction": "diagonal"})
        assert executor.execute(action, mock_adapter) is False

    @patch("time.sleep")
    def test_back_action(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        mock_adapter.press_back.return_value = True
        action = _make_action("back")
        assert executor.execute(action, mock_adapter) is True
        mock_adapter.press_back.assert_called_once()

    @patch("time.sleep")
    def test_custom_coordinate_action(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        mock_adapter.click.return_value = True
        action = _make_action("custom", coordinates=[300, 400], is_custom=True)
        assert executor.execute(action, mock_adapter) is True
        mock_adapter.click.assert_called_once_with(300, 400)

    @patch("time.sleep")
    def test_unsupported_action_type_returns_false(self, mock_sleep, executor):
        mock_adapter = MagicMock()
        action = _make_action("unknown_action")
        assert executor.execute(action, mock_adapter) is False


# ===================================================================
# StateConverter tests
# ===================================================================


class TestStateConverterConversion:
    def test_empty_state_returns_empty(self, converter):
        assert converter.uiautomator_to_droidbot({}) == {}

    def test_none_state_returns_empty(self, converter):
        assert converter.uiautomator_to_droidbot(None) == {}

    def test_xml_maps_to_hierarchy(self, converter, sample_ui_state):
        result = converter.uiautomator_to_droidbot(sample_ui_state)
        assert result["hierarchy"] == sample_ui_state["xml"]

    def test_xml_maps_to_view_tree(self, converter, sample_ui_state):
        result = converter.uiautomator_to_droidbot(sample_ui_state)
        assert result["view_tree"] == sample_ui_state["xml"]

    def test_activity_field_mapping(self, converter, sample_ui_state):
        result = converter.uiautomator_to_droidbot(sample_ui_state)
        assert result["activity"] == "com.example/.MainActivity"

    def test_package_name_field_mapping(self, converter, sample_ui_state):
        result = converter.uiautomator_to_droidbot(sample_ui_state)
        assert result["package_name"] == "com.example"

    def test_screenshot_path_preserved(self, converter, sample_ui_state):
        result = converter.uiautomator_to_droidbot(sample_ui_state)
        assert result["screenshot_path"] == "/tmp/screen.png"

    def test_device_info_preserved(self, converter, sample_ui_state):
        result = converter.uiautomator_to_droidbot(sample_ui_state)
        assert result["device_info"] == {"productName": "sdk_phone"}

    def test_conversion_metadata_present(self, converter, sample_ui_state):
        result = converter.uiautomator_to_droidbot(sample_ui_state)
        meta = result["_conversion_metadata"]
        assert meta["source_format"] == "uiautomator"
        assert meta["target_format"] == "droidbot"

    def test_missing_fields_get_defaults(self, converter):
        result = converter.uiautomator_to_droidbot({"xml": "<h/>"})
        assert result["activity"] == "unknown"
        assert result["package_name"] == "unknown"

    def test_extra_fields_are_preserved(self, converter):
        state = {
            "xml": "<h/>",
            "current_activity": ".Act",
            "current_package": "pkg",
            "custom_field": 42,
        }
        result = converter.uiautomator_to_droidbot(state)
        assert result["custom_field"] == 42


class TestStateConverterScreenHash:
    def test_hash_from_hierarchy(self, converter):
        state = {"hierarchy": "<hierarchy>content</hierarchy>"}
        h = converter.compute_screen_hash(state)
        assert h is not None
        assert len(h) == SCREEN_HASH_LENGTH

    def test_hash_from_xml_key(self, converter):
        state = {"xml": "<hierarchy>content</hierarchy>"}
        h = converter.compute_screen_hash(state)
        assert h is not None
        assert len(h) == SCREEN_HASH_LENGTH

    def test_hash_fallback_to_activity(self, converter):
        state = {"activity": ".Main", "package_name": "com.app"}
        h = converter.compute_screen_hash(state)
        expected = hashlib.sha256("com.app/.Main".encode()).hexdigest()[:SCREEN_HASH_LENGTH]
        assert h == expected

    def test_hash_deterministic(self, converter):
        state = {"hierarchy": "<h>same</h>"}
        assert converter.compute_screen_hash(state) == converter.compute_screen_hash(state)

    def test_hash_different_for_different_content(self, converter):
        h1 = converter.compute_screen_hash({"hierarchy": "<h>aaa</h>"})
        h2 = converter.compute_screen_hash({"hierarchy": "<h>bbb</h>"})
        assert h1 != h2

    def test_hash_empty_state_uses_fallback(self, converter):
        state = {}
        h = converter.compute_screen_hash(state)
        # Falls back to "unknown/unknown"
        expected = hashlib.sha256("unknown/unknown".encode()).hexdigest()[:SCREEN_HASH_LENGTH]
        assert h == expected


# ===================================================================
# Constants validation
# ===================================================================


class TestConstants:
    def test_timeouts_positive(self):
        assert DEFAULT_CONNECTION_TIMEOUT > 0
        assert WAIT_FOR_IDLE_TIMEOUT > 0
        assert WAIT_FOR_SELECTOR_TIMEOUT > 0

    def test_delays_positive(self):
        assert ACTION_EXECUTION_DELAY > 0
        assert TEXT_INPUT_DELAY > 0
        assert STATE_STABILIZATION_DELAY > 0

    def test_screenshot_quality_in_range(self):
        assert 1 <= SCREENSHOT_QUALITY <= 100

    def test_swipe_duration_ordering(self):
        assert MIN_SWIPE_DURATION < DEFAULT_SWIPE_DURATION < MAX_SWIPE_DURATION

    def test_retry_constants_positive(self):
        assert MAX_RETRY_ATTEMPTS > 0
        assert MAX_CONSECUTIVE_ERRORS > 0

    def test_screen_hash_length_positive(self):
        assert SCREEN_HASH_LENGTH > 0

    def test_default_device_id_format(self):
        assert DEFAULT_DEVICE_ID == "emulator-5554"
