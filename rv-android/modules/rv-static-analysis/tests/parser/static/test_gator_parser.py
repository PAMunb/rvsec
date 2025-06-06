import json
import os
import sys
from unittest.mock import patch, mock_open

import pytest

# Add the parent directory to the path to make imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from rvandroid.domain.classes import Classes
from rvandroid.domain.window import Windows
from rvandroid.domain.widget import WidgetEventType
from rvandroid.domain.wtg import WindowTransitionGraph
from rvandroid.parser.static.gator_parser import GatorParser, parse_gator_file

# Sample WTG file data for testing
SAMPLE_WTG_DATA = {
    "windows": [
        {"id": 1379, "name": "br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity"},
        {"id": 1382, "name": "br.unb.cic.cryptoapp.generated.CryptographyActivity"},
        {"id": 1395, "name": "br.unb.cic.cryptoapp.MainActivity"}
    ],
    "transitions": [
        {
            "sourceId": 1395,
            "targetId": 1379,
            "events": [
                {
                    "type": "click",
                    "handler": "<br.unb.cic.cryptoapp.MainActivity: void showScreenMessageDigest(android.view.View)>",
                    "widgetId": 2131296359,
                    "widgetClass": "android.widget.Button",
                    "widgetName": "buttonMessageDigest"
                }
            ],
            "callbacks": [
                {
                    "type": "implicit_lifecycle_event",
                    "handler": "<br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity: void onCreate(android.os.Bundle)>",
                    "widgetId": 1379,
                    "widgetClass": "br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity"
                }
            ]
        }
    ]
}


