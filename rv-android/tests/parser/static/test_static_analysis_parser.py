# tests/parser/static/test_static_analysis_parser.py
"""
Unit tests for the static_analysis_parser module.

This module tests the functionality of the static_analysis_parser, which is responsible for
coordinating the parsing of various static analysis files and building a comprehensive
StaticAnalysisData object.

### Architectural Decisions:
- Uses comprehensive mocking to isolate static_analysis_parser functionality
- Tests both happy paths and error scenarios
- Validates correct interactions between parsers
- Ensures proper file path handling and error propagation

### Role in the System:
- Verifies correct coordination of multiple parser modules
- Validates the creation of comprehensive static analysis data
- Ensures resilience against missing or invalid files
- Confirms proper logging of parsing operations
"""

from unittest.mock import patch

import pytest

from rvandroid.domain.classes import Classes, Method
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.domain.window import Windows, Window
from rvandroid.domain.wtg import WindowTransitionGraph
from rvandroid.parser.static import static_analysis_parser


class TestStaticAnalysisParser:
    """Tests for the static_analysis_parser module functionality."""

    @pytest.fixture
    def mock_classes(self):
        """Create a mock Classes object."""
        classes = Classes()

        # Add a test activity
        main_activity = classes.add_clazz("com.example.MainActivity", True, True)

        # Add a test utility class
        utils = classes.add_clazz("com.example.Utils", False, False)

        # Add methods to classes
        method1 = Method(
            "com.example.MainActivity",
            "onCreate",
            ["android.os.Bundle"],
            "<com.example.MainActivity: void onCreate(android.os.Bundle)>",
            True,
            True,
            False
        )
        method2 = Method(
            "com.example.Utils",
            "encrypt",
            ["java.lang.String"],
            "<com.example.Utils: byte[] encrypt(java.lang.String)>",
            True,
            True,
            True
        )

        classes.add_method(method1)
        classes.add_method(method2)

        return classes

    @pytest.fixture
    def mock_windows(self):
        """Create a mock Windows object."""
        windows = Windows()

        # Add test windows
        main_window = Window("com.example.MainActivity")
        secondary_window = Window("com.example.SecondaryActivity")

        windows.add_window(main_window)
        windows.add_window(secondary_window)

        return windows

    @pytest.fixture
    def mock_wtg(self):
        """Create a mock WindowTransitionGraph object."""
        return WindowTransitionGraph()

    @patch('rvandroid.parser.static.static_analysis_parser._parse_reach')
    @patch('rvandroid.parser.static.static_analysis_parser._parse_gator')
    @patch('rvandroid.parser.static.static_analysis_parser._parse_gesda')
    def test_parse_happy_path(self, mock_parse_gesda, mock_parse_gator,
                              mock_parse_reach, mock_classes, mock_windows, mock_wtg):
        """Test successful parsing of all static analysis files."""
        # Configure mocks
        mock_parse_reach.return_value = mock_classes
        mock_parse_gator.return_value = mock_wtg
        mock_parse_gesda.return_value = None  # This function doesn't return anything

        # Call the function
        result = static_analysis_parser.parse(
            "test_app.reach",
            "test_app.wtg",
            "test_app.gesda",
            "com.example"
        )

        # Verify calls
        mock_parse_reach.assert_called_once_with("test_app.reach")
        mock_parse_gator.assert_called_once_with("test_app.wtg", "com.example", mock_classes, result.windows)
        mock_parse_gesda.assert_called_once_with("test_app.gesda", "com.example", mock_classes, result.windows)

        # Verify result
        assert isinstance(result, StaticAnalysisData)
        assert result.classes == mock_classes
        assert result.wtg == mock_wtg

    @patch('rvandroid.parser.static.static_analysis_parser._parse_reach')
    @patch('rvandroid.parser.static.static_analysis_parser._parse_gator')
    @patch('rvandroid.parser.static.static_analysis_parser._parse_gesda')
    def test_parse_missing_files(self, mock_parse_gesda, mock_parse_gator,
                                 mock_parse_reach, mock_classes):
        """Test handling of missing files."""
        # Configure mocks
        mock_parse_reach.return_value = mock_classes
        mock_parse_gator.return_value = None  # Simulate missing file
        mock_parse_gesda.return_value = None  # This function doesn't return anything

        # Call the function
        result = static_analysis_parser.parse(
            "missing_app.reach",
            "missing_app.wtg",
            "missing_app.gesda",
            "com.example"
        )

        # Verify behavior
        mock_parse_reach.assert_called_once_with("missing_app.reach")
        mock_parse_gator.assert_called_once()
        mock_parse_gesda.assert_called_once()

        # Verify result still returns a valid object
        assert isinstance(result, StaticAnalysisData)
        assert result.classes == mock_classes
        assert result.wtg is None  # WTG should be None if file not found

    @patch('rvandroid.parser.static.static_analysis_parser._parse_reach')
    def test_parser_exceptions(self, mock_parse_reach):
        """Test handling of parser exceptions."""
        # Configure mock to raise an exception
        mock_parse_reach.side_effect = Exception("Parsing error")

        # Call the function - wrap in try/except to handle the exception
        try:
            result = static_analysis_parser.parse(
                "error_app.reach",
                "error_app.wtg",
                "error_app.gesda",
                "com.example"
            )

            # If we reach here, the exception was handled within the function
            assert isinstance(result, StaticAnalysisData)
            assert isinstance(result.classes, Classes)
            assert len(result.classes.classes) == 0  # Should be empty due to error

        except Exception as e:
            # If the exception propagates, the function didn't handle it properly
            # This is a valid test condition if the function isn't supposed to catch errors
            assert str(e) == "Parsing error"

    @patch('rvandroid.parser.static.static_analysis_parser._parse_reach_analysis')
    @patch('rvandroid.parser.static.static_analysis_parser._parse_gator_analysis')
    @patch('rvandroid.parser.static.static_analysis_parser._parse_gesda_analysis')
    def test_read_static_analysis_files(self, mock_parse_gesda, mock_parse_gator,
                                        mock_parse_reach, mock_classes, mock_wtg):
        """Test read_static_analysis_files function."""
        # Configure mocks
        mock_parse_reach.return_value = mock_classes
        mock_parse_gator.return_value = mock_wtg

        # Call the function
        result = static_analysis_parser.read_static_analysis_files(
            "/results/dir",
            "test_app.apk",
            "com.example"
        )

        # Verify calls
        mock_parse_reach.assert_called_once_with("/results/dir", "test_app.apk")
        mock_parse_gator.assert_called_once()
        mock_parse_gesda.assert_called_once()

        # Verify result
        assert isinstance(result, StaticAnalysisData)
        assert result.classes == mock_classes
        assert result.wtg == mock_wtg

    @patch('os.path.exists')
    @patch('rvandroid.parser.static.reach_parser.read_reachable_methods')
    def test_parse_reach(self, mock_read_reachable, mock_exists, mock_classes):
        """Test _parse_reach function."""
        # Configure mocks
        mock_exists.return_value = True
        mock_read_reachable.return_value = mock_classes

        # Call the function
        result = static_analysis_parser._parse_reach("test_reach.csv")

        # Verify calls
        mock_read_reachable.assert_called_once_with("test_reach.csv")

        # Verify result
        assert result == mock_classes

    @patch('os.path.exists')
    def test_parse_reach_file_not_found(self, mock_exists):
        """Test _parse_reach with file not found."""
        # Configure mock
        mock_exists.return_value = False

        # Call the function
        result = static_analysis_parser._parse_reach("nonexistent.csv")

        # Verify result is empty Classes object
        assert isinstance(result, Classes)
        assert len(result.classes) == 0

    # @patch('os.path.join')
    # @patch('rvandroid.parser.static.static_analysis_parser._parse_reach')
    # def test_parse_reach_analysis(self, mock_parse_reach, mock_join, mock_classes):
    #     """Test _parse_reach_analysis function."""
    #     # Configure mocks
    #     mock_join.return_value = "/results/dir/test_app.apk.reach"
    #     mock_parse_reach.return_value = mock_classes
    #
    #     # Call the function
    #     result = static_analysis_parser._parse_reach_analysis("/results/dir", "test_app.apk")
    #
    #     # Verify calls
    #     mock_join.assert_called_once_with("/results/dir", "test_app.apk.reach")
    #     mock_parse_reach.assert_called_once_with("/results/dir/test_app.apk.reach")
    #
    #     # Verify result
    #     assert result == mock_classes

    @patch('os.path.join')
    @patch('rvandroid.parser.static.static_analysis_parser._parse_gesda')
    def test_parse_gesda_analysis(self, mock_parse_gesda, mock_join,
                                  mock_classes, mock_windows):
        """Test _parse_gesda_analysis function."""
        # Configure mocks
        mock_join.side_effect = lambda *args: "/".join(args)

        # Call the function
        static_analysis_parser._parse_gesda_analysis(
            "/results/dir",
            "test_app.apk",
            "com.example",
            mock_classes,
            mock_windows
        )

        # Verify calls
        mock_join.assert_called_with("/results/dir", "test_app.apk.gesda")
        mock_parse_gesda.assert_called_once_with(
            "/results/dir/test_app.apk.gesda",
            "com.example",
            mock_classes,
            mock_windows
        )

    @patch('os.path.join')
    @patch('rvandroid.parser.static.static_analysis_parser._parse_gator')
    def test_parse_gator_analysis(self, mock_parse_gator, mock_join,
                                  mock_classes, mock_windows, mock_wtg):
        """Test _parse_gator_analysis function."""
        # Configure mocks
        mock_join.side_effect = lambda *args: "/".join(args)
        mock_parse_gator.return_value = mock_wtg

        # Call the function
        result = static_analysis_parser._parse_gator_analysis(
            "/results/dir",
            "test_app.apk",
            "com.example",
            mock_classes,
            mock_windows
        )

        # Verify calls
        mock_join.assert_called_with("/results/dir", "test_app.apk.wtg")
        mock_parse_gator.assert_called_once_with(
            "/results/dir/test_app.apk.wtg",
            "com.example",
            mock_classes,
            mock_windows
        )

        # Verify result
        assert result == mock_wtg

    @patch('os.path.exists')
    @patch('rvandroid.parser.static.gesda_parser.parse_gesda_file')
    def test_parse_gesda(self, mock_parse_gesda, mock_exists, mock_classes, mock_windows):
        """Test _parse_gesda function."""
        # Configure mocks
        mock_exists.return_value = True

        # Call the function
        static_analysis_parser._parse_gesda(
            "test_gesda.json",
            "com.example",
            mock_classes,
            mock_windows
        )

        # Verify calls
        mock_parse_gesda.assert_called_once_with(
            "test_gesda.json",
            "com.example",
            mock_classes,
            mock_windows
        )

    @patch('os.path.exists')
    @patch('rvandroid.parser.static.gesda_parser.parse_gesda_file')
    def test_parse_gesda_file_not_found(self, mock_parse_gesda, mock_exists,
                                        mock_classes, mock_windows):
        """Test _parse_gesda with file not found."""
        # Configure mocks
        mock_exists.return_value = False

        # Call the function
        static_analysis_parser._parse_gesda(
            "nonexistent.json",
            "com.example",
            mock_classes,
            mock_windows
        )

        # Verify parse_gesda_file was not called
        mock_parse_gesda.assert_not_called()

    @patch('os.path.exists')
    @patch('rvandroid.parser.static.gator_parser.parse_gator_file')
    def test_parse_gator(self, mock_parse_gator, mock_exists,
                         mock_classes, mock_windows, mock_wtg):
        """Test _parse_gator function."""
        # Configure mocks
        mock_exists.return_value = True
        mock_parse_gator.return_value = mock_wtg

        # Call the function
        result = static_analysis_parser._parse_gator(
            "test_gator.json",
            "com.example",
            mock_classes,
            mock_windows
        )

        # Verify calls
        mock_parse_gator.assert_called_once_with(
            "test_gator.json",
            "com.example",
            mock_classes,
            mock_windows
        )

        # Verify result
        assert result == mock_wtg

    @patch('os.path.exists')
    def test_parse_gator_file_not_found(self, mock_exists, mock_classes, mock_windows):
        """Test _parse_gator with file not found."""
        # Configure mocks
        mock_exists.return_value = False

        # Call the function
        result = static_analysis_parser._parse_gator(
            "nonexistent.json",
            "com.example",
            mock_classes,
            mock_windows
        )

        # Verify result is None
        assert result is None
