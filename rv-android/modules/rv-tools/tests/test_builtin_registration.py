"""
Builtin tool integration tests.

Tests cover:
- INV-TOOL-02: Every registered tool must have a "default" variant
- INV-TOOL-04: ToolSpec must have non-empty name, description, url, version
- INV-TOOL-08: Auto-registration must not fail module import
- FR19: 8 built-in tools registered correctly
- FR20: Each tool's variants match spec table
"""

import pytest
from rv_tools.builtin import BUILTIN_TOOLS
from rv_tools.registry.registry import ToolRegistry

# Expected tools with their variant names (from source code, verified against spec FR20)
EXPECTED_TOOLS = {
    "monkey": {"default", "fast", "stress"},
    "droidbot": {
        "default",
        "dfs_greedy",
        "bfs_greedy",
        "dfs_naive",
        "bfs_naive",
        "random",
    },
    "ape": {"default", "sata", "bfs", "dfs", "random"},
    "fastbot": {"default", "conservative", "aggressive", "balanced"},
    "ares": {"default"},
    "droidmate": {"default"},
    "humanoid": {"default"},
    "qtesting": {"default"},
}

# All 8 expected tool names
EXPECTED_TOOL_NAMES = set(EXPECTED_TOOLS.keys())


@pytest.fixture(scope="module")
def builtin_registry():
    """Registry with all builtins registered (module-scoped for performance)."""
    ToolRegistry.reset_instance()
    registry = ToolRegistry.get_instance()
    for tool_class in BUILTIN_TOOLS:
        registry.register_tool_class(tool_class)
    yield registry
    ToolRegistry.reset_instance()


class TestAutoRegistration:
    """INV-TOOL-08: Auto-registration must not fail module import."""

    def test_import_rv_tools_succeeds(self):
        """INV-TOOL-08: importing rv_tools does not raise."""
        import rv_tools  # noqa: F401

    def test_builtin_tools_count(self):
        """FR19: BUILTIN_TOOLS contains exactly 8 tool classes."""
        assert len(BUILTIN_TOOLS) == 8


class TestAllToolsRegistered:
    """FR19: All 8 built-in tools are registered correctly."""

    def test_all_expected_tools_present(self, builtin_registry):
        """FR19: registry contains all 8 expected tools."""
        registered = set(builtin_registry.get_tool_names())
        assert EXPECTED_TOOL_NAMES.issubset(
            registered
        ), f"Missing tools: {EXPECTED_TOOL_NAMES - registered}"


class TestToolSpecs:
    """INV-TOOL-04: Every ToolSpec must have non-empty name, description, url, version."""

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_spec_fields_non_empty(self, tool_class):
        """INV-TOOL-04: ToolSpec fields are non-empty."""
        spec = tool_class.get_tool_spec()
        assert spec.name, f"{tool_class.__name__}: name is empty"
        assert spec.description, f"{tool_class.__name__}: description is empty"
        assert spec.url, f"{tool_class.__name__}: url is empty"
        assert spec.version, f"{tool_class.__name__}: version is empty"

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_spec_name_matches_registration(self, tool_class, builtin_registry):
        """FR19: spec.name matches the key used in registry."""
        spec = tool_class.get_tool_spec()
        assert builtin_registry.has_tool(spec.name)


class TestDefaultVariant:
    """INV-TOOL-02: Every registered tool must have a 'default' variant."""

    @pytest.mark.parametrize("tool_name", sorted(EXPECTED_TOOL_NAMES))
    def test_has_default_variant(self, tool_name, builtin_registry):
        """INV-TOOL-02: tool has a 'default' variant."""
        variants = builtin_registry.get_tool_variants(tool_name)
        assert "default" in variants, f"{tool_name} missing 'default' variant"


class TestVariantsMatchSpec:
    """FR20: Each tool's variants match the spec table."""

    @pytest.mark.parametrize(
        "tool_name,expected_variants",
        sorted(EXPECTED_TOOLS.items()),
        ids=lambda x: x if isinstance(x, str) else None,
    )
    def test_variants_present(self, tool_name, expected_variants, builtin_registry):
        """FR20: tool contains expected variants."""
        actual = set(builtin_registry.get_tool_variants(tool_name))
        assert expected_variants.issubset(
            actual
        ), f"{tool_name}: missing variants {expected_variants - actual}"


class TestDroidBotPolicyValidation:
    """FR19 scenario: DroidBot rejects invalid policy in configure()."""

    def test_valid_policy_accepted(self, builtin_registry):
        """FR19 scenario: DroidBot accepts valid policy."""
        tool = builtin_registry.get_tool("droidbot")
        tool.configure({"policy": "dfs_greedy", "count": 10000000000})
        assert tool.config["policy"] == "dfs_greedy"
        assert tool.config["count"] == 10000000000

    def test_invalid_policy_rejected(self, builtin_registry):
        """FR19 scenario: DroidBot raises ConfigurationError for invalid policy."""
        from rv_android_core.util.error.exceptions import ConfigurationError

        tool = builtin_registry.get_tool("droidbot")
        with pytest.raises(ConfigurationError, match="invalid_policy"):
            tool.configure({"policy": "invalid_policy"})


class TestMonkeyConfiguration:
    """FR19: MonkeyTool configure applies parameters."""

    def test_configure_event_count(self, builtin_registry):
        """FR19: MonkeyTool.configure sets event_count."""
        tool = builtin_registry.get_tool("monkey")
        tool.configure({"event_count": 5000, "throttle": 100})
        assert tool.config["event_count"] == 5000
        assert tool.config["throttle"] == 100


class TestVariantConfigValues:
    """FR20 scenario: Variant config contains complete parameters."""

    def test_droidbot_dfs_greedy_config(self, builtin_registry):
        """FR20 scenario: droidbot:dfs_greedy has correct parameters."""
        config = builtin_registry.get_variant_config("droidbot", "dfs_greedy")
        assert config["policy"] == "dfs_greedy"
        assert config["count"] == 10000000000
        assert config["interval"] == 3
        assert config["ignore_ad"] is True

    def test_monkey_fast_config(self, builtin_registry):
        """FR20: monkey:fast has seed and reduced event count."""
        config = builtin_registry.get_variant_config("monkey", "fast")
        assert config["event_count"] == 500
        assert config["seed"] == 12345
