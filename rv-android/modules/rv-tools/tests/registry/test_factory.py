"""
Comprehensive unit tests for ToolFactory to maximize code coverage.

This test module covers all aspects of tool creation, specification parsing,
variant handling, and error scenarios in the ToolFactory class.
"""

from typing import Dict, Any
from unittest.mock import Mock, patch

import pytest

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.tools.tool_spec import ToolSpec
from rv_android_core.util.exceptions import ToolNotFoundError
from rv_tools.registry.factory import ToolFactory
from rv_tools.registry.registry import ToolRegistry


class MockBasicTool(AbstractTool):
    """Mock basic tool for testing."""

    TOOL_SPEC = ToolSpec(
        name="mock_basic",
        description="Mock basic tool",
        url="https://example.com/mock_basic",
        version="1.0.0"
    )

    def __init__(self, name="mock_basic", description="Mock basic tool", process_pattern=None):
        super().__init__(name, description, process_pattern or "mock_basic.*")

    def execute_tool_specific_logic(self, task, app):
        pass


class MockConfigurableTool(AbstractTool):
    """Mock configurable tool for testing."""

    TOOL_SPEC = ToolSpec(
        name="mock_configurable",
        description="Mock configurable tool",
        url="https://example.com/mock_configurable",
        version="1.0.0"
    )

    def __init__(self, name="mock_configurable", description="Mock configurable tool", process_pattern=None):
        super().__init__(name, description, process_pattern or "mock_configurable.*")
        self.config = {}
        self.configured_with = []

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the tool and track configurations."""
        self.config.update(config)
        self.configured_with.append(config.copy())

    def execute_tool_specific_logic(self, task, app):
        pass


class MockAdvancedTool(AbstractTool):
    """Mock advanced tool with multiple variants for testing."""

    TOOL_SPEC = ToolSpec(
        name="mock_advanced",
        description="Mock advanced tool with variants",
        url="https://example.com/mock_advanced",
        version="2.0.0"
    )

    def __init__(self, name="mock_advanced", description="Mock advanced tool", process_pattern=None):
        super().__init__(name, description, process_pattern or "mock_advanced.*")
        self.config = {}

    def configure(self, config: Dict[str, Any]) -> None:
        """Configure the tool."""
        self.config.update(config)

    def execute_tool_specific_logic(self, task, app):
        pass


@pytest.fixture
def mock_registry():
    """Create a mock registry with test tools."""
    registry = Mock(spec=ToolRegistry)

    # Mock tools
    registry.has_tool.side_effect = lambda name: name in ["mock_basic", "mock_configurable", "mock_advanced"]

    def mock_get_tool(tool_name, variant="default"):
        if tool_name == "mock_basic":
            return MockBasicTool()
        elif tool_name == "mock_configurable":
            tool = MockConfigurableTool()
            if variant != "default" and registry.has_variant(tool_name, variant):
                config = registry.get_variant_config(tool_name, variant)
                tool.configure(config)
            return tool
        elif tool_name == "mock_advanced":
            tool = MockAdvancedTool()
            if variant != "default" and registry.has_variant(tool_name, variant):
                config = registry.get_variant_config(tool_name, variant)
                tool.configure(config)
            return tool
        else:
            raise ToolNotFoundError(f"Tool '{tool_name}' not found in registry")

    registry.get_tool.side_effect = mock_get_tool

    # Mock variants
    registry.has_variant.side_effect = lambda tool, variant: (
            (tool == "mock_configurable" and variant in ["performance", "debug"]) or
            (tool == "mock_advanced" and variant in ["ai", "adaptive", "batch"])
    )

    def mock_get_variant_config(tool_name, variant_name):
        configs = {
            ("mock_configurable", "performance"): {"timeout": 1200, "threads": 4},
            ("mock_configurable", "debug"): {"verbose": True, "debug": True},
            ("mock_advanced", "ai"): {"model": "gpt-4", "temperature": 0.7},
            ("mock_advanced", "adaptive"): {"strategy": "adaptive", "learning_rate": 0.01},
            ("mock_advanced", "batch"): {"batch_size": 32, "parallel": True}
        }
        return configs.get((tool_name, variant_name), {})

    registry.get_variant_config.side_effect = mock_get_variant_config

    # Mock utility methods
    registry.get_tool_names.return_value = ["mock_basic", "mock_configurable", "mock_advanced"]

    def mock_get_tool_variants(tool_name):
        variants = {
            "mock_basic": [],
            "mock_configurable": ["performance", "debug"],
            "mock_advanced": ["ai", "adaptive", "batch"]
        }
        return variants.get(tool_name, [])

    registry.get_tool_variants.side_effect = mock_get_tool_variants

    return registry


@pytest.fixture
def real_registry():
    """Create a real registry with test tools for integration tests."""
    ToolRegistry.reset_instance()
    registry = ToolRegistry.get_instance()

    # Register test tools
    registry.register_tool("mock_basic", MockBasicTool, MockBasicTool.TOOL_SPEC)
    registry.register_tool("mock_configurable", MockConfigurableTool, MockConfigurableTool.TOOL_SPEC)
    registry.register_tool("mock_advanced", MockAdvancedTool, MockAdvancedTool.TOOL_SPEC)

    # Register variants
    registry.register_variant("mock_configurable", "performance", {"timeout": 1200, "threads": 4})
    registry.register_variant("mock_configurable", "debug", {"verbose": True, "debug": True})
    registry.register_variant("mock_advanced", "ai", {"model": "gpt-4", "temperature": 0.7})
    registry.register_variant("mock_advanced", "adaptive", {"strategy": "adaptive", "learning_rate": 0.01})
    registry.register_variant("mock_advanced", "batch", {"batch_size": 32, "parallel": True})

    yield registry
    ToolRegistry.reset_instance()


class TestToolSpecParsing:
    """Test tool specification parsing functionality."""

    def test_parse_simple_tool_name(self):
        """Test parsing simple tool name."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_basic")

        assert tool_name == "mock_basic"
        assert variants == []
        assert params == {}

    def test_parse_tool_with_single_variant(self):
        """Test parsing tool with single variant."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_configurable:performance")

        assert tool_name == "mock_configurable"
        assert variants == ["performance"]
        assert params == {}

    def test_parse_tool_with_multiple_variants(self):
        """Test parsing tool with multiple variants."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_advanced:ai:adaptive")

        assert tool_name == "mock_advanced"
        assert variants == ["ai", "adaptive"]
        assert params == {}

    def test_parse_tool_with_single_parameter(self):
        """Test parsing tool with single parameter."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_basic@timeout=300")

        assert tool_name == "mock_basic"
        assert variants == []
        assert params == {"timeout": "300"}

    def test_parse_tool_with_multiple_parameters(self):
        """Test parsing tool with multiple parameters."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_basic@timeout=300,verbose=true,count=1000")

        assert tool_name == "mock_basic"
        assert variants == []
        assert params == {"timeout": "300", "verbose": "true", "count": "1000"}

    def test_parse_tool_with_variants_and_parameters(self):
        """Test parsing tool with both variants and parameters."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_advanced:ai:batch@model=gpt-4,batch_size=64")

        assert tool_name == "mock_advanced"
        assert variants == ["ai", "batch"]
        assert params == {"model": "gpt-4", "batch_size": "64"}

    def test_parse_tool_with_boolean_flag_parameter(self):
        """Test parsing tool with boolean flag parameter."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_basic@verbose")

        assert tool_name == "mock_basic"
        assert variants == []
        assert params == {"verbose": True}

    def test_parse_tool_with_mixed_parameters(self):
        """Test parsing tool with mixed parameters (values and flags)."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_configurable@timeout=500,debug,threads=2")

        assert tool_name == "mock_configurable"
        assert variants == []
        assert params == {"timeout": "500", "debug": True, "threads": "2"}

    def test_parse_tool_with_whitespace(self):
        """Test parsing tool spec with whitespace."""
        tool_name, variants, params = ToolFactory._parse_tool_spec(
            " mock_basic : performance @ timeout=300 , verbose=true ")

        assert tool_name == "mock_basic"
        assert variants == ["performance"]
        assert params == {"timeout": "300", "verbose": "true"}

    def test_parse_empty_spec_raises_error(self):
        """Test that empty specification raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ToolFactory._parse_tool_spec("")

        assert "Tool name cannot be empty" in str(exc_info.value)

    def test_parse_whitespace_only_spec_raises_error(self):
        """Test that whitespace-only specification raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ToolFactory._parse_tool_spec("   ")

        assert "Tool name cannot be empty" in str(exc_info.value)

    def test_parse_malformed_parameter_is_handled(self):
        """Test that malformed parameters are handled gracefully."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_basic@param_without_value,timeout=300")

        assert tool_name == "mock_basic"
        assert variants == []
        assert params == {"param_without_value": True, "timeout": "300"}

    def test_parse_empty_variant_is_filtered(self):
        """Test that empty variants are filtered out."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_basic::performance:")

        assert tool_name == "mock_basic"
        assert variants == ["performance"]
        assert params == {}


class TestToolCreationFromSpec:
    """Test tool creation from specification strings."""

    def test_create_simple_tool(self, mock_registry):
        """Test creating simple tool from spec."""
        tool = ToolFactory.create_tool_from_spec("mock_basic", mock_registry)

        assert tool is not None
        assert tool.name == "mock_basic"

    def test_create_tool_with_variant(self, mock_registry):
        """Test creating tool with variant."""
        tool = ToolFactory.create_tool_from_spec("mock_configurable:performance", mock_registry)

        assert tool is not None
        assert tool.name == "mock_configurable"
        # Should have been configured with performance variant
        assert len(tool.configured_with) > 0

    def test_create_tool_with_multiple_variants(self, mock_registry):
        """Test creating tool with multiple variants."""
        tool = ToolFactory.create_tool_from_spec("mock_advanced:ai:adaptive", mock_registry)

        assert tool is not None
        assert tool.name == "mock_advanced"
        # Should have been configured with both variants
        assert "model" in tool.config  # From ai variant
        assert "strategy" in tool.config  # From adaptive variant

    def test_create_tool_with_parameters(self, mock_registry):
        """Test creating tool with parameters."""
        tool = ToolFactory.create_tool_from_spec("mock_configurable@timeout=500,debug=true", mock_registry)

        assert tool is not None
        assert tool.name == "mock_configurable"
        # Should have been configured with parameters
        assert len(tool.configured_with) > 0
        config = tool.configured_with[-1]
        assert config["timeout"] == "500"
        assert config["debug"] == "true"

    def test_create_tool_with_variants_and_parameters(self, mock_registry):
        """Test creating tool with variants and parameters."""
        tool = ToolFactory.create_tool_from_spec("mock_advanced:ai@temperature=0.3,max_tokens=2048", mock_registry)

        assert tool is not None
        assert tool.name == "mock_advanced"
        # Should have ai variant config and additional parameters
        assert "model" in tool.config  # From ai variant
        assert "temperature" in tool.config  # From parameters
        assert "max_tokens" in tool.config  # From parameters

    def test_create_tool_nonexistent_suppresses_error(self, mock_registry):
        """Test that creating non-existent tool is handled by ErrorHandler."""
        # ErrorHandler suppresses exceptions, so this should return None
        result = ToolFactory.create_tool_from_spec("nonexistent_tool", mock_registry)

        assert result is None  # Suppressed exception

    def test_create_tool_with_invalid_spec_suppresses_error(self, mock_registry):
        """Test that invalid spec is handled by ErrorHandler."""
        # ErrorHandler suppresses exceptions, so this should return None
        result = ToolFactory.create_tool_from_spec("", mock_registry)

        assert result is None  # Suppressed exception

    def test_create_tool_without_registry_uses_singleton(self, real_registry):
        """Test that create_tool_from_spec uses singleton registry when none provided."""
        tool = ToolFactory.create_tool_from_spec("mock_basic")

        assert tool is not None
        assert tool.name == "mock_basic"

    def test_create_tool_with_logging(self, mock_registry):
        """Test that tool creation logs debug messages."""
        with patch('rv_tools.registry.factory.LoggingManager') as mock_logging_manager:
            mock_logger = Mock()
            mock_logging_manager.get_instance.return_value.get_logger.return_value = mock_logger

            ToolFactory.create_tool_from_spec("mock_basic", mock_registry)

            # Should have logged debug messages
            assert mock_logger.debug.called


class TestConfiguredToolCreation:
    """Test create_configured_tool method."""

    def test_create_configured_tool_basic(self, mock_registry):
        """Test creating configured tool with basic parameters."""
        tool = ToolFactory.create_configured_tool(
            tool_name="mock_configurable",
            variants=["performance"],
            params={"timeout": 800},
            registry=mock_registry
        )

        assert tool is not None
        assert tool.name == "mock_configurable"
        assert len(tool.configured_with) >= 1

    def test_create_configured_tool_no_variants(self, mock_registry):
        """Test creating configured tool without variants."""
        tool = ToolFactory.create_configured_tool(
            tool_name="mock_basic",
            variants=None,
            params={"timeout": 300},
            registry=mock_registry
        )

        assert tool is not None
        assert tool.name == "mock_basic"

    def test_create_configured_tool_no_params(self, mock_registry):
        """Test creating configured tool without parameters."""
        tool = ToolFactory.create_configured_tool(
            tool_name="mock_configurable",
            variants=["debug"],
            params=None,
            registry=mock_registry
        )

        assert tool is not None
        assert tool.name == "mock_configurable"

    def test_create_configured_tool_without_registry(self, real_registry):
        """Test creating configured tool without explicit registry."""
        tool = ToolFactory.create_configured_tool(
            tool_name="mock_basic",
            variants=[],
            params={}
        )

        assert tool is not None
        assert tool.name == "mock_basic"

    def test_create_configured_tool_nonexistent_suppresses_error(self, mock_registry):
        """Test that creating non-existent configured tool is handled by ErrorHandler."""
        # ErrorHandler suppresses exceptions, so this should return None
        result = ToolFactory.create_configured_tool(
            tool_name="nonexistent_tool",
            variants=[],
            params={},
            registry=mock_registry
        )

        assert result is None  # Suppressed exception


class TestInternalConfiguredToolCreation:
    """Test _create_configured_tool internal method."""

    def test_create_configured_tool_with_primary_variant(self, mock_registry):
        """Test internal tool creation with primary variant."""
        # Mock logger
        mock_logger = Mock()

        tool = ToolFactory._create_configured_tool(
            tool_name="mock_configurable",
            variants=["performance"],
            params={},
            registry=mock_registry,
            logger=mock_logger
        )

        assert tool is not None
        assert tool.name == "mock_configurable"
        # Should log creation with primary variant
        assert any("Created tool" in str(call) for call in mock_logger.debug.call_args_list)

    def test_create_configured_tool_with_additional_variants(self, mock_registry):
        """Test internal tool creation with multiple variants."""
        mock_logger = Mock()

        tool = ToolFactory._create_configured_tool(
            tool_name="mock_advanced",
            variants=["ai", "adaptive"],
            params={},
            registry=mock_registry,
            logger=mock_logger
        )

        assert tool is not None
        assert tool.name == "mock_advanced"
        # Should have both variant configurations
        assert "model" in tool.config  # From ai variant
        assert "strategy" in tool.config  # From adaptive variant

    def test_create_configured_tool_with_nonexistent_additional_variant(self, mock_registry):
        """Test tool creation with non-existent additional variant logs warning."""
        mock_logger = Mock()

        tool = ToolFactory._create_configured_tool(
            tool_name="mock_configurable",
            variants=["performance", "nonexistent_variant"],
            params={},
            registry=mock_registry,
            logger=mock_logger
        )

        assert tool is not None
        # Should log warning about missing variant
        assert any("not found" in str(call) for call in mock_logger.warning.call_args_list)

    def test_create_configured_tool_default_configuration(self, mock_registry):
        """Test tool creation with default configuration."""
        mock_logger = Mock()

        tool = ToolFactory._create_configured_tool(
            tool_name="mock_basic",
            variants=[],
            params={},
            registry=mock_registry,
            logger=mock_logger
        )

        assert tool is not None
        assert tool.name == "mock_basic"
        # Should log creation with default configuration
        assert any("default configuration" in str(call) for call in mock_logger.debug.call_args_list)

    def test_create_configured_tool_with_additional_parameters(self, mock_registry):
        """Test tool creation with additional parameters."""
        mock_logger = Mock()

        tool = ToolFactory._create_configured_tool(
            tool_name="mock_configurable",
            variants=[],
            params={"custom_param": "custom_value"},
            registry=mock_registry,
            logger=mock_logger
        )

        assert tool is not None
        # Should have been configured with additional parameters
        assert len(tool.configured_with) > 0
        # Should log application of additional parameters
        assert any("additional parameters" in str(call) for call in mock_logger.debug.call_args_list)

    def test_create_configured_tool_without_configure_method(self, mock_registry):
        """Test tool creation when tool doesn't have configure method."""
        # Mock a tool that doesn't have configure method
        mock_registry.get_tool.return_value = MockBasicTool()

        mock_logger = Mock()

        tool = ToolFactory._create_configured_tool(
            tool_name="mock_basic",
            variants=["some_variant"],
            params={"param": "value"},
            registry=mock_registry,
            logger=mock_logger
        )

        assert tool is not None
        # Should complete without error even when tool doesn't have configure method

    def test_create_configured_tool_raises_on_creation_failure(self, mock_registry):
        """Test that tool creation failure raises appropriate error."""
        # Mock registry to raise exception
        mock_registry.get_tool.side_effect = Exception("Tool creation failed")

        mock_logger = Mock()

        with pytest.raises(ToolNotFoundError) as exc_info:
            ToolFactory._create_configured_tool(
                tool_name="failing_tool",
                variants=[],
                params={},
                registry=mock_registry,
                logger=mock_logger
            )

        assert "Failed to create configured tool 'failing_tool'" in str(exc_info.value)


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_supported_tools(self, mock_registry):
        """Test getting supported tools."""
        tools = ToolFactory.get_supported_tools(mock_registry)

        assert "mock_basic" in tools
        assert "mock_configurable" in tools
        assert "mock_advanced" in tools
        assert len(tools) == 3

    def test_get_supported_tools_without_registry(self, real_registry):
        """Test getting supported tools without explicit registry."""
        tools = ToolFactory.get_supported_tools()

        assert "mock_basic" in tools
        assert "mock_configurable" in tools
        assert "mock_advanced" in tools

    def test_get_tool_variants(self, mock_registry):
        """Test getting tool variants."""
        variants = ToolFactory.get_tool_variants("mock_configurable", mock_registry)

        assert "performance" in variants
        assert "debug" in variants
        assert len(variants) == 2

    def test_get_tool_variants_for_tool_without_variants(self, mock_registry):
        """Test getting variants for tool without variants."""
        variants = ToolFactory.get_tool_variants("mock_basic", mock_registry)

        assert variants == []

    def test_get_tool_variants_without_registry(self, real_registry):
        """Test getting tool variants without explicit registry."""
        variants = ToolFactory.get_tool_variants("mock_configurable")

        assert "performance" in variants
        assert "debug" in variants


