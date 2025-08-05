
import pytest
from hypothesis import given, strategies as st, settings
from pydantic import ValidationError

from rv_llm.config.prompt_config import PromptConfig
from rv_llm.llm.constants import PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType


class TestPromptConfigInitialization:
    """Tests for the initialization and default values of PromptConfig."""

    def test_default_initialization(self):
        """Test that PromptConfig can be initialized with default values."""
        config = PromptConfig()
        assert config.strategy_type == PromptStrategyType.STANDARD
        assert config.parser_type == ScreenParserType.DROIDBOT
        assert config.visitor_type == VisitorType.DETAILED
        assert config.template_paths == {}
        assert config.max_context_length == 8192
        assert config.additional_params == {}

    @given(
        strategy_type=st.sampled_from(PromptStrategyType.ALL),
        parser_type=st.sampled_from(ScreenParserType.ALL),
        visitor_type=st.sampled_from(VisitorType.ALL),
        max_context_length=st.integers(min_value=512, max_value=32768)
    )
    @settings(max_examples=10)
    def test_property_based_initialization(
        self, strategy_type, parser_type, visitor_type, max_context_length
    ):
        """Test valid random configurations using Hypothesis."""
        config = PromptConfig(
            strategy_type=strategy_type,
            parser_type=parser_type,
            visitor_type=visitor_type,
            max_context_length=max_context_length
        )
        assert config.strategy_type == strategy_type
        assert config.parser_type == parser_type
        assert config.visitor_type == visitor_type
        assert config.max_context_length == max_context_length

    def test_additional_params_handling(self):
        """Test that additional_params are captured correctly."""
        extra_params = {"custom_param": "value", "another": 123}
        config = PromptConfig(additional_params=extra_params)
        assert config.additional_params == extra_params


class TestPromptConfigValidation:
    """Tests for the validation logic within PromptConfig."""

    @pytest.mark.parametrize("invalid_type", [None, "", "invalid_strategy"])
    def test_invalid_strategy_type(self, invalid_type):
        """Test that an invalid strategy_type raises a ValidationError."""
        with pytest.raises(ValidationError):
            PromptConfig(strategy_type=invalid_type)

    @pytest.mark.parametrize("invalid_path", [{"key": 123}, {123: "value"}, {"": "value"}, {"key": ""}])
    def test_invalid_template_paths(self, invalid_path):
        """Test that invalid template_paths raise a ValidationError."""
        with pytest.raises(ValidationError):
            PromptConfig(template_paths=invalid_path)


class TestFromToolConfig:
    """Tests for the from_tool_config class method."""

    def test_from_tool_config_extraction(self):
        """Test that parameters are correctly extracted from a tool_config dict."""
        tool_config = {
            "strategy_type": PromptStrategyType.BATCH_ACTION,
            "parser_type": ScreenParserType.UIAUTOMATOR,
            "visitor_type": VisitorType.BASIC,
            "template_paths": {"system": "path/to/system.xml"},
            "max_context_length": 4096,
            "prompt_custom_param": "custom_value",
            "other_param": "should_be_ignored"
        }
        config = PromptConfig.from_tool_config(tool_config)

        assert config.strategy_type == PromptStrategyType.BATCH_ACTION
        assert config.parser_type == ScreenParserType.UIAUTOMATOR
        assert config.visitor_type == VisitorType.BASIC
        assert config.template_paths == {"system": "path/to/system.xml"}
        assert config.max_context_length == 4096
        assert config.additional_params == {"prompt_custom_param": "custom_value"}

    def test_from_tool_config_defaults(self):
        """Test that default values are used when parameters are missing."""
        config = PromptConfig.from_tool_config({})
        assert config.strategy_type == PromptStrategyType.STANDARD
        assert config.parser_type == ScreenParserType.DROIDBOT
        assert config.visitor_type == VisitorType.DETAILED


class TestFromVariants:
    """Tests for the from_variants class method."""

    @pytest.mark.parametrize("variants, expected_strategy", [
        (["standard"], PromptStrategyType.STANDARD),
        (["batch_action"], PromptStrategyType.BATCH_ACTION)
    ])
    def test_strategy_variants(self, variants, expected_strategy):
        config = PromptConfig.from_variants(variants)
        assert config.strategy_type == expected_strategy

    def test_parameter_override(self):
        """Test that explicit parameters override variant defaults."""
        params = {"strategy_type": PromptStrategyType.STANDARD}
        config = PromptConfig.from_variants(["batch_action"], params=params)
        assert config.strategy_type == PromptStrategyType.STANDARD


class TestPromptConfigMethods:
    """Tests for the helper methods of PromptConfig."""

    def test_get_strategy_parameters(self):
        """Test that get_strategy_parameters extracts the correct subset of parameters."""
        config = PromptConfig(
            strategy_type=PromptStrategyType.BATCH_ACTION,
            additional_params={"prompt_specific": True, "other": "data"}
        )
        strategy_params = config.get_strategy_parameters()

        assert strategy_params["strategy_type"] == PromptStrategyType.BATCH_ACTION
        assert strategy_params["prompt_specific"] is True
        assert strategy_params["other"] == "data"

    def test_to_dict(self):
        """Test that to_dict serializes the config correctly."""
        config = PromptConfig(strategy_type=PromptStrategyType.BATCH_ACTION)
        config_dict = config.to_dict()
        assert config_dict["strategy_type"] == PromptStrategyType.BATCH_ACTION

    def test_string_representations(self):
        """Test the __str__ and __repr__ methods."""
        config = PromptConfig()
        assert "PromptConfig(strategy_type=standard_modular" in str(config)
        assert "strategy_type='standard_modular'" in repr(config)
