import json
import os
import sys
from unittest.mock import patch, mock_open

import pytest

# Add the parent directory to the path to make imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from rv_android_core.domain.classes import Classes
from rv_android_core.domain.window import Windows, WindowType
from rv_android_core.domain.widget import WidgetEventType, Widget
from rv_static_analysis.parser.static.gesda_parser import GesdaParser

# Sample GESDA data for testing
SAMPLE_GESDA_DATA = {
    "fileName": "cryptoapp.apk",
    "packageName": "br.unb.cic.cryptoapp",
    "windows": [
        {
            "id": 2,
            "name": "br.unb.cic.cryptoapp.MainActivity",
            "isMain": True,
            "layoutFileName": "activity_main",
            "type": "ACT",
            "widgets": [
                {
                    "widgetId": "2131296356",
                    "type": "BUTTON",
                    "name": "buttonCipher",
                    "listeners": [
                        {
                            "type": "OnClickListener",
                            "callbackMethod": {
                                "name": "showScreenCipher",
                                "className": "br.unb.cic.cryptoapp.MainActivity",
                                "signature": "<br.unb.cic.cryptoapp.MainActivity: void showScreenCipher(android.view.View)>",
                                "modifiers": 1
                            },
                            "registeredInFile": True
                        }
                    ],
                    "text": "Cipher"
                }
            ]
        }
    ]
}


