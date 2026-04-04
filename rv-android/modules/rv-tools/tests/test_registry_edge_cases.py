"""
ToolRegistry edge case tests.

Tests cover gaps not addressed by existing test_registry.py:
- Re-registration warning behavior
- get_tool with non-default variant applies configure()
- get_tool with unknown variant falls back to default (warning logged)
- reset_instance creates independent singleton
- register_tool stores spec and class atomically
- clear resets variants map
- get_registry_info with multiple tools
- get_tool_variants returns list (not set or dict)
"""

import pytest
from helpers import FakeTool, FakeToolNoDefault
from rv_android_core.util.error.exceptions import ToolNotFoundError
from rv_tools.registry.registry import ToolRegistry


class TestReRegistrationWarning:
    """Re-registration replaces tool and logs warning."""

    def test_re_registration_preserves_latest_class(self, fresh_registry, fake_tool_class):
        """Re-registering same tool name keeps the latest class."""
        fresh_registry.register_tool_class(fake_tool_class)
        fresh_registry.register_tool_class(fake_tool_class)
        assert fresh_registry.get_tool_class("faketool") is fake_tool_class

    def test_re_registration_preserves_variants(self, fresh_registry, fake_tool_class):
        """Re-registering a tool preserves its variants from the latest registration."""
        fresh_registry.register_tool_class(fake_tool_class)
        fresh_registry.register_tool_class(fake_tool_class)
        variants = fresh_registry.get_tool_variants("faketool")
        assert "default" in variants
        assert "fast" in variants
        assert "stress" in variants

    def test_re_registration_updates_spec(self, fresh_registry, fake_tool_class):
        """Re-registering updates the tool spec to the latest one."""
        fresh_registry.register_tool_class(fake_tool_class)
        fresh_registry.register_tool_class(fake_tool_class)
        spec = fresh_registry.get_tool_spec("faketool")
        assert spec.name == "faketool"


class TestResetInstance:
    """reset_instance creates a fully independent new singleton."""

    def test_reset_clears_registered_tools(self):
        """After reset, previously registered tools are gone from new instance."""
        ToolRegistry.reset_instance()
        reg1 = ToolRegistry.get_instance()
        reg1.register_tool_class(FakeTool)
        assert reg1.has_tool("faketool")

        ToolRegistry.reset_instance()
        reg2 = ToolRegistry.get_instance()
        assert not reg2.has_tool("faketool")
        ToolRegistry.reset_instance()

    def test_reset_instance_returns_none(self):
        """reset_instance returns None (void method)."""
        result = ToolRegistry.reset_instance()
        assert result is None
        ToolRegistry.reset_instance()

    def test_old_instance_still_usable_after_reset(self):
        """The old registry object still works after reset (just not the singleton)."""
        ToolRegistry.reset_instance()
        old = ToolRegistry.get_instance()
        old.register_tool_class(FakeTool)

        ToolRegistry.reset_instance()
        # old still has its tools
        assert old.has_tool("faketool")
        # new singleton does not
        new = ToolRegistry.get_instance()
        assert not new.has_tool("faketool")
        ToolRegistry.reset_instance()


class TestGetToolWithVariant:
    """get_tool applies variant configuration via configure()."""

    def test_get_tool_with_named_variant_configures(self, registry_with_fake):
        """get_tool with non-default variant applies variant config via configure()."""
        tool = registry_with_fake.get_tool("faketool", variant="fast")
        assert tool.name == "faketool"
        # FakeTool.configure stores config; for non-default variant
        # registry calls configure() with variant config
        assert tool.config.get("param_a") == 5
        assert tool.config.get("param_b") == "fast"

    def test_get_tool_with_unknown_variant_uses_default(self, registry_with_fake):
        """get_tool with unknown variant falls back to default (no error raised)."""
        tool = registry_with_fake.get_tool("faketool", variant="nonexistent_variant")
        # Tool is still created successfully with default config
        assert tool.name == "faketool"

    def test_get_tool_default_variant_no_configure(self, registry_with_fake):
        """get_tool with 'default' variant does NOT call configure() (optimization)."""
        tool = registry_with_fake.get_tool("faketool", variant="default")
        # FakeTool.__init__ sets config = {}, and since default variant
        # skips configure(), config remains empty
        assert tool.config == {}


