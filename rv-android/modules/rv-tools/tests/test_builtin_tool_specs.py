"""
Builtin tool specification and variant structure tests.

Tests cover:
- ToolSpec validity for all builtin tools (process_pattern set)
- Variant parameter structure for monkey, ape, fastbot, droidbot
- Variant config values are complete and typed correctly
- All tool classes have get_tool_spec and get_variants class methods
"""

import pytest
from rv_tools.builtin import BUILTIN_TOOLS
from rv_tools.builtin.ape.tool import APETool
from rv_tools.builtin.droidbot.tool import DroidBotTool
from rv_tools.builtin.fastbot.tool import FastBotTool
from rv_tools.builtin.monkey.tool import MonkeyTool
from rv_tools.registry.registry import ToolRegistry


@pytest.fixture(scope="module")
def builtin_registry():
    """Registry with all builtins registered."""
    ToolRegistry.reset_instance()
    registry = ToolRegistry.get_instance()
    for tool_class in BUILTIN_TOOLS:
        registry.register_tool_class(tool_class)
    yield registry
    ToolRegistry.reset_instance()


class TestToolSpecProcessPattern:
    """All builtin tools with device interaction have process_pattern set."""

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_spec_has_process_pattern(self, tool_class):
        """ToolSpec process_pattern is set for builtin tools that need it."""
        spec = tool_class.get_tool_spec()
        # All builtin tools should have process_pattern (used for cleanup)
        # Some may be None by design, but monkey/ape/fastbot/droidbot must have it
        if spec.name in ("monkey", "ape", "fastbot", "droidbot"):
            assert spec.process_pattern is not None
            assert len(spec.process_pattern) > 0

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_spec_version_is_semver(self, tool_class):
        """ToolSpec version follows semver-like format (contains dots)."""
        spec = tool_class.get_tool_spec()
        assert "." in spec.version

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_spec_url_is_valid(self, tool_class):
        """ToolSpec url starts with http."""
        spec = tool_class.get_tool_spec()
        assert spec.url.startswith("http")


class TestToolClassMethods:
    """All builtin tools implement required class methods."""

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_has_get_tool_spec(self, tool_class):
        """Tool class has get_tool_spec class method."""
        assert hasattr(tool_class, "get_tool_spec")
        assert callable(tool_class.get_tool_spec)

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_has_get_variants(self, tool_class):
        """Tool class has get_variants class method."""
        assert hasattr(tool_class, "get_variants")
        assert callable(tool_class.get_variants)

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_get_variants_returns_dict(self, tool_class):
        """get_variants returns a dictionary."""
        variants = tool_class.get_variants()
        assert isinstance(variants, dict)

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_get_variants_has_default(self, tool_class):
        """get_variants includes a 'default' key."""
        variants = tool_class.get_variants()
        assert "default" in variants

    @pytest.mark.parametrize("tool_class", BUILTIN_TOOLS, ids=lambda c: c.__name__)
    def test_get_variants_values_are_dicts(self, tool_class):
        """Each variant value is a dictionary."""
        variants = tool_class.get_variants()
        for variant_name, config in variants.items():
            assert isinstance(
                config, dict
            ), f"{tool_class.__name__}:{variant_name} is not a dict"


class TestMonkeyVariantStructure:
    """Monkey variants have expected parameter keys."""

    def test_default_variant_keys(self):
        """Monkey default variant has expected keys."""
        variants = MonkeyTool.get_variants()
        default = variants["default"]
        assert "event_count" in default
        assert "throttle" in default
        assert "verbosity" in default

    def test_fast_variant_has_seed(self):
        """Monkey fast variant sets a reproducible seed."""
        variants = MonkeyTool.get_variants()
        fast = variants["fast"]
        assert fast["seed"] is not None
        assert isinstance(fast["seed"], int)

    def test_stress_variant_high_event_count(self):
        """Monkey stress variant has higher event count than default."""
        variants = MonkeyTool.get_variants()
        assert variants["stress"]["event_count"] > variants["default"]["event_count"]

    def test_fast_variant_ignores_crashes(self):
        """Monkey fast variant sets ignore_crashes to True."""
        variants = MonkeyTool.get_variants()
        assert variants["fast"]["ignore_crashes"] is True

    def test_default_variant_does_not_ignore_crashes(self):
        """Monkey default variant does not ignore crashes."""
        variants = MonkeyTool.get_variants()
        assert variants["default"]["ignore_crashes"] is False


