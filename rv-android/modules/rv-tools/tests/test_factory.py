"""
ToolFactory unit tests.

Tests cover:
- INV-TOOL-05: Factory must call configure() before returning
- FR18 scenario: Factory creates configured tool from ToolConfig
- FR18 scenario: Factory rejects invalid tool or variant
- FR20 scenario: Parameter overrides replace variant values
"""


from rv_android_core.domain.task import ToolConfig
from rv_tools.registry.factory import ToolFactory

class TestCreateTool:
    """FR18: Factory creates configured tool instances from ToolConfig."""

    def test_create_with_default_variant(self, factory):
        """FR18 scenario: create_tool with default variant applies default config."""
        tool_config = ToolConfig(name="faketool", variant="default", parameters={})
        tool = factory.create_tool(tool_config)

        assert tool.name == "faketool"
        assert tool.config["param_a"] == 10
        assert tool.config["param_b"] == "hello"

    def test_create_with_named_variant(self, factory):
        """FR18 scenario: create_tool with named variant applies variant config."""
        tool_config = ToolConfig(name="faketool", variant="fast", parameters={})
        tool = factory.create_tool(tool_config)

        assert tool.name == "faketool"
        assert tool.config["param_a"] == 5
        assert tool.config["param_b"] == "fast"

    def test_parameter_override(self, factory):
        """FR20 scenario: parameters override variant values."""
        tool_config = ToolConfig(
            name="faketool",
            variant="fast",
            parameters={"param_a": 999},
        )
        tool = factory.create_tool(tool_config)

        # param_a overridden, param_b preserved from variant
        assert tool.config["param_a"] == 999
        assert tool.config["param_b"] == "fast"

    def test_extra_parameter_added(self, factory):
        """FR20: extra parameters are merged into final config."""
        tool_config = ToolConfig(
            name="faketool",
            variant="default",
            parameters={"extra_key": "extra_value"},
        )
        tool = factory.create_tool(tool_config)

        assert tool.config["extra_key"] == "extra_value"
        # variant params still present
        assert tool.config["param_a"] == 10


class TestConfigureCalled:
    """INV-TOOL-05: Factory must call configure() before returning."""

    def test_configure_is_called(self, factory):
        """INV-TOOL-05: tool.configure(config) is called with merged config."""
        tool_config = ToolConfig(name="faketool", variant="stress", parameters={})
        tool = factory.create_tool(tool_config)

        # FakeTool.configure stores config — non-empty means it was called
        assert tool.config == {"param_a": 100, "param_b": "stress"}


class TestFactoryRejectsInvalid:
    """FR18 scenario: Factory rejects invalid tool or variant.

    Note: @ErrorHandler.handle_errors on create_tool has reraise=False,
    so errors are absorbed and the method returns None instead of raising.
    """

    def test_rejects_unknown_tool(self, factory):
        """FR18 scenario: unknown tool returns None (error absorbed by decorator)."""
        tool_config = ToolConfig(name="nonexistent_tool", parameters={})
        result = factory.create_tool(tool_config)
        assert result is None

    def test_rejects_invalid_variant(self, factory):
        """FR18 scenario: invalid variant returns None (error absorbed by decorator)."""
        tool_config = ToolConfig(name="faketool", variant="invalid_variant", parameters={})
        result = factory.create_tool(tool_config)
        assert result is None


class TestFactoryInit:
    """ToolFactory initialization."""

    def test_factory_uses_provided_registry(self, registry_with_fake):
        """Factory uses the registry passed in constructor."""
        factory = ToolFactory(registry_with_fake)
        assert factory.registry is registry_with_fake

    def test_factory_default_registry(self):
        """Factory falls back to singleton registry when none provided."""
        factory = ToolFactory()
        assert factory.registry is not None
