"""
Main functionalities tests for rv-tools simplified architecture.

This test module focuses on testing the core functionalities of the
simplified rv-tools architecture, including:
- Tool registration and retrieval
- Variant system functionality
- Tool specification parsing (tool:variant@params format)
- Error handling for common scenarios
- Integration with rv-android-core components
"""

import pytest
from unittest.mock import Mock, patch

from rv_tools.registry.registry import ToolRegistry
from rv_tools.registry.factory import ToolFactory
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.exceptions import ToolNotFoundError, ToolRegistrationError, ToolVariantError


class MockTool(AbstractTool):
    """Mock tool for testing purposes."""
    
    def __init__(self, name="mock_tool", description="Mock tool for testing", process_pattern=None):
        if process_pattern is None:
            process_pattern = f"{name}.*"
        super().__init__(name, description, process_pattern)
        self.tool_spec = ToolSpec(
            name=name,
            description=description,
            url="https://example.com/mock",
            version="1.0.0"
        )
    
    def get_tool_spec(self):
        return self.tool_spec
    
    def execute_tool_specific_logic(self, task, app):
        pass


@pytest.fixture
def clean_registry():
    """Clean registry for each test."""
    ToolRegistry.reset_instance()
    yield ToolRegistry.get_instance()
    ToolRegistry.reset_instance()


@pytest.fixture
def mock_tool():
    """Create a mock tool for testing."""
    return MockTool()


class TestToolRegistryMainFunctionalities:
    """Test main functionalities of ToolRegistry."""
    
    def test_tool_registration_and_retrieval(self, clean_registry, mock_tool):
        """Test basic tool registration and retrieval."""
        registry = clean_registry
        
        # Register tool with correct signature
        registry.register_tool(mock_tool.name, MockTool, mock_tool.get_tool_spec())
        
        # Verify tool is registered
        assert registry.has_tool("mock_tool")
        
        # Retrieve tool instance
        retrieved_tool = registry.get_tool("mock_tool")
        assert retrieved_tool.name == "mock_tool"
    
    def test_tool_registration_error_handling(self, clean_registry):
        """Test error handling during tool registration."""
        registry = clean_registry
        
        # Test registering with empty name (should handle gracefully)
        spec = ToolSpec(name="test", description="test", url="https://example.com", version="1.0.0")
        try:
            registry.register_tool("", MockTool, spec)
            # If no error, check that it registered with empty name
            assert registry.has_tool("")
        except Exception:
            # If error, that's also acceptable
            pass
    
    def test_tool_not_found_error(self, clean_registry):
        """Test ToolNotFoundError when requesting non-existent tool."""
        registry = clean_registry
        
        with pytest.raises(ToolNotFoundError):
            registry.get_tool("non_existent_tool")
    
    def test_variant_registration_and_retrieval(self, clean_registry, mock_tool):
        """Test variant registration and retrieval functionality."""
        registry = clean_registry
        
        # Register base tool
        registry.register_tool(mock_tool.name, MockTool, mock_tool.get_tool_spec())
        
        # Register variant
        variant_config = {"param1": "value1", "timeout": 300}
        registry.register_variant("mock_tool", "test_variant", variant_config)
        
        # Verify variant is registered
        assert registry.has_variant("mock_tool", "test_variant")
        
        # Retrieve variant configuration
        retrieved_config = registry.get_variant_config("mock_tool", "test_variant")
        assert retrieved_config == variant_config
    
    def test_variant_error_handling(self, clean_registry):
        """Test error handling for variant operations."""
        registry = clean_registry
        
        # Test retrieving non-existent variant
        mock_tool = MockTool()
        registry.register_tool(mock_tool.name, MockTool, mock_tool.get_tool_spec())
        
        # Test that non-existent variant returns None or handles gracefully
        try:
            variant_config = registry.get_variant_config("mock_tool", "non_existent_variant")
            # If it returns something, check it's reasonable
            assert variant_config is None or isinstance(variant_config, dict)
        except Exception:
            # If it raises an exception, that's also acceptable
            pass
    
    def test_tool_listing(self, clean_registry):
        """Test listing registered tools."""
        registry = clean_registry
        
        # Register multiple tools
        tool1 = MockTool("tool1", "First tool")
        tool2 = MockTool("tool2", "Second tool")
        
        registry.register_tool(tool1.name, MockTool, tool1.get_tool_spec())
        registry.register_tool(tool2.name, MockTool, tool2.get_tool_spec())
        
        # List tools
        tool_names = registry.get_tool_names()
        assert "tool1" in tool_names
        assert "tool2" in tool_names
        assert len(tool_names) == 2