class TestAPEVariantStructure:
    """APE variants have expected parameter keys."""

    def test_all_variants_have_strategy(self):
        """Every APE variant specifies a strategy."""
        variants = APETool.get_variants()
        for variant_name, config in variants.items():
            assert "strategy" in config, f"APE:{variant_name} missing strategy"

    def test_strategies_are_valid(self):
        """All APE variant strategies are in AVAILABLE_STRATEGIES."""
        variants = APETool.get_variants()
        for variant_name, config in variants.items():
            assert (
                config["strategy"] in APETool.AVAILABLE_STRATEGIES
            ), f"APE:{variant_name} has invalid strategy '{config['strategy']}'"

    def test_all_variants_have_running_minutes(self):
        """Every APE variant specifies running_minutes."""
        variants = APETool.get_variants()
        for variant_name, config in variants.items():
            assert "running_minutes" in config
            assert isinstance(config["running_minutes"], int)
            assert config["running_minutes"] > 0

    def test_variant_count_matches_expected(self):
        """APE has expected number of variants."""
        variants = APETool.get_variants()
        assert len(variants) == 5  # default, sata, bfs, dfs, random


class TestFastBotVariantStructure:
    """FastBot variants have expected parameter keys."""

    def test_all_variants_have_strategy(self):
        """Every FastBot variant specifies a strategy."""
        variants = FastBotTool.get_variants()
        for variant_name, config in variants.items():
            assert "strategy" in config, f"FastBot:{variant_name} missing strategy"

    def test_all_variants_have_max_step(self):
        """Every FastBot variant specifies max_step."""
        variants = FastBotTool.get_variants()
        for variant_name, config in variants.items():
            assert "max_step" in config
            assert isinstance(config["max_step"], int)
            assert config["max_step"] > 0

    def test_all_variants_have_learning_params(self):
        """Every FastBot variant has learning_rate and exploration_rate."""
        variants = FastBotTool.get_variants()
        for variant_name, config in variants.items():
            assert "learning_rate" in config
            assert "exploration_rate" in config
            assert 0.0 <= config["learning_rate"] <= 1.0
            assert 0.0 <= config["exploration_rate"] <= 1.0

    def test_conservative_has_lower_exploration(self):
        """Conservative variant has lower exploration rate than aggressive."""
        variants = FastBotTool.get_variants()
        assert (
            variants["conservative"]["exploration_rate"]
            < variants["aggressive"]["exploration_rate"]
        )

    def test_aggressive_has_higher_max_step(self):
        """Aggressive variant has more steps than conservative."""
        variants = FastBotTool.get_variants()
        assert variants["aggressive"]["max_step"] > variants["conservative"]["max_step"]


class TestDroidBotVariantStructure:
    """DroidBot variants have expected parameter keys."""

    def test_all_variants_have_policy(self):
        """Every DroidBot variant specifies a policy."""
        variants = DroidBotTool.get_variants()
        for variant_name, config in variants.items():
            assert "policy" in config, f"DroidBot:{variant_name} missing policy"

    def test_all_variants_have_count(self):
        """Every DroidBot variant specifies count."""
        variants = DroidBotTool.get_variants()
        for variant_name, config in variants.items():
            assert "count" in config
            assert isinstance(config["count"], int)

    def test_greedy_variants_have_high_count(self):
        """Greedy variants use effectively infinite count."""
        variants = DroidBotTool.get_variants()
        for name in ("dfs_greedy", "bfs_greedy"):
            assert variants[name]["count"] >= 10_000_000_000

    def test_all_variants_have_ignore_ad(self):
        """Every DroidBot variant specifies ignore_ad."""
        variants = DroidBotTool.get_variants()
        for variant_name, config in variants.items():
            assert "ignore_ad" in config
            assert isinstance(config["ignore_ad"], bool)