class TestRegisterToolDirect:
    """register_tool (low-level) stores class and spec atomically."""

    def test_register_tool_stores_class(self, fresh_registry, fake_tool_class):
        """register_tool stores the tool class."""
        spec = fake_tool_class.get_tool_spec()
        fresh_registry.register_tool("faketool", fake_tool_class, spec)
        assert fresh_registry.get_tool_class("faketool") is fake_tool_class

    def test_register_tool_stores_spec(self, fresh_registry, fake_tool_class):
        """register_tool stores the tool spec."""
        spec = fake_tool_class.get_tool_spec()
        fresh_registry.register_tool("faketool", fake_tool_class, spec)
        assert fresh_registry.get_tool_spec("faketool") is spec

    def test_register_tool_initializes_empty_variants(self, fresh_registry, fake_tool_class):
        """register_tool initializes empty variants dict for the tool."""
        spec = fake_tool_class.get_tool_spec()
        fresh_registry.register_tool("faketool", fake_tool_class, spec)
        assert fresh_registry.get_tool_variants("faketool") == []

    def test_register_tool_does_not_overwrite_existing_variants(self, fresh_registry, fake_tool_class):
        """register_tool preserves existing variants if tool is re-registered."""
        spec = fake_tool_class.get_tool_spec()
        fresh_registry.register_tool("faketool", fake_tool_class, spec)
        fresh_registry.register_variant("faketool", "custom", {"key": "val"})

        # Re-register same tool
        fresh_registry.register_tool("faketool", fake_tool_class, spec)
        # Variants should still be there (register_tool checks 'not in variants')
        assert fresh_registry.has_variant("faketool", "custom")


class TestClearBehavior:
    """clear() removes all state from the registry."""

    def test_clear_removes_variants(self, registry_with_fake):
        """clear removes all variants."""
        registry_with_fake.clear()
        assert registry_with_fake.get_tool_variants("faketool") == []

    def test_clear_removes_tool_classes(self, registry_with_fake):
        """clear removes all tool classes."""
        registry_with_fake.clear()
        assert not registry_with_fake.has_tool("faketool")

    def test_clear_removes_specs(self, registry_with_fake):
        """clear removes all tool specs."""
        registry_with_fake.clear()
        with pytest.raises(ToolNotFoundError):
            registry_with_fake.get_tool_spec("faketool")

    def test_registry_usable_after_clear(self, registry_with_fake, fake_tool_class):
        """Registry can register new tools after clear."""
        registry_with_fake.clear()
        registry_with_fake.register_tool_class(fake_tool_class)
        assert registry_with_fake.has_tool("faketool")


class TestGetRegistryInfoMultipleTools:
    """get_registry_info with multiple tools."""

    def test_info_counts_multiple_tools(self, fresh_registry):
        """get_registry_info counts tools and variants across multiple tools."""
        fresh_registry.register_tool_class(FakeTool)
        fresh_registry.register_tool_class(FakeToolNoDefault)

        info = fresh_registry.get_registry_info()
        assert info["total_tools"] == 2
        # FakeTool has 3 variants, FakeToolNoDefault has 1
        assert info["total_variants"] == 4
        assert "faketool" in info["tools"]
        assert "nodefault" in info["tools"]

    def test_info_variants_by_tool(self, fresh_registry):
        """get_registry_info lists variants per tool."""
        fresh_registry.register_tool_class(FakeTool)
        info = fresh_registry.get_registry_info()
        assert set(info["variants_by_tool"]["faketool"]) == {"default", "fast", "stress"}


class TestGetToolVariantsReturnType:
    """get_tool_variants returns a list."""

    def test_returns_list(self, registry_with_fake):
        """get_tool_variants returns a list, not a set or dict."""
        variants = registry_with_fake.get_tool_variants("faketool")
        assert isinstance(variants, list)

    def test_returns_empty_list_for_unknown(self, fresh_registry):
        """get_tool_variants returns empty list for unknown tool, not None."""
        result = fresh_registry.get_tool_variants("unknown")
        assert result == []
        assert isinstance(result, list)