class TestGatorParser:
    """Tests for the GatorParser class."""

    @pytest.fixture
    def parser(self):
        """Initialize a GatorParser instance for testing."""
        return GatorParser()

    @pytest.fixture
    def classes(self):
        """Initialize an empty Classes instance for testing."""
        return Classes()

    @pytest.fixture
    def windows(self):
        """Initialize an empty Windows instance for testing."""
        return Windows()

    @patch("os.path.exists")
    @patch("rvandroid.util.utils.read_json")
    def test_parse_file_success(self, mock_read_json, mock_exists, parser, classes, windows):
        """Test successful parsing of a WTG file."""
        # Setup
        mock_exists.return_value = True
        mock_read_json.return_value = SAMPLE_WTG_DATA

        # Test
        result = parser.parse_file("path/to/wtg.json", "br.unb.cic.cryptoapp", classes, windows)

        # Assertions
        assert isinstance(result, WindowTransitionGraph)
        assert len(windows.windows) == 3  # Three windows defined in sample data

        # Check if windows were parsed correctly
        window_names = [w.name for w in windows.windows]
        assert "br.unb.cic.cryptoapp.MainActivity" in window_names
        assert "br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity" in window_names
        assert "br.unb.cic.cryptoapp.generated.CryptographyActivity" in window_names

        # Check transition graph
        assert len(result.transitions) == 1  # One transition in the sample data

        # Check that the edge exists
        source_window = windows.get_window("br.unb.cic.cryptoapp.MainActivity")
        target_window = windows.get_window("br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity")
        assert source_window is not None
        assert target_window is not None

    @patch("os.path.exists")
    def test_parse_file_nonexistent(self, mock_exists, parser, classes, windows):
        """Test parsing of a nonexistent WTG file."""
        # Setup
        mock_exists.return_value = False

        # Test
        result = parser.parse_file("path/to/nonexistent.json", "br.unb.cic.cryptoapp", classes, windows)

        # Assertions
        assert isinstance(result, WindowTransitionGraph)
        assert len(result.transitions) == 0
        assert len(windows.windows) == 0

    @patch("os.path.exists")
    @patch("rvandroid.util.utils.read_json")
    def test_parse_file_exception(self, mock_read_json, mock_exists, parser, classes, windows):
        """Test handling of exceptions during parsing."""
        # Setup
        mock_exists.return_value = True
        mock_read_json.side_effect = Exception("Test exception")

        # Test
        result = parser.parse_file("path/to/wtg.json", "br.unb.cic.cryptoapp", classes, windows)

        # Assertions
        assert isinstance(result, WindowTransitionGraph)
        assert len(result.transitions) == 0

    def test_process_windows(self, parser, classes, windows):
        """Test processing of window definitions."""
        # Test
        parser.process_windows("br.unb.cic.cryptoapp", classes, windows, SAMPLE_WTG_DATA)

        # Assertions
        assert len(windows.windows) == 3

        # Check that classes were added for windows in the package
        assert len(classes.classes) > 0
        assert "br.unb.cic.cryptoapp.MainActivity" in classes.classes

    def test_process_transitions(self, parser, classes, windows):
        """Test processing of transitions."""
        # Setup - first process windows to have them available
        parser.process_windows("br.unb.cic.cryptoapp", classes, windows, SAMPLE_WTG_DATA)

        # Test
        wtg = parser.process_transitions(windows, SAMPLE_WTG_DATA)

        # Assertions
        assert isinstance(wtg, WindowTransitionGraph)
        assert len(wtg.transitions) == 1

        # Check transition details
        transition = wtg.transitions[0]
        assert transition["source"] == windows.get_window("br.unb.cic.cryptoapp.MainActivity").id
        assert transition["target"] == windows.get_window("br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity").id
        assert transition["widget_id"] == "2131296359"
        assert transition["event_type"] == WidgetEventType.CLICK

    def test_process_transition_events(self, parser, windows):
        """Test processing of events in transitions."""
        # Setup
        source_window = "br.unb.cic.cryptoapp.MainActivity"
        transition_dict = SAMPLE_WTG_DATA["transitions"][0]

        # Prepare windows with required objects
        window = windows.create_new_window(source_window)

        # Test
        events = parser.process_transition_events(source_window, transition_dict, windows)

        # Assertions
        assert len(events) == 1
        assert events[0].widget_id == "2131296359"
        assert events[0].event_type == WidgetEventType.CLICK
        assert events[
                   0].method == "<br.unb.cic.cryptoapp.MainActivity: void showScreenMessageDigest(android.view.View)>"

        # Check that widget was created
        widget = windows.get_widget("2131296359")
        assert widget is not None
        assert widget.name == "buttonMessageDigest"

    def test_create_widget(self, parser):
        """Test widget creation from event data."""
        # Setup
        event_dict = {
            "widgetId": 2131296359,
            "widgetClass": "android.widget.Button",
            "widgetName": "buttonMessageDigest"
        }

        # Test
        widget = parser.create_widget(event_dict)

        # Assertions
        assert widget is not None
        assert widget.id == "2131296359"
        assert widget.name == "buttonMessageDigest"
        assert widget.type.name == "BUTTON"

    def test_create_widget_unsupported_type(self, parser):
        """Test widget creation with unsupported widget type."""
        # Setup
        event_dict = {
            "widgetId": 2131296359,
            "widgetClass": "com.custom.UnsupportedWidget",
            "widgetName": "customWidget"
        }

        # Test
        widget = parser.create_widget(event_dict)

        # Assertions
        assert widget is None

    def test_from_signature(self, parser):
        """Test extraction of class and method names from Soot-style signatures."""
        # Test
        class_name, method_name = parser.from_signature("<com.example.MyClass: void doSomething(int,java.lang.String)>")

        # Assertions
        assert class_name == "com.example.MyClass"
        assert method_name == "doSomething"

    def test_from_signature_invalid(self, parser):
        """Test handling of invalid signatures."""
        # Test
        class_name, method_name = parser.from_signature("invalid signature")

        # Assertions
        assert class_name == ""
        assert method_name == ""

    def test_to_event(self, parser):
        """Test conversion from Gator event strings to WidgetEventType."""
        # Test and assertions
        assert parser.to_event("click") == WidgetEventType.CLICK
        assert parser.to_event("item_click") == WidgetEventType.CLICK
        assert parser.to_event("dialog_positive_button") == WidgetEventType.CLICK

        assert parser.to_event("long_click") == WidgetEventType.LONG_CLICK
        assert parser.to_event("select") == WidgetEventType.SELECTION
        assert parser.to_event("scroll") == WidgetEventType.SCROLL
        assert parser.to_event("drag") == WidgetEventType.DRAG

        # Unsupported event type
        assert parser.to_event("unsupported_event") == WidgetEventType.OTHER

    def test_get_or_create_existing_window(self, parser, windows):
        """Test getting an existing window."""
        # Setup
        window_name = "com.example.TestActivity"
        window_id = "1234"
        existing = windows.create_new_window(window_name, window_id)

        # Test
        result = parser.get_or_create(windows, window_name, window_id)

        # Assertions
        assert result is existing
        assert result.id == window_id

    def test_get_or_create_new_window(self, parser, windows):
        """Test creating a new window."""
        # Setup
        window_name = "com.example.TestActivity"
        window_id = "1234"

        # Test
        result = parser.get_or_create(windows, window_name, window_id)

        # Assertions
        assert result.name == window_name
        assert result.id == window_id
        assert windows.get_window(window_name) is result

    def test_get_or_create_update_window_id(self, parser, windows):
        """Test updating ID of an existing window with no ID."""
        # Setup
        window_name = "com.example.TestActivity"
        window_id = "1234"
        existing = windows.create_new_window(window_name)  # No ID

        # Test
        result = parser.get_or_create(windows, window_name, window_id)

        # Assertions
        assert result is existing
        assert result.id == window_id

    def test_get_or_create_different_id(self, parser, windows):
        """Test handling of a window with a different ID."""
        # Setup
        window_name = "com.example.TestActivity"
        old_id = "1234"
        new_id = "5678"
        existing = windows.create_new_window(window_name, old_id)

        # Test
        result = parser.get_or_create(windows, window_name, new_id)

        # Assertions
        assert result is not existing
        assert result.id == new_id
        assert result.name == window_name

    @patch("os.path.exists")
    @patch("rvandroid.util.utils.read_json")
    def test_parse_gator_file_function(self, mock_read_json, mock_exists, classes, windows):
        """Test the parse_gator_file convenience function."""
        # Setup
        mock_exists.return_value = True
        mock_read_json.return_value = SAMPLE_WTG_DATA

        # Test
        result = parse_gator_file("path/to/wtg.json", "br.unb.cic.cryptoapp", classes, windows)

        # Assertions
        assert isinstance(result, WindowTransitionGraph)
        assert len(windows.windows) == 3
        assert len(result.transitions) == 1

    @patch("os.path.exists")
    @patch("rvandroid.util.utils.read_json")
    def test_full_parse_with_real_data(self, mock_read_json, mock_exists, parser, classes, windows):
        """Test parsing with real WTG data from the provided example."""
        # Setup - load the real data from the test file
        with open('tests/resources/cryptoapp.apk.wtg', 'r') as f:
            real_data = json.load(f)

        mock_exists.return_value = True
        mock_read_json.return_value = real_data

        # Test
        result = parser.parse_file("path/to/wtg.json", "br.unb.cic.cryptoapp", classes, windows)

        # Assertions - focus on key metrics that should be correct
        assert isinstance(result, WindowTransitionGraph)
        assert len(windows.windows) == 6  # 6 windows in the sample
        assert len(result.transitions) > 0  # Should have transitions, exact number depends on parsing logic

        # Verify some key windows are present
        window_names = [w.name for w in windows.windows]
        assert "br.unb.cic.cryptoapp.MainActivity" in window_names
        assert "br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity" in window_names
        assert "br.unb.cic.cryptoapp.cipher.CipherActivity" in window_names
        assert "android.view.Menu" in window_names

        # Verify key widgets are present
        assert len(windows.widgets) > 0
        button_widgets = [w for w in windows.widgets.values() if w.type.name == "BUTTON"]
        assert len(button_widgets) > 0

        # Menu items should be present
        menu_items = [w for w in windows.widgets.values() if w.type.name == "MENU_ITEM"]
        assert len(menu_items) > 0