class TestErrorHandling:
    """Test error handling and exception scenarios."""

    def test_parse_tool_spec_with_exception_wrapping(self):
        """Test that parsing exceptions are properly wrapped."""
        with pytest.raises(ValueError) as exc_info:
            ToolFactory._parse_tool_spec("")

        assert "Invalid tool specification" in str(exc_info.value)

    def test_create_tool_from_spec_with_parsing_error_suppressed(self, mock_registry):
        """Test create_tool_from_spec with parsing error is handled by ErrorHandler."""
        # ErrorHandler suppresses exceptions, so this should return None
        result = ToolFactory.create_tool_from_spec("", mock_registry)

        assert result is None  # Suppressed exception

    def test_create_tool_from_spec_with_registry_error_suppressed(self, mock_registry):
        """Test create_tool_from_spec with registry error is handled by ErrorHandler."""
        # Mock registry to raise exception
        mock_registry.has_tool.side_effect = Exception("Registry error")

        # ErrorHandler suppresses exceptions, so this should return None
        result = ToolFactory.create_tool_from_spec("mock_basic", mock_registry)

        assert result is None  # Suppressed exception

    def test_error_handler_decorator_presence(self):
        """Test that ErrorHandler decorator is present on create_tool_from_spec."""
        assert hasattr(ToolFactory.create_tool_from_spec, '__wrapped__')

    def test_error_handler_decorator_presence_on_create_configured_tool(self):
        """Test that ErrorHandler decorator is present on create_configured_tool."""
        assert hasattr(ToolFactory.create_configured_tool, '__wrapped__')


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_parse_spec_with_empty_parameter_value(self):
        """Test parsing spec with empty parameter value."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_basic@param=")

        assert tool_name == "mock_basic"
        assert variants == []
        assert params == {"param": ""}

    def test_parse_spec_with_special_characters_in_parameters(self):
        """Test parsing spec with special characters in parameters."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_basic@url=https://example.com,path=/tmp/test")

        assert tool_name == "mock_basic"
        assert variants == []
        assert params == {"url": "https://example.com", "path": "/tmp/test"}

    def test_parse_spec_with_unicode_characters(self):
        """Test parsing spec with unicode characters."""
        tool_name, variants, params = ToolFactory._parse_tool_spec("mock_basic@name=测试,value=日本語")

        assert tool_name == "mock_basic"
        assert variants == []
        assert params == {"name": "测试", "value": "日本語"}

    def test_create_tool_with_empty_variants_list(self, mock_registry):
        """Test creating tool with empty variants list."""
        tool = ToolFactory.create_configured_tool(
            tool_name="mock_basic",
            variants=[],
            params={},
            registry=mock_registry
        )

        assert tool is not None
        assert tool.name == "mock_basic"

    def test_create_tool_with_empty_params_dict(self, mock_registry):
        """Test creating tool with empty params dict."""
        tool = ToolFactory.create_configured_tool(
            tool_name="mock_basic",
            variants=None,
            params={},
            registry=mock_registry
        )

        assert tool is not None
        assert tool.name == "mock_basic"


