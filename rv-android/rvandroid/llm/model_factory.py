import logging
from typing import Dict, Optional, Type, List, Any

import torch

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.llm import LanguageModel

# Configure logger
logger = logging.getLogger(__name__)


class ModelFactory:
    """
    Factory class for creating language model instances.
    Centralizes the creation of various LLM implementations and handles configuration.

    ### Architectural Decisions:
    - Integrates with the ComponentRegistry system for dynamic model discovery
    - Provides a factory pattern for language model instantiation
    - Handles model-specific configuration and initialization
    - Supports flexible integration of new model types

    ### Role in the System:
    - Acts as the primary factory for language model creation
    - Maps model types to their implementation classes
    - Handles model-specific parameter configuration
    - Provides consistent model initialization across the system
    - Enables runtime model type registration and discovery
    """

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
        # Get LLM implementation from registry
        llm_registry = ComponentConfigurator._registries['llm']
        model_class = llm_registry.get(model_type)
        
        if not model_class:
            # Fall back to legacy registration if model type not in registry
            legacy_registry = ModelFactory._get_legacy_registry()
            if model_type in legacy_registry:
                model_class = legacy_registry[model_type]
                # Register for future use
                ComponentConfigurator.register_llm(model_type, model_class)
            else:
                raise ValueError(f"Unknown model type: {model_type}. Available types: {llm_registry.get_names()}")

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
    def _get_legacy_registry() -> Dict[str, Type[LanguageModel]]:
        """
        Returns the legacy registry of model types.
        This is used for backward compatibility and will be removed in future versions.

        Returns:
            Dictionary of model types and their implementation classes
        """
        # Import here to avoid circular imports
        from rvandroid.llm.dspy_llm import DSPyLLM
        from rvandroid.llm.frontier_models import FrontierModel
        from rvandroid.llm.huggingface_llm import HuggingFaceLLM
        from rvandroid.llm.langchain_llm import LangchainLLM
        from rvandroid.llm.ollama_llm import OllamaLLM

        return {
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
    def get_available_types() -> List[str]:
        """
        Returns a list of available model types.

        Returns:
            List of model type names
        """
        # Get types from registry
        registry_types = ComponentConfigurator._registries['llm'].get_names()
        
        # Add any legacy types not in registry
        legacy_types = set(ModelFactory._get_legacy_registry().keys())
        all_types = set(registry_types).union(legacy_types)
        
        return list(all_types)

    @staticmethod
    def register_model_type(name: str, model_class: Type[LanguageModel], 
                           metadata: Dict[str, Any] = None) -> None:
        """
        Register a new model type with both the component registry and the factory.

        Args:
            name: Name of the model type
            model_class: Model class implementation
            metadata: Additional model metadata (optional)

        Raises:
            TypeError: If model_class is not a subclass of LanguageModel
        """
        if not issubclass(model_class, LanguageModel):
            raise TypeError(f"Model class must be a subclass of LanguageModel")

        # Register with component registry
        ComponentConfigurator.register_llm(name, model_class, metadata=metadata)
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
        llm_registry = ComponentConfigurator._registries['llm']

        if model_type:
            model_class = llm_registry.get(model_type)
            if not model_class:
                # Try legacy registry
                legacy_registry = ModelFactory._get_legacy_registry()
                if model_type in legacy_registry:
                    model_class = legacy_registry[model_type]
                else:
                    raise ValueError(f"Unknown model type: {model_type}")

            try:
                models[model_type] = model_class.models()
            except Exception as e:
                logger.warning(f"Failed to get models for {model_type}: {e}")
                models[model_type] = []
        else:
            # Get all model types from registry
            for type_name in ModelFactory.get_available_types():
                try:
                    model_class = llm_registry.get(type_name)
                    if not model_class:
                        # Try legacy registry
                        legacy_registry = ModelFactory._get_legacy_registry()
                        if type_name in legacy_registry:
                            model_class = legacy_registry[type_name]
                        else:
                            continue
                            
                    models[type_name] = model_class.models()
                except Exception as e:
                    logger.warning(f"Failed to get models for {type_name}: {e}")
                    models[type_name] = []

        return models
