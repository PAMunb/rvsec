
from unittest.mock import MagicMock, patch

import pytest

from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.language_model import LanguageModel, LLMMessage, LLMResponse


# Concrete implementation of the abstract LanguageModel for testing
class ConcreteLanguageModel(LanguageModel):
    NAME = "concrete"
    MODELS = ["model-a", "model-b"]
    
    def __init__(self, model_name: str):
        """Initialize with model name for testing."""
        config = LLMConfig(llm_type="ollama", model=model_name)
        super().__init__(config)
        self.model_name = model_name  # Store for test assertions

    def generate(self, messages: list[LLMMessage], config: LLMConfig | None = None) -> LLMResponse:
        if self.model_name == "error_model":
            raise ValueError("Generation failed")
        return LLMResponse(text="response", model_id=self.model_name)

    def cleanup(self):
        if self.model_name == "cleanup_error":
            raise RuntimeError("Cleanup failed")
        pass  # No-op for testing


@pytest.fixture
def model_instance():
    """Fixture to create a ConcreteLanguageModel instance."""
    return ConcreteLanguageModel("test_model")


class TestLanguageModelInitialization:
    """Tests for the initialization of the LanguageModel."""

    def test_initialization(self, model_instance):
        """Test that the model is initialized with the correct attributes."""
        assert model_instance.model_name == "test_model"
        assert hasattr(model_instance, "logger")
        assert hasattr(model_instance, "error_handler")


class TestLanguageModelAbstractMethods:
    """Tests for the abstract methods of LanguageModel."""

    def test_generate_is_abstract(self):
        """Test that generate is an abstract method."""
        with pytest.raises(TypeError):
            config = LLMConfig(llm_type="ollama", model="test")
            LanguageModel(config)

    def test_cleanup_is_abstract(self):
        """Test that cleanup is an abstract method."""
        with pytest.raises(TypeError):
            config = LLMConfig(llm_type="ollama", model="test")
            LanguageModel(config)


class TestLanguageModelErrorHandling:
    """Tests for the error handling decorators."""

    @patch("rv_android_core.util.error.error_handler.ErrorHandler.handle_errors")
    def test_handle_generation_errors_decorator(self, mock_handle_errors, model_instance):
        """Test that the generation error handler is called with the correct component name."""
        # This test is a bit white-box, but it's the most direct way to test the decorator helper
        @model_instance._handle_generation_errors
        def decorated_func():
            pass

        mock_handle_errors.assert_called_once_with(
            component="LanguageModel.ConcreteLanguageModel",
            phase="response_generation"
        )

    @patch("rv_android_core.util.error.error_handler.ErrorHandler.handle_errors")
    def test_handle_cleanup_errors_decorator(self, mock_handle_errors, model_instance):
        """Test that the cleanup error handler is called with the correct component name."""

        @model_instance._handle_cleanup_errors
        def decorated_func():
            pass

        mock_handle_errors.assert_called_once_with(
            component="LanguageModel.ConcreteLanguageModel",
            phase="resource_cleanup"
        )


@pytest.fixture
def mock_supported_llm_types(monkeypatch):
    """Fixture to mock the supported LLM types to include 'concrete'."""
    supported_types = ["ollama", "openai", "anthropic", "google", "huggingface", "concrete"]
    monkeypatch.setattr(
        "rv_llm.factories.component_factory.LLMComponentFactory.get_supported_llm_types",
        lambda: supported_types,
    )


class TestLanguageModelHelperMethods:
    """Tests for the helper methods of LanguageModel."""

    def test_get_component_name(self, model_instance):
        """Test that the component name is correctly formatted."""
        assert model_instance._get_component_name() == "LanguageModel.ConcreteLanguageModel"
