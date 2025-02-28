# rvandroid/llm/llm.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class LanguageModel(ABC):
    """
    Abstract base class for all language models.
    Defines the common interface and functionality that all LLM implementations must provide.
    """

    def __init__(self, model_name: str):
        """
        Initialize the language model with a model name.

        Args:
            model_name: Name or identifier of the model
        """
        self.model_name = model_name

    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800) -> str:
        """
        Generate text based on the given messages.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_new_tokens: Maximum number of tokens to generate

        Returns:
            Generated text response

        Raises:
            Exception: If text generation fails
        """
        pass

    @abstractmethod
    def clean(self) -> None:
        """
        Clean up resources used by the model.
        This should release memory, close connections, etc.
        """
        pass

    @staticmethod
    @abstractmethod
    def models() -> List[str]:
        """
        Returns a list of available models for this provider.

        Returns:
            List of model identifiers
        """
        pass

    def __str__(self) -> str:
        """
        String representation of the language model.

        Returns:
            String representation
        """
        return f"{self.__class__.__name__}: {self.model_name}"