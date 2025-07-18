"""
Parser factory for dynamic screen parser instantiation in monitored operations framework.

Provides centralized factory pattern implementation for creating appropriate parser instances
based on input source type, enabling seamless integration with diverse monitoring tools.
"""

from enum import Enum
from typing import Dict, Type, Optional

from rv_screen_parser.constants import ScreenParserType
from rv_screen_parser.parser.screen.base_parser import BaseScreenParser
from rv_screen_parser.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor


class ParserFactory:
    """
    Factory pattern implementation for dynamic parser instantiation in monitored operations.

    ### Architectural Decisions:
    - Implements factory pattern for dynamic parser selection based on monitoring tool output format
    - Uses registry pattern for extensible parser type management and registration
    - Provides type-safe parser instantiation with comprehensive error handling
    - Supports dependency injection through visitor class parameterization
    - Enables runtime parser configuration for diverse monitoring scenarios

    ### Role in the System:
    - Serves as the central entry point for parser instantiation across the framework
    - Facilitates seamless integration with different Android monitoring tools and their outputs
    - Provides abstraction layer for parser selection logic and configuration management
    - Enables extensible architecture for adding new parser implementations without code modification
    - Supports polymorphic parser usage through unified BaseScreenParser interface

    ### Design Note - Extensibility:
    The factory uses a registry pattern to enable dynamic parser registration.
    New parser types can be added by implementing BaseScreenParser and registering
    through register_parser_type() without modifying existing factory code.
    """

    # Registry of parser types and their implementations
    _REGISTRY: Dict[ScreenParserType, Type[BaseScreenParser]] = {}

    @classmethod
    def register_default_parsers(cls):
        """Register the default parser implementations."""
        from rv_screen_parser.parser.screen.droidbot.droidbot_parser import DroidBotParser
        from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser

        # TODO rever tipo do parametro ... usar enum ou str?
        cls.register_parser_type(ScreenParserType.DROIDBOT, DroidBotParser)
        cls.register_parser_type(ScreenParserType.UIAUTOMATOR, UIAutomator2Parser)

    @classmethod
    def create(
            cls,
            parser_type: ScreenParserType,
            visitor_class: Optional[Type[AbstractScreenVisitor]] = None
    ) -> BaseScreenParser:
        """
        Create a parser instance of the specified type.

        Args:
            parser_type: Type of parser to create
            visitor_class: Optional visitor class to use for parsing

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
        return parser_class(visitor_class)

    @staticmethod
    def get_available_types() -> Dict[ScreenParserType, Type[BaseScreenParser]]:
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
    def register_parser_type(parser_type: ScreenParserType, parser_class: Type[BaseScreenParser]) -> None:
        """
        Register a new parser type.

        Args:
            parser_type: Type of the parser
            parser_class: Parser implementation class

        Raises:
            TypeError: If parser is not a subclass of BaseScreenParser
        """
        if not issubclass(parser_class, BaseScreenParser):
            raise TypeError(f"Parser class must be a subclass of BaseScreenParser")

        ParserFactory._REGISTRY[parser_type] = parser_class
