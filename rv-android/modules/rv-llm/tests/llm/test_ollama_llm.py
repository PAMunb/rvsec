
from unittest.mock import MagicMock, patch

import pytest
from ollama import Client, ChatResponse

from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.data_structures import LLMMessage, LLMRole, LLMTextContent
from rv_llm.llm.ollama_llm import OllamaLLM


@pytest.fixture
def mock_ollama_client():
    """Fixture to mock the Ollama client where it is used."""
    with patch("rv_llm.llm.ollama_llm.Client") as mock_client_class:
        mock_instance = mock_client_class.return_value
        yield mock_client_class, mock_instance


@pytest.fixture
def mock_supported_llm_types(monkeypatch):
    """Fixture to mock the supported LLM types to include 'ollama'."""
    supported_types = ["ollama", "openai", "anthropic", "google", "huggingface"]
    monkeypatch.setattr(
        "rv_llm.factories.component_factory.LLMComponentFactory.get_supported_llm_types",
        lambda: supported_types,
    )


class TestOllamaLLMInitialization:
    """Tests for the initialization of the OllamaLLM."""

    def test_initialization_defaults(self):
        """Test that the model initializes with default values."""
        model = OllamaLLM()
        assert model.model_name == OllamaLLM.LLAMA
        assert model.api_base == "http://localhost:11434"
        assert model._client is None

    def test_initialization_with_custom_params(self):
        """Test initialization with a custom model name and base URL."""
        model = OllamaLLM(model_name="custom_model", base_url="http://custom:1234")
        assert model.model_name == "custom_model"
        assert model.api_base == "http://custom:1234"

    def test_client_lazy_initialization(self, mock_ollama_client):
        """Test that the Ollama client is initialized lazily."""
        mock_client_class, _ = mock_ollama_client
        model = OllamaLLM()
        assert model._client is None
        # Accessing the client property should initialize it
        _ = model.client
        assert model._client is not None
        mock_client_class.assert_called_once_with(host="http://localhost:11434")


class TestOllamaLLMGeneration:
    """Tests for the text generation functionality."""

    def test_generate_successful_response(self, mock_ollama_client, mock_supported_llm_types):
        """Test a successful generation call."""
        _, mock_client_instance = mock_ollama_client
        # Mock the response from the ollama client
        mock_response = MagicMock(spec=ChatResponse)
        mock_response.message = MagicMock()
        mock_response.message.content = "Generated response"
        mock_response.done_reason = "stop"
        mock_response.total_duration = 1000
        mock_response.load_duration = 100
        mock_response.prompt_eval_count = 10
        mock_response.prompt_eval_duration = 200
        mock_response.eval_count = 20
        mock_response.eval_duration = 700
        mock_client_instance.chat.return_value = mock_response

        model = OllamaLLM()
        messages = [LLMMessage(role=LLMRole.USER, content=[LLMTextContent(text="Hello")])]
        response = model.generate(messages)

        assert response.content == "Generated response"
        assert response.input_tokens == 10
        assert response.output_tokens == 20
        mock_client_instance.chat.assert_called_once()

    def test_generate_with_custom_config(self, mock_ollama_client, mock_supported_llm_types):
        """Test that custom config parameters are used in the generation call."""
        _, mock_client_instance = mock_ollama_client
        mock_response = MagicMock(spec=ChatResponse)
        mock_response.message = MagicMock()
        mock_response.message.content = ""
        mock_response.done_reason = "stop"
        mock_response.total_duration = 0
        mock_response.load_duration = 0
        mock_response.prompt_eval_count = 0
        mock_response.prompt_eval_duration = 0
        mock_response.eval_count = 0
        mock_response.eval_duration = 0
        mock_client_instance.chat.return_value = mock_response

        model = OllamaLLM()
        messages = [LLMMessage(role=LLMRole.USER, content=[LLMTextContent(text="Hi")])]
        config = LLMConfig(
            temperature=0.9,
            max_tokens=150,
            top_p=0.8,
            top_k=30,
            llm_type="ollama",
            model="test"
        )
        model.generate(messages, config)

        mock_client_instance.chat.assert_called_once()
        call_args = mock_client_instance.chat.call_args
        assert call_args.kwargs["options"]["temperature"] == 0.9
        assert call_args.kwargs["options"]["num_predict"] == 150
        assert call_args.kwargs["options"]["top_p"] == 0.8
        assert call_args.kwargs["options"]["top_k"] == 30

    def test_generate_handles_api_error(self, mock_ollama_client, mock_supported_llm_types):
        """Test that an API error during generation is handled gracefully."""
        _, mock_client_instance = mock_ollama_client
        mock_client_instance.chat.side_effect = Exception("API connection failed")

        model = OllamaLLM()
        messages = [LLMMessage(role=LLMRole.USER, content=[LLMTextContent(text="Test")])]

        with pytest.raises(Exception, match="API connection failed"):
            model.generate(messages)


class TestOllamaLLMMethods:
    """Tests for other helper methods of OllamaLLM."""

    def test_models_classmethod(self):
        """Test that the models classmethod returns the correct list of models."""
        assert OllamaLLM.models() == OllamaLLM.MODELS

    def test_cleanup(self, mock_ollama_client):
        """Test that the cleanup method resets the client."""
        mock_client_class, _ = mock_ollama_client
        model = OllamaLLM()
        # Initialize client
        _ = model.client
        assert model._client is not None

        model.cleanup()
        assert model._client is None
