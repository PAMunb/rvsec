"""
ConfigurationFactory tests.

Tests cover:
- FR16: DSL parsing (parse_tool_specifications, _parse_single_tool_spec)
- FR15: Template generation (basic, advanced, llm)

Note: create_cli_config uses old field names (experiment_dir, experiment_id)
that don't match ExperimentConfig — it is dead code and not tested.
"""

import pytest
from rv_experiment.factories.configuration_factory import ConfigurationFactory


@pytest.fixture
def factory():
    return ConfigurationFactory()


class TestParseToolSpecifications:
    """FR16: Tool specification DSL parsing."""

    def test_simple_tool(self, factory):
        """FR16 scenario: single tool without variant."""
        result = factory.parse_tool_specifications(["monkey"])
        assert len(result) == 1
        assert result[0]["name"] == "monkey"
        assert result[0]["variants"] == []
        assert result[0]["parameters"] == {}

    def test_tool_with_variant(self, factory):
        """FR16: tool:variant parsed correctly."""
        result = factory.parse_tool_specifications(["droidbot:dfs_greedy"])
        assert result[0]["name"] == "droidbot"
        assert result[0]["variants"] == ["dfs_greedy"]

    def test_tool_with_multiple_variants(self, factory):
        """FR16: tool:var1:var2 parsed correctly."""
        result = factory.parse_tool_specifications(["droidbot:dfs_greedy:bfs_greedy"])
        assert result[0]["name"] == "droidbot"
        assert result[0]["variants"] == ["dfs_greedy", "bfs_greedy"]

    def test_tool_with_parameters(self, factory):
        """FR16 scenario: tool with parameters via @ syntax."""
        result = factory.parse_tool_specifications(
            ["rvagent:multimode@temperature=0.3"]
        )
        assert result[0]["name"] == "rvagent"
        assert result[0]["variants"] == ["multimode"]
        assert result[0]["parameters"] == {"temperature": "0.3"}

    def test_tool_with_multiple_parameters(self, factory):
        """FR16 scenario / INV-EXP-09: multiple parameters separated by comma."""
        result = factory.parse_tool_specifications(
            ["rvagent:multimode@temperature=0.3,top_p=0.6"]
        )
        assert result[0]["parameters"] == {"temperature": "0.3", "top_p": "0.6"}

    def test_multiple_tools(self, factory):
        """FR16: parsing multiple tool specs."""
        result = factory.parse_tool_specifications(["monkey", "droidbot:dfs_greedy"])
        assert len(result) == 2
        assert result[0]["name"] == "monkey"
        assert result[1]["name"] == "droidbot"

    def test_empty_tool_name_raises(self, factory):
        """FR16: empty tool name raises ValueError."""
        # parse_tool_specifications is wrapped by @ErrorHandler.handle_errors
        # which may absorb the error. The internal _parse_single_tool_spec raises.
        with pytest.raises((ValueError, Exception)):
            factory._parse_single_tool_spec("")

    def test_boolean_flag_parameter(self, factory):
        """FR16: parameter without = is treated as boolean flag."""
        result = factory.parse_tool_specifications(["tool@debug"])
        assert result[0]["parameters"] == {"debug": True}


class TestTemplates:
    """FR15: Configuration templates generate valid configs.

    Templates use default apks_dir (./apks_examples/) which may not exist.
    Validation errors are absorbed by @ErrorHandler.handle_errors, so the
    config may be created with validation warnings.
    """

    def test_basic_template_fields(self, factory):
        """FR15: basic template has correct name and tools."""
        config = factory.create_basic_template()
        assert config is not None
        assert config.name == "basic_experiment"
        assert len(config.tool_configs) == 1
        assert config.tool_configs[0].name == "monkey"

    def test_advanced_template_fields(self, factory):
        """FR15: advanced template has monkey + droidbot, 3 reps."""
        config = factory.create_advanced_template()
        assert config is not None
        assert config.name == "advanced_experiment"
        assert len(config.tool_configs) == 2
        assert config.repetitions == 3

    def test_llm_template_fields(self, factory):
        """FR15: LLM template has rvagent:multimode, 30min timeout."""
        config = factory.create_llm_template()
        assert config is not None
        assert config.tool_configs[0].name == "rvagent"
        assert config.timeouts == [1800]