# Create a mock file for testing with the real data
@pytest.fixture
def setup_mock_wtg_file(monkeypatch):
    """Create a mock WTG file with the real data from the example."""
    # This is the content of the provided WTG file
    wtg_content = """{"windows":[{"id":1379,"name":"br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity"},{"id":1382,"name":"br.unb.cic.cryptoapp.generated.CryptographyActivity"},{"id":1395,"name":"br.unb.cic.cryptoapp.MainActivity"},{"id":1385,"name":"br.unb.cic.cryptoapp.cipher.CipherActivity"},{"id":1388,"name":"android.view.Menu"},{"id":2088,"name":"presto.android.gui.stubs.PrestoFakeLauncherNodeClass"}],"transitions":[{"sourceId":1388,"targetId":1385,"events":[{"type":"click","handler":"<br.unb.cic.cryptoapp.MainActivity: boolean onOptionsItemSelected(android.view.MenuItem)>","widgetId":2131296546,"widgetClass":"android.view.MenuItem","widgetName":"menu_item_cipher"}],"callbacks":[{"type":"implicit_lifecycle_event","handler":"<br.unb.cic.cryptoapp.cipher.CipherActivity: void onCreate(android.os.Bundle)>","widgetId":1385,"widgetClass":"br.unb.cic.cryptoapp.cipher.CipherActivity"}]},{"sourceId":1385,"targetId":1385,"events":[{"type":"implicit_home_event","handler":"","widgetId":1385,"widgetClass":"br.unb.cic.cryptoapp.cipher.CipherActivity"}],"callbacks":[]}]}"""

    # Mock the file opening and reading
    mock_open_file = mock_open(read_data=wtg_content)
    monkeypatch.setattr('builtins.open', mock_open_file)

    # Mock os.path.exists to return True for the test file
    def mock_exists(path):
        if path == 'tests/resources/cryptoapp.apk.wtg':
            return True
        return False

    monkeypatch.setattr('os.path.exists', mock_exists)
    return wtg_content


def test_integration_with_file_mock(setup_mock_wtg_file):
    """Integration test using a mocked file instead of mocking the parser methods."""
    # Setup
    classes = Classes()
    windows = Windows()
    parser = GatorParser()

    # Create the test directory if it doesn't exist
    os.makedirs('tests/resources', exist_ok=True)

    # Test
    result = parser.parse_file('tests/resources/cryptoapp.apk.wtg', "br.unb.cic.cryptoapp", classes, windows)

    # Basic assertions
    assert isinstance(result, WindowTransitionGraph)
    assert len(windows.windows) > 0
