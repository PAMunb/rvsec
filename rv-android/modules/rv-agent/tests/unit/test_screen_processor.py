"""
Unit tests for ScreenProcessor.

Tests UI element formatting, coordinate transformation, and scored output.
"""

from unittest.mock import MagicMock, patch

import pytest
from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
from rv_agent.services.screen_analyzer import ScreenProcessor
from rv_screen_parser.parser.screen.visitor.model import ItemAction, ScreenDescription


class TestScreenProcessorInit:
    """Test ScreenProcessor initialization."""

    def test_initialization_defaults(self):
        """Processor initializes with default values."""
        device = MagicMock()
        graph = DynamicStateGraph()

        processor = ScreenProcessor(device=device, dynamic_graph=graph)

        assert processor.device is device
        assert processor.dynamic_graph is graph
        assert processor.device_dimensions == (1080, 1920)
        assert processor.max_external_attempts == 3

    def test_initialization_with_custom_dimensions(self):
        """Processor accepts custom device dimensions."""
        device = MagicMock()
        graph = DynamicStateGraph()

        processor = ScreenProcessor(
            device=device, dynamic_graph=graph, device_dimensions=(1440, 2560)
        )

        assert processor.device_dimensions == (1440, 2560)


def _make_interactive_item(
    class_name,
    text="",
    bounds=None,
    resource_id="",
    content_desc="",
    reaches_mop=False,
    directly_reaches_mop=False,
):
    """Helper to create a mock interactive item with actions (required by current format_ui_elements)."""
    item = MagicMock()
    item.view = {
        "class": class_name,
        "text": text,
        "bounds": bounds or [(100, 200), (300, 400)],
        "resource_id": resource_id,
        "content_description": content_desc,
    }

    action = MagicMock(spec=ItemAction)
    action.text = "click"
    action.directly_reaches_mop = directly_reaches_mop
    action.reaches_mop = reaches_mop
    action.event = "click"
    item.actions = [action]

    return item


class TestFormatUIElements:
    """Test format_ui_elements method."""

    @pytest.fixture
    def processor(self):
        device = MagicMock()
        graph = DynamicStateGraph()
        return ScreenProcessor(device=device, dynamic_graph=graph)

    def test_no_elements_returns_message(self, processor):
        """Empty screen returns 'no interactive elements'."""
        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []

        result = processor.format_ui_elements(screen_desc)

        assert result == "No interactive elements found."

    def test_none_screen_desc(self, processor):
        """None screen description returns 'no interactive elements'."""
        result = processor.format_ui_elements(None)

        assert result == "No interactive elements found."

    def test_non_interactive_elements_filtered(self, processor):
        """Items without actions are filtered out."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            "class": "android.widget.TextView",
            "clickable": False,
            "bounds": [(100, 200), (300, 400)],
        }
        item.actions = []  # No actions = not interactive
        screen_desc.items = [item]

        result = processor.format_ui_elements(screen_desc)

        assert result == "No interactive elements found."

    def test_edittext_included_with_type(self, processor):
        """EditText elements are included with type name in output."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = _make_interactive_item(
            "android.widget.EditText",
            text="Email",
            resource_id="com.example/email_input",
        )
        screen_desc.items = [item]

        result = processor.format_ui_elements(screen_desc)

        assert "EditText" in result
        assert "'Email'" in result
        assert "score:" in result

    def test_spinner_included_with_type(self, processor):
        """Spinner elements are included with type name in output."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = _make_interactive_item(
            "android.widget.Spinner",
            text="Select country",
            resource_id="com.example/country_spinner",
        )
        screen_desc.items = [item]

        result = processor.format_ui_elements(screen_desc)

        assert "Spinner" in result
        assert "'Select country'" in result
        assert "score:" in result

    def test_button_included_with_type(self, processor):
        """Button elements are included with type name in output."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = _make_interactive_item(
            "android.widget.Button",
            text="Submit",
            resource_id="com.example/submit_button",
        )
        screen_desc.items = [item]

        result = processor.format_ui_elements(screen_desc)

        assert "Button" in result
        assert "'Submit'" in result
        assert "score:" in result

    def test_mixed_elements_formatted(self, processor):
        """Mixed elements are formatted with scores and sorted."""
        screen_desc = MagicMock(spec=ScreenDescription)

        edittext_item = _make_interactive_item(
            "android.widget.EditText", bounds=[(100, 200), (300, 400)]
        )

        spinner_item = _make_interactive_item(
            "android.widget.Spinner", bounds=[(100, 500), (300, 600)]
        )

        button_item = _make_interactive_item(
            "android.widget.Button", text="OK", bounds=[(100, 700), (300, 800)]
        )

        screen_desc.items = [edittext_item, spinner_item, button_item]

        result = processor.format_ui_elements(screen_desc)

        # All elements should be present with scored format
        assert "EditText" in result
        assert "Spinner" in result
        assert "Button" in result
        assert "score:" in result
        assert "position" in result


