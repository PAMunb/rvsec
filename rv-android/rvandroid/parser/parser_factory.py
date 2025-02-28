# rvandroid/parser/parser_factory.py
from enum import Enum
from typing import Dict, Type, Optional, Callable

from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.abstract_parser import AbstractScreenParser
from rvandroid.parser.visitor.base_visitor import BaseScreenVisitor


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

    @classmethod
    def create(
            cls, 
            parser_type: ParserType, 
            visitor_factory: Optional[Callable[[Optional["StaticAnalysisData"], str], BaseScreenVisitor]] = None
    ) -> AbstractScreenParser:
        """
        Create a parser instance of the specified type.

        Args:
            parser_type: Type of parser to create
            visitor_factory: Optional factory function to create visitor instances

        Returns:
            Parser instance

        Raises:
            ValueError: If parser_type is invalid
        """
        # Register default parsers if registry is empty
        if not cls._REGISTRY:
            cls.register_default_parsers()

        if parser_type not in cls._REGISTRY:
            raise ValueError(f"Unknown parser type: {parser_type}")

        parser_class = cls._REGISTRY[parser_type]
        return parser_class(visitor_factory)

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
