from abc import ABC, abstractmethod
from typing import List, Dict


class LanguageModel(ABC):
    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name

    @abstractmethod
    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 800) -> str:
        """Generates text based on the given messages."""
        pass

    @abstractmethod
    def clean(self):
        """Unloads the model and tokenizer from memory."""
        pass

    @staticmethod
    @abstractmethod
    def models() -> List[str]:
        """Returns a list of available models."""
        pass
