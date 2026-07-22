"""
Pytest configuration for DroidBot parser tests.

This module provides fixtures and setup for testing the DroidBotParser
and its integration with visitors.
"""

import json
import os
from unittest.mock import Mock

import pytest
from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_screen_parser.parser.screen.droidbot.droidbot_parser import DroidBotParser
from rv_screen_parser.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


@pytest.fixture
def parser():
    """Fixture that provides a basic DroidBotParser instance."""
    return DroidBotParser()


@pytest.fixture
def parser_with_basic_visitor():
    """Fixture that provides a DroidBotParser with BasicTextVisitor."""
    return DroidBotParser(BasicTextVisitor)


@pytest.fixture
def mock_visitor():
    """Fixture that provides a mock visitor."""
    mock = Mock()
    mock.get_screen_description.return_value = ScreenDescription(
        "br.unb.cic.cryptoapp.MainActivity", []
    )

    # Add additional required methods for the visitor
    mock.system_navigation_bounds = {}
    mock.device_info = {}

    return mock


@pytest.fixture
def sample_state_file():
    """Fixture that provides the path to a sample DroidBot state file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "fixtures", "001.state")


@pytest.fixture
def sample_state_data(sample_state_file):
    """Fixture that provides the content of the sample DroidBot state file."""
    with open(sample_state_file, "r") as f:
        return json.load(f)


@pytest.fixture
def static_data():
    """Fixture that provides mock static analysis data."""
    classes = Classes()
    windows = Windows()
    wtg = WindowTransitionGraph()
    return StaticAnalysisData(classes, windows, wtg)


@pytest.fixture
def simple_state_data():
    """Fixture that provides a simple state data for testing."""
    return {
        "activity": "com.example.app.MainActivity",
        "view_tree": {
            "package": "com.example.app",
            "class": "android.widget.FrameLayout",
            "bounds": [[0, 0], [1080, 1920]],
            "text": None,
            "resource_id": None,
            "children": [
                {
                    "package": "com.example.app",
                    "class": "android.widget.LinearLayout",
                    "bounds": [[0, 0], [1080, 1800]],
                    "text": None,
                    "resource_id": None,
                    "children": [
                        {
                            "package": "com.example.app",
                            "class": "android.widget.TextView",
                            "bounds": [[100, 100], [500, 200]],
                            "text": "Hello World",
                            "resource_id": "com.example.app:id/text_view",
                            "children": [],
                        },
                        {
                            "package": "com.example.app",
                            "class": "android.widget.Button",
                            "bounds": [[100, 300], [500, 400]],
                            "text": "Click Me",
                            "resource_id": "com.example.app:id/button",
                            "clickable": True,
                            "children": [],
                        },
                    ],
                }
            ],
        },
    }


@pytest.fixture
def crypto_app_state_data(sample_state_data):
    """Fixture that provides the state data for the CryptoApp example with navigation info."""
    # Modify the sample data to include navigation bounds
    sample_state_data["system_navigation_bounds"] = {
        "present": True,
        "top": 1794,
        "left": 0,
        "right": 1080,
        "bottom": 1920,
    }
    sample_state_data["device_info"] = {
        "displayWidth": 1080,
        "displayHeight": 1920,
        "density": 2.0,
        "api_level": 28,
    }
    return sample_state_data
