"""
Unit tests for ScreenProcessor.

Tests UI element formatting, coordinate transformation, and categorization.
"""

import pytest
from unittest.mock import MagicMock, patch
import time

from rv_agent.ui.screen_processor import ScreenProcessor
from rv_agent.core.dynamic_state_graph import DynamicStateGraph
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ItemAction


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
        assert processor.optimized_dimensions == (704, 1248)
        assert processor.max_external_attempts == 3

    def test_initialization_with_custom_dimensions(self):
        """Processor accepts custom dimensions."""
        device = MagicMock()
        graph = DynamicStateGraph()

        processor = ScreenProcessor(
            device=device,
            dynamic_graph=graph,
            device_dimensions=(1440, 2560),
            optimized_dimensions=(540, 960)
        )

        assert processor.device_dimensions == (1440, 2560)
        assert processor.optimized_dimensions == (540, 960)


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

    def test_non_clickable_elements_filtered(self, processor):
        """Non-clickable elements are filtered out."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.TextView',
            'clickable': False,
            'bounds': [(100, 200), (300, 400)]
        }
        screen_desc.items = [item]

        result = processor.format_ui_elements(screen_desc)

        assert result == "No interactive elements found."

    def test_edittext_categorized(self, processor):
        """EditText elements are categorized as text inputs."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'clickable': True,
            'bounds': [(100, 200), (300, 400)],
            'text': 'Email',
            'resource_id': 'com.example/email_input'
        }
        item.actions = []
        screen_desc.items = [item]

        result = processor.format_ui_elements(screen_desc)

        assert "TEXT INPUT FIELDS" in result
        assert "TEXT INPUT" in result
        assert "EditText" in result

    def test_spinner_categorized(self, processor):
        """Spinner elements are categorized as dropdowns."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.Spinner',
            'clickable': True,
            'bounds': [(100, 200), (300, 400)],
            'text': 'Select country',
            'resource_id': 'com.example/country_spinner'
        }
        item.actions = []
        screen_desc.items = [item]

        result = processor.format_ui_elements(screen_desc)

        assert "DROPDOWN SELECTORS" in result
        assert "DROPDOWN" in result
        assert "Spinner" in result

    def test_button_categorized_as_clickable(self, processor):
        """Button elements are categorized as clickable."""
        screen_desc = MagicMock(spec=ScreenDescription)

        item = MagicMock()
        item.view = {
            'class': 'android.widget.Button',
            'clickable': True,
            'bounds': [(100, 200), (300, 400)],
            'text': 'Submit',
            'resource_id': 'com.example/submit_button'
        }
        item.actions = []
        screen_desc.items = [item]

        result = processor.format_ui_elements(screen_desc)

        assert "CLICKABLE ELEMENTS" in result
        assert "Button" in result
        assert "'Submit'" in result

    def test_mixed_elements_categorized(self, processor):
        """Mixed elements are properly categorized."""
        screen_desc = MagicMock(spec=ScreenDescription)

        edittext_item = MagicMock()
        edittext_item.view = {
            'class': 'android.widget.EditText',
            'clickable': True,
            'bounds': [(100, 200), (300, 400)],
            'text': '',
            'resource_id': ''
        }
        edittext_item.actions = []

        spinner_item = MagicMock()
        spinner_item.view = {
            'class': 'android.widget.Spinner',
            'clickable': True,
            'bounds': [(100, 500), (300, 600)],
            'text': '',
            'resource_id': ''
        }
        spinner_item.actions = []

        button_item = MagicMock()
        button_item.view = {
            'class': 'android.widget.Button',
            'clickable': True,
            'bounds': [(100, 700), (300, 800)],
            'text': 'OK',
            'resource_id': ''
        }
        button_item.actions = []

        screen_desc.items = [edittext_item, spinner_item, button_item]

        result = processor.format_ui_elements(screen_desc)

        assert "TEXT INPUT FIELDS" in result
        assert "DROPDOWN SELECTORS" in result
        assert "CLICKABLE ELEMENTS" in result


class TestFormatElement:
    """Test _format_element method."""

    @pytest.fixture
    def processor(self):
        device = MagicMock()
        graph = DynamicStateGraph()
        return ScreenProcessor(device=device, dynamic_graph=graph)

    def test_format_basic_element(self, processor):
        """Format basic element with text and resource_id."""
        item = MagicMock()
        item.view = {
            'class': 'android.widget.Button',
            'text': 'Submit',
            'resource_id': 'com.example/submit_btn',
            'bounds': [(100, 200), (300, 400)]
        }
        item.actions = []

        result = processor._format_element(1, item, None)

        assert "1." in result
        assert "Button" in result
        assert "'Submit'" in result
        assert "(submit_btn)" in result
        assert "position" in result

    def test_format_element_with_category_label(self, processor):
        """Format element with category label."""
        item = MagicMock()
        item.view = {
            'class': 'android.widget.EditText',
            'text': '',
            'resource_id': 'email',
            'bounds': [(100, 200), (300, 400)]
        }
        item.actions = []

        result = processor._format_element(1, item, "TEXT INPUT")

        assert "[TEXT INPUT]" in result
        assert "EditText" in result

    def test_format_element_invalid_bounds(self, processor):
        """Element with invalid bounds returns empty string."""
        item = MagicMock()
        item.view = {
            'class': 'android.widget.Button',
            'text': 'Submit',
            'bounds': None
        }

        result = processor._format_element(1, item, None)

        assert result == ""

    def test_format_element_incomplete_bounds(self, processor):
        """Element with incomplete bounds returns empty string."""
        item = MagicMock()
        item.view = {
            'class': 'android.widget.Button',
            'text': 'Submit',
            'bounds': [(100, 200)]  # Missing second point
        }

        result = processor._format_element(1, item, None)

        assert result == ""

    def test_format_element_with_mop_direct(self, processor):
        """Element with direct MOP marker."""
        item = MagicMock()
        item.view = {
            'class': 'android.widget.Button',
            'text': 'Encrypt',
            'resource_id': '',
            'bounds': [(100, 200), (300, 400)]
        }

        action = MagicMock(spec=ItemAction)
        action.text = "click"
        action.directly_reaches_mop = True
        action.reaches_mop = False
        item.actions = [action]

        result = processor._format_element(1, item, None)

        assert "[DM]" in result

    def test_format_element_with_mop_transitive(self, processor):
        """Element with transitive MOP marker."""
        item = MagicMock()
        item.view = {
            'class': 'android.widget.Button',
            'text': 'Settings',
            'resource_id': '',
            'bounds': [(100, 200), (300, 400)]
        }

        action = MagicMock(spec=ItemAction)
        action.text = "click"
        action.directly_reaches_mop = False
        action.reaches_mop = True
        item.actions = [action]

        result = processor._format_element(1, item, None)

        assert "[M]" in result

    def test_format_element_with_actions(self, processor):
        """Element with actions shows action text."""
        item = MagicMock()
        item.view = {
            'class': 'android.widget.Button',
            'text': 'Submit',
            'resource_id': '',
            'bounds': [(100, 200), (300, 400)]
        }

        action = MagicMock(spec=ItemAction)
        action.text = "click"
        action.directly_reaches_mop = False
        action.reaches_mop = False
        item.actions = [action]

        result = processor._format_element(1, item, None)

        assert "Actions:" in result
        assert "click" in result


class TestRestartApp:
    """Test _restart_app method."""

    def test_restart_app_calls_device_methods(self):
        """Restart app calls stop and start."""
        device = MagicMock()
        graph = DynamicStateGraph()
        processor = ScreenProcessor(device=device, dynamic_graph=graph)

        with patch('time.sleep'):
            processor._restart_app("com.example.app")

        device.stop_app.assert_called_once_with("com.example.app")
        device.start_app.assert_called_once_with("com.example.app")


class TestParseCurrentScreen:
    """Test parse_current_screen method."""

    def test_parse_basic(self):
        """Basic parse returns expected structure."""
        device = MagicMock()
        device.get_current_ui_state.return_value = {
            'xml': '<hierarchy></hierarchy>',
            'current_activity': 'com.example/.MainActivity',
            'current_package': 'com.example'
        }
        graph = DynamicStateGraph()

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = 'MainActivity'

        with patch('rv_agent.ui.screen_processor.ParserFactory') as mock_factory:
            mock_parser = MagicMock()
            mock_parser.parse_screen.return_value = screen_desc
            mock_factory.create.return_value = mock_parser

            processor = ScreenProcessor(device=device, dynamic_graph=graph)
            result = processor.parse_current_screen(
                target_package="com.example",
                external_navigation_count=0
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
            'xml': '<hierarchy></hierarchy>',
            'current_activity': 'com.google/.SearchActivity',
            'current_package': 'com.google'
        }
        graph = DynamicStateGraph()

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = 'SearchActivity'

        with patch('rv_agent.ui.screen_processor.ParserFactory') as mock_factory:
            mock_parser = MagicMock()
            mock_parser.parse_screen.return_value = screen_desc
            mock_factory.create.return_value = mock_parser

            processor = ScreenProcessor(device=device, dynamic_graph=graph)
            result = processor.parse_current_screen(
                target_package="com.example",
                external_navigation_count=0
            )

        assert result["is_external"] is True
        assert result["external_navigation_count"] == 1

    def test_parse_restart_after_max_external(self):
        """Parse restarts app after max external attempts."""
        device = MagicMock()
        # First call returns external, second returns target
        device.get_current_ui_state.side_effect = [
            {
                'xml': '<hierarchy></hierarchy>',
                'current_activity': 'com.google/.SearchActivity',
                'current_package': 'com.google'
            },
            {
                'xml': '<hierarchy></hierarchy>',
                'current_activity': 'com.example/.MainActivity',
                'current_package': 'com.example'
            }
        ]
        graph = DynamicStateGraph()

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = 'MainActivity'

        with patch('rv_agent.ui.screen_processor.ParserFactory') as mock_factory:
            mock_parser = MagicMock()
            mock_parser.parse_screen.return_value = screen_desc
            mock_factory.create.return_value = mock_parser

            with patch('time.sleep'):
                processor = ScreenProcessor(device=device, dynamic_graph=graph)
                result = processor.parse_current_screen(
                    target_package="com.example",
                    external_navigation_count=3  # At max
                )

        assert result["restart_occurred"] is True
        device.stop_app.assert_called_once()
        device.start_app.assert_called_once()

    def test_parse_reset_counter_on_return(self):
        """Counter resets when returning to target app."""
        device = MagicMock()
        device.get_current_ui_state.return_value = {
            'xml': '<hierarchy></hierarchy>',
            'current_activity': 'com.example/.MainActivity',
            'current_package': 'com.example'
        }
        graph = DynamicStateGraph()

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = 'MainActivity'

        with patch('rv_agent.ui.screen_processor.ParserFactory') as mock_factory:
            mock_parser = MagicMock()
            mock_parser.parse_screen.return_value = screen_desc
            mock_factory.create.return_value = mock_parser

            processor = ScreenProcessor(device=device, dynamic_graph=graph)
            result = processor.parse_current_screen(
                target_package="com.example",
                external_navigation_count=2  # Was external
            )

        assert result["external_navigation_count"] == 0

    def test_parse_with_ui_coverage(self):
        """Parse applies UI coverage annotations."""
        device = MagicMock()
        device.get_current_ui_state.return_value = {
            'xml': '<hierarchy></hierarchy>',
            'current_activity': 'com.example/.MainActivity',
            'current_package': 'com.example'
        }
        graph = DynamicStateGraph()

        screen_desc = MagicMock(spec=ScreenDescription)
        screen_desc.items = []
        screen_desc.activity = 'MainActivity'

        ui_coverage = MagicMock()
        ui_coverage.annotate_screen_elements.return_value = "Annotated elements"

        with patch('rv_agent.ui.screen_processor.ParserFactory') as mock_factory:
            mock_parser = MagicMock()
            mock_parser.parse_screen.return_value = screen_desc
            mock_factory.create.return_value = mock_parser

            processor = ScreenProcessor(
                device=device,
                dynamic_graph=graph,
                ui_coverage=ui_coverage
            )
            result = processor.parse_current_screen(
                target_package="com.example",
                external_navigation_count=0
            )

        ui_coverage.annotate_screen_elements.assert_called_once()
        assert result["ui_elements_text"] == "Annotated elements"
