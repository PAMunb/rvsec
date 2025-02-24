# rvandroid/llm/model_factory.py
from typing import Dict, Any, Optional
from rvandroid.llm.llm import LanguageModel
from rvandroid.llm.huggingface import HuggingFaceLLM
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.langchain_llm import LangchainLLM
from rvandroid.llm.dspy_llm import DSPyLLM


class ModelFactory:
    """
    Factory class for creating language model instances.
    """
    
    # Registry of available model types
    _REGISTRY = {
        "huggingface": HuggingFaceLLM,
        "ollama": OllamaLLM,
        "langchain": LangchainLLM,
        "dspy": DSPyLLM
    }
    
    @staticmethod
    def create(model_type: str, model_name: str, **kwargs) -> LanguageModel:
        """
        Create a language model instance.
        
        Args:
            model_type: Type of model ('huggingface', 'ollama', 'langchain', 'dspy')
            model_name: Name of the model
            **kwargs: Additional arguments for the model constructor
            
        Returns:
            LanguageModel instance
        """
        if model_type not in ModelFactory._REGISTRY:
            raise ValueError(f"Unknown model type: {model_type}")
        
        model_class = ModelFactory._REGISTRY[model_type]
        return model_class(model_name, **kwargs)
    
    @staticmethod
    def get_available_types() -> Dict[str, Any]:
        """
        Returns a dictionary of available model types and their classes.
        
        Returns:
            Dictionary of model types
        """
        return ModelFactory._REGISTRY.copy()
    
    @staticmethod
    def register_model_type(name: str, model_class: Any) -> None:
        """
        Register a new model type.
        
        Args:
            name: Name of the model type
            model_class: Model class
        """
        ModelFactory._REGISTRY[name] = model_class
    
    @staticmethod
    def get_available_models(model_type: Optional[str] = None) -> Dict[str, list]:
        """
        Returns available models for a specific type or all types.
        
        Args:
            model_type: Type of model to get models for (optional)
            
        Returns:
            Dictionary of model types and their available models
        """
        models = {}
        
        if model_type:
            if model_type not in ModelFactory._REGISTRY:
                raise ValueError(f"Unknown model type: {model_type}")
            model_class = ModelFactory._REGISTRY[model_type]
            models[model_type] = model_class.models()
        else:
            for type_name, model_class in ModelFactory._REGISTRY.items():
                models[type_name] = model_class.models()
        
        return models