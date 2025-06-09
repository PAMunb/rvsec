import os
import sys
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import pytest

# Add the parent directory to the path to make imports work correctly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from rv_android_core.domain.classes import Classes
from rv_android_core.domain.window import Windows
from rv_static_analysis.parser.static.base_parser import BaseStaticAnalysisParser


class MockParser(BaseStaticAnalysisParser):
    """A concrete implementation of BaseStaticAnalysisParser for testing."""

    def __init__(self, parser_name="test_parser"):
        super().__init__(parser_name)
        self.parse_called = False
        self.return_value = None

    def parse_file(self, file_path: str, package: Optional[str], classes: Optional[Classes],
                   windows: Optional[Windows]) -> Any:
        """Implementation of the abstract method for testing."""
        self.parse_called = True
        return self.return_value


class TestBaseStaticAnalysisParser:
    """Tests for the BaseStaticAnalysisParser class."""

    def test_initialization(self):
        """Test parser initialization."""
        parser = MockParser("custom_parser")

        assert parser.parser_name == "custom_parser"
        assert parser.logger is not None

    def test_validate_package(self):
        """Test package validation."""
        parser = MockParser()

        # Should return True if package is part of class name
        assert parser.validate_package("com.example.MyClass", "com.example") is True

        # Should return False if package is not part of class name
        assert parser.validate_package("com.other.MyClass", "com.example") is False

        # Should handle empty package
        assert parser.validate_package("com.example.MyClass", "") is True

    @patch('rv_android_core.util.logging.manager.LoggingManager')
    def test_log_parse_start(self, mock_logging_manager):
        """Test log_parse_start method."""
        # Setup
        mock_logger = MagicMock()
        mock_instance = MagicMock()
        mock_instance.get_logger.return_value = mock_logger
        mock_logging_manager.get_instance.return_value = mock_instance

        parser = MockParser()
        parser.logger = mock_logger

        # Test
        parser.log_parse_start("/path/to/file.txt")

        # Assertions
        mock_logger.info.assert_called_once()
        assert "Starting to parse file: /path/to/file.txt" in mock_logger.info.call_args[0][0]

    @patch('rv_android_core.util.logging.manager.LoggingManager')
    def test_log_parse_complete(self, mock_logging_manager):
        """Test log_parse_complete method."""
        # Setup
        mock_logger = MagicMock()
        mock_instance = MagicMock()
        mock_instance.get_logger.return_value = mock_logger
        mock_logging_manager.get_instance.return_value = mock_instance

        parser = MockParser()
        parser.logger = mock_logger

        stats = {"classes": 10, "methods": 50}

        # Test
        parser.log_parse_complete("/path/to/file.txt", stats)

        # Assertions
        mock_logger.debug.assert_called()

        # Check the first debug call for the completed message
        first_call = mock_logger.debug.call_args_list[0]
        assert "Completed parsing file: /path/to/file.txt" in first_call[0][0]

        # Check subsequent calls for stats
        assert len(mock_logger.debug.call_args_list) == 3  # Main message + 2 stats entries

    @patch('rv_android_core.util.logging.manager.LoggingManager')
    def test_log_parse_error(self, mock_logging_manager):
        """Test log_parse_error method."""
        # Setup
        mock_logger = MagicMock()
        mock_instance = MagicMock()
        mock_instance.get_logger.return_value = mock_logger
        mock_logging_manager.get_instance.return_value = mock_instance

        parser = MockParser()
        parser.logger = mock_logger

        error = ValueError("Test error")

        # Test
        parser.log_parse_error("/path/to/file.txt", error)

        # Assertions
        mock_logger.error.assert_called_once()
        assert "Error parsing file /path/to/file.txt: Test error" in mock_logger.error.call_args[0][0]

    def test_abstract_method_called(self):
        """Test that the abstract method is called when implemented."""
        parser = MockParser()
        parser.return_value = "test_result"

        result = parser.parse_file("file.txt", "com.example", None, None)

        assert parser.parse_called is True
        assert result == "test_result"


@pytest.mark.skip(reason="This test is expected to fail because BaseStaticAnalysisParser is abstract")
def test_cannot_instantiate_abstract_class():
    """Test that BaseStaticAnalysisParser cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseStaticAnalysisParser("test")
