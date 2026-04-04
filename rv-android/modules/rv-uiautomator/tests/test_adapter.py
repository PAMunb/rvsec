"""
Basic tests for UIAutomator adapter functionality.
"""

from rv_uiautomator.adapter import UIAutomator2Adapter
from rv_uiautomator.executor import UIAutomatorActionExecutor
from rv_uiautomator.state import StateConverter


def test_uiautomator2_adapter_initialization():
    """Test UIAutomator2Adapter initialization."""
    adapter = UIAutomator2Adapter("test-device")
    assert adapter.device_id == "test-device"
    assert not adapter.connected


def test_state_converter_basic():
    """Test StateConverter basic functionality."""
    converter = StateConverter()

    ui_state = {
        "xml": "<hierarchy>test</hierarchy>",
        "current_activity": "com.test/.MainActivity",
        "current_package": "com.test",
        "screenshot_path": "/path/to/screenshot.png",
    }

    result = converter.uiautomator_to_droidbot(ui_state)

    assert result["hierarchy"] == "<hierarchy>test</hierarchy>"
    assert result["activity"] == "com.test/.MainActivity"
    assert result["package_name"] == "com.test"
    assert result["screenshot_path"] == "/path/to/screenshot.png"


def test_action_executor_initialization():
    """Test UIAutomatorActionExecutor initialization."""
    executor = UIAutomatorActionExecutor()
    assert executor is not None
