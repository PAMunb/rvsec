import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add the parent directory to the path to make imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from rv_android_core.domain.classes import Classes
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.constants import EXTENSION_REACH, EXTENSION_GATOR, EXTENSION_GESDA
from rv_static_analysis.parser.static.static_analysis_parser import (
    StaticAnalysisParser,
    parse,
    read_static_analysis_files,
    parse_all
)


class TestStaticAnalysisParser:
    """Tests for the StaticAnalysisParser class."""

    @pytest.fixture
    def parser(self):
        """Initialize a StaticAnalysisParser instance for testing."""
        return StaticAnalysisParser()

    @pytest.fixture
    def mock_reach_parser(self):
        """Create a mock for ReachParser."""
        mock = MagicMock()
        mock.parse_file.return_value = Classes()
        return mock

    @pytest.fixture
    def mock_gator_parser(self):
        """Create a mock for GatorParser."""
        mock = MagicMock()
        mock.parse_file.return_value = WindowTransitionGraph()
        return mock

    @pytest.fixture
    def mock_gesda_parser(self):
        """Create a mock for GesdaParser."""
        mock = MagicMock()
        mock.parse_file.return_value = Windows()
        return mock

    def test_initialization(self, parser):
        """Test initialization of StaticAnalysisParser."""
        assert parser.logger is not None
        assert parser.reach_parser is not None
        assert parser.gator_parser is not None
        assert parser.gesda_parser is not None

    def test_parse_success(self, parser, mock_reach_parser, mock_gator_parser, mock_gesda_parser):
        """Test successful parsing of all file types."""
        # Setup - replace parser instances with mocks
        parser.reach_parser = mock_reach_parser
        parser.gator_parser = mock_gator_parser
        parser.gesda_parser = mock_gesda_parser

        # Setup mock return values
        classes = Classes()
        classes.add_clazz("com.example.TestActivity", True, True)
        mock_reach_parser.parse_file.return_value = classes

        windows = Windows()
        mock_gesda_parser.parse_file.return_value = windows

        wtg = WindowTransitionGraph()
        mock_gator_parser.parse_file.return_value = wtg

        # Test
        result = parser.parse("reach_file.csv", "gator_file.json", "gesda_file.json", "com.example")

        # Assertions
        assert isinstance(result, StaticAnalysisData)
        # Check that the returned object contains the appropriate types
        assert isinstance(result.classes, Classes)
        assert isinstance(result.windows, Windows)
        assert isinstance(result.wtg, WindowTransitionGraph)

        # Check data was populated correctly
        assert "com.example.TestActivity" in result.classes.classes

        # Check that all parsers were called
        mock_reach_parser.parse_file.assert_called_once()
        mock_gator_parser.parse_file.assert_called_once()
        mock_gesda_parser.parse_file.assert_called_once()

    def test_parse_with_exception(self, parser, mock_reach_parser, mock_gator_parser, mock_gesda_parser):
        """Test handling of exceptions during parsing."""
        # Setup - replace parser instances with mocks
        parser.reach_parser = mock_reach_parser
        parser.gator_parser = mock_gator_parser
        parser.gesda_parser = mock_gesda_parser

        # Make reach_parser raise an exception
        mock_reach_parser.parse_file.side_effect = Exception("Test exception")

        # Setup mock return values for other parsers
        windows = Windows()
        mock_gesda_parser.parse_file.return_value = windows

        wtg = WindowTransitionGraph()
        mock_gator_parser.parse_file.return_value = wtg

        # Test
        result = parser.parse("reach_file.csv", "gator_file.json", "gesda_file.json", "com.example")

        # Assertions
        assert isinstance(result, StaticAnalysisData)

        # Even with an exception, we should still get a valid StaticAnalysisData object
        # with empty classes from the exception handler
        assert isinstance(result.classes, Classes)
        assert len(result.classes.classes) == 0

        # Other components should still be populated
        assert isinstance(result.windows, Windows)
        assert isinstance(result.wtg, WindowTransitionGraph)

        # Verify parser calls were made
        mock_reach_parser.parse_file.assert_called_once()
        mock_gator_parser.parse_file.assert_called_once()
        mock_gesda_parser.parse_file.assert_called_once()

    @patch("os.path.join")
    def test_read_static_analysis_files(self, mock_join, parser, mock_reach_parser, mock_gator_parser,
                                        mock_gesda_parser):
        """Test reading static analysis files from a directory."""
        # Setup - replace parser instances with mocks
        parser.reach_parser = mock_reach_parser
        parser.gator_parser = mock_gator_parser
        parser.gesda_parser = mock_gesda_parser

        # Setup mock return values
        classes = Classes()
        mock_reach_parser.parse_file.return_value = classes

        windows = Windows()
        mock_gesda_parser.parse_file.return_value = windows

        wtg = WindowTransitionGraph()
        mock_gator_parser.parse_file.return_value = wtg

        # Setup mock path joining
        mock_join.side_effect = lambda *args: "/".join(args)

        # Test
        result = parser.read_static_analysis_files("/path/to/results", "app.apk", "com.example")

        # Assertions
        assert isinstance(result, StaticAnalysisData)

        # Check that join was called with correct paths
        expected_calls = [
            (("/path/to/results", f"app.apk{EXTENSION_REACH}"),),
            (("/path/to/results", f"app.apk{EXTENSION_GATOR}"),),
            (("/path/to/results", f"app.apk{EXTENSION_GESDA}"),)
        ]
        assert mock_join.call_count == 3
        mock_join.assert_has_calls(expected_calls, any_order=True)

        # Check that parsers were called with correct file paths
        mock_reach_parser.parse_file.assert_called_once()
        mock_gator_parser.parse_file.assert_called_once()
        mock_gesda_parser.parse_file.assert_called_once()

    @patch("rv_static_analysis.parser.static.static_analysis_parser._instance.parse")
    def test_parse_function(self, mock_parse):
        """Test the parse convenience function."""
        # Setup
        mock_parse.return_value = StaticAnalysisData(Classes(), Windows(), WindowTransitionGraph())

        # Test
        result = parse("reach_file.csv", "gator_file.json", "gesda_file.json", "com.example")

        # Assertions
        assert isinstance(result, StaticAnalysisData)
        mock_parse.assert_called_once_with("reach_file.csv", "gator_file.json", "gesda_file.json", "com.example")

    @patch("rv_static_analysis.parser.static.static_analysis_parser._instance.read_static_analysis_files")
    def test_read_static_analysis_files_function(self, mock_read):
        """Test the read_static_analysis_files convenience function."""
        # Setup
        mock_read.return_value = StaticAnalysisData(Classes(), Windows(), WindowTransitionGraph())

        # Test
        result = read_static_analysis_files("/path/to/results", "app.apk", "com.example")

        # Assertions
        assert isinstance(result, StaticAnalysisData)
        mock_read.assert_called_once_with("/path/to/results", "app.apk", "com.example")

    @patch("rv_static_analysis.parser.static.static_analysis_parser._instance.parse")
    def test_parse_all_function(self, mock_parse):
        """Test the deprecated parse_all convenience function."""
        # Setup
        mock_parse.return_value = StaticAnalysisData(Classes(), Windows(), WindowTransitionGraph())

        # Test with string package
        result = parse_all("com.example", "gesda_file.json", "gator_file.json", "reach_file.csv")

        # Assertions
        assert isinstance(result, StaticAnalysisData)
        mock_parse.assert_called_once_with("reach_file.csv", "gator_file.json", "gesda_file.json", "com.example")
        mock_parse.reset_mock()

        # Test with app object
        class MockApp:
            def __init__(self):
                self.package_name = "com.example"

        app = MockApp()
        result = parse_all(app, "gesda_file.json", "gator_file.json", "reach_file.csv")

        # Assertions
        assert isinstance(result, StaticAnalysisData)
        mock_parse.assert_called_once_with("reach_file.csv", "gator_file.json", "gesda_file.json", "com.example")


