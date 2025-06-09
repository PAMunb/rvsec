"""
Pytest configuration for UIAutomator parser tests.

This module provides fixtures and setup for testing the UIAutomator2Parser
and its integration with visitors.
"""

import os
from unittest.mock import Mock

import pytest

from rv_android_core.domain.classes import Classes
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


@pytest.fixture
def parser():
    """Fixture that provides a basic UIAutomator2Parser instance."""
    return UIAutomator2Parser()


@pytest.fixture
def parser_with_basic_visitor():
    """Fixture that provides a UIAutomator2Parser with BasicTextVisitor."""
    return UIAutomator2Parser(BasicTextVisitor)


@pytest.fixture
def mock_visitor():
    """Fixture that provides a mock visitor."""
    mock = Mock()
    mock.get_screen_description.return_value = ScreenDescription("TestActivity", [])

    # Add additional required methods for the visitor
    mock.system_navigation_bounds = {}
    mock.device_info = {}

    return mock


@pytest.fixture
def sample_xml_file():
    """Fixture that provides the path to a sample UIAutomator XML file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, "fixtures", "001.uiautomator")


@pytest.fixture
def sample_xml_content(sample_xml_file):
    """Fixture that provides the content of the sample UIAutomator XML file."""
    with open(sample_xml_file, 'r', encoding='utf-8') as f:
        return f.read()


@pytest.fixture
def static_data():
    """Fixture that provides mock static analysis data."""
    classes = Classes()
    windows = Windows()
    wtg = WindowTransitionGraph()
    return StaticAnalysisData(classes, windows, wtg)


@pytest.fixture
def simple_xml():
    """Fixture that provides a simple XML hierarchy for testing."""
    return """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
    <hierarchy rotation="0">
      <node index="0" text="" resource-id="" class="android.widget.FrameLayout" 
            package="com.example.app" content-desc="" checkable="false" 
            checked="false" clickable="false" enabled="true" 
            bounds="[0,0][1080,1920]">
        <node index="0" text="Hello World" resource-id="com.example.app:id/text_view" 
              class="android.widget.TextView" clickable="false" 
              bounds="[100,100][500,200]" />
        <node index="1" text="Click Me" resource-id="com.example.app:id/button" 
              class="android.widget.Button" clickable="true" 
              bounds="[100,300][500,400]" />
      </node>
    </hierarchy>
    """


@pytest.fixture
def crypto_app_state_data(sample_xml_content):
    """Fixture that provides the state data for the CryptoApp example."""
    return {
        "hierarchy": sample_xml_content,
        "activity": "br.unb.cic.cryptoapp.MainActivity",
        "system_navigation_bounds": {
            "present": True,
            "top": 1794,
            "left": 0,
            "right": 1080,
            "bottom": 1920
        },
        "device_info": {
            "displayWidth": 1080,
            "displayHeight": 1920,
            "density": 2.0,
            "api_level": 28
        }
    }