class TestProcessElement:
    """Test _process_element method."""

    @pytest.fixture
    def processor(self):
        device = MagicMock()
        graph = DynamicStateGraph()
        return ScreenProcessor(device=device, dynamic_graph=graph)

    def test_process_basic_element(self, processor):
        """Process basic element returns dict with expected keys."""
        item = _make_interactive_item(
            "android.widget.Button",
            text="Submit",
            resource_id="com.example/submit_btn",
            bounds=[(100, 200), (300, 400)],
        )

        result = processor._process_element(item, "screen_hash")

        assert result is not None
        assert "Button" in result["description"]
        assert "'Submit'" in result["description"]
        assert result["tag"] == "[UNTESTED]"
        assert result["score"] == 200  # Base score for untested
        assert "x" in result
        assert "y" in result

    def test_process_element_invalid_bounds(self, processor):
        """Element with invalid bounds returns None."""
        item = MagicMock()
        item.view = {"class": "android.widget.Button", "text": "Submit", "bounds": None}
        item.actions = [MagicMock()]

        result = processor._process_element(item, "screen_hash")

        assert result is None

    def test_process_element_incomplete_bounds(self, processor):
        """Element with incomplete bounds returns None."""
        item = MagicMock()
        item.view = {
            "class": "android.widget.Button",
            "text": "Submit",
            "bounds": [(100, 200)],  # Missing second point
        }
        item.actions = [MagicMock()]

        result = processor._process_element(item, "screen_hash")

        assert result is None

    def test_process_element_with_mop_direct(self, processor):
        """Element with direct MOP marker gets [DM] and bonus score."""
        item = _make_interactive_item(
            "android.widget.Button", text="Encrypt", directly_reaches_mop=True
        )

        result = processor._process_element(item, "screen_hash")

        assert result is not None
        assert "[DM]" in result["description"]
        assert result["score"] == 300  # 200 base + 100 DM bonus

    def test_process_element_with_mop_transitive(self, processor):
        """Element with transitive MOP marker gets [M] and bonus score."""
        item = _make_interactive_item(
            "android.widget.Button", text="Settings", reaches_mop=True
        )

        result = processor._process_element(item, "screen_hash")

        assert result is not None
        assert "[M]" in result["description"]
        assert result["score"] == 250  # 200 base + 50 M bonus

    def test_process_element_with_mop_both(self, processor):
        """Element with both MOP flags prioritizes [DM]."""
        item = _make_interactive_item(
            "android.widget.Button",
            text="Submit",
            directly_reaches_mop=True,
            reaches_mop=True,
        )

        result = processor._process_element(item, "screen_hash")

        assert result is not None
        assert "Button" in result["description"]
        assert "'Submit'" in result["description"]
        assert "[DM]" in result["description"]
        assert result["score"] == 300  # 200 base + 100 DM bonus (DM takes precedence)


class TestRestartApp:
    """Test _restart_app method."""

    def test_restart_app_calls_device_methods(self):
        """Restart app calls stop and start."""
        device = MagicMock()
        graph = DynamicStateGraph()
        processor = ScreenProcessor(device=device, dynamic_graph=graph)

        with patch("time.sleep"):
            processor._restart_app("com.example.app")

        device.stop_app.assert_called_once_with("com.example.app")
        device.start_app.assert_called_once_with("com.example.app")


