"""
Shared fixtures and configuration for tests.

This conftest.py provides:
- Custom markers registration
- Shared fixtures across test types
- Test configuration
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "smoke: marks tests as smoke tests (fast, basic sanity)")
    config.addinivalue_line("markers", "unit: marks tests as unit tests (isolated, mocked)")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "system: marks tests as system tests (end-to-end)")
    config.addinivalue_line("markers", "performance: marks tests as performance benchmarks")
    config.addinivalue_line("markers", "regression: marks tests as regression tests")
    config.addinivalue_line("markers", "online: marks tests requiring emulator (slow)")
    config.addinivalue_line("markers", "slow: marks tests that take significant time")


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture
def project_root():
    """Project root directory."""
    return Path(__file__).parent.parent.parent


@pytest.fixture
def fixtures_dir(project_root):
    """Test fixtures directory."""
    return project_root / "tests" / "fixtures"


@pytest.fixture
def screenshots_dir(fixtures_dir):
    """Screenshots fixtures directory."""
    return fixtures_dir / "screenshots"


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_package():
    """Test package name."""
    return "com.example.testapp"


@pytest.fixture
def test_device_id():
    """Test device ID."""
    return os.getenv("TEST_DEVICE_ID", "emulator-5554")


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_device():
    """Mock device interface."""
    device = MagicMock()
    device.take_screenshot.return_value = "/tmp/screenshot.png"
    device.get_ui_dump.return_value = "<hierarchy></hierarchy>"
    device.get_screen_size.return_value = (1080, 1920)
    return device


@pytest.fixture
def mock_config():
    """Mock configuration."""
    config = MagicMock()
    config.package_name = "com.example.app"
    config.timeout = 300
    return config


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_ui_element():
    """Sample UI element for testing."""
    return {
        "resource_id": "com.example:id/button",
        "class_name": "android.widget.Button",
        "text": "Click Me",
        "bounds": [100, 200, 300, 250],
        "clickable": True,
    }


@pytest.fixture
def sample_action():
    """Sample action for testing."""
    return {
        "action_type": "CLICK",
        "target": "button_ok",
        "coordinates": (150, 225),
    }
