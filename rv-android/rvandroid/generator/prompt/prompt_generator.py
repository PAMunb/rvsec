from abc import ABC, abstractmethod
from typing import List, Dict


class PromptGenerator(ABC):
    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name

    @abstractmethod
    def generate_prompt(self, llm) -> str:
        """Generates text based on the given messages."""
        pass