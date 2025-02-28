# rvandroid/parser/parser_factory.py
from enum import Enum
from typing import Dict, Type, Optional

from rvandroid.parser.abstract_parser import AbstractScreenParser


class ParserType(Enum):
    """Enumeration of supported parser types"""
    DROIDBOT = "droidbot"
    UIAUTOMATOR = "uiautomator"


class ParserFactory:
    """
    Factory for creating parser instances.
    Centralizes the creation of different parser types.
    """

    # Registry of parser types and their implementations
    _REGISTRY: Dict[ParserType, Type[AbstractScreenParser]] = {}

    @classmethod
    def register_default_parsers(cls):
        """Register the default parser implementations."""
        from rvandroid.parser.droidbot.droidbot_parser import DroidBotParser
        from rvandroid.parser.uiautomator.uiautomator_parser import UIAutomator2Parser

        cls.register_parser_type(ParserType.DROIDBOT, DroidBotParser)
        cls.register_parser_type(ParserType.UIAUTOMATOR, UIAutomator2Parser)

    @staticmethod
    def create(parser_type: ParserType) -> AbstractScreenParser:
        """
        Create a parser instance of the specified type.

        Args:
            parser_type: Type of parser to create

        Returns:
            Parser instance

        Raises:
            ValueError: If parser_type is invalid
        """
        # Register default parsers if registry is empty
        if not ParserFactory._REGISTRY:
            ParserFactory.register_default_parsers()

        if parser_type not in ParserFactory._REGISTRY:
            raise ValueError(f"Unknown parser type: {parser_type}")

        parser_class = ParserFactory._REGISTRY[parser_type]
        return parser_class()

    @staticmethod
    def get_available_types() -> Dict[ParserType, Type[AbstractScreenParser]]:
        """
        Get all available parser types.

        Returns:
            Dictionary of parser types and their implementations
        """
        # Register default parsers if registry is empty
        if not ParserFactory._REGISTRY:
            ParserFactory.register_default_parsers()

        return ParserFactory._REGISTRY.copy()

    @staticmethod
    def register_parser_type(parser_type: ParserType, parser_class: Type[AbstractScreenParser]) -> None:
        """
        Register a new parser type.

        Args:
            parser_type: Type of the parser
            parser_class: Parser implementation class

        Raises:
            TypeError: If parser_class is not a subclass of AbstractScreenParser
        """
        if not issubclass(parser_class, AbstractScreenParser):
            raise TypeError(f"Parser class must be a subclass of AbstractScreenParser")

        ParserFactory._REGISTRY[parser_type] = parser_class

    @staticmethod
    def get_parser_by_name(name: str) -> Optional[Type[AbstractScreenParser]]:
        """
        Get parser implementation by name.

        Args:
            name: Parser type name

        Returns:
            Parser implementation class or None if not found
        """
        # Register default parsers if registry is empty
        if not ParserFactory._REGISTRY:
            ParserFactory.register_default_parsers()

        try:
            parser_type = ParserType(name)
            return ParserFactory._REGISTRY.get(parser_type)
        except ValueError:
            return None
