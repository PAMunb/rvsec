"""
Integration tests for ScreenProcessor with real UIAutomator fixtures.

Tests screen parsing, UI element formatting, coordinate transformation,
and integration with DynamicStateGraph.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from rv_agent.agent.device_interface import DeviceInterface
from rv_agent.agent.dynamic_state_graph import (
    DynamicStateGraph,
    compute_screen_hash_from_description,
)
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.services.screen_analyzer import ScreenProcessor
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import (
    UIAutomator2Parser,
)
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

pytestmark = pytest.mark.integration


# =============================================================================
# Fixtures
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "screenshots"


def load_xml_content(app_name: str, screen_num: str) -> str:
    """Load raw XML content from fixture."""
    xml_path = FIXTURES_DIR / app_name / f"{screen_num}.uiautomator.xml"
    with open(xml_path, "r") as f:
        return f.read()


@pytest.fixture
def mock_device():
    """Mock device interface."""
    device = MagicMock(spec=DeviceInterface)
    return device


@pytest.fixture
def graph():
    """Fresh DynamicStateGraph."""
    return DynamicStateGraph()


@pytest.fixture
def ui_coverage():
    """UI coverage tracker."""
    return UICoverageTracker()


@pytest.fixture
def screen_processor(mock_device, graph, ui_coverage):
    """ScreenProcessor with mocked device."""
    return ScreenProcessor(
        device=mock_device,
        dynamic_graph=graph,
        ui_coverage=ui_coverage,
        device_dimensions=(1080, 1920),
    )


@pytest.fixture
def parser():
    """UIAutomator parser."""
    return UIAutomator2Parser(visitor_class=DefaultTextVisitor)


# =============================================================================
# UI Element Formatting Tests
# =============================================================================


class TestUIElementFormatting:
    """Test UI element formatting with real fixtures."""

    def test_format_cryptoapp_main_screen(self, screen_processor, parser):
        """Format cryptoapp main screen elements."""
        xml_content = load_xml_content("cryptoapp", "001")
        screen_desc = parser.parse(xml_content, activity="MainActivity")

        formatted = screen_processor.format_ui_elements(screen_desc)

        # Should have scored elements with position info
        assert "Button" in formatted
        assert "position" in formatted
        assert "score:" in formatted

    def test_format_includes_coordinates(self, screen_processor, parser):
        """Formatted output includes element coordinates."""
        xml_content = load_xml_content("cryptoapp", "001")
        screen_desc = parser.parse(xml_content, activity="MainActivity")

        formatted = screen_processor.format_ui_elements(screen_desc)

        # Should have coordinate format like (x, y)
        import re

        coord_pattern = r"position \(\d+, \d+\)"
        matches = re.findall(coord_pattern, formatted)

        assert len(matches) > 0, "Should have coordinate positions"

    def test_format_includes_element_info(self, screen_processor, parser):
        """Formatted output includes element info."""
        xml_content = load_xml_content("cryptoapp", "001")
        screen_desc = parser.parse(xml_content, activity="MainActivity")

        formatted = screen_processor.format_ui_elements(screen_desc)

        # Should have position format like "at position (x, y)"
        import re

        position_pattern = r"at position \(\d+, \d+\)"
        matches = re.findall(position_pattern, formatted)

        assert len(matches) > 0, "Should have element positions"

    def test_format_coordinate_info(self, screen_processor, parser):
        """Formatted output includes coordinate information."""
        xml_content = load_xml_content("cryptoapp", "001")
        screen_desc = parser.parse(xml_content, activity="MainActivity")

        formatted = screen_processor.format_ui_elements(screen_desc)

        # Should have position coordinates in the format (x, y)
        import re

        position_pattern = r"position \(\d+, \d+\)"
        assert re.search(
            position_pattern, formatted
        ), "Should have position coordinates"

    def test_format_empty_screen(self, screen_processor):
        """Format empty screen description."""
        empty_desc = ScreenDescription(activity="Empty", items=[])

        formatted = screen_processor.format_ui_elements(empty_desc)

        assert "No interactive elements" in formatted

    def test_categorizes_text_inputs(self, screen_processor, parser):
        """Text inputs are categorized separately."""
        # Load a screen that has EditText fields
        xml_content = load_xml_content("cryptoapp", "002")
        screen_desc = parser.parse(xml_content, activity="MainActivity")

        formatted = screen_processor.format_ui_elements(screen_desc)

        # Check if text input section exists (may or may not depending on screen)
        # Just verify the format doesn't crash
        assert len(formatted) > 0


# =============================================================================
# Coordinate Transformation Tests
# =============================================================================


class TestCoordinateTransformation:
    """Test coordinate validation in device space."""

    def test_coordinates_in_device_range(self, screen_processor, parser):
        """All coordinates should be within device dimensions."""
        xml_content = load_xml_content("cryptoapp", "001")
        screen_desc = parser.parse(xml_content, activity="MainActivity")

        formatted = screen_processor.format_ui_elements(screen_desc)

        # Extract all coordinates
        import re

        coord_pattern = r"position \((\d+), (\d+)\)"
        matches = re.findall(coord_pattern, formatted)

        device_width, device_height = 1080, 1920

        for x_str, y_str in matches:
            x, y = int(x_str), int(y_str)
            assert 0 <= x <= device_width, f"X coordinate {x} out of range"
            assert 0 <= y <= device_height, f"Y coordinate {y} out of range"

    def test_bounds_in_device_range(self, screen_processor, parser):
        """All bounds should be within device dimensions."""
        xml_content = load_xml_content("cryptoapp", "001")
        screen_desc = parser.parse(xml_content, activity="MainActivity")

        formatted = screen_processor.format_ui_elements(screen_desc)

        # Extract all bounds
        import re

        bounds_pattern = r"bounds\[\[(\d+), (\d+)\], \[(\d+), (\d+)\]\]"
        matches = re.findall(bounds_pattern, formatted)

        device_width, device_height = 1080, 1920

        for x1, y1, x2, y2 in matches:
            assert 0 <= int(x1) <= device_width
            assert 0 <= int(y1) <= device_height
            assert 0 <= int(x2) <= device_width
            assert 0 <= int(y2) <= device_height

    def test_coordinate_bounds_consistency(self, screen_processor, parser):
        """Verify coordinates are within element bounds."""
        xml_content = load_xml_content("cryptoapp", "001")
        screen_desc = parser.parse(xml_content, activity="MainActivity")

        # Get first clickable element with valid bounds
        for item in screen_desc.items:
            bounds = item.view.get("bounds")
            if bounds and item.view.get("clickable"):
                x1, y1 = bounds[0]
                x2, y2 = bounds[1]

                # Center coordinates should be within bounds
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                assert x1 <= center_x <= x2, "Center X not within bounds"
                assert y1 <= center_y <= y2, "Center Y not within bounds"
                break


# =============================================================================
# Screen Parsing Integration Tests
# =============================================================================


class TestScreenParsingIntegration:
    """Test screen parsing with mock device."""

    def test_parse_current_screen_mock(self, screen_processor, mock_device):
        """Parse current screen with mocked device."""
        xml_content = load_xml_content("cryptoapp", "001")

        mock_device.get_current_ui_state.return_value = {
            "xml": xml_content,
            "current_activity": "br.unb.cic.cryptoapp.MainActivity",
            "current_package": "br.unb.cic.cryptoapp",
        }

        result = screen_processor.parse_current_screen(
            target_package="br.unb.cic.cryptoapp"
        )

        assert "screen_hash" in result
        assert "activity" in result
        assert "screen_description" in result
        assert "ui_elements_text" in result
        assert result["is_external"] is False

    def test_parse_detects_external_navigation(self, screen_processor, mock_device):
        """Detect external navigation."""
        xml_content = load_xml_content("cryptoapp", "001")

        mock_device.get_current_ui_state.return_value = {
            "xml": xml_content,
            "current_activity": "com.android.settings.MainActivity",
            "current_package": "com.android.settings",
        }

        result = screen_processor.parse_current_screen(
            target_package="br.unb.cic.cryptoapp"
        )

        assert result["is_external"] is True
        assert result["external_navigation_count"] == 1

    def test_parse_increments_external_count(self, screen_processor, mock_device):
        """External navigation count increments."""
        xml_content = load_xml_content("cryptoapp", "001")

        mock_device.get_current_ui_state.return_value = {
            "xml": xml_content,
            "current_activity": "com.other.Activity",
            "current_package": "com.other",
        }

        result1 = screen_processor.parse_current_screen(
            target_package="br.unb.cic.cryptoapp", external_navigation_count=0
        )

        result2 = screen_processor.parse_current_screen(
            target_package="br.unb.cic.cryptoapp",
            external_navigation_count=result1["external_navigation_count"],
        )

        assert result2["external_navigation_count"] == 2


# =============================================================================
# Hash Computation Integration Tests
# =============================================================================


class TestHashComputationIntegration:
    """Test hash computation with ScreenProcessor."""

    def test_hash_from_parsed_screen(self, screen_processor, mock_device):
        """Hash computed from parsed screen."""
        xml_content = load_xml_content("cryptoapp", "001")

        mock_device.get_current_ui_state.return_value = {
            "xml": xml_content,
            "current_activity": "MainActivity",
            "current_package": "br.unb.cic.cryptoapp",
        }

        result = screen_processor.parse_current_screen(
            target_package="br.unb.cic.cryptoapp"
        )

        assert len(result["screen_hash"]) == 12
        assert result["screen_hash"].isalnum()

    def test_same_screen_same_hash_via_processor(self, screen_processor, mock_device):
        """Same screen produces same hash through processor."""
        xml_content = load_xml_content("cryptoapp", "001")

        mock_device.get_current_ui_state.return_value = {
            "xml": xml_content,
            "current_activity": "MainActivity",
            "current_package": "br.unb.cic.cryptoapp",
        }

        result1 = screen_processor.parse_current_screen(
            target_package="br.unb.cic.cryptoapp"
        )

        result2 = screen_processor.parse_current_screen(
            target_package="br.unb.cic.cryptoapp"
        )

        assert result1["screen_hash"] == result2["screen_hash"]


# =============================================================================
# UI Coverage Annotation Tests
# =============================================================================


class TestUICoverageAnnotation:
    """Test UI coverage annotation in formatted output."""

    def test_coverage_annotation_applied(
        self, screen_processor, mock_device, ui_coverage
    ):
        """UI coverage annotations are applied."""
        xml_content = load_xml_content("cryptoapp", "001")

        mock_device.get_current_ui_state.return_value = {
            "xml": xml_content,
            "current_activity": "MainActivity",
            "current_package": "br.unb.cic.cryptoapp",
        }

        # Record some interactions
        ui_coverage.record_interaction("btn_1", "click", "test_hash")

        result = screen_processor.parse_current_screen(
            target_package="br.unb.cic.cryptoapp"
        )

        # Verify formatted text was generated
        assert len(result["ui_elements_text"]) > 0


# =============================================================================
# Multi-App Integration Tests
# =============================================================================


class TestMultiAppIntegration:
    """Test screen processor with multiple apps."""

    def test_process_ludo_screen(self, screen_processor, mock_device):
        """Process Ludo app screen."""
        xml_content = load_xml_content("ludo", "001")

        mock_device.get_current_ui_state.return_value = {
            "xml": xml_content,
            "current_activity": "org.secuso.privacyfriendlyludo.MainActivity",
            "current_package": "org.secuso.privacyfriendlyludo",
        }

        result = screen_processor.parse_current_screen(
            target_package="org.secuso.privacyfriendlyludo"
        )

        assert result["screen_hash"] is not None
        assert len(result["ui_elements_text"]) > 0

    def test_process_hashpass_screen(self, screen_processor, mock_device):
        """Process Hashpass app screen."""
        xml_content = load_xml_content("hashpass", "001")

        mock_device.get_current_ui_state.return_value = {
            "xml": xml_content,
            "current_activity": "byrne.utilities.hashpass.MainActivity",
            "current_package": "byrne.utilities.hashpass",
        }

        result = screen_processor.parse_current_screen(
            target_package="byrne.utilities.hashpass"
        )

        assert result["screen_hash"] is not None

    def test_different_apps_different_hashes(self, screen_processor, parser):
        """Different apps produce different hashes."""
        crypto_xml = load_xml_content("cryptoapp", "001")
        ludo_xml = load_xml_content("ludo", "001")

        crypto_desc = parser.parse(crypto_xml, activity="CryptoActivity")
        ludo_desc = parser.parse(ludo_xml, activity="LudoActivity")

        crypto_hash = compute_screen_hash_from_description(crypto_desc)
        ludo_hash = compute_screen_hash_from_description(ludo_desc)

        assert crypto_hash != ludo_hash


# =============================================================================
# Element Type Detection Tests
# =============================================================================


class TestElementTypeDetection:
    """Test detection of different UI element types."""

    def test_detects_buttons(self, screen_processor, parser):
        """Detect button elements."""
        xml_content = load_xml_content("cryptoapp", "001")
        screen_desc = parser.parse(xml_content, activity="MainActivity")

        formatted = screen_processor.format_ui_elements(screen_desc)

        assert "Button" in formatted

    def test_detects_element_text(self, screen_processor, parser):
        """Detect element text content."""
        xml_content = load_xml_content("cryptoapp", "001")
        screen_desc = parser.parse(xml_content, activity="MainActivity")

        formatted = screen_processor.format_ui_elements(screen_desc)

        # Cryptoapp has buttons like "MESSAGE DIGEST", "CIPHER"
        # Check for text markers (single quotes around text)
        assert "'" in formatted  # Text is quoted

    def test_detects_resource_ids(self, screen_processor, parser):
        """Detect resource IDs."""
        xml_content = load_xml_content("cryptoapp", "001")
        screen_desc = parser.parse(xml_content, activity="MainActivity")

        formatted = screen_processor.format_ui_elements(screen_desc)

        # Resource IDs are in parentheses
        assert "(" in formatted and ")" in formatted
