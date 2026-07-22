"""
Simple tests for OllamaLLM class to ensure basic functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_llm.llm.language_model import LLMMessage, LLMResponse


class TestOllamaLLMInitialization:
    """Tests for OllamaLLM initialization."""

    def test_initialization_with_config(self):
        """Test that OllamaLLM initializes correctly with config."""
        config = LLMConfig(llm_type="ollama", model="llama3.2")
        model = OllamaLLM(config)
        
        assert model.config == config
        assert hasattr(model, 'logger')
        assert hasattr(model, 'error_handler')

    def test_initialization_stores_config(self):
        """Test that config is stored correctly."""
        config = LLMConfig(llm_type="ollama", model="llama3.2:7b")
        model = OllamaLLM(config)
        
        assert model.config.model == "llama3.2:7b"


class TestOllamaLLMMethods:
    """Tests for OllamaLLM methods."""

    def test_cleanup(self):
        """Test cleanup method."""
        config = LLMConfig(llm_type="ollama", model="llama3.2")
        model = OllamaLLM(config)
        
        # Should not raise any exception
        model.cleanup()


class TestOllamaLLMProperties:
    """Tests for OllamaLLM properties."""

    def test_name_property(self):
        """Test that NAME is correctly set."""
        assert OllamaLLM.NAME == "ollama"

    def test_models_property(self):
        """Test that MODELS is correctly set."""
        assert isinstance(OllamaLLM.MODELS, list)
        assert len(OllamaLLM.MODELS) > 0