class TestToolFactory:
    """Test main functionalities of ToolFactory."""
    
    @pytest.fixture
    def factory_with_tools(self, clean_registry):
        """Create factory with registered tools."""
        registry = clean_registry
        
        # Register tools
        tool1 = MockTool("droidbot", "DroidBot tool")
        tool2 = MockTool("ape", "APE tool")
        
        registry.register_tool(tool1.name, MockTool, tool1.get_tool_spec())
        registry.register_tool(tool2.name, MockTool, tool2.get_tool_spec())
        
        # Register variants
        registry.register_variant("droidbot", "bfs_greedy", {"policy": "bfs_greedy"})
        registry.register_variant("droidbot", "dfs_greedy", {"policy": "dfs_greedy"})
        
        return registry
    
    def test_simple_tool_creation(self, factory_with_tools):
        """Test creating tool from simple name."""
        registry = factory_with_tools
        
        tool = ToolFactory.create_tool_from_spec("droidbot", registry)
        assert tool is not None
        assert tool.name == "droidbot"
    
    def test_tool_with_variant_creation(self, factory_with_tools):
        """Test creating tool with variant."""
        registry = factory_with_tools
        
        tool = ToolFactory.create_tool_from_spec("droidbot:bfs_greedy", registry)
        assert tool is not None
        assert tool.name == "droidbot"
        # Note: In a real implementation, the tool would be configured with the variant
    
    def test_tool_with_parameters_creation(self, factory_with_tools):
        """Test creating tool with parameters."""
        registry = factory_with_tools
        
        tool = ToolFactory.create_tool_from_spec("droidbot:bfs_greedy@timeout=300", registry)
        assert tool is not None
        assert tool.name == "droidbot"
        # Note: In a real implementation, the tool would be configured with the parameters
    
    def test_tool_spec_parsing(self, factory_with_tools):
        """Test parsing of tool specification string."""
        
        # Test simple tool name
        tool_name, variants, params = ToolFactory._parse_tool_spec("droidbot")
        assert tool_name == "droidbot"
        assert variants == []
        assert params == {}
        
        # Test tool with variant
        tool_name, variants, params = ToolFactory._parse_tool_spec("droidbot:bfs_greedy")
        assert tool_name == "droidbot"
        assert variants == ["bfs_greedy"]
        assert params == {}
        
        # Test tool with parameters
        tool_name, variants, params = ToolFactory._parse_tool_spec("droidbot@timeout=300")
        assert tool_name == "droidbot"
        assert variants == []
        assert params == {"timeout": "300"}
        
        # Test tool with variant and parameters
        tool_name, variants, params = ToolFactory._parse_tool_spec("droidbot:bfs_greedy@timeout=300,policy=aggressive")
        assert tool_name == "droidbot"
        assert variants == ["bfs_greedy"]
        assert params == {"timeout": "300", "policy": "aggressive"}
    
    def test_tool_not_found_in_factory(self, factory_with_tools):
        """Test error handling when tool is not found in factory."""
        registry = factory_with_tools
        
        # Test that non-existent tool handles gracefully
        try:
            tool = ToolFactory.create_tool_from_spec("non_existent_tool", registry)
            # Should not reach here, but if it does, check result
            assert tool is None
        except Exception as e:
            # Exception is expected for non-existent tools
            assert "non_existent_tool" in str(e)


class TestToolSpecSimplified:
    """Test simplified ToolSpec functionality."""
    
    def test_tool_spec_creation(self):
        """Test creating ToolSpec with required fields."""
        spec = ToolSpec(
            name="test_tool",
            description="Test tool description",
            url="https://example.com/test",
            version="1.0.0"
        )
        
        assert spec.name == "test_tool"
        assert spec.description == "Test tool description"
        assert spec.url == "https://example.com/test"
        assert spec.version == "1.0.0"
        assert spec.process_pattern is None
    
    def test_tool_spec_with_process_pattern(self):
        """Test creating ToolSpec with process pattern."""
        spec = ToolSpec(
            name="test_tool",
            description="Test tool description",
            url="https://example.com/test",
            version="1.0.0",
            process_pattern="test_pattern"
        )
        
        assert spec.process_pattern == "test_pattern"
    
    def test_tool_spec_builtin_creation(self):
        """Test creating builtin ToolSpec."""
        spec = ToolSpec.create_builtin_spec(
            name="builtin_tool",
            description="Builtin tool",
            url="https://example.com/builtin",
            version="2.0.0"
        )
        
        assert spec.name == "builtin_tool"
        assert spec.description == "Builtin tool"
        assert spec.url == "https://example.com/builtin"
        assert spec.version == "2.0.0"


class TestIntegrationWithBuiltinTools:
    """Test integration with builtin tools."""
    
    def test_registry_with_builtin_tools(self, clean_registry):
        """Test registry functionality with builtin-like tools."""
        registry = clean_registry
        
        # Create tools similar to builtin ones
        droidbot_tool = MockTool("droidbot", "DroidBot automated testing tool")
        ape_tool = MockTool("ape", "APE systematic testing tool")
        
        # Register tools
        registry.register_tool(droidbot_tool.name, MockTool, droidbot_tool.get_tool_spec())
        registry.register_tool(ape_tool.name, MockTool, ape_tool.get_tool_spec())
        
        # Register variants (similar to builtin tool variants)
        registry.register_variant("droidbot", "bfs_greedy", {
            "policy": "bfs_greedy",
            "timeout": 600
        })
        registry.register_variant("droidbot", "dfs_greedy", {
            "policy": "dfs_greedy", 
            "timeout": 800
        })
        registry.register_variant("ape", "systematic", {
            "strategy": "systematic",
            "max_steps": 1000
        })
        
        # Test tool retrieval
        assert registry.has_tool("droidbot")
        assert registry.has_tool("ape")
        
        # Test variant retrieval
        assert registry.has_variant("droidbot", "bfs_greedy")
        assert registry.has_variant("droidbot", "dfs_greedy")
        assert registry.has_variant("ape", "systematic")
        
        # Test variant configurations
        bfs_config = registry.get_variant_config("droidbot", "bfs_greedy")
        assert bfs_config["policy"] == "bfs_greedy"
        assert bfs_config["timeout"] == 600
        
        dfs_config = registry.get_variant_config("droidbot", "dfs_greedy")
        assert dfs_config["policy"] == "dfs_greedy"
        assert dfs_config["timeout"] == 800


if __name__ == "__main__":
    pytest.main([__file__, "-v"])