import logging
from typing import Dict, Optional, Type, List

import torch

from rvandroid.llm.dspy_llm import DSPyLLM
from rvandroid.llm.frontier_models import FrontierModel
# Import model implementations
from rvandroid.llm.huggingface_llm import HuggingFaceLLM
from rvandroid.llm.langchain_llm import LangchainLLM
from rvandroid.llm.llm import LanguageModel
from rvandroid.llm.ollama_llm import OllamaLLM

# Configure logger
logger = logging.getLogger(__name__)


class ModelFactory:
    """
    Factory class for creating language model instances.
    Centralizes the creation of various LLM implementations and handles configuration.
    """

    # Registry of available model types and their implementation classes
    _REGISTRY: Dict[str, Type[LanguageModel]] = {
        "huggingface": HuggingFaceLLM,
        "ollama": OllamaLLM,
        "langchain": LangchainLLM,
        "dspy": DSPyLLM,
        "anthropic": FrontierModel,
        "openai": FrontierModel,
        "google": FrontierModel,
        "amazon": FrontierModel,
        "frontier": FrontierModel
    }

    @staticmethod
    def create(model_type: str, model_name: str, **kwargs) -> LanguageModel:
        """
        Create a language model instance.

        Args:
            model_type: Type of model ('huggingface', 'ollama', 'langchain', 'dspy', 'frontier', etc.)
            model_name: Name of the model
            **kwargs: Additional arguments for the model constructor
                - device: For HuggingFace models, specifies the device ('cuda', 'cpu')
                - base_url: For Ollama models, specifies the API URL
                - api_key: For frontier models, API key for the service
                - provider: For frontier models, provider name

        Returns:
            LanguageModel instance

        Raises:
            ValueError: If model_type is unknown or configuration is invalid
        """
        if model_type not in ModelFactory._REGISTRY:
            raise ValueError(f"Unknown model type: {model_type}")

        model_class = ModelFactory._REGISTRY[model_type]
        logger.info(f"Creating {model_type} model: {model_name}")

        # Handle specific parameters based on model type
        if model_type == "huggingface":
            device = kwargs.pop('device', "cuda" if torch.cuda.is_available() else "cpu")
            return model_class(model_name, device=device, **kwargs)

        elif model_type == "ollama":
            base_url = kwargs.pop('base_url', "http://localhost:11434")
            return model_class(model_name, base_url=base_url, **kwargs)

        elif model_type == "langchain":
            provider = kwargs.pop('provider', "ollama")
            base_url = kwargs.pop('base_url', "http://localhost:11434")
            return model_class(model_name, provider=provider, base_url=base_url, **kwargs)

        elif model_type == "dspy":
            provider = kwargs.pop('provider', "ollama")
            base_url = kwargs.pop('base_url', "http://localhost:11434")
            return model_class(model_name, provider=provider, base_url=base_url, **kwargs)

        elif model_type in ["anthropic", "openai", "google", "amazon", "frontier"]:
            # For frontier models, infer provider from model type if not provided
            provider = kwargs.pop('provider', model_type if model_type != "frontier" else None)
            api_key = kwargs.pop('api_key', None)
            return model_class(model_name, provider=provider, api_key=api_key, **kwargs)

        # Default case
        return model_class(model_name, **kwargs)

    @staticmethod
    def get_available_types() -> Dict[str, Type[LanguageModel]]:
        """
        Returns a dictionary of available model types and their classes.

        Returns:
            Dictionary of model types and their implementation classes
        """
        return ModelFactory._REGISTRY.copy()

    @staticmethod
    def register_model_type(name: str, model_class: Type[LanguageModel]) -> None:
        """
        Register a new model type.

        Args:
            name: Name of the model type
            model_class: Model class implementation

        Raises:
            TypeError: If model_class is not a subclass of LanguageModel
        """
        if not issubclass(model_class, LanguageModel):
            raise TypeError(f"Model class must be a subclass of LanguageModel")

        ModelFactory._REGISTRY[name] = model_class
        logger.info(f"Registered new model type: {name}")

    @staticmethod
    def get_available_models(model_type: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Returns available models for a specific type or all types.

        Args:
            model_type: Type of model to get models for (optional)

        Returns:
            Dictionary of model types and their available models

        Raises:
            ValueError: If the specified model_type is unknown
        """
        models = {}

        if model_type:
            if model_type not in ModelFactory._REGISTRY:
                raise ValueError(f"Unknown model type: {model_type}")

            model_class = ModelFactory._REGISTRY[model_type]
            models[model_type] = model_class.models()
        else:
            for type_name, model_class in ModelFactory._REGISTRY.items():
                try:
                    models[type_name] = model_class.models()
                except Exception as e:
                    logger.warning(f"Failed to get models for {type_name}: {e}")
                    models[type_name] = []

        return models
