"""
ToolRegistry unit tests.

Tests cover:
- INV-TOOL-01: Singleton behavior and reset_instance
- INV-TOOL-03: Unique names, re-registration replaces + logs warning
- INV-TOOL-13: get_variant_config returns copy, not reference
- FR18: Tool registration and retrieval
- FR20: Variant registration, listing, validation
"""

import pytest
from rv_android_core.util.error.exceptions import (
    ConfigurationError,
    ToolNotFoundError,
)
from rv_tools.registry.registry import ToolRegistry


class TestSingleton:
    """INV-TOOL-01: Singleton must return same instance across callers."""

    def test_same_instance(self, fresh_registry):
        """INV-TOOL-01: get_instance returns same object."""
        other = ToolRegistry.get_instance()
        assert fresh_registry is other

    def test_reset_creates_new_instance(self):
        """INV-TOOL-01: reset_instance allows a fresh registry."""
        first = ToolRegistry.get_instance()
        ToolRegistry.reset_instance()
        second = ToolRegistry.get_instance()
        assert first is not second
        ToolRegistry.reset_instance()


class TestToolRegistration:
    """FR18: Tool registration and retrieval."""

    def test_register_tool_class(self, fresh_registry, fake_tool_class):
        """FR18: register_tool_class stores class, spec, and variants."""
        fresh_registry.register_tool_class(fake_tool_class)

        assert fresh_registry.has_tool("faketool")
        assert fresh_registry.get_tool_class("faketool") is fake_tool_class
        assert fresh_registry.get_tool_spec("faketool").name == "faketool"

    def test_register_tool_class_registers_variants(self, fresh_registry, fake_tool_class):
        """FR18/FR20: register_tool_class auto-registers all variants."""
        fresh_registry.register_tool_class(fake_tool_class)

        variant_names = fresh_registry.get_tool_variants("faketool")
        assert "default" in variant_names
        assert "fast" in variant_names
        assert "stress" in variant_names

    def test_has_tool_false_for_unregistered(self, fresh_registry):
        """FR18: has_tool returns False for unknown tool."""
        assert not fresh_registry.has_tool("nonexistent")

    def test_is_tool_registered_alias(self, registry_with_fake):
        """FR18: is_tool_registered is alias for has_tool."""
        assert registry_with_fake.is_tool_registered("faketool")
        assert not registry_with_fake.is_tool_registered("nonexistent")

    def test_get_tool_names(self, registry_with_fake):
        """FR18: get_tool_names lists all registered tools."""
        names = registry_with_fake.get_tool_names()
        assert "faketool" in names

    def test_get_all_tool_names_alias(self, registry_with_fake):
        """FR18: get_all_tool_names is alias for get_tool_names."""
        assert registry_with_fake.get_all_tool_names() == registry_with_fake.get_tool_names()

    def test_get_tool_class_raises_for_unknown(self, fresh_registry):
        """FR18: get_tool_class raises ToolNotFoundError for unknown tool."""
        with pytest.raises(ToolNotFoundError):
            fresh_registry.get_tool_class("nonexistent")

    def test_get_tool_spec_raises_for_unknown(self, fresh_registry):
        """FR18: get_tool_spec raises ToolNotFoundError for unknown tool."""
        with pytest.raises(ToolNotFoundError):
            fresh_registry.get_tool_spec("nonexistent")


class TestReRegistration:
    """INV-TOOL-03: Re-registering a tool replaces previous and logs warning."""

    def test_re_registration_replaces(self, registry_with_fake, fake_tool_class):
        """INV-TOOL-03: duplicate name replaces tool class."""
        registry_with_fake.register_tool_class(fake_tool_class)
        assert registry_with_fake.get_tool_class("faketool") is fake_tool_class
        assert registry_with_fake.get_tool_names().count("faketool") == 1