class TestGesdaParser:
    """Tests for the GesdaParser class."""

    @pytest.fixture
    def parser(self):
        """Initialize a GesdaParser instance for testing."""
        return GesdaParser()

    @pytest.fixture
    def classes(self):
        """Initialize an empty Classes instance for testing."""
        return Classes()

    @pytest.fixture
    def windows(self):
        """Initialize an empty Windows instance for testing."""
        return Windows()

    @patch("os.path.exists")
    @patch("rv_android_core.util.utils.read_json")
    def test_parse_file_success(self, mock_read_json, mock_exists, parser, classes, windows):
        """Test successful parsing of a GESDA file."""
        # Setup
        mock_exists.return_value = True
        mock_read_json.return_value = SAMPLE_GESDA_DATA

        # Test
        result = parser.parse_file("path/to/gesda.json", "br.unb.cic.cryptoapp", classes, windows)

        # Assertions
        # The parser returns a new Windows instance, not the one passed in
        assert isinstance(result, Windows)
        assert len(result.windows) == 1  # One window defined in sample data

        # Check if the window was parsed correctly
        window_list = list(result.windows)
        assert len(window_list) > 0
        window = window_list[0]
        assert window.name == "br.unb.cic.cryptoapp.MainActivity"
        assert window.type == WindowType.ACTIVITY

        # Check if widget was parsed correctly
        assert len(window.widgets) == 1
        widget_values = list(window.widgets.values())
        assert len(widget_values) > 0
        widget = widget_values[0]
        assert widget.name == "buttonCipher"
        assert widget.text == "Cipher"

    @patch("os.path.exists")
    def test_parse_file_nonexistent(self, mock_exists, parser, classes, windows):
        """Test parsing of a nonexistent GESDA file."""
        # Setup
        mock_exists.return_value = False

        # Test
        result = parser.parse_file("path/to/nonexistent.json", "br.unb.cic.cryptoapp", classes, windows)

        # Assertions
        assert isinstance(result, Windows)
        assert len(result.windows) == 0
        assert len(windows.windows) == 0

    # @patch("os.path.exists")
    # @patch("rvandroid.util.utils.read_json")
    # def test_parse_file_exception(self, mock_read_json, mock_exists, parser, classes, windows):
    #     """Test handling of exceptions during parsing."""
    #     # Setup
    #     mock_exists.return_value = True
    #     mock_read_json.side_effect = Exception("Test exception")
    #
    #     # Test
    #     result = parser.parse_file("path/to/gesda.json", "br.unb.cic.cryptoapp", classes, windows)
    #
    #     # Assertions
    #     assert result is windows
    #     assert len(windows.windows) == 0

    def test_process_window(self, parser, classes, windows):
        """Test processing of a single window entry."""
        # Setup
        window_dict = SAMPLE_GESDA_DATA["windows"][0]

        # Test
        parser.process_window(window_dict, "br.unb.cic.cryptoapp", classes, windows)

        # Assertions
        assert len(windows.windows) == 1
        window = next(iter(windows.windows))
        assert window.name == "br.unb.cic.cryptoapp.MainActivity"

        # Check that class was added
        assert "br.unb.cic.cryptoapp.MainActivity" in classes.classes
        assert classes.classes["br.unb.cic.cryptoapp.MainActivity"].is_main_activity

    def test_process_window_not_in_package(self, parser, classes, windows):
        """Test processing of a window not in the specified package."""
        # Setup
        window_dict = SAMPLE_GESDA_DATA["windows"][0]

        # Test
        parser.process_window(window_dict, "com.other.package", classes, windows)

        # Assertions
        assert len(windows.windows) == 0  # Window should be skipped

    def test_create_window(self, parser, windows):
        """Test window creation from GESDA window data."""
        # Setup
        window_dict = {
            "name": "br.unb.cic.cryptoapp.TestActivity",
            "type": "ACT",
            "layoutFileName": "activity_test",
            "isMain": True
        }

        # Test
        window = parser.create_window(window_dict, windows)

        # Assertions
        assert window.name == "br.unb.cic.cryptoapp.TestActivity"
        assert window.type == WindowType.ACTIVITY
        assert window.layout_file == "activity_test"
        assert window.activity == "br.unb.cic.cryptoapp.TestActivity"
        assert window.class_name == "br.unb.cic.cryptoapp.TestActivity"

    def test_create_window_existing(self, parser, windows):
        """Test creation of an already existing window."""
        # Setup
        existing = windows.create_new_window("br.unb.cic.cryptoapp.TestActivity")

        window_dict = {
            "name": "br.unb.cic.cryptoapp.TestActivity",
            "type": "ACT",
            "layoutFileName": "activity_test",
            "isMain": False
        }

        # Test
        window = parser.create_window(window_dict, windows)

        # Assertions
        assert window is existing  # Should return the existing window
        assert window.layout_file == "activity_test"  # Should update properties

    def test_parse_widgets(self, parser, windows):
        """Test parsing of widget entries from GESDA data."""
        # Setup
        widgets_list = SAMPLE_GESDA_DATA["windows"][0]["widgets"]
        window = windows.create_new_window("br.unb.cic.cryptoapp.MainActivity")

        # Test
        result = parser.parse_widgets(widgets_list, window, windows)

        # Assertions
        assert len(result) == 1
        widget = result[0]
        assert widget.name == "buttonCipher"
        assert widget.text == "Cipher"

        # Check events are parsed
        assert len(widget.events) == 1
        event = next(iter(widget.events))
        assert event.type == WidgetEventType.CLICK
        assert event.method == "showScreenCipher"

    def test_get_or_create_widget_new(self, parser, windows):
        """Test creation of a new widget."""
        # Setup
        widget_dict = {
            "widgetId": "2131296356",
            "type": "BUTTON",
            "name": "buttonCipher",
            "text": "Cipher"
        }
        window = windows.create_new_window("br.unb.cic.cryptoapp.MainActivity")

        # Test
        widget = parser.get_or_create_widget(widget_dict, window, windows)

        # Assertions
        assert widget.id == "2131296356"
        assert widget.name == "buttonCipher"
        assert widget.text == "Cipher"
        assert widget.type.name == "BUTTON"

    def test_get_or_create_widget_existing(self, parser, windows):
        """Test getting an existing widget."""
        # Setup
        window = windows.create_new_window("br.unb.cic.cryptoapp.MainActivity")
        # Create the widget - need to use WidgetType enum, not string
        from rv_android_core.domain.widget import WidgetType
        existing = Widget("2131296356", "buttonCipher", WidgetType.BUTTON)
        windows.add_widget(window, existing)

        widget_dict = {
            "widgetId": "2131296356",
            "type": "BUTTON",
            "name": "buttonCipher",
            "text": "Updated Text",
            "hint": "Enter text..."
        }

        # Test
        widget = parser.get_or_create_widget(widget_dict, window, windows)

        # Assertions
        assert widget is existing  # Should return the existing widget
        assert widget.text == "Updated Text"  # Should update properties
        assert widget.hint == "Enter text..."

    def test_parse_listeners(self, parser):
        """Test parsing of event entries from GESDA widget data."""
        # Setup
        events_list = [
            {
                "type": "OnClickListener",
                "callbackMethod": {
                    "name": "showScreenCipher",
                    "className": "br.unb.cic.cryptoapp.MainActivity",
                    "signature": "<br.unb.cic.cryptoapp.MainActivity: void showScreenCipher(android.view.View)>"
                }
            }
        ]

        # Test
        events = parser.parse_listeners(events_list)

        # Assertions
        assert len(events) == 1
        event = next(iter(events))
        assert event.type == WidgetEventType.CLICK
        assert event.clazz == "br.unb.cic.cryptoapp.MainActivity"
        assert event.method == "showScreenCipher"

    def test_parse_listeners_multiple_types(self, parser):
        """Test parsing of different event types."""
        # Setup
        events_list = [
            {
                "type": "OnClickListener",
                "callbackMethod": {
                    "name": "onClick",
                    "className": "TestClass",
                    "signature": "<TestClass: void onClick(android.view.View)>"
                }
            },
            {
                "type": "OnLongClickListener",
                "callbackMethod": {
                    "name": "onLongClick",
                    "className": "TestClass",
                    "signature": "<TestClass: boolean onLongClick(android.view.View)>"
                }
            },
            {
                "type": "OnItemSelectedListener",
                "callbackMethod": {
                    "name": "onItemSelected",
                    "className": "TestClass",
                    "signature": "<TestClass: void onItemSelected(android.widget.AdapterView,android.view.View,int,long)>"
                }
            },
            {
                "type": "UnsupportedListener",
                "callbackMethod": {
                    "name": "onUnsupported",
                    "className": "TestClass",
                    "signature": "<TestClass: void onUnsupported()>"
                }
            }
        ]

        # Test
        events = parser.parse_listeners(events_list)

        # Assertions
        assert len(events) == 3  # Should skip the unsupported listener
        event_types = {event.type for event in events}
        assert WidgetEventType.CLICK in event_types
        assert WidgetEventType.LONG_CLICK in event_types
        assert WidgetEventType.SELECTION in event_types

    def test_to_event(self, parser):
        """Test conversion from GESDA listener type strings to WidgetEventType."""
        # Test various event types
        assert parser.to_event("OnClickListener") == WidgetEventType.CLICK
        assert parser.to_event("OnMenuItemClickListener") == WidgetEventType.CLICK
        assert parser.to_event("OnLongClickListener") == WidgetEventType.LONG_CLICK
        assert parser.to_event("OnItemSelectedListener") == WidgetEventType.SELECTION
        assert parser.to_event("OnScrollListener") == WidgetEventType.SCROLL
        assert parser.to_event("OnGestureListener") == WidgetEventType.GESTURE
        assert parser.to_event("OnDragListener") == WidgetEventType.DRAG
        assert parser.to_event("OnHoverListener") == WidgetEventType.HOVER
        assert parser.to_event("OnTouchListener") == WidgetEventType.TOUCH
        assert parser.to_event("OnFocusChangeListener") == WidgetEventType.FOCUS
        assert parser.to_event("OnKeyListener") == WidgetEventType.KEY

        # Unsupported event type
        assert parser.to_event("UnsupportedListener") == WidgetEventType.OTHER

    # @patch("os.path.exists")
    # @patch("rvandroid.util.utils.read_json")
    # @patch("rvandroid.parser.static.gesda_parser.GesdaParser.parse_file")
    # def test_parse_gesda_file_function(self, mock_parse_file, mock_read_json, mock_exists, classes, windows):
    #     """Test the parse_gesda_file convenience function."""
    #     # Setup
    #     mock_exists.return_value = True
    #     mock_read_json.return_value = SAMPLE_GESDA_DATA
    #
    #     # Create a mock Windows object to return from the mocked parse_file method
    #     mock_result = Windows()
    #     window = mock_result.create_new_window("br.unb.cic.cryptoapp.MainActivity")
    #     mock_parse_file.return_value = mock_result
    #
    #     # Test
    #     result_windows = parse_gesda_file("path/to/gesda.json", "br.unb.cic.cryptoapp", classes, windows)
    #
    #     # Assertions
    #     assert mock_parse_file.called
    #     assert isinstance(result_windows, Windows)
    #     assert result_windows is mock_result  # Should return the Windows object from parse_file
    #     window = next(iter(windows.windows))
    #     assert window.name == "br.unb.cic.cryptoapp.MainActivity"

    @patch("os.path.exists")
    @patch("rv_android_core.util.utils.read_json")
    def test_full_parse_with_real_data(self, mock_read_json, mock_exists, parser, classes, windows):
        """Test parsing with real GESDA data from the provided example."""
        # Setup - load the real data from the test file
        with open('tests/resources/cryptoapp.apk.gesda', 'r') as f:
            real_data = json.load(f)

        mock_exists.return_value = True
        mock_read_json.return_value = real_data

        # Test
        result = parser.parse_file("path/to/gesda.json", "br.unb.cic.cryptoapp", classes, windows)

        # Assertions
        assert isinstance(result, Windows)
        assert len(result.windows) > 0  # Should have windows

        # Verify all expected windows are present
        window_names = [w.name for w in result.windows]
        assert "br.unb.cic.cryptoapp.MainActivity" in window_names
        assert "br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity" in window_names
        assert "br.unb.cic.cryptoapp.cipher.CipherActivity" in window_names
        assert "br.unb.cic.cryptoapp.generated.CryptographyActivity" in window_names

        # Verify main activity is correctly identified
        main_activity = None
        for class_name, clazz in classes.classes.items():
            if clazz.is_main_activity:
                main_activity = class_name
                break
        assert main_activity == "br.unb.cic.cryptoapp.MainActivity"

        # Verify widgets in one of the windows
        main_window = result.get_window("br.unb.cic.cryptoapp.MainActivity")
        assert main_window is not None
        assert len(main_window.widgets) == 3  # Number of widgets in MainActivity

        # Check specific widget properties
        button_cipher = main_window.get_widget_by_name("buttonCipher")
        assert button_cipher is not None
        assert button_cipher.text == "Cipher"
        assert len(button_cipher.events) == 1

        # Check event properties
        event = next(iter(button_cipher.events))
        assert event.type == WidgetEventType.CLICK
        assert event.method == "showScreenCipher"

        # Check all widgets
        all_widgets = result.widgets
        assert len(all_widgets) > 20  # Total number of widgets across all windows