class TestStaticAnalysisParserIntegration:
    """Integration tests for StaticAnalysisParser with real parsers."""

    @pytest.fixture
    def parser(self):
        """Initialize a real StaticAnalysisParser instance for testing."""
        return StaticAnalysisParser()

    @patch("rv_static_analysis.parser.static.reach_parser.ReachParser.parse_file")
    @patch("rv_static_analysis.parser.static.gator_parser.GatorParser.parse_file")
    @patch("rv_static_analysis.parser.static.gesda_parser.GesdaParser.parse_file")
    def test_parse_integration(self, mock_gesda_parse, mock_gator_parse, mock_reach_parse, parser):
        """Test StaticAnalysisParser integration with mocked parsers."""
        # Setup mock return values
        classes = Classes()
        classes.add_clazz("com.example.MainActivity", True, True)
        mock_reach_parse.return_value = classes

        windows = Windows()
        mock_gesda_parse.return_value = windows

        wtg = WindowTransitionGraph()
        mock_gator_parse.return_value = wtg

        # Test
        result = parser.parse("reach_file.csv", "gator_file.json", "gesda_file.json", "com.example")

        # Assertions
        assert isinstance(result, StaticAnalysisData)
        assert isinstance(result.classes, Classes)
        assert isinstance(result.windows, Windows)
        assert isinstance(result.wtg, WindowTransitionGraph)

        # Verify class content
        assert "com.example.MainActivity" in result.classes.classes

        # Check that all parsers were called
        mock_reach_parse.assert_called_once()
        mock_gator_parse.assert_called_once()
        mock_gesda_parse.assert_called_once()
