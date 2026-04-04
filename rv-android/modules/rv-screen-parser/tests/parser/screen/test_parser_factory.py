"""
Unit tests for the ParserFactory.

This module tests the functionality of the ParserFactory, ensuring that it can
correctly create parser instances, register new parser types, and handle
errors gracefully.

### Test Strategy:
- Test the creation of default parsers (DroidBot and UIAutomator).
- Test the registration of a custom parser type.
- Test that the factory raises a ValueError for unknown parser types.
- Test that the factory raises a TypeError for invalid parser classes.
- Test the retrieval of available parser types.
"""

import pytest
from rv_screen_parser.constants import ScreenParserType
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.droidbot.droidbot_parser import DroidBotParser
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser


class TestParserFactory:
    """Test suite for the ParserFactory."""

    def test_create_droidbot_parser(self):
        """Test the creation of a DroidBotParser."""
        parser = ParserFactory.create(ScreenParserType.DROIDBOT)
        assert isinstance(parser, DroidBotParser)

    def test_create_uiautomator_parser(self):
        """Test the creation of a UIAutomator2Parser."""
        parser = ParserFactory.create(ScreenParserType.UIAUTOMATOR)
        assert isinstance(parser, UIAutomator2Parser)

    def test_create_unknown_parser_raises_value_error(self):
        """Test that creating an unknown parser raises a ValueError."""
        with pytest.raises(ValueError):
            ParserFactory.create("unknown_parser")

    def test_register_invalid_parser_raises_type_error(self):
        """Test that registering an invalid parser raises a TypeError."""
        class InvalidParser:
            pass

        with pytest.raises(TypeError):
            ParserFactory.register_parser_type("invalid", InvalidParser)

    def test_get_available_types(self):
        """Test the retrieval of available parser types."""
        available_types = ParserFactory.get_available_types()
        assert ScreenParserType.DROIDBOT in available_types
        assert ScreenParserType.UIAUTOMATOR in available_types