# Create a mock file for testing with the real data
@pytest.fixture
def setup_mock_gesda_file(monkeypatch):
    """Create a mock GESDA file with the real data from the example."""
    # This is the content of the provided GESDA file (truncated for clarity)
    gesda_content = """{"fileName":"cryptoapp.apk","packageName":"br.unb.cic.cryptoapp","windows":[{"id":1,"name":"br.unb.cic.cryptoapp.cipher.CipherActivity","isMain":false,"layoutFileName":"activity_cipher","type":"ACT","widgets":[{"widgetId":"2131296441","type":"EDIT_TEXT","name":"editTextCipherEncrypt","field":"<br.unb.cic.cryptoapp.cipher.CipherActivity: android.widget.EditText editTextEncrypt>","hint":"Input text ...","inputType":"textPersonName"},{"widgetId":"2131296381","type":"TEXT_VIEW","name":"cipherTextView"}]}]}"""

    # Mock the file opening and reading
    mock_open_file = mock_open(read_data=gesda_content)
    monkeypatch.setattr('builtins.open', mock_open_file)

    # Mock os.path.exists to return True for the test file
    def mock_exists(path):
        if path == 'tests/resources/cryptoapp.apk.gesda':
            return True
        return False

    monkeypatch.setattr('os.path.exists', mock_exists)
    return gesda_content


def test_integration_with_file_mock(setup_mock_gesda_file):
    """Integration test using a mocked file instead of mocking the parser methods."""
    # Setup
    classes = Classes()
    windows = Windows()
    parser = GesdaParser()

    # Create the test directory if it doesn't exist
    os.makedirs('tests/resources', exist_ok=True)

    # Test
    result = parser.parse_file('tests/resources/cryptoapp.apk.gesda', "br.unb.cic.cryptoapp", classes, windows)

    # Basic assertions
    assert isinstance(result, Windows)
    assert len(result.windows) > 0

    # Check that we parsed the expected window
    window = result.get_window("br.unb.cic.cryptoapp.cipher.CipherActivity")
    assert window is not None

    # Check that widgets were parsed
    assert len(window.widgets) > 0

    # Verify a specific widget property
    edit_text = window.get_widget_by_name("editTextCipherEncrypt")
    assert edit_text is not None
    assert edit_text.hint == "Input text ..."