class TestVariants:
    """FR20: Variant registration, listing, validation, and retrieval."""

    def test_get_tool_variants(self, registry_with_fake):
        """FR20 scenario: listing variants for a registered tool."""
        variants = registry_with_fake.get_tool_variants("faketool")
        assert set(variants) == {"default", "fast", "stress"}

    def test_get_tool_variants_empty_for_unknown(self, fresh_registry):
        """FR20: get_tool_variants returns empty list for unknown tool."""
        assert fresh_registry.get_tool_variants("nonexistent") == []

    def test_validate_tool_variant_true(self, registry_with_fake):
        """FR20 scenario: validate_tool_variant returns True for valid combo."""
        assert registry_with_fake.validate_tool_variant("faketool", "fast")

    def test_validate_tool_variant_false(self, registry_with_fake):
        """FR20 scenario: validate_tool_variant returns False for invalid variant."""
        assert not registry_with_fake.validate_tool_variant("faketool", "nonexistent")

    def test_validate_tool_variant_false_unknown_tool(self, fresh_registry):
        """FR20: validate_tool_variant returns False for unknown tool."""
        assert not fresh_registry.validate_tool_variant("nonexistent", "default")

    def test_has_variant(self, registry_with_fake):
        """FR20: has_variant checks specific tool+variant combo."""
        assert registry_with_fake.has_variant("faketool", "default")
        assert registry_with_fake.has_variant("faketool", "fast")
        assert not registry_with_fake.has_variant("faketool", "nonexistent")
        assert not registry_with_fake.has_variant("nonexistent", "default")

    def test_get_variant_config(self, registry_with_fake):
        """FR20 scenario: get_variant_config returns complete parameters."""
        config = registry_with_fake.get_variant_config("faketool", "fast")
        assert config == {"param_a": 5, "param_b": "fast"}

    def test_get_variant_config_raises_for_unknown_tool(self, fresh_registry):
        """FR20: get_variant_config raises for unknown tool."""
        with pytest.raises((ConfigurationError, ToolNotFoundError)):
            fresh_registry.get_variant_config("nonexistent", "default")

    def test_get_variant_config_raises_for_unknown_variant(self, registry_with_fake):
        """FR20: get_variant_config raises for unknown variant."""
        with pytest.raises((ConfigurationError, ToolNotFoundError)):
            registry_with_fake.get_variant_config("faketool", "nonexistent")

    def test_register_variant_for_unregistered_tool_is_noop(self, fresh_registry):
        """FR20: registering variant for unknown tool does not store it.

        Note: @ErrorHandler.handle_errors absorbs the exception (reraise=False),
        so register_variant returns None. The variant must NOT appear in storage.
        """
        fresh_registry.register_variant("nonexistent", "v1", {"key": "val"})
        assert not fresh_registry.has_variant("nonexistent", "v1")


class TestVariantConfigIsCopy:
    """INV-TOOL-13: get_variant_config must return a copy, not a reference."""

    def test_mutation_does_not_affect_registry(self, registry_with_fake):
        """INV-TOOL-13: modifying returned dict must not change registry state."""
        config = registry_with_fake.get_variant_config("faketool", "fast")
        config["param_a"] = 99999
        config["injected"] = "hack"

        original = registry_with_fake.get_variant_config("faketool", "fast")
        assert original["param_a"] == 5
        assert "injected" not in original


class TestGetTool:
    """FR18: get_tool creates a configured tool instance."""

    def test_get_tool_default(self, registry_with_fake):
        """FR18: get_tool with default variant returns working instance."""
        tool = registry_with_fake.get_tool("faketool")
        assert tool.name == "faketool"

    def test_get_tool_raises_for_unknown(self, fresh_registry):
        """FR18: get_tool raises ToolNotFoundError for unknown tool."""
        with pytest.raises(ToolNotFoundError):
            fresh_registry.get_tool("nonexistent")


class TestGetAllTools:
    """FR18: get_all_tools creates instances of all registered tools."""

    def test_get_all_tools(self, registry_with_fake):
        """FR18: get_all_tools returns list with one tool instance."""
        tools = registry_with_fake.get_all_tools()
        assert len(tools) == 1
        assert tools[0].name == "faketool"

    def test_get_all_tools_empty(self, fresh_registry):
        """FR18: get_all_tools returns empty list when no tools registered."""
        tools = fresh_registry.get_all_tools()
        assert tools == []


class TestClearAndInfo:
    """Registry housekeeping: clear and get_registry_info."""

    def test_clear(self, registry_with_fake):
        """clear removes all tools and variants."""
        registry_with_fake.clear()
        assert registry_with_fake.get_tool_names() == []
        assert registry_with_fake.get_registry_info()["total_tools"] == 0

    def test_get_registry_info(self, registry_with_fake):
        """get_registry_info returns correct stats."""
        info = registry_with_fake.get_registry_info()
        assert info["total_tools"] == 1
        assert info["total_variants"] == 3
        assert "faketool" in info["tools"]
        assert set(info["variants_by_tool"]["faketool"]) == {"default", "fast", "stress"}

    def test_get_registry_info_empty(self, fresh_registry):
        """get_registry_info on empty registry."""
        info = fresh_registry.get_registry_info()
        assert info["total_tools"] == 0
        assert info["total_variants"] == 0