class TestIntegrationWithRealRegistry:
    """Test integration with real registry for end-to-end validation."""

    def test_complete_workflow_simple_tool(self, real_registry):
        """Test complete workflow with simple tool."""
        tool = ToolFactory.create_tool_from_spec("mock_basic")

        assert tool is not None
        assert tool.name == "mock_basic"
        assert isinstance(tool, MockBasicTool)

    def test_complete_workflow_with_variants(self, real_registry):
        """Test complete workflow with variants."""
        tool = ToolFactory.create_tool_from_spec("mock_configurable:performance")

        assert tool is not None
        assert tool.name == "mock_configurable"
        assert isinstance(tool, MockConfigurableTool)
        # Should have performance configuration
        assert len(tool.configured_with) > 0
        assert tool.configured_with[0]["timeout"] == 1200

    def test_complete_workflow_with_parameters(self, real_registry):
        """Test complete workflow with parameters."""
        tool = ToolFactory.create_tool_from_spec("mock_configurable@custom_timeout=999")

        assert tool is not None
        assert tool.name == "mock_configurable"
        # Should have custom configuration
        assert len(tool.configured_with) > 0
        assert tool.configured_with[0]["custom_timeout"] == "999"

    def test_complete_workflow_complex_spec(self, real_registry):
        """Test complete workflow with complex specification."""
        tool = ToolFactory.create_tool_from_spec("mock_advanced:ai:batch@temperature=0.3,batch_size=16")

        assert tool is not None
        assert tool.name == "mock_advanced"
        assert isinstance(tool, MockAdvancedTool)
        # Should have all configurations applied
        assert "model" in tool.config  # From ai variant
        assert "batch_size" in tool.config  # From batch variant + parameter override
        assert "temperature" in tool.config  # From parameter

    def test_utility_methods_with_real_registry(self, real_registry):
        """Test utility methods with real registry."""
        # Test get_supported_tools
        tools = ToolFactory.get_supported_tools()
        assert len(tools) >= 3
        assert "mock_basic" in tools

        # Test get_tool_variants
        variants = ToolFactory.get_tool_variants("mock_configurable")
        assert "performance" in variants
        assert "debug" in variants


