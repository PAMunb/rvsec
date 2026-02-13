
import os
from unittest.mock import patch

import pytest
from hypothesis import given, strategies as st, settings
from pydantic import ValidationError

from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.constants import LLMType

# A strategy for generating valid temperature values
valid_temperatures = st.floats(min_value=0.0, max_value=2.0)
# A strategy for generating valid model names
valid_model_names = st.text(min_size=1, alphabet=st.characters(min_codepoint=97, max_codepoint=122))


@pytest.fixture(scope="class")
def mock_supported_llm_types_class(request):
    """Class-scoped fixture to mock the supported LLM types."""
    supported_types = ["ollama", "openai", "anthropic", "google", "frontier"]
    patcher = patch(
        "rv_llm.factories.component_factory.LLMComponentFactory.get_supported_llm_types",
        return_value=supported_types
    )
    mock_get_types = patcher.start()
    request.cls.supported_types = supported_types
    yield mock_get_types
    patcher.stop()


@pytest.mark.usefixtures("mock_supported_llm_types_class")
class TestLLMConfigInitialization:
    """Tests for the initialization and default values of LLMConfig."""

    def test_default_initialization(self):
        """Test that LLMConfig can be initialized with default values."""
        config = LLMConfig()
        assert config.llm_type == "ollama"
        assert config.model == "llama3.2:3b"
        assert config.base_url == "http://localhost:11434"
        assert config.temperature == 0.2
        assert config.max_tokens == 800
        assert config.api_key is None
        assert config.provider is None
        assert config.top_p == 1.0
        assert config.top_k == 40
        assert config.frequency_penalty == 0.0
        assert config.presence_penalty == 0.0
        assert config.max_context_length == 8192
        assert config.kwargs == {}

    @given(
        temperature=valid_temperatures,
        max_tokens=st.integers(min_value=1, max_value=4096),
        model=valid_model_names
    )
    @settings(max_examples=10)  # Limit examples for speed
    def test_property_based_initialization(self, temperature, max_tokens, model):
        """Test valid random configurations using Hypothesis."""
        config = LLMConfig(
            llm_type="ollama",
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
        assert config.model == model
        assert config.temperature == temperature
        assert config.max_tokens == max_tokens

    def test_kwargs_handling(self):
        """Test that additional kwargs are captured correctly."""
        extra_params = {"custom_param": "value", "another": 123}
        config = LLMConfig(model="test-model", kwargs=extra_params)
        assert config.kwargs == extra_params
        assert config.to_dict()["custom_param"] == "value"


@pytest.mark.usefixtures("mock_supported_llm_types_class")
class TestLLMConfigValidation:
    """Tests for the validation logic within LLMConfig."""

    def test_validate_llm_type_success(self):
        """Test that supported LLM types are accepted."""
        for llm_type in self.supported_types:
            if llm_type == LLMType.FRONTIER:
                config = LLMConfig(llm_type=llm_type, api_key="dummy")
            else:
                config = LLMConfig(llm_type=llm_type)
            assert config.llm_type == llm_type

    def test_validate_llm_type_failure(self):
        """Test that an unsupported LLM type raises a ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(llm_type="unsupported_type")
        assert "unsupported_type" in str(exc_info.value)
        assert f"must be one of: {self.supported_types}" in str(exc_info.value)

    @pytest.mark.parametrize("invalid_temp", [-0.1, 2.1])
    def test_invalid_temperature_range(self, invalid_temp):
        """Test that temperature values outside the valid range [0.0, 2.0] raise an error."""
        with pytest.raises(ValidationError):
            LLMConfig(temperature=invalid_temp)

    def test_invalid_model_name_is_empty(self):
        """Test that an empty model name raises a validation error."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(model="")
        assert "model must be a non-empty string" in str(exc_info.value)

    def test_invalid_model_name_is_none(self):
        """Test that a None model name raises a validation error."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(model=None)
        assert "Input should be a valid string" in str(exc_info.value)

    def test_api_key_required_for_frontier(self):
        """Test that api_key is required for the 'frontier' llm_type."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(llm_type=LLMType.FRONTIER, api_key=None)
        assert f"api_key is required for {LLMType.FRONTIER}" in str(exc_info.value)

        # Should succeed with an api_key
        config = LLMConfig(llm_type=LLMType.FRONTIER, api_key="dummy_key")
        assert config.api_key == "dummy_key"

    def test_base_url_required_for_ollama(self):
        """Test that base_url is required for the 'ollama' llm_type."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(llm_type=LLMType.OLLAMA, base_url="")
        assert "base_url is required for ollama backend" in str(exc_info.value)

        # Should succeed with a base_url
        config = LLMConfig(llm_type=LLMType.OLLAMA, base_url="http://custom:1234")
        assert config.base_url == "http://custom:1234"


@pytest.mark.usefixtures("mock_supported_llm_types_class")
class TestFromVariantsAndParams:
    """Tests for the from_variants_and_params class method."""

    @patch.dict(os.environ, {}, clear=True)
    def test_parse_llama_variant(self):
        """Test the 'llama' variant sets the correct configuration."""
        config = LLMConfig.from_variants_and_params(variants=["llama"], params={})
        assert config.llm_type == "ollama"
        assert config.model == "llama3.2:3b"
        assert config.base_url == "http://localhost:11434"
        assert config.provider == "ollama"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test_key_openai"}, clear=True)
    def test_parse_gpt4_variant(self):
        """Test the 'gpt4' variant sets the correct configuration."""
        config = LLMConfig.from_variants_and_params(variants=["gpt4"], params={})
        assert config.llm_type == "openai"
        assert config.model == "gpt-4"
        assert config.provider == "openai"
        assert config.api_key == "test_key_openai"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test_key_anthropic"}, clear=True)
    def test_parse_claude_variant(self):
        """Test the 'claude' variant sets the correct configuration."""
        config = LLMConfig.from_variants_and_params(variants=["claude"], params={})
        assert config.llm_type == "anthropic"
        assert config.model == "claude-3-5-sonnet-20241022"
        assert config.provider == "anthropic"
        assert config.api_key == "test_key_anthropic"

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key_google"}, clear=True)
    def test_parse_gemini_variant(self):
        """Test the 'gemini' variant sets the correct configuration."""
        config = LLMConfig.from_variants_and_params(variants=["gemini"], params={})
        assert config.llm_type == "google"
        assert config.model == "gemini-pro"
        assert config.provider == "google"
        assert config.api_key == "test_key_google"

    def test_parameter_override(self):
        """Test that explicit parameters override variant defaults."""
        params = {
            "model": "custom_model",
            "temperature": 0.99,
            "max_tokens": 1234
        }
        config = LLMConfig.from_variants_and_params(variants=["llama"], params=params)
        assert config.llm_type == "ollama"
        assert config.model == "custom_model"
        assert config.temperature == 0.99
        assert config.max_tokens == 1234

    def test_no_variants(self):
        """Test that calling with no variants results in an empty config dict before pydantic defaults."""
        config = LLMConfig.from_variants_and_params(variants=[], params={})
        assert config == LLMConfig()  # Should be equal to a default config


@pytest.mark.usefixtures("mock_supported_llm_types_class")
class TestLLMConfigMethods:
    """Tests for the helper methods of LLMConfig."""

    def test_validate_method(self):
        """Test the backward-compatible validate method."""
        config = LLMConfig()
        is_valid, errors = config.validate()
        assert is_valid
        assert errors == []

    def test_to_dict(self):
        """Test that to_dict serializes the config correctly."""
        config = LLMConfig(model="test_model", kwargs={"extra": "data"})
        config_dict = config.to_dict()

        assert config_dict["model"] == "test_model"
        assert config_dict["temperature"] == 0.2  # Default value
        assert config_dict["extra"] == "data"  # Kwarg included

    def test_get_llm_parameters(self):
        """Test that get_llm_parameters extracts the correct subset of parameters."""
        config = LLMConfig(
            model="test_model",
            temperature=0.5,
            kwargs={"llm_specific": True, "other_data": "ignore"}
        )
        llm_params = config.get_llm_parameters()

        expected_keys = [
            "model", "temperature", "max_tokens", "top_p", "top_k",
            "frequency_penalty", "presence_penalty", "base_url", "api_key",
            "llm_specific"
        ]
        assert all(key in llm_params for key in expected_keys)
        assert "other_data" not in llm_params
        assert llm_params["model"] == "test_model"
        assert llm_params["temperature"] == 0.5
        assert llm_params["llm_specific"] is True

    def test_get_context_parameters(self):
        """Test that get_context_parameters extracts the correct subset of parameters."""
        config = LLMConfig(
            max_context_length=4000,
            kwargs={"context_specific": True, "other_data": "ignore"}
        )
        context_params = config.get_context_parameters()

        expected_keys = ["max_context_length", "max_tokens", "context_specific"]
        assert all(key in context_params for key in expected_keys)
        assert "other_data" not in context_params
        assert context_params["max_context_length"] == 4000
        assert context_params["context_specific"] is True

    def test_string_representations(self):
        """Test the __str__ and __repr__ methods."""
        config = LLMConfig(model="my-model", llm_type="openai")
        assert str(config) == "LLMConfig(llm_type=openai, model=my-model)"
        assert "llm_type='openai'" in repr(config)
        assert "model='my-model'" in repr(config)
        assert "temperature=0.2" in repr(config)
        assert "kwargs_count=0" in repr(config)
