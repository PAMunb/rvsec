"""
Basic tests for rv-tools module.
"""

from rv_tools.registry.registry import ToolRegistry
from rv_tools.registry.factory import ToolFactory


class TestToolRegistry:
    """Basic tests for ToolRegistry."""
    
    def test_registry_initialization(self):
        """Test that ToolRegistry initializes correctly."""
        registry = ToolRegistry()
        assert registry is not None
        
    def test_registry_is_singleton(self):
        """Test that ToolRegistry follows singleton pattern."""
        registry1 = ToolRegistry.get_instance()
        registry2 = ToolRegistry.get_instance()
        assert registry1 is registry2


class TestToolFactory:
    """Basic tests for ToolFactory."""
    
    def test_factory_initialization(self):
        """Test that ToolFactory initializes correctly."""
        registry = ToolRegistry.get_instance()
        factory = ToolFactory(registry)
        assert factory is not None
        assert factory.registry == registry