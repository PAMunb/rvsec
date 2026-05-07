"""
ToolFactory edge case tests.

Tests cover gaps not addressed by existing test_factory.py:
- create_tool merges user params over variant defaults
- create_tool with empty parameters uses variant config as-is
- create_tool with None variant uses default
- Factory with explicit registry reference
- Multiple parameter overrides
- create_tool preserves non-overridden variant values
"""

from rv_android_core.domain.task import ToolConfig
from rv_tools.registry.factory import ToolFactory


class TestParameterOverrideMerging:
    """User parameters override variant defaults in create_tool."""

    def test_single_override_preserves_other_variant_params(self, factory):
        """Overriding one param preserves other variant params."""
        tool_config = ToolConfig(
            name="faketool",
            variant="fast",
            parameters={"param_a": 42},
        )
        tool = factory.create_tool(tool_config)
        assert tool.config["param_a"] == 42
        assert tool.config["param_b"] == "fast"

    def test_override_all_variant_params(self, factory):
        """All variant params can be overridden."""
        tool_config = ToolConfig(
            name="faketool",
            variant="fast",
            parameters={"param_a": 77, "param_b": "custom"},
        )
        tool = factory.create_tool(tool_config)
        assert tool.config["param_a"] == 77
        assert tool.config["param_b"] == "custom"

    def test_extra_params_added_to_variant_config(self, factory):
        """Extra params not in variant are added to final config."""
        tool_config = ToolConfig(
            name="faketool",
            variant="fast",
            parameters={"extra": "bonus"},
        )
        tool = factory.create_tool(tool_config)
        assert tool.config["extra"] == "bonus"
        assert tool.config["param_a"] == 5  # from fast variant

    def test_empty_parameters_uses_variant_as_is(self, factory):
        """Empty parameters dict uses variant config without changes."""
        tool_config = ToolConfig(
            name="faketool",
            variant="stress",
            parameters={},
        )
        tool = factory.create_tool(tool_config)
        assert tool.config["param_a"] == 100
        assert tool.config["param_b"] == "stress"


class TestFactoryVariantResolution:
    """Factory resolves variant from registry before creating tool."""

    def test_none_variant_uses_default(self, factory):
        """When variant is None, factory uses default variant config."""
        tool_config = ToolConfig(name="faketool", parameters={})
        tool = factory.create_tool(tool_config)
        assert tool.config["param_a"] == 10
        assert tool.config["param_b"] == "hello"

    def test_explicit_default_variant(self, factory):
        """Explicit 'default' variant uses default config."""
        tool_config = ToolConfig(name="faketool", variant="default", parameters={})
        tool = factory.create_tool(tool_config)
        assert tool.config["param_a"] == 10
        assert tool.config["param_b"] == "hello"

    def test_stress_variant_values(self, factory):
        """Stress variant applies correct config values."""
        tool_config = ToolConfig(name="faketool", variant="stress", parameters={})
        tool = factory.create_tool(tool_config)
        assert tool.config["param_a"] == 100
        assert tool.config["param_b"] == "stress"


class TestFactoryErrorCases:
    """Factory returns None for invalid tool/variant (errors absorbed by decorator)."""

    def test_unknown_tool_returns_none(self, factory):
        """Unknown tool name returns None."""
        tool_config = ToolConfig(name="does_not_exist", parameters={})
        result = factory.create_tool(tool_config)
        assert result is None

    def test_unknown_variant_returns_none(self, factory):
        """Unknown variant for known tool returns None."""
        tool_config = ToolConfig(
            name="faketool", variant="no_such_variant", parameters={}
        )
        result = factory.create_tool(tool_config)
        assert result is None

    def test_empty_tool_name_returns_none(self, factory):
        """Empty string tool name returns None."""
        tool_config = ToolConfig(name="", parameters={})
        result = factory.create_tool(tool_config)
        assert result is None


class TestFactoryDoesNotMutateRegistry:
    """Factory operations do not mutate registry state."""

    def test_create_tool_does_not_change_variant_config(
        self, factory, registry_with_fake
    ):
        """Creating a tool with overrides does not modify registry variant config."""
        original = registry_with_fake.get_variant_config("faketool", "fast")

        tool_config = ToolConfig(
            name="faketool",
            variant="fast",
            parameters={"param_a": 999, "new_param": "injected"},
        )
        factory.create_tool(tool_config)

        after = registry_with_fake.get_variant_config("faketool", "fast")
        assert after == original
        assert "new_param" not in after