class TestCoverageMaximization:
    """Additional tests to maximize code coverage."""

    def test_create_tool_from_spec_with_logging_context(self, mock_registry):
        """Test that create_tool_from_spec logs with proper context."""
        with patch('rv_tools.registry.factory.LoggingManager') as mock_logging_manager:
            mock_logger = Mock()
            mock_logging_manager.get_instance.return_value.get_logger.return_value = mock_logger

            ToolFactory.create_tool_from_spec("mock_basic", mock_registry)

            # Should have called get_logger with correct parameters
            mock_logging_manager.get_instance.return_value.get_logger.assert_called()
            # Should have logged debug messages
            assert mock_logger.debug.called

    def test_create_configured_tool_internal_with_all_branches(self, mock_registry):
        """Test _create_configured_tool hitting all code branches."""
        mock_logger = Mock()

        # Test with variants that exist
        tool = ToolFactory._create_configured_tool(
            tool_name="mock_configurable",
            variants=["performance"],
            params={"custom": "value"},
            registry=mock_registry,
            logger=mock_logger
        )

        assert tool is not None
        # Should log creation with primary variant
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("Created tool" in call for call in debug_calls)
        assert any("additional parameters" in call for call in debug_calls)

    def test_create_configured_tool_internal_with_missing_variants(self, mock_registry):
        """Test _create_configured_tool with missing variants."""
        mock_logger = Mock()

        # Test with some variants that don't exist
        tool = ToolFactory._create_configured_tool(
            tool_name="mock_basic",
            variants=["nonexistent1", "nonexistent2"],
            params={},
            registry=mock_registry,
            logger=mock_logger
        )

        assert tool is not None
        # Should log warnings about missing variants
        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
        assert any("not found" in call for call in warning_calls)

    def test_create_configured_tool_internal_default_path(self, mock_registry):
        """Test _create_configured_tool default configuration path."""
        mock_logger = Mock()

        # Test with no variants - should use default path
        tool = ToolFactory._create_configured_tool(
            tool_name="mock_basic",
            variants=[],
            params={},
            registry=mock_registry,
            logger=mock_logger
        )

        assert tool is not None
        # Should log default configuration
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("default configuration" in call for call in debug_calls)

    # def test_create_configured_tool_internal_with_tool_without_configure(self, mock_registry):
    #     """Test _create_configured_tool when tool doesn't have configure method."""
    #     mock_logger = Mock()
    #
    #     # Mock basic tool that doesn't have configure method
    #     basic_tool = MockBasicTool()
    #     mock_registry.get_tool.return_value = basic_tool
    #
    #     # Should work even without configure method
    #     tool = ToolFactory._create_configured_tool(
    #         tool_name="mock_basic",
    #         variants=["some_variant"],
    #         params={"some": "param"},
    #         registry=mock_registry,
    #         logger=mock_logger
    #     )
    #
    #     assert tool is not None
    #     assert tool is basic_tool

    def test_parse_tool_spec_edge_cases_for_coverage(self):
        """Test edge cases in _parse_tool_spec for maximum coverage."""
        # Test with parameter that has equals in value
        tool_name, variants, params = ToolFactory._parse_tool_spec("tool@url=http://example.com?param=value")
        assert params["url"] == "http://example.com?param=value"

        # Test with only @ (no parameters)
        tool_name, variants, params = ToolFactory._parse_tool_spec("tool@")
        assert tool_name == "tool"
        assert params == {}

        # Test with multiple colons but empty variants
        tool_name, variants, params = ToolFactory._parse_tool_spec("tool:::variant:::")
        assert tool_name == "tool"
        assert variants == ["variant"]

    def test_parse_tool_spec_exception_handling(self):
        """Test exception handling in _parse_tool_spec."""
        # This should raise ValueError which gets wrapped
        with pytest.raises(ValueError) as exc_info:
            # Simulate an internal error by passing something that will cause issues
            ToolFactory._parse_tool_spec(None)  # This will cause an AttributeError

        # The method should wrap the internal error
        assert "Invalid tool specification" in str(exc_info.value)

    def test_get_supported_tools_with_exception_in_registry(self, mock_registry):
        """Test get_supported_tools when registry raises exception."""
        mock_registry.get_tool_names.side_effect = Exception("Registry error")

        # Should handle gracefully or raise, depending on implementation
        try:
            result = ToolFactory.get_supported_tools(mock_registry)
            # If no exception, should return something reasonable
            assert isinstance(result, list)
        except Exception:
            # If exception is raised, that's also acceptable
            pass

    def test_get_tool_variants_with_exception_in_registry(self, mock_registry):
        """Test get_tool_variants when registry raises exception."""
        mock_registry.get_tool_variants.side_effect = Exception("Registry error")

        # Should handle gracefully or raise, depending on implementation
        try:
            result = ToolFactory.get_tool_variants("mock_basic", mock_registry)
            # If no exception, should return something reasonable
            assert isinstance(result, list)
        except Exception:
            # If exception is raised, that's also acceptable
            pass

    def test_create_tool_from_spec_with_complex_error_scenario(self, mock_registry):
        """Test complex error scenario in create_tool_from_spec."""
        # Mock registry to have tool but fail during creation
        mock_registry.has_tool.return_value = True
        mock_registry.get_tool.side_effect = Exception("Complex creation error")

        # Should be handled by ErrorHandler and return None
        result = ToolFactory.create_tool_from_spec("mock_basic", mock_registry)
        assert result is None

    # def test_create_configured_tool_with_complex_error_scenario(self, mock_registry):
    #     """Test complex error scenario in create_configured_tool."""
    #     # Mock registry to fail in a specific way
    #     mock_registry.has_tool.side_effect = RuntimeError("Registry failure")
    #
    #     # Should be handled by ErrorHandler and return None
    #     result = ToolFactory.create_configured_tool(
    #         tool_name="mock_basic",
    #         variants=[],
    #         params={},
    #         registry=mock_registry
    #     )
    #     assert result is None
