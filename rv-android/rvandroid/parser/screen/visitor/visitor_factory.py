# rvandroid/parser/screen/visitor/visitor_factory.py
from typing import Dict, Type, Optional

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.visitor.base_visitor import BaseScreenVisitor
from rvandroid.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rvandroid.parser.screen.visitor.enhanced_visitor import NewEnhancedTextVisitor
from rvandroid.parser.screen.visitor.text_visitor import EnhancedTextVisitor


class VisitorFactory:
    """
    Factory for creating screen visitor instances.
    Centralizes the creation of different visitor types.
    """

    # Registry of visitor types and their implementations
    _REGISTRY: Dict[str, Type[BaseScreenVisitor]] = {
        "enhanced_text": EnhancedTextVisitor,
        "basic_text": BasicTextVisitor,
        "detailed_text": NewEnhancedTextVisitor,
        # Add other visitor implementations as needed
    }

    @classmethod
    def create(
            cls,
            visitor_type: str = "enhanced_text",
            static_data: Optional[StaticAnalysisData] = None,
            activity: str = "",
            **kwargs
    ) -> BaseScreenVisitor:
        """
        Create a visitor instance of the specified type.

        Args:
            visitor_type: Type of visitor to create
            static_data: Static analysis data (optional)
            activity: Current activity name
            **kwargs: Additional arguments to pass to the visitor constructor

        Returns:
            Visitor instance

        Raises:
            ValueError: If visitor_type is invalid
        """
        if visitor_type not in cls._REGISTRY:
            raise ValueError(f"Unknown visitor type: {visitor_type}. Options: {list(cls._REGISTRY.keys())}")

        visitor_class = cls._REGISTRY[visitor_type]
        return visitor_class(static_data, activity, **kwargs)

    @classmethod
    def get_visitor_class(cls, visitor_type: str = "enhanced_text") -> Type[BaseScreenVisitor]:
        """
        Get the visitor class for a specified type.

        Args:
            visitor_type: Type of visitor

        Returns:
            Visitor class

        Raises:
            ValueError: If visitor_type is invalid
        """
        if visitor_type not in cls._REGISTRY:
            raise ValueError(f"Unknown visitor type: {visitor_type}. Options: {list(cls._REGISTRY.keys())}")

        return cls._REGISTRY[visitor_type]

    @staticmethod
    def register_visitor_type(name: str, visitor_class: Type[BaseScreenVisitor]) -> None:
        """
        Register a new visitor type.

        Args:
            name: Name of the visitor type
            visitor_class: Visitor implementation class

        Raises:
            TypeError: If visitor is not a subclass of BaseScreenVisitor
        """
        if not issubclass(visitor_class, BaseScreenVisitor):
            raise TypeError(f"Visitor class must be a subclass of BaseScreenVisitor")

        VisitorFactory._REGISTRY[name] = visitor_class

    @staticmethod
    def get_available_types() -> Dict[str, Type[BaseScreenVisitor]]:
        """
        Get all available visitor types.

        Returns:
            Dictionary of visitor types and their classes
        """
        return VisitorFactory._REGISTRY.copy()
