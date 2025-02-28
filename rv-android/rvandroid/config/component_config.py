from typing import Type, Dict, Any, Optional, Callable

from rvandroid.llm.prompt_strategy import PromptStrategy
from rvandroid.llm.prompt_strategy_basic import BasicPromptStrategy
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.abstract_parser import AbstractScreenParser
from rvandroid.parser.droidbot.droidbot_parser import DroidBotParser
from rvandroid.parser.visitor.base_visitor import BaseScreenVisitor
from rvandroid.parser.visitor.text_visitor import EnhancedTextVisitor


class ComponentConfig:
    """
    Configuration manager for RV-Android components.
    Provides a centralized way to configure and inject components like parsers, visitors,
    and prompt strategies.
    """

    def __init__(self):
        self.parser_class: Optional[Type[AbstractScreenParser]] = DroidBotParser
        self.visitor_class: Optional[Type[BaseScreenVisitor]] = EnhancedTextVisitor
        self.strategy_class: Optional[Type[PromptStrategy]] = BasicPromptStrategy
        self.parser_kwargs: Dict[str, Any] = {}
        self.visitor_kwargs: Dict[str, Any] = {}
        self.strategy_kwargs: Dict[str, Any] = {}

    def set_parser(self, parser_class: Type[AbstractScreenParser], **kwargs) -> 'ComponentConfig':
        """Configure which parser implementation to use."""
        self.parser_class = parser_class
        self.parser_kwargs = kwargs
        return self
        
    def set_visitor(self, visitor_class: Type[BaseScreenVisitor], **kwargs) -> 'ComponentConfig':
        """Configure which visitor implementation to use."""
        self.visitor_class = visitor_class
        self.visitor_kwargs = kwargs
        return self
        
    def set_strategy(self, strategy_class: Type[PromptStrategy], **kwargs) -> 'ComponentConfig':
        """Configure which prompt strategy implementation to use."""
        self.strategy_class = strategy_class
        self.strategy_kwargs = kwargs
        return self
    
    def create_parser(self) -> AbstractScreenParser:
        """Create an instance of the configured parser."""
        if not self.parser_class:
            raise ValueError("Parser class not configured")
        return self.parser_class(**self.parser_kwargs)
    
    def create_visitor(self, static_data: Optional["StaticAnalysisData"], activity: str) -> BaseScreenVisitor:
        """Create an instance of the configured visitor."""
        if not self.visitor_class:
            raise ValueError("Visitor class not configured")
        kwargs = self.visitor_kwargs.copy()
        return self.visitor_class(static_data, activity, **kwargs)
    
    def create_strategy(self, static_data: Optional["StaticAnalysisData"] = None) -> PromptStrategy:
        """Create an instance of the configured prompt strategy."""
        if not self.strategy_class:
            raise ValueError("Strategy class not configured")
        kwargs = self.strategy_kwargs.copy()
        return self.strategy_class(static_data, **kwargs)
    
