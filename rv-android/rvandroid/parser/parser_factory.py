from enum import Enum
from typing import Dict, Type

from rvandroid.parser.abstract_parser import AbstractStateParser
from rvandroid.parser.droidbot.droidbot_parser import DroidBotParser
from rvandroid.parser.uiautomator.uiautomator_parser import UIAutomator2Parser


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
    _REGISTRY: Dict[ParserType, Type[AbstractStateParser]] = {
        ParserType.DROIDBOT: DroidBotParser,
        ParserType.UIAUTOMATOR: UIAutomator2Parser
    }

    @staticmethod
    def create(parser_type: ParserType) -> AbstractStateParser:
        """
        Create a parser instance of the specified type.

        Args:
            parser_type: Type of parser to create

        Returns:
            Parser instance

        Raises:
            ValueError: If parser_type is invalid
        """
        if parser_type not in ParserFactory._REGISTRY:
            raise ValueError(f"Unknown parser type: {parser_type}")

        parser_class = ParserFactory._REGISTRY[parser_type]
        return parser_class()

    @staticmethod
    def get_available_types() -> Dict[ParserType, Type[AbstractStateParser]]:
        """
        Get all available parser types.

        Returns:
            Dictionary of parser types and their implementations
        """
        return ParserFactory._REGISTRY.copy()

    @staticmethod
    def register_parser_type(parser_type: ParserType, parser_class: Type[AbstractStateParser]) -> None:
        """
        Register a new parser type.

        Args:
            parser_type: Type of the parser
            parser_class: Parser implementation class
        """
        ParserFactory._REGISTRY[parser_type] = parser_class
