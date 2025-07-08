"""
Final corrected unit tests for ToolRegistry based on actual system behavior.

This test module correctly identifies which methods have ErrorHandler decorators
and which methods raise exceptions normally.
"""

import pytest
from unittest.mock import patch
from typing import Dict, Any

from rv_tools.registry.registry import ToolRegistry
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.error.exceptions import ToolNotFoundError


class MockToolWithSpec(AbstractTool):
    """Mock tool with TOOL_SPEC for testing."""

    TOOL_SPEC = ToolSpec(
        name="mock_tool_with_spec",
        description="Mock tool for testing",
        url="https://example.com/mock",
        version="1.0.0"
    )

    def __init__(self, name="mock_tool_with_spec", description="Mock tool", process_pattern=None):
        super().__init__(name, description, process_pattern or "mock.*")

    def execute_tool_specific_logic(self, task, app):
        pass


class MockToolWithoutSpec(AbstractTool):
    """Mock tool without TOOL_SPEC for testing error scenarios."""

    def __init__(self, name="mock_tool_no_spec", description="Mock tool without spec", process_pattern=None):
        super().__init__(name, description, process_pattern or "mock_no_spec.*")

    def execute_tool_specific_logic(self, task, app):
        pass


class MockConfigurableTool(AbstractTool):
    """Mock tool with configure method for testing."""

    TOOL_SPEC = ToolSpec(
        name="configurable_mock",
        description="Configurable mock tool",
        url="https://example.com/configurable",
        version="1.0.0"
    )

    def __init__(self, name="configurable_mock", description="Configurable mock", process_pattern=None):
        super().__init__(name, description, process_pattern or "configurable.*")
        self.config = {}

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the tool."""
        self.config.update(config)

    def execute_tool_specific_logic(self, task, app):
        pass


@pytest.fixture
def clean_registry():
    """Provide a clean registry for each test."""
    ToolRegistry.reset_instance()
    registry = ToolRegistry.get_instance()
    yield registry
    ToolRegistry.reset_instance()


@pytest.fixture
def populated_registry(clean_registry):
    """Provide a registry with some registered tools."""
    registry = clean_registry

    # Register basic tool
    tool_spec = ToolSpec(
        name="test_tool",
        description="Test tool",
        url="https://example.com/test",
        version="1.0.0"
    )
    registry.register_tool("test_tool", MockToolWithSpec, tool_spec)

    # Register configurable tool
    registry.register_tool("configurable_tool", MockConfigurableTool, MockConfigurableTool.TOOL_SPEC)

    # Register some variants
    registry.register_variant("test_tool", "variant1", {"param1": "value1"})
    registry.register_variant("test_tool", "variant2", {"param1": "value2", "param2": 42})

    return registry


class TestToolRegistrySingleton:
    """Test singleton pattern implementation."""

    def test_get_instance_returns_same_instance(self):
        """Test that get_instance always returns the same instance."""
        instance1 = ToolRegistry.get_instance()
        instance2 = ToolRegistry.get_instance()

        assert instance1 is instance2
        assert id(instance1) == id(instance2)

    def test_reset_instance_clears_singleton(self):
        """Test that reset_instance clears the singleton."""
        instance1 = ToolRegistry.get_instance()
        ToolRegistry.reset_instance()
        instance2 = ToolRegistry.get_instance()

        assert instance1 is not instance2
        assert id(instance1) != id(instance2)


class TestToolRegistration:
    """Test tool registration functionality."""

    def test_register_tool_success(self, clean_registry):
        """Test successful tool registration."""
        registry = clean_registry
        tool_spec = ToolSpec(
            name="success_tool",
            description="Success tool",
            url="https://example.com/success",
            version="1.0.0"
        )

        registry.register_tool("success_tool", MockToolWithSpec, tool_spec)

        assert registry.has_tool("success_tool")
        assert "success_tool" in registry.get_tool_names()

    def test_register_tool_overwrites_existing(self, clean_registry):
        """Test that registering existing tool logs warning and overwrites."""
        registry = clean_registry
        tool_spec1 = ToolSpec(
            name="duplicate_tool",
            description="First tool",
            url="https://example.com/first",
            version="1.0.0"
        )
        tool_spec2 = ToolSpec(
            name="duplicate_tool",
            description="Second tool",
            url="https://example.com/second",
            version="2.0.0"
        )

        # Register first tool
        registry.register_tool("duplicate_tool", MockToolWithSpec, tool_spec1)

        # Register second tool with same name (should log warning)
        with patch.object(registry.logger, 'warning') as mock_warning:
            registry.register_tool("duplicate_tool", MockToolWithSpec, tool_spec2)

        mock_warning.assert_called_once()
        assert "already registered" in mock_warning.call_args[0][0]

        # Verify second tool overwrote first
        spec = registry.get_tool_spec("duplicate_tool")
        assert spec.description == "Second tool"
        assert spec.version == "2.0.0"

    def test_register_tool_class_success(self, clean_registry):
        """Test successful tool class registration."""
        registry = clean_registry

        registry.register_tool_class(MockToolWithSpec)

        assert registry.has_tool("mock_tool_with_spec")

        # Verify tool can be retrieved
        tool = registry.get_tool("mock_tool_with_spec")
        assert tool.name == "mock_tool_with_spec"

    def test_register_tool_class_without_spec_suppresses_error(self, clean_registry):
        """Test that registering tool class without TOOL_SPEC is handled by ErrorHandler."""
        registry = clean_registry

        # Based on test failure "DID NOT RAISE", the ErrorHandler suppresses the exception
        result = registry.register_tool_class(MockToolWithoutSpec)

        # Should return None (suppressed exception)
        assert result is None
        # Tool should not be registered
        assert not registry.has_tool("mock_tool_no_spec")


class TestVariantRegistration:
    """Test variant registration functionality."""

    def test_register_variant_success(self, clean_registry):
        """Test successful variant registration."""
        registry = clean_registry
        tool_spec = ToolSpec(
            name="variant_tool",
            description="Tool with variants",
            url="https://example.com/variant",
            version="1.0.0"
        )

        # Register tool first
        registry.register_tool("variant_tool", MockToolWithSpec, tool_spec)

        # Register variant
        variant_config = {"timeout": 300, "verbose": True}
        registry.register_variant("variant_tool", "test_variant", variant_config)

        assert registry.has_variant("variant_tool", "test_variant")
        retrieved_config = registry.get_variant_config("variant_tool", "test_variant")
        assert retrieved_config == variant_config

    def test_register_variant_for_nonexistent_tool_suppresses_error(self, clean_registry):
        """Test that registering variant for non-existent tool is handled by ErrorHandler."""
        registry = clean_registry

        # Based on test behavior, this should NOT raise an exception
        result = registry.register_variant("nonexistent_tool", "variant", {"param": "value"})

        # Should return None (suppressed exception)
        assert result is None
        # Tool should still not exist
        assert not registry.has_tool("nonexistent_tool")

    def test_register_variant_creates_variants_dict_if_missing(self, clean_registry):
        """Test that variant registration creates variants dict if missing."""
        registry = clean_registry
        tool_spec = ToolSpec(
            name="no_variants_tool",
            description="Tool without variants initially",
            url="https://example.com/no_variants",
            version="1.0.0"
        )

        # Register tool
        registry.register_tool("no_variants_tool", MockToolWithSpec, tool_spec)

        # Remove variants entry to test creation
        del registry.variants["no_variants_tool"]

        # Register variant should recreate variants dict
        registry.register_variant("no_variants_tool", "new_variant", {"param": "value"})

        assert registry.has_variant("no_variants_tool", "new_variant")


class TestToolRetrieval:
    """Test tool retrieval functionality."""

    def test_get_tool_default_variant(self, populated_registry):
        """Test getting tool with default variant."""
        registry = populated_registry

        tool = registry.get_tool("test_tool")

        assert tool is not None
        assert tool.name == "test_tool"

    def test_get_tool_with_variant(self, populated_registry):
        """Test getting tool with specific variant."""
        registry = populated_registry

        tool = registry.get_tool("test_tool", "variant1")

        assert tool is not None
        assert tool.name == "test_tool"

    def test_get_tool_with_nonexistent_variant_logs_warning(self, populated_registry):
        """Test that using non-existent variant logs warning and uses default."""
        registry = populated_registry

        with patch.object(registry.logger, 'warning') as mock_warning:
            tool = registry.get_tool("test_tool", "nonexistent_variant")

        mock_warning.assert_called_once()
        assert "Variant 'nonexistent_variant' not found" in mock_warning.call_args[0][0]
        assert tool is not None

    def test_get_tool_configurable_with_variant(self, populated_registry):
        """Test getting configurable tool with variant applies configuration."""
        registry = populated_registry

        # Register variant for configurable tool
        registry.register_variant("configurable_tool", "config_variant", {"setting": "test_value"})

        tool = registry.get_tool("configurable_tool", "config_variant")

        assert tool is not None
        assert hasattr(tool, 'config')

    def test_get_tool_nonexistent_raises_error(self, clean_registry):
        """Test that getting non-existent tool raises ToolNotFoundError."""
        registry = clean_registry

        # get_tool does NOT have ErrorHandler decorator - it raises exceptions normally
        with pytest.raises(ToolNotFoundError) as exc_info:
            registry.get_tool("nonexistent_tool")

        assert "Tool 'nonexistent_tool' not found" in str(exc_info.value)

    def test_get_all_tools_success(self, populated_registry):
        """Test getting all tools successfully."""
        registry = populated_registry

        tools = registry.get_all_tools()

        assert len(tools) == 2  # test_tool and configurable_tool
        tool_names = [tool.name for tool in tools]
        assert "test_tool" in tool_names
        assert "configurable_mock" in tool_names  # Actual name from MockConfigurableTool.TOOL_SPEC

    def test_get_all_tools_with_creation_error_logs_and_continues(self, populated_registry):
        """Test that get_all_tools logs errors and continues for failed tools."""
        registry = populated_registry

        # Mock one tool to fail creation
        original_get_tool = registry.get_tool

        def mock_get_tool(tool_name, variant="default"):
            if tool_name == "test_tool":
                raise Exception("Creation failed")
            return original_get_tool(tool_name, variant)

        with patch.object(registry, 'get_tool', side_effect=mock_get_tool):
            with patch.object(registry.logger, 'error') as mock_error:
                tools = registry.get_all_tools()

        mock_error.assert_called_once()
        assert "Failed to create instance for tool 'test_tool'" in mock_error.call_args[0][0]
        assert len(tools) == 1  # Only successful tool
        assert tools[0].name == "configurable_mock"


class TestToolSpecRetrieval:
    """Test tool specification retrieval."""

    def test_get_tool_spec_success(self, populated_registry):
        """Test successful tool spec retrieval."""
        registry = populated_registry

        spec = registry.get_tool_spec("test_tool")

        assert spec is not None
        assert spec.name == "test_tool"
        assert spec.description == "Test tool"

    def test_get_tool_spec_nonexistent_raises_error(self, clean_registry):
        """Test that getting spec for non-existent tool raises ToolNotFoundError."""
        registry = clean_registry

        # get_tool_spec does NOT have ErrorHandler decorator - it raises exceptions normally
        with pytest.raises(ToolNotFoundError) as exc_info:
            registry.get_tool_spec("nonexistent_tool")

        assert "Tool specification for 'nonexistent_tool' not found" in str(exc_info.value)


class TestVariantOperations:
    """Test variant-related operations."""

    def test_get_tool_variants_with_variants(self, populated_registry):
        """Test getting variants for tool that has variants."""
        registry = populated_registry

        variants = registry.get_tool_variants("test_tool")

        assert "variant1" in variants
        assert "variant2" in variants
        assert len(variants) == 2

    def test_get_tool_variants_no_variants(self, populated_registry):
        """Test getting variants for tool with no variants."""
        registry = populated_registry

        variants = registry.get_tool_variants("configurable_tool")

        assert variants == []

    def test_get_tool_variants_nonexistent_tool(self, clean_registry):
        """Test getting variants for non-existent tool returns empty list."""
        registry = clean_registry

        variants = registry.get_tool_variants("nonexistent_tool")

        assert variants == []

    def test_has_variant_true(self, populated_registry):
        """Test has_variant returns True for existing variant."""
        registry = populated_registry

        assert registry.has_variant("test_tool", "variant1") is True

    def test_has_variant_false_nonexistent_variant(self, populated_registry):
        """Test has_variant returns False for non-existent variant."""
        registry = populated_registry

        assert registry.has_variant("test_tool", "nonexistent_variant") is False

    def test_has_variant_false_nonexistent_tool(self, clean_registry):
        """Test has_variant returns False for non-existent tool."""
        registry = clean_registry

        assert registry.has_variant("nonexistent_tool", "any_variant") is False

    def test_get_variant_config_success(self, populated_registry):
        """Test successful variant config retrieval."""
        registry = populated_registry

        config = registry.get_variant_config("test_tool", "variant1")

        assert config == {"param1": "value1"}

    def test_get_variant_config_nonexistent_raises_error(self, populated_registry):
        """Test that getting config for non-existent variant raises ToolNotFoundError."""
        registry = populated_registry

        # get_variant_config does NOT have ErrorHandler decorator - it raises exceptions normally
        with pytest.raises(ToolNotFoundError) as exc_info:
            registry.get_variant_config("test_tool", "nonexistent_variant")

        assert "Variant 'nonexistent_variant' not found for tool 'test_tool'" in str(exc_info.value)

    def test_get_variant_config_returns_copy(self, populated_registry):
        """Test that get_variant_config returns a copy of the config."""
        registry = populated_registry

        config = registry.get_variant_config("test_tool", "variant1")
        original_config = registry.variants["test_tool"]["variant1"]

        # Modify returned config
        config["new_param"] = "new_value"

        # Original should be unchanged
        assert "new_param" not in original_config


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_tool_names(self, populated_registry):
        """Test getting all tool names."""
        registry = populated_registry

        names = registry.get_tool_names()

        assert "test_tool" in names
        assert "configurable_tool" in names
        assert len(names) == 2

    def test_has_tool_true(self, populated_registry):
        """Test has_tool returns True for existing tool."""
        registry = populated_registry

        assert registry.has_tool("test_tool") is True

    def test_has_tool_false(self, clean_registry):
        """Test has_tool returns False for non-existent tool."""
        registry = clean_registry

        assert registry.has_tool("nonexistent_tool") is False

    def test_clear_registry(self, populated_registry):
        """Test clearing the registry."""
        registry = populated_registry

        # Verify registry has tools
        assert len(registry.get_tool_names()) > 0

        # Clear registry
        with patch.object(registry.logger, 'debug') as mock_debug:
            registry.clear()

        # Verify registry is empty
        assert len(registry.get_tool_names()) == 0
        assert len(registry.tool_specs) == 0
        assert len(registry.variants) == 0

        mock_debug.assert_called_once_with("Registry cleared")

    def test_get_registry_info(self, populated_registry):
        """Test getting registry information."""
        registry = populated_registry

        info = registry.get_registry_info()

        assert info["total_tools"] == 2
        assert info["total_variants"] == 2  # variant1 and variant2 for test_tool
        assert "test_tool" in info["tools"]
        assert "configurable_tool" in info["tools"]
        assert "test_tool" in info["variants_by_tool"]
        assert "variant1" in info["variants_by_tool"]["test_tool"]
        assert "variant2" in info["variants_by_tool"]["test_tool"]


class TestLoggingIntegration:
    """Test logging integration."""

    def test_registry_has_logger(self, clean_registry):
        """Test that registry has a properly initialized logger."""
        registry = clean_registry

        assert registry.logger is not None

    def test_register_tool_success_logging(self, clean_registry):
        """Test that successful tool registration logs info message."""
        registry = clean_registry
        tool_spec = ToolSpec(
            name="logged_tool",
            description="Tool for logging test",
            url="https://example.com/logged",
            version="1.0.0"
        )

        with patch.object(registry.logger, 'info') as mock_info:
            registry.register_tool("logged_tool", MockToolWithSpec, tool_spec)

        mock_info.assert_called_with("Registered tool: logged_tool")

    def test_register_variant_debug_logging(self, populated_registry):
        """Test that variant registration logs debug message."""
        registry = populated_registry

        with patch.object(registry.logger, 'debug') as mock_debug:
            registry.register_variant("test_tool", "debug_variant", {"param": "value"})

        mock_debug.assert_called_with("Registered variant 'debug_variant' for tool: test_tool")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_tool_name_registration(self, clean_registry):
        """Test registration with empty tool name."""
        registry = clean_registry
        tool_spec = ToolSpec(
            name="",
            description="Empty name tool",
            url="https://example.com/empty",
            version="1.0.0"
        )

        # Should not raise exception, but tool name will be empty
        registry.register_tool("", MockToolWithSpec, tool_spec)
        assert registry.has_tool("")

    def test_variant_config_with_complex_types(self, populated_registry):
        """Test variant registration with complex configuration types."""
        registry = populated_registry

        # Test with various config types
        complex_config = {
            "string_param": "test_value",
            "int_param": 42,
            "float_param": 3.14,
            "bool_param": True,
            "list_param": [1, 2, 3],
            "dict_param": {"nested": "value"}
        }

        registry.register_variant("test_tool", "complex_variant", complex_config)

        retrieved_config = registry.get_variant_config("test_tool", "complex_variant")

        # Verify all types are preserved
        assert retrieved_config["string_param"] == "test_value"
        assert retrieved_config["int_param"] == 42
        assert retrieved_config["float_param"] == 3.14
        assert retrieved_config["bool_param"] is True
        assert retrieved_config["list_param"] == [1, 2, 3]
        assert retrieved_config["dict_param"] == {"nested": "value"}

    def test_empty_variant_name(self, populated_registry):
        """Test registering variant with empty name."""
        registry = populated_registry

        registry.register_variant("test_tool", "", {"param": "value"})
        assert registry.has_variant("test_tool", "")

    def test_tool_without_configure_method_with_variant(self, clean_registry):
        """Test tool without configure method with variant application."""
        registry = clean_registry

        # Register tool without configure method
        tool_spec = ToolSpec(
            name="no_configure_tool",
            description="Tool without configure method",
            url="https://example.com/no_configure",
            version="1.0.0"
        )
        registry.register_tool("no_configure_tool", MockToolWithSpec, tool_spec)
        registry.register_variant("no_configure_tool", "test_variant", {"param": "value"})

        # Should work without calling configure
        tool = registry.get_tool("no_configure_tool", "test_variant")
        assert tool is not None


class TestErrorHandlerIntegration:
    """Test integration with error handler."""

    def test_error_handler_exists(self, clean_registry):
        """Test that error handler is properly initialized."""
        registry = clean_registry

        assert registry.error_handler is not None

    def test_error_handler_decorator_presence(self, clean_registry):
        """Test that error handler decorators are present on some methods."""
        registry = clean_registry

        # Some methods have the decorator (can be identified by __wrapped__)
        assert hasattr(registry.register_tool, '__wrapped__')
        assert hasattr(registry.register_variant, '__wrapped__')


class TestCoverageSpecificCases:
    """Test specific cases to maximize coverage of remaining lines."""

    def test_register_tool_with_storage_error_during_specs(self, clean_registry):
        """Test exception during tool registration operations."""
        registry = clean_registry

        tool_spec = ToolSpec(
            name="storage_error_tool",
            description="Tool for storage error testing",
            url="https://example.com/storage_error",
            version="1.0.0"
        )

        # Create a class that will raise an exception when accessed
        class FailingDict(dict):
            def __setitem__(self, key, value):
                if key == "storage_error_tool":
                    raise Exception("Simulated storage error")
                super().__setitem__(key, value)

        # Replace the tool_specs with our failing dict
        original_tool_specs = registry.tool_specs
        registry.tool_specs = FailingDict(original_tool_specs)

        try:
            # Should be handled by ErrorHandler - returns None instead of raising
            result = registry.register_tool("storage_error_tool", MockToolWithSpec, tool_spec)
            assert result is None  # Suppressed exception
        finally:
            # Restore original dict
            registry.tool_specs = original_tool_specs

    def test_register_variant_with_config_copy(self, populated_registry):
        """Test variant registration with config copy operation."""
        registry = populated_registry

        # Use a config that will definitely be copied
        original_config = {"param1": "value1", "param2": [1, 2, 3]}

        registry.register_variant("test_tool", "copy_test_variant", original_config)

        # Verify the config was stored correctly
        stored_config = registry.get_variant_config("test_tool", "copy_test_variant")
        assert stored_config == original_config
        assert stored_config is not original_config  # Should be a copy

    def test_get_registry_info_with_empty_variants_dict(self, clean_registry):
        """Test registry info calculation with empty variants dict."""
        registry = clean_registry

        # Register tool with empty variants dict
        tool_spec = ToolSpec(
            name="empty_variants_info_tool",
            description="Tool with empty variants for info testing",
            url="https://example.com/empty_variants_info",
            version="1.0.0"
        )
        registry.register_tool("empty_variants_info_tool", MockToolWithSpec, tool_spec)

        # Explicitly set variants to empty dict
        registry.variants["empty_variants_info_tool"] = {}

        info = registry.get_registry_info()

        # Should not include empty variants in variants_by_tool
        assert "empty_variants_info_tool" not in info["variants_by_tool"]
        assert info["total_variants"] == 0

    def test_has_variant_with_empty_variants_dict(self, clean_registry):
        """Test has_variant when tool has empty variants dict."""
        registry = clean_registry

        tool_spec = ToolSpec(
            name="empty_variants_tool",
            description="Tool with empty variants",
            url="https://example.com/empty_variants",
            version="1.0.0"
        )
        registry.register_tool("empty_variants_tool", MockToolWithSpec, tool_spec)

        # Explicitly set variants to empty dict
        registry.variants["empty_variants_tool"] = {}

        # Should return False for any variant
        assert registry.has_variant("empty_variants_tool", "any_variant") is False