class TestParseCurrentScreen:
    """Test parse_current_screen method."""

    def test_parse_basic(self):
        """Basic parse returns expected structure."""
        device = MagicMock()
        device.get_current_ui_state.return_value = {
            "xml": "<hierarchy></hierarchy>",
            "current_activity": "com.example/.MainActivity",
            "current_package": "com.example",
        }
        graph = DynamicStateGraph()

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "MainActivity"

        with patch("rv_agent.services.screen_analyzer.ParserFactory") as mock_factory:
            mock_parser = MagicMock()
            mock_parser.parse_screen.return_value = screen_desc
            mock_factory.create.return_value = mock_parser

            processor = ScreenProcessor(device=device, dynamic_graph=graph)
            result = processor.parse_current_screen(
                target_package="com.example", external_navigation_count=0
            )

        assert "screen_hash" in result
        assert "activity" in result
        assert "screen_description" in result
        assert result["is_external"] is False
        assert result["restart_occurred"] is False

    def test_parse_external_navigation(self):
        """Parse detects external navigation."""
        device = MagicMock()
        device.get_current_ui_state.return_value = {
            "xml": "<hierarchy></hierarchy>",
            "current_activity": "com.google/.SearchActivity",
            "current_package": "com.google",
        }
        graph = DynamicStateGraph()

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "SearchActivity"

        with patch("rv_agent.services.screen_analyzer.ParserFactory") as mock_factory:
            mock_parser = MagicMock()
            mock_parser.parse_screen.return_value = screen_desc
            mock_factory.create.return_value = mock_parser

            processor = ScreenProcessor(device=device, dynamic_graph=graph)
            result = processor.parse_current_screen(
                target_package="com.example", external_navigation_count=0
            )

        assert result["is_external"] is True
        assert result["external_navigation_count"] == 1

    def test_parse_restart_after_max_external(self):
        """Parse restarts app after max external attempts."""
        device = MagicMock()
        # First call returns external, second returns target
        device.get_current_ui_state.side_effect = [
            {
                "xml": "<hierarchy></hierarchy>",
                "current_activity": "com.google/.SearchActivity",
                "current_package": "com.google",
            },
            {
                "xml": "<hierarchy></hierarchy>",
                "current_activity": "com.example/.MainActivity",
                "current_package": "com.example",
            },
        ]
        graph = DynamicStateGraph()

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "MainActivity"

        with patch("rv_agent.services.screen_analyzer.ParserFactory") as mock_factory:
            mock_parser = MagicMock()
            mock_parser.parse_screen.return_value = screen_desc
            mock_factory.create.return_value = mock_parser

            with patch("time.sleep"):
                processor = ScreenProcessor(device=device, dynamic_graph=graph)
                result = processor.parse_current_screen(
                    target_package="com.example", external_navigation_count=3  # At max
                )

        assert result["restart_occurred"] is True
        device.stop_app.assert_called_once()
        device.start_app.assert_called_once()

    def test_parse_reset_counter_on_return(self):
        """Counter resets when returning to target app."""
        device = MagicMock()
        device.get_current_ui_state.return_value = {
            "xml": "<hierarchy></hierarchy>",
            "current_activity": "com.example/.MainActivity",
            "current_package": "com.example",
        }
        graph = DynamicStateGraph()

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "MainActivity"

        with patch("rv_agent.services.screen_analyzer.ParserFactory") as mock_factory:
            mock_parser = MagicMock()
            mock_parser.parse_screen.return_value = screen_desc
            mock_factory.create.return_value = mock_parser

            processor = ScreenProcessor(device=device, dynamic_graph=graph)
            result = processor.parse_current_screen(
                target_package="com.example",
                external_navigation_count=2,  # Was external
            )

        assert result["external_navigation_count"] == 0

    def test_parse_with_ui_coverage(self):
        """Parse generates ui_elements_text using format_ui_elements (coverage integrated)."""
        device = MagicMock()
        device.get_current_ui_state.return_value = {
            "xml": "<hierarchy></hierarchy>",
            "current_activity": "com.example/.MainActivity",
            "current_package": "com.example",
        }
        graph = DynamicStateGraph()

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = "MainActivity"

        ui_coverage = MagicMock()

        with patch("rv_agent.services.screen_analyzer.ParserFactory") as mock_factory:
            mock_parser = MagicMock()
            mock_parser.parse_screen.return_value = screen_desc
            mock_factory.create.return_value = mock_parser

            processor = ScreenProcessor(
                device=device, dynamic_graph=graph, ui_coverage=ui_coverage
            )
            result = processor.parse_current_screen(
                target_package="com.example", external_navigation_count=0
            )

        # ui_elements_text is generated via format_ui_elements (not annotate_screen_elements)
        assert "ui_elements_text" in result
        # With empty items, it should be the "no interactive elements" message
        assert result["ui_elements_text"] == "No interactive elements found."
